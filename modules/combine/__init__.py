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

        # Mark dashboard as active so tyres module defers 0x168 to combine.
        runner.car.dashboard.active = True

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/combine.kv')
        Builder.apply(self)

        # Register CAN callbacks
        print('registering radio calls')
        runner.register(100, self.can_combine_indicators)
        runner.register(100, self.can_combine_signals)

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

    def can_combine_indicators(self):
        dash = self._dash
        b0 = dash.airbag_pass << 7 | dash.seatbelt << 6 | dash.brakes << 5 | dash.low_fuel << 4 | dash.preheat << 2
        b1 = dash.warn << 7 | dash.stop << 6 | dash.doors << 4
        b2 = dash.esp << 5 | dash.esp_blink << 4
        b3 = dash.tyre << 6
        b4 = (dash.backlight << 7 | dash.low_beam << 6 | dash.high_beam << 5 |
              dash.fog_front << 4 | dash.fog_rear << 3 | dash.clig_r << 2 | dash.clig_l << 1)
        b5 = dash.on << 7
        return 0x128, [b0, b1, b2, b3, b4, b5, 0x00, 0x00]

    def can_combine_signals(self):
        dash = self._dash
        b0 = dash.coolant_warn << 7 | dash.oil_blink << 6 | dash.coolant_blink << 5 | dash.oil_warn << 3
        tyre_overlay = int(self.runner.car.tyres.alert_0x168_b1) & 0xC0
        b1 = tyre_overlay if tyre_overlay else (dash.tyre << 6)
        b3 = dash.abs << 5 | dash.esp << 4 | dash.obd << 1 | dash.gas_water
        b4 = dash.airbag << 5 | dash.battery << 1
        b6 = dash.dae << 5 | dash.eco_blink << 1 | dash.eco
        b7 = dash.battery_blink << 7 | dash.obd_blink << 6
        return 0x168, [b0, b1, 0x00, b3, b4, 0x00, b6, b7]

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
            data = msg.data
            dash = self._dash
            dash.airbag_pass = (data[0] >> 7) & 1
            dash.seatbelt = (data[0] >> 6) & 1
            dash.brakes = (data[0] >> 5) & 1
            dash.low_fuel = (data[0] >> 4) & 1
            dash.preheat = (data[0] >> 2) & 1
            dash.warn = (data[1] >> 7) & 1
            dash.stop = (data[1] >> 6) & 1
            dash.doors = (data[1] >> 4) & 1
            dash.esp = (data[2] >> 5) & 1
            dash.esp_blink = (data[2] >> 4) & 1
            dash.tyre = (data[3] >> 6) & 1
            dash.backlight = (data[4] >> 7) & 1
            dash.low_beam = (data[4] >> 6) & 1
            dash.high_beam = (data[4] >> 5) & 1
            dash.fog_front = (data[4] >> 4) & 1
            dash.fog_rear = (data[4] >> 3) & 1
            dash.clig_r = (data[4] >> 2) & 1
            dash.clig_l = (data[4] >> 1) & 1
            dash.on = (data[5] >> 7) & 1
            self._sync_ui_from_options()
        elif msg.arbitration_id == 0x168 and len(msg.data) >= 8:
            data = msg.data
            dash = self._dash
            dash.coolant_warn = (data[0] >> 7) & 1
            dash.oil_blink = (data[0] >> 6) & 1
            dash.coolant_blink = (data[0] >> 5) & 1
            dash.oil_warn = (data[0] >> 3) & 1
            dash.tyre = (data[1] >> 6) & 1
            dash.abs = (data[3] >> 5) & 1
            dash.esp = (data[3] >> 4) & 1
            dash.obd = (data[3] >> 1) & 1
            dash.gas_water = data[3] & 1
            dash.airbag = (data[4] >> 5) & 1
            dash.battery = (data[4] >> 1) & 1
            dash.dae = (data[6] >> 5) & 1
            dash.eco_blink = (data[6] >> 1) & 1
            dash.eco = data[6] & 1
            dash.battery_blink = (data[7] >> 7) & 1
            dash.obd_blink = (data[7] >> 6) & 1
            self._sync_ui_from_options()

