"""Serves the canonical 'paste this into any AI' receipt-scanning prompt, so
the frontend and this file never drift apart — one source of truth."""

from fastapi import APIRouter, Depends

from ..dependencies import get_current_user
from ..services.user_store import AuthedUser

router = APIRouter(prefix="/api/receipt-prompt", tags=["receipt"])

RECEIPT_PROMPT = """You are reading a photo of a purchase receipt. Return ONLY a single JSON object — no explanations, no markdown code fences, no text before or after it — in exactly this shape:

{
  "items": [
    { "name": "string", "price": number, "service": number or "N%" (optional) }
  ]
}

Rules:
- One entry per line item on the receipt.
- "name" MUST be in English, even if the receipt is in another language — translate it. Keep it short and recognizable (e.g. "Walnuts", not a long description), so everyone splitting the bill understands what it is.
- "price" is that item's TOTAL line price (already multiplied by quantity), as a plain number — no currency symbols, no commas, no quotes.
- ANY bill-wide surcharge that applies to the WHOLE receipt rather than one specific item — service fee/charge, sales tax, VAT, or any other tax or fee, under whatever label the receipt uses — must be spread across every item's own "service" field. Never create a separate line item for these, regardless of what they're called on the receipt:
  - If it's stated as a percentage (e.g. "12%", "Sales tax 12%", "Service fee 10%"), put that exact percentage string (e.g. "12%") in the "service" field of EVERY item. If there are multiple such percentage surcharges (e.g. both a service fee AND a tax), add their percentages together into one combined percentage string per item (e.g. 10% service + 12% tax → "22%").
  - If one is stated as a flat total amount instead of a percentage, divide it proportionally across all items by each item's price (rounded so the shares sum to the total) and add each item's own share into its "service" field (summing with any percentage-derived amount already computed for that item).
- Tip / gratuity is the ONE exception: if the receipt shows a tip that was actually charged (not just a note that gratuity is optional/not included), add it as its own separate item, e.g. { "name": "Tip", "price": 1000 }. Do not add a Tip item if the receipt only says gratuity is not included.
- Omit "service" entirely (or use 0) only when no service charge/tax/fee of any kind applies.
- Do not invent items that aren't on the receipt, and do not add totals/subtotal lines as items.
- Output must be valid JSON and nothing else."""


@router.get("")
def get_receipt_prompt(user: AuthedUser = Depends(get_current_user)):
    return {"prompt": RECEIPT_PROMPT}
