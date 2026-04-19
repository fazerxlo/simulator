"""Auto-generated from signal-db/trip.yaml — do not edit by hand.

Trip computer messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg221(CanMessage):
    """Trip computer: instantaneous fuel consumption, autonomy, distance."""

    can_id = 0x221
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        t = car.trip
        b0 = t.hide_fuel << 7 | t.hide_dist << 6 | t.com_right << 3 | t.com_left
        fuel = int(t.fuel * 10)
        autonomy = int(t.autonomy)
        distance = int(t.dist * 10)
        return [b0, fuel >> 8, fuel & 0xFF,
                autonomy >> 8, autonomy & 0xFF,
                distance >> 8, distance & 0xFF]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        t = car.trip
        t.hide_fuel = (data[0] >> 7) & 1
        t.hide_dist = (data[0] >> 6) & 1
        t.com_right = (data[0] >> 3) & 1
        t.com_left = data[0] & 1
        t.fuel = ((data[1] << 8) | data[2]) / 10.0
        t.autonomy = (data[3] << 8) | data[4]
        t.dist = ((data[5] << 8) | data[6]) / 10.0


class Msg2A1(CanMessage):
    """Trip computer historical record 1."""

    can_id = 0x2A1
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        hist = car.trip.hist[0]
        dist = int(hist['dist'])
        fuel = int(hist['fuel'] * 10)
        return [int(hist['speed']), dist >> 8, dist & 0xFF,
                fuel >> 8, fuel & 0xFF, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 5:
            h = car.trip.hist[0]
            h['speed'] = data[0]
            h['dist'] = (data[1] << 8) | data[2]
            h['fuel'] = ((data[3] << 8) | data[4]) / 10.0


class Msg261(CanMessage):
    """Trip computer historical record 2."""

    can_id = 0x261
    period_ms = 1000
    required_modules = frozenset({'bsi-trip'})

    def encode(self, car) -> list:
        hist = car.trip.hist[1]
        dist = int(hist['dist'])
        fuel = int(hist['fuel'] * 10)
        return [int(hist['speed']), dist >> 8, dist & 0xFF,
                fuel >> 8, fuel & 0xFF, 0x00, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 5:
            h = car.trip.hist[1]
            h['speed'] = data[0]
            h['dist'] = (data[1] << 8) | data[2]
            h['fuel'] = ((data[3] << 8) | data[4]) / 10.0

