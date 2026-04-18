# CAN2004 CD Changer — Frames 0x131 and 0x1A0 (Peugeot 407)

This document covers the two CAN frames that implement the PSA CAN2004 CD changer
(CDC) protocol on the comfort / infotainment bus (125 kbps).

| Frame | Direction | PSA-RE name | Period |
|-------|-----------|-------------|--------|
| `0x131` | Radio → CDC | `CDE_CDC` | 100 ms (when CDC selected) |
| `0x1A0` | CDC → Radio | `CDC_STATUS` | 100 ms |

---

## Overview

The CDC communicates with the radio head unit over two dedicated frames:

- The head unit sends **`0x131`** (`CDE_CDC`) to select the CDC as the audio source,
  start/pause playback, and request specific disc or track changes.
- The CDC replies with **`0x1A0`** (`CDC_STATUS`) to report its current status, the
  disc and track currently loaded, elapsed track time, total tracks on the disc, and
  active playback mode flags.

The simulator emulates the **CDC side**: it transmits `0x1A0` and decodes received
`0x131` frames.  The simulator never transmits `0x131` — that is the radio's job.

---

## Frame 0x131 — CDE_CDC (Radio → CDC)

PSA-RE canonical name: `CDE_CDC`  
Sender: Radio head unit  
Period: 100 ms (transmitted only while CDC source is selected or during source
        switch transitions)  
Frame length: 8 bytes

### Signal Map

| Byte (1-idx) | Idx | Bits | Signal | Encoding |
|---|---|---|---|---|
| 1 | 0 | 7 | CDC_SELECTED | 1 = CDC is the active audio source |
| 1 | 0 | 4 | PLAY_REQUEST | 1 = play; 0 = pause |
| 1 | 0 | 3-0 | DISC_REQUEST | 0 = no change; 1-6 = select disc |
| 2 | 1 | 7-0 | TRACK_REQUEST | 0 = no change; 1-99 = select track |
| 3-8 | 2-7 | — | (reserved) | `0x00` |

### Byte 0 — Control Flags

```
Bit 7  CDC_SELECTED  — 1 when CDC is the selected audio source
Bit 6  (unused)
Bit 5  (unused)
Bit 4  PLAY_REQUEST  — 1 = play; 0 = pause (only valid when CDC_SELECTED=1)
Bit 3-0 DISC_REQUEST — 0 = no change; 1-6 = select this disc number
```

### Typical byte 0 patterns

| b0 hex | CDC_SELECTED | PLAY_REQUEST | DISC_REQUEST | Meaning |
|--------|---|---|---|---------|
| `0x00` | 0 | — | 0 | CDC deselected |
| `0x80` | 1 | 0 | 0 | CDC selected, pause |
| `0x90` | 1 | 1 | 0 | CDC selected, play |
| `0x91` | 1 | 1 | 1 | Play, select disc 1 |
| `0x92` | 1 | 1 | 2 | Play, select disc 2 |
| `0x96` | 1 | 1 | 6 | Play, select disc 6 |

### Byte 1 — TRACK_REQUEST

| Value | Meaning |
|-------|---------|
| `0x00` | No track change requested |
| `0x01`–`0x63` | Jump to track number 1–99 |

### Decode rules (simulator `Msg131.decode`)

1. If `CDC_SELECTED` (bit 7) is clear → set status to `IDLE`.
2. If `CDC_SELECTED` is set:
   - If `PLAY_REQUEST` (bit 4) is set → set status to `PLAYING`.
   - Otherwise → set status to `PAUSED`.
   - If `DISC_REQUEST` (bits 3-0) is 1-6 and differs from current disc →
     set `disc`, reset `track=1`, reset `minutes=0`, `seconds=0`, set
     status to `SEARCHING`.
3. If `TRACK_REQUEST` (byte 1) is non-zero and differs from current track →
   set `track`, reset `minutes=0`, `seconds=0`.

### Decode snippet

```python
def decode_0x131(data: bytes, cdc_state) -> None:
    """Apply a CDE_CDC command frame to the CDC state object."""
    if len(data) < 2:
        return
    b0 = data[0]
    if not (b0 & 0x80):
        cdc_state.status = cdc_state.STATUS_IDLE
        return
    # CDC selected
    cdc_state.status = (cdc_state.STATUS_PLAYING
                        if b0 & 0x10 else cdc_state.STATUS_PAUSED)
    disc_req = b0 & 0x0F
    if 1 <= disc_req <= 6 and disc_req != cdc_state.disc:
        cdc_state.disc = disc_req
        cdc_state.track = 1
        cdc_state.minutes = 0
        cdc_state.seconds = 0
        cdc_state.status = cdc_state.STATUS_SEARCHING
    track_req = data[1]
    if track_req and track_req != cdc_state.track:
        cdc_state.track = track_req
        cdc_state.minutes = 0
        cdc_state.seconds = 0
```

---

## Frame 0x1A0 — CDC_STATUS (CDC → Radio)

PSA-RE canonical name: `CDC_STATUS`  
Sender: CD changer  
Period: 100 ms  
Frame length: 8 bytes

### Signal Map

| Byte (1-idx) | Idx | Bits | Signal | Encoding |
|---|---|---|---|---|
| 1 | 0 | 7-0 | STATUS | see Status Byte table |
| 2 | 1 | 7-0 | DISC_NUMBER | 0 = none; 1-6 = current disc |
| 3 | 2 | 7-0 | TRACK_NUMBER | 0 = none; 1-99 = current track |
| 4 | 3 | 7-0 | TRACK_MINUTES | Elapsed minutes (0-99) |
| 5 | 4 | 7-0 | TRACK_SECONDS | Elapsed seconds (0-59) |
| 6 | 5 | 7-0 | TOTAL_TRACKS | Total tracks on disc (0 = unknown) |
| 7 | 6 | 3-0 | MODE_FLAGS | see Mode Flags table |
| 8 | 7 | — | (reserved) | `0x00` |

### Byte 0 — Status Byte

The status byte uses bit flags, not a numeric enum.  Only one flag is set at a time
in normal operation.

| Byte value | Meaning |
|---|---------|
| `0x01` | Loading — tray moving or disc spinning up |
| `0x02` | Paused — disc loaded, playback halted |
| `0x04` | Playing — audio output active |
| `0x40` | Searching — disc change or seek in progress |
| `0x80` | No magazine / CDC inactive |

### Byte 6 — Mode Flags

| Bit | Mask | Name | Meaning |
|-----|------|------|---------|
| 0 | `0x01` | SCAN | Scan mode (plays a few seconds of each track) |
| 1 | `0x02` | RANDOM | Shuffle / random track order |
| 2 | `0x04` | REPEAT_ALL | Repeat all tracks on disc |
| 3 | `0x08` | REPEAT_TRACK | Repeat current track |

Flags are independent; multiple may be set simultaneously.  All zero = normal
sequential playback.

### Encode snippet

```python
def encode_0x1A0(cdc_state) -> list:
    """Encode a CDC_STATUS (0x1A0) frame from the CDC state object."""
    STATUS_MAP = {
        0: 0x80,  # idle / no magazine
        1: 0x04,  # playing
        2: 0x02,  # paused
        3: 0x01,  # loading
        4: 0x40,  # searching
    }
    b0 = STATUS_MAP.get(cdc_state.status, 0x80)
    b6 = (
        int(cdc_state.scan) |
        (int(cdc_state.random) << 1) |
        (int(cdc_state.repeat) << 2) |
        (int(cdc_state.repeat_track) << 3)
    )
    return [b0, cdc_state.disc, cdc_state.track,
            cdc_state.minutes, cdc_state.seconds,
            cdc_state.total_tracks, b6, 0x00]
```

### Full frame decode snippet

```python
def decode_0x1A0(data: bytes) -> dict:
    """Decode a CDC_STATUS (0x1A0) frame."""
    assert len(data) >= 7

    b0 = data[0]
    if b0 & 0x04:
        status = 'playing'
    elif b0 & 0x02:
        status = 'paused'
    elif b0 & 0x01:
        status = 'loading'
    elif b0 & 0x40:
        status = 'searching'
    else:
        status = 'idle'

    return {
        'status':        status,
        'disc':          data[1],
        'track':         data[2],
        'minutes':       data[3],
        'seconds':       data[4],
        'total_tracks':  data[5],
        'scan':          bool(data[6] & 0x01),
        'random':        bool(data[6] & 0x02),
        'repeat':        bool(data[6] & 0x04),
        'repeat_track':  bool(data[6] & 0x08),
    }
```

---

## Test Vectors

### 0x1A0 — CDC_STATUS

| Description | Frame (hex, 8 bytes) | status | disc | track | time | total | flags |
|---|---|---|---|---|---|---|---|
| No magazine | `80 00 00 00 00 00 00 00` | idle | 0 | 0 | 0:00 | 0 | none |
| Playing disc 1, track 3, 1:23, 12 tracks | `04 01 03 01 17 0C 00 00` | playing | 1 | 3 | 1:23 | 12 | none |
| Paused disc 2, track 7, 4:05 | `02 02 07 04 05 08 00 00` | paused | 2 | 7 | 4:05 | 8 | none |
| Loading disc 3 | `01 03 00 00 00 00 00 00` | loading | 3 | 0 | 0:00 | 0 | none |
| Searching disc 4 | `40 04 00 00 00 00 00 00` | searching | 4 | 0 | 0:00 | 0 | none |
| Playing, random + repeat all | `04 01 05 02 30 10 06 00` | playing | 1 | 5 | 2:48 | 16 | random+repeat |
| Playing, scan mode | `04 01 01 00 05 10 01 00` | playing | 1 | 1 | 0:05 | 16 | scan |

### 0x131 — CDE_CDC

| Description | Frame (hex, 8 bytes) | CDC_SELECTED | PLAY | DISC_REQ | TRACK_REQ |
|---|---|---|---|---|---|
| Deselect CDC | `00 00 00 00 00 00 00 00` | 0 | — | — | — |
| Select CDC, pause | `80 00 00 00 00 00 00 00` | 1 | 0 | 0 | 0 |
| Select CDC, play | `90 00 00 00 00 00 00 00` | 1 | 1 | 0 | 0 |
| Play, select disc 2 | `92 00 00 00 00 00 00 00` | 1 | 1 | 2 | 0 |
| Play, jump to track 5 | `90 05 00 00 00 00 00 00` | 1 | 1 | 0 | 5 |
| Play disc 3, jump to track 10 | `93 0A 00 00 00 00 00 00` | 1 | 1 | 3 | 10 |

---

## Simulator Implementation

### `CDChanger` state fields (`car_state.py`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `active` | bool | `False` | Set to `True` by the `cdc` module on load |
| `status` | int | `STATUS_IDLE` | One of the `STATUS_*` constants |
| `disc` | int | `1` | Current disc (1-6) |
| `track` | int | `1` | Current track (1-99) |
| `minutes` | int | `0` | Elapsed track time: minutes |
| `seconds` | int | `0` | Elapsed track time: seconds |
| `disc_tracks` | dict[int, int] | `{1: 10, …, 6: 10}` | Per-disc track counts (disc 1-6) |
| `total_tracks` | int (property) | `10` | Total tracks on **current** disc; backed by `disc_tracks[disc]` |
| `random` | bool | `False` | Shuffle playback |
| `repeat` | bool | `False` | Repeat all tracks |
| `repeat_track` | bool | `False` | Repeat current track only |
| `scan` | bool | `False` | Scan mode |

`total_tracks` is a read/write property: reading returns `disc_tracks[disc]`, writing sets `disc_tracks[disc]`.  This means each disc independently stores its own track count.

### Startup announcement sequence

When the `cdc` module loads, it announces itself to the radio head unit:

1. Sets `status = STATUS_LOADING` immediately (0x1A0 byte 0 = `0x01`)
2. After 2 seconds, transitions to `status = STATUS_PAUSED` (0x1A0 byte 0 = `0x02`)

The radio head unit sees a real CDC sequence: the CDC powers on (loading), then indicates a disc is ready (paused).  The user can then press Play on the radio or in the simulator UI.

### `STATUS_*` constants

| Constant | Value | 0x1A0 byte 0 |
|----------|-------|--------------|
| `STATUS_IDLE` | `0` | `0x80` |
| `STATUS_PLAYING` | `1` | `0x04` |
| `STATUS_PAUSED` | `2` | `0x02` |
| `STATUS_LOADING` | `3` | `0x01` |
| `STATUS_SEARCHING` | `4` | `0x40` |

### CAN message classes (`can_messages.py`)

| Class | CAN ID | Direction | Note |
|-------|--------|-----------|------|
| `Msg1A0` | `0x1A0` | TX (CDC → radio) | Returns `None` when `car.cdc.active` is `False` |
| `Msg131` | `0x131` | RX (radio → CDC) | `encode()` always returns `None`; decode-only |

Both classes require the `cdc` module to be enabled (`required_modules = frozenset({'cdc'})`).

### Usage example

```python
from car_state import VirtualCar, CDChanger
from can_messages import Msg1A0

car = VirtualCar()
car.cdc.active = True
car.cdc.status = CDChanger.STATUS_PLAYING
car.cdc.disc = 2
car.cdc.track = 5
car.cdc.minutes = 1
car.cdc.seconds = 30
# Configure track counts per disc
car.cdc.disc_tracks[1] = 10
car.cdc.disc_tracks[2] = 15
car.cdc.disc_tracks[3] = 8
car.cdc.random = True

frame = Msg1A0().encode(car)
# → [0x04, 0x02, 0x05, 0x01, 0x1E, 0x0F, 0x02, 0x00]
# byte 5 = 0x0F = 15 (tracks on disc 2)
```

### Enabling the CDC module

Uncomment the `cdc` entry in `config.yml`:

```yaml
modules:
  - bsi-base
  # ... other modules ...
  - cdc
```

This activates the CDC panel tab in the simulator UI and starts transmitting `0x1A0`
status frames.  The radio source selector in the `radio-gen` module should be set to
`CDC` to begin receiving `0x131` command frames from a connected head unit.

---

## Panel UI

The `modules/cdc/` panel provides:

| Control | Description |
|---------|-------------|
| Status row | Live display of status, disc, track/total, elapsed time |
| Play / Pause / Stop | Playback state control |
| `|<` / `<|` | Previous disc / previous track |
| `|>` / `>|` | Next track / next disc |
| Disc D1–D6 toggles | Direct disc selection (triggers SEARCHING); each button shows the disc number and its configured track count (e.g. `D1\n12`) |
| Tracks on disc N slider | Set track count for the **currently selected** disc (1-30). Moving to a different disc updates the slider to that disc's count |
| Random / Repeat All / Repeat Track / Scan | Playback mode flags |

Each disc (D1–D6) stores its own track count independently.  Select a disc and
drag the slider to configure how many tracks that disc contains.  The disc button
labels update in real time to reflect each disc's count.

### Startup announcement

On module load the CDC transitions through:
```
STATUS_LOADING  (0x1A0 byte 0 = 0x01, ~2 s)  →  STATUS_PAUSED (byte 0 = 0x02)
```
The radio head unit sees the loading → paused sequence and recognises a CDC
magazine as present and ready.  The user can then issue a play command from
either the radio or the simulator UI.

---

## Open Questions

- Does the real 407 radio transmit `0x131` frames continuously at 100 ms, or only
  when source or control state changes?
- What byte value does a magazine with all 6 discs present but none currently
  loaded report in `DISC_NUMBER`?
- Is `TOTAL_TRACKS = 0` a valid "unknown" signal, or does the CDC always report
  at least 1?
- Does random/repeat mode state come from the CDC or from the head unit?  If the
  head unit owns these flags, `0x131` would need additional bit fields.
