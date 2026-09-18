"""Auto-generated from signal-db/steering_wheel.yaml — do not edit by hand.

Steering wheel, column stalks, and wheel angle messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg0C5(CanMessage):
    """Steering wheel angle (0x0C5).
    
    Angle is encoded in 0.1 degree units as a signed 16-bit integer in big-endian
    format (-540.0° to +540.0° range, default 0.0° / centered).
    """

    can_id = 0x0C5
    period_ms = 50
    required_modules = frozenset({'buttons', 'steering_wheel'})

    def encode(self, car) -> list | None:
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None or not sw.active:
            return None
        raw_angle = int(round(sw.angle * 10))
        raw = raw_angle & 0xFFFF
        return [raw >> 8, raw & 0xFF, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 2:
            return
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None:
            return
        val = (data[0] << 8) | data[1]
        if val >= 0x8000:
            val -= 0x10000
        sw.angle = val / 10.0


class Msg21F(CanMessage):
    """Steering-wheel remote key actions.
    
    The real remote uses a 3-byte frame on 0x21F.  The key identity is carried
    in byte 0, while byte 1 is a secondary pulse/aux value and byte 2 is
    reserved/zero.  This simulator models the momentary wheel button action as a
    short pulse so the button's press is visible on the bus for a few frames.
    """

    can_id = 0x21F
    period_ms = 100
    required_modules = frozenset({'buttons', 'steering_wheel'})

    def encode(self, car) -> list | None:
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None or not sw.active:
            return None
        sw.step_pulses()
        if sw.remote_action is None:
            return [0x00, sw.remote_aux, 0x00]

        mask = sw.REMOTE_ACTIONS.get(sw.remote_action, 0x00)
        sw.step_remote_pulses()
        return [mask, sw.remote_aux, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 3:
            return
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None:
            return
        cmd = data[0]
        if cmd == 0x00:
            sw.remote_action = None
            return
        for name, mask in sw.REMOTE_ACTIONS.items():
            if cmd == mask:
                sw.remote_action = name
                return
        sw.remote_action = None


class Msg3E5(CanMessage):
    """Steering wheel control panel buttons.
    
    Encodes from ``car.steering_wheel`` (or ``car.buttons``) when the
    steering wheel subsystem is active.  When only the ``radio`` module is
    active the real workbench radio owns this frame, so the simulator does
    not transmit it (returns ``None``).
    """

    can_id = 0x3E5
    period_ms = 50
    required_modules = frozenset({'buttons', 'radio', 'steering_wheel'})

    def encode(self, car) -> list | None:
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is not None and sw.active:
            p = sw.panel
            sw.step_pulses()
            b0 = (p.get('tel', 0) << 4) | p.get('clima', 0)
            b1 = (p.get('trip', 0) << 6) | (p.get('source', 0) << 4) | p.get('dark', 0)
            b2 = (p.get('ok', 0) << 6) | (p.get('esc', 0) << 4) | (p.get('next', 0) << 2) | p.get('prev', 0)
            b5 = (p.get('up', 0) << 6) | (p.get('down', 0) << 4) | (p.get('right', 0) << 2) | p.get('left', 0)
            return [b0, b1, b2, 0x00, 0x00, b5]
        return None  # radio is listen-only; do not transmit on its behalf

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is not None and sw.active:
            b0, b1, b2 = data[0], data[1], data[2]
            b5 = data[5]
            if 'tel' in sw.panel:
                sw.panel['tel'] = (b0 >> 4) & 1
            if 'clima' in sw.panel:
                sw.panel['clima'] = b0 & 1
            if 'trip' in sw.panel:
                sw.panel['trip'] = (b1 >> 6) & 1
            if 'source' in sw.panel:
                sw.panel['source'] = (b1 >> 4) & 1
            if 'dark' in sw.panel:
                sw.panel['dark'] = b1 & 1
            if 'ok' in sw.panel:
                sw.panel['ok'] = (b2 >> 6) & 1
            if 'esc' in sw.panel:
                sw.panel['esc'] = (b2 >> 4) & 1
            if 'next' in sw.panel:
                sw.panel['next'] = (b2 >> 2) & 1
            if 'prev' in sw.panel:
                sw.panel['prev'] = b2 & 1
            if 'up' in sw.panel:
                sw.panel['up'] = (b5 >> 6) & 1
            if 'down' in sw.panel:
                sw.panel['down'] = (b5 >> 4) & 1
            if 'right' in sw.panel:
                sw.panel['right'] = (b5 >> 2) & 1
            if 'left' in sw.panel:
                sw.panel['left'] = b5 & 1
            return
        b0, b1, b2 = data[0], data[1], data[2]
        b5 = data[5]
        car.radio.panel['menu'] = (b0 >> 6) & 1
        car.radio.panel['tel'] = (b0 >> 4) & 1
        car.radio.panel['clim'] = b0 & 1
        car.radio.panel['trip'] = (b1 >> 6) & 1
        car.radio.panel['mode'] = (b1 >> 4) & 1
        car.radio.panel['audio'] = b1 & 1
        car.radio.panel['ok'] = (b2 >> 6) & 1
        car.radio.panel['esc'] = (b2 >> 4) & 1
        car.radio.panel['up'] = (b5 >> 6) & 1
        car.radio.panel['down'] = (b5 >> 4) & 1
        car.radio.panel['right'] = (b5 >> 2) & 1
        car.radio.panel['left'] = b5 & 1

