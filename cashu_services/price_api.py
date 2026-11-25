"""Soko price API: price lookups that cost a few sats, paid with Cashu ecash.

Follows the idea of NUT-24 (HTTP 402 Payment Required):
  1. Client asks for a price with no payment.
  2. Server replies 402 and an `X-Cashu` header holding a payment request
     (amount, unit, accepted mint).
  3. Client retries with a Cashu token in the `X-Cashu` header.
  4. Server redeems the token at the mint, then returns the data.

Run from the repo root:
    .venv-cashu/bin/uvicorn cashu_services.price_api:app --port 9000
"""

import csv
import os
from pathlib import Path
from typing import Optional

from cashu.core.base import PaymentRequest
from cashu.core.nuts.nut18 import serialize as encode_payment_request
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from .wallet import MINT_URL, open_wallet, parse_token, redeem

PRICE_SATS = int(os.getenv("PRICE_SATS", "5"))
DATA = Path(__file__).resolve().parent.parent / "soko_agent" / "prices.csv"

app = FastAPI(title="Soko price API (paid with Cashu)")


def find_prices(commodity: str, market: str) -> list[dict]:
    rows = []
    with open(DATA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if commodity.lower() in row["commodity"].lower():
                if not market or market.lower() in row["market"].lower():
                    rows.append(row)
    return rows


def payment_required() -> JSONResponse:
    request = PaymentRequest(a=PRICE_SATS, u="sat", m=[MINT_URL], d="Soko price lookup")
    return JSONResponse(
        {"error": "payment_required", "price_sats": PRICE_SATS, "mint": MINT_URL},
        status_code=402,
        headers={"X-Cashu": encode_payment_request(request)},
    )


def bad_payment(reason: str) -> JSONResponse:
    return JSONResponse({"error": "bad_payment", "reason": reason}, status_code=400)


@app.get("/price")
async def price(
    commodity: str,
    market: str = "",
    x_cashu: Optional[str] = Header(default=None),
):
    rows = find_prices(commodity, market)
    if not rows:  # nothing to sell, so nothing to charge
        return {"status": "not_found", "paid_sats": 0, "prices": []}

    if not x_cashu:
        return payment_required()

    # Check the token BEFORE spending effort on it.
    try:
        token = parse_token(x_cashu)
    except Exception:
        return bad_payment("could not read the token")
    if token.mint.rstrip("/") != MINT_URL:
        return bad_payment(f"only tokens from {MINT_URL} are accepted")
    if token.unit != "sat":
        return bad_payment("only sat tokens are accepted")
    if token.amount < PRICE_SATS:
        return bad_payment(f"price is {PRICE_SATS} sats, token holds {token.amount}")

    # Claim the sats at the mint. This fails for fake or already-spent tokens.
    wallet = await open_wallet("server")
    try:
        await redeem(wallet, x_cashu)
    except Exception as error:
        return bad_payment(f"mint refused the token: {error}")

    # token.amount can be a little above the price: it includes the mint's
    # swap fee, which the sender covers so we receive the full price.
    return {
        "status": "ok",
        "paid_sats": PRICE_SATS,
        "mint_fee_sats": token.amount - PRICE_SATS,
        "prices": rows,
    }
