# Hardening notes & threat model

Ringmaster's rails are built to prevent **mistakes** — an over-eager agent, an auto-approved command, a `--dangerously-skip-permissions` session — not to defeat someone deliberately obfuscating a command to evade them. Within that threat model the design is deliberately layered and honest about its edges.

## Two layers

The rails live in:

1. **The `guardrails.py` hook** — deterministic, evaluated *before* Claude Code's permission check, so a `deny` can't be bypassed even under skip-permissions. A hook can only tighten safety, never loosen it. (The ship-on-command actions use the hook's `ask`, so they *pause for you* rather than block.)
2. **The orchestrator skill + session doctrine** — behavioral: the model is instructed to follow the same rails regardless. If the hook can't run, the behavioral layer still holds.

## The cross-platform launcher (and its fail-open caveat)

A `PreToolUse` hook can only block when it actually executes. The hooks launch through a tiny POSIX `sh` shim that discovers an interpreter by **actually running** each candidate — `python3`, then `python`, then `py` — and using the first that executes successfully:

```sh
for c in python3 python py; do "$c" -c pass </dev/null >/dev/null 2>&1 && exec "$c" "$0"; done; exit 0
```

Probing by execution (not just `command -v` existence) matters on Windows: stock Windows 11 ships Microsoft-Store **stub** `python`/`python3` aliases that exist on PATH but only print "Python was not found" and exit. An existence check would pick the stub and the rails would go silently dark; the execution probe skips the fakes and finds a real install — including a `py`-launcher-only setup. This exact trap is simulated in CI on every push (see below).

The shim fires on macOS, Linux, WSL, and Windows (where Claude Code runs hook commands through the Git-Bash `sh` bundled with Git for Windows). The hooks use only the Python standard library. If **no** working interpreter (or no POSIX `sh`) is found, the shim exits cleanly and the hard rail is simply *absent* — and **you'll see it**, because the SessionStart banner ("🎪 Ringmaster is active … Hard safety rails armed") won't appear. Its absence is your signal that only the behavioral layer is live: install Python (python.org or `winget install Python.Python.3`) and reload.

## What the hook catches

- **Every standard git history/publish op** — commit, push, merge, rebase, cherry-pick, revert, **release** creation — including chained, subshell, heredoc, `eval`, and env-prefixed forms; plus `git filter-branch`, `jj`, `hg`, `bzr`, and `svn`.
- **Package/release tooling** — `npm`/`pnpm version <bump>`, `npm`/`yarn`/`pnpm`/`bun publish`, `cargo publish`/`release`, `poetry publish`, `twine upload`, `gem push`, `mvn deploy`/`release:*`, `gradle publish`, `dotnet nuget push`, `release-it`/`standard-version`/`semantic-release`, `changeset publish` — with `--dry-run` and `npm version --no-git-tag-version` correctly exempted.
- **Production targeting** — env vars (`NODE_ENV=production`), long-form flags (`--profile prod`, `--context production`, `--namespace prod`), the **kube-family short namespace flag** (`kubectl`/`helm`/`oc` `-n prod`, scoped to those binaries so `grep -n production` / `tail -n 100 prod.log` stay free), prod-looking URLs, bare `--prod`/`--live` switches, and high-signal action-in-name compounds (`make deploy-prod`, `npm run deploy:prod`, `./deploy-production.sh`, `rake migrate:prod`). It deliberately does **not** trip on a production *build* artifact (`npm run build:prod`), a search term (`grep production`), or `git reset`/branch switches.

## Write/Edit tools are gated too (v2)

A third matcher — `Write|Edit|MultiEdit|NotebookEdit` — runs file writes through `classify_write`: content matching a **live-credential** shape (`sk_live_`/`rk_live_`/`AKIA…`/`ghp_`/`github_pat_`/`glpat-`/Slack `xox…`/Google `AIza…`/a PRIVATE KEY block, each with a length/charset floor so placeholders don't trip it) is **denied**; a write into **`.git/` internals** is **denied**; a write to a **prod env / key / creds** file (`.env.production`, `id_rsa`, `*.pem`/`*.key`, `.aws/credentials`, `.npmrc`, `secrets.*`, …) **asks**. Ordinary source edits and `.env.example`/`.env.local` run free.

## Wrapped-runner resolution (v2)

When a Bash command is a `make <target>`, an `npm`/`yarn`/`pnpm` script, or a `bash`/`sh <file>.sh`, the hook reads the target's body from the working dir and re-applies the *same* policy to it — so a push / prod hit / publish hidden one indirection deep is caught. It's best-effort and **fail-open** (a missing/unreadable target just yields no extra finding) and can only ever *add* a decision, never remove one.

## The A-grade gate has a tooth (v2)

A `Stop` hook (`hooks/stop_gate.py`) blocks a turn from ending while an in-progress task's recorded `gate` has an explicit failure — unless the task is `blocked` or `waitingOnHuman` is set. It respects `stop_hook_active` (no loops), never traps an absent gate, and fails open on a missing/corrupt ledger.

## What the hook *asks* about (ship-on-command, never denied)

Opening/merging a PR (`gh pr create|merge`, `glab mr …`) and a non-prod `vercel deploy` — never autonomous, but they proceed on your confirm.

## Every MCP tool is gated, not just github/vercel

A second matcher — `mcp__.*` in `hooks/hooks.json` — routes **every** `mcp__*` call through the same policy, because those calls aren't Bash and would otherwise bypass the gate entirely. Beyond the GitHub/Vercel ship-gates (PR-write → ask; deploy → prod-deny / preview-ask), it adds:

1. a **universal PROD rail** — *any* MCP tool whose input targets production (`target`/`environment`/`env`/`namespace`/`context` = `prod`/`production`/`live`, `"prod": true`, or `--prod`) is **denied**, so a Supabase / Postgres / infra / data MCP can't touch prod; and
2. **Stripe LIVE mode** (`sk_live_`/`rk_live_` key, `livemode: true`, `mode: "live"`) is **denied** — payments are test/sandbox only.

It stays allow-by-default: read-only MCP calls and dev/UAT writes run free, and prose containing "production" under a non-env key (a Notion/Gmail search) does not false-positive.

## Documented boundary (honest about the edges)

A few bespoke vectors still pass the deterministic hook by design: a schemeless prod hostname (`ssh user@prod-host`), a single-letter host flag (`-h prod…`), a deploy command with *no* environment marker at all (a bare `npm run deploy` that targets prod internally), a resource/app name that merely embeds "prod" but isn't passed through a recognized env flag (`flyctl deploy --app my-prod-api` — chasing this via the flag list would false-positive on every benign `--app`), and a command hidden behind shell-variable indirection. The orchestrator's environment-reasoning layer (`skills/orchestrator/references/safety-and-environments.md`) is the intended backstop for these. `git reset`/branch-switching are intentionally *allowed* (they don't write shared history). **Allow-by-default is the rule:** unrecognized commands are never blocked, so normal dev is never impeded.

**Non-prod envs beyond UAT** (e.g. `qa`, `sandbox`, `ci`) are treated as safe and allowed; only **prod** is denied and **shared pre-prod/staging** asks. This matches the intent of "never prod, confirm shared" without obstructing legitimate test tiers.

**Stacks with `security-guidance`.** If you also run Anthropic's official hook, both fire in parallel and the strictest decision wins — more coverage, no conflict.

## Continuous integration (the proof)

The safety rails are only worth as much as their proof, so the adversarial battery runs automatically — not just on demand. [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) fires on every push and pull request and, with `fail-fast` off, runs the full suite across a matrix:

- **OS:** `ubuntu-latest`, `windows-latest`, `macos-latest` — the three platforms Ringmaster claims to support, so the cross-platform promise (including Windows console-encoding handling) is exercised on real runners, not asserted.
- **Python:** `3.9` (minimum supported) → `3.11` → `3.13` → `3.14` (latest) — the hooks are standard-library only, so the span guards against syntax/stdlib drift with nothing to install.

Each job:

1. validates the JSON manifests (`plugin.json`, `marketplace.json`, `hooks.json`);
2. runs the **191-case** `hooks/test_guardrails.py` battery plus the `test_ledger.py` (27 cases) and `test_routing.py` batteries, and a cross-platform smoke of the `ledger.py` CLI that backs resume and the board/gate commands;
3. drives the hook over **stdin end-to-end** — real `PreToolUse` payloads (a prod-deny, a Write-secret deny, an ask) with the decision asserted, plus a smoke of the `stop_gate.py` Stop hook;
4. smoke-tests the **launcher shim itself** — extracting the *real* registered command from `hooks.json` and running it end-to-end, including a simulated Windows Store-stub trap (fake failing `python3`/`python` ahead of a working `py`) — so the one component outside the Python batteries is verified too.

A separate `plugin-validate` job runs `claude plugin validate --strict` in both of its modes — marketplace mode at the repo root and plugin mode on a marketplace-less copy (the mode that parses skill/agent/command frontmatter and `hooks.json`). This is the same check Anthropic's plugin-review pipeline runs on every submission.

A final `all-green` job gates on the whole matrix plus the validation job, giving a single required check to protect `main` with; its live status is the badge at the top of the README.

Run the batteries yourself any time:

```
python3 hooks/test_guardrails.py   # 191 adversarial cases (or `python` / `py`)
python3 hooks/test_ledger.py       # 27 ledger cases
python3 hooks/test_routing.py      # routing / A-grade gate
```
