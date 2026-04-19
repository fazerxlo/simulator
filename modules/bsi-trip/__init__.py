import datetime
import logging
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from generated.trip_messages import Msg221, Msg2A1, Msg261

_modname = 'BSI_trip'
_modversion = '0.0.1'

logger = logging.getLogger(__name__)

class BSI_trip(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Trip'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/bsi.kv')
        Builder.apply(self)

        # Register per-CAN-ID message objects.
        logger.debug('registering BSI trip module')
        runner.register_message(Msg221())
        runner.register_message(Msg2A1())
        runner.register_message(Msg261())

        # Initialise trip state on the shared VirtualCar.
        trip = runner.car.trip
        trip.hide_fuel = 0
        trip.hide_dist = 0
        trip.com_left = 0
        trip.com_right = 0
        trip.fuel = 7.1
        trip.autonomy = 740
        trip.dist = 120
        trip.hist[0] = {'speed': 37, 'dist': 569, 'fuel': 7.3}
        trip.hist[1] = {'speed': 35, 'dist': 921, 'fuel': 7.9}

        self._apply_initial_values()

    @property
    def _trip(self):
        """Convenience accessor for the shared trip car state."""
        return self.runner.car.trip

    def _apply_initial_values(self):
        # Seed UI with realistic trip values so startup state is not all zeros.
        t = self._trip
        self.on_inst_param('fuel', t.fuel)
        self.on_inst_param('autonomy', t.autonomy)
        self.on_inst_param('dist', t.dist)
        for i in range(2):
            for param in ('speed', 'dist', 'fuel'):
                self.on_hist_param(i, param, t.hist[i][param])

    def on_inst_button(self, name, value):
        setattr(self._trip, name, 1 if value == 'down' else 0)

    def on_inst_param(self, param, value):
        labels = {
            'fuel': 'fuel consumption: {:2.1f} l/km',
            'autonomy': 'autonomy: {} km',
            'dist': 'dist to dest: {} km'
        }
        setattr(self._trip, param, value)
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
        self._trip.hist[hist][param] = value
        self.ids[f'cur_hist{hist}_{param}'].text = labels[param].format(value)
        slider_id = f'slider_hist{hist}_{param}'
        if slider_id in self.ids and self.ids[slider_id].value != value:
            self.ids[slider_id].value = value

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x221 and len(msg.data) >= 7:
            # Msg221.decode() has already updated car.trip; sync UI.
            t = self._trip
            self.ids['cur_inst_fuel'].text = f'fuel consumption: {t.fuel:.1f} l/km'
            self.ids['cur_inst_autonomy'].text = f'autonomy: {t.autonomy} km'
            self.ids['cur_inst_dist'].text = f'dist to dest: {t.dist:.1f} km'
            if 'slider_inst_fuel' in self.ids:
                self.ids['slider_inst_fuel'].value = t.fuel
            if 'slider_inst_autonomy' in self.ids:
                self.ids['slider_inst_autonomy'].value = t.autonomy
            if 'slider_inst_dist' in self.ids:
                self.ids['slider_inst_dist'].value = t.dist
        elif msg.arbitration_id == 0x2A1 and len(msg.data) >= 5:
            h = self._trip.hist[0]
            self.ids['cur_hist0_speed'].text = f'average speed: {h["speed"]} km/h'
            self.ids['cur_hist0_dist'].text = f'distance: {h["dist"]} km'
            self.ids['cur_hist0_fuel'].text = f'average consumption: {h["fuel"]:.1f} l/km'
            if 'slider_hist0_speed' in self.ids:
                self.ids['slider_hist0_speed'].value = h['speed']
            if 'slider_hist0_dist' in self.ids:
                self.ids['slider_hist0_dist'].value = h['dist']
            if 'slider_hist0_fuel' in self.ids:
                self.ids['slider_hist0_fuel'].value = h['fuel']
        elif msg.arbitration_id == 0x261 and len(msg.data) >= 5:
            h = self._trip.hist[1]
            self.ids['cur_hist1_speed'].text = f'average speed: {h["speed"]} km/h'
            self.ids['cur_hist1_dist'].text = f'distance: {h["dist"]} km'
            self.ids['cur_hist1_fuel'].text = f'average consumption: {h["fuel"]:.1f} l/km'
            if 'slider_hist1_speed' in self.ids:
                self.ids['slider_hist1_speed'].value = h['speed']
            if 'slider_hist1_dist' in self.ids:
                self.ids['slider_hist1_dist'].value = h['dist']
            if 'slider_hist1_fuel' in self.ids:
                self.ids['slider_hist1_fuel'].value = h['fuel']
