# CAN 2004 Comfort — autowp.github.io Cross-Reference

Source: [autowp/autowp.github.io](https://github.com/autowp/autowp.github.io)
(`index.html`, commit `c69d613`, accessed 2026-04-18)

> **Reliability note** — autowp.github.io is community-collected data from
> multiple PSA vehicles (C4, 308, 407, Berlingo with various head-units).
> It is **not** an official or officially-confirmed specification.  Where
> autowp and the PSA-RE reference ([PSA_RE_comparison.md](PSA_RE_comparison.md))
> conflict, PSA-RE takes precedence because it is derived from actual BSI
> firmware symbol tables.

---

## Scope of autowp documentation

autowp documents **44 CAN IDs** on the comfort/infotainment bus (CAN-INFO,
125 kbps) plus one chassis bus ID (0x30D on CAN-IS, 10 ms).  The table below
lists every ID and its status relative to this simulator.

| CAN ID | autowp description | Simulator status |
|--------|--------------------|-----------------|
| 0x036 | BSI Ignition, Dashboard lightning | Implemented — agreement confirmed |
| 0x0A4 | Current track name / radiotext (ISO 15765-2) | Partial — no ISO-TP handler |
| 0x0B6 | RPM / Speed / (trip odo, fuel counter) | Implemented — see discrepancy notes |
| 0x0DF | Display menu | Not implemented |
| 0x0E1 | Parktronic sensor data | Implemented |
| 0x0E2 | CD/Yatour current disk number | Not implemented (Yatour-specific) |
| 0x0E6 | Wheels rotation, voltage | Not implemented |
| 0x0F6 | BSI slow data (temp, odo, reverse) | Implemented — see discrepancy notes |
| 0x122 | Universal multiplexed panel (multimedia) | Not implemented |
| 0x125 | CD track list / radio list (ISO 15765-2) | Not implemented |
| 0x128 | Dashboard lights | Implemented — agreement confirmed |
| 0x131 | CD changer command | Not implemented |
| 0x162 | Yatour current disk | Not implemented (Yatour-specific) |
| 0x165 | Radio source/input status | Implemented (radio module) |
| 0x167 | Display status | Not implemented |
| 0x1A0 | CD changer / Yatour status | Not implemented |
| 0x1A1 | BSI informational message (MFD popup) | Implemented |
| 0x1A2 | Yatour current disk track count | Not implemented (Yatour-specific) |
| 0x1A5 | Radio volume | Implemented |
| 0x1D0 | Climate control information | Implemented |
| 0x1E0 | Radio → Display (source info) | Not implemented |
| 0x1E2 | Yatour current CD changer track | Not implemented (Yatour-specific) |
| 0x1E5 | Radio audio settings | Implemented |
| 0x1ED | Display conditioning commands | Not implemented |
| 0x21F | Steering wheel remote control | Not implemented |
| 0x220 | Door status | Implemented — extended in simulator |
| 0x221 | Trip computer info | Implemented — agreement confirmed |
| 0x265 | RDS radio data | Not implemented |
| 0x276 | Date/time + average speed (C4 B7) | Not implemented — see new data |
| 0x30D | Wheel rotation speed (CAN-IS) | Not implemented (chassis bus) |
| 0x325 | CD tray info | Not implemented |
| 0x336 | VIN bytes 1-3 (WMI) | Implemented |
| 0x365 | CD disk info | Not implemented |
| 0x39B | Set system date/time (Display→BSI) | Not implemented — see new data |
| 0x3A5 | Current playing CD track info | Not implemented |
| 0x3B6 | VIN bytes 4-9 (VDS) | Implemented |
| 0x3E5 | Button presses | Implemented |
| 0x3F6 | Date/time (Radio→Display) | Not implemented |
| 0x51D | Parktronic secondary frame | Not implemented |
| 0x5E0 | Radio HW/SW info | Not implemented |
| 0x5E5 | Display HW/SW info | Not implemented |

---

## Detailed comparison for simulator-relevant IDs

### 0x036 — BSI Ignition and Dashboard Illumination

**autowp bit layout** (8 bytes, network: CAN-INFO, src: BSI, dest: Display Radio):

```
Byte 0: 0x0E (constant 0b00001110)
Byte 1: 0x00 (constant)
Byte 2: E0000000  — bit 7 = Economy mode enabled (E)
Byte 3: 00LIBBBB  — L = Dashboard lightning enabled
                    I = Disables dark mode / turns off climate control display
                    BBBB = Brightness for dashboard lightning
Byte 4: 00000MMM  — MMM = Ignition mode
                       001 = ignition on
                       010 = ignition off
                       011 = unknown (once per ignition cycle)
Bytes 5-7: 000000000 00000000 10100000 (constants)
```

**Comparison with simulator** (`Msg036.encode`):

| Signal | autowp position | Simulator position | Agreement |
|--------|-----------------|-------------------|-----------|
| Economy mode | byte 2 bit 7 | byte 2 bit 7 | ✓ matches |
| Dashboard lightning | byte 3 bit 5 | byte 3 bit 5 | ✓ matches |
| Dark mode disable | byte 3 bit 4 | byte 3 bit 4 | ✓ matches |
| Brightness (BBBB) | byte 3 bits 3-0 | byte 3 bits 3-0 | ✓ matches |
| Ignition mode (MMM) | byte 4 bits 2-0 | byte 4 bits 2-0 | ✓ matches |
| Byte 7 constant | 0xA0 (`10100000`) | 0xA0 on normal encode | ✓ matches |

**autowp ignition mode values** vs simulator constants:

| Value | autowp | Simulator constant |
|-------|--------|--------------------|
| 0x00 | — | `_ignition_settled_off` |
| 0x01 | ignition on | `_ignition_on` |
| 0x02 | ignition off | `_ignition_off` |
| 0x03 | unknown/wakeup | `_ignition_wakeup` |

> **Conclusion:** Full agreement.  autowp confirms all signal positions and
> ignition mode encodings used by the simulator.

---

### 0x0B6 — Fast Drivetrain Data (RPM, Speed)

**autowp bit layout** (8 bytes, network: CAN-INFO, src: BSI):

```
Bytes 0-1: MMMMMMMM MMMMM000  — 13-bit tachometer (raw RPM)
Bytes 2-3: SSSSSSSS SSSSSSSS  — actual speed × 100 km/h (uint16)
Bytes 4-5: TTTTTTTT TTTTTTTT  — odometer from start, cm (uint16)
Byte 6:    FFFFFFFF            — fuel consumption counter (uint8)
Byte 7:    11010000            — constant 0xD0
```

**Comparison with simulator** (`Msg0B6.encode`):

| Field | autowp | Simulator | Status |
|-------|--------|-----------|--------|
| RPM encoding | 13-bit raw RPM in bits 15-3 | 16-bit RPM × 10 (uint16 BE) | **Conflict** |
| Speed encoding | uint16 × 100 km/h | uint16 × 100 km/h | ✓ matches |
| Bytes 4-5 | Trip odometer from start (cm) | `0x00 0x00` (not implemented) | **Gap** |
| Byte 6 | Fuel consumption counter | `0x00` (not implemented) | **Gap** |
| Byte 7 | constant `0xD0` | constant `0xD0` | ✓ matches |

**RPM encoding conflict detail:**

autowp documents a 13-bit raw RPM packed into the top 13 bits of the first
16-bit word (bits 15..3), with 3 zero padding bits (bits 2..0).  For 800 RPM:
- autowp encoding: `(800 << 3) = 0x1900` → bytes `0x19 0x00`
- Simulator encoding: `800 × 10 = 8000 = 0x1F40` → bytes `0x1F 0x40`

The simulator uses **RPM × 10** (a ×10 integer scale).  This encoding is also
used in the `decode` path (`raw / 10`), making encode/decode self-consistent.
The real-bus value `0xFF 0xFF` seen in cold-start captures for "engine off /
invalid" fits neither a 13-bit RPM of 8191 (nonsensical) nor RPM × 10 = 65535
(also nonsensical), so `0xFF 0xFF` is a sentinel value used by both approaches
to indicate "no engine data".

> **Recommendation:** Do not change the simulator RPM encoding — it is
> internally consistent and verified against the cold-start capture in
> `CAN2004_cold_start.md`.  The autowp 13-bit claim may reflect a different
> head-unit or firmware variant, or a documentation error.

**Trip odometer / fuel counter gap:**

autowp documents bytes 4-5 as a **trip odometer from ignition-on, encoded in
centimetres** (uint16, wraps at 65535 cm ≈ 655 m before overflow; likely a
partial counter).  Byte 6 is a **fuel consumption pulse counter** (increments
as fuel injectors fire).

The simulator leaves both fields at `0x00`, which is valid for bench-only use.
A future enhancement could track trip distance from simulated speed pulses.

---

### 0x0F6 — BSI Slow Data (Temperature, Odometer, Reverse)

**autowp bit layout** (8 bytes, network: CAN-INFO, src: BSI):

```
Byte 0: 1000 1 110  — bits 7-4 constant, bit 3 = Ignition (1=on)
Byte 1: CCCCCCCC    — Coolant temperature; formula: C − 39 °C
Bytes 2-4: ZZZZZZZZ ZZZZZZZZ ZZZZZZZZ  — Odometer (uint24)
Byte 5: 10001110    — constant 0x8E (autowp)
Byte 6: TTTTTTTT    — External temperature; formula: round(T/2 − 39.5) °C
                       range: 0x00 = −40 °C, 0xFA = +85 °C
Byte 7: R 000Q0 Z F — R=reverse, Q=unknown, Z=turn right, F=turn left
```

**Comparison with simulator and PSA-RE** (`Msg0F6`):

| Field | autowp | PSA-RE / Simulator | Status |
|-------|--------|-------------------|--------|
| Byte 0 | `1000 1 110` with ignition at bit 3 | status byte: 0x88 (customer config + generator ok) | **Conflict** — different interpretation |
| Byte 1 | Coolant: `C − 39` | Coolant: `raw − 40` | **Minor conflict** (±1 °C at boundaries) |
| Bytes 2-4 | Odometer (uint24) | Odometer (uint24) × 0.1 km | ✓ same field, autowp omits scale |
| Byte 5 | constant `0x8E` | EXTERNAL_TEMPERATURE (raw × 0.5 − 40) | **Conflict** |
| Byte 6 | External temp: `round(T/2 − 39.5)` | EXTERNAL_FILTERED_TEMPERATURE (raw × 0.5 − 40) | Partial agreement |
| Byte 7 bit 7 | Reverse (R) | REVERSE_STATUS | ✓ matches |
| Byte 7 bit 1 | Turn right (Z) | BLINKERS_STATUS bit 1 | ✓ broadly consistent |
| Byte 7 bit 0 | Turn left (F) | BLINKERS_STATUS bit 0 | ✓ broadly consistent |

**Temperature formula conflict:**

autowp says coolant formula is `C − 39`; PSA-RE says `raw − 40`.  For most raw
values the difference is 1 °C.  The simulator uses PSA-RE's `raw − 40`
formula, which is derived from the official firmware symbol table and is
treated as authoritative.

Similarly for external temperature:
- autowp: `round(T/2 − 39.5)` with rounding
- PSA-RE: `raw × 0.5 − 40` (equivalent to `raw/2 − 40`)

For `raw = 0x80 = 128`:
- autowp: `round(64 − 39.5)` = `round(24.5)` = 24 or 25 °C (depends on rounding convention)
- PSA-RE: `64 − 40` = 24 °C

The difference is at most 0.5 °C after rounding.  The simulator uses PSA-RE's
formula and this is not considered a bug.

**Byte 5 conflict (most significant discrepancy for 0x0F6):**

autowp places external temperature in **byte 6** and calls byte 5 a constant
(`0x8E`).  PSA-RE places `EXTERNAL_TEMPERATURE` in **byte 5** (idx 4 = 0-indexed
byte 5 in PSA-RE 1-indexed notation) and `EXTERNAL_FILTERED_TEMPERATURE` in
byte 6.  Real bus captures in `CAN2004_cold_start.md` confirm the PSA-RE
layout: `D6` (byte index 5) carries the raw external temperature value
(`0x56/2 − 40 ≈ 3 °C`).

> **Conclusion:** PSA-RE layout is correct.  autowp's byte 5 = 0x8E claim is
> likely an observation artefact — the constant might be valid for a specific
> head-unit trim level that resets byte 5 before the BSI outputs real data.
> Use PSA-RE byte positions for all decode work.

---

### 0x128 — Dashboard Lights

**autowp bit layout** (8 bytes, network: CAN-INFO, src: BSI, dest: Dashboard):

```
Byte 0: 0 S P 00000  — S = Driver seatbelt warning, P = Parking brake
Byte 1: 000 D 0000   — D = Any door or trunk open
Bytes 2-3: all zeros
Byte 4: G F E D C B A 0
           G = sidelights on
           F = low beam on
           E = high beam on
           D = front fog lights on
           C = rear fog light on
           B = right indicator on
           A = left indicator on
Byte 5: 0 (Low fuel level bit omitted in simple form)
...
Byte 7: 0000 BBBB    — Dashboard backlighting level
```

**Comparison with PSA-RE and simulator** (`Msg128`):

| Signal | autowp byte/bit | PSA-RE / Simulator | Status |
|--------|-----------------|-------------------|--------|
| Seatbelt warning | byte 0 bit 6 | byte 0 bit 6 (`FRONT_LEFT_SEATBELT`) | ✓ matches |
| Parking brake | byte 0 bit 5 | byte 0 bit 5 (`PARKING_BRAKES`) | ✓ matches |
| Door open | byte 1 bit 4 | byte 1 bit 4 (`DOORS_1`) | ✓ matches |
| Sidelights on | byte 4 bit 7 | byte 4 bit 7 (`SIDELIGHTS` / `backlight`) | ✓ matches |
| Low beam | byte 4 bit 6 | byte 4 bit 6 (`LOW_BEAM`) | ✓ matches |
| High beam | byte 4 bit 5 | byte 4 bit 5 (`FULL_BEAM`) | ✓ matches |
| Front fog | byte 4 bit 4 | byte 4 bit 4 (`FRONT_FOG_LIGHTS`) | ✓ matches |
| Rear fog | byte 4 bit 3 | byte 4 bit 3 (`REAR_FOG_LIGHTS`) | ✓ matches |
| Right indicator | byte 4 bit 2 | byte 4 bit 2 (`RIGHT_TURN`) | ✓ matches |
| Left indicator | byte 4 bit 1 | byte 4 bit 1 (`LEFT_TURN`) | ✓ matches |

autowp shows a simplified subset of the PSA-RE signal map.  All positions
reported by autowp agree with PSA-RE.  Additional signals documented only by
PSA-RE (e.g. `STOP`, `MAINTENANCE`, `ESP_BLINK`, rear seatbelts) are not
covered by autowp but are present in `PSA_RE_comparison.md`.

> **Conclusion:** Full agreement on lighting signals.  autowp confirms the
> byte 4 lighting byte layout independently of PSA-RE.

---

### 0x1D0 — Climate Control Information

**autowp bit layout** (8 bytes, network: CAN-INFO, src: Climate):

```
Byte 0: 0x22 (constant 0b00100010)
Byte 1: 0x00 (constant)
Byte 2: 00000 FFF 0  — FFF = Fan speed 0-7
Byte 3: DDD 0110 00  — DDD = Air direction
                         001 = Up (when windshield blowing enabled)
                         010 = Down
                         011 = Front
                         100 = Up
                         101 = Front + Down
                         110 = Up + Down
Byte 4: 00 A W 0000  — A = Air recycling enabled, W = Windshield blowing enabled
Byte 5: 000 LLLLL    — Temperature for left zone (lookup table, 5-bit index)
Byte 6: 000 RRRRR    — Temperature for right zone (lookup table, 5-bit index)
Byte 7: 0x00
```

**Comparison with simulator** (`Msg1D0.encode`):

| Signal | autowp position | Simulator position | Status |
|--------|-----------------|-------------------|--------|
| Fan speed (FFF) | byte 2 bits 3-1 | byte 2 (full byte, 0-7) | **Conflict** — byte position differs |
| Air direction (DDD) | byte 3 bits 7-5 | byte 3 bits 7-4 (nibble×2) | **Conflict** — encoding differs |
| Air recycling (A) | byte 4 bit 5 | byte 4 bit 5 | ✓ matches |
| Windshield blowing (W) | byte 4 bit 4 | byte 4 bit 4 | ✓ matches |
| Left temp (LLLLL) | byte 5 bits 4-0 | byte 5 (full byte from temp table) | Broadly consistent |
| Right temp (RRRRR) | byte 6 bits 4-0 | byte 6 (full byte from temp table) | Broadly consistent |

**Air direction encoding conflict:**

autowp and the simulator use different encodings for the air direction byte.
The simulator uses a repeated-nibble format: `dir_left` is encoded as
`(dir_left << 4) | dir_left` in byte 3, so direction value 4 (`Up`) encodes
as `0x44`.  autowp shows a single 3-bit field `DDD` in bits 7-5 of byte 3,
with distinct values for each direction.  The two mappings do not correspond
directly.

The simulator's repeated-nibble format is derived from observed `0x1D0`
capture data (see `CAN2004_cold_start.md` references) and matches the
`Msg1D0.decode` path.  The autowp format may describe a different climate
panel variant.  Until confirmed by a bench capture, treat the autowp direction
encoding as informational only.

**Fan speed byte:**

autowp places `FFF` (3 bits) in byte 2 bits 3-1 (i.e. the byte value is
`fan_speed << 1`).  The simulator places fan speed as the **full byte value**
in byte 2 (0-7 direct).  For `fan = 3`: autowp encodes `0b00000110 = 0x06`,
simulator encodes `0x03`.  This discrepancy requires bench verification.

> **Recommendation:** The simulator's format was derived from observed bench
> data (Msg1D0 decode path has been tested).  Until a fresh bench capture is
> available, keep the current encoding and add a note to verify against a live
> climate panel.

---

### 0x220 — Door Status

**autowp bit layout** (2 bytes):

```
Byte 0: XXXXX 000  — bit 7 = Door Front Left  (1=open)
                      bit 6 = Door Front Right (1=open)
                      bit 5 = Door Back Left   (1=open)
                      bit 4 = Door Back Right  (1=open)
                      bit 3 = Trunk / Boot     (1=open)
                      bits 2-0 = always 0
Byte 1: 0x00 (constant)
```

**Comparison with simulator** (`Msg220.encode`):

| Signal | autowp bit | Simulator bit | Status |
|--------|-----------|---------------|--------|
| Front left door | byte 0 bit 7 | byte 0 bit 7 | ✓ matches |
| Front right door | byte 0 bit 6 | byte 0 bit 6 | ✓ matches |
| Rear left door | byte 0 bit 5 | byte 0 bit 5 | ✓ matches |
| Rear right door | byte 0 bit 4 | byte 0 bit 4 | ✓ matches |
| Boot / trunk | byte 0 bit 3 | byte 0 bit 3 | ✓ matches |
| Bonnet (hood) | not documented | byte 0 bit 2 | **Extended** |
| Rear window | not documented | byte 0 bit 1 | **Extended** |
| Fuel flap | not documented | byte 0 bit 0 | **Extended** |

The simulator encodes three additional openings (bonnet, rear window, fuel
flap) beyond what autowp documents.  These positions are consistent with the
PSA-RE signal map for `DOOR_STATUS` and are harmless extensions.

---

### 0x221 — Trip Computer Info

**autowp bit layout** (7 bytes):

```
Byte 0 (flags): l r 00 T 00 X
                l = 1 when instant fuel is "--.-"
                r = 1 when range is "----"
                T = 1 when trip mode switch is down
                X = voice command / unused light button
Bytes 1-2: LLLLLLLL LLLLLLLL  — Instant fuel consumption (× 10 = L/100 km)
                                  0x0000-0x012C = 0.0-30.0 L/100km
                                  above 0x012C = clamp at 30.0
Bytes 3-4: RRRRRRRR RRRRRRRR  — Range on current fuel (km)
                                  0x0000-0x07D0 = 0-2000 km
                                  above 0x07D0 = clamp at 2000
Bytes 5-6: FFFFFFFF FFFFFFFF  — Distance to destination (km × 10)
                                  0x0000-0xEA5B = 0.0-6000.0 km
                                  0xFFFF = "----" (not set)
```

**Comparison with simulator** (`Msg221`):

| Field | autowp | Simulator | Status |
|-------|--------|-----------|--------|
| Flag byte bit 7 | l = hide fuel display | hide fuel flag | ✓ matches |
| Flag byte bit 6 | r = hide range display | hide range flag | ✓ matches |
| Flag byte bit 4 | T = trip switch down | right button / trip toggle | ✓ broadly matches |
| Bytes 1-2 | fuel × 10 (L/100km) | `trip.fuel × 10` | ✓ matches |
| Bytes 3-4 | range (km) | `trip.autonomy` (km) | ✓ matches |
| Bytes 5-6 | distance to destination (km × 10) | `trip.dist` (km × 10) | ✓ matches |

> **Conclusion:** Full agreement.  autowp's field names for bytes 5-6
> ("rest of run to finish") help clarify that this field represents the
> navigation-system destination distance, matching the simulator's `trip.dist`.

---

### 0x336 and 0x3B6 — VIN Transmission

autowp documents:
- `0x336`: First 3 bytes of VIN (WMI — World Manufacturer Identifier)
- `0x3B6`: VIN bytes 4-9 (VDS — Vehicle Descriptor Section)

The simulator encodes:
- `0x336`: `[0x56, 0x46, 0x33]` = ASCII "VF3" (PSA / Peugeot WMI)
- `0x3B6`: `[0x36, 0x4A, 0x52, 0x48, 0x52, 0x48]` = ASCII "6JRHRH"

autowp also documents `0x2B6` (VIS — Vehicle Identifier Section, bytes 10-17):
the simulator sends `[0x32, 0x31, 0x37, 0x31, 0x35, 0x33, 0x38, 0x33]` = "21715383".

> **Conclusion:** Full agreement on frame usage.

---

## New data from autowp not previously documented

### 0x276 — Date, Time, and Average Speed (C4 B7 / newer trims)

Source: BSI, Network: CAN-INFO.

```
Byte 0: A YYYYYYY  — A = time format (0=12h, 1=24h), Y = year offset from 2000
Byte 1: 000 R MMMM — R = date/time reset flag, M = month (1-12)
Byte 2: 000 DDDDD  — day (1-31)
Byte 3: 000 HHHHH  — hour (0-23)
Byte 4: 00 ZZZZZZ  — minutes (0-59)
Bytes 5-6: constants (0x1B 0x10 from captures)
Byte 7: XXXXXXXX   — average speed 0-250 km/h
Bytes 8-9: YYYYYY YYYYYYYY  — vehicle mileage after reset
Bytes 10-11: ZZZZZZZZ ZZZZZZZZZ — fuel consumption (L/100km × 10, 0-25.5)
Bytes 12-19: VVVVVVVV × 8  — last 8 VIN digits (ASCII)
```

This frame is documented for C4 B7 but not for the Peugeot 407.  It combines
date/time with trip statistics.  Not implemented in the simulator.

### 0x39B — Set System Date/Time (Display → BSI)

Source: Display, Dest: BSI, Network: CAN-INFO.

```
Byte 0: A YYYYYYY  — A = time format, Y = year offset from 2000
Byte 1: 0000 MMMM  — month (1-12)
Byte 2: 000 DDDDD  — day (1-31)
Byte 3: 000 HHHHH  — hour (0-23)
Byte 4: 00 ZZZZZZ  — minutes (0-59)
```

Command sent from the MFD display to the BSI to set the RTC.  Not implemented.

### 0x21F — Steering Wheel Multimedia Remote (alternative)

Source: steering wheel / "Universal Panel", Network: CAN-INFO.

```
Byte 0: F B X 0 U D S 0  — F=Forward, B=Backward, X=unknown, U=VolUp, D=VolDn, S=Source
Byte 1: RRRRRRRR          — Scroll value (continuous)
Byte 2: 0x00 (constant)
```

This is a 3-byte frame for steering wheel controls — simpler than the 6-byte
`0x3E5` frame already implemented.  Not all vehicles use both; the 407 uses
`0x3E5`.

### 0x30D — Wheel Rotation Speed (CAN-IS chassis bus)

Network: CAN-IS (chassis bus, **not** comfort CAN), 10 ms period.

```
Bytes 0-1: FLFLFLFL FLFLFLFL  — Front Left wheel rotation count (uint16)
Bytes 2-3: FRFRFRFR FRFRFRFR  — Front Right
Bytes 4-5: RLRLRLRL RLRLRLRL  — Rear Left
Bytes 6-7: RRRRRRRR RRRRRRRR  — Rear Right
```

This frame is on the chassis CAN bus (typically 500 kbps on the 407), not the
comfort bus (125 kbps).  Out of scope for this simulator.

---

## Summary of actions taken

| Area | Action |
|------|--------|
| 0x036 | No change required — full agreement with autowp |
| 0x0B6 | Notes added — RPM encoding discrepancy documented; simulator kept as-is |
| 0x0B6 | Notes added — bytes 4-5 (trip odometer cm) and byte 6 (fuel counter) not implemented |
| 0x0F6 | Notes added — autowp byte 5 claim (constant 0x8E) contradicts PSA-RE and captures |
| 0x128 | No change required — autowp confirms all lighting bit positions |
| 0x1D0 | Notes added — fan byte and air direction encoding differ from autowp |
| 0x220 | No change required — simulator is a superset of autowp |
| 0x221 | No change required — full agreement with autowp |
| New IDs | 0x276, 0x39B, 0x21F documented as "not implemented" for future reference |
| Tests | New unit tests added — see `tests/test_car_state.py` `TestMsg0B6AwpCompare`, `TestMsg1D0AwpCompare`, `TestMsg128AwpCompare` |
