#!/usr/bin/env python3
"""Ringmaster — battery for the routing/profile helpers (stdlib only)."""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routing import (  # noqa: E402
    profile_for_lane, gate_for_lane, should_escalate, AGRADE_CRITERIA,
)


def run():
    failures = []

    # profile_for_lane maps each lane correctly
    expect = {
        "trivial": ("haiku", "low", "light"),
        "standard": ("sonnet", "medium", "full"),
        "deep": ("opus", "high", "widened"),
    }
    for lane, (model, effort, gate) in expect.items():
        p = profile_for_lane(lane)
        if (p["model"], p["effort"], p["gate"]) != (model, effort, gate):
            failures.append(f"profile_for_lane[{lane}] -> {p}")

    # unknown lane falls back to standard
    if profile_for_lane("bogus")["gate"] != "full":
        failures.append("unknown lane did not fall back to standard")

    # returns a COPY (mutating one result must not affect the next)
    a = profile_for_lane("standard"); a["model"] = "haiku"
    if profile_for_lane("standard")["model"] != "sonnet":
        failures.append("profile_for_lane did not return an independent copy")

    # KEYSTONE INVARIANT: gate is a pure function of lane, independent of model.
    for lane in ("trivial", "standard", "deep"):
        base = gate_for_lane(lane)
        for model in ("haiku", "sonnet", "opus"):
            p = profile_for_lane(lane); p["model"] = model  # simulate downshift
            if gate_for_lane(lane) != base:
                failures.append(f"gate changed for {lane} under model {model}")

    # should_escalate: all pass -> False; any fail or missing -> True
    all_pass = {c: True for c in AGRADE_CRITERIA}
    if should_escalate(all_pass):
        failures.append("should_escalate True when all criteria pass")
    one_fail = dict(all_pass); one_fail["secure"] = False
    if not should_escalate(one_fail):
        failures.append("should_escalate False when a criterion fails")
    if not should_escalate({}):  # missing criteria are fail-closed
        failures.append("should_escalate False on missing criteria (must fail closed)")

    print(f"Ringmaster routing battery: {'OK' if not failures else 'FAIL'} "
          f"({len(AGRADE_CRITERIA)} A-grade criteria).")
    if failures:
        print("\nUnexpected results:")
        for f in failures:
            print("  " + f)
        return 1
    print("All routing helpers behaving as specified. ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
