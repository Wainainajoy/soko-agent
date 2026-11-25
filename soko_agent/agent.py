import os

import httpx
from google.adk import Agent

PRICE_API_URL = os.getenv("PRICE_API_URL", "http://127.0.0.1:9000").rstrip("/")
WALLET_API_URL = os.getenv("WALLET_API_URL", "http://127.0.0.1:9001").rstrip("/")


async def get_price(commodity: str, market: str = "") -> dict:
    """Look up the sample price of a commodity at a Kenyan market.

    The price service charges a few sats per lookup. This tool pays that
    automatically from the agent's own test-ecash wallet.

    Args:
        commodity: The item, e.g. "tomatoes" or "maize".
        market: Optional market name, e.g. "Wakulima".

    Returns:
        A dict with the status, matching price rows and how many sats were paid.
    """
    url = f"{PRICE_API_URL}/price"
    params = {"commodity": commodity, "market": market}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            response = await client.get(url, params=params)

            if response.status_code == 402:  # the service wants payment
                # Ask the wallet service to pay (it enforces the spending limit).
                pay = await client.post(
                    f"{WALLET_API_URL}/pay",
                    json={"payment_request": response.headers["X-Cashu"]},
                )
                if pay.status_code != 200:
                    return {"status": "error", "message": f"Payment failed: {pay.text}"}
                token = pay.json()["token"]
                response = await client.get(url, params=params, headers={"X-Cashu": token})

            if response.status_code != 200:
                return {"status": "error", "message": response.text}
            result = response.json()

            balance = await client.get(f"{WALLET_API_URL}/balance")
            if balance.status_code == 200:
                result["agent_wallet_balance_sats"] = balance.json()["balance_sats"]
            return result
        except httpx.HTTPError as error:
            return {"status": "error", "message": f"Could not reach a service: {error}"}


root_agent = Agent(
    name="soko_agent",
    model="gemini-3.5-flash",  # keep the model name that works for you
    instruction=(
        "You are Soko Agent, a friendly market-price assistant for Kenyan "
        "traders and farmers. Reply in the language the user writes in "
        "(Swahili or English). Always use the get_price tool for prices. "
        "Never invent prices. Prices are in KES per kg. Say that the data "
        "is sample data for a demo. The price service charges the agent a "
        "few test sats per lookup, paid automatically; mention how many sats "
        "were paid in one short sentence, and never ask the user to pay."
    ),
    tools=[get_price],
)
