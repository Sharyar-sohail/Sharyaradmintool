"""
ApexSys State Fetcher & Remote Maintenance Command Dispatcher
Handles fetching scoped client diagnostics and transmitting remote cleanup commands
via GitHub Raw, GitHub REST API, or local scoped directories with zero caching.
"""

import base64
import datetime
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


def fetch_isolated_commands(
    agent_token: str,
    owner: str = "SharyarSoahil",
    repo: str = "Sharyaradmintool",
    branch_name: str = "main",
    token: str = "",
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Fetches the current command state from clients/{agent_token}/commands.json.
    """
    if not agent_token:
        return None, "No Token"

    cache_buster = int(time.time())
    relative_path = f"clients/{agent_token}/commands.json"
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/{relative_path}?t={cache_buster}"
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        res = requests.get(raw_url, headers=headers, timeout=5)
        if res.status_code == 200 and res.content.strip():
            clean_str = res.content.decode("utf-8-sig")
            return json.loads(clean_str), "GitHub Raw"
    except Exception:
        pass

    # Fallback to local file
    local_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "clients",
        agent_token,
        "commands.json",
    )
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8-sig") as f:
                return json.load(f), "Local File"
        except Exception:
            pass

    return None, "Unavailable"


def send_isolated_command(
    agent_token: str,
    action: str,
    parameters: Optional[Dict[str, Any]] = None,
    owner: str = "SharyarSoahil",
    repo: str = "Sharyaradmintool",
    branch_name: str = "main",
    token: str = "",
) -> Tuple[bool, str]:
    """
    Dispatches a remote cleanup/maintenance command to clients/{agent_token}/commands.json.
    """
    cmd_id = f"CMD-{int(time.time())}-{random_hex(4)}"
    cmd_payload = {
        "command_id": cmd_id,
        "agent_token": agent_token,
        "action": action,
        "parameters": parameters or {},
        "status": "PENDING",
        "requested_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "completed_at": None,
        "result": None,
    }

    relative_path = f"clients/{agent_token}/commands.json"
    content_str = json.dumps(cmd_payload, indent=2)

    # 1. Update local file if workspace exists
    local_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clients", agent_token)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, "commands.json")
    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(content_str)
    except Exception:
        pass

    gh_token = token or os.getenv("GITHUB_TOKEN", "")

    # 2. Push to GitHub via REST API if token available
    if gh_token:
        try:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{relative_path}"
            headers = {
                "Authorization": f"token {gh_token}",
                "User-Agent": "ApexSys-Streamlit-Commander",
                "Accept": "application/vnd.github.v3+json",
            }
            # Check existing file SHA
            sha = None
            try:
                check_res = requests.get(api_url + f"?ref={branch_name}", headers=headers, timeout=5)
                if check_res.status_code == 200:
                    sha = check_res.json().get("sha")
            except Exception:
                pass

            base64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
            body = {
                "message": f"ApexSys Remote Directive [{agent_token}]: {action}",
                "content": base64_content,
                "branch": branch_name,
            }
            if sha:
                body["sha"] = sha

            put_res = requests.put(api_url, headers=headers, json=body, timeout=8)
            if put_res.status_code in [200, 201]:
                return True, f"Directive '{action}' pushed to GitHub queue for {agent_token}."
            else:
                return False, f"GitHub API error: {put_res.status_code} {put_res.text[:100]}"
        except Exception as e:
            return False, f"GitHub dispatch failed: {str(e)}"

    # 3. Fallback: If in local Git repository, commit and push via git CLI
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.exists(os.path.join(repo_root, ".git")):
        import subprocess
        try:
            subprocess.run(["git", "add", relative_path], cwd=repo_root, capture_output=True, timeout=5)
            subprocess.run(
                ["git", "commit", "-m", f"ApexSys Remote Directive [{agent_token}]: {action}"],
                cwd=repo_root,
                capture_output=True,
                timeout=5,
            )
            push_res = subprocess.run(["git", "push", "origin", branch_name], cwd=repo_root, capture_output=True, timeout=10)
            if push_res.returncode == 0:
                return True, f"Directive '{action}' committed and pushed via local Git."
        except Exception:
            pass

    # 4. If no remote credentials, staged locally
    return True, f"Directive '{action}' staged locally at {relative_path}."


def random_hex(length: int = 4) -> str:
    import random
    return "".join(random.choices("0123456789ABCDEF", k=length))


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
