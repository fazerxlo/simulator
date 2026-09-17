# CAN2004 steering-wheel key decoding

This note documents the steering-wheel key protocol seen in the provided condensed CAN log and explains how to encode and decode it.

## 1. Scope

The captured log is dominated by a 3-byte steering-wheel remote frame:

- CAN ID: `0x21F`
- DLC: `3`
- Format: `[cmd, aux, reserved]`

This is not the 6-byte `0x3E5` steering-wheel panel frame. The attached log uses `0x21F` for momentary button commands. The 6-byte `0x3E5` format is still valid for other Peugeot 407 bench layouts, but the provided trace is clearly the shorter 3-byte remote format.

The authoritative comparison note for this alternative frame is in:

- `doc/CAN2004_autowp_comparison.md`

It describes the remote as:

```
Byte 0: F B X 0 U D S 0
Byte 1: RRRRRRRR
Byte 2: 0x00
```

where:

- `U` = Volume Up
- `D` = Volume Down
- `S` = Source
- `F` = Forward / Next
- `B` = Backward / Previous

## 2. Real bit mapping from the log

The log proves the bit masks are:

| Bit mask | Meaning |
|---|---|
| `0x08` | Volume Up |
| `0x04` | Volume Down |
| `0x02` | Source |
| `0x80` | Next / Forward |
| `0x40` | Previous / Backward |
| `0x00` | Released / idle |

The first byte (`D1`) is the actual key state.

The second byte (`D2`) is not the button ID; it is a secondary / scroll / pulse counter value. In the captures it often stays near `0x09` or `0x0B` while the key is active, then returns to `0x00` on release.

That makes the practical rule:

- decode the command from `data[0]`
- ignore `data[1]` for button identity
- `data[2]` is reserved / zero in this capture

## 3. Pulse pattern seen in the log

The captured pulses follow the pattern:

- pressed: `XX,YY,00`
- released: `00,YY,00`

Examples from the log:

```text
... 08,09,00, ...
... 00,09,00, ...
```

means: volume up pressed, then released.

Similarly:

```text
... 04,09,00, ...
... 00,09,00, ...
```

means: volume down pressed, then released.

And:

```text
... 80,0B,00, ...
... 00,0B,00, ...
```

means: next / forward pressed, then released.

## 4. Decoding examples from the provided log

The attached capture contains repeated sequences like:

```text
... 08,09,00 ...
... 00,09,00 ...
... 08,09,00 ...
... 00,09,00 ...
... 08,09,00 ...
... 00,09,00 ...
```

This is 3 presses of Volume Up.

Likewise:

```text
... 04,09,00 ...
... 00,09,00 ...
... 04,09,00 ...
... 00,09,00 ...
```

This is 2 presses of Volume Down.

And:

```text
... 02,09,00 ...
... 00,09,00 ...
```

This is a Source key press.

The later part of the log contains:

```text
... 80,0B,00 ...
... 00,0B,00 ...
... 80,0B,00 ...
... 00,0B,00 ...
```

This is Next / Forward.

And:

```text
... 40,0B,00 ...
... 00,0B,00 ...
```

This is Previous / Backward.

## 5. Sequence decoded from the log

From the provided capture, the user action sequence is:

1. Volume Up × 3
2. Volume Down × 2
3. Source × 4
4. Wheel Up / Forward × 3
5. Wheel Down / Backward × 2
6. Next × 4
7. Previous × 3
8. Right press × 5

The actual values in the log map as:

- `0x08` = volume up
- `0x04` = volume down
- `0x02` = source
- `0x80` = next / forward
- `0x40` = previous / backward

The log does not contain a `0x3E5` steering-wheel panel frame. That frame would use a different layout and a different bit assignment scheme.

## 6. Python encoder / decoder

### Decoder

```python
MASK_TO_ACTION = {
    0x00: "idle",
    0x08: "volume_up",
    0x04: "volume_down",
    0x02: "source",
    0x80: "next",
    0x40: "previous",
}


def decode_21f(frame):
    """Decode a 3-byte 0x21F steering-wheel command frame."""
    if len(frame) < 3:
        return None

    cmd = frame[0]
    aux = frame[1]
    reserved = frame[2]

    if cmd == 0x00:
        return {"action": "idle", "cmd": cmd, "aux": aux, "reserved": reserved}

    action = MASK_TO_ACTION.get(cmd)
    return {
        "action": action or "unknown",
        "cmd": cmd,
        "aux": aux,
        "reserved": reserved,
    }
```

### Encoder

```python
ACTION_TO_MASK = {
    "volume_up": 0x08,
    "volume_down": 0x04,
    "source": 0x02,
    "next": 0x80,
    "previous": 0x40,
}


def encode_21f(action, aux=0x09, reserved=0x00):
    """Generate a 3-byte 0x21F frame for a single press."""
    cmd = ACTION_TO_MASK[action]
    return [cmd, aux, reserved]
```

### Example

```python
frame = [0x08, 0x09, 0x00]
print(decode_21f(frame))
# {'action': 'volume_up', 'cmd': 8, 'aux': 9, 'reserved': 0}

print(encode_21f("source"))
# [2, 9, 0]
```

## 7. Implementation note for the simulator

If you want to add a decoder in the simulator, the logic is intentionally simple:

```python
def decode_can_21f(data):
    if len(data) != 3:
        return None

    cmd = data[0]
    if cmd == 0x00:
        return "idle"
    if cmd & 0x08:
        return "volume_up"
    if cmd & 0x04:
        return "volume_down"
    if cmd & 0x02:
        return "source"
    if cmd & 0x80:
        return "next"
    if cmd & 0x40:
        return "previous"
    return "unknown"
```

This is exactly the pattern visible in the attached log: the key is identified by the bit value in byte 0, while the second byte is only a pulse/auxiliary value.

## 8. Summary

The provided log is a condensed capture of steering-wheel remote key presses on `0x21F`:

- `0x08` = Volume Up
- `0x04` = Volume Down
- `0x02` = Source
- `0x80` = Next / Forward
- `0x40` = Previous / Backward
- `0x00` = Idle / Released

The signal is encoded in the first byte of the 3-byte frame and repeated in a press/release pulse pattern.
