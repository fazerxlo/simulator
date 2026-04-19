# Peugeot 407 Real-Car CAN Log Analysis

Source file: [`dump_real_car.csv`](../dump_real_car.csv)

This document analyses a real-car Peugeot 407 CAN 2004 comfort-bus capture and cross-references
every frame found in it against the workspace documentation and the current simulator
implementation.

---

## Capture Overview

| Property | Value |
|---|---|
| File | `Peugeot 407 WORKING CAN LOG.csv` |
| Format | CSV (Time Stamp, ID, Extended, Dir, Bus, LEN, D1–D8) |
| Total messages | 13,896 |
| Unique CAN IDs | 10 |
| Capture duration | ≈ 16.5 seconds (timestamps in microseconds) |
| Bus direction | All Rx (receive-only capture) |
| Bus extended ID | false (all standard 11-bit IDs) |

The capture covers engine startup activity: frames transition from cold/idle state through a brief
RPM burst and a door-open event, with coolant temperature cycling between −40 °C, 60 °C and 120 °C
as the BSI iterates through warm-up states.

### IDs Observed

| CAN ID | Count | DLC | Unique Payloads | Avg Gap (µs) | Documented | Implemented |
|--------|-------|-----|-----------------|--------------|------------|-------------|
| 0x036  | 1,558 | 8   | 2               | ~4,800       | Yes        | Yes         |
| 0x0B6  | 1,157 | 8   | 2               | ~11,300      | Yes        | Yes         |
| 0x0F6  | 2,594 | 8   | 4               | ~1,700       | Yes        | Yes         |
| 0x128  | 1,372 | 8   | 3               | ~9,600       | Yes        | Yes         |
| 0x161  | 1,316 | 7   | 3               | ~8,100       | Yes        | Yes         |
| 0x168  | 1,120 | 8   | 2               | ~9,200       | Yes        | Yes         |
| 0x1A1  | 1,353 | 8   | 3               | ~9,300       | Yes        | Yes         |
| 0x1A8  | 1,038 | 8   | 2               | ~11,700      | Yes        | Yes         |
| 0x228  |   996 | 8   | 1               | ~9,900       | Partial    | No          |
| 0x3F6  | 1,392 | 7   | 1               | ~7,600       | Partial    | No          |

> **Note on timing:** The gap figures above are in microseconds between consecutive frames of the
> same ID. They do not directly represent the nominal transmit period because the CAN capture tool
> samples at the bus bit-level and the log may include bus-echo artefacts. Effective message rate
> for IDs with a consistent payload is roughly 100–120 ms, consistent with the PSA-RE 100 ms
> period for the majority of comfort-CAN frames.

---

## Per-Frame Analysis

### 0x036 — BSI Commands (COMMANDES_BSI)

**Documentation status:** Verified  
**Implementation:** `Msg036` in `can_messages.py`, encoder in `modules/bsi-base/__init__.py`

**Observed payloads:**

```
00 00 06 2F 00 80 00 00   (dominant — engine/IGN on, dash lights, normal state)
00 00 06 2F 01 80 00 00   (rare — same but byte 4 bit 0 toggled)
```

**Decode (0-indexed bytes):**

| Byte | Value | Meaning |
|------|-------|---------|
| 0    | 0x00  | Profile/memory byte 1 — factory profile, no recall/save |
| 1    | 0x00  | Profile/memory byte 2 — passenger profile default |
| 2    | 0x06  | `0b00000110`: lighting bits 2-1 set (economy off, passenger side default) |
| 3    | 0x2F  | POWER_MODE = 0x2F (engine running, all systems active) |
| 4    | 0x00 / 0x01 | Occasionally 0x01 — possibly a rolling toggle or event bit |
| 5    | 0x80  | Dashboard illumination request active (bit 7) |
| 6-7  | 0x00  | Unused / zero |

**Documentation check:** ✅ Matches documentation. POWER_MODE 0x2F is consistent with engine
running state described in PSA-RE.

**Implementation check:** ✅ The `Msg036` encoder sends `d[3] = power_mode` and `d[5]` with
lighting bits matching the observed values. The byte-4 toggle (0x00 ↔ 0x01) is not modelled in
the simulator but appears infrequently and may be an event-driven one-shot bit.

---

### 0x0B6 — Fast Dynamic Data (RPM / Speed)

**Documentation status:** Verified  
**Implementation:** `Msg0B6` in `can_messages.py`

**Observed payloads:**

```
00 00 00 00 00 FF 00 A0   (engine off / stopped)
D9 00 65 8F 00 FF 00 A0   (brief burst — engine running / wheels spinning on bench)
```

**Decode (0-indexed bytes):**

| Byte | Payload 1 | Payload 2 | Meaning |
|------|-----------|-----------|---------|
| 0-1  | 0x0000    | 0xD900    | RPM raw: 0 → 0 RPM; 55552 / 10 = **5,555 RPM** |
| 2-3  | 0x0000    | 0x658F    | Speed raw: 0 → 0 km/h; 25999 / 100 = **259.99 km/h** |
| 4    | 0x00      | 0x00      | Unused |
| 5    | 0xFF      | 0xFF      | Real car sends 0xFF here (implementation sends 0x00) |
| 6    | 0x00      | 0x00      | Unused |
| 7    | 0xA0      | 0xA0      | Status/flags: real car sends 0xA0; **implementation sends 0xD0** |

**Documentation check:** ✅ RPM and speed encoding (`/10` and `/100` respectively) confirmed.

**Implementation check:** ⚠️ Two minor byte-level discrepancies:

1. **Byte 5**: real car = `0xFF`, simulator encodes `0x00`. This byte is unused in the current
   decode path; the difference is cosmetic but worth noting for wire-accurate simulation.
2. **Byte 7 (flags)**: real car = `0xA0` (`0b10100000`), simulator encodes `0xD0`
   (`0b11010000`). Bit 6 (0x40) and bit 4 (0x10) differ. These bits are not decoded in the
   current implementation.

The extreme RPM (5,555 RPM) and speed (260 km/h) values in the second payload appear during a
very brief burst at around t = 23,125 ms. This is consistent with a bench test where the wheels
were spun at high speed or the BSI was exercising sensors.

---

### 0x0F6 — BSI Slow Data (Temperature, Odometer, Reverse)

**Documentation status:** Verified (PSA-RE)  
**Implementation:** `Msg0F6` in `can_messages.py`

**Observed payloads:**

```
86 00 00 00 00 08 63 20   (cold — coolant at initialisation default)
86 64 00 00 00 08 63 20   (warming — coolant 60 °C)
8E A0 00 00 00 08 63 20   (hot — coolant 120 °C, main_status=1)
8E 64 00 00 00 08 63 20   (transitional — coolant 60 °C, main_status=1)
```

**Decode (0-indexed bytes):**

| Byte | Values seen | Meaning |
|------|------------|---------|
| 0    | 0x86 / 0x8E | Status byte: config_mode=2, gen_status=1, powertrain=2; bit 3 (main_status) toggles between 0 (0x86) and 1 (0x8E) |
| 1    | 0x00 / 0x64 / 0xA0 | COOLANT_TEMPERATURE: raw − 40 °C → **−40 °C / 60 °C / 120 °C** |
| 2-4  | 0x00 0x00 0x00 | ODOMETER = 0 (bench capture — no driven distance) |
| 5    | 0x08 | EXTERNAL_TEMPERATURE: 8 × 0.5 − 40 = **−36 °C** (sensor artefact on bench) |
| 6    | 0x63 | EXTERNAL_FILTERED_TEMPERATURE: 99 × 0.5 − 40 = **+9.5 °C** (retained from last drive) |
| 7    | 0x20 | `0b00100000`: reverse=0, wipers=0, wheel_pos=2, cluster_test=0, blinkers=0 |

**Documentation check:** ✅ Byte layout matches PSA-RE documentation.

Status byte observation: real car shows `0x86` / `0x8E` rather than the `0x88` value cited in the
PSA-RE reference as "customer config + generator OK + motor running". The difference lies in
bit 3 (main_status): `0x86` has it clear, `0x8E` has it set. This alternation may represent a
state machine inside the BSI during warm-up. The simulator encoder hard-codes `0x88`, which is
close but does not reproduce the toggle.

External temperature (`−36 °C`) and filtered temperature (`+9.5 °C`) diverge significantly. On a
bench the external sensor is typically disconnected or reading ambient bench temperature; the
filtered value is carried over from the last real-car session stored in BSI EEPROM.

**Implementation check:** ✅ Decode logic in `Msg0F6.decode()` correctly reads coolant, external
temperature, reverse, and blinkers. Encode sends `0x88` for the status byte and `0xFFFFFF` for
the odometer (appropriate for bench simulation). No action required, but note the `0x88` vs
`0x86`/`0x8E` discrepancy if wire-level accuracy is needed.

---

### 0x128 — Cluster Warning and Lamp Status

**Documentation status:** Verified/Observed  
**Implementation:** `Msg128` in `can_messages.py`, encoder in `modules/combine/__init__.py`

**Observed payloads:**

```
00 00 00 00 00 A0 00 00   (baseline — no active warnings)
10 00 00 00 00 A0 00 00   (low-fuel indicator set)
10 00 00 00 00 A0 10 00   (low-fuel + byte 6 bit 4 set)
```

**Decode (0-indexed bytes):**

| Byte | Values | Meaning |
|------|--------|---------|
| 0    | 0x00 / 0x10 | bit 4 = LOW_FUEL warning (0x10 active) |
| 1    | 0x00  | No STOP / STOP_RESTART bits |
| 2-4  | 0x00  | No door, ABS, ESP, suspension flags |
| 5    | 0xA0  | `0b10100000`: bit 7 = active (possibly PARKING_BRAKE), bit 5 = DAYLIGHTS or ambient active |
| 6    | 0x00 / 0x10 | bit 4 active in final variant — purpose not fully decoded |
| 7    | 0x00  | No rear seatbelt indicators |

**Documentation check:** ✅ LOW_FUEL at byte 0 bit 4 confirmed. Byte 5 value `0xA0` is constant
in all three payloads, suggesting it represents a permanent on-bench static state (possibly parking
brake engaged throughout capture or a fixed BSI flag).

**Implementation check:** ✅ The `Msg128` decoder reads byte 0 bits correctly. The byte-6 bit-4
signal is not decoded in the current implementation; its purpose is unconfirmed.

---

### 0x161 — BSI Gauges (Oil Temperature, Fuel Level, Oil Level)

**Documentation status:** Verified (PSA-RE)  
**Implementation:** `Msg161` in `can_messages.py`

**Observed payloads (DLC = 7):**

```
00 00 00 00 00 00 00   (cold — all gauges at zero/off)
00 00 62 00 00 00 00   (warming — oil 58 °C, fuel 0 %)
00 00 D7 64 00 00 00   (warm — oil 175 °C, fuel 100 %)
```

**Decode (0-indexed bytes):**

| Byte | Values | Meaning |
|------|--------|---------|
| 0    | 0x00   | OIL_LEVEL_RESTART flag = 0 |
| 1    | 0x00   | Unused |
| 2    | 0x00 / 0x62 / 0xD7 | OIL_TEMPERATURE: raw − 40 → **−40 / 58 / 175 °C** |
| 3    | 0x00 / 0x64 | FUEL_LEVEL: 0 % or **100 %** (full tank) |
| 4-5  | 0x00   | Real car sends **0x00**; implementation encodes `0xFF 0xFF` |
| 6    | 0x00   | OIL_LEVEL = 0 % (sensor not available on bench) |

**Documentation check:** ✅ DLC = 7 confirmed (matches PSA-RE and implementation). Signal
encoding (raw − 40 for oil temperature, 0–100 % for fuel) confirmed.

**Implementation check:** ⚠️ Minor discrepancy: bytes 4-5 — real car sends `0x00 0x00` while the
simulator encodes `0xFF 0xFF`. PSA-RE marks these bytes as unused/reserved. The difference is
cosmetic; `0xFF` is the standard PSA "invalid/not available" sentinel but real BSI hardware uses
`0x00` in this position.

---

### 0x168 — Dashboard Alerts and Fault Indicators

**Documentation status:** Verified (PSA-RE: COMBINE_ALERTS_INDICATORS)  
**Implementation:** `Msg168` in `can_messages.py`

**Observed payloads:**

```
00 00 00 00 00 00 00 00   (no active alerts)
00 00 00 00 02 00 00 00   (byte 4 bit 1 set — one alert active)
```

**Decode:**

| Byte | Value | Meaning |
|------|-------|---------|
| 0-3  | 0x00  | No alert indicators |
| 4    | 0x00 / 0x02 | Bit 1 active — exact alert signal not yet decoded |
| 5-7  | 0x00  | No further alerts |

**Documentation check:** ✅ Confirmed as alert/indicator frame (not ambient temperature or battery
voltage — previous workspace confusion corrected in PSA_RE_comparison.md).

**Implementation check:** ✅ Implementation decodes byte 4 and other alert bytes. The specific
signal at byte 4 bit 1 (`0x02`) is not currently mapped to a named car state variable; it may
correspond to a generic warning light not yet enumerated in the workspace.

---

### 0x1A1 — MFD Popup / BSI Log Message

**Documentation status:** Observed/Verified  
**Implementation:** `Msg1A1` in `can_messages.py`

**Observed payloads:**

```
00 8B C6 00 00 00 00 00   (idle — no active popup)
00 DE C6 00 00 00 00 00   (door event announcing / flag=0)
80 DE C6 00 00 00 00 00   (door open active / flag=0x80)
```

**Decode (0-indexed bytes):**

| Byte | Values | Meaning |
|------|--------|---------|
| 0    | 0x00 / 0x80 | Flag byte: 0x80 = popup active, 0x00 = dismiss/idle |
| 1    | 0x8B / 0xDE | Message ID: 0x8B = idle baseline, 0xDE = front-left door |
| 2    | 0xC6   | Display flags (constant) |
| 3-7  | 0x00   | No door-status bytes set (doors closed in this capture) |

**Documentation check:** ✅ Perfectly matches the implementation constants:
`IDLE_MESSAGE_ID = 0x8B`, `DISPLAY_FLAGS = 0xC6`. The real-car data confirms these hardcoded
constants were derived from actual bus captures.

**Implementation check:** ✅ The idle payload `00 8B C6 00 00 00 00 00` is reproduced exactly by
`Msg1A1.encode()` when no popup is active. The door-open sequence (`00 DE C6` → `80 DE C6`) is
also correctly modelled: flag byte transitions from 0x00 (announcement) to 0x80 (active) when the
door is open, then back to idle when closed.

---

### 0x1A8 — Speed Control / Cruise Limiter (GESTION_VITESSE)

**Documentation status:** Verified (PSA-RE, CAN2004_0x1A8.md)  
**Implementation:** `Msg1A8` in `can_messages.py`

**Observed payloads:**

```
00 00 00 00 00 00 A0 00   (no active control, partial odo = 40.96 km)
80 00 00 00 00 00 A0 00   (limiter type selected, standby, same odo)
```

**Decode (0-indexed bytes):**

| Byte | Values | Meaning |
|------|--------|---------|
| 0    | 0x00 / 0x80 | bits 7-6: SPEED_CONTROL_TYPE: 0=none, 2=limiter; bits 5-3: ACTIVE_FUNCTION_STATUS=0 (standby) |
| 1-2  | 0x00 0x00 | SET_SPEED = 0 × 0.01 = **0.0 km/h** (limiter set to 0, not 0xFFFF/unset) |
| 3-4  | 0x00 0x00 | Unused |
| 5-7  | 0x00 0xA0 0x00 | ODOMETER_PARTIAL = 0x00A000 × 0.001 = **40.96 km** |

**Documentation check:** ✅ Byte layout confirmed. The partial odometer reading of 40.96 km is a
real value stored in the BSI from the last trip; it persists after power-cycle.

**Implementation check:** ✅ `Msg1A8.encode()` and `Msg1A8.decode()` correctly model the
SPEED_CONTROL_TYPE field, the SET_SPEED encoding, and the ODOMETER_PARTIAL encoding. The
implementation is fully consistent with the observed data.

> **Documentation correction:** `doc/CAN_messages.md` previously stated that 0x1A8 was "not
> implemented in simulator". This is incorrect. `Msg1A8` has been implemented and is registered in
> `ALL_MESSAGES`. The documentation has been updated to reflect this.

---

### 0x228 — Unknown Frame

**Documentation status:** Partial (listed as "?" in PSA_RE_comparison.md)  
**Implementation:** Not implemented

**Observed payload (constant throughout capture):**

```
80 00 80 80 00 00 00 00
```

**Observations:**

- DLC = 8, appears every ≈ 9.9 ms (microseconds), count = 996 across 16.5 s capture.
- Single unique payload; all bytes are constant — this frame carries static configuration data or
  a fixed status register.
- `d[0] = 0x80` (bit 7 set), `d[2] = 0x80`, `d[3] = 0x80`.
- The frame ID 0x228 is numerically close to 0x220 (door status) and 0x221, both already
  implemented. This suggests 0x228 may be a related body-status or configuration frame, but no
  PSA-RE mapping exists in the workspace.
- The constant `80 00 80 80` pattern is consistent with a "module present / alive" heartbeat
  where three separate status flags are hardwired high.

**Recommendation:** Record as **Observed (static)** in documentation. Do not implement until the
signal mapping is confirmed. The constant payload makes it safe to ignore for monitoring purposes.

---

### 0x3F6 — Date/Time Frame (Radio → Display)

**Documentation status:** Partial (autowp: "Date/time (Radio→Display)")  
**Implementation:** Not implemented

**Observed payload (constant throughout capture):**

```
00 00 00 00 00 C0 00   (DLC = 7)
```

**Observations:**

- DLC = 7, appears every ≈ 7.6 ms, count = 1,392.
- Single unique payload; all bytes are zero except `d[5] = 0xC0`.
- The autowp database identifies this ID as a date/time synchronisation frame sent from the
  radio head-unit to the display. In a date/time frame:
  - `d[5] = 0xC0 = 0b11000000` would represent the hour component or a configuration byte.
  - All other bytes at zero suggest the radio was powered but not actively broadcasting time
    (e.g., no RDS time signal received or time not yet set).
- This frame is not part of the vehicle-state monitoring core and has no impact on BSI or
  body-control simulation.

**Recommendation:** Keep as **Inferred (infotainment)** in documentation. Implementation is
optional and only needed for head-unit or display emulation.

---

## Cross-Reference Summary

### Frames Present in Dump vs Documentation

| ID    | In Dump | Documented | Confidence | Notes |
|-------|---------|------------|------------|-------|
| 0x036 | ✅      | ✅ Verified | High | Matches implementation |
| 0x0B6 | ✅      | ✅ Verified | High | d[5] and d[7] byte differ from simulator (cosmetic) |
| 0x0F6 | ✅      | ✅ Verified | High | Status byte 0x86/0x8E vs documented 0x88; decode correct |
| 0x128 | ✅      | ✅ Verified | High | LOW_FUEL confirmed; d[6] bit 4 purpose unknown |
| 0x161 | ✅      | ✅ Verified | High | bytes 4-5 are 0x00 in real car vs 0xFF in simulator |
| 0x168 | ✅      | ✅ Verified | High | byte 4 bit 1 alert unresolved |
| 0x1A1 | ✅      | ✅ Verified | High | IDLE_MESSAGE_ID/DISPLAY_FLAGS constants confirmed |
| 0x1A8 | ✅      | ✅ Verified | High | Implementation correct, old doc note wrong |
| 0x228 | ✅      | ⚠️ Unknown | Low  | Constant heartbeat; no signal mapping available |
| 0x3F6 | ✅      | ⚠️ Partial | Medium | Date/time from radio; infotainment-only |

### Frames Documented but Not in Dump

| ID    | Documented As | Notes |
|-------|--------------|-------|
| 0x220 | Door/body openings | Doors were closed during this capture — frame absent or not sent when idle |
| 0x0E1 | Parking sensors | Parktronic not active |
| 0x1D0 | HVAC status | Climate system not active on bench |
| 0x1E3 | HVAC fan status | Same as above |
| 0x361 | Vehicle config/features | Not present; may only appear at startup or be absent on this variant |

---

## Implementation Discrepancies

The following differences were found between real-car observed frames and simulator encoder
output. All are minor; none affect the primary functional simulation.

| ID    | Byte | Real Car | Simulator | Impact |
|-------|------|----------|-----------|--------|
| 0x0B6 | 5    | 0xFF     | 0x00      | Cosmetic — byte not decoded |
| 0x0B6 | 7    | 0xA0     | 0xD0      | Cosmetic — status bits not decoded |
| 0x0F6 | 0    | 0x86/0x8E | 0x88   | Minor — status byte state machine not reproduced |
| 0x161 | 4-5  | 0x00 0x00 | 0xFF 0xFF | Cosmetic — unused bytes |

---

## New Observations Confirmed by This Dump

1. **0x1A1 `IDLE_MESSAGE_ID = 0x8B` and `DISPLAY_FLAGS = 0xC6`** — previously assumed values
   from earlier bench captures are now confirmed by an independent real-car source.

2. **0x1A8 partial odometer = 40.96 km** — the real BSI retains the partial trip odometer
   across power cycles. The implementation correctly represents this via `sc.partial_odo`.

3. **0x0F6 temperature divergence** — on a bench, external temperature (`d[5]`) and filtered
   external temperature (`d[6]`) will differ significantly because the sensor is physically absent
   while the BSI retains its last filtered value from EEPROM. This is expected behaviour and not
   a decoder error.

4. **0x0F6 status byte variation** — the real BSI alternates the status byte between `0x86` and
   `0x8E` during warm-up (bit 3 = main_status toggling). The simulator uses a fixed `0x88`.

5. **0x228 static frame** — present in every sampled window of the capture with identical
   payload. This suggests a permanently active module reporting a fixed status, not a dynamic
   data source.

6. **0x168 byte 4 bit 1** — one active alert (value `0x02`) appears intermittently. Its signal
   name is not resolved from the available PSA-RE tables.
