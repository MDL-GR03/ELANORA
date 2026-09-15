from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

from .enums import InvitationStatus, ProjectPermission

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class Invitation(Base):
    """Invitation model representing project invitations."""

    __tablename__ = "INVITATION"

    invitation_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    project_permission: Mapped[ProjectPermission] = mapped_column(
        String(20), nullable=False, default=ProjectPermission.READ
    )
    hashed_code: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        SQLEnum(InvitationStatus), nullable=False, default=InvitationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sender: Mapped[int] = mapped_column(
        Integer, ForeignKey("USER.user_id"), nullable=False
    )
    receiver: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id"), nullable=True
    )
    receiver_email: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    sender_user: Mapped["User"] = relationship(
        "User", foreign_keys=[sender], back_populates="sent_invitations"
    )
    receiver_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[receiver], back_populates="received_invitations"
    )
    project: Mapped["Project"] = relationship("Project", back_populates="invitations")

    def __repr__(self) -> str:
        """Return a string representation of the Invitation."""
        return f"<Invitation(invitation_id='{self.invitation_id}', status='{self.status}')>"
