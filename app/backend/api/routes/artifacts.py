"""Generated document artifact endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.backend.schemas.artifacts import ArtifactExportRequest, ArtifactSummary
from app.backend.services.artifact_service import ArtifactService, get_artifact_service

router = APIRouter()


@router.post("/export", response_model=ArtifactSummary, status_code=status.HTTP_201_CREATED)
def export_artifact(
    payload: ArtifactExportRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactSummary:
    """Export content to MD/PDF/DOCX/TEX."""
    try:
        return service.export(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ArtifactSummary])
def list_artifacts(
    service: ArtifactService = Depends(get_artifact_service),
) -> list[ArtifactSummary]:
    """List generated artifacts."""
    return service.list_artifacts()


@router.get("/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> FileResponse:
    """Download one generated artifact."""
    download = service.get_download(artifact_id)
    if download is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown artifact '{artifact_id}'.",
        )
    summary, path = download
    return FileResponse(
        path,
        media_type=summary.mime_type,
        filename=summary.filename,
    )


@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> None:
    """Delete one generated artifact."""
    if not service.delete(artifact_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown artifact '{artifact_id}'.",
        )
