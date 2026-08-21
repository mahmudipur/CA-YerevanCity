from fastapi import APIRouter

from ..services import edit_adapter, persistence
from ..services.session_view import to_view

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history():
    return persistence.list_splits()


@router.get("/{split_id}")
def get_history_item(split_id: str):
    return persistence.load_split(split_id)


@router.post("/{split_id}/edit")
def edit_history_item(split_id: str):
    """Re-open a saved split as an editable session. Saving it again writes
    back to the same split_{id}.json, so this is an in-place edit."""
    session = edit_adapter.start_edit(split_id)
    return to_view(session)
