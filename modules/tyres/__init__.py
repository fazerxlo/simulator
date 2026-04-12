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

TYRE_MESSAGE_PAYLOADS = {
    MSG_DIAGNOSTIC_OK: {
        'active': [0x80, 0x00, 0x58, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
        'clear': [0x00, 0x00, 0x58, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF],
    },
    MSG_PRESSURE_NOT_MONITORED: {
        'active': [0x80, 0xE5, 0xC7, 0x1E, 0x40, 0x00, 0x00, 0x00],
        'clear': [0x00, 0xE5, 0x47, 0x1E, 0x40, 0x00, 0x00, 0x00],
    },
    MSG_PRESSURE_LOW: {
        'active': [0x80, 0x8D, 0xC7, 0x1E, 0x40, 0x00, 0x00, 0x00],
        'clear': [0x00, 0x8D, 0x47, 0x1E, 0x40, 0x00, 0x00, 0x00],
    },
    MSG_MULTIPLE_FLAT: {
        'active': [0x80, 0x0D, 0xC7, 0x1E, 0x40, 0x00, 0x00, 0x00],
        'clear': [0x00, 0x0D, 0x47, 0x1E, 0x40, 0x00, 0x00, 0x00],
    },
}

TYRE_ORDER = ('fl', 'fr', 'rr', 'rl')


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
            self._send_manual_frame('active')
            Clock.schedule_once(self.show_msg, 2)
        elif id == self.msg_id and self.msg_flag != 0xFF:
            pass  # double call guard
        elif self.msg_flag == 0x80:
            self.msg_flag = 0x00
            self._sync_runner_display_state()
            self._send_manual_frame('clear')
            Clock.schedule_once(self.show_msg, 0.2)
        elif self.msg_flag == 0x00:
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

    def _send_manual_frame(self, phase):
        payload = self._build_payload(self.msg_id, phase)
        self.runner.send_message(0x1A1, payload)

    def _build_payload(self, msg_id, phase):
        template = TYRE_MESSAGE_PAYLOADS.get(msg_id)
        if template is not None:
            payload = list(template[phase])
        elif phase == 'active':
            payload = [0x80, msg_id, 0xC6, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
        else:
            payload = [0x00, msg_id, 0x46, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

        # Dynamically set byte 3 for tyre-specific messages using a bitmask.
        # According to arduino-psa-comfort-can-adapter:
        #   bit 7: Front Left, bit 6: Front Right, bit 5: Rear Right, bit 4: Rear Left
        if msg_id in (MSG_PRESSURE_LOW, MSG_PRESSURE_NOT_MONITORED, MSG_MULTIPLE_FLAT):
            param = 0x00
            if self.tyre_state['fl'] != TIRE_OK:
                param |= 0x80
            if self.tyre_state['fr'] != TIRE_OK:
                param |= 0x40
            if self.tyre_state['rr'] != TIRE_OK:
                param |= 0x20
            if self.tyre_state['rl'] != TIRE_OK:
                param |= 0x10
            if param != 0:
                payload[3] = param

        return payload

    # --- Tyre state controls ---

    def on_state_change(self, tyre, state_text):
        idx = TIRE_STATES.index(state_text)
        self.tyre_state[tyre] = idx
        self._update_label(tyre)

        self._trigger_warning()
        self._send_0x120_status()

    def _send_0x120_status(self):
        self.runner.send_message(0x120, self._build_0x120_block2())
        self.runner.send_message(0x120, self._build_0x120_block3())

    def _build_0x120_block2(self):
        payload = [0xBC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        puncture_bits = {
            'fl': (1, 4),
            'fr': (1, 3),
            'rr': (1, 2),
            'rl': (1, 1),
        }
        low_bits = {
            'fl': (5, 1),
            'fr': (5, 0),
            'rr': (6, 7),
            'rl': (6, 5),
        }

        for tyre in TYRE_ORDER:
            state = self.tyre_state[tyre]
            if state == TIRE_FLAT:
                byte_index, bit_index = puncture_bits[tyre]
                payload[byte_index] |= 1 << bit_index
            elif state == TIRE_LOW:
                byte_index, bit_index = low_bits[tyre]
                payload[byte_index] |= 1 << bit_index

        return payload

    def _build_0x120_block3(self):
        payload = [0xFC, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        monitor_fault_bits = {
            'fl': (5, 3),
            'fr': (5, 2),
            'rr': (5, 1),
            'rl': (5, 0),
        }
        underinflation_bits = {
            'fl': (7, 7),
            'fr': (7, 6),
            'rr': (7, 5),
        }

        for tyre in TYRE_ORDER:
            state = self.tyre_state[tyre]
            if state == TIRE_NO_DATA:
                byte_index, bit_index = monitor_fault_bits[tyre]
                payload[byte_index] |= 1 << bit_index
            elif state == TIRE_LOW and tyre in underinflation_bits:
                byte_index, bit_index = underinflation_bits[tyre]
                payload[byte_index] |= 1 << bit_index

        return payload

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
