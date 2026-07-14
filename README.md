# 🎪 Ringmaster

[![CI](https://github.com/raghatatepiyush/ringmaster/actions/workflows/ci.yml/badge.svg)](https://github.com/raghatatepiyush/ringmaster/actions/workflows/ci.yml)
[![Listed on ClaudePluginHub](https://www.claudepluginhub.com/badge/raghatatepiyush-ringmaster)](https://www.claudepluginhub.com/plugins/raghatatepiyush-ringmaster?ref=badge)

> **Step right up — welcome to the SDLC circus.** 🎪
> Shipping software with AI is a high-wire act: fast, dazzling, and one slip from the net below. **Ringmaster is the ringmaster of that show.**

**It turns Claude Code into a disciplined senior engineering team that runs your whole software development lifecycle (SDLC) — safely.** You describe a task in plain English; Ringmaster works out what you *really* want, shows you a short plan, waits for your **"go,"** then directs a troupe of specialists through the entire act: build the feature, cover it with tests, run it past an adversarial security review, make sure *you* understand the code before you own it, and hand back staged, reviewed work — explained so clearly a junior engineer with zero project context could follow along.

It never grabs the mic itself. It reads the room, cues each act in turn, keeps the show on the rails, and — the part that matters most — **never commits, pushes, merges, or touches production on its own.** You always take the final bow: *you* commit, *you* ship.

**Three things make it more than a prompt pack:**

- 🔒 **Safety rails enforced in real code** (a hook) — not just politely requested. They hold *even under* `--dangerously-skip-permissions`.
- ✍️ **An ownership review** that makes you genuinely *understand* AI-written code before you sign your name to it.
- 🧪 **Requirements-first testing** that writes a full coverage plan straight from your Jira ticket, before trusting a single line of code.

Stack-agnostic: Ringmaster fingerprints your language, framework, and conventions and conforms to them. Nothing to configure.

---

## Install

```
/plugin marketplace add raghatatepiyush/ringmaster
/plugin install ringmaster@ringmaster
```

The only dependency is Python 3 (see [Requirements](#requirements)). Your proof the hard rails are armed is the banner at the start of every session:

> 🎪 Ringmaster is active … Hard safety rails armed (hook running on Windows, Python 3.14).

---

## Quick start

You don't need to learn any commands — just describe what you want, the way you'd tell a senior engineer:

> "Add a dark-mode toggle to the settings page and cover it with tests."
> "Fix the bug where expired sessions still work."

Ringmaster wakes up on its own, restates the goal, shows a short plan, waits for your **"go,"** then builds — testing, security-checking, and staging as it goes. When you *do* want to call a specific act by name, here's the cheat-sheet:

| Say | What happens |
| :-- | :-- |
| `/ringmaster:orchestrator` | summon the orchestrator explicitly |
| `/ringmaster:test-architect` | go straight to writing, fixing, or pruning tests **for existing code** |
| `/ringmaster:scenarios-from-requirements` | write requirements-first test **scenarios** from a Jira/Confluence ticket — *before* any code (or just say *"write test scenarios for PROJ-142"*) |
| `/ringmaster:pickup` | resume unfinished work from a previous session — even a teammate's |
| `/ringmaster:ownership-review` | run just the ownership review on a branch/PR you must sign off on |
| `"go deep"` | a one-off exhaustive pass: wider tests, an explicit security sweep, harder review |

---

## Meet the troupe

Every part of Ringmaster has **one clear job**. Here's who does what — and why you'd want them.

> **A quick note on the labels.** A **skill** is a full playbook Ringmaster reasons with (it usually starts itself; you can also type its `/name`). A **command** is a shortcut you type with a `/`. An **agent** is a helper that runs in its own clean context for a single job, then reports back — you never type these; Ringmaster dispatches them.

| Act | What it does — and why you'd want it | Reach it by |
| :-- | :-- | :-- |
| 🎩 **Orchestrator** <br>*the ringmaster* | Turns a plain-English request into finished, staged work: frames the real goal, plans behind your approval, routes each step to the right specialist, and walks the result through tests → security → review → staging. **One conversation runs your whole SDLC — and nothing ships without your say-so.** | `skill` · auto-starts, or `/ringmaster:orchestrator` |
| 🧪 **Test Architect** | Writes and maintains tests in whatever language & framework you use — risk-first, red→green, asserting *behavior* so they survive refactors — and prunes dead ones. Never edits production code to force a green. **Every change ships with tests that actually bite, not coverage theater.** | `skill` · auto, or `/ringmaster:test-architect` |
| 🎟️ **Scenarios from Requirements** | The **requirements-first** sibling of the Test Architect. Reads a Jira/Confluence ticket (your source of truth), grills it for gaps, and writes brutally thorough, fully-traceable **scenarios** — plus a self-contained HTML/CSV coverage report — *before* any code exists. **Test Architect goes `code → tests`; this goes `requirement → scenarios → tests`.** Built for BAs & Test Analysts who trust the spec and distrust the code. | `skill` · `/ringmaster:scenarios-from-requirements` |
| 🔒 **Security Gate** | Before a risky change leaves your machine, a fresh, paranoid reviewer reads the diff for secrets, injection, broken authorization, and crypto misuse — and **blocks the hand-off** on anything critical. **Catches the one bug everyone else was too close to see.** | `agent` · auto-dispatched before staging |
| 🔍 **Code Review** | Reviews your change along **two axes at once, run as parallel reviewers that never see each other's context** — *Spec* (did it build what the ticket asked, no more, no less?) and *Standards* (is the code correct, safe on its edges, and clean?). Aggregates both and records the `clean` quality gate. **Two lenses kept uncontaminated — so scope creep and sloppy code both get caught.** | `skill` · auto in stage 3, or `/ringmaster:code-review` |
| ✍️ **Ownership Review** | A short quiz built from your **actual diff** that proves *you* understand the change before you sign off — you answer first, it teaches on every miss, and flags where you were *confidently wrong*. Records an auditable sign-off a `Stop` hook enforces. **Turns "the AI wrote it" into "I understand it and I own it."** | `skill` · `/ringmaster:ownership-review` |
| 🗂️ **Ledger + resume** | A tiny team board (the `.ringmaster/` folder) tracking every task as **pending · in-progress · done · blocked**, each with an owner and its dependencies. **Any session — or a teammate — resumes exactly where the last one stopped.** | `command` · `/ringmaster:pickup` |

### Also under the tent

A few things the ringmaster does on every run, without being asked:

| | |
| :-- | :-- |
| 🧭 **Routing with fallbacks** | For each step it dispatches the best specialist plugin — `frontend-design`, `code-review`, `playwright`, `supabase`, `stripe`, `vercel`, `github`, `context7`, `superpowers`, … — and falls back to a competent built-in when one isn't installed, so **work never blocks** |
| 🎚️ **Token discipline** | Each task is right-sized to the cheapest model/effort that still clears the bar; work that fails the quality gate auto-escalates back to the premium model — **quality never drops to save tokens** |
| 👥 **Real delegation** | For big jobs it hands bounded lanes to engineer → junior subagents with complete context hand-offs, behind a six-criterion **A-grade quality gate** a `Stop` hook actually enforces |
| 🗣️ **Plain-language output** | Every result is pretty-printed and explained so a newcomer understands what changed and why it's safer now — **the report *is* the deliverable, not an afterthought** |

---

## The safety net (rails enforced in code, not just asked for)

A `PreToolUse` hook inspects every Bash command, every file write, and **every MCP tool call** *before it runs* — and a hook's `deny` is evaluated before Claude Code's own permission system, so the hard rails hold **even under `--dangerously-skip-permissions`**:

| Rail | Enforcement |
| :-- | :-- |
| 🚦 Never commits, pushes, merges, rebases, or publishes a release/package | **deny** — Ringmaster stages with `git add <paths>`; *you* own the commit and the decision to ship |
| 🚦 Never runs anything against **PRODUCTION** — no tests, deploys, or data mutations | **deny** — work stays in DEV/UAT (safe); shared PREPROD asks first |
| 🚦 Never *ships* on its own — opening/merging a PR, a preview deploy | **ask** — pauses for your explicit confirmation, on Bash and the MCP tools alike |
| 🚦 Won't write a live secret to disk or touch `.git/` internals | **deny** — and a production env / key / credentials file pauses for you |
| 🚦 Sees through wrapped runners | `make deploy`, `npm run ship`, `bash deploy.sh` are resolved and re-checked — one indirection can't smuggle a push or a prod hit past the rails |

The hook is **allow-by-default** — normal dev (`npm test`, `git status`, `git add`, local servers) runs untouched, and it will never brick a tool. Every rail is proven by a **191-case adversarial battery** running in CI on Linux, Windows, and macOS across Python 3.9 → 3.14, on every push. The full threat model — what the hook catches, what it deliberately allows, and the honest edges — lives in **[docs/hardening.md](docs/hardening.md)**.

---

## Prove it yourself

Ringmaster's guarantees aren't marketing copy — they're an adversarial test suite you can run in seconds (standard-library Python, nothing to install). The CI badge above runs all of it on every push across **3 OSes × Python 3.9 → 3.14**; to reproduce it locally, from the plugin directory:

```bash
# use python3 — or `py` on Windows, where `python` may be the Microsoft Store stub
python3 hooks/test_guardrails.py                                        # the safety rails
python3 hooks/test_ledger.py                                            # the resumable team board
python3 hooks/test_routing.py                                           # the A-grade quality gate
python3 hooks/test_stop_gate.py                                         # the Stop-hook enforcement
python3 skills/scenarios-from-requirements/assets/test_scenario_report.py  # the requirements-first report generator
```

| The promise | Proven by | Result |
| :-- | :-- | :--: |
| No commit, push, merge, release, prod-hit, live-secret write, or autonomous PR/deploy ever slips through — **even under `--dangerously-skip-permissions`** | `test_guardrails.py` | **191 / 191** |
| The team board (pending · in-progress · done · blocked, with owners + deps) stays correct, so any session — or teammate — resumes cleanly | `test_ledger.py` | **27 / 27** |
| The six-criterion A-grade quality gate is enforced exactly as specified | `test_routing.py` | **6 / 6 criteria** |
| The Stop hook blocks finishing on a failing gate or an unsigned ownership sign-off — and never traps a legitimate pause | `test_stop_gate.py` | **22 / 22** |
| The requirements-first coverage report escapes untrusted ticket text (XSS), neutralizes CSV formula injection, and flags any requirement missing failure-path coverage | `test_scenario_report.py` | **34 / 34** |

That's **274 adversarial cases** across five batteries — plus end-to-end CI smokes for the launcher shim, the `deny / ask / allow` stdin path, and the ledger CLI. If any rail regressed, CI goes red before the change could ever reach you.

---

## How the show runs

Every substantial task follows the same pipeline — and it always halts for your approval before building anything real:

**Frame & classify → plan (🛑 halt for your "go") → route & build → tests → 🔒 Security Gate → 🔍 code review → ✍️ ownership sign-off → docs → 📦 stage & report.**

Under the hood, each skill's `SKILL.md` is a lean router; the depth lives in reference files loaded only when their moment comes (*progressive disclosure*), so the system stays token-light on every run.

<details>
<summary>Repository layout</summary>

```
ringmaster/
├── .claude-plugin/            # plugin + marketplace manifests
├── .github/workflows/ci.yml   # batteries + launcher smoke: 3 OSes × Python 3.9–3.14
├── commands/pickup.md         # /ringmaster:pickup — resume from the ledger
├── hooks/
│   ├── hooks.json             # registers the gates: Bash + Write/Edit + all-MCP + Stop
│   ├── guardrails.py          # PreToolUse policy (deny/ask); resolves wrapped runners
│   ├── stop_gate.py           # Stop hook: the A-grade gate + ownership sign-off teeth
│   ├── session_doctrine.py    # SessionStart banner + stack hint + resume hint
│   ├── ledger.py              # board / next-task / gate / share helpers + CLI
│   ├── routing.py             # Task-Profile + A-grade-gate helpers
│   └── test_*.py              # the batteries (guardrails 191 · ledger 27 · routing · stop-gate 22)
├── skills/
│   ├── orchestrator/                # the Orchestrator — the ringmaster (thin router + references/)
│   ├── code-review/                 # the Code Review — two-axis (Spec + Standards) parallel review
│   ├── ownership-review/            # the Ownership Review — comprehension quiz + auditable sign-off
│   ├── test-architect/              # the Test Architect — tests for existing code (risk-first, red→green)
│   └── scenarios-from-requirements/ # requirements-first scenarios from a Jira/spec (before code) + 34-case report battery
├── agents/
│   ├── security-gate.md       # the Security Gate — adversarial security reviewer
│   ├── code-reviewer.md       # the Code Reviewer — one axis per dispatch (Spec | Standards)
│   └── comprehension.md       # the Comprehension examiner (the Ownership Review's brain)
├── docs/hardening.md          # threat model + CI proof
└── .ringmaster/                # (runtime, per-project) the ledger — self-ignored
```

</details>

---

## Works alongside your other plugins

Ringmaster **directs** the official specialists rather than replacing them: install any of `frontend-design`, `code-review`, `playwright`, `supabase`, `stripe`, `vercel`, `github`, `context7`, `superpowers`, … and Ringmaster routes to them automatically; a needed-but-missing tool is a quick question ("want me to wire it up?"), never a silent downgrade. It stacks cleanly with Anthropic's `security-guidance` hook (both fire; the strictest decision wins) — and it is complete and safe with **zero** external plugins installed. The verified capability map lives in [`skills/orchestrator/references/routing-and-plugins.md`](skills/orchestrator/references/routing-and-plugins.md).

---

## Requirements

- **Claude Code** with plugin support.
- **Python 3**, discoverable as `python3`, `python`, or `py`. The hooks are tiny standard-library-only scripts launched through a POSIX `sh` shim that **probes each candidate by actually running it** — so a broken or fake interpreter (like the Microsoft Store's `python` stubs on stock Windows 11) is skipped, and any real install is found, including a `py`-launcher-only setup.
- **macOS & Linux:** works out of the box (`sh` is native; `python3` is almost always present). **Windows:** fully supported — Claude Code runs hooks through the Git-Bash `sh` bundled with Git for Windows; any Python install (python.org, `winget install Python.Python.3`, or just the `py` launcher) arms the rails.

No banner at session start means the rails aren't armed and only the behavioral layer is live — install/repair Python and reload. That honesty is deliberate: you always know which layer you're standing on.

---

## Learn more

- **[docs/hardening.md](docs/hardening.md)** — the threat model: what the hook catches, what it deliberately allows, and how CI proves it on every push.
- **[CHANGELOG.md](CHANGELOG.md)** — version history. **Latest:** the bundled **Code Review** skill — a two-axis (Spec + Standards) review run as parallel fresh-context sub-agents that records the `clean` quality gate the Stop hook enforces. Before it: the `scenarios-from-requirements` skill — requirements-first, fully-traceable test scenarios with a self-contained HTML/CSV coverage report.
- **[skills/orchestrator/references/](skills/orchestrator/references/)** — the full doctrine: routing, playbooks, safety & environments, state & resume, team & delegation, right-sizing, model routing.

---

## License

MIT.
