"""Auto-generated from signal-db/2004/radio.yaml — do not edit by hand.

Radio and steering button messages for Peugeot 407 CAN2004 comfort bus
"""

from __future__ import annotations

from generated.base import CanMessage


class Msg0A4(CanMessage):
    """RDS RadioText (RT) multi-frame message (0x0A4).
    
    The radio head-unit transmits the RDS RT string using ISO 15765-2
    (ISO-TP) framing, which allows a text up to 64 characters to be split
    across multiple 8-byte CAN frames:
    
    * **Single Frame (SF)** — PCI byte ``0x0N``, N = data length (1–7).
      The complete RT fits in one frame.
    * **First Frame (FF)** — PCI bytes ``0x1H 0xLL``, total length
      = ``(H<<8)|LL``.  Payload bytes 2–7 carry the first 6 RT chars.
    * **Consecutive Frame (CF)** — PCI byte ``0x2N``, N = sequence number
      (1–15, wrapping to 0 after 15).  Bytes 1–7 carry the next 7 chars.
    
    Accumulation state is stored in ``car.radio._rt_buf``.  ``car.radio.rds_text``
    is updated after every received frame so the UI shows text building up
    progressively.  A new SF or FF resets the buffer and discards any
    incomplete in-progress transfer.  An out-of-sequence CF also discards
    the buffer.
    """

    can_id = 0x0A4
    period_ms = 500
    required_modules = frozenset({'radio'})
    listen_only = True

    @staticmethod
    def _trim_rt(raw) -> str:
        """Normalize an RT payload to a displayable ASCII string.

        Real bench captures sometimes prepend an internal 4-byte control
        prefix ``10 00 00 00`` before the 64-character RadioText body.
        Strip that prefix when present, then stop at the first NUL and trim
        outer whitespace used as display padding.
        """
        if isinstance(raw, str):
            raw = raw.encode('ascii', errors='replace')
        raw = bytes(raw)
        if raw.startswith(b'\x10\x00\x00\x00'):
            raw = raw[4:]
        nul = raw.find(b'\x00')
        if nul >= 0:
            raw = raw[:nul]
        return raw.decode('ascii', errors='replace').strip()

    def encode(self, car) -> list:
        return [0x00] * 8

    def decode(self, car, data: bytes) -> None:
        if len(data) < 2:
            return
        pci_type = (data[0] >> 4) & 0x0F

        if pci_type == 0:
            # Single Frame: complete RT text fits in one CAN frame.
            length = data[0] & 0x0F
            if length == 0 or length > 7 or len(data) < 1 + length:
                return
            payload = bytes(data[1:1 + length])
            car.radio._rt_buf = {}
            car.radio.rds_text = self._trim_rt(payload)

        elif pci_type == 1:
            # First Frame: start of a multi-frame transfer.
            if len(data) < 3:
                return
            total_len = ((data[0] & 0x0F) << 8) | data[1]
            chunk = bytearray(data[2:8])
            car.radio._rt_buf = {
                'total': total_len,
                'next_sn': 1,
                'data': chunk,
            }
            # Show the first bytes immediately so the UI updates progressively.
            car.radio.rds_text = self._trim_rt(chunk)

        elif pci_type == 2:
            # Consecutive Frame: continuation of a multi-frame transfer.
            buf = car.radio._rt_buf
            if not buf or 'data' not in buf:
                return
            sn = data[0] & 0x0F
            if sn != (buf.get('next_sn', 1) & 0x0F):
                # Out-of-sequence CF — discard the in-progress transfer.
                car.radio._rt_buf = {}
                return
            buf['data'].extend(data[1:8])
            # Sequence numbers wrap: 15 → 0 → 1 → …
            buf['next_sn'] = (sn + 1) & 0x0F
            total = buf.get('total', 0)
            accumulated = bytes(buf['data'])
            if len(accumulated) >= total:
                # Transfer complete — commit the final text.
                car.radio.rds_text = self._trim_rt(accumulated[:total])
                car.radio._rt_buf = {}
            else:
                # Show partial text as it builds up.
                car.radio.rds_text = self._trim_rt(accumulated)


class Msg165(CanMessage):
    """Radio source / input status."""

    can_id = 0x165
    period_ms = 50
    required_modules = frozenset({'radio'})
    listen_only = True

    def encode(self, car) -> list:
        b2 = car.radio.INPUT_CODES.get(car.radio.input, 0x01) << 4
        return [0xCC, 0x54, b2, 0x02]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 3:
            return
        input_code = data[2] >> 4
        for name, code in car.radio.INPUT_CODES.items():
            if code == input_code:
                car.radio.input = name
                return


class Msg1A5(CanMessage):
    """Radio / buttons volume level."""

    can_id = 0x1A5
    period_ms = 100
    required_modules = frozenset({'buttons', 'radio'})

    def encode(self, car) -> list | None:
        if car.buttons.active:
            car.buttons.step_volume()
            return [car.buttons.volflag | (car.buttons.volume & 0x1F)]
        return None  # radio is listen-only; do not transmit on its behalf

    def decode(self, car, data: bytes) -> None:
        if len(data) >= 1:
            volume = data[0] & 0x1F
            car.radio.volume = volume  # always update for radio display
            if car.buttons.active:
                car.buttons.volume = volume


class Msg1E0(CanMessage):
    """Radio internal status frame (0x1E0).
    
    Observed constant payload from the head unit; decoded by the radio
    module to detect an active head unit on the bench.
    """

    can_id = 0x1E0
    period_ms = 100
    required_modules = frozenset({'radio'})
    listen_only = True

    def encode(self, car) -> list:
        return [0x24, 0x00, 0x00, 0x00, 0x20]

    def decode(self, car, data: bytes) -> None:
        pass


class Msg1E5(CanMessage):
    """Radio audio settings: balance, bass, treble, loudness, ambiance."""

    can_id = 0x1E5
    period_ms = 100
    required_modules = frozenset({'radio'})
    listen_only = True

    _AMBIANCE_CODES = {
        'none': 0x03, 'classical': 0x07, 'jazz-blues': 0x0B,
        'pop-rock': 0x0F, 'vocal': 0x13, 'techno': 0x17,
    }

    def encode(self, car) -> list:
        a = car.radio.audio
        b0 = (1 << 7 if a['menu'] == 'lr-bal' else 0) | (a['lr-bal'] & 0x7F)
        b1 = (1 << 7 if a['menu'] == 'rf-bal' else 0) | (a['rf-bal'] & 0x7F)
        b2 = (1 << 7 if a['menu'] == 'bass' else 0) | (a['bass'] & 0x7F)
        b4 = (1 << 7 if a['menu'] == 'treble' else 0) | (a['treble'] & 0x7F)
        b5 = ((1 << 7 if a['menu'] == 'loudness' else 0) |
              (a['loudness'] << 6) |
              (1 << 4 if a['menu'] == 'volume' else 0) |
              (a['volume'] & 0x0F))
        b6 = ((1 << 6 if a['menu'] == 'ambiance' else 0) |
              self._AMBIANCE_CODES.get(a['ambiance'], 0x03))
        return [b0, b1, b2, 0x00, b4, b5, b6]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 7:
            return
        a = car.radio.audio
        # Always update every field unconditionally so the display reflects the
        # live head-unit state even when no menu is open.
        a['lr-bal'] = data[0] & 0x7F
        a['rf-bal'] = data[1] & 0x7F
        a['bass'] = data[2] & 0x7F
        a['treble'] = data[4] & 0x7F
        a['loudness'] = (data[5] >> 6) & 1        # bit6 = loudness on/off
        a['volume'] = data[5] & 0x07              # bits2:0 = auto-vol threshold
        ambiance_code = data[6] & 0x3F
        for name, code in self._AMBIANCE_CODES.items():
            if code == ambiance_code:
                a['ambiance'] = name
                break
        # Determine which menu is currently open (bit7 of each byte).
        if data[0] & 0x80:
            a['menu'] = 'lr-bal'
        elif data[1] & 0x80:
            a['menu'] = 'rf-bal'
        elif data[2] & 0x80:
            a['menu'] = 'bass'
        elif data[4] & 0x80:
            a['menu'] = 'treble'
        elif data[5] & 0x80:                      # bit7 = loudness menu open
            a['menu'] = 'loudness'
        elif data[5] & 0x10:                      # bit4 = auto-vol menu open
            a['menu'] = 'volume'
        elif data[6] & 0x40:                      # bit6 = ambiance menu open
            a['menu'] = 'ambiance'
        else:
            a['menu'] = 'none'


class Msg225(CanMessage):
    """FM tuner status: frequency, band, memory preset, RDS flags (0x225).
    
    Frequency encoding: display_MHz = raw * 0.05 + 50.
    Cross-referenced with ios-car-dashboard Arduino serial protocol.
    
    Byte 0 bit layout (verified from real bench capture):
      bit7  : LIST   – station list active
      bit6  : SCAN   – scan mode active
      bit5  : RDS    – RDS data available
      bit4  : PTY    – PTY search / data available
      bit3  : TUN    – currently tuning
      bit2  : TA     – traffic announcement flag
      bit1:0: TUNDIR – tuning direction (0=none, 1=up, 2=down)
    
    Band codes (byte 2, verified from real bench capture):
      0x00 = no band / unset
      0x90 = FM Band 1
      0xA0 = FM Band 2
      0xC0 = FM Auto-store (AST)
      0xD0 = AM / medium wave
    """

    can_id = 0x225
    period_ms = 100
    required_modules = frozenset({'radio'})
    listen_only = True

    def encode(self, car) -> list:
        r = car.radio
        b0 = (r.list_flag << 7 | r.scan << 6 | r.rds << 5 | r.pty << 4 |
              r.tun << 3 | r.ta << 2 | (r.tundir & 3))
        return [b0, r.mem, r.band, r.freq >> 8, r.freq & 0xFF]

    def decode(self, car, data: bytes) -> None:
        if len(data) < 5:
            return
        r = car.radio
        r.list_flag = (data[0] >> 7) & 1
        r.scan = (data[0] >> 6) & 1
        r.rds = (data[0] >> 5) & 1
        r.pty = (data[0] >> 4) & 1
        r.tun = (data[0] >> 3) & 1
        r.ta = (data[0] >> 2) & 1
        r.tundir = data[0] & 3
        r.mem = data[1]
        r.band = data[2]
        r.freq = (data[3] << 8) | data[4]


class Msg265(CanMessage):
    """RDS / station info flags (0x265).
    
    Byte 0: status flags (TA, TP, RDS valid, etc.).
    Byte 3: 0x00 = FM/tuner active, 0x01 = CD/CDC active.
    """

    can_id = 0x265
    period_ms = 100
    required_modules = frozenset({'radio'})
    listen_only = True

    def encode(self, car) -> list:
        b0 = (1 << 5) | (1 << 4)   # TA (bit5) and TP (bit4) flags
        b1 = (1 << 7) | (1 << 6) | (2 << 4)
        b3 = 0x00 if car.radio.input == 'TUN' else 0x01
        return [b0, b1, 0x01, b3]

    def decode(self, car, data: bytes) -> None:
        pass


class Msg2A5(CanMessage):
    """Radio station name / RDS Programme Service name (0x2A5).
    
    Payload is a raw ASCII string, left-justified, up to 8 bytes.
    Cross-referenced with ios-car-dashboard serial frame 0x04.
    """

    can_id = 0x2A5
    period_ms = 100
    required_modules = frozenset({'radio'})
    listen_only = True

    def encode(self, car) -> list:
        name = (car.radio.station_name or '')[:8]
        return list(name.encode('ascii', errors='replace'))

    def decode(self, car, data: bytes) -> None:
        try:
            car.radio.station_name = bytes(data).rstrip(b'\x00').decode(
                'ascii', errors='replace'
            ).strip()
        except Exception:
            pass


class Msg3E5(CanMessage):
    """Steering wheel control panel buttons.
    
    Encodes from ``car.buttons`` when the ``buttons`` module is active
    (different bit layout and key set).  When only the ``radio`` module is
    active the real workbench radio owns this frame, so the simulator does
    not transmit it (returns ``None``).
    """

    can_id = 0x3E5
    period_ms = 50
    required_modules = frozenset({'buttons', 'radio'})

    def encode(self, car) -> list | None:
        if car.buttons.active:
            p = car.buttons.panel
            car.buttons.step_pulses()
            b0 = (p['tel'] << 4) | p['clima']
            b1 = (p['trip'] << 6) | (p['source'] << 4) | p['dark']
            b2 = (p['ok'] << 6) | (p['esc'] << 4) | (p['next'] << 2) | p['prev']
            b5 = (p['up'] << 6) | (p['down'] << 4) | (p['right'] << 2) | p['left']
            return [b0, b1, b2, 0x00, 0x00, b5]
        return None  # radio is listen-only; do not transmit on its behalf

    def decode(self, car, data: bytes) -> None:
        if len(data) < 6:
            return
        if car.buttons.active:
            b0, b1, b2 = data[0], data[1], data[2]
            b5 = data[5]
            car.buttons.panel['tel'] = (b0 >> 4) & 1
            car.buttons.panel['clima'] = b0 & 1
            car.buttons.panel['trip'] = (b1 >> 6) & 1
            car.buttons.panel['source'] = (b1 >> 4) & 1
            car.buttons.panel['dark'] = b1 & 1
            car.buttons.panel['ok'] = (b2 >> 6) & 1
            car.buttons.panel['esc'] = (b2 >> 4) & 1
            car.buttons.panel['next'] = (b2 >> 2) & 1
            car.buttons.panel['prev'] = b2 & 1
            car.buttons.panel['up'] = (b5 >> 6) & 1
            car.buttons.panel['down'] = (b5 >> 4) & 1
            car.buttons.panel['right'] = (b5 >> 2) & 1
            car.buttons.panel['left'] = b5 & 1
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

