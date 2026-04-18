# PSA-RE Cross-Reference: AEE2004 Comfort CAN vs Simulator

Source: [prototux/PSA-RE](https://github.com/prototux/PSA-RE) — `buses/AEE2004.full/LS.CONF/`

This document cross-references every frame in the PSA-RE AEE2004 LS.CONF (comfort/infotainment CAN,
125 kbps) against the simulator implementation and existing workspace documentation. It lists gaps,
corrections, and new signal knowledge that did not exist in the workspace before.

> **Byte numbering:** PSA-RE uses **1-indexed** bytes (byte 1 = first byte on the wire). The
> simulator and Python code use **0-indexed** arrays. Throughout this document all mappings are
> given in both forms: `byte N (idx M)`.

---

## Summary of Corrections

| Frame | Issue | Action |
|-------|-------|--------|
| **0x0F6** | Bytes 3-5 (idx 2-4) are a 24-bit **odometer**, not the constant `0x00 0x1F 0x00` the simulator sends | Update docs; simulator sends placeholder — acceptable for bench only |
| **0x0F6** | Byte 8 (idx 7) carries **BLINKERS_STATUS** (bits 1-0) and **FRONT_WIPERS_STATUS** (bit 6) in addition to reverse | Update docs |
| **0x0F6** | Period is **500 ms** per PSA-RE; simulator sends at 100 ms | Noted — may cause EMF to show data faster than real BSI |
| **0x168** | The frame is **alert/warning indicators** (`COMBINE_ALERTS_INDICATORS`), not ambient temperature or battery voltage | Correction — earlier workspace note was from an incorrect source |
| **0x128** | Several signals not documented: STOP, STOP_RESTART, DOORS_1/2, ABS_IN_PROGRESS, CHILD_SAFETY, ESP_DESACTIVED, ESP_BLINK, SUSPENSION, WARNINGS, HILL_HOLDER, DAYLIGHTS, PARKING_BRAKE_DESACTIVATED, all rear-row seatbelt indicators | Documented below |
| **0x161** | Frame is **7 bytes** per PSA-RE; simulator encodes 8 bytes (extra `0xFF` padding); period 500 ms | Noted — extra padding is harmless but period differs |
| **0x161** | Byte 7 (idx 6) carries **OIL_LEVEL** (0–100 %, resolution 1 %) | New signal — not previously documented |
| **0x221** | Period is **1000 ms** per PSA-RE; simulator sends at 100 ms | Period mismatch — acceptable for bench |
| **0x2A1** | Period is **1000 ms** per PSA-RE; simulator sends at 100 ms | Period mismatch — acceptable for bench |
| **0x2A1** | Byte 6-7 (idx 5-6) carry **TOTAL_TIME** (uint16, minutes), not two trailing zeroes | Update docs |
| **0x1A8** | SET_SPEED is a **uint16 × 0.01 km/h** at bytes 2-3 (idx 1-2); bytes 6-8 (idx 5-7) are ODOMETER_PARTIAL (uint24, × 0.001 km) | New detail |
| **0x1D0** | Temperature scale starts at **14 °C** (index 1), not 15 °C; scale goes to 28 °C (index 0x15 = HI) | Update docs |
| **0x036** | Byte 2 (idx 1) carries PROFILE_NUMBER_1 and driver memory recall/save signals | New detail |

---

## Frame-by-Frame Reference

### 0x036 — BSI_COMMANDS (COMMANDES_BSI)

**PSA-RE periodicity:** 100 ms  
**PSA-RE sender:** BSI (+ PASS_ICSV)

| Byte (1-idx) | Idx | Bits | PSA-RE signal | Alt name | Notes |
|---|---|---|---|---|---|
| 2 | 1 | 7-6 | PROFILE_NUMBER_1 | NUM_PROF_1 | 0=factory, 1-3=user profile |
| 2 | 1 | 5 | DRIVER_MEMORY | RAPP_MEM_C | driver memory recall |
| 2 | 1 | 4 | DRIVER_MEMORY_SAVE | MISE_MEM_C | driver memory save |
| 2 | 1 | 3-0 | DRIVER_MEMORY_COUNT | NUM_MEM_C | number of profiles (0-14) |
| 3 | 2 | 7-6 | PROFILE_NUMBER_2 | NUM_PROF_2 | passenger profile |
| 3 | 2 | 5 | PASSENGER_MEMORY | RAPP_MEM_P | passenger memory recall |
| 3 | 2 | 4 | PASSENGER_MEMORY_SAVE | MISE_MEM_P | passenger memory save |
| 3 | 2 | 3-0 | PASSENGER_MEMORY_COUNT | NUM_MEM_P | (0-14) |
| 4 | 3 | 7 | ECO_MODE | MODE_ECO | energy economy mode |
| 4 | 3 | 3-0 | POWER_SAVING_LEVEL | NIV_DELEST | energy economy level |
| 5 | 4 | 7 | RESYNCHRONIZATION | RESYNC | resynchronisation command |
| 5 | 4 | 6 | RHEOSTAT_TYPE | TYPE_RHEOS | 0=manual, 1=automatic |
| 5 | 4 | 5 | DAYNIGHT_STATUS | ETAT_JN | 0=day, 1=night |
| 5 | 4 | 4 | DARK_MODE | BCK_PNL | dark mode on/off |
| 5 | 4 | 3-0 | BRIGHTNESS | LUMINOSITE | 0-15 |
| 6 | 5 | 6 | CLEAR_FAULTS | DEM_EFFAC_DEF | clear all faults |
| 6 | 5 | 5 | DIAG_STATUS | DIAG_MUX_ON | diagnostic session active |
| 6 | 5 | 3 | LOG_FAULTS | INTERD_MEMO_DEF | enable/disable fault logging |
| 6 | 5 | 2-0 | POWER_MANAGEMENT | PHASE_VIE | **0=Sleep, 1=Normal, 2=Going to sleep, 3=Wakeup, 4=No comms** |
| 7 | 6 | 7-5 | HYBRID_STATUS | ETAT_GMP_HY | 0=undef, 1=inactive, 2-5=active modes |
| 7 | 6 | 3 | AVR_ACTIVATION_STATUS | ETAT_ACTIVATION_AVR | |
| 8 | 7 | 7-4 | SECURE_INFO | SECU_ETAT_SEV | 0x0A = security info valid |
| 8 | 7 | 1 | AUDIO_INVIOLABILITY | INVIOLABILITE_AUDIO | |
| 8 | 7 | 0 | TE_POSITION | POSITION_TE | convertible roof (0=closed, 1=open) |

**Simulator cross-check:**

The simulator correctly encodes:
- `POWER_MANAGEMENT` in byte 6 (idx 5) bits 2-0 using values 0-3.
- `ECO_MODE` in byte 4 (idx 3) bit 7.
- `DARK_MODE` and `BRIGHTNESS` in byte 5 (idx 4) bits 4-0.

The simulator sends byte 2 (idx 1) as `0x0E` (fixed). PSA-RE shows byte 2 carries profile/memory
signals. On a real bus these may be non-zero if seat-memory ECUs are present. For bench-only
simulation the constant is acceptable.

---

### 0x0F6 — BSI_SLOW_DATA (DONNEES_BSI_LENTES)

**PSA-RE periodicity:** 500 ms  
**PSA-RE sender:** BSI

| Byte (1-idx) | Idx | Bits | PSA-RE signal | Alt name | Encoding |
|---|---|---|---|---|---|
| 1 | 0 | 7-6 | CONFIG_MODE | MDE_CFG | 0=factory, 2=customer |
| 1 | 0 | 5 | FACTORY_PARK | PARC_USINE | 0=not parked, 1=parked |
| 1 | 0 | 4-3 | MAIN_STATUS | ETAT_PRINCIP_SEV | 0=stopped, 1=contact, 2=starting |
| 1 | 0 | 2 | GEN_STATUS | ETAT_GEN | 0=not working, 1=working |
| 1 | 0 | 1-0 | POWERTRAIN_STATUS | ETAT_GMP | 0=stopped, 1=starting, 2=running, 3=stopping |
| 2 | 1 | 7-0 | COOLANT_TEMPERATURE | TEAU | raw − 40 °C, resolution 1 °C |
| **3-5** | **2-4** | **23-0** | **ODOMETER** | KM_TOTAL | **uint24, × 0.1 km, invalid 0xFFFFFF** |
| 6 | 5 | 7-0 | EXTERNAL_TEMPERATURE | T_EXT | raw × 0.5 − 40 °C, invalid 0xFF |
| 7 | 6 | 7-0 | EXTERNAL_FILTERED_TEMPERATURE | T_EXT_FILT | raw × 0.5 − 40 °C (filtered/damped) |
| 8 | 7 | 7 | REVERSE_STATUS | ETAT_MA | 0=forward, 1=reverse |
| 8 | 7 | 6 | FRONT_WIPERS_STATUS | ESSUYAGE | 0=not wiping, 1=wiping |
| 8 | 7 | 5-4 | WHEEL_POSITION | TYPE_DIR | 1=RHD, 2=LHD |
| 8 | 7 | 3 | CLUSTER_INDICATORS_TEST | TEST_VOY_CMB | lamp test |
| 8 | 7 | 1-0 | BLINKERS_STATUS | ETAT_CLIGNOTANTS | 0=none, 1=right, 2=left, 3=both |

**Corrections vs existing workspace documentation:**

1. **Bytes 3-5 (idx 2-4) are the odometer**, encoded as uint24 × 0.1 km.  The simulator sends
   `0x00, 0x1F, 0x00` as constants in those positions.  This is correct for bench simulation
   (no real odometer to emulate) but should not be confused with meaningful temperature or body
   data.

2. **External temperature resolution is 0.5** (formula: `raw * 0.5 − 40`). The simulator correctly
   uses this formula in the `decode` path (`data[5] / 2.0 - 40`).

3. **Byte 8 (idx 7) carries blinker state** in bits 1-0. The simulator only tracks the reverse bit
   (bit 7) from this byte.

4. **Real-bus first byte (idx 0) starts with 0x88**, not 0x08. PSA-RE shows byte 1 as a multi-field
   status byte (`CONFIG_MODE=2, GEN_STATUS=1` → `0x88` = customer config + generator working).
   The simulator sends `0x08` which corresponds to `CONFIG_MODE=0, POWERTRAIN_STATUS=0` — a
   valid but less realistic pattern.

---

### 0x128 — COMBINE_SIGNALS_INDICATORS (CDE_COMBINE_SIGNALISATION)

**PSA-RE periodicity:** 200 ms  
**PSA-RE sender:** BSI

This frame is the primary dashboard lamp driver. PSA-RE provides a complete signal list.

#### Byte 1 (idx 0) — warning indicators

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | PASSENGER_AIRBAG | ABPI | passenger airbag off indicator |
| 6 | FRONT_LEFT_SEATBELT | OUCC | driver seatbelt |
| 5 | PARKING_BRAKES | FRPK | parking brake |
| 4 | LOW_FUEL | MINC | low fuel |
| 3 | FUEL_DISABLED | CCARB_NEUT | fuel cut indicator |
| 2 | PREHEAT | PRE_CHAUFF | diesel preheat |
| 1 | FRONT_RIGHT_SEATBELT | OUCP | passenger seatbelt |
| 0 | SERVICE_RESTART | RELANCE_SERVICE | service restart indicator |

#### Byte 2 (idx 1)

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | MAINTENANCE | SERVICE | service / spanner indicator |
| 6 | STOP | STOP | STOP indicator |
| 5 | STOP_RESTART | RELANCE_STOP | stop restart indicator |
| 4 | DOORS_1 | SIGNAL_OUV_INF_10 | door open below 10 km/h |
| 3 | DOORS_2 | SIGNAL_OUV_SUP_10 | door open above 10 km/h |
| 2 | FRONT_PASSENGER_PROTECTION | PROT_PASS_AV_ACT | front passenger protection |
| 1 | ABS_IN_PROGRESS | ABS_ACT | ABS in action |
| 0 | REAR_SEATBELT_NOT_FASTENED | DEB_CEINT_AR | rear seatbelt not fastened |

#### Byte 3 (idx 2)

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | COLOR_CHANGE | DMD_COULEUR_CMB | color change request |
| 6 | CUSTOMIZATION | DMD_PERSO_CMB | customisation request |
| 5 | CHILD_SAFETY | SECE_ACT | child safety indicator |
| 4 | ESP_DESACTIVED | ESPI | ESP disabled indicator |
| 3 | ESP_BLINK | ESPACT | ESP blinking |
| 2 | SUSPENSION | SUSP | suspension indicator |
| 1 | WARNINGS | CMD_WARNING | hazard warning lights |
| 0 | IGNITION_READY | READY_HY | hybrid ready |

#### Byte 4 (idx 3) — seatbelt blink + brake pedal

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | FRONT_LEFT_SEATBELT_BLINK | OUCC_CLIG | driver seatbelt blinking |
| 6 | FRONT_RIGHT_SEATBELT_BLINK | OUCP_CLIG | passenger seatbelt blinking |
| 5 | HILL_HOLDER | HILL_HOLDER | hill-start assist |
| 4 | AVAILABLE_SPACE | MPD | parking space measurement |
| 3 | AVAILABLE_PLACE_BLINK | MPD_CLIG | space measurement blinking |
| 2-1 | BRAKE_PEDAL | PIED_FREIN | 0=off, 1=on, 2=blinking |
| 0 | REAR_RIGHT_SEATBELT_BLINK | DEB_CEINT_AR_CLIG | rear seatbelt right blinking |

#### Byte 5 (idx 4) — external lighting

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | SIDELIGHTS | FEUX_POS | parking/sidelights on |
| 6 | LOW_BEAM | FEUX_CROIS | low beam on |
| 5 | FULL_BEAM | FEUX_ROUTE | high beam on |
| 4 | FRONT_FOG_LIGHTS | FEUX_ABAV | front fog lights |
| 3 | REAR_FOG_LIGHTS | FEUX_ABAR | rear fog lights |
| 2 | RIGHT_TURN | CLIGNO_D | right turn indicator |
| 1 | LEFT_TURN | CLIGNO_G | left turn indicator |
| 0 | DAYLIGHTS | FEUX_DIURNES | daytime running lights |

#### Byte 6 (idx 5) — cluster on + rear seatbelts

| Bit | Signal | Alt name | Meaning |
|-----|--------|----------|---------|
| 7 | CMB_ON | ON_CMB | instrument cluster active |
| 6 | REAR_LEFT_SEATBELT | OUCARG | rear left seatbelt |
| 5 | REAR_LEFT_SEATBELT_BLINK | OUCARG_CLIG | rear left seatbelt blinking |
| 4 | REAR_MIDDLE_SEATBELT | OUCARM | rear middle seatbelt |
| 3 | REAR_MIDDLE_SEATBELT_BLINK | OUCARM_CLIG | rear middle seatbelt blinking |
| 2 | REAR_RIGHT_SEATBELT | OUCARD | rear right seatbelt |
| 1 | REAR_RIGHT_SEATBELT_BLINK | OUCARD_CLIG | rear right seatbelt blinking |
| 0 | PARKING_BRAKE_DESACTIVATED | FSE_INHIB | parking brake disabled indicator |

#### Byte 7 (idx 6) — gear display

| Bits | Signal | Alt name | Values |
|------|--------|----------|--------|
| 7-4 | CURRENT_GEAR | RAP_AFF_CMB | 0=P, 1=R, 2=N, 3=D, 4=6, 5=5, 6=4, 7=3, 8=2, 9=1 |
| 3-1 | DRIVE_GEAR | RAP_AFF_DRIVE | 0=declutch, 1-6=gears |
| 0 | CURRENT_GEAR_BLINK | AFF_RAP_CLIGN | blink the gear display |

#### Byte 8 (idx 7) — gearbox mode

| Bits | Signal | Alt name | Values |
|------|--------|----------|--------|
| 7 | GEAR_SHIFT_ARROW_BLINK | TYPE_ALLUM_FLECHE | 0=fixed, 1=blinking |
| 6-4 | AUTO_GEAR_MODE | MODE_BVA_BVMP | 0=Auto, 2=Sport, 4=Sequential, 5=Seq.Sport, 6=Snow |
| 3-2 | GEAR_SHIFT_ARROW | ALLUM_FLECHE | 0=off, 1=up, 2=down, 3=both |
| 1-0 | GEARBOX_TYPE | SEL_BVA_BVM_BVMP | 0=BVA (auto), 1=BVM (manual), 2=BVMP (semi-auto) |

**Simulator cross-check:**

The simulator encodes most of byte 5 (idx 4) correctly. Byte 6 (idx 5) bit 7 = `CMB_ON` is used
as the cluster-active flag, which matches `dash.on` in the combine module.
Bytes 7-8 (idx 6-7) are hardcoded to `0x00` in the simulator's basic mode, and to gear display
fields in combine mode. The full gear encoding above can be used to extend `Msg128` when gear
simulation is added.

---

### 0x161 — BSI_GAUGES (ETAT_BSI_TEMP_NIVEAU)

**PSA-RE frame length:** 7 bytes (simulator encodes 8, with trailing `0xFF` padding)  
**PSA-RE periodicity:** 500 ms

| Byte (1-idx) | Idx | Bits | Signal | Encoding |
|---|---|---|---|---|
| 1 | 0 | 7 | OIL_LEVEL_RESTART | restart request |
| 1 | 0 | 6-2 | (unused) | |
| 3 | 2 | 7-0 | OIL_TEMPERATURE | raw − 40 °C, invalid 0xFF |
| 4 | 3 | 7-0 | FUEL_LEVEL | 0-100 %, invalid 0xFF |
| 5-6 | 4-5 | — | (unused) | |
| 7 | 6 | 7-0 | OIL_LEVEL | 0-250 %, invalid 0xFF |

**New signal:** `OIL_LEVEL` in byte 7 (idx 6) was not previously documented. The simulator sends
`0xFF` in that position (unused/invalid), which is the correct invalid value per PSA-RE.

---

### 0x168 — COMBINE_ALERTS_INDICATORS (CDE_COMBINE_TEMOINS)

**PSA-RE periodicity:** 200 ms  
**PSA-RE sender:** BSI

> ⚠️ **Correction:** Earlier workspace notes (from `peugeot407can.yaml` and `psa_pf2_comfort.md`)
> described 0x168 as carrying ambient temperature and battery voltage. This was incorrect. PSA-RE
> confirms that 0x168 is the **dashboard alert/fault indicator** frame. The `can_messages.py`
> `Msg168` implementation was already correct; only the documentation in `CAN_messages.md` was wrong.

| Byte (1-idx) | Idx | Bits | Signal | Alt name |
|---|---|---|---|---|
| 1 | 0 | 7 | COOLANT_TEMPERATURE_ALERT | ALERTE_T_EAU |
| 1 | 0 | 6 | OIL_TEMPERATURE_ALERT | ALERTE_T_HUIL |
| 1 | 0 | 5 | COOLANT_LEVEL_ALERT | NIVE_AL |
| 1 | 0 | 4 | OIL_LEVEL_ALERT | NIVH_AL |
| 1 | 0 | 3 | OIL_PRESSURE_ALERT | PHUI_AL |
| 1 | 0 | 2 | BRAKE_LEVEL_ALERT | NIVL_AL |
| 1 | 0 | 1 | COLD_ENGINE_ALERT | ALERTE_MOT_FROID |
| 1 | 0 | 0 | DSG_FAULT | DEFAUT_DSG |
| 2 | 1 | 7 | UNDERINFLATION_ALERT | SOUG_AL |
| 2 | 1 | 6 | PUNCTURE_ALERT | CREV_AL |
| 2 | 1 | 5 | AUTO_STOP_ALERT | AUTO_STOP |
| 2 | 1 | 4 | PARTICLE_FILTER_FAULT | DMD_ALLUM_FAP |
| 2 | 1 | 3 | AUTO_WIPE_STATUS | ESSUI_AUTO |
| 2 | 1 | 2 | MAX_RPM_LVL1 | ALLUM_REGIME_MAX1 |
| 2 | 1 | 1 | LOW_FUEL_BLINK | MINC_CLIG |
| 2 | 1 | 0 | MAX_RPM_LVL2 | ALLUM_REGIME_MAX2 |
| 4 | 3 | 7 | REF_EHB_FAULT | REF_DEF |
| 4 | 3 | 6 | SUSPENSION_FAULT | DSUSP_DEF |
| 4 | 3 | 5 | ABS_FAULT | ABS_DEF |
| 4 | 3 | 4 | ASR_FAULT | ASR_DEF |
| 4 | 3 | 3 | GEARBOX_FAULT | BV_DEF |
| 4 | 3 | 2 | BRAKES_FAULT | PLAQ_DEF |
| 4 | 3 | 1 | EOBD_FAULT | EOBD_DEF |
| 4 | 3 | 0 | DIESEL_WATER_FAULT | EAUG_DEF |
| 5 | 4 | 7-6 | REQUEST_PILOT_LIGHT_SCR | DMD_ALLUM_SCR |
| 5 | 4 | 5 | SAFETY_FAULT | SEC_PASS_DEF |
| 5 | 4 | 4 | POLLUTION_FAULT | POLL_DEF |
| 5 | 4 | 2 | BATTERY_FAULT | CBAT_DEF |
| 5 | 4 | 1 | ALTERNATOR_FAULT | GENE_DEF |
| 6 | 5 | 4 | PARKING_BRAKE_FAULT | FSE_SYST_DEF |
| 6 | 5 | 3 | PARKING_BRAKE_TIGHT_FAULT | FSE_SER_DEF |
| 6 | 5 | 2 | ENGINE_FAULT_BLINK | MOT_CLIG |
| 6 | 5 | 1-0 | STT_INDICATOR | DMD_ALLUM_STT |
| 7 | 6 | 4-3 | CAAR | DMD_ALLUM_CAAR | suspension indicator 0=off,1=on,2=blink |
| 7 | 6 | 2 | TURN_LIGHTS_FAULT | CODE_VIR_DEF |
| 7 | 6 | 0 | ENGINE_FAULT | MOT_DEF |
| 8 | 7 | 7 | FUSE_FAULT | PARE_DEF |
| 8 | 7 | 6 | OBD_CODE_READINESS | READINESS_STATUT |
| 8 | 7 | 3-2 | HYBRID_ZEV | P_TEM_GIMH_ZEV |

**Simulator cross-check:** The simulator's `Msg168` encodes the correct subset of signals. The
mapping of `dash.coolant_warn` → byte 0 bit 7, `dash.abs` → byte 3 bit 5, and
`dash.battery` → byte 4 bit 1 are all confirmed by PSA-RE.

---

### 0x1A8 — SPEED_CONTROL (GESTION_VITESSE)

**PSA-RE periodicity:** 200 ms  
**PSA-RE sender:** BSI

| Byte (1-idx) | Idx | Bits | Signal | Alt name | Encoding |
|---|---|---|---|---|---|
| 1 | 0 | 7-6 | SPEED_CONTROL_TYPE | FONCT_ACT_LVV_RVV | 0=none, 1=regulator, 2=limiter, 3=adaptive CC |
| 1 | 0 | 5-3 | ACTIVE_FUNCTION_STATUS | ETAT_FONCT_LVV_RVV | 0=standby, 1=active, 2=limiter active, 3-4=overspeed, 6=not activatable, 7=fault |
| 1 | 0 | 2 | ACTIVATION_ATTEMPT | TENT_ACT_LVV_RVV | |
| 1 | 0 | 1 | CONTROL_UNIT | UNITE_CONSIGNE_LVV_RVV | 0=km/h, 1=mph |
| **2-3** | **1-2** | **15-0** | **SET_SPEED** | VIT_CONS_LVV_RVV | **uint16 × 0.01 km/h, invalid 0xFFFF** |
| **6-8** | **5-7** | **23-0** | **ODOMETER_PARTIAL** | ODO_PARTIEL | **uint24 × 0.001 km, invalid 0xFFFFFF** |

The simulator does not currently implement 0x1A8. When decoding from a real car:

```python
speed_raw = (data[1] << 8) | data[2]
set_speed_kmh = speed_raw * 0.01  # 0xFFFF = not set

odo_raw = (data[5] << 16) | (data[6] << 8) | data[7]
partial_odo_km = odo_raw * 0.001  # 0xFFFFFF = invalid
```

---

### 0x161 — BSI_GAUGES (see above)

See table in the 0x161 section.

---

### 0x220 — DOORS_STATUS

**PSA-RE periodicity:** 500 ms  
**PSA-RE sender:** BSI

PSA-RE confirms the byte 1 (idx 0) door bit layout exactly as documented in `CAN2004_doors.md`.
Two clarifications from PSA-RE:

| Byte (1-idx) | Idx | Bit | Signal | PSA-RE note |
|---|---|---|---|---|
| 2 | 1 | 7 | CAR_TYPE | **0 = 5-door saloon/hatch, 1 = 3-door** (not "vehicle type") |
| 2 | 1 | 6 | SPARE_WHEEL_ARM_STATUS | spare wheel arm open/closed |
| 1 | 0 | 1 | REAR_WINDOW | **only present on SW (estate) models** |

---

### 0x361 — VEHICLE_FEATURE_AVAILABILITY (BSI_INF_CFG)

**PSA-RE periodicity:** 500 ms or trigger  
**PSA-RE sender:** BSI

PSA-RE shows 0x361 as a 6-byte capability/option presence register:

| Byte (1-idx) | Idx | Bits | Signal | Meaning |
|---|---|---|---|---|
| 1 | 0 | 3 | PROFILE_CHANGE_AUTHORIZATION | 0=allowed, 1=forbidden |
| 1 | 0 | 2-0 | ACTIVE_PROFILE_NUMBER | 0=none, 1=P1, 2=P2, 4=P3, 7=default |
| 2 | 1 | 4 | CONFIGURABLE_KEY_OPTION | configurable key option present |
| 2 | 1 | 3 | SPECTROSCOPE_PRESENCE | |
| 2 | 1 | 2 | DRIVER_GREETING_PRESENCE | |
| 2 | 1 | 1 | PARTIAL_WINDOW_DESCENT | |
| 2 | 1 | 0 | REAR_SHUTTER_PERMANENT_LOCKING | |
| 3 | 2 | 7 | DOOR_SELECTIVITY_OPTION | door selectivity at remote key |
| 3 | 2 | 6 | DISTANCE_AUTO_CLOSING | ADML closing option |
| 3 | 2 | 5 | LOCKING_MODE_OPTION | locking mode (COE) |
| 3 | 2 | 4 | FOLLOW_ME_HOME | lighting option |
| 3 | 2 | 3 | GREETING_LIGHT | welcome light |
| 3 | 2 | 2 | ELECTRIC_PARKING_BRAKE_OPTION | auto EPB option |
| 3 | 2 | 1 | IRC_PRESENCE | IRC present |
| 3 | 2 | 0 | AUTOMATIC_HEADLIGHTS | auto light-on option |
| 4 | 3 | 7 | ADAPTIVE_LIGHTING | adaptive headlights |
| 4 | 3 | 6 | DAYLIGHTS_OPTION | DRL option present |
| 4 | 3 | 5 | REAR_WIPER_IN_REVERSE | rear wiper in reverse option |
| 5 | 4 | 7 | PARKING_AID_VISUAL | AAS visual feedback |
| 5 | 4 | 6 | PARKING_AID_AUDIBLE | AAS audible feedback |
| 5 | 4 | 5 | PARKING_AID_INHIBITION | AAS total inhibition |
| 5 | 4 | 4 | EMF_PRESENCE | EMF display present |
| 5 | 4 | 3 | MOTORWAY_LIGHTING | motorway lighting function |
| 5 | 4 | 2 | AMBIENT_LIGHTING | ambient interior lighting |
| 5 | 4 | 1 | BLIND_SPOT_MONITORING | DAS/SAM present |
| 5 | 4 | 0 | BLIND_SPOT_TOTAL_INHIBITION | DAS inhibition |
| 6 | 5 | 7 | BLIND_SPOT_SOUND_INHIBITION | DAS sound inhibition |
| 6 | 5 | 6-4 | TPMS_PRESENCE | 0=none, 1=direct gen1, 2=direct gen2, 3=indirect |
| 6 | 5 | 3 | NBL_PRESENCE | NBL casing |
| 6 | 5 | 2 | TPMS_REINITIALIZATION | TPMS reset menu option |

---

### 0x1D0 — CLIM_STATUS (ETAT_CLIM_AV_BSI)

**PSA-RE periodicity:** 500 ms  
**PSA-RE sender:** CLIM  

Temperature encoding correction from PSA-RE (1-indexed in table):

| Index | Temperature |
|-------|-------------|
| 0x00 | LO |
| 0x01 | 14 °C / 57 °F |
| 0x02 | 15 °C / 59 °F |
| ... | ... |
| 0x16 | HI |

The simulator's temperature table starts at 15 °C (index 1). PSA-RE shows index 1 = **14 °C**.
This is a 1 °C offset at the low end of the scale. Above 14 °C the 0.5 °C step pattern is
identical in both sources.

---

### 0x1E3 — CLIMATE_CONTROL_STATUS (ETAT_CLIM_AV_EMF)

**PSA-RE periodicity:** 200 ms or trigger  
**PSA-RE sender:** CLV (climate display controller)

PSA-RE provides a complete signal list. Key signals confirmed by PSA-RE:

| Byte (1-idx) | Idx | Bits | Signal | Meaning |
|---|---|---|---|---|
| 1 | 0 | 7 | AIR_RECYCLING_STATUS | 0=external/partial, 1=recycling |
| 1 | 0 | 6 | COMPRESSOR_STATUS | 0=on, 1=off (**inverted**) |
| 1 | 0 | 5 | AC_OFF_MODE_REQUEST | general AC off |
| 1 | 0 | 4 | AUTOMATIC_AIR_INTAKE | 0=manual, 1=auto |
| 1 | 0 | 3 | AC_AUTOMATIC_MODE | 0=at least one manual, 1=full auto |
| 1 | 0 | 2 | AUTO_HEATER_STATUS | 0=manual, 1=auto |
| 1 | 0 | 1 | RECYCLING_PUSH | recycling button pressed |
| 1 | 0 | 0 | AC_DUAL_MODE | dual zone on/off |
| 3 | 2 | 4-0 | FRONT_LEFT_TEMPERATURE_SETPOINT | offset from center (0=LO, 0x0B=center, 0x16=HI) |
| 4 | 3 | 4-0 | FRONT_RIGHT_TEMPERATURE_SETPOINT | offset from center |
| 5 | 4 | 7-4 | FRONT_LEFT_AIRFLOW_DISTRIBUTION | 0=auto comfort, 2=floor, 3=vent, 4=defrost, ... |
| 6 | 5 | 7-4 | FRONT_RIGHT_AIRFLOW_DISTRIBUTION | same encoding as left |
| 7 | 6 | 3-0 | AIR_SPEED_LEVEL | 0-7 = speeds 1-8; 0x0F = speed 0 (off) |

**Simulator cross-check:** The `Clim` module's EMF encoder produces bytes 0-6 that broadly match
this layout. The `AC_DUAL_MODE` bit at byte 0 bit 0 is confirmed.

---

### 0x1A1 — BSI_DISPLAY_MESSAGE (BSI_CDE_PTR_MESSAGE)

**PSA-RE periodicity:** 200 ms  
**PSA-RE sender:** BSI

PSA-RE provides a cleaner signal definition than the simulator's ad-hoc byte descriptions:

| Byte (1-idx) | Idx | Bits | Signal | Meaning |
|---|---|---|---|---|
| 1 | 0 | 7 | DISPLAY_MESSAGE | 0=no new message, 1=new message |
| 1-2 | 0-1 | 14-bit field (1.6-2.0) | MESSAGE_ID | message number (0–16383) |
| 3 | 2 | 7 | DEST_EMF | EMF should display |
| 3 | 2 | 6 | DEST_CMB | CMB should display |
| 3 | 2 | 5 | DEST_VTH | VTH should display |
| 3 | 2 | 4 | CHECK_IN_PROGRESS | check in progress flag |
| 3 | 2 | 3-0 | PRIORITY | 0-14 |
| 4-8 | 3-7 | 40-bit field | MESSAGE_ARGS | message arguments / parameters |

**Simulator cross-check:** The simulator uses byte 0 bit 7 (`DISPLAY_MESSAGE`) as the show/hide
flag and byte 1 (idx 1) as the `MESSAGE_ID`. This maps correctly to the PSA-RE definition.

---

### 0x0E1 — AAS_DATA (DONNEES_AAS)

**PSA-RE periodicity:** 100 ms  
**PSA-RE sender:** AAS (parking sensors ECU)

PSA-RE confirms the 6-zone distance layout. Zone values 0-7 represent distance bands (0=closest
obstacle / alarm, 7=no obstacle or inactive). PSA-RE adds:

- Byte 1 (idx 0) bits 7-5: **REAR_STATUS** — 0=undefined, 1=error, 2=disabled by button,
  3=disabled trailer, 4=active, 5=waiting, 6=not working
- Byte 1 (idx 0) bits 4-2: **FRONT_STATUS** — same encoding as REAR_STATUS
- Byte 2 (idx 1) bits 7-6: **SOUND_LR** — 0=none, 1=left, 2=right, 3=both
- Byte 7 (idx 6) bits 7-5: **SPACE_MEASUREMENT_STATUS** — park-assist measurement state

The simulator's parktronic module emits the 6 distance values in bytes 4-6 (idx 3-5) which
matches PSA-RE bytes 4-6 layout.

---

### 0x221 — TRIP_GENERAL_INFOS (INFOS_GEN_ODB)

**PSA-RE periodicity:** 1000 ms (simulator sends at 100 ms — period mismatch)

| Byte (1-idx) | Idx | Bits | Signal | Encoding |
|---|---|---|---|---|
| 1 | 0 | 7 | CHECK_CONSUMPTION | 0=valid, 1=invalid |
| 1 | 0 | 6 | CHECK_AUTONOMY | 0=valid, 1=invalid |
| 1 | 0 | 3 | TRIP_PUSH_BUTTON | right stalk button |
| 1 | 0 | 0 | NAVIGATION_PUSH_BUTTON | left stalk button |
| 2-3 | 1-2 | 15-0 | INSTANT_CONSUMPTION | uint16 × 0.1 L/100 km, invalid 0xFFFF |
| 4-5 | 3-4 | 15-0 | AUTONOMY | uint16 km, invalid 0xFFFF |
| 6-7 | 5-6 | 15-0 | TRIP_DIST_LEFT | uint16 × 0.1 km, invalid 0xFFFF |

**Simulator cross-check:** The simulator encodes instant consumption in bytes 1-2 (idx 1-2) as
`value × 10`, which is equivalent to uint16 × 0.1 with the multiplier already applied.
Autonomy is in bytes 3-4 (idx 3-4) as an integer km — confirmed.

---

### 0x2A1 — TRIP_FIRST_INFOS (INFOS_TRAJET1_ODB)

**PSA-RE periodicity:** 1000 ms (simulator sends at 100 ms — period mismatch)

| Byte (1-idx) | Idx | Bits | Signal | Encoding |
|---|---|---|---|---|
| 1 | 0 | 7-0 | MEAN_SPEED | uint8 km/h, invalid 0xFF |
| 2-3 | 1-2 | 15-0 | TOTAL_DISTANCE | uint16 km, invalid 0xFFFF |
| 4-5 | 3-4 | 15-0 | MEAN_CONSUMPTION | uint16 × 0.1 L/100 km |
| **6-7** | **5-6** | **15-0** | **TOTAL_TIME** | **uint16 minutes**, invalid 0xFFFF |

**Correction:** The simulator's comment says bytes 5-6 (idx 5-6) must be `0x00 0x00` otherwise the
display shows `"--"`. PSA-RE shows these as `TOTAL_TIME`. The `"--"` behaviour means the MFD
treats any non-zero value here as a time to display; sending `0x00 0x00` renders as 0 minutes
which the display may show as `"--"`. This is consistent.

---

## Frames in PSA-RE Not Implemented in Simulator

The following frames exist in the PSA-RE LS.CONF but are not yet implemented in the simulator:

| Frame | PSA-RE name | Notes |
|-------|-------------|-------|
| 0x0D6 | ? | not in simulator |
| 0x0E6 | ? | not in simulator |
| 0x0E8 | ? | not in simulator |
| 0x10B | ? | not in simulator |
| 0x120 | Alerts journal | documented in `CAN2004_0x120.md` |
| 0x126 | ? | not in simulator |
| 0x127 | ? | not in simulator |
| 0x15B | ? | not in simulator |
| 0x1DF | ? | not in simulator |
| 0x1E0 | ? | not in simulator |
| 0x217 | ? | ignition flag at bit 0 (see `CAN2004_cold_start.md`) |
| 0x21F | ? | not in simulator |
| 0x220 | DOORS_STATUS | documented; not yet transmitted by simulator |
| 0x227 | ? | not in simulator |
| 0x228 | ? | not in simulator |
| 0x257 | ? | not in simulator |
| 0x260 | ? | not in simulator |
| 0x265 | ? | not in simulator |
| 0x297 | ? | not in simulator |
| 0x2A5 | ? | not in simulator |
| 0x2E1 | ? | not in simulator |
| 0x317 | ? | not in simulator |
| 0x325 | ? | not in simulator |
| 0x365 | ? | not in simulator |
| 0x3A5 | ? | not in simulator |
| 0x3A7 | ? | not in simulator |
| 0x3F6 | ? | not in simulator |

---

## Proposed New Unit Tests

Based on this comparison, the following unit tests would add meaningful coverage:

1. **`TestMsg0F6`** — verify that `decode()` reads external temperature with `× 0.5 − 40` scaling
   and that blinker bits in byte 7 are accessible (even if not yet decoded to car state)
2. **`TestMsg161OilLevel`** — verify that byte 6 (idx 6) can be decoded as oil level
3. **`TestMsg1A8SpeedControl`** — verify SET_SPEED decode: `(data[1]<<8|data[2]) * 0.01`
4. **`TestMsg128FullBeam`** — verify that full-beam maps to byte 4 (idx 4) bit 5 (`0x20`)
5. **`TestMsg128StopIndicator`** — verify STOP bit at byte 2 (idx 1) bit 6
6. **`TestMsg128DaylightBit`** — verify DAYLIGHTS bit at byte 5 (idx 4) bit 0
