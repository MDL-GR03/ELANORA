from app.schema.common.base import CustomBaseModel


class ElanFileWithMediaResponse(CustomBaseModel):
    """Response schema for ELAN file with associated media filenames."""

    elan_id: int
    filename: str
    file_path: str
    media_filenames: list[str]  # This should match what we're providing


class ProjectFilesWithMediaResponse(CustomBaseModel):
    """Response schema for project files with their associated media."""

    files: list[ElanFileWithMediaResponse]
