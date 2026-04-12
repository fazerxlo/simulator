---
name: Analyze BSI Logs
description: "Analyze Peugeot 407 CAN2004 baseline/action logs and produce a ranked signal map."
agent: "CAN Sniff"
model: "GPT-5 (copilot)"
argument-hint: "Example: compare baseline.log and action.log for hazard lights on can0"
---
Analyze Peugeot 407 CAN2004 bench logs using a baseline/action method.

Input expectations:
- Two logs (baseline and action), or one log with a clearly marked action window.
- Interface defaults to `can0` unless explicitly specified otherwise.

Requirements:
- Prefer CLI compare workflow when files are available:
  - `python -m tools.can_sniff_ai_agent compare <baseline_log> <action_log>`
- If user only describes a live action, suggest identify workflow:
  - `python -m tools.can_sniff_ai_agent identify "<action>" --duration 5 --interface can0`
- Never send CAN frames unless user explicitly asks.
- Focus on changed IDs and changed bytes/bits, not full frame dumps.

Output format:
1. Short summary of strongest candidates.
2. Ranked table with columns:
   - rank
   - CAN ID
   - byte offset(s)
   - bit mask/value transition
   - scaling or enum hypothesis
   - confidence (high/medium/low)
   - counterexamples or caveats
3. Recommended next bench action to disambiguate top candidates.

When evidence is weak:
- state uncertainty explicitly
- propose one controlled action test at a time
- avoid inventing semantics for unchanged bytes
