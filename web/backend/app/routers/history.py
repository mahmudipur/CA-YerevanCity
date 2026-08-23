from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..services import edit_adapter, persistence
from ..services.session_view import to_view
from ..services.user_store import AuthedUser

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("")
def list_history(user: AuthedUser = Depends(get_current_user)):
    return persistence.list_splits(user.id)


@router.get("/{split_id}")
def get_history_item(split_id: str, user: AuthedUser = Depends(get_current_user)):
    return persistence.load_split(user.id, split_id)


@router.post("/{split_id}/edit")
def edit_history_item(split_id: str, user: AuthedUser = Depends(get_current_user)):
    """Re-open a saved split as an editable session. Saving it again writes
    back to the same split_{id}.json, so this is an in-place edit."""
    session = edit_adapter.start_edit(user.id, split_id)
    return to_view(session)
