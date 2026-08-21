"""In-progress split wizard state. Plain dataclass — not an API response model.

Mirrors the terminal flow's state: roster -> items -> per-item assignment ->
fee allocation/totals -> payment -> save. Kept entirely in memory; the
canonical split_{id}.json is only written on "save", exactly like the CLI
(an aborted session loses progress in the terminal too).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional


@dataclass
class SplitSession:
    session_id: str
    kind: Literal["yc", "manual"]
    order_id: Optional[str] = None          # for kind == "yc"
    session_name: Optional[str] = None       # for kind == "manual"
    order: Optional[dict] = None              # full order dict, kind == "yc"
    participants: list = field(default_factory=list)
    items: list = field(default_factory=list)   # raw item dicts, in display order
    assigned: dict = field(default_factory=dict)  # str(index) -> {assignments, assignment_weights, split_method}
    fee_allocations: Optional[dict] = None
    totals: Optional[dict] = None
    currency: Optional[dict] = None
    saved_path: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def active_items(self) -> list:
        return [it for it in self.items if not it.get("is_canceled")]

    def is_fully_assigned(self) -> bool:
        active = self.active_items()
        return len(self.assigned) >= len(active) and all(
            str(i) in self.assigned for i in range(len(active))
        )

    def assembled_items(self) -> list:
        """Active items merged with their stored assignment, in order."""
        out = []
        for i, item in enumerate(self.active_items()):
            rec = self.assigned.get(str(i))
            if rec is None:
                continue
            out.append({**item, **rec})
        return out
