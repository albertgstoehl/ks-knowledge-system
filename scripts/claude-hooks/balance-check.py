#!/usr/bin/env python3
"""Claude Code hook to enforce Balance session requirement.

Blocks Claude Code unless an active Pomodoro session is running.
Prompts user to start a session if none is active.
"""

import sys
import json
from urllib.request import urlopen, Request
from urllib.error import URLError

BALANCE_URL = "https://balance.gstoehl.dev"


def api_get(endpoint: str) -> dict:
    """GET request to Balance API."""
    try:
        with urlopen(f"{BALANCE_URL}{endpoint}", timeout=5) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Can't reach Balance: {e}", file=sys.stderr)
        sys.exit(2)


def api_post(endpoint: str, data: dict) -> dict:
    """POST request to Balance API."""
    try:
        req = Request(
            f"{BALANCE_URL}{endpoint}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except URLError as e:
        print(f"Can't reach Balance: {e}", file=sys.stderr)
        sys.exit(2)


def prompt_start_session() -> bool:
    """Prompt user to start a session. Returns True if session started."""
    import sys

    # Check if we have a TTY for interactive input
    if not sys.stdin.isatty():
        # Non-interactive mode - show helpful message
        print("\n" + "=" * 45)
        print("  NO ACTIVE SESSION")
        print("=" * 45)
        print()
        print("  Start a session at:")
        print(f"  {BALANCE_URL}")
        print()
        print("  Or run this in terminal:")
        print("  python3 ~/.claude/hooks/balance-check.py")
        print("=" * 45 + "\n")
        return False

    # Interactive mode
    print("\n" + "=" * 45)
    print("No active session.")
    print()

    # Ask to start
    try:
        answer = input("Start one now? [y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if answer != "y":
        return False

    # Get type
    print()
    try:
        type_input = input("Type: [E]xpected / [P]ersonal: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if type_input in ("e", "expected"):
        session_type = "expected"
    elif type_input in ("p", "personal"):
        session_type = "personal"
    else:
        print("Invalid type. Use 'e' or 'p'.")
        return False

    # Get intention
    print()
    try:
        intention = input("Intention (3 words): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    if not intention:
        print("Intention required.")
        return False

    # Start the session
    result = api_post("/api/session/quick-start", {
        "type": session_type,
        "intention": intention
    })

    if result.get("success"):
        print()
        print("Session started. 25:00 remaining.")
        print("=" * 45 + "\n")
        return True
    else:
        reason = result.get("reason", "unknown error")
        if reason == "on_break":
            remaining = result.get("remaining", 0)
            mins, secs = divmod(remaining, 60)
            print(f"Break in progress. {mins}:{secs:02d} remaining.")
        else:
            print(f"Can't start session: {reason}")
        print("=" * 45 + "\n")
        return False


def main():
    # Check session status
    status = api_get("/api/session/active")

    if status.get("allowed"):
        # Session active - mark Claude usage and proceed
        api_post("/api/session/mark-claude-used", {})
        sys.exit(0)

    # Not allowed - check reason
    reason = status.get("reason")

    if reason == "on_break":
        remaining = status.get("break_remaining", 0)
        mins, secs = divmod(remaining, 60)
        print(f"\n=== Break in progress. {mins}:{secs:02d} remaining. ===\n", file=sys.stderr)
        sys.exit(2)

    # No session - prompt to start one
    if prompt_start_session():
        # Session started successfully - mark and proceed
        api_post("/api/session/mark-claude-used", {})
        sys.exit(0)
    else:
        print("Start a session to use Claude.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
