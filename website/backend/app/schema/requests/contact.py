"""Request schemas for contact functionality."""

from enum import StrEnum

from pydantic import EmailStr, Field

from app.schema.common.base import CustomBaseModel


class RequestType(StrEnum):
    """Enumeration of contact request types."""

    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    TECHNICAL_SUPPORT = "technical_support"
    ACCOUNT_ISSUE = "account_issue"
    GENERAL_INQUIRY = "general_inquiry"
    OTHER = "other"


class ContactRequest(CustomBaseModel):
    """Schema for contact form submission."""

    email: EmailStr = Field(..., description="Email address of the sender")
    request_type: RequestType = Field(..., description="Type of contact request")
    message: str = Field(
        ..., min_length=10, max_length=5000, description="Message content"
    )
