# auto_push.py
import subprocess
from datetime import datetime
import os
import sys

def auto_push():
    # files you want to stage
    files = [
        "sentiment_output.csv",
        "sentiment_history.csv",
        "analyze.py",
        "dashboard.py"
    ]

    # make sure we're in the project folder
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_dir)

    # git add
    for f in files:
        if os.path.exists(f):
            subprocess.run(["git", "add", f], check=True)

    # commit
    msg = f"chore: auto-update @ {datetime.utcnow().isoformat()}Z"
    subprocess.run(["git", "commit", "-m", msg], check=True)

    # push
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("✅ Auto-push complete.")

if __name__ == "__main__":
    try:
        auto_push()
    except subprocess.CalledProcessError as e:
        print("❌ Git failed:", e)
        sys.exit(1)
