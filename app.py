"""
ApexSys Streamlit Cloud Alternative Entrypoint (app.py)
Delegates execution directly to dashboard/streamlit_app.py
"""

import os
import sys
from pathlib import Path

# Add project root and dashboard directory to sys.path
_root_dir = Path(__file__).resolve().parent
_dashboard_dir = _root_dir / "dashboard"

for _p in [str(_root_dir), str(_dashboard_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import runpy

target_script = str(_dashboard_dir / "streamlit_app.py")
runpy.run_path(target_script, run_name="__main__")
