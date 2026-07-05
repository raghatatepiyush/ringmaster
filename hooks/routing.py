#!/usr/bin/env python3
"""Ringmaster — routing / Task-Profile helpers (pure). Stdlib-only, cross-platform.

The keystone: `gate` is a pure function of `lane`, NEVER of `model`. Downshifting
a model to save tokens therefore cannot weaken the quality gate; work that fails
the model-independent A-grade gate auto-escalates to the premium model.
"""

# Lane -> default profile. Conservative routing (premium by default; only
# mechanically-trivial lanes downshift).
_LANE_PROFILE = {
    "trivial":  {"model": "haiku",  "effort": "low",    "gate": "light"},
    "standard": {"model": "sonnet", "effort": "medium", "gate": "full"},
    "deep":     {"model": "opus",   "effort": "high",   "gate": "widened"},
}
_GATE_FOR_LANE = {"trivial": "light", "standard": "full", "deep": "widened"}

# The A-grade rubric. A step is A-grade only if ALL six pass.
AGRADE_CRITERIA = ("correct", "secure", "clean", "complete", "documented", "explained")


def profile_for_lane(lane):
    """Return a fresh {model, effort, gate} for a lane. Unknown lane -> standard."""
    base = _LANE_PROFILE.get(lane, _LANE_PROFILE["standard"])
    return dict(base)


def gate_for_lane(lane):
    """The quality-gate strength for a lane — a pure function of lane only."""
    return _GATE_FOR_LANE.get(lane, "full")


def should_escalate(gate_results):
    """True iff any A-grade criterion is not passed (missing == not passed)."""
    if not isinstance(gate_results, dict):
        return True
    return any(not gate_results.get(c, False) for c in AGRADE_CRITERIA)
