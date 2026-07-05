# Right-Sizing — the Task Profile

The cost of orchestration must be proportional to the task. A great ringmaster doesn't call the whole troupe into the ring to juggle a single ball — and Ringmaster shouldn't spin up the Test Architect, the Security Gate, a review pass, and a fresh-context subagent to fix a typo in a comment. Right-sizing is how Ringmaster stays fast, tidy, and token-frugal on small work while still bringing the full machinery to bear on work that earns it. Read this in stage 1, the moment you've classified the task.

The output of right-sizing is a single bundle — the **Task Profile** — computed once and recorded in the ledger.

---

## The Task Profile

One triage decision answers four questions at once:

```
TaskProfile = { lane, model, effort, gate }
  lane   ∈ { trivial, standard, deep }   how much ceremony the work warrants
  model  ∈ { haiku, sonnet, opus }       which model tier to run it on
  effort ∈ { low, medium, high }          how hard to think
  gate   ∈ { light, full, widened }       how deep the verify/secure/review gate runs
```

Compute it in stage 1, write it into the task's `profile` field in the ledger, and let it drive everything downstream: which specialist/model handles the step (`references/model-and-effort.md`), whether you HALT at the plan gate, and how thorough the verification is. One concept, set once — not three scattered judgments.

---

## The three lanes

| Lane | What it is | Signals |
| :-- | :-- | :-- |
| **trivial** | No change to production behavior | A one-line doc/comment/format edit, a rename with no semantic change, a pure test-file edit, scaffolding, a config tweak with no runtime effect. Single file, no logic, no new dependency, no user-input path, trivially reversible. |
| **standard** | The everyday unit of real work | Most features, fixes, and tests. Production behavior changes; the blast radius is bounded and the path is reasonably clear. |
| **deep** | High-stakes or hard-to-reason work | The person said "go deep" / "thorough" / "critical" / "high-stakes"; or it touches security, payments, auth, or data integrity; or requirements are ambiguous; or it spans multiple subsystems; or a wrong move is expensive to undo. |

When a request blends lanes (a trivial doc tweak bundled with a real feature), profile each piece on its own — don't let the trivial part borrow the feature's ceremony, or the feature part hide in the trivial part's lightness.

---

## The right-sizing principle

**Spend ceremony where it buys safety or quality, nowhere else.** A `trivial` task skips the heavy pipeline: no plan-HALT, often a cheaper-model subagent, a `light` gate (a quick read-back and a sanity check rather than the full test+security+review battery). A `standard` task runs the normal pipeline. A `deep` task widens everything — read callers and contracts, broaden the test battery, add an explicit security pass, iterate review until issues are exhausted (the existing effort dial).

This is the same instinct as the token-discipline section in `SKILL.md`, made concrete: most runs are frugal; you escalate deliberately and say so.

---

## The hard guard — ceremony, never safety

> **Triage tunes how much ceremony a task gets. It never tunes the safety rails.**

The lane decides *ceremony weight* — it must never become an excuse to skip a safety gate on real behavior. So the bright line:

- **Any change to production behavior is at minimum `standard`**, and therefore always ships with tests (Test Architect) and always passes the Security Gate before staging. There is no "trivial" production-behavior change.
- `trivial` is reserved for changes that genuinely cannot alter what the running system does: docs, comments, formatting, pure test edits, scaffolding.
- The hook-enforced rails (no commit/push/merge, no PROD, ship-on-command gates) apply **identically in every lane**. A trivial task gets a lighter *process*, never a lighter *boundary*.

If you're unsure whether something touches production behavior, it does — treat it as `standard`. The cheap over-classification beats the expensive missed defect.

---

## Lane → what actually changes

| Lane | Plan gate | Tests + Security Gate | Typical model · effort · gate |
| :-- | :-- | :-- | :-- |
| **trivial** | Skip (just do it) | Not required (no production-behavior change) | haiku · low · light |
| **standard** | HALT on substantial work | **Required** | sonnet (→ opus if reasoning-heavy) · medium/high · full |
| **deep** | Always HALT | **Required + widened** | opus · high · widened |

The model/effort/gate columns are the defaults from `references/model-and-effort.md` — where the model-independent A-grade gate and the auto-escalation rule live. Right-sizing decides the lane; that reference decides what the lane costs and how its quality is guaranteed.
