#!/usr/bin/env bash
# ============================================================================
# kill-step.sh — Kill the currently running story-cycle step
#
# Usage:
#   ./kill-step.sh          # kill current step (reads from pidfile)
#   ./kill-step.sh <PID>    # kill a specific PID and its children
# ============================================================================

PIDFILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.story-cycle-step.pid"

if [[ -n "${1:-}" ]]; then
  TARGET_PID="$1"
elif [[ -f "$PIDFILE" ]]; then
  TARGET_PID=$(cat "$PIDFILE")
else
  echo "No running step found (no pidfile and no PID argument)."
  echo "Usage: ./kill-step.sh [PID]"
  exit 1
fi

echo "Killing step process tree (PID: $TARGET_PID)..."

# Kill the entire process group/tree
# First try SIGTERM for graceful shutdown
pkill -TERM -P "$TARGET_PID" 2>/dev/null
kill -TERM "$TARGET_PID" 2>/dev/null

# Wait briefly then force-kill any survivors
sleep 2
if kill -0 "$TARGET_PID" 2>/dev/null; then
  echo "Process still alive — sending SIGKILL..."
  pkill -KILL -P "$TARGET_PID" 2>/dev/null
  kill -KILL "$TARGET_PID" 2>/dev/null
fi

rm -f "$PIDFILE"
echo "Done. The story-cycle script will detect the failure and halt for review."
