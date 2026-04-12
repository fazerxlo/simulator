# CAN2004 Cold Start Analysis — Peugeot 407

Source log: `power_on_and_ignition_on.csv`  
Scenario: bench power on → wait → ignition on  
Log span: **86.4 s**, **10 548 frames**, timestamp unit: µs

---

## 1. Phase summary

| Phase | Time window | Active IDs | Description |
|-------|-------------|-----------|-------------|
| Power ON | t+0.0 s … t+50.65 s | 7 | BSI only, sparse bus |
| Ignition transition | t+50.65 s … t+50.70 s | — | 0x036 D5: 0x03 briefly |
| Ignition ON | t+50.70 s … end | 83 | Full bus awake |

---

## 2. 0x036 — BSI Power Mode

Period: ~100 ms (post-ignition), slower pre-ignition.

| Byte (1-indexed) | Symbol | Notes |
|---|---|---|
| D1 | `0x0E` | Constant in this log |
| D4 | `0x0F` | Constant in this log |
| **D5** | **Ignition state** | See table below |
| D8 | `0xA0` | Constant after boot; `0x50` only on the very first frame |

### D5 ignition state values observed

| Value | Time | Interpretation | Confidence |
|---|---|---|---|
| `0x02` | t+0.39 s → t+14.29 s | Power-on announcement / ACC init | High |
| `0x00` | t+14.29 s → t+50.65 s | Stable pre-ignition / key not engaged | High |
| `0x03` | t+50.65 s (≈40 ms only) | Key turning, wakeup transition | High |
| `0x01` | t+50.70 s onwards | Ignition RUN state | High |

> The simulator already uses `0x01` / `0x02` / `0x03`. The `0x00` (settled off) state is not
> explicitly emulated — consider handling it in `bsi-base` for bench fidelity.

---

## 3. Pre-ignition bus (Phase 1)

Only these 7 IDs are alive when BSI has power but ignition is off:

| ID | Period | Sample data | Notes |
|---|---|---|---|
| `0x036` | ~175 ms slow, ~100 ms fast | `0E 00 00 0F 00 00 00 A0` | Power mode, emitted by BSI |
| `0x110` | ~100 ms | `FF FF FF FF 00 00 00 00` | All-FF status; unknown function |
| `0x190` | ~200 ms | `FF FF 02 77 FF FF FF FF` | D4=`0x77` pre-ignition |
| `0x1D0` | ~500 ms | `08 00 00 00 00 0B 0B 00` | Unchanged throughout log |
| `0x1E3` | ~200 ms | `1C 40 0B 0B 00 00 00 00` | D2 changes at ignition |
| `0x217` | ~100 ms | `A0 00 00 00 00 FF 00 00` | D1 bit 0 set at ignition |
| `0x52D` | ~1 s | `00 00 00 00 00 00 00 00` | All zeroes pre-ignition |

---

## 4. Ignition ON transition — key signal changes

### 0x036 D5
- `0x00` → `0x03` (brief, ~40 ms) → `0x01`

### 0x52D
```
Pre:   00 00 00 00 00 00 00 00
Post:  01 00 00 00 01 00 00 00
```
- D1 and D5 both flip `0x00 → 0x01` exactly at ignition.
- Likely an ignition-confirming echo or module-ready flag.
- Confidence: **high**.

### 0x190 D4
```
Pre:   FF FF 02 77 FF FF FF FF   (D4 = 0x77)
Post:  FF FF 02 7E FF FF FF FF   (D4 = 0x7E)
```
- D4 lower nibble changes `0x7 → 0xE` at ignition.
- After ignition D4 alternates `0x7E ↔ 0x7F` every ~200 ms → bit 0 is a **rolling counter**.
- Bits 4–7 of D4 (`0x70` = constant `7`) — purpose unknown.
- Confidence for counter: **high**. Semantic of upper nibble: **low**.

### 0x1E3 D2
```
Pre:   1C 40 0B 0B 00 00 00 00
Post:  1C 30 0B 0B 00 00 00 00
```
- D2 changes `0x40 → 0x30` at ignition.
- Upper nibble `0x4 → 0x3` — possibly a state/mode nibble.
- Confidence: **medium** (only one transition observed).

### 0x217 D1 and D3
```
Pre:   A0 00 00 00 00 FF 00 00
Post:  A1 00 80 00 00 FF FF E0   (t+50.92 s)
```
- D1 bit 0: `0 → 1` at ignition. Likely **ignition flag**.
- D3 `0x00 → 0x80` shortly after. D7 `0x00 → 0xFF`. D8 `0x00 → 0xE0`.
- Confidence for D1 bit 0 = ignition: **high**.
- Bytes D3, D7, D8: settling of other ECU state, **medium**.

---

## 5. Ignition wake burst — 76 new IDs appear within 200 ms of t+50.65 s

### Fast periodic (≈50 ms)
`0x0B6`

### Normal periodic (≈100 ms)
`0x036`, `0x110`, `0x126`, `0x131`, `0x14C`, `0x162`, `0x165`,
`0x167`, `0x18C`, `0x21F`, `0x217`, `0x24C`, `0x28C`, `0x355`

### Medium periodic (≈200 ms)
`0x128`, `0x168`, `0x190`, `0x1A1`, `0x1A8`, `0x1CC`, `0x1DF`, `0x1E3`

### Slow periodic (≈500 ms)
`0x0F6`, `0x12D`, `0x161`, `0x1A0`, `0x1A2`, `0x1D0`, `0x1E1`,
`0x1E2`, `0x220`, `0x225`, `0x227`, `0x260`, `0x265`, `0x2A0`,
`0x325`, `0x361`, `0x365`, `0x3A5`, `0x3A7`, `0x525`

### Very slow periodic (≈1 s)
`0x0E2`, `0x120`, `0x261`, `0x2A1`, `0x2B6`, `0x2E1`, `0x315`,
`0x317`, `0x336`, `0x3B6`, `0x50C`, `0x512`, `0x51D`, `0x51F`,
`0x520`, `0x52D`, `0x531`

### One-shot init frames (appear exactly once at ignition)
Sent once by each ECU as it wakes up. Likely version/calibration data.

| ID | Data | ASCII | Hypothesis |
|---|---|---|---|
| `0x5CC` | `0C 19 01 06 0A 09 20 12` | `...... .` | ECU calibration date or version |
| `0x5D2` | `B0 00 00 00 01 0A 06 16` | `........` | ECU calibration date: 2022-10-01? |
| `0x5DD` | `1D 02 06 05 02 84 20 12` | `...... .` | ECU version data |
| `0x5DF` | `1F 18 09 03 08 00 20 0D` | `...... .` | ECU version data |
| `0x5E0` | `20 1E 03 04 05 0E 20 0D` | ` ..... .` | ECU version data |
| `0x5E5` | `25 09 03 05 18 08 20 11` | `%..... .` | ECU version data |
| `0x5ED` | `2D 09 06 04 64 05 20 0D` | `-...d. .` | ECU version data |
| `0x5F1` | `31 14 08 03 05 00 20 09` | `1..... .` | ECU version data |
| `0x48C` | `50 FC 18 FF 04 06 07 08` | `P.......` | Unknown init |

---

## 6. Known IDs — data observed at ignition

### 0x0B6 — Engine / drivetrain (50 ms)
```
FF FF 00 00 00 00 00 D0    (initial, RPM=invalid, speed=0)
FF FF FF FF 00 00 00 D0    (after ~2 s — engine off, all invalid)
```
- RPM bytes D1-D2 = `0xFFFF` = no engine running. Expected.
- Speed bytes D3-D4 = 0. Expected (stationary bench).

### 0x0F6 — Vehicle body status (500 ms)
```
t+50.98 s:  88 3C 1F 5E 0B 56 FF 28
t+51.48 s:  88 3C 1F 5E 0B 56 56 28
t+51.98 s:  88 3C 1F 5E 0B 55 56 28
t+52.98 s:  88 FF FF FF FF 55 56 28
t+53.71 s:  88 FF FF FF FF 55 56 20
```
- D1 = `0x88` constant.
- D2 = `0x3C` initially (coolant = 0x3C - 40 = 20°C cold start), then `0xFF` (sensor unavailable, engine off).
- D6 = `0x56` → `0x55` → `0x57` — external temperature: `0x56/2 - 40 = 3°C`. Plausible bench temp.
- D7 = ext temp duplicate.
- D8 = `0x28` → `0x20` — reverse gear bit (bit 7) and other flags.

### 0x2B6 / 0x336 / 0x3B6 — VIN (_~1 s)
All three confirmed matching the simulator's hardcoded values:

| ID | Data | Content |
|---|---|---|
| `0x336` | `XX XX XX` | WMI = `[REDACTED]` (Peugeot) |
| `0x2B6` | `XX XX XX XX XX XX XX XX` | VIS = `[REDACTED]` |
| `0x3B6` | `XX XX XX XX XX XX` | VDS = `[REDACTED]` |

Combined VIN: **[REDACTED]**

> These are **periodic** at ~1 s on real BSI. The simulator produces them at 100 ms.
> Consider aligning simulator period to 1000 ms for bus fidelity.

### 0x1E1 — Steering wheel / column status (500 ms)
```
t+50.74 s:  80 80 80 80 80 80 00 00
t+53.24 s:  40 40 40 40 80 20 00 00
```
- All `0x80` pattern at ignition suggests "no button pressed" default.
- Change at t+53 s may be due to controls powering up / calibrating.
- D5 = `0x80` unchanged — may separate row.
- Follow-up wheel-turn test (max right -> max left) showed `0x1E1` remained static.
- Confidence: **medium** for button/column status, **low** for steering angle.

### 0x1A1 — Steering / front lighting state candidate (200 ms)
Observed in wheel-turn follow-up capture (`turn_wheels_right_then_left.csv`):
```
t+0.06 s:   00 78 46 80 00 00 00 00
t+3.64 s:   80 7F 46 FF FF FF FF FF   (max right action window)
t+15.65 s:  00 83 46 FF FF FF FF FF   (max left action window)
```
- D1 bit 7 toggles with side state (`0x00 <-> 0x80`).
- D2 moves around `0x80` (`0x78 -> 0x7F -> 0x83`) and is the best steering-position candidate.
- D3 stayed constant (`0x46`) in this run.
- Confidence: **medium** (direction/state), requires slow sweep capture for angle scaling.

---

## 7. IDs worth investigating next (not yet decoded)

| ID | Period | Sample | Priority |
|---|---|---|---|
| `0x110` | 100 ms | `FF FF FF FF 00 00 00 00` | Medium — always alive, unknown |
| `0x120` | 1 s | `BC 00 00 00 00 00 00 00` | Medium — first byte `0xBC` |
| `0x14C` | 100 ms | `00 00 00 00 80 00 00 00` | Low |
| `0x15B` | 260 ms | `05 00 00 00 00 00 00 00` | Low |
| `0x1CC` | 200 ms | `00 00 00 00 00 00 00 00` | Low — all zeros |
| `0x24C` | 100 ms | `04 00 00 00 00 00 00 00` | Medium — matches 0x28C |
| `0x28C` | 100 ms | `04 00 00 00 00 00 00 00` | Medium — same as 0x24C |
| `0x355` | 100 ms | `02 00 00 00 00 00 00 00` | Medium |
| `0x512` | 1 s | `01 00 00 00 00 00 00 00` | Low |

---

## 8. Recommended next captures

To decode lights state (your planned next scenario):

1. Capture **baseline**: ignition ON, lights OFF — save as `lights_baseline.log`
2. Capture **action 1**: switch to parking lights — save as `lights_parking.log`
3. Capture **action 2**: switch to low beam — save as `lights_low_beam.log`
4. Compare:
   ```
   python -m tools.can_sniff_ai_agent compare lights_baseline.log lights_parking.log
   python -m tools.can_sniff_ai_agent compare lights_parking.log lights_low_beam.log
   ```

Primary candidates for lights signal based on this log: **`0x128`** (confirmed), plus secondary context IDs **`0x225`** and **`0x1A1`**.

---

## 9. Open questions

- What does `0x1D0` encode? Completely static throughout 86 s log.
- What does `0x52D` D5 represent? (Both D1 and D5 flip to 0x01 at ignition.)
- Does `0x190` D4 upper nibble carry meaning beyond the rolling counter bit 0?
- Why does `0x036` first broadcast `0x02` for ~14 s then drop to `0x00` — is this BSI ACC detection timeout?
- VIN period mismatch: simulator 100 ms vs real BSI ~1000 ms.
- For `0x1A1`, determine angle scaling/sign with a slow center->right->left sweep capture.
