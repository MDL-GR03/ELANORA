"""Per-project data governance contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.model.enums import DataClassification

MIN_RETENTION_DAYS = 30


class ProjectDataGovernance(BaseModel):
    """What an administrator records about a project's research data."""

    model_config = ConfigDict(extra="forbid")

    data_classification: DataClassification | None = None
    legal_basis: str | None = Field(default=None, max_length=2000)
    retention_days: int | None = Field(default=None, ge=MIN_RETENTION_DAYS, le=36_500)
    legal_hold: bool = False
    legal_hold_reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def complete_for_its_sensitivity(self) -> "ProjectDataGovernance":
        """Personal data needs a legal basis; a legal hold needs a reason."""
        self.legal_basis = (self.legal_basis or "").strip() or None
        self.legal_hold_reason = (self.legal_hold_reason or "").strip() or None
        if (
            self.data_classification == DataClassification.SENSITIVE_PERSONAL
            and self.legal_basis is None
        ):
            raise ValueError("sensitive personal data requires a legal basis")
        if self.legal_hold and self.legal_hold_reason is None:
            raise ValueError("a legal hold requires a reason")
        return self


class ProjectDataGovernanceResponse(ProjectDataGovernance):
    """Recorded governance, with who last changed it."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    updated_at: datetime | None = None
    updated_by: int | None = None
