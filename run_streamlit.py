"""
ApexSys Streamlit Companion Launcher
"""

import os
import sys
import subprocess

if __name__ == "__main__":
    app_path = os.path.join(os.path.dirname(__file__), "dashboard", "streamlit_app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.port", "8501"]
    subprocess.run(cmd)
