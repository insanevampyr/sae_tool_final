import feedparser

def fetch_rss_articles(keyword, limit=5):
    feed_urls = [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://news.bitcoin.com/feed/",
        "https://cryptopotato.com/feed/",
        "https://www.newsbtc.com/feed/"
    ]

    results = []

    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                if keyword.lower() in entry.title.lower() and count < limit:
                    text = f"{entry.title}. {entry.get('summary', '')}"
                    results.append({
                        "text": text,
                        "url": entry.link
                    })
                    count += 1
        except Exception as e:
            print(f"⚠️ Failed to fetch from {url}: {e}")

    return results
