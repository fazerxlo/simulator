"""Helper to re-run codegen into an arbitrary output directory.

Used by test_codegen.py for the idempotency check.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def regenerate_to_dir(out_dir: Path | str, can_version: str = "2004") -> None:
    """Run the code generator, writing output to *out_dir* instead of
    the default ``generated/`` directory."""
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)

    # Load the codegen module from its file path (signal-db has a hyphen).
    codegen_path = REPO_ROOT / "signal-db" / "codegen" / "gen_py_encoder.py"
    spec = importlib.util.spec_from_file_location("gen_py_encoder", codegen_path)
    codegen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codegen)

    # Temporarily override the codegen output directory.
    orig_dir = codegen.GENERATED_DIR
    try:
        codegen.GENERATED_DIR = out_dir
        codegen.main(can_version=can_version)
    finally:
        codegen.GENERATED_DIR = orig_dir
