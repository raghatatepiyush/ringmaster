# Changelog

All notable changes to Ringmaster. Versions follow [semver](https://semver.org/); the format follows [Keep a Changelog](https://keepachangelog.com/).

## [2.6.0] — 2026-07-09

**A bundled two-axis Code Review — the review layer Ringmaster always assumed but never shipped.** The orchestrator and the Ownership Review both route through a "code-review" step, and `gate.clean` has always been one of the six A-grade criteria — yet the only built-in version was a prose two-stage block. This release makes it a real, always-present specialist, adopting the parallel-sub-agent technique surfaced by a Ringside market scan (`mattpocock/skills`) and fitting it to Ringmaster's own architecture (a skill orchestrates; a fresh-context agent does the isolated work).

### Added

- **A new bundled `code-review` skill** (`skills/code-review/`, invoked as `/ringmaster:code-review`) and its **`code-reviewer` agent** (`agents/code-reviewer.md`). The skill pins the diff and the plan/spec, risk-tiers the change, then dispatches the reviewer **twice in parallel, in fresh contexts** — once on the **Spec** axis (does the change match the plan/ticket, no more, no less?) and once on the **Standards** axis (is the code correct, safe on its edges, and conventional?) — so the two lenses never pollute each other. It aggregates both into the house two-stage report and records the **`gate.clean`** criterion the Stop hook already enforces. It reuses the Security Gate's severity scale (any 🔴 on either axis blocks hand-off), inherits the read-only / never-fix / never-commit rails, and degrades honestly when sub-agents or a ledger aren't available (single-context pass; review real but not hook-enforced).

### Changed

- **`code-review` is now the fifth always-present bundled specialist** (Test Architect · Scenarios · Security Gate · **Code Review** · Ownership Review). The orchestrator's routing table and stage-3 review step now route to the bundled skill by default; the external `code-review` plugin becomes an optional richer pass Ringmaster prefers when installed. `references/routing-and-plugins.md` (map row + the always-present list, now **five**), `references/output-style.md` (the two-stage block re-titled as the skill's report format, its stages labelled Spec / Standards), `references/workflow-playbooks.md` (the review step now routes to the bundled skill, not a "fallback" pass), and `skills/ownership-review/SKILL.md` (its Stage-1 detection reference) were updated to match.
- **No Python changed.** `gate.clean` was already a universal A-grade criterion (`hooks/ledger.py`, `hooks/stop_gate.py`, `hooks/routing.py`), so this graft is documentation + skill/agent definitions only; every existing hook battery is untouched.
- **Docs accuracy.** `docs/hardening.md` now enumerates all five batteries (guardrails · ledger · routing · Stop-gate · report-generator — **274 cases**) in both its CI description and its local-run snippet; `.claude-plugin/marketplace.json`'s description now names the code-review and ownership layers.

## [2.5.0] — 2026-07-08

**`scenarios-from-requirements` — requirements-first test scenarios.** A new standalone skill for the people who own product quality (BAs, Test Analysts): it trusts the *requirement* and distrusts the *code*. It's the sibling of the Test Architect — where the Test Architect goes *code → tests*, this goes *requirement → scenarios → tests*.

### Added

- **A new `scenarios-from-requirements` skill** (`skills/scenarios-from-requirements/`, invoked as `/ringmaster:scenarios-from-requirements`), the requirements-first sibling of the Test Architect. It reads a Jira/Confluence (or Trello/Linear/Azure DevOps/GitHub Issues) ticket through a connection-agnostic, read-only adapter (Atlassian MCP → REST token → manual paste), **interrogates it for genuine gaps** with grounded, YAGNI-guarded questions, then writes brutally thorough, fully-traceable test **scenarios** (edge cases included) *before* any test code — handing the confirmed scenarios to the Test Architect for the write→run phases. Its scenario brain runs on three principles (grounding — *YAGNI generalized* — · SRP · AHA/DAMP), honest about pedigree: grounding is the one genuinely requirements-first principle, while SRP and AHA/DAMP are the Test Architect's craft restated for scenarios; requirement→scenario traceability is enforced by the schema, and it deliberately rejects the principles that don't fit requirements-first design. Full playbook in the skill's `references/requirements-first-scenarios.md`.
- **A tested HTML + CSV coverage report generator** (`skills/scenarios-from-requirements/assets/scenario_report.py`, stdlib-only) that renders a self-contained, theme-aware HTML report and a re-importable requirement→scenario→coverage CSV — HTML-escaping untrusted ticket text, neutralizing CSV formula injection, and flagging any requirement missing failure-path coverage as **thin**. Ships with a **34-case battery** (`test_scenario_report.py`) and cleared the bundled Security Gate before staging.

## [2.4.0] — 2026-07-05

**The rename to Ringmaster.** The plugin's marketplace `name` collided with an existing community plugin of the same former name, so submissions showed *Published* but never synced into `marketplace.json`. Renaming to the unique, on-theme **`ringmaster`** — the one who runs the whole show and cues each act — resolves the collision: same tool, same rails, new name, verified clear in the community marketplace.

### Changed

- **The plugin identity is now `ringmaster`.** `.claude-plugin/plugin.json` and `marketplace.json` use `name: ringmaster` / `displayName: Ringmaster`; every command, skill, and agent is now namespaced `ringmaster:*` (e.g. `/ringmaster:orchestrator`, `/ringmaster:pickup`, the bundled `ringmaster:security-gate` and `ringmaster:comprehension` agents); the per-project working ledger lives in `.ringmaster/`; `homepage`/`repository` point at `raghatatepiyush/ringmaster`. The voice moves with the name — the old orchestra metaphor becomes the circus *ringmaster* who directs the acts and keeps the show on cue.
- **No behavioral change.** A token-scoped rename touched only identifiers, paths, brand text, and metaphor prose. Every safety rail is behavior-identical: the guardrails, ledger, routing, and stop-gate batteries all pass, and `claude plugin validate --strict` passes in both marketplace and plugin modes.

## [2.3.0] — 2026-07-05

**The ownership review** — the pass that turns *"the AI wrote it"* into *"I understand it and I take 100% responsibility for it."* This is the missing gate for the AI era: when Claude writes the code, the old road to understanding (writing it yourself) is gone, and a developer can ship a diff they've only skimmed.

### Added

- **A bundled Ownership Review skill + Comprehension agent.** Where the Security Gate and `code-review` ask *is the code correct and safe?*, this new layer asks the harder question: *does the human about to own this change actually understand it?* The `comprehension` agent reads the **real diff**, risk-tiers it, and generates **grounded, answer-first questions** across five levels (architectural · code · functional · business · test); the `ownership-review` skill conducts the quiz in the main thread, teaches every miss in plain language anchored to `file:line`, and **calibrates the developer's stated confidence against how they actually did** — surfacing the *sure-and-wrong* blind spots that cause 2am incidents. It reuses detection (never rebuilds it), is risk-tiered so a trivial change gets no quiz, and honors an **anti-hallucination contract** (it may only assert answers grounded in the diff/evidence — never a confidently-wrong "correct answer" about your own code). Output is an **auditable Ownership Sign-off Record** with a draft-and-paste (or Atlassian-MCP) evidence trail.
- **The ownership sign-off got teeth — a conditional `gate.owned` in the Stop hook.** A seventh gate flag on a *different axis* from the six A-grade criteria (the human's understanding, not the code's quality). It is **conditional by design**: written only by the ownership review, it never traps trivial / test / docs work, and — composing with `waitingOnHuman` — it blocks finishing only on the one dishonest pattern of marking an *unowned* change done. The six universal A-grade criteria (`routing.AGRADE_CRITERIA`) are deliberately **unchanged**, so no existing task, lane, or test is affected.
- **`hooks/test_stop_gate.py` — a 22-case battery for the Stop gate**, now run in CI across three OSes and Python 3.9 → 3.14. `stop_gate.py` was refactored to expose a pure, IO-free decision function (`evaluate`), so both axes and every conservative escape hatch (`stop_hook_active`, `waitingOnHuman`, absent gate, non-`in_progress` tasks) are directly unit-tested; the inline CI Stop-gate smoke now also drives the ownership axis end to end over stdin.

### Changed

- The orchestrator's **stage-3 gate** now includes an **ownership sign-off** step for any change a human must own. `references/routing-and-plugins.md` now lists **three** always-present bundled specialists (Test Architect · Security Gate · **Ownership Review**); `references/state-and-resume.md` documents the conditional `gate.owned` semantics; the README gains the ownership-review capability and the updated pipeline line.

## [2.2.1] — 2026-07-03

The submission-readiness release: one real defect fixed, then polish for the community-marketplace review pipeline.

### Fixed

- **The orchestrator skill's YAML frontmatter was invalid, so the skill loaded with no metadata.** The description contained an unquoted `rails: never …` — a colon followed by a space inside a plain YAML scalar, which YAML forbids — so the whole frontmatter failed to parse and Claude Code loaded the skill with every field silently dropped, disabling description-based auto-triggering (v2.2.0 shipped this). The description is now quoted; `claude plugin validate --strict` passes in both marketplace mode and plugin mode. The regression was invisible to repo-root validation (which only checks `marketplace.json`) and is now guarded in CI (below).
- **Bundled-helper paths now resolve from an installed plugin.** `/ringmaster:pickup`, the orchestrator skill, and the reference docs invoked `python hooks/ledger.py …` relative to the repo root — correct in a checkout of this repo, wrong for an installed plugin (the helper lives under the plugin's install directory). Skill and command content now uses `${CLAUDE_PLUGIN_ROOT}` (substituted inline by Claude Code); the reference files, which are read raw, spell out how to locate `<plugin-root>` from their own path.

### Added

- **CI: `claude plugin validate --strict`, both modes** — marketplace mode at the repo root and plugin mode on a marketplace-less copy (the mode that actually parses skill/agent/command frontmatter and `hooks/hooks.json`). This is the same check Anthropic's plugin-review pipeline runs on every submission, so a manifest or frontmatter regression can no longer ship.

### Changed

- `plugin.json`: `description` cut from ~1,600 characters to three sentences (the field is UI-facing; the depth lives in the README), added `displayName`, trimmed `keywords` to ten, fuller `author`. `.claude-plugin/marketplace.json`: added the top-level marketplace `description` — previously the one `--strict` warning.
- Docs: the guardrails battery count is **191** everywhere it's quoted (the five ReDoS perf-guard cases added after v2.2.0 hadn't been reflected in the README and `docs/hardening.md` — `python hooks/test_guardrails.py` is the source of truth).

## [2.2.0] — 2026-07-02

The "arms everywhere, installable by anyone" release.

### Fixed

- **The hook launcher now probes each interpreter candidate by *executing* it** (`"$c" -c pass </dev/null`) instead of merely checking it exists on PATH. Stock Windows 11 ships Microsoft-Store stub `python`/`python3` aliases that exist on PATH but only print an error and exit — the old `command -v` probe exec'd the stub, and every hard rail, the Stop gate, and the SessionStart banner went **silently dark**, even on machines with real Python installed via the `py` launcher. The shim now skips anything that doesn't actually run and finds the working interpreter behind it. Found by dogfooding on a stock Windows 11 machine; now guarded by a dedicated CI smoke (below).
- `plugin.json` `homepage`/`repository` pointed at a repository that doesn't exist; both now point at the real repo.

### Added

- **`.claude-plugin/marketplace.json`** — Ringmaster is now installable in two lines: `/plugin marketplace add raghatatepiyush/ringmaster`, then `/plugin install ringmaster@ringmaster`.
- **CI: launcher-shim smoke on all three OSes.** It extracts the *real* registered command from `hooks.json` (so the test can never drift from what ships) and drives it end-to-end — including a simulated Store-stub trap: fake failing `python3`/`python` executables placed ahead of a working `py` on PATH. The one component the Python batteries couldn't reach is now continuously verified.
- `CHANGELOG.md` (this file) and `docs/hardening.md` — the version history and the threat model moved out of the README, which is now a front page people can actually read.

## [2.1.0]

### Added

- **The PROD rail closes the kube short-flag gap.** `kubectl` / `helm` / `oc` `-n prod` is denied exactly like the long-form `--namespace prod` — scoped to those three binaries, so an unrelated `grep -n production` or `tail -n 100 prod.log` stays free. The adversarial battery grew to **186 cases**.

## [2.0.0]

### Added

- **A shared team board.** The `.ringmaster/` ledger gained an owner per task (`assignee`: `principal` / `engineer:<lane>` / `junior:<lane>` / a specialist) and explicit dependencies, across four columns (pending · in-progress · done · blocked). Render it with `python3 hooks/ledger.py board .ringmaster/state.json`. Two workers can never hold the same task.
- **Principal → engineer → junior delegation.** Big work decomposes top-down into bounded lanes with complete context hand-offs, kept a shallow 2–3 levels deep; the principal owns the integration seams.
- **The A-grade gate got teeth.** A `Stop` hook refuses to end a turn while an in-progress task is on record as failing its six-criterion gate (correct · secure · clean · complete · documented · explained). Conservative by design: an absent gate never traps; `waitingOnHuman` always allows a legitimate pause; it fails open on a missing/corrupt ledger.
- **File-write rails.** `Write`/`Edit`/`MultiEdit`/`NotebookEdit` are gated: writing a live credential (real `sk_live_`/`AKIA…`/`ghp_` keys, PRIVATE KEY blocks) or into `.git/` internals is **denied**; a production env / key / credentials file **asks** first.
- **Wrapped-runner resolution.** The hook looks inside `make` targets, `npm`/`yarn`/`pnpm` scripts, and invoked shell scripts and re-applies the same policy to the resolved body — a `git push` or prod hit one indirection deep (`make deploy`, `npm run ship`) is still caught. VCS coverage broadened to `git filter-branch`, `jj`, `hg`, and `svn`.

## [1.3.0]

### Added

- **Continuity & resume.** The `.ringmaster/` ledger (`state.json` + human-readable `PROGRESS.md`), self-ignored by default for zero git footprint; say `pickup` (or `/ringmaster:pickup`) in any fresh session to reconcile against the repo and continue the highest-priority task.
- **Right-sizing.** Every task gets a Task Profile (lane · model · effort · gate). Triage tunes ceremony, never safety: any change to production behavior always gets tests + the Security Gate.
- **Model & effort routing.** Mechanically-trivial lanes downshift to a cheaper model behind the **model-independent** A-grade gate; work that fails the gate auto-escalates back to the premium model. Tokens saved on the easy parts; the bar held constant.
- **Compaction on your terms.** `/compact` is recommended only at safe checkpoints, with the ledger saved first so nothing is lost.
