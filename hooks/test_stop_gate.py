#!/usr/bin/env python3
"""Conductor - battery for the Stop gate (stdlib only).

Covers the two axes the hook guards - the six A-grade criteria and the
conditional `owned` ownership sign-off - plus every conservative escape hatch
(stop_hook_active, waitingOnHuman, absent gate, non-in_progress tasks). The
stdin/file/stdout wiring is separately smoke-tested in .github/workflows/ci.yml.
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stop_gate import (  # noqa: E402
    evaluate, build_reason, _failing_inprogress, AGRADE, SIGNOFF, CRITERIA,
)


def _task(tid="T1", status="in_progress", gate=None):
    t = {"id": tid, "status": status}
    if gate is not None:
        t["gate"] = gate
    return t


def _state(tasks, waiting=False):
    s = {"schemaVersion": 2, "tasks": tasks}
    if waiting:
        s["waitingOnHuman"] = True
    return s


FULL = {c: True for c in AGRADE}  # all six true, NO `owned` key (owned is conditional)

# name, data (hook payload), state, expected decision
CASES = [
    # --- the six A-grade criteria (unchanged behavior) ---
    ("no tasks -> allow",                    {}, _state([]),                                  "allow"),
    ("in_progress, no gate -> never trap",   {}, _state([_task(gate=None)]),                  "allow"),
    ("failing A-grade -> block",             {}, _state([_task(gate={"secure": False})]),     "block"),
    ("full A-grade gate -> allow",           {}, _state([_task(gate=FULL)]),                  "allow"),
    ("pending task failing -> allow",        {}, _state([_task(status="pending", gate={"secure": False})]), "allow"),
    ("done task failing -> allow",           {}, _state([_task(status="done", gate={"secure": False})]),    "allow"),
    ("stop_hook_active -> no loop, allow",   {"stop_hook_active": True}, _state([_task(gate={"secure": False})]), "allow"),
    ("waitingOnHuman -> allow though failing",{}, _state([_task(gate={"secure": False})], waiting=True),     "allow"),
    # --- the conditional ownership sign-off (new) ---
    ("owned absent -> never trap",           {}, _state([_task(gate=FULL)]),                  "allow"),
    ("owned:false -> block",                 {}, _state([_task(gate=dict(FULL, owned=False))]), "block"),
    ("owned:true + full A-grade -> allow",   {}, _state([_task(gate=dict(FULL, owned=True))]),  "allow"),
    ("owned:false but waitingOnHuman -> allow",{}, _state([_task(gate=dict(FULL, owned=False))], waiting=True), "allow"),
    ("owned:false + stop_hook_active -> allow",{"stop_hook_active": True}, _state([_task(gate=dict(FULL, owned=False))]), "allow"),
    # --- fail-open robustness (the docstring's "ANY error -> allow" promise) ---
    ("tasks is null -> fail open, allow",    {}, {"schemaVersion": 2, "tasks": None},  "allow"),
    ("tasks not a list -> allow",            {}, {"schemaVersion": 2, "tasks": "nope"}, "allow"),
    ("state is not a dict -> allow",         {}, [],                                    "allow"),
    ("data not a dict -> no crash, still evaluates state",  [], _state([_task(gate={"secure": False})]), "block"),
]


def run():
    failures = []

    for name, data, state, expected in CASES:
        decision = evaluate(data, state)
        got = "block" if (isinstance(decision, dict) and decision.get("decision") == "block") else "allow"
        if got != expected:
            failures.append("evaluate[%s]: expected %s, got %s" % (name, expected, got))

    # owned must be a real seventh criterion the scanner knows about
    if "owned" not in CRITERIA or set(AGRADE) & set(SIGNOFF):
        failures.append("CRITERIA/axes wrong: AGRADE=%s SIGNOFF=%s" % (AGRADE, SIGNOFF))

    # build_reason: A-grade-only failure teaches the A-grade path, not the owned path
    r = build_reason([("T1", ["secure"])])
    if "A-grade criteria" not in r or "ownership sign-off" in r:
        failures.append("build_reason(A-grade only) wrong: %r" % r)
    # owned-only failure teaches the ownership path and forbids self-signing
    r = build_reason([("T1", ["owned"])])
    if "ownership sign-off" not in r or "ONLY" not in r or "A-grade criteria" in r:
        failures.append("build_reason(owned only) wrong: %r" % r)
    # both axes failing -> both taught
    r = build_reason([("T1", ["secure", "owned"])])
    if "A-grade criteria" not in r or "ownership sign-off" not in r:
        failures.append("build_reason(both) wrong: %r" % r)

    # _failing_inprogress: only explicit false counts; absent keys never do
    f = _failing_inprogress(_state([_task(gate={"correct": True, "owned": False})]))
    if f != [("T1", ["owned"])]:
        failures.append("_failing_inprogress(owned false only) -> %r" % f)

    total = len(CASES) + 1 + 3 + 1  # cases + axes + 3 build_reason + failing_inprogress
    print("Conductor stop-gate battery: %d/%d cases as expected." % (total - len(failures), total))
    if failures:
        print("\nUnexpected results:")
        for x in failures:
            print("  " + x)
        return 1
    print("All stop-gate behavior as specified. ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
