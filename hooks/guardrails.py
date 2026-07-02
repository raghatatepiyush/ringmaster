#!/usr/bin/env python3
"""
Conductor - safety gate (PreToolUse: Bash + Write/Edit/MultiEdit + every `mcp__*`)

This is the hard, deterministic enforcement layer. A PreToolUse `deny` is
evaluated *before* Claude Code's permission system, so it blocks the tool even
under `--dangerously-skip-permissions`. A hook can only tighten, never loosen.
That is what lets these rails hold "even if the user allows it by mistake".

Two decision strengths are used:
  - `deny` : a hard wall (irreversible / human-owned / production). Cannot be
             waved through, even under skip-permissions.
  - `ask`  : blocked *autonomously*, but allowed when the human explicitly
             confirms at the prompt. This is how "never on its own, but do it
             when I say so" is expressed for safe/reversible ship actions.

Policy (see classify() / classify_tool() for the single source of truth):
  1. DENY any operation that writes git history or publishes a release/package:
       - git: commit, push, merge, rebase, cherry-pick, revert, am.
       - forge release creation: `gh release create`, `glab release create`.
       - package/release tooling: `npm/pnpm version <bump>`, `npm/pnpm/yarn/bun
         publish`, `cargo publish/release`, `poetry publish`, `twine upload`,
         `gem push`, `mvn deploy`/`release:*`, `gradle publish`,
         `dotnet nuget push`, `release-it`/`standard-version`/`semantic-release`,
         `changeset publish`. A non-mutating `--dry-run`, and an
         `npm version --no-git-tag-version` (which does not touch git), are
         deliberately exempted.
     The human owns the commit, the review, and the decision to ship.
  2. DENY any command that targets a PRODUCTION environment
     (prod / production / prd / live) - via env var, CLI flag, deploy target,
     a prod-looking host/URL, a bare `--prod` switch, or a high-signal
     `deploy/release/migrate/...-prod` compound in a script/target/binary name
     (`make deploy-prod`, `npm run deploy:prod`, `./deploy-production.sh`).
     Tests and changes never touch prod. This also catches `vercel --prod`.
  3. ASK (human confirms) for the *ship-on-command* actions - blocked when the
     agent reaches for them on its own, allowed when the human says so:
       - opening / merging a pull request: `gh pr create|merge`,
         `glab mr create|merge`, and the GitHub-MCP equivalents
         (create_pull_request / merge_pull_request / push_files / file writes),
         which the Bash hook cannot see on its own.
       - a non-production deploy: `vercel deploy` (preview/dev), and the
         Vercel-MCP deploy tool when its target is not production.
  4. ASK (human confirms) for commands that target a shared PRE-PROD / STAGING
     environment - others depend on it, so a human signs off first.
  5. Otherwise stay out of the way: exit 0 with no JSON, deferring to Claude
     Code's normal permission flow. DEV / UAT / local work is unaffected.

Design choice: false positives (asking about something safe) are a minor
nuisance; false negatives (letting a commit, a prod hit, or an autonomous PR /
deploy through) are unacceptable. So matching errs toward catching. On ANY
internal error we exit 0 (never brick a tool) - the orchestrator skill + session
doctrine provide defense-in-depth above this.

This module is import-safe: classify() and classify_tool() are pure functions
with no I/O, so the bundled test battery (hooks/test_guardrails.py) can exercise
the full policy.
"""

import json
import re
import sys
from typing import Optional, Tuple

Decision = Tuple[str, str, str]  # (permissionDecision, reason, human_msg)


# --- Rule 1a: git operations that write history -------------------------------
# Matches `git <global flags>* <verb>` so it catches `git -C path commit`,
# `git -c k=v commit`, `git commit -m ...`, and the verb appearing inside a
# chained or nested command (e.g. `git add . && git commit`, `bash -c "git push"`).
# The trailing (?![\w-]) keeps a real verb matching (`git merge feature`) while NOT
# tripping on read-only plumbing that merely *starts* with it — `git merge-base`,
# `git merge-tree`, `git commit-tree` are not history writes and must stay allowed.
GIT_WRITE = re.compile(
    r"\bgit\s+(?:-[A-Za-z]\S*\s+|--\S+\s+|-C\s+\S+\s+|-c\s+\S+\s+)*"
    r"(commit|push|merge|rebase|cherry-pick|revert|am|filter-branch)(?![\w-])"
)
# Forge RELEASE creation -> deny (cutting a release ships an artifact). PR/MR
# open+merge is handled separately as an ASK (see FORGE_PR). `git push` is
# already covered by GIT_WRITE, so it is intentionally not duplicated here.
FORGE_RELEASE = re.compile(r"\b(?:gh|glab)\s+release\s+create\b")

# Forge PR / MR open+merge -> ASK (ship-on-command, not autonomous).
FORGE_PR = re.compile(
    r"\b(?:gh\s+pr\s+(?:merge|create)|glab\s+mr\s+(?:merge|create))\b"
)

# Other VCS that write history / ship. git is dominant, but a stack-agnostic
# tool should be honest about the others. The "ship" op is what matters most
# (jj git push / hg push / svn commit), plus their commit verbs.
OTHER_VCS_WRITE = re.compile(
    r"\bjj\s+(?:git\s+push|commit|describe)(?![\w-])"
    r"|\bhg\s+(?:commit|push)(?![\w-])"
    r"|\bbzr\s+(?:commit|push)(?![\w-])"
    r"|\bsvn\s+(?:commit|ci)(?![\w-])"
)

# --- Rule 1b: package / release publish tooling ------------------------------
# Commands that publish a package or cut a release (which writes git history
# and/or ships an artifact). The human owns the decision to ship, so these are
# denied just like a raw `git push`. Exemptions below keep non-mutating forms
# (a dry run; an npm version that does not touch git) allowed.
PUBLISH = re.compile(
    r"(?<![A-Za-z])(?:"
    r"(?:npm|pnpm)\s+version\s+(?:major|minor|patch|premajor|preminor|prepatch|prerelease|from-git|v?\d)"
    r"|(?:npm|pnpm|yarn|bun)\s+publish"
    r"|yarn\s+version(?![\w-])"
    r"|cargo\s+(?:publish|release)"
    r"|poetry\s+publish"
    r"|twine\s+upload"
    r"|gem\s+push"
    r"|mvn\s+(?:deploy|release:(?:prepare|perform))"
    r"|(?:gradle|gradlew|\./gradlew)\s+\S*publish"
    r"|dotnet\s+nuget\s+push"
    r"|(?:release-it|standard-version|commit-and-tag-version|semantic-release)(?![\w-])"
    r"|changesets?\s+publish"
    r")",
    re.IGNORECASE,
)
# A dry run mutates nothing; `--no-git-tag-version` makes `npm version` skip the
# commit/tag. Either present -> the publish op is not actually publishing.
PUBLISH_EXEMPT = re.compile(
    r"(?<![A-Za-z])--(?:dry[-_]?run|no-git(?:-tag-version)?)(?![A-Za-z])",
    re.IGNORECASE,
)


def hits_git_write(cmd: str) -> str:
    """Return the offending verb/op if the command writes history / publishes."""
    m = GIT_WRITE.search(cmd)
    if m:
        return m.group(1)
    m = FORGE_RELEASE.search(cmd)
    if m:
        return m.group(0).strip()
    if PUBLISH.search(cmd) and not PUBLISH_EXEMPT.search(cmd):
        return "publish/release"
    m = OTHER_VCS_WRITE.search(cmd)
    if m:
        return m.group(0).strip()
    return ""


# --- Rule 3a: non-production deploy (ask) ------------------------------------
# `vercel deploy` / `vc deploy` (preview/dev). A `--prod`/`--production` form is
# caught earlier by the PROD rail (deny), so by the time we reach here a vercel
# deploy is a non-prod one -> ask the human to confirm rather than run it blind.
VERCEL_DEPLOY = re.compile(r"(?<![A-Za-z])(?:vercel|vc)\s+deploy(?![\w-])", re.IGNORECASE)


# --- Rules 2 & 4: environment targeting --------------------------------------
# We only flag an environment *value* attached to a setting: an env-var
# assignment, a recognised CLI flag value, a bare deploy switch, a token inside
# a URL, or a high-signal action+prod compound (see PROD_COMPOUND). Every
# environment word is matched as a BOUNDED token (not surrounded by letters), so
# "production-ready" in prose, a repo named "product", or `grep production`
# never trips the gate.

_ENV_VARS = (
    r"(?:NODE_ENV|APP_ENV|RAILS_ENV|RACK_ENV|ENVIRONMENT|ENV|DJANGO_SETTINGS_MODULE|"
    r"FLASK_ENV|ASPNETCORE_ENVIRONMENT|DEPLOY_ENV|TARGET_ENV|SPRING_PROFILES_ACTIVE)"
)
_FLAGS = (
    r"(?:env|environment|stage|profile|context|project|namespace|target|account|"
    r"to|destination|dest|host)"
)


def _bounded(words, pre_guard: bool = False) -> str:
    """An alternation of words that must stand alone (no surrounding letters).

    pre_guard=True additionally refuses a match preceded by 'pre-' or 'pre_',
    so a hyphenated 'pre-prod' / 'pre-production' is NOT seen as production.
    """
    guard = r"(?<!pre-)(?<!pre_)" if pre_guard else ""
    return r"(?<![A-Za-z])" + guard + r"(?:" + "|".join(words) + r")(?![A-Za-z])"


# Production words. "live"/"prd" only count in the highest-signal contexts
# (env assignment, bare --switch) to avoid matching "live-reload" etc. in URLs.
_PROD_ENV_TOK = _bounded([r"prod(?:uction)?", r"prd", r"live"], pre_guard=True)
_PROD_FU_TOK = _bounded([r"prod(?:uction)?"], pre_guard=True)  # URL / flag-value

# Pre-prod / staging words. Note: "stage" alone is excluded - it is the flag
# NAME in `--stage <value>`, not an environment value; only "staging" counts.
_PREPROD_TOK = _bounded([r"pre[-_]?prod(?:uction)?", r"staging", r"uat[-_]?shared", r"shared[-_]?uat"])


def _context_regex(env_tok: str, fu_tok: str, bare_words=None) -> re.Pattern:
    pats = [
        rf"{_ENV_VARS}\s*=\s*[\"']?[\w./\-]*{env_tok}[\w./\-]*",          # NODE_ENV=production
        rf"--?{_FLAGS}[=\s]+[\"']?[\w.:/\-]*{fu_tok}[\w.:/\-]*",          # --stage prod / --to my-prod
        # URL scheme + host containing a prod token. The scheme run is BOUNDED
        # ({0,15}) and left-anchored by a lookbehind: without both, a long run
        # of [a-z0-9+.-] with no '://' makes the engine retry a greedy match at
        # every offset -> O(N^2) backtracking (a hook-timeout ReDoS). Real URL
        # schemes are <=~8 chars, so 15 keeps every legitimate match.
        rf"(?<![a-z0-9+.\-])[a-z][a-z0-9+.\-]{{0,15}}://[^\s\"']*{fu_tok}[^\s\"']*",  # https://api.prod.acme.com
    ]
    if bare_words:
        # bare deploy switch: --prod / --production / --live, but NOT --prod-preview
        pats.append(rf"--(?:{'|'.join(bare_words)})(?![\w-])")
    return re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)


PROD_RE = _context_regex(_PROD_ENV_TOK, _PROD_FU_TOK, bare_words=[r"prod(?:uction)?", r"prd", r"live"])
PREPROD_RE = _context_regex(_PREPROD_TOK, _PREPROD_TOK)

# High-signal "act on prod" compound: an action verb joined to a prod word by
# '-', '_' or ':' in a target/script/binary name. Catches `make deploy-prod`,
# `npm run deploy:prod`, `./deploy-production.sh`, `rake migrate:prod`,
# `prod-deploy`. The action set is deliberately limited to verbs that mean
# "deploy/operate on an environment" - NOT artifact-producing verbs like
# build/compile/bundle, so `npm run build:prod` (a local production *build*)
# is correctly left alone.
_PROD_ACTION = (
    r"(?:deploy(?:ment)?|release|publish|promote|roll-?out|ship|migrate|"
    r"provision|destroy|tear-?down|roll-?back)"
)
_PROD_WORD = r"(?:prod(?:uction)?|prd|live)"
PROD_COMPOUND = re.compile(
    r"(?<![A-Za-z])(?:"
    rf"{_PROD_ACTION}[-_:]{_PROD_WORD}"
    rf"|{_PROD_WORD}[-_:]{_PROD_ACTION}"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)


# Kube-family short namespace flag. `kubectl -n prod` / `helm -n prod` /
# `oc -n prod` mean exactly what the long `--namespace prod` (already caught)
# means — but `-n` is only an environment selector for *these* tools (elsewhere
# it is grep's line-numbers, etc.), so the short-flag check is scoped to the
# kube-family binaries to stay false-positive-free. The binary and the
# `-n <value>` must sit in the SAME command segment: the [^|&;\n] class refuses
# to cross a pipe / `;` / `&&` / newline, so a chained
# `kubectl get && grep -n production` does NOT trip it. The `[=\s]+` after `-n`
# forces it to be a complete short flag (so `--namespace` / `-name` aren't
# mistaken for it). Mirrors the long-form behavior exactly: prod -> deny,
# shared pre-prod / staging -> ask.
_KUBE_SEG = (
    r"(?<![A-Za-z])(?:kubectl|helm|oc)(?![A-Za-z])"  # a kube-family binary
    r"[^|&;\n]{0,256}?"                               # its args, not crossing a separator
    r"(?<![A-Za-z])-n[=\s]+[\"']?[\w./\-]*"           # a complete `-n <value>` namespace flag
)
# The {0,256} gap is BOUNDED, not open `*?`: an unbounded lazy run makes every
# `oc`/`helm`/`kubectl` token in a separator-free segment launch a scan to the
# segment end looking for a `-n` that isn't there -> O(N^2) across many tokens
# (e.g. `oc oc oc ...`), a hook-timeout ReDoS that fails OPEN. 256 chars is ~2x
# the longest realistic binary-to-`-n` gap, so no real kube command is missed.
_KUBE_NS_PROD = re.compile(_KUBE_SEG + _PROD_FU_TOK + r"[\w./\-]*", re.IGNORECASE)
_KUBE_NS_PREPROD = re.compile(_KUBE_SEG + _PREPROD_TOK + r"[\w./\-]*", re.IGNORECASE)


def targets_prod(cmd: str) -> bool:
    return bool(PROD_RE.search(cmd) or PROD_COMPOUND.search(cmd) or _KUBE_NS_PROD.search(cmd))


def targets_preprod(cmd: str) -> bool:
    return bool(PREPROD_RE.search(cmd) or _KUBE_NS_PREPROD.search(cmd))


# --- The policy (pure, importable, side-effect free) -------------------------

_GIT_WRITE_MSG = (
    "🛑 Conductor rail: no commit / push / merge / release / publish. Work was "
    "staged for you to review and ship yourself."
)
_PROD_MSG = "🛑 Conductor rail: production is off-limits. Re-target DEV / UAT / PREPROD."
_PR_MSG = (
    "⏸ Conductor: opening/merging a PR is yours to confirm — Conductor won't do it on "
    "its own. Approve to proceed, or I'll stage and hand off."
)
_DEPLOY_MSG = (
    "⏸ Conductor: a deploy waits for your go — Conductor won't deploy on its own. "
    "Approve to run this preview/dev deploy. (Production deploys are blocked entirely.)"
)
_PREPROD_MSG = "⏸ Conductor: this hits shared pre-prod/staging. Confirm before running."

_PR_REASON = (
    "Conductor never opens or merges pull requests on its own — that ships code and is "
    "the human's call. This is paused for explicit confirmation: approve it if you "
    "intended this, otherwise Conductor will stage the work with `git add <paths>` and "
    "hand it off."
)
_DEPLOY_REASON = (
    "Conductor never deploys on its own. This is a non-production (preview/dev) deploy "
    "paused for your explicit confirmation — approve to run it. Production deploys are "
    "blocked entirely; run those yourself."
)


def _decide(command: str) -> Optional[Decision]:
    """The deterministic Bash policy for a *literal* command string, or None.

    Pure - no stdin/stdout, no exit. `classify` (below) wraps this with
    wrapped-runner resolution; this function is the rule cascade itself.
    """
    cmd = command or ""
    if not cmd.strip():
        return None

    # Rule 1 - history / release / publish operations (highest priority, deny).
    verb = hits_git_write(cmd)
    if verb:
        if verb == "publish/release":
            reason = (
                "Conductor blocked a package/release publish step. Conductor never "
                "publishes packages or cuts releases in any mode - the human owns the "
                "decision to ship. Stage your work with `git add <paths>` and hand it "
                "off; the person will version, publish, or release it themselves. "
                "(A `--dry-run`, or an `npm version --no-git-tag-version`, is allowed.)"
            )
        else:
            reason = (
                f"Conductor blocked a git operation that writes history "
                f"('{verb}'). Conductor never commits, pushes, merges, or cuts releases "
                f"in any mode - the human owns the commit message, the review, and the "
                f"decision to ship. Stage your work with `git add <paths>` instead and "
                f"hand it off; the person will commit it themselves."
            )
        return ("deny", reason, _GIT_WRITE_MSG)

    # Rule 2 - production targeting (hard deny). Catches `vercel --prod` too.
    if targets_prod(cmd):
        reason = (
            "Conductor blocked a command that appears to target a PRODUCTION "
            "environment (prod / production / live). Conductor never runs tests, "
            "deploys, or mutates anything against production - under any circumstances, "
            "even if it was explicitly approved. Re-point this at DEV, UAT, or PREPROD "
            "and try again."
        )
        return ("deny", reason, _PROD_MSG)

    # Rule 3a - PR / MR open+merge (ask: ship-on-command, never autonomous).
    if FORGE_PR.search(cmd):
        return ("ask", _PR_REASON, _PR_MSG)

    # Rule 3b - non-production deploy (ask: ship-on-command, never autonomous).
    if VERCEL_DEPLOY.search(cmd):
        return ("ask", _DEPLOY_REASON, _DEPLOY_MSG)

    # Rule 4 - shared pre-prod / staging (ask the human first).
    if targets_preprod(cmd):
        reason = (
            "This command appears to target a shared PRE-PROD / STAGING environment. "
            "That tier is allowed, but other people depend on it and this run can "
            "create or mutate data and trip alerts - so a human should confirm before "
            "it runs."
        )
        return ("ask", reason, _PREPROD_MSG)

    # Everything else: not our concern - defer to normal permission flow.
    return None


# --- Wrapped-runner resolution (close the script-indirection gap) ------------
# A bare `make deploy`, `npm run ship`, or `bash deploy.sh` hides its real
# actions from a command-string scan. Best-effort: resolve the runner target to
# its body and re-run the SAME deterministic policy on it, so a push / prod hit /
# publish hidden one indirection deep is still caught. Fail-open on anything
# (missing file, parse trouble) - we only ever ADD a decision, never remove one.

_MAX_BODY = 65536  # never read a pathologically large file into the hook


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(_MAX_BODY)
    except Exception:
        return ""


_NPM_SCRIPT = re.compile(
    r"(?<![A-Za-z])(?:npm|pnpm|bun)\s+run\s+([A-Za-z0-9:_.-]+)"
    r"|(?<![A-Za-z])yarn\s+(?!add\b|remove\b|install\b)([A-Za-z0-9:_.-]+)"
)
_MAKE_TGT = re.compile(r"(?<![A-Za-z])make\s+(?:-\S+\s+)*([A-Za-z0-9:_./-]+)")
_SCRIPT_FILE = re.compile(
    r"(?<![A-Za-z])(?:bash|sh|zsh|source|\.)\s+(\S+\.sh)(?![\w/])"
    r"|(?<![A-Za-z])(\./\S+\.sh)(?![\w/])"
)


def _npm_script_body(name: str) -> str:
    raw = _read_text("package.json")
    if not raw:
        return ""
    try:
        scripts = (json.loads(raw) or {}).get("scripts", {}) or {}
    except Exception:
        return ""
    return scripts.get(name, "") if isinstance(scripts, dict) else ""


def _make_target_body(name: str) -> str:
    for mk in ("Makefile", "makefile", "GNUmakefile"):
        raw = _read_text(mk)
        if not raw:
            continue
        body, capturing = [], False
        for line in raw.splitlines():
            if not capturing:
                if re.match(r"^%s\s*:" % re.escape(name), line):
                    capturing = True
                continue
            if line.startswith("\t") or line.strip() == "":
                body.append(line)
            else:
                break
        if body:
            return "\n".join(body)
    return ""


def _resolve_runner_body(cmd: str) -> str:
    parts = []
    m = _NPM_SCRIPT.search(cmd)
    if m:
        name = m.group(1) or m.group(2)
        if name:
            parts.append(_npm_script_body(name))
    m = _MAKE_TGT.search(cmd)
    if m:
        parts.append(_make_target_body(m.group(1)))
    m = _SCRIPT_FILE.search(cmd)
    if m:
        path = (m.group(1) or m.group(2) or "")
        if path.startswith("./"):
            path = path[2:]
        if path:
            parts.append(_read_text(path))
    return "\n".join(p for p in parts if p)


def classify(command: str) -> Optional[Decision]:
    """Return (decision, reason, human_msg) for a Bash command, or None to allow.

    The single source of truth for the Bash policy and what the test battery
    exercises. It applies the deterministic rules to the literal command; if
    that allows, it resolves any wrapped runner (a make target, an
    npm/yarn/pnpm script, or a shell script invoked here) and re-applies the
    same rules to the resolved body - so a push or a prod hit hidden one
    indirection deep is still caught. The runner read is best-effort and
    fail-open (a missing/unreadable target simply yields no extra finding).
    """
    cmd = command or ""
    if not cmd.strip():
        return None
    direct = _decide(cmd)
    if direct is not None:
        return direct
    body = _resolve_runner_body(cmd)
    if body:
        inner = _decide(body)
        if inner is not None:
            dec, reason, msg = inner
            wrapped = (
                "Conductor looked inside a wrapped runner (a make target, an "
                "npm/yarn/pnpm script, or a shell script this command invokes) and "
                "the resolved body triggers a rail. " + reason
            )
            return (dec, wrapped, msg)
    return None

# --- MCP-tool policy ---------------------------------------------------------
# The Bash hook above cannot see MCP tool calls (they are not Bash commands).
# A GitHub-MCP "create/merge PR", a Vercel-MCP deploy, a Supabase/DB MCP write
# against prod, or a Stripe-MCP live charge would otherwise slip past the rails
# entirely. classify_tool() closes that gap by inspecting the tool name and its
# input directly — and it now runs on EVERY `mcp__*` tool, not just
# github/vercel (the hooks.json matcher is `mcp__.*`). Same two-strength model:
# anything that targets PRODUCTION is `deny`; a ship-on-command action (PR
# write, non-prod deploy) is `ask`. Allow-by-default otherwise, so the flood of
# read-only MCP calls (search, list, get, query-docs) runs untouched.

# GitHub write tools that ship code / open-merge PRs (matched on the tool name,
# lower-cased). Reads (get_*, list_*, search_*) carry no write verb -> allowed.
_GH_WRITE_TOOL = re.compile(
    r"(?:create_pull_request|merge_pull_request|update_pull_request_branch|"
    r"push_files|create_or_update_file|delete_file)"
)
_GH_TOOL_MSG = (
    "⏸ Conductor: that GitHub action writes to the repo (PR / push). Conductor won't do "
    "it on its own — approve to proceed, or I'll stage and hand off."
)
_GH_TOOL_REASON = (
    "Conductor blocked an autonomous GitHub write (open/merge a pull request, or push "
    "code) via an MCP tool — the Bash safety hook can't see MCP calls, so the rail is "
    "enforced here too. These ship code and are yours to confirm: approve if you "
    "intended it, otherwise Conductor stages the work and hands it off."
)


# An environment value of prod/prd/live attached to a recognized target/env key,
# a bare `"prod": true`, or a `--prod` switch inside the input. Deliberately
# key-scoped: we do NOT trip on a bare string value of "production" under an
# arbitrary key (e.g. a Notion/Gmail search query "production roadmap", or a
# calendar event titled "production"), which would false-positive on the large
# read-only surface of general MCP servers. Prod only counts when it's plainly
# an environment *target*. Bounded so "reproduction" / "preprod" don't match.
_PROD_INPUT_KEY = re.compile(
    r'"(?:target|environment|env|stage|namespace|context|profile|account|'
    r'deploy_env|target_env|node_env|app_env|rails_env|rack_env|'
    r'aspnetcore_environment|destination|dest|cluster|region_env)"\s*:\s*'
    r'"[^"]*(?<![A-Za-z])(?:prod(?:uction)?|prd|live)(?![A-Za-z])',
    re.IGNORECASE,
)


def _input_targets_prod(tool_input) -> bool:
    """Best-effort: does this MCP tool input aim at PRODUCTION?

    Key-scoped on purpose (see _PROD_INPUT_KEY) so it catches a real prod target
    without denying benign reads that merely contain the word 'production'.
    """
    try:
        blob = json.dumps(tool_input, default=str)
    except Exception:
        return False
    if _PROD_INPUT_KEY.search(blob):
        return True
    low = blob.lower()
    return bool(re.search(r'"prod"\s*:\s*true', low) or "--prod" in low)


def _input_is_stripe_live(tool_input) -> bool:
    """Best-effort: does this Stripe MCP call run against LIVE mode (real money)?

    Only what's visible in the tool input — the live/test split is usually decided
    by the configured API key the hook can't see, so this is defense-in-depth, not
    a complete guarantee (the behavioral layer enforces test-mode-only too)."""
    try:
        blob = json.dumps(tool_input, default=str).lower()
    except Exception:
        return False
    return bool(
        "sk_live_" in blob
        or "rk_live_" in blob
        or re.search(r'"livemode"\s*:\s*true', blob)
        or re.search(r'"(?:mode|environment|env)"\s*:\s*"live"', blob)
    )


_MCP_PROD_REASON = (
    "Conductor blocked an MCP tool call whose input targets a PRODUCTION environment. "
    "Production is off-limits under any circumstances — even via an MCP specialist "
    "(database, deploy, infra, data). The Bash hook can't see MCP calls, so the prod "
    "rail is enforced here too. Re-point this at DEV / UAT / PREPROD and try again."
)
_VERCEL_PROD_REASON = (
    "Conductor blocked a Vercel PRODUCTION deploy via an MCP tool. Production is "
    "off-limits to Conductor under any circumstances — run a prod deploy yourself. "
    "Target preview/dev instead and I'll proceed on your confirm."
)
_STRIPE_LIVE_MSG = (
    "🛑 Conductor rail: Stripe is in LIVE mode (real charges). Switch to test/sandbox "
    "keys — Conductor never touches live billing."
)
_STRIPE_LIVE_REASON = (
    "Conductor blocked a Stripe MCP call that appears to run in LIVE mode (a live key "
    "or livemode flag). Payments work happens in test/sandbox mode only — never live "
    "keys, never a real charge. Re-run with test-mode keys."
)


def classify_tool(tool_name: str, tool_input) -> Optional[Decision]:
    """Policy for non-Bash (MCP) tools. Pure; returns None to allow.

    Runs on every `mcp__*` tool (the hooks.json matcher is `mcp__.*`). Order
    matters: specialist ship-gates first (so they get their specific message),
    then the universal PROD rail as a catch-all for every other MCP specialist.
    """
    name = (tool_name or "").lower()
    if not name:
        return None
    # Only our concern for MCP tools. Built-in tools (Read, Edit, Bash-handled
    # separately, …) defer to the normal permission flow.
    if not name.startswith("mcp__"):
        return None

    # GitHub MCP writes (PR open/merge, code push, file writes) -> ask.
    if "github" in name and _GH_WRITE_TOOL.search(name):
        return ("ask", _GH_TOOL_REASON, _GH_TOOL_MSG)

    # Vercel MCP deploy: prod -> deny (own message); non-prod (preview/dev) -> ask.
    if "vercel" in name and "deploy" in name:
        if _input_targets_prod(tool_input):
            return ("deny", _VERCEL_PROD_REASON, _PROD_MSG)
        return ("ask", _DEPLOY_REASON, _DEPLOY_MSG)

    # Stripe MCP in LIVE mode -> deny (real money). Test/sandbox -> allowed.
    if "stripe" in name and _input_is_stripe_live(tool_input):
        return ("deny", _STRIPE_LIVE_REASON, _STRIPE_LIVE_MSG)

    # Universal PROD rail: ANY MCP tool whose input targets production -> deny.
    # This is the gap-closer — a Supabase/Postgres/Mongo/infra/data MCP that the
    # github/vercel branches don't know about still cannot touch prod.
    if _input_targets_prod(tool_input):
        return ("deny", _MCP_PROD_REASON, _PROD_MSG)

    return None


# --- Write/Edit-tool policy (close the ungated file-write flank) -------------
# Historically the hook saw only Bash + MCP. But the Write / Edit / MultiEdit /
# NotebookEdit tools can drop a LIVE secret into a file, tamper with git
# internals, or rewrite production config - all entirely unseen by the Bash
# gate. classify_write closes that: DENY putting a live credential on disk or
# writing into .git/; ASK before writing a production env / key / credentials
# file. Allow-by-default otherwise, so ordinary source edits run untouched.
# Same two-strength model as the rest of the hook; same fail-open guarantee.

# High-signal live-credential shapes. Tuned to match a *real* secret, not a
# placeholder: the length/charset floors keep `sk_live_xxx` style stubs out.
_LIVE_SECRET = re.compile(
    r"sk_live_[0-9a-zA-Z]{16,}"
    r"|rk_live_[0-9a-zA-Z]{16,}"
    r"|AKIA[0-9A-Z]{16}"
    r"|ghp_[0-9A-Za-z]{30,}"
    r"|github_pat_[0-9A-Za-z_]{30,}"
    r"|glpat-[0-9A-Za-z_\-]{16,}"
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"
    r"|AIza[0-9A-Za-z_\-]{30,}"
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"
)
# Writing into git internals is never a legitimate autonomous action (the
# `*.sample` hook templates are the one benign exception).
_GIT_INTERNALS_PATH = re.compile(r"(?:^|/)\.git/(?!hooks/[A-Za-z0-9._-]+\.sample$)")
# Production env / key / credential files: sometimes legitimate, but pause first.
_SENSITIVE_PATH = re.compile(
    r"(?:^|/)\.env(?:\.(?:production|prod|live))?$"
    r"|(?:^|/)id_(?:rsa|ed25519|ecdsa|dsa)$"
    r"|\.pem$|\.p12$|\.pfx$|(?:^|/)[^/]*\.key$"
    r"|(?:^|/)\.aws/credentials$|(?:^|/)\.npmrc$|(?:^|/)\.netrc$|(?:^|/)\.pypirc$"
    r"|(?:^|/)secrets?\.(?:ya?ml|json|env|toml)$"
    r"|(?:^|/)credentials?\.(?:ya?ml|json|env)$",
    re.IGNORECASE,
)

_SECRET_WRITE_MSG = (
    "🛑 Conductor rail: that write contains what looks like a LIVE credential "
    "(a real key/token/private key). Refusing to put a live secret on disk."
)
_SECRET_WRITE_REASON = (
    "Conductor blocked a file write whose content matches a live-credential "
    "pattern (a `sk_live_`/`AKIA…`/`ghp_` key or a PRIVATE KEY block). Writing a "
    "real secret into a file is exactly the mistake this rail exists to prevent - "
    "use a secrets manager or an untracked local file, never a value the agent "
    "bakes into the repo."
)
_GIT_INTERNALS_MSG = "🛑 Conductor rail: writing into .git/ internals is blocked."
_GIT_INTERNALS_REASON = (
    "Conductor blocked a write into the .git/ directory. Tampering with git "
    "internals (config, refs, hooks) out from under the human is never a safe "
    "autonomous action - make the change through normal git porcelain, which the "
    "human runs."
)
_SENSITIVE_WRITE_MSG = (
    "⏸ Conductor: this writes a production env / key / credentials file. "
    "Confirm before I touch it."
)
_SENSITIVE_WRITE_REASON = (
    "Conductor paused a write to what looks like a production environment, key, "
    "or credentials file. That can be legitimate, but it's high-blast-radius - "
    "approve if you intended it, otherwise point the write at a local/dev file."
)


def classify_write(tool_name: str, tool_input) -> Optional[Decision]:
    """Policy for Write / Edit / MultiEdit / NotebookEdit tools. None == allow.

    Scans the serialized input for a live-secret pattern (deny), and the target
    path for git-internals (deny) or a sensitive prod/key/creds file (ask).
    Pure; fail-open is handled by the caller.
    """
    try:
        blob = json.dumps(tool_input, default=str)
    except Exception:
        blob = ""
    if blob and _LIVE_SECRET.search(blob):
        return ("deny", _SECRET_WRITE_REASON, _SECRET_WRITE_MSG)
    path = ""
    if isinstance(tool_input, dict):
        path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    norm = path.replace("\\", "/")
    if norm and _GIT_INTERNALS_PATH.search(norm):
        return ("deny", _GIT_INTERNALS_REASON, _GIT_INTERNALS_MSG)
    if norm and _SENSITIVE_PATH.search(norm):
        return ("ask", _SENSITIVE_WRITE_REASON, _SENSITIVE_WRITE_MSG)
    return None


# --- I/O wiring (kept thin; all real logic is in classify/classify_tool) -----

def emit(decision: str, reason: str, human_msg: str) -> None:
    """Print a PreToolUse decision as JSON on stdout and exit 0."""
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,  # "deny" | "ask"
            "permissionDecisionReason": reason,
        },
        "systemMessage": human_msg,
    }
    print(json.dumps(out))
    sys.exit(0)


def main() -> None:
    try:
        data = json.load(sys.stdin)
        tool = data.get("tool_name", "") or ""
        tool_input = data.get("tool_input") or {}
        if tool == "Bash":
            result = classify(tool_input.get("command", "") or "")
        elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            result = classify_write(tool, tool_input)
        else:
            result = classify_tool(tool, tool_input)
        if result is None:
            sys.exit(0)
        emit(*result)
    except SystemExit:
        raise
    except Exception:
        # Never brick a tool on an internal error - fail open and let the
        # behavioral layer (orchestrator skill) hold.
        sys.exit(0)


if __name__ == "__main__":
    main()
