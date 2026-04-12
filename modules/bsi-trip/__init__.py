import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'BSI_trip'
_modversion = '0.0.1'

class BSI_trip(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Trip'

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/bsi.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering BSI calls')
        runner.register(100, self.can_inst)
        runner.register(100, self.can_trip1)
        runner.register(100, self.can_trip2)

        self.inst_params = {
            'hide_fuel': 0,
            'hide_dist': 0,
            'com_left': 0,
            'com_right': 0,
            'fuel': 7.1,
            'autonomy': 740,
            'dist': 120
        }

        self.history = [
            {'speed': 37, 'dist': 569, 'fuel': 7.3},
            {'speed': 35, 'dist': 921, 'fuel': 7.9}
        ]

        self._apply_initial_values()

    def _apply_initial_values(self):
        # Seed UI with realistic trip values so startup state is not all zeros.
        self.on_inst_param('fuel', self.inst_params['fuel'])
        self.on_inst_param('autonomy', self.inst_params['autonomy'])
        self.on_inst_param('dist', self.inst_params['dist'])
        self.on_hist_param(0, 'speed', self.history[0]['speed'])
        self.on_hist_param(0, 'dist', self.history[0]['dist'])
        self.on_hist_param(0, 'fuel', self.history[0]['fuel'])
        self.on_hist_param(1, 'speed', self.history[1]['speed'])
        self.on_hist_param(1, 'dist', self.history[1]['dist'])
        self.on_hist_param(1, 'fuel', self.history[1]['fuel'])

    def on_inst_button(self, name, value):
        self.inst_params[name] = 1 if value == 'down' else 0

    def on_inst_param(self, param, value):
        labels = {
            'fuel': 'fuel consumption: {:2.1f} l/km',
            'autonomy': 'autonomy: {} km',
            'dist': 'dist to dest: {} km'
        }
        self.inst_params[param] = value
        self.ids[f'cur_inst_{param}'].text = labels[param].format(value)
        slider_id = f'slider_inst_{param}'
        if slider_id in self.ids and self.ids[slider_id].value != value:
            self.ids[slider_id].value = value

    def on_hist_param(self, hist, param, value):
        labels = {
            'speed': 'average speed: {} km/h',
            'dist': 'distance: {} km',
            'fuel': 'average consumption: {:2.1f} l/km'
        }
        self.history[hist][param] = value
        self.ids[f'cur_hist{hist}_{param}'].text = labels[param].format(value)
        slider_id = f'slider_hist{hist}_{param}'
        if slider_id in self.ids and self.ids[slider_id].value != value:
            self.ids[slider_id].value = value

    def can_inst(self):
        params = self.inst_params
        # Other bits seems unused
        b0 = params['hide_fuel']<<7 | params['hide_dist']<<6 | params['com_right']<<3 | params['com_left']
        fuel = int(params['fuel']*10)
        autonomy = int(params['autonomy'])
        distance = int(params['dist']*10)
        return 0x221, [b0, fuel>>8, fuel&0xFF, autonomy>>8, autonomy&0xFF, distance>>8, distance&0xFF]

    def can_trip1(self):
        hist = self.history[0]
        dist = int(hist['dist'])
        fuel = int(hist['fuel']*10)
        # No idea why there's two trailing bytes, but they're needed
        # Else everything shows "--"
        return 0x2A1, [int(hist['speed']), dist>>8, dist&0xFF, fuel>>8, fuel&0xFF, 0x00, 0x00]

    def can_trip2(self):
        hist = self.history[1]
        dist = int(hist['dist'])
        fuel = int(hist['fuel']*10)
        # No idea why there's two trailing bytes, but they're needed
        # Else everything shows "--"
        return 0x261, [int(hist['speed']), dist>>8, dist&0xFF, fuel>>8, fuel&0xFF, 0x00, 0x00]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x221 and len(msg.data) >= 7:
            self.inst_params['hide_fuel'] = (msg.data[0] >> 7) & 1
            self.inst_params['hide_dist'] = (msg.data[0] >> 6) & 1
            self.inst_params['com_right'] = (msg.data[0] >> 3) & 1
            self.inst_params['com_left'] = msg.data[0] & 1
            self.inst_params['fuel'] = ((msg.data[1] << 8) | msg.data[2]) / 10.0
            self.inst_params['autonomy'] = (msg.data[3] << 8) | msg.data[4]
            self.inst_params['dist'] = ((msg.data[5] << 8) | msg.data[6]) / 10.0
            self.ids['cur_inst_fuel'].text = f'fuel consumption: {self.inst_params["fuel"]:.1f} l/km'
            self.ids['cur_inst_autonomy'].text = f'autonomy: {self.inst_params["autonomy"]} km'
            self.ids['cur_inst_dist'].text = f'dist to dest: {self.inst_params["dist"]:.1f} km'
            if 'slider_inst_fuel' in self.ids:
                self.ids['slider_inst_fuel'].value = self.inst_params['fuel']
            if 'slider_inst_autonomy' in self.ids:
                self.ids['slider_inst_autonomy'].value = self.inst_params['autonomy']
            if 'slider_inst_dist' in self.ids:
                self.ids['slider_inst_dist'].value = self.inst_params['dist']
        elif msg.arbitration_id == 0x2A1 and len(msg.data) >= 5:
            self.history[0]['speed'] = msg.data[0]
            self.history[0]['dist'] = (msg.data[1] << 8) | msg.data[2]
            self.history[0]['fuel'] = ((msg.data[3] << 8) | msg.data[4]) / 10.0
            self.ids['cur_hist0_speed'].text = f'average speed: {self.history[0]["speed"]} km/h'
            self.ids['cur_hist0_dist'].text = f'distance: {self.history[0]["dist"]} km'
            self.ids['cur_hist0_fuel'].text = f'average consumption: {self.history[0]["fuel"]:.1f} l/km'
            if 'slider_hist0_speed' in self.ids:
                self.ids['slider_hist0_speed'].value = self.history[0]['speed']
            if 'slider_hist0_dist' in self.ids:
                self.ids['slider_hist0_dist'].value = self.history[0]['dist']
            if 'slider_hist0_fuel' in self.ids:
                self.ids['slider_hist0_fuel'].value = self.history[0]['fuel']
        elif msg.arbitration_id == 0x261 and len(msg.data) >= 5:
            self.history[1]['speed'] = msg.data[0]
            self.history[1]['dist'] = (msg.data[1] << 8) | msg.data[2]
            self.history[1]['fuel'] = ((msg.data[3] << 8) | msg.data[4]) / 10.0
            self.ids['cur_hist1_speed'].text = f'average speed: {self.history[1]["speed"]} km/h'
            self.ids['cur_hist1_dist'].text = f'distance: {self.history[1]["dist"]} km'
            self.ids['cur_hist1_fuel'].text = f'average consumption: {self.history[1]["fuel"]:.1f} l/km'
            if 'slider_hist1_speed' in self.ids:
                self.ids['slider_hist1_speed'].value = self.history[1]['speed']
            if 'slider_hist1_dist' in self.ids:
                self.ids['slider_hist1_dist'].value = self.history[1]['dist']
            if 'slider_hist1_fuel' in self.ids:
                self.ids['slider_hist1_fuel'].value = self.history[1]['fuel']
