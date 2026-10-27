"""
ApexSys Quick GitHub Sync Utility (Python)
Automates git staging, committing, pulling, and pushing to origin main.
"""

import datetime
import subprocess
import sys


def run_cmd(cmd: str) -> bool:
    print(f"> {cmd}")
    res = subprocess.run(cmd, shell=True, text=True)
    return res.returncode == 0


def sync(message: str = ""):
    print("========================================")
    print("   APEXSYS GITHUB CONTINUOUS SYNC")
    print("========================================")

    # Check status
    proc = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    status = proc.stdout.strip()

    if not status:
        print("[*] Working tree is clean. Pulling latest from origin main...")
        run_cmd("git pull origin main")
        return

    if not message:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Auto-sync update: {ts}"

    print(f"[*] Staging and committing: {message}")
    run_cmd("git add .")
    run_cmd(f'git commit -m "{message}"')
    run_cmd("git pull --rebase origin main")
    success = run_cmd("git push origin main")

    if success:
        print("\n[SUCCESS] Local workspace pushed to GitHub main branch!")
        print("[*] Streamlit Community Cloud will auto-redeploy with the new changes.")
    else:
        print("\n[!] Push failed. Check credentials or remote connectivity.")


if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else ""
    sync(msg)
