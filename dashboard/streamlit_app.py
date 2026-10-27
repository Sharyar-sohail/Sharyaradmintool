"""
ApexSys Executive Command Dashboard (Streamlit Companion)
Provides executive fleet analytics, historical telemetry charts, issue drills,
and remote remediation triggers.
"""

import os
import time
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configure Streamlit page
st.set_page_config(
    page_title="ApexSys Executive IT Commander",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Cyberpunk / Dark Executive styling
st.markdown("""
<style>
    .reportview-container, .main, .block-container {
        background-color: #080b11;
        color: #e2e8f0;
    }
    .metric-card {
        background: rgba(13, 19, 33, 0.85);
        border: 1px solid rgba(0, 243, 255, 0.2);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00f3ff, #00ff88);
        color: #07090e;
        font-weight: 800;
        border: none;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("## ⚡ **APEXSYS COMMANDER**")
st.sidebar.markdown("*Autonomous Remote IT Doctor & Deep Remediation*")

# API Server Configuration
DEFAULT_API = os.getenv("APEX_API_URL", "http://127.0.0.1:8000/api")
API_BASE = st.sidebar.text_input("Commander API Endpoint", value=DEFAULT_API).rstrip("/")

# Compute default WebSocket URL from API endpoint
clean_base = API_BASE.replace("/api", "").rstrip("/")
if clean_base.startswith("https://"):
    DEFAULT_WS = clean_base.replace("https://", "wss://")
elif clean_base.startswith("http://"):
    DEFAULT_WS = clean_base.replace("http://", "ws://")
else:
    DEFAULT_WS = f"ws://{clean_base}"

refresh_rate = st.sidebar.slider("Auto-Refresh Rate (seconds)", 2, 10, 4)


def get_ps1_script_content(target_ws_url: str) -> str:
    """Loads ApexAgent.ps1 and injects the specified target WebSocket URL."""
    agent_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "ApexAgent.ps1")
    content = ""
    if os.path.exists(agent_path):
        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        try:
            r = requests.get(f"{API_BASE}/agent/download-ps1", timeout=3)
            if r.status_code == 200:
                content = r.text
        except Exception:
            pass

    if content and target_ws_url:
        content = content.replace('[string]$ServerUrl = "ws://127.0.0.1:8000"', f'[string]$ServerUrl = "{target_ws_url}"')
    return content


def render_agent_deployment_card(default_ws_url: str, expanded: bool = False):
    """Renders the downloadable PowerShell Agent banner with instructions."""
    with st.expander("📥 Connect New Client Machine (Download PowerShell Agent)", expanded=expanded):
        st.markdown("### 🚀 Client Agent Deployment")
        st.markdown(
            "Download this standalone, zero-dependency PowerShell script and run it as an **Administrator** on any Windows PC to establish a live, secure telemetry and remediation link back to this Commander."
        )

        dcol1, dcol2 = st.columns([2, 1])
        with dcol1:
            custom_ws = st.text_input(
                "Target Commander WebSocket URL:",
                value=default_ws_url,
                help="The WebSocket URL the agent will connect back to. Examples: ws://192.168.1.100:8000 or wss://commander.yourdomain.com",
            )
        with dcol2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            script_data = get_ps1_script_content(custom_ws)
            st.download_button(
                label="📥 Download Agent Script (ApexAgent.ps1)",
                data=script_data,
                file_name="ApexAgent.ps1",
                mime="application/x-powershell",
                use_container_width=True,
            )

        st.markdown("---")
        col_step1, col_step2, col_step3 = st.columns(3)
        with col_step1:
            st.markdown("**1. Download Script**")
            st.caption("Click the download button above to get the customized `ApexAgent.ps1`.")
        with col_step2:
            st.markdown("**2. Run as Administrator**")
            st.caption("Right-click `ApexAgent.ps1` > 'Run with PowerShell', or run in an elevated PowerShell terminal.")
        with col_step3:
            st.markdown("**3. Live Auto-Sync**")
            st.caption("Agent connects via WebSocket, executes Master Scan, and streams live telemetry to this dashboard.")

        st.markdown("**Or Execute Directly via PowerShell Admin One-Liner:**")
        one_liner = f'powershell.exe -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri \'{API_BASE}/agent/download-ps1?server_url={custom_ws}\' -OutFile ApexAgent.ps1; .\\ApexAgent.ps1"'
        st.code(one_liner, language="powershell")


def fetch_nodes():
    try:
        r = requests.get(f"{API_BASE}/nodes", timeout=3)
        if r.status_code == 200:
            return r.json().get("nodes", [])
    except Exception:
        pass
    return []


def fetch_node_detail(client_id):
    try:
        r = requests.get(f"{API_BASE}/nodes/{client_id}", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


nodes = fetch_nodes()

if not nodes:
    st.sidebar.warning("No client machines connected. Start an agent to begin.")
    selected_client_id = None
else:
    node_options = {f"{n.get('system_info', {}).get('hostname', n['client_id'])} ({n['client_id'][:8]})": n['client_id'] for n in nodes}
    selected_label = st.sidebar.selectbox("Select Target Machine", list(node_options.keys()))
    selected_client_id = node_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.markdown("### Fleet Quick Stats")
total_nodes = len(nodes)
online_nodes = sum(1 for n in nodes if n.get("status") == "ONLINE")
crit_issues = sum(n.get("issue_counts", {}).get("critical", 0) for n in nodes)

st.sidebar.metric("Total Endpoints", total_nodes)
st.sidebar.metric("Online Agents", online_nodes)
st.sidebar.metric("Total Critical Flaws", crit_issues)

# Main Dashboard View
if not selected_client_id:
    st.title("⚡ ApexSys Master Control Center")
    st.info("No active client machine connected yet. Deploy the PowerShell agent below to establish a live connection.")
    render_agent_deployment_card(DEFAULT_WS, expanded=True)
else:
    render_agent_deployment_card(DEFAULT_WS, expanded=False)
    node_data = fetch_node_detail(selected_client_id)
    if not node_data:
        st.error("Failed to fetch node details from server.")
        st.stop()

    sys_info = node_data.get("system_info", {})
    health_score = node_data.get("health_score", 100)
    cat_scores = node_data.get("category_scores", {})
    issues = node_data.get("issues", [])
    tele_history = node_data.get("telemetry_history", [])

    # Top Banner
    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
    with col1:
        st.subheader(f"🖥️ {sys_info.get('hostname', selected_client_id)}")
        admin_badge = "👑 Elevated Administrator" if sys_info.get("is_admin") else "⚠️ Standard User"
        st.caption(f"{sys_info.get('os_name')} ({sys_info.get('architecture')}) | {sys_info.get('ip_address')} | {admin_badge}")
    with col2:
        st.metric("CPU Model", sys_info.get("cpu_model", "Unknown")[:18] + "...")
    with col3:
        st.metric("RAM Total", f"{sys_info.get('total_ram_gb', 0)} GB")
    with col4:
        st.metric("Status", node_data.get("status", "ONLINE"))
    with col5:
        st.metric("Active Task", node_data.get("active_task") or "Idle")

    st.markdown("---")

    # Health Score Gauge & Categorical Radar
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown("### Holistic Vitality Score")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Health Score (0-100)", 'font': {'size': 18, 'color': "#ffffff"}},
            number={'font': {'size': 48, 'color': "#00ff88" if health_score >= 80 else "#ffaa00" if health_score >= 50 else "#ff3366"}},
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
        fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with right_col:
        st.markdown("### Categorical Health Breakdown")
        cats = list(cat_scores.keys())
        scores = list(cat_scores.values())

        fig_bar = px.bar(
            x=scores,
            y=cats,
            orientation='h',
            text=scores,
            labels={'x': 'Score (%)', 'y': 'Diagnostic Category'},
            color=scores,
            color_continuous_scale=["#ff3366", "#ffaa00", "#00ff88"],
            range_color=[0, 100],
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            height=260,
            margin=dict(l=20, r=20, t=10, b=20),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Remediation Action Deck
    st.markdown("### 🛠️ Remote Command Deck")
    bcol1, bcol2, bcol3 = st.columns([2, 1, 1])
    with bcol1:
        if st.button("⚡ ONE-CLICK AUTONOMOUS FIX ALL", use_container_width=True):
            r = requests.post(f"{API_BASE}/nodes/{selected_client_id}/fix-all")
            if r.status_code == 200:
                st.success("One-Click Autonomous Fix All dispatched!")
            else:
                st.error("Failed to trigger fix.")
    with bcol2:
        if st.button("🔍 Run Master Diagnostic Scan", use_container_width=True):
            r = requests.post(f"{API_BASE}/nodes/{selected_client_id}/scan")
            if r.status_code == 200:
                st.info("Master Scan initiated.")
    with bcol3:
        if st.button("💥 Secure Self-Destruct", use_container_width=True):
            r = requests.post(f"{API_BASE}/nodes/{selected_client_id}/self-destruct")
            if r.status_code == 200:
                st.warning("Self-Destruct payload verified & dispatched.")

    # Telemetry Line Chart
    if tele_history:
        st.markdown("### 📈 Real-Time Telemetry History")
        df_tele = pd.DataFrame(tele_history)
        if "timestamp" in df_tele.columns:
            df_tele["Time"] = pd.to_datetime(df_tele["timestamp"], unit='s')
            fig_tele = px.line(
                df_tele,
                x="Time",
                y=["cpu_percent", "ram_percent", "disk_percent"],
                labels={"value": "Utilization (%)", "variable": "Resource"},
                color_discrete_map={"cpu_percent": "#00f3ff", "ram_percent": "#00ff88", "disk_percent": "#ffaa00"},
            )
            fig_tele.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"),
                height=240,
                margin=dict(l=20, r=20, t=10, b=20),
            )
            st.plotly_chart(fig_tele, use_container_width=True)

    # Diagnosed Issues Board
    st.markdown(f"### 📋 Detected Diagnostic Issues ({len(issues)})")
    if not issues:
        st.success("No system flaws detected. All categories fully verified.")
    else:
        for iss in issues:
            sev = iss.get("severity", "INFO")
            color = "#ff3366" if sev == "CRITICAL" else "#ffaa00" if sev == "WARNING" else "#00f3ff"
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding: 8px 14px; background: rgba(16,24,39,0.5); margin-bottom: 8px; border-radius: 4px;">
                <strong style="color: #fff;">[{iss.get('category')}] {iss.get('title')}</strong> <span style="color: {color}; font-size: 0.8rem; font-weight: 700;">({sev})</span><br>
                <span style="color: #a0aec0; font-size: 0.85rem;">{iss.get('description')}</span>
            </div>
            """, unsafe_allow_html=True)
            if not iss.get("resolved", False):
                if st.button(f"Remediate: {iss.get('title')[:35]}...", key=iss.get("id")):
                    requests.post(
                        f"{API_BASE}/nodes/{selected_client_id}/remediate",
                        json={"action": iss.get("fix_id")},
                    )
                    st.info(f"Dispatched fix {iss.get('fix_id')}.")

    # Terminal Log Excerpt
    st.markdown("### 💻 Agent Execution Logs")
    term_logs = node_data.get("terminal_logs", [])
    log_text = "\n".join([f"[{l.get('ts')}] {l.get('text')}" for l in term_logs[-25:]])
    st.text_area("Live Terminal Stream", log_text if log_text else "No logs recorded yet.", height=180)

# Periodic loop trigger for live update
time.sleep(refresh_rate)
st.rerun()
