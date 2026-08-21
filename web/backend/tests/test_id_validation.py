"""IDs that become part of a filename must be restricted to a safe
character set, now that the server may be reachable beyond localhost."""

import pytest
from fastapi import HTTPException

from app.services.persistence import validate_id


def test_normal_ids_pass():
    for ok in ["KM0030169110", "edit_smoke_cafe", "FIXTURE-1", "a" * 128]:
        assert validate_id(ok) == ok


@pytest.mark.parametrize("bad", [
    "../../etc/passwd",
    "..",
    "a/b",
    "a\\b",
    "",
    "a" * 129,
    "a b",
    "a.json",
])
def test_unsafe_ids_rejected(bad):
    with pytest.raises(HTTPException) as exc:
        validate_id(bad)
    assert exc.value.status_code == 400


def test_history_endpoint_never_leaks_file_contents_via_traversal_id():
    """
    Belt-and-suspenders check: even before validate_id() runs, Starlette's
    router normalizes ".." segments in the URL itself, so a traversal
    attempt never reaches the route with a literal ".." in split_id — it
    falls through to the SPA catch-all (200, index.html) instead of ever
    touching the filesystem outside .tmp/. Assert on the one thing that
    actually matters: no /etc/passwd content ever comes back.
    """
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/history/..%2f..%2f..%2fetc%2fpasswd")
    assert "root:" not in resp.text
