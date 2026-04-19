import datetime
import logging
import os
from functools import partial

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import (
    Msg036, Msg0B6, Msg0F6, Msg110, Msg12D, Msg128, Msg161, Msg168,
    Msg190, Msg1A1, Msg1D0, Msg1E3, Msg217, Msg2B6, Msg336, Msg3B6, Msg52D,
    STARTUP_WAKEUP_BURST,
)

_modname = 'BSI_base'
_modversion = '0.0.1'

logger = logging.getLogger(__name__)

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

        # Register per-CAN-ID message objects.  Each class owns exactly one
        # arbitration ID; the runner calls encode() periodically and decode()
        # when a matching frame is received.
        logger.debug('registering BSI base messages')
        runner.register_message(Msg036())
        runner.register_message(Msg0B6())
        runner.register_message(Msg0F6())
        runner.register_message(Msg110())
        runner.register_message(Msg128())
        runner.register_message(Msg161())
        runner.register_message(Msg168())
        runner.register_message(Msg190())
        runner.register_message(Msg1A1())
        runner.register_message(Msg1D0())
        runner.register_message(Msg1E3())
        runner.register_message(Msg12D())
        runner.register_message(Msg217())
        runner.register_message(Msg2B6())
        runner.register_message(Msg336())
        runner.register_message(Msg3B6())
        runner.register_message(Msg52D())

        # Initialise BSI state on the shared VirtualCar.  All reads and
        # writes go through runner.car.bsi so that other modules (e.g.
        # clim, parktronic) can observe changes without ad-hoc runner attrs.
        bsi = runner.car.bsi
        bsi.economy = 0
        bsi.dash_lights = 0
        bsi.dark_mode = 0
        bsi.light_mode = BSI_base._lights_off
        bsi.lum = 15
        bsi.power_mode = BSI_base._ignition_off
        bsi.engine_running = 0
        bsi.rpm = 0
        bsi.speed = 0
        bsi.fuel = 0
        bsi.oil = 0
        bsi.coolant = 0
        bsi.temperature = 20
        bsi.ignition_on = False
        bsi.reverse = 0
        bsi.startup_banner_pending = True

        self._updating_power_buttons = False
        self._updating_light_buttons = False
        self._set_off_event = None
        self._ignition_finalize_event = None
        self._wakeup_burst_events = []
        self.set_power_mode(bsi.power_mode)
        self.set_light_mode(bsi.light_mode, update_ui=True)
        self._apply_monitor_ui_lock()

    @property
    def _bsi(self):
        """Convenience accessor for the shared BSI car state."""
        return self.runner.car.bsi

    def _sync_dashboard_power_from_bsi(self):
        dash = getattr(self.runner.car, 'dashboard', None)
        if dash is None:
            return
        dash.on = 1 if (
            self._bsi.ignition_on
            or int(self._bsi.power_mode) in (BSI_base._ignition_on, BSI_base._ignition_wakeup)
        ) else 0

    def _sync_dashboard_lights_from_bsi(self):
        dash = getattr(self.runner.car, 'dashboard', None)
        if dash is None:
            return
        mode = int(self._bsi.light_mode)
        dash.backlight = 1 if mode >= BSI_base._lights_side else 0
        dash.low_beam = 1 if mode == BSI_base._lights_low else 0
        dash.high_beam = 1 if mode == BSI_base._lights_high else 0

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
        setattr(self._bsi, command, int(value))

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

        _light_names = {
            BSI_base._lights_off: 'off',
            BSI_base._lights_side: 'side lights',
            BSI_base._lights_low: 'low beam',
            BSI_base._lights_high: 'high beam',
        }
        if self._bsi.light_mode != mode:
            logger.info('Lights set to %s', _light_names.get(mode, str(mode)))

        self._bsi.light_mode = mode
        self._sync_dashboard_lights_from_bsi()

        # Keep this behavior for local UI actions, but do not force lum/dash when
        # synchronizing from received 0x128 frames.
        if sync_dash:
            if mode == BSI_base._lights_off:
                self._bsi.dash_lights = 0
                self._bsi.dark_mode = 0
                self._bsi.lum = 15
            else:
                self._bsi.dash_lights = 1
                self._bsi.dark_mode = 0
                self._bsi.lum = 10

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
            self.ids['dash_lights'].state = 'down' if self._bsi.dash_lights else 'normal'
        if 'dark_mode' in self.ids:
            self.ids['dark_mode'].state = 'down' if self._bsi.dark_mode else 'normal'
        if 'cur_lum' in self.ids:
            self.ids['cur_lum'].text = f"lum: {self._bsi.lum}"
        if 'slider_lum' in self.ids and self.ids['slider_lum'].value != self._bsi.lum:
            self.ids['slider_lum'].value = self._bsi.lum

    def _cancel_power_timers(self):
        if self._set_off_event is not None:
            self._set_off_event.cancel()
            self._set_off_event = None
        if self._ignition_finalize_event is not None:
            self._ignition_finalize_event.cancel()
            self._ignition_finalize_event = None
        for event in self._wakeup_burst_events:
            event.cancel()
        self._wakeup_burst_events = []

    def _send_wakeup_frame(self, arbitration_id, data, _dt=0):
        self.runner.send_message(arbitration_id, list(data))

    def _schedule_wakeup_burst(self):
        if getattr(self.runner, 'monitor', False):
            return
        for delay_s, arbitration_id, data in STARTUP_WAKEUP_BURST:
            event = Clock.schedule_once(partial(self._send_wakeup_frame, arbitration_id, data), delay_s)
            self._wakeup_burst_events.append(event)

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
        previous_mode = int(self._bsi.power_mode)
        power_mode = int(value)
        _mode_names = {
            BSI_base._ignition_settled_off: 'sleeping',
            BSI_base._ignition_on: 'ON',
            BSI_base._ignition_off: 'OFF',
            BSI_base._ignition_wakeup: 'wakeup',
        }
        if previous_mode != power_mode:
            logger.info('Ignition %s', _mode_names.get(power_mode, f'mode 0x{power_mode:02X}'))
        self._bsi.power_mode = power_mode
        self._bsi.ignition_on = (power_mode == BSI_base._ignition_on)
        self._sync_dashboard_power_from_bsi()
        self._updating_power_buttons = True
        if power_mode == BSI_base._ignition_on:
            if 'engine' in self.ids:
                self.ids['engine'].disabled = False
        else:
            if 'engine' in self.ids:
                self.ids['engine'].disabled = True
                self.ids['engine'].state = 'normal'
                self.ids['engine'].text = 'Engine'
            self._bsi.engine_running = 0
            self.on_val('rpm', 0)
            self.on_val('speed', 0)

        if 'ignition' in self.ids:
            self.ids['ignition'].state = 'down' if power_mode == BSI_base._ignition_on else 'normal'
        if 'sleeping' in self.ids:
            self.ids['sleeping'].state = 'down' if power_mode == 0x00 else 'normal'
        if 'wakeup' in self.ids:
            self.ids['wakeup'].state = 'down' if power_mode == BSI_base._ignition_wakeup else 'normal'
        self._updating_power_buttons = False

        if (
            power_mode == BSI_base._ignition_on
            and previous_mode != BSI_base._ignition_on
        ):
            self._schedule_wakeup_burst()

    def toggle_engine(self, state):
        if self._bsi.power_mode != BSI_base._ignition_on:
            return
        if state == 'down':
            logger.info('Engine started')
            self._bsi.engine_running = 1
            self.on_val('rpm', 800)
            self.on_val('speed', 10)
            self.on_val('fuel', 30)
            self.on_val('oil', 65)
            self.on_val('coolant', 60)
        else:
            logger.info('Engine stopped')
            self._bsi.engine_running = 0
            self.on_val('rpm', 0)
            self.on_val('speed', 0)
            if 'engine' in self.ids:
                self.ids['engine'].text = 'Engine'

    def on_temp(self, step, value):
        # Avoid overflows, anything over 250 (85.0) is not displayed
        if self._bsi.temperature == -40 and value == -0.5:
            return
        elif self._bsi.temperature == 85 and value == +0.5:
            return

        if step:
            self._bsi.temperature += value
        else:
            self._bsi.temperature = value
        logger.info('Outside temperature set to %s°C', self._bsi.temperature)
        self.ids['cur_ext_temp'].text = f'temp: {self._bsi.temperature}'
        if 'slider_temp' in self.ids and self.ids['slider_temp'].value != self._bsi.temperature:
            self.ids['slider_temp'].value = self._bsi.temperature

    def on_val(self, name, value):
        texts = {
            'rpm': 'RPM: {}',
            'speed': 'Speed: {} km/h',
            'fuel': 'Fuel: {}%',
            'oil': 'Oil temp: {} deg',
            'coolant': 'Coolant temp: {} deg'
        }
        log_msgs = {
            'rpm': 'RPM set to {}',
            'speed': 'Speed set to {} km/h',
            'fuel': 'Fuel level set to {}%',
            'oil': 'Oil temperature set to {}°C',
            'coolant': 'Coolant temperature set to {}°C',
        }

        logger.info(log_msgs[name].format(value))
        self.ids[f'cur_{name}'].text = texts[name].format(value)
        slider_id = f'slider_{name}'
        if slider_id in self.ids and self.ids[slider_id].value != value:
            self.ids[slider_id].value = value
        setattr(self._bsi, name, int(value))

    def can_commandes(self):
        bsi = self._bsi
        b2 = bsi.economy << 7
        b3 = bsi.dash_lights << 5 | bsi.dark_mode << 4 | bsi.lum & 0xFF
        b4 = bsi.power_mode
        return 0x036, [0x0E, 0x00, b2, b3, b4, 0x80, 0x00, 0xA0]

    def can_slow(self):
        bsi = self._bsi
        temp = int((bsi.temperature + 40) * 2)
        coolant = int(bsi.coolant + 40)
        reverse = (int(bsi.reverse) << 7) | 0x01
        return 0x0F6, [0x08, coolant, 0x00, 0x1F, 0x00, temp, temp, reverse]

    def can_fast(self):
        bsi = self._bsi
        rpm = max(0, int(bsi.rpm)) << 3
        speed = int(bsi.speed * 100)
        return 0x0B6, [rpm >> 8, rpm & 0xFF, speed >> 8, speed & 0xFF, 0x00, 0x00, 0x00, 0xD0]

    def can_vin_vis(self):
        #32 31 37 31 35 33 38 33
        return 0x2B6, [0x32, 0x31, 0x37, 0x31, 0x35, 0x33, 0x38, 0x33]

    def can_vin_wmi(self):
        #56 46 33
        return 0x336, [0x56, 0x46, 0x33]

    def can_vin_vds(self):
        #36 4A 52 48 52 48
        return 0x3B6, [0x36, 0x4A, 0x52, 0x48, 0x52, 0x48]

    def can_110(self):
        return 0x110, [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00]

    def can_128(self):
        d5 = BSI_base._lights_to_128.get(self._bsi.light_mode, 0x00)
        return 0x128, [0x91, 0xE0, 0x00, 0x00, d5, 0x80, 0xB0, 0x01]

    def can_190(self):
        mode = int(self._bsi.power_mode)
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
        d2 = 0x30 if int(self._bsi.power_mode) == BSI_base._ignition_on else 0x40
        return 0x1E3, [0x1C, d2, 0x0B, 0x0B, 0x00, 0x00, 0x00, 0x00]

    def can_217(self):
        if int(self._bsi.power_mode) == BSI_base._ignition_on:
            return 0x217, [0xA1, 0x00, 0x80, 0x00, 0x00, 0xFF, 0xFF, 0xE0]
        return 0x217, [0xA0, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00, 0x00]

    def can_52d(self):
        if int(self._bsi.power_mode) == BSI_base._ignition_on:
            return 0x52D, [0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00]
        return 0x52D, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            b3 = msg.data[3]
            b4 = msg.data[4]
            economy = (msg.data[2] >> 7) & 1
            dash_lights = (b3 >> 5) & 1
            dark_mode = (b3 >> 4) & 1
            lum = b3 & 0x0F
            power_mode = b4
            # Car state already updated by Msg036.decode(); just sync UI.
            self.ids['economy'].state = 'down' if economy else 'normal'
            self.ids['dash_lights'].state = 'down' if dash_lights else 'normal'
            self.ids['dark_mode'].state = 'down' if dark_mode else 'normal'
            self.ids['cur_lum'].text = f'lum: {lum}'
            if 'slider_lum' in self.ids:
                self.ids['slider_lum'].value = lum
            self.set_power_mode(power_mode)
        elif msg.arbitration_id == 0x0B6 and len(msg.data) >= 4:
            # Msg0B6.decode() has already normalized invalid placeholders such
            # as 0xFFFF into sane shared state values; sync the UI from that.
            self.on_val('rpm', self._bsi.rpm)
            self.on_val('speed', self._bsi.speed)
            if 'engine' in self.ids:
                self.ids['engine'].state = 'down' if self._bsi.engine_running else 'normal'
        elif msg.arbitration_id == 0x161 and len(msg.data) >= 4:
            self.on_val('oil', self._bsi.oil)
            self.on_val('fuel', self._bsi.fuel)
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
            # Msg128.decode() already updated car state; just sync the light mode UI.
            self.set_light_mode(self._bsi.light_mode, update_ui=True, sync_dash=False)

