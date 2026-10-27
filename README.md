# Sharyar Admin Tool: Autonomous AI Remote IT Commander & Deep Remediation Suite
### *The Ultimate AI-Powered Enterprise Windows Updating, Repair & Self-Healing Platform*

---

## ⚡ Overview
**Sharyar Admin Tool** (also known as **Sharyar IT Tool** / **شریار ایڈمن ٹول**) is an enterprise-grade autonomous AI remote IT administration platform pairing a real-time web command dashboard with zero-dependency PowerShell client agents. Built to act as an autonomous **"AI Master IT Doctor"**, it performs multi-layered hardware diagnostics, component store self-healing, Microsoft Defender live antivirus scanning, winget CLI package management, deep storage purging, and one-click AI autonomous system updates across Windows endpoints without requiring any paid cloud servers or database infrastructure.

---

## 🚀 Key Capabilities

### 1. Python Backend & Real-Time Command Dashboard
- **FastAPI Core (`backend/server.py`)**: Asynchronous, high-throughput WebSocket hub & REST API.
- **Futuristic Glassmorphic Web Dashboard (`backend/static/`)**:
  - Central holographic Vitality Index (0-100 score).
  - 5 Categorical health score meters: **Hardware**, **Operating System**, **Storage**, **Drivers**, and **Security**.
  - Real-time telemetry monitoring (CPU, RAM, Disk, Gateway Latency).
  - Interactive terminal streaming live stdout/stderr logs from agents in real time.
  - One-Click **"Fix All"** master button and targeted remediation pills.
  - Multi-node fleet selector.
- **Streamlit Executive Companion (`dashboard/streamlit_app.py`)**:
  - Fleet-wide analytics, historical telemetry line charts, and deep issue audits.

### 2. Client-Side Deep Diagnostic Engine (The "Master Scan")
- **Hardware Diagnostics**:
  - Physical drive SMART status (`Get-PhysicalDisk`, SSD/HDD health, wear, bad sectors).
  - RAM health, module speeds, and memory allocation faults.
  - CPU frequency throttling detection (Current vs. Max clock speed ratio) and ACPI thermal monitoring.
  - Device Manager Yellow-Bang inspection (`Win32_PnPEntity` error codes 10, 28, 43, etc.).
- **OS & File System Integrity**:
  - DISM component store corruption check (`/CheckHealth` & CBS analysis).
  - System File Checker (SFC) integrity analysis & CBS servicing log parser.
  - Registry startup key audit (flags broken Run/RunOnce keys pointing to missing binaries).
  - Orphaned desktop and Start Menu shortcut scanner.
- **Performance & Bottleneck Analysis**:
  - Windows Event Log parser (detects Kernel-Power Event ID 41, BSOD BugChecks, App crashes, Disk controller errors).
  - Background runaway process detection (CPU > 45% or RAM > 1.2 GB).
  - Network stack diagnostics: DNS latency benchmarking, default gateway ping, packet loss.

### 3. Autonomous Remediation & "One-Click Fix" Engine
- **Targeted Automated Actions**:
  - `FIX_DISM_RESTORE`: Runs `dism.exe /Online /Cleanup-Image /RestoreHealth`.
  - `FIX_SFC_REPAIR`: Runs `sfc.exe /scannow`.
  - `FIX_NETWORK_STACK`: Runs `ipconfig /flushdns`, `ipconfig /registerdns`, `netsh winsock reset`, `netsh int ip reset`.
  - `FIX_CLEAN_DEEP_JUNK`: Purges Temp, Prefetch, and servicing download caches.
  - `FIX_REGISTRY_INTEGRITY`: Prunes broken startup keys with automatic rollback backup.
  - `FIX_ORPHAN_SHORTCUTS`: Removes dead shortcut links.
  - `FIX_RESTART_SERVICES`: Recycles `wuauserv`, `bits`, `cryptsvc`, and `spooler`.
  - `FIX_DRIVER_RESCAN`: Runs `pnputil /scan-devices`.
  - `FIX_POWER_OPTIMIZE`: Restores High Performance power plan profile.
  - `FIX_ALL`: Sequences the complete multi-phase remediation pipeline.

### 4. Multi-User Session Isolation & Token-Based Linkage
- **Per-User Scoped Payloads**: Each client machine runs with a unique Session Token (e.g., `APEX-A1B2C3D4`). Telemetry is scoped exclusively to `clients/{AGENT_TOKEN}/status.json` on GitHub.
- **Zero Cross-Tenant Data Leakage**: Administrators authenticate via their private token on the Streamlit dashboard or via direct URL (`?token=APEX-A1B2C3D4`). Sessions are strictly isolated in `st.session_state`.
- **Automatic Lifecycle Termination**: When the PowerShell agent terminates (Ctrl+C, terminal exit, or window close), it automatically updates its GitHub status to `OFFLINE` and exits cleanly without hanging background processes.

---

## 📁 Project Structure

```
d:\sharyar\online master pc\
├── backend/
│   ├── server.py              # FastAPI server, WebSocket hub, REST endpoints
│   ├── security.py            # HMAC-SHA256 signature, token validation, anti-replay
│   ├── node_manager.py        # Client registry, telemetry buffers, health scoring
│   ├── remediation_engine.py  # Fix payload generator, task orchestrator, verification
│   └── static/
│       ├── index.html         # Futuristic Glassmorphic Commander Web Dashboard
│       ├── css/apex.css       # Sleek cyberpunk theme, gauges, glowing animations
│       └── js/apex_dash.js    # WebSocket client, live charts, terminal streamer
├── dashboard/
│   └── streamlit_app.py       # Streamlit executive analytics companion
├── agent/
│   ├── apex_agent.py          # Unified Python agent (multi-threaded, WMI, WebSockets)
│   ├── ApexAgent.ps1          # Pure PowerShell 5.1+ agent (Zero-python dependency)
│   ├── modules/
│   │   ├── hardware.py        # SMART, RAM, CPU throttling, PnP yellow-bang detection
│   │   ├── os_integrity.py    # DISM, SFC, Registry, Orphaned shortcuts, Junk metrics
│   │   ├── performance.py     # Event Logs (BSOD, Crashes), Resource hogs, Network stack
│   │   └── remediator.py      # Low-level system repair executors
│   └── self_destruct.py       # DoD 5220.22-M multi-pass secure wiper
├── tests/
│   ├── test_security.py       # Cryptographic signature & tamper tests
│   ├── test_backend.py        # Health scoring & node manager tests
│   └── test_agent_modules.py  # Diagnostic modules & shredder tests
├── docs/
│   ├── ARCHITECTURE.md        # Detailed architecture & component breakdown
│   ├── DEPLOYMENT.md          # Enterprise deployment (GPO, Intune, WinRM, UAC)
│   └── SECURITY_SPEC.md       # Cryptographic specifications & threat modeling
├── run_server.py              # CLI launcher for Backend & Web Dashboard
├── run_agent.py               # CLI launcher for Python Agent
└── run_streamlit.py           # CLI launcher for Streamlit Companion Dashboard
```

---

## 🛠️ Quick Start Guide

### 1. Launch the Backend Server
```bash
python run_server.py --port 8000
```
- Open Web Dashboard: **http://127.0.0.1:8000**
- API Documentation: **http://127.0.0.1:8000/docs**

### 2. Connect a Client Machine
#### Option A: Pure PowerShell Agent (No Python Required)
```powershell
powershell -ExecutionPolicy Bypass -File .\agent\ApexAgent.ps1 -ServerUrl "ws://127.0.0.1:8000"
```

#### Option B: Python Agent
```bash
python run_agent.py --server ws://127.0.0.1:8000 --elevate
```

### 3. Launch Streamlit Executive Companion (Optional)
```bash
python run_streamlit.py
```
- Open Streamlit: **http://127.0.0.1:8501**

### 4. Run Automated Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py"
```
