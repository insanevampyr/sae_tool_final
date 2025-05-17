# analyze.py
import os, json, subprocess
from datetime import datetime, timezone, timedelta

from train_price_predictor import predict_prices    # your model inference fn
from fetch_prices        import fetch_prices        # cleans up the timeout bug
from analyze_sentiment   import get_latest_sentiment

from telegram import Bot   # python-telegram-bot

# ─── CONFIG ────────────────────────────────────────────────────────────────
COINS         = ["Bitcoin","Ethereum","Solana","Dogecoin"]
TOKEN         = os.getenv("TELEGRAM_TOKEN")
CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID")
HIST_CSV      = "sentiment_history.csv"
PRED_JSON     = "prediction_log.json"

bot = Bot(token=TOKEN)


def send_telegram_message(msg: str):
    bot.send_message(chat_id=CHAT_ID, text=msg)


def compute_24h_accuracy(coin: str, now: datetime) -> str:
    """Reads prediction_log.json and returns 'xx%' over the last 24h."""
    if not os.path.exists(PRED_JSON):
        return "–"
    log    = json.load(open(PRED_JSON))
    cutoff = now - timedelta(hours=24)
    total = correct = 0

    for entry in log:
        ts = datetime.fromisoformat(entry["timestamp"])
        if ts < cutoff:
            break
        info = entry.get(coin)
        if info and isinstance(info.get("accurate"), bool):
            total += 1
            if info["accurate"]:
                correct += 1

    if not total:
        return "–"
    return f"{round(correct/total * 100)}%"


def update_predictions():
    now     = datetime.now(timezone.utc)
    prices  = fetch_prices(COINS)
    preds   = predict_prices()   # returns { coin: (pred_price: float, target_time: datetime) }

    history = (
        json.load(open(PRED_JSON))
        if os.path.exists(PRED_JSON) else []
    )

    new_entry = {"timestamp": now.isoformat()}
    for coin, (p_price, t_time) in preds.items():
        curr  = prices.get(coin)
        pct   = ((p_price - curr) / curr * 100) if curr else None
        acc24 = compute_24h_accuracy(coin, now)

        new_entry[coin] = {
            "current":      curr,
            "diff_pct":     round(pct, 2) if pct is not None else None,
            "timestamp":    now.isoformat(),
            "by":           t_time.strftime("%H:%M"),
            "accuracy24h":  acc24,
            "accurate":     None,   # placeholder
        }

    history.insert(0, new_entry)
    with open(PRED_JSON, "w") as f:
        json.dump(history, f, indent=2)

    return new_entry


def main():
    # ─── append latest sentiment ─────────────────────────────────────────────
    sent = get_latest_sentiment()   # dict with keys Timestamp,Coin,...
    row  = ",".join(str(sent[k]) for k in ("Timestamp","Coin","Source","Sentiment","PriceUSD","SuggestedAction"))
    with open(HIST_CSV, "a") as f:
        f.write(row + "\n")

    # ─── update & push predictions ────────────────────────────────────────────
    new_pred = update_predictions()
    subprocess.check_output(["git","add", HIST_CSV, PRED_JSON])
    subprocess.check_output([
        "git","commit","-m",
        f"chore: auto-update @ {datetime.utcnow().isoformat()}Z"
    ], text=True)
    subprocess.check_output(["git","push"], text=True)
    print(f"✅ Pushed predictions @ {new_pred['timestamp']}")

    # ─── send ONE telegram alert ───────────────────────────────────────────────
    lines = ["📈 Next-hour forecasts:"]
    for coin in COINS:
        info = new_pred[coin]
        sign = "+" if info["diff_pct"] and info["diff_pct"] > 0 else ""
        lines.append(
            f"{coin}: Now ${info['current']:.2f} → ${preds[coin][0]:.2f} "
            f"({sign}{info['diff_pct']:.2f}% by {info['by']} UTC, 24 h acc {info['accuracy24h']})"
        )

    send_telegram_message("\n".join(lines))
    print("✅ Telegram alert sent.")


if __name__ == "__main__":
    main()
