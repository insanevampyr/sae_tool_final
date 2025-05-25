# check_accuracy.py
import json
from datetime import datetime, timezone, timedelta

with open("prediction_log.json","r",encoding="utf-8") as f:
    log = json.load(f)

cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

for coin, entries in log.items():
    recent = [
        e for e in entries
        if datetime.fromisoformat(e["timestamp"]) > cutoff
    ]
    total   = len(recent)
    correct = sum(1 for e in recent if e.get("accurate"))
    pct      = f"{(correct/total*100):.0f}%" if total else "–"
    print(f"{coin}: {correct}/{total} correct → {pct}")
