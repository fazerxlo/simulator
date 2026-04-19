"""Tests for the Combine (instrument cluster) module UI helpers."""

import types

import pytest

from car_state import VirtualCar
from conftest import DummyWidget
from modules.combine import Combine as CombineModule


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
