#!/usr/bin/env python3
"""Ringmaster — battery for the ledger helpers (stdlib only)."""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger import (  # noqa: E402
    validate_state, next_task, share_gitignore, DEFAULT_GITIGNORE,
    gate_status, board,
)


def _task(tid, status="pending", priority=1, depends=None, effort="medium",
          assignee=None, gate=None):
    t = {
        "id": tid, "title": tid, "status": status, "priority": priority,
        "dependsOn": depends or [], "type": "feature",
        "profile": {"lane": "standard", "model": "sonnet", "effort": effort, "gate": "full"},
    }
    if assignee is not None:
        t["assignee"] = assignee
    if gate is not None:
        t["gate"] = gate
    return t


def _state(tasks, schema=2):
    return {"schemaVersion": schema, "project": "x", "updated": "now", "goal": "g", "tasks": tasks}


_FULL_GATE = {"correct": True, "secure": True, "clean": True,
              "complete": True, "documented": True, "explained": True}

VALIDATE_CASES = [
    ("valid minimal", _state([_task("T1")]), True),
    ("valid v1 still accepted", _state([_task("T1")], schema=1), True),
    ("bad schemaVersion", {"schemaVersion": 3, "tasks": []}, False),
    ("tasks not a list", {"schemaVersion": 2, "tasks": {}}, False),
    ("missing id", _state([{"status": "pending"}]), False),
    ("duplicate id", _state([_task("T1"), _task("T1")]), False),
    ("bad status", _state([{"id": "T1", "status": "wip"}]), False),
    ("unknown dependsOn", _state([_task("T1", depends=["T9"])]), False),
    ("not an object", [], False),
    ("valid with gate + assignee", _state([_task("T1", assignee="engineer:auth", gate=_FULL_GATE)]), True),
    ("bad gate type", _state([_task("T1", gate=["correct"])]), False),
]

NEXT_CASES = [
    # name, state, expected next id
    ("single pending", _state([_task("T1")]), "T1"),
    ("priority wins", _state([_task("T1", priority=5), _task("T2", priority=1)]), "T2"),
    ("blocked by unmet dep", _state([_task("T1", status="pending", depends=["T2"]),
                                     _task("T2", status="pending")]), "T2"),
    ("dep satisfied unlocks", _state([_task("T1", depends=["T2"]),
                                      _task("T2", status="done")]), "T1"),
    ("all blocked -> None", _state([_task("T1", status="pending", depends=["T2"]),
                                    _task("T2", status="in_progress")]), None),
    ("none pending -> None", _state([_task("T1", status="done")]), None),
    # tie on priority -> the one unblocking more downstream tasks wins
    ("unblock-count tie-break", _state([
        _task("A", priority=1),
        _task("B", priority=1),
        _task("C", status="pending", depends=["A"]),
        _task("D", status="pending", depends=["A"]),
    ]), "A"),
]


def run():
    failures = []
    for name, state, expected_valid in VALIDATE_CASES:
        got_valid = (validate_state(state) == [])
        if got_valid != expected_valid:
            failures.append(f"validate[{name}]: expected valid={expected_valid}, got {got_valid} ({validate_state(state)})")
    for name, state, expected in NEXT_CASES:
        got = next_task(state)
        if got != expected:
            failures.append(f"next[{name}]: expected {expected!r}, got {got!r}")
    # share_gitignore: adds the un-ignore, and is idempotent
    once = share_gitignore(DEFAULT_GITIGNORE)
    twice = share_gitignore(once)
    if "!PROGRESS.md" not in once:
        failures.append("share_gitignore did not un-ignore PROGRESS.md")
    if once != twice:
        failures.append("share_gitignore is not idempotent")

    # gate_status: full gate passes; a partial gate reports what's missing;
    # an absent gate is fail-closed (all criteria missing).
    ok, missing = gate_status(_task("T1", gate=_FULL_GATE))
    if not ok or missing:
        failures.append(f"gate_status(full) -> ({ok}, {missing})")
    ok, missing = gate_status(_task("T1", gate={"correct": True, "secure": False}))
    if ok or "secure" not in missing:
        failures.append(f"gate_status(partial) -> ({ok}, {missing})")
    ok, missing = gate_status(_task("T1"))
    if ok or len(missing) != 6:
        failures.append(f"gate_status(absent) must be fail-closed -> ({ok}, {missing})")

    # board: renders buckets, includes ids + assignee, never crashes
    rendered = board(_state([
        _task("T1", status="in_progress", assignee="principal", gate={"secure": False}),
        _task("T2", status="pending", depends=["T1"], assignee="engineer:ui"),
        _task("T3", status="done", gate=_FULL_GATE),
    ]))
    for needle in ("In progress", "Pending", "Done", "T1", "T2", "engineer:ui", "gate"):
        if needle not in rendered:
            failures.append(f"board() missing '{needle}' in:\n{rendered}")
    if board(_state([])) != "(no tasks yet)":
        failures.append("board() empty-state wrong")

    extra = 3 + 3 + 1  # gate_status(3) + board needles(grouped as 3) + empty(1)
    total = len(VALIDATE_CASES) + len(NEXT_CASES) + 2 + extra
    print(f"Ringmaster ledger battery: {total - len(failures)}/{total} cases as expected.")
    if failures:
        print("\nUnexpected results:")
        for f in failures:
            print("  " + f)
        return 1
    print("All ledger helpers behaving as specified. ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
