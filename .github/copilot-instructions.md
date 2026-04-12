# Copilot Instructions for Peugeot 407 CAN2004 Simulator

## Project intent

- This repository is a reverse engineering and simulation tool for Peugeot 407 comfort CAN (AEE2004 / CAN2004, 125 kbps).
- Typical bench hardware includes: odometer, MFD display, radio, CD changer, climate panel, steering wheel controls.
- The simulator is for bench/debug only, not in-vehicle safety-critical use.

## Development context Copilot should assume

- Primary CAN interface for real bench work is `can0` (USB CAN adapter via slcan).
- Virtual testing may use `vcan0` when explicitly requested.
- Preferred default bus speed is 125000.
- Use monitor mode (`python app.py --monitor`) when the goal is receive-only analysis.
- Avoid transmitting on live bus unless explicitly requested.

## Bench workflow

- For signal discovery, use baseline/action comparison:
  - capture baseline traffic
  - perform one physical action on the bench
  - capture action traffic
  - compare deltas and rank candidate IDs
- When user provides real BSI logs, prioritize mapping:
  - CAN ID
  - byte offset
  - bit mask
  - scaling/enum hypothesis
  - confidence and counterexamples

## Code and analysis priorities

- Prefer reproducible scripts and commands over manual ad-hoc steps.
- Keep protocol notes close to code and documentation under `doc/`.
- Preserve existing simulator module loading from `config.yml` and module boundaries under `modules/`.
- For new decoding logic, include small test vectors when possible.

## Safety and guardrails

- Do not suggest commands that spam CAN transmissions by default.
- Before any transmit command, mention interface and expected impact.
- If interface is unclear, ask whether to use `can0` or `vcan0`.

## Useful commands

- Start normal mode: `python app.py`
- Start monitor mode: `python app.py --monitor`
- Bring up vcan quickly (if needed): `./vcan.sh`
- Bring up slcan adapter (if needed): `./slcan.sh`
- CAN sniff agent identify example: `python -m tools.can_sniff_ai_agent identify "hazard lights" --duration 5 --interface can0`
- Compare saved baseline/action logs: `python -m tools.can_sniff_ai_agent compare baseline.log action.log`

## Copilot prompt shortcuts

- `Analyze BSI Logs` for ranking changed IDs and producing signal hypotheses.
- `Generate CAN Decoder` for module-ready mapping, decode snippets, and test vectors.
