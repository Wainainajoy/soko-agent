import csv
from pathlib import Path

from google.adk import Agent

DATA = Path(__file__).parent / "prices.csv"


def get_price(commodity: str, market: str = "") -> dict:
    """Look up the sample price of a commodity at a Kenyan market.

    Args:
        commodity: The item, e.g. "tomatoes" or "maize".
        market: Optional market name, e.g. "Wakulima".

    Returns:
        A dict with a status and the matching price rows.
    """
    rows = []
    with open(DATA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if commodity.lower() in row["commodity"].lower():
                if not market or market.lower() in row["market"].lower():
                    rows.append(row)
    if not rows:
        return {"status": "not_found", "message": f"No price found for {commodity}."}
    return {"status": "ok", "prices": rows}


root_agent = Agent(
    name="soko_agent",
    model="gemini-3.5-flash",
    instruction=(
        "You are Soko Agent, a friendly market-price assistant for Kenyan "
        "traders and farmers. Reply in the language the user writes in "
        "(Swahili or English). Always use the get_price tool for prices. "
        "Never invent prices. Prices are in KES per kg. Say that the data "
        "is sample data for a demo."
    ),
    tools=[get_price],
)