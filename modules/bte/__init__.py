import datetime
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from can_messages import Msg12B

_modname = 'BTE'
_modversion = '0.0.1'

class BTE(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'BTE'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/ui.kv')
        Builder.apply(self)

        # Register per-CAN-ID message object.
        print('registering BSI calls')
        runner.register_message(Msg12B())

        # Initialise BTE state on the shared VirtualCar.
        runner.car.bte.bits = 0

    @property
    def _bte(self):
        """Convenience accessor for the shared BTE car state."""
        return self.runner.car.bte

    def on_toggle(self, bit, value):
        if value == 'down':
            self._bte.bits |= 1 << bit
        else:
            self._bte.bits &= ~(1 << bit)

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x12B and len(msg.data) >= 1:
            # Msg12B.decode() has already updated car.bte.bits; sync UI.
            for bit in range(8):
                key = f'b{bit}'
                if key in self.ids:
                    self.ids[key].state = 'down' if (self._bte.bits >> bit) & 1 else 'normal'
