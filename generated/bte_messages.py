"""Auto-generated from signal-db/bte.yaml — do not edit by hand.

BTE module messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg12B(CanMessage):
    """BTE module status byte."""

    can_id = 0x12B
    period_ms = 100
    required_modules = frozenset({'bte'})

    def encode(self, car) -> list:
        return [car.bte.bits]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.bte.bits = data[0]

