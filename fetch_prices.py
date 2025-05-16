import requests

def fetch_prices(timeout: int = 10) -> dict:
    """
    Fetch current USD prices for configured coins via CoinGecko.
    Returns a dict mapping coin names to float prices (0.0 on failure).
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,solana,dogecoin",
        "vs_currencies": "usd"
    }
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        prices = resp.json()
        # Map API keys to our coin names
        return {
            "Bitcoin": float(prices.get("bitcoin", {}).get("usd", 0.0)),
            "Ethereum": float(prices.get("ethereum", {}).get("usd", 0.0)),
            "Solana": float(prices.get("solana", {}).get("usd", 0.0)),
            "Dogecoin": float(prices.get("dogecoin", {}).get("usd", 0.0)),
        }
    except requests.exceptions.RequestException as e:
        # Log a warning and return zero prices to avoid crashing
        print(f"⚠️ Price fetch failed: {e}")
        return {coin: 0.0 for coin in ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]}
