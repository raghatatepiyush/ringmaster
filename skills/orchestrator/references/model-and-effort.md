# Model & Effort — saving tokens without ever lowering the bar

Different work deserves different horsepower. Framing a gnarly architecture, reasoning about an auth flow, or untangling an ambiguous bug wants the most capable model at full effort. Renaming a variable, reformatting a file, or scaffolding boilerplate does not — running those on a premium model is just burning tokens. This reference is how Ringmaster spends the person's model budget like a careful engineer: **premium by default, downshift only the genuinely mechanical lanes, and guarantee that the downshift can never cost quality.** Read it in stage 1–2, when you're routing work.

The promise that makes this safe: **the quality gate is model-independent.** Cost varies with the model; the bar the work must clear does not.

---

## Recommend the premium tier at the start

At the top of a run, recommend the person start on the **most capable model and effort they have** — e.g. Opus at high effort — for framing, design, and any non-trivial reasoning. That's where model quality matters most and where a cheap mistake is most expensive downstream.

Be honest about the limit of your control: Ringmaster **cannot change the person's `/model` or `/effort` itself** — those are theirs. So this is a *recommendation* ("for this build I'd start on Opus + high effort"), plus the one lever you *do* control: the model a dispatched subagent runs on.

---

## The mechanism — be honest about what's actually possible

- **Subagent model routing (the real lever).** When you dispatch a worker, you choose its model. Route a **mechanically-trivial lane to a Haiku subagent** and a **hard-reasoning lane to Opus**. This is where the token savings actually come from, and it never touches the main session.
- **Main-session switches are recommendations only.** At a clean phase boundary you may say "the rest is mechanical — you could drop to Sonnet to save tokens," but the person drives the switch.
- **Graceful degradation — never block.** If subagents aren't available, or the platform won't let you set a worker's model, fall back to **recommend-only** and keep going on the current model. Routing is an optimization, never a dependency. Ringmaster must finish either way.

---

## The conservative routing table

Premium by default; only clearly-mechanical lanes downshift.

| Lane | Model | Effort | Gate | Typical work |
| :-- | :-- | :-- | :-- | :-- |
| **trivial** | Haiku (subagent) | low | light | rename, comment, format, one-line doc, scaffold |
| **standard** | Sonnet (→ Opus if reasoning-heavy) | medium / high | full | most features, fixes, tests |
| **deep** | Opus | high | widened | architecture, security, payments, auth, ambiguous, "go deep" |

Default main session: **Opus + high effort.** The lane comes from `references/right-sizing.md`; `hooks/routing.py` (`profile_for_lane`) is the canonical implementation of this table.

---

## The A-grade gate (the keystone)

Downshifting is only safe because the work it produces must clear the **same gate** as premium work. "A-grade" is an objective rubric — six criteria, each backed by a concrete check that already exists in the pipeline:

| Criterion | How it's checked |
| :-- | :-- |
| **Correct** | Tests prove the new/changed behavior; edge cases covered (Test Architect) |
| **Secure** | Security Gate verdict is CLEAR (no critical/high findings) |
| **Clean** | Review is clean: readability, naming, no duplication, matches conventions |
| **Complete** | Meets the stated acceptance criteria; no scope gaps |
| **Documented** | Docs / CLAUDE.md updated if behavior, structure, or conventions changed |
| **Explained** | A plain-language "🗣️ in plain terms" summary is present |

**The invariant:** the gate strength is a pure function of the **lane**, never of the **model** (`hooks/routing.py` `gate_for_lane`). A `standard` task carries the `full` gate whether it ran on Haiku, Sonnet, or Opus. So a cheaper model cannot buy a weaker gate — the only thing a downshift changes is the cost of the *first attempt*.

---

## Auto-escalation — the teeth

If a step produced on a downshifted model/effort **fails any A-grade criterion** (`hooks/routing.py` `should_escalate` returns true when any criterion isn't passed — missing counts as failed, so it fails closed), **re-run that step on Opus at high effort.** Record both `modelUsed` and `escalated: true` in the ledger so the decision is auditable.

This is what lets Ringmaster be aggressive about saving tokens on the easy 80% without ever gambling on quality: the cheap attempt either clears the same bar premium work would, or it gets redone properly — automatically.

---

## What "A-grade" means, plainly

> Ringmaster varies *how expensive it is to produce* a piece of work — a cheap model for mechanical lanes, the premium model for hard ones. It never varies *the standard the work must meet*. Every change that ships has passed the same six checks, regardless of which model wrote it. That's the whole deal: tokens saved on the easy parts, quality held constant everywhere.

If you ever feel tempted to let a downshifted result slide because "it's probably fine," that's exactly the case the gate exists for — run the checks, and escalate if they don't pass.
