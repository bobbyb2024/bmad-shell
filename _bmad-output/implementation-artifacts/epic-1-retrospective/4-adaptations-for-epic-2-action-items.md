# 4. Adaptations for Epic 2 (Action Items)
- **Adversarial Tuning:** Standardize the review cycle count to **2 rounds x 2 models** (e.g., Claude and Gemini) to optimize for both quality and speed.
- **Cross-Platform Patterns:** Favor `shutil` and Python standard library primitives over shell-specific commands (like `which`) to ensure container and cross-distro compatibility.
- **State Standardization:** Re-affirmed the naming convention `bmad-orch-state.json` for all state persistence to match architectural documentation.
