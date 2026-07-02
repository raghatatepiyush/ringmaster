# Changelog

All notable changes to Conductor. Versions follow [semver](https://semver.org/); the format follows [Keep a Changelog](https://keepachangelog.com/).

## [2.2.1] — 2026-07-03

The submission-readiness release: one real defect fixed, then polish for the community-marketplace review pipeline.

### Fixed

- **The orchestrator skill's YAML frontmatter was invalid, so the skill loaded with no metadata.** The description contained an unquoted `rails: never …` — a colon followed by a space inside a plain YAML scalar, which YAML forbids — so the whole frontmatter failed to parse and Claude Code loaded the skill with every field silently dropped, disabling description-based auto-triggering (v2.2.0 shipped this). The description is now quoted; `claude plugin validate --strict` passes in both marketplace mode and plugin mode. The regression was invisible to repo-root validation (which only checks `marketplace.json`) and is now guarded in CI (below).
- **Bundled-helper paths now resolve from an installed plugin.** `/conductor:pickup`, the orchestrator skill, and the reference docs invoked `python hooks/ledger.py …` relative to the repo root — correct in a checkout of this repo, wrong for an installed plugin (the helper lives under the plugin's install directory). Skill and command content now uses `${CLAUDE_PLUGIN_ROOT}` (substituted inline by Claude Code); the reference files, which are read raw, spell out how to locate `<plugin-root>` from their own path.

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

- **`.claude-plugin/marketplace.json`** — Conductor is now installable in two lines: `/plugin marketplace add raghatatepiyush/conductor`, then `/plugin install conductor@conductor`.
- **CI: launcher-shim smoke on all three OSes.** It extracts the *real* registered command from `hooks.json` (so the test can never drift from what ships) and drives it end-to-end — including a simulated Store-stub trap: fake failing `python3`/`python` executables placed ahead of a working `py` on PATH. The one component the Python batteries couldn't reach is now continuously verified.
- `CHANGELOG.md` (this file) and `docs/hardening.md` — the version history and the threat model moved out of the README, which is now a front page people can actually read.

## [2.1.0]

### Added

- **The PROD rail closes the kube short-flag gap.** `kubectl` / `helm` / `oc` `-n prod` is denied exactly like the long-form `--namespace prod` — scoped to those three binaries, so an unrelated `grep -n production` or `tail -n 100 prod.log` stays free. The adversarial battery grew to **186 cases**.

## [2.0.0]

### Added

- **A shared team board.** The `.conductor/` ledger gained an owner per task (`assignee`: `principal` / `engineer:<lane>` / `junior:<lane>` / a specialist) and explicit dependencies, across four columns (pending · in-progress · done · blocked). Render it with `python3 hooks/ledger.py board .conductor/state.json`. Two workers can never hold the same task.
- **Principal → engineer → junior delegation.** Big work decomposes top-down into bounded lanes with complete context hand-offs, kept a shallow 2–3 levels deep; the principal owns the integration seams.
- **The A-grade gate got teeth.** A `Stop` hook refuses to end a turn while an in-progress task is on record as failing its six-criterion gate (correct · secure · clean · complete · documented · explained). Conservative by design: an absent gate never traps; `waitingOnHuman` always allows a legitimate pause; it fails open on a missing/corrupt ledger.
- **File-write rails.** `Write`/`Edit`/`MultiEdit`/`NotebookEdit` are gated: writing a live credential (real `sk_live_`/`AKIA…`/`ghp_` keys, PRIVATE KEY blocks) or into `.git/` internals is **denied**; a production env / key / credentials file **asks** first.
- **Wrapped-runner resolution.** The hook looks inside `make` targets, `npm`/`yarn`/`pnpm` scripts, and invoked shell scripts and re-applies the same policy to the resolved body — a `git push` or prod hit one indirection deep (`make deploy`, `npm run ship`) is still caught. VCS coverage broadened to `git filter-branch`, `jj`, `hg`, and `svn`.

## [1.3.0]

### Added

- **Continuity & resume.** The `.conductor/` ledger (`state.json` + human-readable `PROGRESS.md`), self-ignored by default for zero git footprint; say `pickup` (or `/conductor:pickup`) in any fresh session to reconcile against the repo and continue the highest-priority task.
- **Right-sizing.** Every task gets a Task Profile (lane · model · effort · gate). Triage tunes ceremony, never safety: any change to production behavior always gets tests + the Security Gate.
- **Model & effort routing.** Mechanically-trivial lanes downshift to a cheaper model behind the **model-independent** A-grade gate; work that fails the gate auto-escalates back to the premium model. Tokens saved on the easy parts; the bar held constant.
- **Compaction on your terms.** `/compact` is recommended only at safe checkpoints, with the ledger saved first so nothing is lost.
