"""
review_board.validator

Validates a Claude-produced state_turnN.json file using Pydantic models
in review_board.schemas (authoritative schema).
"""

from __future__ import annotations

import json
from pathlib import Path

from review_board.schemas import ReviewState


def validate_state(state_json_path: str) -> None:
    """Validate a state JSON file. Raises on failure, prints OK on success."""
    data = json.loads(Path(state_json_path).read_text(encoding="utf-8"))
    ReviewState.model_validate(data)
    print("OK")
