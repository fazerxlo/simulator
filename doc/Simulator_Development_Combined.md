# Simulator Development — Combined CAN2004 ↔ CAN2010 Reference

This document combines and reconciles:

- `doc/PSACANBridgeCAN2010_Simulator_Development.md`
- `doc/arduino-psa-comfort-can-adapter_Simulator_Development.md`

It is intended as a practical simulator-oriented reference for both implementations:

- **PSA CAN Bridge** (`src/Can/...`, C++)
- **Arduino comfort CAN adapter** (`arduino-psa-comfort-can-adapter.ino`)

---

## 1) Shared Architecture

Both projects bridge an old PSA CAN network (CAN2004 side) with a newer CAN2010 telematic/head-unit side.

- **CAN2004 side (car/BSI/dashboard)** provides ignition, speed, status, comfort, and personalization data.
- **CAN2010 side (NAC/SMEG/RCC)** expects normalized frames, regular timing, and certain synthetic helper frames.

Common pipeline:

1. Receive CAN2004 frames
2. Decode/remap fields
3. Build CAN2010-compatible frames
4. Periodically transmit with expected cadence

---

## 2) Canonical Simulator Minimum Set (for NAC/RCC boot and stable UI)

Send at least the following CAN2010 frames:

| ID | Purpose | Minimum expectation |
|---|---|---|
| `0x036` | Ignition / BSI status | Ignition normal (`0x01`), forward direction |
| `0x236` | Vehicle electrical/network status | Client config, normal or ECO as needed |
| `0x0F6` | Dashboard status | Ignition ON with valid temperature fields |
| `0x0B6` | Speed | Speed = 0 when parked |
| `0x128` | Indicator cluster | Neutral/no warning baseline |
| `0x168` | Fault cluster | No active faults baseline |
| `0x260` | Language/units/settings | Valid language + unit payload |
| `0x276` | Date/time | Continuously valid clock data |

Recommended supporting frames:

- `0x0E6` with valid rolling checksum/counter
- `0x361` feature availability
- VIN split frames `0x336`, `0x3B6`, `0x2B6`
- Optional popup frame `0x1A1` (door popup compatibility)

---

## 3) Unified Message Matrix (high-value simulator IDs)

| ID | CAN2004 In | CAN2010 Out | Combined behavior summary |
|---|---|---|---|
| `0x036` | Yes | Yes | Economy mode, brightness, night/black panel, ignition mode remap |
| `0x0B6` | Yes | Yes | Speed/rpm source; usually pass-through or directly mirrored |
| `0x0E6` | Yes | Yes | Wheel/ESP info; byte7 checksum+counter regenerated |
| `0x0F6` | Yes | Yes | Ignition/external temperature/mileage; used as readiness signal |
| `0x122` | Optional trigger source | Yes | Empty/presence frame for cruise/FMUX context |
| `0x128` | Yes | Yes | Extensive CAN2004→CAN2010 indicator remap |
| `0x161` | Yes | Yes | Fuel/range data; may inject configured tank capacity |
| `0x168` | Yes | Yes | Fault/status remap and CAN2010 layout adaptation |
| `0x1A1` | Optional source | Yes | Popup/display notifications; can be synthetic (door popup) |
| `0x1A8` | Yes | Yes | Cruise status conversion and/or periodic cruise payload |
| `0x217` | Yes | Yes | Cluster requests pass-through with optional mutation |
| `0x21F` | Yes | Yes | Steering/radio command remap (MODE/SRC/FMUX variants) |
| `0x227` / `0x350` | Yes (`0x1D0`/`0x227`) | Yes | A/C conversion to CAN2010 style |
| `0x228` | Yes (`0x1A8` source or RTC events) | Yes (or CAN0 clock) | Cruise/clock format depends on mode |
| `0x236` | Derived | Yes | Vehicle electrical/network/door status synthesis |
| `0x260` | Yes (personalization source) | Yes | Language/units/comfort settings translation |
| `0x276` | Derived | Yes | Date/time periodic frame |
| `0x361` | Yes | Yes | Feature/menu availability remap |
| `0x3A7`→`0x3E7` | Yes | Yes | Maintenance conversion (days/km + wrench flags) |

---

## 4) Timing Guidance (merged)

Use these intervals as simulator defaults (keep jitter low):

- **~100 ms**: `0x036`, `0x217`, `0x21F`
- **45–90 ms**: `0x0B6`, `0x0E6`
- **~200 ms**: `0x128`, `0x168`, `0x1A1`, `0x1A8`, `0x122`
- **~500 ms**: `0x0F6`, `0x161`, `0x227`, `0x260`, `0x361`, `0x3E7`
- **~1000 ms**: `0x228`, `0x236`, `0x276`, VIN frames (`0x336`, `0x3B6`, `0x2B6`)

---

## 5) Critical Compatibility Rules

### 5.1 `0x0E6` checksum/counter

Byte 7 must include a valid rolling counter/check nibble pair.  
Counter cycles `0x0`..`0xF`; checksum is computed from bytes 0..6 nibbles plus counter.

### 5.2 VIN split encoding

Use ASCII VIN, split exactly:

- `0x336`: chars 1–3
- `0x3B6`: chars 4–9
- `0x2B6`: chars 10–17

### 5.3 Door/popup compatibility

Some head units expect explicit popup behavior on `0x1A1`.  
If no native popup source exists, use synthetic show/hide door popup payloads.

### 5.4 Loop prevention

Frames such as `0x260` and `0x361` are often generated locally on CAN2010 side and should not be blindly echoed back to avoid loops.

---

## 6) Source-Specific Notes (important differences)

### PSA CAN Bridge document emphasizes

- `DataBroker`-driven architecture and typed message handlers
- Detailed C++ struct-level field mapping (`CAN_*_2010.h`)
- Scheduler cadence from `CanMessageHandlerContainer2010`

### Arduino adapter document emphasizes

- Practical firmware behavior flags (`generatePOPups`, `emulateVIN`, `listenCAN2004Language`, etc.)
- Bi-directional suppression/injection logic on both CAN sides
- Startup/init helper frames and telematic interaction behavior

---

## 7) Practical Simulator Bring-Up Sequence

1. Start periodic `0x036`, `0x0F6`, `0x0B6`, `0x236`
2. Add `0x260` + `0x276` (language/units/time)
3. Add baseline `0x128` + `0x168` (all-clear state)
4. Enable `0x0E6` with valid rolling checksum
5. Add VIN split frames (`0x336`, `0x3B6`, `0x2B6`)
6. Add optional popups (`0x1A1`) and comfort features (`0x361`, climate/cruise paths)

---

## 8) Original Detailed References

For full byte/bit-level detail and implementation-specific edge cases, consult:

- `doc/PSACANBridgeCAN2010_Simulator_Development.md`
- `doc/arduino-psa-comfort-can-adapter_Simulator_Development.md`

