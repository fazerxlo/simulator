"""Unit tests for the Tyres module UI and RT4 TPMS integration."""
import types
import pytest

from car_state import VirtualCar, Tyres as CarTyres
from conftest import DummyWidget
from modules.tyres import (
    Tyres as TyresModule,
    TIRE_OK, TIRE_LOW, TIRE_FLAT, TIRE_NO_DATA, TIRE_BATTERY_LOW,
    MSG_PRESSURE_LOW, MSG_PRESSURE_NOT_MONITORED, MSG_MULTIPLE_FLAT,
    MSG_DIAGNOSTIC_OK, MSG_HIGH_SPEED_CHECK, MSG_UNDERINFLATED,
)
from generated.tyres_messages import Msg1E1, Msg3A1


class TestTyresModule:
    def _make_tyres_widget(self):
        sent_messages = []

        class DummyRunner:
            def __init__(self):
                self.car = VirtualCar()
                self._can_message_objects = {}
            def register_message(self, msg_obj):
                self._can_message_objects[msg_obj.can_id] = msg_obj
            def send_message(self, can_id, data):
                sent_messages.append((can_id, list(data)))

        runner = DummyRunner()
        widget = TyresModule.__new__(TyresModule)
        widget.runner = runner
        widget.ids = {
            'cur_mess': DummyWidget(text='0'),
            'slider_mess': DummyWidget(value=0),
            'send': DummyWidget(text='send'),
            'status_msg': DummyWidget(text='-'),
            'state_fl': DummyWidget(text='OK'),
            'spinner_fl': DummyWidget(text='OK'),
            'cur_pressure_fl': DummyWidget(text='2.40 bar'),
            'slider_pressure_fl': DummyWidget(value=2.4),
            'state_fr': DummyWidget(text='OK'),
            'spinner_fr': DummyWidget(text='OK'),
            'cur_pressure_fr': DummyWidget(text='2.40 bar'),
            'slider_pressure_fr': DummyWidget(value=2.4),
            'state_rl': DummyWidget(text='OK'),
            'spinner_rl': DummyWidget(text='OK'),
            'cur_pressure_rl': DummyWidget(text='2.20 bar'),
            'slider_pressure_rl': DummyWidget(value=2.2),
            'state_rr': DummyWidget(text='OK'),
            'spinner_rr': DummyWidget(text='OK'),
            'cur_pressure_rr': DummyWidget(text='2.20 bar'),
            'slider_pressure_rr': DummyWidget(value=2.2),
            'state_spare': DummyWidget(text='OK'),
            'spinner_spare': DummyWidget(text='OK'),
            'btn_calib': DummyWidget(state='down'),
            'btn_fault': DummyWidget(state='normal'),
        }
        widget.sent_messages = sent_messages
        widget.msg_flag = 0xFF
        widget.msg_id = 0x00
        widget.mess = 0x00

        # Run initialization logic
        runner.register_message(Msg1E1())
        runner.register_message(Msg3A1())
        widget._update_labels()
        widget._update_pressure_displays()
        widget._update_system_buttons()

        return widget

    def test_initial_state_and_message_registration(self):
        widget = self._make_tyres_widget()
        assert 0x1E1 in widget.runner._can_message_objects
        assert 0x3A1 in widget.runner._can_message_objects
        assert widget.runner.car.tyres.fl == TIRE_OK
        assert widget.runner.car.tyres.spare == TIRE_OK
        assert widget.runner.car.tyres.pressure_fl == 2.4
        assert widget.runner.car.tyres.tpms_system_state == 0x20

    def test_state_change_updates_car_and_ui(self):
        widget = self._make_tyres_widget()
        widget.on_state_change('fl', 'LOW')
        assert widget.runner.car.tyres.fl == TIRE_LOW
        assert widget.ids['state_fl'].text == 'LOW'
        assert widget.ids['state_fl'].color == (1, 0.8, 0, 1)
        assert widget.ids['spinner_fl'].text == 'LOW'

        widget.on_state_change('rr', 'FLAT')
        assert widget.runner.car.tyres.rr == TIRE_FLAT
        assert widget.ids['state_rr'].text == 'FLAT'
        assert widget.ids['state_rr'].color == (1, 0, 0, 1)

        widget.on_state_change('spare', 'BATTERY LOW')
        assert widget.runner.car.tyres.spare == TIRE_BATTERY_LOW
        assert widget.ids['state_spare'].text == 'BATTERY LOW'
        assert widget.ids['state_spare'].color == (1, 0.5, 0, 1)

    def test_pressure_change_updates_car_and_ui(self):
        widget = self._make_tyres_widget()
        widget.on_pressure_change('fl', 2.15)
        assert widget.runner.car.tyres.pressure_fl == 2.15
        assert widget.ids['cur_pressure_fl'].text == '2.15 bar'
        assert widget.ids['slider_pressure_fl'].value == 2.15

        widget.on_pressure_change('rr', 1.80)
        assert widget.runner.car.tyres.pressure_rr == 1.80
        assert widget.ids['cur_pressure_rr'].text == '1.80 bar'

    def test_system_state_toggles(self):
        widget = self._make_tyres_widget()
        assert widget.runner.car.tyres.tpms_system_state == 0x20

        widget.on_system_toggle('fault', 'down')
        assert widget.runner.car.tyres.tpms_system_state == 0xA0

        widget.on_system_toggle('calibration', 'normal')
        assert widget.runner.car.tyres.tpms_system_state == 0x80

        widget.on_system_toggle('fault', 'normal')
        assert widget.runner.car.tyres.tpms_system_state == 0x00

    def test_dashboard_alert_calculation(self):
        widget = self._make_tyres_widget()
        widget.on_state_change('fl', 'OK')
        assert widget.runner.car.tyres.alert_0x168_b1 == 0x00

        widget.on_state_change('fl', 'LOW')
        # Byte 1 bit 7 = 1 (0x80)
        assert widget.runner.car.tyres.alert_0x168_b1 == 0x80

        widget.on_state_change('fr', 'FLAT')
        # Byte 1 bit 7 = 1, bit 6 = 1 (0xC0)
        assert widget.runner.car.tyres.alert_0x168_b1 == 0xC0

    def test_build_payload_0x1a1_wheel_mask(self):
        widget = self._make_tyres_widget()
        widget.runner.car.tyres.fl = TIRE_LOW
        widget.runner.car.tyres.rr = TIRE_FLAT

        payload = widget._build_payload(MSG_PRESSURE_LOW, 'active')
        assert payload[0] == 0x80
        assert payload[1] == MSG_PRESSURE_LOW
        # FL bit 4 (0x10) | RR bit 2 (0x04) = 0x14
        assert payload[3] == 0x14
        assert payload[4] == 0x00

    def test_rear_left_flat_sets_correct_puncture_popup_and_rl_bitmask(self):
        widget = self._make_tyres_widget()
        car = widget.runner.car
        widget.on_state_change('rl', 'FLAT')

        assert car.tyres.rl == TIRE_FLAT
        assert car.tyres.pressure_rl == 0.0
        assert car.tyres.popup_msg_id == MSG_MULTIPLE_FLAT  # 0x0D (Puncture/Flat)
        assert car.dashboard.stop == 1
        assert car.dashboard.warn == 1
        assert car.dashboard.tyre == 1

        sent_1a1 = [d for can_id, d in widget.sent_messages if can_id == 0x1A1]
        assert len(sent_1a1) > 0
        last = sent_1a1[-1]
        assert last[0] == 0x80
        assert last[1] == MSG_MULTIPLE_FLAT  # 0x0D
        assert last[3] == 0x02  # RL bitmask (Bit 1)
        assert last[4] == 0x00  # Byte 4 must not contain dummy 0x40

    def test_on_can_message_0x1e1_syncs_ui(self):
        widget = self._make_tyres_widget()
        car = widget.runner.car
        # Encode: FL=LOW (1<<3=0x08), FR=FLAT (2<<3=0x10), RR=NO_DATA (3<<3=0x18), RL=OK (0), Spare=BATTERY_LOW (4<<3=0x20), Sys=0xA0
        data = [0x08, 0x10, 0x18, 0x00, 0x20, 0xA0, 0x00, 0x00]
        msg = types.SimpleNamespace(arbitration_id=0x1E1, data=data)
        widget.on_can_message(msg)

        assert car.tyres.fl == TIRE_LOW
        assert car.tyres.fr == TIRE_FLAT
        assert car.tyres.rr == TIRE_NO_DATA
        assert car.tyres.rl == TIRE_OK
        assert car.tyres.spare == TIRE_BATTERY_LOW
        assert car.tyres.tpms_system_state == 0xA0

        assert widget.ids['state_fl'].text == 'LOW'
        assert widget.ids['state_fr'].text == 'FLAT'
        assert widget.ids['state_rr'].text == 'NO DATA'
        assert widget.ids['state_rl'].text == 'OK'
        assert widget.ids['state_spare'].text == 'BATTERY LOW'
        assert widget.ids['btn_fault'].state == 'down'
        assert widget.ids['btn_calib'].state == 'down'

    def test_popup_trigger_and_cluster_lamps(self):
        widget = self._make_tyres_widget()
        car = widget.runner.car
        widget.on_state_change('fl', 'LOW')

        assert car.tyres.display_active is True
        assert car.tyres.popup_msg_id == MSG_PRESSURE_LOW
        assert car.tyres.popup_flag == 0x80
        assert car.dashboard.tyre == 1
        assert car.dashboard.warn == 1
        assert car.dashboard.stop == 0

        # Check that 0x1A1 frame was sent
        sent_1a1 = [d for can_id, d in widget.sent_messages if can_id == 0x1A1]
        assert len(sent_1a1) > 0
        assert sent_1a1[-1][0] == 0x80
        assert sent_1a1[-1][1] == MSG_PRESSURE_LOW
        assert sent_1a1[-1][3] == 0x10  # FL bitmask is bit 4 (0x10)

        # When tyre becomes FLAT, STOP indicator turns on and popup is Puncture
        widget.on_state_change('fr', 'FLAT')
        assert car.dashboard.stop == 1
        assert car.dashboard.tyre == 1
        assert car.tyres.popup_msg_id == MSG_MULTIPLE_FLAT

    def test_reset_all_nominal(self):
        widget = self._make_tyres_widget()
        car = widget.runner.car

        widget.on_state_change('fl', 'FLAT')
        assert car.tyres.fl == TIRE_FLAT
        assert car.tyres.pressure_fl == 0.0
        assert car.dashboard.stop == 1
        assert car.dashboard.tyre == 1

        widget.reset_all_nominal()
        assert car.tyres.fl == TIRE_OK
        assert car.tyres.fr == TIRE_OK
        assert car.tyres.rl == TIRE_OK
        assert car.tyres.rr == TIRE_OK
        assert car.tyres.pressure_fl == 2.4
        assert car.dashboard.tyre == 0
        assert car.dashboard.warn == 0

    def test_on_can_message_0x361_syncs_states_and_pressures(self):
        widget = self._make_tyres_widget()
        car = widget.runner.car
        # FL: OK (0) @ 2.4 bar (24=0x18) -> 0x00, 0x18
        # FR: LOW (1) @ 1.4 bar (14=0x0E) -> 0x40, 0x0E
        # RR: FLAT (2) @ 0.0 bar (0) -> 0x80, 0x00
        # RL: NO_DATA (3) @ 0.0 bar -> 0xFF, 0xFF
        data = [0x00, 0x18, 0x40, 0x0E, 0x80, 0x00, 0xFF, 0xFF]
        msg = types.SimpleNamespace(arbitration_id=0x361, data=data)
        widget.on_can_message(msg)

        assert car.tyres.fl == TIRE_OK
        assert car.tyres.pressure_fl == 2.4
        assert car.tyres.fr == TIRE_LOW
        assert car.tyres.pressure_fr == 1.4
        assert car.tyres.rr == TIRE_FLAT
        assert car.tyres.pressure_rr == 0.0
        assert car.tyres.rl == TIRE_NO_DATA

        assert widget.ids['state_fl'].text == 'OK'
        assert widget.ids['state_fr'].text == 'LOW'
        assert widget.ids['state_rr'].text == 'FLAT'
        assert widget.ids['state_rl'].text == 'NO DATA'

    def test_each_wheel_bitmask_individual(self):
        widget = self._make_tyres_widget()
        expected_masks = {
            'fl': 0x10,     # Bit 4
            'fr': 0x08,     # Bit 3
            'rr': 0x04,     # Bit 2
            'rl': 0x02,     # Bit 1
            'spare': 0x01,  # Bit 0
        }
        for wheel, expected_mask in expected_masks.items():
            widget.reset_all_nominal()
            widget.on_state_change(wheel, 'LOW')
            payload = widget._build_payload(MSG_PRESSURE_LOW, 'active')
            assert payload[3] == expected_mask, f"Wheel {wheel} expected bitmask 0x{expected_mask:02X}, got 0x{payload[3]:02X}"




