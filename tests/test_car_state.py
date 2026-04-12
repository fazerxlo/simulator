"""
Tests for car_state.VirtualCar and the CanRunner integration.
"""
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
            pass
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

from car_state import BSI, Clim, Dashboard, Doors, Parktronic, Tyres, VirtualCar


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

    def test_dashboard_defaults(self):
        car = VirtualCar()
        assert car.dashboard.active is False
        for attr in ('airbag_pass', 'seatbelt', 'brakes', 'warn', 'stop',
                     'esp', 'tyre', 'low_beam'):
            assert getattr(car.dashboard, attr) == 0


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


class TestVirtualCarIsolation:
    """Each VirtualCar instance has independent state."""

    def test_two_cars_are_independent(self):
        car_a = VirtualCar()
        car_b = VirtualCar()
        car_a.bsi.ignition_on = True
        car_a.tyres.fl = Tyres.FLAT
        assert car_b.bsi.ignition_on is False
        assert car_b.tyres.fl == Tyres.OK


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
