"""Auto-generated from signal-db/kml.yaml — do not edit by hand.

KML hands-free phone module messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg1A3(CanMessage):
    """KML / hands-free phone module status."""

    can_id = 0x1A3
    period_ms = 100
    required_modules = frozenset({'kml'})

    def encode(self, car) -> list:
        return [0x80, car.kml.opt << 2, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 2:
            car.kml.opt = (data[1] >> 2) & 1


class Msg223(CanMessage):
    """KML module data frame."""

    can_id = 0x223
    period_ms = 100
    required_modules = frozenset({'kml'})

    def encode(self, car) -> list:
        return [car.kml.bits_223, 0x00, 0x00, 0x00, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.kml.bits_223 = data[0]


class Msg323(CanMessage):
    """KML module data frame 2 (mostly fixed content)."""

    can_id = 0x323
    period_ms = 100
    required_modules = frozenset({'kml'})

    _FIXED = [0x66, 0x08, 0x68, 0x00, 0x02, 0x02, 0x00]

    def encode(self, car) -> list:
        return list(self._FIXED)

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            car.kml.bits_323 = data[0]

