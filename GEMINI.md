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

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `search(source: "label")` later.

