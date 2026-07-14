---
name: ownership-review
description: "The ownership review - use when a developer must take 100% responsibility for a code change written largely by AI and wants to genuinely understand and stand behind it before shipping. Trigger on 'review this branch/PR', 'code review', 'help me own this code', 'I have to be responsible for this', 'sign off on this change', or 'make sure I understand this before I ship'. It runs AFTER detection (the Security Gate and the code-review pipeline find the bugs) and adds what they cannot - it reconstructs the developer's understanding through active recall by dispatching the comprehension agent to generate diff-grounded questions, conducts the quiz answer-first in the main thread, teaches on every miss with grounded explanations a junior could follow, and records an auditable ownership sign-off (gate.owned) that the Stop hook enforces. It never fixes code, never commits, and never rubber-stamps."
---

# Ownership Review

Most code review asks one question: *is the code correct and safe?* Ringmaster already answers that — the **Security Gate** hunts vulnerabilities and the **code-review** pipeline hunts defects. This skill exists for the *other* question, the one the AI era makes urgent and no market tool answers well:

> **Does the human who is about to take 100% responsibility for this change actually understand it?**

When AI writes the code, the old path to understanding — *writing it yourself* — is gone. A developer can ship a diff they've only skimmed and honestly believe they've "reviewed" it. That's the gap that ends in a 2am incident nobody on the team can debug. This skill closes it: it **reconstructs** the developer's understanding through active recall, **teaches** wherever it finds a hole, and produces an **auditable ownership sign-off** so "I take responsibility for this" is backed by evidence instead of a vibe.

Two stances at once, and both matter:

- **Be a rigorous examiner.** Understanding is not having read the diff. Ask what only a person who genuinely grasps the change can answer. The sign-off is worthless if it's easy.
- **Be a warm senior peer.** This is a debrief between colleagues, not an exam that judges. Never shame a miss — a hole caught here is the whole point. The developer should leave **more** confident and more responsible, never smaller.

This skill is **stack-independent** and it does **not** re-implement bug detection — it stands on top of the tools that do.

---

## The safety rails (inherited, non-negotiable)

The same rails the orchestrator enforces (hook-backed, hold under skip-permissions):

1. **You review; you never fix.** Read-only. If comprehension surfaces a real defect, it goes into the record and back to the human — you don't patch it.
2. **You never commit, push, or write history.** The only things this skill writes are the ledger's sign-off record and — on the human's say-so — an *evidence draft*. The human commits and ships.
3. **Never run anything against production.** Execution grounding (running the change's own tests to confirm a claim) is DEV/UAT only.
4. **Never rubber-stamp.** A sign-off that isn't honestly earned is worse than none — it launders responsibility. If the understanding isn't there, say so and stop.

---

## Where this sits in "code review with Ringmaster"

```
Security Gate  →  code-review  →  Ownership Review  →  sign-off
   (secrets,       (defects,        (reconstruct         (gate.owned
    injection,      logic, edge      understanding,       recorded;
    authz)          cases)           teach the holes,     evidence
                                     calibrate)           trail)
```

Detection runs **first** — you can't honestly own a change that's still broken. If the Security Gate or the bundled **`code-review`** skill haven't run on this diff yet, trigger them before comprehension. Fold their findings into the questions: a defect they flagged is exactly the kind of thing the developer should be made to understand before signing.

---

## The pipeline

### Stage 0 — Scope & risk-tier (cheap, first)

Get the change: `git diff` (working/staged) or the PR. Risk-tier it using the comprehension agent's tiers (`agents/comprehension.md`): **trivial · standard · critical**. A **trivial** change (rename, comment, formatting) gets **no quiz** — say so plainly and move to a light sign-off. Over-quizzing a typo is the fastest way to make this hated; the risk tier is what keeps it welcome.

### Stage 1 — Detection (reuse, never rebuild)

Confirm the diff has cleared the **Security Gate** (`agents/security-gate.md`) and the bundled **`code-review`** skill (`skills/code-review/`) — route to them, or to the external `code-review` plugin if it's installed (see `skills/orchestrator/references/routing-and-plugins.md` and `skills/orchestrator/references/output-style.md`). This skill adds a layer; it does not duplicate theirs. Carry their headline findings into Stage 2.

### Stage 2 — Comprehension (the heart) — two phases

Because a Claude Code subagent can't take live input, comprehension splits cleanly (full method in `agents/comprehension.md`):

- **Phase 1 — Generate.** Dispatch the **`comprehension`** subagent on the diff. In its fresh context it risk-tiers, finds the load-bearing spots, and returns a **grounded question bank** across the five levels (architectural · code · functional · business · test) — each question carrying an evidence anchor (`file:line`), a model answer, the load-bearing points, and the common wrong turns. It asks the human nothing.
- **Phase 2 — Conduct.** *You* (in the main thread, where the human can answer) run the quiz **one question at a time**: ask → capture confidence *before* revealing → take the answer in their own words → grade against the anchors → on anything below solid, reveal the grounded answer, point at the exact lines, and teach it plainly. Then the **confidence calibration** — compare what they *said* to how they *did*; the "sure-and-wrong" answers are the blind spots this whole pass exists to catch.

### Stage 3 — Ownership sign-off gate

Record the outcome as **`gate.owned`** on the change's ledger task, and honor the interaction contract below so it can never deadlock or be gamed. Then present the **Ownership Sign-off Record** (format in `references/signoff-and-evidence.md`).

### Stage 4 — Evidence trail

Turn the record into a durable, auditable artifact — the thing that lets the developer *prove* they owned this in a future incident review or audit. Default is **draft-and-paste** (you produce the block, the human pastes it into Jira/Confluence). If the Atlassian MCP is connected, offer to write it directly (MCP preflight — see `references/signoff-and-evidence.md`); never assume it's there.

---

## The interaction contract (this is what makes the gate real, not theater)

The ownership sign-off is enforced by the **Stop hook** via a conditional `gate.owned` criterion (`hooks/stop_gate.py`). To make that a genuine tooth that never traps a legitimate pause, manage two ledger fields together:

1. **Before conducting the quiz** on a standard+ change: set `waitingOnHuman: true` and record `gate.owned: false` on the task. (`waitingOnHuman` tells the Stop hook this pause is legitimate, so you can stop to actually ask the human.)
2. **On honest completion** — the developer engaged, misses were corrected and understood: set `gate.owned: true` and `waitingOnHuman: false`.
3. **If the developer disengages**, or a *critical* answer can't be grounded: leave `gate.owned: false`, keep `waitingOnHuman: true`, and stop to ask. The sign-off is **not** honest yet — do not proceed.
4. **Never set `owned: true` to escape the gate.** The one pattern the Stop hook is built to catch is a change marked done while its sign-off is on record as *not honest* (`owned: false` **and** `waitingOnHuman: false`). That composition means the tooth only ever bites the dishonest case — silently shipping an unowned change.

> **No ledger?** For an ad-hoc "review my branch" with no `.ringmaster/` ledger, run the quiz and produce the record all the same — it just isn't hook-enforced (there's no task to record `owned` on). Say so honestly in the report: the sign-off is real, the *automatic* enforcement isn't active without a ledger.

---

## Output — the Ownership Sign-off Record

Emit the record from `references/signoff-and-evidence.md`. It reuses the house style (`skills/orchestrator/references/output-style.md`): a compact table, per-question verdicts, the confidence-calibration flags, an honest overall posture, and a plain-language line that ends with the concrete thing the developer can now do — *walk into an incident review for this change and explain the load-bearing part in their own words.* That sentence is the deliverable: it's what "I own this" is worth.

## Status (end with exactly one)

- **DONE** — comprehension is solid (or misses were corrected and genuinely understood); the ownership sign-off is honest and recorded (`gate.owned: true`). Detection was clean or its findings understood.
- **DONE WITH CONCERNS** — signed off, but with recorded holes, corrected blind spots, or a detection finding the human accepted knowingly. The record names them; nothing is buried.
- **BLOCKED** — a Security Gate critical or a code-review blocker stands; you can't honestly own a broken change until it's resolved.
- **NEEDS INPUT** — the developer hasn't finished the sign-off (disengaged, or a critical answer couldn't be grounded). `gate.owned` stays false; say exactly what's outstanding.

---

## Reference files

- **`agents/comprehension.md`** — the comprehension examiner: the full question-generation rubric (risk-tiering, the five levels, the question taxonomy, the grounded question-bank format) and the grading rubric (answer-first, the four verdicts, confidence calibration, the anti-hallucination contract). **Read/execute in Stage 2.**
- **`references/signoff-and-evidence.md`** — the Ownership Sign-off Record format, the honesty doctrine for what a sign-off may and may not claim, and the draft-and-paste (or Atlassian-MCP) evidence trail. **Read in Stages 3–4.**
- **`skills/orchestrator/references/output-style.md`** — the house style shared across Ringmaster. **Read before printing.**
