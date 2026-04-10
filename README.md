# Peugeot Comfort CAN Simulator

A debug and reverse engineering tool for AEE2004 CAN networks.

> WARNING: This project is not designed for use in a real car. It is a debugging/emulation tool and may be unstable or contain bugs.

## Overview

This is a Python + Kivy application that connects to a SocketCAN interface (default: `can0`) and loads simulator modules from `config.yml`.

Each module exposes a tabbed UI and CAN handlers for one part of the car, such as radio, BSI, climate control, or instrument cluster data.

The simulator can run in two modes:
- normal mode: emit CAN frames from simulator modules and optionally respond to incoming CAN traffic
- monitor mode: listen to CAN traffic only and update UI state from incoming frames without sending any simulator frames

## Requirements

- Python 3
- Kivy
- `python-can`
- A SocketCAN network interface named `vcan0` by default
  - If you are using a real CAN interface, use `can0` instead or update `can_runner.py`

Optional but recommended:

- Create and activate a virtual environment in the project root:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Run the simulator

Start normal simulator mode:

    python app.py

Start monitor-only mode:

    python app.py monitor

or:

    python app.py --monitor

Monitor mode will keep the app connected to `can0`, receive and process incoming CAN frames, and prevent the simulator from sending outgoing CAN traffic.

## Project structure

- `app.py` — main Kivy application entry point
- `can_runner.py` — CAN send/receive loop and monitor-mode support
- `config.yml` — list of enabled simulation modules
- `modules/` — per-module simulation code and UI definitions
- `requirements.txt` — Python dependencies

## Notes

- The CAN interface is currently hardcoded to `can0`.
- Modules register themselves dynamically via `config.yml`.
- Monitor mode is useful for observing live vehicle traffic and mapping incoming CAN state into simulator UI controls.
