---
name: Workbench Verification Issue
description: "Analyze Peugeot 407 CAN2004 host-mode mismatches between simulator UI actions and real workbench behavior, then suggest likely root cause and the smallest fix."
argument-hint: "Example: low beam set in UI but cluster shows sidelights only; can0 host mode; candump attached"
---
Analyze a real workbench verification issue for the Peugeot 407 CAN2004 simulator.

Use this when:
- the simulator is connected to the real bench on can0
- the app is running in host / active transmit mode
- the user changes something in the simulator UI
- the physical workbench response is incorrect, incomplete, delayed, or missing

Context assumptions:
- Bench/debug only, not in-vehicle use
- Preferred bench interface is can0 at 125000 bit/s
- The repository contains known signal mappings, message encoders, tests, and protocol notes under doc/ and modules/
- Work from existing evidence before proposing changes

Your job:
1. Summarize the mismatch in one short sentence.
2. Identify the most likely CAN ID or IDs involved.
3. Point to the probable byte / bit / timing mismatch.
4. Determine the likely root cause category:
   - wrong payload encoding
   - wrong timing / message period
   - missing frame
   - wrong module gating
   - UI state not reaching VirtualCar state
   - encode / decode mismatch
   - bench expectation differs from current implementation
5. Identify the smallest relevant code area to inspect.
6. If confidence is high, propose a minimal patch.
7. If evidence is incomplete, ask only for the smallest next proof needed.

Preferred workflow:
- compare expected simulator behavior against repository docs and tests
- use baseline/action thinking
- prioritize exact CAN IDs, byte offsets, bit masks, enum mappings, and periodicity
- do not guess when evidence is weak
- propose one controlled verification step at a time

Issue details:
- UI action performed:
  [describe exactly what was changed in the simulator UI]

- Expected workbench result:
  [describe what the cluster / MFD / radio / climate panel should show]

- Actual workbench result:
  [describe what really happened]

- Affected bench modules:
  [combine / MFD / radio / climate / CD / other]

- CAN evidence if available:
  [paste candump lines, missing IDs, wrong bytes, or timing notes]

- Regression status:
  [worked before / never worked / unknown]

Response format:
1. Short mismatch summary
2. Most likely IDs and signals
3. Root cause hypothesis with confidence
4. Exact files or symbols to inspect
5. Next verification step
6. Proposed fix or patch outline

If logs are provided:
- compare them against the known bench-aligned behavior in the repository
- call out any missing or incorrect payload bytes
- highlight timing mismatches separately from payload mismatches
