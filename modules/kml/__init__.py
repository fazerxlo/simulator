import datetime
import logging
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from generated.kml_messages import Msg1A3, Msg223, Msg323

_modname = 'KML'
_modversion = '0.0.1'

logger = logging.getLogger(__name__)

class KML(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        # Base init (super and name)
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'KML'
        self.runner = runner

        # Load kv file
        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/kml.kv')
        Builder.apply(self)

        # Register per-CAN-ID message objects.
        logger.debug('registering KML module')
        runner.register_message(Msg1A3())
        runner.register_message(Msg223())
        runner.register_message(Msg323())

        # Initialise KML state on the shared VirtualCar.
        kml = runner.car.kml
        kml.opt = 0
        kml.bits_223 = 0

    @property
    def _kml(self):
        """Convenience accessor for the shared KML car state."""
        return self.runner.car.kml

    def on_opt(self, value):
        self._kml.opt = 1 if value == 'down' else 0

    def on_toggle(self, bit, value):
        if value == 'down':
            self._kml.bits_223 |= 1 << bit
        else:
            self._kml.bits_223 &= ~(1 << bit)

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x1A3 and len(msg.data) >= 2:
            # Msg1A3.decode() has already updated car.kml.opt; sync UI.
            if 'opt' in self.ids:
                self.ids['opt'].state = 'down' if self._kml.opt else 'normal'
        elif msg.arbitration_id == 0x223 and len(msg.data) >= 1:
            # Msg223.decode() has already updated car.kml.bits_223; sync UI.
            for bit in range(8):
                key = f'b{bit}'
                if key in self.ids:
                    self.ids[key].state = 'down' if (self._kml.bits_223 >> bit) & 1 else 'normal'
        elif msg.arbitration_id == 0x323 and len(msg.data) >= 1:
            # Msg323.decode() updated car.kml.bits_323; reflect in UI if present.
            for bit in range(8):
                key = f'b{bit}'
                if key in self.ids:
                    self.ids[key].state = 'down' if (self._kml.bits_323 >> bit) & 1 else 'normal'
