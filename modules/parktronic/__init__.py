import os

from kivy.app import App
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

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
    _inactive_frame = [0x24, 0x00, 0x3F, 0xFC, 0xFC, 0xFC, 0x00]

    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Parktronic'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/parktronic.kv')
        Builder.apply(self)

        runner.register(100, self.can_parktronic)

        self.parktronic_state = {
            'display': 0,
            'front_active': 0,
            'rear_active': 0,
            'rear_left': 7,
            'rear_center': 7,
            'rear_right': 7,
            'front_left': 7,
            'front_center': 7,
            'front_right': 7,
        }
        self.reverse = 0
        if not hasattr(self.runner, 'reverse'):
            self.runner.reverse = 0

    def _sync_reverse_toggle(self):
        if 'park_reverse' in self.ids:
            desired_state = 'down' if self.reverse else 'normal'
            if self.ids['park_reverse'].state != desired_state:
                self.ids['park_reverse'].state = desired_state
        if 'reverse_state' in self.ids:
            self.ids['reverse_state'].text = f'Reverse: {"on" if self.reverse else "off"}'

    def _push_reverse_to_bus_state(self):
        self.runner.reverse = int(self.reverse)

    def on_reverse_toggle(self, state):
        self.reverse = 1 if state == 'down' else 0
        self._sync_reverse_toggle()
        self._push_reverse_to_bus_state()
        if self.reverse:
            if not self.parktronic_state['display']:
                self._update_toggle('display', 1)
            if not self.parktronic_state['rear_active']:
                self._update_toggle('rear_active', 1)
        else:
            self.clear_sensors()

    def _zone_has_detection(self, sensor_names):
        return any(self.parktronic_state[name] < 7 for name in sensor_names)

    def _update_toggle(self, name, enabled):
        value = 1 if int(enabled) else 0
        self.parktronic_state[name] = value
        widget_id = f'park_{name}'
        if widget_id in self.ids:
            desired_state = 'down' if value else 'normal'
            if self.ids[widget_id].state != desired_state:
                self.ids[widget_id].state = desired_state

    def on_toggle(self, name, state):
        self._update_toggle(name, state == 'down')

    def _update_sensor(self, name, value):
        sensor_value = max(0, min(7, int(value)))
        self.parktronic_state[name] = sensor_value
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

    def can_parktronic(self):
        rear_active = self.parktronic_state['rear_active']
        front_active = self.parktronic_state['front_active']
        display_active = self.parktronic_state['display']

        if not display_active and not rear_active and not front_active:
            return 0x0E1, self._inactive_frame

        sensor_a = ((self.parktronic_state['rear_left'] & 0x07) << 5) | ((self.parktronic_state['rear_center'] & 0x07) << 2)
        sensor_b = ((self.parktronic_state['rear_right'] & 0x07) << 5) | ((self.parktronic_state['front_left'] & 0x07) << 2)
        sensor_c = ((self.parktronic_state['front_center'] & 0x07) << 5) | ((self.parktronic_state['front_right'] & 0x07) << 2) | 0x02
        zone_flags = (0x40 if rear_active else 0x00) | (0x10 if front_active else 0x00)
        # _inactive_frame = [0x24, 0x00, 0x3F, 0xFC, 0xFC, 0xFC, 0x00]
        return 0x0E1, [0x24, zone_flags, 0x3F, sensor_a, sensor_b, sensor_c, 0x00]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x0F6 and len(msg.data) >= 8:
            self.reverse = (msg.data[7] >> 7) & 0x01
            self.runner.reverse = int(self.reverse)
            self._sync_reverse_toggle()
        elif msg.arbitration_id == 0x0E1 and len(msg.data) >= 6:
            self._update_toggle('rear_active', (msg.data[1] >> 6) & 0x01)
            self._update_toggle('front_active', (msg.data[1] >> 4) & 0x01)
            self._update_toggle('display', 1 if (msg.data[5] & 0x02) else 0)
            self._update_sensor('rear_left', (msg.data[3] >> 5) & 0x07)
            self._update_sensor('rear_center', (msg.data[3] >> 2) & 0x07)
            self._update_sensor('rear_right', (msg.data[4] >> 5) & 0x07)
            self._update_sensor('front_left', (msg.data[4] >> 2) & 0x07)
            self._update_sensor('front_center', (msg.data[5] >> 5) & 0x07)
            self._update_sensor('front_right', (msg.data[5] >> 2) & 0x07)