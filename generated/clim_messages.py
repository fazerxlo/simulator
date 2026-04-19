"""Auto-generated from signal-db/clim.yaml — do not edit by hand.

Climate control messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


def _encode_clim_fan(fan_level: int) -> int:
    """Encode UI fan level 0-8 to the bench raw nibble used on 0x1D0 / 0x1E3.

    Real bench captures and PSA-RE show:
    - raw 0x0F = fan off
    - raw 0x00-0x07 = fan levels 1-8
    """
    level = max(0, min(8, int(fan_level)))
    return 0x0F if level == 0 else level - 1


def _decode_clim_fan(raw_value: int) -> int:
    """Decode the bench raw nibble to a UI fan level 0-8."""
    raw = int(raw_value) & 0x0F
    if raw == 0x0F:
        return 0
    if 0 <= raw <= 7:
        return raw + 1
    return 0


class Msg12D(CanMessage):
    """Climate controller command (suppressed when ignition is off)."""

    can_id = 0x12D
    period_ms = 500
    required_modules = frozenset({'clim'})

    def encode(self, car) -> list | None:
        if not car.bsi.ignition_on:
            return None
        return [0x00, 0x32, 0x32, 0x00, 0x00, 0x00, 0x98, 0x80]


class Msg1D0(CanMessage):
    """Climate panel frame (0x1D0).
    
    Sends the BSI idle frame when the clim module is not loaded or ignition
    is off.  When ``car.clim.enabled`` is ``True`` and ignition is on, the
    full climate panel state is encoded instead.
    """

    can_id = 0x1D0
    period_ms = 500
    required_modules = frozenset({'clim'})

    def get_period_ms(self, car) -> int:
        return 500

    def encode(self, car) -> list:
        if not car.bsi.ignition_on:
            return [0x08, 0x00, 0x00, 0x00, 0x00, 0x0B, 0x0B, 0x00]
        clim = car.clim
        if not clim.enabled:
            # Standby (fan=0, ignition on): climate suspended but ignition is on.
            # Workbench byte0=0xA8 (0x80|0x20|0x08); fan=0x0F; temps preserved.
            return [0xA8, 0x00, 0x0F, 0x00, 0x00, clim.temp_left, clim.temp_right, 0x00]
        dir_left = int(clim.dir_left) & 0x0F
        dir_right = int(clim.dir_right) & 0x0F
        dir_byte = (dir_left << 4) | dir_right
        if clim.unfrost_front:
            b0 = 0x19  # 0x08 | 0x11
        elif clim.auto or clim.intake_explicit:
            b0 = 0x08  # AUTO mode or explicit intake (recirc/fresh) — no manual-distribution bit
        else:
            b0 = 0x28  # 0x08 | 0x20 — manual fan/direction mode
        # Byte 4 bit layout (workbench-verified from clima_auto_inside_outside_auto.csv):
        #   bit5 (0x20): "explicit non-auto intake mode" — set when Fresh, Recirc, or
        #                UnfrostFront was actively selected by the user.
        #   bit4 (0x10): "recirculation" — set only when recirc is active.
        # AUTO mode: byte4=0x00; Fresh explicit: 0x20; Recirc explicit: 0x30.
        b4 = (0x20 if clim.intake_explicit else 0x00) | (0x10 if clim.recycle else 0x00)
        fan_raw = _encode_clim_fan(clim.fan)
        return [b0, 0x00, fan_raw, dir_byte, b4,
                clim.temp_left, clim.temp_right, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        car.clim.fan = _decode_clim_fan(data[2])
        raw_dir = data[3]
        high = (raw_dir >> 4) & 0x0F
        low = raw_dir & 0x0F
        # Real bench captures show 0x1D0 sometimes emits an ambiguous single-
        # nibble direction value (for example 0x04 while left=auto and right=up).
        # Only trust the classic mirrored-nibble format here, otherwise leave the
        # per-side airflow state to 0x1E3 which carries both zones explicitly.
        if high and high == low:
            car.clim.dir_left = high
        # bit4 = recirculation (workbench-verified); bit5 = non-auto intake flag.
        car.clim.recycle = (data[4] >> 4) & 1
        car.clim.temp_left = data[5]
        car.clim.temp_right = data[6]


class Msg1E3(CanMessage):
    """Climate EMF status frame (0x1E3).
    
    Same conditional logic as Msg1D0: uses the BSI standby frame
    unless ``car.clim.enabled`` is ``True`` and ignition is on.
    """

    can_id = 0x1E3
    period_ms = 200
    required_modules = frozenset({'clim'})

    def encode(self, car) -> list:
        if not car.bsi.ignition_on:
            return [0x1C, 0x40, 0x0B, 0x0B, 0x00, 0x00, 0x00, 0x00]
        clim = car.clim
        if not clim.enabled:
            # Standby (fan=0, ignition on): climate suspended but ignition is on.
            # Workbench byte0=(ac<<4)|0x20|dual; fan=0x0F; temps preserved.
            b1 = (clim.ac << 4) | 0x20 | clim.dual
            b2 = 0x30 | (clim.unfrost_front << 7)
            return [b1, b2, clim.temp_left, clim.temp_right, 0x00, 0x00, 0x0F, 0x00]
        # In AUTO mode bits 2+3 (0x0C) are set together; when an explicit
        # non-auto intake mode is active (Fresh/Recirc/UnfrostFront selected by
        # the user) bit2 (0x04) alone is set; in implicit manual mode both are
        # clear.  Bit 7 (0x80) is the recirculation indicator, set when
        # clim.recycle=1.
        # Verified against workbench:
        #   auto=1, ac=1, dual=0        → 0x1C
        #   auto=1, ac=1, dual=1        → 0x1D
        #   auto=0, ac=1, dual=1 (implicit fresh, from standby raise) → 0x11
        #   explicit fresh, ac=0, dual=1 → 0x05
        #   explicit recirc, ac=0, dual=1 → 0x85
        if clim.auto:
            mode_bits = 0x0C
        elif clim.intake_explicit:
            mode_bits = 0x04
        else:
            mode_bits = 0x00
        recirc_bit = 0x80 if clim.recycle else 0x00
        # Bit1 (0x02) is the one-shot MFD notification trigger: the real BSI
        # sets it for exactly one frame when switching to Recirc (→ popup
        # "Cabin air recycling activated") or Fresh (→ "Forced intake of
        # outside air").  Workbench: 0x87 = 0x85|0x02 on recirc entry,
        # 0x07 = 0x05|0x02 on fresh entry.
        notify_bit = 0x02 if clim.intake_notify else 0x00
        clim.intake_notify = False  # one-shot: consume after first use
        # Workbench: recirc and explicit-fresh always encode ac=0 in byte0
        # (verified from workbench captures: 0x85 for recirc, 0x05 for fresh).
        # AUTO mode and unfrost_front preserve the user's A/C setting (clim.ac).
        # This keeps the simulator A/C button state independent of airflow mode.
        if clim.auto or clim.unfrost_front or not clim.intake_explicit:
            ac_enc = clim.ac
        else:
            ac_enc = 0
        b1 = recirc_bit | (ac_enc << 4) | mode_bits | notify_bit | clim.dual
        b2 = 0x30 | (clim.unfrost_front << 7)
        b3 = clim.bits | clim.temp_left
        b4 = clim.temp_right
        b5 = clim.dir_left << 4
        b6 = clim.dir_right << 4
        b7 = _encode_clim_fan(clim.fan)
        return [b1, b2, b3, b4, b5, b6, b7, 0x00]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        car.clim.fan = _decode_clim_fan(data[6])
        car.clim.dir_left = data[4] >> 4
        car.clim.dir_right = data[5] >> 4
        car.clim.ac = (data[0] >> 4) & 1
        car.clim.auto = (data[0] >> 3) & 1
        car.clim.dual = data[0] & 1
        # bit7 of byte0 = recirculation indicator (workbench-verified).
        car.clim.recycle = (data[0] >> 7) & 1
        car.clim.unfrost_front = (data[1] >> 7) & 1
        car.clim.temp_left = data[2] & 0x1F
        car.clim.temp_right = data[3]

