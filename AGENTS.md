# Vertical SaaS White-Space Atlas Agent Rules

Read first:
- `CURRENT_STATUS.md`
- `docs/FOUNDING_PACKET.md`
- `docs/FIRST_SLICE.md`
- `docs/IMPLEMENTATION_ENTRY_BRIEF.md`
- `docs/ARCHITECTURE_GUARDRAILS.md`

Rules:
- Treat this repo as standalone.
- Do not import sibling KProject context unless explicitly asked.
- Keep raw artifacts, normalized tables, and AI-derived scores as separate layers.

## Write-back rule

After every material completion (committed code, schema/config changes, new/changed docs, test suite changes):

1. **Update `CURRENT_STATUS.md` in this repo** to reflect the new present-tense state. Overwrite it, keep it under 30 lines. Skip this if the work was a review or decision that did not change repo state.

2. **Append a completion entry to `Lifehub/SYSTEM/COMPLETION_LOG.md`** (absolute path: `/Users/ryanjameson/Desktop/Lifehub/SYSTEM/COMPLETION_LOG.md`):

```
## YYYY-MM-DD | [this-repo-name] | Codex
Done: [what changed, 1-2 sentences]
Repo: [branch, commit hash]
Verified: [tests/build status]
Next: [who acts next and what]
Refs: [Linear issue, PR, relevant doc paths]
```

3. **Tell Ryan in your final message:** "Completion logged in `SYSTEM/COMPLETION_LOG.md`; `CURRENT_STATUS.md` updated if applicable."

Do not log: exploratory reads, reverted experiments, formatting fixes, routine Q&A.
Do not write to `SYSTEM/HANDOFF.md` or `SYSTEM/ACTIVE_WORK_HANDOFFS.md` (deprecated).
