#!/usr/bin/env python3
import argparse
import os
import csv
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd
from dateutil import parser as isoparser
from dotenv import load_dotenv

# ─── Load .env for optional Reddit creds ────────────────────────────────────
load_dotenv()

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS          = ["Bitcoin", "Ethereum", "Solana", "Dogecoin"]
SUBREDDIT      = "CryptoCurrency"
HIST_CSV       = "sentiment_history.csv"
PUSHSHIFT_URL  = "https://api.pushshift.io/reddit/search/submission"
PUSHSHIFT_SIZE = 500
HEADERS        = {"User-Agent": "backfill-sentiment-script"}

# ─── USER’S SENTIMENT FUNCTION ─────────────────────────────────────────────
from analyze_sentiment import analyze_sentiment

# ─── PUSHSHIFT FETCH ───────────────────────────────────────────────────────
def fetch_pushshift(coin: str, after: int, before: int) -> list[str]:
    try:
        resp = requests.get(
            PUSHSHIFT_URL,
            params={
                "subreddit": SUBREDDIT,
                "q":         coin,
                "after":     after,
                "before":    before,
                "size":      PUSHSHIFT_SIZE,
                "sort":      "asc",
            },
            headers=HEADERS,
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        texts = []
        for item in data:
            t = item.get("selftext") or item.get("title") or ""
            if t:
                texts.append(t)
        return texts
    except Exception as e:
        print(f"⚠️  Pushshift error for {coin} @ {datetime.fromtimestamp(after, timezone.utc).isoformat()}, skipping → {e}")
        return []

# ─── OPTIONAL PRAW FALLBACK ─────────────────────────────────────────────────
def fetch_reddit_api(coin: str, after: int, before: int) -> list[str]:
    client_id     = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent    = os.getenv("REDDIT_USER_AGENT")
    if not (client_id and client_secret and user_agent):
        return []
    try:
        import praw
        reddit = praw.Reddit(
            client_id     = client_id,
            client_secret = client_secret,
            user_agent    = user_agent
        )
        query = f'title:{coin} timestamp:{after}.{before}'
        texts = []
        for sub in reddit.subreddit(SUBREDDIT).search(
            query, sort="new", limit=PUSHSHIFT_SIZE, syntax="cloudsearch"
        ):
            t = sub.selftext or sub.title or ""
            if t:
                texts.append(t)
        return texts
    except Exception as e:
        print(f"⚠️  Reddit API error for {coin} @ {datetime.fromtimestamp(after, timezone.utc).isoformat()}, skipping → {e}")
        return []

# ─── PARSE ISO8601 INTO UTC ─────────────────────────────────────────────────
def parse_iso(ts: str) -> datetime:
    dt = isoparser.isoparse(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# ─── BACKFILL LOOP ─────────────────────────────────────────────────────────
def backfill(start_iso: str, end_iso: str):
    start = parse_iso(start_iso).replace(minute=0, second=0, microsecond=0)
    end   = parse_iso(end_iso)

    # load existing history
    if os.path.exists(HIST_CSV):
        hist_df = pd.read_csv(HIST_CSV)
    else:
        hist_df = pd.DataFrame(columns=["Timestamp","Coin","Sentiment","PriceUSD"])

    records = []
    curr = start
    while curr < end:
        after  = int(curr.timestamp())
        before = int((curr + timedelta(hours=1)).timestamp())
        iso_ts = curr.astimezone(timezone.utc).isoformat()

        for coin in COINS:
            texts = fetch_pushshift(coin, after, before)
            if not texts:
                texts = fetch_reddit_api(coin, after, before)

            sents = [analyze_sentiment(t) for t in texts]
            avg   = round(sum(sents)/len(sents), 4) if sents else 0.0

            records.append({
                "Timestamp": iso_ts,
                "Coin":      coin,
                "Sentiment": avg,
                "PriceUSD":  0.0
            })

        curr += timedelta(hours=1)

    # merge + dedupe + write
    new_df   = pd.DataFrame(records)
    combined = pd.concat([hist_df, new_df], ignore_index=True)
    combined.drop_duplicates(subset=["Timestamp","Coin"], keep="last", inplace=True)
    combined.to_csv(HIST_CSV, index=False)
    print(f"✅ Finished backfill from {start_iso} to {end_iso}")

# ─── CLI ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Backfill sentiment_history.csv with real Reddit data"
    )
    p.add_argument("--start", required=True,
                   help="Inclusive ISO8601 start e.g. 2025-05-16T00:00:00+00:00")
    p.add_argument("--end",   required=True,
                   help="Exclusive ISO8601 end   e.g. 2025-05-19T00:00:00+00:00")
    args = p.parse_args()
    backfill(args.start, args.end)
