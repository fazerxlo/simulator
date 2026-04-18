import datetime
import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Combine'
_version = '0.0.1'

class Combine(TabbedPanelItem):
    _ignition_on = 0x01

    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Combine'
        self.runner = runner

        # Mark dashboard as active so that Msg128 and Msg168 (registered by
        # bsi-base) switch to the full combine encoding.  No CAN TX callbacks
        # are registered here — state mutations via runner.car.dashboard are
        # sufficient.
        runner.car.dashboard.active = True

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/combine.kv')
        Builder.apply(self)

        self._last_ignition_state = None

        # Initialise dashboard state on the shared VirtualCar.
        dash = runner.car.dashboard
        dash.airbag_pass = 0
        dash.seatbelt = 0
        dash.brakes = 0
        dash.low_fuel = 0
        dash.preheat = 0
        dash.warn = 0
        dash.stop = 0
        dash.doors = 0
        dash.esp = 0
        dash.esp_blink = 0
        dash.tyre = 0
        dash.backlight = 0
        dash.on = 0
        dash.low_beam = 0
        dash.high_beam = 0
        dash.fog_front = 0
        dash.fog_rear = 0
        dash.clig_r = 0
        dash.clig_l = 0
        dash.coolant_warn = 0
        dash.oil_blink = 0
        dash.coolant_blink = 0
        dash.oil_warn = 0
        dash.abs = 0
        dash.obd = 0
        dash.gas_water = 0
        dash.airbag = 0
        dash.battery = 0
        dash.dae = 0
        dash.eco_blink = 0
        dash.eco = 0
        dash.battery_blink = 0
        dash.obd_blink = 0

        # Sync UI with options on startup
        self._sync_ui_from_options()

    @property
    def _dash(self):
        """Convenience accessor for the shared dashboard car state."""
        return self.runner.car.dashboard

    def _sync_ui_from_options(self):
        """Update all UI elements to match current dashboard state."""
        dash = self._dash
        for key in ('airbag_pass', 'seatbelt', 'brakes', 'low_fuel', 'preheat',
                    'warn', 'stop', 'doors', 'esp', 'esp_blink', 'tyre',
                    'backlight', 'on', 'low_beam', 'high_beam', 'fog_front',
                    'fog_rear', 'clig_r', 'clig_l', 'coolant_warn', 'oil_blink',
                    'coolant_blink', 'oil_warn', 'abs', 'obd', 'gas_water',
                    'airbag', 'battery', 'dae', 'eco_blink', 'eco',
                    'battery_blink', 'obd_blink'):
            if key in self.ids:
                self.ids[key].state = 'down' if getattr(dash, key) else 'normal'

    def on_option(self, option, value):
        setattr(self._dash, option, 1 if value == 'down' else 0)

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x036 and len(msg.data) >= 5:
            # Keep combine ignition icon in sync with BSI power mode.
            current_ignition = 1 if int(msg.data[4]) == self._ignition_on else 0
            self._dash.on = current_ignition
            if 'on' in self.ids:
                self.ids['on'].state = 'down' if self._dash.on else 'normal'
            # When ignition state changes, refresh display to ensure UI is visible/active
            if self._last_ignition_state != current_ignition:
                self._last_ignition_state = current_ignition
                if current_ignition:
                    # Force UI refresh when ignition turns on to make indicators visible
                    self._sync_ui_from_options()
        elif msg.arbitration_id == 0x128 and len(msg.data) >= 6:
            # Car state already updated by Msg128.decode(); just sync the UI.
            self._sync_ui_from_options()
        elif msg.arbitration_id == 0x168 and len(msg.data) >= 8:
            # Car state already updated by Msg168.decode(); just sync the UI.
            self._sync_ui_from_options()
