#!/usr/bin/env python3
"""
Ringmaster - A-grade gate + ownership sign-off teeth (Stop hook).

The quality gate used to live only in prose: the orchestrator was *asked* to run
tests + Security Gate + review and not ship failing work. This hook gives that
one real tooth. A Stop hook fires when the main agent tries to end its turn; by
returning {"decision": "block", "reason": ...} it sends the agent back to finish
the job instead of stopping on unfinished work.

It guards two DISTINCT axes, both recorded on a task's `gate`:

  * the six UNIVERSAL A-grade criteria - correct, secure, clean, complete,
    documented, explained - "is the code excellent?" (canonical source:
    routing.AGRADE_CRITERIA); and

  * a seventh, CONDITIONAL criterion `owned` - "has a human honestly taken
    responsibility for this change?" It is written ONLY by the ownership-review
    skill's comprehension pass, and ONLY on a change someone is signing off. A
    task that never runs the ownership review never carries an `owned` key, so
    ordinary / trivial / test / docs work is never trapped by it. And because
    the ownership review sets
    `waitingOnHuman` while a sign-off is still pending (a legitimate pause this
    hook already allows), `owned` only ever bites the one bad pattern it exists
    for: a reviewed change being marked done while its ownership sign-off is on
    record as NOT honest.

It is deliberately CONSERVATIVE - it must never trap a legitimate pause:
  * It respects `stop_hook_active`: if we already blocked once this turn, we let
    the stop through (no loops).
  * It only fires when a `.ringmaster/state.json` ledger exists and an
    *in_progress* task carries a `gate` record with an EXPLICIT failure
    (a criterion recorded as false). A simply-absent gate - or a simply-absent
    `owned` - is NOT a trap.
  * It always allows the stop when `state.waitingOnHuman` is true - the
    orchestrator legitimately pausing to ask a question, or waiting on the human
    to complete the comprehension sign-off.
  * On ANY error it fails open (exit 0) - it can only ever *add* a nudge, never
    brick the session.

The decision logic is factored into pure functions (`evaluate`, `build_reason`,
`_failing_inprogress`) so it is directly unit-testable (hooks/test_stop_gate.py);
`main()` is a thin stdin/file/stdout wrapper around them.
"""

import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# The six universal A-grade criteria (code quality). Mirrors
# routing.AGRADE_CRITERIA; duplicated here so the Stop hook stays import-free.
AGRADE = ("correct", "secure", "clean", "complete", "documented", "explained")

# The conditional ownership sign-off (human responsibility) - a different axis,
# written only by the ownership-review skill's comprehension pass. See the docstring.
SIGNOFF = ("owned",)

# What an in-progress task must not walk away from when a criterion is EXPLICITLY
# recorded false. Absent criteria never trap - that is the conservative promise.
CRITERIA = AGRADE + SIGNOFF


def _failing_inprogress(state):
    """Return list of (task_id, [failing criteria]) for in_progress tasks whose
    gate record has at least one explicit false. Absent gate => not failing."""
    out = []
    tasks = state.get("tasks", []) if isinstance(state, dict) else []
    if not isinstance(tasks, list):  # e.g. "tasks": null or a string -> nothing to trap
        tasks = []
    for t in tasks:
        if not isinstance(t, dict) or t.get("status") != "in_progress":
            continue
        gate = t.get("gate")
        if not isinstance(gate, dict):
            continue  # no recorded gate yet -> do not trap
        failing = [c for c in CRITERIA if c in gate and not gate.get(c)]
        if failing:
            out.append((t.get("id", "?"), failing))
    return out


def build_reason(failing):
    """Compose the block message, tailored to whether the failing criteria are
    A-grade (code quality), the ownership sign-off, or both. Pure function."""
    bits = "; ".join("%s (missing: %s)" % (tid, ", ".join(cs)) for tid, cs in failing)
    agrade_pending = any(c in AGRADE for _, cs in failing for c in cs)
    owned_pending = any(c in SIGNOFF for _, cs in failing for c in cs)

    parts = [
        "Ringmaster gate: an in-progress task is on record as NOT yet ready, so "
        "don't finish here. " + bits + ". "
    ]
    if agrade_pending:
        parts.append(
            "For the A-grade criteria (correct/secure/clean/complete/documented/"
            "explained): run the Test Architect and the Security Gate, fix what "
            "they find, refresh docs, add the plain-language summary. "
        )
    if owned_pending:
        parts.append(
            "For `owned` (the human's ownership sign-off): the ownership-review skill's "
            "comprehension pass has not honestly cleared. Conduct it with the "
            "human - ask the questions, take their answers first, grade against "
            "the evidence, and teach on any miss - then set gate.owned=true ONLY "
            "if the sign-off is genuine. If you're waiting on the human to answer, "
            "set state.waitingOnHuman=true and ask - that lets you stop. Never set "
            "owned=true just to escape this gate. "
        )
    parts.append(
        "Update the task's gate in .ringmaster/state.json, then continue. If you're "
        "genuinely blocked, set that task to 'blocked' (with blockedBy) or set "
        "state.waitingOnHuman=true and ask your question - either lets you stop."
    )
    return "".join(parts)


def evaluate(data, state):
    """Pure decision: return a {'decision':'block','reason':...} dict to send the
    agent back, or None to allow the stop. IO-free, so it is directly testable."""
    # Never loop: if our own block already re-engaged the agent, let it stop.
    if isinstance(data, dict) and data.get("stop_hook_active"):
        return None
    # Legitimate pause for a question / a pending sign-off -> allow the stop.
    if isinstance(state, dict) and state.get("waitingOnHuman"):
        return None
    failing = _failing_inprogress(state)
    if not failing:
        return None
    return {"decision": "block", "reason": build_reason(failing)}


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # Never loop (checked early so we don't even touch the disk on a re-entry).
    if isinstance(data, dict) and data.get("stop_hook_active"):
        sys.exit(0)

    path = os.path.join(".ringmaster", "state.json")
    if not os.path.isfile(path):
        sys.exit(0)
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except Exception:
        sys.exit(0)

    try:
        decision = evaluate(data, state)
    except Exception:
        sys.exit(0)  # fail open on ANY error - only ever add a nudge, never brick
    if decision is not None:
        print(json.dumps(decision))
    sys.exit(0)


if __name__ == "__main__":
    main()
