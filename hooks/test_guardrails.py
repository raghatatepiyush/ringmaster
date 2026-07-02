#!/usr/bin/env python3
"""
Conductor - adversarial test battery for the guardrails hook.

Runs the pure policy (guardrails.classify) against a matrix of commands and
asserts the decision (deny / ask / allow). This is the battery the README
refers to: it documents exactly what the rails catch and, just as importantly,
what they leave alone, so normal dev work is never impeded.

Run it from anywhere:

    python3 hooks/test_guardrails.py     # or: python hooks/... / py hooks/...

Exit code 0 = all green; 1 = at least one case behaved unexpectedly.
No third-party dependencies - standard library only.
"""

import os
import sys

# On Windows the default console encoding (cp1252) can't encode the ✅/emoji in
# the summary, which would crash an otherwise-green run. Force UTF-8 so the
# battery prints identically on every OS (mirrors session_doctrine.py).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guardrails import classify, classify_tool, classify_write  # noqa: E402


def decision_of(cmd: str) -> str:
    result = classify(cmd)
    return "allow" if result is None else result[0]


def decision_of_tool(name: str, tool_input=None) -> str:
    result = classify_tool(name, tool_input or {})
    return "allow" if result is None else result[0]


def decision_of_write(name: str, tool_input) -> str:
    result = classify_write(name, tool_input)
    return "allow" if result is None else result[0]


# (command, expected_decision). Grouped by intent for readability.
CASES = [
    # ---- DENY: git history / publish ----------------------------------------
    ("git commit -m 'x'", "deny"),
    ("git add . && git commit -m wip", "deny"),
    ('bash -c "git push origin main"', "deny"),
    ('eval "git commit -m x"', "deny"),
    ("git\tcommit -m x", "deny"),                  # tab whitespace
    ("GIT_DIR=/r git push", "deny"),               # env-prefixed
    ("git -C /repo push", "deny"),                 # -C global flag
    ("git -c user.name=x commit -m y", "deny"),    # -c global flag
    ("echo hi; git push", "deny"),                 # chained
    ("git merge feature", "deny"),
    ("git rebase -i HEAD~3", "deny"),
    ("git cherry-pick abc123", "deny"),
    ("git revert HEAD", "deny"),
    ("git am < patch.eml", "deny"),
    ("gh release create v1.2.3", "deny"),
    ("git filter-branch --tree-filter x HEAD", "deny"),   # history rewrite
    ("jj git push", "deny"),                               # jujutsu ship
    ("jj commit -m x", "deny"),
    ("hg commit -m x", "deny"),                            # mercurial
    ("hg push", "deny"),
    ("svn commit -m x", "deny"),

    # ---- DENY: package / release publish tooling ----------------------------
    ("npm version patch", "deny"),
    ("npm version 2.0.0", "deny"),
    ("pnpm version minor", "deny"),
    ("npm publish", "deny"),
    ("yarn publish", "deny"),
    ("pnpm publish --access public", "deny"),
    ("bun publish", "deny"),
    ("cargo publish", "deny"),
    ("cargo release", "deny"),
    ("poetry publish --build", "deny"),
    ("twine upload dist/*", "deny"),
    ("python -m twine upload dist/*", "deny"),
    ("gem push mygem-1.0.0.gem", "deny"),
    ("mvn release:perform", "deny"),
    ("mvn deploy", "deny"),
    ("./gradlew publish", "deny"),
    ("dotnet nuget push pkg.nupkg -k KEY", "deny"),
    ("npx release-it", "deny"),
    ("npx standard-version", "deny"),
    ("semantic-release", "deny"),
    ("npx changeset publish", "deny"),

    # ---- DENY: production targeting -----------------------------------------
    ("NODE_ENV=production npm run deploy", "deny"),
    ("ASPNETCORE_ENVIRONMENT=Production dotnet run", "deny"),
    ("DEPLOY_ENV=prod ./run.sh", "deny"),
    ("kubectl --namespace prod apply -f x.yaml", "deny"),
    ("kubectl --context production get pods", "deny"),
    ("serverless deploy --stage prod", "deny"),
    ("curl https://api.prod.acme.com/v1/users", "deny"),
    ("psql postgres://db.production.internal/app", "deny"),
    ("vercel --prod", "deny"),
    ("vercel deploy --prod", "deny"),          # prod deploy stays a hard wall
    ("wrangler deploy --env production", "deny"),
    # high-signal action+prod compound (the gap this version closes)
    ("make deploy-prod", "deny"),
    ("npm run deploy:prod", "deny"),
    ("yarn release:production", "deny"),
    ("./deploy-prod.sh", "deny"),
    ("bash scripts/deploy-production.sh", "deny"),
    ("rake migrate:prod", "deny"),
    ("make prod-deploy", "deny"),
    ("npm run rollback:prod", "deny"),
    # kube-family short namespace flag `-n prod` == long `--namespace prod` (deny)
    ("kubectl -n prod get pods", "deny"),
    ("kubectl -n production delete pod web-0", "deny"),
    ("kubectl get pods -n prod", "deny"),               # flag after the subcommand
    ("kubectl -n=prod apply -f deploy.yaml", "deny"),   # equals form of the short flag
    ("kubectl -n my-prod-ns get svc", "deny"),          # prod embedded in the ns name
    ("helm upgrade -n prod app ./chart", "deny"),
    ("oc -n prod rollout restart deploy/api", "deny"),

    # ---- ASK: ship-on-command (blocked autonomously, allowed on confirm) -----
    ("gh pr merge 42", "ask"),
    ("gh pr create --fill", "ask"),
    ("glab mr merge 7", "ask"),
    ("glab mr create", "ask"),
    ("vercel deploy", "ask"),
    ("vc deploy --prebuilt", "ask"),
    ("vercel deploy --prebuilt --archive=tgz", "ask"),

    # ---- ASK: shared pre-prod / staging -------------------------------------
    ("deploy --env staging", "ask"),
    ("kubectl --namespace preprod rollout status deploy/api", "ask"),
    ("curl https://api.staging.acme.com/health", "ask"),
    ("NODE_ENV=preprod npm run seed", "ask"),
    ("deploy --stage pre-prod", "ask"),
    ("kubectl -n staging rollout status deploy/api", "ask"),   # short flag, shared tier
    ("helm -n preprod upgrade app ./chart", "ask"),

    # ---- ALLOW: normal dev work (must never be impeded) ---------------------
    ("npm test", "allow"),
    ("npm run build", "allow"),
    ("npm run build:prod", "allow"),               # a local production *build*, not a deploy
    ("npm run dev", "allow"),
    ("npm start", "allow"),
    ("npm ci", "allow"),
    ("pnpm install", "allow"),
    ("yarn add lodash", "allow"),
    ("pytest -q", "allow"),
    ("go test ./...", "allow"),
    ("cargo test", "allow"),
    ("docker build -t app .", "allow"),
    ("git status", "allow"),
    ("git diff --staged", "allow"),
    ("git add src/components/Button.tsx", "allow"),
    ("git log --oneline -10", "allow"),
    ("git show HEAD", "allow"),
    ("git stash", "allow"),
    ("git reset --hard HEAD", "allow"),            # rewinds working tree, not shared history
    ("git checkout -b feature/x", "allow"),
    ("git switch main", "allow"),
    ("git restore src/app.ts", "allow"),
    ("git merge-base HEAD main", "allow"),         # read-only plumbing, NOT a history-writing merge
    ("git merge-tree base br1 br2", "allow"),      # read-only plumbing, NOT a history-writing merge
    ("grep -r production ./src", "allow"),         # a search term, not a target
    ("grep -n production ./src/app.ts", "allow"),  # -n = line numbers (NOT a kube ns flag)
    ("wc -c report-production.txt", "allow"),      # -c = byte count, no kube binary
    ("kubectl -n default get pods", "allow"),      # a benign namespace
    ("kubectl -n dev apply -f x.yaml", "allow"),   # dev namespace is safe
    ("kubectl get pods && grep -n production log.txt", "allow"),  # kube + grep -n in SEPARATE segments
    ("cat config/production.json", "allow"),       # reading a file, not targeting prod
    ("echo 'reproduction steps for the bug'", "allow"),   # 'reproduction' contains 'production'
    # Documented residual: a resource/app name that merely embeds 'prod' but is
    # NOT passed through a recognized env flag (here fly's `--app`) is left to the
    # behavioral layer - chasing it via the flag list would false-positive on
    # every benign `--app myapp`. See README "Hardening notes & threat model".
    ("flyctl deploy --app my-prod-api", "allow"),
    ("ls deploy/", "allow"),
    ("make build", "allow"),
    ("make test", "allow"),
    ("vercel env pull", "allow"),                 # non-deploy vercel subcommands
    ("vercel ls", "allow"),
    ("vercel logs my-app", "allow"),
    ("vercel build", "allow"),                     # a build, not a deploy
    # publish-shaped but non-mutating -> exempt
    ("npm publish --dry-run", "allow"),
    ("npm version patch --no-git-tag-version", "allow"),
    ("npm version", "allow"),                      # bare: prints version, no bump
    ("cargo publish --dry-run", "allow"),
    ("jj status", "allow"),                        # read-only jj
    ("jj log", "allow"),
    ("hg status", "allow"),                        # read-only hg
    ("svn status", "allow"),
]


# MCP-tool cases (the Bash hook can't see these; classify_tool gates them).
# (tool_name, tool_input, expected_decision).
TOOL_CASES = [
    # ---- ASK: GitHub MCP writes (PR open/merge, code push, file writes) ------
    ("mcp__plugin_github_github__create_pull_request", {"title": "x"}, "ask"),
    ("mcp__plugin_github_github__merge_pull_request", {"pull_number": 7}, "ask"),
    ("mcp__plugin_github_github__push_files", {"branch": "feat"}, "ask"),
    ("mcp__plugin_github_github__create_or_update_file", {"path": "a"}, "ask"),
    ("mcp__plugin_github_github__delete_file", {"path": "a"}, "ask"),
    ("mcp__github__merge_pull_request", {"pull_number": 1}, "ask"),
    # ---- ALLOW: GitHub MCP reads (no write verb) ----------------------------
    ("mcp__plugin_github_github__get_pull_request", {"pull_number": 7}, "allow"),
    ("mcp__plugin_github_github__list_issues", {}, "allow"),
    ("mcp__plugin_github_github__search_repositories", {"q": "x"}, "allow"),
    ("mcp__plugin_github_github__get_file_contents", {"path": "a"}, "allow"),
    # ---- Vercel MCP deploy: prod denies, non-prod asks ----------------------
    ("mcp__plugin_vercel_vercel__deploy", {"target": "production"}, "deny"),
    ("mcp__plugin_vercel_vercel__deploy", {"prod": True}, "deny"),
    ("mcp__plugin_vercel_vercel__deploy", {"target": "preview"}, "ask"),
    ("mcp__plugin_vercel_vercel__deploy", {}, "ask"),
    # ---- DENY: universal PROD rail on ANY MCP tool (the gap-closer) ----------
    # Supabase / database / infra MCPs that the github/vercel branches don't know
    # about still cannot touch production.
    ("mcp__plugin_supabase_supabase__execute_sql", {"environment": "production"}, "deny"),
    ("mcp__plugin_supabase_supabase__apply_migration", {"target": "prod"}, "deny"),
    ("mcp__some_db_mcp__run_query", {"env": "production"}, "deny"),
    ("mcp__infra_mcp__apply", {"namespace": "prod"}, "deny"),
    ("mcp__infra_mcp__apply", {"context": "prod-cluster"}, "deny"),
    ("mcp__deploy_mcp__release", {"prod": True}, "deny"),
    ("mcp__deploy_mcp__release", {"flags": "--prod"}, "deny"),
    # ---- DENY: Stripe MCP in LIVE mode (real money) -------------------------
    ("mcp__plugin_stripe_stripe__create_charge", {"api_key": "sk_live_abc123"}, "deny"),
    ("mcp__plugin_stripe_stripe__create_payment", {"livemode": True}, "deny"),
    ("mcp__plugin_stripe_stripe__refund", {"mode": "live"}, "deny"),
    # ---- ALLOW: unrelated / read-only / test-mode MCP tools -----------------
    ("mcp__plugin_vercel_vercel__list_projects", {}, "allow"),
    ("mcp__plugin_supabase_supabase__list_tables", {}, "allow"),
    ("mcp__plugin_supabase_supabase__execute_sql", {"environment": "uat"}, "allow"),
    ("mcp__plugin_context7_context7__query-docs", {}, "allow"),
    ("mcp__plugin_stripe_stripe__create_charge", {"api_key": "sk_test_abc123"}, "allow"),
    # prose containing "production" under a non-env key must NOT false-positive
    ("mcp__plugin_notion_notion__search", {"query": "production roadmap"}, "allow"),
    ("mcp__plugin_gmail_gmail__search", {"q": "production incident"}, "allow"),
    ("mcp__plugin_supabase_supabase__execute_sql", {"query": "select * from reproduction"}, "allow"),
    ("Read", {"file_path": "/x"}, "allow"),
]


# Write / Edit / MultiEdit / NotebookEdit cases (the file-write flank).
# (tool_name, tool_input, expected_decision).
WRITE_CASES = [
    # ---- ALLOW: ordinary source edits ---------------------------------------
    ("Write", {"file_path": "src/x.ts", "content": "export const a = 1"}, "allow"),
    ("Edit", {"file_path": "src/app.py", "old_string": "a = 1", "new_string": "a = 2"}, "allow"),
    ("Write", {"file_path": ".env.example", "content": "API_KEY="}, "allow"),
    ("Write", {"file_path": ".env.local", "content": "API_KEY=dev"}, "allow"),
    ("Write", {"file_path": "src/ok.ts", "content": "const k = 'sk_test_abc123'"}, "allow"),
    ("NotebookEdit", {"file_path": "nb.ipynb", "new_source": "print(1)"}, "allow"),
    # ---- DENY: a LIVE credential being written to disk -----------------------
    # (fixture key split so secret scanners never match this source line;
    #  the hook still receives it joined — Stripe's docs example key, live-prefixed)
    ("Edit", {"file_path": "src/pay.ts", "old_string": "x",
              "new_string": "const k='" + "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc00'"}, "deny"),
    ("Write", {"file_path": "src/aws.ts", "content": "AKIAIOSFODNN7EXAMPLE"}, "deny"),
    ("Write", {"file_path": "cfg.ts", "content": "token = ghp_0123456789abcdefghijklmnopqrstuvwx"}, "deny"),
    ("Write", {"file_path": "key.txt", "content": "-----BEGIN OPENSSH PRIVATE KEY-----"}, "deny"),
    # ---- DENY: writing into git internals -----------------------------------
    ("Write", {"file_path": ".git/config", "content": "[core]"}, "deny"),
    ("Write", {"file_path": "repo/.git/hooks/pre-commit", "content": "#!/bin/sh"}, "deny"),
    # ---- ASK: a production env / key / credentials file ----------------------
    ("Write", {"file_path": ".env.production", "content": "DEBUG=1"}, "ask"),
    ("Write", {"file_path": "config/.env", "content": "X=1"}, "ask"),
    ("Write", {"file_path": "deploy/id_rsa", "content": "x"}, "ask"),
    ("Write", {"file_path": "app/service.pem", "content": "x"}, "ask"),
    ("Write", {"file_path": ".aws/credentials", "content": "[default]"}, "ask"),
]


def runner_cases():
    """Hermetic: wrapped runners (make / npm script / shell script) whose body
    triggers a rail must be caught one indirection deep. Returns failure msgs."""
    import tempfile
    fails = []
    cwd = os.getcwd()
    d = tempfile.mkdtemp()
    try:
        os.chdir(d)
        with open("package.json", "w", encoding="utf-8") as fh:
            fh.write('{"scripts": {"ship": "git push origin main", "t": "jest"}}')
        if decision_of("npm run ship") != "deny":
            fails.append("wrapped npm script (git push) was not denied")
        if decision_of("npm run t") != "allow":
            fails.append("benign npm script (jest) was wrongly blocked")
        with open("Makefile", "w", encoding="utf-8") as fh:
            fh.write("deploy:\n\tNODE_ENV=production ./do.sh\n\nbuild:\n\ttsc\n")
        if decision_of("make deploy") != "deny":
            fails.append("wrapped make target (prod) was not denied")
        if decision_of("make build") != "allow":
            fails.append("benign make target (tsc) was wrongly blocked")
        with open("release.sh", "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nnpm publish\n")
        if decision_of("bash release.sh") != "deny":
            fails.append("wrapped shell script (npm publish) was not denied")
        with open("ok.sh", "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\nnpm test && echo done\n")
        if decision_of("bash ok.sh") != "allow":
            fails.append("benign wrapped shell script was wrongly blocked")
    finally:
        os.chdir(cwd)
    return fails


def perf_cases():
    """ReDoS regression guard - a complexity tripwire, NOT a wall-clock SLA.

    The env-targeting regexes once backtracked quadratically: the unbounded
    URL-scheme alternative (`[a-z][a-z0-9+.-]*://...`) and the open lazy gap in
    _KUBE_SEG both went O(N^2) on a long token, blowing past the 10 s hook
    timeout - which fails OPEN (the tool call proceeds unguarded). After the fix
    they are linear: the probes below classify in well under a second, ~0.5 s
    even on a loaded CI runner. A *reintroduced* quadratic would take tens of
    seconds on the same inputs (the old code was ~15 s at 58 KB). The budget is
    set far above linear-on-slow-CI and far below any quadratic regression, so
    it catches a regression without flaking on runner noise - do NOT tighten it
    toward the observed linear time. See guardrails._context_regex / _KUBE_SEG."""
    import time
    fails = []
    budget_s = 5.0  # linear is ~0.5 s here even on slow CI; a quadratic regression is tens of s
    for probe in ("a" * 100000,                       # bare long token, no '://'
                  "kubectl -n " + "a" * 100000,       # trigger absent past a long run
                  "oc " * 30000):                     # repeated kube binary (_KUBE_SEG gap)
        t0 = time.perf_counter()
        classify(probe)
        dt = time.perf_counter() - t0
        if dt > budget_s:
            fails.append(f"classify({len(probe)//1000}KB token) took {dt:.2f}s "
                         f"(> {budget_s}s budget) - possible ReDoS regression")
    # The fix must not change what the URL alternative catches.
    if decision_of("curl https://api.prod.acme.com/health") != "deny":
        fails.append("prod URL no longer denied after ReDoS fix")
    if decision_of("curl https://api.staging.acme.com/x") != "ask":
        fails.append("staging URL no longer asked after ReDoS fix")
    return fails


def main() -> int:
    passed = 0
    failures = []
    for cmd, expected in CASES:
        got = decision_of(cmd)
        if got == expected:
            passed += 1
        else:
            failures.append((repr(cmd), expected, got))
    for name, tin, expected in TOOL_CASES:
        got = decision_of_tool(name, tin)
        if got == expected:
            passed += 1
        else:
            failures.append((f"{name} {tin}", expected, got))
    for name, tin, expected in WRITE_CASES:
        got = decision_of_write(name, tin)
        if got == expected:
            passed += 1
        else:
            failures.append((f"{name} {tin}", expected, got))

    runner_fails = runner_cases()
    runner_total = 6
    passed += (runner_total - len(runner_fails))
    for msg in runner_fails:
        failures.append((f"runner: {msg}", "-", "-"))

    perf_fails = perf_cases()
    perf_total = 5
    passed += (perf_total - len(perf_fails))
    for msg in perf_fails:
        failures.append((f"perf: {msg}", "-", "-"))

    total = len(CASES) + len(TOOL_CASES) + len(WRITE_CASES) + runner_total + perf_total
    print(f"Conductor guardrails battery: {passed}/{total} cases as expected "
          f"({len(CASES)} Bash + {len(TOOL_CASES)} MCP-tool + {len(WRITE_CASES)} "
          f"Write/Edit + {runner_total} wrapped-runner + {perf_total} perf/ReDoS).")
    if failures:
        print("\nUnexpected results:")
        for case, expected, got in failures:
            print(f"  [{expected:>5} expected, got {got:>5}]  {case}")
        return 1
    print("All rails behaving as specified. \u2705")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
