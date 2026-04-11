# Tool Specification: `sniff_packets`

## Overview
The `sniff_packets` tool is designed to provide the AI Agent with "eyes" on the vehicle's CAN bus. It captures raw traffic from the `can0` interface for a defined window of time, allowing the agent to analyze changes in data patterns relative to user actions (e.g., toggling a switch).

## Technical Requirements
* **Operating System:** Linux (supporting SocketCAN).
* **Dependencies:** `can-utils` package installed (`sudo apt install can-utils`).
* **Hardware:** CAN-to-USB interface mapped to `can0`.
* **Permissions:** The user running the agent must have permissions to access the network interface (often requires `sudo` or being in the `plugdev` group).

---

## Function Definition

### `sniff_packets(duration: int)`
Captures CAN traffic using the `candump` utility in log format.

**Parameters:**
* `duration` (Integer): The number of seconds to record traffic. (Recommended range: 1–10 seconds to prevent context window overflow).

**Returns:**
* `String`: A log containing the captured CAN frames in the standard log format:
    `(timestamp) interface identification#data`

---

## Reference Implementation (Python)

```python
import subprocess
import time

def sniff_packets(duration: int) -> str:
    """
    Executes candump for a specified duration and returns the log output.
    """
    try:
        # -L: Log format (absolute timestamps)
        # -t a: Absolute time
        # -T: Timeout in milliseconds
        timeout_ms = duration * 1000
        
        command = ["candump", "-L", f"-T {timeout_ms}", "can0"]
        
        # We use timeout from subprocess as a fallback to the -T flag
        result = subprocess.run(
            ["timeout", f"{duration}s", "candump", "-L", "can0"],
            capture_output=True,
            text=True
        )
        
        if not result.stdout:
            return "No data captured. Ensure can0 is UP and traffic is present."
            
        return result.stdout

    except Exception as e:
        return f"Error capturing CAN data: {str(e)}"
```

---

## Agent Logic Instructions

### 1. Delta Analysis Pattern
When the user asks to "Identify the headlight message," the agent should:
1.  Call `sniff_packets(5)` to establish a **Baseline**.
2.  Prompt the user: *"Please turn on the headlights now."*
3.  Call `sniff_packets(5)` again to capture the **Action** state.
4.  Compare the logs to find unique IDs or payload changes.

### 2. Output Formatting
The agent should filter the raw log before presenting findings to the user. It should ignore high-frequency "Heartbeat" messages (IDs that appear consistently in both logs with the same data) and highlight the "Deltas."

### 3. Safety Constraints
* The agent should never attempt to write to the bus (`cansend`) unless specifically instructed by the user.
* If the log size exceeds 500 lines, the agent should summarize the most frequent IDs rather than printing the full log to save tokens.

---

## Example Usage Scenario
**User:** "Find the ID for the hazard lights."
**Agent:** "I'll start a 5-second baseline capture. Please keep the hazards OFF. [Calls `sniff_packets(5)`]"
**Agent:** "Baseline captured. Now, please turn the hazard lights ON. I'm starting the next capture. [Calls `sniff_packets(5)`]"
**Agent:** "Analysis complete. I found that ID `0x21A` changed its third byte from `00` to `01`. This is likely your hazard light trigger."