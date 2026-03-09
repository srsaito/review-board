"""
review_board.cli

CLI entry points for the review-board package.
"""

from __future__ import annotations

import argparse
import json
import sys

from review_board.bridge import (
    DEFAULT_CHATGPT_MODEL,
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_GEMINI_MODEL,
    run_review,
)
from review_board.validator import validate_state


def main_review() -> None:
    """Entry point for `review-board` CLI command."""
    ap = argparse.ArgumentParser(
        prog="review-board",
        description="Multi-model code review bridge (ChatGPT + Gemini + optional Claude CLI)",
    )
    ap.add_argument("artifact_path", help="Path to the artifact to review")
    ap.add_argument(
        "--reference-docs",
        required=True,
        help="Comma-separated reference doc paths",
    )
    ap.add_argument("--out-base", default="docs/reviews",
                    help="Base directory for review session output (default: docs/reviews)")
    ap.add_argument("--chatgpt-model", default=DEFAULT_CHATGPT_MODEL)
    ap.add_argument("--gemini-model", default=DEFAULT_GEMINI_MODEL)
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--api-base", default="http://127.0.0.1:4000",
                    help="LiteLLM proxy base URL (default: http://127.0.0.1:4000)")
    ap.add_argument("--claude-reviewer", action="store_true",
                    help="Enable Claude Code CLI as third reviewer (uses subscription)")
    ap.add_argument("--claude-model", default=DEFAULT_CLAUDE_MODEL,
                    help="Claude model for CLI reviewer (sonnet|opus|haiku)")
    args = ap.parse_args()

    ref_paths = [p.strip() for p in args.reference_docs.split(",")]

    result = run_review(
        artifact_path=args.artifact_path,
        reference_docs=ref_paths,
        out_base=args.out_base,
        chatgpt_model=args.chatgpt_model,
        gemini_model=args.gemini_model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        api_base=args.api_base,
        claude_reviewer=args.claude_reviewer,
        claude_model=args.claude_model,
    )

    print(json.dumps(result))
    sys.exit(2 if result["status"] == "error" else 0)


def main_validate() -> None:
    """Entry point for `validate-state` CLI command."""
    ap = argparse.ArgumentParser(
        prog="validate-state",
        description="Validate a review state JSON file against the Pydantic schema",
    )
    ap.add_argument("state_json_path", help="Path to state_turnN.json file")
    args = ap.parse_args()

    try:
        validate_state(args.state_json_path)
    except Exception as e:
        print(f"VALIDATION FAILED: {e}", file=sys.stderr)
        sys.exit(1)
