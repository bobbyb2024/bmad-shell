# BMAD Shell - Project Overview & Instructions

**bmad-shell** is a BMAD Framework (v6.1.0) installation. It is an integrated multi-agent, multi-module AI system for end-to-end product development. The system is **configuration-only** (Markdown + YAML + CSV) and does not contain traditional source code, build systems, or test suites.

## Project Architecture

### Module System
The framework is divided into four specialized modules:
- **core**: Universal tools (orchestration, brainstorming, adversarial reviews).
- **bmm** (Business Method Module): Product lifecycle (Analysis → Planning → Solutioning → Implementation).
- **cis** (Creative Intelligence Suite): Creative ideation, design thinking, and storytelling.
- **tea** (Test Architecture Enterprise): Risk-based testing and CI/CD governance.

### Execution Model
- **Agents**: AI personas defined in Markdown (with embedded XML/YAML) located in `_bmad/{module}/agents/`.
- **Workflows**: Step-file based sequences located in `_bmad/{module}/workflows/`. Each step is a self-contained `.md` file.
- **Artifacts**: All generated documents (PRDs, Architecture, UX Specs) are stored in `_bmad-output/` and include YAML frontmatter for state tracking.

## Key Directories

| Path | Purpose |
|------|---------|
| `_bmad/_config/` | System manifests, skill definitions, and routing tables. |
| `_bmad/_memory/` | Documentation standards and agent preferences. |
| `_bmad/{module}/agents/` | Agent persona definitions and interaction menus. |
| `_bmad/{module}/workflows/` | Workflow step-files and supporting templates. |
| `_bmad-output/` | **Primary output directory** for all generated project artifacts. |
| `.gemini/skills/` | Skill definitions specifically for Gemini CLI integration. |

## Agent Interaction Workflow

To interact with the system, follow this pattern:
1. **Load Config**: Read `{project-root}/_bmad/bmm/config.yaml` to initialize session variables (`user_name`, `output_folder`, etc.).
2. **Activate Agent**: Read an agent definition (e.g., `_bmad/bmm/agents/pm.md`) and embody the persona.
3. **Display Menu**: Present the numbered menu items from the agent's `<menu>` section.
4. **Execute**: When a user selects a menu item, load the corresponding workflow file (specified by the `exec` attribute) and follow its instructions sequentially.

## Development Conventions

- **File Formats**: Use Markdown for all content, YAML for configuration/state, and CSV for manifests.
- **State Tracking**: All output artifacts must maintain a `stepsCompleted` array in their YAML frontmatter.
- **Diagrams**: Use **Mermaid** syntax for all architectural or flow diagrams.
- **Context Efficiency**: Agents should only load the files required for the current step; do not ingest the entire directory at once.
- **Documentation**: Adhere to the standards in `_bmad/_memory/tech-writer-sidecar/documentation-standards.md`.

## Help & Routing
Users can invoke the `bmad-help` skill at any time. The system uses `_bmad/_config/bmad-help.csv` to route requests to the appropriate agent or workflow based on the current project state (inferred from `_bmad-output/`).

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any shell command containing `curl` or `wget` will be intercepted and blocked. Do NOT retry.
Instead use:
- `mcp__context-mode__ctx_fetch_and_index(url, source)` to fetch and index web pages
- `mcp__context-mode__ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any shell command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` will be intercepted and blocked. Do NOT retry with shell.
Instead use:
- `mcp__context-mode__ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch / web browsing — BLOCKED
Direct web fetching is blocked. Use the sandbox equivalent.
Instead use:
- `mcp__context-mode__ctx_fetch_and_index(url, source)` then `mcp__context-mode__ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Shell (>20 lines output)
Shell is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `mcp__context-mode__ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `mcp__context-mode__ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### read_file (for analysis)
If you are reading a file to **edit** it → read_file is correct (edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `mcp__context-mode__ctx_execute_file(path, language, code)` instead. Only your printed summary enters context.

### grep / search (large results)
Search results can flood context. Use `mcp__context-mode__ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `mcp__context-mode__ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `mcp__context-mode__ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `mcp__context-mode__ctx_execute(language, code)` | `mcp__context-mode__ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `mcp__context-mode__ctx_fetch_and_index(url, source)` then `mcp__context-mode__ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `mcp__context-mode__ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `upgrade` MCP tool, run the returned shell command, display as checklist |
