"""Tests for CanRunner integration: VirtualCar wiring, transmit robustness, scheduler tuning."""

import datetime
import importlib
import logging
import sys
import types

import pytest

from car_state import VirtualCar
from generated import (Msg036, Msg1D0, Msg12D, Msg1A5, Msg3E5, Msg12B, Msg0B6, Msg1E3, CanMessage)
from conftest import make_can_mock


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
        # Msg1A5 / Msg3E5 require at least one of radio, buttons
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
