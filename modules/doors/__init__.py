import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Doors'
_version = '0.0.1'

MSG_DOORS_OPEN = 0x0B


class Doors(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Doors'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/doors.kv')
        Builder.apply(self)

        self._ui_sync = False
        self._pending_clear_ev = None
        self._pending_show_ev = None
        self.door_state = {
            'front_left': 0,
            'front_right': 0,
            'rear_left': 0,
            'rear_right': 0,
            'boot': 0,
            'bonnet': 0,
            'rear_window': 0,
            'fuel_flap': 0,
        }

        self._sync_ui()
        self._update_summary()

    def on_toggle(self, field, state):
        if self._ui_sync:
            return
        self.door_state[field] = 1 if state == 'down' else 0
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def open_all(self):
        for key in self.door_state:
            self.door_state[key] = 1
        self._sync_ui()
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def close_all(self):
        for key in self.door_state:
            self.door_state[key] = 0
        self._sync_ui()
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def _sync_ui(self):
        self._ui_sync = True
        try:
            for key in self.door_state:
                widget_id = f'door_{key}'
                if widget_id in self.ids:
                    self.ids[widget_id].state = 'down' if self.door_state[key] else 'normal'
        finally:
            self._ui_sync = False

    def _any_open(self):
        return any(self.door_state.values())

    def _update_summary(self):
        if 'door_summary' not in self.ids:
            return

        opened = []
        labels = {
            'front_left': 'FL',
            'front_right': 'FR',
            'rear_left': 'RL',
            'rear_right': 'RR',
            'boot': 'BOOT',
            'bonnet': 'BONNET',
            'rear_window': 'REAR WINDOW',
            'fuel_flap': 'FUEL FLAP',
        }
        for key, value in self.door_state.items():
            if value:
                opened.append(labels[key])

        if opened:
            self.ids['door_summary'].text = 'Open: ' + ', '.join(opened)
            self.ids['door_summary'].color = (1, 0.8, 0, 1)
        else:
            self.ids['door_summary'].text = 'Open: none'
            self.ids['door_summary'].color = (0, 1, 0, 1)

    def _build_0x220(self):
        b0 = 0x00
        if self.door_state['front_left']:
            b0 |= 1 << 7
        if self.door_state['front_right']:
            b0 |= 1 << 6
        if self.door_state['rear_left']:
            b0 |= 1 << 5
        if self.door_state['rear_right']:
            b0 |= 1 << 4
        if self.door_state['boot']:
            b0 |= 1 << 3
        if self.door_state['bonnet']:
            b0 |= 1 << 2
        if self.door_state['rear_window']:
            b0 |= 1 << 1
        if self.door_state['fuel_flap']:
            b0 |= 1 << 0
        return [b0, 0x00]

    def _build_0x1A1_door_bytes(self):
        d3 = 0x00
        d4 = 0x00
        if self.door_state['front_right']:
            d3 |= 1 << 7
        if self.door_state['front_left']:
            d3 |= 1 << 6
        if self.door_state['rear_right']:
            d3 |= 1 << 5
        if self.door_state['rear_left']:
            d3 |= 1 << 4
        if self.door_state['boot']:
            d3 |= 1 << 3
        if self.door_state['bonnet']:
            d3 |= 1 << 2
        if self.door_state['rear_window']:
            d4 |= 1 << 7
        if self.door_state['fuel_flap']:
            d4 |= 1 << 6
        return d3, d4

    def _send_0x220_status(self):
        self.runner.send_message(0x220, self._build_0x220())

    def _send_0x1A1_popup(self):
        if self._pending_show_ev is not None:
            self._pending_show_ev.cancel()
            self._pending_show_ev = None

        if self._pending_clear_ev is not None:
            self._pending_clear_ev.cancel()
            self._pending_clear_ev = None

        if self._any_open():
            # Some clusters keep the first opened-door context until popup is refreshed.
            self.runner.send_message(0x1A1, [0x7F, MSG_DOORS_OPEN, 0x47, 0x00, 0x00, 0x00, 0x00, 0x00])
            self._pending_show_ev = Clock.schedule_once(self._send_popup_show, 0.05)
            return

        self.runner.send_message(0x1A1, [0x7F, MSG_DOORS_OPEN, 0x47, 0x00, 0x00, 0x00, 0x00, 0x00])
        self._pending_clear_ev = Clock.schedule_once(self._send_popup_clear, 0.2)

    def _send_popup_show(self, _dt):
        self._pending_show_ev = None
        if not self._any_open():
            return
        d3, d4 = self._build_0x1A1_door_bytes()
        self.runner.send_message(0x1A1, [0x80, MSG_DOORS_OPEN, 0xC7, d3, d4, 0x00, 0x00, 0x00])

    def _send_popup_clear(self, _dt):
        self._pending_clear_ev = None
        self.runner.send_message(0x1A1, [0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x220 and len(msg.data) >= 2:
            b0 = msg.data[0]
            self.door_state['front_left'] = (b0 >> 7) & 0x01
            self.door_state['front_right'] = (b0 >> 6) & 0x01
            self.door_state['rear_left'] = (b0 >> 5) & 0x01
            self.door_state['rear_right'] = (b0 >> 4) & 0x01
            self.door_state['boot'] = (b0 >> 3) & 0x01
            self.door_state['bonnet'] = (b0 >> 2) & 0x01
            self.door_state['rear_window'] = (b0 >> 1) & 0x01
            self.door_state['fuel_flap'] = (b0 >> 0) & 0x01
            self._sync_ui()
            self._update_summary()