import os

from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Tyres'
_modversion = '0.0.1'

# CAN 0x120 - AEE2004 BSI Alerts Journal - Block 2 (tyre-specific alerts)
# Reference: https://github.com/ludwig-v/arduino-psa-comfort-can-adapter/
#
# Block 2 is identified by data[0] bit7=1, bit6=0 (data[0] = 0x80)
#
# Puncture / Flat tyre  (data[1]):
#   bit 4 = Front Left
#   bit 3 = Front Right
#   bit 2 = Rear Right
#   bit 1 = Rear Left
#
# Under-pressure / Adjust tyre pressure (data[5], data[6]):
#   data[5] bit 1 = Front Left
#   data[5] bit 0 = Front Right
#   data[6] bit 7 = Rear Right
#   data[6] bit 5 = Rear Left
#
# CAN 0x168 - AEE2004 Instrument Panel (dash signals) - generic tyre alerts
# Reference: https://github.com/morcibacsi/PSACANBridge (CAN_168.h)
#   data[1] bit 7 = tyre_pressure_alert (any under-pressure)
#   data[1] bit 6 = flat_tyre_alert     (any flat/puncture)

CAN_ID_BSI_ALERTS  = 0x120
CAN_ID_DASH3       = 0x168

# Block 2 identifier byte
BLOCK2_ID = 0x80


class Tyres(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BSI/Tyre'

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/tyre.kv')
        Builder.apply(self)

        # Per-tire flat/puncture flags
        # Per-tire under-pressure flags
        self.tyres = {
            'fl_flat':     0,
            'fr_flat':     0,
            'rl_flat':     0,
            'rr_flat':     0,
            'fl_pressure': 0,
            'fr_pressure': 0,
            'rl_pressure': 0,
            'rr_pressure': 0,
        }

        # Register periodic CAN message callbacks (every 100 ms)
        runner.register(100, self.can_120_tyre_alerts)
        runner.register(100, self.can_168_tyre)

    def on_toggle(self, flag, value):
        """Called by UI toggle buttons to set/clear individual tyre flags."""
        self.tyres[flag] = 1 if value == 'down' else 0

    def _any_flat(self):
        t = self.tyres
        return t['fl_flat'] or t['fr_flat'] or t['rl_flat'] or t['rr_flat']

    def _any_pressure(self):
        t = self.tyres
        return t['fl_pressure'] or t['fr_pressure'] or t['rl_pressure'] or t['rr_pressure']

    def can_120_tyre_alerts(self):
        """CAN 0x120 Block 2 – per-tire flat and under-pressure alerts.

        Only sends when at least one tyre flag is active so the CAN bus is
        not flooded with messages that do nothing.
        """
        t = self.tyres

        if not (self._any_flat() or self._any_pressure()):
            return CAN_ID_BSI_ALERTS, None

        # data[0]: Block 2 identifier (bit7=1, bit6=0)
        d0 = BLOCK2_ID

        # data[1]: puncture bits (FL=bit4, FR=bit3, RR=bit2, RL=bit1)
        d1 = (t['fl_flat'] << 4) | (t['fr_flat'] << 3) | (t['rr_flat'] << 2) | (t['rl_flat'] << 1)

        # data[5]: under-pressure FL=bit1, FR=bit0
        d5 = (t['fl_pressure'] << 1) | t['fr_pressure']

        # data[6]: under-pressure RR=bit7, RL=bit5
        d6 = (t['rr_pressure'] << 7) | (t['rl_pressure'] << 5)

        return CAN_ID_BSI_ALERTS, [d0, d1, 0x00, 0x00, 0x00, d5, d6, 0x00]

    def can_168_tyre(self):
        """CAN 0x168 – generic flat_tyre_alert and tyre_pressure_alert bits.

        Byte 1 (data[1]):
            bit 7 = tyre_pressure_alert (set when any tyre has low pressure)
            bit 6 = flat_tyre_alert     (set when any tyre is flat/punctured)
        All other bytes sent as 0x00.
        """
        any_flat     = 1 if self._any_flat()     else 0
        any_pressure = 1 if self._any_pressure() else 0

        d1 = (any_pressure << 7) | (any_flat << 6)

        return CAN_ID_DASH3, [0x00, d1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
