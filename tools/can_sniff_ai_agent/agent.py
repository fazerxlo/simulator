from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LOG_PATTERN = re.compile(
    r"^\((?P<timestamp>\d+\.\d+)\)\s+"
    r"(?P<interface>\S+)\s+"
    r"(?P<can_id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)$"
)


class CaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class CanFrame:
    timestamp: float
    interface: str
    can_id: str
    data: str


@dataclass(frozen=True)
class SignalCandidate:
    can_id: str
    score: int
    baseline_count: int
    action_count: int
    baseline_top_payload: str | None
    action_top_payload: str | None
    new_payloads: tuple[str, ...]
    removed_payloads: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "can_id": self.can_id,
            "score": self.score,
            "baseline_count": self.baseline_count,
            "action_count": self.action_count,
            "baseline_top_payload": self.baseline_top_payload,
            "action_top_payload": self.action_top_payload,
            "new_payloads": list(self.new_payloads),
            "removed_payloads": list(self.removed_payloads),
        }


@dataclass(frozen=True)
class DeltaReport:
    total_baseline_frames: int
    total_action_frames: int
    ignored_ids: tuple[str, ...]
    candidates: tuple[SignalCandidate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_baseline_frames": self.total_baseline_frames,
            "total_action_frames": self.total_action_frames,
            "ignored_ids": list(self.ignored_ids),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def sniff_packets(duration: int, interface: str = "can0") -> str:
    """Capture CAN packets from a SocketCAN interface using candump."""
    if duration <= 0:
        raise ValueError("duration must be a positive integer")

    if shutil.which("candump") is None:
        raise CaptureError("candump is not installed. Install can-utils and retry.")

    if shutil.which("timeout") is None:
        raise CaptureError("timeout is not installed. It is required to limit capture duration.")

    result = subprocess.run(
        ["timeout", f"{duration}s", "candump", "-L", interface],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode not in (0, 124):
        error_text = (result.stderr or result.stdout).strip()
        if not error_text:
            error_text = "unknown error"
        raise CaptureError(f"candump failed: {error_text}")

    output = result.stdout.strip()
    if not output:
        raise CaptureError(f"No data captured on {interface}. Ensure the interface is UP and traffic is present.")

    return output


def parse_candump_log(log_text: str) -> list[CanFrame]:
    frames: list[CanFrame] = []
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = LOG_PATTERN.match(line)
        if not match:
            continue

        frames.append(
            CanFrame(
                timestamp=float(match.group("timestamp")),
                interface=match.group("interface"),
                can_id=match.group("can_id").upper(),
                data=match.group("data").upper(),
            )
        )
    return frames


def summarize_log(log_text: str, top_n: int = 12) -> str:
    frames = parse_candump_log(log_text)
    if not frames:
        return "No valid CAN frames found in capture."

    counts = Counter(frame.can_id for frame in frames)
    lines = [f"Captured {len(frames)} frames across {len(counts)} CAN IDs."]
    for can_id, count in counts.most_common(top_n):
        payloads = Counter(frame.data for frame in frames if frame.can_id == can_id)
        payload, payload_count = payloads.most_common(1)[0]
        lines.append(
            f"- {can_id}: {count} frames, top payload {payload} ({payload_count}x)"
        )

    if len(counts) > top_n:
        lines.append(f"- ... {len(counts) - top_n} more IDs omitted")

    return "\n".join(lines)


def compare_logs(baseline_log: str, action_log: str) -> DeltaReport:
    baseline_frames = parse_candump_log(baseline_log)
    action_frames = parse_candump_log(action_log)

    baseline_by_id = _group_payloads(baseline_frames)
    action_by_id = _group_payloads(action_frames)

    ignored_ids: list[str] = []
    candidates: list[SignalCandidate] = []
    all_ids = sorted(set(baseline_by_id) | set(action_by_id))

    for can_id in all_ids:
        baseline_payloads = baseline_by_id.get(can_id, Counter())
        action_payloads = action_by_id.get(can_id, Counter())

        baseline_count = sum(baseline_payloads.values())
        action_count = sum(action_payloads.values())
        new_payloads = tuple(sorted(set(action_payloads) - set(baseline_payloads)))
        removed_payloads = tuple(sorted(set(baseline_payloads) - set(action_payloads)))

        if _is_stable_message(baseline_payloads, action_payloads):
            ignored_ids.append(can_id)
            continue

        score = _score_candidate(baseline_payloads, action_payloads)
        if score <= 0:
            continue

        candidates.append(
            SignalCandidate(
                can_id=can_id,
                score=score,
                baseline_count=baseline_count,
                action_count=action_count,
                baseline_top_payload=_top_payload(baseline_payloads),
                action_top_payload=_top_payload(action_payloads),
                new_payloads=new_payloads,
                removed_payloads=removed_payloads,
            )
        )

    candidates.sort(key=lambda candidate: (-candidate.score, candidate.can_id))
    return DeltaReport(
        total_baseline_frames=len(baseline_frames),
        total_action_frames=len(action_frames),
        ignored_ids=tuple(ignored_ids),
        candidates=tuple(candidates),
    )


def render_delta_report(report: DeltaReport, signal_name: str | None = None, limit: int = 10) -> str:
    header = "Analysis complete."
    if signal_name:
        header = f"Analysis complete for {signal_name}."

    lines = [header]
    lines.append(
        f"Baseline frames: {report.total_baseline_frames}, action frames: {report.total_action_frames}."
    )

    if not report.candidates:
        lines.append("No meaningful deltas found. Try a longer capture or reduce unrelated bus activity.")
        return "\n".join(lines)

    lines.append("Most likely signal candidates:")
    for candidate in report.candidates[:limit]:
        details: list[str] = [
            f"ID {candidate.can_id}",
            f"score {candidate.score}",
            f"count {candidate.baseline_count}->{candidate.action_count}",
        ]
        if candidate.baseline_top_payload or candidate.action_top_payload:
            details.append(
                f"top payload {candidate.baseline_top_payload or 'none'} -> {candidate.action_top_payload or 'none'}"
            )
        if candidate.new_payloads:
            details.append(f"new payloads {', '.join(candidate.new_payloads)}")
        if candidate.removed_payloads:
            details.append(f"removed payloads {', '.join(candidate.removed_payloads)}")
        lines.append(f"- {'; '.join(details)}")

    if report.ignored_ids:
        preview = ", ".join(report.ignored_ids[:8])
        suffix = "" if len(report.ignored_ids) <= 8 else ", ..."
        lines.append(f"Ignored stable IDs: {preview}{suffix}")

    return "\n".join(lines)


def identify_signal(
    signal_name: str,
    duration: int,
    interface: str = "can0",
    baseline_prompt: str = "Keep the target control OFF, then press Enter to start the baseline capture.",
    action_prompt: str | None = None,
) -> DeltaReport:
    print(baseline_prompt)
    input().strip()
    print(f"Capturing baseline on {interface} for {duration}s...")
    baseline_log = sniff_packets(duration=duration, interface=interface)

    prompt = action_prompt or f"Please toggle {signal_name} now, then press Enter to capture the action state."
    print(prompt)
    input().strip()
    print(f"Capturing action state on {interface} for {duration}s...")
    action_log = sniff_packets(duration=duration, interface=interface)

    report = compare_logs(baseline_log, action_log)
    print(render_delta_report(report, signal_name=signal_name))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CAN sniffing agent for signal discovery.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sniff_parser = subparsers.add_parser("sniff", help="Capture CAN traffic and print the result.")
    sniff_parser.add_argument("duration", type=int, help="Capture duration in seconds.")
    sniff_parser.add_argument("--interface", default="can0", help="SocketCAN interface name.")
    sniff_parser.add_argument(
        "--max-lines",
        type=int,
        default=500,
        help="Maximum raw lines to print before switching to a summary.",
    )

    compare_parser = subparsers.add_parser("compare", help="Compare two candump log files.")
    compare_parser.add_argument("baseline", type=Path, help="Path to the baseline candump log.")
    compare_parser.add_argument("action", type=Path, help="Path to the action candump log.")
    compare_parser.add_argument("--signal", default=None, help="Optional signal name for the report header.")
    compare_parser.add_argument("--json", action="store_true", help="Output the comparison as JSON.")

    identify_parser = subparsers.add_parser(
        "identify",
        help="Run an interactive baseline/action workflow to find a changed signal.",
    )
    identify_parser.add_argument("signal", help="Human-readable name of the signal to identify.")
    identify_parser.add_argument("--duration", type=int, default=5, help="Capture duration in seconds.")
    identify_parser.add_argument("--interface", default="can0", help="SocketCAN interface name.")
    identify_parser.add_argument(
        "--baseline-prompt",
        default="Keep the target control OFF, then press Enter to start the baseline capture.",
        help="Prompt displayed before the baseline capture.",
    )
    identify_parser.add_argument(
        "--action-prompt",
        default=None,
        help="Prompt displayed before the action capture.",
    )
    identify_parser.add_argument("--json", action="store_true", help="Print the final report as JSON.")

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "sniff":
            log_text = sniff_packets(duration=args.duration, interface=args.interface)
            lines = log_text.splitlines()
            if len(lines) > args.max_lines:
                print(summarize_log(log_text))
            else:
                print(log_text)
            return 0

        if args.command == "compare":
            report = compare_logs(args.baseline.read_text(), args.action.read_text())
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            else:
                print(render_delta_report(report, signal_name=args.signal))
            return 0

        if args.command == "identify":
            report = identify_signal(
                signal_name=args.signal,
                duration=args.duration,
                interface=args.interface,
                baseline_prompt=args.baseline_prompt,
                action_prompt=args.action_prompt,
            )
            if args.json:
                print(json.dumps(report.to_dict(), indent=2))
            return 0

    except CaptureError as error:
        parser.exit(status=1, message=f"Error: {error}\n")

    return 1


def _group_payloads(frames: Iterable[CanFrame]) -> dict[str, Counter[str]]:
    grouped: dict[str, Counter[str]] = {}
    for frame in frames:
        grouped.setdefault(frame.can_id, Counter())[frame.data] += 1
    return grouped


def _is_stable_message(baseline_payloads: Counter[str], action_payloads: Counter[str]) -> bool:
    if not baseline_payloads and not action_payloads:
        return True

    if baseline_payloads == action_payloads:
        return True

    if set(baseline_payloads) != set(action_payloads):
        return False

    baseline_total = sum(baseline_payloads.values())
    action_total = sum(action_payloads.values())
    if baseline_total == 0 or action_total == 0:
        return False

    ratio = max(baseline_total, action_total) / min(baseline_total, action_total)
    return ratio <= 1.15


def _score_candidate(baseline_payloads: Counter[str], action_payloads: Counter[str]) -> int:
    score = 0
    new_payloads = set(action_payloads) - set(baseline_payloads)
    removed_payloads = set(baseline_payloads) - set(action_payloads)
    baseline_total = sum(baseline_payloads.values())
    action_total = sum(action_payloads.values())

    score += 4 * len(new_payloads)
    score += 2 * len(removed_payloads)

    shared_payloads = set(action_payloads) & set(baseline_payloads)
    for payload in shared_payloads:
        score += abs(action_payloads[payload] - baseline_payloads[payload])

    baseline_top = _top_payload(baseline_payloads)
    action_top = _top_payload(action_payloads)
    if baseline_top != action_top:
        score += 3

    if baseline_payloads and action_payloads:
        score += 5 + min(baseline_total, action_total)
    elif baseline_payloads and not action_payloads:
        score += 1
    elif action_payloads and not baseline_payloads:
        score += 3 + min(action_total, 2)

    return score


def _top_payload(payloads: Counter[str]) -> str | None:
    if not payloads:
        return None
    return payloads.most_common(1)[0][0]


if __name__ == "__main__":
    raise SystemExit(main())