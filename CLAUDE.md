# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**bmad-shell** is a BMAD Framework (v6.1.0) installation — an integrated multi-agent, multi-module AI system for end-to-end product development. It is configuration-only (markdown + YAML + CSV); there is no traditional build system, test suite, or compiled code.

**User:** Bobby | **Language:** English | **Output:** `_bmad-output/`

## Architecture

### Module System

Four modules, each with agents, workflows, and configs:

- **core** — Universal tools available anytime: bmad-master (orchestrator), party-mode, brainstorming, editorial reviews, adversarial reviews, edge-case hunting
- **bmm** (Business Method Module) — Product development lifecycle across 4 phases: Analysis → Planning → Solutioning → Implementation. 9 agents (PM, Architect, Dev, QA, SM, UX, Analyst, Tech Writer, Quick Flow)
- **cis** (Creative Intelligence Suite) — 6 creative agents for ideation, design thinking, innovation strategy, storytelling, presentations
- **tea** (Test Architecture Enterprise) — Risk-based testing, ATDD, CI/CD governance, test design patterns. Supports pytest, Playwright, Cypress, JUnit, etc.

### Execution Model

Agents load resources at runtime from `_bmad/` — never pre-load all files. Workflows are step-file based: each step is a self-contained `.md` file executed sequentially. Agents present numbered menus and wait for user selection. All generated artifacts go to `_bmad-output/`.

### Key Paths

| Path | Purpose |
|------|---------|
| `_bmad/_config/` | Manifests (agents, skills, workflows) and routing tables |
| `_bmad/_memory/` | Agent preferences, documentation standards |
| `_bmad/{module}/agents/` | Agent persona definitions (markdown with XML schema) |
| `_bmad/{module}/workflows/` | Step-file workflows with supporting data/templates |
| `_bmad-output/planning-artifacts/` | PRDs, architecture docs, research, UX specs |
| `_bmad-output/implementation-artifacts/` | Sprint status, code reviews, retrospectives |
| `_bmad-output/test-artifacts/` | Test suites, traceability matrices |
| `.claude/skills/` | 60 skill definitions for Claude Code activation |

### Agent Activation Pattern

1. Load the module's `config.yaml` first (critical for session variables: `user_name`, `communication_language`, `output_folder`)
2. Read the full agent `.md` file and embody the persona
3. Present the menu from the agent definition
4. Wait for user input — never auto-execute menu items
5. On selection: load workflow/task files on-demand via `exec=` attributes

### Workflow Step-File Pattern

Workflows use micro-file architecture: `workflow.md` → `steps/step-01-init.md` → `step-02-*.md` → etc. Each step file has mandatory execution rules, context boundaries, and menu handling logic. Steps append content to an output document and track progress in its YAML frontmatter (`stepsCompleted` array).

## BMM Phase Sequencing

Workflows follow a required phase order. Some are gates that block progress:

1. **Analysis:** Market/Domain/Technical Research → Product Brief
2. **Planning:** Create PRD (required) → UX Design
3. **Solutioning:** Architecture (required) → Epics & Stories (required) → Implementation Readiness Check
4. **Implementation:** Sprint Planning → Create Story → Dev Story → Code Review → QA → Retrospective

## Routing

`bmad-help` uses `_bmad/_config/bmad-help.csv` and `_bmad/bmm/module-help.csv` to route users to the right workflow based on context. It scans `_bmad-output/` for existing artifacts to infer project state.

## Conventions

- Agent definitions: markdown with embedded XML schema and YAML frontmatter
- Configs: YAML for settings, CSV for routing/manifests
- All output artifacts: markdown with YAML frontmatter for state tracking
- Documentation standards: `_bmad/_memory/tech-writer-sidecar/documentation-standards.md`
- Diagrams: Mermaid preferred over verbose text descriptions
