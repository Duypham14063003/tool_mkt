---
name: spx-apply
description: Implement tasks from an OpenSpec change. Use when the user wants to start implementing, continue implementation, or work through tasks.
---

spx-apply:

Implement tasks from an OpenSpec change.

> **CLI NOTE**: Run all `openspec` and `bash` commands directly from the workspace root. Do NOT `cd` into any directory before running them. The `openspec` CLI is designed to work from the project root.

**⚠️ MODE: IMPLEMENTATION** — This command puts you in implementation mode. You write code, complete tasks, and modify files. This is the OPPOSITE of explore mode (`/spx-plan`). When this command ends (completion or pause), you remain in implementation context until the user explicitly switches mode.

**🚫 SUBAGENT BLACKLIST:** NEVER use the `explore` or `plan` subagents. These are generic subagents from other kits and are NOT part of this workflow. Only use subagents explicitly listed in this kit (e.g., `spx-uiux-designer`). Do your own implementation work directly.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

**Steps**

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override (e.g., `/spx-apply <other>`).

2. **Check status to understand the schema**
   ```bash
   openspec status --change "<name>" --json
   ```
   Parse the JSON to understand:
   - `schemaName`: The workflow being used (e.g., "spec-driven")
   - Which artifact contains the tasks (typically "tasks" for spec-driven, check status for others)

3. **Get apply instructions**

   ```bash
   openspec instructions apply --change "<name>" --json
   ```

   This returns:
   - Context file paths (varies by schema - could be proposal/specs/design/tasks or spec/tests/implementation/docs)
   - Progress (total, complete, remaining)
   - Task list with status
   - Dynamic instruction based on current state

   **Handle states:**
   - If `state: "blocked"` (missing artifacts): show message, suggest using openspec-continue-change
   - If `state: "all_done"`: congratulate, suggest archive
   - Otherwise: proceed to implementation

4. **Read context files**

   Read the files listed in `contextFiles` from the apply instructions output.
   The files depend on the schema being used:
   - **spec-driven**: proposal, specs, design, tasks
   - Other schemas: follow the contextFiles from CLI output

5. **Show current progress**

   Display:
   - Schema being used
   - Progress: "N/M tasks complete"
   - Remaining tasks overview
   - Dynamic instruction from CLI

6. **Implement tasks (loop until done or blocked)**

   For each pending task:
   - Show which task is being worked on
   - Make the code changes required
   - Keep changes minimal and focused
   - Mark task complete in the tasks file: `- [ ]` → `- [x]`
   - Continue to next task

   **Pause if:**
   - Task is unclear → ask for clarification
   - Implementation reveals a design issue → suggest updating artifacts
   - Error or blocker encountered → report and wait for guidance
   - User interrupts

7. **On completion or pause, show status**

   Display:
   - Tasks completed this session
   - Overall progress: "N/M tasks complete"
   - If paused: explain why and wait for guidance
   - If all done OR only manual/testing tasks remain: **proceed to auto-verify** (step 8)

8. **Auto-Verify on Completion**

   When all tasks are complete OR only manual/testing tasks remain, **automatically run verification**:

   ```
   ## All Tasks Complete — Running Verification...
   ```

   **Run the `spx-impl-verifier` subagent** with these instructions:

   ```
   Verify implementation for change: <name>

   **Artifacts:**
   - Tasks: openspec/changes/<name>/tasks.md
   - Proposal: openspec/changes/<name>/proposal.md
   - Design: openspec/changes/<name>/design.md (if exists)
   - Specs: openspec/changes/<name>/specs/*.md (if exist)

   **Implementation context:**
   - [tasks completed this session]
   - [files modified]

   Check completeness, correctness, coherence, and run project conventions.
   ```

9. **Auto-Fix Loop**

   After receiving verification report:

   **Auto-fix without asking** (these don't need user input):
   - Type errors → fix the code
   - Lint errors → run lint --fix or fix manually
   - Test failures → fix the failing tests
   - Incomplete tasks that are actually done → mark checkbox
   - Clear implementation gaps → implement

   **Skip and collect** (need user decision):
   - Ambiguous requirements
   - Design decisions that need revisiting
   - Scope questions

   ```
   ## Auto-Fixing Issues...

   ✓ Fixed: Type error in auth.ts:45
   ✓ Fixed: Lint error - missing semicolon
   ✓ Fixed: Test failure in user.test.ts
   ⏸ Skipped: Unclear requirement (needs your input)

   Re-verifying...
   ```

   **Repeat** until:
   - All auto-fixable issues resolved
   - Only manual issues remain

10. **Final Output**

    **If all clear:**
    ```
    ## ✅ Implementation Complete & Verified

    **Change:** <change-name>
    **Progress:** 7/7 tasks complete ✓
    **Verification:** All checks passed ✓

    Ready to archive → `/spx-archive <name>`
    ```

    **If manual issues remain:**
    ```
    ## ⚠️ Implementation Complete (Manual Issues Remain)

    **Change:** <change-name>
    **Progress:** 7/7 tasks complete ✓
    **Auto-fixed:** [N] issues
    **Remaining:** [M] manual issues

    ### Issues Needing Your Decision:
    1. [issue] — [options]
    2. [issue] — [options]

    After resolving, run `/spx-verify` again or proceed to archive.
    ```

**Output During Implementation**

```
## Implementing: <change-name> (schema: <schema-name>)

Working on task 3/7: <task description>
[...implementation happening...]
✓ Task complete

Working on task 4/7: <task description>
[...implementation happening...]
✓ Task complete
```

**Output On Pause (Issue Encountered)**

```
## Implementation Paused

**Change:** <change-name>
**Schema:** <schema-name>
**Progress:** 4/7 tasks complete

### Issue Encountered
<description of the issue>

**Options:**
1. <option 1>
2. <option 2>
3. Other approach

What would you like to do?
```

**Guardrails**
- Keep going through tasks until done or blocked
- Always read context files before starting (from the apply instructions output)
- If task is ambiguous, pause and ask before implementing
- If implementation reveals issues, pause and suggest artifact updates
- Keep code changes minimal and scoped to each task
- Update task checkbox immediately after completing each task
- Pause on errors, blockers, or unclear requirements - don't guess
- Use contextFiles from CLI output, don't assume specific file names
- **Auto-verify on completion** — MUST run `spx-impl-verifier` subagent when all AI-doable tasks complete (even if manual/testing tasks remain), don't skip
- **Auto-fix what you can** — only ask user for decisions that need their input

**Fluid Workflow Integration**

This skill supports the "actions on a change" model:

- **Can be invoked anytime**: Before all artifacts are done (if tasks exist), after partial implementation, interleaved with other actions
- **Allows artifact updates**: If implementation reveals design issues, suggest updating artifacts - not phase-locked, work fluidly
- **Auto-verify on completion**: When all tasks done, automatically verify and fix issues

**Subagent Reference**

| Subagent | Purpose |
|----------|---------|
| `spx-impl-verifier` | Independent verification of implementation (clean context) |

**Mode Transition Hints**

After implementation completes (with verification) or pauses:

- To think/explore/brainstorm → `/spx-plan`
- To create a new change → `/spx-ff`
- To re-verify manually → `/spx-verify`
- To archive completed work → `/spx-archive`

**IMPORTANT**: After this command ends, do NOT automatically continue writing code on subsequent user messages unless the user explicitly asks to continue implementation or invokes `/spx-apply` again. If the user invokes `/spx-plan`, you MUST fully switch to explore mode — no code writing. If the user invokes `/spx-ff`, you MUST fully switch to change creation mode — no code writing, no continuing tasks.