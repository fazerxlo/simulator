from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent import compare_logs, parse_candump_log, summarize_log  # noqa: E402


BASELINE = """
(1741427240.001000) can0 21A#00000000
(1741427240.101000) can0 128#AA55
(1741427240.201000) can0 128#AA55
(1741427240.301000) can0 21A#00000000
""".strip()


ACTION = """
(1741427245.001000) can0 21A#00010000
(1741427245.101000) can0 128#AA55
(1741427245.201000) can0 128#AA55
(1741427245.301000) can0 21A#00010000
(1741427245.401000) can0 305#0F0F
""".strip()


def test_parse_candump_log_extracts_frames() -> None:
    frames = parse_candump_log(BASELINE)
    assert len(frames) == 4
    assert frames[0].can_id == "21A"
    assert frames[0].data == "00000000"


def test_compare_logs_prioritizes_changed_signal() -> None:
    report = compare_logs(BASELINE, ACTION)
    assert report.candidates
    assert report.candidates[0].can_id == "21A"
    assert "00010000" in report.candidates[0].new_payloads
    assert "128" in report.ignored_ids


def test_summarize_log_reports_top_ids() -> None:
    summary = summarize_log(ACTION, top_n=2)
    assert "Captured 5 frames across 3 CAN IDs." in summary
    assert "21A: 2 frames" in summary