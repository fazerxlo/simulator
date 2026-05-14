# Peugeot Comfort CAN Simulator

A debug and reverse engineering tool for AEE2004 CAN networks.

> WARNING: This project is not designed for use in a real car. It is a debugging/emulation tool and may be unstable or contain bugs.

## Overview

This is a Python + Kivy application that connects to a SocketCAN interface and loads simulator modules from `config.yml`. By default it uses `vcan0`, and for bench work you can pass `--channel can0`.

Each module exposes a tabbed UI and CAN handlers for one part of the car, such as radio, BSI, climate control, or instrument cluster data.

The simulator can run in two modes:
- normal mode: emit CAN frames from simulator modules and optionally respond to incoming CAN traffic
- monitor mode: listen to CAN traffic only and update UI state from incoming frames without sending any simulator frames

## Requirements

- Python 3
- Kivy
- `python-can`
- A SocketCAN network interface such as `can0` or `vcan0`
  - Bench setups typically use `can0`
  - Virtual testing can use `vcan0`

Optional but recommended:

- Create and activate a virtual environment in the project root:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Run the simulator

Start normal simulator mode on the default bench interface:

    python app.py

Start normal simulator mode on the virtual bus:

    python app.py --channel vcan0

Start with CAN2010 signal profile:

    python app.py --can-version 2010

Start monitor-only mode on the virtual bus:

    python app.py --monitor --channel vcan0

Monitor mode will receive and process incoming CAN frames on the selected interface and prevent the simulator from sending outgoing CAN traffic.

## Project structure

- `app.py` — main Kivy application entry point
- `can_runner.py` — CAN send/receive loop and monitor-mode support
- `config.yml` — list of enabled simulation modules
- `modules/` — per-module simulation code and UI definitions
- `generated/` — auto-generated CAN message encoder modules (one per subsystem)
- `signal-db/` — YAML signal database, split by CAN version (`2004/` and `2010/`)
- `signal-db/codegen/` — code generator that reads YAML and produces `generated/` modules
- `requirements.txt` — Python dependencies

## Signal database and code generation

All CAN message definitions live in YAML files under `signal-db/<can-version>/`, one per vehicle subsystem:

| YAML file | Module group | Messages |
|-----------|-------------|----------|
| `bsi.yaml` | BSI core | 0x036, 0x0B6, 0x0F6, 0x110, 0x128, 0x161, 0x168, 0x190, 0x1A1, 0x1A8, 0x217, 0x220, 0x2B6, 0x336, 0x3B6, 0x52D |
| `clim.yaml` | Climate | 0x12D, 0x1D0, 0x1E3 |
| `radio.yaml` | Radio | 0x0A4, 0x165, 0x1A5, 0x1E0, 0x1E5, 0x225, 0x265, 0x2A5, 0x3E5 |
| `trip.yaml` | Trip computer | 0x221, 0x2A1, 0x261 |
| `parktronic.yaml` | Parking sensors | 0x0E1 |
| `bte.yaml` | BTE | 0x12B |
| `kml.yaml` | KML / hands-free | 0x1A3, 0x223, 0x323 |

### Regenerating encoder modules

After editing any YAML file in `signal-db/<can-version>/`, regenerate the Python encoder modules:

    python -m signal-db.codegen.gen_py_encoder --can-version 2004

or:

    python -m signal-db.codegen.gen_py_encoder --can-version 2010

This reads all `signal-db/<can-version>/*.yaml` files and writes the corresponding Python modules to `generated/`. The generated files are committed to the repository so the simulator works out of the box without running codegen.

### Adding a new CAN message

1. Choose the appropriate YAML file in `signal-db/<can-version>/` (or create a new one for a new subsystem).
2. Add a message entry with `can_id`, `period_ms`, `encode_body`, and optionally `decode_body`, `required_modules`, `listen_only`, etc.
3. Run `python -m signal-db.codegen.gen_py_encoder --can-version <2004|2010>` to regenerate `generated/`.
4. Import the new message class from `generated.<module>_messages` in the appropriate simulator module.
5. Run `python -m pytest tests/` to verify everything works.

## Notes

- The CAN interface can be selected with `--channel`, so you can switch between `can0` and `vcan0` without editing code.
- The CAN profile can be selected with `--can-version` (`2004` by default, `2010` optional).
- Modules register themselves dynamically via `config.yml`.
- Monitor mode is useful for observing live vehicle traffic and mapping incoming CAN state into simulator UI controls.
