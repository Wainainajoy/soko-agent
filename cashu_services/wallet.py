"""Small helper around the Nutshell ("cashu") wallet library.

Two wallets are used in this project:
  - "agent":  the Soko agent's spending wallet
  - "server": the price API's wallet, which receives the payments

Everything here uses a TEST mint with fake sats. Never put real money in it.
"""

import asyncio
import os
from pathlib import Path

from cashu.wallet.helpers import deserialize_token_from_string, receive
from cashu.wallet.wallet import Wallet

# The mint both sides agree on. Testnut is a public test mint with fake sats.
MINT_URL = os.getenv("MINT_URL", "https://testnut.cashu.space").rstrip("/")

# Where wallet databases (which contain secret keys) are stored. Keep this
# folder out of git! (.wallets/ must be listed in .gitignore.)
WALLET_DIR = Path(os.getenv("WALLET_DIR", ".wallets")).resolve()


async def open_wallet(name: str) -> Wallet:
    """Open (or create) a named wallet connected to MINT_URL."""
    WALLET_DIR.mkdir(parents=True, exist_ok=True)
    db_path = str(WALLET_DIR / name)
    # First call runs the database setup, the second one loads the wallet.
    await Wallet.with_db(MINT_URL, db_path, name=name, skip_db_read=True)
    wallet = await Wallet.with_db(MINT_URL, db_path, name=name)
    if not hasattr(wallet, "keyset_id"):
        await wallet.load_mint_keysets()
        await wallet.activate_keyset()
    await wallet.load_proofs(reload=True)
    return wallet


async def get_balance(wallet: Wallet) -> int:
    """Spendable balance in sats."""
    await wallet.load_proofs(reload=True)
    return int(wallet.available_balance.amount)


async def fund(wallet: Wallet, amount: int) -> None:
    """Mint fake sats into the wallet. Only works on test mints like Testnut."""
    quote = await wallet.request_mint(amount)
    last_error = None
    for _ in range(15):  # the fake mint marks the invoice paid almost instantly
        try:
            await wallet.mint(amount, quote_id=quote.quote)
            return
        except Exception as error:  # invoice not marked paid yet: wait, retry
            last_error = error
            await asyncio.sleep(1)
    raise RuntimeError(f"Could not mint test sats: {last_error}")


async def make_token(wallet: Wallet, amount: int) -> str:
    """Take `amount` sats out of the wallet as a Cashu token (a text string)."""
    await wallet.load_proofs(reload=True)
    await wallet.load_mint()
    # include_fees=True makes the sender cover the mint's swap fee, so the
    # receiver ends up with the full amount.
    send_proofs, _fees = await wallet.select_to_send(
        wallet.proofs,
        amount,
        set_reserved=False,
        offline=False,
        include_fees=True,
    )
    token = await wallet.serialize_proofs(send_proofs, include_dleq=False, legacy=False)
    await wallet.set_reserved_for_send(send_proofs, reserved=True)
    return token


def parse_token(token_string: str):
    """Decode a token string without spending it."""
    return deserialize_token_from_string(token_string)


async def redeem(wallet: Wallet, token_string: str) -> None:
    """Claim a token into this wallet. Fails if it was already spent."""
    await receive(wallet, parse_token(token_string))
