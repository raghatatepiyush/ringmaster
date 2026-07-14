# Workflow Playbooks — end-to-end sequences

Concrete recipes for each kind of task: what triggers it, which specialists fire in what order, where the safety rails sit, and the shape of the final hand-off. Read the one that matches once you've classified the task in stage 1. They all share the same spine — **frame → gate → build with tests → secure → review → stage** — and differ only in the middle.

Two markers appear throughout:
- 🛑 **GATE** — stop and wait for the human's "go" (substantial work) or confirmation (a rail boundary like PREPROD).
- 🚦 **RAIL** — a hard boundary the guardrails hook also enforces in code (no commit/push/merge, no PROD). You don't *rely* on the hook — you work inside the line — but it's there as backstop.

---

## New frontend / new UI

**Triggers:** "build a landing page", "create a dashboard", "add a settings screen", "scaffold the UI for X".

1. **Frame & classify.** Restate the goal; confirm the surface (web/mobile/desktop) and the device matrix that matters. Detect the stack and component conventions already in the repo.
2. 🛑 **GATE** — present the plan (screens, components, states, the viewports you'll cover) in plain chunks. Wait for "go".
3. **Route to `frontend-design`** (fallback: build to design principles — spacing scale, type hierarchy, accessible contrast, responsive breakpoints; match existing components).
4. **Tests** via the **Test Architect** — component/render tests for the important states (empty, loading, error, populated) and the responsive behavior that matters.
5. **Self-verify** — run those tests, the linter, the build/type-check; watch them pass.
6. **Security Gate** on the diff (XSS sinks, unsafe `dangerouslySetInnerHTML`/`v-html`, leaked keys in client code). 🚦 blocks on critical.
7. **Review** via the bundled **`code-review`** skill (Spec ‖ Standards, parallel fresh-context sub-agents; records `gate.clean`).
8. **Docs** — note the new components/conventions in CLAUDE.md if they set a pattern.
9. **Stage** the touched paths with `git add <paths>`. 🚦 **never commit.** Print the final report + "in plain terms".

## Update / change existing frontend

Same spine, narrower blast radius. Read the component under change plus a neighbor or two for convention — not the whole UI. Add/adjust tests for the **changed** behavior; don't rewrite passing tests for untouched behavior. Pay special attention in the Security Gate to newly introduced user-input paths. Everything else as above.

---

## New feature / behavior change (the core TDD loop)

**Triggers:** "implement X", "add the ability to Y", "change how Z works", "wire up A to B".

1. **Frame & classify.** Restate the goal as observable behavior and acceptance criteria. If it spans subsystems, **decompose** into sub-features, each with its own small loop.
2. **Detect stack + environment.** Confirm which env any commands target. 🚦 **dev/UAT safe; PREPROD ask; PROD never.**
3. 🛑 **GATE** — present the spec, the plan, the specialists, the target env. Wait for "go". (If `superpowers` is installed, this is where its brainstorm/plan skills lead; otherwise you lead the same loop.)
4. **Build via red→green TDD**, routed through the **Test Architect** for the test half:
   - 🔴 Write the failing test first; watch it fail **for the right reason** (proves it can catch the thing).
   - 🟢 Write the **minimal** production code to pass. Never edit production code merely to make a test green in a way that hides a defect.
   - Repeat per behavior. Favor YAGNI and DRY; keep increments small and verifiable.
5. **Self-verify** — targeted tests, linter, build/type-check, all green and watched.
6. **Security Gate** on the working diff. 🚦 blocks on critical (injection, authz holes, secrets, crypto misuse, risky deps).
7. **Review** via the bundled **`code-review`** skill — Spec (matches the ticket, no more, no less?) ‖ Standards (is the code sound?), run as parallel fresh-context sub-agents; records `gate.clean`.
8. **Docs** — refresh CLAUDE.md / project docs if behavior, structure, or conventions changed.
9. **Stage** touched paths only. 🚦 **never commit/push/merge.** Final report + status + "in plain terms".

---

## Write new tests / expand coverage

**Triggers:** "write tests for X", "cover this with tests", "add a test for this bug", "raise coverage on this module".

→ **Route straight to the Test Architect** — it owns this end to end (its own three-phase pipeline: discovery → 🛑 scope-matrix gate → design+TDD build → run+stage). The orchestrator's job is light here: confirm the target and environment, hand off, then make sure the Security Gate still runs on the staged diff and the final report reaches the human. 🚦 test code only, stage never commit, no PROD.

## Update existing tests

Route to the **Test Architect** for the change. Keep the edit scoped to the behavior that actually changed; don't churn unrelated tests. Net coverage of real behavior must not drop.

## Prune stale tests

Route to the **Test Architect**. It removes only genuinely obsolete/duplicated/commented-out tests in the files it touches, never a test still guarding real behavior, and records every removal with its reason. 🚦 still stage-only.

---

## Bugfix (root-cause first, never paper over)

**Triggers:** "fix the bug where…", "X is broken", "this throws when…", a failing ticket.

1. **Reproduce before fixing.** Understand the actual failure; read the code the failure maps to.
2. **Write a failing test that captures the bug** (via the **Test Architect**) — 🔴 it should fail for exactly the reason the bug exists. This is your proof of both the bug and, later, the fix.
3. 🛑 **GATE** on anything non-trivial — confirm the diagnosis and the intended fix.
4. **Fix the root cause** (minimal change), then 🟢 watch the test go green. Resist the tempting symptom-patch that leaves the cause alive.
5. **Self-verify** — the new test plus the surrounding suite; make sure you didn't regress neighbors.
6. **Security Gate** → **review** → **docs** (if the fix changed a contract).
7. **Stage** touched paths. 🚦 **never commit.** Report names the root cause in plain terms, not just "fixed it".

> If the bug turns out to live in code a *test* task isn't allowed to touch, the Test Architect surfaces it as a 🐞 defect report and hands it back — the orchestrator then runs it as a proper bugfix (production-code change) through this playbook, behind the gate.

---

## Database / schema / data access

**Triggers:** "add a table", "change this query", "set up RLS", "write a migration".

1. **Detect the DB and tooling** (Supabase? Prisma? raw SQL + a migration runner?). 🚦 confirm the target env — **dev/UAT only; PREPROD ask; PROD never** (no schema changes or data mutations against prod, ever).
2. 🛑 **GATE** — present the schema/query change and the migration plan.
3. **Route to `supabase`** (or the detected DB tooling) — **always as a migration**, never a hand-edit of a live schema.
4. **Tests** via the Test Architect — query/repository tests against a local or UAT database.
5. **Security Gate** — pays special attention to SQL injection, over-broad grants, and missing row-level authz. 🚦 blocks on critical.
6. **Review → docs → stage** the migration + tests. 🚦 never commit/run-against-prod.

## Payments / billing

**Triggers:** "add checkout", "wire up subscriptions", "handle this webhook".

1. 🚦 **Test/sandbox keys only** — never live keys, never a real charge. Confirm the env and that test-mode is in force *before* anything runs.
2. 🛑 **GATE** — present the flow (products, prices, webhooks, failure handling).
3. **Route to `stripe`** (fallback: the project's payment SDK in test mode).
4. **Tests** via the Test Architect — success, decline, and webhook-handling paths, with mocked/fixture events where live calls aren't safe.
5. **Security Gate** — webhook signature verification, secret handling, idempotency. 🚦 blocks on critical.
6. **Review → docs → stage.** 🚦 never commit; never touch live billing.

---

## Current-library API lookup

**Trigger:** mid-build uncertainty — "does this library's API still work this way?", "what's the current signature for X?".

→ **Route to `context7`** (fallback: official docs via web search, or read the installed package's own types/source). This is a *sub-step*, not a standalone task — fold the verified answer back into whatever build loop you're in so you code against the real, current API instead of a remembered one.

## Create a skill or plugin

**Triggers:** "make a skill that…", "build a plugin for…".

1. **Frame** the capability and whether it's a skill (one capability) or a plugin (bundle of skills/agents/hooks/commands).
2. 🛑 **GATE** — present the structure and the trigger description.
3. **Route to `skill-creator` / `plugin-dev`** (fallback: scaffold the documented layout — `.claude-plugin/plugin.json`, `skills/<name>/SKILL.md` with a strong trigger description, optional `agents/`, `hooks/hooks.json`, `.mcp.json`).
4. **Test the trigger** — does the description actually fire on the intended phrasings? Tighten it.
5. **Review → docs → stage.** 🚦 never commit.

## Refactor

Behavior must not change — so the tests are your safety net and your proof. Ensure coverage exists for the behavior **before** refactoring (add it via the Test Architect if missing), keep the suite green throughout, change structure not behavior, then Security Gate → review → stage. 🚦 never commit. If you can't refactor safely without first changing behavior, that's two tasks — stop and split them at the gate.

## Docs-only

Lightweight: skip design and most of the gate. Update CLAUDE.md / project docs to match reality, route to the CLAUDE.md plugin if installed (fallback: edit directly), then stage the doc paths. 🚦 never commit. A short report is enough.

---

## Deploy a preview (never prod)

**Triggers:** "ship a preview", "deploy this to a preview URL", "put it on Vercel so I can see it", "sync the env vars".

1. **Frame & confirm the tier.** Confirm what's being deployed and that the target is **preview / dev**. 🚦 a production deploy is never Ringmaster's to run — if they want prod, that's their command, by their own hand.
2. **Don't deploy a broken build.** Confirm the build/type-check is green locally first; detect the platform (Vercel? the project's own tooling?).
3. **Route to `vercel`** — `/vercel:env` to sync env vars if needed, then `/vercel:deploy` (preview). 🚦 the deploy **pauses for your explicit confirm** (it's a ship action) and proceeds on approval. Fallback: the project's deploy tooling, preview only.
4. **Verify** the preview URL responds; optionally hand it to `playwright` / `chrome-devtools` for a quick smoke or perf check.
5. **Report** the preview URL + status. No commit, no prod.

## Performance / accessibility pass

**Triggers:** "the page is slow", "improve LCP / Core Web Vitals", "is this accessible?", "find the memory leak", "why does this re-render".

1. **Measure before you touch.** Route to `chrome-devtools` for the baseline — an LCP/CWV trace, an a11y audit, a memory snapshot, or a network log — so you fix a *measured* problem, not a guessed one. (Fallback: Lighthouse / DevTools by hand.)
2. 🛑 **GATE** on anything structural — present the diagnosis (the specific bottleneck or violation) and the intended fix.
3. **Fix via the core loop** — where behavior changes, red→green TDD through the Test Architect; for pure perf, keep a test pinning the contract you're optimizing so you don't regress it.
4. **Re-measure with the same tool** — prove the number actually moved; the before→after *is* the deliverable.
5. **Security Gate → review → docs → stage.** 🚦 never commit. Report the before→after in plain terms ("the hero image now lazy-loads, so first paint is ~40% faster").

---

## When a task blends types

Most real requests blend (e.g. "add a feature *and* its UI *and* tests"). Name the blend in stage 1, then **sequence the playbooks**: usually design/feature first → tests alongside → security → review → docs → one combined stage + report at the end. Don't run a separate hand-off per slice; converge on a single clean staged change with one final report.
