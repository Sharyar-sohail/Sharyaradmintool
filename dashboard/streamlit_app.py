"""
ApexSys Executive Command Dashboard (GitHub Serverless State Sync)
Fetches live telemetry and diagnostic reports directly from the GitHub repository
(via raw content or GitHub API), displaying holistic health scores, categorical
diagnostics, and issue resolutions with ZERO paid servers or open ports.
"""

import datetime
import json
import os
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="ApexSys Autonomous IT Commander",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-Tech Cyberpunk & Glassmorphic Styling
st.markdown("""
<style>
    .reportview-container, .main, .block-container {
        background-color: #080b11;
        color: #e2e8f0;
    }
    .metric-card {
        background: rgba(13, 19, 33, 0.85);
        border: 1px solid rgba(0, 243, 255, 0.25);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .stButton>button {
        background: linear-gradient(135deg, #00f3ff, #00ff88);
        color: #07090e;
        font-weight: 800;
        border: none;
        border-radius: 6px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.5);
    }
    .sync-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 700;
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
        border: 1px solid #00ff88;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Configuration & Parameters -----------------
st.sidebar.markdown("## ⚡ **APEXSYS COMMANDER**")
st.sidebar.markdown("*100% Serverless GitHub State Sync Engine*")

DEFAULT_OWNER = os.getenv("GITHUB_REPO_OWNER", "SharyarSoahil")
DEFAULT_REPO = os.getenv("GITHUB_REPO_NAME", "Sharyaradmintool")
DEFAULT_BRANCH = os.getenv("GITHUB_BRANCH", "main")
DEFAULT_TOKEN = os.getenv("GITHUB_TOKEN", "")

with st.sidebar.expander("⚙️ Repository Settings", expanded=False):
    repo_owner = st.text_input("GitHub Owner", value=DEFAULT_OWNER)
    repo_name = st.text_input("GitHub Repository", value=DEFAULT_REPO)
    branch = st.text_input("Branch", value=DEFAULT_BRANCH)
    github_token = st.text_input("Personal Access Token (Optional)", value=DEFAULT_TOKEN, type="password")

refresh_rate = st.sidebar.slider("Auto-Refresh Rate (seconds)", min_value=5, max_value=60, value=15)
manual_refresh = st.sidebar.button("🔄 Refresh Telemetry Now", use_container_width=True)


# ----------------- Data Fetcher Engine -----------------
def fetch_status_from_github(owner: str, repo: str, branch_name: str, token: str = ""):
    """
    Fetches status.json using cache-busted raw GitHub URL or GitHub API fallback.
    """
    cache_buster = int(time.time())
    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/status.json?t={cache_buster}"
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    # Try Raw URL
    try:
        res = requests.get(raw_url, headers=headers, timeout=5)
        if res.status_code == 200 and res.text.strip():
            return json.loads(res.text), "GitHub Raw"
    except Exception:
        pass

    # Fallback to GitHub REST API
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/status.json?ref={branch_name}"
        res = requests.get(api_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "content" in data:
                import base64
                decoded = base64.b64decode(data["content"]).decode("utf-8")
                return json.loads(decoded), "GitHub REST API"
    except Exception:
        pass

    # Local fallback
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "status.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f), "Local File"
        except Exception:
            pass

    return None, "Unavailable"


# ----------------- Load Agent Script for Download -----------------
def get_customized_agent_script(owner: str, repo: str, branch_name: str, token: str) -> str:
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "ApexAgent.ps1")
    content = ""
    if os.path.exists(script_path):
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # Fetch from GitHub raw
        try:
            r = requests.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch_name}/agent/ApexAgent.ps1", timeout=5)
            if r.status_code == 200:
                content = r.text
        except Exception:
            pass

    # Inject configured parameters
    if content:
        content = content.replace('[string]$RepoOwner = "SharyarSoahil"', f'[string]$RepoOwner = "{owner}"')
        content = content.replace('[string]$RepoName = "Sharyaradmintool"', f'[string]$RepoName = "{repo}"')
        content = content.replace('[string]$Branch = "main"', f'[string]$Branch = "{branch_name}"')
        if token:
            content = content.replace('[string]$GitHubToken = $env:GITHUB_TOKEN', f'[string]$GitHubToken = "{token}"')
    return content


# Fetch telemetry state
status_data, fetch_source = fetch_status_from_github(repo_owner, repo_name, branch, github_token)

# ----------------- Top Deployment & Download Section -----------------
with st.expander("📥 Deploy & Run PowerShell Agent on Client PC", expanded=(status_data is None)):
    st.markdown("### 🚀 Serverless IT Commander Deployment")
    st.markdown(
        "Run this standalone PowerShell script as an **Administrator** on any Windows machine. "
        "It performs a multi-layer diagnostic scan (SMART drives, DISM/SFC integrity, Event Log BSODs, yellow-bang devices) "
        "and automatically pushes `status.json` back to this repository."
    )

    dcol1, dcol2 = st.columns([2, 1])
    with dcol1:
        st.markdown("**1. Download the pre-configured script:**")
        script_code = get_customized_agent_script(repo_owner, repo_name, branch, github_token)
        st.download_button(
            label="📥 Download Agent Script (ApexAgent.ps1)",
            data=script_code,
            file_name="ApexAgent.ps1",
            mime="application/x-powershell",
            use_container_width=True,
        )
    with dcol2:
        st.markdown("**Execution Modes:**")
        st.markdown("- **Single Scan & Push**: `.\\ApexAgent.ps1`")
        st.markdown("- **Continuous Sync (60s loop)**: `.\\ApexAgent.ps1 -Continuous 1`")

    st.markdown("---")
    st.markdown("**Or Execute Directly via PowerShell Admin One-Liner (Zero-Install):**")
    one_liner = (
        f'powershell.exe -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest -Uri \'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/agent/ApexAgent.ps1\' -OutFile ApexAgent.ps1; '
        f'.\\ApexAgent.ps1"'
    )
    st.code(one_liner, language="powershell")


# ----------------- Main Dashboard Rendering -----------------
if not status_data:
    st.warning("⏳ No diagnostic data found yet in `status.json`. Run the agent on your PC to initiate the first sync!")
    st.info("Once the agent executes `Push-ApexStatusToGitHub`, this dashboard will automatically update with complete machine diagnostics.")
    time.sleep(refresh_rate)
    st.rerun()

# Extract fields safely
client_id = status_data.get("client_id", "Unknown PC")
health_score = status_data.get("health_score", 100)
cat_scores = status_data.get("category_scores", {})
sys_info = status_data.get("system_info", {})
telemetry = status_data.get("telemetry", {})
diag = status_data.get("diagnostics", {})
issues = status_data.get("issues", [])
last_synced = status_data.get("last_synced", "Unknown")

# Calculate sync latency
sync_badge_color = "#00ff88"
age_text = "Just now"
try:
    ts_str = status_data.get("timestamp")
    if ts_str:
        # ISO parse
        clean_ts = ts_str.replace("Z", "+00:00")
        sync_time = datetime.datetime.fromisoformat(clean_ts)
        now_time = datetime.datetime.now(datetime.timezone.utc)
        diff_sec = int((now_time - sync_time).total_seconds())
        if diff_sec < 60:
            age_text = f"{diff_sec}s ago"
        elif diff_sec < 3600:
            age_text = f"{diff_sec // 60}m ago"
        else:
            age_text = f"{diff_sec // 3600}h ago"
            sync_badge_color = "#ffaa00"
except Exception:
    pass

# Top Machine Banner
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    admin_pill = "👑 Elevated Administrator" if sys_info.get("is_admin") else "⚠️ Standard User"
    st.markdown(f"## 🖥️ **{sys_info.get('hostname', client_id)}**")
    st.caption(f"{sys_info.get('os_name')} ({sys_info.get('architecture')}) | IP: {sys_info.get('ip_address')} | {admin_pill}")
with col_h2:
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <span class="sync-badge" style="color: {sync_badge_color}; border-color: {sync_badge_color};">
            ● GITHUB SYNC: {age_text}
        </span><br>
        <span style="font-size: 0.75rem; color: #a0aec0;">Source: {fetch_source}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Health Score Gauge & Categorical Radar Section
col_gauge, col_bars = st.columns([1, 2])

with col_gauge:
    st.markdown("### Holistic Vitality Index")
    gauge_color = "#00ff88" if health_score >= 80 else "#ffaa00" if health_score >= 50 else "#ff3366"

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "System Health Score", 'font': {'size': 18, 'color': "#ffffff"}},
        number={'font': {'size': 48, 'color': gauge_color}, 'suffix': "%"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#718096"},
            'bar': {'color': "#00f3ff"},
            'bgcolor': "#162136",
            'borderwidth': 2,
            'bordercolor': "#718096",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(255, 51, 102, 0.3)'},
                {'range': [50, 80], 'color': 'rgba(255, 170, 0, 0.3)'},
                {'range': [80, 100], 'color': 'rgba(0, 255, 136, 0.3)'},
            ],
        }
    ))
    fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=250, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_bars:
    st.markdown("### Categorical Health Breakdown")
    cats = list(cat_scores.keys()) if cat_scores else ["Hardware", "Operating System", "Storage", "Drivers", "Security"]
    scores = [cat_scores.get(c, 100) for c in cats]

    fig_bar = px.bar(
        x=scores,
        y=cats,
        orientation='h',
        text=scores,
        labels={'x': 'Integrity Score (%)', 'y': 'Diagnostic Category'},
        color=scores,
        color_continuous_scale=["#ff3366", "#ffaa00", "#00ff88"],
        range_color=[0, 100],
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        height=250,
        margin=dict(l=20, r=20, t=10, b=20),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# Live Telemetry Metrics
st.markdown("### 📈 Live Telemetry Snapshot")
tcol1, tcol2, tcol3, tcol4 = st.columns(4)
with tcol1:
    st.metric("CPU Utilization", f"{telemetry.get('cpu_percent', 0)}%", f"{telemetry.get('cpu_freq_mhz', 0)} MHz")
with tcol2:
    st.metric("RAM Utilization", f"{telemetry.get('ram_percent', 0)}%", f"{telemetry.get('ram_used_gb', 0)} / {sys_info.get('total_ram_gb', 0)} GB")
with tcol3:
    st.metric("System Disk (C:)", f"{telemetry.get('disk_percent', 0)}% Fill")
with tcol4:
    st.metric("Gateway Latency", f"{telemetry.get('net_latency_ms', 0)} ms")

# Detected Issues Triage
st.markdown(f"### 📋 Actionable Diagnostic Issues ({len(issues)})")
if not issues:
    st.success("✓ ALL SYSTEMS VERIFIED: No hardware failures, component store damage, or system errors detected.")
else:
    for idx, iss in enumerate(issues, 1):
        sev = iss.get("severity", "INFO")
        color = "#ff3366" if sev == "CRITICAL" else "#ffaa00" if sev == "WARNING" else "#00f3ff"
        st.markdown(f"""
        <div style="border-left: 4px solid {color}; padding: 10px 16px; background: rgba(16,24,39,0.6); margin-bottom: 10px; border-radius: 6px;">
            <strong style="color: #fff;">[{iss.get('category')}] {iss.get('title')}</strong> 
            <span style="color: {color}; font-size: 0.8rem; font-weight: 700;">({sev})</span><br>
            <span style="color: #cbd5e0; font-size: 0.85rem;">{iss.get('description')}</span><br>
            <span style="color: var(--neon-cyan); font-family: monospace; font-size: 0.78rem;">Suggested Fix: {iss.get('fix_id')}</span>
        </div>
        """, unsafe_allow_html=True)

# Detailed Hardware & OS Audits
st.markdown("### 🔍 Deep Diagnostic Audits")
tab_hw, tab_os, tab_stor, tab_sec = st.tabs(["Hardware & Devices", "OS Integrity (DISM/SFC)", "Storage & Junk", "Security & BSODs"])

with tab_hw:
    hw_data = diag.get("hardware", {})
    st.markdown(f"**Processor**: `{sys_info.get('cpu_model')}` ({sys_info.get('cpu_cores')} logical cores)")
    st.markdown(f"**RAM Capacity**: `{sys_info.get('total_ram_gb')} GB`")

    drives = hw_data.get("smart_drives", [])
    if drives:
        st.markdown("#### Physical Drives (SMART Status)")
        df_drives = pd.DataFrame(drives)[["device_id", "model", "media_type", "size_gb", "health_status", "operational_status", "bad_sectors"]]
        st.dataframe(df_drives, use_container_width=True)

    failing_devs = hw_data.get("failing_devices", [])
    if failing_devs:
        st.markdown("#### Failing or Missing Hardware Devices (Yellow-Bangs)")
        df_pnp = pd.DataFrame(failing_devs)[["name", "code", "status", "error_desc"]]
        st.dataframe(df_pnp, use_container_width=True)
    else:
        st.info("No failing or unconfigured PnP devices found in Device Manager.")

with tab_os:
    os_data = diag.get("os_integrity", {})
    dism_stat = os_data.get("dism_status", "Healthy")
    sfc_stat = "Corrupted Binaries Flagged" if os_data.get("sfc_corrupted") else "Clean / Intact"
    st.markdown(f"- **DISM Component Store**: `{dism_stat}`")
    st.markdown(f"- **System File Checker (SFC)**: `{sfc_stat}`")
    st.markdown(f"- **CBS Servicing Log Errors**: `{os_data.get('cbs_error_count', 0)} entries`")

with tab_stor:
    stor_data = diag.get("storage", {})
    junk_mb = stor_data.get("temp_junk_mb", 0)
    st.markdown(f"**Total Deep Junk & Cache Bloat**: `{junk_mb} MB` ({round(junk_mb/1024, 2)} GB)")
    st.caption("Includes Windows Temp, User Temp, Prefetch, and servicing download caches.")

    log_drives = stor_data.get("drives", [])
    if log_drives:
        st.markdown("#### Logical Volumes Capacity")
        df_log = pd.DataFrame(log_drives)[["letter", "total_gb", "free_gb", "free_pct"]]
        st.dataframe(df_log, use_container_width=True)

with tab_sec:
    sec_data = diag.get("security", {})
    bsod_count = sec_data.get("bsod_events_count", 0)
    latest_bsod = sec_data.get("latest_bsod_code", "None")
    st.markdown(f"- **Recent BSOD Crashes (Last 48h)**: `{bsod_count} events`")
    if latest_bsod:
        st.markdown(f"- **Latest BugCheck / Crash Code**: `{latest_bsod}`")

# Auto-refresh loop
time.sleep(refresh_rate)
st.rerun()
