# Install and Use the CAN Sniff AI Agent in VS Code

This document explains how to set up the CAN sniffing agent in VS Code and how to use it together with GitHub Copilot.

## What this agent is

This agent is a Python command-line tool located in this folder. It is not a native VS Code extension and it is not automatically exposed to Copilot as a built-in tool.

What it does:

- captures CAN traffic from a SocketCAN interface such as `can0`
- compares a baseline capture against an action capture
- highlights CAN IDs and payload changes that are likely related to the action you performed

Main file:

- `agent.py`

## Prerequisites

You need all of the following:

- Linux with SocketCAN support
- VS Code
- GitHub Copilot extension in VS Code
- Python 3
- `can-utils` installed
- access to a live CAN interface such as `can0`
- permission to read that interface

## 1. Install system packages

On Debian or Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv can-utils
```

Verify the CAN tools are available:

```bash
candump --help
```

## 2. Open the project in VS Code

Open the `simulator` repository root in VS Code, or open the current multi-root workspace if you are already using one.

The agent lives here:

- `tools/can_sniff_ai_agent/`

## 3. Install VS Code extensions

Install these extensions:

- GitHub Copilot
- GitHub Copilot Chat
- Python

Optional but useful:

- Pylance

## 4. Create a Python virtual environment

From the `simulator` repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This project already includes `python-can` in `requirements.txt`. The CAN sniff agent itself mainly uses the standard library plus `candump` from `can-utils`.

## 5. Select the interpreter in VS Code

In VS Code:

1. Open the Command Palette.
2. Run `Python: Select Interpreter`.
3. Choose the interpreter from `.venv`.

If the environment was created in the `simulator` repo root, the interpreter is typically:

```bash
.venv/bin/python
```

## 6. Verify the agent files are present

This folder should contain at least:

- `README.md`
- `INSTALL.md`
- `agent.py`
- `__main__.py`
- `__init__.py`
- `test_agent.py`

## 7. Verify the CAN interface

Check whether `can0` exists:

```bash
ip link show can0
```

If you are using real hardware, ensure the interface is up and correctly configured.

Example:

```bash
sudo ip link set can0 up type can bitrate 125000
```

If you use a different bitrate, replace `125000` with the correct value for your network.

If your interface name is not `can0`, pass the correct interface using `--interface` when running the agent.

## 8. Run the included validation

From `tools/can_sniff_ai_agent`:

```bash
../../.venv/bin/python -c "import test_agent; test_agent.test_parse_candump_log_extracts_frames(); test_agent.test_compare_logs_prioritizes_changed_signal(); test_agent.test_summarize_log_reports_top_ids(); print('ok')"
```

If your current shell already has the virtual environment activated, you can use:

```bash
python -c "import test_agent; test_agent.test_parse_candump_log_extracts_frames(); test_agent.test_compare_logs_prioritizes_changed_signal(); test_agent.test_summarize_log_reports_top_ids(); print('ok')"
```

## 9. Run the agent manually

From the `simulator` repo root, use module mode:

### Capture raw traffic

```bash
python -m tools.can_sniff_ai_agent sniff 5
```

### Run an interactive identify workflow

```bash
python -m tools.can_sniff_ai_agent identify "hazard lights" --duration 5
```

### Compare two saved candump logs

```bash
python -m tools.can_sniff_ai_agent compare baseline.log action.log
```

### Use a different CAN interface

```bash
python -m tools.can_sniff_ai_agent identify "headlights" --duration 5 --interface can1
```

## 10. How to use this with GitHub Copilot in VS Code

The practical setup is:

- Copilot helps you run commands, inspect code, and analyze the resulting logs
- the actual CAN capture is still performed by this Python tool and `candump`

This means Copilot can assist you inside VS Code, but it does not automatically gain a new native tool called `sniff_packets` just because this folder exists.

### Workspace Copilot configuration included in this repo

This workspace now includes a custom Copilot agent and a prompt file:

- `.github/agents/can-sniff.agent.md`
- `.github/prompts/identify-can-signal.prompt.md`

What this gives you:

- a custom Copilot agent named `CAN Sniff`
- a reusable slash prompt named `Identify CAN Signal`
- workspace-specific instructions telling Copilot to prefer `vcan0` by default and call the CLI in this repository

How to use it in VS Code:

1. Reload the VS Code window if Copilot was already open before these files were added.
2. Open Copilot Chat.
3. Select the `CAN Sniff` agent in the agent picker, or type `/Identify CAN Signal` in chat.
4. Ask for the signal you want to identify, for example: `hazard lights on vcan0 for 5 seconds`

What Copilot will do:

- use the workspace agent instructions
- prefer commands like `python -m tools.can_sniff_ai_agent identify ... --interface vcan0`
- fall back to `.venv/bin/python` if `python` is not available in the shell

### Recommended workflow with Copilot Chat

1. Open Copilot Chat in VS Code.
2. Ask Copilot to run or explain commands for this agent.
3. Run the command in the VS Code terminal.
4. Paste the comparison output or saved logs back into chat if you want help interpreting results.

Example prompts for Copilot:

- `Run the CAN sniff agent to identify the hazard lights on can0 for 5 seconds.`
- `Explain the most likely CAN IDs from this compare output.`
- `Generate a command to compare baseline.log and action.log with this agent.`
- `Summarize these candump deltas and tell me which ID is the strongest candidate.`

### Good usage pattern

Use Copilot to coordinate the workflow, but keep the bus access explicit:

1. baseline capture with the target control off
2. action capture after toggling the target control
3. compare the two captures
4. inspect the highest-ranked CAN IDs

## 11. What Copilot can and cannot do here

Copilot can:

- help you run the agent from the terminal
- explain the code in `agent.py`
- analyze output from `compare`
- help adapt the scoring logic for your vehicle

Copilot cannot automatically do the following unless you build additional integration:

- register this script as a first-class Copilot tool
- access your CAN adapter outside the permissions of your local machine
- safely write to the CAN bus without you explicitly choosing to add that behavior

## 12. If you want deeper Copilot integration

If your goal is to make this available as a real agent tool inside Copilot, you need an additional integration layer such as:

- a local MCP server that wraps `sniff_packets`
- a VS Code extension that exposes commands and structured outputs
- a custom agent workflow that calls the CLI and returns formatted results

This repository currently includes only the Python CLI implementation.

## Troubleshooting

### `candump is not installed`

Install `can-utils`:

```bash
sudo apt install -y can-utils
```

### `No data captured on can0`

Check all of the following:

- the CAN interface is up
- traffic is actually present on the bus
- you are listening on the correct interface
- your user has permission to access the interface

### `candump failed: ...`

Check the interface state:

```bash
ip -details link show can0
```

### VS Code does not use the right Python interpreter

Open the Command Palette and run `Python: Select Interpreter`, then choose the `.venv` interpreter.

### Copilot does not see a custom tool named `sniff_packets`

That is expected with the current implementation. This folder provides a CLI tool, not a native Copilot tool registration.

## Safety note

This agent reads CAN traffic only. It does not send frames to the bus. Keep it that way unless you deliberately add write support and fully understand the risks.