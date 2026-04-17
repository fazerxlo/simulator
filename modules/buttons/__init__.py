import os

from kivy.lang.builder import Builder
from kivy.uix.tabbedpanel import TabbedPanelItem

_modname = 'Buttons'
_modversion = '0.0.1'


class Buttons(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Buttons'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/buttons.kv')
        Builder.apply(self)

        # Mark the buttons subsystem as active so Msg1A5 / Msg3E5 use the
        # buttons encoding path rather than the radio-gen path.
        runner.car.buttons.active = True

        # No register_message() call here — bsi-base already registered Msg1A5
        # and Msg3E5 for all modules.  Setting car.buttons.active switches the
        # encoding inside those objects automatically.

        self._button_ids = {f'btn_{k}': k for k in runner.car.buttons.panel}

        self._sync_ui_from_state()

    @property
    def _buttons(self):
        """Convenience accessor for the shared buttons car state."""
        return self.runner.car.buttons

    def _sync_ui_from_state(self):
        b = self._buttons
        for wid, key in self._button_ids.items():
            if wid in self.ids:
                desired = 'down' if b.panel.get(key) else 'normal'
                if self.ids[wid].state != desired:
                    self.ids[wid].state = desired
        self._update_pressed_label()
        self.ids['cur_vol'].text = f'volume: {b.volume}'

    def _update_pressed_label(self):
        pressed = [k for k, v in self._buttons.panel.items() if v]
        self.ids['pressed_keys'].text = ', '.join(pressed) if pressed else '-'

    def _set_button_state(self, key, pressed):
        wid = f'btn_{key}'
        if wid in self.ids:
            desired = 'down' if pressed else 'normal'
            if self.ids[wid].state != desired:
                self.ids[wid].state = desired

    def press_key(self, key):
        b = self._buttons
        if key not in b.panel:
            return
        b.press(key)
        self._set_button_state(key, True)
        self._update_pressed_label()

    def pulse_volume(self, direction):
        b = self._buttons
        if direction == 'up':
            b.volume_up()
        else:
            b.volume_down()
        self.ids['cur_vol'].text = f'volume: {b.volume}'

    def on_can_message(self, msg):
        b = self._buttons
        if msg.arbitration_id == 0x1A5 and len(msg.data) >= 1:
            # Msg1A5.decode() has already updated car.buttons.volume; sync UI.
            self.ids['cur_vol'].text = f'volume: {b.volume}'
            return

        if msg.arbitration_id != 0x3E5 or len(msg.data) < 6:
            return

        # Msg3E5.decode() has already updated car.buttons.panel; sync UI.
        # Also reflect any pulse-timer-cleared keys in the UI.
        for key, value in b.panel.items():
            self._set_button_state(key, bool(value))
        self._update_pressed_label()
