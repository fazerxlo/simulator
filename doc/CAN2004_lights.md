# CAN2004 Lights Analysis — Peugeot 407

Source log: `lights_off_side_light_on_headlights_on.csv`  
Scenario: ignition ON → lights OFF/AUTO → side lights → headlights → full beam  
Log span: **10.3 s**, **2 992 frames**

---

## 1. Primary signal — `0x128` D5 (confirmed, HIGH confidence)

This is the definitive lights state byte. A single byte encodes all 4 positions with a clean additive bitfield.

### Encoding

| State | D5 hex | D5 binary | Bits set |
|---|---|---|---|
| OFF / AUTO | `0x00` | `00000000` | — |
| Side lights | `0x80` | `10000000` | bit 7 |
| Headlights (low beam) | `0xC0` | `11000000` | bit 7 + bit 6 |
| Full beam (high beam) | `0xE0` | `11100000` | bit 7 + bit 6 + bit 5 |

### Bit map

| Bit | Mask | Meaning |
|---|---|---|
| 7 | `0x80` | Lights switch engaged (any lights on) |
| 6 | `0x40` | Low beam active |
| 5 | `0x20` | High beam active |
| 4–0 | `0x1F` | Unchanged in this log (static `0x00`) |

### Observed transitions

| Time | Value | Event |
|---|---|---|
| t+0.14 s | `0x00` | Log start — lights OFF / AUTO |
| t+2.43 s | `0x80` | Rotary → side lights |
| t+4.53 s | `0xC0` | Rotary → headlights |
| t+6.66 s | `0xE0` | Stalk → full beam |
| t+6.69 s | `0xA0` | **Transient** — 30 ms after full beam |

### Transient state `0xA0`

Appears 30 ms after full beam (`0xE0`). Bit 6 (low beam) drops but bit 5 (high beam) stays set:
```
0xA0 = 10100000 = bit7 + bit5
```
Hypothesis: debounce artefact of the stalk spring-return. The physical stalk
briefly passes through a position where headlight relay drops before high beam latches.  
Safe to treat `0xA0` as equivalent to `0xC0` (headlights) in a decoder —
or map it to `FULL_BEAM` since it appears only during the full-beam action.

### Python decode snippet

```python
# 0x128 D5 light switch state
def decode_lights(data: bytes) -> str:
    d5 = data[4]
    HIGH_BEAM_MASK  = 0x20
    LOW_BEAM_MASK   = 0x40
    LIGHTS_ON_MASK  = 0x80
    if not (d5 & LIGHTS_ON_MASK):
        return "OFF"
    if d5 & HIGH_BEAM_MASK:
        return "FULL_BEAM"   # 0xE0 or transient 0xA0
    if d5 & LOW_BEAM_MASK:
        return "HEADLIGHTS"  # 0xC0
    return "SIDE_LIGHTS"     # 0x80
```

### Test vectors

| Raw D5 | Expected |
|---|---|
| `0x00` | `OFF` |
| `0x80` | `SIDE_LIGHTS` |
| `0xC0` | `HEADLIGHTS` |
| `0xE0` | `FULL_BEAM` |
| `0xA0` | `FULL_BEAM` (transient) |

---

## 2. Secondary signal — `0x036` D4 (dash lights, HIGH confidence)

BSI activates dashboard illumination automatically when side lights are switched on.

| State | D4 hex | D4 binary | Dash light bit | Luminosity nibble |
|---|---|---|---|---|
| Lights OFF | `0x0F` | `00001111` | 0 (off) | 15 |
| Side lights ON | `0x2A` | `00101010` | 1 (on) | 10 |

### Bit map of D4

| Bits | Mask | Meaning |
|---|---|---|
| 5 | `0x20` | Dashboard illumination enabled |
| 4 | `0x10` | Dark mode |
| 3–0 | `0x0F` | Luminosity level (0–15) |

Dashboard illumination turns on (bit 5 = 1) together with side lights.
Luminosity auto-adjusts from 15 (max/day) to 10 (ambient-adjusted).

Remains at `0x2A` for all subsequent light states (headlights, full beam).

---

## 3. Secondary signal — `0x225` D1 bit 4 (COINCIDENTAL — FM Tuner RDS/PTY)

> ⚠️ **Protocol Clarification:** Cross-referencing against verified infotainment specifications (see [CAN2004_radio.md §5](CAN2004_radio.md)) and `generated/radio_messages.py` confirms that **`0x225` is the FM Tuner Status frame** (`ETAT_TUNER`), emitted by the radio head-unit. In Byte 0 (D1), bit 5 is `RDS` and bit 4 is `PTY` (Program Type search/flag). This frame has **no connection to exterior lighting**; the transition observed during the bench test was coincidental RDS tuner activity.

| State | D1 hex | D1 binary | bit 4 |
|---|---|---|---|
| Lights OFF | `0x20` | `00100000` | 0 |
| Side lights ON | `0x30` | `00110000` | 1 |

---

## 4. Secondary signal — `0x1A1` D1 bit 7 (COINCIDENTAL — BSI Popup Alert)

> ⚠️ **Protocol Clarification:** Verified BSI documentation (see [CAN2004_doors.md §2](CAN2004_doors.md), [PSA_RE_comparison.md](PSA_RE_comparison.md), and [CAN_2004.md §3](CAN_2004.md)) confirms that **`0x1A1` is the BSI MFD popup / alert notification frame** (`BSI_DISPLAY_MESSAGE`). Byte 0 (D1) bit 7 (`0x80`) is the `DISPLAY_MESSAGE` show trigger, D2 is the `MESSAGE_ID`, and D3 is display destination flags (`0xC6`/`0x46`). The transition observed here coincided with an automatic headlight or dashboard status popup, not a headlamp relay or steering angle signal.

| State | D1 hex | Meaning |
|---|---|---|
| OFF / Side lights | `0x00` | Popup idle / dismiss |
| Headlights / Full beam | `0x80` | Popup active (`DISPLAY_MESSAGE`) |

Transition at **t+4.36 s** (headlights), before `0x128` changes at t+4.53 s.

---

## 5. `0x120` — Alerts Journal (multiplexed), NOT lights-related

`0x120` cycles through 3 fixed payloads every 1 second. As detailed in [CAN2004_0x120.md](CAN2004_0x120.md), this is the **multiplexed Alerts Journal / Diagnostics frame**, cycling across Block 1, Block 2, and Block 3 selected by `data[0]` bits 7:6:

```
FC 00 00 00 00 0F 00 00   (Block 3: bits 7:6 = 11)
BC 00 00 00 00 00 00 00   (Block 2: bits 7:6 = 10)
7C 10 00 03 00 04 00 08   (Block 1: bits 7:6 = 01)
```
While not a lighting frame, it is the alert diagnostic broadcast.

---

## 6. `0x260` — rotating 3-state counter, NOT lights-related

Cycles through 3 payloads every ~500 ms throughout the entire log.
Ignore for lights decoding.

---

## 7. Full signal map for simulator implementation

| Signal | CAN ID | Byte | Mask | Meaning |
|---|---|---|---|---|
| Light switch position | `0x128` | D5 | `0xE0` | See bitfield above |
| Dash illumination enabled | `0x036` | D4 | `0x20` | Set when any lights on |
| Dash luminosity | `0x036` | D4 | `0x0F` | 15=day, 10=lights on |

*(Note: `0x225` and `0x1A1` were observed in the capture but are FM tuner and popup alert frames respectively; they should not be simulated as lighting outputs.)*

---

## 8. Simulator implementation notes

The `clim` and `bsi-base` modules need updates to:
1. Emit `0x128` with correct D5 when light state changes in UI.
2. Automatically update `0x036` D4 dash illumination bit when side lights or above.
3. Keep `0x225` strictly in the `radio` module and `0x1A1` in `bsi-log`.

Current `0x128` in `bsi-base` emits the frame — verify D5 encoding matches.

---

## 9. Open questions

- What do `0x1A1` D2 and D3 carry? (changes at headlights — adaptive lighting angle?)
- Is `0xA0` in `0x128` D5 always transient, or is it a real state (e.g. flash-to-pass)?
- Does `0x128` D5 lower nibble (`0x1F`) encode wiper state in the same frame?
- Does `0x225` D1 bit 5 (`0x20`) carry a separate meaning? (set in both states)
- Verify: does `0x036` D4 luminosity value track a dashboard dimmer control?

---

## 10. Recommended next capture

To pin down `0x1A1` D2/D3 and rule out adaptive headlights:

1. Capture with headlights ON, car stationary.
2. Capture while slowly turning steering wheel.
3. Compare `0x1A1` D2 and D3 — if they change, it is adaptive headlamp angle.

To clarify `0xA0` transient vs flash-to-pass:

1. Capture momentary flash-to-pass (push stalk forward without latching).
2. Check if `0x128` D5 = `0xA0` or `0xE0` during the flash, and for how long.
