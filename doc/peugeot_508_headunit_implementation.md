# Peugeot 508 Headunit Implementation Specification & AI Agent Guide

**Document Version:** 1.0 (Production Specification)  
**Target Platform:** QianFeng (QF) / ROCO Android Head Unit (`QF_Canbus.apk` / `QF_Framework.apk`, Unisoc UIS7862 / SC8581 / QCM6125)  
**Selected Headunit Profile:** **Peugeot 508** (Version: `peugeot_508_11_h` / `peugeot_508_15_h`, Provider: `canprovider_raise_fd` / `canprovider_raise_2e`)  
**Target Vehicle Application:** Peugeot 407 (Comfort CAN 125 kbps) interfaced via custom CANbox / Microcontroller Bridge (STM32 / NUC131 / ESP32)  
**Intended Audience:** Autonomous Implementation AI Agents & Embedded Firmware Engineers  

---

## 1. System Overview & Engineering Rationale

### 1.1 The Core Problem & The Peugeot 508 Solution
In factory QianFeng firmware (`avehicle_config.xml` & `PeugeotConstant.java`), vehicle features are gated strictly by `cartypeKey`, `carversionKey`, and `providerKey`:
1. **The Peugeot 407 Profile Flaw:** Under `cartype_peugeot_407`, the factory firmware omitted Shenzhen Raise (`RZC`). It only lists Hiworld (`5AA5`), Simple (`XP 2E`), and Luzhen (`LZ 2E`). Furthermore, the DSP (JBL amplifier) tile is locked out by default.
2. **The Peugeot 508 Advantage:** Under **Peugeot 508** (`peugeot_508_11_h` / `peugeot_508_15_h`):
   - **Raise Protocol is Native:** Registered as `canprovider_raise_fd` (Raise FD @ 19200 bps) and `canprovider_raise_2e` (Raise 2E @ 38400 bps), driven by `com.qf.vehicle.band.peugeot.parse.rzc.PeugeotDataController`.
   - **DSP / JBL Amplifier Enabled:** `VehicleConfigUtil.setCarDspEnable(context, true)` is **enabled by default** for `peugeot_508_15_h` in `PeugeotConstant.java`.
   - **Central Vehicle Settings Enabled:** `VehicleConfigUtil.setCentralSettingEnable(context, true)` is enabled, granting full access to BSI menus (lighting, locks, parking aids).
   - **Rich Telemetry Set:** Native support for 360/reverse radar, multi-page trip computer, steering wheel buttons, door status, outside temperature, and air conditioning popup overlays.

```
+-----------------------------------------------------------------------------------------+
|                               Android Headunit (QianFeng)                               |
|   Factory Setting: Peugeot 508 (2011-2016 Mid/High or 2015 High)                        |
|   Active CAN Controller: PeugeotDataParser.java (com.qf.vehicle.band.peugeot.parse.rzc)  |
|   Supported Features: DSP (JBL Amp), AC Overlay, Radar, Trip, Doors, Stalk Keys         |
+-----------------------------------------------------------------------------------------+
                                           ^
                                           | UART Interface (TTL 3.3V)
                                           | Primary: Raise FD (0xFD @ 19200 bps)
                                           | Fallback: Raise 2E (0x2E @ 38400 bps)
                                           v
+-----------------------------------------------------------------------------------------+
|                    Custom CANbox / Microcontroller Firmware Bridge                      |
|                      (STM32F103 / Nuvoton NUC131 / ESP32 TWAI)                          |
+-----------------------------------------------------------------------------------------+
                                           ^
                                           | Vehicle CAN Bus (125 kbps, 11-bit IDs)
                                           | Quadlock Connector Part A: Pin 13 (H) & Pin 10 (L)
                                           v
+-----------------------------------------------------------------------------------------+
|                              Peugeot 407 Vehicle CAN Bus                                |
|        ECU / BSI Telemetry: 0x0F6 (Stalk), 0x1D0 (AC), 0x221 (Doors), 0x260 (Radar)     |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Serial Physical & Link Layer Protocols

The firmware bridge connects directly to the **CAN Box UART port** on the Android head unit's main wiring harness.

### 2.1 Profile Selection

| Parameter | Profile A: Raise FD (**Primary / Recommended**) | Profile B: Raise 2E (**Secondary / Fallback**) |
| :--- | :--- | :--- |
| **Headunit Provider Key** | `canprovider_raise_fd` | `canprovider_raise_2e` |
| **Baud Rate** | **`19200` bps** | **`38400` bps** |
| **Data / Parity / Stop** | 8N1 (8 Data bits, No parity, 1 Stop bit) | 8N1 (8 Data bits, No parity, 1 Stop bit) |
| **Sync Byte (Header)** | `0xFD` (Accept `0xDF` on RX) | `0x2E` |
| **Length Definition** | $\text{LEN} = \text{PayloadLength } (N) + 3$ | $\text{LEN} = \text{PayloadLength } (N)$ |
| **Total Wire Frame Size** | $\text{TotalBytes} = \text{LEN} + 1 = N + 4$ | $\text{TotalBytes} = N + 4$ |
| **Checksum Algorithm** | Additive sum modulo 256 over `LEN`..`Payload` | Bitwise inverted sum `(~sum) & 0xFF` |

---

### 2.2 Wire Framing & Checksum Algorithms

#### Profile A: Raise FD (`0xFD`) Framing
```
+------------+------------+------------+-------------------------+------------+
| Byte 0     | Byte 1     | Byte 2     | Byte 3 .. (N + 2)       | Byte N + 3 |
+------------+------------+------------+-------------------------+------------+
| Sync Byte  | Length     | Command ID | Payload Data            | Checksum   |
|   0xFD     | LEN (N + 3)|   CMD_ID   | DATA[0] ... DATA[N - 1] |    CSUM    |
+------------+------------+------------+-------------------------+------------+
```
$$\text{CSUM} = \left(\text{LEN} + \text{CMD\_ID} + \sum_{i=0}^{N-1} \text{DATA}[i]\right) \ \& \ \text{0xFF}$$

**C Implementation (Profile A):**
```c
uint8_t calculate_csum_raise_fd(uint8_t len, uint8_t cmd_id, const uint8_t *payload, uint8_t payload_len) {
    uint8_t sum = len + cmd_id;
    for (uint8_t i = 0; i < payload_len; i++) {
        sum += payload[i];
    }
    return sum;
}

void send_raise_fd_packet(uint8_t cmd_id, const uint8_t *payload, uint8_t payload_len) {
    uint8_t frame[64];
    uint8_t len = payload_len + 3;
    frame[0] = 0xFD;
    frame[1] = len;
    frame[2] = cmd_id;
    if (payload_len > 0 && payload != NULL) {
        memcpy(&frame[3], payload, payload_len);
    }
    frame[3 + payload_len] = calculate_csum_raise_fd(len, cmd_id, payload, payload_len);
    uart_write_bytes(frame, len + 1);
}
```

#### Profile B: Raise 2E (`0x2E`) Framing
```
+------------+------------+------------+-------------------------+------------+
| Byte 0     | Byte 1     | Byte 2     | Byte 3 .. (N + 2)       | Byte N + 3 |
+------------+------------+------------+-------------------------+------------+
| Sync Byte  | Command ID | Length     | Payload Data            | Checksum   |
|   0x2E     |   CMD_ID   |  LEN (N)   | DATA[0] ... DATA[N - 1] |    CSUM    |
+------------+------------+------------+-------------------------+------------+
```
$$\text{CSUM} = \left(\sim \left(\text{CMD\_ID} + \text{LEN} + \sum_{i=0}^{N-1} \text{DATA}[i]\right)\right) \ \& \ \text{0xFF} = \left(\left(\text{CMD\_ID} + \text{LEN} + \sum_{i=0}^{N-1} \text{DATA}[i]\right) \oplus \text{0xFF}\right) \ \& \ \text{0xFF}$$

**C Implementation (Profile B):**
```c
uint8_t calculate_csum_raise_2e(uint8_t cmd_id, uint8_t len, const uint8_t *payload, uint8_t payload_len) {
    uint8_t sum = cmd_id + len;
    for (uint8_t i = 0; i < payload_len; i++) {
        sum += payload[i];
    }
    return (uint8_t)(sum ^ 0xFF);
}

void send_raise_2e_packet(uint8_t cmd_id, const uint8_t *payload, uint8_t payload_len) {
    uint8_t frame[64];
    frame[0] = 0x2E;
    frame[1] = cmd_id;
    frame[2] = payload_len;
    if (payload_len > 0 && payload != NULL) {
        memcpy(&frame[3], payload, payload_len);
    }
    frame[3 + payload_len] = calculate_csum_raise_2e(cmd_id, payload_len, payload, payload_len);
    uart_write_bytes(frame, payload_len + 4);
}
```

---

## 3. Master Command Implementation Catalog

Below is the exhaustive catalog of all commands that the AI agent must implement for the Peugeot 508 profile, verified against `PeugeotDataParser.java` and `PeugeotDataDefine.java`:

| Command ID | Hex | Direction | Priority | Description & Purpose | Transmission Policy |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `SteeringWheelKey` | `0x02` | CANbox $\to$ HU | **P0** | Steering column stalk buttons & rotary wheels | Event-driven (Press + Release) |
| `CameraState` | `0x40` | CANbox $\to$ HU | **P0** | Direct reversing camera screen switch trigger | Event-driven (on Reverse gear toggle) |
| `DoorWindowCentralState`| `0x38` | CANbox $\to$ HU | **P0** | Doors, trunk, hood, reverse gear, handbrake, lights | 500 ms periodic + on change |
| `AcState` | `0x21` | CANbox $\to$ HU | **P1** | Dual-zone AC status, fan speed, vents, temps | 500 ms periodic + on change |
| `DspStatePopUp` | `0x56` | CANbox $\to$ HU | **P1** | JBL Sound Amplifier status (Volume, EQ, Balance) | 1000 ms periodic + on change |
| `RearRadarState` | `0x32` | CANbox $\to$ HU | **P1** | Ultrasonic parking sensors (6-channel / 8-channel) | 100 ms (active in reverse/low speed) |
| `EcuInfoPage0` | `0x33` | CANbox $\to$ HU | **P2** | Instant fuel economy, range to empty, destination | 1000 ms periodic |
| `EcuInfoPage1` | `0x34` | CANbox $\to$ HU | **P2** | Trip 1 average fuel, average speed, distance | 1000 ms periodic |
| `EcuInfoPage2` | `0x35` | CANbox $\to$ HU | **P2** | Trip 2 average fuel, average speed, distance | 1000 ms periodic |
| `OutTemp` | `0x36` | CANbox $\to$ HU | **P2** | Outside ambient temperature ($^\circ\text{C}$ sign-magnitude) | 2000 ms periodic |
| `SteeringWheelAngle` | `0x29` | CANbox $\to$ HU | **P2** | Steering wheel trajectory angle ($\pm 540^\circ$) | 50 ms periodic (when wheel turns) |
| `CanVersionInfo` | `0x7F` | CANbox $\to$ HU | **P3** | CANbox firmware identifier string | On startup / on poll `0x8F` |
| `ForwardAcSetting` | `0x8A` | HU $\to$ CANbox | **P1** | Touchscreen AC button presses from user | Async incoming from HU |
| `ForwardDspState` | `0xC5` | HU $\to$ CANbox | **P1** | DSP equalizer and fader sliders from user | Async incoming from HU |
| `ForwardCentralSetting`| `0x80` | HU $\to$ CANbox | **P2** | Vehicle configuration menu options (DRL, EPB, etc.)| Async incoming from HU |
| `ForwardTimeSetting` | `0xA6` | HU $\to$ CANbox | **P2** | System clock / time synchronization from Android | Async incoming from HU |
| `ForwardHostQuery` | `0x8F` | HU $\to$ CANbox | **P2** | Status polling query requesting immediate packet | Async incoming from HU |
| `ForwardEcuInfo` | `0x82` | HU $\to$ CANbox | **P3** | Trip 1 / Trip 2 reset command from user | Async incoming from HU |

---

## 4. Inbound Telemetry Specifications (CANbox $\to$ Head Unit)

### 4.1 Steering Wheel & Stalk Keys (`Cmd 0x02`)
- **Payload Length ($N$):** 2 bytes
- **Wire Format (Raise FD):** `FD 05 02 [KeyCode] [State] [CSUM]`
- **Fields:**
  - `KeyCode`: Raw button identifier (see map below).
  - `State`: `0x01` = Pressed / Down, `0x00` = Released / Up.

#### Peugeot 407 CAN (`0x0F6`) to Headunit Keycode Translation Matrix:
The headunit maps `KeyCode` to Android functions via `PeugeotDataDefine.java`:

| Physical Stalk / Button on 407 | PSA CAN `0x0F6` Byte/Bit | Raise Wire KeyCode (`Byte 0`) | `PeugeotDataDefine` Internal Code | Resulting Android Action |
| :--- | :--- | :---: | :---: | :--- |
| **Volume Up ($VOL+$)** | Byte 0 Bit 3 (`0x08`) | **`0x14`** (20) | `1` | `VolumeIncrease` |
| **Volume Down ($VOL-$)** | Byte 0 Bit 2 (`0x04`) | **`0x15`** (21) | `2` | `VolumeDecrease` |
| **Mute (Vol+ & Vol- together)**| Byte 0 Bits 2+3 (`0x0C`)| **`0x16`** (22) | `6` | `Mute` toggle |
| **Seek Next ($>>$)** | Byte 1 Bit 3 (`0x08`) | **`0x12`** (18) | `28` | `SeekIncrease` / Next Track |
| **Seek Prev ($<<$)** | Byte 1 Bit 2 (`0x04`) | **`0x13`** (19) | `29` | `SeekDecrease` / Prev Track |
| **Source / Mode Stalk Button** | Byte 0 Bit 0 (`0x01`) | **`0x11`** (17) | `7` | `Src` (Radio $\to$ USB $\to$ BT) |
| **Scroll Wheel Down** | Byte 1 Wheel counter $\downarrow$| **`0x23`** (35) | `4` | `Previous` Track / Preset Down |
| **Scroll Wheel Up** | Byte 1 Wheel counter $\uparrow$  | **`0x24`** (36) | `3` | `Next` Track / Preset Up |
| **ESC Button** | Byte 0 Bit 5 (`0x20`) | **`0x08`** (8) | `12` | `Back` |
| **Menu Button** | Byte 0 Bit 6 (`0x40`) | **`0x02`** (2) | `35` | `Menu` |
| **OK / Confirm Button** | Byte 0 Bit 4 (`0x10`) | **`0x07`** (7) | `23` | `Confirm` / Play-Pause |
| **Dark Button** | Byte 0 Bit 7 (`0x80`) | **`0x54`** (84) | `9` | Screen Off / Standby |

> [!IMPORTANT]
> **Transmission Protocol for Buttons:**
> Always transmit an initial packet with `State = 0x01` (Pressed), followed by a second packet with `State = 0x00` (Released) after a **50 ms to 100 ms delay**. If the release packet is not sent, Android will interpret it as a stuck long-press.

---

### 4.2 Climate / Air Conditioning Status (`Cmd 0x21`)
Triggers the native Peugeot floating climate dialog overlay.
- **Payload Length ($N$):** 7 bytes
- **Wire Format (Raise FD):** `FD 0A 21 [D0] [D1] [D2] [D3] [D4] [D5] [D6] [CSUM]`

#### Byte Breakdown:
- **Byte 0 (`D0`) - Master System Flags:**
  - `Bit 7`: Power ($1 = \text{ON}, 0 = \text{OFF}$)
  - `Bit 6`: A/C Compressor ($1 = \text{Compressor ON}, 0 = \text{OFF}$)
  - `Bit 5`: Air Recirculation ($1 = \text{Internal Recirculation}, 0 = \text{Fresh Air}$)
  - `Bit 4`: AQS (Air Quality Sensor) ($1 = \text{Active}$)
  - `Bit 3`: AUTO Mode ($1 = \text{Full Auto}, 0 = \text{Manual}$)
  - `Bit 2`: DUAL Zone ($1 = \text{Dual active}, 0 = \text{Mono active}$)
  - `Bit 0`: Rear Window Defrost / Demist ($1 = \text{Heating ON}$)
- **Byte 1 (`D1`) - Vents & Blower Speed:**
  - `Bit 7`: Wind Up (Windshield defogger vents)
  - `Bit 6`: Wind Parallel (Face/Dashboard center vents)
  - `Bit 5`: Wind Down (Footwell floor vents)
  - `Bits 3..0`: Blower Fan Speed Level ($0 = \text{Off}$, $1..8 = \text{Level } 1 \dots 8$).  
    *Formula in Android:* $\text{UI Speed} = (\text{raw} \& 0\text{x0F}) - 1$. If raw is `0x01`, UI shows Speed 0/Auto; if `0x09`, UI shows Speed 8.
- **Byte 2 (`D2`) - Driver (Left) Temperature:**
  - `0x00`: Displays `"Low"`
  - `0xFF` (`-1`): Displays `"High"`
  - Other: Raw byte $= \text{Temperature in } ^\circ\text{C} \times 2$.  
    *Examples:* $21.5^\circ\text{C} = 43 = \text{0x2B}$; $18.0^\circ\text{C} = 36 = \text{0x24}$.
- **Byte 3 (`D3`) - Passenger (Right) Temperature:**
  - Identical encoding to Driver Temperature ($0x00=\text{Low}, 0xFF=\text{High}, \text{raw} = ^\circ\text{C} \times 2$).
- **Byte 4 (`D4`) - Max Modes & Units:**
  - `Bit 7`: Front Window Max Defog / Defrost Clear ($1 = \text{Active}$)
  - `Bit 3`: A/C Max ($1 = \text{Fast Cool Active}$)
  - `Bit 0`: Temperature Unit ($0 = ^\circ\text{C}, 1 = ^\circ\text{F}$)
- **Byte 5 (`D5`):**
  - `Bit 7`: Rear Air Conditioning Power ($1 = \text{ON}$)
- **Byte 6 (`D6`) - Airflow Profile & Peugeot 407 Right Zone Vents:**
  - `Bits 7..6`: Auto Blower Intensity ($0 = \text{Soft / Low}, 1 = \text{Normal / Med}, 2 = \text{Fast / High}$)
  - `Bit 7`: Right Wind Up (Peugeot 407 independent right vent)
  - `Bit 6`: Right Wind Parallel
  - `Bit 5`: Right Wind Down

---

### 4.3 Parking Assist Ultrasonic Radar (`Cmd 0x32`)
Pops up the graphical 360 obstacle proximity display.
- **Payload Length ($N$):** 7 bytes
- **Wire Format (Raise FD):** `FD 0A 32 [Status] [RL] [RM] [RR] [FL] [FM] [FR] [CSUM]`

#### Byte Breakdown:
- **Byte 0 (`Status`):**
  - `0x02`: Radar active and display window visible (Standard active state).
  - `0x00` / `0x01`: Inactive or background muted.
- **Bytes 1..3:** Rear Ultrasonic Distances:
  - `Byte 1`: Rear Left (`RL`)
  - `Byte 2`: Rear Center / Mid (`RM`)
  - `Byte 3`: Rear Right (`RR`)
- **Bytes 4..6:** Front Ultrasonic Distances:
  - `Byte 4`: Front Left (`FL`)
  - `Byte 5`: Front Center / Mid (`FM`)
  - `Byte 6`: Front Right (`FR`)

#### Distance Level Mapping:
In Raise FD protocol, distance values range **`0` to `5`**:
- `0x00`: **Zone 5 (Critical Stop)** — 10 bars / Flashing Red + continuous beep.
- `0x01`: **Zone 4 (Very Close)** — 7 bars / Red.
- `0x02`: **Zone 3 (Close)** — 5 bars / Orange.
- `0x03`: **Zone 2 (Approaching)** — 3 bars / Yellow.
- `0x04`: **Zone 1 (Far)** — 1 bar / Green.
- `0x05`: **Clear / No obstacle** — 0 bars (Inactive).

#### Conversion from Peugeot 407 CAN Radar (CAN `0x260` / `0x270`):
PSA CAN transmits obstacle levels from $0$ (no obstacle) to $7$ (closest obstacle). Convert with:
```c
uint8_t psa_radar_to_raise(uint8_t psa_val) {
    switch (psa_val) {
        case 7: return 0x00; // Critical (closest)
        case 6: return 0x01;
        case 5: return 0x02;
        case 4: return 0x03;
        case 3:
        case 2:
        case 1: return 0x04; // Far
        case 0:
        default: return 0x05; // Clear
    }
}
```

---

### 4.4 Doors, Vehicle Status & Reversing Camera (`Cmd 0x38` & `Cmd 0x40`)

#### Vehicle Status & Doors (`Cmd 0x38`):
- **Payload Length ($N$):** 8 bytes
- **Wire Format (Raise FD):** `FD 0B 38 [D0] [D1] [D2] [D3] [D4] [D5] [D6] [D7] [CSUM]`
- **Byte 0 (`D0`) - Doors & Hatches:**
  - `Bit 7`: Front Left Door ($1 = \text{Open}, 0 = \text{Closed}$)
  - `Bit 6`: Front Right Door
  - `Bit 5`: Rear Left Door
  - `Bit 4`: Rear Right Door
  - `Bit 3`: Trunk / Tailgate ($1 = \text{Open}$)
  - `Bit 2`: Engine Bonnet / Hood ($1 = \text{Open}$)
  - `Bit 0`: Warning Beep trigger
- **Byte 1 (`D1`) - Brakes & Seatbelts:**
  - `Bit 7`: Handbrake / Parking Brake ($1 = \text{Engaged}$)
  - `Bit 6`: Driver Seatbelt ($1 = \text{Unbuckled}$)
  - `Bit 3`: Passenger Seatbelt ($1 = \text{Unbuckled}$)
- **Byte 3 (`D3`) - Gear & Illumination:**
  - `Bit 2`: **Reverse Gear Active** ($1 = \text{Reverse Engaged}, 0 = \text{Neutral/Forward}$)
  - `Bit 1`: Parking Brake active
  - `Bit 0`: Side Markers / Small Lights ($1 = \text{Illumination ON}$)
- **Byte 4 (`D4`):**
  - `Bit 0`: Low fuel warning indicator ($1 = \text{Low Fuel}$)

#### Direct Camera Switch Trigger (`Cmd 0x40`):
- **Payload Length ($N$):** 1 byte
- **Wire Format (Raise FD):** `FD 04 40 [State] [CSUM]`
  - `State = 0x80`: Camera Active (instantly forces headunit to rear camera view).
  - `State = 0x00`: Camera Inactive (returns headunit to previous app).

---

### 4.5 Multi-Page Trip Computer & Outside Temperature

#### Page 0: Instant Telemetry (`Cmd 0x33`, Payload = 9 bytes):
`FD 0C 33 [InstFuel_H] [InstFuel_L] [Range_H] [Range_L] [Dest_H] [Dest_L] [Hours] [Min] [Sec] [CSUM]`
- **Bytes 0..1 (`InstFuel`):** Big-Endian unsigned integer. Formula: $\text{L/100km} = \frac{\text{raw}}{10.0}$. If $> 3000$, displays `"--.-"`.
- **Bytes 2..3 (`Range`):** Big-Endian unsigned integer in km. If $> 2000$, displays `"----"`.
- **Bytes 4..5 (`Dest`):** Distance to destination in km.
- **Bytes 6..8:** Engine Start-Stop / Running time elapsed (`[Hours] [Minutes] [Seconds]`).

#### Page 1: Trip 1 (`Cmd 0x34`, Payload = 6 bytes):
`FD 09 34 [AvgFuel_H] [AvgFuel_L] [AvgSpd_H] [AvgSpd_L] [Dist_H] [Dist_L] [CSUM]`
- **Bytes 0..1 (`AvgFuel`):** Big-Endian unsigned integer $= \text{L/100km} \times 10$.
- **Bytes 2..3 (`AvgSpeed`):** Big-Endian unsigned integer $= \text{km/h}$.
- **Bytes 4..5 (`TripDistance`):** Big-Endian unsigned integer $= \text{km}$.

#### Page 2: Trip 2 (`Cmd 0x35`, Payload = 6 bytes):
- Exactly identical byte layout and formulas as Page 1 (`Cmd 0x34`).

#### Outside Ambient Temperature (`Cmd 0x36`, Payload = 1 byte):
`FD 04 36 [TempByte] [CSUM]`
- **`TempByte` Format:** Sign-Magnitude format with Bit 7 as negative sign flag:
  - Bit 7 = `0`: Positive temperature ($\text{Temp} = +\text{Byte}\ ^\circ\text{C}$). E.g., $+22^\circ\text{C} = \text{0x16}$.
  - Bit 7 = `1`: Negative temperature ($\text{Temp} = -(\text{Byte} \& \text{0x7F})\ ^\circ\text{C}$). E.g., $-5^\circ\text{C} = 0\text{x80} | 5 = \text{0x85}$.
- **C Implementation:**
  ```c
  uint8_t encode_outside_temp(int8_t temp_celsius) {
      if (temp_celsius < 0) {
          return (uint8_t)(0x80 | ((-temp_celsius) & 0x7F));
      }
      return (uint8_t)(temp_celsius & 0x7F);
  }
  ```

---

### 4.6 OEM Sound Amplifier & JBL DSP Telemetry (`Cmd 0x56`)
Controls and synchronizes the native JBL Amplifier tile (unlocked by the Peugeot 508 profile).
- **Payload Length ($N$):** 8 bytes
- **Wire Format (Raise FD):** `FD 0B 56 00 [Bass] [Treble] [Balance] [Fader] [Preset] [Loudness_Speed] [Volume] [CSUM]`

#### Byte Breakdown:
- **Byte 0:** Reserved (`0x00`).
- **Byte 1 (`Bass`):** Level $0 \dots 14$ (Neutral Center = 7).
- **Byte 2 (`Treble`):** Level $0 \dots 14$ (Neutral Center = 7).
- **Byte 3 (`Balance`):** Level $0 \dots 14$ ($0 = \text{Full Left}$, $7 = \text{Center}$, $14 = \text{Full Right}$).
- **Byte 4 (`Fader`):** Level $0 \dots 14$ ($0 = \text{Full Rear}$, $7 = \text{Center}$, $14 = \text{Full Front}$).
- **Byte 5 (`Preset`):** Equalizer preset:
  - `0`: Custom / Manual
  - `1`: Pop
  - `2`: Classic
  - `3`: Electronic
  - `4`: Jazz
  - `5`: Vocal
- **Byte 6:**
  - `Bit 4`: Loudness ($1 = \text{ON}, 0 = \text{OFF}$)
  - `Bits 3..0`: Speed-dependent volume compensation level ($0..3$)
- **Byte 7 (`Volume`):** Master amplifier volume ($0 \dots 30$).

---

### 4.7 Steering Wheel Angle Trajectory (`Cmd 0x29`)
Feeds dynamic reverse camera parking trajectory guidelines.
- **Payload Length ($N$):** 2 bytes
- **Wire Format (Raise FD):** `FD 05 29 [Angle_L] [Angle_H] [CSUM]`
- **Value Format:** Signed 16-bit integer (`int16_t`) Little-Endian:
  - `0x0000`: Steering Centered ($0^\circ$)
  - Positive ($>0$): Steering Wheel turned Right ($+1^\circ$ to $+540^\circ$)
  - Negative ($<0$): Steering Wheel turned Left (two's complement, $-1^\circ$ to $-540^\circ$)

---

### 4.8 CANbox Version Identification (`Cmd 0x7F`)
- **Payload Length ($N$):** String length (e.g. 14 bytes)
- **Wire Format (Raise FD):** `FD 11 7F [ASCII Version String] [CSUM]`
  - Example Payload: `"RZC-PSA-508-V1"`

---

## 5. Outbound Control Specifications (Head Unit $\to$ CANbox)

When the user touches controls on the Android screen, `PeugeotDataParser.java` sends command packets down to the CANbox.

### 5.1 Remote Climate Control Commands (`Cmd 0x8A`)
Sent by `PeugeotDataParser.forwardAcState()`:
- **Wire Format:** `FD 05 8A [SubCmd] [Value] [CSUM]`

| SubCmd | Target Feature | Parameter `Value` | Action Required by CANbox Bridge |
| :---: | :--- | :--- | :--- |
| `0x01` | AUTO Mode | `0x00` = Off, `0x01` = Auto Active | Forward to PSA CAN `0x1E0` / update state |
| `0x02` | A/C Compressor | `0x00` = Compressor Off, `0x01` = A/C On | Forward to PSA CAN `0x1E0` / update state |
| `0x03` | A/C Max | `0x00` = Off, `0x01` = A/C Max On | Trigger max blower + compressor |
| `0x04` | Driver Temp Adjust | `0x01` = Temp Up ($+0.5^\circ\text{C}$), `0x02` = Temp Down ($-0.5^\circ\text{C}$) | Adjust driver setpoint $\pm 1$ step |
| `0x05` | Passenger Temp Adjust| `0x01` = Temp Up ($+0.5^\circ\text{C}$), `0x02` = Temp Down ($-0.5^\circ\text{C}$) | Adjust passenger setpoint $\pm 1$ step |
| `0x06` | Wind Parallel (Face) | `0x00` = Close, `0x01` = Open | Set dashboard air distribution |
| `0x07` | Wind Up (Windshield) | `0x00` = Close, `0x01` = Open | Set windshield defrost vents |
| `0x08` | Wind Down (Floor) | `0x00` = Close, `0x01` = Open | Set footwell floor vents |
| `0x09` | Air Intensity Profile| `0x00` = Soft, `0x01` = Normal, `0x02` = Fast | Set auto blower curve |
| `0x0A` | Fan Speed Direct | `0x01` = Speed Up, `0x02` = Speed Down | Increment/decrement fan speed $0..8$ |
| `0x0B` | Dual / Mono Mode | `0x00` = Dual active, `0x01` = Mono active | Sync left/right setpoints |
| `0x0C` | HVAC System Power | `0x00` = Power Off, `0x01` = Power On | Master climate power switch |
| `0x0D` | AQS (Air Quality) | `0x00` = Off, `0x01` = Auto Recirc | Air quality sensor toggle |
| `0x0E` | Rear Window Defrost | `0x01` = Toggle rear heating wire | Rear window defrost switch |
| `0x11` | Front Max Defog | `0x00` = Off, `0x01` = Max Clear Active | Front windshield rapid defog |

---

### 5.2 DSP / JBL Amplifier Slider Adjustments (`Cmd 0xC5`)
Sent by `PeugeotDataParser.forwardDspState()` whenever the user drags audio sliders:
- **Wire Format:** `FD 0B C5 [D0] [D1] [D2] [D3] [D4] [D5] [D6] 0x01 [CSUM]`

#### Byte Breakdown:
- **Byte 0 (`D0`):** `Fader` ($0 \dots 14$)
- **Byte 1 (`D1`):** `Balance` ($0 \dots 14$)
- **Byte 2 (`D2`):** `Bass` ($0 \dots 14$)
- **Byte 3 (`D3`):** `Treble` ($0 \dots 14$)
- **Byte 4 (`D4`):** `Middle` ($0 \dots 14$)
- **Byte 5 (`D5`):** `(DriverSoundField << 7) + (VolChangeBySpeed << 6) + SoundEffect`
- **Byte 6 (`D6`):** `(Punch << 4) + DspPosition`
- **Byte 7 (`D7`):** Constant `0x01`.

> [!NOTE]
> **Action on Receiving `0xC5`:**
> The CANbox bridge should:
> 1. Store the new EQ/volume levels into its local `dsp_state` memory.
> 2. Translate these levels into PSA CAN frames (`0x1A0` / `0x280`) addressed to the Peugeot JBL amplifier.
> 3. Transmit an updated status packet `Cmd 0x56` back to Android within 100 ms to confirm synchronization.

---

### 5.3 Vehicle Central Settings Menu (`Cmd 0x80`)
Sent by `PeugeotDataParser.forwardCentralState()`:
- **Wire Format:** `FD 05 80 [SettingType] [Value] [CSUM]`

| SettingType | Feature Name | Allowed `Value` |
| :---: | :--- | :--- |
| `0x01` | Parking Assist System | `0x00` = Off, `0x01` = On |
| `0x02` | Rear Wiper in Reverse | `0x00` = Off, `0x01` = On |
| `0x03` | Daytime Running Lights (DRL) | `0x00` = Off, `0x01` = On |
| `0x05` | Ambient Interior Lighting | `0x00` = Off, `0x01`–`0x05` = Brightness Level |
| `0x06` | Parking Distance Warning Sound | `0x00` = Muted, `0x01` = Active |
| `0x07` | Follow-Me-Home Headlight Delay| `0x00` = Off, `0x01` = 15s, `0x02` = 30s, `0x03` = 60s |
| `0x08` | Welcome Lighting Delay | `0x00` = Off, `0x01` = 15s, `0x02` = 30s, `0x03` = 60s |
| `0x09` | Audio Warning Sound Theme | `1` = Classic, `2` = Crystal, `3` = Urban, `4` = Fantasy |
| `0x0A` | Fuel Consumption Unit | `0x00` = L/100KM, `0x01` = KM/L, `0x02` = MPG |
| `0x0B` | System Language | `0x00` = English, `0x01` = Chinese, `0x02` = French, etc. |
| `0x0C` | Blind Spot Monitoring (SAM) | `0x00` = Disabled, `0x01` = Enabled |
| `0x0D` | Auto Start-Stop System | `0x00` = Enabled, `0x01` = Disabled |
| `0x0E` | Welcome Driver Seat Comfort | `0x00` = Off, `0x01` = On |
| `0x0F` | Selective Door Unlock Mode | `0x00` = Driver Door Only, `0x01` = All Doors |
| `0x10` | TPMS Sensor Re-calibration | `0x01` = Trigger calibration routine |
| `0x14` | Temperature Unit | `0x00` = Celsius ($^\circ\text{C}$), `0x01` = Fahrenheit ($^\circ\text{F}$) |

---

### 5.4 System Clock Synchronization (`Cmd 0xA6`)
Sent by `PeugeotDataParser.forwardSystemTime()` whenever Android system time changes:
- **Wire Format:** `FD 08 A6 [Year] [Month] [Day] [Hour] [Minute] [CSUM]`
- **Fields:**
  - `Year`: $\text{Current Year} - 2000$ (e.g. $2026 \implies 26 = \text{0x1A}$).
  - `Month`: $1 \dots 12$
  - `Day`: $1 \dots 31$
  - `Hour`: $0 \dots 23$ (24-hour format)
  - `Minute`: $0 \dots 59$

---

### 5.5 Status Polling Query (`Cmd 0x8F`)
Sent by Android to request an immediate refresh of a specific telemetry packet:
- **Wire Format:** `FD 04 8F [Target_CMD_ID] [CSUM]`
- **Examples:**
  - `FD 04 8F 21 CB`: Polling Climate Status $\implies$ CANbox must reply with `0x21`.
  - `FD 04 8F 38 C2`: Polling Doors & Vehicle Status $\implies$ CANbox must reply with `0x38`.
  - `FD 04 8F 56 A4`: Polling DSP Status $\implies$ CANbox must reply with `0x56`.
  - `FD 04 8F 7F 7D`: Polling Version Info $\implies$ CANbox must reply with `0x7F`.

---

## 6. Vehicle CAN Bus Mapping (Peugeot 407 $\longleftrightarrow$ Serial)

### 6.1 Physical CAN Interface (Quadlock Part A)
```
          Peugeot 407 Quadlock Connector (Back of OEM Radio)
     +-------------------------------------------------------+
     |  [1]   [2]   [3]   [4]   [5]   [6]   [7]   [8]        |
     |  [9]  [10]  [11]  [12]  [13]  [14]  [15]  [16]        |
     +-------------------------------------------------------+
               |     |     |     |           |
             CAN-L  REM   GND   CAN-H       +12V
             (P10)  (P11) (P12) (P13)       (P15)
```
- **Pin 10:** CAN-L (PSA Comfort CAN, 125 kbps)
- **Pin 13:** CAN-H (PSA Comfort CAN, 125 kbps)
- **Pin 11:** Remote Amplifier Turn-on (Active +12V trigger to turn on JBL amp)
- **Pin 12:** Ground (GND)
- **Pin 15:** Battery +12V Constant

### 6.2 PSA Comfort CAN Message Translation Rules

| PSA CAN ID | CAN DLC | Target Field | Transformation into Serial Packet |
| :---: | :---: | :--- | :--- |
| **`0x0F6`** | 8 | Stalk Buttons & Scroll Wheel | Map Byte 0/1 bits to KeyCode, send `0x02` Press + Release frames. |
| **`0x036`** | 8 | Reverse Gear & Vehicle Speed | Byte 4 Bit 0 is Reverse Gear $\implies$ Update `0x38` Byte 3 Bit 2 and fire `0x40` (`0x80`/`0x00`). |
| **`0x1D0`** | 8 | BSI Climate Controls | Left/right temperatures, blower speed, mono flag $\implies$ Map to `0x21`. |
| **`0x1E0`** | 8 | AC Compressor & Vents | AC compressor flag, defogger flags, vent direction $\implies$ Map to `0x21`. |
| **`0x260`** | 8 | Rear Parking Sensors | 4 rear obstacle zones ($0..7$) $\implies$ Scale to $0..5$, pack into `0x32`. |
| **`0x270`** | 8 | Front Parking Sensors | 4 front obstacle zones ($0..7$) $\implies$ Scale to $0..5$, pack into `0x32`. |
| **`0x221`** | 8 | BSI Door & Hatch Status | Door switches (LF, RF, LR, RR, trunk, bonnet) $\implies$ Map directly to `0x38` Byte 0. |
| **`0x165`** | 8 | Trip Computer Instant | Instant fuel consumption & range $\implies$ Map to `0x33`. |
| **`0x1A5`** | 8 | Trip Computer Accumulators | Trip 1 & Trip 2 average consumption & distance $\implies$ Map to `0x34` & `0x35`. |
| **`0x1A0`** | 8 | JBL Amplifier Status | Volume level, fader, balance from amp $\implies$ Map to `0x56`. |

---

## 7. Firmware Architecture & Implementation Guide for AI Agent

### 7.1 State Machine Design

```
+-----------------------------------------------------------------------------------------+
|                                    Firmware Main Loop                                   |
+-----------------------------------------------------------------------------------------+
       |                                       |                                   |
       v                                       v                                   v
[1. CAN Receive ISR]                 [2. Periodic TX Timers]              [3. UART RX Parser]
  - Read 125k CAN msg                  - 50ms:  Steering Angle (0x29)       - State 0: Wait 0xFD
  - Decode 0x0F6 (Keys)                - 100ms: Radar in Rev (0x32)         - State 1: Read LEN
  - Decode 0x221 (Doors)               - 500ms: Doors/State (0x38)          - State 2: Read CMD
  - Decode 0x1D0/0x1E0 (AC)            - 500ms: Climate (0x21)              - State 3: Read Payload
  - Decode 0x260/0x270 (Radar)         - 1000ms: Trip 0/1/2 (0x33-0x35)     - State 4: Checksum
  - Update `car_state` struct          - 1000ms: DSP Status (0x56)          - Dispatch:
                                       - 2000ms: Outside Temp (0x36)          * 0x8A -> AC write
                                                                              * 0xC5 -> DSP write
                                                                              * 0x8F -> Reply query
```

### 7.2 Core C Data Structures

```c
#pragma pack(push, 1)

typedef struct {
    // Doors & Hatches
    uint8_t door_lf : 1;
    uint8_t door_rf : 1;
    uint8_t door_lr : 1;
    uint8_t door_rr : 1;
    uint8_t trunk   : 1;
    uint8_t hood    : 1;
    
    // Status
    uint8_t reverse_gear : 1;
    uint8_t handbrake    : 1;
    uint8_t side_lights  : 1;
    uint8_t seatbelt_driver : 1;
    
    // Telemetry
    int8_t  outside_temp_c;
    int16_t steering_angle;
    
    // Radar (0=Critical, 5=Clear)
    uint8_t radar_rl;
    uint8_t radar_rm;
    uint8_t radar_rr;
    uint8_t radar_fl;
    uint8_t radar_fm;
    uint8_t radar_fr;
} vehicle_telemetry_t;

typedef struct {
    uint8_t power       : 1;
    uint8_t ac_on       : 1;
    uint8_t recirc      : 1;
    uint8_t auto_mode   : 1;
    uint8_t dual_mode   : 1;
    uint8_t rear_defrost: 1;
    uint8_t front_defog : 1;
    uint8_t ac_max      : 1;
    
    uint8_t wind_up     : 1;
    uint8_t wind_mid    : 1;
    uint8_t wind_down   : 1;
    uint8_t fan_speed;      // 0..8
    
    uint8_t temp_left_c2;   // Celsius * 2
    uint8_t temp_right_c2;  // Celsius * 2
    uint8_t blower_profile; // 0=Soft, 1=Normal, 2=Fast
} vehicle_climate_t;

typedef struct {
    uint8_t volume;   // 0..30
    uint8_t bass;     // 0..14 (Center 7)
    uint8_t treble;   // 0..14 (Center 7)
    uint8_t balance;  // 0..14 (Center 7)
    uint8_t fader;    // 0..14 (Center 7)
    uint8_t preset;   // 0..5
    uint8_t loudness; // 0..1
} vehicle_dsp_t;

#pragma pack(pop)
```

### 7.3 UART Parser Implementation

```c
typedef enum {
    RX_STATE_SYNC = 0,
    RX_STATE_LEN,
    RX_STATE_CMD,
    RX_STATE_PAYLOAD,
    RX_STATE_CHECKSUM
} rx_parser_state_t;

void process_incoming_uart_byte(uint8_t byte) {
    static rx_parser_state_t state = RX_STATE_SYNC;
    static uint8_t len = 0;
    static uint8_t cmd = 0;
    static uint8_t payload[32];
    static uint8_t payload_idx = 0;
    static uint8_t calc_csum = 0;

    switch (state) {
        case RX_STATE_SYNC:
            if (byte == 0xFD || byte == 0xDF) {
                state = RX_STATE_LEN;
            }
            break;

        case RX_STATE_LEN:
            len = byte;
            if (len >= 3 && (len - 3) <= sizeof(payload)) {
                calc_csum = len;
                state = RX_STATE_CMD;
            } else {
                state = RX_STATE_SYNC; // Invalid length, re-sync
            }
            break;

        case RX_STATE_CMD:
            cmd = byte;
            calc_csum += cmd;
            payload_idx = 0;
            if (len > 3) {
                state = RX_STATE_PAYLOAD;
            } else {
                state = RX_STATE_CHECKSUM;
            }
            break;

        case RX_STATE_PAYLOAD:
            payload[payload_idx++] = byte;
            calc_csum += byte;
            if (payload_idx >= (len - 3)) {
                state = RX_STATE_CHECKSUM;
            }
            break;

        case RX_STATE_CHECKSUM:
            if (byte == calc_csum) {
                // Packet valid! Dispatch command
                dispatch_headunit_command(cmd, payload, len - 3);
            }
            state = RX_STATE_SYNC;
            break;
    }
}
```

### 7.4 Actionable Implementation Checklist for the AI Agent

```markdown
- [ ] 1. Configure Microcontroller Peripherals
      - UART at 19200 bps, 8N1 (Profile A - Raise FD).
      - CAN controller at 125 kbps (Peugeot Comfort CAN, standard 11-bit IDs).
      - Set up GPIO for Quadlock Pin 11 (Remote Turn-on +12V trigger).

- [ ] 2. Implement Framing & Checksum Drivers
      - Build `send_raise_fd_packet(cmd_id, payload, len)`.
      - Implement modulo-256 additive checksum calculator.

- [ ] 3. Implement P0 Critical Handlers
      - Button Press/Release task (`Cmd 0x02`) with debouncing and 50ms release timer.
      - Reverse Gear detection (`Cmd 0x38` Byte 3 Bit 2 & Camera Trigger `Cmd 0x40`).
      - Door & Bonnet status monitor (`Cmd 0x38` Byte 0).

- [ ] 4. Implement P1 Telemetry & DSP Handlers
      - Climate control serializer (`Cmd 0x21`, 7 bytes).
      - Radar proximity serializer (`Cmd 0x32`, 7 bytes with 0..5 inversion).
      - JBL Amplifier state tracker (`Cmd 0x56`, 8 bytes).

- [ ] 5. Implement Headunit Inbound Command Receiver
      - State machine parser for `0xFD` packets.
      - AC control dispatcher (`Cmd 0x8A`).
      - DSP slider dispatcher (`Cmd 0xC5`) with loopback confirmation.
      - Query request responder (`Cmd 0x8F`).
      - Time synchronization parser (`Cmd 0xA6`).

- [ ] 6. Verification & End-to-End Testing
      - Test using `tools/raiserzc_hu_sim/raiserzc_hu_sim.py` or actual headunit.
      - Verify Android DSP tile responds to EQ updates.
      - Verify reverse camera triggers immediately when reverse is engaged.
```

