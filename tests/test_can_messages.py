"""Tests for generated CAN message encoders and decoders."""
import datetime
import importlib
import os
import sys
import types

import pytest

from car_state import (BSI, Buttons, SteeringWheel, Clim, Dashboard, Doors, MFDPopup,
                       Parktronic, Tyres, VirtualCar, Radio, Trip,
                       KMLState, BTEState, SpeedControl)
from generated import (ALL_MESSAGES, CanMessage, Msg036, Msg0E1, Msg0B6,
                          Msg128, Msg168, Msg190, Msg1A1, Msg1D0, Msg1E3,
                          Msg221, Msg2A1, Msg261, Msg12B, Msg1A3, Msg223,
                          Msg323, Msg165, Msg1A5, Msg1E5, Msg0C5, Msg21F, Msg3E5,
                          Msg52D, Msg110, Msg0F6, Msg161, Msg1A8, Msg217,
                          Msg12D, Msg0A9, Msg0E6, Msg1E1, Msg2E1, Msg361, Msg3A1,
                          Msg3A7, Msg4A4, Msg269, STARTUP_WAKEUP_BURST)
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


class TestMsg0F6Defrost:
    def test_rear_defrost_active_sets_bit0_in_bytes2_and_3(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.unfrost_rear = 1
        data = Msg0F6().encode(car)
        assert data[2] & 0x01 == 1
        assert data[3] & 0x01 == 1

    def test_rear_defrost_inactive_clears_bit0_when_ignition_on(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.unfrost_rear = 0
        data = Msg0F6().encode(car)
        assert data[2] & 0x01 == 0
        assert data[3] & 0x01 == 0

    def test_rear_defrost_decoded_from_msg0f6(self):
        car = VirtualCar()
        Msg0F6().decode(car, [0x88, 0x3C, 0x01, 0x01, 0x00, 0xFC, 0xFC, 0x20])
        assert car.clim.unfrost_rear == 1


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

    def test_unfrost_rear_state_confirmation_in_msg128(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.unfrost_rear = 1
        data = Msg128().encode(car)
        assert data[1] & 0x10 == 0x10  # Byte 1 Bit 4 set
        assert data[2] & 0x01 == 1
        assert data[3] & 0x11 != 0

    def test_unfrost_rear_inactive_clears_byte1_bit4_in_msg128(self):
        car = VirtualCar()
        car.bsi.ignition_on = True
        car.clim.unfrost_rear = 0
        data = Msg128().encode(car)
        assert data[1] & 0x10 == 0x00  # Byte 1 Bit 4 cleared

    def test_unfrost_rear_decoded_from_msg128_byte1_bit4(self):
        car = VirtualCar()
        Msg128().decode(car, [0x00, 0x10, 0x00, 0x00, 0x00, 0x80, 0xB0, 0x01])
        assert car.clim.unfrost_rear == 1

    def test_unfrost_rear_decoded_from_msg128(self):
        car = VirtualCar()
        Msg128().decode(car, [0x91, 0xE0, 0x01, 0x11, 0x00, 0x80, 0xB0, 0x01])
        assert car.clim.unfrost_rear == 1


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



    def test_encodes_tyre_popup_when_tyre_display_active(self):
        car = VirtualCar()
        car.tyres.display_active = True
        car.tyres.fl = Tyres.LOW
        assert Msg1A1().encode(car) == [0x80, 0x8D, 0xC6, 0x10, 0x00, 0x00, 0x00, 0x00]

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

    def test_unfrost_rear_encoded_in_byte4_bit0(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.unfrost_rear = 1
        data = Msg1D0().encode(car)
        assert data[4] & 0x01 == 1

    def test_unfrost_rear_decoded_from_byte4_bit0(self):
        car = VirtualCar()
        Msg1D0().decode(car, [0x08, 0x00, 0x00, 0x00, 0x01, 0x0B, 0x0B, 0x00])
        assert car.clim.unfrost_rear == 1


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

    def test_com_right_pulse_asserted(self):
        car = VirtualCar()
        car.trip.press_com('com_right', ticks=2)
        d1 = Msg221().encode(car)
        assert (d1[0] >> 3) & 1 == 1  # com_right bit asserted
        d2 = Msg221().encode(car)
        assert (d2[0] >> 3) & 1 == 1  # 2nd tick still asserted
        d3 = Msg221().encode(car)
        assert (d3[0] >> 3) & 1 == 0  # cleared after ticks expire

    def test_com_buttons_press_and_release(self):
        car = VirtualCar()
        # Press com_right
        car.trip.com_right = 1
        d_press = Msg221().encode(car)
        assert (d_press[0] >> 3) & 1 == 1
        # Release com_right
        car.trip.com_right = 0
        car.trip._com_right_ticks = 0
        d_release = Msg221().encode(car)
        assert (d_release[0] >> 3) & 1 == 0

        # Press com_left
        car.trip.com_left = 1
        d_press_l = Msg221().encode(car)
        assert d_press_l[0] & 1 == 1
        # Release com_left
        car.trip.com_left = 0
        car.trip._com_left_ticks = 0
        d_release_l = Msg221().encode(car)
        assert d_release_l[0] & 1 == 0


class TestMsg2A1Msg261EncodeDecodeRoundtrip:
    """Wire layout: B0 = speed (uint8 km/h), B1-2 = dist, B3-4 = fuel, B5-6 = speed (uint16)."""

    def test_msg2a1_roundtrip(self):
        car_a = VirtualCar()
        car_a.trip.hist[0] = {'speed': 48, 'dist': 650, 'fuel': 6.8}
        data = Msg2A1().encode(car_a)
        assert len(data) == 7
        assert data[0] == 48  # Mean speed in Byte 0 for EMF-C and cluster displays
        assert data[1] == 650 >> 8
        assert data[2] == 650 & 0xFF
        assert data[3] == 68 >> 8
        assert data[4] == 68 & 0xFF
        assert data[5] == 48 >> 8
        assert data[6] == 48 & 0xFF

        car_b = VirtualCar()
        Msg2A1().decode(car_b, data)
        assert car_b.trip.hist[0]['dist'] == 650
        assert abs(car_b.trip.hist[0]['fuel'] - 6.8) < 0.1
        assert car_b.trip.hist[0]['speed'] == 48

    def test_msg261_roundtrip(self):
        car_a = VirtualCar()
        car_a.trip.hist[1] = {'speed': 92, 'dist': 1420, 'fuel': 5.4}
        data = Msg261().encode(car_a)
        assert len(data) == 7
        assert data[0] == 92  # Mean speed in Byte 0
        assert data[5] == 92 >> 8
        assert data[6] == 92 & 0xFF

        car_b = VirtualCar()
        Msg261().decode(car_b, data)
        assert car_b.trip.hist[1]['dist'] == 1420
        assert abs(car_b.trip.hist[1]['fuel'] - 5.4) < 0.1
        assert car_b.trip.hist[1]['speed'] == 92


class TestRT4NewMessages:
    def test_msg0a9_nav_repeat_idle(self):
        car = VirtualCar()
        data = Msg0A9().encode(car)
        # Default idle vector from RT4 spec
        assert data == [0x00, 0x3F, 0xFF, 0x3F, 0xFF, 0xFF, 0xFF, 0xFF]

    def test_msg0a9_nav_repeat_active(self):
        car = VirtualCar()
        car.bsi.nav_active = True
        car.bsi.nav_picto = 0x12
        car.bsi.nav_altitude = 250  # +999 offset: raw = 1249 = 0x04E1
        car.bsi.nav_dist_dest = 1500  # raw = 0x05DC
        car.bsi.nav_dist_maneuver = 400
        car.bsi.nav_eta_hour = 14
        car.bsi.nav_eta_minute = 35
        data = Msg0A9().encode(car)
        assert data[0] & 0x80  # active
        assert (data[0] & 0x3F) == 0x12  # picto
        # decode
        car_b = VirtualCar()
        Msg0A9().decode(car_b, data)
        assert car_b.bsi.nav_active is True
        assert car_b.bsi.nav_picto == 0x12
        assert car_b.bsi.nav_altitude == 250
        assert car_b.bsi.nav_dist_dest == 1500
        assert car_b.bsi.nav_dist_maneuver == 400
        assert car_b.bsi.nav_eta_hour == 14
        assert car_b.bsi.nav_eta_minute == 35

    def test_msg0e6_wheel_ticks(self):
        car = VirtualCar()
        car.bsi.wheel_ticks_rr = 1234
        car.bsi.wheel_ticks_rl = 5678
        data = Msg0E6().encode(car)
        assert len(data) == 5
        car_b = VirtualCar()
        Msg0E6().decode(car_b, data)
        assert car_b.bsi.wheel_ticks_rr == 1234
        assert car_b.bsi.wheel_ticks_rl == 5678

    def test_msg1e1_tpms_wheel_status(self):
        car = VirtualCar()
        car.tyres.fl = Tyres.LOW
        car.tyres.fr = Tyres.OK
        car.tyres.rr = Tyres.FLAT
        car.tyres.rl = Tyres.OK
        car.tyres.spare = Tyres.BATTERY_LOW
        car.tyres.tpms_system_state = 0xA0
        data = Msg1E1().encode(car)
        assert len(data) == 8
        assert data[0] >> 3 == 1  # LOW
        assert data[1] >> 3 == 0  # OK
        assert data[2] >> 3 == 2  # FLAT
        assert data[4] >> 3 == 4  # BATTERY_LOW
        assert data[5] == 0xA0
        car_b = VirtualCar()
        Msg1E1().decode(car_b, data)
        assert car_b.tyres.fl == Tyres.LOW
        assert car_b.tyres.fr == Tyres.OK
        assert car_b.tyres.rr == Tyres.FLAT
        assert car_b.tyres.spare == Tyres.BATTERY_LOW
        assert car_b.tyres.tpms_system_state == 0xA0

    def test_msg2e1_functions_status(self):
        car = VirtualCar()
        car.bsi.light_mode = 2  # low beam
        car.bsi.wipers_front = 2
        car.speed_control.control_type = SpeedControl.REGULATOR
        data = Msg2E1().encode(car)
        assert len(data) == 3
        car_b = VirtualCar()
        Msg2E1().decode(car_b, data)
        assert car_b.bsi.wipers_front == 2

    def test_msg361_tpms_direct_sensors(self):
        car = VirtualCar()
        car.tyres.fl = Tyres.LOW
        car.tyres.pressure_fl = 1.8
        car.tyres.fr = Tyres.OK
        car.tyres.pressure_fr = 2.4
        car.tyres.rr = Tyres.FLAT
        car.tyres.pressure_rr = 0.5
        car.tyres.rl = Tyres.NO_DATA
        car.tyres.pressure_rl = 0.0

        data = Msg361().encode(car)
        assert len(data) == 8
        # FL: state=1 (LOW) -> (1 << 14) | round(1.8 / 0.1) = 0x4000 | 18 = 0x4012 -> (0x40, 0x12)
        assert data[0] == 0x40
        assert data[1] == 18
        # FR: state=0 (OK) -> 0x0000 | 24 = 24 -> (0x00, 0x18)
        assert data[2] == 0x00
        assert data[3] == 24
        # RR: state=2 (FLAT) -> (2 << 14) | 5 = 0x8005 -> (0x80, 0x05)
        assert data[4] == 0x80
        assert data[5] == 5
        # RL: state=3 (NO_DATA) -> state=3 with 0x3FFF invalid pressure = 0xFFFF -> (0xFF, 0xFF)
        assert data[6] == 0xFF
        assert data[7] == 0xFF

        car_b = VirtualCar()
        Msg361().decode(car_b, data)
        assert car_b.tyres.fl == Tyres.LOW
        assert abs(car_b.tyres.pressure_fl - 1.8) < 0.05
        assert car_b.tyres.fr == Tyres.OK
        assert abs(car_b.tyres.pressure_fr - 2.4) < 0.05
        assert car_b.tyres.rr == Tyres.FLAT
        assert abs(car_b.tyres.pressure_rr - 0.5) < 0.05
        assert car_b.tyres.rl == Tyres.NO_DATA
        assert abs(car_b.tyres.pressure_rl - 0.0) < 0.05

    def test_msg3a1_wheel_pressures(self):
        car = VirtualCar()
        car.tyres.pressure_fl = 2.4
        car.tyres.pressure_fr = 2.4
        car.tyres.pressure_rr = 2.2
        car.tyres.pressure_rl = 2.2
        data = Msg3A1().encode(car)
        assert len(data) == 8
        assert data[0] == 48  # 2.4 / 0.05
        assert data[2] == 44  # 2.2 / 0.05
        car_b = VirtualCar()
        Msg3A1().decode(car_b, data)
        assert abs(car_b.tyres.pressure_fl - 2.4) < 0.05

    def test_msg3a7_maintenance(self):
        car = VirtualCar()
        car.bsi.service_countdown = 15000
        car.bsi.service_spanner = 0
        data = Msg3A7().encode(car)
        assert len(data) == 8
        car_b = VirtualCar()
        Msg3A7().decode(car_b, data)
        assert car_b.bsi.service_countdown == 15000

    def test_msg4a4_failure_dtc(self):
        car = VirtualCar()
        data = Msg4A4().encode(car)
        assert data == [0x50, 0x00, 0x00, 0x80, 0x01, 0x02, 0x05, 0x07]

    def test_msg269_crash_status(self):
        car = VirtualCar()
        car.bsi.crash_confirmed = 0
        data = Msg269().encode(car)
        assert data == [0x00, 0x00, 0x00]
        car.bsi.crash_confirmed = 1
        data = Msg269().encode(car)
        assert data[0] & 0x80


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


class TestMsg21FSteeringWheelButtons:
    def test_encode_volume_up_press_uses_remote_mask(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.press_remote('volume_up')
        assert Msg21F().encode(car) == [0x08, 0x09, 0x00]

    def test_encode_releases_after_pulse_window(self):
        car = VirtualCar()
        car.buttons.active = True
        car.buttons.press_remote('source')
        for _ in range(car.buttons._pulse_window):
            Msg21F().encode(car)
        assert Msg21F().encode(car) == [0x00, 0x09, 0x00]

    def test_decode_identifies_volume_up(self):
        car = VirtualCar()
        Msg21F().decode(car, [0x08, 0x09, 0x00])
        assert car.buttons.remote_action == 'volume_up'


class TestMsg3E5RadioPanel:
    def test_radio_encoding_when_inactive(self):
        car = VirtualCar()
        car.radio.active = False
        car.radio.panel['tel'] = 1
        data = Msg3E5().encode(car)
        assert data is None

    def test_radio_encoding_when_active(self):
        car = VirtualCar()
        car.radio.active = True
        car.radio.panel['menu'] = 1
        car.radio.panel['tel'] = 1
        car.radio.panel['ok'] = 1
        data = Msg3E5().encode(car)
        assert data is not None
        assert (data[0] >> 6) & 1 == 1  # menu
        assert (data[0] >> 4) & 1 == 1  # tel
        assert (data[2] >> 6) & 1 == 1  # ok

    def test_radio_required_modules(self):
        assert 'radio' in Msg3E5.required_modules

    def test_decode_updates_radio_panel(self):
        car = VirtualCar()
        # Byte 0: menu (b0 >> 6), tel (b0 >> 4), clim (b0 & 1)
        # Byte 1: trip (b1 >> 6), mode (b1 >> 4), audio (b1 & 1)
        # Byte 2: ok (b2 >> 6), esc (b2 >> 4)
        # Byte 5: up (b5 >> 6), down (b5 >> 4), right (b5 >> 2), left (b5 & 1)
        b0 = (1 << 6) | (1 << 4) | 1
        b1 = (1 << 6) | (1 << 4) | 1
        b2 = (1 << 6) | (1 << 4)
        b5 = (1 << 6) | (1 << 4) | (1 << 2) | 1
        frame = [b0, b1, b2, 0x00, 0x00, b5]
        Msg3E5().decode(car, frame)

        assert car.radio.panel['menu'] == 1
        assert car.radio.panel['tel'] == 1
        assert car.radio.panel['clim'] == 1
        assert car.radio.panel['trip'] == 1
        assert car.radio.panel['mode'] == 1
        assert car.radio.panel['audio'] == 1
        assert car.radio.panel['ok'] == 1
        assert car.radio.panel['esc'] == 1
        assert car.radio.panel['up'] == 1
        assert car.radio.panel['down'] == 1
        assert car.radio.panel['right'] == 1
        assert car.radio.panel['left'] == 1



class TestMsg0C5SteeringAngle:
    def test_encode_centered_angle_zero(self):
        car = VirtualCar()
        car.steering_wheel.active = True
        car.steering_wheel.angle = 0.0
        assert Msg0C5().encode(car) == [0x00, 0x00, 0x00, 0x00]

    def test_encode_positive_angle(self):
        car = VirtualCar()
        car.steering_wheel.active = True
        car.steering_wheel.angle = 90.0  # 900 in 0.1 deg
        assert Msg0C5().encode(car) == [900 >> 8, 900 & 0xFF, 0x00, 0x00]

    def test_encode_negative_angle(self):
        car = VirtualCar()
        car.steering_wheel.active = True
        car.steering_wheel.angle = -90.0  # -900 = 0xFC7C
        assert Msg0C5().encode(car) == [0xFC, 0x7C, 0x00, 0x00]

    def test_encode_returns_none_when_inactive(self):
        car = VirtualCar()
        assert Msg0C5().encode(car) is None

    def test_decode_updates_angle(self):
        car = VirtualCar()
        # 45.0 deg -> raw 450 = 0x01C2
        Msg0C5().decode(car, [0x01, 0xC2, 0x00, 0x00])
        assert car.steering_wheel.angle == 45.0
