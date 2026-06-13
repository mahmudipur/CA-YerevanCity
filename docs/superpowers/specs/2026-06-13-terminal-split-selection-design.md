# Terminal split: arrow-key selection + editable per-item assignment

**Date:** 2026-06-13
**Status:** Design — awaiting user review
**Scope:** Interactive terminal UX of `tools/split_basket.py` and `tools/manual_split.py`

## Goal

Replace the typed participant/assignment prompts with arrow-key selection and
per-person share input, and let the user edit any item before finalizing. The
tool stays terminal-only for now. The split arithmetic and all downstream
behavior (fee allocation, totals, reports, CSV) are unchanged.

## Non-goals

- No web app, Telegram bot, or any non-terminal interface.
- No change to the split math (`_largest_remainder`, fee allocation, EUR logic).
- No change to report/CSV formats or the `split_{id}.json` schema, **except**
  that `assignment_weights` for the new "Part" mode follow the existing
  GCD-reduced-weight convention already used by the fixed-AMD path.
- No change to `fetch_order.py`, `generate_report.py`, `generate_csv.py`.

## Decisions (locked with user)

1. **Selection mechanism:** arrow-key checkboxes / menus via `questionary`.
2. **Four split modes:** Equal, Percentage, Amount (AMD), Part (ratio).
3. **Editable:** review-and-edit menu **after** the walk (no mid-walk back).
4. **Roster:** default roster is just **"Me"**; temp participants are typed
   in fresh at the start of every split. No "drop present people" checkbox.
5. **Both tools:** `split_basket.py` and `manual_split.py` get the same UX.

## The contract that must not change

Each item must still end up with the same pair the current parser produces:

- `assignments`: `{participant: int_amount}` summing exactly to the item's
  `net_price` (drives fee allocation and totals).
- `assignment_weights`: `{participant: number}` — the natural display weights
  (equal → 1/0 per person; percentage → the % value; amount/part →
  GCD-reduced integer weights).

`interactive.py` produces these two structures directly from structured input,
reusing the existing math. Everything downstream is untouched.

## New module: `tools/interactive.py`

All `questionary`-based UI lives here so both tools share one implementation.
Pure UI + thin glue; the math stays in `split_basket.py` and is imported.

Functions (names indicative):

- `setup_roster(default_roster: list[str]) -> list[str]`
  Print the default roster ("Me"), prompt for temp participants (typed, comma
  or repeated entry), return the combined active roster.
- `assign_item(item: dict, participants: list[str]) -> tuple[dict, dict, str]`
  Run the per-item flow (below). Returns `(amounts, weights, method)` matching
  today's `parse_assignment` output plus the method label.
- `review_and_edit(items: list[dict], participants: list[str]) -> list[dict]`
  Show the review menu; re-open `assign_item` for any chosen item; return the
  final enriched item list when the user picks Finish.

### Per-item flow (`assign_item`)

1. **Who shares it?** — `questionary.checkbox`, all participants **pre-ticked**
   (Enter with no change = everyone). At least one must be selected; empty
   selection re-prompts.
2. **How to split?** — `questionary.select` menu: **Equal** (default/top) ·
   **Percentage** · **Amount (AMD)** · **Part (ratio)**.
3. **Per-person values** (skipped for Equal): prompt each selected participant
   in turn for a number.
   - **Equal:** equal split among the selected (largest-remainder).
   - **Percentage:** each person's %; must sum to 100 (±0.01) or re-prompt.
   - **Amount:** each person's AMD; must sum to the item `net_price` or re-prompt.
   - **Part:** each person's relative weight (any positive numbers); the tool
     splits proportionally — no sum constraint.
4. Echo the computed line (`→ Me: 1,000 AMD | Amir: 500 AMD`).

The four modes map onto existing helpers: Equal/Part/Percentage → weighted
`_largest_remainder`; Amount → direct amounts validated against `net_price`.
Display weights follow the existing convention (Part reuses the GCD reduction
already applied to fixed-AMD weights).

### Review-and-edit menu (`review_and_edit`)

After every item is assigned once, show a `questionary.select` list:

```
  ✓ Finish
  Beer "Gyumri" 1l        → Me 1,000 | Amir 500   (part)
  Yeast "Zolotoye" 15g    → all equal              (equal)
  ...
```

Selecting an item re-runs `assign_item` for it and returns to the menu;
selecting **Finish** ends the loop. Nothing is written until Finish.

## Integration into the two tools

- `split_basket.py`
  - `main()`: replace the typed temp-participant block (≈ lines 450–465) with
    `interactive.setup_roster(...)`.
  - Replace `assign_items(...)` + the per-item typed loop with: an initial pass
    calling `interactive.assign_item` per active item, then
    `interactive.review_and_edit(...)`. Net price / canceled-item filtering and
    the assembled `assigned_items` records keep their current shape.
  - Keep `parse_assignment`/`resolve_name` in place (still imported by
    `manual_split`, and usable for any non-interactive path), but they are no
    longer the primary input route.
- `manual_split.py`
  - `collect_items(...)` and its typed temp-participant prompt switch to the
    same `interactive` calls. (Manual items have no fees/canceled flags; flow is
    otherwise identical.)

## Roster default change

Update the in-code default from `"Me,Mahdi,Amir"` to `"Me"` (the
`DEFAULT_PARTICIPANTS` env var still overrides). The user will adjust their
`.env` separately if desired.

## Dependency & environment

- Add **`questionary`** (pulls `prompt_toolkit`) to the project `.venv`.
- The repo currently has **no `requirements.txt`**. Create one capturing the
  real runtime deps (`requests`, `python-dotenv`, Google API libs already in
  use, `questionary`) so the new dependency is recorded.
- `questionary` needs a real interactive TTY — fine for the existing
  `run.py`/CLI usage.

## Error handling

- **Ctrl-C / EOF** anywhere → clean abort (matches current behavior).
- **Empty participant selection** → re-prompt.
- **Percentage** not summing to 100 / **Amount** not matching `net_price` /
  non-numeric input → message + re-prompt (no crash).
- A non-TTY environment (e.g. piped stdin) → clear error telling the user to run
  in an interactive terminal.

## Testing

- **Pure logic** is already covered by the math functions; add unit tests for
  the new value→`(amounts, weights)` builders (Equal/%/Amount/Part), including
  the sum-validation failures and the Part GCD reduction. These need no TTY.
- **UI wiring** (questionary prompts) verified by a manual run of `run.py` on a
  fetched order: assign a few items across all four modes, edit one via the
  review menu, finish, and confirm the resulting `split_{id}.json` totals match
  the order total (the existing discrepancy check in `print_summary`).

## Risks / open considerations

- `questionary` rendering differs across terminals; acceptable for personal use.
- Per-person sequential prompts for many participants could feel long; mitigated
  by Equal being the one-keypress default for the common case.
