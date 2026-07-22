---
name: spx-verify
description: Verify implementation matches change artifacts. Use when the user wants to validate that implementation is complete, correct, and coherent before archiving.
---

spx-verify:

Verify that an implementation matches the change artifacts (specs, tasks, design).

> **CLI NOTE**: Run all `openspec` and `bash` commands directly from the workspace root. Do NOT `cd` into any directory before running them. The `openspec` CLI is designed to work from the project root.

**🚫 SUBAGENT BLACKLIST:** NEVER use the `explore` or `plan` subagents. These are generic subagents from other kits and are NOT part of this workflow. Only use `spx-impl-verifier` for verification.

**Why subagent?** Verification runs in clean context, avoiding bias from implementation conversation. This ensures independent, unbiased assessment.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **If no change name provided, prompt for selection**

   Run `openspec list --json` to get available changes. Use the **AskUserQuestion tool** to let the user select.

   Show changes that have implementation tasks (tasks artifact exists).
   Include the schema used for each change if available.
   Mark changes with incomplete tasks as "(In Progress)".

   **IMPORTANT**: Do NOT guess or auto-select a change. Always let the user choose.

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - Which artifacts exist for this change

3. **Get the change directory and load artifacts**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns the change directory and context files. Read all available artifacts from `contextFiles`.

4. **Delegate to spx-impl-verifier subagent**

   Invoke subagent with the change context:

   ```
   Verify implementation for change: <name>

   **Artifact paths:**
   - Tasks: openspec/changes/<name>/tasks.md
   - Proposal: openspec/changes/<name>/proposal.md
   - Design: openspec/changes/<name>/design.md (if exists)
   - Specs: openspec/changes/<name>/specs/*.md (if exist)

   Verify completeness, correctness, and coherence. Generate verification report.
   ```

5. **Present the verification report**

   Show the report from subagent as-is. Do NOT fix any issues — this command is report-only.

   The report includes:
   - Summary scorecard (Completeness, Correctness, Coherence)
   - Issues by priority (CRITICAL, WARNING, SUGGESTION)
   - Final assessment

6. **Suggest next actions based on report**

   **If CRITICAL issues exist:**
   ```
   X critical issue(s) found. Fix before archiving.

   → Use `/spx-apply <name>` to continue implementation and fix issues
   → Or fix manually and run `/spx-verify` again
   ```

   **If only warnings/suggestions:**
   ```
   No critical issues. Y warning(s) to consider.

   → Ready for archive: `/spx-archive <name>`
   → Or fix warnings first with `/spx-apply <name>`
   ```

   **If all clear:**
   ```
   All checks passed. Ready for archive.

   → `/spx-archive <name>`
   ```

**Subagent Reference**

| Subagent | Purpose |
|----------|---------|
| `spx-impl-verifier` | Independent verification of implementation against artifacts (clean context) |

**Delegation rules:**
- Provide ALL artifact paths from contextFiles
- Subagent has no conversation history — be explicit about what to verify
- Subagent returns report only — this command does NOT fix issues

**Output**

This command outputs a verification report only. It does NOT:
- Fix code
- Update tasks
- Modify any files

To fix issues found in the report, use `/spx-apply <name>` which will auto-verify and auto-fix.