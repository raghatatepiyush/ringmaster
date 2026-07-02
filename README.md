# 🎼 Conductor

[![CI](https://github.com/raghatatepiyush/conductor/actions/workflows/ci.yml/badge.svg)](https://github.com/raghatatepiyush/conductor/actions/workflows/ci.yml)

**Turn Claude Code into a disciplined senior engineering team.** Describe a task in plain English — build a screen, add a feature, write tests, wire a database, fix a bug — and Conductor frames the real goal, shows you a short plan, waits for your **"go"**, routes each step to the best specialist plugin (or a built-in fallback), ships every change with tests through an adversarial Security Gate, and hands back staged, reviewed work — explained so a junior engineer with no project context could follow it.

It's the *conductor*, not the orchestra: it reads the score, picks who plays each part, keeps tempo, and enforces the safety rails — without re-implementing the specialists it directs.

## Install

```
/plugin marketplace add raghatatepiyush/conductor
/plugin install conductor@conductor
```

The only dependency is Python 3 (see [Requirements](#requirements)). On every OS, the SessionStart banner is your proof the hard rails are armed:

> 🎼 Conductor is active … Hard safety rails armed (hook running on Windows, Python 3.14).

## Quick start

Just talk to Claude normally:

> "Add a dark-mode toggle to the settings page and cover it with tests."
> "Fix the bug where expired sessions still work."

Conductor auto-triggers: it frames the task, shows a short plan, waits for your **"go"**, then builds — testing, security-gating, and staging as it goes. Also useful:

| Say | To |
| :-- | :-- |
| `/conductor:orchestrator` | invoke it explicitly |
| `pickup` (or `/conductor:pickup`) | resume unfinished work from a previous session — even a teammate's |
| "go deep" | a one-off exhaustive pass: wider tests, an explicit security sweep, harder review |

## What you get

| | |
| :-- | :-- |
| 🎼 **A smart orchestrator** | classifies any request — frontend, feature, tests, bugfix, database, payments, docs, skill creation — and runs the right end-to-end playbook |
| 🧭 **Routing with fallbacks** | dispatches the best specialist plugin for each step (`frontend-design`, `code-review`, `playwright`, `supabase`, `stripe`, `vercel`, `github`, `context7`, `superpowers`, …) and falls back to a competent built-in when one isn't installed — work never blocks |
| 🧪 **A bundled Test Architect** | risk-based, red→green TDD, behavior-not-implementation assertions, stale-test pruning |
| 🔒 **A bundled Security Gate** | a fresh-context adversarial reviewer that hunts secrets, injection, broken authz, crypto misuse — and **blocks hand-off** on critical findings |
| 🗂️ **A resumable team board** | the `.conductor/` ledger tracks pending · in-progress · done · blocked with an owner and dependencies per task; any fresh session (or teammate) picks up exactly where the last one stopped |
| 👥 **Real delegation** | principal → engineer → junior subagents with complete context hand-offs, behind a six-criterion A-grade quality gate that a `Stop` hook actually enforces |
| 🎚️ **Token discipline** | every task is right-sized to the cheapest model/effort that still holds the bar; work that fails the gate auto-escalates back to the premium model — quality is model-independent |
| 🗣️ **Plain-language output** | every result is pretty-printed and explained so a newcomer understands what changed and why it's safer now |

Stack-agnostic: Conductor fingerprints your language, framework, and conventions and conforms. Nothing to configure.

## The safety rails (enforced in code, not just asked for)

A `PreToolUse` hook inspects every Bash command, every file write, and **every MCP tool call** *before it runs* — and a hook's `deny` is evaluated before Claude Code's permission system, so the hard rails hold **even under `--dangerously-skip-permissions`**:

| Rail | Enforcement |
| :-- | :-- |
| 🚦 Never commits, pushes, merges, rebases, or publishes a release/package | **deny** — Conductor stages with `git add <paths>`; *you* own the commit and the decision to ship |
| 🚦 Never runs anything against **PRODUCTION** — no tests, deploys, or data mutations | **deny** — work stays in DEV/UAT (free); shared PREPROD asks first |
| 🚦 Never *ships* on its own — opening/merging a PR, a preview deploy | **ask** — pauses for your explicit confirmation, on Bash and the MCP tools alike |
| 🚦 Won't write a live secret to disk or touch `.git/` internals | **deny** — and a prod env / key / credentials file pauses for you |
| 🚦 Sees through wrapped runners | `make deploy`, `npm run ship`, `bash deploy.sh` are resolved and re-checked — one indirection can't smuggle a push or a prod hit |

The hook is **allow-by-default** — normal dev (`npm test`, `git status`, `git add`, local servers) runs untouched, and it will never brick a tool. Every rail is proven by a **191-case adversarial battery** running in CI on Linux, Windows, and macOS across Python 3.9 → 3.14, on every push. The full threat model — what the hook catches, what it deliberately allows, and the honest edges — lives in **[docs/hardening.md](docs/hardening.md)**.

## How it works

**Frame & classify → plan (🛑 halt for your "go") → route & build → tests → 🔒 Security Gate → review → docs → 📦 stage & report.**

`SKILL.md` is a lean router; the depth lives in reference files loaded only when their moment comes (progressive disclosure), so the system stays token-light on every run.

<details>
<summary>Repository layout</summary>

```
conductor/
├── .claude-plugin/            # plugin + marketplace manifests
├── .github/workflows/ci.yml   # batteries + launcher smoke: 3 OSes × Python 3.9–3.14
├── commands/pickup.md         # /conductor:pickup — resume from the ledger
├── hooks/
│   ├── hooks.json             # registers the gates: Bash + Write/Edit + all-MCP + Stop
│   ├── guardrails.py          # PreToolUse policy (deny/ask); resolves wrapped runners
│   ├── stop_gate.py           # Stop hook: the A-grade gate's teeth
│   ├── session_doctrine.py    # SessionStart banner + stack hint + resume hint
│   ├── ledger.py              # board / next-task / gate / share helpers + CLI
│   ├── routing.py             # Task-Profile + A-grade-gate helpers
│   └── test_*.py              # the batteries (guardrails 191 · ledger 27 · routing)
├── skills/
│   ├── orchestrator/          # the conductor skill (thin router + references/)
│   └── test-architect/        # bundled Test Architect skill
├── agents/security-gate.md    # bundled adversarial security reviewer
├── docs/hardening.md          # threat model + CI proof
└── .conductor/                # (runtime, per-project) the ledger — self-ignored
```

</details>

## Requirements

- **Claude Code** with plugin support.
- **Python 3**, discoverable as `python3`, `python`, or `py`. The hooks are tiny standard-library-only scripts launched through a POSIX `sh` shim that **probes each candidate by actually running it** — so a broken or fake interpreter (like the Microsoft Store's `python` stubs on stock Windows 11) is skipped, and any real install is found, including a `py`-launcher-only setup.
- **macOS & Linux:** out of the box (`sh` is native; `python3` is almost always present). **Windows:** fully supported — Claude Code runs hooks through the Git-Bash `sh` bundled with Git for Windows; any Python install (python.org, `winget install Python.Python.3`, or just the `py` launcher) arms the rails.

No banner at session start = the rails aren't armed and only the behavioral layer is live — install/repair Python and reload. That honesty is deliberate: you always know which layer you're standing on.

## Stacking with other plugins

Conductor **directs** the official specialists rather than replacing them: install any of `frontend-design`, `code-review`, `playwright`, `supabase`, `stripe`, `vercel`, `github`, `context7`, `superpowers`, … and Conductor routes to them automatically; a needed-but-missing MCP is a quick question ("want me to wire it up?"), never a silent downgrade. It stacks cleanly with Anthropic's `security-guidance` hook (both fire; the strictest decision wins) — and it is complete and safe with zero external plugins installed. The verified capability map: [`skills/orchestrator/references/routing-and-plugins.md`](skills/orchestrator/references/routing-and-plugins.md).

## Learn more

- **[docs/hardening.md](docs/hardening.md)** — the threat model: what the hook catches, what it deliberately allows, and how CI proves it on every push.
- **[CHANGELOG.md](CHANGELOG.md)** — version history. New in **v2.2.1**: valid orchestrator-skill frontmatter (v2.2.0 shipped it broken, which disabled auto-triggering), bundled-helper paths that resolve from an installed plugin, and CI now runs `claude plugin validate --strict` in both modes.
- **[skills/orchestrator/references/](skills/orchestrator/references/)** — the full doctrine: routing, playbooks, safety & environments, state & resume, team & delegation, right-sizing, model routing.

## License

MIT.
