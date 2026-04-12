import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'BSI_base'
_modversion = '0.0.1'

class BSI_base(TabbedPanelItem):

    _ignition_on = 0x01
    _ignition_off = 0x02
    _ignition_wakeup = 0x03
    _ignition_settled_off = 0x00
    _lights_off = 0
    _lights_side = 1
    _lights_low = 2
    _lights_high = 3

    _lights_to_128 = {
        _lights_off: 0x00,
        _lights_side: 0x80,
        _lights_low: 0xC0,
        _lights_high: 0xE0,
    }

    _settle_off_delay_s = 14.0
    _wakeup_pulse_s = 0.04
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Base'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/bsi.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering BSI calls')
        runner.register(50, self.can_commandes)
        runner.register(100, self.can_slow)
        runner.register(1000, self.can_vin_vis)
        runner.register(1000, self.can_vin_wmi)
        runner.register(1000, self.can_vin_vds)
        runner.register(50, self.can_fast)
        runner.register(100, self.can_temp_level)
        runner.register(100, self.can_110)
        runner.register(200, self.can_128)
        runner.register(200, self.can_190)
        runner.register(500, self.can_1d0)
        runner.register(200, self.can_1e3)
        runner.register(100, self.can_217)
        runner.register(1000, self.can_52d)

        # COMMANDES_BSI values
        self.commands = {
            'economy': 0,
            'dash_lights': 0,
            'dark_mode': 0,
            'light_mode': BSI_base._lights_off,
            'lum': 10,
            'power_mode': BSI_base._ignition_off,
            'engine_running': 0
        }

        self.gauges = {
            'rpm': 0,
            'speed': 0,
            'fuel': 0,
            'oil': 0,
            'coolant': 0
        }
        self.temperature = 20
        self._updating_power_buttons = False
        self._updating_light_buttons = False
        self._set_off_event = None
        self._ignition_finalize_event = None
        self._rolling_190 = 0
        self.runner.ignition_on = False
        if not hasattr(self.runner, 'reverse'):
            self.runner.reverse = 0
        self.set_power_mode(self.commands['power_mode'])
        self._apply_monitor_ui_lock()

    def on_command(self, command, value):
        if command in ['economy', 'dash_lights', 'dark_mode']:
            value = 1 if value == 'down' else 0
        if command == 'light_mode':
            if self._updating_light_buttons:
                return
            self.set_light_mode(int(value), update_ui=True)
            return
        if command == 'lum':
            self.ids['cur_lum'].text = f'lum: {value}'
        if command == 'power_mode':
            if self._updating_power_buttons:
                return
            self.transition_power_mode(value)
            return
        self.commands[command] = int(value)

    def _apply_monitor_ui_lock(self):
        if not getattr(self.runner, 'monitor', False):
            return
        control_ids = [
            'economy', 'dash_lights', 'dark_mode',
            'lights_off', 'lights_side', 'lights_low', 'lights_high',
            'sleeping', 'ignition', 'wakeup', 'engine',
            'slider_lum', 'slider_temp', 'slider_rpm', 'slider_speed',
            'slider_fuel', 'slider_oil', 'slider_coolant',
        ]
        for wid in control_ids:
            if wid in self.ids:
                self.ids[wid].disabled = True

    def set_light_mode(self, mode, update_ui=False, sync_dash=True):
        mode = int(mode)
        if mode < BSI_base._lights_off:
            mode = BSI_base._lights_off
        if mode > BSI_base._lights_high:
            mode = BSI_base._lights_high

        self.commands['light_mode'] = mode

        # Keep this behavior for local UI actions, but do not force lum/dash when
        # synchronizing from received 0x128 frames.
        if sync_dash:
            if mode == BSI_base._lights_off:
                self.commands['dash_lights'] = 0
                self.commands['dark_mode'] = 0
                self.commands['lum'] = 15
            else:
                self.commands['dash_lights'] = 1
                self.commands['dark_mode'] = 0
                self.commands['lum'] = 10

        if not update_ui:
            return

        self._updating_light_buttons = True
        if 'lights_off' in self.ids:
            self.ids['lights_off'].state = 'down' if mode == BSI_base._lights_off else 'normal'
        if 'lights_side' in self.ids:
            self.ids['lights_side'].state = 'down' if mode == BSI_base._lights_side else 'normal'
        if 'lights_low' in self.ids:
            self.ids['lights_low'].state = 'down' if mode == BSI_base._lights_low else 'normal'
        if 'lights_high' in self.ids:
            self.ids['lights_high'].state = 'down' if mode == BSI_base._lights_high else 'normal'
        self._updating_light_buttons = False
        if 'dash_lights' in self.ids:
            self.ids['dash_lights'].state = 'down' if self.commands['dash_lights'] else 'normal'
        if 'dark_mode' in self.ids:
            self.ids['dark_mode'].state = 'down' if self.commands['dark_mode'] else 'normal'
        if 'cur_lum' in self.ids:
            self.ids['cur_lum'].text = f"lum: {self.commands['lum']}"
        if 'slider_lum' in self.ids and self.ids['slider_lum'].value != self.commands['lum']:
            self.ids['slider_lum'].value = self.commands['lum']

    def _cancel_power_timers(self):
        if self._set_off_event is not None:
            self._set_off_event.cancel()
            self._set_off_event = None
        if self._ignition_finalize_event is not None:
            self._ignition_finalize_event.cancel()
            self._ignition_finalize_event = None

    def transition_power_mode(self, value):
        target_mode = int(value)
        self._cancel_power_timers()

        if target_mode == BSI_base._ignition_on:
            # Real traces show a short wakeup pulse before stable ignition ON.
            self.set_power_mode(BSI_base._ignition_wakeup)
            self._ignition_finalize_event = Clock.schedule_once(
                lambda _dt: self.set_power_mode(BSI_base._ignition_on),
                BSI_base._wakeup_pulse_s,
            )
            return

        if target_mode == BSI_base._ignition_off:
            # Real cold-start settles from 0x02 to 0x00 after startup.
            self.set_power_mode(BSI_base._ignition_off)
            self._set_off_event = Clock.schedule_once(
                lambda _dt: self.set_power_mode(BSI_base._ignition_settled_off),
                BSI_base._settle_off_delay_s,
            )
            return

        self.set_power_mode(target_mode)

    def set_power_mode(self, value):
        power_mode = int(value)
        self.commands['power_mode'] = power_mode
        self.runner.ignition_on = (power_mode == BSI_base._ignition_on)
        self.runner.power_mode = power_mode
        self._updating_power_buttons = True
        self.commands['power_mode'] = power_mode
        if power_mode == BSI_base._ignition_on:
            if 'engine' in self.ids:
                self.ids['engine'].disabled = False
        else:
            if 'engine' in self.ids:
                self.ids['engine'].disabled = True
                self.ids['engine'].state = 'normal'
                self.ids['engine'].text = 'Engine'
            self.commands['engine_running'] = 0
            self.on_val('rpm', 0)
            self.on_val('speed', 0)

        if 'ignition' in self.ids:
            self.ids['ignition'].state = 'down' if power_mode == BSI_base._ignition_on else 'normal'
        if 'sleeping' in self.ids:
            self.ids['sleeping'].state = 'down' if power_mode == 0x00 else 'normal'
        if 'wakeup' in self.ids:
            self.ids['wakeup'].state = 'down' if power_mode == BSI_base._ignition_wakeup else 'normal'
        self._updating_power_buttons = False

    def toggle_engine(self, state):
        if self.commands['power_mode'] != BSI_base._ignition_on:
            return
        if state == 'down':
            self.commands['engine_running'] = 1
            self.on_val('rpm', 800)
            self.on_val('speed', 10)
            self.on_val('fuel', 30)
            self.on_val('oil', 65)
            self.on_val('coolant', 60)
        else:
            self.commands['engine_running'] = 0
            self.on_val('rpm', 0)
            self.on_val('speed', 0)
            if 'engine' in self.ids:
                self.ids['engine'].text = 'Engine'

    def on_temp(self, step, value):
        # Avoid overflows, anything over 250 (85.0) is not displayed
        if self.temperature == -40 and value == -0.5:
            return
        elif self.temperature == 85 and value == +0.5:
            return

        if step:
            self.temperature += value
        else:
            self.temperature = value
        self.ids['cur_ext_temp'].text = f'temp: {self.temperature}'
        if 'slider_temp' in self.ids and self.ids['slider_temp'].value != self.temperature:
            self.ids['slider_temp'].value = self.temperature

    def on_val(self, name, value):
        texts = {
            'rpm': 'RPM: {}',
            'speed': 'Speed: {} km/h',
            'fuel': 'Fuel: {}%',
            'oil': 'Oil temp: {} deg',
            'coolant': 'Coolant temp: {} deg'
        }

        self.ids[f'cur_{name}'].text = texts[name].format(value)
        slider_id = f'slider_{name}'
        if slider_id in self.ids and self.ids[slider_id].value != value:
            self.ids[slider_id].value = value
        self.gauges[name] = int(value)

    def can_commandes(self):
        com = self.commands
        b2 = com['economy']<<7
        b3 = com['dash_lights']<<5 | com['dark_mode']<<4 | com['lum']&0xFF
        b4 = com['power_mode']
        return 0x036, [0x0E, 0x00, b2, b3, b4, 0x80, 0x00, 0xA0]

    def can_slow(self):
        temp = int((self.temperature+40)*2)
        coolant = int(self.gauges['coolant']+40)
        reverse = (int(getattr(self.runner, 'reverse', 0)) << 7) | 0x01
        return 0x0F6, [0x08, coolant, 0x00, 0x1F, 0x00, temp, temp, reverse]

    def can_fast(self):
        rpm = int(self.gauges['rpm']*10)
        speed = int(self.gauges['speed']*100)
        return 0x0B6, [rpm>>8, rpm&0xFF, speed>>8, speed&0xFF, 0x00, 0x00, 0x00, 0x00]
    
    def can_vin_vis(self):
        #32 31 37 31 35 33 38 33
        return 0x2B6, [0x32, 0x31, 0x37, 0x31, 0x35, 0x33, 0x38, 0x33]

    def can_vin_wmi(self):
        #56 46 33
        return 0x336, [0x56, 0x46, 0x33]

    def can_vin_vds(self):
        #36 4A 52 48 52 48
        return 0x3B6, [0x36, 0x4A, 0x52, 0x48, 0x52, 0x48]

    def can_temp_level(self):
        oil = self.gauges['oil']+40
        return 0x161, [0x00, 0x00, oil, self.gauges['fuel'], 0xff, 0xff, 0xff, 0xff]

    def can_110(self):
        return 0x110, [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]

    def can_128(self):
        d5 = BSI_base._lights_to_128.get(self.commands['light_mode'], 0x00)
        return 0x128, [0x91, 0xE0, 0x00, 0x00, d5, 0x80, 0xB0, 0x01]

    def can_190(self):
        mode = int(self.commands['power_mode'])
        if mode == BSI_base._ignition_on:
            # Keep low bit rolling as seen on real bus in ignition-on state.
            d4 = 0x7E | self._rolling_190
            self._rolling_190 ^= 0x01
        else:
            d4 = 0x77
            self._rolling_190 = 0
        return 0x190, [0xFF, 0xFF, 0x02, d4, 0xFF, 0xFF, 0xFF, 0xFF]

    def can_1d0(self):
        return 0x1D0, [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]

    def can_1e3(self):
        d2 = 0x30 if int(self.commands['power_mode']) == BSI_base._ignition_on else 0x40
        return 0x1E3, [0x1C, d2, 0x0B, 0x0B, 0x00, 0x00, 0x00, 0x00]

    def can_217(self):
        if int(self.commands['power_mode']) == BSI_base._ignition_on:
            return 0x217, [0xA1, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xE0]
        return 0x217, [0xA0, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00]

    def can_52d(self):
        if int(self.commands['power_mode']) == BSI_base._ignition_on:
            return 0x52D, [0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]
        return 0x52D, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            b2 = msg.data[2]
            b3 = msg.data[3]
            b4 = msg.data[4]
            economy = (b2 >> 7) & 1
            dash_lights = (b3 >> 5) & 1
            dark_mode = (b3 >> 4) & 1
            lum = b3 & 0x0F
            power_mode = b4
            self.commands['economy'] = economy
            self.commands['dash_lights'] = dash_lights
            self.commands['dark_mode'] = dark_mode
            self.commands['lum'] = lum
            self.ids['economy'].state = 'down' if economy else 'normal'
            self.ids['dash_lights'].state = 'down' if dash_lights else 'normal'
            self.ids['dark_mode'].state = 'down' if dark_mode else 'normal'
            self.ids['cur_lum'].text = f'lum: {lum}'
            if 'slider_lum' in self.ids:
                self.ids['slider_lum'].value = lum
            self.set_power_mode(power_mode)
        elif msg.arbitration_id == 0x0B6 and len(msg.data) >= 4:
            rpm = (msg.data[0] << 8) | msg.data[1]
            speed = (msg.data[2] << 8) | msg.data[3]
            self.on_val('rpm', int(rpm / 10))
            self.on_val('speed', int(speed / 100))
            engine_running = 1 if rpm > 0 else 0
            self.commands['engine_running'] = engine_running
            if 'engine' in self.ids:
                self.ids['engine'].state = 'down' if engine_running else 'normal'
        elif msg.arbitration_id == 0x161 and len(msg.data) >= 4:
            self.on_val('oil', int(msg.data[2]) - 40)
            self.on_val('fuel', int(msg.data[3]))
        elif msg.arbitration_id == 0x0F6 and len(msg.data) >= 8:
            coolant = int(msg.data[1])
            temp = int(msg.data[5])
            self.on_val('coolant', coolant - 40)
            self.on_temp(False, temp / 2 - 40)
        elif msg.arbitration_id == 0x217 and len(msg.data) >= 8:
            raw_bytes = ' '.join(f'{b:02X}' for b in msg.data)
            if 'cur_217_raw' in self.ids:
                self.ids['cur_217_raw'].text = f'0x217: {raw_bytes}'
        elif msg.arbitration_id == 0x128 and len(msg.data) >= 5:
            d5 = int(msg.data[4]) & 0xE0
            if d5 & 0x20:
                light_mode = BSI_base._lights_high
            elif d5 & 0x40:
                light_mode = BSI_base._lights_low
            elif d5 & 0x80:
                light_mode = BSI_base._lights_side
            else:
                light_mode = BSI_base._lights_off
            self.set_light_mode(light_mode, update_ui=True, sync_dash=False)
