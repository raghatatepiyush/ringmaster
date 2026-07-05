#!/usr/bin/env python3
"""Ringmaster — ledger helpers (pure functions + thin CLI).  Schema v2.

Stdlib-only, cross-platform. This module is the canonical spec for ledger
validation, the prioritization order, the A-grade gate check, and the team
board render — the target of hooks/test_ledger.py and an optional deterministic
helper the orchestrator may call (it can also follow the documented algorithm).

Back-compatible: accepts schemaVersion 1 or 2. v2 adds, per task, an `assignee`
(who on the team owns it — principal / an engineer lane / a junior worker), an
optional `gate` record (the six A-grade criteria as booleans), and an optional
`tokensEstimated`; and, top-level, a `waitingOnHuman` flag the Stop hook reads
so it never traps a legitimate pause for a question. No third-party deps.
"""
import json
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from routing import AGRADE_CRITERIA, should_escalate  # canonical source
except Exception:  # keep the CLI working even if routing isn't importable
    AGRADE_CRITERIA = ("correct", "secure", "clean", "complete", "documented", "explained")

    def should_escalate(gate_results):  # mirror of routing.should_escalate
        if not isinstance(gate_results, dict):
            return True
        return any(not gate_results.get(c, False) for c in AGRADE_CRITERIA)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VALID_STATUS = {"pending", "in_progress", "done", "blocked"}
_EFFORT_RANK = {"low": 0, "medium": 1, "high": 2}

DEFAULT_GITIGNORE = (
    "# Ringmaster working memory — self-ignored so it never pollutes your repo history.\n"
    "# To share task state with your team, Ringmaster un-ignores PROGRESS.md on request.\n"
    "*\n"
    "!.gitignore\n"
)


def validate_state(state) -> List[str]:
    """Return a list of human-readable errors; an empty list means valid."""
    errors = []  # type: List[str]
    if not isinstance(state, dict):
        return ["state must be a JSON object"]
    if state.get("schemaVersion") not in (1, 2):
        errors.append("schemaVersion must be 1 or 2")
    tasks = state.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be a list")
        return errors
    ids = set()
    for i, t in enumerate(tasks):
        where = "tasks[%d]" % i
        if not isinstance(t, dict):
            errors.append("%s must be an object" % where)
            continue
        tid = t.get("id")
        if not tid:
            errors.append("%s.id is required" % where)
        elif tid in ids:
            errors.append("%s.id '%s' is duplicated" % (where, tid))
        else:
            ids.add(tid)
        if t.get("status") not in VALID_STATUS:
            errors.append("%s.status must be one of %s" % (where, sorted(VALID_STATUS)))
        gate = t.get("gate")
        if gate is not None and not isinstance(gate, dict):
            errors.append("%s.gate must be an object of A-grade criteria" % where)
    for i, t in enumerate(tasks):
        if not isinstance(t, dict):
            continue
        for dep in (t.get("dependsOn") or []):
            if dep not in ids:
                errors.append("tasks[%d].dependsOn references unknown id '%s'" % (i, dep))
    return errors


def _unblock_count(tasks, tid) -> int:
    return sum(1 for t in tasks
               if isinstance(t, dict) and tid in (t.get("dependsOn") or []))


def next_task(state) -> Optional[str]:
    """Return the id of the highest-priority ELIGIBLE task, or None.

    Eligible = status 'pending' and every dependsOn id is 'done'. Ordering:
    priority asc (1 = highest), then more-downstream-unblocked first, then lower
    effort first, then id for stability.
    """
    tasks = state.get("tasks", []) if isinstance(state, dict) else []
    done = {t["id"] for t in tasks
            if isinstance(t, dict) and t.get("status") == "done" and t.get("id")}
    eligible = []
    for t in tasks:
        if not isinstance(t, dict) or t.get("status") != "pending":
            continue
        if all(d in done for d in (t.get("dependsOn") or [])):
            eligible.append(t)
    if not eligible:
        return None

    def sort_key(t):
        effort = (t.get("profile") or {}).get("effort", "medium")
        return (
            t.get("priority", 1000000),
            -_unblock_count(tasks, t.get("id")),
            _EFFORT_RANK.get(effort, 1),
            str(t.get("id")),
        )

    eligible.sort(key=sort_key)
    return eligible[0].get("id")


def gate_status(task):
    """Return (passed: bool, missing: list[str]) for a task's A-grade gate.

    A missing gate record counts as all-criteria-missing (fail-closed), matching
    routing.should_escalate so the cheap path can never silently skip the bar.
    """
    gate = task.get("gate") if isinstance(task, dict) else None
    if not isinstance(gate, dict):
        return (False, list(AGRADE_CRITERIA))
    missing = [c for c in AGRADE_CRITERIA if not gate.get(c, False)]
    return (not missing, missing)


_STATUS_ICON = {"pending": "○", "in_progress": "◐", "done": "●", "blocked": "✗"}
_BUCKET_TITLE = {"in_progress": "In progress", "pending": "Pending",
                 "blocked": "Blocked", "done": "Done"}


def board(state) -> str:
    """Render the team board: who owns what, status, dependencies, gate state.

    This is the 'everyone knows who is working on what' view — for the human at
    a glance and for a resuming session. Pure string render; never raises on a
    well-formed-enough state.
    """
    tasks = state.get("tasks", []) if isinstance(state, dict) else []
    buckets = {"in_progress": [], "pending": [], "blocked": [], "done": []}
    for t in tasks:
        if isinstance(t, dict):
            buckets.get(t.get("status"), buckets["pending"]).append(t)
    lines = []
    for key in ("in_progress", "pending", "blocked", "done"):
        rows = buckets[key]
        if not rows:
            continue
        lines.append("%s %s (%d)" % (_STATUS_ICON.get(key, "•"), _BUCKET_TITLE[key], len(rows)))
        for t in rows:
            who = t.get("assignee") or "unassigned"
            deps = ", ".join(t.get("dependsOn") or [])
            dep_s = ("  <- needs " + deps) if deps else ""
            g = ""
            if key in ("in_progress", "done") and isinstance(t.get("gate"), dict):
                ok, missing = gate_status(t)
                g = "  [gate OK]" if ok else "  [gate: missing %s]" % ",".join(missing)
            blk = ""
            if key == "blocked" and t.get("blockedBy"):
                blk = "  (blocked: %s)" % t.get("blockedBy")
            lines.append("    %s %s — %s%s%s%s" % (
                t.get("id"), t.get("title", ""), who, dep_s, g, blk))
    return "\n".join(lines) if lines else "(no tasks yet)"


def share_gitignore(current_text: str) -> str:
    """Return .gitignore text with PROGRESS.md un-ignored. Idempotent."""
    stripped = [ln.strip() for ln in (current_text or "").splitlines()]
    if "!PROGRESS.md" in stripped:
        return current_text if current_text.endswith("\n") else current_text + "\n"
    lines = (current_text or "").splitlines()
    if "!.gitignore" not in stripped:
        lines.append("!.gitignore")
    lines.append("!PROGRESS.md")
    return "\n".join(lines) + "\n"


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _main(argv) -> int:
    if len(argv) >= 3 and argv[1] in {"validate", "next", "board", "gate"}:
        try:
            state = _load(argv[2])
        except Exception as exc:  # missing/corrupt -> non-zero, never crash hard
            print("error: %s" % exc, file=sys.stderr)
            return 2
        if argv[1] == "validate":
            errs = validate_state(state)
            for e in errs:
                print("invalid: %s" % e)
            if not errs:
                print("valid")
            return 1 if errs else 0
        if argv[1] == "next":
            nt = next_task(state)
            print(nt if nt else "")
            return 0
        if argv[1] == "board":
            print(board(state))
            return 0
        if argv[1] == "gate":
            if len(argv) < 4:
                print("usage: ledger.py gate <state.json> <taskId>", file=sys.stderr)
                return 2
            tid = argv[3]
            task = next((t for t in state.get("tasks", [])
                         if isinstance(t, dict) and t.get("id") == tid), None)
            if task is None:
                print("error: no task '%s'" % tid, file=sys.stderr)
                return 2
            ok, missing = gate_status(task)
            if ok:
                print("PASS %s — A-grade gate complete" % tid)
                return 0
            print("FAIL %s — escalate to premium model; missing: %s"
                  % (tid, ", ".join(missing)))
            return 1
    print("usage: ledger.py [validate|next|board|gate] <state.json> [taskId]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
