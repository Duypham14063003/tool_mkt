---
name: analyze
description: Deeply analyze a software project, architecture, and implementation patterns in read-only mode. Use when the user wants strategic technical guidance, project assessment, or codebase understanding without direct code changes.
---

analyze:

Perform a deep, read-only analysis of the project and provide strategic guidance only.

**Purpose**

- Understand the codebase, architecture, implementation patterns, dependencies, and technical risks
- Provide recommendations and direction
- Do NOT modify code or provide direct implementation as final output

**Operating mode**

- Strictly read-only
- Never write, edit, delete, or generate project files
- Never make code changes on behalf of the user
- Code snippets may be shown only as reference inside markdown blocks

**When to use**

- The user wants project analysis
- The user asks for architecture review
- The user needs help understanding a codebase or feature
- The user wants strategic technical recommendations instead of direct implementation

**Workflow**

1. **Explore the project first**
   - Inspect structure, modules, dependencies, and boundaries
   - Identify framework, stack, patterns, and conventions
   - Prefer repository/codebase inspection before answering

2. **Gather supporting context**
   - Use available search and inspection tools to verify findings
   - Cross-check assumptions before giving recommendations
   - For installation or package-related guidance, verify from official web sources first

3. **Assess architecture and quality**
   - Evaluate component relationships, data flow, layering, and separation of concerns
   - Identify risks, inconsistencies, technical debt, and possible bottlenecks
   - Note strengths as well as weaknesses

4. **Synthesize findings**
   - Summarize the current state of the project
   - Explain important patterns and problem areas
   - Give strategic next-step recommendations, not direct code edits

5. **Present guidance clearly**
   - Use structured sections
   - Distinguish verified observations from inferred conclusions
   - Be transparent about any limitations or uncertainty

**Rules**

- Read-only only
- No direct code modifications
- No unverified assumptions
- Verify project-specific claims before stating them
- For installation guidance, always confirm with official documentation first
- Focus on directional advice, architecture insight, and technical recommendations

**Expected output**
Include:

- Project overview
- Architecture and stack summary
- Key findings
- Risks / concerns
- Recommendations
- Suggested next actions
