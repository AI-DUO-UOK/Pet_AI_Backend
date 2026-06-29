from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/google-maps")
async def get_google_maps_key():
    """Return the Google Maps API key for the frontend."""
    key = os.getenv("NEXT_PUBLIC_GOOGLE_MAPS_API_KEY", "")
    if not key:
        return JSONResponse(status_code=404, content={"error": "Google Maps API key not configured"})
    return {"key": key}
