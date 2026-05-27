# CAN Messages Reference — PSA CAN2004 ↔ CAN2010 Adapter

This document describes all CAN frames handled by the adapter firmware. The adapter bridges two separate networks:

- **CAN0** — the original vehicle CAN-BUS (CAN2004 / "old BSI" side), running at 125 kbps.
- **CAN1** — the modern telematic/comfort device bus (CAN2010 side, e.g. NAC, SMEG), also at 125 kbps.

All IDs are 11-bit standard CAN. Byte indices start at 0 (data[0] is the first byte).

---

## Table of Contents

1. [CAN0 → Adapter (frames received from the car)](#can0--adapter-frames-received-from-the-car)
2. [Adapter → CAN1 (frames sent to the CAN2010 device)](#adapter--can1-frames-sent-to-the-can2010-device)
3. [CAN1 → Adapter (frames received from the CAN2010 device)](#can1--adapter-frames-received-from-the-can2010-device)
4. [Adapter → CAN0 (frames sent back to the car)](#adapter--can0-frames-sent-back-to-the-car)
5. [Startup / Init frames](#startup--init-frames)
6. [Bit-field notation](#bit-field-notation)

---

## CAN0 → Adapter (frames received from the car)

### 0x036 — BSI / Economy mode & brightness (len = 8)

| Byte | Bit | Description |
|------|-----|-------------|
| 2 | 7 | Economy mode active (1 = ON) |
| 3 | 7:0 | Brightness level (0x00–0xFF). With `fixedBrightness`, values ≥ 0x20 are forced to 0x28. |

After optional brightness adjustment the frame is forwarded to CAN1 unchanged.

---

### 0x0B6 — Engine / Speed (len = 8)

| Bytes | Description |
|-------|-------------|
| 0–1 | Engine RPM = value × 0.125 |
| 2–3 | Vehicle speed = value × 0.01 km/h |

The frame is forwarded to CAN1 unchanged. The adapter tracks `EngineRunning` (RPM > 0) and `vehicleSpeed` internally.

---

### 0x0E6 — ABS status (len < 8 on CAN2004)

CAN2004 only sends 7 bytes; CAN2010 devices expect 8. The adapter extends the frame:

| Byte | Description |
|------|-------------|
| 0 | Status lights / Alerts |
| 1–2 | Rear-left wheel rotations |
| 3–4 | Rear-right wheel rotations |
| 5 | Battery voltage measured by ABS |
| 6 | STT / Slope / Emergency braking flags |
| 7 | **Calculated checksum/counter** (see `checksumm_0E6()`) |

The reconstructed 8-byte frame is sent to CAN1 with the same ID `0x0E6`.

> **Checksum algorithm** (`checksumm_0E6`): Sum the nibbles of bytes 0–6, add a 4-bit rolling counter (0–15), XOR with 0xFF, subtract 3, mask to the lower nibble, then XOR with the counter shifted left 4.

---

### 0x0F6 — BSI status / Ignition & external temperature (len = 8)

| Byte | Bit / Range | Description |
|------|-------------|-------------|
| 0 | > 0x80 | Ignition ON |
| 0 | ≤ 0x80 | Ignition OFF |
| 5 | 7:1 | External temperature raw value. Actual °C = (raw >> 1) − 40 (range −40 °C … +87.5 °C) |

The frame is forwarded to CAN1 unchanged.

---

### 0x120 — Alerts journal / Diagnostics (len = 8, `generatePOPups` must be true)

A multi-block frame sent by the cluster. The adapter decodes individual fault bits and generates CAN2010 popup notifications (ID `0x1A1`). The block in use is identified by data[0]:

| data[0] bits [7:6] | Block |
|--------------------|-------|
| `00` or `01` | Block 1 — critical faults |
| `10` | Block 2 — lamps, tyres, sensors |
| `11` | Block 3 — openings, secondary faults |

Selected fault bits and their popup mapping (Block 1):

| Byte.Bit | Popup ID | Description |
|----------|----------|-------------|
| 1.7 | 5 | Engine oil pressure fault — stop the vehicle |
| 1.6 | 1 | Engine temperature fault — stop the vehicle |
| 1.5 | 138 | Charging system fault |
| 1.4 | 106 | Braking system fault — stop the vehicle |
| 1.2 | 109 | Power steering fault — stop the vehicle |
| 1.1 | 3 | Top up coolant level |
| 2.7 | 4 | Top up engine oil level |
| 2.5–2.0 | 8 | Door(s) / boot open |
| 3.6 | 107 | ESP/ASR fault |
| 3.3 | 125 | Water in diesel fuel filter |
| 3.2 | 103 | Brake pad replacement needed |
| 3.1 | 224 | Fuel level low |
| 3.0 | 120 | Airbag / seatbelt pre-tensioner fault |
| 4.5 | 106 | ABS fault |
| 4.4 | 15 | Particle filter full |
| 4.2 | 129 | Particle filter additive low |
| 4.0 | 17 | Suspension fault |
| 5.2 | 131 | Electronic immobiliser fault |
| 6.1 | 223 | Top up screenwash |
| 6.0 | 227 | Replace remote control battery |

The original frame is also forwarded to CAN1.

---

### 0x128 — Instrument panel (cluster indicators) (len = 8)

Contains gearbox position, indicator lamps, seatbelts, and parking/braking status. The adapter remaps all bits into a CAN2010-compatible layout and sends a new `0x128` frame to CAN1 (see [Adapter → CAN1 0x128](#0x128--instrument-panel-indicators-converted-len--8)).

---

### 0x15B — Personalization status (len = 8, direction: CAN0 → Adapter only)

Sent by the BSI to reflect current user profile settings. The adapter does **not** forward this frame to CAN1 (it is suppressed to prevent loops).

---

### 0x168 — Instrument panel (WIP) (len = 8)

The adapter rewrites byte 6 to add CAN2010-specific flags (ambiance, EMF availability, gearbox report bits) and sends the modified frame to CAN1 under the same ID.

| data[6] bit | Description |
|-------------|-------------|
| 7 | Reserved (0) |
| 6 | Ambiance available |
| 5 | EMF availability |
| 4 | Gearbox report (from data[5].0) |
| 3–1 | Gearbox report (from data[6].7–5) |
| 0 | Reserved (0) |

---

### 0x1A8 — Cruise control (len = 8)

CAN2004 cruise control frame. The adapter forwards it to CAN1 as-is and also creates a translated CAN2010 cruise control frame `0x228` (8 bytes).

---

### 0x1D0 — Air conditioning / Climate control (len = 7)

Decoded and converted into the CAN2010 A/C frame `0x350`. Key mappings:

| CAN2004 byte | Content |
|--------------|---------|
| 0 | A/C mode flags (see table below) |
| 2 | Fan speed raw (15 = OFF; otherwise +66 → range 0x42–0x49) |
| 3 | Fan direction (0x10–0x80 codes, see table below) |
| 4 | Air recirculation / demist mode |
| 5 | Left temperature setpoint |
| 6 | Right temperature setpoint (equals left → MONO mode) |

**A/C mode byte (data[0]) values:**

| Value | A/C | DeMist | FanOff |
|-------|-----|--------|--------|
| 0x11 | ON | YES | NO |
| 0x12 | OFF | YES | NO |
| 0x21 | ON | YES | NO |
| 0xA2 | OFF | — | YES |
| 0x22 | OFF | NO | NO |
| 0x20 | ON | NO | NO |
| 0x02 | OFF | NO | NO |
| 0x00 | ON (Auto) | NO | NO |

**Fan direction byte (data[3]) values:**

| Value | Foot | Windshield | Central |
|-------|------|-----------|---------|
| 0x10 | NO | NO | NO |
| 0x20 | YES | NO | NO |
| 0x30 | NO | NO | YES |
| 0x40 | NO | YES | NO |
| 0x50 | YES | NO | YES |
| 0x60 | YES | YES | NO |
| 0x70 | NO | YES | YES |
| 0x80 | YES | YES | YES |

> **Note**: Only processed when `EngineRunning` is true.

---

### 0x21F — Steering wheel commands, Generic (len = 3)

| Byte | Bit | Button / action |
|------|-----|-----------------|
| 0 | 1 | MODE / SRC |
| 1 | 7:0 | Scroll wheel delta |
| 2 | 7:0 | Reserved |

When `noFMUX` is enabled and `steeringWheelCommands_Type == 0`, a MODE/SRC press is remapped to the CAN2010 MENU command (`0x122`, data[0] = 0x80).

Otherwise the frame is forwarded to CAN1 unchanged, and if `noFMUX` is set a blank FMUX frame `0x122` is also sent.

---

### 0x221 — Trip info (variable length)

The full frame is cached in `statusTRIP[]` and forwarded to CAN1. Additionally a CAN2010 time-stamp frame `0x3F6` is generated and sent to CAN0.

---

### 0x260 — Personalization settings status (len = 8)

Sent periodically by the BSI with the current user-profile settings. The adapter remaps all fields to the CAN2010 format and sends:
- `0x260` (7 bytes) to CAN1 with remapped fields
- `0x15B` (8 bytes) to CAN0 with personalization status
- `0x236` (8 bytes) to CAN1 (economy mode simulation)
- `0x276` (7 bytes) to CAN1 (current date/time)
- `0x350` (8 bytes) to CAN1 (A/C status reset if engine not running)

---

### 0x2B6 — VIN digits 10–17 (len = 8, ASCII, `emulateVIN` must be true)

The last 8 characters of the VIN are replaced with the configured `vinNumber[9..16]` and forwarded to CAN1.

---

### 0x2D7 — CAN2004 Matrix language / units (len = 5, `listenCAN2004Language` must be true)

| data[0] | Description |
|---------|-------------|
| bits 5:0 | Language ID (0–32) |
| bit 5 | If set: km/L mode enabled |

The language ID is stored in EEPROM and used to set `languageAndUnitNum` for the CAN2010 side.

---

### 0x321 — Unknown (len < 5)

The adapter intercepts this frame, pads it to 5 bytes (appending 0x00), and sends the result to CAN1 under the same ID.

---

### 0x336 — VIN digits 1–3 (len = 3, ASCII, `emulateVIN` must be true)

Replaced with `vinNumber[0..2]` and forwarded to CAN1.

---

### 0x361 — Personalization menus availability (variable length)

Received from BSI. The adapter converts the bit-fields to the CAN2010 layout and sends back a new `0x361` (8 bytes) to CAN1.

Key mappings (CAN2004 source → CAN2010 output):

| CAN2010 output byte.bit | CAN2004 source | Feature |
|-------------------------|---------------|---------|
| 0.7 | hardcoded 1 | Parameters availability |
| 0.6 | src[2].3 | High-beam |
| 0.4 | src[3].7 | Adaptive lighting |
| 0.3 | src[4].1 | SAM |
| 0.2 | src[4].2 | Ambiance lighting |
| 0.1 | src[2].0 | Automatic headlights |
| 0.0 | src[3].6 | Daytime running lights |
| 1.7 | src[5].5 | AAS |
| 1.6 | src[3].5 | Wiper in reverse |
| 1.5 | src[2].4 | Guide-me home lighting |
| 1.4 | src[1].2 | Driver welcome |
| 1.3 | src[2].6 | Motorized tailgate |
| 1.2 | src[2].0 | Selective openings — Rear |
| 1.1 | src[2].7 | Selective openings — Key |
| 2.7 | hardcoded 1 | TNB — Seatbelt indicator |
| 2.6 | hardcoded 1 | XVV — Custom cruise limits |
| 2.5 | src[1].4 | Configurable button |
| 2.4 | src[2].2 | Automatic parking brake |
| 3.7 | hardcoded 1 | DSG Reset |
| 3.4 | hardcoded 1 | XVV Menu |
| 3.3 | hardcoded 1 | Recommended speed indicator |
| 3.2–3.0 | src[5].6–4 | DSG underinflation (3 bits) |
| 6.5 | hardcoded 1 | Privacy mode |

---

### 0x3A7 — Maintenance (len = 8)

| CAN2004 bytes | Content |
|---------------|---------|
| 3–4 | km remaining ÷ 20 (WORD, big-endian) |
| 5–6 | Days remaining (WORD, big-endian; 0xFFFF = disabled) |

Converted to CAN2010 format `0x3E7` (5 bytes):

| CAN2010 byte | Content |
|-------------|---------|
| 0 | 0x40 (fixed) |
| 1–2 | Days remaining (WORD, big-endian) |
| 3–4 | km remaining ÷ 20 (WORD, big-endian) |

---

### 0x3B6 — VIN digits 4–9 (len = 6, ASCII, `emulateVIN` must be true)

Replaced with `vinNumber[3..8]` and forwarded to CAN1.

---

## Adapter → CAN1 (frames sent to the CAN2010 device)

### 0x122 — FMUX button commands (len = 8)

Sent when analogue/FMUX buttons are pressed or remapped from steering wheel commands.

| data[0] bit | Button |
|-------------|--------|
| 7 | MENU |
| 6 | SRC / SOURCE |
| 5 | (not used) |
| 4 | (not used) |

| data[1] bit | Button (C4 I / C5 X7 mapping) |
|-------------|-------------------------------|
| 5 | MUSIC |
| 3 | NAV |
| 2 | PHONE (partial) |
| 1 | APPS (partial) |

| data[2] bit | Button |
|-------------|--------|
| 3 | PHONE trigger |

| data[5] | Fixed 0x02 (button validity flag) |
|---------|-----------------------------------|

| data[6] | Volume potentiometer button |
|---------|----------------------------|

---

### 0x128 — Instrument panel indicators (converted, len = 8)

Remapped from CAN2004 `0x128` into the CAN2010 layout:

| CAN2010 byte.bit | Description |
|-----------------|-------------|
| 0 | Main driving lights (from src[4]) |
| 1.7–0 | Gearbox report (from src[6].7–0) |
| 2.7 | Arrow blinking (from src[7].7) |
| 2.6–4 | BVA mode (from src[7].6–4) |
| 2.3–2 | Arrow type (from src[7].3–2) |
| 2.1–0 | Gearbox type (from src[7].1–0; BVMP forced to 00) |
| 3.7 | Service (from src[1].7) |
| 3.6 | STOP (from src[1].6) |
| 3.5 | Child security (from src[2].5) |
| 3.4 | Passenger airbag (from src[0].7) |
| 3.3–2 | Foot on brake (from src[3].2–1) |
| 3.1 | Parking brake (from src[0].5) |
| 3.0 | Electric parking brake (hardcoded 0) |
| 4.7 | Diesel pre-heating (from src[0].2) |
| 4.6 | Opening open (from src[1].4) |
| 4.5–4 | Automatic parking (from src[3].4–3) |
| 4.3 | Automatic high beam (hardcoded 0) |
| 4.2 | ESP disabled (from src[2].4) |
| 4.1 | ESP active (from src[2].3) |
| 4.0 | Active suspension (from src[2].2) |
| 5.7 | Low fuel (from src[0].4) |
| 5.6 | Driver seatbelt (from src[0].6) |
| 5.5 | Driver seatbelt blinking (from src[3].7) |
| 5.4 | Passenger seatbelt (from src[0].1) |
| 5.3 | Passenger seatbelt blinking (from src[3].6) |
| 5.0 | Rear-left seatbelt (from src[5].6) |
| 6.7 | Rear seatbelt left blinking (from src[5].5) |
| 6.6 | Rear-right seatbelt (from src[5].2) |
| 6.5 | Rear-right seatbelt blinking (from src[5].1) |
| 6.4 | Rear-middle seatbelt (from src[5].4) |
| 6.3 | Rear-middle seatbelt blinking (from src[5].3) |
| 6.2 | Instrument panel ON (from src[5].7) |
| 6.1 | Warnings (from src[2].1) |
| 7 | Reserved (0x00) |

---

### 0x1A1 — Popup / notification (len = 8)

Generated by the adapter from the alerts journal (`0x120`) when `generatePOPups` is true.

| Byte | Description |
|------|-------------|
| 0 | High byte of notification ID (bit 7 = 1 for new message) |
| 1 | Low byte of notification ID |
| 2 | Priority (0–14); bit 7 = destination NAC/EMF/MATT; bit 6 = destination CMB |
| 3–7 | Optional parameters (door/tyre position masks, etc.) |

To close a popup: data[0] = 0x7F, data[1] = 0xFF.

---

### 0x21F — Volume commands (len = 3, analogue buttons only)

| data[0] | Action |
|---------|--------|
| 0x04 | Volume down |
| 0x08 | Volume up |
| 0x0C | Mute |

data[1] = scroll-wheel delta value.

---

### 0x228 — Clock / Cruise control (CAN2010 format)

**Clock mode** (len = 2, sent at startup and on time change):

| Byte | Content |
|------|---------|
| 0 | Hour (0–23) |
| 1 | Minute (0–59) |

**Cruise control mode** (len = 8, converted from CAN2004 `0x1A8`):

| CAN2010 byte | Source |
|-------------|--------|
| 0 | CAN2004 src[1] |
| 1 | CAN2004 src[2] |
| 2 | CAN2004 src[0] |
| 3 | 0x80 (fixed) |
| 4 | 0x14 (fixed) |
| 5 | 0x7F (fixed) |
| 6 | 0xFF (fixed) |
| 7 | 0x98 (fixed) |

---

### 0x236 — Economy mode simulation (len = 8)

Sent after receiving `0x260` from the car. Signals the CAN2010 device about ECO state and engine status.

| Byte | ECO + Engine OFF | ECO + Engine ON | Normal Engine ON | Normal Engine OFF |
|------|-----------------|-----------------|-----------------|-------------------|
| 0 | 0x14 | 0x14 | 0x54 | 0x04 |
| 1 | 0x03 | 0x03 | 0x03 | 0x03 |
| 2 | 0xDE | 0xDE | 0xDE | 0xDE |
| 3–4 | Counter (0x00/0x00) | Counter (0x00/0x00) | Counter | Counter |
| 5 | 0x0C | 0x0E | 0x0F | 0x0F |
| 6 | 0xFE | 0xFE | 0xFE | 0xFE |
| 7 | 0x00 | 0x00 | 0x00 | 0x00 |

---

### 0x260 — Personalization settings (CAN2010 format, len = 7)

Sent to the CAN2010 device after converting the CAN2004 `0x260` frame. Contains language, units, lighting, and comfort options in CAN2010 bit layout.

| Byte | Content |
|------|---------|
| 0 | Language and unit number (`languageAndUnitNum` = languageID × 4 + 128) |
| 1 | Units, ambiance level, parameters availability, sound harmony |
| 2 | Selective openings, driver welcome, adaptive lighting, DRL, ambiance |
| 3 | Guide-me home, beam, lighting, automatic headlights |
| 4 | AAS, SAM, wiper in reverse, motorized tailgate, configurable button |
| 5–6 | Reserved (0x00) |

---

### 0x268 — Fake CVM speed limit frame (len = 8, `CVM_Emul` must be true)

Generated from the telematic's suggested speed (`0x1E9`).

| Byte | Content |
|------|---------|
| 0 | Speed limit value (from CAN2010 src[1]) |
| 1 | 0x30 if over-speed, else 0x10 |
| 2–3 | 0x00 |
| 4 | 0x7C |
| 5 | 0xF8 |
| 6–7 | 0x00 |

---

### 0x276 — Current date/time (len = 7)

Sent after receiving `0x260` from the car.

| Byte | Content |
|------|---------|
| 0 | Year − 1872 (range for years 1872–2127) |
| 1 | Month (1–12) |
| 2 | Day (1–31) |
| 3 | Hour (0–23) |
| 4 | Minute (0–59) |
| 5 | 0x3F |
| 6 | 0xFE |

---

### 0x321 — Reconstructed frame (len = 5)

Original CAN2004 `0x321` frames shorter than 5 bytes are padded with a trailing 0x00 byte.

---

### 0x350 — Air conditioning status (CAN2010 format, len = 8)

Converted from CAN2004 `0x1D0`.

| Byte | Content |
|------|---------|
| 0 | 0x01 (A/C ON) or 0x09 (A/C OFF) |
| 1–2 | Reserved (0x00) |
| 3 | Left temperature setpoint (or 0x00 when fan off) |
| 4 | Right temperature setpoint (or 0x00 when fan off) |
| 5 | Fan speed (0x41 = off; 0x42–0x49 = speed 1–8; 0x10 = auto/demist) |
| 6 | Fan position (see table below) |
| 7 | Reserved (0x00) |

**Fan position encoding (byte 6):**

| Value | Foot | Windshield | Central | DeMist +16 |
|-------|------|-----------|---------|------------|
| 0x04 | NO | NO | NO | — |
| 0x24 | YES | NO | NO | — |
| 0x34 | NO | NO | YES | — |
| 0x44 | NO | YES | NO | — |
| 0x54 | YES | NO | YES | — |
| 0x64 | YES | YES | NO | — |
| 0x74 | NO | YES | YES | — |
| 0x84 | YES | YES | YES | — |

When DeMist is active, 0x10 is added to the fan position value.

---

### 0x361 — Personalization menus availability (CAN2010 format, len = 8)

Sent to CAN1 after converting CAN2004 `0x361`. See [0x361 received from CAN0](#0x361--personalization-menus-availability-variable-length) for the field mapping table.

---

### 0x3E7 — Maintenance (CAN2010 format, len = 5)

Converted from CAN2004 `0x3A7`.

| Byte | Content |
|------|---------|
| 0 | 0x40 (fixed) |
| 1–2 | Days remaining (WORD, big-endian; 0xFFFF = disabled) |
| 3–4 | km remaining ÷ 20 (WORD, big-endian) |

---

### 0x3F6 — Fake EMF time frame (len = 7)

Sent to CAN0 (car side) whenever a `0x221` trip frame is received. Encodes the current RTC time and day-of-year.

| Byte | Content |
|------|---------|
| 0 | Seconds-since-midnight bits [19:12] |
| 1 | Seconds-since-midnight bits [11:4] |
| 2 | Seconds-since-midnight bits [3:0] \| day-of-year bits [11:8] |
| 3 | Day-of-year bits [7:0] |
| 4 | 0x00 |
| 5 | 0xC0 |
| 6 | Language ID |

---

## CAN1 → Adapter (frames received from the CAN2010 device)

### 0x15B — Personalization settings from telematic (len = 8)

Sent by the NAC/SMEG when the user modifies a comfort/vehicle setting.

| Byte | Bit | Description |
|------|-----|-------------|
| 0 | 7:2 | Language+unit number (if ≥ 128) or language ID (< 128) |
| 1 | 7 | Imperial fuel consumption (mpgMi) |
| 1 | 6 | Temperature in Fahrenheit |
| 1 | 2 | **Parameters validity flag** (must be 1 to process the frame) |
| 2 | 7:0 | Vehicle comfort settings (selective openings, driver welcome, etc.) |
| 3 | 7:0 | Lighting settings (guide-me home, beam, daytime running lights, etc.) |
| 4 | 7:0 | AAS, SAM, wiper in reverse, configurable button |

When the validity flag is set, the adapter re-translates all fields into the CAN2004 format and sends a new `0x15B` to CAN0.

---

### 0x1A9 — Telematic commands (len = 8)

Sent periodically by the NAC/SMEG. Marks `TelematicPresent = true`.

| Byte | Bit | Description |
|------|-----|-------------|
| 0 | 7 | Dark mode (black panel) |
| 0 | 1 | Reset Trip 1 |
| 0 | 0 | Reset Trip 2 |
| 1 | 7 | Stop CHECK |
| 3 | 2 | AAS push |
| 5 | 0 | DSG indirect reset / Black panel |
| 6 | 7 | Start&Stop push |
| 6 | 0 | CHECK push |

The adapter generates a fake EMF status frame `0x167` on CAN0 and, if no physical cluster is present, injects the button presses into a `0x217` cluster frame.

---

### 0x1E5 — Audio settings (len = 7)

Sent by the NAC/SMEG to set audio parameters. The adapter converts CAN2010 ranges to CAN2004 ranges and forwards to CAN0.

| Byte | CAN2010 | CAN2004 formula | Description |
|------|---------|-----------------|-------------|
| 0 | 0x20–0x58 | ((val−32)>>2)+57 | Front/Back balance |
| 1 | 0x20–0x58 | ((val−32)>>2)+57 | Left/Right balance |
| 2 | 0x20–0x58 | ((val−32)>>2)+57 | Bass |
| 3 | 0x20–0x58 | ((val−32)>>2)+57 → pos 4 | Treble |
| 4 | loudness+speed flags | see table | Loudness / speed link |
| 5 | ambience code | see table | Sound ambience |
| 6 | 0x40–0x54 (calculated) | set from ambience | Ambience CAN2004 code |

**Loudness / speed (data[4]) mapping:**

| CAN2010 | CAN2004 | Description |
|---------|---------|-------------|
| 0x10 | 0x40 | Loudness ON / not linked to speed |
| 0x14 | 0x47 | Loudness ON / linked to speed |
| 0x04 | 0x07 | No loudness / linked to speed |
| 0x00 | 0x00 | No loudness / not linked to speed |

**Ambience (data[5]) mapping:**

| CAN2010 | CAN2004 | Description |
|---------|---------|-------------|
| 0x00 | 0x40 | User |
| 0x08 | 0x44 | Classical |
| 0x10 | 0x48 | Jazz |
| 0x18 | 0x4C | Pop-Rock |
| 0x20 | 0x50 | Vocal |
| 0x28 | 0x54 | Techno |

---

### 0x1E9 — Telematic suggested speed (len ≥ 2, `CVM_Emul` must be true)

| Byte | Content |
|------|---------|
| 0 | Speed limit value (km/h) |
| 1 | Speed limit display value |
| 3 | bits [7:2] = POI type (6 bits) |

Forwarded to CAN0 unchanged; also used to generate a fake CVM frame `0x268` on CAN1.

---

### 0x217 — Cluster status from CAN2010 (len = 8)

When a CAN2010 cluster is present (`ClusterPresent = true`), the adapter intercepts this frame, injects telematic button states (trip reset, CHECK, AAS, ASR, SAM, DSG, STT) and forwards the result to CAN0.

---

### 0x260, 0x361 — Suppressed (direction: CAN1 → Adapter)

Frames with these IDs coming from the CAN2010 side are **not** forwarded to CAN0 to prevent loops (the adapter itself generates these frames).

---

### 0x31C — MATT status (len = 5)

Forwarded to CAN0. If `resetTrip1` or `resetTrip2` flags are active, bits 3 and 2 of data[0] are set respectively before forwarding.

---

### 0x329 — ASR/ESP (len = 8)

| Byte | Bit | Description |
|------|-----|-------------|
| 3 | 0 | ESP/ASR push |

Used internally; not forwarded.

---

### 0x39B — Time set from telematic (len = 5)

| Byte | Content |
|------|---------|
| 0 | Year − 1872 |
| 1 | Month (1–12) |
| 2 | Day (1–31) |
| 3 | Hour (0–23) |
| 4 | Minute (0–59) |

The adapter updates the RTC module, the internal time, EEPROM, and sends a clock frame `0x228` to CAN0.

---

## Adapter → CAN0 (frames sent back to the car)

### 0x15B — Personalization frame status (len = 8)

Sent to the BSI when the adapter initializes or when personalization settings change (from `0x260` or `0x15B` telematic).

| Byte | Bit | Description |
|------|-----|-------------|
| 0 | 2 | Parameters validity (1 = valid / 0 = changed) |
| 0 | 1–0 | User profile (01 = profile 1) |
| 1–7 | 7:0 | Personalization settings bytes |

---

### 0x167 — Fake EMF status frame (len = 8)

Sent when the telematic sends commands (`0x1A9`) or when no telematic is present but ignition is on.

| Byte | Content |
|------|---------|
| 0 | 0x00, with bit 7 = Trip1 reset, bit 6 = Trip2 reset, bit 5 = dark mode |
| 1 | 0x10 |
| 2–3 | 0xFF |
| 4 | 0x7F |
| 5 | 0xFF |
| 6–7 | 0x00 |

---

### 0x217 — Cluster commands (len = 8)

Sent to the BSI to relay telematic button presses when no physical CAN2010 cluster is present.

| Byte | Bit | Description |
|------|-----|-------------|
| 1 | 4 | CHECK pushed |
| 1 | 2 | Reset Trip 1 |
| 2 | 7 | AAS pushed |
| 2 | 6 | ASR/ESP pushed |
| 3 | 3 | SAM pushed |
| 3 | 0 | Reset Trip 2 |
| 4 | 7 | DSG reset pushed |
| 6 | 7 | Start&Stop pushed |

---

### 0x228 — Clock frame (len = 2)

Sent at startup and whenever the telematic updates the time (`0x39B`).

| Byte | Content |
|------|---------|
| 0 | Hour (0–23) |
| 1 | Minute (0–59) |

---

### 0x3F6 — Fake EMF time frame (len = 7)

See [Adapter → CAN1: 0x3F6](#0x3f6--fake-emf-time-frame-len--7). Note: this frame is sent to **CAN0** (car side), not CAN1.

---

## Startup / Init frames

The following frames are sent **once** at startup to CAN0 (car side):

| ID | Len | Content |
|----|-----|---------|
| 0x228 | 2 | Current hour + minute (clock sync) |
| 0x5E5 | 8 | Fake EMF software version: `25 0A 0B 04 0C 01 20 11` |

---

## Bit-field notation

Throughout this document bits are described as `byte.bit` where `bit 7` is the most-significant bit and `bit 0` is the least-significant bit of that byte.

Values are hexadecimal unless stated otherwise (e.g. `0x0F`, `15`, `0b00110011`).

---

*This document was generated from the firmware source `arduino-psa-comfort-can-adapter.ino`. Cross-reference with the source code for the most up-to-date details.*
