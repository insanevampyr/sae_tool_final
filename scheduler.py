import schedule
import time
import subprocess

def run_analysis():
    print("🔁 Running scheduled sentiment analysis...\n")
    subprocess.run(["python", "analyze.py"])

# Every 60 minutes (you can adjust this)
schedule.every(60).minutes.do(run_analysis)

print("🕒 Scheduler started. Press Ctrl+C to stop.\n")
while True:
    schedule.run_pending()
    time.sleep(1)
