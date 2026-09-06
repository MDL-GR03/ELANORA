from app.schema.common.base import CustomBaseModel


class ElanFileMediaResponse(CustomBaseModel):
    """Response schema for ELAN file media information."""

    media_id: int
    media_url: str
    relative_media_url: str | None = None
    mime_type: str | None = None


class ElanFileWithMediaResponse(CustomBaseModel):
    """Response schema for ELAN file with associated media filenames."""

    elan_id: int
    filename: str
    file_path: str
    media_filenames: list[str]  # This should match what we're providing


class ProjectFilesWithMediaResponse(CustomBaseModel):
    """Response schema for project files with their associated media."""

    files: list[ElanFileWithMediaResponse]
