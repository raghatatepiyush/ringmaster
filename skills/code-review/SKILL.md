---
name: code-review
description: "The bundled two-axis code review — use to review a change for quality and spec-fit before it is staged and handed off. Trigger on 'review this change/branch/PR', 'code review', 'is this sound', 'does this match the ticket', or as the orchestrator's Stage 3 review step. It reviews the diff along two independent axes run as parallel fresh-context sub-agents — Spec (does the change do what the plan/PRD/ticket asked, no more, no less?) and Standards (is the code correct, safe on edge cases, and conventional?) — then aggregates both into one house-style report and records the gate.clean criterion the Stop hook enforces. It runs AFTER the Security Gate and BEFORE the ownership review. It reports defects; it never fixes them, never commits, and never rubber-stamps."
---

# Code Review

Ringmaster's detection layer asks two questions of every change, and they are
genuinely different:

> **Spec — did we build the *right* thing?** Does the change do what was asked —
> the plan, the PRD, the ticket — no more and no less?
>
> **Standards — did we build the thing *right*?** Is the code correct, safe on its
> edges, and does it look like it belongs in this repo?

A single reviewer holding both questions at once bleeds them together — excusing
messy code because "it matches the ticket", or polishing style while a whole
requirement is quietly missing. So this skill runs the two axes as **parallel
fresh-context sub-agents** (`agents/code-reviewer.md`, dispatched twice — once per
axis) and lays their two reports side by side. Separation is the point.

This skill is **stack-independent**. It reviews; it does **not** fix, and it does not
re-run the Security Gate — it stands beside it.

---

## The safety rails (inherited, non-negotiable)

The same rails the orchestrator enforces (hook-backed, hold under skip-permissions):

1. **You review; you never fix.** Read-only. A real defect goes into the record and
   back to the human — you don't patch it.
2. **You never commit, push, or write history.** The only thing this skill writes is
   the ledger's `gate.clean` record. The human commits and ships.
3. **Never run anything against production.** Running the change's own tests to
   confirm a claim is DEV/UAT only.
4. **Never rubber-stamp.** ✅ clean is a valid verdict only when the paths were
   actually traced. Manufacturing findings to look thorough is as dishonest as
   waving a broken change through.

---

## Where this sits in "code review with Ringmaster"

```
Security Gate  →  code-review  →  Ownership Review  →  sign-off
  (secrets,       (Spec: right       (reconstruct         (gate.owned)
   injection,      thing? +           understanding,
   authz)          Standards:         teach the holes)
                   built right?)
```

Detection runs in order: the **Security Gate** clears the diff of vulnerabilities
first (it can block), then **this skill** reviews quality and spec-fit, then the
**Ownership Review** makes sure the human actually understands what they're about to
own. This skill produces the `clean` verdict the ownership review assumes has already
run.

---

## The pipeline

### Stage 0 — Pin the fixed point & risk-tier (cheap, first)

Get the change and what it was supposed to do:

- **The diff** — `git diff` (working) / `git diff --staged`, or the diff against a
  fixed point the user supplies (a commit SHA, branch, tag, `main`, `HEAD~5`, a PR
  base). If they didn't specify one, review the working/staged diff and say so.
- **The spec** — the plan/PRD/ticket/acceptance-criteria for the Spec axis. If none
  is available, note it; the Spec reviewer will review against the change's stated
  intent and flag the gap honestly (it must not invent acceptance criteria).

Risk-tier the change (reuse the comprehension tiers in `agents/comprehension.md`):
**trivial · standard · critical**. A **trivial** change (rename, comment, formatting,
isolated no-behavior config) gets a single light note and **skips the parallel
dispatch** — over-reviewing a typo is the fastest way to make this hated. Standard and
critical changes get the full two-axis pass.

### Stage 1 — Review both axes in parallel (the heart)

Dispatch **`agents/code-reviewer.md` twice, in parallel**, each in its own fresh
context (the Task tool), so the two lenses never pollute each other:

- **Dispatch A — `Axis: Spec`.** Brief it with the diff and the plan/PRD/ticket (or
  "no spec — review against stated intent"). It judges match-to-requirement only.
- **Dispatch B — `Axis: Standards`.** Brief it with the diff and the repo's
  conventions to match. It judges code soundness only.

Each returns a house-style per-axis report with a severity breakdown and a verdict.
Give each a complete brief — a subagent knows only what you tell it: the fixed point,
the files in scope, the target environment (DEV/UAT), and (for Spec) the acceptance
criteria.

> **If sub-agents aren't available** (no Task tool in this session), don't hard-fail:
> run both axes yourself in a single pass, in two clearly separated sections, and say
> plainly that they ran in one context rather than isolated ones.

### Stage 2 — Aggregate into one report

Combine both per-axis reports into the single house-style **two-stage review block**
(`skills/orchestrator/references/output-style.md`): Stage 1 = Spec (matches the
plan?), Stage 2 = Standards (code sound?). The **combined verdict** is the worse of
the two — **any 🔴 on either axis ⇒ 🛑 NEEDS CHANGES / BLOCKED**. Never bury a finding;
if either axis blocks, the change is not ready to hand off.

### Stage 3 — Record `gate.clean`

Record the outcome as the **`clean`** criterion on the change's ledger task in
`.ringmaster/state.json` (Ringmaster reads and writes this file directly — atomic
write, per `skills/orchestrator/references/state-and-resume.md`):

- Both axes ✅/⚠️ with no 🔴 → `gate.clean: true`.
- Any 🔴 on either axis → leave `gate.clean: false` and report BLOCKED; the change
  can't reach `done` until the human resolves it (the Stop hook, `hooks/stop_gate.py`,
  enforces the six A-grade criteria, of which `clean` is one — check any task with
  `python "${CLAUDE_PLUGIN_ROOT}/hooks/ledger.py" gate .ringmaster/state.json <id>`).

> **No ledger?** For an ad-hoc "review my branch" with no `.ringmaster/` ledger,
> produce the full review all the same — it just isn't hook-enforced (there's no task
> to record `clean` on). Say so honestly: the review is real, the *automatic*
> enforcement isn't active without a ledger.

---

## Output — the aggregated review

Emit the two-stage review block from `skills/orchestrator/references/output-style.md`,
filled from both axes: the Spec findings under Stage 1, the Standards findings under
Stage 2, the combined verdict, and a short **"in plain terms"** line — written so a
junior with no context understands whether this change is good to hand off and, if
not, the one thing that must change first.

## Status (end with exactly one)

- **DONE** — reviewed on both axes; no critical findings; `gate.clean: true` recorded.
  Lower-severity notes may still be listed.
- **DONE WITH CONCERNS** — no criticals, but high/medium findings on either axis the
  team should weigh before shipping; recorded, nothing buried.
- **BLOCKED** — at least one critical finding on Spec or Standards; `gate.clean` stays
  false and hand-off must not proceed until it's resolved.

---

## Reference files

- **`agents/code-reviewer.md`** — the per-axis reviewer you dispatch twice (once as
  `Axis: Spec`, once as `Axis: Standards`): the axis checklists, hard boundaries,
  severity scale, and report format. **Dispatch in Stage 1.**
- **`skills/orchestrator/references/output-style.md`** — the house two-stage review
  block and status protocol. **Read before printing.**
- **`skills/orchestrator/references/state-and-resume.md`** — the `.ringmaster/`
  ledger schema and atomic-write discipline for recording `gate.clean`. **Read in
  Stage 3.**
