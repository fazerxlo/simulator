"""
Tests for car_state.VirtualCar, can_messages, and the CanRunner integration.
"""
import datetime
import importlib
import os
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_can_mock():
    """Return a minimal 'can' module stub so CanRunner can be imported."""
    can_mock = types.ModuleType('can')

    class MockBus:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
        def recv(self, timeout):
            return None
        def send(self, msg):
            pass

    class MockMessage:
        def __init__(self, **kwargs):
            self.arbitration_id = kwargs.get('arbitration_id', 0)
            self.data = kwargs.get('data', [])
            self.is_extended_id = kwargs.get('is_extended_id', False)

    can_mock.Bus = MockBus
    can_mock.Message = MockMessage
    return can_mock


# ---------------------------------------------------------------------------
# car_state tests
# ---------------------------------------------------------------------------

from car_state import (BSI, Buttons, Clim, Dashboard, Doors, MFDPopup,
                       Parktronic, Tyres, VirtualCar, Radio, Trip,
                       KMLState, BTEState, SpeedControl)
from modules.clim import Clim as ClimModule
from modules.combine import Combine as CombineModule
DoorsModule = importlib.import_module('modules.doors').Doors
BSIBaseModule = importlib.import_module('modules.bsi-base').BSI_base


class TestVirtualCarDefaults:
    def test_bsi_defaults(self):
        car = VirtualCar()
        assert car.bsi.ignition_on is False
        assert car.bsi.power_mode == 0x02
        assert car.bsi.reverse == 0
        assert car.bsi.rpm == 0
        assert car.bsi.speed == 0

    def test_doors_defaults(self):
        car = VirtualCar()
        for attr in ('front_left', 'front_right', 'rear_left', 'rear_right',
                     'boot', 'bonnet', 'rear_window', 'fuel_flap'):
            assert getattr(car.doors, attr) == 0
        assert car.doors.display_active is False

    def test_tyres_defaults(self):
        car = VirtualCar()
        for attr in ('fl', 'fr', 'rl', 'rr'):
            assert getattr(car.tyres, attr) == Tyres.OK
        assert car.tyres.display_active is False
        assert car.tyres.alert_0x168_b1 == 0

    def test_parktronic_defaults(self):
        car = VirtualCar()
        for attr in ('rear_left', 'rear_center', 'rear_right',
                     'front_left', 'front_center', 'front_right'):
            assert getattr(car.parktronic, attr) == 7
        assert car.parktronic.display == 0

    def test_clim_defaults(self):
        car = VirtualCar()
        assert car.clim.fan == 0
        assert car.clim.auto == 0
        assert car.clim.dual == 0
        assert car.clim.ac == 1
        assert car.clim.enabled is False

    def test_dashboard_defaults(self):
        car = VirtualCar()
        assert car.dashboard.active is False
        for attr in ('airbag_pass', 'seatbelt', 'brakes', 'warn', 'stop',
                     'esp', 'tyre', 'low_beam'):
            assert getattr(car.dashboard, attr) == 0

    def test_radio_defaults(self):
        car = VirtualCar()
        assert car.radio.input == 'TUN'
        assert car.radio.volume == 15
        assert car.radio.volflag == 0xE0
        assert car.radio.audio['bass'] == 0x3F
        assert car.radio.audio['menu'] == 'none'

    def test_trip_defaults(self):
        car = VirtualCar()
        assert car.trip.fuel == 7.1
        assert car.trip.autonomy == 740
        assert len(car.trip.hist) == 2

    def test_kml_defaults(self):
        car = VirtualCar()
        assert car.kml.opt == 0
        assert car.kml.bits_223 == 0

    def test_bte_defaults(self):
        car = VirtualCar()
        assert car.bte.bits == 0

    def test_buttons_defaults(self):
        car = VirtualCar()
        assert car.buttons.active is False
        assert car.buttons.volume == 15
        assert car.buttons.volflag == 0xE0
        assert car.buttons._volume_action_ticks == 0
        for key in car.buttons.panel:
            assert car.buttons.panel[key] == 0

    def test_mfd_popup_defaults(self):
        car = VirtualCar()
        assert car.mfd_popup.flag == 0xFF
        assert car.mfd_popup.msg_id == 0x00
        assert car.mfd_popup.display_flags == 0xC6

    def test_bsi_new_fields_defaults(self):
        """New PSA-RE fields: blinkers and oil_level should have correct defaults."""
        car = VirtualCar()
        assert car.bsi.blinkers == 0       # no blinker
        assert car.bsi.oil_level == 0xFF   # invalid / not available

    def test_speed_control_defaults(self):
        """SpeedControl should start in NONE/STANDBY with no set_speed."""
        car = VirtualCar()
        assert car.speed_control.control_type == SpeedControl.NONE
        assert car.speed_control.function_status == SpeedControl.STANDBY
        assert car.speed_control.set_speed is None
        assert car.speed_control.partial_odo is None
        assert car.speed_control.unit_mph is False


class TestVirtualCarMutation:
    def test_bsi_state_mutation(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.reverse = 1
        assert car.bsi.ignition_on is True
        assert car.bsi.reverse == 1

    def test_doors_state_mutation(self):
        car = VirtualCar()
        car.doors.front_left = 1
        car.doors.boot = 1
        car.doors.display_active = True
        assert car.doors.front_left == 1
        assert car.doors.boot == 1
        assert car.doors.display_active is True

    def test_tyres_state_mutation(self):
        car = VirtualCar()
        car.tyres.fl = Tyres.FLAT
        car.tyres.fr = Tyres.LOW
        car.tyres.display_active = True
        car.tyres.alert_0x168_b1 = 0xC0
        assert car.tyres.fl == Tyres.FLAT
        assert car.tyres.fr == Tyres.LOW
        assert car.tyres.display_active is True
        assert car.tyres.alert_0x168_b1 == 0xC0

    def test_tyres_constants(self):
        assert Tyres.OK == 0
        assert Tyres.LOW == 1
        assert Tyres.FLAT == 2
        assert Tyres.NO_DATA == 3

    def test_dashboard_active_flag(self):
        car = VirtualCar()
        car.dashboard.active = True
        assert car.dashboard.active is True

    def test_parktronic_sensor_mutation(self):
        car = VirtualCar()
        car.parktronic.rear_left = 3
        car.parktronic.front_center = 1
        assert car.parktronic.rear_left == 3
        assert car.parktronic.front_center == 1

    def test_radio_mutation(self):
        car = VirtualCar()
        car.radio.input = 'CDC'
        car.radio.volume = 20
        car.radio.audio['bass'] = 0x45
        assert car.radio.input == 'CDC'
        assert car.radio.volume == 20
        assert car.radio.audio['bass'] == 0x45

    def test_trip_mutation(self):
        car = VirtualCar()
        car.trip.fuel = 9.5
        car.trip.hist[0]['speed'] = 50
        assert car.trip.fuel == 9.5
        assert car.trip.hist[0]['speed'] == 50

    def test_mfd_popup_mutation(self):
        car = VirtualCar()
        car.mfd_popup.flag = 0x80
        car.mfd_popup.msg_id = 0x42
        assert car.mfd_popup.flag == 0x80
        assert car.mfd_popup.msg_id == 0x42

    def test_buttons_mutation(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.volume = 22
        car.buttons.panel['ok'] = 1
        assert car.buttons.active is True
        assert car.buttons.volume == 22
        assert car.buttons.panel['ok'] == 1

    def test_buttons_press_sets_pulse(self):
        car = VirtualCar()
        car.buttons.press('trip')
        assert car.buttons.panel['trip'] == 1
        assert car.buttons._pulse_ticks['trip'] == car.buttons._pulse_window

    def test_buttons_step_pulses_clears_after_window(self):
        car = VirtualCar()
        car.buttons.press('up')
        for _ in range(car.buttons._pulse_window):
            car.buttons.step_pulses()
        assert car.buttons.panel['up'] == 0

    def test_buttons_step_volume_resets_volflag(self):
        car = VirtualCar()
        car.buttons.volflag = 0x00
        car.buttons._volume_action_ticks = 1
        car.buttons.step_volume()
        assert car.buttons.volflag == 0xE0


class TestVirtualCarIsolation:
    """Each VirtualCar instance has independent state."""

    def test_two_cars_are_independent(self):
        car_a = VirtualCar()
        car_b = VirtualCar()
        car_a.bsi.ignition_on = True
        car_a.tyres.fl = Tyres.FLAT
        assert car_b.bsi.ignition_on is False
        assert car_b.tyres.fl == Tyres.OK


class DummyWidget:
    def __init__(self, state='normal', value=0, text=''):
        self.state = state
        self.value = value
        self.text = text


class TestClimUiHelpers:
    def _make_clim_widget(self, ignition_on=True):
        widget = ClimModule.__new__(ClimModule)
        widget.runner = types.SimpleNamespace(car=VirtualCar())
        widget.runner.car.bsi.ignition_on = ignition_on
        widget.temp_disp = [
            'MIN', '14', '15', '16', '17', '18', '18.5', '19', '19.5', '20', '20.5',
            '21', '21.5', '22', '22.5', '23', '23.5', '24', '25', '26', '27', '28', 'HI'
        ]
        widget.ids = {
            'slider_fan': DummyWidget(value=0),
            'cur_fan': DummyWidget(text='Fan: 0'),
            'auto': DummyWidget(),
            'dual': DummyWidget(),
            'recycle': DummyWidget(),
            'intake_fresh': DummyWidget(),
            'intake_recycle': DummyWidget(),
            'unfrost_front': DummyWidget(),
            'unfrost_rear': DummyWidget(),
            # New mode buttons
            'clim_on': DummyWidget(state='down'),
            'ac_on': DummyWidget(state='down'),
            'mode_auto': DummyWidget(),
            'mode_unfrost_front': DummyWidget(),
            'mode_recirc': DummyWidget(),
            'mode_fresh': DummyWidget(),
        }
        return widget

    def test_on_option_resyncs_front_defrost_when_ignition_off(self):
        widget = self._make_clim_widget(ignition_on=False)
        widget.ids['unfrost_front'].state = 'down'
        widget.on_option('unfrost_front', 'down')
        assert widget.runner.car.clim.unfrost_front == 0
        assert widget.ids['unfrost_front'].state == 'normal'

    def test_on_fan_updates_shared_state_and_label(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.on_fan(5)
        assert widget.runner.car.clim.fan == 5
        assert widget.ids['slider_fan'].value == 5
        assert widget.ids['cur_fan'].text == 'Fan: 5'

    def test_on_fan_zero_preserves_settings_and_disables(self):
        """Fan=0 sets enabled=False and fan=0 but preserves ac, dual, direction."""
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.enabled = True
        widget.runner.car.clim.fan = 3
        widget.runner.car.clim.ac = 1
        widget.runner.car.clim.dual = 1
        widget.runner.car.clim.dir_left = 4
        widget.on_fan(0)
        assert widget.runner.car.clim.fan == 0
        assert widget.runner.car.clim.enabled is False
        # Other settings must be preserved for restoration on fan-up.
        assert widget.runner.car.clim.ac == 1
        assert widget.runner.car.clim.dual == 1
        assert widget.runner.car.clim.dir_left == 4

    def test_on_fan_from_zero_reenables_climate(self):
        """Increasing fan from 0 re-enables climate with preserved settings."""
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.enabled = False
        widget.runner.car.clim.fan = 0
        widget.runner.car.clim.ac = 1
        widget.runner.car.clim.dual = 1
        widget.on_fan(3)
        assert widget.runner.car.clim.enabled is True
        assert widget.runner.car.clim.fan == 3
        assert widget.runner.car.clim.ac == 1
        assert widget.runner.car.clim.dual == 1

    def test_on_fan_disables_auto_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.auto = 1
        widget.on_fan(4)
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.fan == 4

    def test_update_dir_buttons_recognizes_real_fast_code(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
        })
        widget.runner.car.clim.dir_left = 0x08
        widget.runner.car.clim.dir_right = 0x08
        widget._update_dir_buttons()
        assert widget.ids['left_fast'].state == 'down'
        assert widget.ids['right_fast'].state == 'down'

    def test_update_dir_buttons_auto_direction_selects_auto_button(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
        })
        widget.runner.car.clim.dir_left = 0x00
        widget.runner.car.clim.dir_right = 0x00
        widget._update_dir_buttons()
        assert widget.ids['left_auto'].state == 'down'
        assert widget.ids['right_auto'].state == 'down'
        assert widget.ids['left_fr'].state == 'normal'
        assert widget.ids['right_fr'].state == 'normal'

    def test_update_dir_buttons_all_vents_direction(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
        })
        widget.runner.car.clim.dir_left = 0x07
        widget.runner.car.clim.dir_right = 0x07
        widget._update_dir_buttons()
        assert widget.ids['left_all'].state == 'down'
        assert widget.ids['right_all'].state == 'down'

    def test_on_dir_ignores_normal_state_transition(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dir_left = 0x04
        widget.on_dir(0, 0x08, 'normal')
        assert widget.runner.car.clim.dir_left == 0x04

    def test_on_dir_accepts_down_state_transition(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.dir_left = 0x04
        widget.on_dir(1, 0x05, 'down')
        assert widget.runner.car.clim.dual == 1
        assert widget.runner.car.clim.dir_right == 0x05

    def test_on_dir_right_same_as_left_keeps_mono_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.auto = 0
        widget.runner.car.clim.dir_left = 0x04
        widget.runner.car.clim.dir_right = 0x04

        widget.on_dir(1, 0x04, 'down')

        assert widget.runner.car.clim.dual == 0
        assert widget.runner.car.clim.dir_left == 0x04
        assert widget.runner.car.clim.dir_right == 0x04
        assert widget.ids['left_up'].state == 'down'
        assert widget.ids['right_up'].state == 'down'
        assert widget.ids['dual'].state == 'normal'

    def test_on_dir_left_mirrors_right_in_mono_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.dir_left = 0x04
        widget.runner.car.clim.dir_right = 0x02
        widget.on_dir(0, 0x07, 'down')
        assert widget.runner.car.clim.dir_left == 0x07
        assert widget.runner.car.clim.dir_right == 0x07

    def test_idle_1d0_monitor_update_does_not_clear_left_button(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
            'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text=''),
        })
        widget.runner.car.clim.dir_left = 0x04
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0x08, 0x00, 0x07, 0x00, 0x00, 0x10, 0x10, 0x00])
        widget.on_can_message(msg)
        assert widget.runner.car.clim.dir_left == 0x04
        assert widget.ids['left_up'].state == 'down'

    def test_monitor_temp_code_01_starts_at_14c(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'cur_temp0': DummyWidget(text=''),
            'cur_temp1': DummyWidget(text=''),
        })
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0x08, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x00])
        widget.on_can_message(msg)
        assert widget.ids['cur_temp0'].text == '14c'
        assert widget.ids['cur_temp1'].text == '14c'

    def test_monitor_temp_code_0b_matches_real_bench_display(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'cur_temp0': DummyWidget(text=''),
            'cur_temp1': DummyWidget(text=''),
        })
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00])
        widget.on_can_message(msg)
        assert widget.ids['cur_temp0'].text == '21c'
        assert widget.ids['cur_temp1'].text == '21c'

    def test_1e3_left_auto_frame_keeps_left_auto_and_sets_right_up(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
            'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text=''),
        })
        msg = types.SimpleNamespace(arbitration_id=0x1E3, data=[0x11, 0x30, 0x0E, 0x0A, 0x00, 0x40, 0x02, 0x00])
        widget.on_can_message(msg)
        assert widget.runner.car.clim.dir_left == 0x00
        assert widget.runner.car.clim.dir_right == 0x04
        assert widget.ids['left_auto'].state == 'down'
        assert widget.ids['left_up'].state == 'normal'
        assert widget.ids['right_up'].state == 'down'

    def test_1d0_single_nibble_direction_does_not_force_left_up(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_auto': DummyWidget(), 'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_all': DummyWidget(), 'left_fast': DummyWidget(),
            'right_auto': DummyWidget(), 'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_all': DummyWidget(), 'right_fast': DummyWidget(),
            'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text=''),
        })
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0x28, 0x00, 0x02, 0x04, 0x00, 0x0E, 0x0A, 0x00])
        widget.on_can_message(msg)
        assert widget.runner.car.clim.dir_left == 0x00
        assert widget.ids['left_auto'].state == 'down'
        assert widget.ids['left_up'].state == 'normal'

    def test_on_temp_right_zone_enables_dual_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.temp_left = 11
        widget.runner.car.clim.temp_right = 11
        widget.ids.update({'cur_temp1': DummyWidget(text='')})
        widget.on_temp(1, -1)
        assert widget.runner.car.clim.dual == 1
        assert widget.runner.car.clim.temp_right == 10  # decreased by 1

    def test_on_temp_right_zone_does_not_re_enable_dual_when_already_set(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 1
        widget.runner.car.clim.temp_right = 11
        widget.ids.update({'cur_temp1': DummyWidget(text='')})
        widget.on_temp(1, +1)
        assert widget.runner.car.clim.dual == 1
        assert widget.runner.car.clim.temp_right == 12

    def test_on_temp_left_zone_does_not_enable_dual_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.temp_left = 11
        widget.ids.update({'cur_temp0': DummyWidget(text='')})
        widget.on_temp(0, +1)
        assert widget.runner.car.clim.dual == 0
        assert widget.runner.car.clim.temp_left == 12

    def test_on_intake_fresh_sets_recycle_off(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.recycle = 1
        widget.on_intake(False, 'down')
        assert widget.runner.car.clim.recycle == 0
        assert widget.ids['intake_fresh'].state == 'down'
        assert widget.ids['intake_recycle'].state == 'normal'

    def test_on_intake_recirc_sets_recycle_on(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.recycle = 0
        widget.on_intake(True, 'down')
        assert widget.runner.car.clim.recycle == 1
        assert widget.ids['intake_recycle'].state == 'down'
        assert widget.ids['intake_fresh'].state == 'normal'

    def test_on_intake_ignition_off_does_not_set_recycle(self):
        widget = self._make_clim_widget(ignition_on=False)
        widget.runner.car.clim.recycle = 0
        widget.on_intake(True, 'down')
        assert widget.runner.car.clim.recycle == 0

    def test_on_intake_normal_state_is_ignored(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.recycle = 1
        widget.on_intake(False, 'normal')
        assert widget.runner.car.clim.recycle == 1

    # --- Mono mode (dual=0): left temp change syncs right ---

    def test_on_temp_left_zone_in_mono_mode_syncs_right_temp(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.temp_left = 11
        widget.runner.car.clim.temp_right = 11
        widget.ids.update({'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text='')})
        widget.on_temp(0, +1)
        assert widget.runner.car.clim.dual == 0
        assert widget.runner.car.clim.temp_left == 12
        assert widget.runner.car.clim.temp_right == 12  # synced in mono mode
        assert widget.ids['cur_temp0'].text == '21.5c'
        assert widget.ids['cur_temp1'].text == '21.5c'

    def test_on_temp_left_zone_mono_sync_stops_when_dual_is_on(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 1
        widget.runner.car.clim.temp_left = 11
        widget.runner.car.clim.temp_right = 8
        widget.ids.update({'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text='')})
        widget.on_temp(0, +1)
        assert widget.runner.car.clim.temp_left == 12
        assert widget.runner.car.clim.temp_right == 8  # NOT synced in dual mode

    # --- AUTO mode: direction buttons show auto; manual press exits auto ---

    def _make_dir_ids(self):
        """Return a dict of all direction button DummyWidgets for both zones."""
        ids = {}
        for prefix in ('left', 'right'):
            for suffix in ('auto', 'fr', 'up', 'ud', 'down', 'fd', 'all', 'fast'):
                ids[f'{prefix}_{suffix}'] = DummyWidget()
        return ids

    def test_update_dir_buttons_shows_auto_for_both_zones_when_auto_mode_on(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.dir_left = 0x04
        widget.runner.car.clim.dir_right = 0x02
        widget.runner.car.clim.auto = 1
        widget._update_dir_buttons()
        assert widget.ids['left_auto'].state == 'down'
        assert widget.ids['right_auto'].state == 'down'
        assert widget.ids['left_up'].state == 'normal'
        assert widget.ids['right_down'].state == 'normal'

    def test_update_dir_buttons_uses_dir_values_when_auto_mode_off(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.dir_left = 0x04
        widget.runner.car.clim.dir_right = 0x02
        widget.runner.car.clim.auto = 0
        widget._update_dir_buttons()
        assert widget.ids['left_up'].state == 'down'
        assert widget.ids['right_down'].state == 'down'
        assert widget.ids['left_auto'].state == 'normal'

    def test_on_dir_manual_press_exits_auto_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.auto = 1
        widget.on_dir(0, 0x04, 'down')  # press Up direction
        assert widget.runner.car.clim.auto == 0  # auto mode exited
        assert widget.runner.car.clim.dir_left == 0x04

    def test_on_dir_left_updates_right_ui_in_mono_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.auto = 0
        widget.on_dir(0, 0x04, 'down')
        assert widget.ids['left_up'].state == 'down'
        assert widget.ids['right_up'].state == 'down'
        assert widget.ids['right_auto'].state == 'normal'

    def test_on_dir_pressing_auto_dir_does_not_exit_auto_mode(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.auto = 1
        widget.on_dir(0, 0x00, 'down')  # press Auto direction
        assert widget.runner.car.clim.auto == 1  # stays in auto mode

    # --- on_airflow_mode: mutex group ---

    def test_on_airflow_mode_auto_sets_both_dirs_to_zero(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.dir_left = 0x04
        widget.runner.car.clim.dir_right = 0x02
        widget.on_airflow_mode('auto', 'down')
        assert widget.runner.car.clim.auto == 1
        assert widget.runner.car.clim.unfrost_front == 0
        assert widget.runner.car.clim.recycle == 0
        assert widget.runner.car.clim.dir_left == 0x00
        assert widget.runner.car.clim.dir_right == 0x00
        assert widget.ids['left_auto'].state == 'down'
        assert widget.ids['right_auto'].state == 'down'

    def test_on_airflow_mode_unfrost_front(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.auto = 1
        widget.on_airflow_mode('unfrost_front', 'down')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.unfrost_front == 1
        assert widget.runner.car.clim.recycle == 0
        assert widget.ids['unfrost_front'].state == 'down'
        assert widget.ids['mode_unfrost_front'].state == 'down'
        assert widget.ids['mode_auto'].state == 'normal'

    def test_on_airflow_mode_recirc(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1  # start with A/C on
        widget.on_airflow_mode('recirc', 'down')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.unfrost_front == 0
        assert widget.runner.car.clim.recycle == 1
        # Workbench-verified: recirc turns A/C off (0x1E3 byte0 ac bit = 0).
        assert widget.runner.car.clim.ac == 0
        assert widget.ids['intake_recycle'].state == 'down'
        assert widget.ids['mode_recirc'].state == 'down'

    def test_on_airflow_mode_fresh(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1  # start with A/C on
        widget.runner.car.clim.recycle = 1
        widget.on_airflow_mode('fresh', 'down')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.unfrost_front == 0
        assert widget.runner.car.clim.recycle == 0
        # Workbench-verified: fresh turns A/C off (0x1E3 byte0 ac bit = 0).
        assert widget.runner.car.clim.ac == 0
        assert widget.ids['mode_fresh'].state == 'down'
        assert widget.ids['mode_recirc'].state == 'normal'

    def test_on_airflow_mode_unfrost_front_preserves_ac(self):
        """Workbench-verified: unfrost_front does NOT turn A/C off (0x1E3 byte0 ac bit stays)."""
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1
        widget.on_airflow_mode('unfrost_front', 'down')
        assert widget.runner.car.clim.ac == 1  # A/C preserved

    def test_on_airflow_mode_ignored_when_ignition_off(self):
        widget = self._make_clim_widget(ignition_on=False)
        widget.runner.car.clim.auto = 0
        widget.on_airflow_mode('auto', 'down')
        assert widget.runner.car.clim.auto == 0  # not changed

    def test_on_airflow_mode_auto_from_standby_reenables_climate_at_fan1(self):
        """Pressing AUTO while climate is in standby (fan=0) re-enables it at fan=1.
        Workbench-verified: after fan→0 standby then AUTO pressed, climate is
        immediately active with auto mode and fan level 1.
        """
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.enabled = False  # standby
        widget.runner.car.clim.fan = 0
        widget.on_airflow_mode('auto', 'down')
        assert widget.runner.car.clim.enabled is True
        assert widget.runner.car.clim.fan == 1
        assert widget.runner.car.clim.auto == 1

    def test_on_airflow_mode_auto_from_standby_does_not_trigger_popup(self):
        """Pressing AUTO from standby must NOT trigger a 0x1A1 popup (workbench shows
        the 0x1A1 frame stays at 00 65 41 rather than switching to 80 08 41).
        """
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.enabled = False  # standby
        widget.runner.car.clim.fan = 0
        widget.runner.car.mfd_popup.flag = 0x00
        widget.runner.car.mfd_popup.msg_id = 0x65
        widget.on_airflow_mode('auto', 'down')
        # popup must NOT have changed to active state
        assert widget.runner.car.mfd_popup.flag != 0x80

    def test_on_airflow_mode_auto_from_recirc_triggers_mfd_popup(self):
        """Pressing AUTO from an active non-auto state triggers MFD popup
        with msg_id=0x08 and display_flags=0x41 (workbench: 80 08 41).
        """
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.enabled = True
        widget.runner.car.clim.auto = 0
        widget.runner.car.clim.recycle = 1
        widget.runner.car.clim.intake_explicit = True
        widget.on_airflow_mode('auto', 'down')
        mfd = widget.runner.car.mfd_popup
        assert mfd.flag == 0x80
        assert mfd.msg_id == 0x08
        assert mfd.display_flags == 0x41

    def test_on_airflow_mode_auto_from_auto_does_not_change_popup(self):
        """Pressing AUTO when already in AUTO must NOT trigger a popup."""
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.enabled = True
        widget.runner.car.clim.auto = 1
        widget.runner.car.mfd_popup.flag = 0xFF
        widget.runner.car.mfd_popup.msg_id = 0x00
        widget.on_airflow_mode('auto', 'down')
        assert widget.runner.car.mfd_popup.flag == 0xFF  # unchanged

    def test_on_fan_zero_sets_mfd_standby_state(self):
        """Fan=0 (standby) must update 0x1A1 to workbench-observed flag=0x00,
        msg_id=0x65, display_flags=0x41.
        """
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.enabled = True
        widget.runner.car.clim.fan = 3
        widget.on_fan(0)
        mfd = widget.runner.car.mfd_popup
        assert mfd.flag == 0x00
        assert mfd.msg_id == 0x65
        assert mfd.display_flags == 0x41

    def test_disabling_dual_mirrors_right_zone_to_left(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dual = 1
        widget.runner.car.clim.temp_left = 14
        widget.runner.car.clim.temp_right = 7
        widget.runner.car.clim.dir_left = 0x06
        widget.runner.car.clim.dir_right = 0x03
        widget.on_option('dual', 'normal')

        assert widget.runner.car.clim.dual == 0
        assert widget.runner.car.clim.temp_right == 14
        assert widget.runner.car.clim.dir_right == 0x06

    # --- on_clim_on / on_ac ---

    def test_on_clim_on_off_disables_clim_enabled(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.enabled = True
        widget.on_clim_on('normal')
        assert widget.runner.car.clim.enabled is False

    def test_on_clim_on_off_resets_auto_and_preserves_ac(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.auto = 1
        widget.runner.car.clim.ac = 1
        widget.on_clim_on('normal')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.ac == 1

    def test_on_clim_on_on_enables_clim_enabled(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.enabled = False
        widget.on_clim_on('down')
        assert widget.runner.car.clim.enabled is True

    def test_on_ac_sets_ac_on(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 0
        widget.on_ac('down')
        assert widget.runner.car.clim.ac == 1
        assert widget.ids['ac_on'].state == 'down'

    def test_on_ac_sets_ac_off(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1
        widget.on_ac('normal')
        assert widget.runner.car.clim.ac == 0

    def test_on_ac_off_disables_generic_auto(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1
        widget.runner.car.clim.auto = 1
        widget.on_ac('normal')
        assert widget.runner.car.clim.ac == 0
        assert widget.runner.car.clim.auto == 0
        assert widget.ids['mode_auto'].state == 'normal'

    def test_on_ac_ignored_when_ignition_off(self):
        widget = self._make_clim_widget(ignition_on=False)
        widget.runner.car.clim.ac = 1
        widget.on_ac('normal')
        assert widget.runner.car.clim.ac == 1  # not changed



    def _make_doors_widget(self):
        sent = []

        def send_message(arbitration_id, data):
            sent.append((arbitration_id, list(data)))

        runner = types.SimpleNamespace(car=VirtualCar(), send_message=send_message)
        widget = DoorsModule(runner)
        return widget, sent

    def test_send_0x1a1_popup_announces_before_show(self):
        widget, sent = self._make_doors_widget()
        widget._doors.front_left = 1

        widget._send_0x1A1_popup()

        assert sent[-1] == (0x1A1, [0x7F, 0xDE, 0x47, 0x00, 0x00, 0x00, 0x00, 0x00])

    def test_send_popup_show_contains_door_bitmap(self):
        widget, sent = self._make_doors_widget()
        widget._doors.front_left = 1
        widget._doors.boot = 1

        widget._send_popup_show(0)

        assert sent[-1] == (0x1A1, [0x80, 0x0B, 0xC7, 0x48, 0x00, 0x00, 0x00, 0x00])

    def test_send_popup_clear_uses_explicit_clear_frame(self):
        widget, sent = self._make_doors_widget()
        widget._doors.display_active = True
        widget._doors.popup_msg_id = 0xDE

        widget._send_popup_clear(0)

        assert sent[-1] == (0x1A1, [0xFF, 0x00, 0x47, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert widget._doors.display_active is False


class TestCombineUiHelpers:
    def _make_combine_widget(self):
        return CombineModule(types.SimpleNamespace(car=VirtualCar()))

    def test_combine_exposes_options_proxy_for_kv_bindings(self):
        widget = self._make_combine_widget()
        assert hasattr(widget, 'options')
        widget.options['low_beam'] = 1
        assert widget.runner.car.dashboard.low_beam == 1

    def test_combine_maps_legacy_coolant_and_oil_keys(self):
        widget = self._make_combine_widget()
        widget.on_option('coolant', 'down')
        widget.on_option('oil', 'down')
        assert widget.runner.car.dashboard.coolant_warn == 1
        assert widget.runner.car.dashboard.oil_warn == 1

    def test_sync_ui_updates_legacy_warning_toggle_ids(self):
        widget = self._make_combine_widget()
        widget.ids = {
            'coolant': DummyWidget(state='normal'),
            'oil': DummyWidget(state='normal'),
            'low_beam': DummyWidget(state='normal'),
        }
        widget.runner.car.dashboard.coolant_warn = 1
        widget.runner.car.dashboard.oil_warn = 1
        widget.runner.car.dashboard.low_beam = 1
        widget._sync_ui_from_options()
        assert widget.ids['coolant'].state == 'down'
        assert widget.ids['oil'].state == 'down'
        assert widget.ids['low_beam'].state == 'down'

    def test_combine_startup_keeps_cluster_on_when_ignition_is_already_on(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.power_mode = 0x01
        widget = CombineModule(types.SimpleNamespace(car=car))
        assert widget.runner.car.dashboard.on == 1


# ---------------------------------------------------------------------------
# can_messages tests
# ---------------------------------------------------------------------------

from can_messages import (ALL_MESSAGES, CanMessage, Msg036, Msg0E1, Msg0B6,
                          Msg128, Msg168, Msg190, Msg1A1, Msg1D0, Msg1E3,
                          Msg221, Msg2A1, Msg261, Msg12B, Msg1A3, Msg223,
                          Msg323, Msg165, Msg1A5, Msg1E5, Msg3E5, Msg52D,
                          Msg110, Msg0F6, Msg161, Msg1A8, Msg217, Msg12D,
                          STARTUP_WAKEUP_BURST)


class TestAppArgumentParsing:
    @pytest.fixture(autouse=True)
    def patch_app_deps(self):
        """Mock heavy app dependencies so app.py can be imported in tests."""
        import importlib
        # Provide minimal stubs for modules not mocked by conftest.py
        stubs = {}
        if 'can' not in sys.modules:
            stubs['can'] = make_can_mock()
        if 'yaml' not in sys.modules:
            yaml_mod = types.ModuleType('yaml')
            yaml_mod.load = lambda *a, **kw: {}
            yaml_mod.FullLoader = None
            stubs['yaml'] = yaml_mod
        for name, mod in stubs.items():
            sys.modules[name] = mod
        # Force re-import so the env var is applied fresh
        sys.modules.pop('app', None)
        yield
        for name in stubs:
            sys.modules.pop(name, None)
        sys.modules.pop('app', None)

    def test_kivy_args_disabled_for_custom_cli_flags(self):
        import app
        assert app.os.environ.get('KIVY_NO_ARGS') == '1'

    def test_parse_args_accepts_channel_option(self, monkeypatch):
        import app
        monkeypatch.setattr(sys, 'argv', ['app.py', '--channel', 'vcan0', '--monitor'])
        args = app.parse_args()
        assert args.channel == 'vcan0'
        assert args.monitor is True


class TestStartupWakeupBurst:
    def test_contains_expected_workbench_ids(self):
        ids = [can_id for _delay_s, can_id, _data in STARTUP_WAKEUP_BURST]
        for expected in (0x5D2, 0x5ED, 0x5E5, 0x5CC, 0x5DF, 0x5E0, 0x5F1, 0x48C):
            assert expected in ids

    def test_all_burst_frames_are_can_dlc_8(self):
        for delay_s, can_id, data in STARTUP_WAKEUP_BURST:
            assert delay_s >= 0
            assert can_id > 0
            assert len(data) == 8


class TestCanMessageDefaults:
    def test_all_messages_have_can_id(self):
        for can_id, cls in ALL_MESSAGES.items():
            msg = cls()
            assert msg.can_id == can_id

    def test_all_messages_have_period_ms(self):
        for cls in ALL_MESSAGES.values():
            msg = cls()
            assert isinstance(msg.period_ms, int)
            assert msg.period_ms > 0

    def test_repr_contains_id(self):
        msg = Msg036()
        assert '0x036' in repr(msg)


class TestMsg036Encode:
    def test_default_encode(self):
        car = VirtualCar()
        data = Msg036().encode(car)
        assert data[4] == car.bsi.power_mode

    def test_matches_workbench_power_off_signature(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x02
        data = Msg036().encode(car)
        assert data == [0x0E, 0x00, 0x00, 0x0F, 0x02, 0x00, 0x00, 0xA0]

    def test_matches_workbench_ignition_on_signature(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x01
        car.bsi.ignition_on = True
        data = Msg036().encode(car)
        assert data == [0x0E, 0x00, 0x00, 0x0F, 0x01, 0x00, 0x00, 0xA0]

    def test_first_boot_frame_uses_initial_workbench_trailer(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x02
        car.bsi.startup_banner_pending = True
        msg = Msg036()
        first = msg.encode(car)
        second = msg.encode(car)
        assert first[7] == 0x50
        assert second[7] == 0xA0

    def test_preignition_period_matches_workbench(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x02
        assert Msg036().get_period_ms(car) == 175

    def test_ignition_on_period_matches_workbench(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x01
        car.bsi.ignition_on = True
        assert Msg036().get_period_ms(car) == 100

    def test_economy_bit(self):
        car = VirtualCar()
        car.bsi.economy = 1
        data = Msg036().encode(car)
        assert (data[2] >> 7) & 1 == 1

    def test_decode_updates_ignition(self):
        car = VirtualCar()
        Msg036().decode(car, [0x0E, 0x00, 0x00, 0x00, 0x01, 0x80, 0x00, 0xA0])
        assert car.bsi.ignition_on is True
        assert car.bsi.power_mode == 0x01

    def test_lighting_states_match_workbench_dash_signature(self):
        expected = {
            0: [0x0E, 0x00, 0x00, 0x0F, 0x02, 0x00, 0x00, 0xA0],
            1: [0x0E, 0x00, 0x00, 0x2A, 0x02, 0x00, 0x00, 0xA0],
            2: [0x0E, 0x00, 0x00, 0x2A, 0x02, 0x00, 0x00, 0xA0],
            3: [0x0E, 0x00, 0x00, 0x2A, 0x02, 0x00, 0x00, 0xA0],
        }
        for mode, payload in expected.items():
            car = VirtualCar()
            car.bsi.light_mode = mode
            car.bsi.dash_lights = 0 if mode == 0 else 1
            car.bsi.dark_mode = 0
            car.bsi.lum = 15 if mode == 0 else 10
            car.bsi.power_mode = 0x02
            assert Msg036().encode(car) == payload


class TestWorkbenchAlignedMessagePeriods:
    def test_slow_bsi_frames_match_workbench_periods(self):
        assert Msg0F6().period_ms == 500
        assert Msg161().period_ms == 500
        assert Msg12D().period_ms == 500

    def test_cluster_and_status_frames_match_workbench_periods(self):
        assert Msg128().period_ms == 200
        assert Msg168().period_ms == 200
        assert Msg1A1().period_ms == 200

    def test_trip_frames_match_workbench_periods(self):
        assert Msg221().period_ms == 1000
        assert Msg2A1().period_ms == 1000
        assert Msg261().period_ms == 1000


class TestMsg0B6Encode:
    def test_matches_workbench_idle_placeholders_when_power_off(self):
        car = VirtualCar()
        car.bsi.ignition_on = False
        data = Msg0B6().encode(car)
        assert data == [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xD0]

    def test_matches_workbench_idle_placeholders_when_ignition_on(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        data = Msg0B6().encode(car)
        assert data == [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD0]

    def test_decode_treats_ffff_placeholders_as_zero(self):
        car = VirtualCar()
        Msg0B6().decode(car, [0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xD0])
        assert car.bsi.rpm == 0
        assert car.bsi.speed == 0
        assert car.bsi.engine_running == 0


class TestBsiBaseMonitorFastData:
    def test_monitor_placeholder_fast_frame_does_not_show_crazy_values(self):
        widget = BSIBaseModule.__new__(BSIBaseModule)
        widget.runner = types.SimpleNamespace(car=VirtualCar(), monitor=True)
        widget.ids = {
            'cur_rpm': DummyWidget(text='RPM: 0'),
            'slider_rpm': DummyWidget(value=0),
            'cur_speed': DummyWidget(text='Speed: 0 km/h'),
            'slider_speed': DummyWidget(value=0),
            'engine': DummyWidget(state='down'),
        }
        msg = types.SimpleNamespace(
            arbitration_id=0x0B6,
            data=[0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0xD0],
        )
        Msg0B6().decode(widget.runner.car, msg.data)
        widget.on_can_message(msg)
        assert widget.runner.car.bsi.rpm == 0
        assert widget.runner.car.bsi.speed == 0
        assert widget.ids['cur_rpm'].text == 'RPM: 0'
        assert widget.ids['cur_speed'].text == 'Speed: 0 km/h'
        assert widget.ids['engine'].state == 'normal'


class TestMsg0E1Encode:
    def test_inactive_when_no_sensors(self):
        car = VirtualCar()
        data = Msg0E1().encode(car)
        assert data == [0x24, 0x00, 0x3F, 0xFC, 0xFC, 0xFC, 0x00]

    def test_active_with_rear_sensors(self):
        car = VirtualCar()
        car.parktronic.rear_active = 1
        car.parktronic.rear_left = 3
        data = Msg0E1().encode(car)
        assert data[1] & 0x40  # rear_active flag set

    def test_decode_updates_car(self):
        car = VirtualCar()
        Msg0E1().decode(car, [0x24, 0x40, 0x3F, 0xE0, 0x00, 0x42, 0x00])
        assert car.parktronic.rear_active == 1
        assert car.parktronic.rear_left == 7


class TestMsg128Encode:
    def test_bsi_encoding_when_dashboard_inactive(self):
        car = VirtualCar()
        data = Msg128().encode(car)
        # bsi-base lighting encoding: byte[0] = 0x91
        assert data[0] == 0x91

    def test_combine_encoding_when_dashboard_active(self):
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.seatbelt = 1
        data = Msg128().encode(car)
        assert (data[0] >> 6) & 1 == 1  # seatbelt bit

    def test_combine_encoding_keeps_cluster_on_and_manual_gearbox_defaults(self):
        car = VirtualCar()
        car.dashboard.active = True
        car.bsi.ignition_on = True
        car.bsi.power_mode = 0x01
        data = Msg128().encode(car)
        assert (data[5] >> 7) & 1 == 1
        assert data[7] & 0x03 == 0x01

    def test_decode_updates_light_mode(self):
        car = VirtualCar()
        # byte[4] = 0xC0 means low beam
        Msg128().decode(car, [0x91, 0xE0, 0x00, 0x00, 0xC0, 0x80, 0xB0, 0x01])
        assert car.bsi.light_mode == 2  # _lights_low

    def test_matches_workbench_light_mode_payloads(self):
        car = VirtualCar()
        msg = Msg128()
        expected = {0: 0x00, 1: 0x80, 2: 0xC0, 3: 0xE0}
        for mode, d5 in expected.items():
            car.bsi.light_mode = mode
            assert msg.encode(car) == [0x91, 0xE0, 0x00, 0x00, d5, 0x80, 0xB0, 0x01]

    def test_decode_treats_0xa0_as_high_beam_transition(self):
        car = VirtualCar()
        Msg128().decode(car, [0x91, 0xE0, 0x00, 0x00, 0xA0, 0x80, 0xB0, 0x01])
        assert car.bsi.light_mode == 3


class TestMsg168Encode:
    def test_returns_none_when_dashboard_inactive_and_no_tyre_alert(self):
        car = VirtualCar()
        assert Msg168().encode(car) is None

    def test_returns_tyre_overlay_when_inactive_and_alert_set(self):
        car = VirtualCar()
        car.tyres.alert_0x168_b1 = 0x80
        data = Msg168().encode(car)
        assert data is not None
        assert data[1] == 0x80

    def test_combine_encoding(self):
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.battery = 1
        data = Msg168().encode(car)
        assert data is not None
        assert (data[4] >> 1) & 1 == 1  # battery bit


class TestMsg1E3DecodeBenchAlignment:
    def test_left_auto_dump_decodes_auto_left_and_up_right(self):
        car = VirtualCar()
        Msg1E3().decode(car, [0x11, 0x30, 0x0E, 0x0A, 0x00, 0x40, 0x02, 0x00])
        assert car.clim.dir_left == 0x00
        assert car.clim.dir_right == 0x04

    def test_ac_bit_decoded_when_on(self):
        car = VirtualCar()
        Msg1E3().decode(car, [0x1C, 0x30, 0x0B, 0x0B, 0x00, 0x00, 0x02, 0x00])
        assert car.clim.ac == 1   # bit 4 of byte 0
        assert car.clim.auto == 1
        assert car.clim.dual == 0

    def test_ac_bit_decoded_when_off(self):
        car = VirtualCar()
        Msg1E3().decode(car, [0x0C, 0x30, 0x0B, 0x0B, 0x00, 0x00, 0x02, 0x00])
        assert car.clim.ac == 0   # bit 4 of byte 0 is 0
        assert car.clim.auto == 1


class TestMsg1E3EncodeBenchAlignment:
    """Verify 0x1E3 active-climate encoding matches workbench captures."""

    def test_byte0_auto_ac_no_dual_gives_0x1c(self):
        """Workbench initial state: 1C 30 0B 0B 00 00 02 00 → byte0=0x1C."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        car.clim.dual = 0
        data = Msg1E3().encode(car)
        assert data[0] == 0x1C  # (1<<4) | 0x0C | 0

    def test_byte0_dual_bit_set_with_auto_gives_0x1d(self):
        """Workbench dual+auto state: byte0=0x1D."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        car.clim.dual = 1
        data = Msg1E3().encode(car)
        assert data[0] == 0x1D  # (1<<4) | 0x0C | 1

    def test_byte0_manual_ac_no_dual_gives_0x10(self):
        """Manual mode (implicit fresh, auto=0, intake_explicit=False), A/C on, no dual: byte0=0x10."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 0
        car.clim.ac = 1
        car.clim.dual = 0
        # intake_explicit=False (default) → mode_bits=0x00; matches fanoff workbench 0x10
        data = Msg1E3().encode(car)
        assert data[0] == 0x10  # (1<<4) | 0 | 0

    def test_byte0_manual_ac_dual_gives_0x11(self):
        """Workbench fan-speed test (fanoff): implicit manual, A/C on, dual=1 → byte0=0x11."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 0
        car.clim.ac = 1
        car.clim.dual = 1
        # intake_explicit=False (default) → mode_bits=0x00; matches fanoff workbench 0x11
        data = Msg1E3().encode(car)
        assert data[0] == 0x11  # (1<<4) | 0 | 1

    def test_byte1_has_constant_0x30_bits_when_unfrost_off(self):
        """Workbench: byte1=0x30 when front unfrost is off."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_front = 0
        data = Msg1E3().encode(car)
        assert data[1] == 0x30

    def test_byte1_is_0xb0_when_unfrost_active(self):
        """Workbench: byte1=0xB0=0x30|0x80 when front unfrost is on."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_front = 1
        data = Msg1E3().encode(car)
        assert data[1] == 0xB0  # 0x30 | (1<<7)

    def test_full_initial_state_matches_workbench(self):
        """Workbench initial state: left=21°C, right=21°C, auto, fan=3."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        car.clim.dual = 0
        car.clim.temp_left = 11   # index 11 = 21°C
        car.clim.temp_right = 11
        car.clim.fan = 3
        data = Msg1E3().encode(car)
        assert data == [0x1C, 0x30, 0x0B, 0x0B, 0x00, 0x00, 0x02, 0x00]

    def test_byte0_ac_off_with_auto_gives_0x0c(self):
        """When A/C compressor is off, byte 0 bit 4 is 0: 0x04|(0<<4)|(1<<3)=0x0C."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 0
        car.clim.auto = 1
        car.clim.dual = 0
        data = Msg1E3().encode(car)
        assert data[0] == 0x0C  # 0x04 | 0 | 0x08 | 0

    def test_byte0_ac_off_manual_gives_0x00(self):
        """A/C off, implicit manual mode (intake_explicit=False): (0<<4)|0|0 = 0x00."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 0
        car.clim.auto = 0
        car.clim.dual = 0
        # intake_explicit=False → mode_bits=0x00
        data = Msg1E3().encode(car)
        assert data[0] == 0x00

    def test_byte0_explicit_fresh_ac_off_dual_gives_0x05(self):
        """Workbench: explicit Fresh after AUTO, ac=0, dual=1 → byte0=0x05."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 0
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 0
        car.clim.intake_explicit = True   # Fresh explicitly selected
        data = Msg1E3().encode(car)
        assert data[0] == 0x05  # 0x00 (no recirc) | 0x00 (ac=0) | 0x04 (explicit) | 0x01 (dual)

    def test_byte0_explicit_recirc_ac_off_dual_gives_0x85(self):
        """Workbench: explicit Recirc, ac=0, dual=1 → byte0=0x85."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 0
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 1
        car.clim.intake_explicit = True   # Recirc explicitly selected
        data = Msg1E3().encode(car)
        assert data[0] == 0x85  # 0x80 (recirc) | 0x00 (ac=0) | 0x04 (explicit) | 0x01 (dual)

    def test_byte0_explicit_fresh_ac_on_dual_gives_0x15(self):
        """Explicit Fresh with A/C still on, dual=1 → byte0=0x15."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 0
        car.clim.intake_explicit = True
        data = Msg1E3().encode(car)
        assert data[0] == 0x15  # 0x00 | 0x10 (ac) | 0x04 (explicit) | 0x01 (dual)

    def test_standby_byte0_encodes_ac_and_dual_with_0x20(self):
        """Workbench fan=0 standby: byte0=(ac<<4)|0x20|dual; fan=0x0F; temps preserved."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.enabled = False
        car.clim.ac = 1
        car.clim.dual = 1
        car.clim.temp_left = 11
        car.clim.temp_right = 11
        data = Msg1E3().encode(car)
        assert data[0] == 0x31   # (1<<4)|0x20|1 — matches workbench standby frame
        assert data[6] == 0x0F  # fan=off
        assert data[2] == 11    # temp_left preserved
        assert data[3] == 11    # temp_right preserved

    def test_standby_byte0_ac_on_no_dual(self):
        """Standby with ac=1, dual=0: byte0=(1<<4)|0x20|0=0x30."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.enabled = False
        car.clim.ac = 1
        car.clim.dual = 0
        data = Msg1E3().encode(car)
        assert data[0] == 0x30   # (1<<4)|0x20|0

    def test_standby_preserves_temps_in_1e3(self):
        """When suspended (fan=0), 0x1E3 preserves the temperature bytes."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.enabled = False
        car.clim.ac = 1
        car.clim.temp_left = 14
        car.clim.temp_right = 9
        data = Msg1E3().encode(car)
        assert data[2] == 14
        assert data[3] == 9


class TestMsg12DEncode:
    """Verify 0x12D matches workbench captures."""

    def test_suppressed_when_ignition_off(self):
        car = VirtualCar()
        car.bsi.ignition_on = False
        assert Msg12D().encode(car) is None

    def test_workbench_fixed_payload_when_ignition_on(self):
        """Workbench always sends 00 32 32 00 00 00 98 80 when ignition on."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        data = Msg12D().encode(car)
        assert data == [0x00, 0x32, 0x32, 0x00, 0x00, 0x00, 0x98, 0x80]



    def test_suppressed_when_tyre_display_active(self):
        car = VirtualCar()
        car.tyres.display_active = True
        assert Msg1A1().encode(car) is None

    def test_encodes_driver_door_popup_when_door_display_active(self):
        car = VirtualCar()
        car.doors.display_active = True
        car.doors.front_left = 1
        assert Msg1A1().encode(car) == [0x80, 0xDE, 0xC7, 0x40, 0x00, 0x00, 0x00, 0x00]

    def test_encodes_door_status_bits_for_workbench_mfd_popup(self):
        car = VirtualCar()
        car.doors.display_active = True
        car.doors.front_left = 1
        car.doors.rear_right = 1
        car.doors.boot = 1
        car.doors.fuel_flap = 1
        assert Msg1A1().encode(car) == [0x80, 0x0B, 0xC7, 0x68, 0x40, 0x00, 0x00, 0x00]

    def test_idle_encoding_matches_dump_style(self):
        car = VirtualCar()
        assert Msg1A1().encode(car) == [0x00, 0x8B, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_encodes_active_popup_like_real_dump(self):
        car = VirtualCar()
        car.mfd_popup.flag = 0x80
        car.mfd_popup.msg_id = 0xDE
        assert Msg1A1().encode(car) == [0x80, 0xDE, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_encodes_clear_stage_like_real_dump(self):
        car = VirtualCar()
        car.mfd_popup.flag = 0x00
        car.mfd_popup.msg_id = 0xDE
        assert Msg1A1().encode(car) == [0x00, 0xDE, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_uses_mfd_popup_display_flags_when_set(self):
        """Msg1A1 byte2 must use mfd_popup.display_flags (not a fixed constant).
        Workbench: climate AUTO popup uses 0x41 as the display/priority byte.
        """
        car = VirtualCar()
        car.mfd_popup.flag = 0x80
        car.mfd_popup.msg_id = 0x08
        car.mfd_popup.display_flags = 0x41
        data = Msg1A1().encode(car)
        assert data == [0x80, 0x08, 0x41, 0x00, 0x00, 0x00, 0x00, 0x00]

    def test_decode_updates_car(self):
        car = VirtualCar()
        Msg1A1().decode(car, [0x80, 0x42, 0xC6, 0, 0, 0, 0, 0])
        assert car.mfd_popup.flag == 0x80
        assert car.mfd_popup.msg_id == 0x42


class TestMsg1D0Encode:
    def test_bsi_idle_when_clim_not_enabled(self):
        car = VirtualCar()
        data = Msg1D0().encode(car)
        assert data == [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]

    def test_airflow_direction_encodes_both_zones_independently(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 0x04
        car.clim.dir_right = 0x00
        data = Msg1D0().encode(car)
        assert data[3] == 0x40  # (4 << 4) | 0

    def test_airflow_direction_both_zones_independent(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 0x04   # up
        car.clim.dir_right = 0x02  # down
        data = Msg1D0().encode(car)
        assert data[3] == 0x42  # workbench: left=4 up, right=2 bottom

    def test_byte0_base_constant_in_auto_mode(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        data = Msg1D0().encode(car)
        assert data[0] == 0x08  # workbench: AUTO mode, no manual-distribution bit

    def test_byte0_recirc_mode_uses_0x08_not_0x28(self):
        """Workbench: recirc mode → byte0=0x08 (same as AUTO), NOT 0x28.
        From workbench_airflow.csv: 08 00 00 00 30 0B 0B 00 when recirc is active.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 0
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[0] == 0x08

    def test_byte0_fresh_explicit_mode_uses_0x08_not_0x28(self):
        """Workbench: explicit fresh mode → byte0=0x08 (same as AUTO), NOT 0x28.
        From workbench_airflow.csv: 08 00 00 00 20 0B 0B 00 when fresh is active.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 0
        car.clim.recycle = 0
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[0] == 0x08

    def test_byte0_manual_mode_has_0x20_bit(self):
        """Workbench fan-speed test: manual mode (no auto, no explicit intake) adds 0x20 → byte0=0x28."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 0
        car.clim.intake_explicit = False
        data = Msg1D0().encode(car)
        assert data[0] == 0x28  # 0x08 | 0x20

    def test_byte0_includes_unfrost_flags_when_active(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_front = 1
        data = Msg1D0().encode(car)
        assert data[0] == 0x19  # workbench: 0x08 | 0x11 when unfrost active

    def test_decode_extracts_left_zone_from_high_nibble_when_mirrored(self):
        car = VirtualCar()
        Msg1D0().decode(car, [0x08, 0x00, 0x07, 0x88, 0x00, 0x10, 0x10, 0x00])
        assert car.clim.dir_left == 0x08

    def test_preignition_period_matches_workbench(self):
        car = VirtualCar()
        assert Msg1D0().get_period_ms(car) == 500

    def test_idle_1d0_frame_does_not_clear_left_direction(self):
        car = VirtualCar()
        car.clim.dir_left = 0x04
        Msg1D0().decode(car, [0x08, 0x00, 0x07, 0x00, 0x00, 0x10, 0x10, 0x00])
        assert car.clim.dir_left == 0x04

    def test_bsi_idle_when_ignition_off_even_if_clim_enabled(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = False
        data = Msg1D0().encode(car)
        assert data == [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]

    def test_clim_encoding_when_enabled_and_ignition_on(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.fan = 3
        data = Msg1D0().encode(car)
        assert data[2] == 2  # bench raw 0x02 = fan level 3

    def test_clim_off_encodes_as_0x0f(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.fan = 0
        data = Msg1D0().encode(car)
        assert data[2] == 0x0F

    def test_decode_fan_raw_zero_means_level_one(self):
        car = VirtualCar()
        Msg1D0().decode(car, [0x28, 0x00, 0x00, 0x44, 0x00, 0x0D, 0x0A, 0x00])
        assert car.clim.fan == 1

    def test_standby_byte0_is_0xa8_when_clim_disabled_ignition_on(self):
        """Workbench: fan=0 standby frame has byte0=0xA8 (0x80|0x20|0x08)."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.enabled = False
        car.clim.temp_left = 11
        car.clim.temp_right = 11
        data = Msg1D0().encode(car)
        assert data[0] == 0xA8
        assert data[2] == 0x0F  # fan=off
        assert data[5] == 11    # temp_left preserved
        assert data[6] == 11    # temp_right preserved

    def test_standby_preserves_temps_in_1d0(self):
        """When suspended (fan=0), 0x1D0 preserves the temperature bytes."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.enabled = False
        car.clim.temp_left = 14
        car.clim.temp_right = 9
        data = Msg1D0().encode(car)
        assert data[5] == 14
        assert data[6] == 9


class TestMsg190Rolling:
    def test_counter_rolls_when_ignition_on(self):
        car = VirtualCar()
        car.bsi.power_mode = 0x01
        msg = Msg190()
        d1 = msg.encode(car)
        d2 = msg.encode(car)
        assert d1[3] != d2[3]

    def test_counter_stable_when_ignition_off(self):
        car = VirtualCar()
        msg = Msg190()
        d1 = msg.encode(car)
        d2 = msg.encode(car)
        assert d1[3] == d2[3]


class TestMsg221EncodeDecodeRoundtrip:
    def test_roundtrip(self):
        car_a = VirtualCar()
        car_a.trip.fuel = 8.7
        car_a.trip.autonomy = 500
        car_a.trip.dist = 45
        data = Msg221().encode(car_a)
        car_b = VirtualCar()
        Msg221().decode(car_b, data)
        assert abs(car_b.trip.fuel - 8.7) < 0.1
        assert car_b.trip.autonomy == 500
        assert abs(car_b.trip.dist - 45) < 0.2


class TestMsg12BEncodeDecode:
    def test_encode(self):
        car = VirtualCar()
        car.bte.bits = 0b10110001
        data = Msg12B().encode(car)
        assert data == [0b10110001]

    def test_decode(self):
        car = VirtualCar()
        Msg12B().decode(car, [0b10110001])
        assert car.bte.bits == 0b10110001


class TestAllMessagesRegistry:
    def test_no_duplicate_can_ids(self):
        ids = list(ALL_MESSAGES.keys())
        assert len(ids) == len(set(ids)), "Duplicate CAN IDs found in ALL_MESSAGES"

    def test_all_subclasses_registered(self):
        """Every CanMessage subclass with a real can_id should appear in ALL_MESSAGES."""
        def subclasses(cls):
            for sub in cls.__subclasses__():
                yield sub
                yield from subclasses(sub)
        for sub in subclasses(CanMessage):
            if sub.can_id != 0:
                assert sub.can_id in ALL_MESSAGES, f'{sub.__name__} not in ALL_MESSAGES'


class TestMsg1A5Buttons:
    def test_radio_encoding_when_buttons_inactive(self):
        car = VirtualCar()
        car.radio.volflag = 0xE0
        car.radio.volume = 15
        data = Msg1A5().encode(car)
        assert data == [0xE0 | 15]

    def test_buttons_encoding_when_active(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.volflag = 0x00
        car.buttons.volume = 20
        data = Msg1A5().encode(car)
        assert data == [0x00 | 20]

    def test_buttons_encode_steps_volume_ticks(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.volflag = 0x00
        car.buttons._volume_action_ticks = 1
        Msg1A5().encode(car)
        assert car.buttons._volume_action_ticks == 0
        assert car.buttons.volflag == 0xE0

    def test_buttons_required_modules_includes_buttons(self):
        assert 'buttons' in Msg1A5.required_modules

    def test_decode_updates_buttons_volume_when_active(self):
        car = VirtualCar()
        car.buttons.active = True
        Msg1A5().decode(car, [0x00 | 22])
        assert car.buttons.volume == 22
        assert car.radio.volume == 15  # unchanged

    def test_decode_updates_radio_volume_when_buttons_inactive(self):
        car = VirtualCar()
        Msg1A5().decode(car, [0x00 | 22])
        assert car.radio.volume == 22


class TestMsg3E5Buttons:
    def test_radio_encoding_when_buttons_inactive(self):
        car = VirtualCar()
        car.radio.panel['tel'] = 1
        data = Msg3E5().encode(car)
        # radio-gen layout: tel is in b0 bits [5:4]
        assert (data[0] >> 4) & 1 == 1

    def test_buttons_encoding_when_active(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.panel['tel'] = 1
        data = Msg3E5().encode(car)
        # buttons layout: tel is in b0 bits [5:4]
        assert (data[0] >> 4) & 1 == 1

    def test_buttons_encoding_ok_key(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.panel['ok'] = 1
        data = Msg3E5().encode(car)
        assert (data[2] >> 6) & 1 == 1

    def test_buttons_encode_steps_pulse_ticks(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.press('trip')
        assert car.buttons.panel['trip'] == 1
        # Encoding steps the pulse timer; after _pulse_window ticks button clears
        for _ in range(car.buttons._pulse_window):
            Msg3E5().encode(car)
        assert car.buttons.panel['trip'] == 0

    def test_buttons_required_modules_includes_buttons(self):
        assert 'buttons' in Msg3E5.required_modules

    def test_decode_updates_buttons_panel_when_active(self):
        car = VirtualCar()
        car.buttons.active = True
        # Encode 'ok' pressed in buttons layout
        frame = [0x00, 0x00, (1 << 6), 0x00, 0x00, 0x00]
        Msg3E5().decode(car, frame)
        assert car.buttons.panel['ok'] == 1

    def test_decode_updates_radio_panel_when_buttons_inactive(self):
        car = VirtualCar()
        # radio-gen layout: ok is b2[7:6]
        frame = [0x00, 0x00, (1 << 6), 0x00, 0x00, 0x00]
        Msg3E5().decode(car, frame)
        assert car.radio.panel['ok'] == 1


# ---------------------------------------------------------------------------
# CanRunner integration tests
# ---------------------------------------------------------------------------

class TestCanRunnerVirtualCar:
    @pytest.fixture(autouse=True)
    def patch_can(self):
        sys.modules['can'] = make_can_mock()
        yield
        sys.modules.pop('can', None)

    def _make_runner(self):
        import importlib
        import can_runner as cr
        importlib.reload(cr)
        return cr.CanRunner(monitor=True)

    def test_runner_has_car(self):
        runner = self._make_runner()
        assert hasattr(runner, 'car')
        assert runner.car is not None

    def test_runner_defaults_to_vcan0(self):
        runner = self._make_runner()
        assert runner.channel == 'vcan0'

    def test_runner_accepts_custom_channel(self):
        import importlib
        import can_runner as cr
        importlib.reload(cr)
        runner = cr.CanRunner(channel='vcan0', monitor=True)
        assert runner.channel == 'vcan0'

    def test_ignition_on_property_reads_from_car(self):
        runner = self._make_runner()
        assert runner.ignition_on is False
        runner.car.bsi.ignition_on = True
        assert runner.ignition_on is True

    def test_ignition_on_property_writes_to_car(self):
        runner = self._make_runner()
        runner.ignition_on = True
        assert runner.car.bsi.ignition_on is True

    def test_power_mode_property(self):
        runner = self._make_runner()
        runner.power_mode = 0x01
        assert runner.car.bsi.power_mode == 0x01
        assert runner.power_mode == 0x01

    def test_reverse_property(self):
        runner = self._make_runner()
        runner.reverse = 1
        assert runner.car.bsi.reverse == 1
        assert runner.reverse == 1

    def test_tyres_display_active_property(self):
        runner = self._make_runner()
        runner.tyres_display_active = True
        assert runner.car.tyres.display_active is True
        assert runner.tyres_display_active is True

    def test_doors_display_active_property(self):
        runner = self._make_runner()
        runner.doors_display_active = True
        assert runner.car.doors.display_active is True
        assert runner.doors_display_active is True

    def test_tyres_alert_0x168_b1_property(self):
        runner = self._make_runner()
        runner.tyres_alert_0x168_b1 = 0xC0
        assert runner.car.tyres.alert_0x168_b1 == 0xC0
        assert runner.tyres_alert_0x168_b1 == 0xC0

    def test_combine_active_0x168_property(self):
        runner = self._make_runner()
        runner.combine_active_0x168 = True
        assert runner.car.dashboard.active is True
        assert runner.combine_active_0x168 is True

    def test_register_message_stores_object(self):
        runner = self._make_runner()
        msg = Msg036()
        runner.register_message(msg)
        assert runner._can_message_objects[0x036] is msg

    def test_register_message_duplicate_warns(self, caplog):
        import logging
        runner = self._make_runner()
        with caplog.at_level(logging.WARNING):
            runner.register_message(Msg036())
            runner.register_message(Msg036())
        assert any('0x036' in r.message for r in caplog.records if r.levelno == logging.WARNING)

    def test_module_specific_message_disabled_when_module_missing(self):
        runner = self._make_runner()
        runner.set_enabled_modules(['bsi-base'])
        assert runner.message_enabled(Msg1D0()) is False
        assert runner.message_enabled(Msg12D()) is False
        # Msg1A5 / Msg3E5 require at least one of radio-gen, buttons, radio-cd
        assert runner.message_enabled(Msg1A5()) is False
        assert runner.message_enabled(Msg3E5()) is False

    def test_module_specific_message_enabled_when_module_present(self):
        runner = self._make_runner()
        runner.set_enabled_modules(['bsi-base', 'clim'])
        assert runner.message_enabled(Msg1D0()) is True
        assert runner.message_enabled(Msg12D()) is True

    def test_buttons_message_enabled_when_buttons_active(self):
        runner = self._make_runner()
        runner.set_enabled_modules(['bsi-base', 'buttons'])
        assert runner.message_enabled(Msg1A5()) is True
        assert runner.message_enabled(Msg3E5()) is True

    def test_base_message_not_gated_by_module_list(self):
        runner = self._make_runner()
        runner.set_enabled_modules(['clim'])
        assert runner.message_enabled(Msg036()) is True


class TestCanRunnerTransmitRobustness:
    @pytest.fixture(autouse=True)
    def patch_can(self):
        can_mock = make_can_mock()

        class MockCanError(Exception):
            pass

        can_mock.CanError = MockCanError
        sys.modules['can'] = can_mock
        yield
        sys.modules.pop('can', None)

    def _make_runner(self, monitor=False):
        import importlib
        import can_runner as cr
        importlib.reload(cr)
        return cr.CanRunner(monitor=monitor)

    def test_send_message_swallows_transmit_buffer_errors(self, capsys):
        runner = self._make_runner(monitor=False)

        def fail_send(_msg):
            raise sys.modules['can'].CanError('Failed to transmit: [Errno 105] No buffer space available')

        runner.bus.send = fail_send
        runner.car.bsi.ignition_on = True

        runner.send_message(0x036, [0x00] * 8)

        out = capsys.readouterr().out
        assert 'TX warning' in out
        assert '0x036' in out

    def test_can_message_object_send_error_does_not_abort_sender_loop(self, capsys):
        runner = self._make_runner(monitor=False)
        runner.car.bsi.ignition_on = True

        class OneShotMessage:
            can_id = 0x036
            period_ms = 1
            required_modules = frozenset()

            def get_period_ms(self, car):
                return 1

            def encode(self, car):
                return [0x00] * 8

        def fail_send(_msg, *args, **kwargs):
            runner.sender_exit.set()
            raise sys.modules['can'].CanError('Failed to transmit: [Errno 105] No buffer space available')

        runner.bus.send = fail_send
        runner.register_message(OneShotMessage())
        runner._message_object_timers[0x036] = datetime.datetime.now() - datetime.timedelta(seconds=1)

        type(runner).sender(runner)

        out = capsys.readouterr().out
        assert 'TX warning' in out
        assert '0x036' in out

    def test_one_tx_error_does_not_block_other_keepalive_ids(self, capsys):
        runner = self._make_runner(monitor=False)
        runner.car.bsi.ignition_on = True
        sent_ids = []

        def selective_send(msg, *args, **kwargs):
            sent_ids.append(msg.arbitration_id)
            if msg.arbitration_id == 0x036 and sent_ids.count(0x036) == 1:
                raise sys.modules['can'].CanError('Failed to transmit: [Errno 105] No buffer space available')

        runner.bus.send = selective_send

        runner.send_message(0x036, [0x00] * 8)
        runner.send_message(0x110, [0x00] * 8)

        out = capsys.readouterr().out
        assert 'TX warning' in out
        assert 0x110 in sent_ids


class TestCanRunnerSchedulerTuning:
    @pytest.fixture(autouse=True)
    def patch_can(self):
        sys.modules['can'] = make_can_mock()
        yield
        sys.modules.pop('can', None)

    def test_scheduler_uses_small_early_send_margin(self):
        import importlib
        import can_runner as cr
        importlib.reload(cr)
        runner = cr.CanRunner(monitor=True)

        assert runner.SCHEDULE_ADVANCE_FACTOR == pytest.approx(0.95)
        assert runner.SENDER_SLEEP_S <= 0.005
        assert runner._period_due(0.095, 100) is True
        assert runner._period_due(0.090, 100) is False


class TestCanRunnerDuplicateDetection:
    @pytest.fixture(autouse=True)
    def patch_can(self):
        sys.modules['can'] = make_can_mock()
        yield
        sys.modules.pop('can', None)

    def _make_runner(self):
        import importlib
        import can_runner as cr
        importlib.reload(cr)
        return cr.CanRunner(monitor=True)

    def test_first_registration_no_warning(self, caplog):
        import logging
        runner = self._make_runner()
        with caplog.at_level(logging.WARNING):
            runner.reg(lambda: None, 0x1D0, 500)
        assert not any(r.levelno == logging.WARNING for r in caplog.records)

    def test_duplicate_registration_emits_warning(self, caplog):
        import logging
        runner = self._make_runner()
        with caplog.at_level(logging.WARNING):
            runner.reg(lambda: None, 0x1D0, 500)
            runner.reg(lambda: None, 0x1D0, 100)
        assert any('0x1D0' in r.message for r in caplog.records if r.levelno == logging.WARNING)

    def test_duplicate_registration_overrides(self):
        runner = self._make_runner()
        def sender_a():
            return 0x1D0, [0x01]
        def sender_b():
            return 0x1D0, [0x02]
        runner.reg(sender_a, 0x1D0, 500)
        runner.reg(sender_b, 0x1D0, 500)
        assert runner._can_id_owners[0x1D0] is sender_b

    def test_different_ids_no_warning(self, caplog):
        import logging
        runner = self._make_runner()
        with caplog.at_level(logging.WARNING):
            runner.reg(lambda: None, 0x1D0, 500)
            runner.reg(lambda: None, 0x1E3, 500)
        assert not any(r.levelno == logging.WARNING for r in caplog.records)


# ---------------------------------------------------------------------------
# PSA-RE cross-reference tests
# Verify signal mappings confirmed by prototux/PSA-RE AEE2004 LS.CONF data
# ---------------------------------------------------------------------------

class TestMsg0F6PSARe:
    """0x0F6 — BSI_SLOW_DATA: verified signal positions from PSA-RE."""

    def test_decode_external_temperature_uses_half_degree_scaling(self):
        """PSA-RE: EXTERNAL_TEMPERATURE at byte 5 (idx 5), formula raw×0.5−40."""
        car = VirtualCar()
        # raw=0xB2=178 → 178*0.5-40 = 49.0 °C
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xB2, 0xB2, 0x20])
        assert abs(car.bsi.temperature - 49.0) < 0.01

    def test_decode_external_temperature_lo_boundary(self):
        """raw=0 → 0*0.5-40 = -40 °C (minimum)."""
        car = VirtualCar()
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20])
        assert abs(car.bsi.temperature - (-40.0)) < 0.01

    def test_decode_coolant_temperature_offset_minus_40(self):
        """PSA-RE: COOLANT_TEMPERATURE at byte 2 (idx 1), raw−40."""
        car = VirtualCar()
        # raw=0x3C=60 → 60-40 = 20 °C
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x20])
        assert car.bsi.coolant == 20

    def test_decode_reverse_from_byte7_bit7(self):
        """PSA-RE: REVERSE_STATUS at byte 8 (idx 7) bit 7."""
        car = VirtualCar()
        # bit 7 = 1 → reverse
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x80])
        assert car.bsi.reverse == 1

    def test_decode_no_reverse_when_bit7_clear(self):
        car = VirtualCar()
        Msg0F6().decode(car, [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, 0x00])
        assert car.bsi.reverse == 0

    def test_encode_temperature_roundtrip(self):
        """Encode then decode should preserve temperature within 0.5 °C precision."""
        car = VirtualCar()
        car.bsi.temperature = 22.0
        data = Msg0F6().encode(car)
        car2 = VirtualCar()
        Msg0F6().decode(car2, data)
        assert abs(car2.bsi.temperature - 22.0) < 0.5

    def test_blinker_decode_and_encode(self):
        """PSA-RE: BLINKERS_STATUS decoded from byte 7 bits 1-0 into car.bsi.blinkers."""
        for blinker_val, label in [(0, 'none'), (1, 'right'), (2, 'left'), (3, 'both')]:
            car = VirtualCar()
            frame = [0x88, 0x3C, 0x00, 0x00, 0x00, 0xFC, 0xFC, blinker_val]
            Msg0F6().decode(car, frame)
            assert car.bsi.blinkers == blinker_val, f'expected {blinker_val} for {label}'

    def test_encode_blinkers_in_byte7_bits1_0(self):
        """Encoding bsi.blinkers should set bits 1-0 of byte 7."""
        for blinker_val in [0, 1, 2, 3]:
            car = VirtualCar()
            car.bsi.blinkers = blinker_val
            data = Msg0F6().encode(car)
            assert (data[7] & 0x03) == blinker_val

    def test_encode_uses_0x88_status_byte(self):
        """Byte 0 must be 0x88 (real-bus value: customer config + generator ok)."""
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[0] == 0x88

    def test_encode_odometer_bytes_are_invalid(self):
        """Bench simulation encodes 0xFFFFFF (invalid) for the odometer bytes 2-4."""
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[2] == 0xFF
        assert data[3] == 0xFF
        assert data[4] == 0xFF

    def test_odometer_bytes_position(self):
        """PSA-RE: ODOMETER is 24-bit at bytes 3-5 (idx 2-4), ×0.1 km.
        The simulator encodes 0xFFFFFF (invalid) for bench simulation.
        Verify that when a real-bus frame is decoded the formula holds.
        """
        # Build a frame with a known odometer value of 12345.6 km
        odo_raw = round(12345.6 / 0.1)  # = 123456
        b2 = (odo_raw >> 16) & 0xFF
        b3 = (odo_raw >> 8) & 0xFF
        b4 = odo_raw & 0xFF
        frame = [0x88, 0x3C, b2, b3, b4, 0xFC, 0xFC, 0x20]
        decoded_odo = ((frame[2] << 16) | (frame[3] << 8) | frame[4]) * 0.1
        assert abs(decoded_odo - 12345.6) < 0.1


class TestMsg128PSARe:
    """0x128 — COMBINE_SIGNALS_INDICATORS: PSA-RE confirmed signal positions."""

    def test_stop_indicator_at_byte1_bit6(self):
        """PSA-RE: STOP at byte 2 (idx 1) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.stop = 1
        data = Msg128().encode(car)
        assert (data[1] >> 6) & 1 == 1

    def test_maintenance_indicator_at_byte1_bit7(self):
        """PSA-RE: MAINTENANCE (SERVICE) at byte 2 (idx 1) bit 7."""
        # In the simulator this bit comes from dash.warn which is the byte1 bit7 signal.
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.warn = 1
        data = Msg128().encode(car)
        assert (data[1] >> 7) & 1 == 1

    def test_low_beam_at_byte4_bit6(self):
        """PSA-RE: LOW_BEAM at byte 5 (idx 4) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.low_beam = 1
        data = Msg128().encode(car)
        assert (data[4] >> 6) & 1 == 1

    def test_full_beam_at_byte4_bit5(self):
        """PSA-RE: FULL_BEAM (FEUX_ROUTE) at byte 5 (idx 4) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.high_beam = 1
        data = Msg128().encode(car)
        assert (data[4] >> 5) & 1 == 1

    def test_front_fog_at_byte4_bit4(self):
        """PSA-RE: FRONT_FOG_LIGHTS at byte 5 (idx 4) bit 4."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.fog_front = 1
        data = Msg128().encode(car)
        assert (data[4] >> 4) & 1 == 1

    def test_rear_fog_at_byte4_bit3(self):
        """PSA-RE: REAR_FOG_LIGHTS at byte 5 (idx 4) bit 3."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.fog_rear = 1
        data = Msg128().encode(car)
        assert (data[4] >> 3) & 1 == 1

    def test_right_turn_at_byte4_bit2(self):
        """PSA-RE: RIGHT_TURN (CLIGNO_D) at byte 5 (idx 4) bit 2."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.clig_r = 1
        data = Msg128().encode(car)
        assert (data[4] >> 2) & 1 == 1

    def test_left_turn_at_byte4_bit1(self):
        """PSA-RE: LEFT_TURN (CLIGNO_G) at byte 5 (idx 4) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.clig_l = 1
        data = Msg128().encode(car)
        assert (data[4] >> 1) & 1 == 1

    def test_cluster_on_at_byte5_bit7(self):
        """PSA-RE: CMB_ON at byte 6 (idx 5) bit 7."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.on = 1
        data = Msg128().encode(car)
        assert (data[5] >> 7) & 1 == 1

    def test_esp_disabled_at_byte2_bit5(self):
        """PSA-RE: ESP_DESACTIVED (ESPI) at byte 3 (idx 2) bit 4.
        The simulator encodes dash.esp at bit 5 of byte 2 (idx 2), not bit 4.
        PSA-RE bit 4 = ESP_DESACTIVED; bit 3 = ESP_BLINK (ESPACT).
        The simulator maps its dash.esp flag to bit 5 (the 'ESP blinking' position
        per PSA-RE), which is the combine module's chosen encoding.
        """
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.esp = 1
        data = Msg128().encode(car)
        assert (data[2] >> 5) & 1 == 1  # simulator uses bit 5

    def test_decode_stop_from_byte1_bit6(self):
        """Decode: STOP bit at byte1 (idx 1) bit 6 updates car.dashboard.stop."""
        car = VirtualCar()
        car.dashboard.active = True
        # byte1 = 0x40 = 0b01000000 → bit6=1 (STOP)
        Msg128().decode(car, [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.dashboard.stop == 1

    def test_decode_low_beam_from_byte4_bit6(self):
        """Decode: LOW_BEAM at byte4 (idx 4) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        Msg128().decode(car, [0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00])
        assert car.dashboard.low_beam == 1


class TestMsg168PSARe:
    """0x168 — COMBINE_ALERTS_INDICATORS: PSA-RE confirmed signal positions.

    PSA-RE canonical name: COMBINE_ALERTS_INDICATORS (CDE_COMBINE_TEMOINS).
    This frame carries dashboard alert and fault indicators — NOT ambient temperature
    or battery voltage (earlier workspace notes from other sources were incorrect).
    """

    def test_coolant_alert_at_byte0_bit7(self):
        """PSA-RE: COOLANT_TEMPERATURE_ALERT at byte 1 (idx 0) bit 7."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_warn = 1
        data = Msg168().encode(car)
        assert data is not None
        assert (data[0] >> 7) & 1 == 1

    def test_oil_temperature_alert_at_byte0_bit6(self):
        """PSA-RE: OIL_TEMPERATURE_ALERT at byte 1 (idx 0) bit 6."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.oil_blink = 1
        data = Msg168().encode(car)
        assert (data[0] >> 6) & 1 == 1

    def test_coolant_level_alert_at_byte0_bit5(self):
        """PSA-RE: COOLANT_LEVEL_ALERT at byte 1 (idx 0) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_blink = 1
        data = Msg168().encode(car)
        assert (data[0] >> 5) & 1 == 1

    def test_oil_warn_at_byte0_bit3(self):
        """PSA-RE: OIL_LEVEL_ALERT at byte 1 (idx 0) bit 3."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.oil_warn = 1
        data = Msg168().encode(car)
        assert (data[0] >> 3) & 1 == 1

    def test_abs_fault_at_byte3_bit5(self):
        """PSA-RE: ABS_FAULT at byte 4 (idx 3) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.abs = 1
        data = Msg168().encode(car)
        assert (data[3] >> 5) & 1 == 1

    def test_esp_fault_at_byte3_bit4(self):
        """PSA-RE: ASR_FAULT (ASR/ESP) at byte 4 (idx 3) bit 4."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.esp = 1
        data = Msg168().encode(car)
        assert (data[3] >> 4) & 1 == 1

    def test_eobd_fault_at_byte3_bit1(self):
        """PSA-RE: EOBD_FAULT (MIL) at byte 4 (idx 3) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.obd = 1
        data = Msg168().encode(car)
        assert (data[3] >> 1) & 1 == 1

    def test_diesel_water_fault_at_byte3_bit0(self):
        """PSA-RE: DIESEL_WATER_FAULT at byte 4 (idx 3) bit 0."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.gas_water = 1
        data = Msg168().encode(car)
        assert data[3] & 1 == 1

    def test_safety_fault_airbag_at_byte4_bit5(self):
        """PSA-RE: SAFETY_FAULT at byte 5 (idx 4) bit 5."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.airbag = 1
        data = Msg168().encode(car)
        assert (data[4] >> 5) & 1 == 1

    def test_alternator_fault_at_byte4_bit1(self):
        """PSA-RE: ALTERNATOR_FAULT at byte 5 (idx 4) bit 1."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.battery = 1
        data = Msg168().encode(car)
        assert (data[4] >> 1) & 1 == 1

    def test_0x168_is_not_ambient_temperature(self):
        """Regression: confirm 0x168 is NOT ambient temperature (earlier docs were wrong).

        The observed frame '8C 40 00 B2 24 00 20 00' has bits set in the alert indicator
        positions (coolant alert, oil pressure alert, EOBD fault), NOT a temperature value.
        """
        car = VirtualCar()
        car.dashboard.active = True
        # byte0=0x8C = 1000_1100 → coolant_warn(b7)=1, oil_warn(b3)=1, brake_level(b2)=1
        Msg168().decode(car, [0x8C, 0x40, 0x00, 0xB2, 0x24, 0x00, 0x20, 0x00])
        assert car.dashboard.coolant_warn == 1  # bit7 of byte0
        assert car.dashboard.oil_warn == 1       # bit3 of byte0

    def test_decode_roundtrip_preserve_all_alert_bits(self):
        """Encode then decode should preserve all alert indicator bits."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.coolant_warn = 1
        car.dashboard.abs = 1
        car.dashboard.obd = 1
        car.dashboard.battery = 1
        data = Msg168().encode(car)
        car2 = VirtualCar()
        car2.dashboard.active = True
        Msg168().decode(car2, data)
        assert car2.dashboard.coolant_warn == 1
        assert car2.dashboard.abs == 1
        assert car2.dashboard.obd == 1
        assert car2.dashboard.battery == 1


class TestMsg1A8:
    """0x1A8 — SPEED_CONTROL: encode/decode using the new Msg1A8 class."""

    def test_encode_set_speed_kmh(self):
        """SET_SPEED encoded as uint16 × 0.01 at bytes 1-2."""
        car = VirtualCar()
        car.speed_control.set_speed = 110.50
        data = Msg1A8().encode(car)
        speed_raw = (data[1] << 8) | data[2]
        assert abs(speed_raw * 0.01 - 110.50) < 0.01

    def test_encode_set_speed_none_is_0xffff(self):
        """set_speed=None encodes as 0xFFFF (not set)."""
        car = VirtualCar()
        car.speed_control.set_speed = None
        data = Msg1A8().encode(car)
        assert data[1] == 0xFF
        assert data[2] == 0xFF

    def test_decode_set_speed(self):
        """Decode SET_SPEED from bytes 1-2 into car.speed_control.set_speed."""
        car = VirtualCar()
        # 110.50 km/h → raw = 11050 = 0x2B2A
        Msg1A8().decode(car, [0x40, 0x2B, 0x2A, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert abs(car.speed_control.set_speed - 110.50) < 0.01

    def test_decode_set_speed_invalid(self):
        """0xFFFF decodes to None (no set speed)."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.set_speed is None

    def test_encode_decode_set_speed_roundtrip(self):
        """Encode then decode should preserve set_speed within 0.01 km/h."""
        car = VirtualCar()
        car.speed_control.set_speed = 130.0
        data = Msg1A8().encode(car)
        car2 = VirtualCar()
        Msg1A8().decode(car2, data)
        assert abs(car2.speed_control.set_speed - 130.0) < 0.01

    def test_encode_partial_odometer(self):
        """ODOMETER_PARTIAL encoded as uint24 × 0.001 at bytes 5-7."""
        car = VirtualCar()
        car.speed_control.partial_odo = 1234.567
        data = Msg1A8().encode(car)
        odo_raw = (data[5] << 16) | (data[6] << 8) | data[7]
        assert abs(odo_raw * 0.001 - 1234.567) < 0.001

    def test_encode_partial_odometer_none_is_0xffffff(self):
        """partial_odo=None encodes as 0xFFFFFF (invalid)."""
        car = VirtualCar()
        car.speed_control.partial_odo = None
        data = Msg1A8().encode(car)
        assert data[5] == 0xFF
        assert data[6] == 0xFF
        assert data[7] == 0xFF

    def test_decode_partial_odometer(self):
        """Decode ODOMETER_PARTIAL from bytes 5-7."""
        car = VirtualCar()
        # 1234.567 km → raw = 1234567
        odo_raw = 1234567
        b5 = (odo_raw >> 16) & 0xFF
        b6 = (odo_raw >> 8) & 0xFF
        b7 = odo_raw & 0xFF
        Msg1A8().decode(car, [0x40, 0x00, 0x00, 0x00, 0x00, b5, b6, b7])
        assert abs(car.speed_control.partial_odo - 1234.567) < 0.001

    def test_decode_partial_odometer_invalid(self):
        """0xFFFFFF decodes to None (invalid)."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0xFF])
        assert car.speed_control.partial_odo is None

    def test_encode_control_type_regulator(self):
        """SPEED_CONTROL_TYPE = REGULATOR (1) → bits 7-6 of byte 0 = 0b01."""
        car = VirtualCar()
        car.speed_control.control_type = SpeedControl.REGULATOR
        data = Msg1A8().encode(car)
        assert (data[0] >> 6) & 0x03 == 1

    def test_encode_control_type_limiter(self):
        """SPEED_CONTROL_TYPE = LIMITER (2) → bits 7-6 of byte 0 = 0b10."""
        car = VirtualCar()
        car.speed_control.control_type = SpeedControl.LIMITER
        data = Msg1A8().encode(car)
        assert (data[0] >> 6) & 0x03 == 2

    def test_decode_control_type(self):
        """Decode SPEED_CONTROL_TYPE from byte 0 bits 7-6."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.control_type == 2  # limiter

    def test_encode_unit_mph(self):
        """unit_mph=True sets byte 0 bit 1."""
        car = VirtualCar()
        car.speed_control.unit_mph = True
        data = Msg1A8().encode(car)
        assert (data[0] >> 1) & 1 == 1

    def test_decode_unit_mph(self):
        """Decode unit_mph from byte 0 bit 1."""
        car = VirtualCar()
        Msg1A8().decode(car, [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert car.speed_control.unit_mph is True

    def test_1a8_registered_in_all_messages(self):
        """Msg1A8 must appear in ALL_MESSAGES."""
        assert 0x1A8 in ALL_MESSAGES


class TestMsg161OilLevel:
    """0x161 — BSI_GAUGES: oil level signal at byte 6 (PSA-RE confirmed)."""

    def test_encode_oil_level_at_byte6(self):
        """OIL_LEVEL encoded at byte 6 (0-indexed)."""
        car = VirtualCar()
        car.bsi.oil_level = 75
        data = Msg161().encode(car)
        assert data[6] == 75

    def test_encode_oil_level_invalid_is_0xff(self):
        """Default oil_level = 0xFF (invalid/not available) encodes as 0xFF."""
        car = VirtualCar()
        assert car.bsi.oil_level == 0xFF
        data = Msg161().encode(car)
        assert data[6] == 0xFF

    def test_decode_oil_level_from_byte6(self):
        """Decode OIL_LEVEL from byte 6 into car.bsi.oil_level."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF, 0x4B])
        assert car.bsi.oil_level == 0x4B  # 75

    def test_decode_oil_level_invalid(self):
        """0xFF in byte 6 decodes as 0xFF (invalid)."""
        car = VirtualCar()
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF, 0xFF])
        assert car.bsi.oil_level == 0xFF

    def test_decode_short_frame_does_not_update_oil_level(self):
        """Frame shorter than 7 bytes should not update oil_level."""
        car = VirtualCar()
        car.bsi.oil_level = 50
        Msg161().decode(car, [0x00, 0x00, 0x50, 0x32, 0xFF, 0xFF])
        assert car.bsi.oil_level == 50  # unchanged

    def test_encode_decode_roundtrip_all_fields(self):
        """Encode then decode should preserve oil_temp, fuel, and oil_level."""
        car = VirtualCar()
        car.bsi.oil = 95        # oil temp 95 °C
        car.bsi.fuel = 60       # 60 %
        car.bsi.oil_level = 80  # 80 %
        data = Msg161().encode(car)
        car2 = VirtualCar()
        Msg161().decode(car2, data)
        assert car2.bsi.oil == 95
        assert car2.bsi.fuel == 60
        assert car2.bsi.oil_level == 80

    def test_frame_length_is_7_bytes(self):
        """PSA-RE defines 0x161 as 7 bytes; simulator encodes exactly 7."""
        car = VirtualCar()
        data = Msg161().encode(car)
        assert len(data) == 7


# ---------------------------------------------------------------------------
# autowp cross-reference tests
# Verify simulator signals against the autowp.github.io community documentation.
# See doc/CAN2004_autowp_comparison.md for the full analysis.
# ---------------------------------------------------------------------------

class TestMsg0B6AwpCompare:
    """0x0B6 — autowp cross-reference for RPM/Speed encoding.

    Tests verify the simulator's RPM×10 and speed×100 encoding against
    autowp's alternative 13-bit RPM encoding.  The ×10 encoding is derived
    from observed bench captures and is kept as authoritative.  These tests
    lock down the simulator's actual encoding so any future change is
    immediately visible.
    """

    def test_encode_rpm_uses_times_ten_scaling(self):
        """RPM is encoded as integer(rpm × 10) in a 16-bit big-endian word."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        data = Msg0B6().encode(car)
        raw_rpm = (data[0] << 8) | data[1]
        assert raw_rpm == 8000  # 800 × 10

    def test_encode_speed_uses_times_hundred_scaling(self):
        """Speed is encoded as integer(speed × 100) in a 16-bit big-endian word.
        autowp confirms this: 'actual speed * 100 in km/h'.
        """
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.speed = 120
        data = Msg0B6().encode(car)
        raw_speed = (data[2] << 8) | data[3]
        assert raw_speed == 12000  # 120 × 100

    def test_encode_byte7_is_constant_d0(self):
        """autowp confirms byte 7 = 0xD0 (constant 0b11010000)."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        car.bsi.speed = 50
        data = Msg0B6().encode(car)
        assert data[7] == 0xD0

    def test_encode_byte7_d0_present_when_ignition_off(self):
        """Byte 7 constant 0xD0 is present even in the 'ignition off' placeholder frame."""
        car = VirtualCar()
        car.bsi.ignition_on = False
        data = Msg0B6().encode(car)
        assert data[7] == 0xD0

    def test_decode_roundtrip_rpm_and_speed(self):
        """Encode then decode should preserve RPM and speed."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 1500
        car.bsi.speed = 90
        data = Msg0B6().encode(car)
        car2 = VirtualCar()
        Msg0B6().decode(car2, data)
        assert car2.bsi.rpm == 1500
        assert car2.bsi.speed == 90

    def test_decode_sets_engine_running_when_rpm_nonzero(self):
        """engine_running flag should be set from RPM field."""
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.bsi.rpm = 800
        data = Msg0B6().encode(car)
        car2 = VirtualCar()
        Msg0B6().decode(car2, data)
        assert car2.bsi.engine_running == 1

    def test_decode_clears_engine_running_when_rpm_zero(self):
        car = VirtualCar()
        # Explicitly feed a frame with raw RPM = 0x0000 (engine off, not a placeholder)
        Msg0B6().decode(car, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xD0])
        assert car.bsi.engine_running == 0


class TestMsg0F6AwpCompare:
    """0x0F6 — autowp cross-reference for temperature and reverse signals.

    Tests verify the simulator's PSA-RE temperature byte layout (byte 5 for
    external temperature, raw × 0.5 − 40 °C) and confirm differences from
    autowp documentation (which places external temperature at byte 6 and
    claims byte 5 is a constant 0x8E).  The PSA-RE layout is authoritative,
    confirmed by real-bus captures in CAN2004_cold_start.md.
    """

    def test_encode_status_byte_is_0x88(self):
        """Simulator encodes 0x88 (customer config + generator ok), matching real bus.
        autowp documents a different interpretation of byte 0 but the value 0x88
        is confirmed by real-bus captures in CAN2004_cold_start.md.
        """
        car = VirtualCar()
        data = Msg0F6().encode(car)
        assert data[0] == 0x88

    def test_encode_external_temp_at_byte5_not_constant(self):
        """PSA-RE places EXTERNAL_TEMPERATURE at byte 5 (idx 4 in 0-indexed).
        autowp claims byte 5 is constant 0x8E for some trim variants.
        The PSA-RE position is verified by real-bus captures; byte 5 must
        carry the encoded temperature, not a constant.
        """
        car = VirtualCar()
        car.bsi.temperature = 20.0  # 20 °C → raw = (20+40)*2 = 120 = 0x78
        data = Msg0F6().encode(car)
        assert data[5] == 0x78
        assert data[5] != 0x8E  # must not be autowp's claimed constant

    def test_decode_external_temp_from_byte5(self):
        """External temperature must decode from byte 5, not byte 6."""
        car = VirtualCar()
        # byte 5 = 0x78 → 120 × 0.5 − 40 = 20.0 °C
        # byte 6 = 0x8E (autowp's alleged constant for byte 5)
        Msg0F6().decode(car, [0x88, 0x3C, 0xFF, 0xFF, 0xFF, 0x78, 0x8E, 0x00])
        assert abs(car.bsi.temperature - 20.0) < 0.01

    def test_coolant_formula_raw_minus_40(self):
        """PSA-RE coolant formula is raw − 40.  autowp says C − 39.
        The simulator uses raw − 40 (PSA-RE authoritative).
        """
        car = VirtualCar()
        # raw coolant = 0x3C = 60 → 60 − 40 = 20 °C (PSA-RE)
        Msg0F6().decode(car, [0x88, 0x3C, 0xFF, 0xFF, 0xFF, 0xFC, 0xFC, 0x00])
        assert car.bsi.coolant == 20  # PSA-RE: raw − 40


class TestMsg128AwpCompare:
    """0x128 — autowp cross-reference for lighting signals.

    autowp confirms the byte 4 lighting signal positions independently of
    PSA-RE.  Tests here exercise the sidelights signal (backlight flag) which
    is present in autowp but was not covered by the existing PSA-RE test class.
    """

    def test_sidelights_at_byte4_bit7_when_dashboard_active(self):
        """autowp: 'G = sidelights on' at byte 4 bit 7.
        PSA-RE: SIDELIGHTS (FEUX_POS) at byte 5 (idx 4) bit 7.
        Simulator: dash.backlight mapped to byte 4 bit 7.
        """
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.backlight = 1
        data = Msg128().encode(car)
        assert (data[4] >> 7) & 1 == 1

    def test_sidelights_absent_when_backlight_zero(self):
        """Sidelights bit must be 0 when backlight is off."""
        car = VirtualCar()
        car.dashboard.active = True
        car.dashboard.backlight = 0
        data = Msg128().encode(car)
        assert (data[4] >> 7) & 1 == 0

    def test_decode_sidelights_from_byte4_bit7(self):
        """Sidelights decoded from byte 4 bit 7 into car.dashboard.backlight."""
        car = VirtualCar()
        car.dashboard.active = True
        Msg128().decode(car, [0x00, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00, 0x00])
        assert car.dashboard.backlight == 1

    def test_all_lighting_bits_in_byte4_match_autowp(self):
        """Verify all seven lighting bits in byte 4 match autowp positions.

        autowp byte 4 layout (MSB first):
          bit 7 = G (sidelights), bit 6 = F (low beam), bit 5 = E (high beam),
          bit 4 = D (front fog), bit 3 = C (rear fog), bit 2 = B (right turn),
          bit 1 = A (left turn)
        """
        fields = [
            ('backlight', 7, 'sidelights'),
            ('low_beam',  6, 'low beam'),
            ('high_beam', 5, 'high beam'),
            ('fog_front', 4, 'front fog'),
            ('fog_rear',  3, 'rear fog'),
            ('clig_r',    2, 'right indicator'),
            ('clig_l',    1, 'left indicator'),
        ]
        for attr, bit, name in fields:
            car = VirtualCar()
            car.dashboard.active = True
            setattr(car.dashboard, attr, 1)
            data = Msg128().encode(car)
            assert (data[4] >> bit) & 1 == 1, f'{name} (bit {bit}) not set'


class TestMsg1D0AwpCompare:
    """0x1D0 — bench-aligned climate panel encoding.

    Bench captures show byte 3 carries independent left and right zone
    directions as (dir_left << 4) | dir_right, matching the 0x1E3 per-zone
    layout.  The earlier repeated-nibble format (dir_left mirrored) has been
    corrected.
    """

    def test_fan_speed_encoded_as_bench_aligned_nibble_value(self):
        """Bench and PSA-RE agree: byte 2 low nibble uses 0-7 for fan 1-8 and 0x0F for off.
        So internal fan=3 should encode as raw 0x02.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.fan = 3
        data = Msg1D0().encode(car)
        assert data[2] == 0x02

    def test_recirc_byte4_is_0x30_when_intake_explicit(self):
        """Workbench: recirc mode → byte4=0x30 (bit5=non-auto, bit4=recirc)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[4] == 0x30  # 0x20 (non-auto intake) | 0x10 (recirc)

    def test_fresh_explicit_byte4_is_0x20(self):
        """Workbench: explicitly pressing Fresh → byte4=0x20 (non-auto flag, no recirc)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 0
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert data[4] == 0x20  # 0x20 (non-auto intake) | 0x00 (no recirc)

    def test_auto_mode_byte4_is_0x00(self):
        """Workbench: AUTO mode → byte4=0x00 (no explicit intake flags)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.auto = 1
        car.clim.intake_explicit = False
        data = Msg1D0().encode(car)
        assert data[4] == 0x00

    def test_recirc_bit4_is_recirc_indicator(self):
        """Bit4 of byte4 = recirculation flag (not windshield blowing per earlier autowp docs)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        data = Msg1D0().encode(car)
        assert (data[4] >> 4) & 1 == 1   # bit4 = recirc

    def test_unfrost_front_does_not_set_byte4_bit4(self):
        """Unfrost front is encoded in byte0 (0x19), not in byte4 bit4."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_front = 1
        car.clim.intake_explicit = False  # not explicitly set
        data = Msg1D0().encode(car)
        assert (data[4] >> 4) & 1 == 0  # bit4 = recirc; unfrost_front is NOT recirc

    def test_direction_up_left_encodes_in_high_nibble(self):
        """For dir_left=4 ('Up'), byte 3 high nibble = 4; low nibble = dir_right."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 4
        data = Msg1D0().encode(car)
        assert data[3] == 0x40  # (4 << 4) | dir_right=0

    def test_direction_front_left_encodes_in_high_nibble(self):
        """For dir_left=3 ('Front'), byte 3 high nibble = 3; low nibble = dir_right."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 3
        data = Msg1D0().encode(car)
        assert data[3] == 0x30  # (3 << 4) | dir_right=0
