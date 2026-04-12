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

## 3. Secondary signal — `0x225` D1 bit 4 (MEDIUM confidence)

| State | D1 hex | D1 binary | bit 4 |
|---|---|---|---|
| Lights OFF | `0x20` | `00100000` | 0 |
| Side lights ON | `0x30` | `00110000` | 1 |

Transition at **t+2.02 s**, which is ~400 ms **before** `0x128` changes at t+2.43 s.
This may be a pre-activation signal from BSM/body control — or the rotary switch
position being reported earlier than the actual light relay state.

Remains set for headlights and full beam.

---

## 4. Secondary signal — `0x1A1` D1 bit 7 (MEDIUM confidence)

| State | D1 hex | Meaning |
|---|---|---|
| OFF / Side lights | `0x00` | Headlights inactive |
| Headlights / Full beam | `0x80` | Headlamps active |

Transition at **t+4.36 s** (headlights), before `0x128` changes at t+4.53 s.
D2 and D3 also change significantly at the same time:
```
OFF:   00 65 41 ...
HEAD:  80 E0 46 ...
```
D2 change (`0x65→0xE0`) and D3 (`0x41→0x46`) may encode headlamp intensity or
adaptive lighting angle — needs further investigation.

---

## 5. `0x120` — rolling counter, NOT lights-related

`0x120` cycles through 3 fixed payloads every 1 second regardless of light state.
Transitions that appear in the "headlights" and "full beam" windows are coincidental.

Cycle sequence:
```
FC 00 00 00 00 0F 00 00
BC 00 00 00 00 00 00 00
7C 10 00 03 00 04 00 08
```
Probably a rolling version/status counter from another ECU.

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
| Side+head lamp active flag? | `0x225` | D1 | `0x10` | Set at side lights or above |
| Headlamp relay active? | `0x1A1` | D1 | `0x80` | Set at headlights or above |

---

## 8. Simulator implementation notes

The `clim` and `bsi-base` modules need updates to:
1. Emit `0x128` with correct D5 when light state changes in UI.
2. Automatically update `0x036` D4 dash illumination bit when side lights or above.
3. Optionally reflect `0x225` D1 bit 4 and `0x1A1` D1 bit 7 for ECU compatibility.

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
