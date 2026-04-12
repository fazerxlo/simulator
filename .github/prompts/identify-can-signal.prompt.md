---
name: Identify CAN Signal
description: "Identify a CAN signal with the workspace CAN sniff agent using can0 by default."
agent: "CAN Sniff"
model: "GPT-5 (copilot)"
argument-hint: "Example: hazard lights on can0 for 5 seconds"
---
Use the workspace CAN sniff agent to identify the requested CAN signal.

Requirements:

- Default to `can0` unless the user specifies another interface.
- Use the CLI in `tools/can_sniff_ai_agent`.
- Prefer the `identify` workflow for live discovery.
- If the user already has logs, use `compare` instead.
- Summarize the strongest candidate CAN IDs and payload changes.
- If execution fails because `python` is missing, retry with `.venv/bin/python`.