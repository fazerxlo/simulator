"""Auto-generated from signal-db/cdc.yaml — do not edit by hand.

CD changer (CDC) messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg131(CanMessage):
    """CD changer command frame sent by the head unit to the CDC (0x131).
    
    PSA CAN2004 canonical name: ``CDE_CDC``.
    
    This frame is transmitted by the radio head unit and received by the CD
    changer.  The simulator does not transmit this ID — it decodes incoming
    frames so that bench testing with a real head unit works correctly.
    
    Byte layout (0-indexed):
      0  — bit 7: CDC source selected (1 = CDC active)
             bit 4: play request (1 = play, 0 = pause)
             bits 3-0: disc request (1-6 = specific disc, 0 = no change)
      1  — track request (1-99 = specific track, 0 = no change)
      2-7 — reserved (0x00)
    """

    can_id = 0x131
    period_ms = 100
    required_modules = frozenset({'cdc'})

    def encode(self, car) -> list | None:
        # The CDC does not transmit this frame — the radio head unit does.
        return None

    def decode(self, car, data: bytes) -> None:
        if len(data) < 2 or not car.cdc.active:
            return
        cdc = car.cdc
        b0 = data[0]
        if b0 & 0x80:
            # CDC selected as audio source.
            if b0 & 0x10:
                cdc.status = cdc.STATUS_PLAYING
            else:
                cdc.status = cdc.STATUS_PAUSED
            disc_req = b0 & 0x0F
            if 1 <= disc_req <= 6 and disc_req != cdc.disc:
                cdc.disc = disc_req
                cdc.track = 1
                cdc.minutes = 0
                cdc.seconds = 0
                cdc.status = cdc.STATUS_SEARCHING
        else:
            # CDC deselected.
            cdc.status = cdc.STATUS_IDLE
        track_req = data[1]
        if track_req and track_req != cdc.track:
            cdc.track = track_req
            cdc.minutes = 0
            cdc.seconds = 0


class Msg1A0(CanMessage):
    """CD changer status frame transmitted by the CDC to the head unit (0x1A0).
    
    PSA CAN2004 canonical name: ``CDC_STATUS``.
    
    Byte layout (0-indexed):
      0  — status byte:
             0x80 = no magazine / CDC inactive
             0x40 = searching / disc changing
             0x04 = playing (CD spinning)
             0x02 = paused
             0x01 = loading
      1  — current disc number (1-6; 0 = inactive)
      2  — current track number (1-99; 0 = inactive)
      3  — track elapsed time: minutes (0-99)
      4  — track elapsed time: seconds (0-59)
      5  — total tracks on current disc (0 = unknown)
      6  — mode flags:
             bit 0: scan mode
             bit 1: random play
             bit 2: repeat all
             bit 3: repeat current track
      7  — reserved (0x00)
    """

    can_id = 0x1A0
    period_ms = 100
    required_modules = frozenset({'cdc'})

    _STATUS_MAP = {
        0: 0x80,  # idle → no magazine
        1: 0x04,  # playing
        2: 0x02,  # paused
        3: 0x01,  # loading
        4: 0x40,  # searching
    }

    def encode(self, car) -> list | None:
        cdc = car.cdc
        if not cdc.active:
            return None
        b0 = self._STATUS_MAP.get(cdc.status, 0x80)
        b6 = (
            int(cdc.scan) |
            (int(cdc.random) << 1) |
            (int(cdc.repeat) << 2) |
            (int(cdc.repeat_track) << 3)
        )
        return [b0, cdc.disc, cdc.track,
                cdc.minutes, cdc.seconds,
                cdc.total_tracks, b6, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        cdc = car.cdc
        b0 = data[0]
        cdc.disc = data[1]
        cdc.track = data[2]
        cdc.minutes = data[3]
        cdc.seconds = data[4]
        cdc.total_tracks = data[5]
        if b0 & 0x04:
            cdc.status = cdc.STATUS_PLAYING
        elif b0 & 0x02:
            cdc.status = cdc.STATUS_PAUSED
        elif b0 & 0x01:
            cdc.status = cdc.STATUS_LOADING
        elif b0 & 0x40:
            cdc.status = cdc.STATUS_SEARCHING
        else:
            cdc.status = cdc.STATUS_IDLE
        if len(data) >= 7:
            cdc.scan = bool(data[6] & 0x01)
            cdc.random = bool(data[6] & 0x02)
            cdc.repeat = bool(data[6] & 0x04)
            cdc.repeat_track = bool(data[6] & 0x08)

