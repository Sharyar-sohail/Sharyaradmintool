"""
Sharyar Admin Tool - Autonomous AI Windows Updating, Repair & Multi-User Administration Suite
Strict Multi-User Session Isolation Architecture with GitHub-based zero-cost state syncing.
Each user/administrator links to an exclusive Agent Token. Telemetry is scoped exclusively
to clients/{AGENT_TOKEN}/status.json and commands.json with zero cross-tenant data mixing.
"""

import datetime
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

# Configure Streamlit page
st.set_page_config(
    page_title="Sharyar Admin Tool - Autonomous AI IT Commander",
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
    .ai-hero-card {
        background: linear-gradient(135deg, rgba(16, 28, 54, 0.95), rgba(7, 14, 28, 0.95));
        border: 1px solid #00f3ff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 0 25px rgba(0, 243, 255, 0.2);
        margin-bottom: 20px;
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
    .share-card {
        background: rgba(13, 19, 33, 0.9);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 10px;
        padding: 16px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

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
    st.markdown("## ⚡ **شریار ایڈمن ٹول (SHARYAR ADMIN TOOL)**")
    st.markdown("### 🤖 Autonomous AI Windows Updating, Repair & IT Commander Suite")
    st.info("سسٹم میں سخت ملٹی یوزر سیشن آئسولیشن نافذ ہے۔ اپنا یونیک ایجنٹ سیشن ٹوکن درج کریں تاکہ آپ کا کنٹرول سینٹر فعال ہو سکے:")

    col_gate1, col_gate2 = st.columns(2)

    with col_gate1:
        st.markdown("#### 🔑 موجودہ کلائنٹ مشین سے جڑیں (Connect Client Token)")
        st.markdown("اپنے کلائنٹ کمپیوٹر پر چلنے والے اسکرپٹ سے سیشن ٹوکن حاصل کر کے یہاں داخل کریں:")
        input_token = st.text_input("Session Token (ایجنٹ ٹوکن)", placeholder="مثلاً APEX-A1B2C3D4", key="login_token_input")
        if st.button("🚀 نجی سیشن کھولیں (Open Private Session)", use_container_width=True):
            if input_token.strip():
                clean_t = input_token.strip().upper()
                st.session_state["agent_token"] = clean_t
                st.query_params["token"] = clean_t
                st.rerun()
            else:
                st.error("براہ کرم ایک درست ٹوکن درج کریں۔")

        st.markdown("---")
        st.caption("فوری ٹیسٹنگ کے لیے ڈیمو مشین لوڈ کریں:")
        if st.button("🧪 ویریفائیڈ ڈیمو مشین کھولیں (APEX-DEMO01)", use_container_width=True):
            st.session_state["agent_token"] = "APEX-DEMO01"
            st.query_params["token"] = "APEX-DEMO01"
            st.rerun()

    with col_gate2:
        st.markdown("#### ⚡ نیا ٹوکن بنائیں اور ایجنٹ ڈاؤنلوڈ کریں (Deploy Agent)")
        st.markdown("کسی بھی نئے ونڈوز کمپیوٹر کو کنیکٹ کرنے کے لیے پہلے سے جڑا ہوا ایجنٹ اسکرپٹ ڈاؤنلوڈ کریں:")
        new_token = st.session_state["suggested_token"]
        st.code(new_token, language="text")

        prelinked_script = get_customized_agent_script(new_token, DEFAULT_OWNER, DEFAULT_REPO, DEFAULT_BRANCH)
        st.download_button(
            label=f"📥 ڈاؤنلوڈ شریار ایجنٹ اسکرپٹ ({new_token})",
            data=prelinked_script,
            file_name=f"SharyarAgent_{new_token}.ps1",
            mime="application/x-powershell",
            use_container_width=True,
        )

        if st.button(f"سیشن شروع کریں ({new_token})", use_container_width=True):
            st.session_state["agent_token"] = new_token
            st.query_params["token"] = new_token
            st.rerun()

    st.stop()


# ----------------- ACTIVE ISOLATED SESSION VIEW -----------------
st.sidebar.markdown("## ⚡ **شریار ایڈمن ٹول**")
st.sidebar.markdown(f"**منسلک مشین:** <span class='token-badge'>{current_token}</span>", unsafe_allow_html=True)

if st.sidebar.button("🔒 سیشن بند کریں / ٹوکن تبدیل کریں", use_container_width=True):
    del st.session_state["agent_token"]
    if "token" in st.query_params:
        del st.query_params["token"]
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ ریپوزٹری اور اجازت نامہ ترتیبات", expanded=False):
    repo_owner = st.text_input("GitHub Owner", value=DEFAULT_OWNER)
    repo_name = st.text_input("GitHub Repository", value=DEFAULT_REPO)
    branch = st.text_input("Branch", value=DEFAULT_BRANCH)
    github_token = st.text_input("Personal Access Token (اختیاری)", value=DEFAULT_TOKEN, type="password")

refresh_rate = st.sidebar.slider("آٹو ریفریش کا وقت (سیکنڈز)", min_value=5, max_value=60, value=15)
if st.sidebar.button("🔄 ابھی ٹیلی میٹری تازہ کریں", use_container_width=True):
    st.rerun()

# Fetch isolated telemetry
status_data, fetch_source = fetch_isolated_status(current_token, repo_owner, repo_name, branch, github_token)

# Shareable URL
share_url = f"?token={current_token}"
st.sidebar.caption(f"براہِ راست سیشن لنک: `{share_url}`")

# ----------------- Top Deployment & Script Card -----------------
with st.expander(f"📥 کلائنٹ پی سی انسٹالیشن اور ون لائنر اسکرپٹ [{current_token}]", expanded=(status_data is None)):
    st.markdown("### 🚀 شریار آئی ٹی ٹول ایجنٹ انسٹالیشن")
    st.markdown(
        f"یہ اسکرپٹ خصوصی طور پر ٹوکن `{current_token}` کے ساتھ منسلک ہے۔ "
        f"تمام ڈائیگنوسٹکس اور ریموٹ احکامات `clients/{current_token}/` پر گٹ ہب کے ذریعے خودکار سنک ہوں گے۔"
    )

    dcol1, dcol2 = st.columns([2, 1])
    with dcol1:
        agent_script_code = get_customized_agent_script(current_token, repo_owner, repo_name, branch)
        st.download_button(
            label=f"📥 ڈاؤنلوڈ شریار ایجنٹ ({current_token})",
            data=agent_script_code,
            file_name=f"SharyarAgent_{current_token}.ps1",
            mime="application/x-powershell",
            use_container_width=True,
        )
    with dcol2:
        st.markdown("**کلائنٹ پی سی پر رن کریں (Admin PowerShell):**")
        st.markdown(f"- سنگل اسکین: `.\\SharyarAgent.ps1 -AgentToken {current_token}`")
        st.markdown(f"- مسلسل نگرانی: `.\\SharyarAgent.ps1 -AgentToken {current_token} -Continuous 1`")

    st.markdown("---")
    st.markdown("**پاور شیل ایڈمن انسٹنٹ ون لائنر (بغیر کسی پیشگی ڈاؤنلوڈ کے براہ راست چلائیں):**")
    one_liner = (
        f'powershell.exe -ExecutionPolicy Bypass -Command '
        f'"Invoke-WebRequest -Uri \'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/agent/ApexAgent.ps1\' -OutFile SharyarAgent.ps1; '
        f'.\\SharyarAgent.ps1 -AgentToken {current_token}"'
    )
    st.code(one_liner, language="powershell")


# ----------------- Status Data Validation -----------------
if not status_data:
    st.warning(f"⏳ کلائنٹ ایجنٹ `{current_token}` کے پہلے اسکین کا انتظار کیا جا رہا ہے...")
    st.info(f"اپنے کمپیوٹر پر ایجنٹ چلائیں۔ اسکین مکمل ہوتے ہی آپ کا ڈیش بورڈ لائیو فعال ہو جائے گا۔")
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
age_text = "ابھی"
try:
    ts_str = status_data.get("timestamp")
    if ts_str:
        clean_ts = ts_str.replace("Z", "+00:00")
        sync_time = datetime.datetime.fromisoformat(clean_ts)
        now_time = datetime.datetime.now(datetime.timezone.utc)
        diff_sec = int((now_time - sync_time).total_seconds())
        if diff_sec < 60:
            age_text = f"{diff_sec}s پہلے"
        elif diff_sec < 3600:
            age_text = f"{diff_sec // 60}m پہلے"
        else:
            age_text = f"{diff_sec // 3600}h پہلے"
except Exception:
    pass

# Top Machine Banner
col_h1, col_h2 = st.columns([3, 2])
with col_h1:
    admin_pill = "👑 ایلیویٹڈ ایڈمنسٹریٹر" if sys_info.get("is_admin") else "⚠️ اسٹینڈرڈ یوزر"
    st.markdown(f"## 🖥️ **{sys_info.get('hostname', client_id)}**")
    st.caption(f"{sys_info.get('os_name')} (Build {sys_info.get('os_build')}, {sys_info.get('architecture')}) | IP: {sys_info.get('ip_address')} | {admin_pill}")

with col_h2:
    status_badge_html = (
        f"<span class='status-badge-online'>● آن لائن (سنک: {age_text})</span>"
        if agent_status == "ONLINE"
        else f"<span class='status-badge-offline'>■ بند / آف لائن ({last_synced})</span>"
    )
    st.markdown(f"""
    <div style="text-align: right; padding-top: 6px;">
        {status_badge_html}
        <span class="token-badge" style="margin-left: 8px;">ٹوکن: {current_token}</span><br>
        <span style="font-size: 0.75rem; color: #a0aec0;">شریار ایڈمن فیڈ: {fetch_source}</span>
    </div>
    """, unsafe_allow_html=True)

if agent_status == "OFFLINE":
    st.error(f"⚠️ کلائنٹ ایجنٹ آف لائن ہے: آخری سیشن وقت {last_synced} پر ختم ہوا۔ آخری محفوظ شدہ رپورٹ دکھائی جا رہی ہے۔")

# ----------------- 🤖 SHARYAR AI AUTONOMOUS UPDATER HERO CARD -----------------
st.markdown("""
<div class="ai-hero-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h3 style="color: #00f3ff; margin-bottom: 4px;">🤖 شریار AI آٹونومس اپ ڈیٹ اور سیلف ہیلنگ سسٹم</h3>
            <p style="color: #cbd5e0; margin: 0; font-size: 0.9rem;">
                ایک کلک میں خودکار اے آئی انجن ونڈوز ڈیفینڈر سگنیچرز اپ ڈیٹ کرے گا، تمام تھرڈ پارٹی سافٹ ویئرز اپ گریڈ کرے گا، 
                کرپٹ سسٹم فائلز (SFC/DISM) ٹھیک کرے گا، اور سارا کباڑ کیشے صاف کر کے انٹرنیٹ اسٹیک بحال کرے گا۔
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

ai_btn_col1, ai_btn_col2 = st.columns([3, 1])
with ai_btn_col1:
    if st.button("🚀 لائیو شریار AI سسٹم اپ ڈیٹ اور ہیلنگ چلائیں (Run AI Auto-Update & Heal)", key="btn_ai_smart_update", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "AI_SMART_UPDATE", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("شریار AI اپ ڈیٹ کمانڈ بھیج دی گئی!")
            st.success(f"✓ AI Autonomous Pipeline Queued: {msg}")
            time.sleep(1)
            st.rerun()
        else:
            st.error(msg)
with ai_btn_col2:
    if st.button("📤 شیئر ہیلتھ رپورٹ (Share)", key="btn_quick_share", use_container_width=True):
        st.toast("رپورٹ شیئر سیکشن پر جائیں")

st.markdown("---")

# Health Score Gauge & Categorical Breakdown
col_gauge, col_bars = st.columns([1, 2])

with col_gauge:
    st.markdown("### 📊 مجموعی سسٹم وائٹلٹی اسکور")
    gauge_color = "#00ff88" if health_score >= 80 else "#ffaa00" if health_score >= 50 else "#ff3366"

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=health_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Health Score", 'font': {'size': 18, 'color': "#ffffff"}},
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
    st.markdown("### 📈 کیٹیگری بریک ڈاؤن")
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
st.markdown("### ⚡ لائیو پی سی ٹیلی میٹری")
tcol1, tcol2, tcol3, tcol4 = st.columns(4)
with tcol1:
    st.metric("سی پی یو لوڈ (CPU)", f"{telemetry.get('cpu_percent', 0)}%", f"{telemetry.get('cpu_freq_mhz', 0)} MHz")
with tcol2:
    st.metric("ریم کا استعمال (RAM)", f"{telemetry.get('ram_percent', 0)}%", f"{telemetry.get('ram_used_gb', 0)} / {sys_info.get('total_ram_gb', 0)} GB")
with tcol3:
    st.metric("سسٹم ڈرائیو فل (C:)", f"{telemetry.get('disk_percent', 0)}% Fill")
with tcol4:
    st.metric("انٹرنیٹ پنگ لیٹنسی", f"{telemetry.get('net_latency_ms', 0)} ms")

# ----------------- 🧠 SHARYAR AI DOCTOR DIAGNOSTIC ADVISOR -----------------
st.markdown("### 🧠 شریار AI ڈاکٹر کی تجاویز (AI System Health Advisor)")
ai_advices = []
if health_score >= 90:
    ai_advices.append("🟢 **بہترین حالت**: تمام اہم ونڈوز سروسز اور سیکیورٹی سسٹمز بالکل ٹھیک کام کر رہے ہیں۔")
elif health_score >= 70:
    ai_advices.append("🟡 **توجہ درکار**: سسٹم میں کچھ ڈرائیورز یا فالتو کیشے موجود ہیں۔ تجویز ہے کہ 'AI Auto-Update' چلائیں۔")
else:
    ai_advices.append("🔴 **فوری ریپیئر درکار**: سسٹم میں سنگین مسائل یا کرپشن دیکھی گئی ہے۔ فوری طور پر ریپیئر چلائیں۔")

# Check Disk
if telemetry.get('disk_percent', 0) > 80:
    ai_advices.append(f"⚠️ **اسٹوریج دباؤ**: سی ڈرائیو {telemetry.get('disk_percent')}% پر ہے۔ تجویز ہے کہ فالتو کیشے فائلز صاف کریں۔")
# Check Antivirus
av_info = diag.get("antivirus", {})
if not av_info.get("realtime_protection", True):
    ai_advices.append("🚨 **سیکیورٹی الرٹ**: مائیکروسافٹ ڈیفینڈر کی ریل ٹائم پروٹیکشن بند ہے، اسے فوراً آن کریں۔")
if av_info.get("quick_scan_age_days", 0) > 3:
    ai_advices.append(f"🛡️ **اسکین الرٹ**: آخری وائرس اسکین {av_info.get('quick_scan_age_days')} دن پہلے ہوا تھا۔ نیا اسکین چلائیں۔")

for adv in ai_advices:
    st.markdown(f"- {adv}")

st.markdown("---")

# ----------------- Fetch latest command state -----------------
cmd_data, cmd_source = fetch_isolated_commands(current_token, repo_owner, repo_name, branch, github_token)

# ----------------- ENTERPRISE CONTROL TABS -----------------
tab_issues, tab_av, tab_pkg, tab_svc, tab_stor, tab_diag, tab_term, tab_share = st.tabs([
    "📋 ایکشن ایبل مسائل",
    "🛡️ اینٹی وائرس اور خطرات",
    "📦 سافٹ ویئر مینیجر (winget)",
    "⚙️ سروسز اور اسٹارٹ اپ",
    "🛠️ اسٹوریج اور نیٹ ورک",
    "🔍 ہارڈ ویئر و ڈرائیورز",
    "💻 لائیو ٹرمینل لاگ",
    "📤 شیئر اور رپورٹ سینٹر",
])

# ----------------- TAB 1: Actionable Issues -----------------
with tab_issues:
    st.markdown(f"### 📋 حل طلب مسائل ({len(issues)})")
    if not issues:
        st.success("✓ تمام سسٹمز بالکل درست ہیں: کوئی ہارڈ ویئر فالٹ، وائرس یا کرپشن نہیں ملی۔")
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
                    if st.button("⚡ خودکار مرمت", key=f"fix_btn_{idx}_{fix_id}", use_container_width=True):
                        ok, msg = send_isolated_command(current_token, fix_id, {}, repo_owner, repo_name, branch, github_token)
                        if ok:
                            st.toast(f"ریپیئر کمانڈ بھیج دی گئی: {fix_id}")
                            st.success(f"Dispatched {fix_id}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)

# ----------------- TAB 2: Antivirus & Threat Defense -----------------
with tab_av:
    st.markdown("### 🛡️ مائیکروسافٹ ڈیفینڈر اور وائرس تحفظ")
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
        rt_badge = "🟢 محفوظ / فعال (ACTIVE)" if av_realtime else "🔴 غیر فعال (DISABLED)"
        st.metric("ریل ٹائم تحفظ", rt_badge)
    with av_c2:
        st.metric("سگنیچر ورژن", av_sig, f"اپ ڈیٹ: {av_update}")
    with av_c3:
        scan_txt = f"{av_scan_age} دن پہلے" if av_scan_age >= 0 else "کبھی نہیں"
        st.metric("آخری کوئیک اسکین", scan_txt)

    st.markdown("#### ⚡ اینٹی وائرس ایکشن بٹنز")
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        if st.button("🛡️ فوری وائرس اسکین چلائیں (Quick Scan)", key="btn_av_quick", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_VIRUS_SCAN", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("کوئیک اسکین شروع ہو گیا!"); st.success(msg); time.sleep(1); st.rerun()
            else: st.error(msg)
    with btn_col2:
        if st.button("🔬 مکمل سسٹم اسکین چلائیں (Full Scan)", key="btn_av_full", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_FULL_VIRUS_SCAN", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("مکمل اسکین شروع ہو گیا!"); st.success(msg); time.sleep(1); st.rerun()
            else: st.error(msg)
    with btn_col3:
        if st.button("🔄 وائرس سگنیچرز اپ ڈیٹ کریں", key="btn_av_update", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "UPDATE_VIRUS_SIGNATURES", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("سگنیچرز اپ ڈیٹ شروع!"); st.success(msg); time.sleep(1); st.rerun()
            else: st.error(msg)

    st.markdown("---")
    st.markdown(f"#### 🚨 پکڑے گئے خطرات کی ہسٹری ({len(threats)} کل، {active_threats_count} ایکٹو)")
    if not threats:
        st.info("کمپیوٹر میں کوئی وائرس یا مالویئر خطرہ موجود نہیں ہے۔")
    else:
        df_th = pd.DataFrame(threats)
        st.dataframe(df_th, use_container_width=True)

# ----------------- TAB 3: Software & winget Packaging -----------------
with tab_pkg:
    st.markdown("### 📦 سافٹ ویئر اور پیکیج مینیجر (winget)")
    soft_data = diag.get("software", {})
    winget_ok = soft_data.get("winget_available", False)
    installed_apps = soft_data.get("installed_apps", [])
    total_apps_count = soft_data.get("installed_count", len(installed_apps))

    if not winget_ok:
        st.warning("⚠️ کلائنٹ مشین پر ونڈوز پیکیج مینیجر (`winget.exe`) موجود نہیں ملا۔")

    st.markdown("#### ⚡ ضروری آئی ٹی ٹولز کی فوری انسٹالیشن (1-Click Installers)")
    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        if st.button("📥 Install 7-Zip", key="pkg_7zip", use_container_width=True):
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
            if ok: st.toast("تمام سافٹ ویئرز اپ گریڈ ہو رہے ہیں..."); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown("#### 🎯 کسٹم سافٹ ویئر انسٹالیشن اور اَن انسٹالیشن")
    c_pkg1, c_pkg2 = st.columns(2)
    with c_pkg1:
        st.markdown("**پیکیج ID سے انسٹال کریں:**")
        custom_install_id = st.text_input("Package ID", placeholder="مثلاً Mozilla.Firefox, Zoom.Zoom", key="in_pkg_install")
        if st.button("انسٹال کریں (Install)", key="btn_custom_install"):
            if custom_install_id.strip():
                ok, msg = send_isolated_command(current_token, "WINGET_INSTALL", {"package_id": custom_install_id.strip()}, repo_owner, repo_name, branch, github_token)
                if ok: st.toast(f"Installing {custom_install_id}..."); st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)
    with c_pkg2:
        st.markdown("**پیکیج ID سے ڈیلیٹ کریں:**")
        custom_uninstall_id = st.text_input("Package ID to Remove", placeholder="مثلاً 7zip.7zip", key="in_pkg_uninstall")
        if st.button("اَن انسٹال کریں (Uninstall)", key="btn_custom_uninstall"):
            if custom_uninstall_id.strip():
                ok, msg = send_isolated_command(current_token, "WINGET_UNINSTALL", {"package_id": custom_uninstall_id.strip()}, repo_owner, repo_name, branch, github_token)
                if ok: st.toast(f"Uninstalling {custom_uninstall_id}..."); st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

    st.markdown("---")
    st.markdown(f"#### 📋 انسٹال شدہ سافٹ ویئرز کی لسٹ ({total_apps_count} ملے)")
    if installed_apps:
        df_apps = pd.DataFrame(installed_apps)
        st.dataframe(df_apps, use_container_width=True)

# ----------------- TAB 4: Services & Startup Control -----------------
with tab_svc:
    st.markdown("### ⚙️ ونڈوز سروسز اور اسٹارٹ اپ کنٹرول")
    svc_data = diag.get("services", {})
    crit_services = svc_data.get("critical_services", [])
    startup_items = svc_data.get("startup_items", [])

    st.markdown("#### 🔄 اہم ونڈوز سروسز کی لائیو مانیٹرنگ")
    if crit_services:
        df_svc = pd.DataFrame(crit_services)
        st.dataframe(df_svc[["name", "display_name", "status", "start_type"]], use_container_width=True)

    st.markdown("#### ⚡ سروس ریموٹ کنٹرولر")
    scol1, scol2, scol3 = st.columns([2, 1, 1])
    with scol1:
        selected_svc = st.selectbox(
            "سروس منتخب کریں",
            options=[s.get("name") for s in crit_services] if crit_services else ["wuauserv", "Spooler", "BITS", "WinDefend", "Dhcp", "Dnscache"]
        )
    with scol2:
        if st.button("🔄 ری اسٹارٹ کریں", key="btn_restart_svc", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "SERVICE_RESTART", {"service_name": selected_svc}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast(f"{selected_svc} ری اسٹارٹ ہو رہی ہے..."); st.success(msg); time.sleep(1); st.rerun()
    with scol3:
        if st.button("▶️ شروع / ⏹️ بند کریں", key="btn_toggle_svc", use_container_width=True):
            curr_s = next((s.get("status") for s in crit_services if s.get("name") == selected_svc), "Running")
            target_act = "SERVICE_STOP" if curr_s == "Running" else "SERVICE_START"
            ok, msg = send_isolated_command(current_token, target_act, {"service_name": selected_svc}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast(f"{target_act} بھیج دیا گیا..."); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown(f"#### 🚀 کمپیوٹر اسٹارٹ اپ پروگرامز ({len(startup_items)} آئٹمز)")
    if startup_items:
        df_start = pd.DataFrame(startup_items)
        st.dataframe(df_start[["name", "command", "location", "user"]], use_container_width=True)

# ----------------- TAB 5: Storage & Network Optimization -----------------
with tab_stor:
    st.markdown("### 🛠️ اسٹوریج اور ڈیپ کیشے کلین اپ")
    stor_data = diag.get("storage", {})
    total_junk = stor_data.get("temp_junk_mb", 0)
    junk_bd = stor_data.get("junk_breakdown", {})

    st.metric("بیکار کیشے اور کباڑ فائلز", f"{total_junk} MB", f"{round(total_junk/1024, 2)} GB")

    jcol1, jcol2, jcol3, jcol4, jcol5 = st.columns(5)
    with jcol1: st.metric("یوزر ٹیمپ", f"{junk_bd.get('user_temp_mb', 0)} MB")
    with jcol2: st.metric("ونڈوز ٹیمپ", f"{junk_bd.get('win_temp_mb', 0)} MB")
    with jcol3: st.metric("پریفچ", f"{junk_bd.get('prefetch_mb', 0)} MB")
    with jcol4: st.metric("اپ ڈیٹ کیشے", f"{junk_bd.get('softwaredist_mb', 0)} MB")
    with jcol5: st.metric("کریش ڈمپس", f"{junk_bd.get('wer_dumps_mb', 0)} MB")

    st.markdown("#### ⚡ کلین اپ ایکشن بٹنز")
    cl_col1, cl_col2, cl_col3, cl_col4 = st.columns(4)
    with cl_col1:
        if st.button("🧹 تمام کباڑ صاف کریں (Clean All)", key="btn_cl_all", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_ALL_JUNK", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("مکمل کلین اپ کمانڈ بھیج دی گئی!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col2:
        if st.button("🗂️ ٹیمپ فائلز خالی کریں", key="btn_cl_temp", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_TEMP", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("ٹیمپ کلین اپ شروع!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col3:
        if st.button("⚡ پریفچ صاف کریں", key="btn_cl_prefetch", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_PREFETCH", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("پریفچ کلین شروع!"); st.success(msg); time.sleep(1); st.rerun()
    with cl_col4:
        if st.button("📦 ونڈوز اپ ڈیٹ کیشے صاف کریں", key="btn_cl_softwaredist", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_SOFTWAREDIST", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("اپ ڈیٹ کیشے صفائی شروع!"); st.success(msg); time.sleep(1); st.rerun()

    st.markdown("---")
    st.markdown("### 🌐 انٹرنیٹ اور نیٹ ورک ٹربل شوٹنگ")
    net_data = diag.get("network", {})
    st.markdown(f"- **پرائمری آئی پی**: `{net_data.get('primary_ip', 'Unknown')}`")
    st.markdown(f"- **ڈی این ایس لیٹنسی**: `{net_data.get('dns_latency_ms', 0)} ms`")

    if st.button("🌐 فلش DNS اور TCP/IP نیٹ ورک ری سیٹ کریں", key="btn_reset_network", use_container_width=True):
        ok, msg = send_isolated_command(current_token, "RESET_NETWORK", {}, repo_owner, repo_name, branch, github_token)
        if ok: st.toast("نیٹ ورک ری سیٹ کمانڈ بھیج دی گئی!"); st.success(msg); time.sleep(1); st.rerun()

    adapters = net_data.get("adapters", [])
    if adapters:
        st.markdown("#### نیٹ ورک کارڈز (Adapters)")
        st.dataframe(pd.DataFrame(adapters)[["name", "status", "link_speed", "mac", "description"]], use_container_width=True)

# ----------------- TAB 6: Deep Audits (Hardware & OS) -----------------
with tab_diag:
    st.markdown("### 🔍 ہارڈ ویئر SMART اسٹیٹس اور ونڈوز انٹیگریٹی")
    hw_data = diag.get("hardware", {})
    os_data = diag.get("os_integrity", {})

    st.markdown(f"**پروسیسر**: `{sys_info.get('cpu_model')}` ({sys_info.get('cpu_cores')} Cores) | Clock: `{hw_data.get('cpu_curr_mhz')} MHz`")

    drives = hw_data.get("smart_drives", [])
    if drives:
        st.markdown("#### فزیکل ہارڈ ڈرائیوز / SSDs (SMART Status)")
        st.dataframe(pd.DataFrame(drives)[["device_id", "model", "media_type", "size_gb", "health_status", "operational_status", "bad_sectors"]], use_container_width=True)

    failing_devs = hw_data.get("failing_devices", [])
    if failing_devs:
        st.markdown("#### خراب یا مسنگ ہارڈ ویئر ڈرائیورز (Yellow-Bangs)")
        st.dataframe(pd.DataFrame(failing_devs)[["name", "code", "status", "error_desc"]], use_container_width=True)
    else:
        st.info("ڈیوائس مینیجر میں کوئی خراب ڈرائیور موجود نہیں ہے۔")

    st.markdown("#### ونڈوز کمپوننٹ اسٹور اور سسٹم فائلز")
    st.markdown(f"- **DISM Component Store**: `{os_data.get('dism_status')}`")
    st.markdown(f"- **SFC کرپٹ فائلز**: `{'کرپٹ فائلز کا پتا چلا' if os_data.get('sfc_corrupted') else 'تمام سسٹم فائلز بالکل درست ہیں'}`")
    st.markdown(f"- **CBS Servicing لاگ ایررز**: `{os_data.get('cbs_error_count', 0)} ایررز`")

    st.markdown("---")
    st.markdown("#### ⚡ انٹیگریٹی ریپیئر بٹنز")
    os_b1, os_b2, os_b3 = st.columns(3)
    with os_b1:
        if st.button("🛠️ SFC سسٹم فائل ریپیئر چلائیں", key="btn_sfc_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_SFC_REPAIR", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("SFC Repair شروع ہو گیا!"); st.success(msg); time.sleep(1); st.rerun()
    with os_b2:
        if st.button("🏥 DISM RestoreHealth چلائیں", key="btn_dism_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "RUN_DISM_RESTORE", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("DISM RestoreHealth شروع ہو گیا!"); st.success(msg); time.sleep(1); st.rerun()
    with os_b3:
        if st.button("🧹 کمپوننٹ اسٹور صاف کریں", key="btn_clean_comp_tab", use_container_width=True):
            ok, msg = send_isolated_command(current_token, "CLEAN_COMPONENT_STORE", {}, repo_owner, repo_name, branch, github_token)
            if ok: st.toast("Component cleanup شروع ہو گیا!"); st.success(msg); time.sleep(1); st.rerun()

# ----------------- TAB 7: Live Terminal Console -----------------
with tab_term:
    st.markdown("### 💻 لائیو ریموٹ ایگزیکیوشن ٹرمینل لاگ")
    st.caption(f"کلائنٹ پی سی `{current_token}` کے اصل ٹرمینل کا لائیو آؤٹ پٹ:")

    if not cmd_data:
        st.info("اس سیشن میں ابھی تک کوئی ریموٹ کمانڈ نہیں چلائی گئی۔ کسی بھی ٹیب سے بٹن دبا کر لائیو لاگ چیک کریں۔")
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
            <strong>کمانڈ ID:</strong> <code>{cmd_id}</code> | 
            <strong>ایکشن:</strong> <code>{cmd_act}</code> | 
            <strong>حالت:</strong> <span style="color: {t_stat_color}; font-weight: 800;">{cmd_stat}</span><br>
            <span style="font-size: 0.8rem; color: #a0aec0;">طلب کردہ وقت: {cmd_req} | مکمل وقت: {cmd_comp}</span><br>
            <span style="color: #00f3ff; font-weight: 600;">{cmd_res}</span>
            {f"<span style='color: #00ff88; margin-left: 10px;'>[خالی شدہ جگہ: {freed} MB]</span>" if freed else ""}
        </div>
        """, unsafe_allow_html=True)

        if cmd_out:
            st.markdown("#### 🖥️ لائیو ایجنٹ آؤٹ پٹ اسٹریم")
            st.markdown(f'<div class="terminal-box">{cmd_out}</div>', unsafe_allow_html=True)
        elif cmd_stat == "PENDING":
            st.warning("⏳ کمانڈ کیو میں ہے۔ کلائنٹ ایجنٹ اگلے چند سیکنڈ میں اسے پکڑ کر چلائے گا...")

    st.markdown("---")
    st.markdown("#### ⚠️ زیرو فوٹ پرنٹ سیلف ڈسٹرکٹ پروٹوکول (Zero-Footprint Self-Destruct)")
    st.caption("کلائنٹ پی سی سے ایجنٹ کی تمام عارضی فائلز، ٹوکنز اور لاگز کو مٹا کر سیشن بند کر دے گا۔")
    if st.button("💣 ایجنٹ سیلف ڈسٹرکٹ چلائیں (Execute Self-Destruct)", key="btn_self_destruct"):
        ok, msg = send_isolated_command(current_token, "SELF_DESTRUCT", {}, repo_owner, repo_name, branch, github_token)
        if ok:
            st.toast("Self-Destruct directive dispatched!")
            st.warning("سیلف ڈسٹرکٹ کمانڈ بھیج دی گئی۔ ایجنٹ کلین اپ کر کے بند ہو جائے گا۔")
            time.sleep(1)
            st.rerun()

# ----------------- TAB 8: Share & Report Center (شیئر اور رپورٹ سینٹر) -----------------
with tab_share:
    st.markdown("### 📤 شیئر اور ایگزیکٹو ہیلتھ رپورٹ سینٹر (Share & Report Center)")
    st.markdown(
        "یہاں سے آپ اس پی سی کی مکمل ہیلتھ سمری کلائنٹس، مینیجرز یا واٹس ایپ پر شیئر کر سکتے ہیں اور مکمل تفصیلی رپورٹ ڈاؤنلوڈ کر سکتے ہیں۔"
    )

    # 1. Direct Session Link
    st.markdown("#### 🔗 براہِ راست سیشن شیئرنگ لنک")
    full_share_url = f"?token={current_token}"
    st.code(full_share_url, language="text")
    st.caption("یہ لنک کسی بھی براؤزر میں کھول کر اس پی سی کا ڈیش بورڈ دیکھا جا سکتا ہے۔")

    # 2. Formatted WhatsApp / Email Summary
    st.markdown("#### 📱 واٹس ایپ اور ای میل کے لیے ریڈی میڈ فارمیٹڈ سمری")
    whatsapp_summary = f"""🖥️ شریار آئی ٹی ٹول - سسٹم ہیلتھ اور اے آئی اپ ڈیٹ رپورٹ
━━━━━━━━━━━━━━━━━━━━━━━━━━
مشین کا نام : {sys_info.get('hostname', client_id)}
سیشن ٹوکن   : {current_token}
حالت        : {agent_status} (ہیلتھ اسکور: {health_score}%)
آپریٹنگ سسٹم: {sys_info.get('os_name')} ({sys_info.get('architecture')})
پروسیسر     : {sys_info.get('cpu_model')} (لوڈ: {telemetry.get('cpu_percent', 0)}%)
ریم میموری  : {telemetry.get('ram_used_gb', 0)} GB / {sys_info.get('total_ram_gb', 0)} GB ({telemetry.get('ram_percent', 0)}%)
سسٹم ڈرائیو : C: ڈرائیو {telemetry.get('disk_percent', 0)}% بھری ہوئی ہے
اینٹی وائرس : Microsoft Defender ({'فعال / محفوظ' if diag.get('antivirus', {}).get('realtime_protection') else 'غیر فعال'})
فالتو کیشے  : {diag.get('storage', {}).get('temp_junk_mb', 0)} MB کباڑ فائلز
مسائل       : {len(issues)} ایکشن ایبل ایشوز
━━━━━━━━━━━━━━━━━━━━━━━━━━
مینیجڈ بائی : شریار ایڈمن ٹول (Sharyar Admin Tool - AI Updating Suite)
لائیو ڈیش بورڈ: https://sharyaradmintool.streamlit.app/?token={current_token}"""

    st.text_area("کاپی کرنے کے لیے ٹیکسٹ (Copy & Share):", value=whatsapp_summary, height=220)

    # 3. Downloadable Markdown Executive Report
    st.markdown("#### 📥 مکمل تفصیلی پی ڈی ایف / مارک ڈاؤن آڈٹ رپورٹ ڈاؤنلوڈ کریں")
    report_md = f"""# ⚡ SHARYAR ADMIN TOOL - EXECUTIVE HEALTH & AUDIT REPORT
**Target Workstation**: `{sys_info.get('hostname', client_id)}`  
**Session Token**: `{current_token}`  
**Audit Timestamp**: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  
**Overall Vitality Score**: `{health_score}%`  

---

## 1. System Specifications
- **Operating System**: {sys_info.get('os_name')} (Build {sys_info.get('os_build')})
- **Architecture**: {sys_info.get('architecture')}
- **Processor**: {sys_info.get('cpu_model')} ({sys_info.get('cpu_cores')} Logical Cores)
- **Physical Memory**: {sys_info.get('total_ram_gb')} GB RAM
- **Primary IP Address**: {sys_info.get('ip_address')}
- **Elevation Privileges**: {'Administrator (Elevated)' if sys_info.get('is_admin') else 'Standard User'}

---

## 2. Real-Time Telemetry Snapshot
- **CPU Load**: {telemetry.get('cpu_percent')}% ({telemetry.get('cpu_freq_mhz')} MHz)
- **RAM Utilization**: {telemetry.get('ram_percent')}% ({telemetry.get('ram_used_gb')} / {sys_info.get('total_ram_gb')} GB)
- **Primary Storage (C:)**: {telemetry.get('disk_percent')}% fill
- **Gateway/DNS Latency**: {telemetry.get('net_latency_ms')} ms

---

## 3. Microsoft Defender & Threat Telemetry
- **Real-Time Protection**: {'ACTIVE / SECURED' if diag.get('antivirus', {}).get('realtime_protection') else 'DISABLED / VULNERABLE'}
- **Antivirus Definition Version**: {diag.get('antivirus', {}).get('signature_version')}
- **Last Definition Update**: {diag.get('antivirus', {}).get('last_signature_update')}
- **Active Threats Detected**: {diag.get('antivirus', {}).get('active_threats_count', 0)}

---

## 4. Operating System Integrity
- **DISM Component Store**: {diag.get('os_integrity', {}).get('dism_status')}
- **SFC System Binaries**: {'Corrupted files flagged' if diag.get('os_integrity', {}).get('sfc_corrupted') else 'Clean / Intact'}
- **CBS Log Servicing Errors**: {diag.get('os_integrity', {}).get('cbs_error_count', 0)}

---

## 5. Storage Bloat Breakdown
- **User Temp (%TEMP%)**: {diag.get('storage', {}).get('junk_breakdown', {}).get('user_temp_mb', 0)} MB
- **Windows Temp**: {diag.get('storage', {}).get('junk_breakdown', {}).get('win_temp_mb', 0)} MB
- **Prefetch Cache**: {diag.get('storage', {}).get('junk_breakdown', {}).get('prefetch_mb', 0)} MB
- **SoftwareDistribution (Updates)**: {diag.get('storage', {}).get('junk_breakdown', {}).get('softwaredist_mb', 0)} MB
- **Total Recoverable Space**: {diag.get('storage', {}).get('temp_junk_mb', 0)} MB

---

## 6. Actionable Diagnostic Issues
{chr(10).join([f"- **[{i.get('category')}] {i.get('title')}** ({i.get('severity')}): {i.get('description')} (Fix Directive: `{i.get('fix_id')}`)" for i in issues]) if issues else "Zero hardware faults, malware, or component corruption detected."}

---
*Report Generated autonomously by Sharyar Admin Tool - Autonomous AI Updating & Repair Suite.*
"""

    down_col1, down_col2 = st.columns(2)
    with down_col1:
        st.download_button(
            label="📥 ڈاؤنلوڈ مکمل آڈٹ رپورٹ (Markdown)",
            data=report_md,
            file_name=f"SharyarAuditReport_{sys_info.get('hostname', client_id)}_{current_token}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with down_col2:
        st.download_button(
            label="📥 ڈاؤنلوڈ را ڈیٹا (JSON Telemetry)",
            data=json.dumps(status_data, indent=2),
            file_name=f"SharyarTelemetry_{current_token}.json",
            mime="application/json",
            use_container_width=True,
        )

# ----------------- Auto-Refresh Loop -----------------
time.sleep(refresh_rate)
st.rerun()
