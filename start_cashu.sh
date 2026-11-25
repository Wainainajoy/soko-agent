#!/usr/bin/env bash
# Starts the price API (port 9000) and the agent wallet service (port 9001)
# in the background. Run from the repo root:  bash start_cashu.sh
cd "$(dirname "$0")" || exit 1

export MINT_URL="${MINT_URL:-https://testnut.cashu.space}"
export WALLET_DIR="${WALLET_DIR:-$PWD/.wallets}"

bash stop_cashu.sh >/dev/null 2>&1

nohup .venv-cashu/bin/uvicorn cashu_services.price_api:app \
  --host 127.0.0.1 --port 9000 > price_api.log 2>&1 &
nohup .venv-cashu/bin/uvicorn cashu_services.wallet_api:app \
  --host 127.0.0.1 --port 9001 > wallet_api.log 2>&1 &

sleep 5
echo "Mint:        $MINT_URL"
echo "Price API:   $(curl -s -m 5 -o /dev/null -w '%{http_code}' 'http://127.0.0.1:9000/price?commodity=none') (200 = running)"
echo "Wallet API:  $(curl -s -m 20 -o /dev/null -w '%{http_code}' 'http://127.0.0.1:9001/balance') (200 = running)"
echo "Logs: price_api.log and wallet_api.log"
