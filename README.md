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

Start monitor-only mode on the virtual bus:

    python app.py --monitor --channel vcan0

Monitor mode will receive and process incoming CAN frames on the selected interface and prevent the simulator from sending outgoing CAN traffic.

## Project structure

- `app.py` — main Kivy application entry point
- `can_runner.py` — CAN send/receive loop and monitor-mode support
- `config.yml` — list of enabled simulation modules
- `modules/` — per-module simulation code and UI definitions
- `requirements.txt` — Python dependencies

## Notes

- The CAN interface can be selected with `--channel`, so you can switch between `can0` and `vcan0` without editing code.
- Modules register themselves dynamically via `config.yml`.
- Monitor mode is useful for observing live vehicle traffic and mapping incoming CAN state into simulator UI controls.
