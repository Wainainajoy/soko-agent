"""The agent's wallet, as a tiny local service.

The ADK agent runs in a different Python environment from the Cashu library,
so it asks this service to pay for it. The service enforces a spending limit.

Run from the repo root (keep it on 127.0.0.1 and keep the port PRIVATE):
    .venv-cashu/bin/uvicorn cashu_services.wallet_api:app --port 9001 --host 127.0.0.1
"""

import os

from cashu.core.nuts.nut18 import deserialize as decode_payment_request
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .wallet import MINT_URL, get_balance, make_token, open_wallet

# Safety limit: never pay more than this for one request.
MAX_SATS_PER_PAYMENT = int(os.getenv("MAX_SATS_PER_PAYMENT", "10"))

app = FastAPI(title="Soko agent wallet (test sats only)")


class PayBody(BaseModel):
    payment_request: str  # the value of the X-Cashu header from a 402 response


@app.get("/balance")
async def balance():
    wallet = await open_wallet("agent")
    return {"mint": MINT_URL, "balance_sats": await get_balance(wallet)}


@app.post("/pay")
async def pay(body: PayBody):
    try:
        request = decode_payment_request(body.payment_request)
    except Exception:
        raise HTTPException(400, "Could not read the payment request.")

    if request.u != "sat" or not request.a:
        raise HTTPException(400, "Unsupported payment request (need an amount in sat).")
    if request.a > MAX_SATS_PER_PAYMENT:
        raise HTTPException(
            400,
            f"Price {request.a} sats is above the limit of {MAX_SATS_PER_PAYMENT} sats.",
        )
    if request.m and MINT_URL not in [m.rstrip("/") for m in request.m]:
        raise HTTPException(400, "The service does not accept the mint this wallet uses.")

    wallet = await open_wallet("agent")
    if await get_balance(wallet) < request.a:
        raise HTTPException(402, "Wallet is out of sats. Top it up with fund_wallet.py.")

    token = await make_token(wallet, request.a)
    return {"token": token, "amount_sats": request.a}
