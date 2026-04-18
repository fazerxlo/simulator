import os

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import Msg0E1

_modname = 'Parktronic'
_modversion = '0.0.1'


class Parktronic(TabbedPanelItem):
    _sensor_labels = {
        'rear_left': 'Rear left',
        'rear_center': 'Rear center',
        'rear_right': 'Rear right',
        'front_left': 'Front left',
        'front_center': 'Front center',
        'front_right': 'Front right',
    }

    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Parktronic'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/parktronic.kv')
        Builder.apply(self)

        runner.register_message(Msg0E1())

        # Initialise parktronic state on the shared VirtualCar.
        park = runner.car.parktronic
        park.display = 0
        park.front_active = 0
        park.rear_active = 0
        park.rear_left = 7
        park.rear_center = 7
        park.rear_right = 7
        park.front_left = 7
        park.front_center = 7
        park.front_right = 7

    @property
    def _park(self):
        """Convenience accessor for the shared parktronic car state."""
        return self.runner.car.parktronic

    def _sync_reverse_toggle(self):
        reverse = self.runner.car.bsi.reverse
        if 'park_reverse' in self.ids:
            desired_state = 'down' if reverse else 'normal'
            if self.ids['park_reverse'].state != desired_state:
                self.ids['park_reverse'].state = desired_state
        if 'reverse_state' in self.ids:
            self.ids['reverse_state'].text = f'Reverse: {"on" if reverse else "off"}'

    def on_reverse_toggle(self, state):
        self.runner.car.bsi.reverse = 1 if state == 'down' else 0
        self._sync_reverse_toggle()
        if self.runner.car.bsi.reverse:
            if not self._park.display:
                self._update_toggle('display', 1)
            if not self._park.rear_active:
                self._update_toggle('rear_active', 1)
        else:
            self.clear_sensors()

    def _zone_has_detection(self, sensor_names):
        return any(getattr(self._park, name) < 7 for name in sensor_names)

    def _update_toggle(self, name, enabled):
        value = 1 if int(enabled) else 0
        setattr(self._park, name, value)
        widget_id = f'park_{name}'
        if widget_id in self.ids:
            desired_state = 'down' if value else 'normal'
            if self.ids[widget_id].state != desired_state:
                self.ids[widget_id].state = desired_state

    def on_toggle(self, name, state):
        self._update_toggle(name, state == 'down')

    def _update_sensor(self, name, value):
        sensor_value = max(0, min(7, int(value)))
        setattr(self._park, name, sensor_value)
        label_id = f'cur_park_{name}'
        slider_id = f'slider_park_{name}'
        if label_id in self.ids:
            self.ids[label_id].text = f'{self._sensor_labels[name]}: {sensor_value}'
        if slider_id in self.ids and self.ids[slider_id].value != sensor_value:
            self.ids[slider_id].value = sensor_value

    def on_sensor(self, name, value):
        self._update_sensor(name, value)

    def clear_sensors(self):
        self._update_toggle('display', 0)
        self._update_toggle('front_active', 0)
        self._update_toggle('rear_active', 0)
        for sensor_name in self._sensor_labels:
            self._update_sensor(sensor_name, 7)

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x0F6 and len(msg.data) >= 8:
            # Msg0F6.decode() has already updated car.bsi.reverse; just sync UI.
            self._sync_reverse_toggle()
        elif msg.arbitration_id == 0x0E1 and len(msg.data) >= 6:
            # Msg0E1.decode() has already updated car.parktronic.*; just sync UI.
            self._update_toggle('rear_active', self._park.rear_active)
            self._update_toggle('front_active', self._park.front_active)
            self._update_toggle('display', self._park.display)
            self._update_sensor('rear_left', self._park.rear_left)
            self._update_sensor('rear_center', self._park.rear_center)
            self._update_sensor('rear_right', self._park.rear_right)
            self._update_sensor('front_left', self._park.front_left)
            self._update_sensor('front_center', self._park.front_center)
            self._update_sensor('front_right', self._park.front_right)
