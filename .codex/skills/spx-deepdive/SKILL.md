---
name: deepdive
description: Delve into a specific feature and trace its full flow across the project. Use when the user wants a complete feature walkthrough, data flow summary, and related follow-up exploration options.
---

deepdive:

Investigate a specific feature in depth and provide a complete end-to-end flow summary.

**Purpose**

- Understand how a feature works across the codebase
- Trace data movement from UI to API to database and back
- Surface related files, hidden dependencies, and possible edge cases

**When to use**

- The user asks how a feature works
- The user wants a complete flow summary
- The user wants to inspect a module end-to-end before debugging or extending it

**Workflow**

1. **Run preliminary search**
   - Search the codebase multiple times using the requested feature name and related keywords
   - Build an initial set of relevant files, modules, and entry points

2. **Expand coverage**
   - Search outward from initial findings
   - Include related components, hooks, routes, services, actions, database models, and configuration
   - Ensure project-wide coverage rather than a narrow local read

3. **Read the important files**
   - Read relevant files fully or by focused sections
   - Understand feature behavior, branching logic, dependencies, and state transitions

4. **Check hidden paths**
   - Search from alternate angles
   - Look for validation, permissions, side effects, background logic, error handling, and fallback behavior
   - If new paths appear, loop back and expand again

5. **Filter and synthesize**
   - Remove unrelated results
   - Keep only files and logic directly tied to the requested feature
   - Build a coherent flow explanation

6. **Explain the full flow**
   - Describe how the feature starts, what it calls, where data moves, and how the result is returned
   - Include important conditions, validations, and persistence behavior

7. **Summarize in flow format**
   - Provide a concise chain such as:
     `UI → handler → API / action → service → database → response → UI`

8. **Suggest next exploration options**
   - End with numbered next-step choices for the developer, such as:
     1. Explore UI layer
     2. Explore backend logic
     3. Explore database and schema
     4. Investigate edge cases
     5. Review everything

**Output format**
Include:

- Feature overview
- Key files involved
- End-to-end flow explanation
- Short flow summary (`A → B → C`)
- Hidden considerations / risks
- Numbered next-action options
