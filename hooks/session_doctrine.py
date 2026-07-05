#!/usr/bin/env python3
"""
Ringmaster — session bootstrap (SessionStart).

Plain-text stdout from a SessionStart hook is injected into the model's context
at the start of every session. We keep this deliberately short (token discipline)
and let the orchestrator skill carry the detail, loaded only when a real task
arrives. We also print a cheap, best-effort stack fingerprint so Ringmaster feels
plug-and-play on whatever project it lands in, and — when a previous session left
a ledger — a one-line resume hint so a fresh session knows work is waiting.
"""

import json
import os
import sys

# On Windows the default console encoding (e.g. cp1252) can raise
# UnicodeEncodeError on the emoji/em-dash below, which would crash this hook and
# suppress the banner. Force UTF-8 so the doctrine prints identically on every OS.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Best-effort, no-cost stack detection from manifest files in the working dir.
MANIFESTS = {
    "package.json": "Node/JS-TS",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "deno.json": "Deno",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "Pipfile": "Python",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java/Maven",
    "build.gradle": "JVM/Gradle",
    "build.gradle.kts": "JVM/Gradle",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "pubspec.yaml": "Dart/Flutter",
    "mix.exs": "Elixir",
    "Package.swift": "Swift",
    "CMakeLists.txt": "C/C++",
    "*.csproj": ".NET",
    "*.sln": ".NET",
}


def detect_stack() -> str:
    try:
        entries = set(os.listdir("."))
    except Exception:
        return ""
    found = []
    for name, label in MANIFESTS.items():
        if name.startswith("*."):
            ext = name[1:]
            if any(e.endswith(ext) for e in entries):
                found.append(label)
        elif name in entries:
            found.append(label)
    # de-dup, keep order
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return ", ".join(out)


def detect_resume() -> str:
    """Best-effort: if a Ringmaster ledger exists, summarize pending work in one line.

    Never raises — a missing or malformed ledger simply yields no hint, so the
    banner is never suppressed by a bad state file."""
    try:
        path = os.path.join(".ringmaster", "state.json")
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
        tasks = state.get("tasks", []) if isinstance(state, dict) else []
        pending = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "pending")
        in_prog = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "in_progress")
        if pending == 0 and in_prog == 0:
            return ""
        updated = state.get("updated", "a previous session")
        return ("▶ Resume available: %d pending · %d in-progress (from %s) "
                "— say \"pickup\" or /ringmaster:pickup." % (pending, in_prog, updated))
    except Exception:
        return ""


stack = detect_stack()
stack_line = f"Detected stack signals here: {stack}." if stack else "No manifest detected yet — Ringmaster will fingerprint the stack when work begins."
resume_line = detect_resume()

# This hook runs through the same interpreter-discovery shim as the guardrails
# hook, so if you can read this line, the hard rails are armed on this OS too.
_os = {"win32": "Windows", "darwin": "macOS"}.get(sys.platform, "Linux/Unix")
py = f"{sys.version_info.major}.{sys.version_info.minor}"
runtime_line = f"Hard safety rails armed (hook running on {_os}, Python {py})."

print(
    f"""🎪 Ringmaster is active — you direct a senior engineering team, not code alone. The full playbook lives in the `ringmaster:orchestrator` skill; read it before acting on any build/change/test/frontend/back-end/DB/payments/skill task. In short: clarify the real goal and plan in plain language, get a "go" before building anything substantial, route each step to the best specialist (with a built-in fallback if one's missing — never block), ship every production-code change with tests via the Test Architect and through the Security Gate before staging, and pretty-print every result in plain language a junior engineer could follow.

Hard safety rails (enforced in code by a hook — they hold even under skip-permissions, so don't fight them, just work within them):
  • Stage only — never commit, push, merge, rebase, or cut a release. The human commits and ships.
  • Never run anything against PRODUCTION; a prod deploy is blocked outright. Work only in DEV / UAT / PREPROD (shared pre-prod asks first).
  • Opening/merging a PR or a preview deploy pauses for your explicit "go" — enforced on Bash and the GitHub/Vercel MCP tools alike.

{runtime_line}
{stack_line}{(chr(10) + resume_line) if resume_line else ""}"""
)
