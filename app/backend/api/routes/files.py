"""Uploaded file parsing and retrieval endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.backend.schemas.file_context import UploadedFileSummary
from app.backend.services.file_context_service import (
    FileContextService,
    get_file_context_service,
)

router = APIRouter()


@router.post("", response_model=UploadedFileSummary, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    service: FileContextService = Depends(get_file_context_service),
) -> UploadedFileSummary:
    """Upload and parse one file for later task retrieval."""
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(data) > service.settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Uploaded file is too large. "
                f"Limit is {service.settings.upload_max_bytes} bytes."
            ),
        )
    return service.save_upload(
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        data=data,
    )


@router.get("", response_model=list[UploadedFileSummary])
def list_files(
    service: FileContextService = Depends(get_file_context_service),
) -> list[UploadedFileSummary]:
    """List uploaded files."""
    return service.list_files()


@router.get("/{file_id}", response_model=UploadedFileSummary)
def get_file(
    file_id: str,
    service: FileContextService = Depends(get_file_context_service),
) -> UploadedFileSummary:
    """Return metadata for one uploaded file."""
    summary = service.get_file(file_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown file '{file_id}'.",
        )
    return summary


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    service: FileContextService = Depends(get_file_context_service),
) -> None:
    """Delete one uploaded file and its parsed index."""
    if not service.delete_file(file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown file '{file_id}'.",
        )
