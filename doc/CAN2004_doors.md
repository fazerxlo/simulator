# CAN2004 — Doors, Boot, Bonnet and Body Openings

This document covers the two CAN frames that carry door and body-opening status on the PSA CAN2004 bus, and the popup-display integration on `0x1A1`.

---

## `0x220` — Door and Body Openings (2 bytes, primary source)

**Period:** passive — sent by BSI only when state changes (event-driven).

This is the authoritative real-time door/body status frame. Prefer this frame over any secondary door bits when it is present on the bus.

### Byte layout

| Byte | Bits | Field |
|------|------|-------|
| 0    | 7    | Front left door open |
| 0    | 6    | Front right door open |
| 0    | 5    | Rear left door open |
| 0    | 4    | Rear right door open |
| 0    | 3    | Trunk / boot lid open |
| 0    | 2    | Hood / bonnet open |
| 0    | 1    | Rear window open (**SW/estate models only** — source: PSA-RE) |
| 0    | 0    | Fuel filler flap open |
| 1    | 7    | Vehicle type (`0` = 5-door saloon/hatch, `1` = 3-door — source: PSA-RE `CAR_TYPE`) |
| 1    | 6    | Spare wheel arm status (`SPARE_WHEEL_ARM_STATUS`) |
| 1    | 5–0  | Reserved / unused |

> **Bit order note:** Bits are read right-to-left in the hardware struct (LSB = bit 0), so `bit 7` of byte 0 is the most-significant bit of the first byte.

### Example frames

| Byte 0 | Byte 1 | Meaning |
|--------|--------|---------|
| `0x00` | `0x00` | All closed |
| `0x80` | `0x00` | Front left door open |
| `0x40` | `0x00` | Front right door open |
| `0x20` | `0x00` | Rear left door open |
| `0x10` | `0x00` | Rear right door open |
| `0x08` | `0x00` | Trunk open |
| `0x04` | `0x00` | Hood open |
| `0x02` | `0x00` | Rear window open |
| `0x01` | `0x00` | Fuel filler flap open |
| `0xF8` | `0x00` | All four doors + trunk open |

### How it is used in PSACANBridge

```cpp
// CanDataConverter.cpp — Handle_220()
_dataBroker->IsFrontLeftDoorOpen  = tmp.Field1.data.front_left_door_open;
_dataBroker->IsFrontRightDoorOpen = tmp.Field1.data.front_right_door_open;
_dataBroker->IsRearLeftDoorOpen   = tmp.Field1.data.rear_left_door_open;
_dataBroker->IsRearRightDoorOpen  = tmp.Field1.data.rear_right_door_open;
_dataBroker->IsBootLidOpen        = tmp.Field1.data.trunk_open;
_dataBroker->IsHoodOpen           = tmp.Field1.data.hood_open;
_dataBroker->IsFuelFlapOpen       = tmp.Field1.data.fuel_flap_open;
_dataBroker->IsRearWindowOpen     = tmp.Field1.data.rear_window_open;
```

After storing the state, `Handle_220()` immediately re-sends `0x1A1` with the door popup so the head unit display is updated.

---

## `0x1A1` — Display Popup (8 bytes)

**CAN ID:** `0x1A1`  
**Source:** `CanDisplayStructs.h`

This frame drives the instrument cluster / VTH popup. When used for door/body notifications it carries both the human-readable popup trigger **and** the individual door open bits in bytes 3–4.

### Byte layout

| Byte | Name | Meaning |
|------|------|---------|
| 0 | `ShowPopup` | `0x80` = show (category 1), `0x81` = show (cat 2), `0x82` = show (cat 3), `0x7F` = hide, `0xFF` = clear/idle |
| 1 | `PopupMessageType` | Message ID (see table below) |
| 2 | `Field2` | Priority and display-destination flags (see below) |
| 3 | `DoorStatus1` | Individual door open bits (see below) |
| 4 | `DoorStatus2` | Fuel flap and rear screen open bits (see below) |
| 5 | `Field5` | `0x00` (reserved) |
| 6 | `KmDividedBy256` | Distance high byte (used by fuel/range messages) |
| 7 | `KmRemainderUpTo255` | Distance low byte (used by fuel/range messages, `0x00` otherwise) |

### Byte 0 — ShowPopup

| Value | Constant | Meaning |
|-------|----------|---------|
| `0x80` | `CAN_POPUP_MSG_SHOW_CATEGORY1` | Show popup, category 1 warning |
| `0x81` | `CAN_POPUP_MSG_SHOW_CATEGORY2` | Show popup, category 2 |
| `0x82` | `CAN_POPUP_MSG_SHOW_CATEGORY3` | Show popup, category 3 |
| `0x7F` | `CAN_POPUP_MSG_HIDE` | Hide / dismiss current popup |
| `0xFF` | `CAN_POPUP_MSG_CLEAR` | Clear / no popup (idle state) |

### Byte 2 — Field2 (display flags)

Bits are read right-to-left (LSB first):

| Bit | Meaning |
|-----|---------|
| 0–3 | Priority (0–14) |
| 4   | Check in progress |
| 5   | Show popup on VTH |
| 6   | Show popup on CMB (instrument cluster) |
| 7   | Show popup on EMF |

Typical door-warning value: `0xC7` = priority 7, show on VTH + CMB + EMF.

### Byte 3 — DoorStatus1

Individual door open flags. Bits are read right-to-left (LSB first):

| Bit | Meaning |
|-----|---------|
| 7   | Front right door open |
| 6   | Front left door open |
| 5   | Rear right door open |
| 4   | Rear left door open |
| 3   | Boot / trunk open |
| 2   | Bonnet / hood open |
| 1   | (reserved) |
| 0   | (reserved) |

### Byte 4 — DoorStatus2

| Bit | Meaning |
|-----|---------|
| 7   | Rear screen open |
| 6   | Fuel filler flap open |
| 5–0 | (reserved) |

### Door / body-related popup message codes (byte 1)

| Code | Constant | Description |
|------|----------|-------------|
| `0x0B` | `CAN_POPUP_MSG_DOORS_BOOT_BONNET_REAR_SCREEN_AND_FUEL_TANK_OPEN` | One or more doors/openings still open |
| `0xDE` | `CAN_POPUP_MSG_DOORS_BOOT_BONNET_REAR_SCREEN_AND_FUEL_TANK_OPEN_2` | Variant 2 of the above (vehicle-specific) |
| `0x33` | `CAN_POPUP_MSG_AUTOMATIC_DOOR_LOCKING_ACTIVATED` | Auto door-lock activated |
| `0x34` | `CAN_POPUP_MSG_AUTOMATIC_DOOR_LOCKING_DEACTIVATED` | Auto door-lock deactivated |
| `0x37` | `CAN_POPUP_MSG_CHILD_SAFETY_ACTIVATED` | Child safety (rear doors) activated |
| `0x38` | `CAN_POPUP_MSG_CHILD_SAFETY_DEACTIVATED` | Child safety deactivated |
| `0x79` | `CAN_POPUP_MSG_ACTIVE_BONNET_FAULTY` | Active bonnet fault |
| `0x86` | `CAN_POPUP_MSG_RIGHT_REAR_SLIDING_DOOR_FAULTY` | Right rear sliding door fault |
| `0x87` | `CAN_POPUP_MSG_LEFT_REAR_SLIDING_DOOR_FAULTY` | Left rear sliding door fault |
| `0xD1` | `CAN_POPUP_MSG_ACTIVE_BONNET_DEPLOYED` | Active bonnet deployed |

### Example frame — doors + boot open

Send a popup for "doors/boot open" showing front-left, rear-right and boot open:

```
Byte:  0     1     2     3     4     5     6     7
       80    0B    C7    58    00    00    00    00
```

- Byte 0 `0x80` = show category 1
- Byte 1 `0x0B` = DOORS_BOOT_BONNET... message
- Byte 2 `0xC7` = priority 7, display on CMB + VTH + EMF
- Byte 3 `0x58` = `0101 1000` → bit6=FL, bit4=RL, bit3=boot
- Byte 4 `0x00` = fuel flap and rear screen closed

To dismiss: resend with byte 0 = `0x7F`, then after ~200 ms with `0xFF`.

---

## Choosing between frames

| Scenario | Recommended frame |
|----------|-------------------|
| Simulator sending door state to head unit | `0x220` for raw status + `0x1A1` for popup |
| Monitor app observing CAN2004 bus | Subscribe to `0x220` first; fall back to `0x1A1` bytes 3–4 |
| Sliding-door fault indication | Only available via `0x1A1` popup (codes `0x86`/`0x87`) |
