# CAN 2004 Radio / Infotainment Frames — Peugeot 407 / PSA Comfort CAN

**Bus:** PSA comfort / infotainment CAN, 125 kbps  
**Scope:** Head unit, steering-wheel controls, audio settings, RDS tuner  
**Reference comparison:** [alexandreblin/ios-car-dashboard](https://github.com/alexandreblin/ios-car-dashboard) (Peugeot 207, RD4 radio)

---

## 1. Cross-reference with `alexandreblin/ios-car-dashboard`

Alexandre Blin's `ios-car-dashboard` project reads CAN data from a Peugeot 207 via an Arduino
board (see [arduino-peugeot-can](https://github.com/alexandreblin/arduino-peugeot-can)).  The
Arduino reads the comfort CAN and re-encodes signals into a compact Bluetooth serial protocol
for the iOS app.  This makes it an independent ground-truth source for signal positions on the
Peugeot 207/407 (same RD4 radio head unit as the 407).

Mapping from serial frame ID to source CAN frame:

| iOS serial frame | Signal | Source CAN frame |
|---|---|---|
| `0x01` | Volume (0–30) | `0x1A5` byte 0 bits 4:0 |
| `0x02` | Exterior temperature (°C, signed byte) | `0x0F6` byte 5 (`raw × 0.5 − 40`) |
| `0x03` | Radio source (1=FM, 4=phone, 5=aux) | `0x165` byte 2 high nibble |
| `0x04` | Station name (ASCII string) | `0x2A5` bytes 0–n |
| `0x05` | Frequency (`UInt16 / 10.0` MHz) | `0x225` bytes 3–4 (`raw × 0.05 + 50` MHz) |
| `0x06` | FM band name (1=Band1, 2=Band2, 4=AST) | `0x225` byte 2 |
| `0x07` | Station description / RDS PS text | `0x2A5` (extended payload) |
| `0x08` | BSI info message | `0x1A1` |
| `0x0C` | Trip 1 (speed, distance, fuel) | `0x2A1` |
| `0x0D` | Trip 2 (speed, distance, fuel) | `0x261` |
| `0x0E` | Instant info (autonomy, fuel usage) | `0x221` |
| `0x0F` | Trip mode (instant/trip1/trip2) | `0x221` byte 0 bits 3, 0 |
| `0x10` | Audio settings (balance, bass, treble, loudness, EQ) | `0x1E5` |

**Frequency encoding comparison:**  
The ios-car-dashboard serial frame uses `MHz × 10` (e.g. 96 MHz → 960).  
The real CAN bus (and this simulator) uses `raw = (MHz − 50) / 0.05`:
- 96 MHz → CAN raw = 920 → display = `920 × 0.05 + 50 = 96.0 MHz` ✓  
The Arduino converts `CAN_raw / 2 + 500 = serial_raw`, so the encodings are consistent.

**Confidence:** Verified — the audio-settings layout from `0x1E5` (Msg1E5 in `can_messages.py`)
exactly matches the ios-car-dashboard `AudioSettings.swift` / frame-0x10 parser.

---

## 2. `0x165` — Radio Source / Input Status

**PSA name:** `ETAT_AUTORADIO` (inferred)  
**Period:** 50 ms  
**Module:** `radio`  
**Confidence:** Verified (simulator + ios-car-dashboard cross-reference)

### Byte layout

| Byte | Bits | Signal | Notes |
|---|---|---|---|
| 0 | 7:0 | Status byte 1 | `0xCC` constant in simulator |
| 1 | 7:0 | Status byte 2 | `0x54` constant in simulator |
| 2 | 7:4 | **INPUT_SOURCE** | nibble code (see table below) |
| 2 | 3:0 | Sub-status | `0x01` in simulator |
| 3 | 7:0 | Status byte 4 | `0x02` constant in simulator |

### Input source codes (byte 2, high nibble)

| Code | Name | Description | ios-car-dashboard |
|---|---|---|---|
| `0x1` | `TUN` | FM/AM tuner | `fmTuner` (serial `0x03` data=1) |
| `0x2` | `CD` | Internal CD | — |
| `0x3` | `CDC` | CD changer | — |
| `0x4` | `AUX1` | Auxiliary 1 / phone | `phone` (serial `0x03` data=4) |
| `0x5` | `AUX2` | Auxiliary 2 / ext. AUX | `aux` (serial `0x03` data=5) |
| `0x6` | `USB` | USB media | — |
| `0x7` | `BT` | Bluetooth audio | — |

### Decode snippet

```python
# 0x165 radio source
input_nibble = data[2] >> 4
INPUT_NAMES = {0x1: 'TUN', 0x2: 'CD', 0x3: 'CDC',
               0x4: 'AUX1', 0x5: 'AUX2', 0x6: 'USB', 0x7: 'BT'}
radio_source = INPUT_NAMES.get(input_nibble, 'UNKNOWN')
```

### Test vectors

| Payload | Input |
|---|---|
| `CC 54 10 02` | FM tuner (`TUN`) |
| `CC 54 30 02` | CD changer (`CDC`) |
| `CC 54 50 02` | AUX 2 |

---

## 3. `0x1A5` — Radio Volume

**PSA name:** `VOLUME_RADIO` (inferred)  
**Period:** 100 ms  
**Module:** `radio`, `buttons`  
**Confidence:** Verified (simulator + ios-car-dashboard cross-reference)

### Byte layout

| Byte | Bits | Signal | Notes |
|---|---|---|---|
| 0 | 7:5 | **VOLFLAG** | `0xE0` = stable; `0x00` = volume changing |
| 0 | 4:0 | **VOLUME** | 0–30 (linear) |

### Notes

- The `VOLFLAG` (`0xE0` vs `0x00`) is used to signal to the display that a volume change is
  in progress; the MFD shows a volume bar only while the flag is `0x00`.  After ~2 s of
  inactivity the flag reverts to `0xE0`.
- ios-car-dashboard serial frame `0x01` carries only the volume byte (`0x00–0x1E`), matching
  `data[0] & 0x1F`.
- Maximum volume is 30, minimum is 0 — identical in the ios-car-dashboard and this simulator.

### Decode snippet

```python
# 0x1A5 volume
volflag = data[0] & 0xE0   # 0xE0 = stable, 0x00 = changing
volume  = data[0] & 0x1F   # 0–30
```

### Test vectors

| Payload | VOLFLAG | Volume |
|---|---|---|
| `EF` | `0xE0` (stable) | 15 |
| `00` | `0x00` (changing) | 0 |
| `1E` | `0x00` (changing) | 30 |

---

## 4. `0x1E5` — Radio Audio Settings

**PSA name:** `REGLAGES_SON` (inferred)  
**Period:** 100 ms  
**Module:** `radio`  
**Confidence:** Verified — byte layout confirmed against `AudioSettings.swift` in
[ios-car-dashboard](https://github.com/alexandreblin/ios-car-dashboard/blob/master/CarDash/AudioSettings.swift)
and the `CarInfo+SerialParserDelegate.swift` frame-`0x10` parser.

### Byte layout

| Byte | Bit 7 | Bits 6:0 | Notes |
|---|---|---|---|
| 0 | L/R-balance menu active | L/R balance + `0x3F` | `0x3F` = centre; `< 0x3F` = left; `> 0x3F` = right |
| 1 | F/R-balance menu active | F/R balance + `0x3F` | `0x3F` = centre; `< 0x3F` = front; `> 0x3F` = rear |
| 2 | Bass menu active | Bass + `0x3F` | `0x3F` = flat; `< 0x3F` = cut; `> 0x3F` = boost |
| 3 | — | — | Always `0x00` |
| 4 | Treble menu active | Treble + `0x3F` | Same encoding as bass |
| 5 | Loudness menu active | bit 6 = loudness on, bit 4 = auto-vol menu active, bits 2:0 = auto-vol threshold | See detail below |
| 6 | Ambiance/equalizer menu active | Ambiance code bits 5:0 | See codes below |

### Byte 5 detail

| Bits | Meaning |
|---|---|
| 7 | Loudness menu is currently open |
| 6 | Loudness enabled |
| 4 | Automatic-volume menu is currently open |
| 2:0 | Automatic-volume threshold (`0x07` = enabled; `0x00` = disabled) |

### Ambiance / equalizer codes (byte 6, bits 5:0)

These match the ios-car-dashboard `EqualizerSetting` enum exactly:

| Code | Name | ios-car-dashboard |
|---|---|---|
| `0x03` | `none` | `.none` |
| `0x07` | `classical` | `.classical` |
| `0x0B` | `jazz-blues` | `.jazzBlues` |
| `0x0F` | `pop-rock` | `.popRock` |
| `0x13` | `vocal` | `.vocals` |
| `0x17` | `techno` | `.techno` |

### Decode snippet

```python
# 0x1E5 audio settings
lr_bal_active = (data[0] >> 7) & 1
lr_bal        = (data[0] & 0x7F) - 0x3F  # -9 … +9

fr_bal_active = (data[1] >> 7) & 1
fr_bal        = (data[1] & 0x7F) - 0x3F

bass_active   = (data[2] >> 7) & 1
bass          = (data[2] & 0x7F) - 0x3F

treble_active = (data[4] >> 7) & 1
treble        = (data[4] & 0x7F) - 0x3F

loudness_menu = (data[5] >> 7) & 1
loudness_on   = (data[5] >> 6) & 1
autovol_menu  = (data[5] >> 4) & 1
autovol_on    = (data[5] & 0x07) == 0x07

ambiance_menu   = (data[6] >> 6) & 1
ambiance_code   = data[6] & 0x3F
AMBIANCE_NAMES  = {0x03: 'none', 0x07: 'classical', 0x0B: 'jazz-blues',
                   0x0F: 'pop-rock', 0x13: 'vocal', 0x17: 'techno'}
ambiance        = AMBIANCE_NAMES.get(ambiance_code, 'unknown')
```

### Test vectors

| Payload | Meaning |
|---|---|
| `3F 3F 3F 00 3F 00 03` | All flat, no menu open |
| `BF 3F 3F 00 3F 00 03` | L/R-balance menu open, centre |
| `3F 3F BF 00 3F 00 03` | Bass menu open, flat |
| `3F 3F 3F 00 3F 40 03` | Loudness enabled, no menu |
| `3F 3F 3F 00 3F 00 4F` | Pop-rock preset, ambiance menu open |

---

## 5. `0x225` — FM Tuner Status

**PSA name:** `ETAT_TUNER` (inferred)  
**Period:** 100 ms  
**Module:** `radio`  
**Confidence:** Verified from real bench capture (Peugeot 407, FM2 band at 96.0 MHz)

### Byte layout

| Byte | Bits | Signal | Notes |
|---|---|---|---|
| 0 | 7 | LIST | station list active |
| 0 | 6 | SCAN | scan mode active |
| 0 | 5 | RDS | RDS data available |
| 0 | 4 | PTY | PTY search / data available |
| 0 | 3 | TUN | currently tuning |
| 0 | 2 | TA | traffic announcement flag |
| 0 | 1:0 | TUNDIR | tuning direction (0=none, 1=up, 2=down) |
| 1 | 7:0 | MEMORY | memory preset number (0 = no preset) |
| 2 | 7:0 | BAND | band code (see table below) |
| 3–4 | 15:0 | FREQUENCY | uint16; `display_MHz = raw × 0.05 + 50` |

### Frequency encoding

```python
# Encode: MHz → CAN raw
freq_raw = round((freq_mhz - 50.0) / 0.05)  # e.g. 96.0 MHz → 920

# Decode: CAN raw → MHz
freq_mhz = freq_raw * 0.05 + 50.0            # e.g. 920 → 96.0 MHz
```

**ios-car-dashboard note:** The Arduino serial protocol sends frequency as `MHz × 10`
(e.g. 96 MHz → 960).  The relationship is: `serial_val = (CAN_raw / 2) + 500`, so the
encodings are consistent.

### Band codes

| BAND byte | Meaning |
|---|---|
| `0x00` | No band / unset |
| `0x10` | FM Band 1 |
| `0x20` | FM Band 2 (confirmed from bench capture) |
| `0x40` | FM Auto-store (AST) |
| `0x50` | AM / medium wave (frequency displayed as kHz) |

**Note:** The ios-car-dashboard Arduino serial protocol sends band as `CAN_byte >> 4`
(1=FM1, 2=FM2, 4=AST, 5=AM), which is consistent with the above encoding.

### Test vectors

| Payload | Decoded |
|---|---|
| `30 10 20 03 98` | FM2, mem=1, RDS+PTY on, TA off, 96.0 MHz (bench verified) |
| `40 00 10 02 EE` | FM1, scanning, 87.5 MHz (raw=750=0x02EE) |
| `00 03 50 03 A8` | AM, preset 3, 936 kHz (raw=936=0x03A8) |

---

## 6. `0x265` — RDS / Station Info Flags

**PSA name:** `INFO_TUNER` (inferred)  
**Period:** 100 ms  
**Module:** `radio`  
**Confidence:** Inferred (simulator implementation; not independently confirmed from ios-car-dashboard)

### Byte layout (observed from simulator)

| Byte | Value (CD/CDC mode) | Value (FM mode) | Notes |
|---|---|---|---|
| 0 | `0xBC` (`1 1 0 1 1 1 0 0`) | `0x30` (`0 0 1 1 0 0 0 0`) | Status flags |
| 1 | `0xE0` (`1 1 1 0 0 0 0 0`) | `0xE0` | Head-unit type flags |
| 2 | `0x01` | `0x01` | Sub-status |
| 3 | `0x01` (CD) / `0x00` (FM) | `0x00` | Source indicator |

**Byte 0 flag map (inferred from simulator can_rds implementations):**

| Bit | Mask | Meaning (tentative) |
|---|---|---|
| 7 | `0x80` | CD/changer active |
| 5 | `0x20` | RDS TA (traffic announcement) flag |
| 4 | `0x10` | RDS TP (traffic programme) flag |
| 2 | `0x04` | RDS PS valid |
| 1 | `0x02` | Station info valid |
| 0 | `0x01` | PTY data present |

---

## 7. `0x0A4` — RDS RadioText (RT)

**PSA name:** `TEXTE_RADIO` (inferred)  
**Period:** variable (100–500 ms between frames; head unit transmits when RDS RT is available)  
**Module:** `radio` (listen-only — emitted by head unit, received by display/simulator)  
**Confidence:** Bench-verified from the April 2026 `radio_loop.csv` capture

This frame carries the RDS RadioText (RT) string — a free-form text message up to 64 characters
broadcast by FM radio stations. The head unit splits the text across multiple CAN frames using
**ISO 15765-2 (ISO-TP)** transport protocol framing.

The verified dump shows a slightly richer real-world format than the earlier synthetic example:

- the first frame starts with `10 44`, meaning a **68-byte** total payload
- the reassembled payload begins with an internal **4-byte prefix** `10 00 00 00`
- the remaining **64 bytes** are the actual ASCII RadioText, space-padded on the right
- in monitor mode the simulator now strips that prefix and displays the recovered text directly in the Radio tab

### ISO 15765-2 Frame Types

| PCI high nibble | Frame type | Abbrev | Description |
|---|---|---|---|
| `0x0` | Single Frame | SF | Complete text fits in one CAN frame (1–7 bytes) |
| `0x1` | First Frame | FF | Start of multi-frame transfer; total length encoded in bytes 0–1 |
| `0x2` | Consecutive Frame | CF | Continuation; sequence number in low nibble (1–15, wraps to 0) |

### Single Frame (SF) layout

Used when the RT text is ≤ 7 characters.

| Byte | Bits | Field | Notes |
|---|---|---|---|
| 0 | 7:4 | PCI type = `0x0` | Single Frame |
| 0 | 3:0 | Data length N | 1–7 |
| 1–N | 7:0 | RT text | ASCII; NUL-terminated if shorter than N |

### First Frame (FF) layout

Used when the RT text is > 7 characters (typically 32 or 64 chars).

| Byte | Bits | Field | Notes |
|---|---|---|---|
| 0 | 7:4 | PCI type = `0x1` | First Frame |
| 0 | 3:0 | Total length [11:8] | High nibble of total message length |
| 1 | 7:0 | Total length [7:0] | Low byte of total message length |
| 2–7 | 7:0 | RT text [0:5] | First 6 bytes of the RT string |

### Consecutive Frame (CF) layout

| Byte | Bits | Field | Notes |
|---|---|---|---|
| 0 | 7:4 | PCI type = `0x2` | Consecutive Frame |
| 0 | 3:0 | Sequence number N | 1–15, wraps to 0 after 15 |
| 1–7 | 7:0 | RT text [chunk] | Next 7 bytes |

### Verified multi-frame sequence from the real dump

```
0x0A4  10 44 10 00 00 00 44 7A   # FF: total=68, embedded prefix + "Dz"
0x0A4  21 77 6F 6E 63 69 65 20   # CF SN=1
0x0A4  22 64 6F 20 6E 61 73 20   # CF SN=2
0x0A4  23 2D 20 74 65 6C 2E 20   # CF SN=3
0x0A4  24 31 32 20 44 57 41 20   # CF SN=4
0x0A4  25 4D 49 4C 49 4F 4E 59   # CF SN=5
0x0A4  26 20 63 7A 79 6E 6E 79   # CF SN=6
0x0A4  27 20 63 61 6C 61 20 64   # CF SN=7
0x0A4  28 6F 62 65 2E 20 20 20   # CF SN=8
0x0A4  29 20 20 20 20 20 20 00   # CF SN=9 + final padding/NUL
```

Decoded RadioText:

> Dzwoncie do nas - tel. 12 DWA MILIONY czynny cala dobe.

Other verified texts seen in the same capture include:

- `Zapraszamy na nasza strone: www.rmf.fm`
- `Osmioro dzieci nie zyje. Dramat w Luizjanie`
- `Polacy chca jasnych decyzji prezydenta. Sondaz nie pozostawia...`
- `RMF FM wita w Krakowie na czestotliwosci 96 MHz`

### Decode snippet

```python
pci_type = (data[0] >> 4) & 0x0F

if pci_type == 0:          # Single Frame
    payload = bytes(data[1:1 + (data[0] & 0x0F)])

elif pci_type == 1:        # First Frame — start accumulation buffer
    total_len = ((data[0] & 0x0F) << 8) | data[1]
    buf = {'total': total_len, 'next_sn': 1, 'data': bytearray(data[2:8])}

elif pci_type == 2:        # Consecutive Frame — extend buffer
    sn = data[0] & 0x0F
    buf['data'].extend(data[1:8])
    buf['next_sn'] = (sn + 1) & 0x0F
    if len(buf['data']) >= buf['total']:
        payload = bytes(buf['data'][:buf['total']])
        if payload.startswith(b'\x10\x00\x00\x00'):
            payload = payload[4:]
        text = payload.split(b'\x00', 1)[0].decode('ascii', errors='replace').strip()
        text = buf['data'][:buf['total']].strip('\x00').strip()
```

### Test vectors

#### SF — short RT (6 chars)

| Payload (hex) | Decoded RT |
|---|---|
| `06 52 4D 46 20 46 4D` | `"RMF FM"` |

#### SF — NUL-terminated RT

| Payload (hex) | Decoded RT |
|---|---|
| `06 48 65 6C 6C 6F 00` | `"Hello"` (NUL at position 5 terminates) |

#### FF + CF — 13-char RT

| Frame | Payload (hex) | Notes |
|---|---|---|
| FF | `10 0D 48 65 6C 6C 6F 2C` | total=13, text[0:6]="Hello," |
| CF SN=1 | `21 20 57 6F 72 6C 64 21` | text[6:13]=" World!" → complete: `"Hello, World!"` |

### Notes

- The simulator only **receives** this frame (`listen_only = True`).  
- The RD4 radio broadcasts RT asynchronously when an FM station provides an RDS signal.  
  RT is not always present; when absent, `car.radio.rds_text` stays at its last value (or
  empty string on startup).  
- RDS RT messages are typically padded to 32 or 64 characters with spaces.  The decoder strips
  trailing whitespace and truncates at the first `0x00` (NUL) byte.  
- If a Consecutive Frame arrives with the wrong sequence number the in-progress transfer is
  discarded silently; the previous `rds_text` is preserved.  
- Partial text is written to `car.radio.rds_text` after the First Frame (first 6 chars) and
  after each subsequent CF, so the UI label updates progressively.  
- The related `0x125` frame carries CD track lists and radio station lists using the same
  ISO-TP framing; it is not yet implemented.

---

## 9. `0x2A5` — Radio Station Name / RDS PS

**PSA name:** `NOM_STATION` (inferred)  
**Period:** 100 ms  
**Module:** `radio`  
**Confidence:** Inferred (simulator + ios-car-dashboard cross-reference)

### Byte layout

The payload is a raw ASCII string, left-justified, padded with `0x00` if shorter than the
frame.  Length is variable (typically 4–8 bytes).

```text
Bytes 0–7: ASCII station name / RDS PS (Programme Service) name
           e.g. 't', 'e', 's', 't' → [0x74, 0x65, 0x73, 0x74]
```

The ios-car-dashboard reads this as the station name (serial frame `0x04`) and the extended
description (serial frame `0x07`), both stripped of leading/trailing whitespace.

---

## 10. `0x3E5` — Steering Wheel Panel Buttons

**PSA name:** `CDE_CLAVIER_VOLANT` / `COMMANDES_CLAVIER` (inferred)  
**Period:** 50 ms  
**Module:** `radio`, `buttons`  
**Confidence:** Verified (simulator implementation)

This frame carries momentary button states from the steering wheel controls.  Two layouts
are used depending on whether the `buttons` module or `radio`/`radio` is active.

### `radio` / `radio` layout

| Byte | Bits | Button | Notes |
|---|---|---|---|
| 0 | 7:6 | MENU | menu navigation |
| 0 | 5:4 | TEL | telephone key |
| 0 | 1:0 | CLIM | climate shortcut |
| 1 | 7:6 | TRIP | trip computer |
| 1 | 5:4 | MODE | source/mode |
| 1 | 1:0 | AUDIO | audio settings |
| 2 | 7:6 | OK | confirm |
| 2 | 5:4 | ESC | escape |
| 5 | 7:6 | UP | scroll up |
| 5 | 5:4 | DOWN | scroll down |
| 5 | 3:2 | RIGHT | scroll right |
| 5 | 1:0 | LEFT | scroll left |

### `buttons` module layout

Same bit positions for `TEL`, `UP`, `DOWN`, `RIGHT`, `LEFT`, `OK`, `ESC`.  
Different keys: `TRIP` (b1[7:6]), `SOURCE` (b1[5:4]), `DARK` (b1[1:0]), `NEXT` (b2[3:2]), `PREV` (b2[1:0]).

### Notes

- Each button bit is `1` while pressed and `0` when released.
- The `buttons` module keeps each press asserted for a configurable pulse window (~150 ms,
  3 × 50 ms period) to ensure reliable reception by the head unit.
- Bytes 3 and 4 are always `0x00`.

---

## 11. Comparison summary: simulator vs ios-car-dashboard

| Signal | Simulator (Peugeot 407) | ios-car-dashboard (Peugeot 207) | Match? |
|---|---|---|---|
| Volume (0x1A5) | bits 4:0 of byte 0 | Arduino serial frame 0x01 | ✓ Identical |
| Radio source (0x165) | byte 2 high nibble, codes 1–7 | Arduino serial frame 0x03, codes 1/4/5 | ✓ Codes overlap |
| Audio settings (0x1E5) | 7-byte frame (see §4) | Arduino serial frame 0x10, same layout | ✓ Identical |
| Equalizer codes | none=3, classical=7, jazz=11, pop=15, vocal=19, techno=23 | Same | ✓ Identical |
| FM frequency (0x225) | `raw × 0.05 + 50` MHz | `MHz × 10` serial (= `(CAN_raw/2) + 500`) | ✓ Consistent |
| Station name (0x2A5) | ASCII bytes | Arduino serial frame 0x04 (string) | ✓ Consistent |
| Trip data (0x221/0x2A1/0x261) | See `doc/CAN_2004.md` | Arduino serial frames 0x0C, 0x0D, 0x0E | ✓ Consistent |
| Exterior temperature (0x0F6) | `raw × 0.5 − 40` °C | Arduino serial frame 0x02 (signed byte) | ✓ Consistent |

The 207 and 407 share the same RD4 radio platform (AEE2004 / CAN2004), so the signal
positions are expected to be identical for infotainment-related frames.

---

## 12. Open questions

- `0x265` byte 0 flag meanings are inferred from the simulator source; independent capture
  is needed to confirm each bit.
- `0x3E5` bytes 3–4 are always `0x00` in the simulator; real-bus captures may reveal
  additional signals in those bytes.
- The `radio` module sends both `0x165` and `0x225`; on a real bench with the MFD
  (multifunctional display) present, capturing the MFD's responses to those frames would
  help confirm decoding.
- ios-car-dashboard serial frame `0x42` ("secret button") has no obvious counterpart in
  the current simulator — the source CAN frame is unknown.
