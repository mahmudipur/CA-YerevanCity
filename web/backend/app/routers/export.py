from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ..dependencies import get_current_user
from ..services import csv_service
from ..services.user_store import AuthedUser

router = APIRouter(prefix="/api/sessions", tags=["export"])


@router.get("/{split_id}/csv")
def download_csv(split_id: str, user: AuthedUser = Depends(get_current_user)):
    path = csv_service.generate(user.id, split_id)
    return FileResponse(path, media_type="text/csv", filename=f"report_{split_id}.csv")
