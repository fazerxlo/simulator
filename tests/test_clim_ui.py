"""Tests for the Climate module UI helpers."""
import importlib
import types

import pytest

from car_state import VirtualCar
from conftest import DummyWidget
from modules.clim import Clim as ClimModule
DoorsModule = importlib.import_module('modules.doors').Doors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeRunner:
    """Minimal runner stub that satisfies ClimModule.__init__."""

    def __init__(self):
        self.car = VirtualCar()


def _make_clim():
    """Create a fully initialised ClimModule wired to a fake runner."""
    runner = _FakeRunner()
    # Ensure ignition is on so that callbacks accept input.
    runner.car.bsi.ignition_on = True
    # The Kivy stub's TabbedPanelItem.__init__ sets self.ids, but the Clim
    # module calls super(TabbedPanelItem, self).__init__() which skips it.
    # Patch __init__ to pre-seed ids before the real body runs.
    _orig_init = ClimModule.__init__

    def _patched_init(self, runner_arg, **kwargs):
        self.ids = {}
        _orig_init(self, runner_arg, **kwargs)

    ClimModule.__init__ = _patched_init
    try:
        clim = ClimModule(runner)
    finally:
        ClimModule.__init__ = _orig_init
    # Populate the ids dict with DummyWidget stubs for every widget id
    # referenced by the production code.
    _ensure_ids(clim)
    return clim


def _ensure_ids(clim):
    """Make sure every widget id the module references exists."""
    needed = [
        'slider_fan', 'cur_fan',
        'cur_temp0', 'cur_temp1',
        'clim_on', 'ac_on', 'dual', 'unfrost_rear',
        'mode_auto', 'mode_unfrost_front', 'mode_recirc', 'mode_fresh',
        'auto', 'intake_fresh', 'intake_recycle', 'recycle', 'unfrost_front',
        # direction grid buttons
        'left_auto', 'left_fr', 'left_up', 'left_ud',
        'left_down', 'left_fd', 'left_all', 'left_fast',
        'right_auto', 'right_fr', 'right_up', 'right_ud',
        'right_down', 'right_fd', 'right_all', 'right_fast',
    ]
    for wid in needed:
        if wid not in clim.ids:
            clim.ids[wid] = DummyWidget()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestClimUiHelpers:
    """Climate module UI helper tests."""

    # -- Constructor defaults ------------------------------------------------

    def test_init_sets_enabled(self):
        clim = _make_clim()
        assert clim._clim.enabled is True

    def test_init_fan(self):
        clim = _make_clim()
        assert clim._clim.fan == 2

    def test_init_auto(self):
        clim = _make_clim()
        assert clim._clim.auto == 1

    def test_init_ac(self):
        clim = _make_clim()
        assert clim._clim.ac == 1

    def test_init_dual(self):
        clim = _make_clim()
        assert clim._clim.dual == 0

    def test_init_temps(self):
        clim = _make_clim()
        assert clim._clim.temp_left == 11
        assert clim._clim.temp_right == 11

    def test_init_directions(self):
        clim = _make_clim()
        assert clim._clim.dir_left == 0
        assert clim._clim.dir_right == 0

    def test_init_unfrost(self):
        clim = _make_clim()
        assert clim._clim.unfrost_front == 0
        assert clim._clim.unfrost_rear == 0

    def test_init_recycle(self):
        clim = _make_clim()
        assert clim._clim.recycle == 0

    def test_init_bits(self):
        clim = _make_clim()
        assert clim._clim.bits == 0

    def test_temp_disp_length(self):
        clim = _make_clim()
        assert len(clim.temp_disp) == 23

    def test_temp_disp_boundaries(self):
        clim = _make_clim()
        assert clim.temp_disp[0] == 'MIN'
        assert clim.temp_disp[-1] == 'HI'

    # -- _normalize_ui_fan ---------------------------------------------------

    def test_normalize_ui_fan_valid(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(5) == 5

    def test_normalize_ui_fan_zero(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(0) == 0

    def test_normalize_ui_fan_max(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(8) == 8

    def test_normalize_ui_fan_over(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(9) == clim._clim.fan

    def test_normalize_ui_fan_negative(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(-1) == clim._clim.fan

    def test_normalize_ui_fan_none(self):
        clim = _make_clim()
        assert clim._normalize_ui_fan(None) == clim._clim.fan

    # -- _decode_can_fan -----------------------------------------------------

    def test_decode_can_fan_0x0F_is_zero(self):
        clim = _make_clim()
        assert clim._decode_can_fan(0x0F) == 0

    def test_decode_can_fan_0_is_1(self):
        clim = _make_clim()
        assert clim._decode_can_fan(0) == 1

    def test_decode_can_fan_7_is_8(self):
        clim = _make_clim()
        assert clim._decode_can_fan(7) == 8

    def test_decode_can_fan_none(self):
        clim = _make_clim()
        assert clim._decode_can_fan(None) == clim._clim.fan

    def test_decode_can_fan_out_of_range(self):
        clim = _make_clim()
        assert clim._decode_can_fan(0x0E) == clim._clim.fan

    # -- _normalize_dir ------------------------------------------------------

    def test_normalize_dir_zero(self):
        clim = _make_clim()
        assert clim._normalize_dir(0) == 0

    def test_normalize_dir_low_nibble(self):
        clim = _make_clim()
        assert clim._normalize_dir(0x05) == 5

    def test_normalize_dir_high_nibble(self):
        clim = _make_clim()
        assert clim._normalize_dir(0x50) == 5

    def test_normalize_dir_none(self):
        clim = _make_clim()
        assert clim._normalize_dir(None) == 0

    # -- _temp_label ---------------------------------------------------------

    def test_temp_label_min(self):
        clim = _make_clim()
        assert clim._temp_label(0) == 'MIN'

    def test_temp_label_hi(self):
        clim = _make_clim()
        assert clim._temp_label(22) == 'HI'

    def test_temp_label_mid(self):
        clim = _make_clim()
        assert clim._temp_label(9) == '20'

    def test_temp_label_out_of_range(self):
        clim = _make_clim()
        assert clim._temp_label(99) == '99'

    # -- _update_fan ---------------------------------------------------------

    def test_update_fan_sets_state(self):
        clim = _make_clim()
        clim._update_fan(5)
        assert clim._clim.fan == 5

    def test_update_fan_sets_slider(self):
        clim = _make_clim()
        clim._update_fan(4)
        assert clim.ids['slider_fan'].value == 4

    def test_update_fan_sets_label(self):
        clim = _make_clim()
        clim._update_fan(3)
        assert clim.ids['cur_fan'].text == 'Fan: 3'

    # -- _update_temps -------------------------------------------------------

    def test_update_temps_left(self):
        clim = _make_clim()
        clim._clim.temp_left = 5
        clim._update_temps()
        assert '18' in clim.ids['cur_temp0'].text

    def test_update_temps_right(self):
        clim = _make_clim()
        clim._clim.temp_right = 0
        clim._update_temps()
        assert 'MIN' in clim.ids['cur_temp1'].text

    # -- _get_airflow_mode ---------------------------------------------------

    def test_airflow_mode_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        assert clim._get_airflow_mode() == 'auto'

    def test_airflow_mode_unfrost(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.unfrost_front = 1
        assert clim._get_airflow_mode() == 'unfrost_front'

    def test_airflow_mode_recirc(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.unfrost_front = 0
        clim._clim.recycle = 1
        assert clim._get_airflow_mode() == 'recirc'

    def test_airflow_mode_fresh(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.unfrost_front = 0
        clim._clim.recycle = 0
        assert clim._get_airflow_mode() == 'fresh'

    # -- _update_options (widget state sync) ---------------------------------

    def test_update_options_clim_on_enabled(self):
        clim = _make_clim()
        clim._clim.enabled = True
        clim._update_options()
        assert clim.ids['clim_on'].state == 'down'

    def test_update_options_clim_on_disabled(self):
        clim = _make_clim()
        clim._clim.enabled = False
        clim._update_options()
        assert clim.ids['clim_on'].state == 'normal'

    def test_update_options_ac_on(self):
        clim = _make_clim()
        clim._clim.ac = 1
        clim._update_options()
        assert clim.ids['ac_on'].state == 'down'

    def test_update_options_ac_off(self):
        clim = _make_clim()
        clim._clim.ac = 0
        clim._update_options()
        assert clim.ids['ac_on'].state == 'normal'

    def test_update_options_dual_on(self):
        clim = _make_clim()
        clim._clim.dual = 1
        clim._update_options()
        assert clim.ids['dual'].state == 'down'

    def test_update_options_dual_off(self):
        clim = _make_clim()
        clim._clim.dual = 0
        clim._update_options()
        assert clim.ids['dual'].state == 'normal'

    def test_update_options_mode_auto_selected(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim._update_options()
        assert clim.ids['mode_auto'].state == 'down'
        assert clim.ids['mode_recirc'].state == 'normal'

    def test_update_options_mode_recirc_selected(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.recycle = 1
        clim._clim.unfrost_front = 0
        clim._update_options()
        assert clim.ids['mode_recirc'].state == 'down'
        assert clim.ids['mode_auto'].state == 'normal'

    def test_update_options_mode_fresh_selected(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.recycle = 0
        clim._clim.unfrost_front = 0
        clim._update_options()
        assert clim.ids['mode_fresh'].state == 'down'
        assert clim.ids['mode_auto'].state == 'normal'

    def test_update_options_mode_unfrost_front_selected(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.unfrost_front = 1
        clim._update_options()
        assert clim.ids['mode_unfrost_front'].state == 'down'
        assert clim.ids['mode_auto'].state == 'normal'

    def test_update_options_unfrost_rear(self):
        clim = _make_clim()
        clim._clim.unfrost_rear = 1
        clim._update_options()
        assert clim.ids['unfrost_rear'].state == 'down'

    def test_update_options_backward_compat_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim._update_options()
        assert clim.ids['auto'].state == 'down'

    def test_update_options_backward_compat_recycle(self):
        clim = _make_clim()
        clim._clim.recycle = 1
        clim._update_options()
        assert clim.ids['recycle'].state == 'down'
        assert clim.ids['intake_recycle'].state == 'down'
        assert clim.ids['intake_fresh'].state == 'normal'

    def test_update_options_backward_compat_fresh(self):
        clim = _make_clim()
        clim._clim.recycle = 0
        clim._update_options()
        assert clim.ids['intake_fresh'].state == 'down'
        assert clim.ids['intake_recycle'].state == 'normal'

    # -- _update_dir_buttons -------------------------------------------------

    def test_dir_buttons_auto_mode(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim._update_dir_buttons()
        assert clim.ids['left_auto'].state == 'down'
        assert clim.ids['right_auto'].state == 'down'
        assert clim.ids['left_up'].state == 'normal'

    def test_dir_buttons_manual_left(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dir_left = 0x04  # up
        clim._update_dir_buttons()
        assert clim.ids['left_up'].state == 'down'
        assert clim.ids['left_auto'].state == 'normal'

    def test_dir_buttons_manual_right(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dir_right = 0x02  # down
        clim._update_dir_buttons()
        assert clim.ids['right_down'].state == 'down'
        assert clim.ids['right_auto'].state == 'normal'

    # -- on_dir --------------------------------------------------------------

    def test_on_dir_left_sets_direction(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim.on_dir(0, 0x04)
        assert clim._clim.dir_left == 0x04

    def test_on_dir_left_mirrors_right_in_mono(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dual = 0
        clim.on_dir(0, 0x03)
        assert clim._clim.dir_right == 0x03

    def test_on_dir_left_no_mirror_in_dual(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dual = 1
        clim._clim.dir_right = 0x02
        clim.on_dir(0, 0x05)
        assert clim._clim.dir_left == 0x05
        assert clim._clim.dir_right == 0x02

    def test_on_dir_right_activates_dual(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dual = 0
        clim._clim.dir_left = 0x04
        clim.on_dir(1, 0x02)
        assert clim._clim.dual == 1
        assert clim._clim.dir_right == 0x02

    def test_on_dir_right_same_as_left_no_dual(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim._clim.dual = 0
        clim._clim.dir_left = 0x04
        clim.on_dir(1, 0x04)
        assert clim._clim.dual == 0

    def test_on_dir_exits_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim.on_dir(0, 0x04)
        assert clim._clim.auto == 0

    def test_on_dir_auto_dir_stays_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim.on_dir(0, 0x00)
        assert clim._clim.auto == 1

    def test_on_dir_ignition_off_no_change(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.dir_left = 0x00
        clim.on_dir(0, 0x04)
        assert clim._clim.dir_left == 0x00

    def test_on_dir_state_not_down_no_change(self):
        clim = _make_clim()
        clim._clim.dir_left = 0x00
        clim.on_dir(0, 0x04, state='normal')
        assert clim._clim.dir_left == 0x00

    # -- on_clim_on ----------------------------------------------------------

    def test_on_clim_on_enables(self):
        clim = _make_clim()
        clim._clim.enabled = False
        clim.on_clim_on('down')
        assert clim._clim.enabled is True

    def test_on_clim_on_disables(self):
        clim = _make_clim()
        clim._clim.enabled = True
        clim.on_clim_on('normal')
        assert clim._clim.enabled is False

    def test_on_clim_on_disable_resets_fan(self):
        clim = _make_clim()
        clim._clim.fan = 5
        clim.on_clim_on('normal')
        assert clim._clim.fan == 0

    def test_on_clim_on_disable_resets_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim.on_clim_on('normal')
        assert clim._clim.auto == 0

    def test_on_clim_on_guard_flag(self):
        clim = _make_clim()
        clim._updating_ui = True
        original = clim._clim.enabled
        clim.on_clim_on('normal')
        assert clim._clim.enabled == original
        clim._updating_ui = False

    # -- on_ac ---------------------------------------------------------------

    def test_on_ac_enable(self):
        clim = _make_clim()
        clim._clim.ac = 0
        clim.on_ac('down')
        assert clim._clim.ac == 1

    def test_on_ac_disable(self):
        clim = _make_clim()
        clim._clim.ac = 1
        clim.on_ac('normal')
        assert clim._clim.ac == 0

    def test_on_ac_disable_exits_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim._clim.ac = 1
        clim.on_ac('normal')
        assert clim._clim.auto == 0

    def test_on_ac_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        original_ac = clim._clim.ac
        clim.on_ac('normal')
        assert clim._clim.ac == original_ac

    def test_on_ac_guard_flag(self):
        clim = _make_clim()
        clim._updating_ui = True
        original_ac = clim._clim.ac
        clim.on_ac('normal')
        assert clim._clim.ac == original_ac
        clim._updating_ui = False

    # -- on_airflow_mode -----------------------------------------------------

    def test_airflow_mode_auto_sets_flags(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim.on_airflow_mode('auto')
        assert clim._clim.auto == 1
        assert clim._clim.unfrost_front == 0
        assert clim._clim.recycle == 0

    def test_airflow_mode_auto_resets_dirs(self):
        clim = _make_clim()
        clim._clim.dir_left = 0x04
        clim._clim.dir_right = 0x03
        clim.on_airflow_mode('auto')
        assert clim._clim.dir_left == 0x00
        assert clim._clim.dir_right == 0x00

    def test_airflow_mode_auto_sets_ac_on(self):
        clim = _make_clim()
        clim._clim.ac = 0
        clim.on_airflow_mode('auto')
        assert clim._clim.ac == 1

    def test_airflow_mode_unfrost_front(self):
        clim = _make_clim()
        clim.on_airflow_mode('unfrost_front')
        assert clim._clim.unfrost_front == 1
        assert clim._clim.auto == 0
        assert clim._clim.recycle == 0

    def test_airflow_mode_recirc(self):
        clim = _make_clim()
        clim.on_airflow_mode('recirc')
        assert clim._clim.recycle == 1
        assert clim._clim.auto == 0
        assert clim._clim.unfrost_front == 0

    def test_airflow_mode_fresh(self):
        clim = _make_clim()
        clim.on_airflow_mode('fresh')
        assert clim._clim.auto == 0
        assert clim._clim.recycle == 0
        assert clim._clim.unfrost_front == 0

    def test_airflow_mode_recirc_sets_intake_notify(self):
        clim = _make_clim()
        clim._clim.intake_notify = False
        clim.on_airflow_mode('recirc')
        assert clim._clim.intake_notify is True

    def test_airflow_mode_fresh_sets_intake_notify(self):
        clim = _make_clim()
        clim._clim.intake_notify = False
        clim.on_airflow_mode('fresh')
        assert clim._clim.intake_notify is True

    def test_airflow_mode_auto_clears_intake_explicit(self):
        clim = _make_clim()
        clim._clim.intake_explicit = True
        clim.on_airflow_mode('auto')
        assert clim._clim.intake_explicit is False

    def test_airflow_mode_recirc_sets_intake_explicit(self):
        clim = _make_clim()
        clim._clim.intake_explicit = False
        clim.on_airflow_mode('recirc')
        assert clim._clim.intake_explicit is True

    def test_airflow_mode_fresh_sets_intake_explicit(self):
        clim = _make_clim()
        clim._clim.intake_explicit = False
        clim.on_airflow_mode('fresh')
        assert clim._clim.intake_explicit is True

    def test_airflow_mode_unfrost_front_sets_intake_explicit(self):
        clim = _make_clim()
        clim._clim.intake_explicit = False
        clim.on_airflow_mode('unfrost_front')
        assert clim._clim.intake_explicit is True

    def test_airflow_mode_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.auto = 1
        clim.on_airflow_mode('fresh')
        assert clim._clim.auto == 1

    def test_airflow_mode_state_not_down(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim.on_airflow_mode('fresh', state='normal')
        assert clim._clim.auto == 1

    def test_airflow_mode_guard_flag(self):
        clim = _make_clim()
        clim._updating_ui = True
        clim._clim.auto = 1
        clim.on_airflow_mode('fresh')
        assert clim._clim.auto == 1
        clim._updating_ui = False

    def test_airflow_auto_from_standby_reenables(self):
        clim = _make_clim()
        clim._clim.enabled = False
        clim._clim.fan = 0
        clim.on_airflow_mode('auto')
        assert clim._clim.enabled is True
        assert clim._clim.fan == 1

    def test_airflow_auto_from_active_non_auto_sends_popup(self):
        clim = _make_clim()
        clim._clim.enabled = True
        clim._clim.auto = 0
        clim.on_airflow_mode('auto')
        mfd = clim.runner.car.mfd_popup
        assert mfd.msg_id == 0x08
        assert mfd.flag == 0x80
        assert mfd.display_flags == 0x41

    # -- on_temp -------------------------------------------------------------

    def test_on_temp_left_up(self):
        clim = _make_clim()
        initial = clim._clim.temp_left
        clim.on_temp(0, +1)
        assert clim._clim.temp_left == initial + 1

    def test_on_temp_left_down(self):
        clim = _make_clim()
        initial = clim._clim.temp_left
        clim.on_temp(0, -1)
        assert clim._clim.temp_left == initial - 1

    def test_on_temp_left_mirrors_right_in_mono(self):
        clim = _make_clim()
        clim._clim.dual = 0
        clim._clim.temp_left = 10
        clim._clim.temp_right = 10
        clim.on_temp(0, +1)
        assert clim._clim.temp_left == 11
        assert clim._clim.temp_right == 11

    def test_on_temp_right_activates_dual(self):
        clim = _make_clim()
        clim._clim.dual = 0
        clim.on_temp(1, +1)
        assert clim._clim.dual == 1

    def test_on_temp_right_changes_only_right(self):
        clim = _make_clim()
        clim._clim.dual = 1
        initial_left = clim._clim.temp_left
        initial_right = clim._clim.temp_right
        clim.on_temp(1, +1)
        assert clim._clim.temp_left == initial_left
        assert clim._clim.temp_right == initial_right + 1

    def test_on_temp_clamp_min(self):
        clim = _make_clim()
        clim._clim.temp_left = 0
        clim.on_temp(0, -1)
        assert clim._clim.temp_left == 0

    def test_on_temp_clamp_max(self):
        clim = _make_clim()
        max_idx = len(clim.temp_disp) - 1
        clim._clim.temp_left = max_idx
        clim.on_temp(0, +1)
        assert clim._clim.temp_left == max_idx

    def test_on_temp_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        initial = clim._clim.temp_left
        clim.on_temp(0, +1)
        assert clim._clim.temp_left == initial

    def test_on_temp_updates_label(self):
        clim = _make_clim()
        clim._clim.temp_left = 9  # '20'
        clim.on_temp(0, +1)
        assert '20.5' in clim.ids['cur_temp0'].text

    # -- on_option -----------------------------------------------------------

    def test_on_option_dual_on(self):
        clim = _make_clim()
        clim._clim.dual = 0
        clim.on_option('dual', 'down')
        assert clim._clim.dual == 1

    def test_on_option_dual_off_mirrors(self):
        clim = _make_clim()
        clim._clim.dual = 1
        clim._clim.temp_left = 8
        clim._clim.temp_right = 15
        clim._clim.dir_left = 0x04
        clim._clim.dir_right = 0x02
        clim.on_option('dual', 'normal')
        assert clim._clim.dual == 0
        assert clim._clim.temp_right == clim._clim.temp_left
        assert clim._clim.dir_right == clim._clim.dir_left

    def test_on_option_unfrost_rear(self):
        clim = _make_clim()
        clim._clim.unfrost_rear = 0
        clim.on_option('unfrost_rear', 'down')
        assert clim._clim.unfrost_rear == 1

    def test_on_option_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.dual = 0
        clim.on_option('dual', 'down')
        assert clim._clim.dual == 0

    def test_on_option_guard_flag(self):
        clim = _make_clim()
        clim._updating_ui = True
        clim._clim.dual = 0
        clim.on_option('dual', 'down')
        assert clim._clim.dual == 0
        clim._updating_ui = False

    # -- on_intake -----------------------------------------------------------

    def test_on_intake_recirculate(self):
        clim = _make_clim()
        clim._clim.recycle = 0
        clim.on_intake(True)
        assert clim._clim.recycle == 1
        assert clim._clim.intake_explicit is True

    def test_on_intake_fresh(self):
        clim = _make_clim()
        clim._clim.recycle = 1
        clim.on_intake(False)
        assert clim._clim.recycle == 0
        assert clim._clim.intake_explicit is True

    def test_on_intake_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.recycle = 0
        clim.on_intake(True)
        assert clim._clim.recycle == 0

    def test_on_intake_state_not_down(self):
        clim = _make_clim()
        clim._clim.recycle = 0
        clim.on_intake(True, state='normal')
        assert clim._clim.recycle == 0

    # -- on_fan --------------------------------------------------------------

    def test_on_fan_set_value(self):
        clim = _make_clim()
        clim._clim.auto = 0
        clim.on_fan(5)
        assert clim._clim.fan == 5

    def test_on_fan_zero_disables(self):
        clim = _make_clim()
        clim.on_fan(0)
        assert clim._clim.enabled is False
        assert clim._clim.fan == 0

    def test_on_fan_zero_sets_mfd_popup(self):
        clim = _make_clim()
        clim.on_fan(0)
        mfd = clim.runner.car.mfd_popup
        assert mfd.flag == 0x00
        assert mfd.msg_id == 0x65
        assert mfd.display_flags == 0x41

    def test_on_fan_from_zero_reenables(self):
        clim = _make_clim()
        clim._clim.fan = 0
        clim._clim.enabled = False
        clim.on_fan(3)
        assert clim._clim.enabled is True

    def test_on_fan_exits_auto(self):
        clim = _make_clim()
        clim._clim.auto = 1
        clim._clim.fan = 2
        clim.on_fan(4)
        assert clim._clim.auto == 0

    def test_on_fan_ignition_off_no_change(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.fan = 3
        clim.on_fan(5)
        assert clim._clim.fan == 3

    # -- on_toggle -----------------------------------------------------------

    def test_on_toggle_set_bit(self):
        clim = _make_clim()
        clim._clim.bits = 0
        clim.on_toggle(2, 'down')
        assert clim._clim.bits & (1 << 2)

    def test_on_toggle_clear_bit(self):
        clim = _make_clim()
        clim._clim.bits = 0xFF
        clim.on_toggle(3, 'normal')
        assert not (clim._clim.bits & (1 << 3))

    def test_on_toggle_ignition_off(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        clim._clim.bits = 0
        clim.on_toggle(0, 'down')
        assert clim._clim.bits == 0

    # -- _set_off_state ------------------------------------------------------

    def test_set_off_state_resets_fan(self):
        clim = _make_clim()
        clim._clim.fan = 5
        clim._set_off_state()
        assert clim._clim.fan == 0

    def test_set_off_state_resets_dirs(self):
        clim = _make_clim()
        clim._clim.dir_left = 0x04
        clim._clim.dir_right = 0x03
        clim._set_off_state()
        assert clim._clim.dir_left == 0
        assert clim._clim.dir_right == 0

    def test_set_off_state_resets_bits(self):
        clim = _make_clim()
        clim._clim.bits = 0xFF
        clim._set_off_state()
        assert clim._clim.bits == 0

    def test_set_off_state_resets_flags(self):
        clim = _make_clim()
        clim._clim.unfrost_front = 1
        clim._clim.unfrost_rear = 1
        clim._clim.recycle = 1
        clim._clim.auto = 1
        clim._set_off_state()
        assert clim._clim.unfrost_front == 0
        assert clim._clim.unfrost_rear == 0
        assert clim._clim.recycle == 0
        assert clim._clim.auto == 0

    def test_set_off_state_clears_intake_explicit(self):
        clim = _make_clim()
        clim._clim.intake_explicit = True
        clim._set_off_state()
        assert clim._clim.intake_explicit is False

    # -- on_can_message (0x036 ignition off) ---------------------------------

    def test_can_036_ignition_change_resets(self):
        clim = _make_clim()
        clim._clim.fan = 5
        msg = types.SimpleNamespace(
            arbitration_id=0x036,
            data=[0, 0, 0, 0, 0x00],  # byte4 != _ignition_on
        )
        clim.on_can_message(msg)
        assert clim._clim.fan == 0

    def test_can_036_ignition_same_no_reset(self):
        clim = _make_clim()
        clim._clim.fan = 5
        msg = types.SimpleNamespace(
            arbitration_id=0x036,
            data=[0, 0, 0, 0, ClimModule._ignition_on],
        )
        clim.on_can_message(msg)
        assert clim._clim.fan == 5

    # -- on_can_message (0x1D0) -----------------------------------------------

    def test_can_1D0_updates_fan(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1D0,
            data=[0, 0, 0x02, 0x00, 0x00, 11, 11],
        )
        clim.on_can_message(msg)
        assert clim._clim.fan == 3  # _decode_can_fan(0x02) = 3

    def test_can_1D0_updates_temps(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1D0,
            data=[0, 0, 0x0F, 0x00, 0x00, 5, 8],
        )
        clim.on_can_message(msg)
        assert clim._clim.temp_left == 5
        assert clim._clim.temp_right == 8

    def test_can_1D0_updates_recycle(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1D0,
            data=[0, 0, 0x0F, 0x00, 0x10, 11, 11],
        )
        clim.on_can_message(msg)
        assert clim._clim.recycle == 1

    def test_can_1D0_direction_high_low_same(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1D0,
            data=[0, 0, 0x0F, 0x44, 0x00, 11, 11],
        )
        clim.on_can_message(msg)
        assert clim._clim.dir_left == 0x04

    def test_can_1D0_direction_high_low_different(self):
        clim = _make_clim()
        clim._clim.dir_left = 0x02
        msg = types.SimpleNamespace(
            arbitration_id=0x1D0,
            data=[0, 0, 0x0F, 0x43, 0x00, 11, 11],
        )
        clim.on_can_message(msg)
        # high != low → dir_left unchanged
        assert clim._clim.dir_left == 0x02

    # -- on_can_message (0x1E3) -----------------------------------------------

    def test_can_1E3_updates_fan(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x00, 0x00, 11, 11, 0x00, 0x00, 0x03],
        )
        clim.on_can_message(msg)
        assert clim._clim.fan == 4  # _decode_can_fan(0x03) = 4

    def test_can_1E3_updates_directions(self):
        clim = _make_clim()
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x00, 0x00, 11, 11, 0x40, 0x30, 0x0F],
        )
        clim.on_can_message(msg)
        assert clim._clim.dir_left == 4
        assert clim._clim.dir_right == 3

    def test_can_1E3_updates_ac_auto_dual(self):
        clim = _make_clim()
        # byte0 = 0x19 → ac=1(bit4), auto=1(bit3), dual=1(bit0)
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x19, 0x00, 11, 11, 0x00, 0x00, 0x0F],
        )
        clim.on_can_message(msg)
        assert clim._clim.ac == 1
        assert clim._clim.auto == 1
        assert clim._clim.dual == 1

    def test_can_1E3_updates_recycle(self):
        clim = _make_clim()
        # byte0 bit7 = recirculation
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x80, 0x00, 11, 11, 0x00, 0x00, 0x0F],
        )
        clim.on_can_message(msg)
        assert clim._clim.recycle == 1

    def test_can_1E3_updates_unfrost_front(self):
        clim = _make_clim()
        # byte1 bit7 = unfrost_front
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x00, 0x80, 11, 11, 0x00, 0x00, 0x0F],
        )
        clim.on_can_message(msg)
        assert clim._clim.unfrost_front == 1

    def test_can_1E3_updates_temps(self):
        clim = _make_clim()
        # byte2 & 0x1F = temp_left; byte3 = temp_right
        msg = types.SimpleNamespace(
            arbitration_id=0x1E3,
            data=[0x00, 0x00, 0x0A, 0x0C, 0x00, 0x00, 0x0F],
        )
        clim.on_can_message(msg)
        assert clim._clim.temp_left == 10
        assert clim._clim.temp_right == 12

    # -- Short / unknown CAN messages ----------------------------------------

    def test_can_short_message_ignored(self):
        clim = _make_clim()
        clim._clim.fan = 5
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0, 0])
        clim.on_can_message(msg)
        assert clim._clim.fan == 5

    def test_can_unknown_id_ignored(self):
        clim = _make_clim()
        clim._clim.fan = 5
        msg = types.SimpleNamespace(arbitration_id=0x999, data=[0] * 8)
        clim.on_can_message(msg)
        assert clim._clim.fan == 5

    # -- _is_ignition_on helper ----------------------------------------------

    def test_is_ignition_on_true(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = True
        assert clim._is_ignition_on() is True

    def test_is_ignition_on_false(self):
        clim = _make_clim()
        clim.runner.car.bsi.ignition_on = False
        assert clim._is_ignition_on() is False

    # -- _clim property helper -----------------------------------------------

    def test_clim_property_returns_car_clim(self):
        clim = _make_clim()
        assert clim._clim is clim.runner.car.clim
