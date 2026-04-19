"""Tests for CAN message encoders and decoders."""
import datetime
import importlib
import os
import sys
import types

import pytest

from car_state import (BSI, Buttons, Clim, CDChanger, Dashboard, Doors, MFDPopup,
                       Parktronic, Tyres, VirtualCar, Radio, Trip,
                       KMLState, BTEState, SpeedControl)
from can_messages import (ALL_MESSAGES, CanMessage, Msg036, Msg0E1, Msg0B6,
                          Msg128, Msg131, Msg168, Msg190, Msg1A0, Msg1A1,
                          Msg1D0, Msg1E3, Msg221, Msg2A1, Msg261, Msg12B,
                          Msg1A3, Msg223, Msg323, Msg165, Msg1A5, Msg1E5,
                          Msg3E5, Msg52D, Msg110, Msg0F6, Msg161, Msg1A8,
                          Msg217, Msg12D, STARTUP_WAKEUP_BURST)
from conftest import make_can_mock, DummyWidget

BSIBaseModule = importlib.import_module('modules.bsi-base').BSI_base


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


class TestBsiBaseCombineSync:
    def _make_bsi_widget(self):
        widget = BSIBaseModule.__new__(BSIBaseModule)
        widget.runner = types.SimpleNamespace(car=VirtualCar(), monitor=True)
        engine = DummyWidget(state='normal', text='Engine')
        engine.disabled = True
        widget.ids = {
            'engine': engine,
            'ignition': DummyWidget(state='normal'),
            'sleeping': DummyWidget(state='normal'),
            'wakeup': DummyWidget(state='normal'),
            'lights_off': DummyWidget(state='down'),
            'lights_side': DummyWidget(state='normal'),
            'lights_low': DummyWidget(state='normal'),
            'lights_high': DummyWidget(state='normal'),
            'dash_lights': DummyWidget(state='normal'),
            'dark_mode': DummyWidget(state='normal'),
            'cur_lum': DummyWidget(text='lum: 15'),
            'slider_lum': DummyWidget(value=15),
        }
        widget._updating_power_buttons = False
        widget._updating_light_buttons = False
        return widget

    def test_set_power_mode_turns_combine_on_when_dashboard_active(self):
        widget = self._make_bsi_widget()
        widget.runner.car.dashboard.active = True

        widget.set_power_mode(0x01)

        assert widget.runner.car.bsi.ignition_on is True
        assert widget.runner.car.dashboard.on == 1

    def test_set_light_mode_updates_combine_light_icons(self):
        widget = self._make_bsi_widget()
        widget.runner.car.dashboard.active = True

        widget.set_light_mode(2, update_ui=True)
        assert widget.runner.car.dashboard.backlight == 1
        assert widget.runner.car.dashboard.low_beam == 1
        assert widget.runner.car.dashboard.high_beam == 0

        widget.set_light_mode(3, update_ui=True)
        assert widget.runner.car.dashboard.backlight == 1
        assert widget.runner.car.dashboard.low_beam == 0
        assert widget.runner.car.dashboard.high_beam == 1

        widget.set_light_mode(0, update_ui=True)
        assert widget.runner.car.dashboard.backlight == 0
        assert widget.runner.car.dashboard.low_beam == 0
        assert widget.runner.car.dashboard.high_beam == 0


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

    def test_byte0_explicit_fresh_ac_preserved_dual_gives_0x05(self):
        """Workbench: explicit Fresh → byte0=0x05 regardless of clim.ac state.

        The user's A/C preference (clim.ac) is preserved in state; Msg1E3 encodes
        ac=0 in byte0 when recirc/fresh is explicitly active (workbench-verified).
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference stays on in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 0
        car.clim.intake_explicit = True   # Fresh explicitly selected
        data = Msg1E3().encode(car)
        assert data[0] == 0x05  # 0x00 (no recirc) | 0x00 (ac forced to 0) | 0x04 (explicit) | 0x01 (dual)

    def test_byte0_explicit_recirc_ac_preserved_dual_gives_0x85(self):
        """Workbench: explicit Recirc → byte0=0x85 regardless of clim.ac state.

        The user's A/C preference (clim.ac) is preserved in state; Msg1E3 encodes
        ac=0 in byte0 when recirc/fresh is explicitly active (workbench-verified).
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference stays on in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 1
        car.clim.intake_explicit = True   # Recirc explicitly selected
        data = Msg1E3().encode(car)
        assert data[0] == 0x85  # 0x80 (recirc) | 0x00 (ac forced to 0) | 0x04 (explicit) | 0x01 (dual)

    def test_byte0_unfrost_front_preserves_ac_in_frame(self):
        """unfrost_front preserves clim.ac in the byte0 encoding (workbench: A/C unchanged)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.unfrost_front = 1
        car.clim.intake_explicit = True
        data = Msg1E3().encode(car)
        assert data[0] & 0x10  # ac bit still set (0x10) — unfrost preserves A/C

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

    def test_recirc_notify_sets_bit1_on_first_frame(self):
        """Workbench: 0x1E3 byte0=0x87 (0x85|0x02) on first frame after recirc entry.

        clim.ac is preserved as 1 in state; Msg1E3 encodes ac=0 in the frame.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference preserved in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        car.clim.intake_notify = True   # set by on_airflow_mode('recirc')
        data = Msg1E3().encode(car)
        assert data[0] == 0x87  # 0x85 | 0x02 — matches workbench recirc entry frame

    def test_recirc_notify_cleared_after_first_frame(self):
        """intake_notify is one-shot: Msg1E3.encode consumes it and clears the flag."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference preserved in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        car.clim.intake_notify = True
        Msg1E3().encode(car)
        assert car.clim.intake_notify is False
        # Second frame: no notify bit → back to 0x85
        data = Msg1E3().encode(car)
        assert data[0] == 0x85

    def test_fresh_notify_sets_bit1_on_first_frame(self):
        """Workbench: 0x1E3 byte0=0x07 (0x05|0x02) on first frame after fresh entry.

        clim.ac is preserved as 1 in state; Msg1E3 encodes ac=0 in the frame.
        """
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference preserved in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 0
        car.clim.intake_explicit = True
        car.clim.intake_notify = True   # set by on_airflow_mode('fresh')
        data = Msg1E3().encode(car)
        assert data[0] == 0x07  # 0x05 | 0x02 — matches workbench fresh entry frame

    def test_no_notify_bit_without_flag(self):
        """Without intake_notify, stable recirc byte0 stays at 0x85 (no bit1)."""
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.ac = 1   # A/C preference preserved in state
        car.clim.auto = 0
        car.clim.dual = 1
        car.clim.recycle = 1
        car.clim.intake_explicit = True
        car.clim.intake_notify = False
        data = Msg1E3().encode(car)
        assert data[0] == 0x85  # stable recirc, no popup bit


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
        assert Msg1A1().encode(car) == [0x80, 0xDE, 0xC6, 0x40, 0x00, 0x00, 0x00, 0x00]

    def test_encodes_door_status_bits_for_workbench_mfd_popup(self):
        car = VirtualCar()
        car.doors.display_active = True
        car.doors.front_left = 1
        car.doors.rear_right = 1
        car.doors.boot = 1
        car.doors.fuel_flap = 1
        assert Msg1A1().encode(car) == [0x80, 0x0B, 0xC6, 0x68, 0x40, 0x00, 0x00, 0x00]

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
        # radio is listen-only; encode returns None when buttons are not active
        assert data is None

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
        assert car.radio.volume == 22  # also updated so radio display reflects bus

    def test_decode_updates_radio_volume_when_buttons_inactive(self):
        car = VirtualCar()
        Msg1A5().decode(car, [0x00 | 22])
        assert car.radio.volume == 22


class TestMsg3E5Buttons:
    def test_radio_encoding_when_buttons_inactive(self):
        car = VirtualCar()
        car.radio.panel['tel'] = 1
        data = Msg3E5().encode(car)
        # radio is listen-only; encode returns None when buttons are not active
        assert data is None

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
        # radio module layout: ok is b2[7:6]
        frame = [0x00, 0x00, (1 << 6), 0x00, 0x00, 0x00]
        Msg3E5().decode(car, frame)
        assert car.radio.panel['ok'] == 1

