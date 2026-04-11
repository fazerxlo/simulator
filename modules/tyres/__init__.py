import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from modules import messages_1a1

_modname = 'Tyres'
_version = '0.0.2'

# Tire states
TIRE_OK = 0
TIRE_LOW = 1
TIRE_FLAT = 2
TIRE_NO_DATA = 3

TIRE_STATES = ['OK', 'LOW', 'FLAT', 'NO DATA']

# BSI log message IDs for tyre warnings (0x1A1)
MSG_PRESSURE_LOW = 0x8D
MSG_PRESSURE_NOT_MONITORED = 0xE5
MSG_MULTIPLE_FLAT = 0x0D
MSG_DIAGNOSTIC_OK = 0x00

TYRE_QUICK_MESSAGES = {
    'not_monitored': MSG_PRESSURE_NOT_MONITORED,
    'ok': MSG_DIAGNOSTIC_OK,
    'flat_tire': MSG_MULTIPLE_FLAT,
    'low_pressure': MSG_PRESSURE_LOW,
}


class Tyres(TabbedPanelItem):
    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Tyres'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/tyres.kv')
        Builder.apply(self)

        self.tyre_state = {
            'fl': TIRE_OK,
            'fr': TIRE_OK,
            'rl': TIRE_OK,
            'rr': TIRE_OK,
        }

        # 0x1A1 display state machine
        self.msg_flag = 0xFF
        self.msg_id = 0x00
        self.mess = 0x00
        self.runner.tyres_display_active = False

        self._update_labels()

        runner.register(100, self.can_message)

    # --- Generic 0x1A1 system message controls (like bsi-log) ---

    def on_mess(self, mess):
        if mess < 0:
            mess = 0
        if mess > 0xFF:
            mess = 0xFF
        self.mess = int(mess)
        self.ids['cur_mess'].text = f'{self.mess}'
        if self.ids['slider_mess'].value != mess:
            self.ids['slider_mess'].value = mess
        if self.mess in messages_1a1.messages:
            self.ids['send'].text = f'send {messages_1a1.messages[self.mess]}'
        else:
            self.ids['send'].text = 'send (inconnu)'

    def dec_mess(self):
        self.on_mess(self.mess - 1)
        self.show_msg(self.mess)

    def inc_mess(self):
        self.on_mess(self.mess + 1)
        self.show_msg(self.mess)

    def send_tyre_message(self, message_key):
        if message_key not in TYRE_QUICK_MESSAGES:
            return
        msg_id = TYRE_QUICK_MESSAGES[message_key]
        self.on_mess(msg_id)
        self.show_msg(msg_id)

    def show_msg(self, id=None):
        if id and self.msg_flag == 0xFF:
            self.msg_id = int(id)
            self.msg_flag = 0x80
            self._update_status()
            self._sync_runner_display_state()
            Clock.schedule_once(self.show_msg, 2)
        elif id == self.msg_id and self.msg_flag != 0xFF:
            pass  # double call guard
        elif self.msg_flag == 0x80:
            self.msg_flag = 0x7F
            self._sync_runner_display_state()
            Clock.schedule_once(self.show_msg, 0.2)
        elif self.msg_flag == 0x7F:
            self.msg_flag = 0xFF
            self.msg_id = 0x00
            self._update_status()
            self._sync_runner_display_state()

    def _update_status(self):
        if 'status_msg' in self.ids:
            if self.msg_flag != 0xFF and self.msg_id in messages_1a1.messages:
                self.ids['status_msg'].text = messages_1a1.messages[self.msg_id]
                self.ids['status_msg'].color = (1, 0.8, 0, 1)
            else:
                self.ids['status_msg'].text = '-'
                self.ids['status_msg'].color = (0.5, 0.5, 0.5, 1)

    def _sync_runner_display_state(self):
        self.runner.tyres_display_active = (self.msg_flag != 0xFF)

    def can_message(self):
        if self.msg_flag == 0xFF:
            return 0x1A1, None
        b2 = 0xF0 if self.msg_flag != 0xFF else 0x00
        return 0x1A1, [self.msg_flag, self.msg_id, b2, 0x00, 0x00, 0x00, 0x00, 0x00]

    # --- Tyre state controls ---

    def on_state_change(self, tyre, state_text):
        idx = TIRE_STATES.index(state_text)
        self.tyre_state[tyre] = idx
        self._update_label(tyre)
        self._trigger_warning()

    def _trigger_warning(self):
        worst = TIRE_OK
        flat_count = 0
        for state in self.tyre_state.values():
            if state == TIRE_FLAT:
                flat_count += 1
            if state > worst:
                worst = state

        if worst == TIRE_OK:
            return

        if flat_count > 1:
            msg_id = MSG_MULTIPLE_FLAT
        elif worst == TIRE_FLAT:
            msg_id = MSG_PRESSURE_LOW
        elif worst == TIRE_LOW:
            msg_id = MSG_PRESSURE_LOW
        else:
            msg_id = MSG_PRESSURE_NOT_MONITORED

        self.show_msg(msg_id)

    def _update_labels(self):
        for tyre in self.tyre_state:
            self._update_label(tyre)

    def _update_label(self, tyre):
        label_id = f'state_{tyre}'
        if label_id in self.ids:
            state = self.tyre_state[tyre]
            text = TIRE_STATES[state]
            self.ids[label_id].text = text
            if state == TIRE_OK:
                self.ids[label_id].color = (0, 1, 0, 1)
            elif state == TIRE_LOW:
                self.ids[label_id].color = (1, 0.8, 0, 1)
            elif state == TIRE_FLAT:
                self.ids[label_id].color = (1, 0, 0, 1)
            else:
                self.ids[label_id].color = (0.5, 0.5, 0.5, 1)

    # --- Monitor mode ---

    def on_can_message(self, msg):
        if msg.arbitration_id != 0x1A1 or len(msg.data) < 2:
            return
        self.msg_flag = msg.data[0]
        self.msg_id = msg.data[1]
        self._update_status()
        self._sync_runner_display_state()
        self.ids['cur_mess'].text = f'{self.msg_id}'
        if self.ids['slider_mess'].value != self.msg_id:
            self.ids['slider_mess'].value = self.msg_id
        if self.msg_id in messages_1a1.messages:
            self.ids['send'].text = f'send {messages_1a1.messages[self.msg_id]}'
        else:
            self.ids['send'].text = 'send (inconnu)'
