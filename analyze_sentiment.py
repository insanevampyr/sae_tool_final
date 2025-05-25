import os
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from textblob import TextBlob
from crypto_price_alerts import COINS
from fetch_prices import fetch_prices
from reddit_fetch import fetch_reddit_posts

# Load environment vars
load_dotenv()


def analyze_sentiment(text: str) -> float:
    """
    Compute the sentiment polarity of the given text using TextBlob.

    Returns a float in [-1.0, 1.0].
    """
    blob = TextBlob(text)
    return blob.sentiment.polarity


def get_latest_sentiment():
    """
    Fetch latest sentiment for each coin from Reddit posts.
    Aggregates sentiment and attaches price and suggested action.

    Returns:
        List[Dict]: entries with Timestamp, Coin, Source, Sentiment,
                     PriceUSD, SuggestedAction.
    """
    items = []
    ts = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    for coin in COINS:
        for post in fetch_reddit_posts('CryptoCurrency', coin, 5):
            items.append({
                'Timestamp': ts,
                'Coin': coin,
                'Source': 'Reddit',
                'text': post['text'],
            })

    # fetch current prices once
    prices = fetch_prices(COINS).set_index('Coin')['PriceUSD'].to_dict()
    out = []
    for item in items:
        sent = analyze_sentiment(item['text'])
        price = prices.get(item['Coin'], 0.0) or 0.0
        if sent >  0.2:
            action = "BUY"
        elif sent < -0.2:
            action = "SELL"
        else:
            action = "HOLD"
        out.append({
            'Timestamp':       item['Timestamp'],
            'Coin':            item['Coin'],
            'Source':          item['Source'],
            'Sentiment':       sent,
            'PriceUSD':        round(price, 2),
            'SuggestedAction': action,
        })
    return out
