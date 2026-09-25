import os

from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.lang.builder import Builder

from generated.tyres_messages import Msg1E1, Msg361, Msg3A1
from modules import messages_1a1

_modname = 'Tyres'
_version = '0.2.0'

# Tire states (RT4 CAN 2004 enum: 0=OK, 1=LOW, 2=FLAT, 3=NO_DATA, 4=BATTERY_LOW)
TIRE_OK = 0
TIRE_LOW = 1
TIRE_FLAT = 2
TIRE_NO_DATA = 3
TIRE_BATTERY_LOW = 4

TIRE_STATES = ['OK', 'LOW', 'FLAT', 'NO DATA', 'BATTERY LOW']

# BSI log message IDs for tyre warnings (0x1A1)
MSG_DIAGNOSTIC_OK = 0x00
MSG_MULTIPLE_FLAT = 0x0D
MSG_PRESSURE_LOW = 0x8D
MSG_PRESSURE_NOT_MONITORED = 0xE5
MSG_HIGH_SPEED_CHECK = 0xE7
MSG_UNDERINFLATED = 0xE8

TYRE_QUICK_MESSAGES = {
    'ok': MSG_DIAGNOSTIC_OK,
    'flat_tire': MSG_MULTIPLE_FLAT,
    'low_pressure': MSG_PRESSURE_LOW,
    'not_monitored': MSG_PRESSURE_NOT_MONITORED,
    'high_speed': MSG_HIGH_SPEED_CHECK,
    'underinflated': MSG_UNDERINFLATED,
}

TYRE_MESSAGE_PAYLOADS = {
    MSG_DIAGNOSTIC_OK: {
        'active': [0x80, 0x00, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0x00, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
    MSG_PRESSURE_NOT_MONITORED: {
        'active': [0x80, 0xE5, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0xE5, 0x46, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
    MSG_PRESSURE_LOW: {
        'active': [0x80, 0x8D, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0x8D, 0x46, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
    MSG_MULTIPLE_FLAT: {
        'active': [0x80, 0x0D, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0x0D, 0x46, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
    MSG_HIGH_SPEED_CHECK: {
        'active': [0x80, 0xE7, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0xE7, 0x46, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
    MSG_UNDERINFLATED: {
        'active': [0x80, 0xE8, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00],
        'clear': [0x00, 0xE8, 0x46, 0x00, 0x00, 0x00, 0x00, 0x00],
    },
}

ALL_TYRES = ('fl', 'fr', 'rr', 'rl', 'spare')
ROAD_TYRES = ('fl', 'fr', 'rr', 'rl')
TYRE_ORDER = ('fl', 'fr', 'rr', 'rl')


class Tyres(TabbedPanelItem):
    _popup_timer = None

    def __init__(self, runner, **kwargs):
        super(TabbedPanelItem, self).__init__(**kwargs)
        self.text = 'Tyres'
        self.runner = runner

        self.kv = Builder.load_file(f'{os.path.dirname(__file__)}/tyres.kv')
        Builder.apply(self)

        # Register periodic CAN message objects for 0x361, 0x1E1, and 0x3A1
        runner.register_message(Msg361())
        runner.register_message(Msg1E1())
        runner.register_message(Msg3A1())

        # 0x1A1 display state machine
        self.msg_flag = 0xFF
        self.msg_id = 0x00
        self.mess = 0x00
        self._popup_timer = None

        # Initialise tyre state on the shared VirtualCar.
        tyres = runner.car.tyres
        tyres.fl = TIRE_OK
        tyres.fr = TIRE_OK
        tyres.rl = TIRE_OK
        tyres.rr = TIRE_OK
        tyres.spare = TIRE_OK
        tyres.pressure_fl = 2.4
        tyres.pressure_fr = 2.4
        tyres.pressure_rr = 2.2
        tyres.pressure_rl = 2.2
        tyres.tpms_system_state = 0x20
        tyres.display_active = False
        tyres.popup_msg_id = MSG_PRESSURE_LOW
        tyres.popup_flag = 0x80
        tyres.display_flags = 0xC6
        tyres.alert_0x168_b1 = 0

        self._update_labels()
        self._update_pressure_displays()
        self._update_system_buttons()

    @property
    def _tyres(self):
        """Convenience accessor for the shared tyres car state."""
        return self.runner.car.tyres

    @property
    def tyre_state(self):
        """Dict-like view of the shared tyre states for backward compatibility."""
        t = self._tyres
        return {'fl': t.fl, 'fr': t.fr, 'rl': t.rl, 'rr': t.rr, 'spare': t.spare}

    def _set_tyre(self, tyre, state):
        setattr(self._tyres, tyre, state)

    # --- Generic 0x1A1 system message controls ---

    def on_mess(self, mess):
        if mess < 0:
            mess = 0
        if mess > 0xFF:
            mess = 0xFF
        self.mess = int(mess)
        if 'cur_mess' in self.ids:
            self.ids['cur_mess'].text = f'{self.mess}'
        if 'slider_mess' in self.ids and self.ids['slider_mess'].value != mess:
            self.ids['slider_mess'].value = mess
        if 'send' in self.ids:
            if self.mess in messages_1a1.messages:
                self.ids['send'].text = f'send {messages_1a1.messages[self.mess]}'
            else:
                self.ids['send'].text = 'send (inconnu)'

    def dec_mess(self):
        self.on_mess(self.mess - 1)
        self.trigger_popup(self.mess)

    def inc_mess(self):
        self.on_mess(self.mess + 1)
        self.trigger_popup(self.mess)

    def send_tyre_message(self, message_key):
        if message_key not in TYRE_QUICK_MESSAGES:
            return
        msg_id = TYRE_QUICK_MESSAGES[message_key]
        self.on_mess(msg_id)
        if msg_id == MSG_DIAGNOSTIC_OK:
            self.clear_popup()
        else:
            self.trigger_popup(msg_id)

    def show_msg(self, id=None):
        """Compatibility wrapper for show_msg."""
        msg_id = int(id) if id is not None else self.mess
        self.trigger_popup(msg_id)

    @staticmethod
    def _tyre_status_bytes(tyres) -> tuple[int, int]:
        d3 = 0x00
        if getattr(tyres, 'fl', 0) != 0:
            d3 |= 1 << 4
        if getattr(tyres, 'fr', 0) != 0:
            d3 |= 1 << 3
        if getattr(tyres, 'rr', 0) != 0:
            d3 |= 1 << 2
        if getattr(tyres, 'rl', 0) != 0:
            d3 |= 1 << 1
        if getattr(tyres, 'spare', 0) != 0:
            d3 |= 1 << 0
        return d3, 0x00

    def trigger_popup(self, msg_id=None, duration=4.0):
        if msg_id is None:
            worst = self._worst_state()
            if worst == TIRE_OK:
                self.clear_popup()
                return
            elif worst == TIRE_FLAT:
                msg_id = MSG_MULTIPLE_FLAT
            elif worst == TIRE_LOW:
                msg_id = MSG_PRESSURE_LOW
            else:
                msg_id = MSG_PRESSURE_NOT_MONITORED

        self.msg_id = int(msg_id)
        self.msg_flag = 0x80
        self._tyres.popup_msg_id = self.msg_id
        self._tyres.popup_flag = 0x80
        self._tyres.display_active = True
        self._update_status()

        # Send immediate burst to ensure instant reception by displays
        payload = self._build_payload(self.msg_id, 'active')
        self.runner.send_message(0x1A1, payload)
        self._send_0x168_alert()

        if getattr(self, '_popup_timer', None) is not None:
            if hasattr(self._popup_timer, 'cancel'):
                self._popup_timer.cancel()
            self._popup_timer = None
        if duration > 0:
            self._popup_timer = Clock.schedule_once(lambda _dt: self.clear_popup(), duration)

    def clear_popup(self):
        if getattr(self, '_popup_timer', None) is not None:
            if hasattr(self._popup_timer, 'cancel'):
                self._popup_timer.cancel()
            self._popup_timer = None

        self._tyres.popup_flag = 0x00
        self.msg_flag = 0x00

        # Send clear frame
        clear_payload = self._build_payload(self.msg_id if self.msg_id else MSG_DIAGNOSTIC_OK, 'clear')
        self.runner.send_message(0x1A1, clear_payload)

        self._tyres.display_active = False
        self.msg_flag = 0xFF
        self._update_status()

    def _update_status(self):
        if 'status_msg' in self.ids:
            if self.msg_flag != 0xFF and self.msg_id in messages_1a1.messages:
                self.ids['status_msg'].text = messages_1a1.messages[self.msg_id]
                self.ids['status_msg'].color = (1, 0.8, 0, 1)
            else:
                self.ids['status_msg'].text = '-'
                self.ids['status_msg'].color = (0.5, 0.5, 0.5, 1)

    def _build_payload(self, msg_id, phase):
        template = TYRE_MESSAGE_PAYLOADS.get(msg_id)
        if template is not None:
            payload = list(template[phase])
        elif phase == 'active':
            payload = [0x80, msg_id, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00]
        else:
            payload = [0x00, msg_id, 0xC6, 0x00, 0x00, 0x00, 0x00, 0x00]

        # Dynamically set bytes 3 and 4 for tyre-specific messages using standard bitmask
        if phase == 'active' and msg_id in (
            MSG_PRESSURE_LOW, MSG_PRESSURE_NOT_MONITORED,
            MSG_MULTIPLE_FLAT, MSG_HIGH_SPEED_CHECK, MSG_UNDERINFLATED,
        ):
            d3, d4 = self._tyre_status_bytes(self._tyres)
            payload[3] = d3
            payload[4] = d4

        return payload



    def reset_all_nominal(self):
        self._set_wheel_full('fl', TIRE_OK, 2.4)
        self._set_wheel_full('fr', TIRE_OK, 2.4)
        self._set_wheel_full('rl', TIRE_OK, 2.2)
        self._set_wheel_full('rr', TIRE_OK, 2.2)
        self._set_wheel_full('spare', TIRE_OK, 2.5)
        self._update_labels()
        self._update_pressure_displays()
        self._sync_dashboard_and_alerts()
        self.clear_popup()

    def _set_wheel_full(self, tyre, state, pressure):
        self._set_tyre(tyre, state)
        if tyre in ROAD_TYRES:
            setattr(self._tyres, f'pressure_{tyre}', float(pressure))

    # --- Tyre state & pressure controls ---

    def on_state_change(self, tyre, state_text):
        if state_text not in TIRE_STATES:
            return
        idx = TIRE_STATES.index(state_text)
        self._set_tyre(tyre, idx)
        self._update_label(tyre)

        # Sync pressure readout to match selected condition
        if idx == TIRE_FLAT:
            setattr(self._tyres, f'pressure_{tyre}', 0.0)
        elif idx == TIRE_LOW:
            setattr(self._tyres, f'pressure_{tyre}', 1.5)
        elif idx == TIRE_OK:
            setattr(self._tyres, f'pressure_{tyre}', 2.4 if tyre in ('fl', 'fr') else 2.2)
        self._update_pressure_displays()

        self._sync_dashboard_and_alerts()
        self.trigger_popup()

    def on_pressure_change(self, tyre, value):
        val = round(float(value), 2)
        setattr(self._tyres, f'pressure_{tyre}', val)
        label_id = f'cur_pressure_{tyre}'
        if label_id in self.ids:
            self.ids[label_id].text = f'{val:.2f} bar'
        slider_id = f'slider_pressure_{tyre}'
        if slider_id in self.ids and abs(self.ids[slider_id].value - val) > 0.01:
            self.ids[slider_id].value = val

        # Auto-update tyre state based on direct pressure value
        if val <= 0.8:
            new_state = TIRE_FLAT
        elif val < 2.0:
            new_state = TIRE_LOW
        else:
            new_state = TIRE_OK

        current_state = getattr(self._tyres, tyre, TIRE_OK)
        if current_state != new_state:
            self._set_tyre(tyre, new_state)
            self._update_label(tyre)
            self._sync_dashboard_and_alerts()
            self.trigger_popup()

    def on_system_toggle(self, toggle_name, state):
        sys_state = getattr(self._tyres, 'tpms_system_state', 0x20)
        if toggle_name == 'fault':
            if state == 'down':
                sys_state |= 0x80
            else:
                sys_state &= ~0x80
        elif toggle_name == 'calibration':
            if state == 'down':
                sys_state |= 0x20
            else:
                sys_state &= ~0x20
        self._tyres.tpms_system_state = sys_state

    def _worst_state(self):
        return max(getattr(self._tyres, k, TIRE_OK) for k in ROAD_TYRES)

    def _flat_count(self):
        return sum(1 for k in ROAD_TYRES if getattr(self._tyres, k, TIRE_OK) == TIRE_FLAT)

    def _any_flat(self):
        """Check if any road tyre is in FLAT state."""
        t = self._tyres
        return any(getattr(t, k) == TIRE_FLAT for k in ROAD_TYRES)

    def _any_low_or_nodata(self):
        """Check if any road tyre is in LOW, NO_DATA, or BATTERY_LOW state."""
        t = self._tyres
        return any(getattr(t, k) in (TIRE_LOW, TIRE_NO_DATA, TIRE_BATTERY_LOW) for k in ROAD_TYRES)

    def _sync_dashboard_and_alerts(self):
        """Synchronize instrument cluster telltales (0x128), alerts (0x168), and popup state."""
        any_flat = self._any_flat()
        any_low_or_nodata = self._any_low_or_nodata()

        # 0x168 byte 1: bit 7 = under-inflation, bit 6 = flat/puncture
        d1 = ((1 if any_low_or_nodata else 0) << 7) | ((1 if any_flat else 0) << 6)
        self._tyres.alert_0x168_b1 = d1

        # Instrument cluster (Combine / 0x128) lamps
        dash = getattr(self.runner.car, 'dashboard', None)
        if dash is not None:
            if any_flat:
                dash.tyre = 1
                dash.stop = 1
                dash.warn = 1
            elif any_low_or_nodata:
                dash.tyre = 1
                dash.warn = 1
                dash.stop = 0
            else:
                dash.tyre = 0
                dash.stop = 0
                dash.warn = 0

        self._send_0x168_alert()

    def _send_0x168_alert(self):
        """Update generic tyre dashboard alert (0x168)."""
        d1 = self._tyres.alert_0x168_b1
        if not self.runner.car.dashboard.active:
            self.runner.send_message(0x168, [0x00, d1, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    def _update_labels(self):
        for tyre in ALL_TYRES:
            self._update_label(tyre)

    def _update_label(self, tyre):
        label_id = f'state_{tyre}'
        spinner_id = f'spinner_{tyre}'
        state = getattr(self._tyres, tyre, TIRE_OK)
        if state >= len(TIRE_STATES):
            state = TIRE_OK
        text = TIRE_STATES[state]

        if label_id in self.ids:
            self.ids[label_id].text = text
            if state == TIRE_OK:
                self.ids[label_id].color = (0, 1, 0, 1)
            elif state == TIRE_LOW:
                self.ids[label_id].color = (1, 0.8, 0, 1)
            elif state == TIRE_FLAT:
                self.ids[label_id].color = (1, 0, 0, 1)
            elif state == TIRE_BATTERY_LOW:
                self.ids[label_id].color = (1, 0.5, 0, 1)
            else:
                self.ids[label_id].color = (0.5, 0.5, 0.5, 1)

        if spinner_id in self.ids and self.ids[spinner_id].text != text:
            self.ids[spinner_id].text = text

    def _update_pressure_displays(self):
        for tyre in ROAD_TYRES:
            pressure = getattr(self._tyres, f'pressure_{tyre}', 2.4)
            label_id = f'cur_pressure_{tyre}'
            slider_id = f'slider_pressure_{tyre}'
            if label_id in self.ids:
                self.ids[label_id].text = f'{pressure:.2f} bar'
            if slider_id in self.ids and abs(self.ids[slider_id].value - pressure) > 0.01:
                self.ids[slider_id].value = pressure

    def _update_system_buttons(self):
        sys_state = getattr(self._tyres, 'tpms_system_state', 0x20)
        if 'btn_calib' in self.ids:
            self.ids['btn_calib'].state = 'down' if (sys_state & 0x20) else 'normal'
        if 'btn_fault' in self.ids:
            self.ids['btn_fault'].state = 'down' if (sys_state & 0x80) else 'normal'

    # --- Monitor mode ---

    def on_can_message(self, msg):
        if msg.arbitration_id == 0x361 and len(msg.data) >= 8:
            # 0x361: TPMS sensor data across 4 wheels (2 bytes/wheel)
            Msg361().decode(self.runner.car, msg.data)
            self._update_labels()
            self._update_pressure_displays()
            return

        if msg.arbitration_id == 0x1E1 and len(msg.data) >= 4:
            # 0x1E1: MSG_DONNEES_ETAT_ROUES (FL, FR, RR, RL, Spare, TPMS system state)
            Msg1E1().decode(self.runner.car, msg.data)
            self._update_labels()
            self._update_system_buttons()
            return

        if msg.arbitration_id == 0x3A1 and len(msg.data) >= 4:
            # 0x3A1: MSG_DONNEES_PRESSION_ROUES (FL, FR, RR, RL pressures)
            Msg3A1().decode(self.runner.car, msg.data)
            self._update_pressure_displays()
            return

        if msg.arbitration_id != 0x1A1 or len(msg.data) < 2:
            return

        self.msg_flag = msg.data[0]
        self.msg_id = msg.data[1]
        self._update_status()
        self._tyres.display_active = (self.msg_flag != 0xFF)
        if 'cur_mess' in self.ids:
            self.ids['cur_mess'].text = f'{self.msg_id}'
        if 'slider_mess' in self.ids and self.ids['slider_mess'].value != self.msg_id:
            self.ids['slider_mess'].value = self.msg_id
        if 'send' in self.ids:
            if self.msg_id in messages_1a1.messages:
                self.ids['send'].text = f'send {messages_1a1.messages[self.msg_id]}'
            else:
                self.ids['send'].text = 'send (inconnu)'
