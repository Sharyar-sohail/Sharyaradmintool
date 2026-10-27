"""
ApexSys Server CLI Launcher
Starts the FastAPI real-time command dashboard & WebSocket broker.
"""

import argparse
import sys
import uvicorn

BANNER = """
========================================================================
   ___    ____  _______  ______  ______  ______
  /   |  / __ \\/ ____/ |/ / __ \\/ ___/ |/ / __ \\
 / /| | / /_/ / __/  |   / /_/ /\\__ \\ |   / /_/ /
/ ___ |/ ____/ /___ /   / ____/___/ //   / ____/ 
/_/  |_/_/   /_____//_/|_/_/   /____//_/|_/_/    
   Autonomous Remote IT Commander & Deep Remediation Suite
========================================================================
"""


def main():
    parser = argparse.ArgumentParser(description="ApexSys Remote IT Commander Server")
    parser.add_argument("--host", default="0.0.0.0", help="Binding host IP (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable live code reloading")
    args = parser.parse_args()

    print(BANNER)
    print(f"[ApexSys] Serving Commander Web Dashboard at: http://127.0.0.1:{args.port}")
    print(f"[ApexSys] WebSocket Agent Broker Endpoint at: ws://127.0.0.1:{args.port}/ws/agent/{{client_id}}")
    print(f"[ApexSys] REST API Docs available at:         http://127.0.0.1:{args.port}/docs\n")

    uvicorn.run("backend.server:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
