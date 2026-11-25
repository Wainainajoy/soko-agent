"""Put fake test sats into the agent's wallet.

Usage (from the repo root):
    .venv-cashu/bin/python -m cashu_services.fund_wallet 100
"""

import asyncio
import sys

from .wallet import MINT_URL, fund, get_balance, open_wallet


async def main(amount: int) -> None:
    wallet = await open_wallet("agent")
    print(f"Mint: {MINT_URL}")
    print(f"Balance before: {await get_balance(wallet)} sat")
    await fund(wallet, amount)
    print(f"Balance after:  {await get_balance(wallet)} sat")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
