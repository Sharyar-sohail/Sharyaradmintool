"""
ApexSys Executive Command Dashboard - Ultra-Powerful Windows Repair, Optimization & Administration Suite
Strict Multi-User Session Isolation Architecture with GitHub-based zero-cost state syncing.
Each user/administrator links to an exclusive Agent Token. Telemetry is scoped exclusively
to clients/{AGENT_TOKEN}/status.json and commands.json with zero cross-tenant data mixing.
"""

import datetime
import json
import os
import random
import time
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="ApexSys Windows Repair & Admin Suite",
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
    .token-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 14px;
        font-size: 0.85rem;
        font-family: monospace;
        font-weight: 800;
        background: rgba(0, 243, 255, 0.15);
        color: #00f3ff;
        border: 1px solid #00f3ff;
    }
    .status-badge-online {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 700;
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
        border: 1px solid #00ff88;
    }
    .status-badge-offline {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 700;
        background: rgba(255, 51, 102, 0.15);
        color: #ff3366;
        border: 1px solid #ff3366;
    }
    .terminal-box {
        background-color: #04060a;
        color: #00ff88;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 0.85rem;
        padding: 14px;
        border-radius: 8px;
        border: 1px solid rgba(0, 243, 255, 0.3);
        max-height: 420px;
        overflow-y: auto;
        white-space: pre-wrap;
        box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.8);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Configuration & State Fetchers -----------------
import sys
from pathlib import Path

# Ensure both repository root and dashboard directory are present in sys.path
_current_dir = Path(__file__).resolve().parent
_repo_root = _current_dir.parent
for _p in [str(_repo_root), str(_current_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from dashboard.fetcher import (
        fetch_isolated_status,
        fetch_isolated_commands,
        send_isolated_command,
        get_customized_agent_script,
    )
except (ImportError, ModuleNotFoundError):
    from fetcher import (
        fetch_isolated_status,
        fetch_isolated_commands,
        send_isolated_command,
        get_customized_agent_script,
    )

DEFAULT_OWNER = os.getenv("GITHUB_REPO_OWNER", "SharyarSoahil")
DEFAULT_REPO = os.getenv("GITHUB_REPO_NAME", "Sharyaradmintool")
DEFAULT_BRANCH = os.getenv("GITHUB_BRANCH", "main")
DEFAULT_TOKEN = os.getenv("GITHUB_TOKEN", "")

# ----------------- Multi-User Session Token Resolution -----------------
query_token = st.query_params.get("token")
if query_token and "agent_token" not in st.session_state:
    st.session_state["agent_token"] = str(query_token).strip().upper()

if "suggested_token" not in st.session_state:
    rand_hex = "".join(random.choices("0123456789ABCDEF", k=8))
    st.session_state["suggested_token"] = f"APEX-{rand_hex}"

# ----------------- SESSION GATEWAY SCREEN -----------------
current_token = st.session_state.get("agent_token", "").strip().upper()

if not current_token:
    st.markdown("## ⚡ **APEXSYS ENTERPRISE WINDOWS REPAIR & ADMIN SUITE**")
    st.markdown("### 🔒 Zero-Contamination Multi-User Session Gateway")
    st.info("ApexSys enforces strict multi-tenant isolation. Telemetry and remote maintenance queues are scoped strictly to your unique Agent Token with zero cross-tenant mixing.")

    col_gate1, col_gate2 = st.columns(2)

    with col_gate1:
        st.markdown("#### 🔑 Connect Existing Client Machine")
        st.markdown("Enter the unique Session Token generated when launching the agent on your client machine:")
        input_token = st.text_input("Agent Session Token", placeholder="e.g. APEX-A1B2C3D4", key="login_token_input")
        if st.button("🚀 Access Isolated Session", use_container_width=True):
            if input_token.strip():
                clean_t = input_token.strip().upper()
                st.session_state["agent_token"] = clean_t
                st.query_params["token"] = clean_t
                st.rerun()
            else:
                st.error("Please enter a valid session token.")

        st.markdown("---")
        st.caption("Quick Test: Click below to load the pre-verified demo workstation telemetry:")
        if st.button("🧪 Launch Verified Demo Machine (APEX-DEMO01)", use_container_width=True):
            st.session_state["agent_token"] = "APEX-DEMO01"
            st.query_params["token"] = "APEX-DEMO01"
            st.rerun()

    with col_gate2:
        st.markdown("#### ⚡ Generate New Token & Deploy Agent")
        st.markdown("Provision a new target system with a freshly generated, pre-linked session token:")
        new_token = st.session_state["suggested_token"]
        st.code(new_token, language="text")

        prelinked_script = get_customized_agent_script(new_token, DEFAULT_OWNER, DEFAULT_REPO, DEFAULT_BRANCH)
        st.download_button(
            label=f"📥 Download Pre-Bound Agent ({new_token})",
            data=prelinked_script,
            file_name=f"ApexAgent_{new_token}.ps1",
            mime="application/x-powershell",
            use_container_width=True,
        )

        if st.button(f"Launch Session with {new_token}", use_container_width=True):
            st.session_state["agent_token"] = new_token
            st.query_params["token"] = new_token
            st.rerun()

    st.stop()


# ----------------- ACTIVE ISOLATED SESSION VIEW -----------------
st.sidebar.markdown("## ⚡ **APEXSYS COMMANDER**")
st.sidebar.markdown(f"**Linked Machine:** <span class='token-badge'>{current_token}</span>", unsafe_allow_html=True)

if st.sidebar.button("🔒 Switch Agent / Disconnect", use_container_width=True):
    del st.session_state["agent_token"]
    if "token" in st.query_params:
        del st.query_params["token"]
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Repository & Auth Settings", expanded=False):
    repo_owner = st.text_input("GitHub Owner", value=DEFAULT_OWNER)
    repo_name = st.text_input("GitHub Repository", value=DEFAULT_REPO)
    branch = st.text_input("Branch", value=DEFAULT_BRANCH)
    github_token = st.text_input("Personal Access Token (Optional)", value=DEFAULT_TOKEN, type="password")

refresh_rate = st.sidebar.slider("Auto-Refresh Rate (seconds)", min_value=5, max_value=60, value=15)
if st.sidebar.button("🔄 Refresh Telemetry Now", use_container_width=True):
    st.rerun()

# Fetch isolated telemetry
status_data, fetch_source = fetch_isolated_status(current_token, repo_owner, repo_name, branch, github_token)

# Shareable URL
share_url = f"?token={current_token}"
st.sidebar.caption(f"Direct Session Link: `{share_url}`")

# ----------------- Top Deployment & Script Card -----------------
with st.expander(f"📥 PowerShell Agent Deployment & One-Liner [{current_token}]", expanded=(status_data is None)):
    st.markdown("### 🚀 Client Agent Deployment")
    st.markdown(
        f"This agent script is **pre-bound specifically to Token `{current_token}`**. "
        f"All diagnostic metrics and commands are scoped exclusively to `clients/{current_token}/` on GitHub."
    )

    dcol1, dcol2 = st.columns([2, 1])
    with dcol1:
        agent_script_code = get_customized_agent_script(current_token, repo_owner, repo_name, branch)
        st.download_button(
            label=f"📥 Download Linked Agent ({current_token})",
            data=agent_script_code,
            file_name=f"ApexAgent_{current_token}.ps1",
            mime="application/x-powershell",
            use_container_width=True,
        )
    with dcol2:
        st.markdown("**Run on Client PC (Admin):**")
        st.markdown(f"- Single scan: `.\\ApexAgent.ps1 -AgentToken {current_token}`")
        st.markdown(f"- Continuous loop: `.\\ApexAgent.ps1 -AgentToken {current_token} -Continuous 1`")

    st.markdown("---")
    st.markdown("**Zero-Install Admin One-Liner (Run directly in PowerShell as Admin):**")
    one_liner = (
        f'powershell.exe -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest -Uri \'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/agent/ApexAgent.ps1\' -OutFile ApexAgent.ps1; '
        f'.\\ApexAgent.ps1 -AgentToken {current_token}"'
    )
    st.code(one_liner, language="powershell")


# ----------------- Status Data Validation -----------------
if not status_data:
    st.warning(f"⏳ Waiting for Agent `{current_token}` to publish its initial diagnostic scan...")
    st.info(f"Run `ApexAgent.ps1 -AgentToken {current_token}` on your client PC. Once completed, your private command dashboard will activate automatically.")
    time.sleep(refresh_rate)
    st.rerun()
    st.stop()

# Extract fields
client_id = status_data.get("client_id", "Unknown PC")
agent_status = status_data.get("status", "ONLINE").upper()
health_score = status_data.get("health_score", 100)
cat_scores = status_data.get("category_scores", {})
sys_info = status_data.get("system_info", {})
telemetry = status_data.get("telemetry", {})
diag = status_data.get("diagnostics", {})
issues = status_data.get("issues", [])
last_synced = status_data.get("last_synced", "Unknown")

# Calculate sync latency
age_text = "Just now"
try:
    ts_str = status_data.get("timestamp")
    if ts_str:
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
except Exception:
    pass

# Top Machine Banner
col_h1, col_h2 = st.columns([3, 2])
with col_h1:
    admin_pill = "👑 Elevated Administrator" if sys_info.get("is_admin") else "⚠️ Standard User"
    st.markdown(f"## 🖥️ **{sys_info.get('hostname', client_id)}**")
    st.caption(f"{sys_info.get('os_name')} (Build {sys_info.get('os_build')}, {sys_info.get('architecture')}) | IP: {sys_info.get('ip_address')} | {admin_pill}")

with col_h2:
    status_badge_html = (
        f"<span class='status-badge-online'>● ONLINE (Synced: {age_text})</span>"
        if agent_status == "ONLINE"
        else f"<span class='status-badge-offline'>■ TERMINATED / OFFLINE ({last_synced})</span>"
    )
    st.markdown(f"""
    <div style="text-align: right; padding-top: 6px;">
        {status_badge_html}
        <span class="token-badge" style="margin-left: 8px;">TOKEN: {current_token}</span><br>
        <span style="font-size: 0.75rem; color: #a0aec0;">Feed: {fetch_source}</span>
    </div>
    """, unsafe_allow_html=True)

if agent_status == "OFFLINE":
    st.error(f"⚠️ CLIENT AGENT TERMINATED: Process cleanly exited at {last_synced}. Showing last recorded diagnostic state.")

st.markdown("---")

# Health Score Gauge & Categorical Breakdown
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
    fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=240, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_bars:
    st.markdown("### Categorical Breakdown")
    cats = list(cat_scores.keys()) if cat_scores else ["Hardware", "Operating System", "Storage", "Drivers", "Security"]
    scores = [cat_scores.get(c, 100) for c in cats]

    fig_bar = px.bar(
        x=scores,
        y=cats,
        orientation='h',
        text=scores,
        labels={'x': 'Integrity Score (%)', 'y': 'Category'},
        color=scores,
        color_continuous_scale=["#ff3366", "#ffaa00", "#00ff88"],
        range_color=[0, 100],
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0"),
        height=240,
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

st.markdown("---")

# ----------------- Fetch latest command state -----------------
cmd_data, cmd_source = fetch_isolated_commands(current_token, repo_owner, repo_name, branch, github_token)

# ----------------- ENTERPRISE CONTROL TABS -----------------
tab_issues, tab_av, tab_pkg, tab_svc, tab_stor, tab_diag, tab_term = st.tabs([
    "📋 Actionable Issues",
    "🛡️ Antivirus & Threats",
    "📦 Software (winget)",
    "⚙️ Services & Startup",
    "🛠️ Storage & Network",
    "🔍 Deep Audits (Hardware/OS)",
    "💻 Live Terminal Console",
])

# ----------------- TAB 1: Actionable Issues -----------------
with tab_issues:
    st.markdown(f"### 📋 Actionable Diagnostic Issues ({len(issues)})")
    if not issues:
        st.success("✓ ALL SYSTEMS VERIFIED: Zero hardware faults, component store damage, or virus threats detected.")
    else:
        for idx, iss in enumerate(issues, 1):
            sev = iss.get("severity", "INFO")
            color = "#ff3366" if sev == "CRITICAL" else "#ffaa00" if sev == "WARNING" else "#00f3ff"
            fix_id = iss.get("fix_id")

            col_iss_txt, col_iss_btn = st.columns([5, 1])
            with col_iss_txt:
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding: 10px 16px; background: rgba(16,24,39,0.6); margin-bottom: 8px; border-radius: 6px;">
                    <strong style="color: #fff;">[{iss.get('category')}] {iss.get('title')}</strong> 
                    <span style="color: {color}; font-size: 0.8rem; font-weight: 700;">({sev})</span><br>
                    <span style="color: #cbd5e0; font-size: 0.85rem;">{iss.get('description')}</span><br>
                    <span style="color: #00f3ff; font-family: monospace; font-size: 0.78rem;">Fix Directive: {fix_id}</span>
                </div>
                """, unsafe_allow_html=True)
            with col_iss_btn:
                if fix_id:
                    if st.button("⚡ Remediate", key=f"fix_btn_{idx}_{fix_id}", use_container_width=True):
                        ok, msg = send_isolated_command(current_token, fix_id, {}, repo_owner, repo_name, branch, github_token)
                        if ok:
                            st.toast(f"Remediation directive {fix_id} dispatched!")
                            st.success(f"Dispatched {fix_id}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)

# ----------------- TAB 2: Antivirus & Threat Defense -----------------
with tab_av:
    st.markdown("### 🛡️ Microsoft Defender & Threat Defense")
    av_data = diag.get("antivirus", {})
    av_enabled = av_data.get("enabled", False)
    av_realtime = av_data.get("realtime_protection", False)
    av_sig = av_data.get("signature_version", "Unknown")
    av_update = av_data.get("last_signature_update", "Unknown")
    av_scan_age = av_data.get("quick_scan_age_days", -1)
    threats = av_data.get("threats", [])
    active_threats_count = av_data.get("active_threats_count", 0)

    # Status Cards
    av_c1, av_c2, av_c3 = st.columns(3)
    with av_c1:
        rt_badge = "🟢 ACTIVE / PROTECTED" if av_realtime else "🔴 DISABLED"
        st.metric("Real-Time Protection", rt_badge)
    with av_c2:
        st.metric("Signature Version", av_sig, f"Updated: {av_update}")
    with av_c3:
        scan_txt = f"{av_scan_age} days ago" if av_scan_age >= 0 else "Never"
        st.metric("Last Quick Scan", scan_txt)

    # Antivirus Action Triggers
    st.markdown("#### ⚡ Antivirus Actions")
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("🛡️ Run Quick Virus Scan", key="btn_av_quick", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_VIRUS_SCAN", {}, repo_owner, repo_name, branch, github_token)
            if ok:
                st.toast("Quick virus scan queued!")
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with btn_col2:
        if st.button("🔬 Run Full System Scan", key="btn_av_full", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_FULL_VIRUS_SCAN", {}, repo_owner, repo_name, branch, github_token)
            if ok:
                st.toast("Full scan queued!")
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)
    with btn_col3:
        if st.button("🔄 Update Virus Definitions", key="btn_av_update", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "UPDATE_VIRUS_SIGNATURES", {}, repo_owner, repo_name, branch, github_token)
            if ok:
                st.toast("Definition update queued!")
                st.success(msg)
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown(f"#### 🚨 Threat Detection History ({len(threats)} total, {active_threats_count} active)")
    if not threats:
        st.info("No malware or virus threats recorded by Microsoft Defender.")
    else:
        df_th = pd.DataFrame(threats)
        st.dataframe(df_th, use_container_width=True)

# ----------------- TAB 3: Software & winget Packaging -----------------
with tab_pkg:
    st.markdown("### 📦 Software & Package Management (winget)")
    soft_data = diag.get("software", {})
    winget_ok = soft_data.get("winget_available", False)
    installed_apps = soft_data.get("installed_apps", [])
    total_apps_count = soft_data.get("installed_count", len(installed_apps))

    if not winget_ok:
        st.warning("⚠️ Windows Package Manager (`winget.exe`) was not detected on this machine. Remote installations require winget or App Installer.")

    st.markdown("#### ⚡ 1-Click Essential IT Admin Utilities")
    st.caption("Deploy verified enterprise utilities silently via Windows Package Manager:")
    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        if st.button("📥 Install 7-Zip (7zip.7zip)", key="pkg_7zip", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": "7zip.7zip"}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Installing 7-Zip..."); st.success(msg); time.sleep(1); st.rerun()
        if st.button("📥 Install Google Chrome", key="pkg_chrome", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": "Google.Chrome"}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Installing Google Chrome..."); st.success(msg); time.sleep(1); st.rerun()
    with pcol2:
        if st.button("📥 Install VS Code", key="pkg_vscode", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": "Microsoft.VisualStudioCode"}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Installing VS Code..."); st.success(msg); time.sleep(1); st.rerun()
        if st.button("📥 Install Git for Windows", key="pkg_git", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": "Git.Git"}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Installing Git..."); st.success(msg); time.sleep(1); st.rerun()
    with pcol3:
        if st.button("📥 Install Notepad++", key="pkg_npp", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": "Notepad++.Notepad++"}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Installing Notepad++..."); st.success(msg); time.sleep(1); st.rerun()
        if st.button("🚀 Upgrade All Software", key="pkg_upg_all", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "WINGET_UPGRADE_ALL", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Upgrading all packages..."); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown("#### 🎯 Custom Package Management")
    c_pkg1, c_pkg2 = st.columns(2)
    with c_pkg1:
        st.markdown("**Remote Install by Package ID:**")
        custom_install_id = st.text_input("Package ID to Install", placeholder="e.g. Mozilla.Firefox, Zoom.Zoom", key="in_pkg_install")
        if st.button("Install Package", key="btn_custom_install"):
            if custom_install_id.strip():
                ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": custom_install_id.strip()}, repo_owner, repo_name, branch, github_token)
                if ok: st.toast(f"Installing {custom_install_id}..."); st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)
    with c_pkg2:
        st.markdown("**Remote Uninstall by Package ID:**")
        custom_uninstall_id = st.text_input("Package ID to Uninstall", placeholder="e.g. 7zip.7zip", key="in_pkg_uninstall")
        if st.button("Uninstall Package", key="btn_custom_uninstall"):
            if custom_uninstall_id.strip():
                ok, msg = send_isolated_command(current_token, "WINGET_UNINSTALL", {"package_id": custom_uninstall_id.strip()}, repo_owner, repo_name, branch, github_token)
                if ok: st.toast(f"Uninstalling {custom_uninstall_id}..."); st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

    st.markdown("---")
    st.markdown(f"#### 📋 Installed Software Inventory ({total_apps_count} detected)")
    if installed_apps:
        df_apps = pd.DataFrame(installed_apps)
        st.dataframe(df_apps, use_container_width=True)

# ----------------- TAB 4: Services & Startup Control -----------------
with tab_svc:
    st.markdown("### ⚙️ Windows Services & Startup Program Control")
    svc_data = diag.get("services", {})
    crit_services = svc_data.get("critical_services", [])
    startup_items = svc_data.get("startup_items", [])

    st.markdown("#### 🔄 Critical Windows Services")
    if crit_services:
        df_svc = pd.DataFrame(crit_services)
        st.dataframe(df_svc[["name", "display_name", "status", "start_type"]], use_container_width=True)

    st.markdown("#### ⚡ Service Remote Controller")
    scol1, scol2, scol3 = st.columns([2, 1, 1])
    with scol1:
        selected_svc = st.selectbox(
            "Select Service to Manage",
            options=[s.get("name") for s in crit_services] if crit_services else ["wuauserv", "Spooler", "BITS", "WinDefend", "Dhcp", "Dnscache"]
        )
    with scol2:
        if st.button("🔄 Restart Service", key="btn_restart_svc", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "SERVICE_RESTART", {"service_name": selected_svc}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast(f"Restarting {selected_svc}..."); st.success(msg); time.sleep(1); st.rerun()
    with scol3:
        if st.button("▶️ Start / ⏹️ Stop", key="btn_toggle_svc", use_container_width=True):
            # Check current status
            curr_s = next((s.get("status") for s in crit_services if s.get("name") == selected_svc), "Running")
            target_act = "SERVICE_STOP" if curr_s == "Running" else "SERVICE_START"
            ok, msg = send_isolated_command(current_token, target_act, {"service_name": selected_svc}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast(f"Executing {target_act} on {selected_svc}..."); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown(f"#### 🚀 Startup Applications ({len(startup_items)} items audited)")
    if startup_items:
        df_start = pd.DataFrame(startup_items)
        st.dataframe(df_start[["name", "command", "location", "user"]], use_container_width=True)

# ----------------- TAB 5: Storage & Network Optimization -----------------
with tab_stor:
    st.markdown("### 🛠️ Storage & Deep Cache Optimization")
    stor_data = diag.get("storage", {})
    total_junk = stor_data.get("temp_junk_mb", 0)
    junk_bd = stor_data.get("junk_breakdown", {})

    st.metric("Total Deep Junk Bloat", f"{total_junk} MB", f"{round(total_junk/1024, 2)} GB")

    jcol1, jcol2, jcol3, jcol4, jcol5 = st.columns(5)
    with jcol1: st.metric("User Temp", f"{junk_bd.get('user_temp_mb', 0)} MB")
    with jcol2: st.metric("Windows Temp", f"{junk_bd.get('win_temp_mb', 0)} MB")
    with jcol3: st.metric("Prefetch", f"{junk_bd.get('prefetch_mb', 0)} MB")
    with jcol4: st.metric("SoftwareDist", f"{junk_bd.get('softwaredist_mb', 0)} MB")
    with jcol5: st.metric("WER / Dumps", f"{junk_bd.get('wer_dumps_mb', 0)} MB")

    st.markdown("#### ⚡ Storage Maintenance Actions")
    cl_col1, cl_col2, cl_col3, cl_col4 = st.columns(4)
    with cl_col1:
        if st.button("🧹 Clean All Deep Junk", key="btn_cl_all", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_ALL_JUNK", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Clean All Junk queued!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col2:
        if st.button("🗂️ Purge Temp Files", key="btn_cl_temp", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_TEMP", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Temp purge queued!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col3:
        if st.button("⚡ Purge Prefetch", key="btn_cl_prefetch", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_PREFETCH", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Prefetch purge queued!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col4:
        if st.button("📦 Purge Update Cache", key="btn_cl_softwaredist", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_SOFTWAREDIST", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Update cache purge queued!"); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown("### 🌐 Network Stack Troubleshooting")
    net_data = diag.get("network", {})
    st.markdown(f"- **Primary IP**: `{net_data.get('primary_ip', 'Unknown')}`")
    st.markdown(f"- **DNS Resolution Latency**: `{net_data.get('dns_latency_ms', 0)} ms`")

    if st.button("🌐 Flush DNS & Reset TCP/IP Stack", key="btn_reset_network", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "RESET_NETWORK", {}, repo_owner, repo_name, branch, github_token)
        if ok: st.toast("Network stack reset queued!"); st.success(msg); time.sleep(1); st.rerun()

    adapters = net_data.get("adapters", [])
    if adapters:
        st.markdown("#### Active Network Adapters")
        st.dataframe(pd.DataFrame(adapters)[["name", "status", "link_speed", "mac", "description"]], use_container_width=True)

# ----------------- TAB 6: Deep Audits (Hardware & OS) -----------------
with tab_diag:
    st.markdown("### 🔍 Hardware SMART & OS Integrity Diagnostics")
    hw_data = diag.get("hardware", {})
    os_data = diag.get("os_integrity", {})

    st.markdown(f"**Processor**: `{sys_info.get('cpu_model')}` ({sys_info.get('cpu_cores')} cores) | Current Clock: `{hw_data.get('cpu_curr_mhz')} MHz`")

    drives = hw_data.get("smart_drives", [])
    if drives:
        st.markdown("#### Physical Drives (SMART Status)")
        st.dataframe(pd.DataFrame(drives)[["device_id", "model", "media_type", "size_gb", "health_status", "operational_status", "bad_sectors"]], use_container_width=True)

    failing_devs = hw_data.get("failing_devices", [])
    if failing_devs:
        st.markdown("#### Failing or Missing Hardware Devices (Yellow-Bangs)")
        st.dataframe(pd.DataFrame(failing_devs)[["name", "code", "status", "error_desc"]], use_container_width=True)
    else:
        st.info("No failing PnP devices flagged in Device Manager.")

    st.markdown("#### Windows Component Store & Servicing Logs")
    st.markdown(f"- **DISM Component Store**: `{os_data.get('dism_status')}`")
    st.markdown(f"- **SFC Corrupted Binaries**: `{'Corrupted Binaries Flagged' if os_data.get('sfc_corrupted') else 'Clean / Intact'}`")
    st.markdown(f"- **CBS Error Count**: `{os_data.get('cbs_error_count', 0)} logged errors`")

    st.markdown("---")
    st.markdown("#### ⚡ OS Integrity Repairs")
    os_b1, os_b2, os_b3 = st.columns(3)
    with os_b1:
        if st.button("🛠️ Run SFC System File Repair", key="btn_sfc_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_SFC_REPAIR", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("SFC Repair queued!"); st.success(msg); time.sleep(1); st.rerun()
    with os_b2:
        if st.button("🏥 Run DISM RestoreHealth", key="btn_dism_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_DISM_RESTORE", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("DISM RestoreHealth queued!"); st.success(msg); time.sleep(1); st.rerun()
    with os_b3:
        if st.button("🧹 Clean Component Store", key="btn_clean_comp_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_COMPONENT_STORE", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Component cleanup queued!"); st.success(msg); time.sleep(1); st.rerun()

# ----------------- TAB 7: Live Terminal Console -----------------
with tab_term:
    st.markdown("### 💻 Live Remote Execution Terminal")
    st.caption(f"Real-time command dispatch and ANSI execution logs for Agent `{current_token}`.")

    if not cmd_data:
        st.info("No remote directives have been executed yet in this session. Trigger an action from any tab to view the streaming execution log.")
    else:
        cmd_id = cmd_data.get("command_id", "UNKNOWN")
        cmd_act = cmd_data.get("action", "UNKNOWN")
        cmd_stat = cmd_data.get("status", "PENDING")
        cmd_req = cmd_data.get("requested_at", "Unknown")
        cmd_comp = cmd_data.get("completed_at", "In Progress...")
        cmd_res = cmd_data.get("result", "")
        cmd_out = cmd_data.get("terminal_output", "")
        freed = cmd_data.get("freed_mb", 0)

        t_stat_color = "#00ff88" if cmd_stat == "COMPLETED" else "#ffaa00"
        st.markdown(f"""
        <div style="background: rgba(13, 19, 33, 0.9); padding: 14px 18px; border-radius: 8px; border: 1px solid rgba(0, 243, 255, 0.25); margin-bottom: 12px;">
            <strong>Command ID:</strong> <code>{cmd_id}</code> | 
            <strong>Action:</strong> <code>{cmd_act}</code> | 
            <strong>Status:</strong> <span style="color: {t_stat_color}; font-weight: 800;">{cmd_stat}</span><br>
            <span style="font-size: 0.8rem; color: #a0aec0;">Requested: {cmd_req} | Completed: {cmd_comp}</span><br>
            <span style="color: #00f3ff; font-weight: 600;">{cmd_res}</span>
            {f"<span style='color: #00ff88; margin-left: 10px;'>[Freed: {freed} MB]</span>" if freed else ""}
        </div>
        """, unsafe_allow_html=True)

        if cmd_out:
            st.markdown("#### 🖥️ Agent Terminal Output Stream")
            st.markdown(f'<div class="terminal-box">{cmd_out}</div>', unsafe_allow_html=True)
        elif cmd_stat == "PENDING":
            st.warning("⏳ Directive is in queue. The client agent will pick it up on its next cycle...")

    st.markdown("---")
    st.markdown("#### ⚠️ Zero-Footprint Self-Destruct Protocol")
    st.caption("Instructs the client agent to securely purge its temporary diagnostic logs, wipe local state, and terminate.")
    if st.button("💣 Execute Agent Self-Destruct", key="btn_self_destruct"):
        ok, msg = send_isolated_command(current_token, "SELF_DESTRUCT", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Self-Destruct directive dispatched!")
            st.warning("Self-Destruct directive staged. The client agent will wipe local state and terminate.")
            time.sleep(1)
            st.rerun()

# ----------------- Auto-Refresh Loop -----------------
time.sleep(refresh_rate)
st.rerun()
