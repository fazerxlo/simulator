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

        runner.register(100, self.can_panel)
        runner.register(100, self.can_volume)

        self.panel = {
            'source': 0,
            'trip': 0,
            'clima': 0,
            'tel': 0,
            'dark': 0,
            'ok': 0,
            'esc': 0,
            'up': 0,
            'down': 0,
            'next': 0,
            'prev': 0,
            'right': 0,
            'left': 0,
        }
        self._button_ids = {f'btn_{k}': k for k in self.panel.keys()}
        self._pulse_ticks = {k: 0 for k in self.panel.keys()}
        self._pulse_window_ticks = 3

        self.volume = 15
        self.volflag = 0xE0
        self._volume_action_ticks = 0

        self._sync_ui_from_state()

    def _sync_ui_from_state(self):
        for wid, key in self._button_ids.items():
            value = self.panel[key]
            if wid in self.ids:
                desired = 'down' if value else 'normal'
                if self.ids[wid].state != desired:
                    self.ids[wid].state = desired
        self._update_pressed_label()
        self.ids['cur_vol'].text = f'volume: {self.volume}'

    def _update_pressed_label(self):
        pressed = [name for name, value in self.panel.items() if value]
        self.ids['pressed_keys'].text = ', '.join(pressed) if pressed else '-'

    def _set_button_state(self, key, pressed):
        wid = f'btn_{key}'
        if wid in self.ids:
            desired = 'down' if pressed else 'normal'
            if self.ids[wid].state != desired:
                self.ids[wid].state = desired

    def press_key(self, key):
        if key not in self.panel:
            return
        self.panel[key] = 1
        self._pulse_ticks[key] = self._pulse_window_ticks
        self._set_button_state(key, True)
        self._update_pressed_label()

    def _step_pulses(self):
        changed = False
        for key in self.panel:
            if self._pulse_ticks[key] > 0:
                self._pulse_ticks[key] -= 1
                if self._pulse_ticks[key] == 0 and self.panel[key] != 0:
                    self.panel[key] = 0
                    self._set_button_state(key, False)
                    changed = True
        if changed:
            self._update_pressed_label()

    def pulse_volume(self, direction):
        if direction == 'up':
            self.volume = min(30, self.volume + 1)
        else:
            self.volume = max(0, self.volume - 1)
        self.volflag = 0x00
        self._volume_action_ticks = 3
        self.ids['cur_vol'].text = f'volume: {self.volume}'

    def can_volume(self):
        if self._volume_action_ticks > 0:
            self._volume_action_ticks -= 1
            if self._volume_action_ticks == 0:
                self.volflag = 0xE0
        return 0x1A5, [self.volflag | self.volume]

    def can_panel(self):
        p = self.panel
        b0 = (p['tel'] << 4) | p['clima']
        b1 = (p['trip'] << 6) | (p['source'] << 4) | p['dark']
        b2 = (p['ok'] << 6) | (p['esc'] << 4) | (p['next'] << 2) | p['prev']
        b5 = (p['up'] << 6) | (p['down'] << 4) | (p['right'] << 2) | p['left']
        self._step_pulses()
        return 0x3E5, [b0, b1, b2, 0x00, 0x00, b5]

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x1A5 and len(msg.data) >= 1:
            self.volume = int(msg.data[0]) & 0x1F
            self.ids['cur_vol'].text = f'volume: {self.volume}'
            return

        if msg.arbitration_id != 0x3E5 or len(msg.data) < 6:
            return

        b1 = msg.data[1]
        b2 = msg.data[2]
        b5 = msg.data[5]
        b0 = msg.data[0]

        self.panel['trip'] = (b1 >> 6) & 1
        self.panel['source'] = (b1 >> 4) & 1
        self.panel['dark'] = b1 & 1
        self.panel['tel'] = (b0 >> 4) & 1
        self.panel['clima'] = b0 & 1
        self.panel['ok'] = (b2 >> 6) & 1
        self.panel['esc'] = (b2 >> 4) & 1
        self.panel['next'] = (b2 >> 2) & 1
        self.panel['prev'] = b2 & 1
        self.panel['up'] = (b5 >> 6) & 1
        self.panel['down'] = (b5 >> 4) & 1
        self.panel['right'] = (b5 >> 2) & 1
        self.panel['left'] = b5 & 1

        self._sync_ui_from_state()
