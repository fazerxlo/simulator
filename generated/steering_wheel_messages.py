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
    required_modules = frozenset({'steering-wheel', 'steering_wheel', 'buttons'})

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
    """Steering-wheel remote key actions and rotary scroll encoder position.
    
    The Peugeot 407 / WIP Nav+ satellite stalk uses a 3-byte frame on 0x21F.
    Byte 0 carries the button command mask, Byte 1 contains the rotary scroll
    encoder position counter, and Byte 2 indicates the button state
    (0x00=idle, 0x01=pressed, 0x02=long_press).
    """

    can_id = 0x21F
    period_ms = 100
    required_modules = frozenset({'steering-wheel', 'steering_wheel', 'buttons'})

    def encode(self, car) -> list | None:
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None or not sw.active:
            return None
        sw.step_pulses()
        sw.step_remote_pulses()
        return sw.sm.get_can_21f_frame()

    def decode(self, car, data: bytes) -> None:
        if len(data) < 3:
            return
        sw = getattr(car, 'steering_wheel', getattr(car, 'buttons', None))
        if sw is None:
            return
        cmd = data[0]
        sw.sm.scroll_counter = data[1]
        sw.remote_aux = data[1]
        if cmd == 0x00:
            sw.remote_action = None
            return
        for name, mask in sw.REMOTE_ACTIONS.items():
            if cmd == mask:
                sw.remote_action = name
                return
        sw.remote_action = None

