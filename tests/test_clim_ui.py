"""Tests for the Climate and Doors module UI helpers."""
import importlib
import types

import pytest

from car_state import VirtualCar
from conftest import DummyWidget
from modules.clim import Clim as ClimModule

DoorsModule = importlib.import_module('modules.doors').Doors


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

    def test_updating_ui_guard_suppresses_airflow_mode_callback(self):
        """_update_options sets _updating_ui=True so programmatic widget state
        changes (e.g. when exiting AUTO via a direction button) do not re-enter
        on_airflow_mode and incorrectly trigger intake_notify or reset clim.ac."""
        widget = self._make_clim_widget(ignition_on=True)
        widget._updating_ui = True
        widget.runner.car.clim.recycle = 0
        widget.runner.car.clim.intake_notify = False
        widget.runner.car.clim.ac = 1
        widget.on_airflow_mode('recirc', 'down')
        # Guard active → none of the state should have changed
        assert widget.runner.car.clim.recycle == 0
        assert widget.runner.car.clim.intake_notify is False
        assert widget.runner.car.clim.ac == 1

    def test_on_dir_from_auto_in_mono_does_not_set_intake_notify(self):
        """Pressing a direction button while in AUTO (mono mode) exits AUTO but
        must NOT set intake_notify — no MFD popup should appear for direction changes.
        DummyWidget does not fire on_state callbacks, so this directly verifies that
        on_dir itself does not set intake_notify."""
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update(self._make_dir_ids())
        widget.runner.car.clim.auto = 1
        widget.runner.car.clim.dual = 0
        widget.runner.car.clim.intake_notify = False
        widget.on_dir(0, 0x04, 'down')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.dir_left == 0x04
        assert widget.runner.car.clim.intake_notify is False

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
        # A/C user preference is preserved; ac=0 is only encoded in the CAN frame
        # by Msg1E3 (workbench-verified: 0x1E3 byte0 ac bit = 0 for recirc).
        assert widget.runner.car.clim.ac == 1
        assert widget.ids['intake_recycle'].state == 'down'
        assert widget.ids['mode_recirc'].state == 'down'
        # Workbench: one-shot notification bit triggers MFD popup.
        assert widget.runner.car.clim.intake_notify is True

    def test_on_airflow_mode_fresh(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.ac = 1  # start with A/C on
        widget.runner.car.clim.recycle = 1
        widget.on_airflow_mode('fresh', 'down')
        assert widget.runner.car.clim.auto == 0
        assert widget.runner.car.clim.unfrost_front == 0
        assert widget.runner.car.clim.recycle == 0
        # A/C user preference is preserved; ac=0 is only encoded in the CAN frame
        # by Msg1E3 (workbench-verified: 0x1E3 byte0 ac bit = 0 for explicit fresh).
        assert widget.runner.car.clim.ac == 1
        assert widget.ids['mode_fresh'].state == 'down'
        assert widget.ids['mode_recirc'].state == 'normal'
        # Workbench: one-shot notification bit triggers MFD popup.
        assert widget.runner.car.clim.intake_notify is True

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

        assert sent[-1] == (0x1A1, [0x00, 0xDE, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00])

    def test_send_popup_show_contains_door_bitmap(self):
        widget, sent = self._make_doors_widget()
        widget._doors.front_left = 1
        widget._doors.boot = 1

        widget._send_popup_show(0)

        assert sent[-1] == (0x1A1, [0x80, 0x0B, 0xC6, 0x48, 0x00, 0x00, 0x00, 0x00])

    def test_send_popup_clear_uses_idle_baseline_frame(self):
        widget, sent = self._make_doors_widget()
        widget._doors.display_active = True
        widget._doors.popup_msg_id = 0xDE

        widget._send_popup_clear(0)

        assert sent[-1] == (0x1A1, [0x00, 0x8B, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert widget._doors.display_active is False


