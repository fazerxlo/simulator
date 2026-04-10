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

    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Base'

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/bsi.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering BSI calls')
        runner.register(50, self.can_commandes)
        runner.register(100, self.can_slow)
        runner.register(100, self.can_vin_vis)
        runner.register(100, self.can_vin_wmi)
        runner.register(100, self.can_vin_vds)
        runner.register(100, self.parktronic)
        runner.register(50, self.can_fast)
        runner.register(100, self.can_temp_level)

        # COMMANDES_BSI values
        self.commands = {
            'economy': 0,
            'dash_lights': 0,
            'dark_mode': 0,
            'reverse': 0,
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

    def on_command(self, command, value):
        if command in ['economy', 'dash_lights', 'dark_mode', 'reverse']:
            value = 1 if value == 'down' else 0
        if command == 'lum':
            self.ids['cur_lum'].text = f'lum: {value}'
        if command == 'power_mode':
            self.set_power_mode(value)
            return
        self.commands[command] = int(value)

    def set_power_mode(self, value):
        power_mode = int(value)
        self.commands['power_mode'] = power_mode
        if power_mode == BSI_base._ignition_on:
            self.ids['engine'].disabled = False
        else:
            self.ids['engine'].disabled = True
            self.commands['engine_running'] = 0
            self.on_val('rpm', 0)
            self.on_val('speed', 0)

        if 'ignition' in self.ids:
            self.ids['ignition'].state = 'down' if power_mode == BSI_base._ignition_on else 'normal'
        if 'sleeping' in self.ids:
            self.ids['sleeping'].state = 'down' if power_mode == 0x00 else 'normal'
        if 'wakeup' in self.ids:
            self.ids['wakeup'].state = 'down' if power_mode == BSI_base._ignition_wakeup else 'normal'

    def start_engine(self):
        if self.commands['power_mode'] != BSI_base._ignition_on:
            return
        self.commands['engine_running'] = 1
        self.on_val('rpm', 800)
        self.on_val('speed', 10)
        self.on_val('fuel', 30)
        self.on_val('oil', 65)
        self.on_val('coolant', 60)

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
        com = self.commands
        reverse = int(com['reverse'])<<7 | 0x01
        return 0x0F6, [0x08, coolant, 0x00, 0x1F, 0x00, temp, temp, reverse]

    def can_fast(self):
        rpm = int(self.gauges['rpm']*10)
        speed = int(self.gauges['speed']*100)
        return 0x0B6, [rpm>>8, rpm&0xFF, speed>>8, speed&0xFF, 0x00, 0x00, 0x00, 0x00]
    
    def parktronic(self):
        com = self.commands
        if int(com['reverse']) == 1:
            return 0x0E1, [0x24, 0xD0, 0xCC, 0x11, 0x5C, 0xFE, 0xC2]
        else:
            return 0x0E1, None
        # 0x0E1, [0x24, 0x00, 0x3F, 0xFC, 0xFC, 0xFC, 0x00]
        # D8 00 3F FC FC FC 00

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
        elif msg.arbitration_id == 0x161 and len(msg.data) >= 4:
            self.on_val('oil', int(msg.data[2]) - 40)
            self.on_val('fuel', int(msg.data[3]))
        elif msg.arbitration_id == 0x0F6 and len(msg.data) >= 8:
            reverse = (msg.data[7] >> 7) & 1
            self.commands['reverse'] = reverse
            if 'reverse' in self.ids:
                self.ids['reverse'].state = 'down' if reverse else 'normal'
            coolant = int(msg.data[1])
            temp = int(msg.data[5])
            self.on_val('coolant', coolant - 40)
            self.on_temp(False, temp / 2 - 40)
        elif msg.arbitration_id == 0x217 and len(msg.data) >= 8:
            raw_bytes = ' '.join(f'{b:02X}' for b in msg.data)
            if 'cur_217_raw' in self.ids:
                self.ids['cur_217_raw'].text = f'0x217: {raw_bytes}'
