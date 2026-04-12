---
name: Generate CAN Decoder
description: "Generate module-ready Peugeot 407 CAN2004 decoder output from analyzed signal candidates."
agent: "CAN Sniff"
model: "GPT-5 (copilot)"
argument-hint: "Example: generate decoder mapping for 0x21F door status and 0x261 trip data"
---
Generate decoder-ready output for Peugeot 407 CAN2004 based on provided signal analysis, logs, or candidate tables.

Context assumptions:
- Bench interface is `can0` unless explicitly changed.
- Existing architecture uses module boundaries under `modules/` and dynamic loading via `config.yml`.
- Keep outputs suitable for `doc/` notes and Python implementation.

Requirements:
- Do not invent certainty when evidence is weak.
- For each proposed signal include confidence and at least one counterexample risk.
- Prefer incremental patches over broad refactors.
- Keep proposed decoding compatible with monitor mode (`python app.py --monitor`).

Output format:
1. Candidate mapping table with columns:
   - CAN ID
   - byte offset
   - bit mask
   - value mapping (enum or scale formula)
   - confidence
   - caveats
2. Suggested Python decode snippets (minimal, focused):
   - extraction expression
   - normalization/scaling expression
   - target state field name
3. Suggested test vectors:
   - raw frame bytes
   - expected decoded value
4. Suggested doc entry for `doc/`:
   - message ID summary
   - field definitions
   - open questions

Coding guidance for snippets:
- Use small pure helper functions when logic is reused.
- Keep constants explicit (mask, shift, multiplier, offset).
- Include concise comments only where bit packing is non-obvious.
- Preserve existing simulator style and naming conventions.

If input only has baseline/action logs:
- ask to run compare first or provide a ranked delta summary
- then generate decoder output from top-ranked IDs only
