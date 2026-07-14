# Routing & Plugins — the specialist map (verified)

This is the ringmaster's address book: for each kind of work, who the best specialist is, how to call them, how to install them if missing, and the built-in fallback that keeps the job moving when they're absent. Read it in **stage 2**, when you're choosing who takes each act.

The guiding rule: **route when you can, fall back when you must, and the work never blocks.** Ringmaster is a thin layer — it doesn't re-implement these specialists. When one is installed, hand the step to it; when it isn't, do a competent built-in version and *offer* the one-line install so the person can upgrade that capability for next time.

The names, commands, and install lines below were verified against Anthropic's live plugin directory (`claude.com/plugins`) and the `claude-plugins-official` / `anthropics/claude-code` marketplaces. Where a capability is delivered as an MCP server rather than a plugin, that's called out — they install differently.

---

## How to tell what's installed

You don't guess — you look. When a plugin is installed, its **skills, slash-commands, and subagents become available in the session**; an MCP server exposes **`mcp__…` tools**. So before routing a step:

1. **Check availability, not location.** Is the specialist's skill / command / agent / MCP tool present *in this session*? If yes → route to it. A plugin can be enabled at **user scope** (every project) or **project scope** (just this repo) — you don't care which; if it's live in the session, use it. If it's absent, use the fallback.
2. **Never hard-depend.** Treat every external specialist as optional. The bundled pieces (Test Architect, Security Gate) and your own fallbacks are always enough to finish.
3. **A missing *MCP* is a recommend-and-ask, not a silent fallback.** Plugins install in one line, but an MCP server often needs credentials or config only the human has (a Supabase project, a Stripe key, a browser, a GitHub token). So when a step would be **materially better** with an MCP specialist that isn't connected, **say so and offer it as a real choice** before proceeding — don't quietly drop to a weaker path on work they'd rather have done properly. Lead with what they gain, keep both doors open, and use the verbatim "Missing-MCP recommendation" block in `output-style.md`:
   > 🔌 **Ringmaster can do this materially better with the `<name>` MCP, which isn't installed.** I can:
   > **(a)** wait while you add it — `<one-line install>` (may need `<credential/config>`), then I'll use it; or
   > **(b)** proceed now with `<fallback>` — you'd lose `<specific capability>`.
   > Which do you want?

   Then proceed on their answer. The bar for "materially better" is judgment: a payments task genuinely needs `stripe`; a perf/a11y audit genuinely needs `chrome-devtools`; a Supabase schema change genuinely needs `supabase`. A passing mention that *could* use an MCP but is fine without it doesn't trip this — don't manufacture blockers. **Never stall silently and never downgrade silently:** either you have the MCP, you've asked and have an answer, or — on their go-ahead — you run the most appropriate **guarded** fallback (never a silent downgrade).
4. **Offer the upgrade once.** When you fall back on a *plugin* (cheap to install), add one line: *"This ran on the built-in fallback — installing `<plugin>` (`<one-liner>`) gives a stronger version next time."* Don't nag; mention it once and move on.

### MCP preflight (do this before you start building, not mid-step)

Once the task is classified (stage 1), look ahead at the playbook and name the MCP specialists it will *actually* lean on — then check they're live **before** you start, not when you trip over the gap halfway through. If a needed one is missing, raise the recommend-and-ask from point 3 *at the gate*, bundled into your plan ("this plan needs `supabase` + `stripe`; `stripe` isn't configured — set it up, or fall back?"). Catching it up front is the difference between one clean question and a stalled half-build. Bundled specialists (Test Architect, Security Gate) are always live, so they never need a preflight.

### Installing a specialist

Two delivery mechanisms, two install paths:

**Plugins** — most specialists. The **`claude-plugins-official`** marketplace is *built into* Claude Code, so its plugins install in one line, no marketplace-add needed:

```
/plugin install <plugin-name>@claude-plugins-official
```

Run **`/plugin`** to browse the directory in a menu. (`superpowers` is also published at its own marketplace — `/plugin marketplace add obra/superpowers` then `/plugin install superpowers@superpowers-marketplace` — and mirrored as `superpowers@claude-plugins-official`.) If a name has drifted, the `/plugin` browser is the source of truth.

**MCP servers** — `context7`, `playwright`, `supabase`, `stripe`. These are also listed as plugins in the directory (which wrap the MCP), or you can add the server directly:

```
claude mcp add context7 -- npx -y @upstash/context7-mcp@latest
claude mcp add playwright --scope local -- npx -y @playwright/mcp --headless
claude mcp add --transport http supabase https://mcp.supabase.com/mcp
```

A caveat worth knowing: stdio MCP servers launched via `npx @pkg@latest` can be slow to start and flaky across many concurrent sessions; pinning them as local devDependencies and pointing `.mcp.json` at the installed path is faster and steadier. Not your problem to fix mid-task — just don't be surprised if an MCP specialist is missing or slow, and fall back cleanly.

---

## The map

| The work is about… | Specialist (route here first) | How to invoke | One-line install | Built-in fallback when absent |
| :-- | :-- | :-- | :-- | :-- |
| **UI, components, layout, styling, design polish** | `frontend-design` *(plugin)* | Auto-invoking design skill — just describe the UI work | `/plugin install frontend-design@claude-plugins-official` | Build it yourself to the design bar it sets: a deliberate aesthetic direction, real type hierarchy (avoid default Inter/Roboto "AI slop"), spacing scale, accessible contrast, responsive breakpoints, purposeful motion. Mirror existing components. |
| **A feature / behavior change (the disciplined loop)** | `superpowers` *(plugin)* — methodology; or `feature-dev` *(plugin)* | Their workflow skills trigger on build/feature requests | `/plugin install superpowers@claude-plugins-official` · `/plugin install feature-dev@claude-plugins-official` | Run the loop yourself: brainstorm → spec → plan → **red→green TDD** → subagent two-stage review → finish (see `workflow-playbooks.md`). You already embody superpowers' method. |
| **Writing / fixing / pruning tests** (from code) | **Test Architect** *(bundled — always here)* | Route to the `test-architect` skill | — bundled with Ringmaster | — (never absent) |
| **Test scenarios from a requirement** (Jira/spec, before code) | **Scenarios from Requirements** *(bundled — always here)* | Route to the `scenarios-from-requirements` skill | — bundled with Ringmaster | — (never absent) |
| **Browser / end-to-end runs, real-DOM checks** | `playwright` *(MCP, by Microsoft)* | Describe the flow to exercise; uses `mcp__…playwright` tools | `claude mcp add playwright --scope local -- npx -y @playwright/mcp --headless` (or `/plugin install playwright@claude-plugins-official`) | Use the project's existing e2e runner (Cypress, an installed Playwright, Selenium); if none, write unit/integration coverage and flag the e2e gap |
| **Current library API: "how does X work now?"** | `context7` *(MCP, Upstash)* | Add "use context7" to the request, or call its `query-docs`/`resolve-library-id` tools | `claude mcp add context7 -- npx -y @upstash/context7-mcp@latest` (or `/plugin install context7@claude-plugins-official`) | Official docs via web search, or read the installed package's own types/source in `node_modules` / site-packages |
| **Database: schema, migrations, queries, auth** | `supabase` *(MCP)* if a Supabase project — else the project's DB tooling | Its `mcp__…supabase` tools | `claude mcp add --transport http supabase https://mcp.supabase.com/mcp` (or `/plugin install supabase@claude-plugins-official`) | Project's own DB tooling + migration system; never hand-edit a live schema — write a migration and stage it |
| **Payments / billing / checkout** | `stripe` *(official MCP)* | Its `mcp__…stripe` tools, **test mode only** | `/plugin install stripe@claude-plugins-official` (or add the official Stripe MCP) | Project's payment SDK against **test/sandbox keys only**; never live keys or real charges |
| **Security review before staging** | **Security Gate** *(bundled agent — always here)* | Dispatch the `security-gate` subagent on the diff | — bundled with Ringmaster | — (never absent) |
| **Extra security hardening / scanning** | `security-guidance` *(plugin)* — or `semgrep` / `aikido` | `security-guidance` runs as a `PreToolUse` hook (9 patterns); Semgrep scans in real time | `/plugin install security-guidance@claude-plugins-official` | The bundled Security Gate already covers this; these stack on top |
| **Code review of a change** | **Code Review** *(bundled skill — always here)* | The `code-review` skill; it dispatches `code-reviewer` ×2 (Spec ‖ Standards) | — bundled with Ringmaster | — (never absent); the `code-review` plugin (`/plugin install code-review@claude-plugins-official`) is a richer optional upgrade Ringmaster prefers when present |
| **Owning an AI-written change — comprehension + auditable sign-off** | **Ownership Review** *(bundled skill — always here)* | The `ownership-review` skill; it drives the `comprehension` agent | — bundled with Ringmaster | — (never absent) |
| **Deeper PR review (tests, types, simplification)** | `pr-review-toolkit` *(plugin)* — 6 specialized agents | Its review agents | `/plugin install pr-review-toolkit@claude-plugins-official` | Fold into the bundled review pass |
| **Tidy / simplify recently-changed code** | `code-simplifier` *(plugin)* | Its clarity agent | `/plugin install code-simplifier@claude-plugins-official` | Apply the simplification yourself, preserving behavior (keep tests green) |
| **Keeping CLAUDE.md / project docs current** | `claude-md-management` *(plugin)* | Its CLAUDE.md audit skill | `/plugin install claude-md-management@claude-plugins-official` | Edit `CLAUDE.md` and docs directly — capture changed behavior, structure, conventions |
| **Creating a *skill*** | `skill-creator` *(plugin)* | Create / improve / **eval & benchmark** skills | `/plugin install skill-creator@claude-plugins-official` | Scaffold a `skills/<name>/SKILL.md` with a strong trigger description yourself |
| **Creating a *plugin*** | `plugin-dev` *(plugin)* | `/plugin-dev:create-plugin` + 7 expert skills (hooks, MCP, commands, agents) | `/plugin install plugin-dev@claude-plugins-official` | Scaffold the documented layout (`.claude-plugin/plugin.json`, `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`) |
| **An interactive visual explorer for a problem** | `playground` *(plugin)* | `/playground <what to explore>` — builds a single-file HTML tool with live controls/preview | `/plugin install playground@claude-plugins-official` | Build a small self-contained HTML explorer yourself, or reason it through in chat |
| **Deploy *previews*, hosting, env vars, Next.js / serverless, AI SDK / Gateway** | `vercel` *(plugin + MCP)* | `/vercel:deploy` (preview) · `/vercel:env` · `/vercel:status`; Next.js/AI skills auto-fire; agents `deployment-expert` · `performance-optimizer` · `ai-architect` | `/plugin install vercel@claude-plugins-official` | The project's own deploy/env tooling — preview/dev only, never prod |
| **Performance (LCP / Core Web Vitals), accessibility audits, memory leaks, network & runtime debugging** | `chrome-devtools` *(MCP)* | Describe the perf/a11y/debug goal; skills `debug-optimize-lcp` · `a11y-debugging` · `memory-leak-debugging` · `chrome-devtools` | `/plugin install chrome-devtools-mcp@claude-plugins-official` | Lighthouse / DevTools by hand; reason from build output and profiles |
| **GitHub: issues, repo & PR *read*/review, code search, CI status** | `github` *(MCP)* | Its `mcp__…github` tools | `/plugin install github@claude-plugins-official` | `gh` CLI **read-only** (`gh pr view`, `gh run list`, `gh search`) |

> **Rail interaction worth knowing:** the `commit-commands` plugin exposes `/commit`, `/commit-push-pr`, and `/clean_gone`. Ringmaster's guardrails hook will **deny** the commit/push/PR actions even if that plugin is installed and invoked — staging-and-handing-off is the rule regardless of what tooling is present. That's by design, not a conflict.

> **Ship-on-command (rail interaction for `vercel` & `github`):** these two specialists can take *shipping* actions, so the rails meet them precisely. A **production deploy** (`vercel --prod`, or the Vercel-MCP deploy with a prod target) is **blocked outright** — you run prod yourself. A **preview/dev deploy** and **opening/merging a PR** (`gh pr create|merge`, or the GitHub-MCP `create_pull_request` / `merge_pull_request` / `push_files`) are never done autonomously — they **pause for your explicit confirmation**, then proceed. Read-only GitHub (view / list / search) and non-deploy Vercel (`env`, `ls`, `logs`, `build`) run freely. So: route freely for *reading, reviewing, building, and preparing*; let the human's confirm (or their own hand) drive the *shipping*.

> **Every MCP tool is gated now, not just github/vercel.** The guardrails hook's MCP matcher is `mcp__.*` (in `hooks/hooks.json`) — so the same policy (`classify_tool`) runs on **every** `mcp__*` call, closing the gap where a Bash-blind MCP could slip past. What it enforces beyond the ship-gates above: (1) a **universal PROD rail** — *any* MCP tool whose input targets production (a `target`/`environment`/`env`/`namespace`/`context` value of `prod`/`production`/`live`, a `"prod": true`, or `--prod`) is **denied**, so a `supabase`, Postgres, Mongo, infra, or data MCP can't touch prod even though the Bash hook never sees it; and (2) **Stripe in LIVE mode** (a `sk_live_`/`rk_live_` key, `livemode: true`, or `mode: "live"`) is **denied** — payments work is test/sandbox only. It stays **allow-by-default**: read-only MCP calls (search, list, get, `query-docs`) and dev/UAT-targeted writes run untouched, and prose that merely *contains* "production" under a non-env key (a Notion/Gmail search for "production incident") does **not** false-positive. The live/test split for Stripe is usually decided by the configured key the hook can't see, so test-mode-only is also a behavioral rail (see `stripe` note) — defense in depth.

---

## Notes on the specialists (verified specifics)

**superpowers (obra/superpowers, MIT; also in the official directory).** The *methodology* engine, not a feature tool. Anthropic's own directory summarizes it as teaching Claude "brainstorming, subagent development with code review, debugging, TDD, and skill authoring." It's the discipline Ringmaster is built on: don't rush to code — tease out the spec, show the plan in readable chunks, drive **true red→green TDD** with fresh-subagent two-stage review (spec-compliance, then code-quality), honest status protocol. Installed → lean on its skills. Absent → you already are it. (For scale: ~752k installs as of mid-2026, second only to frontend-design's ~829k — this is the ecosystem's center of gravity for method.)

**frontend-design.** Auto-invokes on UI work — describing the task is usually enough. Its whole point is *distinctive, production-grade* design that avoids generic AI aesthetics: a chosen aesthetic direction, characterful typography (it explicitly steers away from Inter/Roboto defaults), high-impact motion, gradient meshes / noise / grain for atmosphere. If you fall back to building UI yourself, hold that same bar — don't ship default-looking markup.

**code-review (bundled skill + optional plugin).** Ringmaster ships its own **`code-review` skill**: it reviews the diff along two axes as **parallel fresh-context sub-agents** (`agents/code-reviewer.md` dispatched twice — *Spec*: does it match the plan/ticket, no more, no less? and *Standards*: is the code sound?), aggregates them, and records `gate.clean`. Route here in stage 3 *after* the Security Gate clears the diff — security first (it can block), then quality/spec review — and *before* the ownership review's sign-off: detection finds the defects, then the ownership review makes sure the human actually understands the change they're about to own. The external **`code-review` plugin** (`/code-review`) is an optional upgrade — a multi-agent pipeline with **confidence scoring 0–100, reporting only issues ≥80**, `gh`/MCP integration, and Opus validation; install it for a richer pass and Ringmaster will prefer it when present.

**feature-dev.** A **7-phase** workflow orchestrating three agents — `code-explorer` (understands the codebase), `code-architect` (designs the change), `code-reviewer` (quality gate) — and it also does CLAUDE.md audits and session-learning capture. A strong alternative to the superpowers loop for larger features.

**security-guidance.** A complementary **`PreToolUse` hook scanning diffs for 9 security patterns**. If the user has it installed it stacks cleanly with Ringmaster's own guardrails hook (hooks run in parallel; the strictest decision wins). It does **not** replace the bundled Security Gate agent, which is a deeper, fresh-context adversarial review you actively dispatch. Semgrep and Aikido are heavier scanning options in the same directory.

**context7 (Upstash MCP).** Reach for it the instant you're unsure an API is current — it resolves a library to an ID and injects up-to-date, version-specific docs (React 19, Next.js 15, etc.) before you generate code, killing the most common silent bug: an API that changed since training. Requires Node 18+; package `@upstash/context7-mcp`.

**playwright (Microsoft MCP).** Browser automation + e2e: navigate, click, fill forms, screenshot, run flows. Package `@playwright/mcp`. Useful for letting the build verify its own UI end to end — but it's an MCP, so confirm it's connected before relying on it.

**supabase (MCP).** Schema, SQL, migrations, data. **Supabase's own documentation states the MCP is for development and testing only and must never be connected to production data** — which lines up exactly with Ringmaster's prod rail. The Security Gate and guardrails hook enforce dev/UAT/preprod regardless of which DB specialist is driving.

**stripe (official MCP).** Payments/billing. **Test/sandbox mode only — never live keys, never a real charge.** Confirm test-mode is in force before anything runs; the rails apply with full force. The guardrails hook now **denies a Stripe MCP call it can see running in live mode** (a `sk_live_`/`rk_live_` key, `livemode: true`, or `mode: "live"` in the call input) — but the live/test split usually lives in the *configured key* the hook can't read, so this is a backstop, not a guarantee: your judgment that test-mode is in force is still the primary rail. Note `stripe` is an MCP — if a payments task needs it and it isn't configured, **stop and ask to wire it up** (or fall back to the project's payment SDK in test mode), per the MCP preflight rule above.

**playground.** Not a code sandbox (an earlier assumption I corrected) — it's a generator of **interactive single-file HTML explorers** with visual controls, live preview, and a copy-out prompt. Templates: design-playground, data-explorer, concept-map, document-critique. Invoke with `/playground <thing to explore>`. Use it when the input space is large, visual, or structural and hard to express as plain text.

**vercel (plugin + MCP).** The deploy/host/platform specialist: `/vercel:deploy` (preview by default), `/vercel:env` (env-var sync), `/vercel:status`, plus deep skills for Next.js, the AI SDK / AI Gateway, storage, middleware, and three agents (`deployment-expert`, `performance-optimizer`, `ai-architect`). Reach for it for anything deploy-, env-, or Next.js-shaped. **Rail-critical:** a *preview* deploy asks first and a *production* deploy is blocked (see the ship-on-command note above) — so route it for building, env work, and preview, and leave prod to the human. Its `knowledge-update` skill also corrects stale platform assumptions (Fluid Compute, `vercel.ts`, AI Gateway) — trust it over memory.

**chrome-devtools (MCP).** The **performance, accessibility, and deep-debugging** specialist — and the complement to playwright, not a duplicate of it: think *playwright = drive a user flow end-to-end*, *chrome-devtools = profile and diagnose what that flow does*. Use it for Core Web Vitals / LCP work (`debug-optimize-lcp`), a11y audits (`a11y-debugging` — semantic HTML, ARIA, contrast, tap targets, keyboard nav), memory-leak hunts (`memory-leak-debugging`), and network/console/runtime inspection (`chrome-devtools`). It's an MCP, so confirm it's connected before relying on it; if it isn't, ask whether to wire it up (perf/a11y are hard to do well without it).

**github (MCP).** Repo management over the GitHub API: issues, pull-request **read & review**, code/repo search, CI run status. Route here for *understanding and reviewing* what's on GitHub. **Rail-critical:** its *write* tools (`create_pull_request`, `merge_pull_request`, `push_files`, file create/update/delete) are gated exactly like the Bash forge ops — never autonomous, paused for your confirm — and the guardrails MCP matcher enforces that even though they aren't Bash. So lean on it freely for reads/reviews; let the human's confirm drive any PR write.

---

## The five always-present specialists

These ship inside Ringmaster — available on every project with zero install, the backbone the rails lean on:

- **Test Architect** (`skills/test-architect/`) — all test craft: risk-based design, red→green TDD, behavior-not-implementation assertions, determinism, pruning stale tests, pretty final report. Route *every* test-from-code step here.
- **Scenarios from Requirements** (`skills/scenarios-from-requirements/`) — the requirements-first sibling of the Test Architect: reads a Jira/Confluence (or Trello/Linear/Azure DevOps/GitHub Issues) source of truth through a read-only adapter, interrogates it for genuine gaps, and writes brutally thorough, fully-traceable **scenarios** (with a security-hardened HTML/CSV coverage report) *before* any code — then hands them to the Test Architect for the write→run phases. Route here when the job starts from a **requirement**, not from code.
- **Security Gate** (`agents/security-gate.md`) — a fresh-context adversarial reviewer dispatched on the working diff before staging. Hunts secrets, injection, broken authz, crypto misuse, dependency risk; **blocks on critical**; reports defects but never fixes them; never commits.
- **Code Review** (`skills/code-review/`, driving `agents/code-reviewer.md`) — the two-axis quality-and-spec review. It dispatches the `code-reviewer` agent **twice in parallel**, once as *Spec* (does the change match the plan/ticket — no more, no less?) and once as *Standards* (is the code correct, safe on its edges, and conventional?), so the two lenses never cross-pollinate; it aggregates both into the house two-stage report and records `gate.clean`. Runs after the Security Gate and before the Ownership Review; reports defects but never fixes them; never commits.
- **Ownership Review** (`skills/ownership-review/`, driving `agents/comprehension.md`) — where the Security Gate and Code Review above ask "is the code correct and safe?", this asks "does the human about to take 100% responsibility actually understand it?" It reconstructs understanding through an **answer-first** comprehension quiz grounded in the real diff, teaches every hole in plain language, calibrates the developer's confidence against how they truly did, and records an **auditable ownership sign-off** (`gate.owned`) the Stop hook enforces. Route to it in stage 3 for any change someone must own; it reuses (never rebuilds) the detection above.

Everything else is an optional upgrade. Ringmaster is complete and safe with zero external plugins installed — those just make individual capabilities sharper.
