# CAN2010 Simulator Development — CAN Messages Reference

This document is a developer guide for building a **CAN2010 simulator** that mimics the messages a PSA CAN2010 head unit (NAC/RCC) receives from the vehicle. It covers:

- The bridge architecture and data flow
- Every CAN2004 input message the bridge reads from the old car bus
- Every CAN2010 output message the bridge generates for the new head unit
- Byte-level field descriptions derived directly from the source code

---

## 1. Architecture Overview

```
Old Car (CAN2004/2007 bus)                     New Head Unit (CAN2010 bus)
┌──────────────────┐     ┌──────────────────────────────────────────────┐
│  BSI / Dashboard │────▶│                PSA CAN Bridge                 │────▶  NAC / RCC
│  ECU / modules   │     │  CanDataConverter ──▶ DataBroker              │
└──────────────────┘     │       │                    │                  │
                         │       ▼                    ▼                  │
                         │  Handle_XXX()   CanMessageHandlerContainer2010│
                         │  (parse 2004)   (builds & sends 2010 frames)  │
                         └──────────────────────────────────────────────┘
```

### Key components

| Component | File | Responsibility |
|---|---|---|
| `CanDataConverter` | `src/Can/CanDataConverter.cpp` | Receives CAN2004 frames, parses them, updates `DataBroker` |
| `DataBroker` | `src/Helpers/DataBroker.h` | Shared in-memory state; every field is annotated with its source message |
| `CanMessageHandlerContainer2010` | `src/Can/CanMessageHandlerContainer2010.cpp` | Holds all 2010 handlers; calls `SendMessage` at configured intervals |
| `MessageHandler_XXX` | `src/Can/Handlers/` | Builds one specific CAN2010 frame from `DataBroker` fields |
| `CAN_XXX_2010.h` | `src/Can/Structs/` | Bit-field structures describing every byte of each frame |

---

## 2. CAN2004 Input Messages

The bridge listens to the following messages on the **CAN2004 bus** and maps their data into `DataBroker`.

### 0x036 — BSI Commands / Ignition

**Length:** 8 bytes · **Source struct:** `CanIgnitionStruct` (`CAN_036.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Memory 1 | [3:0] | `memory_slot` (4 bits) |
| 0 | Memory 1 | [4] | `memory_ordered` |
| 0 | Memory 1 | [5] | `passenger_memory_recall_order` |
| 0 | Memory 1 | [7:6] | `ihm_profile` |
| 1 | Memory 2 | [3:0] | `memory_slot` |
| 1 | Memory 2 | [4] | `memory_ordered` |
| 1 | Memory 2 | [5] | `passenger_memory_recall_order` |
| 1 | Memory 2 | [7:6] | `ihm_profile` |
| 2 | Load shedding | [4:0] | `load_shedding_level` |
| 2 | Load shedding | [7] | **`economy_mode_active`** → `DataBroker.EconomyMode` |
| 3 | Brightness | [3:0] | **`dashboard_brightness`** → `DataBroker.Brightness` |
| 3 | Brightness | [4] | **`black_panel_status`** → `DataBroker.BlackPanel` |
| 3 | Brightness | [5] | **`night_mode`** → `DataBroker.NightMode` |
| 4 | Ignition | [2:0] | **`ignition_mode`** → `DataBroker.IgnitionMode` |
| 4 | Ignition | [3] | `prevent_fault_log` |
| 4 | Ignition | [5] | `network_supervision_enabled` |
| 4 | Ignition | [6] | `global_fault_clearance` |
| 6 | Rear camera | [3] | `activate_rear_camera` |

**Ignition mode values:**

| Value | Constant | Meaning |
|-------|----------|---------|
| 0x00 | `CAN_IGNITION_MODE_STANDBY` | Standby |
| 0x01 | `CAN_IGNITION_MODE_NORMAL` | Normal / key-on |
| 0x02 | `CAN_IGNITION_MODE_STANDBY_SOON` | About to go to standby |
| 0x03 | `CAN_IGNITION_MODE_WAKE_UP` | Wake up |
| 0x04 | `CAN_IGNITION_MODE_COM_OFF` | Communication off |

---

### 0x0F6 — Dashboard 1 (Engine / Ignition Status)

**Length:** 8 bytes · **Source struct:** `Can0F6Dash1Struct` (`CAN_0F6.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Ignition | [1:0] | `engine_status` |
| 0 | Ignition | [2] | **`ignition`** → `DataBroker.Ignition` |
| 0 | Ignition | [3] | `starting` |
| 0 | Ignition | [5] | `factory_mode` |
| 0 | Ignition | [7:6] | `config_mode` |
| 1 | — | — | **`CoolantTemperature`** → `DataBroker.CoolantTemperature` |
| 2–4 | Mileage | — | Three-byte odometer (MSB first) |
| 6 | — | — | **`ExternalTemperature`** → `DataBroker.ExternalTemperature` |
| 7 | Lights | [0] | `turn_left_light` |
| 7 | Lights | [1] | `turn_right_light` |
| 7 | Lights | [6] | `wiper_status` |
| 7 | Lights | [7] | **`reverse_gear_light`** → `DataBroker.IsReverseEngaged` |

> The entire frame is also forwarded byte-for-byte to `DataBroker.S_0F6Byte1…8` and re-emitted on CAN2010.

---

### 0x0B6 — Vehicle Speed

**Length:** 8 bytes · Bytes forwarded verbatim.

| Byte | Field | Description |
|------|-------|-------------|
| 0–1 | — | Passed through to `DataBroker.S_0B6Byte1–2` |
| 2–3 | Speed | Unsigned 16-bit speed in km/h → `DataBroker.SpeedInKmh` |
| 4–7 | — | Passed through to `DataBroker.S_0B6Byte5–8` |

---

### 0x0E6 — ESP / Stability Control

**Length:** 8 bytes.

| Byte | Field | Description |
|------|-------|-------------|
| 0–4 | Data | Forwarded to `DataBroker.S_0E6Byte1–5` |
| 5 | — | Fixed 0x83 in output |
| 6 | — | Fixed 0x8C in output |
| 7 | Checksum | Rolling counter + nibble checksum computed by bridge |

---

### 0x127 — CMB 2004 Status

**Length:** 3 bytes · **Source struct:** `Can127_2004_Struct` (`CAN_127.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Status | [7] | **`enable_vth`** → `DataBroker.EnableVTH` |
| 1 | — | — | Luminosity |

---

### 0x128 — CMB Indicator Lights (CAN2004)

**Length:** 8 bytes · **Source struct:** `CMB2004_128Struct` (`CAN_128.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Indicator1 | [1] | `passenger_seatbelt_warning` |
| 0 | Indicator1 | [2] | `diesel_pre_heating` |
| 0 | Indicator1 | [4] | `fuel_level_low` |
| 0 | Indicator1 | [5] | `handbrake_signal` |
| 0 | Indicator1 | [6] | `driver_seatbelt_warning` |
| 0 | Indicator1 | [7] | `passenger_airbag_deactivated` |
| 1 | Indicator2 | [2] | `activate_front_passenger_protection` |
| 1 | Indicator2 | [6] | `stop_light` |
| 1 | Indicator2 | [7] | `service_indicator_exclamation` |
| 2 | Indicator3 | [0] | `ready_lamp` |
| 2 | Indicator3 | [1] | `warning_light_active` |
| 2 | Indicator3 | [2] | `suspension_status` |
| 2 | Indicator3 | [3] | `esp_in_progress` |
| 2 | Indicator3 | [4] | `esp_inactivated` |
| 2 | Indicator3 | [5] | `child_security_active` |
| 2 | Indicator3 | [6] | `change_personalization` |
| 2 | Indicator3 | [7] | `change_color` |
| 3 | Indicator4 | [1:2] | `foot_on_break_indicator` |
| 3 | Indicator4 | [3] | `operation_indicator_light_blinking` |
| 3 | Indicator4 | [4] | `operation_indicator_light_on` |
| 3 | Indicator4 | [6] | `passenger_seatbelt_warning_blinking` |
| 3 | Indicator4 | [7] | `driver_seatbelt_warning_blinking` |
| 4 | Indicator5 | [0] | `drl` |
| 4 | Indicator5 | [1] | `left_turn_indicator` |
| 4 | Indicator5 | [2] | `right_turn_indicator` |
| 4 | Indicator5 | [3] | `rear_foglight` |
| 4 | Indicator5 | [4] | `front_foglight` |
| 4 | Indicator5 | [5] | `high_beam_on` |
| 4 | Indicator5 | [6] | `low_beam_on` |
| 4 | Indicator5 | [7] | `parking_light_indicator` |
| 5 | Indicator6 | [0] | `fse_inhibited` |
| 5 | Indicator6 | [1] | `row1_rr_seatbelt_forgotten_blinking` |
| 5 | Indicator6 | [2] | `row1_rr_seatbelt_forgotten` |
| 5 | Indicator6 | [3] | `row1_rc_seatbelt_forgotten_blinking` |
| 5 | Indicator6 | [4] | `row1_rc_seatbelt_forgotten` |
| 5 | Indicator6 | [5] | `row1_rl_seatbelt_forgotten_blinking` |
| 5 | Indicator6 | [6] | `row1_rl_seatbelt_forgotten` |
| 5 | Indicator6 | [7] | `cmb_active` |
| 6 | Indicator7 | [0] | `display_blinking` |
| 6 | Indicator7 | [3:1] | `gear_position_drive` |
| 6 | Indicator7 | [7:4] | `gear_position_cmb` |
| 7 | Indicator8 | [1:0] | `auto_gearbox_selection` |
| 7 | Indicator8 | [6:4] | `auto_gearbox_mode` |

---

### 0x161 — Fuel / Range

**Length:** 7 bytes. Bytes 0, 2, 3, 6 are forwarded to `DataBroker.S_161Byte1/3/4/7`.

---

### 0x168 — Dashboard 3 / Fault Indicators (CAN2004)

**Length:** 8 bytes. See `CAN_168.h` for structs. Significant fields extracted:

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 1 | Field2 | [1] | `max_rpm_2` |
| 1 | Field2 | [2] | `max_rpm_1` |
| 1 | Field2 | [3] | `auto_wiping_active` |
| 1 | Field2 | [4] | `fap_clogged` |
| 1 | Field2 | [5] | `minc_blinking` |
| 1 | Field2 | [6] | `flat_tyre_alert` |
| 1 | Field2 | [7] | `tyre_pressure_alert` |
| 2 | Field3 | — | `foot_on_clutch`, row2 seatbelt status/blinking |
| 3 | Field4 | — | `serious_suspension_fault`, `serious_ref_ehb_fault`, `mil`, `brake_pad_fault`, `gearbox_fault`, `esp_fault`, `abs_fault`, `water_in_diesel` |
| 4 | Field5 | — | `generator_fault`, `battery_charge_fault`, `scr_indicator` |
| 5 | Field6 | — | `caar_lamp_status`, `curve_code_fault` |
| 6 | Field7 | — | `fse_tightening_fault`, `fse_system_fault`, `stt_lamp_status`, `power_steering_fault` |

---

### 0x1A1 — Display / Popup Messages

**Length:** 8 bytes. All bytes forwarded to `DataBroker.S_1A1Byte1–8`. Used directly (or overridden with a door-open popup) in the CAN2010 0x1A1 output.

---

### 0x1A8 — Cruise Control (CAN2004)

**Length:** 8 bytes · **Source struct:** `CAN_1A8_2004Struct` (`CAN_1A8_2004.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Field1 | [0] | `setting_status` |
| 0 | Field1 | [1] | `unit_of_speed` |
| 0 | Field1 | [2] | **`activate_function`** |
| 0 | Field1 | [5:3] | **`status_of_selected_function`** |
| 0 | Field1 | [7:6] | **`selected_function`** |
| 1 | Speed | — | Cruise speed byte 1 |
| 2 | Speed | — | Cruise speed byte 2 |
| 5–7 | Trip | — | Trip counter on CMB (3 bytes) |

---

### 0x21F — Steering Wheel Radio Remote

**Length:** 2 or 3 bytes · **Source struct:** `CAN_21F.h`

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Command | [1] | `mode_phone` |
| 0 | Command | [2] | `volume_minus` |
| 0 | Command | [3] | `volume_plus` |
| 0 | Command | [4] | `overflow_scan_negative` |
| 0 | Command | [5] | `overflow_scan_positive` |
| 0 | Command | [6] | `seek_down` |
| 0 | Command | [7] | `seek_up` |
| 1 | — | — | Scroll position |

---

### 0x220 — Door Status (CAN2004)

**Length:** 2 bytes · **Source struct:** `Can220_2004_Struct` (`CAN_220.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Field1 | [0] | `fuel_flap_open` |
| 0 | Field1 | [1] | `rear_window_open` |
| 0 | Field1 | [2] | `hood_open` |
| 0 | Field1 | [3] | `trunk_open` |
| 0 | Field1 | [4] | `rear_right_door_open` |
| 0 | Field1 | [5] | `rear_left_door_open` |
| 0 | Field1 | [6] | `front_right_door_open` |
| 0 | Field1 | [7] | `front_left_door_open` |
| 1 | Field2 | [6] | `spare_wheel_status` |
| 1 | Field2 | [7] | `vehicle_type` |

---

### 0x217 — CMB Requests (CAN2004)

**Length:** 8 bytes. Bytes 0–6 forwarded; byte 7 set to 0x00 in CAN2010 output. See `CAN_217.h` for full bit layout (brightness, button presses, reostats, vehicle speed, etc.).

---

### 0x221 — Air Conditioning (CAN2004)

**Length:** 7 bytes. Forwarded to `DataBroker.S_221Byte1–7` (0xFF values are zeroed out in output).

---

### 0x227 — Climate Control Data

**Length:** 7 bytes. Bytes 0–3 forwarded to `DataBroker.S_227Byte1–4`.

---

### 0x3A7 — Maintenance Data (CAN2004)

**Length:** 8 bytes · **Source struct:** `Can3A7Struct` (`CAN_3A7.h`)

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Type | [3:2] | `wrench_without_km` |
| 0 | Type | [5:4] | `wrench_with_km` → `DataBroker.WrenchIcon` |
| 0 | Type | [7] | `maintenance_due` |
| 1 | Km info | [5] | `km_blinking` |
| 1 | Km info | [7] | `maintenance_sign_km` |
| 2 | Time info | [5] | `time_blinking` |
| 2 | Time info | [7] | `maintenance_sign_time` |
| 3–4 | — | — | Maintenance km (MSB first) |
| 5–6 | — | — | Days before maintenance (MSB first) |

---

### 0x361 — Vehicle Configuration (CAN2004)

**Length:** 6 bytes · **Source struct:** `Can361_2004Struct` (`CAN_361_2004.h`). Maps directly to `DataBroker` options used by the 0x361 and 0x260 CAN2010 handlers (DRL, auto-lighting, ambient lighting, blindspot monitoring, TPMS, etc.).

---

## 3. CAN2010 Output Messages

These are the messages the bridge sends on the **CAN2010 bus** for the head unit (NAC/RCC).

### 0x036 — BSI Commands 2010 (Ignition / Brightness)

**Length:** 8 bytes · **Interval:** ~90 ms · **Struct:** `CAN_036_2010.h`

| Byte | Field | Bits | Value source |
|------|-------|------|-------------|
| 0 | Byte1 | [3:0] | `memory_slot` |
| 0 | Byte1 | [4] | `driver_memo_sequence` |
| 0 | Byte1 | [5] | `driver_memo_recall` |
| 0 | Byte1 | [7:6] | **`driving_direction`** ← `DataBroker.IsReverseEngaged` |
| 1 | — | — | Unused (0x00) |
| 2 | Byte3 | [6:0] | `ambience_level` |
| 2 | Byte3 | [7] | **`economy_mode_active`** ← `DataBroker.EconomyMode` |
| 3 | Byte4 | [3:0] | **`dashboard_brightness`** ← `DataBroker.Brightness` |
| 3 | Byte4 | [4] | **`black_panel_status`** ← `DataBroker.BlackPanel` |
| 3 | Byte4 | [5] | **`night_mode`** ← `DataBroker.NightMode` |
| 4 | Byte5 | [2:0] | **`ignition_mode`** ← `DataBroker.IgnitionMode` |
| 7 | — | — | Fixed 0xA0 |

**Driving direction values:**

| Value | Constant | Meaning |
|-------|----------|---------|
| 0x00 | `DRIVING_DIRECTION_UNDEFINED` | Undefined |
| 0x01 | `DRIVING_DIRECTION_FORWARD` | Forward |
| 0x02 | `DRIVING_DIRECTION_REVERSE` | Reverse |
| 0x03 | `DRIVING_DIRECTION_INVALID` | Invalid |

---

### 0x0B6 — Vehicle Speed (Pass-Through)

**Length:** 8 bytes · **Interval:** ~45 ms

All 8 bytes are forwarded verbatim from `DataBroker.S_0B6Byte1–8`. Bytes 2–3 encode the current speed in km/h (unsigned 16-bit, big-endian).

---

### 0x0E6 — ESP / Wheel Speed

**Length:** 8 bytes · **Interval:** ~90 ms

| Byte | Field | Description |
|------|-------|-------------|
| 0–4 | Data | From `DataBroker.S_0E6Byte1–5` |
| 5 | — | Fixed 0x83 |
| 6 | — | Fixed 0x8C |
| 7 | Checksum | `(counter << 4) \| ((0x7FFC - nibble_sum) & 0x0F)`, counter cycles 0x0–0xF |

---

### 0x0F6 — Dashboard 1 (Pass-Through)

**Length:** 8 bytes · **Interval:** ~450 ms

All 8 bytes forwarded verbatim from `DataBroker.S_0F6Byte1–8`.

---

### 0x122 — Cruise Control Presence

**Length:** 8 bytes · **Interval:** 200 ms

All bytes are 0x00. This empty frame must be present on the bus to signal cruise-control availability. Only sent after ignition data has arrived.

---

### 0x128 — CMB Indicator Lights (CAN2010)

**Length:** 8 bytes · **Interval:** 200 ms · **Struct:** `CAN_128_2010.h`

This is a full remap of the CAN2004 0x128 layout to the CAN2010 structure:

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Indicator1 | [0] | `drl` |
| 0 | Indicator1 | [1] | `left_turn_indicator` |
| 0 | Indicator1 | [2] | `right_turn_indicator` |
| 0 | Indicator1 | [3] | `rear_foglight` |
| 0 | Indicator1 | [4] | `front_foglight` |
| 0 | Indicator1 | [5] | `high_beam_on` |
| 0 | Indicator1 | [6] | `low_beam_on` |
| 0 | Indicator1 | [7] | `parking_light_indicator` |
| 1 | — | — | `S_128Byte7` (gear display from 2004, byte 7) |
| 2 | — | — | `S_128Byte8` |
| 3 | Indicator4 | [0] | `fse_inhibited` |
| 3 | Indicator4 | [1] | `handbrake_signal` |
| 3 | Indicator4 | [3:2] | `foot_on_break_indicator` |
| 3 | Indicator4 | [4] | `passenger_airbag_activated` |
| 3 | Indicator4 | [5] | `child_security_active` |
| 3 | Indicator4 | [6] | `stop_light` |
| 3 | Indicator4 | [7] | `service_indicator_exclamation` |
| 4 | Indicator5 | [0] | `suspension_status` |
| 4 | Indicator5 | [1] | `esp_in_progress` |
| 4 | Indicator5 | [2] | `esp_inactivated` |
| 4 | Indicator5 | [4] | `operation_indicator_light_blinking` |
| 4 | Indicator5 | [5] | `operation_indicator_light_on` |
| 4 | Indicator5 | [6] | `door_open` (= `DoorStatusByte > 0`) |
| 4 | Indicator5 | [7] | `diesel_pre_heating` |
| 5 | Indicator6 | [0] | `row1_rl_seatbelt_forgotten` |
| 5 | Indicator6 | [2:1] | `scr_indicator` |
| 5 | Indicator6 | [3] | `passenger_seatbelt_warning_blinking` |
| 5 | Indicator6 | [4] | `passenger_seatbelt_warning` |
| 5 | Indicator6 | [5] | `driver_seatbelt_warning_blinking` |
| 5 | Indicator6 | [6] | `driver_seatbelt_warning` |
| 5 | Indicator6 | [7] | `fuel_level_low` |
| 6 | Indicator7 | [0] | `activate_front_passenger_protection` |
| 6 | Indicator7 | [1] | `warning_light_active` |
| 6 | Indicator7 | [2] | `cmb_active` |
| 6 | Indicator7 | [3] | `row1_rr_seatbelt_forgotten_blinking` |
| 6 | Indicator7 | [4] | `row1_rr_seatbelt_forgotten` |
| 6 | Indicator7 | [5] | `row1_rc_seatbelt_forgotten_blinking` |
| 6 | Indicator7 | [6] | `row1_rc_seatbelt_forgotten` |
| 6 | Indicator7 | [7] | `row1_rl_seatbelt_forgotten_blinking` |
| 7 | Indicator8 | [0] | `change_personalization` |
| 7 | Indicator8 | [1] | `change_color` |
| 7 | Indicator8 | [2] | `ready_lamp` |
| 7 | Indicator8 | [3] | `minc_blinking` |
| 7 | Indicator8 | [5:4] | `foot_on_clutch` |

---

### 0x161 — Fuel / Range (CAN2010)

**Length:** 7 bytes · **Interval:** ~480 ms · **Struct:** `CAN_161_2010.h`

| Byte | Description |
|------|-------------|
| 0 | `S_161Byte1` from 2004 |
| 1 | 0x00 |
| 2 | `S_161Byte3` from 2004 |
| 3 | `S_161Byte4` from 2004 |
| 4 | Fuel tank capacity: `config.FUEL_TANK_CAPACITY_IN_LITERS` in bits [7:1] |
| 5 | 0x00 |
| 6 | `S_161Byte7` from 2004 |

---

### 0x168 — Dashboard 3 / Fault Indicators (CAN2010)

**Length:** 8 bytes · **Interval:** 200 ms · **Struct:** `CAN_168_2010.h`

Full remap from CAN2004 0x168 fields to CAN2010 layout:

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Byte1 | — | `S_168Byte1` (byte 0 pass-through), `number_of_gears` forced to 0 |
| 1 | Byte2 | [1] | `max_rpm_2` |
| 1 | Byte2 | [2] | `max_rpm_1` |
| 1 | Byte2 | [3] | `auto_wiping_active` |
| 1 | Byte2 | [4] | `fap_clogged` |
| 1 | Byte2 | [6] | `flat_tyre_alert` |
| 1 | Byte2 | [7] | `tyre_pressure_alert` |
| 2 | Byte3 | [0] | `generator_fault` |
| 2 | Byte3 | [1] | `battery_charge_fault` |
| 2 | Byte3 | [2] | `serious_suspension_fault` |
| 2 | Byte3 | [3] | `serious_ref_ehb_fault` |
| 3 | Byte4 | [1] | `mil` |
| 3 | Byte4 | [2] | `brake_pad_fault` |
| 3 | Byte4 | [3] | `gearbox_fault` |
| 3 | Byte4 | [4] | `esp_fault` |
| 3 | Byte4 | [5] | `abs_fault` |
| 3 | Byte4 | [6] | `fse_tightening_fault` |
| 3 | Byte4 | [7] | `fse_system_fault` |
| 4 | Byte5 | [1:0] | `stt_lamp_status` |
| 4 | Byte5 | [2] | `power_steering_fault` |
| 4 | Byte5 | [4:3] | `caar_lamp_status` |
| 4 | Byte5 | [6] | `curve_code_fault` |
| 4 | Byte5 | [7] | `water_in_diesel` |
| 6 | Byte7 | [4:1] | `gearbox_position` |
| 6 | Byte7 | [7] | `authorize_vth` ← `DataBroker.EnableVTH` |

---

### 0x1A1 — Display / Popup Messages (CAN2010)

**Length:** 8 bytes · **Interval:** ~190 ms

Normally all 8 bytes are forwarded from `DataBroker.S_1A1Byte1–8`.

**Door-open popup override** (when `config.GENERATE_POPUP_FOR_DOOR_STATUS = true` and the 2004 bus does not supply popup messages):

| Byte | Value | Description |
|------|-------|-------------|
| 0 | `0x0C` (show) or `0x0E` (hide) | Show/hide command |
| 1 | `0x0B` | Popup ID: doors/boot/bonnet/fuel open |
| 2 | Priority + show flags | bit2=priority, bit3=CMB, bit4=EMF, bit5=VTH |
| 3 | Door status byte 1 | Front left/right, rear left/right, boot, bonnet |
| 4 | Door status byte 2 | Fuel flap |

**Popup message IDs** (byte 1):

| Value | Constant | Message |
|-------|----------|---------|
| 0x00 | `CAN_POPUP_MSG_DIAGNOSIS_OK` | Diagnosis OK |
| 0x01 | — | Engine temperature fault – stop vehicle |
| 0x03 | — | Top up coolant level |
| 0x04 | — | Top up engine oil level |
| 0x05 | — | Engine oil pressure fault – stop vehicle |
| 0x08 | — | Braking system faulty |
| 0x0B | — | Door/boot/bonnet/fuel tank open |
| 0x11 | — | Suspension faulty – max 90 km/h |
| 0x13 | — | Power steering faulty |
| 0x61 | — | Parking brake applied |
| 0x62 | — | Parking brake released |
| 0x67 | — | Brake pads worn |

See `CanDisplayStructs.h` for the complete list.

---

### 0x1A8 — Cruise Control Status (CAN2010)

**Length:** 8 bytes · **Interval:** 200 ms

| Byte | Value |
|------|-------|
| 0 | `0x02` if cruise active, `0x00` otherwise |
| 1 | `CruiseSpeed1` |
| 2 | `CruiseSpeed2` |
| 3 | `CruiseSpeed1` (duplicate) |
| 4 | `CruiseSpeed2` (duplicate) |
| 5–7 | Trip counter on CMB (3 bytes) |

---

### 0x217 — CMB Requests Pass-Through

**Length:** 8 bytes · **Interval:** 100 ms (forced on each received 2004 0x217)

All bytes forwarded from `DataBroker.S_217Byte1–8`. Byte 7 is always 0x00. If `config.MODIFY_217_WITH_CURRENT_SPEED` is enabled, byte 6 is replaced with the current speed in km/h.

---

### 0x21F — Steering Wheel Remote (CAN2010)

**Length:** 3 bytes · **Interval:** 100 ms · **Struct:** `CAN_21F_2010.h`

| Byte | Field | Bits | Description |
|------|-------|------|-------------|
| 0 | Command1 | [0] | `list` |
| 0 | Command1 | [1] | `mode_phone` |
| 0 | Command1 | [2] | `volume_minus` |
| 0 | Command1 | [3] | `volume_plus` |
| 0 | Command1 | [6] | `seek_down` |
| 0 | Command1 | [7] | `seek_up` |
| 1 | — | — | Scroll position |
| 2 | Command3 | [6] | `source` (if `REPLACE_REMOTE_MODE_BTN_WITH_SRC` enabled, `mode_phone` bit is moved here) |
| 2 | Command3 | [7] | `radio_command_validation` |

---

### 0x227 — Air Conditioning

**Length:** 7 bytes · **Interval:** 500 ms

| Byte | Value |
|------|-------|
| 0 | `S_227Byte1` |
| 1 | `S_227Byte2` |
| 2 | `S_227Byte3` |
| 3 | `S_227Byte4` |
| 4–6 | 0x00 |

---

### 0x228 — Cruise Control Full Status (CAN2010)

**Length:** 8 bytes · **Interval:** 1000 ms · **Struct:** `CAN_228_2010.h`

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Speed byte 1 | — | `CruiseSpeed1` |
| 1 | Speed byte 2 | — | `CruiseSpeed2` |
| 2 | Status1 | [0] | `setting_status` (fixed 0) |
| 2 | Status1 | [1] | `target_present` (fixed 1) |
| 2 | Status1 | [2] | `activate_function` |
| 2 | Status1 | [5:3] | `status_of_selected_function` |
| 2 | Status1 | [7:6] | `selected_function` |
| 3 | — | — | 0x80 |
| 4 | — | — | 0x14 |
| 5 | — | — | 0x7F |
| 6 | — | — | 0xFF |
| 7 | — | — | 0x98 |

---

### 0x236 — BSI / Vehicle Status (CAN2010)

**Length:** 8 bytes · **Interval:** 1000 ms · **Struct:** `CAN_236_2010.h`

Only sent after ignition data has arrived.

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | VehicleStatus1 | [3:0] | `vehicle_config` (0x04 = client) |
| 0 | VehicleStatus1 | [7:4] | `electric_network_status` (0x00 normal, 0x01 eco) |
| 1 | — | — | Fixed 0x03 |
| 2 | — | — | Fixed 0xDE |
| 3–4 | — | — | 0x00 |
| 5 | VehicleStatus2 | [6] | `driver_door_status` ← `IsFrontLeftDoorOpen` |
| 5 | VehicleStatus2 | [7] | `trunk_status` ← `IsBootLidOpen` |
| 6 | — | — | Fixed 0xFE |
| 7 | DoorStatus | [1] | `passenger_door_status` ← `IsFrontRightDoorOpen` |
| 7 | DoorStatus | [3] | `driver_door_status_estimated` ← `IsFrontLeftDoorOpen` |
| 7 | DoorStatus | [4] | `rear_left_door_status` |
| 7 | DoorStatus | [5] | `rear_right_door_status` |

**Electric network status values:**

| Value | Constant | Meaning |
|-------|----------|---------|
| 0x00 | `CAN_2010_ELECTRIC_NETWORK_STATUS_NORMAL` | Normal |
| 0x01 | `CAN_2010_ELECTRIC_NETWORK_STATUS_ECO` | Economy |
| 0x02 | `CAN_2010_ELECTRIC_NETWORK_STATUS_START_AVAIL` | Start available |
| 0x03 | `CAN_2010_ELECTRIC_NETWORK_STATUS_STARTING` | Starting |

---

### 0x260 — Vehicle Settings (Language, Units, Personalisation)

**Length:** 8 bytes · **Interval:** 500 ms · **Struct:** `CAN_260_2010.h`

Only sent after ignition data has arrived.

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Byte1 | [0] | `consumption_unit` ← `config.CONSUMPTION_UNIT` |
| 0 | Byte1 | [1] | `distance_unit` ← `config.DISTANCE_UNIT` |
| 0 | Byte1 | [6:2] | `language` ← `config.LANGUAGE` |
| 0 | Byte1 | [7] | `unit_and_language_data_valid` = 1 |
| 1 | Byte2 | [1:0] | `sound_harmony` ← `config.SOUND_HARMONY` |
| 1 | Byte2 | [2] | `vehicle_function_data` = 1 |
| 1 | Byte2 | [5:3] | `ambience_level` ← `config.AMBIENCE_LEVEL` |
| 1 | Byte2 | [6] | `temperature_unit` ← `config.TEMPERATURE_UNIT` |
| 1 | Byte2 | [7] | `volume_unit` ← `config.VOLUME_UNIT` |
| 2 | Byte3 | [0] | `ambience_lighting` ← `DataBroker.AmbientLighting` |
| 2 | Byte3 | [1] | `drl` ← `DataBroker.DRL` |
| 2 | Byte3 | [7] | `automatic_electric_brake` ← `DataBroker.AutomaticElectricBrake` |
| 5 | Byte6 | [4] | `braking_on_alarm_risk` ← `DataBroker.BreakingOnAlarmRisk` |
| 3–4, 6–7 | — | — | 0x00 |

**Language values** (5-bit field, examples):

| Value | Language | Value | Language |
|-------|----------|-------|----------|
| 0x00 | French | 0x01 | English |
| 0x02 | German | 0x03 | Spanish |
| 0x04 | Italian | 0x05 | Portuguese |
| 0x06 | Dutch | 0x0E | Russian |
| 0x0F | Czech | 0x10 | Croatian |
| 0x11 | Hungarian | 0x12 | Arabic |

See `CAN_260_2010.h` for the complete list of 32 languages.

---

### 0x276 — Date and Time

**Length:** 8 bytes · **Interval:** 1000 ms · **Struct:** `CAN_276_2010.h`

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Byte1 | [6:0] | `year` (= `DataBroker.Year - 2000`) |
| 0 | Byte1 | [7] | `time_format` = 1 (24-hour) |
| 1 | Byte2 | [3:0] | `month` |
| 2 | Byte3 | [5:0] | `day` |
| 3 | Byte4 | [4:0] | `hour` |
| 4 | Byte5 | [5:0] | `minute` |
| 5–7 | — | — | 0x00 |

---

### 0x2B6 — VIN Bytes 10–17

**Length:** 8 bytes · Only sent after ignition data has arrived.

| Byte | Value |
|------|-------|
| 0–7 | `config.VIN_FOR_HEADUNIT[9..16]` |

---

### 0x336 — VIN Bytes 1–3

**Length:** 8 bytes · Only sent after ignition data has arrived.

| Byte | Value |
|------|-------|
| 0–2 | `config.VIN_FOR_HEADUNIT[0..2]` |
| 3–7 | Unused |

---

### 0x361 — Vehicle Feature Configuration (CAN2010)

**Length:** 4 bytes · **Interval:** 500 ms · **Struct:** `CAN_361_2010.h`

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Byte1 | [0] | `drl_present` |
| 0 | Byte1 | [1] | `auto_lighting` |
| 0 | Byte1 | [2] | `ambient_lighting` |
| 0 | Byte1 | [3] | `blindspot_monitoring` |
| 0 | Byte1 | [6] | `highway_lighting_present` |
| 0 | Byte1 | [7] | `setting_menu_available` = 1 |
| 1 | Byte2 | [1] | `hinge_panel_select` |
| 1 | Byte2 | [4] | `permanent_rear_flap_lock` |
| 1 | Byte2 | [5] | `follow_me_home` |
| 1 | Byte2 | [6] | `rear_wiper_option` |
| 1 | Byte2 | [7] | `aas_disable` |
| 2 | Byte3 | [4] | `automatic_electric_brake` |
| 2 | Byte3 | [5] | `config_enabled` |
| 2 | Byte3 | [7] | `tnb_present` |
| 3 | Byte4 | [2:0] | `tpms_present` |
| 3 | Byte4 | [3] | `irc_present` |
| 3 | Byte4 | [6] | `breaking_on_alarm_risk` |
| 3 | Byte4 | [7] | `tpms_reset_present` |

---

### 0x3B6 — VIN Bytes 4–9

**Length:** 8 bytes · Only sent after ignition data has arrived.

| Byte | Value |
|------|-------|
| 0–5 | `config.VIN_FOR_HEADUNIT[3..8]` |
| 6–7 | Unused |

---

### 0x3E7 — Maintenance Data (CAN2010)

**Length:** 5 bytes · **Interval:** 500 ms · **Struct:** `CAN_3E7_2010.h`

| Byte | Field | Bits | Value |
|------|-------|------|-------|
| 0 | Byte1 | [2] | `maintenance_sign_time` |
| 0 | Byte1 | [3] | `maintenance_sign_km` |
| 0 | Byte1 | [4] | `km_blinking` (time or km blinking) |
| 0 | Byte1 | [5] | `wrench_icon` |
| 0 | Byte1 | [7] | `maintenance_type_km` (`IsMaintenanceDue`) |
| 1–2 | — | — | Days until maintenance (MSB first) |
| 3–4 | — | — | Km until maintenance (MSB first) |

---

## 4. Simulator Development Notes

When writing a CAN2010 simulator (e.g. for testing the NAC/RCC without a real car), implement the following:

### Minimum required messages

To make a NAC/RCC boot and display the main screen, send at minimum:

| Message | Minimum content |
|---------|----------------|
| **0x036** | `ignition_mode = 0x01` (normal), `driving_direction = 0x01` (forward) |
| **0x236** | `vehicle_config = 0x04` (client), `electric_network_status = 0x00` |
| **0x0F6** | `ignition = 1`, valid coolant/external temperature |
| **0x0B6** | Speed = 0 |
| **0x128** | All zero indicators (vehicle at rest) |
| **0x168** | All zero faults |
| **0x260** | Valid language and unit configuration |
| **0x276** | Current date and time |

### Message scheduling

Use the intervals documented above. Key timing requirements:

- **0x036, 0x217, 0x21F** — 100 ms (high priority, steering + ignition)
- **0x0B6, 0x0E6** — 45–90 ms (speed/stability, real-time)
- **0x128, 0x1A8, 0x168, 0x1A1** — 200 ms (dashboard indicators)
- **0x0F6, 0x161, 0x260, 0x361, 0x3E7** — 500 ms (low-frequency settings)
- **0x228, 0x236, 0x276, 0x2B6, 0x3B6, 0x336** — 1000 ms (VIN, time, cruise status)

### 0x0E6 Rolling checksum

The NAC/RCC validates the checksum in byte 7 of 0x0E6. Implement as follows:

```c
static uint8_t counter = 0;  // cycles 0x0..0xF

uint8_t compute_chk(uint8_t buf[8]) {
    uint8_t sum = counter;
    for (int i = 0; i < 7; i++) {
        sum += buf[i] >> 4;
        sum += buf[i] & 0x0F;
    }
    uint8_t result = (counter << 4) | ((0x7FFC - sum) & 0x0F);
    counter = (counter < 0x0F) ? counter + 1 : 0;
    return result;
}
```

Place the result in `buf[7]` after setting bytes 0–6.

### VIN encoding

The head unit expects the VIN string split across three messages:

| Message | Characters |
|---------|-----------|
| 0x336 | chars 1–3 (indices 0–2) |
| 0x3B6 | chars 4–9 (indices 3–8) |
| 0x2B6 | chars 10–17 (indices 9–16) |

Use ASCII. A dummy VIN such as `VF3XXXXXXXXYYYYY` is sufficient for testing.

### Door popup

If the head unit firmware requires a door-status popup message on 0x1A1 (e.g. older NAC builds), send byte 0 = `0x0E` (hide) with byte 1 = `0x0B` when no doors are open.

---

## 5. Quick Reference — Message ID Summary

| ID | Direction | Protocol | Description | Interval |
|----|-----------|----------|-------------|---------|
| 0x036 | IN (2004) / OUT (2010) | Both | Ignition / BSI commands | 90 ms |
| 0x0B6 | IN / OUT pass-through | Both | Vehicle speed | 45 ms |
| 0x0E6 | IN / OUT | Both | ESP / wheel speed (+ checksum) | 90 ms |
| 0x0F6 | IN / OUT pass-through | Both | Dashboard 1 (temperature, mileage) | 450 ms |
| 0x122 | OUT only | 2010 | Cruise control presence (empty) | 200 ms |
| 0x127 | IN only | 2004 | CMB 2004 (VTH enable) | — |
| 0x128 | IN (2004) / OUT (2010) | Both | CMB indicator lights | 200 ms |
| 0x161 | IN / OUT | Both | Fuel / range | 480 ms |
| 0x168 | IN (2004) / OUT (2010) | Both | Dashboard 3 / faults | 200 ms |
| 0x1A1 | IN / OUT | Both | Display / popup messages | 190 ms |
| 0x1A8 | IN (2004) / OUT (2010) | Both | Cruise control | 200 ms |
| 0x217 | IN / OUT pass-through | Both | CMB requests / steering wheel | 100 ms |
| 0x21F | IN / OUT | Both | Radio remote commands | 100 ms |
| 0x220 | IN only | 2004 | Door status | — |
| 0x221 | IN / OUT | Both | Climate (disabled in container) | 1000 ms |
| 0x227 | IN / OUT pass-through | Both | Air conditioning data | 500 ms |
| 0x228 | OUT only | 2010 | Cruise control full status | 1000 ms |
| 0x236 | OUT only | 2010 | BSI / vehicle status + door status | 1000 ms |
| 0x260 | OUT only | 2010 | Vehicle settings (language, units) | 500 ms |
| 0x276 | OUT only | 2010 | Date and time | 1000 ms |
| 0x2B6 | OUT only | 2010 | VIN bytes 10–17 | 1000 ms |
| 0x336 | OUT only | 2010 | VIN bytes 1–3 | 1000 ms |
| 0x361 | IN (2004) / OUT (2010) | Both | Vehicle feature configuration | 500 ms |
| 0x3A7 | IN only | 2004 | Maintenance data | — |
| 0x3B6 | OUT only | 2010 | VIN bytes 4–9 | 1000 ms |
| 0x3E7 | OUT only | 2010 | Maintenance data | 500 ms |
