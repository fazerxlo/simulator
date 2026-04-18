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

These items have contradictory documentation from two or more sources.  A
single bench capture is enough to pick the correct interpretation.

---

### 1.1  0x0B6 RPM encoding — 13-bit shift vs ×10 multiplier

**Conflict:** autowp documents a 13-bit raw-RPM packed into bits 15-3 of the
first 16-bit word (`raw_rpm << 3`).  The simulator uses RPM × 10 as a plain
uint16 big-endian (`rpm * 10`).

For 800 RPM:
- autowp: `800 << 3 = 0x1900` → bytes `0x19 0x00`
- Simulator: `800 × 10 = 8000 = 0x1F40` → bytes `0x1F 0x40`

**Bench action:** with the engine running at a known idle RPM (read from the
cluster tacho), capture `0x0B6` and decode bytes 0-1.

```bash
candump -L can0 | grep " 0B6 " > logs/YYYYMMDD_rpm_idle.log
```

**Decode:**

```python
raw = (data[0] << 8) | data[1]
rpm_autowp = raw >> 3          # 13-bit right-shifted
rpm_sim    = raw / 10.0        # ×10 scale
# Compare with tacho reading
```

**Expected:** one of the two values will match the cluster display; record which.

**Reference:** `CAN2004_autowp_comparison.md` §0x0B6

---

### 1.2  0x1D0 fan speed byte position

**Conflict:** autowp places fan speed as a 3-bit value `FFF` in byte 2
**bits 3-1** (`byte_value = fan_speed << 1`).  The simulator writes fan speed
as the raw 0-7 integer into the **full byte 2**.

For fan level 3:
- autowp: `3 << 1 = 0x06`
- Simulator: `0x03`

**Bench action:** set the climate panel to a known fan level (e.g. level 3)
and capture `0x1D0` byte 2 (0-indexed).

```bash
candump -L can0 | grep " 1D0 " > logs/YYYYMMDD_clim_fan.log
```

**Decode:**

```python
byte2 = data[2]
fan_autowp = (byte2 >> 1) & 0x07
fan_sim    = byte2 & 0x07
# Compare with panel display
```

**Reference:** `CAN2004_autowp_comparison.md` §0x1D0

---

### 1.3  0x1D0 air direction encoding — 3-bit DDD vs repeated nibble

**Conflict:** autowp shows a single 3-bit `DDD` field in byte 3 bits 7-5.
The simulator encodes direction as a **repeated nibble**: `(dir << 4) | dir`.

For direction value 4 (Up):
- autowp: `0x80` (bit 7 set)
- Simulator: `0x44` (nibble 4 repeated)

**Bench action:** step through air direction positions on the climate panel and
capture `0x1D0` byte 3 for each position.

```bash
candump -L can0 | grep " 1D0 " > logs/YYYYMMDD_clim_dir_<position>.log
```

Record byte 3 for each direction.  Compare with both decode formulas above.

**Reference:** `CAN2004_autowp_comparison.md` §0x1D0

---

### 1.4  0x0F6 coolant temperature offset — raw−40 vs raw−39

**Conflict:** PSA-RE says `coolant_°C = raw − 40`.  autowp says `coolant_°C =
raw − 39` (1 °C off).

**Bench action:** with a warm engine at a known coolant temperature (read from
the cluster gauge or a scan tool), capture `0x0F6` byte 1 and test both formulas.

```bash
candump -L can0 | grep " 0F6 " | head -5
```

**Decode:**

```python
raw = data[1]
t_psare  = raw - 40
t_autowp = raw - 39
# Compare with cluster reading
```

**Expected:** PSA-RE (`raw − 40`) is treated as authoritative; confirm or note
any discrepancy.

**Reference:** `CAN2004_autowp_comparison.md` §0x0F6, `CAN2004_0x0F6.md`

---

### 1.5  0x1D0 climate temperature scale start — 14 °C vs 15 °C at index 1

**Conflict:** the simulator temperature lookup table begins at 15 °C for index 1.
PSA-RE shows index 1 = **14 °C**.

**Bench action:** set left zone to the lowest available temperature and read
byte 5 of `0x1D0`.  If the index is `0x01` compare with both 14 °C and 15 °C.

```bash
candump -L can0 | grep " 1D0 " > logs/YYYYMMDD_clim_temp_lo.log
```

**Decode:**

```python
index = data[5] & 0x1F   # bits 4-0
temp_sim   = 15 + (index - 1) * 0.5
temp_psare = 14 + (index - 1) * 0.5
```

**Reference:** `PSA_RE_comparison.md` §0x1D0

---

## Category 2 — Observed frames, unverified bit assignments

These frames are seen on the bus but their individual bit assignments have not
been verified against a known physical state on this vehicle.

---

### 2.1  0x220 extended body openings — hood, rear window, fuel flap

**Current state:** autowp and PSA-RE agree on bits 7-3 (four doors + trunk).
The simulator also encodes bit 2 (hood), bit 1 (rear window), bit 0 (fuel flap)
based on the PSA-RE `DOOR_STATUS` map, but these have not been verified on the
bench.

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

**Current state:** older workspace notes treat `0x131` as a door-state frame
(byte 1 bits 0-5 = FL, FR, RL, RR, bonnet, tailgate).  The canbox source and
autowp treat it as CD-changer command traffic.  The observed dump shows mostly
byte 0 activity with byte 1 staying zero, which does not fit the door mapping.

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

**Decode:**

```python
wipers = (data[7] >> 6) & 1   # 1 = wiping
```

**Reference:** `CAN2004_0x0F6.md`

---

### 2.4  0x0F6 external temperature byte 5 vs byte 6 (filtered lag)

**Current state:** PSA-RE describes byte 5 as the raw external temperature and
byte 6 as a BSI-filtered (damped) version of the same signal.  The simulator
sends the same value in both positions.  It is unknown how quickly byte 6 tracks
byte 5 on a real vehicle.

**Bench action:** move the temperature sensor (or use a hair dryer / cold spray
if available) to create a rapid temperature change.  Log `0x0F6` bytes 5 and 6
over ~30 s.

```bash
candump -L can0 | grep " 0F6 " > logs/YYYYMMDD_ext_temp_ramp.log
```

**Decode:**

```python
t_raw  = data[5] * 0.5 - 40.0
t_filt = data[6] * 0.5 - 40.0
```

Record both values over time.  If they track identically → single-source.  If
byte 6 lags → filter constant is measurable.

**Reference:** `CAN2004_0x0F6.md` §Open Questions, `PSA_RE_comparison.md` §0x0F6

---

### 2.5  0x0F6 cluster indicator test (byte 7 bit 3)

**Current state:** PSA-RE shows `CLUSTER_INDICATORS_TEST` (bit 3) in byte 7.
It is unknown whether the BSI sets this during the normal instrument lamp test
at ignition-on, or only when a diagnostic sequence requests it.

**Bench action:** capture `0x0F6` during the ignition-on lamp test (first ~2 s
after turning the key).  Check whether bit 3 of byte 7 is ever set to 1.

```bash
candump -L can0 > logs/YYYYMMDD_ignition_lamptest.log
# analyse byte 7 of 0x0F6
grep " 0F6 " logs/YYYYMMDD_ignition_lampttest.log | \
    awk '{print $9}' | sort -u
```

**Reference:** `CAN2004_0x0F6.md` §Open Questions

---

### 2.6  0x1A8 cruise / limiter state and partial odometer

**Current state:** the simulator now emits `0x1A8` with the correct PSA-RE
layout, but it has not been verified against a real cruise-control engagement on
this bench.

**Bench action:** engage cruise control at a fixed speed and capture `0x1A8`.

```bash
candump -L can0 | grep " 1A8 " > logs/YYYYMMDD_cruise_engaged.log
```

**Decode:**

```python
ctrl_type   = (data[0] >> 6) & 0x03   # 1=regulator, 2=limiter
status      = (data[0] >> 3) & 0x07   # 1=active
set_speed   = ((data[1] << 8) | data[2]) * 0.01   # km/h
partial_odo = ((data[5] << 16) | (data[6] << 8) | data[7]) * 0.001  # km
```

Confirm that `set_speed` matches the displayed cruise setpoint and that
`partial_odo` increments as the car moves.

**Reference:** `CAN2004_0x1A8.md`, `PSA_RE_comparison.md` §0x1A8

---

### 2.7  0x361 vehicle feature availability bits

**Current state:** the frame is observed on the bus (`01 01 91 40 30 10`) but
individual capability bits have not been mapped to this vehicle's option list.

**Bench action:** log `0x361` at ignition-on and verify selected bits against
known options.

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

## Category 3 — Period mismatches

The simulator runs these frames at a shorter period than the real BSI.  This
usually does not affect bench behaviour but should be confirmed and noted.

| Frame | Simulator period | PSA-RE / real bus period | Action |
|-------|-----------------|--------------------------|--------|
| `0x0F6` | 100 ms | 500 ms | candump timestamp diff |
| `0x161` | 100 ms | 500 ms | candump timestamp diff |
| `0x221` | 100 ms | 1000 ms | candump timestamp diff |
| `0x2A1` | 100 ms | 1000 ms | candump timestamp diff |
| `0x336` / `0x3B6` / `0x2B6` | 100 ms | ~1000 ms | candump timestamp diff |

**How to measure:**

```bash
candump can0 | grep " 0F6 "   # timestamp in first column
# measure delta between consecutive lines (should be ~500 ms for real BSI)
```

If on a mixed bench (simulator + real BSI) a period mismatch causes the real
module to behave differently, adjust the simulator period in `can_runner.py`.

---

## Category 4 — Cold-start and power-sequence unknowns

These questions come from analysing `power_on_and_ignition_on.csv`.  They
require targeted passive captures.

---

### 4.1  0x036 D5 power-mode sequence

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

### 4.2  0x52D byte meanings

**Observation:** `0x52D` is all-zero pre-ignition; bytes D1 and D5 both flip to
`0x01` at ignition-on.

**Bench action:** capture `0x52D` across ignition-on and ignition-off transitions
to confirm the pattern, then check whether the simulator emits this frame.

```bash
candump -L can0 | grep " 52D " > logs/YYYYMMDD_52D.log
```

**Reference:** `CAN2004_cold_start.md` §4

---

### 4.3  0x190 D4 upper nibble meaning

**Observation:** D4 upper nibble is constant `0x7` (= `0111b`), while the lower
nibble alternates `0x7 ↔ 0xE` as a rolling counter.  The upper nibble purpose
is unknown.

**Bench action:** log `0x190` across different ignition states.  Check if the
upper nibble ever changes (e.g. to `0x0` when engine is started or a fault is
present).

```bash
candump -L can0 | grep " 190 " > logs/YYYYMMDD_190.log
```

**Reference:** `CAN2004_cold_start.md` §4

---

### 4.4  0x110 purpose

**Observation:** `0x110` is active at 100 ms from the moment the bench has
power (even before ignition).  Data is always `FF FF FF FF 00 00 00 00`.

**Question:** is this a keep-alive heartbeat, a module-present advertisement,
or something else?

**Bench action:** check whether `0x110` disappears when a specific module is
disconnected.  If it changes when ignition goes off it likely belongs to the BSI
or gateway.

```bash
python -m tools.can_sniff_ai_agent identify "any state change on 0x110" \
    --duration 10 --interface can0
```

**Reference:** `CAN2004_cold_start.md` §3 and §7

---

### 4.5  0x1E1 steering-wheel column status

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

## Category 5 — Not-yet-implemented frames worth confirming on this bench

These frames are documented in autowp or PSA-RE but not implemented in the
simulator.  The goal here is to confirm whether they are actually present and
useful on the 407 workbench.

---

### 5.1  0x276 — Date, time, and average speed

autowp documents this for C4 B7 and newer trims.  It may not be present on all
407 variants.

**Bench action:** log the bus and grep for `0x276`.  If present, decode per the
autowp layout (see `CAN2004_autowp_comparison.md` §New data).

```bash
candump -L can0 | grep " 276 "
```

---

### 5.2  0x39B — Set system date/time (Display → BSI)

The MFD display sends this to update the BSI clock.  Verify it appears when the
user sets the time via the MFD menu.

```bash
python -m tools.can_sniff_ai_agent identify "set clock via MFD menu" \
    --duration 10 --interface can0
```

---

### 5.3  0x0E6 — Wheels rotation and voltage

autowp documents `0x0E6` as wheel rotation counts and battery voltage.  It is
not implemented in the simulator.  Confirm whether it appears on this bench and
what the voltage encoding is.

```bash
candump -L can0 | grep " 0E6 " | head -5
```

---

### 5.4  0x0E2 / 0x162 / 0x1A0 / 0x1A2 / 0x1E2 — Yatour / CD-changer frames

These are CD-changer and Yatour-specific frames.  Verify whether they are
present on this bench with its real CD changer.

```bash
for ID in 0E2 162 1A0 1A2 1E2; do
    echo "=== $ID ==="
    candump -L can0 | grep " $ID " | head -3
done
```

---

### 5.5  0x21F — Steering wheel multimedia remote (alternate frame)

Some PSA vehicles use `0x21F` (3-byte) instead of or in addition to `0x3E5`
(6-byte).  The 407 is believed to use `0x3E5` only, but this should be
confirmed.

```bash
python -m tools.can_sniff_ai_agent identify "steering wheel volume button" \
    --duration 5 --interface can0
# check if 0x21F or only 0x3E5 changes
```

---

## Category 6 — Gauge and sensor verification

These items need a known physical reference value to verify the decode formula.

---

### 6.1  0x161 oil level (byte 6)

PSA-RE added `OIL_LEVEL` at byte 6 (idx 6), scale 0-250 %, invalid = `0xFF`.
The simulator now sends `0xFF` (invalid) at that position.

**Bench action:** if the bench BSI has oil-level data, log `0x161` byte 6 and
check whether it reports a plausible value.

```bash
candump -L can0 | grep " 161 " | head -5
```

**Decode:**

```python
oil_level_pct = data[6] if data[6] != 0xFF else None
```

**Reference:** `PSA_RE_comparison.md` §0x161

---

### 6.2  0x0B6 bytes 4-5 trip odometer (cm) and byte 6 fuel counter

autowp documents bytes 4-5 as a uint16 trip-odometer from ignition-on in cm,
and byte 6 as a fuel-injection pulse counter.  The simulator sends `0x00 0x00 0x00`
in those positions.

**Bench action:** drive (or simulate movement) and log `0x0B6` bytes 4-5 to
confirm they increment, then calculate distance from the cm count.

```bash
candump -L can0 | grep " 0B6 " > logs/YYYYMMDD_0B6_drive.log
```

**Decode:**

```python
trip_cm     = (data[4] << 8) | data[5]
fuel_pulses = data[6]
```

**Reference:** `CAN2004_autowp_comparison.md` §0x0B6

---

## Quick reference — priority order for a single bench session

If you have limited bench time, work in this order:

1. **RPM encoding** (1.1) — one idle capture resolves a long-standing conflict
2. **0x1D0 fan byte** (1.2) — two climate panel steps
3. **0x1D0 air direction** (1.3) — step through all directions
4. **0x220 hood / fuel flap** (2.1) — physically open each
5. **0x131 door vs changer** (2.2) — open a door, watch 0x131
6. **0x0F6 wiper bit** (2.3) — turn wipers on
7. **Period measurements** (Category 3) — passive, no action needed
8. **0x036 power sequence** (4.1) — power-on without key, 30 s log
9. **Cruise/limiter** (2.6) — if bench supports it
10. **Oil level** (6.1) — passive read of 0x161 byte 6
