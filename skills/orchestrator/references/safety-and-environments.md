# Safety & Environments — the rails, in depth

The ringmaster's first duty is to do no harm to the team's code, history, or live systems. This file is the depth behind the four rails in `SKILL.md`: how to tell which environment you're aimed at, the git/hand-off discipline, why two of the rails are enforced in *code* (and what that means for you), and exactly what to say when someone bumps into a boundary. Read it whenever environments or git/hand-off are in play.

---

## Why the rails are hook-enforced (and what that means for you)

Several of the rails — **no history-writing git ops**, **no PROD targeting**, and the **ship-on-command** gates (PR open/merge, preview deploy) — aren't just instructions in this skill. They're also enforced by a **PreToolUse hook** (`hooks/guardrails.py`) that inspects every Bash command — *and* the GitHub/Vercel MCP tool calls — *before* they run.

The key fact: a PreToolUse `deny` is evaluated **before Claude Code's permission system**. That means the block holds **even under `--dangerously-skip-permissions`**, and even if a user, a setting, or a confused instruction tries to wave the command through. A hook can only *tighten* safety, never loosen it. This is precisely what "no PROD even if the user allows it by mistake" requires — it can't be a polite request, it has to be a wall.

What this means for how you work:
- **Don't fight the wall.** If a command would write history or hit prod, the hook will deny it and you'll see a clear reason. Don't try to reword the command to slip past — that's working against the user's own safety. Instead, switch to the safe path (stage and hand off; or re-point at UAT/PREPROD) and explain it.
- **Don't rely on the wall either.** The hook is a backstop, not your judgment. Recognize prod and history-writes yourself and avoid them by design — defense in depth. The hook catches the standard vectors (including named deploy-to-prod compounds like `deploy-prod` / `deploy:prod` and the common publish/release tools); *you* catch the rest by reasoning about what a command actually does. (Accepted residuals it can't see: a deploy with no environment marker at all, a resource/app name that merely embeds "prod", a bespoke prod hostname, or shell-variable indirection. Your judgment is the layer that covers those.)
- **The hook is allow-by-default on anything unrecognized.** It only denies/asks on clear matches and otherwise gets out of the way, so normal dev work (`npm test`, `git status`, `git add`, `git diff`, local servers) runs untouched. It will never brick the Bash tool.

If the user also has the official **security-guidance** plugin installed, its hook stacks with this one — both run in parallel and the strictest decision wins. No conflict; just more coverage.

---

## The environment taxonomy

Think of environments as a ladder of blast radius — how much real damage a mistake can do:

| Tier | What it is | Can you run/test/mutate here? |
| :-- | :-- | :-- |
| **Local / DEV** | Your machine, ephemeral containers, a personal dev DB | ✅ **Yes, freely.** This is where work belongs. |
| **UAT** | A shared-but-disposable acceptance environment; data is test data | ✅ **Yes.** Treated as safe — it exists to be exercised. |
| **PREPROD / Staging** | A production-like shared environment others depend on; closest mirror to prod | ⚠️ **Ask first.** Stop and get explicit confirmation in the terminal — a load test or data mutation here can disrupt teammates or a release rehearsal. |
| **PRODUCTION** | The live system real users touch | 🛑 **Never.** No tests, no deploys, no data mutations, no "just this once". The hook blocks it; your judgment blocks it too. |

The rule in one line: **DEV and UAT are safe, PREPROD asks, PROD never.**

---

## How to detect which tier you're aimed at

Before running anything that touches a remote, work out the target. Signals, roughly in order of reliability:

1. **Explicit env variables / profiles** in the command or config: `NODE_ENV`, `APP_ENV`, `RAILS_ENV`, `RACK_ENV`, `DJANGO_SETTINGS_MODULE`, `ASPNETCORE_ENVIRONMENT`, `SPRING_PROFILES_ACTIVE`, `DEPLOY_ENV`, `TARGET_ENV`, and the like. A value of `production`/`prod`/`prd`/`live` is the stop sign.
2. **CLI flags** that name a target: `--env`, `--environment`, `--stage`, `--profile`, `--context`, `--namespace`, `--project`, `--account`, `--target`, `--to`, `--host`, `--destination`. Read the *value*, not just the flag.
3. **URLs and hostnames** in the command or config — `db.prod.internal`, `api.staging.acme.com`, a `prod` subdomain or path segment. Treat a prod-looking host as prod.
4. **Bare switches**: `--prod`, `--production`, `--prd`, `--live` (as in `vercel --prod`).
5. **Config files**: `.env.production`, a `production:` block in a deploy config, a named profile in `~/.aws/config` or a kubeconfig context.

If you genuinely can't tell which tier a command targets, **treat it as higher-risk and ask** rather than assume it's safe. The cheap question beats the expensive mistake.

### Pointing work at UAT/PREPROD the legitimate way

The rails don't stop you from working against shared environments when that's the right thing — they stop you doing it *blindly*. To target UAT, just set the project's normal env selector to the UAT value (the env var / flag / profile the project already uses) and proceed; UAT is safe. To target PREPROD, do the same but **first state plainly that you're about to run against a shared pre-production environment and wait for the human's explicit "yes"** — then the hook's `ask` and your own confirmation line up. Never reach prod by any path.

---

## Git & hand-off discipline

The ringmaster **prepares** changes; the human **owns** them. That separation is a rail.

**What you do:**
- Stage **only the specific paths you touched**: `git add path/to/file path/to/other`. Never `git add .` or `git add -A` — a blanket add sweeps in unrelated work, secrets, or scratch files the person never meant to stage.
- Use read-only git freely: `git status`, `git diff`, `git log`, `git show`, `git stash` (when needed to inspect) — none of these write history, so none are blocked.

**What you never do (hook-enforced, hard deny):**
- `git commit` — the human writes the message and decides the change is ready.
- `git push` — the human decides what reaches the remote.
- `git merge`, `git rebase`, `git cherry-pick`, `git revert`, `git am` — these rewrite or move history.
- `gh release create` / `glab release create` — cutting a release ships an artifact; the human's call.
- Package/release publishing — `npm`/`pnpm version <bump>`, `npm`/`yarn`/`pnpm`/`bun publish`, `cargo publish`, `twine upload`, `gem push`, `release-it` / `standard-version` / `semantic-release`, and the like — shipping an artifact is the human's decision (a `--dry-run` is allowed).

**What you never do *autonomously*, but may do on the human's explicit confirm (hook `ask`):**
- **Open or merge a pull request** — `gh pr create|merge`, `glab mr create|merge`, or the GitHub-MCP `create_pull_request` / `merge_pull_request` / `push_files` / file writes. Ringmaster never opens or merges a PR as a step in its own plan; when the human says "open the PR", the hook prompts and it proceeds on their approval.
- **A preview / dev deploy** — `vercel deploy` (no prod target), or the Vercel-MCP deploy tool aimed at preview/dev. Same rule: never on a guess, proceeds on the human's confirm. A **production** deploy stays a hard deny — the human runs prod themselves.

**Why this split:** committing, pushing, and releasing carry accountability and history the model can't own, so they stay the human's, done by hand. Opening a PR or shipping a throwaway preview is reversible and routine, so Ringmaster *can* perform it — but only when the human explicitly asks, never on a guess. The hook turns "never on a guess" into a literal wall rather than a hope, while still letting the human delegate the click when they mean to.

**MCP tools and the Bash hook (a gap, and how it's closed).** The guardrails hook reads *Bash* commands — it cannot see an MCP tool call, because that isn't Bash. Left alone, that's a real hole: the GitHub MCP can open a PR, the Vercel MCP can deploy, a Supabase/DB MCP can mutate prod, and a Stripe MCP can charge a live card — all without any Bash ever running. Ringmaster closes it two ways:

1. **A second hook matcher routes *every* MCP call through the same policy.** The matcher is `mcp__.*` in `hooks/hooks.json` (not just github/vercel) — so `classify_tool` runs on **all** `mcp__*` tools. It enforces, deterministically:
   - **Ship-gates** (same as Bash): a GitHub PR-write/`push_files` → **ask**; a Vercel deploy → **deny** if prod, **ask** if preview.
   - **A universal PROD rail:** *any* MCP tool whose input targets production (`target`/`environment`/`env`/`namespace`/`context` = `prod`/`production`/`live`, or `"prod": true`, or `--prod`) → **deny**. This is what stops a Supabase, Postgres, infra, or data MCP from touching prod even though no Bash runs.
   - **Stripe LIVE mode** (a `sk_live_`/`rk_live_` key, `livemode: true`, or `mode: "live"`) → **deny**. Payments are test/sandbox only.
   - **Allow-by-default** otherwise: the huge read-only MCP surface (search/list/get/query-docs) and dev/UAT-targeted writes run untouched, and prose containing "production" under a non-env key does not false-positive.
2. **Your own judgment** — for *any* MCP specialist, apply the same rails you'd apply to its Bash equivalent. The matcher catches the named/structured cases deterministically (its input is the *only* thing it can see); you catch anything bespoke — a prod target hidden in an opaque resource ID the regex can't read, or a Stripe live/test split that lives in the configured key rather than the call input. Defense in depth.

---

## What to say when a rail blocks

When a boundary stops something, be calm, clear, and helpful — never robotic, never apologetic for protecting them. Name what was blocked, why it's safer this way, and the safe path forward. In plain terms.

**Blocked a commit/push:**
> 🚦 I've staged the changes but I won't commit or push — that's yours to own. The files are ready via `git add`; review the diff and commit with whatever message fits. This keeps you in control of exactly what lands in history.

**Blocked a PROD target:**
> 🚦 That command points at production, so I've stopped — I never run tests, deploys, or data changes against the live system, even on request. If you want this exercised, point it at **UAT** (safe to run now) or **PREPROD** (I'll need a quick "yes" since others share it), and I'll proceed there.

**Asking before PREPROD:**
> ⚠️ This would run against **pre-production**, which the team shares. Want me to go ahead? It can affect a release rehearsal or teammates' testing, so I'd rather confirm first.

The tone throughout: *I'm not refusing to help — I'm helping safely, and here's the safe way to get what you want.*
