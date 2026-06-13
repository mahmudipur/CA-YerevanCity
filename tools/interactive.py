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
