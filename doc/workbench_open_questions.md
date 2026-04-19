# Workbench Open Questions — What to Resolve With Real CAN Logs

This document lists every signal conflict, unverified encoding, gap, and open
question that can be closed with the Peugeot 407 workbench and a CAN log
capture on `can0` at 125 kbps.  Items are grouped by category and ordered by
how much a resolution affects the simulator's correctness.

For each item the document specifies:
- what exactly is unknown or disputed
- the physical action required on the bench
- the capture / comparison commands to run
- the decode snippet to apply to the captured data

Resolved items are marked **✅ RESOLVED** with a note on what confirmed them.

---

## How to capture and compare

```bash
# Start monitor (receive-only) session
python app.py --monitor --channel can0 --bitrate 125000

# Save a raw candump log
candump -L can0 > logs/YYYYMMDD_<topic>.log

# Compare two logs for changed IDs
python -m tools.can_sniff_ai_agent compare logs/baseline.log logs/action.log

# Identify which ID changes on a specific action (5 s window)
python -m tools.can_sniff_ai_agent identify "<action description>" \
    --duration 5 --interface can0
```

---

## Category 1 — Source conflicts (highest priority)

These items had contradictory documentation from two or more sources.

---

### 1.1  0x0B6 RPM encoding — 13-bit shift vs ×10 multiplier

**✅ RESOLVED** — Workbench combine verification confirmed the 13-bit shift
encoding (`rpm << 3`).  The simulator was updated in `Msg0B6.encode()` to use
`int(car.bsi.rpm) << 3`.  The real-car dump (`dump_real_car.csv`) further
confirmed the decode by cross-checking `0xD900 >> 3 = 6912 RPM` against bench
behaviour.

**Reference:** `CAN2004_autowp_comparison.md` §0x0B6, `CAN2004_real_car_dump.md` §0x0B6

---

### 1.2  0x1D0 fan speed raw encoding

**✅ RESOLVED** — Workbench captures confirmed the fan raw nibble encoding
used in the simulator: `0x0F` = fan off; `0x00`–`0x07` = levels 1–8.  This
differs from both the simple 0-7 integer and the autowp left-shifted value.
The `_encode_clim_fan()` helper in `can_messages.py` reflects this.

**Reference:** `CAN2004_clima.md` §Fan encoding

---

### 1.3  0x1D0 air direction encoding — 3-bit DDD vs repeated nibble

**✅ RESOLVED** — Workbench captures confirmed the repeated-nibble format:
byte 3 = `(dir_left << 4) | dir_right`.  The autowp single 3-bit `DDD` field
is specific to a different climate-panel variant.

**Reference:** `CAN2004_clima.md` §Byte layout

---

### 1.4  0x0F6 coolant temperature offset — raw−40 vs raw−39

**Status: open** — PSA-RE says `coolant_°C = raw − 40`; autowp says
`raw − 39`.  The real-car dump confirmed the formula works for observed
values but did not include an independent cluster-readout reference.

**Bench action:** with the engine warm and the cluster showing a specific
coolant temperature, capture `0x0F6` byte 1 and apply both formulas.

```bash
candump -L can0 | grep " 0F6 " | head -5
```

```python
raw = data[1]
t_psare  = raw - 40
t_autowp = raw - 39
# Compare with cluster reading
```

**Reference:** `CAN2004_autowp_comparison.md` §0x0F6, `CAN2004_0x0F6.md`

---

### 1.5  0x1D0 climate temperature scale — index 1 = 14 °C vs 15 °C

**✅ RESOLVED** — PSA-RE value confirmed: index 1 = 14 °C.  The temperature
lookup table in `modules/clim/__init__.py` was corrected accordingly.
Full table is documented in `CAN2004_clima.md` §Temperature index.

**Reference:** `CAN2004_clima.md` §Temperature index

---

## Category 2 — Observed frames, unverified bit assignments

These frames are seen on the bus but individual bit assignments have not yet
been verified against a known physical state on this vehicle.

---

### 2.1  0x220 extended body openings — hood, rear window, fuel flap

**Current state:** autowp and PSA-RE agree on bits 7-3 (four doors + trunk).
The simulator also encodes bit 2 (hood), bit 1 (rear window), bit 0 (fuel flap)
from the PSA-RE `DOOR_STATUS` map, but these have not been verified on the bench.

**Note from PSA-RE:** the rear window bit (bit 1) is only present on SW (estate)
variants.  A 407 saloon may never set this bit.

**Bench actions:**

| Action | Expected byte 0 change |
|--------|----------------------|
| Open bonnet / hood | bit 2 → 1 (byte value += 0x04) |
| Open fuel filler flap | bit 0 → 1 (byte value += 0x01) |
| Open rear window (SW only) | bit 1 → 1 (byte value += 0x02) |

```bash
candump -L can0 | grep " 220 " > logs/YYYYMMDD_doors_baseline.log
# perform action
candump -L can0 | grep " 220 " > logs/YYYYMMDD_doors_hood.log
python -m tools.can_sniff_ai_agent compare logs/YYYYMMDD_doors_baseline.log \
    logs/YYYYMMDD_doors_hood.log
```

**Reference:** `CAN2004_doors.md`, `CAN_messages.md` §0x220

---

### 2.2  0x131 — door state vs CD-changer traffic

**Current state:** older workspace notes treat `0x131` as a door-state frame.
The canbox source and autowp treat it as CD-changer command traffic.  The
observed dump shows mostly byte 0 activity with byte 1 staying zero, which
does not fit the door mapping.

**Bench action:** open and close individual doors while monitoring `0x131`.

```bash
python -m tools.can_sniff_ai_agent identify "open front left door" \
    --duration 5 --interface can0
```

If `0x131` byte 1 changes when a door opens → door interpretation is partially
correct.  If `0x131` does not change at all → it is infotainment-only traffic
on this vehicle.  Prefer `0x220` if it is already changing correctly (see 2.1).

**Reference:** `CAN_messages.md` §0x131

---

### 2.3  0x0F6 byte 7 wiper status (bit 6)

**Current state:** PSA-RE says bit 6 of byte 7 = `FRONT_WIPERS_STATUS`
(0=not wiping, 1=wiping).  It is decoded in the frame but not stored as a
dedicated state field, and it is unknown whether the MFD reacts to it.

**Bench action:** enable front wipers and capture `0x0F6` byte 7.  Also check
whether the MFD shows any wiper indicator or menu.

```bash
python -m tools.can_sniff_ai_agent identify "wiper on" \
    --duration 5 --interface can0
```

```python
wipers = (data[7] >> 6) & 1   # 1 = wiping
```

**Reference:** `CAN2004_0x0F6.md`

---

### 2.4  0x0F6 external temperature byte 5 vs byte 6 (filtered lag)

**Partially answered** — The real-car dump shows bytes 5 and 6 diverge
significantly on a bench because the external sensor is physically absent and
byte 6 retains the last EEPROM-stored filtered value from the previous drive.
On a moving vehicle with the sensor connected the lag behaviour has not yet
been measured.

**Bench action (driving vehicle only):** create a rapid temperature change and
log `0x0F6` bytes 5 and 6 over ~30 s to measure the filter time constant.

```bash
candump -L can0 | grep " 0F6 " > logs/YYYYMMDD_ext_temp_ramp.log
```

```python
t_raw  = data[5] * 0.5 - 40.0
t_filt = data[6] * 0.5 - 40.0
```

**Reference:** `CAN2004_real_car_dump.md` §0x0F6, `CAN2004_0x0F6.md`

---

### 2.5  0x0F6 cluster indicator test (byte 7 bit 3)

**Current state:** PSA-RE shows `CLUSTER_INDICATORS_TEST` (bit 3) in byte 7.
It is unknown whether the BSI sets this during the normal instrument lamp test
at ignition-on, or only when a diagnostic sequence requests it.

**Bench action:** capture `0x0F6` during the ignition-on lamp test (first ~2 s
after turning the key).  Check whether bit 3 of byte 7 is ever set to 1.

```bash
candump -L can0 > logs/YYYYMMDD_ignition_lamptest.log
grep " 0F6 " logs/YYYYMMDD_ignition_lamptest.log | \
    awk '{print $9}' | sort -u
```

**Reference:** `CAN2004_0x0F6.md` §Open Questions

---

### 2.6  0x1A8 cruise / limiter state and partial odometer

**✅ RESOLVED** — The real-car dump (`dump_real_car.csv`) confirmed the PSA-RE
byte layout.  The partial odometer value of 40.96 km was read back correctly,
showing the BSI retains partial trip across power cycles.  `Msg1A8.encode()`
and `Msg1A8.decode()` are confirmed correct.

**Reference:** `CAN2004_real_car_dump.md` §0x1A8, `CAN2004_0x1A8.md`

---

### 2.7  0x361 vehicle feature availability bits

**Current state:** the frame is observed on the bench bus (`01 01 91 40 30 10`)
but was **absent** in the real-car dump, suggesting it may only appear at a
specific startup phase or may not be present on all 407 trim levels.

**Bench action:** log `0x361` across a full ignition-on cycle and verify
selected bits against known vehicle options.

```bash
candump -L can0 | grep " 361 " | head -3
```

Check:
- byte 0 bits 2-0: active profile number
- byte 2 bit 7: door selectivity option (factory-configured)
- byte 2 bit 2: EPB auto option
- byte 4 bit 6: DRL option present
- byte 5 bits 6-4: TPMS type (0=none, 1=direct gen1, …)

**Reference:** `PSA_RE_comparison.md` §0x361

---

## Category 3 — Real-car discrepancies (cosmetic but worth verifying)

These items were discovered by comparing the real-car dump against the
simulator output.  None break functional simulation but should be settled
if wire-accurate encoding is required.

---

### 3.1  0x0F6 status byte — 0x88 (simulator) vs 0x86/0x8E (real car)

**Current state:** the real-car dump shows the status byte alternates between
`0x86` and `0x8E` during warm-up (bit 3 = `MAIN_STATUS` toggling).  The
simulator sends a fixed `0x88`.

**Bench action:** capture `0x0F6` byte 0 during a cold-start and warm-up
sequence.  Record all distinct values and the temperature range at each value.

```bash
candump -L can0 | grep " 0F6 " > logs/YYYYMMDD_0F6_warmup.log
awk '{print $4, $5}' logs/YYYYMMDD_0F6_warmup.log | sort -u
```

**Decode:**

```python
config_mode       = (data[0] >> 6) & 0x03   # 2=customer
main_status       = (data[0] >> 3) & 0x03   # toggles 0↔1
gen_status        = (data[0] >> 2) & 0x01   # 1=generator ok
powertrain_status = data[0] & 0x03          # 2=running
```

**Reference:** `CAN2004_real_car_dump.md` §0x0F6

---

### 3.2  0x0B6 byte 5 and byte 7 constant values

**Current state:**

| Byte | Real car | Simulator | Meaning |
|------|---------|-----------|---------|
| 5    | `0xFF`  | `0x00`    | Unused — cosmetic difference |
| 7    | `0xA0`  | `0xD0`    | Flags byte — bits 6 and 4 differ |

Bit 6 of byte 7 (`0x40`) and bit 4 (`0x10`) are set in the real car but not
in the simulator.  Their meaning is not decoded.

**Bench action:** check whether these bits ever change (e.g. when engine
starts, reverse is engaged, or ABS is active).

```bash
candump -L can0 | grep " 0B6 " | awk '{print $9}' | sort -u
```

**Reference:** `CAN2004_real_car_dump.md` §0x0B6

---

### 3.3  0x161 bytes 4-5 — 0x00 (real car) vs 0xFF (simulator)

**Current state:** the real-car dump shows bytes 4-5 of `0x161` as `0x00 0x00`.
The simulator sends `0xFF 0xFF` (treating them as unused/invalid).

**Bench action:** log `0x161` and verify bytes 4-5 are consistently zero.
If so, update the simulator to send `0x00 0x00` for better wire accuracy.

```bash
candump -L can0 | grep " 161 " | head -5
```

**Reference:** `CAN2004_real_car_dump.md` §0x161

---

### 3.4  0x128 byte 6 bit 4 — purpose unknown

**Current state:** the real-car dump shows `0x128` byte 6 bit 4 (`0x10`) sets
alongside the `LOW_FUEL` indicator (byte 0 bit 4).  It may be a secondary fuel
warning flag or a gear-display signal.

**Bench action:** intentionally set the fuel level near-zero and watch whether
byte 6 bit 4 mirrors byte 0 bit 4, or triggers at a different threshold.

```bash
python -m tools.can_sniff_ai_agent identify "low fuel warning" \
    --duration 10 --interface can0
```

```python
b6_bit4 = (data[6] >> 4) & 1
b0_bit4 = (data[0] >> 4) & 1  # LOW_FUEL
```

**Reference:** `CAN2004_real_car_dump.md` §0x128

---

### 3.5  0x168 byte 4 bit 1 — unresolved alert

**Current state:** the real-car dump shows `0x168` byte 4 value `0x02` (bit 1
set) appearing intermittently.  The PSA-RE signal at that position is
`ALTERNATOR_FAULT` (`GENE_DEF`).  However the dump is a warm-engine capture
and alternator faults are unexpected; it may be a different signal.

**Bench action:** disable the alternator or measure battery voltage while
capturing `0x168`.  Check whether byte 4 bit 1 corresponds to a charging
system indicator on the cluster.

```bash
candump -L can0 | grep " 168 " > logs/YYYYMMDD_168.log
awk '{print $5}' logs/YYYYMMDD_168.log | sort -u   # unique byte 4 values
```

**Reference:** `CAN2004_real_car_dump.md` §0x168

---

## Category 4 — Not-yet-implemented frames seen in real-car dump

These frames appeared in the real-car dump but are not implemented in the
simulator.  Confirm their content and determine whether they need to be
added for bench realism.

---

### 4.1  0x228 — Unknown static frame

**Current state:** `0x228` appeared in the real-car dump at ~10 ms with a
constant payload `80 00 80 80 00 00 00 00`.  No PSA-RE or community source
documents this ID.

**Bench action:** capture `0x228` across different ignition states and actions
to check if it ever changes.

```bash
candump -L can0 | grep " 228 " | head -5
```

If it remains constant it is likely a module-present heartbeat.  No decode
action required until the payload varies.

**Reference:** `CAN2004_real_car_dump.md` §0x228

---

### 4.2  0x3F6 — Date/time from radio to display

**Current state:** autowp documents `0x3F6` as a date/time frame sent by the
radio to the display.  It appeared in the real-car dump with a constant 7-byte
payload.

**Bench action:** change the radio time display and observe `0x3F6`.

```bash
python -m tools.can_sniff_ai_agent identify "change time on radio display" \
    --duration 5 --interface can0
```

**Reference:** `CAN2004_autowp_comparison.md` §New data, `CAN2004_real_car_dump.md`

---

## Category 5 — Cold-start and power-sequence unknowns

These questions come from analysing `power_on_and_ignition_on.csv`.  They
require targeted passive captures.

---

### 5.1  0x036 D5 power-mode sequence

**Observation:** at bench power-on D5 = `0x02` for ~14 s, then drops to `0x00`
before the key is turned.  The transition `0x00 → 0x03 → 0x01` lasts ~40 ms.

**Question:** does `0x02` represent an ACC or battery-detect phase?  Is the
`0x00` state (settled off) something the simulator should emit when the ignition
is explicitly off?

**Bench action:** power the bench without turning the key and log `0x036` for
30 s to confirm the `0x02 → 0x00` transition and its duration.

```bash
candump -L can0 | grep " 036 " > logs/YYYYMMDD_036_powerup.log
```

**Reference:** `CAN2004_cold_start.md` §2

---

### 5.2  0x52D byte meanings

**Observation:** `0x52D` is all-zero pre-ignition; bytes D1 and D5 both flip to
`0x01` at ignition-on.

**Bench action:** capture `0x52D` across ignition-on and ignition-off transitions
to confirm the pattern, then check whether the simulator emits this frame.

```bash
candump -L can0 | grep " 52D " > logs/YYYYMMDD_52D.log
```

**Reference:** `CAN2004_cold_start.md` §4

---

### 5.3  0x190 D4 upper nibble meaning

**Observation:** D4 upper nibble is constant `0x7`, lower nibble alternates
`0x7 ↔ 0xE` as a rolling counter.  Upper nibble purpose is unknown.

**Bench action:** log `0x190` across different ignition states.  Check if the
upper nibble ever changes (e.g. when engine starts or a fault is present).

```bash
candump -L can0 | grep " 190 " > logs/YYYYMMDD_190.log
```

**Reference:** `CAN2004_cold_start.md` §4

---

### 5.4  0x110 purpose

**Observation:** `0x110` is active at 100 ms from the moment the bench has
power (even before ignition).  Data is always `FF FF FF FF 00 00 00 00`.

**Bench action:** check whether `0x110` disappears when a specific module is
disconnected.  If it changes when ignition goes off it likely belongs to the BSI
or gateway.

```bash
python -m tools.can_sniff_ai_agent identify "any state change on 0x110" \
    --duration 10 --interface can0
```

**Reference:** `CAN2004_cold_start.md` §3 and §7

---

### 5.5  0x1E1 steering-wheel column status

**Observation:** `0x1E1` shows an all-`0x80` pattern at ignition-on and changes
shortly after, but a wheel-turn test showed it remaining static.  It may be a
steering-column (not steering-angle) status frame.

**Bench action:** press each steering-wheel button while logging `0x1E1`.  Also
check `0x3E5` (already decoded) to see which frame the buttons use.

```bash
python -m tools.can_sniff_ai_agent identify "steering wheel button press" \
    --duration 5 --interface can0
```

**Reference:** `CAN2004_cold_start.md` §6

---

## Category 6 — Not-yet-implemented community-documented frames

These frames are documented in autowp or PSA-RE but not implemented in the
simulator.  The goal here is to confirm whether they are present and useful
on the 407 workbench.

---

### 6.1  0x276 — Date, time, and average speed

autowp documents this for C4 B7 and newer trims.  It may not be present on all
407 variants.

**Bench action:** log the bus and grep for `0x276`.  If present, decode per the
autowp layout (see `CAN2004_autowp_comparison.md` §New data).

```bash
candump -L can0 | grep " 276 "
```

---

### 6.2  0x39B — Set system date/time (Display → BSI)

The MFD display sends this to update the BSI clock.  Verify it appears when the
user sets the time via the MFD menu.

```bash
python -m tools.can_sniff_ai_agent identify "set clock via MFD menu" \
    --duration 10 --interface can0
```

---

### 6.3  0x0E6 — Wheel rotation and battery voltage

autowp documents `0x0E6` as wheel rotation counts and battery voltage.  It is
not implemented in the simulator.  Confirm whether it appears on this bench and
what the voltage encoding is.

```bash
candump -L can0 | grep " 0E6 " | head -5
```

---

### 6.4  0x0E2 / 0x162 / 0x1A0 / 0x1A2 / 0x1E2 — Yatour / CD-changer frames

These are CD-changer and Yatour-specific frames.  Verify whether they are
present on this bench with its real CD changer.

```bash
for ID in 0E2 162 1A0 1A2 1E2; do
    echo "=== $ID ==="
    candump -L can0 | grep " $ID " | head -3
done
```

---

### 6.5  0x21F — Steering wheel multimedia remote (alternate frame)

Some PSA vehicles use `0x21F` (3-byte) instead of or in addition to `0x3E5`
(6-byte).  The 407 is believed to use `0x3E5` only, but this should be
confirmed.

```bash
python -m tools.can_sniff_ai_agent identify "steering wheel volume button" \
    --duration 5 --interface can0
# check if 0x21F or only 0x3E5 changes
```

---

## Category 7 — Gauge and sensor verification

These items need a known physical reference value to verify the decode formula.

---

### 7.1  0x161 oil level (byte 6)

PSA-RE documents `OIL_LEVEL` at byte 6 (idx 6), scale 0-250, invalid = `0xFF`.
The simulator sends `0xFF` (invalid) at that position.  The real-car dump
showed `0x00` in all captured frames, which may mean oil-level data is not
available on a static bench.

**Bench action:** if the bench BSI has oil-level data, log `0x161` byte 6 and
check whether it reports a plausible value.

```bash
candump -L can0 | grep " 161 " | head -5
```

```python
oil_level_pct = data[6] if data[6] != 0xFF else None
```

**Reference:** `PSA_RE_comparison.md` §0x161

---

### 7.2  0x0B6 bytes 4-5 trip odometer (cm) and byte 6 fuel counter

autowp documents bytes 4-5 as a uint16 trip-odometer from ignition-on in cm,
and byte 6 as a fuel-injection pulse counter.  The simulator sends `0x00 0x00 0x00`
in those positions.

**Bench action:** with the engine running for several minutes, log `0x0B6`
bytes 4-5 to confirm they increment.

```bash
candump -L can0 | grep " 0B6 " > logs/YYYYMMDD_0B6_drive.log
```

```python
trip_cm     = (data[4] << 8) | data[5]
fuel_pulses = data[6]
```

**Reference:** `CAN2004_autowp_comparison.md` §0x0B6

---

## Quick reference — priority order for a single bench session

Items already marked ✅ RESOLVED above do not need bench time.

1. **0x0F6 coolant offset** (1.4) — one warm-engine capture with cluster readout
2. **0x220 hood / fuel flap** (2.1) — physically open each and watch 0x220
3. **0x131 door vs changer** (2.2) — open a door and watch 0x131
4. **0x0F6 wiper bit** (2.3) — turn wipers on, watch byte 7 bit 6
5. **0x0F6 status byte** (3.1) — cold-start capture to map 0x86/0x8E toggling
6. **0x128 byte 6 bit 4** (3.4) — low-fuel scenario
7. **0x168 byte 4 bit 1** (3.5) — charging system state during capture
8. **Period measurements** (Category 3 table) — passive, no action needed
9. **0x036 power sequence** (5.1) — power-on without key, 30 s log
10. **0x228 static frame** (4.1) — passive read, check for variation
