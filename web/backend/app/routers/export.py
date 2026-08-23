from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..dependencies import get_current_user
from ..services import csv_service, receipt_image_service
from ..services.user_store import AuthedUser

router = APIRouter(prefix="/api/sessions", tags=["export"])


@router.get("/{split_id}/csv")
def download_csv(split_id: str, user: AuthedUser = Depends(get_current_user)):
    path = csv_service.generate(user.id, split_id)
    return FileResponse(path, media_type="text/csv", filename=f"report_{split_id}.csv")


@router.get("/{split_id}/image")
def download_receipt_image(split_id: str, user: AuthedUser = Depends(get_current_user)):
    """One PNG containing every row the CSV has — meant to replace
    'open the CSV, screenshot it' for pasting into Tricount, since a
    screenshot of a scrollable spreadsheet doesn't fit on a phone."""
    path = receipt_image_service.generate(user.id, split_id)
    return FileResponse(path, media_type="image/png", filename=f"receipt_{split_id}.png")
