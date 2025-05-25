# -*- coding: utf-8 -*-
"""
Your price‐alert thresholds, plus the list of coins you track.
"""

# 1) Define the coins you support:
COINS = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]

# 2) (the rest of your existing thresholds & alert logic lives here)
# For example:
THRESHOLDS = {
    "Bitcoin":  { "upper": 70000, "lower": 30000 },
    "Ethereum": { "upper":  4000, "lower":  1000 },
    "Solana":   { "upper":   500, "lower":   10 },
    "Dogecoin": { "upper":     1, "lower":    0.05 },
}

def check_price_alerts(current_prices):
    """
    Given a dict of { coin: price }, returns list of
    (coin, price, "above upper" / "below lower") for any alerts.
    """
    alerts = []
    for coin, price in current_prices.items():
        if coin not in THRESHOLDS:
            continue
        t = THRESHOLDS[coin]
        if price >= t["upper"]:
            alerts.append((coin, price, "above upper"))
        elif price <= t["lower"]:
            alerts.append((coin, price, "below lower"))
    return alerts
