# CAN2004 — Climate Control (Clim module)

This document covers the three CAN frames that carry climate control state on the PSA CAN2004 bus, the UI controls available in the simulator's **Clim** tab, and the encoding rules verified against workbench captures.

---

## Overview

The **Clim** module (`modules/clim/`) manages the climate panel tab in the simulator and drives three periodic CAN frames:

| CAN ID  | Name                    | Period   | Description                          |
|---------|-------------------------|----------|--------------------------------------|
| `0x12D` | Climate command frame   | 500 ms   | Fixed capability/identity payload    |
| `0x1D0` | Climate panel state     | 500 ms   | Fan, direction, temperature, flags   |
| `0x1E3` | Climate EMF/display     | 200 ms   | Auto/dual/direction/temp for display |

All three frames are **suppressed** (or switch to a BSI standby encoding) when `car.clim.enabled` is `False` or ignition is off.

---

## `0x12D` — Climate command frame

**Period:** 500 ms — suppressed when ignition is off.

Workbench captures show this frame carries a constant payload throughout the entire climate operating scenario.  Bytes 1–2 and 6–7 appear to be fixed controller-identity or capability fields.

```
00 32 32 00 00 00 98 80
```

| Byte | Value  | Notes                          |
|------|--------|--------------------------------|
| 0    | `0x00` | Constant                       |
| 1    | `0x32` | Constant capability field      |
| 2    | `0x32` | Constant capability field      |
| 3    | `0x00` | Constant                       |
| 4    | `0x00` | Constant                       |
| 5    | `0x00` | Constant                       |
| 6    | `0x98` | Constant identity field        |
| 7    | `0x80` | Constant identity field        |

---

## `0x1D0` — Climate panel state

**Period:** 500 ms.

When `car.clim.enabled` is `False` or ignition is off, the BSI idle frame is sent:

```
08 00 00 00 00 0B 0B 00
```

When climate is active:

### Byte layout

| Byte | Meaning                                                                 |
|------|-------------------------------------------------------------------------|
| 0    | `0x08` base constant; `0x19` when front demist is active (`0x08\|0x11`) |
| 1    | Constant `0x00`                                                         |
| 2    | Fan speed raw value (see [Fan encoding](#fan-encoding))                 |
| 3    | High nibble = left zone air distribution, low nibble = right zone       |
| 4    | Bit 5 = recirculation (`recycle`), Bit 4 = front demist (`unfrost_front`) |
| 5    | Left zone temperature index (see [Temperature index](#temperature-index)) |
| 6    | Right zone temperature index                                            |
| 7    | Constant `0x00`                                                         |

### Workbench example frames

| Frame (hex)            | Condition                                |
|------------------------|------------------------------------------|
| `08 00 02 00 00 16 00 00` | Auto mode, fan 3, temp 22 (left), left/right dir=auto |
| `08 00 02 42 00 08 0A 00` | Dual mode, left dir=up(4), right dir=down(2), temp differs |
| `19 00 02 11 10 08 0A 00` | Front demist active, recirculation on |

---

## `0x1E3` — Climate EMF/display state

**Period:** 200 ms.

When `car.clim.enabled` is `False` or ignition is off, the BSI standby frame is sent:
- Ignition on, climate off: `1C 30 0B 0B 00 00 00 00`
- Ignition off: `1C 40 0B 0B 00 00 00 00`

When climate is active:

### Byte layout

| Byte | Encoding                                                           |
|------|--------------------------------------------------------------------|
| 0    | `0x14 \| (auto << 3) \| dual`                                      |
| 1    | `0x30 \| (unfrost_front << 7)`                                     |
| 2    | `clim.bits \| temp_left` (bits 0–4 = left temperature index)       |
| 3    | Right zone temperature index                                       |
| 4    | Left zone air distribution in high nibble (`dir_left << 4`)        |
| 5    | Right zone air distribution in high nibble (`dir_right << 4`)      |
| 6    | Fan speed raw value (see [Fan encoding](#fan-encoding))             |
| 7    | Constant `0x00`                                                    |

### Byte 0 — mode flags

| Value  | auto | dual | Condition              |
|--------|------|------|------------------------|
| `0x1C` | 1    | 0    | Auto mode, single zone |
| `0x1D` | 1    | 1    | Auto mode, dual zone   |
| `0x14` | 0    | 0    | Manual, single zone    |
| `0x15` | 0    | 1    | Manual, dual zone      |

---

## Fan encoding

Used in both `0x1D0` byte 2 and `0x1E3` byte 6.

| UI fan level | Raw CAN nibble |
|:---:|:---:|
| 0 (off) | `0x0F` |
| 1 | `0x00` |
| 2 | `0x01` |
| 3 | `0x02` |
| 4 | `0x03` |
| 5 | `0x04` |
| 6 | `0x05` |
| 7 | `0x06` |
| 8 | `0x07` |

---

## Temperature index

Used in `0x1D0` bytes 5–6 and `0x1E3` bytes 2–3.

| Index | Display |
|:---:|:---:|
| 0  | MIN  |
| 1  | 14°C |
| 2  | 15°C |
| 3  | 16°C |
| 4  | 17°C |
| 5  | 18°C |
| 6  | 18.5°C |
| 7  | 19°C |
| 8  | 19.5°C |
| 9  | 20°C |
| 10 | 20.5°C |
| 11 | 21°C |
| 12 | 21.5°C |
| 13 | 22°C |
| 14 | 22.5°C |
| 15 | 23°C |
| 16 | 23.5°C |
| 17 | 24°C |
| 18 | 25°C |
| 19 | 26°C |
| 20 | 27°C |
| 21 | 28°C |
| 22 | HI   |

---

## Air distribution codes

Used in `0x1D0` byte 3 (each nibble) and `0x1E3` bytes 4–5 (high nibble only).

| Code | UI button | Vents active                |
|:----:|-----------|-----------------------------|
| `0x00` | **Auto**  | Power-on default (no specific vent) |
| `0x02` | **Dwn**   | Floor / feet vents          |
| `0x03` | **Frt**   | Windscreen (front demist direction) |
| `0x04` | **Up**    | Face-level / dashboard vents |
| `0x05` | **F+D**   | Front + floor               |
| `0x06` | **U+D**   | Face + floor                |
| `0x07` | **All**   | All three vents (face + floor + front) |
| `0x08` | **Fst**   | Fast / max distribution     |

---

## UI controls

All controls in the **Clim** tab are disabled when ignition is off.

### Options bar (top row)

| Button ID           | Label         | Effect                                                    |
|---------------------|---------------|-----------------------------------------------------------|
| `clim_on`           | ON            | Toggles `clim.enabled`; when off sends BSI idle frames and resets all state |
| `ac_on`             | A/C           | Toggles `clim.ac` (A/C compressor); reflected in `0x1E3` byte 0 bit 4 |
| `dual`              | dual          | Toggles `clim.dual`; also auto-enabled when right zone temperature is changed independently |
| `unfrost_rear`      | unfrost rear  | Toggles `clim.unfrost_rear` (rear demist)                 |
| `mode_auto`         | AUTO          | **Mutex group** — sets `auto=1`, resets both direction zones to 0x00 (auto) |
| `mode_unfrost_front`| Unfrost Frt   | **Mutex group** — sets `unfrost_front=1`, clears auto and recycle |
| `mode_recirc`       | Recirc        | **Mutex group** — sets `recycle=1` (cabin recirculation), clears others |
| `mode_fresh`        | Fresh         | **Mutex group** — clears auto, unfrost_front, and recycle (outside fresh air, manual mode) |

The four `mode_*` buttons form a Kivy `group='airflow_mode'` so only one can be active at a time.
**AUTO** is selected by default on startup and when ignition returns.

> Pressing **Recirc** corresponds to "set air flow circulation on in cabin";
> pressing **Fresh** corresponds to "set air flow from outside".

**Default startup state** (after ignition on / module load):
- ON: active
- A/C: active (`clim.ac = 1`)
- DUAL: off
- UNFROST REAR: off
- AUTO: active (`clim.auto = 1`, both direction zones = 0x00)

### AUTO mode and direction grids

When **AUTO** is selected:
- Both left and right direction button grids show the **Auto** button as active.
- Pressing any other direction button (e.g. Up, Dwn) **automatically exits AUTO mode** (switches to **Fresh**) and applies the chosen direction. This mirrors the real climate panel behaviour.

### Temperature controls

Left zone `+`/`−` buttons adjust `clim.temp_left`.

- When **DUAL** mode is off (single-zone / mono mode), changing the left temperature also syncs `clim.temp_right` to the same value (real panel mono behaviour).
- Right zone `+`/`−` buttons adjust `clim.temp_right` and **automatically enable dual mode** (`clim.dual = 1`) if it is not already active.

### Fan slider

The fan slider maps UI values 0–8 to the raw CAN nibble via the [Fan encoding](#fan-encoding) table.

### Air distribution grids

Two 2-column grids (left zone and right zone) each contain eight `ToggleButton`s in a Kivy `group` so only one direction is active at a time per zone:

| Button | Code  | Vents |
|--------|-------|-------|
| Auto   | `0x00`| Default (power-on) |
| Frt    | `0x03`| Windscreen |
| Up     | `0x04`| Face level |
| U+D    | `0x06`| Face + floor |
| Dwn    | `0x02`| Floor only |
| F+D    | `0x05`| Front + floor |
| All    | `0x07`| All three vents |
| Fst    | `0x08`| Fast / max |

---

## Dual-mode behaviour

When the simulator starts with climate enabled, `clim.dual = 0`.  The `0x1E3` frame opens at `0x1C` (auto=1, dual=0).

**Mono mode (dual=0):** Changing the **left zone** temperature via the UI (`on_temp(zone=0)`) also updates `clim.temp_right` to the same value, keeping both zones in sync.  This matches the real climate panel where a single set-point governs both sides.

**Entering dual mode:** As soon as the **right zone temperature** is adjusted via the UI (`on_temp(zone=1)`), `clim.dual` is set to 1 and the next `0x1E3` byte 0 transitions to `0x1D` (auto=1, dual=1).  After that, left and right zones are independently tracked.

---

## Workbench-verified scenario sequence

The following sequence was captured from a real Peugeot 407 bench and is used to verify the simulator.

1. **Climate on** — `0x1E3[0] = 0x1C` (auto=1, dual=0), all directions `0x00` (auto), fan off
2. **Fan up to level 3** — `0x1D0[2] = 0x02`, `0x1E3[6] = 0x02`
3. **Air direction left → Up** — `0x1E3[4] = 0x40`
4. **Air direction right → Dwn** — `0x1E3[5] = 0x20`, `0x1D0[3] = 0x42`
5. **Right temp +1** — `clim.dual = 1`, `0x1E3[0] = 0x1D`
6. **Front demist on** — `0x1D0[0] = 0x19`, `0x1E3[1] = 0xB0`, `0x1D0[4] |= 0x10`
7. **Recirc on** — `0x1D0[4] |= 0x20` (bit 5 set)
8. **Fresh (outside air)** — `0x1D0[4] &= ~0x20` (bit 5 cleared)
