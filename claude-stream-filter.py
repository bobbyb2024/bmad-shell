#!/usr/bin/env python3
"""
Filter for: claude --print --verbose --output-format stream-json

Reads stream-json lines from stdin and outputs human-readable text in real-time.
Extracts: assistant text, tool calls, tool results, cost, and duration.
Suppresses: hooks, system init, rate limits, and other noise.
"""
import json
import sys

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        msg_type = obj.get("type", "")
        subtype = obj.get("subtype", "")

        # --- Assistant message: extract text and tool calls ---
        if msg_type == "assistant":
            message = obj.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    print(block["text"], flush=True)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    tool_input = block.get("input", {})
                    print(f"\n>>> [Tool: {name}]", flush=True)
                    # Show key details for common tools
                    if name in ("Read", "Glob", "Grep"):
                        target = tool_input.get("file_path") or tool_input.get("pattern") or tool_input.get("path", "")
                        if target:
                            print(f"    {target}", flush=True)
                    elif name in ("Edit", "Write"):
                        fp = tool_input.get("file_path", "")
                        if fp:
                            print(f"    {fp}", flush=True)
                    elif name == "Bash":
                        cmd = tool_input.get("command", "")
                        if cmd:
                            print(f"    $ {cmd[:120]}", flush=True)

        # --- Streaming text deltas ---
        elif msg_type == "content_block_delta":
            delta = obj.get("delta", {})
            if delta.get("type") == "text_delta":
                print(delta.get("text", ""), end="", flush=True)

        # --- Tool results (verbose mode) ---
        elif msg_type == "tool_result":
            tool_name = obj.get("tool_name", "")
            content = obj.get("content", "")
            if tool_name:
                # Truncate long results
                preview = str(content)[:200]
                if len(str(content)) > 200:
                    preview += "..."
                print(f"    ← [{tool_name}] {preview}", flush=True)

        # --- Final result: show summary ---
        elif msg_type == "result":
            result_text = obj.get("result", "")
            if isinstance(result_text, str) and result_text:
                print(f"\n{result_text}", flush=True)
            elif isinstance(result_text, dict):
                for block in result_text.get("content", []):
                    if block.get("type") == "text":
                        print(block["text"], flush=True)

            cost = obj.get("total_cost_usd")
            duration = obj.get("duration_ms")
            num_turns = obj.get("num_turns", "?")
            parts = []
            if cost is not None:
                parts.append(f"${cost:.4f}")
            if duration is not None:
                parts.append(f"{duration/1000:.1f}s")
            parts.append(f"{num_turns} turns")
            print(f"\n>>> [Claude finished: {', '.join(parts)}]", flush=True)

        # --- System messages: only show init (skip hooks, noise) ---
        elif msg_type == "system":
            if subtype == "init":
                model = obj.get("model", "unknown")
                print(f">>> [Session started: {model}]", flush=True)
            # Skip: hook_started, hook_response, etc.

        # --- Skip rate_limit_event silently ---
        elif msg_type == "rate_limit_event":
            pass

    except json.JSONDecodeError:
        # Not JSON — pass through raw
        print(line, flush=True)
    except (KeyError, TypeError):
        pass
