# Agent Guidelines & Development Environment

## Environment & Tooling
- **Virtual Environment**: Always use the virtual environment located at `./.venv/bin/python` and `./.venv/bin/pytest`.
- **Running Tests**: Run tests via `./.venv/bin/pytest`.
- **Package Management**: Dependencies are specified in `requirements.txt`.

## Project Architecture & Code Generation
- **Signal Database**: All CAN message definitions live as YAML files under `signal-db/`.
- **Code Generator**: When editing or adding YAML files in `signal-db/`, regenerate the Python encoder modules using:
  ```bash
  ./.venv/bin/python signal-db/codegen/gen_py_encoder.py
  ```
- **Generated Code**: Message classes in `generated/` are auto-generated from `signal-db/*.yaml`. Do not edit `generated/*.py` manually unless modifying the generator template itself.
- **Car State (`car_state.py`)**: `VirtualCar` is the single source of truth for the vehicle state shared between UI modules and message encoders/decoders.

## Verification
- Before finishing any task, run the test suite using `./.venv/bin/pytest` and verify that all tests pass.

