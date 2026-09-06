from pydantic import BaseModel


class FileTypeLocationOut(BaseModel):
    id: int
    project_id: int
    location_id: int
    project_file_type_id: int


class AddFileTypeToLocationResponse(BaseModel):
    success: bool
    file_type: FileTypeLocationOut


class RemoveFileTypeFromLocationResponse(BaseModel):
    success: bool
    removed: int


class GetFileTypesForLocationResponse(BaseModel):
    file_types: list[FileTypeLocationOut]
