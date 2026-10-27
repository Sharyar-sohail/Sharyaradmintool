"""
ApexSys Agent CLI Launcher
Connects the local PC to the ApexSys Commander server.
"""

import argparse
import asyncio
import ctypes
import os
import sys
from agent.apex_agent import ApexAgent

BANNER = """
========================================================================
   ___    ____  _______  ______  ______  ______
  /   |  / __ \\/ ____/ |/ / __ \\/ ___/ |/ / __ \\
 / /| | / /_/ / __/  |   / /_/ /\\__ \\ |   / /_/ /
/ ___ |/ ____/ /___ /   / ____/___/ //   / ____/ 
/_/  |_/_/   /_____//_/|_/_/   /____//_/|_/_/    
              CLIENT AUTONOMOUS IT DOCTOR AGENT
========================================================================
"""


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate():
    """Relaunches current script with Administrator elevation."""
    if not is_admin():
        print("[ApexSys Agent] Elevating privileges via UAC prompt...")
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            None,
            1,
        )
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="ApexSys Autonomous IT Doctor Agent")
    parser.add_argument("--server", default="ws://127.0.0.1:8000", help="WebSocket server URL (default: ws://127.0.0.1:8000)")
    parser.add_argument("--client-id", default=None, help="Custom identifier for this machine (default: auto)")
    parser.add_argument("--elevate", action="store_true", help="Automatically request Administrator elevation")
    args = parser.parse_args()

    print(BANNER)
    if args.elevate and not is_admin():
        elevate()

    admin_status = "ELEVATED (Full DISM/SFC enabled)" if is_admin() else "STANDARD (Read-only mode for some deep repairs)"
    print(f"[*] Privilege Level : {admin_status}")
    print(f"[*] Target Commander: {args.server}\n")

    agent = ApexAgent(server_url=args.server, client_id=args.client_id)
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n[ApexSys Agent] Agent terminated by user.")


if __name__ == "__main__":
    main()
