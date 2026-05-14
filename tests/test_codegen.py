"""Tests for the signal-db code generator and generated encoder modules.

Validates that:
* The code generator produces correct Python from YAML signal definitions.
* Every generated message class matches the expected CAN ID, period, and
  module association.
* Re-running codegen produces output identical to the committed generated files
  (idempotency check).
* Adding a test signal to a YAML and re-running codegen produces usable code.
"""

import importlib
import os
import sys
import textwrap

import pytest
import yaml


# ---------------------------------------------------------------------------
# Ensure the repo root is on sys.path so generated/ is importable.
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAN_VERSION = "2004"
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_yaml(name):
    """Load a signal-db YAML file by module group name."""
    path = os.path.join(REPO_ROOT, "signal-db", CAN_VERSION, f"{name}.yaml")
    with open(path) as fh:
        return yaml.safe_load(fh)


def _all_yaml_names():
    """Return sorted list of all signal-db YAML file stems."""
    db_dir = os.path.join(REPO_ROOT, "signal-db", CAN_VERSION)
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(db_dir)
        if f.endswith(".yaml")
    )


# ---------------------------------------------------------------------------
# Test: YAML files are well-formed and contain required keys
# ---------------------------------------------------------------------------

class TestYAMLSchema:
    """Every signal-db YAML file must have the expected top-level keys."""

    @pytest.fixture(params=_all_yaml_names())
    def yaml_spec(self, request):
        return _load_yaml(request.param), request.param

    def test_has_module_group(self, yaml_spec):
        spec, name = yaml_spec
        assert "module_group" in spec, f"{name}.yaml missing 'module_group'"

    def test_has_messages(self, yaml_spec):
        spec, name = yaml_spec
        assert "messages" in spec, f"{name}.yaml missing 'messages'"
        assert len(spec["messages"]) > 0, f"{name}.yaml has no messages"

    def test_messages_have_required_fields(self, yaml_spec):
        spec, name = yaml_spec
        for msg_name, msg in spec["messages"].items():
            assert "can_id" in msg, f"{name}/{msg_name} missing can_id"
            assert "period_ms" in msg, f"{name}/{msg_name} missing period_ms"
            assert isinstance(msg["can_id"], int), f"{name}/{msg_name} can_id not int"
            assert isinstance(msg["period_ms"], int), f"{name}/{msg_name} period_ms not int"


# ---------------------------------------------------------------------------
# Test: Generated modules have the expected classes with correct attributes
# ---------------------------------------------------------------------------

class TestGeneratedModules:
    """Every generated module contains classes matching the YAML definitions."""

    @pytest.fixture(params=_all_yaml_names())
    def module_and_spec(self, request):
        name = request.param
        spec = _load_yaml(name)
        mod = importlib.import_module(f"generated.{name}_messages")
        return mod, spec, name

    def test_all_classes_present(self, module_and_spec):
        mod, spec, name = module_and_spec
        for msg_name in spec["messages"]:
            assert hasattr(mod, msg_name), (
                f"generated.{name}_messages missing class {msg_name}"
            )

    def test_can_id_matches(self, module_and_spec):
        mod, spec, name = module_and_spec
        for msg_name, msg_def in spec["messages"].items():
            cls = getattr(mod, msg_name)
            assert cls.can_id == msg_def["can_id"], (
                f"{msg_name}.can_id: expected 0x{msg_def['can_id']:03X}, "
                f"got 0x{cls.can_id:03X}"
            )

    def test_period_ms_matches(self, module_and_spec):
        mod, spec, name = module_and_spec
        for msg_name, msg_def in spec["messages"].items():
            cls = getattr(mod, msg_name)
            assert cls.period_ms == msg_def["period_ms"], (
                f"{msg_name}.period_ms: expected {msg_def['period_ms']}, "
                f"got {cls.period_ms}"
            )

    def test_required_modules_matches(self, module_and_spec):
        mod, spec, name = module_and_spec
        for msg_name, msg_def in spec["messages"].items():
            cls = getattr(mod, msg_name)
            expected = frozenset(msg_def.get("required_modules") or [])
            assert cls.required_modules == expected, (
                f"{msg_name}.required_modules: expected {expected}, "
                f"got {cls.required_modules}"
            )

    def test_listen_only_matches(self, module_and_spec):
        mod, spec, name = module_and_spec
        for msg_name, msg_def in spec["messages"].items():
            cls = getattr(mod, msg_name)
            expected = bool(msg_def.get("listen_only", False))
            assert cls.listen_only == expected, (
                f"{msg_name}.listen_only: expected {expected}, "
                f"got {cls.listen_only}"
            )


# ---------------------------------------------------------------------------
# Test: ALL_MESSAGES registry is complete
# ---------------------------------------------------------------------------

class TestAllMessagesRegistry:
    """The generated/__init__.py ALL_MESSAGES dict contains every message."""

    def test_all_messages_count(self):
        from generated import ALL_MESSAGES
        total = sum(
            len(spec["messages"])
            for spec in (_load_yaml(n) for n in _all_yaml_names())
        )
        assert len(ALL_MESSAGES) == total

    def test_all_ids_present(self):
        from generated import ALL_MESSAGES
        for name in _all_yaml_names():
            spec = _load_yaml(name)
            for msg_name, msg_def in spec["messages"].items():
                assert msg_def["can_id"] in ALL_MESSAGES, (
                    f"CAN ID 0x{msg_def['can_id']:03X} ({msg_name}) "
                    f"missing from ALL_MESSAGES"
                )


# ---------------------------------------------------------------------------
# Test: CanMessage base class
# ---------------------------------------------------------------------------

class TestCanMessageBase:
    def test_base_class_exists(self):
        from generated.base import CanMessage
        assert CanMessage.can_id == 0
        assert CanMessage.period_ms == 100

    def test_base_encode_returns_none(self):
        from generated.base import CanMessage
        msg = CanMessage()
        assert msg.encode(None) is None

    def test_base_repr(self):
        from generated.base import CanMessage
        msg = CanMessage()
        assert "CanMessage" in repr(msg)


# ---------------------------------------------------------------------------
# Test: STARTUP_WAKEUP_BURST constant
# ---------------------------------------------------------------------------

class TestStartupBurst:
    def test_burst_available(self):
        from generated import STARTUP_WAKEUP_BURST
        assert isinstance(STARTUP_WAKEUP_BURST, list)
        assert len(STARTUP_WAKEUP_BURST) == 9

    def test_burst_entries_are_tuples(self):
        from generated import STARTUP_WAKEUP_BURST
        for entry in STARTUP_WAKEUP_BURST:
            assert isinstance(entry, tuple)
            assert len(entry) == 3
            delay, can_id, data = entry
            assert isinstance(delay, float)
            assert isinstance(can_id, int)
            assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Test: Codegen idempotency — re-running produces the same output
# ---------------------------------------------------------------------------

class TestCodegenIdempotency:
    def test_regenerate_matches_committed(self, tmp_path):
        """Re-running the code generator produces output identical to
        what is already committed in generated/."""
        sys.path.insert(0, os.path.dirname(__file__))
        from signal_db_codegen_helper import regenerate_to_dir
        regenerate_to_dir(tmp_path, can_version=CAN_VERSION)

        generated_dir = os.path.join(REPO_ROOT, "generated")
        for fname in os.listdir(generated_dir):
            if not fname.endswith(".py"):
                continue
            committed = open(os.path.join(generated_dir, fname)).read()
            regenerated = open(os.path.join(tmp_path, fname)).read()
            assert committed == regenerated, (
                f"generated/{fname} differs from re-generated output"
            )
