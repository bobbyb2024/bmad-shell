#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# run-story-cycle.sh — Full automated story lifecycle
#
# For each backlog story in the current in-progress epic:
#   1. Gemini: create-story
#   2. Adversarial review cycle (Claude → Gemini → Claude → Gemini)
#   3. Gemini: dev-story (implementation)
#   4. Code review cycle (Claude → Gemini → Claude → Gemini)
#   5. Git commit + push
#   6. Move to next story
#
# All output is logged per-story to _bmad-output/implementation-artifacts/
# On any error, execution halts and waits for human intervention.
#
# Usage:
#   ./run-story-cycle.sh              # process all remaining backlog stories
#   ./run-story-cycle.sh [story-key]  # process a single story
# ============================================================================

SPRINT_STATUS="_bmad-output/implementation-artifacts/sprint-status.yaml"
STORY_DIR="_bmad-output/implementation-artifacts"
STEP_TIMEOUT=1800  # 30 minutes per CLI invocation

# --- Logging ---
LOG_FILE=""

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  if [[ -n "$LOG_FILE" ]]; then
    echo "$msg" >> "$LOG_FILE"
  fi
}

init_log() {
  local story_key="$1"
  LOG_FILE="${STORY_DIR}/${story_key}-cycle.log"
  echo "" > "$LOG_FILE"
  log "═══════════════════════════════════════════════════════════"
  log "  Story Cycle Log: $story_key"
  log "  Started: $(date '+%Y-%m-%d %H:%M:%S')"
  log "  Host: $(hostname)"
  log "═══════════════════════════════════════════════════════════"
}

# --- Error handling ---
# Logs full error context and halts for human intervention
halt_on_error() {
  local step_label="$1"
  local command="$2"
  local exit_code="$3"
  local elapsed="$4"

  log ""
  log "╔══════════════════════════════════════════════════════════╗"
  log "  ERROR — HUMAN INTERVENTION REQUIRED"
  log "╠══════════════════════════════════════════════════════════╣"
  log "  Step:      $step_label"
  log "  Command:   $command"
  log "  Exit code: $exit_code"
  log "  Elapsed:   ${elapsed}s"
  log "  Time:      $(date '+%Y-%m-%d %H:%M:%S')"
  log "  Log file:  $LOG_FILE"
  if [[ "$exit_code" -eq 124 ]]; then
    log "  Cause:     TIMEOUT (exceeded ${STEP_TIMEOUT}s limit)"
    log "             The CLI may be stuck at a prompt or in a loop."
  elif [[ "$exit_code" -eq 130 ]]; then
    log "  Cause:     INTERRUPTED (SIGINT)"
  elif [[ "$exit_code" -eq 137 ]]; then
    log "  Cause:     KILLED (SIGKILL / OOM)"
  else
    log "  Cause:     Non-zero exit from CLI"
  fi
  log "╠══════════════════════════════════════════════════════════╣"
  log "  Review the log file above, fix the issue, then re-run:"
  log "    ./run-story-cycle.sh"
  log "╚══════════════════════════════════════════════════════════╝"
  log ""

  echo ""
  echo ">>> Script halted. See log: $LOG_FILE <<<"
  echo ""
  exit 1
}

# --- Run a CLI step with timeout, logging, and error detection ---
# Usage: run_step "label" "full command string"
# The command is passed as a single string and executed via bash -c
# to preserve quoting of arguments (e.g., -p "multi word prompt").
run_step() {
  local step_label="$1"
  local cmd_str="$2"

  log ""
  log "────────────────────────────────────────────────────────────"
  log "  STEP: $step_label"
  log "  CMD:  $cmd_str"
  log "  START: $(date '+%Y-%m-%d %H:%M:%S')"
  log "────────────────────────────────────────────────────────────"

  local start_ts
  start_ts=$(date +%s)
  local rc=0

  # Run with timeout via bash -c; unbuffered tee to log while streaming to terminal
  timeout "$STEP_TIMEOUT" bash -c "$cmd_str" 2>&1 | stdbuf -oL tee -a "$LOG_FILE" || rc=$?

  local end_ts
  end_ts=$(date +%s)
  local elapsed=$(( end_ts - start_ts ))

  if [[ "$rc" -ne 0 ]]; then
    halt_on_error "$step_label" "$cmd_str" "$rc" "$elapsed"
  fi

  log ""
  log "  DONE: $step_label (${elapsed}s, exit 0)"
  log ""
}

# --- Helper: find the story file (tolerates naming variations) ---
resolve_story_file() {
  local key="$1"
  local path="${STORY_DIR}/${key}.md"
  if [[ -f "$path" ]]; then
    echo "$path"
    return
  fi
  local found
  found=$(find "$STORY_DIR" -name "${key}*" -type f -not -name "*.log" 2>/dev/null | head -1)
  if [[ -n "$found" ]]; then
    echo "$found"
    return
  fi
  echo ""
}

# --- Helper: get all pending stories for the in-progress epic ---
# Returns stories with status: backlog or ready-for-dev
get_pending_stories() {
  local epic epic_num
  epic=$(grep -E '^\s+epic-[0-9]+: in-progress' "$SPRINT_STATUS" | head -1 | sed 's/:.*//' | xargs)
  if [[ -z "$epic" ]]; then
    echo ""
    return
  fi
  epic_num="${epic#epic-}"
  grep -E "^\s+${epic_num}-[0-9]+-.*: (backlog|ready-for-dev)" "$SPRINT_STATUS" | sed 's/:.*//' | xargs -n1
}

# --- Git commit and push after each story ---
git_commit_and_push() {
  local story_key="$1"

  log ""
  log "────────────────────────────────────────────────────────────"
  log "  GIT: Committing and pushing ($story_key)"
  log "────────────────────────────────────────────────────────────"

  # Stage all changes including new untracked files
  git add -A 2>&1 | tee -a "$LOG_FILE"

  # Check if there's anything to commit
  if git diff --cached --quiet 2>/dev/null; then
    log "  GIT: No changes to commit."
    return 0
  fi

  local commit_msg
  commit_msg="feat(story): complete lifecycle for ${story_key}

Automated story cycle:
- Story creation (Gemini)
- 4x adversarial review passes (Claude/Gemini alternating)
- Dev story implementation (Gemini)
- 4x code review passes (Claude/Gemini alternating)

Co-Authored-By: run-story-cycle.sh <automation@bmad>"

  git commit -m "$commit_msg" 2>&1 | tee -a "$LOG_FILE"
  local rc=$?
  if [[ "$rc" -ne 0 ]]; then
    halt_on_error "git commit ($story_key)" "git commit" "$rc" "0"
  fi

  git push 2>&1 | tee -a "$LOG_FILE"
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    halt_on_error "git push ($story_key)" "git push" "$rc" "0"
  fi

  log "  GIT: Committed and pushed successfully."
}

# --- Process a single story through the full lifecycle ---
process_story() {
  local STORY_KEY="$1"
  local TOTAL=11

  init_log "$STORY_KEY"

  log ""
  log "╔════════════════════════════════════════════════════════════╗"
  log "  STORY LIFECYCLE: $STORY_KEY"
  log "╚════════════════════════════════════════════════════════════╝"
  log ""

  # --- Phase 1: Story Creation (skip if file already exists / ready-for-dev) ---
  STORY_FILE=$(resolve_story_file "$STORY_KEY")
  if [[ -n "$STORY_FILE" ]]; then
    log "==> Story file already exists (ready-for-dev), skipping creation: $STORY_FILE"
  else
    run_step "[1/${TOTAL}] Gemini: Create story ($STORY_KEY)" \
      "gemini -y -p '/bmad-create-story Create story ${STORY_KEY}'"

    STORY_FILE=$(resolve_story_file "$STORY_KEY")
    if [[ -z "$STORY_FILE" ]]; then
      halt_on_error "[1/${TOTAL}] Story file not found" \
        "resolve_story_file ${STORY_KEY}" "1" "0"
    fi
    log "==> Story file created: $STORY_FILE"
  fi

  # --- Phase 2: Adversarial Story Reviews (4 passes) ---
  run_step "[2/${TOTAL}] Claude: Adversarial review (pass 1)" \
    "claude --dangerously-skip-permissions -p --verbose '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'"

  run_step "[3/${TOTAL}] Gemini: Adversarial review (pass 2)" \
    "gemini -y -p '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'"

  run_step "[4/${TOTAL}] Claude: Adversarial review (pass 3)" \
    "claude --dangerously-skip-permissions -p --verbose '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'"

  run_step "[5/${TOTAL}] Gemini: Adversarial review (pass 4)" \
    "gemini -y -p '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'"

  # --- Phase 3: ATDD — Generate acceptance tests before implementation ---
  run_step "[6/${TOTAL}] Claude: ATDD test generation ($STORY_KEY)" \
    "claude --dangerously-skip-permissions -p --verbose '/bmad-testarch-atdd Generate failing acceptance tests for story: ${STORY_FILE}'"

  # --- Phase 4: Dev Story (Implementation) ---
  run_step "[7/${TOTAL}] Gemini: Dev story ($STORY_KEY)" \
    "gemini -y -p '/bmad-dev-story Implement story: ${STORY_FILE}'"

  # --- Phase 5: Code Review Cycle (4 passes) ---
  run_step "[8/${TOTAL}] Claude: Code review (pass 1)" \
    "claude --dangerously-skip-permissions -p --verbose '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'"

  run_step "[9/${TOTAL}] Gemini: Code review (pass 2)" \
    "gemini -y -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'"

  run_step "[10/${TOTAL}] Claude: Code review (pass 3)" \
    "claude --dangerously-skip-permissions -p --verbose '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'"

  run_step "[11/${TOTAL}] Gemini: Code review (pass 4)" \
    "gemini -y -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'"

  # --- Phase 5: Git commit + push ---
  git_commit_and_push "$STORY_KEY"

  log ""
  log "╔════════════════════════════════════════════════════════════╗"
  log "  COMPLETE: $STORY_KEY"
  log "  Log: $LOG_FILE"
  log "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
  log "╚════════════════════════════════════════════════════════════╝"
  log ""
}

# --- Main ---
if [[ -n "${1:-}" ]]; then
  process_story "$1"
else
  STORIES=$(get_pending_stories)
  if [[ -z "$STORIES" ]]; then
    echo "ERROR: No in-progress epic or no pending stories (backlog/ready-for-dev) found."
    exit 1
  fi

  STORY_COUNT=$(echo "$STORIES" | wc -l)
  CURRENT=0
  echo "============================================"
  echo "  Processing $STORY_COUNT backlog stories"
  echo "============================================"

  while IFS= read -r story; do
    CURRENT=$(( CURRENT + 1 ))
    echo ""
    echo ">>> Story $CURRENT of $STORY_COUNT <<<"
    process_story "$story"
  done <<< "$STORIES"

  echo ""
  echo "============================================"
  echo "  All $STORY_COUNT stories processed!"
  echo "============================================"
fi
