from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ----------------------------
# Shared enums / literals
# ----------------------------

Severity = Literal["blocker", "major", "minor", "nit"]
Category = Literal[
    "architecture",
    "tests",
    "dependencies",
    "performance",
    "clarity",
    "security",
    "process",
    "other",
]
OverallAssessment = Literal["pass", "revise", "block"]

ALLOWED_CATEGORIES = {
    "architecture", "tests", "dependencies", "performance",
    "clarity", "security", "process", "other",
}

CATEGORY_NORMALIZATION = {
    "completeness": "process",
    "hardening": "process",
    "planning": "process",
    "test": "tests",
    "testing": "tests",
    "perf": "performance",
    "dependency": "dependencies",
    "deps": "dependencies",
}


# ----------------------------
# Beads delta (actionable ops)
# ----------------------------

class BeadsDelta(BaseModel):
    """
    A structured description of changes to your Beads graph.

    Intended to be translatable into your Beads/CLI operations.
    """
    model_config = ConfigDict(extra="forbid")

    action: Literal["add", "modify", "remove"]
    bead_type: Literal["epic", "task", "gate", "note"]

    # For add operations, parent is usually required.
    parent: Optional[str] = None

    # For modify/remove operations, bead_id is usually required.
    bead_id: Optional[str] = None

    # Optional title (useful for add)
    title: Optional[str] = None

    details: str


# ----------------------------
# Reviewer output schema
# ----------------------------

class Issue(BaseModel):
    """
    One review issue. Must be grounded and falsifiable where possible.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable within this reviewer output, e.g. ISSUE-001")
    severity: Severity
    category: Category

    @field_validator("category", mode="before")
    @classmethod
    def coerce_category(cls, v: object) -> str:
        if v is None:
            return "other"
        if isinstance(v, str):
            key = v.strip().lower()
            if key in ALLOWED_CATEGORIES:
                return key
            if key in CATEGORY_NORMALIZATION:
                return CATEGORY_NORMALIZATION[key]
        return "other"

    location: str = Field(..., description="Heading/task id/path reference")
    evidence: str = Field(..., description="Short quote or precise pointer")

    problem: str
    recommendation: str

    suggested_patch: Optional[str] = Field(
        default=None,
        description="Optional patch-like snippet or replacement text.",
    )

    proposed_gate: Optional[str] = Field(
        default=None,
        description="Optional falsifiable test/gate idea (helpful for must-fix promotion).",
    )

    questions: List[str] = Field(default_factory=list)


class ReviewerOutput(BaseModel):
    """
    The required JSON format that ChatGPT/Gemini must return.
    """
    model_config = ConfigDict(extra="forbid")

    model: str  # free-form identifier, since providers vary
    overall_assessment: OverallAssessment

    scores: Dict[str, int] = Field(
        ...,
        description="Rubric scores: correctness, completeness, testability, risk, maintainability (1-5).",
    )

    issues: List[Issue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    beads_deltas: List[BeadsDelta] = Field(default_factory=list)

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v: Dict[str, int]) -> Dict[str, int]:
        required = {"correctness", "completeness", "testability", "risk", "maintainability"}
        if set(v.keys()) != required:
            missing = sorted(required - set(v.keys()))
            extra = sorted(set(v.keys()) - required)
            raise ValueError(f"scores keys must be exactly {sorted(required)}; missing={missing}, extra={extra}")
        for k, val in v.items():
            if not isinstance(val, int) or not (1 <= val <= 5):
                raise ValueError(f"scores['{k}'] must be int in [1,5]; got {val!r}")
        return v


# ----------------------------
# Moderator state schema
# ----------------------------

class SourceRef(BaseModel):
    """
    Traceability back to reviewer issues.
    """
    model_config = ConfigDict(extra="forbid")

    reviewer: Literal["chatgpt", "gemini", "claude"]
    issue_id: str


class StateItem(BaseModel):
    """
    A merged/moderated representation of a single topic/issue/dispute.
    """
    model_config = ConfigDict(extra="forbid")

    topic: str
    location: str
    evidence: str
    sources: List[SourceRef] = Field(..., min_length=1)


class Agreement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: StateItem
    recommended_action: str
    beads_deltas: List[BeadsDelta] = Field(default_factory=list)


class MustFix(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: StateItem
    severity: Severity
    recommended_action: str
    beads_deltas: List[BeadsDelta] = Field(default_factory=list)


class NeedsVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: StateItem
    reason: str


class DisputePositions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chatgpt: Optional[str] = None
    gemini: Optional[str] = None
    claude: Optional[str] = None


class DisputeOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option: str
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    cost: Optional[str] = None  # free-form: "low/med/high" or notes
    beads_deltas: List[BeadsDelta] = Field(default_factory=list)


class Dispute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    item: StateItem
    positions: DisputePositions
    decision_needed: bool = True
    options: List[DisputeOption] = Field(..., min_length=2)
    tie_break_question: str


class ReviewState(BaseModel):
    """
    The moderated, compact state used to decide stop/continue and to drive follow-up turns.
    """
    model_config = ConfigDict(extra="forbid")

    artifact_path: str
    artifact_sha256: str
    reference_paths: List[str]
    reference_sha256: str

    turn: int

    agreements: List[Agreement] = Field(default_factory=list)
    must_fix: List[MustFix] = Field(default_factory=list)
    needs_verification: List[NeedsVerification] = Field(default_factory=list)
    disputes: List[Dispute] = Field(default_factory=list)

    stop_recommendation: Literal["stop", "continue"]
