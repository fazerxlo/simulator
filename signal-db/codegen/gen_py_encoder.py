#!/usr/bin/env python3
"""Code generator: reads signal-db YAML files and produces per-module
Python encoder/decoder modules in the ``generated/`` package.

Usage::

    python -m signal-db.codegen.gen_py_encoder          # generate all
    python -m signal-db.codegen.gen_py_encoder bsi clim  # generate specific modules

Each YAML file in ``signal-db/`` maps to one Python module in ``generated/``.
For example ``signal-db/bsi.yaml`` → ``generated/bsi_messages.py``.

The generator also writes:
* ``generated/__init__.py`` — re-exports every message class plus
  ``ALL_MESSAGES``, ``CanMessage``, and ``STARTUP_WAKEUP_BURST`` so that
  existing ``from can_messages import X`` style imports keep working when
  pointed at the ``generated`` package.
* ``generated/base.py`` — the ``CanMessage`` base class.
"""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SIGNAL_DB_DIR = REPO_ROOT / "signal-db"
GENERATED_DIR = REPO_ROOT / "generated"


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

def _indent(text: str, spaces: int = 8) -> str:
    """Indent every line of *text* by *spaces* spaces."""
    prefix = " " * spaces
    lines = text.rstrip("\n").split("\n")
    return "\n".join(prefix + line if line.strip() else "" for line in lines)


def _generate_class(name: str, msg: dict) -> str:
    """Generate the Python source for one CanMessage subclass."""
    parts: list[str] = []

    # Class declaration
    desc = msg.get("description", "").strip()
    parts.append(f"class {name}(CanMessage):")
    if desc:
        # Multi-line docstring
        doc_lines = desc.split("\n")
        if len(doc_lines) == 1:
            parts.append(f'    """{doc_lines[0]}"""')
        else:
            parts.append(f'    """{doc_lines[0]}')
            for dl in doc_lines[1:]:
                parts.append(f"    {dl}")
            parts.append('    """')
    parts.append("")

    # Class attributes
    can_id = msg["can_id"]
    parts.append(f"    can_id = 0x{can_id:03X}")
    parts.append(f"    period_ms = {msg['period_ms']}")

    req = msg.get("required_modules")
    if req:
        mod_str = ", ".join(repr(m) for m in req)
        parts.append(f"    required_modules = frozenset({{{mod_str}}})")

    if msg.get("listen_only"):
        parts.append("    listen_only = True")

    # Class body (constants, static methods, etc.)
    class_body = msg.get("class_body", "").rstrip("\n")
    if class_body:
        parts.append("")
        for line in class_body.split("\n"):
            parts.append(f"    {line}" if line.strip() else "")

    # __init__
    init_body = msg.get("init_body", "").rstrip("\n")
    if init_body:
        parts.append("")
        parts.append("    def __init__(self) -> None:")
        parts.append(_indent(init_body))

    # get_period_ms
    gpm = msg.get("get_period_ms_body", "").rstrip("\n")
    if gpm:
        parts.append("")
        parts.append("    def get_period_ms(self, car) -> int:")
        parts.append(_indent(gpm))

    # encode
    encode_body = msg.get("encode_body", "").rstrip("\n")
    if encode_body:
        ret_hint = "list | None" if "return None" in encode_body else "list"
        parts.append("")
        parts.append(f"    def encode(self, car) -> {ret_hint}:")
        parts.append(_indent(encode_body))

    # decode
    decode_body = msg.get("decode_body", "").rstrip("\n")
    if decode_body:
        parts.append("")
        parts.append("    def decode(self, car, data: bytes) -> None:")
        parts.append(_indent(decode_body))

    parts.append("")
    return "\n".join(parts)


def _generate_module(yaml_path: Path) -> str:
    """Generate the full Python source for one YAML definition file."""
    with open(yaml_path) as fh:
        spec = yaml.safe_load(fh)

    group = spec["module_group"]
    desc = spec.get("description", f"Auto-generated CAN message encoders for {group}.")

    lines: list[str] = []
    lines.append(f'"""Auto-generated from signal-db/{yaml_path.name} — do not edit by hand.')
    lines.append("")
    lines.append(f"{desc}")
    lines.append('"""')
    lines.append("")
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("from generated.base import CanMessage")
    lines.append("")
    lines.append("")

    # Module-level helpers
    helpers = spec.get("helpers", "").rstrip("\n")
    if helpers:
        lines.append(helpers)
        lines.append("")
        lines.append("")

    # Module-level constants
    constants = spec.get("constants", {})
    for const_name, const_val in constants.items():
        val = const_val.strip()
        lines.append(f"{const_name} = {val}")
        lines.append("")
        lines.append("")

    # Message classes
    msg_names: list[str] = []
    for name, msg in spec["messages"].items():
        msg_names.append(name)
        lines.append(_generate_class(name, msg))
        lines.append("")

    return "\n".join(lines), msg_names


def _generate_base() -> str:
    """Generate the base.py module with the CanMessage base class."""
    return textwrap.dedent('''\
        """CanMessage base class for the Peugeot 407 CAN2004 simulator.

        Auto-generated — do not edit by hand.
        """

        from __future__ import annotations


        class CanMessage:
            """Base class for a periodic CAN message.

            Subclasses **must** set ``can_id`` and ``period_ms`` as class attributes
            and override ``encode``.  Overriding ``decode`` is optional but strongly
            recommended so that monitor mode and loopback testing work correctly.

            ``required_modules`` may be set to one or more config-module names.
            When non-empty, the runner only transmits this message while at least
            one of those modules is enabled in ``config.yml``.
            """

            #: CAN arbitration ID owned by this object.
            can_id: int = 0

            #: Transmit period in milliseconds.
            period_ms: int = 100

            #: Config-module names that must be enabled for this message to transmit.
            required_modules: frozenset[str] = frozenset()

            #: When True the runner only calls decode() on this message and never
            #: calls encode() / transmits it.  Set on CAN IDs that are owned by an
            #: external node (e.g. the real workbench radio) so the simulator only
            #: monitors and displays the traffic without injecting its own frames.
            listen_only: bool = False

            def get_period_ms(self, car) -> int:
                """Return the active transmit period for the current car state."""
                return self.period_ms

            def encode(self, car) -> list | None:
                """Build frame byte payload from car state.

                Return ``None`` to skip transmission this cycle.
                """
                return None

            def decode(self, car, data: bytes) -> None:
                """Update car state from a received frame with this *can_id*."""

            def __repr__(self) -> str:
                return f\'{type(self).__name__}(can_id=0x{self.can_id:03X}, period_ms={self.period_ms})\'
    ''')


def _generate_init(module_info: dict[str, list[str]]) -> str:
    """Generate ``generated/__init__.py`` that re-exports everything.

    This provides backward compatibility: code that previously did
    ``from can_messages import Msg036`` can now do
    ``from generated import Msg036`` and the test shim ``can_messages.py``
    re-exports from here.
    """
    lines: list[str] = []
    lines.append('"""Auto-generated package — re-exports all CAN message classes.')
    lines.append("")
    lines.append('Provides ``ALL_MESSAGES``, ``CanMessage``, ``STARTUP_WAKEUP_BURST``')
    lines.append("and every ``MsgXXX`` class so that existing import patterns keep working.")
    lines.append('"""')
    lines.append("")
    lines.append("from generated.base import CanMessage  # noqa: F401")
    lines.append("")

    all_msg_names: list[str] = []
    has_startup_burst = False

    for mod_name in sorted(module_info.keys()):
        msg_names = module_info[mod_name]
        import_names = list(msg_names)
        # Check if this module has STARTUP_WAKEUP_BURST
        if mod_name == "bsi":
            import_names.append("STARTUP_WAKEUP_BURST")
            has_startup_burst = True
        joined = ", ".join(import_names)
        lines.append(f"from generated.{mod_name}_messages import {joined}  # noqa: F401")
        all_msg_names.extend(msg_names)

    lines.append("")
    lines.append("")

    # ALL_MESSAGES dict
    lines.append("#: Maps CAN arbitration IDs to their :class:`CanMessage` subclass.")
    lines.append("ALL_MESSAGES: dict[int, type] = {")
    lines.append("    cls.can_id: cls")
    lines.append("    for cls in (")
    # Wrap the class names
    chunk_size = 6
    for i in range(0, len(all_msg_names), chunk_size):
        chunk = all_msg_names[i : i + chunk_size]
        suffix = "," if i + chunk_size < len(all_msg_names) else ","
        lines.append(f"        {', '.join(chunk)}{suffix}")
    lines.append("    )")
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(module_names: list[str] | None = None) -> None:
    """Generate Python encoder modules from signal-db YAML files.

    Parameters
    ----------
    module_names : list of str, optional
        If provided, only generate these modules (e.g. ``['bsi', 'clim']``).
        Otherwise generate all YAML files found in ``signal-db/``.
    """
    GENERATED_DIR.mkdir(exist_ok=True)

    # Discover YAML files
    yaml_files: list[Path] = sorted(SIGNAL_DB_DIR.glob("*.yaml"))
    if module_names:
        yaml_files = [
            f for f in yaml_files if f.stem in module_names
        ]

    if not yaml_files:
        print("No YAML files found in", SIGNAL_DB_DIR)
        sys.exit(1)

    module_info: dict[str, list[str]] = {}

    # Generate base.py
    base_path = GENERATED_DIR / "base.py"
    base_path.write_text(_generate_base())
    print(f"  wrote {base_path.relative_to(REPO_ROOT)}")

    # Generate per-module files
    for yaml_path in yaml_files:
        source, msg_names = _generate_module(yaml_path)
        group = yaml_path.stem
        out_path = GENERATED_DIR / f"{group}_messages.py"
        out_path.write_text(source)
        module_info[group] = msg_names
        print(f"  wrote {out_path.relative_to(REPO_ROOT)} ({len(msg_names)} messages)")

    # If generating all modules, also produce __init__.py
    if not module_names or set(module_names) == {f.stem for f in sorted(SIGNAL_DB_DIR.glob("*.yaml"))}:
        # Need to re-scan all for init
        all_yaml = sorted(SIGNAL_DB_DIR.glob("*.yaml"))
        all_info: dict[str, list[str]] = {}
        for yp in all_yaml:
            with open(yp) as fh:
                spec = yaml.safe_load(fh)
            all_info[yp.stem] = list(spec["messages"].keys())
        init_path = GENERATED_DIR / "__init__.py"
        init_path.write_text(_generate_init(all_info))
        print(f"  wrote {init_path.relative_to(REPO_ROOT)}")

    print(f"\nDone — {sum(len(v) for v in module_info.values())} message classes generated.")


if __name__ == "__main__":
    modules = sys.argv[1:] if len(sys.argv) > 1 else None
    main(modules)
