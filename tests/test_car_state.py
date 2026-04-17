"""
Tests for car_state.VirtualCar, can_messages, and the CanRunner integration.
"""
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
                       KMLState, BTEState)
from modules.clim import Clim as ClimModule


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
            'LO', '15', '16', '17', '18', '18.5', '19', '19.5', '20', '20.5',
            '21', '21.5', '22', '22.5', '23', '23.5', '24', '25', '26', '27', 'HI'
        ]
        widget.ids = {
            'slider_fan': DummyWidget(value=0),
            'cur_fan': DummyWidget(text='Fan: 0'),
            'auto': DummyWidget(),
            'dual': DummyWidget(),
            'recycle': DummyWidget(),
            'unfrost_front': DummyWidget(),
            'unfrost_rear': DummyWidget(),
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

    def test_update_dir_buttons_recognizes_real_fast_code(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_fast': DummyWidget(),
            'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_fast': DummyWidget(),
        })
        widget.runner.car.clim.dir_left = 0x08
        widget.runner.car.clim.dir_right = 0x08
        widget._update_dir_buttons()
        assert widget.ids['left_fast'].state == 'down'
        assert widget.ids['right_fast'].state == 'down'

    def test_on_dir_ignores_normal_state_transition(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.runner.car.clim.dir_left = 0x04
        widget.on_dir(0, 0x08, 'normal')
        assert widget.runner.car.clim.dir_left == 0x04

    def test_on_dir_accepts_down_state_transition(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.on_dir(1, 0x05, 'down')
        assert widget.runner.car.clim.dir_right == 0x05

    def test_idle_1d0_monitor_update_does_not_clear_left_button(self):
        widget = self._make_clim_widget(ignition_on=True)
        widget.ids.update({
            'left_fr': DummyWidget(), 'left_up': DummyWidget(), 'left_ud': DummyWidget(),
            'left_down': DummyWidget(), 'left_fd': DummyWidget(), 'left_fast': DummyWidget(),
            'right_fr': DummyWidget(), 'right_up': DummyWidget(), 'right_ud': DummyWidget(),
            'right_down': DummyWidget(), 'right_fd': DummyWidget(), 'right_fast': DummyWidget(),
            'cur_temp0': DummyWidget(text=''), 'cur_temp1': DummyWidget(text=''),
        })
        widget.runner.car.clim.dir_left = 0x04
        msg = types.SimpleNamespace(arbitration_id=0x1D0, data=[0x08, 0x00, 0x07, 0x00, 0x00, 0x10, 0x10, 0x00])
        widget.on_can_message(msg)
        assert widget.runner.car.clim.dir_left == 0x04
        assert widget.ids['left_up'].state == 'down'


# ---------------------------------------------------------------------------
# can_messages tests
# ---------------------------------------------------------------------------

from can_messages import (ALL_MESSAGES, CanMessage, Msg036, Msg0E1, Msg0B6,
                          Msg128, Msg168, Msg190, Msg1A1, Msg1D0, Msg1E3,
                          Msg221, Msg2A1, Msg261, Msg12B, Msg1A3, Msg223,
                          Msg323, Msg165, Msg1A5, Msg1E5, Msg3E5, Msg52D,
                          Msg110, Msg0F6, Msg161, Msg217, Msg12D)


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

    def test_decode_updates_light_mode(self):
        car = VirtualCar()
        # byte[4] = 0xC0 means low beam
        Msg128().decode(car, [0x91, 0xE0, 0x00, 0x00, 0xC0, 0x80, 0xB0, 0x01])
        assert car.bsi.light_mode == 2  # _lights_low


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


class TestMsg1A1Encode:
    def test_suppressed_when_tyre_display_active(self):
        car = VirtualCar()
        car.tyres.display_active = True
        assert Msg1A1().encode(car) is None

    def test_suppressed_when_door_display_active(self):
        car = VirtualCar()
        car.doors.display_active = True
        assert Msg1A1().encode(car) is None

    def test_suppressed_when_no_popup(self):
        car = VirtualCar()
        assert Msg1A1().encode(car) is None

    def test_encodes_popup(self):
        car = VirtualCar()
        car.mfd_popup.flag = 0x80
        car.mfd_popup.msg_id = 0x42
        data = Msg1A1().encode(car)
        assert data[0] == 0x80
        assert data[1] == 0x42

    def test_decode_updates_car(self):
        car = VirtualCar()
        Msg1A1().decode(car, [0x80, 0x42, 0xF0, 0, 0, 0, 0, 0])
        assert car.mfd_popup.flag == 0x80
        assert car.mfd_popup.msg_id == 0x42


class TestMsg1D0Encode:
    def test_bsi_idle_when_clim_not_enabled(self):
        car = VirtualCar()
        data = Msg1D0().encode(car)
        assert data == [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]

    def test_airflow_direction_uses_repeated_nibble_format(self):
        car = VirtualCar()
        car.clim.enabled = True
        car.bsi.ignition_on = True
        car.clim.dir_left = 0x04
        data = Msg1D0().encode(car)
        assert data[3] == 0x44

    def test_decode_normalizes_repeated_nibble_airflow_value(self):
        car = VirtualCar()
        Msg1D0().decode(car, [0x08, 0x00, 0x07, 0x88, 0x00, 0x10, 0x10, 0x00])
        assert car.clim.dir_left == 0x08

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
        assert data[2] == 3  # fan byte


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

    def test_register_message_duplicate_warns(self, capsys):
        runner = self._make_runner()
        runner.register_message(Msg036())
        runner.register_message(Msg036())
        out = capsys.readouterr().out
        assert 'WARNING' in out
        assert '0x036' in out

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

    def test_first_registration_no_warning(self, capsys):
        runner = self._make_runner()
        runner.reg(lambda: None, 0x1D0, 500)
        out = capsys.readouterr().out
        assert 'WARNING' not in out

    def test_duplicate_registration_emits_warning(self, capsys):
        runner = self._make_runner()
        runner.reg(lambda: None, 0x1D0, 500)
        runner.reg(lambda: None, 0x1D0, 100)
        out = capsys.readouterr().out
        assert 'WARNING' in out
        assert '0x1D0' in out

    def test_duplicate_registration_overrides(self):
        runner = self._make_runner()
        def sender_a():
            return 0x1D0, [0x01]
        def sender_b():
            return 0x1D0, [0x02]
        runner.reg(sender_a, 0x1D0, 500)
        runner.reg(sender_b, 0x1D0, 500)
        assert runner._can_id_owners[0x1D0] is sender_b

    def test_different_ids_no_warning(self, capsys):
        runner = self._make_runner()
        runner.reg(lambda: None, 0x1D0, 500)
        runner.reg(lambda: None, 0x1E3, 500)
        out = capsys.readouterr().out
        assert 'WARNING' not in out
