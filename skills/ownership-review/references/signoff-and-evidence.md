# Sign-off & Evidence — the ownership record and its audit trail

This is what makes the ownership review more than a quiz: a **durable, honest artifact** that lets a developer prove — to themselves, their lead, an auditor, or a future incident review — that they genuinely owned an AI-written change. Read this in Stages 3–4 of the `ownership-review` skill. It reuses the house style in `skills/orchestrator/references/output-style.md`.

---

## The Ownership Sign-off Record

Emit this at hand-off. It folds in the comprehension result (from `agents/comprehension.md`) and the detection headlines (Security Gate + code-review), then states the sign-off honestly.

```
### ✍️ Ownership Sign-off — Record

| Field        | Detail                                                            |
| :----------- | :--------------------------------------------------------------- |
| Change       | <branch / PR / diff scope>                                        |
| Owner        | <the developer taking responsibility>                            |
| Tier         | Trivial / Standard / Critical                                    |
| Detection    | 🔒 <Security Gate verdict> · 🔍 <code-review verdict>            |
| Comprehension| ✅ <n> solid · 🟡 <n> partial · ❌ <n> corrected · 🔵 <n> unknown  |
| Calibration  | <n> sure-and-wrong (blind spots caught before prod)              |
| Sign-off     | ✅ OWNED  /  ⚠️ OWNED WITH NOTES  /  ⛔ NOT YET OWNED             |
| gate.owned   | true / false  ·  <enforced by Stop hook / not ledger-tracked>    |

<one line per comprehension question, in order:>
- [<level>] <✅/🟡/❌/🔵> <short question> — <what they got / what was corrected> <(⚠ was "sure")>

#### 🗣️ In plain terms
> <2-4 sentences. Was this change genuinely understood by the person signing?
>  Name where understanding was solid, and name honestly where it was rebuilt.
>  End with the concrete, defensible thing they can now do — e.g.
>  "You can walk into an incident review for this refund path and explain, in your
>   own words, why an ownership check on line 34 is what stops user A refunding
>   user B's order — that's what your sign-off is worth.">
```

Fold, don't duplicate: the Security Gate and code-review print their own blocks — reference their verdicts in the table, let their detail stand.

---

## The honesty doctrine — what a sign-off may and may not claim

A sign-off is a claim about a *person's understanding at a moment*, not a certificate of correctness. Hold it to this bar:

- **It records reconstruction, not perfection.** A developer who was wrong, got corrected, and now genuinely understands has a **valid** ownership claim. The record shows what was native and what was rebuilt — honestly. Hiding that they needed correcting is the only real failure.
- **A corrected miss stays in the record.** No retry-to-erase. "Solid" and "corrected then understood" are both honest; a silently-scrubbed miss is not.
- **`⛔ NOT YET OWNED` is a legitimate, useful outcome.** If the developer disengaged, or a *critical* answer couldn't be grounded, the sign-off is not honest — say so and stop. `gate.owned` stays false; the Stop hook backs you (see the interaction contract in `SKILL.md`). Never upgrade the verdict to be agreeable.
- **Never claim more than the evidence.** The comprehension grader may only assert answers grounded in the diff, the surrounding code, `context7`, or a test it ran (the anti-hallucination contract). The record inherits that: every "corrected" line traces to a real `file:line`. A sign-off built on a confidently-wrong "correct answer" is worse than none — it teaches the owner false things about their own code.
- **Ownership is the human's, always.** This skill *evidences* a sign-off; it never *is* one. The developer signs. Conductor never commits, and never marks a change owned on the human's behalf to move things along.

---

## The evidence trail — Jira / Confluence

The record is most valuable when it's **durable and findable** later — attached to the ticket or the PR, not lost in a terminal scrollback. Two paths, in order of preference by what's actually connected:

### Default — draft-and-paste (always available, zero dependencies)

Produce a clean, paste-ready block the developer drops into the Jira ticket, the PR description, or a Confluence page. This is the default and it always works — no MCP, no credentials, no assumptions.

```
Ownership sign-off — <change> — <date>
Owner: <developer>   Verdict: <OWNED / OWNED WITH NOTES / NOT YET OWNED>
Detection: Security Gate <verdict>, code-review <verdict>
Comprehension: <n solid / n corrected / n unknown>; blind spots caught: <n>
Understood & defensible: <the load-bearing point, in one plain sentence>
Corrected during review: <the miss(es), or "none">
```

### Upgrade — Atlassian MCP (only if connected)

If the **Atlassian MCP** is live in the session (its `mcp__…` Jira/Confluence tools are present), offer to write the sign-off straight onto the ticket or page. Follow the MCP preflight rule (`skills/orchestrator/references/routing-and-plugins.md`): **check first, never assume, never stall silently.** Use the missing-MCP recommendation block from `output-style.md`:

> 🔌 Conductor can attach this sign-off straight to the Jira ticket with the `atlassian` MCP, which isn't connected. I can:
>  (a) wait while you add it, then write it to the ticket; or
>  (b) give you the paste-ready block now (above) — you drop it into Jira/Confluence yourself.
> Which do you want?

**Rails still apply to the write.** Writing a sign-off comment to a DEV/UAT ticket is fine; anything that looks like a production mutation is not. And the write is *evidence*, never a shipping action — it records that the human owns the change; it does not commit, merge, or deploy it. As with every MCP call, the guardrails hook gates it; don't fight the rail, work within it.
