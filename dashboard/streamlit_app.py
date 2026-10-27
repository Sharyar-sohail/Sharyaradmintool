"""
ApexSys Executive Command Dashboard - Multi-User Session Isolation Architecture
Each user/administrator links to an exclusive Agent Token. Telemetry is scoped
to clients/{AGENT_TOKEN}/status.json with zero cross-tenant data mixing.
"""

import datetime
import json
import os
import random
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
</style>
""", unsafe_allow_html=True)

# ----------------- Configuration & Parameters -----------------
from dashboard.fetcher import (
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
# Check URL query params for ?token=
query_token = st.query_params.get("token")
if query_token and "agent_token" not in st.session_state:
    st.session_state["agent_token"] = str(query_token).strip().upper()

# Generate temporary suggestion token if not in session
if "suggested_token" not in st.session_state:
    rand_hex = "".join(random.choices("0123456789ABCDEF", k=8))
    st.session_state["suggested_token"] = f"APEX-{rand_hex}"


# ----------------- SESSION GATEWAY SCREEN -----------------
current_token = st.session_state.get("agent_token", "").strip().upper()

if not current_token:
    st.markdown("## ⚡ **APEXSYS COMMANDER**")
    st.markdown("### 🔒 Secure Multi-User Session Gateway")
    st.info("ApexSys enforces strict session isolation. Please authenticate with your unique Agent Token to access your private machine telemetry.")

    col_gate1, col_gate2 = st.columns(2)

    with col_gate1:
        st.markdown("#### 🔑 Connect Existing Agent Token")
        st.markdown("Enter the session token displayed on your client PC terminal or saved from a prior run:")
        input_token = st.text_input("Agent Token", placeholder="e.g. APEX-A1B2C3D4", key="login_token_input")
        if st.button("🚀 Connect Private Session", use_container_width=True):
            if input_token.strip():
                clean_t = input_token.strip().upper()
                st.session_state["agent_token"] = clean_t
                st.query_params["token"] = clean_t
                st.rerun()
            else:
                st.error("Please enter a valid token.")

        st.markdown("---")
        st.caption("Quick Demo Test: Enter `APEX-DEMO01` to view an active verified diagnostic report.")

    with col_gate2:
        st.markdown("#### ⚡ Generate New Token & Deploy Agent")
        st.markdown("Deploy a new client machine with a dynamically generated, pre-linked session token:")
        new_token = st.session_state["suggested_token"]
        st.code(new_token, language="text")

        prelinked_script = get_customized_agent_script(new_token, DEFAULT_OWNER, DEFAULT_REPO, DEFAULT_BRANCH)
        st.download_button(
            label=f"📥 Download Pre-Linked Agent ({new_token})",
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
st.sidebar.markdown(f"**Session:** <span class='token-badge'>{current_token}</span>", unsafe_allow_html=True)

if st.sidebar.button("🔒 Disconnect / Switch Token", use_container_width=True):
    del st.session_state["agent_token"]
    if "token" in st.query_params:
        del st.query_params["token"]
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Repository Settings", expanded=False):
    repo_owner = st.text_input("GitHub Owner", value=DEFAULT_OWNER)
    repo_name = st.text_input("GitHub Repository", value=DEFAULT_REPO)
    branch = st.text_input("Branch", value=DEFAULT_BRANCH)
    github_token = st.text_input("Personal Access Token (Optional)", value=DEFAULT_TOKEN, type="password")

refresh_rate = st.sidebar.slider("Auto-Refresh Rate (seconds)", min_value=5, max_value=60, value=15)
manual_refresh = st.sidebar.button("🔄 Refresh Telemetry Now", use_container_width=True)

# Fetch isolated telemetry
status_data, fetch_source = fetch_isolated_status(current_token, repo_owner, repo_name, branch, github_token)

# Direct Share Link
share_url = f"?token={current_token}"
st.sidebar.caption(f"Direct Session Link: `{share_url}`")

# ----------------- Top Deployment & Script Card -----------------
with st.expander(f"📥 PowerShell Agent Deployment for Token [{current_token}]", expanded=(status_data is None)):
    st.markdown("### 🚀 Client Agent Deployment")
    st.markdown(
        f"This agent script is **pre-bound specifically to Token `{current_token}`**. "
        f"All diagnostic metrics will be saved exclusively to `clients/{current_token}/status.json` on GitHub."
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
        st.markdown(f"- `.\\ApexAgent.ps1 -AgentToken {current_token}`")
        st.markdown(f"- Continuous: `.\\ApexAgent.ps1 -AgentToken {current_token} -Continuous 1`")

    st.markdown("---")
    st.markdown("**PowerShell Admin Instant One-Liner (Zero-Install):**")
    one_liner = (
        f'powershell.exe -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest -Uri \'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/agent/ApexAgent.ps1\' -OutFile ApexAgent.ps1; '
        f'.\\ApexAgent.ps1 -AgentToken {current_token}"'
    )
    st.code(one_liner, language="powershell")


# ----------------- Status Data Validation -----------------
if not status_data:
    st.warning(f"⏳ Waiting for Agent `{current_token}` to publish its initial diagnostic scan...")
    st.info(f"Run `ApexAgent.ps1 -AgentToken {current_token}` on your client PC. As soon as the scan completes, your private dashboard will activate automatically.")
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
    st.caption(f"{sys_info.get('os_name')} ({sys_info.get('architecture')}) | IP: {sys_info.get('ip_address')} | {admin_pill}")

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

# Offline Banner Alert
if agent_status == "OFFLINE":
    st.error(f"⚠️ AGENT TERMINATED: Client process cleanly exited at {last_synced}. Showing last recorded diagnostic state.")

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
st.markdown("### 📈 Real-Time Telemetry Snapshot")
tcol1, tcol2, tcol3, tcol4 = st.columns(4)
with tcol1:
    st.metric("CPU Utilization", f"{telemetry.get('cpu_percent', 0)}%", f"{telemetry.get('cpu_freq_mhz', 0)} MHz")
with tcol2:
    st.metric("RAM Utilization", f"{telemetry.get('ram_percent', 0)}%", f"{telemetry.get('ram_used_gb', 0)} / {sys_info.get('total_ram_gb', 0)} GB")
with tcol3:
    st.metric("System Disk (C:)", f"{telemetry.get('disk_percent', 0)}% Fill")
with tcol4:
    st.metric("Gateway Latency", f"{telemetry.get('net_latency_ms', 0)} ms")

# ----------------- Remote Maintenance & Optimization Command Hub -----------------
st.markdown("---")
st.markdown("### 🛠️ **Autonomous Remote Maintenance & Storage Optimization**")
st.markdown(
    f"Trigger targeted cleanup and remediation directives directly on client `<span class='token-badge'>{current_token}</span>`. "
    f"Commands are staged to `clients/{current_token}/commands.json` via GitHub state synchronization.",
    unsafe_allow_html=True,
)

# Fetch latest command queue status
cmd_data, cmd_source = fetch_isolated_commands(current_token, repo_owner, repo_name, branch, github_token)

# Show last command status banner if available
if cmd_data:
    cmd_status = cmd_data.get("status", "UNKNOWN")
    cmd_action = cmd_data.get("action", "")
    cmd_req_time = cmd_data.get("requested_at", "")
    cmd_comp_time = cmd_data.get("completed_at", "")
    cmd_result = cmd_data.get("result", "")
    freed_mb = cmd_data.get("freed_mb", 0)

    if cmd_status == "PENDING":
        st.warning(f"⏳ **Directive in Queue**: `{cmd_action}` (Queued at {cmd_req_time}). Waiting for agent execution cycle...")
    elif cmd_status == "COMPLETED":
        freed_txt = f" — Freed **{freed_mb} MB**" if freed_mb else ""
        st.success(f"✓ **Last Directive Executed**: `{cmd_action}` at {cmd_comp_time}{freed_txt}. Result: {cmd_result}")

# Action Buttons Grid
col_act1, col_act2, col_act3 = st.columns(3)

with col_act1:
    st.markdown("#### 🧹 Deep Junk Purge")
    st.caption("Safely purge User Temp, Windows Temp, Prefetch, and obsolete SoftwareDistribution cache.")
    if st.button("🚀 Clean All Deep Junk", key="btn_clean_all", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "CLEAN_ALL_JUNK", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast(f"Directive CLEAN_ALL_JUNK queued for {current_token}!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("---")
    st.markdown("#### ⚡ Prefetch Cache")
    st.caption("Remove stale prefetch hash files to resolve application launch conflicts.")
    if st.button("Purge Prefetch Files", key="btn_clean_prefetch", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "CLEAN_PREFETCH", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Directive CLEAN_PREFETCH queued!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

with col_act2:
    st.markdown("#### 🗂️ Temporary Files")
    st.caption("Clean `%TEMP%` and `C:\\Windows\\Temp` without stopping system services.")
    if st.button("Purge Temporary Files", key="btn_clean_temp", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "CLEAN_TEMP", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Directive CLEAN_TEMP queued!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("---")
    st.markdown("#### 🌐 Network Stack & DNS")
    st.caption("Flush Windows DNS resolver cache and reset Winsock catalog sockets.")
    if st.button("Reset Network Stack", key="btn_reset_net", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "RESET_NETWORK", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Directive RESET_NETWORK queued!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

with col_act3:
    st.markdown("#### 📦 Windows Update Cache")
    st.caption("Stop wuauserv, purge `SoftwareDistribution\\Download`, restart servicing.")
    if st.button("Purge Update Cache", key="btn_clean_softwaredist", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "CLEAN_SOFTWAREDIST", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Directive CLEAN_SOFTWAREDIST queued!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

    st.markdown("---")
    st.markdown("#### 🔄 Force Diagnostic Rescan")
    st.caption("Force agent to immediately run full DISM, hardware, and event audit.")
    if st.button("Force Immediate Rescan", key="btn_force_rescan", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "FORCE_RESCAN", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Directive FORCE_RESCAN queued!")
            st.success(msg)
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)

st.markdown("---")

# Detected Issues Triage
st.markdown(f"### 📋 Actionable Diagnostic Issues ({len(issues)})")
if not issues:
    st.success("✓ ALL SYSTEMS VERIFIED: Zero hardware faults, component store damage, or system errors detected.")
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
                if st.button("⚡ Fix Issue", key=f"fix_btn_{idx}_{fix_id}", use_container_width=True):
                    ok, msg = send_isolated_command(current_token, fix_id, {}, repo_owner, repo_name, branch, github_token)
                    if ok:
                        st.toast(f"Remediation directive {fix_id} dispatched!")
                        st.success(f"Dispatched {fix_id}")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)

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
