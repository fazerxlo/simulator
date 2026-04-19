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

Three operating conditions:

- **Ignition off**: BSI idle frame — `08 00 00 00 00 0B 0B 00`
- **Standby** (`enabled=False`, ignition on — fan dragged to 0): workbench-verified standby frame with `byte0=0xA8`, fan nibble `0x0F`, and both zone temperatures preserved from the last active state:
  ```
  A8 00 0F 00 00 <temp_left> <temp_right> 00
  ```
- **Active** (`enabled=True`, ignition on): full climate panel state (see byte layout below).

### Byte layout (active mode)

| Byte | Meaning                                                                 |
|------|-------------------------------------------------------------------------|
| 0    | Mode byte — see table below                                             |
| 1    | Constant `0x00`                                                         |
| 2    | Fan speed raw value (see [Fan encoding](#fan-encoding))                 |
| 3    | High nibble = left zone air distribution, low nibble = right zone       |
| 4    | Bit 5 = explicit non-auto intake mode (`intake_explicit`), Bit 4 = recirculation (`recycle`) |
| 5    | Left zone temperature index (see [Temperature index](#temperature-index)) |
| 6    | Right zone temperature index                                            |
| 7    | Constant `0x00`                                                         |

### Byte 0 — mode flags

| Value  | Condition                                        |
|--------|--------------------------------------------------|
| `0x08` | AUTO mode (`auto=1`)                             |
| `0x28` | Manual mode (`auto=0`) — `0x08 \| 0x20` (manual distribution bit) |
| `0x19` | Front demist active — `0x08 \| 0x11`             |
| `0xA8` | **Standby** — `0x80 \| 0x20 \| 0x08` (fan=0, ignition on) |

### Workbench example frames

| Frame (hex)                       | Condition                                            |
|-----------------------------------|------------------------------------------------------|
| `08 00 02 00 00 0B 0B 00`         | AUTO mode, fan 3, both zones 21°C, both dir=auto     |
| `28 00 02 42 00 08 0A 00`         | Manual mode, left dir=up(4), right dir=down(2)       |
| `28 00 02 42 20 08 0A 00`         | Explicit Fresh, manual, left dir=up(4)               |
| `28 00 02 42 30 08 0A 00`         | Explicit Recirc, manual, left dir=up(4)              |
| `19 00 02 11 20 08 0A 00`         | Front demist active                                  |
| `A8 00 0F 00 00 0B 0B 00`         | Standby (fan=0), both zone temps preserved at 21°C   |

---

## `0x1E3` — Climate EMF/display state

**Period:** 200 ms.

Three operating conditions:

- **Ignition off**: `1C 40 0B 0B 00 00 00 00`
- **Standby** (`enabled=False`, ignition on): byte 0 = `(ac << 4) | 0x20 | dual`, fan nibble `0x0F`, zone temperatures preserved:
  ```
  <(ac<<4)|0x20|dual>  <0x30|(unfrost_front<<7)>  <temp_left>  <temp_right>  00 00 0F 00
  ```
  Example: ac=1, dual=0 → byte0 = `0x30` (0x10|0x20|0); ac=1, dual=1 → byte0 = `0x31` (0x10|0x20|1)
- **Active** (`enabled=True`, ignition on): full climate EMF state (see byte layout below).

### Byte layout (active mode)

| Byte | Encoding                                                           |
|------|--------------------------------------------------------------------|
| 0    | `(ac << 4) \| mode_bits \| dual` — see table below                |
| 1    | `0x30 \| (unfrost_front << 7)`                                     |
| 2    | `clim.bits \| temp_left` (bits 0–4 = left temperature index)       |
| 3    | Right zone temperature index                                       |
| 4    | Left zone air distribution in high nibble (`dir_left << 4`)        |
| 5    | Right zone air distribution in high nibble (`dir_right << 4`)      |
| 6    | Fan speed raw value (see [Fan encoding](#fan-encoding))             |
| 7    | Constant `0x00`                                                    |

### Byte 0 — mode flags

`mode_bits` depends on auto and explicit intake state:
- `0x0C` when `auto=1` (bits 2 and 3 both set — AUTO indicator)
- `0x04` when `auto=0` and an explicit intake mode was selected by the user (bit 2 = explicit non-AUTO intake)
- `0x00` when `auto=0` and intake mode was not explicitly set (e.g. after raising fan from standby)

Bit 7 (`0x80`) is the recirculation indicator — set when `recycle=1`.

```python
if clim.auto:
    mode_bits = 0x0C
elif clim.intake_explicit:
    mode_bits = 0x04
else:
    mode_bits = 0x00
recirc_bit = 0x80 if clim.recycle else 0x00
# Recirc/explicit-fresh always encode ac=0 in frame (workbench-verified)
if clim.auto or clim.unfrost_front or not clim.intake_explicit:
    ac_enc = clim.ac
else:
    ac_enc = 0
byte0 = recirc_bit | (ac_enc << 4) | mode_bits | clim.dual
```

### Bit 1 — one-shot MFD notification (`intake_notify`)

When the user presses **Recirc** or **Fresh**, the real BSI sends exactly **one** frame with bit 1 (`0x02`) set in byte 0. This single frame triggers the MFD popup message:
- Recirc entry: `0x87 = 0x85 | 0x02` → popup "Cabin air recycling activated"
- Fresh entry: `0x07 = 0x05 | 0x02` → popup "Forced intake of outside air"

The simulator replicates this via a one-shot `clim.intake_notify` flag:
1. `on_airflow_mode('recirc'/'fresh')` sets `clim.intake_notify = True`
2. The next `Msg1E3.encode()` call includes `0x02` in byte 0 **and immediately clears** `intake_notify`
3. Subsequent frames return to the stable value (`0x85` / `0x05`) without the notification bit

| Value  | ac | auto | intake_explicit | recycle | dual | Condition                        |
|--------|----|------|-----------------|---------|------|----------------------------------|
| `0x1C` | 1  | 1    | —               | 0       | 0    | Auto mode, single zone           |
| `0x1D` | 1  | 1    | —               | 0       | 1    | Auto mode, dual zone             |
| `0x10` | 1  | 0    | 0               | 0       | 0    | Implicit manual, single zone     |
| `0x11` | 1  | 0    | 0               | 0       | 1    | Implicit manual, dual zone       |
| `0x05` | 0  | 0    | 1               | 0       | 1    | Explicit Fresh, ac=off, dual     |
| `0x85` | 0  | 0    | 1               | 1       | 1    | Explicit Recirc, ac=off, dual    |
| `0x0C` | 0  | 1    | —               | 0       | 0    | A/C off, auto mode               |

> **Note**: `intake_explicit` is set when the user presses Fresh, Recirc, or UnfrostFront explicitly.
> It is cleared when AUTO mode is selected or climate is fully reset (ON button off).
> Raising the fan from standby does **not** set `intake_explicit`.
> Pressing a **direction button** while AUTO is active also does **not** set `intake_explicit` —
> it exits AUTO silently (no popup) and enters implicit manual mode.

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
| `clim_on`           | ON            | Toggles `clim.enabled`; when off resets direction, fan, airflow mode (but preserves `ac`, `dual`, and zone temperatures) |
| `ac_on`             | A/C           | Toggles `clim.ac` (A/C compressor); reflected in `0x1E3` byte 0 bit 4 |
| `dual`              | dual          | Toggles `clim.dual`; also auto-enabled when right zone temperature is changed independently, or when right zone direction is changed |
| `unfrost_rear`      | unfrost rear  | Toggles `clim.unfrost_rear` (rear demist)                 |
| `mode_auto`         | AUTO          | **Mutex group** — sets `auto=1`, resets both direction zones to 0x00 (auto), forces `ac=1` |
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
- Pressing any other direction button (e.g. Up, Dwn) **automatically exits AUTO mode** (enters implicit manual/fresh state) and applies the chosen direction. No circulation popup is shown — this mirrors real climate panel behaviour.
- Exiting AUTO via a direction button does **not** set `intake_explicit` and does **not** trigger the MFD popup (no `intake_notify`).

### A/C compressor and airflow mode

`clim.ac` represents the user's A/C compressor preference and is **not** forced off when recirc or fresh is selected. The physical A/C button state is preserved independently of the airflow mode.

However, `Msg1E3.encode` encodes **ac=0 in byte0** (bit 4 = 0) whenever recirc or explicit-fresh is active (workbench-verified: `0x85` for recirc, `0x05` for fresh). AUTO mode and front-unfrost use `clim.ac` as-is.

```
Effective ac encoding in 0x1E3 byte0:
  AUTO or unfrost_front        → clim.ac  (user preference)
  explicit recirc / fresh      → 0        (workbench-verified, regardless of clim.ac)
```

### Temperature controls

Left zone `+`/`−` buttons adjust `clim.temp_left`.

- When **DUAL** mode is off (single-zone / mono mode), changing the left temperature also syncs `clim.temp_right` to the same value (real panel mono behaviour).
- Right zone `+`/`−` buttons adjust `clim.temp_right` and **automatically enable dual mode** (`clim.dual = 1`) if it is not already active.

### Fan slider

The fan slider maps UI values 0–8 to the raw CAN nibble via the [Fan encoding](#fan-encoding) table.

- **Dragging fan to 0** suspends climate (`enabled=False`) but **preserves all settings** (ac, dual, direction, temps, recycle, unfrost).  The CAN frames switch to the standby encoding.
- **Raising fan from 0** re-enables climate (`enabled=True`), exits AUTO mode (enters manual/fresh distribution), and resumes with the previously preserved settings.
- **Changing fan while AUTO is active** automatically exits AUTO mode (`auto=0`) before applying the new fan level.

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

**Entering dual mode:** Dual mode is automatically activated when:
- The **right zone temperature** is adjusted via the UI (`on_temp(zone=1)`)
- The **right zone air direction** is changed via the UI (`on_dir(seat=1, ...)`)
- The **DUAL** button is pressed directly

Once dual=1, the next `0x1E3` byte 0 transitions to `0x1D` (auto=1, dual=1). After that, left and right zones are independently tracked.

---

## Standby / fan=0 behaviour

Setting the fan slider to 0 puts climate into **standby**:
- `clim.enabled = False`; CAN frames switch to the standby encoding (see `0x1D0` and `0x1E3` standby rows above)
- `ac`, `dual`, `dir_left`, `dir_right`, `temp_left`, `temp_right`, `recycle`, `unfrost_front`, `unfrost_rear` are **all preserved**
- Raising the fan from 0 re-enables climate (`enabled=True`), automatically exits AUTO mode, and resumes with all preserved settings

**Pressing the ON button to off** (`on_clim_on('normal')`) performs a fuller reset:
- `fan=0`, `dir_left=0`, `dir_right=0`, `auto=0`, `unfrost_front=0`, `unfrost_rear=0`, `recycle=0`
- `ac` and `dual` are preserved (they represent personal preferences)
- Zone temperatures are preserved

---

## Workbench-verified scenario sequence

The following sequence was captured from a real Peugeot 407 bench and is used to verify the simulator.

1. **Climate on** — `0x1E3[0] = 0x1C` (auto=1, ac=1, dual=0), all directions `0x00` (auto), fan standby
2. **Fan up to level 3** — exits AUTO → manual mode; `0x1D0[0] = 0x28`, `0x1D0[2] = 0x02`, `0x1E3[6] = 0x02`, `0x1E3[0] = 0x10`
3. **Air direction left → Up** — `0x1E3[4] = 0x40`, `0x1D0[3] = 0x40`
4. **Air direction right → Dwn** — auto-enables dual; `0x1E3[5] = 0x20`, `0x1D0[3] = 0x42`, `0x1E3[0] = 0x11` (dual=1)
5. **Right temp +1** — `0x1E3[0] = 0x11` (already dual), temp_right increments
6. **Front demist on** — `0x1D0[0] = 0x19`, `0x1E3[1] = 0xB0`, `0x1D0[4] |= 0x10`
7. **Recirc on** — `0x1D0[4] |= 0x20` (bit 5 set), `0x1D0[0] = 0x28`
8. **Fresh (outside air)** — `0x1D0[4] &= ~0x20` (bit 5 cleared)
