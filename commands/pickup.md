---
description: Resume Conductor work from the .conductor/ ledger — reconcile against the repo, then continue the highest-priority pending task.
---

You are resuming a Conductor session. Follow the **pickup / resume flow** in
`${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/state-and-resume.md` exactly:

1. Read `.conductor/state.json` and `.conductor/PROGRESS.md`. If neither exists,
   say so plainly and offer to start fresh — do not invent a ledger.
2. Validate: `python "${CLAUDE_PLUGIN_ROOT}/hooks/ledger.py" validate .conductor/state.json`
   (use `python3` or `py` if `python` isn't on PATH). If it reports problems,
   surface them and ask before proceeding.
3. **Reconcile (trust but verify):** run read-only `git status` / `git diff --stat`,
   confirm the recorded `filesTouched` still exist, and detect drift (files moved,
   tasks completed elsewhere, new commits). If anything is ambiguous, flag it and
   ask before resuming; update the ledger to match reality.
4. Print a compact **resume briefing** (goal; done / in-progress / pending / blocked
   counts; key decisions; the next task) using the block in
   `${CLAUDE_PLUGIN_ROOT}/skills/orchestrator/references/output-style.md`.
5. Select the next task (`python "${CLAUDE_PLUGIN_ROOT}/hooks/ledger.py" next .conductor/state.json`,
   or the documented algorithm) and continue it through the normal orchestrator
   pipeline — behind the stage-1 approval gate if it is substantial.

Honor every safety rail. Stage, never commit.
