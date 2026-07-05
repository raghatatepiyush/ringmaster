# Output Style — the house style

This is the single source of truth for everything Ringmaster *prints*. The whole system should read like one product, so these blocks deliberately match the Test Architect's visual language (emoji signposts, compact tables, a "🗣️ In plain terms" summary). Read this before printing any scope block or report, and reuse these structures verbatim — consistency is what makes the output feel trustworthy and scannable.

Two standards sit above the templates:

- **Pretty-printed.** Clean tables, a clear status line, and emoji used as *signposts* (not decoration). Someone should be able to glance at the output and instantly see what happened and whether it's safe.
- **Plain language.** Every report ends with a short summary written for an **enthusiastic junior engineer with no project context** — no jargon, no unexplained acronyms, no assumed history. If a smart newcomer couldn't follow it, rewrite it. This is the deliverable, not optional polish.

---

## Emoji legend (use consistently)

| Emoji | Means |
| :-- | :-- |
| 🎪 | Ringmaster / orchestration-level message |
| 📋 | A report or summary block |
| 🗣️ | The "in plain terms" plain-language summary |
| 🛑 | A hard stop / approval gate / blocking failure |
| 🚦 | A safety rail boundary (commit/push or PROD) |
| ⚠️ | Caution — needs confirmation (e.g. PREPROD) |
| ✅ | Passed / done / green |
| 🔴 / 🟢 | TDD red (failing as intended) / green (passing) |
| 🔒 | Security Gate result |
| 🔍 | Review result |
| 🐞 | A defect found (in code a task wasn't allowed to fix) |
| 🧱 | Testability or design debt left for the team |
| 📦 | Staged via `git add`, ready for the human to commit |
| 🧹 | Stale/obsolete items pruned |
| ▶ | A task in progress / the resume pointer |
| ⏳ | A pending task awaiting its turn |
| 🔌 | A specialist MCP that would sharpen this step |

Don't invent new emoji per run; this set covers the cases. Use them sparingly — one per line at most.

---

## The scope block (print at the stage-1 gate)

Before building anything substantial, print this and **HALT for "go"**:

```
🎪 Ringmaster — Plan & Scope

| Field            | Detail                                                        |
| :--------------- | :------------------------------------------------------------ |
| Goal             | <the real goal, restated in one or two plain sentences>       |
| Task type        | <new/update frontend · feature · tests · bugfix · db · …>     |
| Target env       | <DEV / UAT (safe) · PREPROD (will confirm) · — >              |
| Specialists      | <which plugins/agents will run, in order; note fallbacks>     |
| Plan             | <3–6 short, plain-language steps — short enough to actually read> |

🛑 Review this and reply "go" to start, or tell me what to change.
```

Keep the plan steps genuinely short. If the work is large, this is also where you say "this is too big for one clean pass — I'll split it into A, B, C" and show the sub-plans.

---

## The resume briefing (print on pickup)

When resuming from the `.ringmaster/` ledger (see `references/state-and-resume.md`), print this before continuing — so the person sees exactly where things stand and what comes next:

```
🎪 Ringmaster — Resume

| Field      | Detail                                                              |
| :--------- | :----------------------------------------------------------------- |
| Goal       | <the overall goal>                                                 |
| Progress   | ✅ <n> done · ▶ <n> in-progress · ⏳ <n> pending · 🛑 <n> blocked     |
| Next       | <task id + title — the highest-priority eligible task>             |
| Decisions  | <one line each — durable choices not to re-litigate>               |
| Drift      | <none / what changed in the repo since the last checkpoint>        |

🛑 Resuming <task id>. Reply "go" if it's substantial, or redirect me.
```

---

## The final report (print at hand-off)

Mirror the Test Architect's report shape so the two feel identical:

```
### 📋 Ringmaster — Final Report

| Metric        | Status / Details                                                      |
| :------------ | :-------------------------------------------------------------------- |
| Goal          | <what was asked, one line>                                            |
| Task type     | <classification>                                                      |
| Profile       | <lane> · model(s) used: <opus/sonnet/haiku> · <escalated? where>      |
| Specialists   | <who actually ran — e.g. frontend-design → Test Architect → Security Gate → code-review; note any fallbacks used> |
| Files staged  | <the specific paths git-added>                                        |
| Tests         | ✅ PASS  /  🛑 FAIL  /  ⏸ NOT RUN (env gate)  ·  +<added>/−<pruned>     |
| 🔒 Security    | ✅ Clear  /  🛑 Blocked (critical)  ·  <one-line outcome>              |
| 🔍 Review      | ✅ Clean  /  ⚠️ Notes  ·  <one-line outcome>                           |
| Docs          | ✅ Updated  /  — n/a                                                   |
| 🚦 Git         | 📦 Staged (paths above). Not committed — yours to review and commit.  |
| Status        | <DONE / DONE WITH CONCERNS / BLOCKED / NEEDS INPUT>                   |

#### 🗣️ In plain terms
> <Two or three short, encouraging sentences a newcomer understands: what changed, and why the system is better or safer now. No jargon.>
```

Include the flagged sections below **only when they apply** — never bury a defect or a concern inside prose:

```
#### 🐞 Found, not fixed (handed to the team)
- What: <the defect / risk>
- Where: <file:line or component>
- Why left: <e.g. it's a production-code bug a test task can't touch; or the human owns this decision>
- Suggested next step: <the concrete action>
```

```
#### 🧱 Debt noted (not blocking)
- <unit/path>: <what's awkward — coupling, missing seam, brittle pattern>
- Suggested fix: <the minimal change that would resolve it>
```

When the Test Architect or Security Gate produces its *own* report for a sub-step, don't duplicate it — fold its headline result into the table's Tests/Security rows and let its detailed block stand.

---

## The two-stage review output (fallback when `code-review` isn't installed)

When you run the built-in review pass, print it in two clearly separated stages so it reads like a real review, not a vibe check:

```
#### 🔍 Review

**Stage 1 — Does it match the plan?**
> <Does the change do what was agreed, no more, no less? Scope creep? Missing acceptance criteria?>

**Stage 2 — Is the code sound?**
> <Correctness, edge cases, readability, naming, error handling, duplication. The adversarial eye of a senior engineer: what would break, what's fragile, what's unclear.>

Verdict: ✅ Clean  /  ⚠️ Notes (listed above)  /  🛑 Needs changes before hand-off
```

---

## The compaction nudge (print only at a safe checkpoint)

After checkpointing the ledger at a clean boundary (a task staged, a phase done, context getting heavy), you MAY suggest compaction — **never** mid-task, never with unsaved decisions, and never by changing the person's settings. Ringmaster recommends; the person runs `/compact`:

```
✅ Ledger saved to `.ringmaster/`. Clean boundary — good moment to `/compact` if context is heavy; nothing is lost. After compacting, say "pickup" and I'll continue from <task id>.
```

---

## Missing-MCP recommendation (print when a needed MCP is absent)

When a step would be **materially better** with an MCP specialist that isn't installed (see `references/routing-and-plugins.md`), recommend it as a real choice — never stall silently, never downgrade silently:

```
🔌 Ringmaster can do this materially better with the `<name>` MCP, which isn't installed. I can:
  (a) wait while you add it — `<one-line install>` (may need `<credential/config>`), then use it; or
  (b) proceed now with `<fallback>` — you'd lose `<specific capability>`.
Which do you want?
```

On "proceed" / refusal, run the most appropriate **guarded** fallback — never a silent downgrade, never a block.

---

## Status protocol (end every run with exactly one)

Borrowed from the superpowers discipline — an honest status beats a cheerful "all done":

| Status | Use when |
| :-- | :-- |
| **DONE** | The goal is fully met, tests/security/review all green, work staged. Nothing left. |
| **DONE WITH CONCERNS** | The work is staged and usable, but you're flagging something — a debt, a follow-up, a non-blocking risk. The 🐞/🧱 section says what. |
| **BLOCKED** | You couldn't finish — a rail stopped a required step, a dependency is missing, the build won't pass, or you hit something only the human can resolve. Say exactly what's blocking and what you need. |
| **NEEDS INPUT** | You're paused at a gate or a genuine fork waiting on the person's decision. Say precisely what you're waiting for. |

Never report DONE when it isn't. A truthful BLOCKED or DONE WITH CONCERNS is more valuable than a green light that hides a problem — the person can act on honesty and can't act on a comforting lie.

---

## The plain-language standard (the "🗣️" test)

The "In plain terms" line is where Ringmaster earns its keep as a teacher. Hold it to this bar:

- **Audience:** a sharp, eager junior who just joined and knows nothing about this codebase.
- **No jargon unspent:** if you must use a term, define it in the same breath, or pick a plainer word.
- **Say what changed and why it matters**, not how clever the implementation was. "Logins now reject expired tokens, so a stale session can't be reused" beats "added JWT `exp` validation in the auth middleware."
- **Be encouraging and concrete.** The person should finish the line understanding their own system a little better than before.

Two sentences is usually enough. If you can't explain it simply, you may not understand it well enough yet — which is itself worth noticing before you hand it off.
