---
name: Workbench Monitor UI Issue
description: "Analyze Peugeot 407 CAN2004 monitor-mode mismatches where real workbench actions are not reflected correctly in the simulator UI."
argument-hint: "Example: turn on low beam on the bench but the app still shows sidelights only; monitor mode on can0"
---
Analyze a real workbench monitor-mode issue for the Peugeot 407 CAN2004 simulator.

Use this when:
- the simulator is connected to the real bench on can0
- the app is running in monitor / listen-only mode
- the user performs an action on the physical workbench
- the simulator UI does not update correctly, updates partially, updates with the wrong value, or does not react at all

Context assumptions:
- Bench/debug only, not in-vehicle use
- Preferred bench interface is can0 at 125000 bit/s
- In monitor mode, the app should not transmit simulator frames and should instead decode incoming CAN traffic into VirtualCar state and UI state
- The repository contains known signal mappings, decoder logic, message classes, tests, and notes under doc/ and modules/

Your job:
1. Summarize the mismatch in one short sentence.
2. Identify the most likely CAN ID or IDs that should carry the workbench action.
3. Point to the probable decode, state-mapping, UI-sync, or timing issue.
4. Determine the likely root cause category:
   - missing or incomplete decode logic
   - wrong byte / bit extraction
   - wrong scaling or enum mapping
   - UI not synced after VirtualCar state changes
   - module not listening to the relevant CAN frame
   - monitor-mode-only behavior gap
   - bench signal differs from current assumptions
5. Identify the smallest relevant code area to inspect.
6. If confidence is high, propose a minimal patch.
7. If evidence is incomplete, ask only for the smallest next proof needed.

Preferred workflow:
- compare the reported behavior against existing repository docs and tests
- use baseline/action reasoning
- prioritize exact CAN IDs, byte offsets, bit masks, scale formulas, and UI update hooks
- do not guess when evidence is weak
- propose one controlled verification step at a time

Issue details:
- Workbench action performed:
  [describe exactly what was done on the real workbench]

- Expected app UI result:
  [describe what the simulator UI should have shown]

- Actual app UI result:
  [describe what the app really showed]

- Affected app module or tab:
  [bsi-base / combine / clim / radio / bsi-log / parktronic / other]

- CAN evidence if available:
  [paste candump lines, observed IDs, missing IDs, wrong bytes, or timing notes]

- Regression status:
  [worked before / never worked / unknown]

Response format:
1. Short mismatch summary
2. Most likely IDs and decoded signals
3. Root cause hypothesis with confidence
4. Exact files or symbols to inspect
5. Next verification step
6. Proposed fix or patch outline

If logs are provided:
- compare them against the repository’s known message mappings
- identify whether the issue is in decode logic, state propagation, or UI refresh handling
- separate payload problems from rendering / sync problems
