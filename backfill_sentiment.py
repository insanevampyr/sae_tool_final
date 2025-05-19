#!/usr/bin/env python3
import os
import csv
import argparse
from datetime import datetime, timedelta, timezone

import praw
from dateutil import parser as dtparser
from analyze_sentiment import analyze_sentiment

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS     = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SUBREDDIT = "CryptoCurrency"
HIST_CSV  = "sentiment_history.csv"

# ─── HELPERS ────────────────────────────────────────────────────────────────
def init_writer(path):
    """Open CSV for append, write header if missing."""
    header = not os.path.exists(path)
    f = open(path, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=[
        "Timestamp", "Coin", "Source", "Sentiment", "PriceUSD", "SuggestedAction"
    ])
    if header:
        w.writeheader()
    return f, w

# ─── BACKFILL LOGIC ─────────────────────────────────────────────────────────
def backfill(start: datetime, end: datetime):
    """Backfill sentiment_history.csv hour-by-hour from start→end UTC."""
    # initialize PRAW (must have these in your env)
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ.get("REDDIT_USER_AGENT", "backfill-sentiment-script"),
    )

    f, writer = init_writer(HIST_CSV)
    cur = start.replace(minute=0, second=0, microsecond=0)
    while cur < end:
        nxt  = cur + timedelta(hours=1)
        # ISO timestamp bucket
        iso_ts = cur.replace(tzinfo=timezone.utc).isoformat()
        after  = int(cur.replace(tzinfo=timezone.utc).timestamp())
        before = int(nxt.replace(tzinfo=timezone.utc).timestamp())

        for coin in COINS:
            # — Reddit posts in this window mentioning the coin
            query = f'timestamp:{after}..{before} "{coin}"'
            try:
                subs = reddit.subreddit(SUBREDDIT).search(
                    query,
                    sort="asc",
                    syntax="cloudsearch",
                    limit=500
                )
                texts = []
                for sub in subs:
                    txt = (sub.title or "") + "\n" + (getattr(sub, "selftext", "") or "")
                    texts.append(txt)
            except Exception:
                texts = []

            if texts:
                scores = [analyze_sentiment(t) for t in texts]
                avg_s  = round(sum(scores) / len(scores), 4)
            else:
                avg_s = 0.0

            # write the Reddit‐source row
            writer.writerow({
                "Timestamp":       iso_ts,
                "Coin":            coin,
                "Source":          "Reddit",
                "Sentiment":       avg_s,
                "PriceUSD":        "",   # leave blank; dashboard ignores it here
                "SuggestedAction": ""
            })
            # write a News‐source placeholder (0 sentiment)
            writer.writerow({
                "Timestamp":       iso_ts,
                "Coin":            coin,
                "Source":          "News",
                "Sentiment":       0.0,
                "PriceUSD":        "",
                "SuggestedAction": ""
            })

        print(f"Backfilled hour {iso_ts}")
        cur = nxt

    f.close()
    print(f"✅ Finished backfill from {start.isoformat()} to {end.isoformat()}.")

# ─── CLI ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Backfill sentiment_history.csv from Reddit hour-by-hour"
    )
    p.add_argument(
        "--start", required=True,
        help="ISO8601 start time inclusive, e.g. 2025-05-16T00:00:00+00:00"
    )
    p.add_argument(
        "--end",   required=True,
        help="ISO8601 end time exclusive"
    )
    args = p.parse_args()

    start = dtparser.isoparse(args.start)
    end   = dtparser.isoparse(args.end)
    backfill(start, end)
