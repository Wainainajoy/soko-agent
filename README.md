# Soko Agent 

A Swahili/English market-price assistant for Kenyan traders and farmers, built with **Google ADK**. Its price lookups are paid for with **Cashu ecash**: the agent has its own small wallet and pays a few sats per lookup, automatically, using HTTP 402.

Users chat for free. The *agent* pays for the data it needs.

> Demo uses the **Testnut test mint** (fake sats, no real money) and **sample price data**.

## How it works

1. A user asks: "Bei ya nyanya Wakulima ni ngapi?"
2. The agent calls its `get_price` tool, which asks the price API for the data.
3. The price API replies **402 Payment Required**, with an `X-Cashu` header holding a payment request (5 sats, accepted mint).
4. The tool asks the agent's wallet service to pay. The wallet has a spending limit per payment and makes a Cashu token.
5. The tool retries with the token in the `X-Cashu` header. The price API redeems it at the mint and returns the prices.
6. The agent answers in the user's language and mentions the 5 sats it paid.

```
User ── chat ──> Soko agent (ADK) ──> get_price ──> Price API (402, 5 sats)
                                          │                ▲
                                          └─> Agent wallet ┘  pays with Cashu token
                                                   │
                                            Testnut test mint
```

## Parts

| Path | What it is |
|---|---|
| `soko_agent/agent.py` | The ADK agent and its `get_price` tool (no Cashu code inside) |
| `soko_agent/prices.csv` | Sample price data (made up for the demo) |
| `cashu_services/price_api.py` | Paywalled price API (HTTP 402, X-Cashu header) |
| `cashu_services/wallet_api.py` | The agent's wallet service, with a per-payment spending limit |
| `cashu_services/wallet.py` | Small helper around the Nutshell Cashu wallet library |
| `cashu_services/fund_wallet.py` | Mints fake test sats into the agent wallet |

## Run it (GitHub Codespaces works fine)

The agent and the Cashu wallet library need different dependency versions, so they use two environments.

```bash
# 1. Agent environment
python -m venv .venv && source .venv/bin/activate
pip install google-adk uv

# 2. Cashu environment (Python 3.12)
uv venv --python 3.12 .venv-cashu
pip --python .venv-cashu/bin/python install -r requirements-cashu.txt

# 3. Gemini key: put it in soko_agent/.env
#    GOOGLE_API_KEY=your-key-from-Google-AI-Studio

# 4. Start the price API (port 9000) and wallet service (port 9001)
bash start_cashu.sh

# 5. Give the agent wallet 100 fake test sats
.venv-cashu/bin/python -m cashu_services.fund_wallet 100

# 6. Start the agent
adk web --host 0.0.0.0 --allow_origins="*"
```

Open the page, choose `soko_agent`, and ask a question. Check the wallet any time:

```bash
curl -s http://127.0.0.1:9001/balance
```

See the paywall by itself:

```bash
curl -i "http://127.0.0.1:9000/price?commodity=tomatoes"   # 402 + X-Cashu header
```

## Safety notes

- Test mint only. Never put real money in this demo.
- The wallet service refuses to pay more than `MAX_SATS_PER_PAYMENT` (default 10) and only pays the accepted mint.
- Wallet files (`.wallets/`) hold secret keys and are git-ignored.

## Built for Nut November

Built for the Nut November hackathon to show a practical use of Cashu: autonomous agents paying for small API calls without accounts or cards.

## License

See `LICENSE`.
