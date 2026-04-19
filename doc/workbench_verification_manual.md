# Real Workbench Verification Manual

## Purpose

This document defines the final real-bench verification procedure for the Peugeot 407 CAN2004 simulator.

The goal is to verify the simulator in both directions:

1. **Host / active simulator mode**  
   Change values in the simulator UI and confirm that the physical workbench behaves the same way as the real system.

2. **Listen / monitor mode**  
   Perform actions on the physical workbench and confirm that the simulator UI updates to match the live CAN traffic.

This is a **bench-only** validation workflow for **can0** at **125000 bit/s**.

---

## Current bench scope

Confirmed workbench components:

- Instrument cluster / combine
- MFD display
- Radio / head unit
- Climate panel
- Steering wheel controls / stalk buttons
- CD changer
- Reverse signal available

Known visible outputs:

- Combine icons and telltales
- RPM / speed / fuel / temperatures / odometer areas
- MFD climate display
- MFD time / date / outside temperature / radio / CD info
- Popups and message overlays

---

## Hardware inventory template

Fill in PSA numbers before the final sign-off run.

| Module | PSA number | Notes |
|---|---:|---|
| Instrument cluster / combine | ______ | |
| MFD display | ______ | |
| Radio / head unit | ______ | |
| Climate panel | ______ | |
| Steering wheel controls / COM unit | ______ | |
| CD changer | ______ | |

---

## Safety rules

1. Start with **monitor mode first**.
2. Capture a baseline log before any active transmission.
3. Only switch to host / active mode when the bench is stable and you expect the modules to react.
4. If the bench starts resetting, flooding, or showing unexpected errors, stop the test and save the log.

---

## Test evidence to collect

For every important test group, save:

- one CAN log
- one note about the physical result
- optional photo or short video
- pass / fail / partial result

Recommended naming:

- `logs/YYYYMMDD_baseline_<topic>.log`
- `logs/YYYYMMDD_action_<topic>.log`
- `logs/YYYYMMDD_host_<topic>.log`
- `logs/YYYYMMDD_monitor_<topic>.log`

Useful commands:

```bash
python app.py --monitor --channel can0 --bitrate 125000
python app.py --channel can0 --bitrate 125000
candump -L can0 > logs/bench_capture.log
python -m tools.can_sniff_ai_agent compare baseline.log action.log
```

---

## Pass criteria

A test is considered **PASS** only when all of the following are true:

1. **Correct CAN IDs** are present
2. **Correct payload bytes** or expected bit changes are present
3. **Timing / periodicity** is close to the reference capture
4. **Visible workbench behavior** matches the expected module behavior

### Timing tolerance

Use these target periods when comparing against the bench:

> The simulator now targets the workbench cadence with a small scheduling lead of up to about 5% to compensate for thread jitter. Slightly earlier simulator frames within that margin are acceptable.

| Frame | Typical period |
|---|---:|
| 0x0B6 | 50 ms |
| 0x036 | 100–175 ms depending on state |
| 0x128 / 0x168 / 0x1A8 / 0x1E3 | 200 ms or 100 ms depending on module/state |
| 0x0F6 / 0x1D0 / 0x161 | 500 ms |
| 0x52D / some infotainment frames | about 1000 ms |

If the visible behavior is correct but timing or one reserved byte differs, mark the case as **PARTIAL** and note the delta.

---

## Test execution order

Use this order for the final verification run:

1. Bench power-up baseline capture
2. Listen-mode verification
3. Host-mode verification
4. Action-by-action baseline vs action comparisons
5. Final regression sweep

---

# Part A — Listen mode verification

## LM-01: Power-on baseline

**Goal:** verify that the simulator UI reflects the idle bench state without transmitting.

**Mode:** monitor

**Steps:**
1. Start the app in monitor mode on can0.
2. Power the workbench with ignition off.
3. Wait 20–30 seconds.
4. Observe cluster, MFD, radio, and climate pages in the simulator.

**Expected CAN evidence:**
- 0x036 present
- 0x110 present
- 0x190 present
- 0x1D0 present
- 0x1E3 present
- 0x217 present
- 0x52D present

**Expected UI / bench alignment:**
- ignition shown as off or pre-ignition
- climate idle state visible
- no false warning overlays
- radio / display idle status stable

---

## LM-02: Ignition transition

**Goal:** verify that bench ignition changes are reflected in the simulator UI.

**Action:** move through available ignition states on the bench.

**Expected CAN evidence:**
- 0x036 byte 5 sequence should reflect power transition
- 0x217 should change from the idle pattern to the ignition-on pattern
- 0x190 should begin rolling when ignition is on
- one-shot wake frames may appear: 0x5D2, 0x5ED, 0x5E5, 0x5CC, 0x5DF, 0x5E0, 0x5F1, 0x48C

**Expected UI result:**
- ignition status updates in the simulator
- cluster-related pages wake up
- MFD / radio / climate pages become active as on the real bench

---

## LM-03: Lights and indicators from the bench

**Goal:** verify that the simulator UI reflects real switch actions.

**Actions to test:**
- left indicator
- right indicator
- sidelights
- low beam
- high beam
- front fog
- rear fog

**Known key frame:** 0x128

**Reference expectations:**
- 0x128 byte 5 carries the light state bits
- sidelights = bit 7
- low beam = bit 6
- high beam = bit 5
- front fog = bit 4
- rear fog = bit 3
- right turn = bit 2
- left turn = bit 1

**Expected UI result:**
- corresponding telltales and state selectors update in the app
- no wrong icon remains latched after the action is cleared

---

## LM-04: Climate controls from the bench

**Goal:** verify that the simulator climate UI follows the real panel.

**Actions to test:**
- fan up / down
- temperature left / right up / down
- airflow enable / disable
- air direction changes
- defrost / recycle

**Known key frames:**
- 0x1D0
- 0x1E3

**Reference expectations:**
- 0x1D0 byte 3 = fan level
- 0x1D0 byte 4 = repeated-nibble air direction code
- 0x1D0 byte 5 bit 5 = recycle
- 0x1D0 byte 5 bit 4 = front defrost
- 0x1E3 carries auto / dual / direction / temperature state

**Expected UI result:**
- fan slider and labels update
- temperature labels update
- direction buttons reflect the physical state
- front defrost does not glitch or clear incorrectly

---

## LM-05: Outside temperature and gauges from the bench

**Goal:** confirm that measured values from the bench propagate into the simulator UI.

**Items to observe:**
- outside temperature
- fuel level
- oil level if available
- RPM and speed placeholders or live values
- odometer / trip values if the bench produces them

**Known key frames:**
- 0x0F6 for outside temperature and reverse
- 0x0B6 for RPM and speed
- 0x161 for fuel / oil temperature / oil level
- 0x221, 0x2A1, 0x261 for trip data

**Reference expectations:**
- 0x0F6 external temperature = raw × 0.5 − 40
- 0x0B6 RPM = raw / 10
- 0x0B6 speed = raw / 100
- 0x161 byte 7 = oil level

---

## LM-06: Radio, source, and steering wheel buttons from the bench

**Goal:** verify that infotainment-related bench actions update the app.

**Actions to test:**
- radio volume up / down
- source change
- steering wheel arrows / OK / ESC / next / prev
- FM radio play
- CD play or CD changer actions

**Known key frames:**
- 0x1A5 for volume
- 0x165 for source / input
- 0x1E5 for audio settings
- 0x3E5 for steering wheel / radio panel buttons
- 0x225 for radio frequency-related updates

**Expected UI result:**
- source field changes correctly
- volume updates correctly
- radio and button pages reflect real button presses
- FM / CD status shown on the MFD when available

---

## LM-07: Reverse input from the bench

**Goal:** verify that reverse state is reflected in the simulator.

**Action:** trigger reverse on the workbench.

**Known key frame:** 0x0F6

**Reference expectation:**
- reverse status is carried in 0x0F6 byte 8 bit 7

**Expected UI result:**
- reverse indicator in the simulator updates
- if any dependent page reacts, it should switch accordingly

---

## LM-08: Time, date, and configuration readback

**Goal:** confirm that live workbench values appear in the simulator UI.

**Actions to test:**
- set or read time/date from the workbench
- change a configuration item if supported on the bench

**Expected result:**
- simulator display mirrors the live workbench state
- capture the CAN IDs involved and attach them to this document for the final version

**Observed IDs / notes:**
- Time/date frame(s): ______
- Configuration frame(s): ______

---

# Part B — Host / active simulator verification

## HM-01: Active startup and wake-up

**Goal:** confirm that starting the simulator in active mode wakes the bench like the real system.

**Mode:** active simulator transmit on can0

**Steps:**
1. Power the bench.
2. Start the simulator in active mode.
3. Watch the cluster and MFD during the first 5 seconds.

**Expected CAN evidence:**
- startup wake burst includes 0x5D2, 0x5ED, 0x5E5, 0x5CC, 0x5DF, 0x5E0, 0x5F1, and 0x48C
- 0x036 begins periodic transmission immediately after start

**Expected physical result:**
- workbench wakes reliably
- MFD and cluster leave the dead / sleep state
- no abnormal resets or flashing loops

---

## HM-02: Ignition and power mode from the UI

**Goal:** verify that UI ignition changes drive the bench correctly.

**UI actions:**
- ignition off
- pre-ignition / accessory
- ignition on

**Primary frames to observe:**
- 0x036
- 0x190
- 0x217
- 0x52D

**Expected result:**
- physical modules match the chosen state
- 0x036 / 0x217 payloads are aligned with the reference capture

---

## HM-03: Lighting from the UI

**Goal:** verify that cluster icons and display lighting match simulator actions.

**UI actions:**
- indicators left / right
- sidelights
- low beam
- high beam
- fog lights

**Primary frame:** 0x128

**Expected physical result:**
- correct light telltales on the cluster
- no swapped left/right indication
- no missing beam or fog icon

**Reference byte note:**
- for basic mode comparison, 0x128 byte 5 should match:
  - 0x00 = off
  - 0x80 = sidelights
  - 0xC0 = low beam
  - 0xE0 = high beam

---

## HM-04: Climate from the UI

**Goal:** verify that climate settings shown in the simulator are reproduced on the MFD / climate unit.

**UI actions:**
- fan level changes
- temperature changes
- auto / dual
- recycle
- front defrost
- air direction changes

**Primary frames:**
- 0x1D0
- 0x1E3

**Expected physical result:**
- the MFD shows matching climate values
- the panel state remains stable without flicker or incorrect resets

---

## HM-05: Outside temperature and gauges from the UI

**Goal:** verify that values emitted by the simulator match the workbench display.

**UI actions:**
- outside temperature change
- fuel level change
- oil level if exposed in the simulator
- trip values if exposed
- speed / RPM placeholders if used for testing

**Primary frames:**
- 0x0F6
- 0x0B6
- 0x161
- 0x221 / 0x2A1 / 0x261

**Expected physical result:**
- combine and MFD show the same values as the simulator UI
- displayed units and rounding are acceptable versus the real bench

---

## HM-06: Radio, CD, and steering wheel actions from the UI

**Goal:** verify that infotainment-related simulator actions drive the real radio/display correctly.

**UI actions:**
- volume up / down
- source change
- FM radio selection
- CD play / changer actions
- steering wheel button presses

**Primary frames:**
- 0x1A5
- 0x165
- 0x1E5
- 0x3E5
- 0x225

**Expected physical result:**
- volume behaves correctly
- source and radio text on the MFD are consistent
- CD information appears when the CD path is selected
- steering wheel events are recognized correctly

---

## HM-07: Reverse from the UI

**Goal:** verify that setting reverse in the simulator drives the bench response.

**UI action:** toggle reverse on and off.

**Primary frame:** 0x0F6

**Expected physical result:**
- reverse-related indication appears and clears correctly
- no unrelated warning appears

---

## HM-08: Popup and message behavior

**Goal:** verify that the MFD popup handling matches the real display.

**UI actions:**
- trigger message / popup state
- clear message / popup state

**Primary frame:** 0x1A1

**Expected physical result:**
- popup appears on the MFD with the expected priority behavior
- idle baseline frame remains stable when no popup is active

---

## HM-09: Time/date and configuration from the UI

**Goal:** verify whether simulator-driven configuration or time/date values are reflected on the bench.

**UI actions:**
- set time/date if supported in the current module set
- change available configuration items

**Expected physical result:**
- values displayed by the bench match the simulator
- if the mapping is incomplete, save a reference capture and mark the case PARTIAL

---

# Part C — Regression sweep

Run this short sweep after any code change:

- startup / wake-up
- ignition on / off
- sidelights / low beam / high beam
- left and right indicators
- climate fan and temperature
- radio volume and source
- reverse
- MFD popup stability

If any one of these regresses, do not sign off the build.

---

# Final sign-off sheet

| Test ID | Result | Notes | Log file | Photo/video |
|---|---|---|---|---|
| LM-01 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-02 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-03 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-04 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-05 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-06 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-07 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| LM-08 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-01 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-02 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-03 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-04 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-05 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-06 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-07 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-08 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |
| HM-09 | ☐ PASS ☐ FAIL ☐ PARTIAL | | | |

---

## Notes for the final version

When you repeat the captures for the final verification, append the real observed payloads for each action under the relevant test case. That will turn this from a generic manual into the signed reference procedure for your exact workbench.
