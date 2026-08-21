from fastapi import APIRouter
from fastapi.responses import FileResponse

from ..services import csv_service

router = APIRouter(prefix="/api/sessions", tags=["export"])


@router.get("/{split_id}/csv")
def download_csv(split_id: str):
    path = csv_service.generate(split_id)
    return FileResponse(path, media_type="text/csv", filename=f"report_{split_id}.csv")
