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
#   ./run-story-cycle.sh                    # process all (prompts to resume if applicable)
#   ./run-story-cycle.sh --resume           # auto-resume without prompting
#   ./run-story-cycle.sh --fresh            # start fresh, discard any saved progress
#   ./run-story-cycle.sh [story-key]        # process a single story from step 1
#   ./run-story-cycle.sh [story-key] --resume  # resume a specific story
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPRINT_STATUS="_bmad-output/implementation-artifacts/sprint-status.yaml"
STORY_DIR="_bmad-output/implementation-artifacts"
STEP_TIMEOUT=1800  # 30 minutes per CLI invocation
PIDFILE="${SCRIPT_DIR}/.story-cycle-step.pid"
PROGRESS_FILE="${SCRIPT_DIR}/.story-cycle-progress"

# --- Parse flags ---
RESUME_MODE=""  # "auto", "fresh", or "" (prompt)
STORY_ARG=""
for arg in "$@"; do
  case "$arg" in
    --resume)   RESUME_MODE="auto" ;;
    --fresh|--no-resume) RESUME_MODE="fresh" ;;
    --help|-h)
      echo "Usage: ./run-story-cycle.sh [options] [story-key]"
      echo ""
      echo "Options:"
      echo "  --resume       Auto-resume from last checkpoint (no prompt)"
      echo "  --fresh        Start fresh, discard saved progress"
      echo "  --no-resume    Alias for --fresh"
      echo "  -h, --help     Show this help"
      echo ""
      echo "Examples:"
      echo "  ./run-story-cycle.sh                  # prompts if progress exists"
      echo "  ./run-story-cycle.sh --resume         # auto-resume"
      echo "  ./run-story-cycle.sh --fresh          # ignore progress, start over"
      echo "  ./run-story-cycle.sh 3-4-cycle-engine # run single story"
      exit 0
      ;;
    -*)
      echo "Unknown flag: $arg (try --help)"
      exit 1
      ;;
    *)  STORY_ARG="$arg" ;;
  esac
done

# Clean up pidfile on exit
cleanup_pidfile() {
  rm -f "$PIDFILE"
}
trap cleanup_pidfile EXIT

# --- Progress tracking ---
# Writes: story_key, step_number, step_label, timestamp
save_progress() {
  local story_key="$1" step_num="$2" step_label="$3"
  cat > "$PROGRESS_FILE" <<EOF
story_key="$story_key"
step_completed="$step_num"
step_label="$step_label"
timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
started="$(date '+%Y-%m-%d %H:%M:%S')"
EOF
}

clear_progress() {
  rm -f "$PROGRESS_FILE"
}

# Returns the step number to resume FROM (the next step after last completed)
# Sets RESUME_STORY and RESUME_STEP globals. Returns 1 if no resume.
# Respects RESUME_MODE: "auto" (skip prompt), "fresh" (discard), "" (prompt).
check_resume() {
  RESUME_STORY=""
  RESUME_STEP=0

  if [[ ! -f "$PROGRESS_FILE" ]]; then
    return 1
  fi

  # --fresh: discard progress immediately
  if [[ "$RESUME_MODE" == "fresh" ]]; then
    echo "==> --fresh: discarding saved progress"
    clear_progress
    return 1
  fi

  local story_key step_completed step_label timestamp started
  source "$PROGRESS_FILE"
  RESUME_STORY="$story_key"
  RESUME_STEP=$(( step_completed + 1 ))

  echo ""
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "  Previous session found:"
  echo "  Story:     $story_key"
  echo "  Completed: Step $step_completed — $step_label"
  echo "  Time:      $timestamp"
  echo "  Started:   $started"
  echo "╚════════════════════════════════════════════════════════════╝"

  # --resume: auto-resume without prompting
  if [[ "$RESUME_MODE" == "auto" ]]; then
    echo "==> --resume: resuming $story_key from step $RESUME_STEP"
    return 0
  fi

  # Interactive prompt
  echo ""
  echo "  (r) Resume from step $RESUME_STEP"
  echo "  (s) Start fresh (discard progress)"
  echo "  (q) Quit"
  echo ""
  read -rp "Choice [r/s/q]: " choice
  case "$choice" in
    r|R|"")
      echo "==> Resuming $story_key from step $RESUME_STEP..."
      return 0
      ;;
    s|S)
      echo "==> Starting fresh..."
      clear_progress
      RESUME_STORY=""
      RESUME_STEP=0
      return 1
      ;;
    q|Q)
      echo "==> Quitting."
      exit 0
      ;;
    *)
      echo "==> Invalid choice. Quitting."
      exit 1
      ;;
  esac
}

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

# --- Run a CLI step in a separate gnome-terminal window ---
# Opens a visible terminal so you can watch output in real-time.
# The main script waits for the command to finish, then reads the exit code.
# Usage: run_step "label" "command" [story_key] [step_number]
run_step() {
  local step_label="$1"
  local cmd_str="$2"
  local story_key="${3:-}"
  local step_num="${4:-0}"

  log ""
  log "────────────────────────────────────────────────────────────"
  log "  STEP: $step_label"
  log "  CMD:  $cmd_str"
  log "  START: $(date '+%Y-%m-%d %H:%M:%S')"
  log "────────────────────────────────────────────────────────────"

  # Temp files for the wrapper script, exit code, and log capture
  local tmp_script rc_file step_log
  tmp_script=$(mktemp /tmp/story-cycle-XXXXXX.sh)
  rc_file=$(mktemp /tmp/story-cycle-rc-XXXXXX)
  step_log=$(mktemp /tmp/story-cycle-log-XXXXXX)

  # Write wrapper script: runs the command, captures exit code, waits for keypress on error
  cat > "$tmp_script" <<CMDEOF
#!/usr/bin/env bash
echo \$\$ > "$PIDFILE"
echo "──────────────────────────────────────────────"
echo "  $step_label"
echo "  PID: \$\$"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "──────────────────────────────────────────────"
echo ""

# Run command, filter claude stream-json if applicable, tee to step log
if echo "$cmd_str" | grep -q '^claude'; then
  $cmd_str 2>&1 | python3 -u "$SCRIPT_DIR/claude-stream-filter.py" | tee "$step_log"
else
  $cmd_str 2>&1 | tee "$step_log"
fi
CMD_RC=\${PIPESTATUS[0]}

echo ""
echo "──────────────────────────────────────────────"
if [ "\$CMD_RC" -eq 0 ]; then
  echo "  DONE (exit 0) — closing in 5s..."
  sleep 5
else
  echo "  FAILED (exit \$CMD_RC)"
  echo "  Press Enter to close this window..."
  read -r
fi
echo "\$CMD_RC" > "$rc_file"
CMDEOF
  chmod +x "$tmp_script"

  local start_ts
  start_ts=$(date +%s)

  # Launch in a new gnome-terminal window with a descriptive title
  gnome-terminal --title="$step_label" -- bash "$tmp_script"

  # Wait for PID file to appear then log it
  local wait_count=0
  while [[ ! -f "$PIDFILE" ]] && [[ "$wait_count" -lt 10 ]]; do
    sleep 1
    wait_count=$(( wait_count + 1 ))
  done
  if [[ -f "$PIDFILE" ]]; then
    local cli_pid
    cli_pid=$(cat "$PIDFILE")
    log "  PID:  $cli_pid  kill: ./kill-step.sh or kill $cli_pid"
  fi

  # Poll for the rc_file (written when command finishes)
  log "  Waiting for completion (watching terminal window)..."
  while [[ ! -s "$rc_file" ]]; do
    sleep 5
  done

  local rc
  rc=$(cat "$rc_file")

  # Append step log to main log
  if [[ -f "$step_log" ]]; then
    cat "$step_log" >> "$LOG_FILE"
  fi

  rm -f "$tmp_script" "$rc_file" "$step_log" "$PIDFILE"

  local end_ts
  end_ts=$(date +%s)
  local elapsed=$(( end_ts - start_ts ))

  if [[ "$rc" -ne 0 ]]; then
    halt_on_error "$step_label" "$cmd_str" "$rc" "$elapsed"
  fi

  log ""
  log "  DONE: $step_label (${elapsed}s, exit 0)"
  log ""

  # Save progress checkpoint
  if [[ -n "$story_key" && "$step_num" -gt 0 ]]; then
    save_progress "$story_key" "$step_num" "$step_label"
  fi
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

# --- Helper: get the current epic (in-progress, or promote next backlog) ---
# Returns the epic key (e.g., "epic-2") or empty if none remain.
# If no in-progress epic exists, promotes the first backlog epic to in-progress.
get_current_epic() {
  local epic
  epic=$(grep -E '^\s+epic-[0-9]+: in-progress' "$SPRINT_STATUS" | head -1 | sed 's/:.*//' | xargs || true)
  if [[ -n "$epic" ]]; then
    echo "$epic"
    return
  fi

  # No in-progress epic — promote the first backlog epic
  epic=$(grep -E '^\s+epic-[0-9]+: backlog' "$SPRINT_STATUS" | head -1 | sed 's/:.*//' | xargs || true)
  if [[ -z "$epic" ]]; then
    echo ""
    return
  fi

  echo "==> Promoting $epic to in-progress" >&2
  sed -i "s/\(${epic}\): backlog/\1: in-progress/" "$SPRINT_STATUS"
  echo "$epic"
}

# --- Helper: get the NEXT single pending story for the current epic ---
# Returns only the first story with status: backlog or ready-for-dev
get_next_story() {
  local epic epic_num
  epic=$(get_current_epic)
  if [[ -z "$epic" ]]; then
    echo ""
    return
  fi
  epic_num="${epic#epic-}"
  grep -E "^\s+${epic_num}-[0-9]+-.*: (backlog|ready-for-dev)" "$SPRINT_STATUS" | head -1 | sed 's/:.*//' | xargs || true
}

# --- Helper: mark current epic as done if no pending stories remain ---
check_epic_completion() {
  local epic epic_num remaining
  epic=$(grep -E '^\s+epic-[0-9]+: in-progress' "$SPRINT_STATUS" | head -1 | sed 's/:.*//' | xargs || true)
  if [[ -z "$epic" ]]; then
    return
  fi
  epic_num="${epic#epic-}"
  remaining=$(grep -cE "^\s+${epic_num}-[0-9]+-.*: (backlog|ready-for-dev)" "$SPRINT_STATUS" || true)
  if [[ "$remaining" -eq 0 ]]; then
    echo "==> All stories in $epic complete — marking epic as done"
    sed -i "s/\(${epic}\): in-progress/\1: done/" "$SPRINT_STATUS"
  fi
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
# Usage: process_story <story_key> [start_from_step]
process_story() {
  local STORY_KEY="$1"
  local START_STEP="${2:-1}"
  local TOTAL=11

  init_log "$STORY_KEY"

  log ""
  log "╔════════════════════════════════════════════════════════════╗"
  log "  STORY LIFECYCLE: $STORY_KEY"
  if [[ "$START_STEP" -gt 1 ]]; then
    log "  RESUMING from step $START_STEP"
  fi
  log "╚════════════════════════════════════════════════════════════╝"
  log ""

  # --- Phase 1: Story Creation (skip if file already exists / ready-for-dev) ---
  STORY_FILE=$(resolve_story_file "$STORY_KEY")
  if [[ -n "$STORY_FILE" ]]; then
    log "==> Story file already exists (ready-for-dev), skipping creation: $STORY_FILE"
  elif [[ "$START_STEP" -le 1 ]]; then
    run_step "[1/${TOTAL}] Gemini: Create story ($STORY_KEY)" \
      "gemini -y -p '/bmad-create-story Create story ${STORY_KEY}'" \
      "$STORY_KEY" 1

    STORY_FILE=$(resolve_story_file "$STORY_KEY")
    if [[ -z "$STORY_FILE" ]]; then
      halt_on_error "[1/${TOTAL}] Story file not found" \
        "resolve_story_file ${STORY_KEY}" "1" "0"
    fi
    log "==> Story file created: $STORY_FILE"
  else
    STORY_FILE=$(resolve_story_file "$STORY_KEY")
    if [[ -z "$STORY_FILE" ]]; then
      halt_on_error "Resume failed — story file not found" \
        "resolve_story_file ${STORY_KEY}" "1" "0"
    fi
    log "==> Story file (resumed): $STORY_FILE"
  fi

  # --- Phase 2: Adversarial Story Reviews (4 passes) ---
  if [[ "$START_STEP" -le 2 ]]; then
    run_step "[2/${TOTAL}] Claude: Adversarial review (pass 1)" \
      "claude --dangerously-skip-permissions --print --verbose --output-format stream-json -p 'bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 2
  fi

  if [[ "$START_STEP" -le 3 ]]; then
    run_step "[3/${TOTAL}] Gemini: Adversarial review (pass 2)" \
      "gemini --model=gemini-3.1-pro-preview -y -p '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 3
  fi

  if [[ "$START_STEP" -le 4 ]]; then
    run_step "[4/${TOTAL}] Claude: Adversarial review (pass 3)" \
      "claude --dangerously-skip-permissions --print --verbose --output-format stream-json -p '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 4
  fi

  if [[ "$START_STEP" -le 5 ]]; then
    run_step "[5/${TOTAL}] Gemini: Adversarial review (pass 4)" \
      "gemini --model=gemini-3.1-pro-preview -y -p '/bmad-review-adversarial-general Review the story file: ${STORY_FILE} — after the review, automatically apply all fixes directly to the file. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 5
  fi

  # --- Phase 3: ATDD — Generate acceptance tests before implementation ---
  if [[ "$START_STEP" -le 6 ]]; then
    run_step "[6/${TOTAL}] Claude: ATDD test generation ($STORY_KEY)" \
      "claude --dangerously-skip-permissions --print --verbose --output-format stream-json -p '/bmad-testarch-atdd Generate failing acceptance tests for story: ${STORY_FILE}'" \
      "$STORY_KEY" 6
  fi

  # --- Phase 4: Dev Story (Implementation) ---
  if [[ "$START_STEP" -le 7 ]]; then
    run_step "[7/${TOTAL}] Gemini: Dev story ($STORY_KEY)" \
      "gemini -y -p '/bmad-dev-story Implement story: ${STORY_FILE}'" \
      "$STORY_KEY" 7
  fi

  # --- Phase 5: Code Review Cycle (4 passes) ---
  if [[ "$START_STEP" -le 8 ]]; then
    run_step "[8/${TOTAL}] Claude: Code review (pass 1)" \
      "claude --dangerously-skip-permissions --print --verbose --output-format stream-json -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 8
  fi

  if [[ "$START_STEP" -le 9 ]]; then
    run_step "[9/${TOTAL}] Gemini: Code review (pass 2)" \
      "gemini --model=gemini-3.1-pro-preview -y -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 9
  fi

  if [[ "$START_STEP" -le 10 ]]; then
    run_step "[10/${TOTAL}] Claude: Code review (pass 3)" \
      "claude --dangerously-skip-permissions --print --verbose --output-format stream-json -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 10
  fi

  if [[ "$START_STEP" -le 11 ]]; then
    run_step "[11/${TOTAL}] Gemini: Code review (pass 4)" \
      "gemini --model=gemini-3.1-pro-preview -y -p '/bmad-code-review Review code for story: ${STORY_FILE} — after the review, automatically apply all fixes to the code. Do not ask for confirmation, just make the edits.'" \
      "$STORY_KEY" 11
  fi

  # --- Phase 6: Git commit + push ---
  git_commit_and_push "$STORY_KEY"
  clear_progress

  log ""
  log "╔════════════════════════════════════════════════════════════╗"
  log "  COMPLETE: $STORY_KEY"
  log "  Log: $LOG_FILE"
  log "  Finished: $(date '+%Y-%m-%d %H:%M:%S')"
  log "╚════════════════════════════════════════════════════════════╝"
  log ""
}

# --- Main ---
if [[ -n "$STORY_ARG" ]]; then
  process_story "$STORY_ARG"
else
  TOTAL_PROCESSED=0
  SKIP_TO_STORY=""
  SKIP_TO_STEP=1

  # Check for previous progress and offer resume
  if check_resume; then
    SKIP_TO_STORY="$RESUME_STORY"
    SKIP_TO_STEP="$RESUME_STEP"
  fi

  # Single loop: one story at a time, re-reading sprint-status each iteration
  MAX_LOOPS=200  # safety valve
  LOOPS=0
  while true; do
    LOOPS=$(( LOOPS + 1 ))
    if [[ "$LOOPS" -gt "$MAX_LOOPS" ]]; then
      echo "ERROR: Exceeded $MAX_LOOPS iterations — possible infinite loop. Halting."
      exit 1
    fi

    # If current in-progress epic is exhausted, mark it done
    check_epic_completion

    # Get the current (or next promoted) epic
    EPIC=$(get_current_epic)
    if [[ -z "$EPIC" ]]; then
      if [[ "$TOTAL_PROCESSED" -eq 0 ]]; then
        echo "ERROR: No epics with pending stories found."
        exit 1
      fi
      break
    fi

    # Get the next single story
    NEXT_STORY=$(get_next_story)
    if [[ -z "$NEXT_STORY" ]]; then
      # Epic has no pending stories — mark done and loop to pick up next epic
      echo "==> $EPIC has no pending stories — marking done and moving on"
      sed -i "s/\(${EPIC}\): in-progress/\1: done/" "$SPRINT_STATUS"
      continue
    fi

    TOTAL_PROCESSED=$(( TOTAL_PROCESSED + 1 ))
    echo ""
    echo "============================================"
    echo "  $EPIC — Story: $NEXT_STORY (total: $TOTAL_PROCESSED)"
    echo "============================================"

    # If resuming, check if the resume story matches or is already done
    if [[ -n "$SKIP_TO_STORY" ]]; then
      if [[ "$NEXT_STORY" == "$SKIP_TO_STORY" ]]; then
        # Found the resume story — pick up at the saved step
        process_story "$NEXT_STORY" "$SKIP_TO_STEP"
        SKIP_TO_STORY=""
        SKIP_TO_STEP=1
      else
        # Resume story doesn't match — check if it's already done
        resume_status=$(grep -E "^\s+${SKIP_TO_STORY}:" "$SPRINT_STATUS" | sed 's/.*: //' | xargs || true)
        if [[ "$resume_status" == "done" ]]; then
          # Resume story already completed — clear resume and process normally
          echo "==> Resume story $SKIP_TO_STORY already done — continuing normally"
          clear_progress
          SKIP_TO_STORY=""
          SKIP_TO_STEP=1
          process_story "$NEXT_STORY"
        else
          echo "==> Skipping $NEXT_STORY (resuming to $SKIP_TO_STORY)..."
          continue
        fi
      fi
    else
      process_story "$NEXT_STORY"
    fi
  done

  echo ""
  echo "============================================"
  echo "  All done! $TOTAL_PROCESSED stories processed."
  echo "============================================"
fi
