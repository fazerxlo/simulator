"""Unit tests for Parktronic module UI helpers (6-zone 3x2 layout)."""
import types
import pytest

from car_state import VirtualCar
from conftest import DummyWidget
from modules.parktronic import Parktronic as ParktronicModule


class TestParktronicUiHelpers:
    def _make_parktronic_widget(self):
        widget = ParktronicModule.__new__(ParktronicModule)
        widget.runner = types.SimpleNamespace(car=VirtualCar())
        widget._sensor_labels = ParktronicModule._sensor_labels
        widget.ids = {
            'reverse_state': DummyWidget(text='Reverse: off'),
            'park_reverse': DummyWidget(state='normal'),
            'park_display': DummyWidget(state='normal'),
            'park_front_active': DummyWidget(state='normal'),
            'park_rear_active': DummyWidget(state='normal'),
            'cur_park_front_left': DummyWidget(text='Front left: 7'),
            'slider_park_front_left': DummyWidget(value=7),
            'cur_park_front_center': DummyWidget(text='Front center: 7'),
            'slider_park_front_center': DummyWidget(value=7),
            'cur_park_front_right': DummyWidget(text='Front right: 7'),
            'slider_park_front_right': DummyWidget(value=7),
            'cur_park_rear_left': DummyWidget(text='Rear left: 7'),
            'slider_park_rear_left': DummyWidget(value=7),
            'cur_park_rear_center': DummyWidget(text='Rear center: 7'),
            'slider_park_rear_center': DummyWidget(value=7),
            'cur_park_rear_right': DummyWidget(text='Rear right: 7'),
            'slider_park_rear_right': DummyWidget(value=7),
        }
        return widget

    def test_on_sensor_updates_car_state_and_slider(self):
        widget = self._make_parktronic_widget()
        widget.on_sensor('front_left', 3)
        assert widget.runner.car.parktronic.front_left == 3
        assert widget.ids['slider_park_front_left'].value == 3
        assert widget.ids['cur_park_front_left'].text == 'Front left: 3'

    def test_reverse_toggle_engages_parktronic(self):
        widget = self._make_parktronic_widget()
        widget.on_reverse_toggle('down')
        assert widget.runner.car.bsi.reverse == 1
        assert widget.runner.car.parktronic.display == 1
        assert widget.runner.car.parktronic.rear_active == 1
        assert widget.ids['park_reverse'].state == 'down'
        assert widget.ids['park_display'].state == 'down'
        assert widget.ids['park_rear_active'].state == 'down'
        assert widget.ids['reverse_state'].text == 'Reverse: on'

    def test_reverse_toggle_off_clears_sensors(self):
        widget = self._make_parktronic_widget()
        widget.on_reverse_toggle('down')
        widget.on_sensor('rear_left', 3)
        assert widget.runner.car.parktronic.rear_left == 3

        widget.on_reverse_toggle('normal')
        assert widget.runner.car.bsi.reverse == 0
        assert widget.runner.car.parktronic.display == 0
        assert widget.runner.car.parktronic.rear_active == 0
        assert widget.runner.car.parktronic.rear_left == 7
        assert widget.ids['slider_park_rear_left'].value == 7
        assert widget.ids['reverse_state'].text == 'Reverse: off'

    def test_clear_sensors_resets_all_zones(self):
        widget = self._make_parktronic_widget()
        widget.on_sensor('front_left', 3)
        widget.on_sensor('rear_right', 2)
        widget.on_toggle('front_active', 'down')
        widget.clear_sensors()
        assert widget.runner.car.parktronic.front_left == 7
        assert widget.runner.car.parktronic.rear_right == 7
        assert widget.runner.car.parktronic.front_active == 0
        assert widget.ids['slider_park_front_left'].value == 7
        assert widget.ids['slider_park_rear_right'].value == 7

    def test_on_can_message_syncs_0e1(self):
        widget = self._make_parktronic_widget()
        car = widget.runner.car
        from generated.parktronic_messages import Msg0E1
        # [0x24, zone=0x50 (rear+front), 0x3F, RL=3, RC=2 (0x68), RR=1, FL=4 (0x30), FC=5, FR=6, 0x02 (display)]
        # Msg0E1 decode takes at least 6 bytes
        data = [0x24, 0x50, 0x3F, (3 << 5) | (2 << 2), (1 << 5) | (4 << 2), (5 << 5) | (6 << 2) | 0x02, 0x00]
        Msg0E1().decode(car, data)

        msg = types.SimpleNamespace(arbitration_id=0x0E1, data=data)
        widget.on_can_message(msg)

        assert widget.ids['park_display'].state == 'down'
        assert widget.ids['park_rear_active'].state == 'down'
        assert widget.ids['park_front_active'].state == 'down'
        assert widget.ids['slider_park_rear_left'].value == 3
        assert widget.ids['slider_park_rear_center'].value == 2
        assert widget.ids['slider_park_rear_right'].value == 1
        assert widget.ids['slider_park_front_left'].value == 4
        assert widget.ids['slider_park_front_center'].value == 5
        assert widget.ids['slider_park_front_right'].value == 6
