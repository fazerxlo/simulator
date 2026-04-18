# PSA CAN 2004 Comfort CAN Messages

This document is derived from the current workspace, not from a single external source. It is intended as a practical reference for building an application that monitors Peugeot/Citroen PSA CAN 2004 comfort-bus traffic through a CAN interface.

Primary sources used:

- simulator implementation in [modules/bsi-base](../modules/bsi-base), [modules/bsi-trip](../modules/bsi-trip), [modules/combine](../modules/combine), [modules/clim](../modules/clim), and [modules/bsi-log](../modules/bsi-log)
- workspace notes in [doc/peugeot407can.yaml](peugeot407can.yaml), [doc/psa_pf2.md](psa_pf2.md), and [doc/psa_pf2_comfort.md](psa_pf2_comfort.md)
- cross-project notes in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)
- observed traffic in [dump.csv](../dump.csv)
- community data from [autowp/autowp.github.io](https://github.com/autowp/autowp.github.io) (see [CAN2004_autowp_comparison.md](CAN2004_autowp_comparison.md))

This is a monitoring-oriented reference. Where sources disagree, the document marks the confidence level and describes the conflict instead of pretending the signal is fully confirmed.

## Scope

- Bus type: PSA comfort / infotainment CAN
- Nominal speed: 125 kbps
- Frame format: standard 11-bit CAN IDs
- Target use: passive monitoring and parameter extraction

## Confidence Levels

- Verified: implemented in workspace code and supported by observed dump data
- Observed: present in dump data, but not fully decoded in workspace code
- Inferred: described in workspace notes, but not fully verified from code or dump
- Conflict: multiple workspace sources disagree about bit or byte meaning

## Vehicle Monitoring Core

These frames are the primary set for a car-parameter monitor.

| CAN ID | Purpose | Confidence | Notes |
|--------|---------|------------|-------|
| 0x036 | ignition state, dashboard illumination | Verified | best source for ACC/IGN and dimming |
| 0x0F6 | reverse, coolant/external temperature, odometer, blinkers | Verified (PSA-RE) | bytes 2-4 = 24-bit odometer; byte 5-6 = temperature × 0.5 − 40 |
| 0x128 | cluster warning and lamp state | Verified (PSA-RE) | full 8-byte signal map confirmed; rich signal set |
| 0x161 | oil temperature, fuel level, oil level | Verified (PSA-RE) | byte 6 = oil level 0-100 % |
| 0x168 | dashboard alert/fault indicators | Verified (PSA-RE) | **NOT ambient temperature** — see correction below |
| 0x220 | door and body openings | Observed | present in dump, not implemented in simulator |
| 0x1A8 | cruise/speed-limiter state | Observed | present in dump, not implemented in simulator |
| 0x361 | vehicle configuration/features | Observed | present in dump, not implemented in simulator |
| 0x0E1 | parking sensors | Inferred | decode available in workspace notes |
| 0x14C / 0x28C | vehicle speed and odometer | Inferred | important for monitoring, not comfort-only |
| 0x1D0 / 0x1E3 | HVAC status | Verified | useful if climate monitoring is needed |

## Infotainment And Display Frames

These frames are useful if the application also needs head-unit, display, or audio integration, but they should not be treated as part of the default vehicle-state core.

| CAN ID | Purpose | Confidence | Notes |
|--------|---------|------------|-------|
| 0x131 | CD-changer command or mixed auxiliary traffic | Inferred/Observed | not a reliable universal door-state source |
| 0x0A4 / 0x125 | radio text and track/list transport | Inferred | ISO-TP style display payloads |
| 0x0DF / 0x167 / 0x3E5 / 0x3F6 | display/menu/button state | Inferred | UI-oriented, not vehicle-state core |
| 0x122 / 0x21F | multimedia and steering-wheel controls | Inferred | input/control frames |
| 0x162 / 0x165 / 0x1A0 / 0x1A2 / 0x1A5 / 0x1E0 / 0x1E2 / 0x1E5 | radio or changer status | Inferred | audio-source integration only |
| 0x1A1 | BSI informational display message | Observed | useful for text warnings, not raw vehicle-state decoding |
| 0x225 / 0x265 / 0x325 / 0x365 / 0x3A5 / 0x5E0 / 0x5E5 | tuner, disk, RDS, and device metadata | Inferred | infotainment-specific |

## Important Workspace Finding

The workspace contains two documentation tracks:

- an older PF2-oriented set centered on `0x036`, `0x0F6`, `0x128`, `0x131`, `0x161`, and `0x168`
- a newer comfort-oriented set centered on `0x128`, `0x220`, `0x1A8`, and `0x361`

The canbox source document adds a useful third track: Peugeot 407 and Citroen infotainment-oriented notes that strongly support `0x036`, `0x0F6`, `0x0E1`, `0x1D0`, and the radio/display IDs, while also treating `0x131` as CD-changer command traffic and `0x220` as a compact door-status frame.

The observed dump confirms that `0x220`, `0x1A8`, and `0x361` are real on the bus, even though the current simulator does not implement them.

## Message Details

### Vehicle Monitoring Frames

### 0x036 - Ignition and Dashboard Illumination

Status: Verified

Source evidence:

- implemented in [modules/bsi-base/__init__.py](../modules/bsi-base/__init__.py)
- documented in [psa_pf2_comfort.md](psa_pf2_comfort.md)
- corroborated by [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)
- observed in [dump.csv](../dump.csv)

Workspace implementation:

```text
Byte 2 bit 7   economy mode
Byte 3 bit 5   dash lights enabled
Byte 3 bit 4   dark mode
Byte 3 bits 3:0 luminosity level
Byte 4         power mode
```

Current simulator encoder in [modules/bsi-base/__init__.py](../modules/bsi-base/__init__.py):

```python
b2 = com['economy'] << 7
b3 = com['dash_lights'] << 5 | com['dark_mode'] << 4 | com['lum'] & 0xFF
b4 = com['power_mode']
```

Observed examples:

```text
0E 00 00 2F 03 00 00 A0
0E 00 00 2F 01 00 00 A0
```

Recommended monitor decode:

- `ignition_on`: byte 4 == `0x01`
- `accessory_on`: byte 4 == `0x03`
- `illumination_enabled`: `(byte3 >> 5) & 1`
- `illumination_level`: `byte3 & 0x0F`

Notes:

- [psa_pf2_comfort.md](psa_pf2_comfort.md) treats byte 4 values `00`, `01`, and `03` as OFF, IGN_ON, and ACC_ON.
- [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md) also treats this as the main ignition/dashboard-illumination frame and notes a 100 ms period.
- The simulator sends byte 5 as `0x80`, while the dump shows `0x00`, so only bytes 3 and 4 should be treated as stable signals for monitoring.

### 0x0F6 - BSI_SLOW_DATA (Reverse, Temperature, Odometer)

Status: **Verified (PSA-RE)**

PSA-RE canonical name: `BSI_SLOW_DATA` / `DONNEES_BSI_LENTES`. Period: 500 ms.

| Byte (0-idx) | PSA-RE signal | Encoding |
|---|---|---|
| 0 | CONFIG_MODE (bits 7-6), FACTORY_PARK (bit 5), MAIN_STATUS (bits 4-3), GEN_STATUS (bit 2), POWERTRAIN_STATUS (bits 1-0) | Status byte; real bus = `0x88` (customer config + generator ok + motor running) |
| 1 | COOLANT_TEMPERATURE | raw − 40 °C |
| 2-4 | **ODOMETER** (uint24) | × 0.1 km; `0xFFFFFF` = invalid |
| 5 | EXTERNAL_TEMPERATURE | raw × 0.5 − 40 °C; `0xFF` = invalid |
| 6 | EXTERNAL_FILTERED_TEMPERATURE | raw × 0.5 − 40 °C (filtered); `0xFF` = invalid |
| 7 | REVERSE_STATUS (bit 7), FRONT_WIPERS_STATUS (bit 6), WHEEL_POSITION (bits 5-4), CLUSTER_INDICATORS_TEST (bit 3), **BLINKERS_STATUS (bits 1-0)** | BLINKERS: 0=none, 1=right, 2=left, 3=both |

Observed examples (from bench capture):

```text
88 3C 1F 5E 0B FC FF 28
88 FF FF FF FF FC FF 28
88 FF FF FF FF FF FF 20
```

Decode snippet:

```python
coolant_c = data[1] - 40
odo_km = ((data[2] << 16) | (data[3] << 8) | data[4]) * 0.1
ext_temp_c = data[5] * 0.5 - 40 if data[5] != 0xFF else None
reverse = (data[7] >> 7) & 1
blinkers = data[7] & 0x03  # 0=none,1=right,2=left,3=both
```

Notes:

- The simulator sends `0x88` in byte 0 (matching the real-bus customer-config + generator-ok
  pattern) and `0xFF 0xFF 0xFF` (invalid sentinel) in bytes 2-4 for the odometer.  Real BSI
  sends an actual odometer count in those three bytes.  This is intentional bench simplification.
- Bytes 5 and 6 carry the same temperature measurement before and after the BSI's smoothing
  filter. The simulator sends the same value in both positions.
- **BLINKERS_STATUS** (byte 7 bits 1-0) was previously undocumented in this workspace.
- Prefer `0x1A8` bytes 5-7 for a partial-trip odometer; use `0x0F6` for the total odometer.

### 0x128 - Cluster Warning and Lamp Status

Status: Verified/Observed

Source evidence:

- partially implemented in [modules/combine/__init__.py](../modules/combine/__init__.py)
- described in [psa_pf2_comfort.md](psa_pf2_comfort.md)
- described in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)
- described in [PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md](PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md)
- observed in [dump.csv](../dump.csv)

Observed examples:

```text
B1 C0 00 00 C0 80 B0 01
B0 C0 00 00 C0 80 B0 01
91 E0 00 00 C0 80 B0 01
```

Fields reliably useful for monitoring:

| Byte | Bit(s) | Meaning | Confidence |
|------|--------|---------|------------|
| 0 | 7 | passenger airbag / airbag disable indicator | Inferred |
| 0 | 6 | seatbelt warning | Verified |
| 0 | 5 | parking brake / brake warning | Verified |
| 0 | 4 | low fuel warning | Verified |
| 0 | 2 | diesel preheat | Verified |
| 1 | 7 | warning/service indicator | Verified |
| 1 | 6 | STOP indicator | Verified |
| 1 | 4 | door open indicator | Verified |
| 4 | 7 | sidelights / parking lights | Verified |
| 4 | 6 | low beam on | Verified |
| 4 | 5 | high beam on | Verified |
| 4 | 4 | front fog | Verified |
| 4 | 3 | rear fog | Verified |
| 4 | 2 | right indicator | Verified |
| 4 | 1 | left indicator | Verified |
| 5 | 7 | cluster active | Verified |
| 6 | 7:4 | gear display code | Observed |
| 6 | 3:1 | drive gear code | Observed |
| 7 | 6:4 | gearbox mode | Observed |
| 7 | 1:0 | gearbox selection | Observed |

Notes for implementation:

- The current simulator only models part of this frame and hardcodes bytes 6 and 7 to zero.
- The real dump clearly uses bytes 6 and 7, so a monitoring app should keep those bytes available as raw signals even if symbolic decoding is not yet complete.
- The canbox source reinforces the older 407-style interpretation of this frame as core dashboard lamp state, but it does not fully explain the richer byte 6-7 values seen in the dump.
- [peugeot407can.yaml](peugeot407can.yaml) uses an older interpretation of `0x128` and should not be treated as the only source.

### Infotainment And Display Frames

### 0x131 - Doors, Fuel Context, and CDC Traffic

Status: Inferred/Observed

Source evidence:

- documented in [peugeot407can.yaml](peugeot407can.yaml) and [psa_pf2_comfort.md](psa_pf2_comfort.md)
- described in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md) as CD changer command traffic
- observed in [dump.csv](../dump.csv)

Observed examples:

```text
01 00 00 00 00
81 00 00 00 00
83 00 00 00 00
8B 00 00 00 00
83 00 02 00 00
```

Monitoring guidance:

- treat `0x131` as a mixed-purpose frame
- expect some variants to use it for doors
- expect CDC or radio-related command/status reuse on some vehicles

Workspace notes say:

- Byte 1 bits 0-5 may contain FL, FR, RL, RR, bonnet, tailgate
- Byte 3 may contribute to fuel-level calculation together with `0x161`

Observed dump caveat:

- most changes happen in byte 0 while byte 1 remains zero
- this does not fit the older YAML door mapping cleanly

Recommendation:

- if your target is a 407, monitor `0x131` raw and compare against physical door actions
- do not hardcode the older byte 1 door mapping without verification
- prefer `0x220` if it is present on the bus

Interpretation update:

- the canbox source makes it more likely that `0x131` is infotainment/CD-changer traffic on at least some PSA variants rather than a reliable universal door-state frame
- for a monitor app, treat any door interpretation on `0x131` as vehicle-specific fallback only

### 0x161 - Oil Temperature and Fuel Raw Data

Status: Verified

Source evidence:

- implemented in [modules/bsi-base/__init__.py](../modules/bsi-base/__init__.py)
- documented in [peugeot407can.yaml](peugeot407can.yaml) and [psa_pf2_comfort.md](psa_pf2_comfort.md)
- observed in [dump.csv](../dump.csv)

Observed examples:

```text
00 00 3C 07 00 00 FF
00 00 FF 07 00 00 FF
```

Recommended monitor decode:

- oil temperature raw: byte 2
- oil temperature celsius: `byte2 - 40` if following simulator convention, or `byte2 + 40` if following older note wording; verify against real temperature
- fuel raw: byte 3
- fuel level bits: `(byte3 >> 2) & 0x3F`
- fuel max bits: `(byte3 >> 1) & 0x7F`
- fuel percent: `fuel_level * 100 / fuel_max` when `fuel_max != 0`

Notes:

- The workspace notes disagree on offset wording, but the common pattern is that byte 2 is the oil temperature source.
- The simulator currently decodes oil as `msg.data[2] - 40`.

### 0x168 - COMBINE_ALERTS_INDICATORS (Dashboard Warning Lamps)

Status: **Verified (PSA-RE)**

PSA-RE canonical name: `COMBINE_ALERTS_INDICATORS` / `CDE_COMBINE_TEMOINS`. Period: 200 ms.

> ⚠️ **Correction:** Earlier versions of this document (based on `peugeot407can.yaml` and
> `psa_pf2_comfort.md`) described 0x168 as carrying **ambient temperature** (byte 0) and
> **battery voltage** (byte 1). **This was incorrect.** PSA-RE confirms that 0x168 is the
> dashboard alert/fault indicator frame, not a temperature or voltage frame. The
> `can_messages.py Msg168` implementation was already correct; only this documentation was wrong.

The frame carries one indicator flag per bit across all 8 bytes. Selected signals:

| Byte (0-idx) | Bit | Signal | Meaning |
|---|---|---|---|
| 0 | 7 | COOLANT_TEMPERATURE_ALERT | coolant temp high |
| 0 | 6 | OIL_TEMPERATURE_ALERT | oil temp high |
| 0 | 5 | COOLANT_LEVEL_ALERT | coolant level low |
| 0 | 4 | OIL_LEVEL_ALERT | oil level low |
| 0 | 3 | OIL_PRESSURE_ALERT | oil pressure low |
| 0 | 2 | BRAKE_LEVEL_ALERT | brake fluid low |
| 0 | 1 | COLD_ENGINE_ALERT | cold engine |
| 0 | 0 | DSG_FAULT | TPMS fault |
| 1 | 7 | UNDERINFLATION_ALERT | tyre under-inflation |
| 1 | 6 | PUNCTURE_ALERT | tyre puncture |
| 1 | 4 | PARTICLE_FILTER_FAULT | DPF warning |
| 3 | 5 | ABS_FAULT | ABS fault |
| 3 | 4 | ASR_FAULT | ASR/ESP fault |
| 3 | 3 | GEARBOX_FAULT | gearbox fault |
| 3 | 2 | BRAKES_FAULT | brake pads worn |
| 3 | 1 | EOBD_FAULT | MIL (check engine) |
| 4 | 5 | SAFETY_FAULT | airbag/safety fault |
| 4 | 1 | ALTERNATOR_FAULT | alternator fault |
| 7 | 6 | ENGINE_FAULT | engine fault |

See `doc/PSA_RE_comparison.md` section "0x168" for the complete 40-signal table.

Notes:

- Observed example `8C 40 00 B2 24 00 20 00` contains alert bits set (coolant + oil pressure
  alerts). This is consistent with the alert-indicator interpretation.
- Ambient temperature is carried in `0x0F6` bytes 5-6 (× 0.5 − 40 °C).
- Battery voltage is not directly available on the comfort CAN; it comes from a separate frame
  on the powertrain CAN or from the BSI diagnostic endpoint.

### 0x220 - Door and Body Openings

Status: Observed

Source evidence:

- described in [PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md](PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md)
- described in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)
- observed in [dump.csv](../dump.csv)
- mentioned in [psa_pf2.md](psa_pf2.md)

Observed example:

```text
04 00
```

Comfort-document interpretation:

| Byte | Bit | Meaning |
|------|-----|---------|
| 0 | 7 | front left door open |
| 0 | 6 | front right door open |
| 0 | 5 | rear left door open |
| 0 | 4 | rear right door open |
| 0 | 3 | trunk open |
| 0 | 2 | hood open |
| 0 | 1 | rear window open |
| 0 | 0 | fuel flap open |
| 1 | 7 | vehicle type |
| 1 | 6 | spare wheel status |

Recommendation:

- subscribe to `0x220` if present and prefer it over `0x131` for door/body state
- validate each bit against physical actions on the target vehicle before using it in user-facing UI

Interpretation update:

- the canbox source agrees with the door bits in byte 0 for front/rear doors and trunk on Peugeot 407-style traffic
- the extra body bits from the comfort document, such as hood, rear window, and fuel flap, should be treated as lower-confidence until verified on the target vehicle

### 0x1A8 - Cruise Control and Function Settings

Status: Observed

Source evidence:

- described in [PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md](PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md)
- observed in [dump.csv](../dump.csv)

Observed examples:

```text
00 FF FF 00 00 13 E2 2D
00 FF FF 00 00 FF FF FF
```

Comfort-document interpretation:

- byte 0: selected function, status, activation, unit, setting state
- bytes 1-2: cruise set speed
- bytes 5-7: trip-related display data

Recommendation:

- expose the full raw frame in your app
- decode byte 0 symbolically only after confirming bit mapping on the target car
- preserve bytes 5-7 as raw trip/status bytes even if you cannot label them yet

### 0x361 - Vehicle Configuration and Feature Availability

Status: Observed

Source evidence:

- described in [PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md](PSA_CAN_2004_COMFORT_MESSAGES_DOCUMENTATION.md)
- observed in [dump.csv](../dump.csv)

Observed example:

```text
01 01 91 40 30 10
```

Comfort-document interpretation groups this frame into:

- profile settings
- window/control features
- lighting features
- wiper/DRL capability
- advanced features
- TPMS and monitoring

Recommendation:

- use this frame for capability flags rather than transient vehicle state
- record raw bytes and annotate features only after validation on the target vehicle/equipment level

### 0x0E1 - Parking Sensor Status

Status: Inferred

Source evidence:

- documented in [peugeot407can.yaml](peugeot407can.yaml) and [psa_pf2_comfort.md](psa_pf2_comfort.md)
- described in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)
- observed in [dump.csv](../dump.csv)

Observed example:

```text
D8 00 3F FC FC FC 00
```

Monitoring guidance:

- decode only if you need parking distance visualization
- sensor distances are packed across bytes 2, 3, and 4
- byte 5 bit 0 is treated in workspace notes as parktronic active

### 0x14C / 0x28C - Speed and Odometer

Status: Inferred

Source evidence:

- described in [peugeot407can.yaml](peugeot407can.yaml) and [psa_pf2_comfort.md](psa_pf2_comfort.md)
- `0x14C` appears in the dump

Recommended monitor decode:

- speed raw: bytes 0-1, big-endian, scale `0.01 km/h`
- odometer raw: bytes 1-3, verify exact byte usage on target vehicle

These frames are not strictly comfort-only, but they are typically needed in any car-monitor application.

### 0x1D0 / 0x1E3 - HVAC State

Status: Verified

Source evidence:

- implemented in [modules/clim/__init__.py](../modules/clim/__init__.py)
- described in [psa_pf2_comfort.md](psa_pf2_comfort.md)
- described in [canbox/doc/sources/PSACAN.md](../../canbox/doc/sources/PSACAN.md)

Useful decoded fields from workspace code:

- fan speed
- recirculation
- front defrost
- left/right set temperatures
- airflow direction
- auto mode
- dual mode

Use these if climate pages or overlay monitoring are in scope.

## Recommended Subscription Order

For a first vehicle-monitoring application, start with these IDs:

1. `0x036` for ignition and illumination
2. `0x128` for warning lamps and external lighting
3. `0x161` for oil temperature, fuel level, and oil level
4. `0x168` for dashboard alert and fault indicators
5. `0x0F6` for coolant temperature, external temperature, odometer, reverse, and blinker state
6. `0x220` for door and body state
7. `0x1A8` for cruise/limiter state and partial odometer
8. `0x361` for vehicle capability/option metadata
9. `0x0E1` if parking-aid visualization is needed
10. `0x1D0` and `0x1E3` if climate monitoring is needed

If infotainment integration is also needed, add these separately:

1. `0x131` for changer or auxiliary command tracking
2. `0x0A4` and `0x125` for radio text and lists
3. `0x1A1` for BSI text or warning messages
4. `0x165`, `0x1A5`, `0x1E0`, and `0x1E5` for radio state and audio menus
5. `0x0DF`, `0x167`, `0x21F`, and `0x3E5` for display and user-input state

## Implementation Notes For A Monitor App

- Keep both raw bytes and decoded values in your internal model.
- Mark each decoded signal with a confidence level.
- Do not throw away bytes 6 and 7 of `0x128`; real traffic uses them.
- Treat `0x220` as the primary door-state source for Peugeot 407-style monitoring.
- Keep `0x131` in a separate infotainment parser unless target-vehicle testing proves it carries useful body-state data.
- Prefer passive subscriptions first; do not assume the simulator output is wire-accurate for every frame.
- Store recent samples with timestamps so you can compare state changes against physical events.

## Known Gaps In The Workspace

- The simulator does not currently implement `0x220`, `0x1A8`, or `0x361`.
- The simulator only partially models `0x128` and does not decode real gear/mode bytes.
- `0x0F6` byte 5 conflict between autowp (constant `0x8E`) and PSA-RE (external temperature)
  is resolved in favour of PSA-RE — see [CAN2004_autowp_comparison.md](CAN2004_autowp_comparison.md).
- `0x0B6` bytes 4-5 (trip odometer in cm) and byte 6 (fuel consumption counter) documented
  by autowp are not implemented; simulator sends `0x00` in those positions.
- `0x131` appears to serve multiple purposes and should be treated as infotainment-side traffic unless the target vehicle proves otherwise.

## Quick Raw Examples

These payloads are useful as smoke-test samples when developing a decoder:

```text
0x036  0E 00 00 2F 03 00 00 A0
0x128  B1 C0 00 00 C0 80 B0 01
0x161  00 00 3C 07 00 00 FF
0x168  8C 40 00 B2 24 00 20 00
0x1A8  00 FF FF 00 00 13 E2 2D
0x220  04 00
0x361  01 01 91 40 30 10
```

## Summary

For this workspace, the most reliable vehicle-monitoring core is `0x036`, `0x128`, `0x161`, `0x168`, `0x220`, `0x1A8`, and `0x361`. Infotainment and display traffic, especially `0x131`, should be parsed as a separate concern so the car-parameter monitor is not coupled to radio or changer behavior. Build the application around raw-frame retention plus progressive decoding, not around a fixed assumption that every signal is already settled.