import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
TOOLS_DIR = REPO_ROOT / "tools"

for p in (str(BACKEND_DIR), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "order_FIXTURE.json"


def load_fixture_order() -> dict:
    return json.loads(FIXTURE_PATH.read_text())
