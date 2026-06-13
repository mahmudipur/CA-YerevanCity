import sys
from pathlib import Path

# Make tools/ importable as top-level modules (split_math, interactive, ...)
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
