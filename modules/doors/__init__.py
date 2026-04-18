import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

_modname = 'Doors'
_version = '0.0.1'

MSG_DOORS_OPEN = 0x0B
MSG_DRIVER_DOOR_OPEN = 0xDE


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

        # Initialise door state on the shared VirtualCar.
        doors = runner.car.doors
        doors.front_left = 0
        doors.front_right = 0
        doors.rear_left = 0
        doors.rear_right = 0
        doors.boot = 0
        doors.bonnet = 0
        doors.rear_window = 0
        doors.fuel_flap = 0
        doors.display_active = False
        doors.popup_msg_id = MSG_DOORS_OPEN

        self._sync_ui()
        self._update_summary()

    @property
    def _doors(self):
        """Convenience accessor for the shared doors car state."""
        return self.runner.car.doors

    def on_toggle(self, field, state):
        if self._ui_sync:
            return
        setattr(self._doors, field, 1 if state == 'down' else 0)
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def open_all(self):
        doors = self._doors
        for key in ('front_left', 'front_right', 'rear_left', 'rear_right',
                    'boot', 'bonnet', 'rear_window', 'fuel_flap'):
            setattr(doors, key, 1)
        self._sync_ui()
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def close_all(self):
        doors = self._doors
        for key in ('front_left', 'front_right', 'rear_left', 'rear_right',
                    'boot', 'bonnet', 'rear_window', 'fuel_flap'):
            setattr(doors, key, 0)
        self._sync_ui()
        self._update_summary()
        self._send_0x220_status()
        self._send_0x1A1_popup()

    def _sync_ui(self):
        self._ui_sync = True
        try:
            doors = self._doors
            for key in ('front_left', 'front_right', 'rear_left', 'rear_right',
                        'boot', 'bonnet', 'rear_window', 'fuel_flap'):
                widget_id = f'door_{key}'
                if widget_id in self.ids:
                    self.ids[widget_id].state = 'down' if getattr(doors, key) else 'normal'
        finally:
            self._ui_sync = False

    def _any_open(self):
        doors = self._doors
        return any(getattr(doors, k) for k in (
            'front_left', 'front_right', 'rear_left', 'rear_right',
            'boot', 'bonnet', 'rear_window', 'fuel_flap'))

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
        doors = self._doors
        for key, label in labels.items():
            if getattr(doors, key):
                opened.append(label)

        if opened:
            self.ids['door_summary'].text = 'Open: ' + ', '.join(opened)
            self.ids['door_summary'].color = (1, 0.8, 0, 1)
        else:
            self.ids['door_summary'].text = 'Open: none'
            self.ids['door_summary'].color = (0, 1, 0, 1)

    def _build_0x220(self):
        doors = self._doors
        b0 = 0x00
        if doors.front_left:
            b0 |= 1 << 7
        if doors.front_right:
            b0 |= 1 << 6
        if doors.rear_left:
            b0 |= 1 << 5
        if doors.rear_right:
            b0 |= 1 << 4
        if doors.boot:
            b0 |= 1 << 3
        if doors.bonnet:
            b0 |= 1 << 2
        if doors.rear_window:
            b0 |= 1 << 1
        if doors.fuel_flap:
            b0 |= 1 << 0
        return [b0, 0x00]

    def _build_0x1A1_door_bytes(self):
        doors = self._doors
        d3 = 0x00
        d4 = 0x00
        if doors.front_right:
            d3 |= 1 << 7
        if doors.front_left:
            d3 |= 1 << 6
        if doors.rear_right:
            d3 |= 1 << 5
        if doors.rear_left:
            d3 |= 1 << 4
        if doors.boot:
            d3 |= 1 << 3
        if doors.bonnet:
            d3 |= 1 << 2
        if doors.rear_window:
            d4 |= 1 << 7
        if doors.fuel_flap:
            d4 |= 1 << 6
        return d3, d4

    def _send_0x220_status(self):
        self.runner.send_message(0x220, self._build_0x220())

    def _popup_message_id(self):
        doors = self._doors
        if doors.front_left and not any((
            doors.front_right, doors.rear_left, doors.rear_right,
            doors.boot, doors.bonnet, doors.rear_window, doors.fuel_flap,
        )):
            return MSG_DRIVER_DOOR_OPEN
        return MSG_DOORS_OPEN

    def _send_0x1A1_popup(self):
        if self._pending_show_ev is not None:
            self._pending_show_ev.cancel()
            self._pending_show_ev = None

        if self._pending_clear_ev is not None:
            self._pending_clear_ev.cancel()
            self._pending_clear_ev = None

        if self._any_open():
            self._doors.display_active = True
            self._doors.popup_msg_id = self._popup_message_id()
            # Real dumps show a 0x00/0x80 toggle with the same message id.
            self.runner.send_message(0x1A1, [0x00, self._doors.popup_msg_id, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00])
            self._pending_show_ev = Clock.schedule_once(self._send_popup_show, 0.05)
            return

        self._doors.display_active = True
        self.runner.send_message(0x1A1, [0x00, self._doors.popup_msg_id, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00])
        self._pending_clear_ev = Clock.schedule_once(self._send_popup_clear, 0.2)

    def _send_popup_show(self, _dt):
        self._pending_show_ev = None
        if not self._any_open():
            return
        self.runner.send_message(0x1A1, [0x80, self._doors.popup_msg_id, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00])

    def _send_popup_clear(self, _dt):
        self._pending_clear_ev = None
        self._doors.display_active = False

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x220 and len(msg.data) >= 2:
            b0 = msg.data[0]
            doors = self._doors
            doors.front_left = (b0 >> 7) & 0x01
            doors.front_right = (b0 >> 6) & 0x01
            doors.rear_left = (b0 >> 5) & 0x01
            doors.rear_right = (b0 >> 4) & 0x01
            doors.boot = (b0 >> 3) & 0x01
            doors.bonnet = (b0 >> 2) & 0x01
            doors.rear_window = (b0 >> 1) & 0x01
            doors.fuel_flap = (b0 >> 0) & 0x01
            self._sync_ui()
            self._update_summary()
