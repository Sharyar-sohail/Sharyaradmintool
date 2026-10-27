"""
ApexSys State Fetcher & Payload Handler
Handles fetching scoped client diagnostics from GitHub Raw, GitHub REST API,
or local scoped directories with UTF-8 BOM safety and zero caching.
"""

import json
import os
import time
from typing import Any, Dict, Optional, Tuple
import requests


def fetch_isolated_status(
    agent_token: str,
    owner: str = "SharyarSoahil",
    repo: str = "Sharyaradmintool",
    branch_name: str = "main",
    token: str = "",
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Fetches the diagnostics payload scoped exclusively to clients/{agent_token}/status.json.
    """
    if not agent_token:
        return None, "No Token Provided"

    cache_buster = int(time.time())
    relative_path = f"clients/{agent_token}/status.json"
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/{relative_path}?t={cache_buster}"
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    # 1. Fetch from GitHub Raw
    try:
        res = requests.get(raw_url, headers=headers, timeout=5)
        if res.status_code == 200 and res.content.strip():
            clean_str = res.content.decode("utf-8-sig")
            return json.loads(clean_str), "GitHub Raw"
    except Exception:
        pass

    # 2. Fallback to GitHub REST API
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{relative_path}?ref={branch_name}"
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "content" in data:
                import base64
                raw_bytes = base64.b64decode(data["content"])
                decoded = raw_bytes.decode("utf-8-sig")
                return json.loads(decoded), "GitHub REST API"
    except Exception:
        pass

    # 3. Local scoped filesystem fallback
    local_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "clients",
        agent_token,
        "status.json",
    )
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8-sig") as f:
                return json.load(f), "Local Scoped File"
        except Exception:
            pass

    return None, "Unavailable"


def get_customized_agent_script(token: str, owner: str, repo: str, branch_name: str) -> str:
    """Generates an agent script pre-bound to the user's isolated session token."""
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "ApexAgent.ps1")
    content = ""
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    else:
        try:
            r = requests.get(
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/agent/ApexAgent.ps1",
                timeout=5,
            )
            if r.status_code == 200:
                content = r.text
        except Exception:
            pass

    if content:
        content = content.replace('[string]$AgentToken = ""', f'[string]$AgentToken = "{token}"')
        content = content.replace('[string]$RepoOwner = "SharyarSoahil"', f'[string]$RepoOwner = "{owner}"')
        content = content.replace('[string]$RepoName = "Sharyaradmintool"', f'[string]$RepoName = "{repo}"')
        content = content.replace('[string]$Branch = "main"', f'[string]$Branch = "{branch_name}"')
    return content
