# PSA CAN 2004 — Protocol Differences: RT4 Specification vs. Project Documentation

This document isolates and describes **only the differences, signal corrections, architectural divergences, and newly discovered frames** between the reverse-engineered RT4 firmware specification ([`doc/RT4_CAN_2004.md`](doc/RT4_CAN_2004.md), SW 8.31) and other existing repository documentation ([`doc/CAN_2004.md`](doc/CAN_2004.md), [`doc/CAN_messages.md`](doc/CAN_messages.md), [`doc/PSA_RE_comparison.md`](doc/PSA_RE_comparison.md), [`doc/CAN2004_autowp_comparison.md`](doc/CAN2004_autowp_comparison.md), [`doc/CAN2004_radio.md`](doc/CAN2004_radio.md), [`doc/CAN2004_0x0F6.md`](doc/CAN2004_0x0F6.md), [`doc/CAN2004_0x161.md`](doc/CAN2004_0x161.md), [`generated/`](generated/)).

> [!NOTE]
> **Omission of Identical Frames:**
> Frames with 100% agreement and identical signal definitions (`0x018`, `0x026`, `0x036`, `0x0E1`, `0x120`, `0x125`, `0x162`, `0x1A0`, `0x1A1`, `0x1A2`, `0x1D0`, `0x1E2`, `0x1E3`, `0x21F`, `0x260`, `0x265`, `0x764`/`0x664`) are excluded from this document.

---

## 1. Master Difference Matrix

| CAN ID | Canonical PSA Name | Existing Project Documentation | RT4 Specification (`RT4_CAN_2004.md`) | Difference Type | Resolution & Simulator Impact |
|:---:|---|---|---|:---:|---|
| **`0x0A9`** | `MSG_RAPPEL_NAV_VTH` | Missing or misdocumented as `0x1A9` with a progress bargraph | Verified CAN ID `0x0A9`: Picto ID (B0[5:0]), 14-bit GPS Altitude (B1–2), Dist to Dest (B3–4), Dist to Maneuver (B5–6[7:3]), ETA Hour/Minute (B6–7). **No bargraph exists**. | **Correction & Extension** | Cluster nav repeat must be emitted on `0x0A9` using the verified bitfield. Default idle vector: `00 3F FF 3F FF FF FF FF`. |
| **`0x0B6`** | Drivetrain Dynamic Data | Varied speed vs. RPM placement; assumed head unit calculates speed arithmetic | Wire layout: RPM in Bytes 0–1 (`raw >> 3`), Speed in Bytes 2–3 (`raw * 0.01 km/h`), Byte 7 status/counter. **RT4 does not parse this frame** (opaque `memcpy` cache; `get_filtered_speed` is a dummy stub). | **Protocol Clarification** | Wire layout confirmed via `dump_real_car.csv`. Bench simulators must emit RPM in B0–1 and Speed in B2–3. |
| **`0x0E6`** | `MSG_IS_DAT_ABR` | Not documented in existing project files | Dead reckoning wheel encoder ticks: 15-bit modulo counters for Rear Right (B1–2) and Rear Left (B3–4) with validity flags, correlated with `0x0F6` Reverse gear. | **New Discovery** | Required for dead reckoning simulation in navigation-equipped benches. |
| **`0x0F6`** | `MSG_DONNEES_BSI_LENTES` | Byte 1 described as general engine alarm info (`0xFF`); Ext Temp byte positions debated | **Byte 1 is Coolant Water Temp** (`TEAU`, $raw - 40^\circ\text{C}$); drives cluster water temp gauge. **Byte 6 is Filtered External Temp** ($raw \times 0.5 - 40^\circ\text{C}$); Byte 5 is Instantaneous. | **Signal Correction** | Water temperature gauge on cluster/trip computer is driven by `0x0F6` Byte 1, not `0x161`. |
| **`0x128`** | `MSG_INFOS_STT_ET_HY` | Documented as 8-byte cluster telltales (`CDE_COMBINE_SIGNALISATION`) | RT4 treats as 3-byte Stop & Start / Hybrid status frame; does not process cluster warning lamps. | **Scope Divergence** | RT4 consumes only the first 3 bytes; cluster nodes consume all 8 bytes. |
| **`0x161`** | `MSG_ETAT_BSI_TEMP_NIVEAU` | Byte 3 documented as Coolant Water Temperature | **Byte 3 is Fuel Level Calculation** (`NIV_CARBU`), forwarded only to BCall emergency telediagnostics. Byte 2 is Oil Temp ($raw - 40^\circ\text{C}$). Coolant is on `0x0F6`. | **Signal Correction** | Do not route `0x161` Byte 3 to water temperature gauges. |
| **`0x165`** | Audio General Status | Source carried in **Byte 2 bits 7:4** (RD4 layout); emitted on CAN to EMF-C | Source carried in **Byte 0 bits 7:4** (RT4 layout). **Not emitted on vehicle CAN** (routed to internal Front Panel IPC via `C_BCM_FP_PROTOCOL`). | **Architecture Divergence** | RD4 broadcasts to external EMF display; RT4 drives integrated screen internally. Source byte offset differs. |
| **`0x1A5`** | Audio / Media Status | Documented as **Radio Volume** (Byte 0: volume step 0–30 + `VOLFLAG` on RD4) | Documented as **CD / Jukebox Playback Status** (Track number, elapsed minutes/seconds). Volume is on `0x1E5` / DSP. Internal IPC on RT4. | **Architecture Divergence** | `0x1A5` has completely different meanings between RD4 (volume) and RT4 (media playback time). |
| **`0x1A8`** | Cruise / Limiter Display | Documented as Comfort bus frame for cluster display | **Not registered in RT4** (`Reception_Id_Tab`). RT4 obtains cruise state from `0x2E1`. | **Scope Divergence** | `0x1A8` is ignored by RT4; simulator does not need to feed `0x1A8` to the head unit. |
| **`0x1E1`** | `MSG_DONNEES_ETAT_ROUES` | Missing or only high-level mention | TPMS 5-wheel status enum extracted via `srwi r, 3` (0=OK, 1=Low, 2=Puncture, 3=Sensor Missing, 4=Battery Low). | **New Discovery** | Fully documents TPMS wheel status bitfield. |
| **`0x1E5`** | Audio Tone & Equalizer | Tone settings only (Bass, Treble, Bal, Fad, Loudness, Ambiance) on RD4 | Tone settings AND **Master Volume in Byte 6** (0..30), broadcast over CAN to external JBL digital HiFi amplifiers. | **Architecture Divergence** | RT4 controls external JBL digital amplifiers via `0x1E5`; RD4 carries volume on `0x1A5`. |
| **`0x221`** | `MSG_INFO_GEN_ODB` | Cruising Range in Bytes 1–2, Instant Consumption in Bytes 3–4 | **Inverted:** Bytes 1–2 is Instant Consumption (`CONSO_INST`, `* 0.1 L/100km`), Bytes 3–4 is Cruising Range (`AUTONOMIE`, `* 1.0 km`). | **Signal Correction** | Swap signal offsets in trip computer parsers and packet encoders. |
| **`0x225`** | Tuner Frequency | Emitted by head unit on CAN to EMF-C | Internal Front Panel IPC on RT4 (integrated screen); only emitted on CAN in RD4 systems. | **Architecture Divergence** | No vehicle CAN broadcast from RT4. |
| **`0x229`** | `MSG_NOM_RUE_NAV` | Not documented in existing project files | Navigation current/next maneuver street name: segmented ASCII string broadcast to dashboard matrix. | **New Discovery** | Entry 2 in `Emission_Id_Tab` (`0x648A`). |
| **`0x261`** | `MSG_INFOS_TRAJET2_ODB` | Older autowp/PSA-RE notes claimed Byte 0 = Mean Speed, Bytes 5–6 = Elapsed Time | Byte 0 = Status/Units (`stb r0, 8(r29)`), Bytes 1–2 = Distance, Bytes 3–4 = Avg Cons, **Bytes 5–6 = Average Road Speed** (`sth r9, 14(r29)`). | **Signal Correction** | Bytes 5–6 carries average road speed, formatted by `Update_Speed_Display` in `mmi_trip.out`. |
| **`0x269`** | `MSG_ETAT_INFO_CRASH` | Not documented in existing project files | Airbag / Crash notification: Byte 0 = Crash confirmation / severity, Byte 1 = Pretensioners / fuel cut request. Automatically triggers RT4 eCall. | **New Discovery** | Required for triggering automatic emergency eCall states. |
| **`0x2A1`** | `MSG_INFOS_TRAJET1_ODB` | Older autowp/PSA-RE notes claimed Byte 0 = Mean Speed, Bytes 5–6 = Elapsed Time | Byte 0 = Status/Units (`stb r0, 8(r29)`), Bytes 1–2 = Distance, Bytes 3–4 = Avg Cons, **Bytes 5–6 = Average Road Speed** (`sth r9, 14(r29)`). | **Signal Correction** | Identical structure to `0x261`. Bytes 5–6 is average speed, not elapsed time. |
| **`0x2A5`** | RDS PS Station Name | Emitted by head unit on CAN to EMF-C | Internal Front Panel IPC on RT4; only emitted on CAN in RD4 systems. | **Architecture Divergence** | No vehicle CAN broadcast from RT4. |
| **`0x2B6` / `0x336` / `0x3B6`** | VIN Broadcast / Theft Lock | Listed as head unit / radio CAN emissions | **RT4 never emits VIN**. BSI broadcasts VIN. RT4 receives `0x2B6` (`MSG_VIN_VIS`, slot 18); `bcm_system.out` checks digits 9–16 against EEPROM to suppress theft beep. | **Direction Correction** | Simulators must transmit `0x2B6` to RT4 to silence the anti-theft beep. |
| **`0x2E1`** | `MSG_ETAT_FONCTIONS` | Absent or split across miscellaneous BSI notes | 3-byte function state: Byte 0 = Lighting bitfield, Byte 1 = Front/Rear Wipers enum, Byte 2 = Cruise mode (`RVV`/`LVV`) and pause flag. | **New Discovery** | Provides consolidated lighting, wiper, and cruise regulation states. |
| **`0x3A1`** | `MSG_DONNEES_PRESSION_ROUES` | Not documented in existing project files | Direct individual tire pressure values for 4 wheels in $raw \times 0.05\text{ bar}$ (or 10 kPa). | **New Discovery** | Provides direct pressure readings alongside `0x1E1` status. |
| **`0x3A7`** | `MSG_INFOS_MAINTENANCE` | Not documented in existing project files | Scheduled maintenance distance countdown: Bytes 5–6 carry remaining distance until oil change (`(Byte 5 << 8) \| Byte 6`). | **New Discovery** | Drives service spanner alert and maintenance menu countdown. |
| **`0x4A4`** | `EVENEMENT_DEFAUT_BTEL` | Not documented in existing project files | Telematics failure / DTC broadcast: Entry 4 in `Emission_Id_Tab` (`cmd_send_failure` at `0x011578`). Default: `50 00 00 80 01 02 05 07`. | **New Discovery** | Asynchronous internal DTC notification from telematics to BSI. |

---

## 2. In-Depth Technical Divergence Details

### 2.1 Signal Inversions & Layout Corrections

#### Coolant Water Temperature: `0x0F6` Byte 1 vs. `0x161` Byte 3
* **Discrepancy:** Older project notes placed Coolant Water Temperature in `0x161` Byte 3.
* **Firmware Ground Truth:**
  - `get_alarm_engine_info__9C_BCM_CANPUc` (`0x00F230` in `Fp_Network_CAN.out`) reads **`0x0F6` Byte 1** and logs:
    ```text
    "Get_alarm_engine_info -> DONNEES_BSI_LENTES[TEAU] =  %x \n"
    ```
  - In `mmi_trip.out` (`0x000054F8`, `SetPropFor_NIO_TRIP_F41_Z0_3_Temp_water`), this value directly drives the coolant water temperature dial needle.
  - In `0x161`, Byte 3 is **`NIV_CARBU`** (Fuel Level calculation). It is stored to struct offset 2 (`stb r0, 2(r29)` in `get_levels_status`), ignored by dashboard dials, and only packed into byte 43 of emergency telemetry in `mmi_acp.out` (`FormTeleDiagMessage`). Only Byte 2 of `0x161` drives a dial (the oil temperature needle, `Temp_oil`).

#### Trip Computer Instantaneous Telemetry: `0x221` Bytes 1–2 vs. Bytes 3–4
* **Discrepancy:** Earlier documentation inverted Instant Consumption and Cruising Range (Autonomy).
* **Firmware Ground Truth (`0x012454` in `Fp_Network_CAN.out`):**
  - Bytes 1–2 $\to$ struct offset 10: logged as `"INFOS_GEN_ODB[CONSO_INST] : %x %x \n"`. Rendered by `Update_Consumption_Display` in `mmi_trip.out` with `sprintf(..., "%.1f")` and `"L/100"`.
  - Bytes 3–4 $\to$ struct offset 12: logged as `"INFOS_GEN_ODB[AUTONOMIE] : %x %x \n"`. Rendered by `Update_Autonomy_Display` in `mmi_trip.out` with `sprintf(..., "%d")` and `"km"`.
  - **Verdict:** Bytes 1–2 is Instant Consumption (`* 0.1 L/100km`), Bytes 3–4 is Autonomy (`km`).

#### Trip 1 & Trip 2: `0x2A1` & `0x261` Bytes 5–6 vs. Byte 0
* **Discrepancy:** Older autowp/PSA-RE notes claimed Byte 0 was Mean Speed and Bytes 5–6 was Elapsed Time.
* **Firmware Ground Truth (`0x01215C` in `Fp_Network_CAN.out`):**
  - Byte 0 $\to$ struct offset 8: trip status and fuel consumption unit flags (`stb r0, 8(r29)`).
  - Bytes 1–2 $\to$ struct offset 10: trip distance (`sth r9, 10(r29)`).
  - Bytes 3–4 $\to$ struct offset 12: average fuel consumption (`sth r9, 12(r29)`).
  - Bytes 5–6 $\to$ struct offset 14: **Average Road Speed** (`sth r9, 14(r29)`). Consumed by `Update_Speed_Display` in `mmi_trip.out` (`0x00002E5C`), which formats it as average speed (including imperial conversion $\times 1000 / 1609$ to mph).

---

### 2.2 Head Unit Architecture: RT4 (Integrated Color) vs. RD4 (Monochrome + EMF)

| Architectural Area | RD4 Architecture (Standalone Radio + Remote EMF-C) | RT4 Architecture (Integrated NaviDrive + JBL Amp) |
|---|---|---|
| **Radio Frames on CAN (`0x165`, `0x225`, `0x2A5`, `0x0A4`, `0x125`)** | Broadcast over vehicle CAN to display radio text, station name, and frequency on remote EMF-C screen. | **Not broadcast on vehicle CAN**. Routed internally via Front Panel IPC (`C_BCM_FP_PROTOCOL` / `write__5C_KEYUcPUcUc`) to the integrated color screen. |
| **`0x165` Audio Source Position** | Source enum is carried in **Byte 2 bits 7:4** (`CAN2004_radio.md`). | Source enum is carried in **Byte 0 bits 7:4** (`set_audio_general`). |
| **`0x1A5` Definition** | **Radio Volume Step** (Byte 0: volume 0–30 + `VOLFLAG`). | **CD / Jukebox Playback State** (Track number, elapsed minutes/seconds). |
| **`0x1E5` Definition** | **Tone Settings Only** (Bass, Treble, Bal, Fad, Loudness, Ambiance). | **Tone Settings AND Master Volume in Byte 6** (0..30), broadcast over CAN to external JBL digital HiFi amp. |
| **`0x128` Scope** | Full 8-byte warning lamp driver (`CDE_COMBINE_SIGNALISATION`). | 3-byte Stop & Start / Hybrid status (`MSG_INFOS_STT_ET_HY`). Cluster lamps ignored. |
| **VIN Transmission (`0x2B6`)** | Radio does not verify VIN against internal EEPROM; EMF or BSI handles pairing. | RT4 receives `0x2B6` from BSI; `VinStateAction` (`bcm_system.out`) compares digits 9–16 against EEPROM to suppress theft beep. RT4 never emits VIN. |

---

### 2.3 Verified Cluster Navigation Repeat: `0x0A9` (Replacing `0x1A9`)

* **Incorrect Earlier Specification (`0x1A9`):** Claimed CAN ID `0x1A9`, maneuver icon in Bytes 5–6, distance to turn in Bytes 1–2, and progress bargraph in Byte 7.
* **Verified Wire Layout (`0x0A9`, Entry 0 in `Emission_Id_Tab` at `0x648A`):**
  - **Byte 0:** Bit 7 = Guidance active (`info[0] & 0x80`), Bit 6 = Recalculating (`info[0] & 0x40`), Bits 5:0 = Maneuver Picto ID (`info[0] & 0x3F`).
  - **Bytes 1–2:** 14-bit GPS Altitude (+999m offset): $\text{Alt [m]} = ((\text{B1} \& 0x3F) \ll 8 \mid \text{B2}) - 999$.
  - **Bytes 3–4:** 14-bit Distance to Destination: $((\text{B3} \& 0x3F) \ll 8 \mid \text{B4})$.
  - **Bytes 5–6[7:3]:** 13-bit Distance to Maneuver: $((\text{B5} \ll 5) \mid (\text{B6} \gg 3))$.
  - **Byte 6[2:0] & Byte 7:** 5-bit ETA Hour (`((B6 & 0x07) << 2) | ((B7 & 0xC0) >> 6)`) and 6-bit ETA Minute (`B7 & 0x3F`).
  - **Bargraph Status:** **Completely absent**. Byte 7 carries the ETA minute and lower hour bits.
  - **Default Idle Payload:** `00 3F FF 3F FF FF FF FF`.