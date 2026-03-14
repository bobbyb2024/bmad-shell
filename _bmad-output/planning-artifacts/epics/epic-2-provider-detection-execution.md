# Epic 2: Provider Detection & Execution

The orchestrator detects installed AI CLIs (Claude, Gemini), queries their available models, and executes prompts with full streaming output capture via PTY.

## Story 2.1: Provider Adapter Interface & Detection Framework

As a **developer**,
I want a provider adapter interface with CLI detection capabilities,
So that new providers can be added by implementing a single contract without changing core engine code.

**Acceptance Criteria:**

**Given** the `providers/base.py` module
**When** I inspect the `ProviderAdapter` ABC
**Then** it defines `async def execute(prompt: str) -> AsyncIterator[OutputChunk]`, `def detect() -> bool`, and `def list_models() -> list[str]`

**Given** the provider detection framework
**When** I call `detect()` on an adapter
**Then** it checks whether the provider's CLI binary is installed and executable on the host machine

**Given** a provider CLI is installed
**When** I call `list_models()` on its adapter
**Then** it queries the CLI for available models and returns them as a list of strings

**Given** the adapter registry in `providers/__init__.py`
**When** I call `get_adapter(name)` with a valid provider name
**Then** it returns the correct adapter instance

**Given** the adapter registry
**When** I call `get_adapter(name)` with an unknown provider name
**Then** it raises `ProviderNotFoundError` with a clear message listing available providers

**Given** any provider adapter's `execute()` method
**When** the subprocess produces output
**Then** output is captured via PTY and yielded as `OutputChunk` objects preserving ANSI formatting

## Story 2.2: Claude CLI Adapter

As a **user**,
I want the orchestrator to invoke Claude CLI with my configured prompts,
So that Claude can execute generative and validation steps in my workflows.

**Acceptance Criteria:**

**Given** the Claude CLI is installed on the host
**When** `ClaudeAdapter.detect()` is called
**Then** it returns `True`

**Given** the Claude CLI is not installed
**When** `ClaudeAdapter.detect()` is called
**Then** it returns `False`

**Given** a detected Claude CLI
**When** `ClaudeAdapter.list_models()` is called
**Then** it returns the list of available models from the Claude CLI

**Given** a valid prompt and model configuration
**When** `ClaudeAdapter.execute(prompt)` is called
**Then** the Claude CLI is invoked as an async subprocess via PTY with the configured model and prompt
**And** stdout is streamed as `OutputChunk` objects via `AsyncIterator`

**Given** a running Claude subprocess
**When** it completes successfully
**Then** the adapter detects completion and yields a final `OutputChunk` with completion status

**Given** a running Claude subprocess
**When** it times out or terminates unexpectedly (crash, OOM, signal)
**Then** the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises `ProviderCrashError` or `ProviderTimeoutError` with exit code context

**Given** a running Claude subprocess
**When** the CLI output format is unrecognizable
**Then** the adapter parses defensively and raises an explicit error rather than silently producing garbage output

## Story 2.3: Gemini CLI Adapter

As a **user**,
I want the orchestrator to invoke Gemini CLI with my configured prompts,
So that Gemini can execute validation steps and provide adversarial review in my workflows.

**Acceptance Criteria:**

**Given** the Gemini CLI is installed on the host
**When** `GeminiAdapter.detect()` is called
**Then** it returns `True`

**Given** the Gemini CLI is not installed
**When** `GeminiAdapter.detect()` is called
**Then** it returns `False`

**Given** a detected Gemini CLI
**When** `GeminiAdapter.list_models()` is called
**Then** it returns the list of available models from the Gemini CLI

**Given** a valid prompt and model configuration
**When** `GeminiAdapter.execute(prompt)` is called
**Then** the Gemini CLI is invoked as an async subprocess via PTY with the configured model and prompt
**And** stdout is streamed as `OutputChunk` objects via `AsyncIterator`

**Given** a running Gemini subprocess
**When** it completes successfully
**Then** the adapter detects completion and yields a final `OutputChunk` with completion status

**Given** a running Gemini subprocess
**When** it times out or terminates unexpectedly
**Then** the adapter detects the failure, calls `process.kill()` + `await process.wait()`, and raises the appropriate `ProviderError` subclass

**Given** a running Gemini subprocess
**When** the CLI output format is unrecognizable
**Then** the adapter parses defensively and raises an explicit error

## Story 2.4: Single-Provider Graceful Mode

As a **user with only one AI CLI installed**,
I want the orchestrator to operate fully with a single provider,
So that I can run automated cycles without needing to install a second CLI.

**Acceptance Criteria:**

**Given** a config file that references two providers but only one is detected on the host
**When** the orchestrator validates the config
**Then** it reports which providers are missing and exits with a clear error suggesting the user update their config or install the missing CLI

**Given** a config file that references only one provider for all steps
**When** the orchestrator validates the config
**Then** validation passes — single-provider configs are fully valid

**Given** a single-provider config
**When** cycles execute
**Then** all steps run against the single provider with no errors or warnings about missing adversarial validation

**Given** the provider detection framework
**When** no CLI providers are detected at all
**Then** the system exits with a clear error message and helpful install links for supported CLIs
