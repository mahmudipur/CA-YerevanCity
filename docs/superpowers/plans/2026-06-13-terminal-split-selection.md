# Terminal Split: Arrow-Key Selection + Editable Items — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the typed participant/assignment prompts in `split_basket.py` and `manual_split.py` with arrow-key selection, four per-person split modes (Equal/Percentage/Amount/Part), and an after-the-walk review menu to edit any item before finalizing.

**Architecture:** Extract the pure proportional-split math plus a new structured `build_split()` into `tools/split_math.py` (no UI, fully unit-tested). Put all `questionary` UI in a new `tools/interactive.py` that calls `build_split()`. Both CLI tools call `interactive` for roster setup, per-item assignment, and review/edit. The `(assignments, assignment_weights, split_method)` output contract is preserved so fee allocation, totals, reports, and CSV are untouched.

**Tech Stack:** Python 3, `questionary` (arrow-key prompts, pulls `prompt_toolkit`), `pytest` (logic tests). Runs in the existing `.venv`.

**Dependency graph (no cycles):** `interactive.py → split_math.py`; `split_basket.py → {interactive, split_math}`; `manual_split.py → {split_basket, interactive}`.

---

## File Structure

- **Create** `tools/split_math.py` — pure logic: `_largest_remainder`, `_equal_split`, `_pct_split` (moved from `split_basket.py`), and the new `build_split()`. No `questionary` import.
- **Create** `tools/interactive.py` — `questionary` UI: `setup_roster()`, `assign_item()`, `review_and_edit()`. Imports `build_split` from `split_math`.
- **Modify** `tools/split_basket.py` — import math from `split_math`; replace temp-participant prompt + `assign_items()` loop with `interactive` calls; drop now-dead `assign_items()`/`_detect_method()`; keep `parse_assignment`/`resolve_name`.
- **Modify** `tools/manual_split.py` — use `interactive` for roster + item collection.
- **Create** `requirements.txt` — record real runtime deps + `questionary`.
- **Create** `tests/conftest.py`, `tests/test_split_math.py`, `tests/test_build_split.py`.
- **Edit (local, uncommitted)** `.env` — `DEFAULT_PARTICIPANTS=Me`.

**Method labels** (preserve existing strings; add one): Equal→`equal/all` (all roster) / `equal/partial` / `single` (one person); Percentage→`percentage`; Amount→`fixed`; Part→`ratio` (new, display-only).

---

## Task 1: Set up dependencies and test infrastructure

**Files:**
- Create: `requirements.txt`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.32.5
python-dotenv==1.2.2
requests-oauthlib==2.0.0
questionary==2.0.1
pytest==8.3.4
```

- [ ] **Step 2: Install into the existing venv**

Run: `.venv/bin/python -m pip install questionary==2.0.1 pytest==8.3.4`
Expected: ends with `Successfully installed ... questionary-2.0.1 ... pytest-8.3.4`

- [ ] **Step 3: Verify imports**

Run: `.venv/bin/python -c "import questionary, pytest; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Create `tests/conftest.py`** so tests can import modules from `tools/`

```python
import sys
from pathlib import Path

# Make tools/ importable as top-level modules (split_math, interactive, ...)
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
```

- [ ] **Step 5: Verify pytest collects an empty suite**

Run: `.venv/bin/python -m pytest -q`
Expected: `no tests ran` (exit code 5) — confirms pytest + conftest load without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/conftest.py
git commit -m "chore: add questionary+pytest deps and test bootstrap"
```

---

## Task 2: Extract pure split math into `tools/split_math.py`

Move the three proportional-split helpers out of `split_basket.py` verbatim, then re-import them so existing behavior is unchanged.

**Files:**
- Create: `tools/split_math.py`
- Modify: `tools/split_basket.py` (remove the three defs, add an import)
- Test: `tests/test_split_math.py`

- [ ] **Step 1: Write the failing test** `tests/test_split_math.py`

```python
from split_math import _largest_remainder, _equal_split, _pct_split


def test_largest_remainder_sums_to_total():
    out = _largest_remainder(694, {"a": 1, "b": 1, "c": 1})
    assert sum(out.values()) == 694
    assert sorted(out.values()) == [231, 231, 232]


def test_largest_remainder_zero_weights():
    assert _largest_remainder(100, {"a": 0, "b": 0}) == {"a": 0, "b": 0}


def test_equal_split_sums_to_total():
    out = _equal_split(["a", "b"], 1500)
    assert out == {"a": 750, "b": 750}


def test_pct_split_proportional():
    out = _pct_split({"a": 60.0, "b": 40.0}, 1000)
    assert out == {"a": 600, "b": 400}
    assert sum(out.values()) == 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_split_math.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'split_math'`

- [ ] **Step 3: Create `tools/split_math.py`** with the helpers moved from `split_basket.py` (identical bodies)

```python
"""Pure proportional-split math and structured split builder. No UI, no I/O."""

from decimal import Decimal
from functools import reduce
from math import gcd


def _largest_remainder(total: int, weights: dict) -> dict:
    """
    Split `total` (integer AMD) among keys proportionally to their weights.
    Uses the largest-remainder method so sum(result) == total always.
    """
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return {k: 0 for k in weights}
    raw = {k: Decimal(total) * Decimal(str(v)) / Decimal(str(weight_sum))
           for k, v in weights.items()}
    floored = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(floored.values())
    for k, _ in sorted(raw.items(), key=lambda x: -(x[1] % 1)):
        if remainder <= 0:
            break
        floored[k] += 1
        remainder -= 1
    assert sum(floored.values()) == total, "Rounding error"
    return floored


def _equal_split(names: list, total: int) -> dict:
    equal_weights = {n: 1 for n in names}
    return _largest_remainder(total, equal_weights)


def _pct_split(pct_dict: dict, total: int) -> dict:
    """pct_dict: {name: float_pct}. Must sum to 100."""
    return _largest_remainder(total, pct_dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_split_math.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Update `tools/split_basket.py` to import from `split_math`**

Remove the local `_largest_remainder`, `_equal_split`, `_pct_split` definitions (the block under `# ── Maths ──`, currently lines ~41-72). Replace the now-unused imports `from decimal import Decimal` / `from functools import reduce` / `from math import gcd` **only if** they become unused after later tasks — for now leave them (still used by `parse_assignment`). Add this import near the other `tools/` import:

```python
sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
from split_math import _largest_remainder, _equal_split, _pct_split
```

- [ ] **Step 6: Verify `split_basket` still imports and the old parser still works**

Run:
```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'tools')
from split_basket import parse_assignment, allocate_fees
amounts, weights = parse_assignment('a:60%,b:40%', ['a','b'], 1000)
assert amounts == {'a':600,'b':400}, amounts
assert weights == {'a':60.0,'b':40.0}, weights
print('ok')
"
```
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add tools/split_math.py tools/split_basket.py tests/test_split_math.py
git commit -m "refactor: extract split math into split_math module"
```

---

## Task 3: Add `build_split()` to `split_math.py` (the 4-mode logic)

Pure function turning structured selection input into the same `(amounts, weights, method)` shape the UI will store.

**Files:**
- Modify: `tools/split_math.py`
- Test: `tests/test_build_split.py`

- [ ] **Step 1: Write the failing test** `tests/test_build_split.py`

```python
import pytest
from split_math import build_split

P = ["Me", "Mahdi", "Amir"]


def test_equal_all():
    amounts, weights, method = build_split("equal", P, {}, 1500, P)
    assert sum(amounts.values()) == 1500
    assert weights == {"Me": 1, "Mahdi": 1, "Amir": 1}
    assert method == "equal/all"


def test_equal_partial():
    amounts, weights, method = build_split("equal", ["Me", "Amir"], {}, 1000, P)
    assert amounts == {"Me": 500, "Amir": 500}
    assert weights == {"Me": 1, "Mahdi": 0, "Amir": 1}
    assert method == "equal/partial"


def test_single():
    amounts, weights, method = build_split("equal", ["Me"], {}, 800, P)
    assert amounts == {"Me": 800}
    assert weights == {"Me": 1, "Mahdi": 0, "Amir": 0}
    assert method == "single"


def test_percentage():
    amounts, weights, method = build_split(
        "percentage", ["Me", "Amir"], {"Me": 67, "Amir": 33}, 1500, P)
    assert sum(amounts.values()) == 1500
    assert weights == {"Me": 67, "Mahdi": 0, "Amir": 33}
    assert method == "percentage"


def test_percentage_bad_sum():
    with pytest.raises(ValueError, match="100"):
        build_split("percentage", ["Me", "Amir"], {"Me": 60, "Amir": 30}, 1500, P)


def test_amount():
    amounts, weights, method = build_split(
        "amount", ["Me", "Amir"], {"Me": 1000, "Amir": 500}, 1500, P)
    assert amounts == {"Me": 1000, "Amir": 500}
    assert weights == {"Me": 2, "Mahdi": 0, "Amir": 1}  # GCD-reduced
    assert method == "fixed"


def test_amount_bad_sum():
    with pytest.raises(ValueError, match="net price"):
        build_split("amount", ["Me", "Amir"], {"Me": 1000, "Amir": 400}, 1500, P)


def test_part_ratio():
    amounts, weights, method = build_split(
        "part", ["Me", "Amir"], {"Me": 2, "Amir": 1}, 1500, P)
    assert amounts == {"Me": 1000, "Amir": 500}
    assert weights == {"Me": 2, "Mahdi": 0, "Amir": 1}
    assert method == "ratio"


def test_part_equivalent_ratios():
    a1, w1, _ = build_split("part", ["Me", "Amir"], {"Me": 4, "Amir": 2}, 1500, P)
    assert a1 == {"Me": 1000, "Amir": 500}
    assert w1 == {"Me": 2, "Mahdi": 0, "Amir": 1}


def test_empty_selection():
    with pytest.raises(ValueError, match="select"):
        build_split("equal", [], {}, 100, P)


def test_missing_value():
    with pytest.raises(ValueError, match="[Mm]issing"):
        build_split("amount", ["Me", "Amir"], {"Me": 1000}, 1500, P)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_build_split.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_split'`

- [ ] **Step 3: Append `build_split()` to `tools/split_math.py`**

```python
def build_split(mode: str, selected: list, values: dict,
                net_price: int, participants: list) -> tuple:
    """
    Turn a structured selection into (amounts, weights, method).

    mode         : "equal" | "percentage" | "amount" | "part"
    selected     : participants sharing this item (subset of `participants`)
    values       : {participant: number} for non-equal modes (keys cover `selected`)
    net_price    : item net price in integer AMD
    participants : full active roster (used to zero-fill display weights)

    Output mirrors the legacy parse_assignment contract:
      amounts : {participant: int} over the sharing people, summing to net_price
      weights : {participant: number} zero-filled across the full roster
      method  : label string for the report
    """
    # Canonical order + dedupe against the roster.
    selected = [p for p in participants if p in set(selected)]
    if not selected:
        raise ValueError("Select at least one person for this item.")

    if mode == "equal":
        amounts = _equal_split(selected, net_price)
        weights = {p: (1 if p in selected else 0) for p in participants}
        if len(selected) == len(participants):
            method = "equal/all"
        elif len(selected) == 1:
            method = "single"
        else:
            method = "equal/partial"
        return amounts, weights, method

    missing = [p for p in selected if p not in values]
    if missing:
        raise ValueError(f"Missing value for: {', '.join(missing)}")

    if mode == "percentage":
        pct_sum = sum(float(values[p]) for p in selected)
        if abs(pct_sum - 100) > 0.01:
            raise ValueError(f"Percentages sum to {pct_sum:.1f}%, must be 100%.")
        pct_map = {p: float(values[p]) for p in selected}
        amounts = _pct_split(pct_map, net_price)
        weights = {p: round(float(values[p]), 2) if p in selected else 0
                   for p in participants}
        return amounts, weights, "percentage"

    if mode == "amount":
        amounts_in = {p: int(round(float(values[p]))) for p in selected}
        total = sum(amounts_in.values())
        if total != net_price:
            raise ValueError(
                f"Amounts sum to {total:,} AMD, but item net price is "
                f"{net_price:,} AMD.")
        nonzero = [v for v in amounts_in.values() if v > 0]
        g = reduce(gcd, nonzero) if nonzero else 1
        weights = {p: amounts_in.get(p, 0) // g for p in participants}
        return amounts_in, weights, "fixed"

    if mode == "part":
        parts = {p: float(values[p]) for p in selected}
        if sum(parts.values()) <= 0:
            raise ValueError("Parts must be positive numbers.")
        amounts = _largest_remainder(net_price, parts)
        int_parts = {p: int(round(float(values[p]))) for p in selected}
        nonzero = [v for v in int_parts.values() if v > 0]
        g = reduce(gcd, nonzero) if nonzero else 1
        weights = {p: int_parts.get(p, 0) // g for p in participants}
        return amounts, weights, "ratio"

    raise ValueError(f"Unknown split mode: {mode}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_build_split.py -q`
Expected: PASS (11 passed)

- [ ] **Step 5: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (15 passed)

- [ ] **Step 6: Commit**

```bash
git add tools/split_math.py tests/test_build_split.py
git commit -m "feat: add build_split for structured 4-mode item splitting"
```

---

## Task 4: Build the questionary UI in `tools/interactive.py`

UI cannot be unit-tested without a TTY; verify by import + a manual run in Task 7. Keep all logic in `build_split` so this layer stays thin.

**Files:**
- Create: `tools/interactive.py`

- [ ] **Step 1: Create `tools/interactive.py`**

```python
"""Questionary-based terminal UI for participant selection and item splitting.

Thin presentation layer: all arithmetic/validation lives in split_math.build_split.
Each function raises KeyboardInterrupt on Ctrl-C/Esc so callers abort cleanly.
"""

import sys
from pathlib import Path

import questionary

sys.path.insert(0, str(Path(__file__).parent))
from split_math import build_split

MODES = [
    ("Equal split", "equal"),
    ("Percentage (%)", "percentage"),
    ("Amount (AMD)", "amount"),
    ("Part (ratio, e.g. 2 vs 1)", "part"),
]

VALUE_PROMPT = {
    "percentage": "%",
    "amount": "AMD",
    "part": "parts",
}


def _ask(result):
    """questionary returns None on Ctrl-C/Esc — turn that into an abort."""
    if result is None:
        raise KeyboardInterrupt
    return result


def setup_roster(default_roster: list) -> list:
    """Show the persistent default(s), prompt for temp participants, return combined."""
    print(f"  Default participants: {', '.join(default_roster)}")
    raw = _ask(questionary.text(
        "  Temporary participants? (comma-separated, Enter to skip):").ask())
    temp = [p.strip() for p in raw.split(",") if p.strip()]
    roster = default_roster + temp
    if temp:
        print(f"  Active participants: {', '.join(roster)}")
    return roster


def _prompt_values(mode: str, selected: list) -> dict:
    """Ask each selected participant for their number in the chosen mode."""
    unit = VALUE_PROMPT[mode]
    values = {}
    for p in selected:
        while True:
            raw = _ask(questionary.text(f"    {p} ({unit}):").ask()).strip()
            try:
                values[p] = float(raw)
                break
            except ValueError:
                print("    [!] Enter a number.")
    return values


def assign_item(item: dict, participants: list) -> tuple:
    """Run the per-item flow. Returns (amounts, weights, method)."""
    net = item["net_price"]
    header = f'{item["name"]}  ·  Net: {net:,} AMD\n  Who shares this item?'
    while True:
        selected = _ask(questionary.checkbox(
            header,
            choices=[questionary.Choice(p, checked=True) for p in participants],
        ).ask())
        if not selected:
            print("  [!] Select at least one person.")
            continue
        mode = _ask(questionary.select(
            "  How to split?",
            choices=[questionary.Choice(title, value) for title, value in MODES],
        ).ask())
        values = {} if mode == "equal" else _prompt_values(mode, selected)
        try:
            amounts, weights, method = build_split(
                mode, selected, values, net, participants)
        except ValueError as e:
            print(f"  [!] {e}")
            continue
        line = "  →  " + "  |  ".join(
            f"{n}: {a:,} AMD" for n, a in amounts.items() if a > 0)
        print(line)
        return amounts, weights, method


def _summarize(record: dict) -> str:
    return "  |  ".join(
        f"{n}: {a:,}" for n, a in record["assignments"].items() if a > 0)


def review_and_edit(records: list, participants: list) -> list:
    """Show all items; let the user re-open any one; return final records."""
    while True:
        choices = [questionary.Choice("✓ Finish", "__done__")]
        for idx, rec in enumerate(records):
            label = f'{rec["name"]}  →  {_summarize(rec)}  ({rec["split_method"]})'
            choices.append(questionary.Choice(label, idx))
        pick = questionary.select(
            "  Review — pick an item to edit, or Finish:", choices=choices).ask()
        if pick is None or pick == "__done__":
            return records
        amounts, weights, method = assign_item(records[pick], participants)
        records[pick]["assignments"] = amounts
        records[pick]["assignment_weights"] = weights
        records[pick]["split_method"] = method
```

- [ ] **Step 2: Verify it imports**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'tools'); import interactive; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add tools/interactive.py
git commit -m "feat: add questionary UI (roster, per-item assign, review/edit)"
```

---

## Task 5: Wire `interactive` into `split_basket.py`

**Files:**
- Modify: `tools/split_basket.py` (default roster, imports, roster prompt, item loop; remove dead `assign_items`/`_detect_method`)

- [ ] **Step 1: Add the `interactive` import** next to the `split_math` import

```python
from split_math import _largest_remainder, _equal_split, _pct_split
import interactive
```

- [ ] **Step 2: Change the default roster** — in `main()` find:

```python
    defaults = [p.strip() for p in os.getenv("DEFAULT_PARTICIPANTS", "Me,Mahdi,Amir").split(",") if p.strip()]
```

Replace `"Me,Mahdi,Amir"` with `"Me"`:

```python
    defaults = [p.strip() for p in os.getenv("DEFAULT_PARTICIPANTS", "Me").split(",") if p.strip()]
```

- [ ] **Step 3: Replace the temp-participant prompt block** — find (currently ~lines 454-465):

```python
    print(f"  Default participants: {', '.join(defaults)}")
    try:
        temp_raw = input("  Temporary participants? (names comma-separated, or Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)

    temp_participants = [p.strip() for p in temp_raw.split(",") if p.strip()] if temp_raw else []
    participants = defaults + temp_participants

    if temp_participants:
        print(f"  Active participants: {', '.join(participants)}")
```

Replace with:

```python
    try:
        participants = interactive.setup_roster(defaults)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
```

- [ ] **Step 4: Replace the assignment call** — find:

```python
    print(f"\n  Walking through {len(active_items)} items. Canceled items are skipped.")
    input("  Press Enter to begin ...")

    # ── Item-by-item assignment ─────────────────────────────────────────────
    assigned_items = assign_items(order["items"], participants)
```

Replace with:

```python
    print(f"\n  Walking through {len(active_items)} items. Canceled items are skipped.")

    # ── Item-by-item assignment ─────────────────────────────────────────────
    try:
        records = []
        for seq, item in enumerate(active_items, start=1):
            print(f"\n{SEP}\n  Item {seq}/{len(active_items)}")
            amounts, weights, method = interactive.assign_item(item, participants)
            records.append({**item, "assignments": amounts,
                            "assignment_weights": weights, "split_method": method})
        assigned_items = interactive.review_and_edit(records, participants)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
```

- [ ] **Step 5: Remove dead code** — delete the `assign_items()` function (currently ~lines 169-215) and the `_detect_method()` function (currently ~lines 218-229). `parse_assignment` and `resolve_name` stay.

- [ ] **Step 6: Verify import + no syntax errors**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'tools'); import split_basket; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Run the test suite (regression on math/parser)**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS (15 passed)

- [ ] **Step 8: Commit**

```bash
git add tools/split_basket.py
git commit -m "feat: use interactive selection UI in split_basket"
```

---

## Task 6: Wire `interactive` into `manual_split.py`

**Files:**
- Modify: `tools/manual_split.py` (imports, roster prompt, `collect_items`)

- [ ] **Step 1: Read the current `collect_items` and roster block**

Run: `.venv/bin/python -c "print(open('tools/manual_split.py').read())"`
Note the exact text of: the import line `from split_basket import (parse_assignment, resolve_name, ...)`, the temp-participant prompt (~line 142), and `collect_items` (~lines 66-118).

- [ ] **Step 2: Add the `interactive` import** at the top with the other `tools/` imports

```python
sys.path.insert(0, str(Path(__file__).parent))
import interactive
```
(Leave the existing `from split_basket import ...` line; `allocate_fees`, `compute_totals`, `print_summary`, `collect_payment_info` are still used. `parse_assignment`/`resolve_name` may now be unused here — remove them from that import list if present.)

- [ ] **Step 3: Replace the temp-participant prompt** — find (~lines 140-147):

```python
    print(f"  Default participants: {', '.join(defaults)}")
    ...
    temp_raw     = _prompt("  Temporary participants? (comma-separated, or Enter to skip): ")
    ...
    participants = defaults + temp_list
    ...
        print(f"  Active participants: {', '.join(participants)}")
```

Replace the whole block with:

```python
    try:
        participants = interactive.setup_roster(defaults)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
```

Also change the in-code default in `manual_split.py` `defaults = ... "Me,Mahdi,Amir" ...` to `"Me"` (same edit as Task 5 Step 2).

- [ ] **Step 4: Rewrite `collect_items`** to use the interactive flow

```python
def collect_items(participants: list) -> list:
    """Prompt for free-form manual items, then assign each via the interactive UI."""
    items = []
    print(f"\n{SEP}")
    print("  Enter items (blank name to finish).")
    while True:
        name = _prompt("  Item name (Enter to finish): ")
        if not name:
            break
        while True:
            raw_price = _prompt(f"  '{name}' price (AMD): ")
            try:
                net = int(round(float(raw_price)))
                if net > 0:
                    break
            except ValueError:
                pass
            print("  [!] Enter a positive number.")
        items.append({"name": name, "net_price": net, "quantity": 1,
                      "unit": None, "unit_price": net, "discount": 0,
                      "is_canceled": False})

    if not items:
        print("  No items entered.")
        sys.exit(0)

    try:
        records = []
        for seq, item in enumerate(items, start=1):
            print(f"\n{SEP}\n  Item {seq}/{len(items)}")
            amounts, weights, method = interactive.assign_item(item, participants)
            records.append({**item, "assignments": amounts,
                            "assignment_weights": weights, "split_method": method})
        return interactive.review_and_edit(records, participants)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
```

(Keep the existing `SEP` / `_prompt` definitions in `manual_split.py`. If `collect_items` previously had a different item-dict shape, this shape matches what `allocate_fees`/`compute_totals`/report code reads: `name`, `net_price`, `assignments`, `assignment_weights`, `split_method`.)

- [ ] **Step 5: Verify import**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'tools'); import manual_split; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add tools/manual_split.py
git commit -m "feat: use interactive selection UI in manual_split"
```

---

## Task 7: Set local default roster and verify end-to-end

**Files:**
- Edit (local, uncommitted): `.env`

- [ ] **Step 1: Set the default roster to just "Me"** in `.env`

Change the line `DEFAULT_PARTICIPANTS=Me,Mahdi,Amir` to:

```
DEFAULT_PARTICIPANTS=Me
```

- [ ] **Step 2: Manual end-to-end run on the already-cached order** (interactive — run in a real terminal)

Run: `.venv/bin/python tools/split_basket.py KM0030952134`
Do this during the run:
- At the roster prompt, add a temp participant (e.g. `Amir`).
- Assign the first item **Equal** (just press Enter through the checkbox, pick Equal).
- Assign another item **Part**: deselect everyone but Me and Amir, choose Part, enter `2` and `1`; confirm the echoed line shows a 2:1 split.
- Assign another **Amount** with values that sum to its net price.
- At the **Review** menu, pick the Equal item, re-open it, change it to Percentage `Me 50 / Amir 50`, then Finish.
- Choose Cash at the payment prompt.

Expected: prints `SPLIT SUMMARY`, grand total equals the order total (no discrepancy warning), and `Saved: .tmp/split_KM0030952134.json`.

- [ ] **Step 3: Verify the saved split is well-formed and self-consistent**

Run:
```bash
.venv/bin/python -c "
import json
s = json.load(open('.tmp/split_KM0030952134.json'))
gt = sum(v['total'] for v in s['totals'].values())
print('grand', gt, 'order', s['order_total'])
assert abs(gt - s['order_total']) <= 2, 'totals drift'
for it in s['items']:
    assert abs(sum(it['assignments'].values()) - it['net_price']) <= 1
    assert 'assignment_weights' in it and 'split_method' in it
print('ok')
"
```
Expected: prints matching totals and `ok`.

- [ ] **Step 4: Verify the report/CSV pipeline still consumes the new splits**

Run: `.venv/bin/python tools/generate_csv.py KM0030952134`
Expected: writes `.tmp/report_KM0030952134.csv` with no error; spot-check that per-person amount columns sum to each item's price.

- [ ] **Step 5: Manual smoke test of `manual_split.py`** (interactive)

Run: `.venv/bin/python tools/manual_split.py`
Enter one item (e.g. `Taxi` / `2000`), assign it Part `Me 3 / Amir 1`, Finish, Cash.
Expected: `SPLIT SUMMARY` shows Me 1,500 / Amir 500 and a `split_*.json` is saved.

- [ ] **Step 6: Commit** (no `.env` — it is gitignored; this commit just records that the feature is verified via the plan checkboxes)

```bash
git add docs/superpowers/plans/2026-06-13-terminal-split-selection.md
git commit -m "docs: mark terminal split selection plan complete"
```

---

## Self-Review

**Spec coverage:**
- Arrow-key checkboxes + 4 modes → Task 3 (`build_split`) + Task 4 (`assign_item`). ✓
- Editable after-walk review menu → Task 4 (`review_and_edit`) + Tasks 5/6 wiring. ✓
- Roster = "Me" + typed temp each run → Task 4 (`setup_roster`), Tasks 5/6 default change, Task 7 `.env`. ✓
- Both tools → Tasks 5 and 6. ✓
- Preserved `(assignments, assignment_weights, split_method)` contract → Task 3 mirrors `parse_assignment`; verified in Task 7 Steps 3-4. ✓
- `questionary` dependency + missing `requirements.txt` → Task 1. ✓
- Error handling (empty selection, bad sums, Ctrl-C, non-numeric) → `build_split` raises (Task 3 tests) + `interactive` re-prompts/`_ask` abort (Task 4). ✓
- Testing: unit tests for math + builders (no TTY) → Tasks 2-3; UI via manual run → Task 7. ✓

**Placeholder scan:** No TBD/TODO; every code step contains full code; commands have expected output. ✓

**Type consistency:** `build_split(mode, selected, values, net_price, participants) -> (amounts, weights, method)` used identically in Task 3 def, Task 4 `assign_item`, and Tasks 5/6 callers. Record keys `assignments`/`assignment_weights`/`split_method` consistent across Tasks 4-6 and match `generate_csv`/`generate_report` consumers. ✓
