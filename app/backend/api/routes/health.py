"""Health-check endpoint for the local backend service."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return a minimal liveness payload."""
    return {"status": "ok", "service": "mindforge"}
