#!/usr/bin/env bash
# Stops the two Cashu services started by start_cashu.sh
pkill -f "cashu_services.price_api" 2>/dev/null
pkill -f "cashu_services.wallet_api" 2>/dev/null
echo "Cashu services stopped."
