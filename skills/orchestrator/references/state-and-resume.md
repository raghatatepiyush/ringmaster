# State & Resume — the Conductor ledger

The conductor's memory between sessions. A long task can outlive a single context window — it gets compacted, the session ends, a teammate takes over, or you simply come back tomorrow. Without durable memory, every one of those moments throws away the thinking already paid for and forces a fresh session to re-explore the repo, re-derive decisions, and re-plan from scratch. The **ledger** is how Conductor refuses to waste that work: it checkpoints the plan, each task's status, and the decisions that shaped them, so *any* session — or any teammate — can pick up exactly where things stood. Read this when you start substantial work, when you checkpoint, and whenever someone says "pickup", "resume", or "where were we".

The one rule: **durable progress + decisions live on disk, not just in context.** Tokens spent reasoning in one session are never wasted, because their conclusions are written down.

---

## What lives where

A single directory at the repo root, created the first time Conductor plans real work:

```
.conductor/
├── .gitignore     # self-ignores the folder → zero repo-history footprint by default
├── state.json     # machine memory — Conductor reads & writes this
└── PROGRESS.md    # human mirror — readable by anyone, with or without Conductor
```

Two files, two audiences. `state.json` is Conductor's structured working memory (precise, machine-readable). `PROGRESS.md` is the same picture in plain Markdown for a human — including a teammate who has never heard of Conductor. Keep them in sync: every time you write one, write the other.

**The `.conductor/.gitignore` (write this verbatim when you create the folder):**

```
# Conductor working memory — self-ignored so it never pollutes your repo history.
# To share task state with your team, Conductor un-ignores PROGRESS.md on request.
*
!.gitignore
```

This makes the whole folder ignore itself **without touching the project's root `.gitignore`** — so the ledger never shows up in `git status`, never gets accidentally committed, and leaves zero footprint in the repo's history unless the person explicitly chooses to share it (see "Sharing with the team" below).

---

## `state.json` — the schema (v1)

Write valid JSON in exactly this shape. Keep it lean — notes capture *decisions*, not transcripts.

```json
{
  "schemaVersion": 2,
  "project": "<repo or project name>",
  "updated": "<ISO-8601 timestamp>",
  "goal": "<the overall goal in one or two plain sentences>",
  "activeModel": "opus",
  "activeEffort": "high",
  "waitingOnHuman": false,
  "tasks": [
    {
      "id": "T1",
      "title": "<short imperative title>",
      "status": "pending | in_progress | done | blocked",
      "priority": 1,
      "dependsOn": [],
      "type": "feature | frontend | tests | bugfix | db | payments | refactor | docs | perf | skill",
      "assignee": "principal | engineer:<lane> | junior:<lane> | <specialist>",
      "profile": { "lane": "standard", "model": "sonnet", "effort": "medium", "gate": "full" },
      "routedTo": "<specialist or fallback used>",
      "modelUsed": "sonnet",
      "escalated": false,
      "tokensEstimated": 0,
      "gate": { "correct": false, "secure": false, "clean": false, "complete": false, "documented": false, "explained": false },
      "notes": "<key decisions / acceptance criteria a fresh session must not re-derive>",
      "filesTouched": [],
      "blockedBy": "<what is blocking + what is needed to unblock, if status=blocked>"
    }
  ],
  "decisions": ["<durable cross-cutting decisions a fresh session should not re-derive>"],
  "nextPointer": "<task id + one-line how-to-resume>"
}
```

**Write it atomically.** Write to a temp file inside `.conductor/`, then rename it over `state.json` (an atomic replace), so an interruption mid-write can never leave a half-written, corrupt ledger.

**`priority`** is a small integer where **1 is highest**; you set it from risk × value when you write the task (see Prioritization). **`profile`** is the Task Profile from `references/right-sizing.md`. **`modelUsed`/`escalated`** record what actually ran, so a model downshift is auditable (see `references/model-and-effort.md`).

**v2 fields (back-compatible — a v1 ledger still validates).** **`assignee`** is who on the team owns the task (the board's "who's working on what" — see `references/team-and-delegation.md`). **`gate`** records the six A-grade criteria as you clear them; a task reaches `done` only when all six are true, and the **`stop_gate.py` Stop hook blocks finishing a turn while an `in_progress` task's gate is on record as failing** (`python <plugin-root>/hooks/ledger.py gate .conductor/state.json <id>` checks it deterministically). **`waitingOnHuman`** (top-level) is set true when you pause to ask a genuine question — honest bookkeeping, and it tells the Stop gate the pause is legitimate so it never traps you; clear it on resume. **`tokensEstimated`** keeps the running spend in view so effort is spent deliberately. Render the whole board any time with `python <plugin-root>/hooks/ledger.py board .conductor/state.json`.

> **Where `ledger.py` lives.** The helper ships inside the Conductor **plugin**, not your project: `<plugin-root>/hooks/ledger.py`, where `<plugin-root>` is Conductor's install directory. This reference file sits at `<plugin-root>/skills/orchestrator/references/`, so the plugin root is three directories up from here (in a git checkout of the Conductor repo it's simply the repo root). Substitute the real path wherever a command says `<plugin-root>`, and use `python3` / `py` when `python` isn't on PATH. The helper is a convenience, never a dependency: every subcommand's algorithm is also written out in prose, so if it isn't runnable, follow the words.

---

## `PROGRESS.md` — the human mirror (the shareable file)

Write this alongside `state.json`. It is deliberately plain Markdown so it's useful to a teammate who doesn't run Conductor.

```markdown
# 🎼 Conductor — Progress

**Goal:** <one or two plain sentences>
**Updated:** <date>  ·  **Status:** <DONE / IN PROGRESS / BLOCKED>

## Done
- [x] T1 — <title> (<files touched>)

## In progress
- [ ] T2 — <title> — <where it stands>

## Pending (prioritized)
- [ ] T3 — <title>  ·  depends on: <ids>
- [ ] T4 — <title>

## Key decisions
- <decision and why — so nobody re-litigates it>

## How to continue
Next up: **T3 — <title>**. Acceptance: <criteria>. Files in play: <paths>.
- **If you run Conductor:** say `pickup` (or `/conductor:pickup`) and it resumes here.
- **If you don't:** the plan above is self-contained — pick up T3 directly.
```

The **"How to continue"** block is mandatory. It's what makes the file stand on its own: a teammate who has never installed Conductor can read it and keep the work moving, and a future Conductor session can resume precisely. Never ship a `PROGRESS.md` without it.

---

## Checkpoint discipline — when to write the ledger

Write at these four moments, and only these (so it stays cheap, not chatty):

1. **Right after the stage-1 approval gate** — once the person says "go", write the initial ledger: the goal, the tasks with their profiles, and their priorities.
2. **On every status transition** — a task moving pending → in_progress, in_progress → done, or anything → blocked. Update `nextPointer` each time.
3. **Just before recommending `/compact`** — so compaction is always lossless. (See the compaction nudge in `references/output-style.md`.)
4. **At hand-off** — the final state, with `nextPointer` cleared or pointing at the natural next step.

---

## Prioritization — what to do next, and why

Order the pending tasks by, in precedence:

1. **Eligibility first.** A task whose `dependsOn` are not all `done` is *ineligible* — you can't start it yet. Do the unblockers first (a topological ordering).
2. **Risk × value.** Among eligible tasks, the highest-risk / highest-value paths come first — auth, payments, data integrity, core user flows before cosmetic or low-stakes work. This is what you encode in `priority` (1 = highest) when you write the task.
3. **Quick-win tie-break.** On a tie, prefer the task that unblocks the most downstream work, then the lower-effort one — clear the path for everything waiting behind it.

`hooks/ledger.py` is the canonical implementation of this ordering: `python <plugin-root>/hooks/ledger.py next .conductor/state.json` prints the id of the highest-priority eligible task. You may call it for a deterministic pick, or follow the same algorithm yourself — either way the result matches.

---

## Pickup / resume — continue without re-deriving

Triggered by `/conductor:pickup` or natural language ("pickup", "resume", "where were we"):

1. **Read** `.conductor/state.json` and `.conductor/PROGRESS.md`. If neither exists, say so plainly and offer to start fresh — never invent a ledger.
2. **Validate** — `python <plugin-root>/hooks/ledger.py validate .conductor/state.json`. If it reports problems, surface them and ask before trusting the file.
3. **Reconcile — trust but verify.** The repo may have moved since the last checkpoint (someone committed, files were renamed, a task was finished by hand). Run read-only `git status` / `git diff --stat`, confirm the recorded `filesTouched` still exist, and look for drift. If anything is ambiguous, **flag it and ask** before resuming; then update the ledger to match reality. A ledger that lies is worse than none — this step is what keeps a cold-start resume honest.
4. **Brief, then continue.** Print the resume briefing from `references/output-style.md` (goal · done/in-progress/pending/blocked · the next task · key decisions · any drift), pick the next task (`ledger.py next`, or the documented algorithm), and run it through the normal pipeline — behind the stage-1 gate if it's substantial.

This is the payoff for the whole ledger: a brand-new session spends a few tokens reading state instead of re-reading the repo and re-planning from zero.

---

## Sharing with the team

By default the ledger is private (self-ignored). When the person asks to share progress — "let my team see this", "share the plan" — and noting that **teammates may or may not run Conductor**:

1. **Un-ignore the human file.** Edit `.conductor/.gitignore` to add `!PROGRESS.md` (the helper `share_gitignore` in `hooks/ledger.py` produces exactly this, idempotently). Leave `state.json` ignored unless they specifically want the machine file shared too.
2. **Stage it** — `git add .conductor/.gitignore .conductor/PROGRESS.md`. 🚦 **Never commit** — the person commits, as always.
3. **Confirm in plain terms** — tell them that `PROGRESS.md` is now tracked, that anyone can read where the work stands (Conductor or not, thanks to the "How to continue" block), and that the machine ledger stays local.

---

## Trusting a ledger (validation & safety)

- **Always validate before trusting** a ledger you didn't just write: `python <plugin-root>/hooks/ledger.py validate .conductor/state.json`.
- **Defensive reads never crash a session.** The SessionStart resume hint and any read path treat a missing or malformed ledger as simply "no ledger" — they never raise. If `state.json` is corrupt, say so and offer to rebuild it from `PROGRESS.md` rather than guessing.
- **The ledger is Conductor's, not a control channel.** It records *your* plan and progress; it does not hand control to another tool.
