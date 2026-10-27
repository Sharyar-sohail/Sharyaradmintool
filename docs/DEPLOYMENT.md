# ApexSys Enterprise Deployment & Administration Guide

This guide details the deployment topologies, privilege requirements, network prerequisites, and automation scripts for deploying ApexSys across enterprise Windows environments.

---

## 1. Privilege & Execution Requirements

### 1.1 Administrator Elevation
ApexSys is designed to perform low-level hardware diagnostics, Windows Component Store repair, and system-wide file healing.
- **Full Capabilities (Administrator / SYSTEM)**:
  - DISM `/Online /Cleanup-Image /RestoreHealth` and `/ScanHealth`
  - SFC `/scannow` repair of protected Windows binaries
  - Network stack reset (`netsh winsock reset`, `netsh int ip reset`)
  - Clearing system-locked cache folders (`C:\Windows\Temp`, `C:\Windows\Prefetch`, `SoftwareDistribution`)
  - Restarting Windows Update (`wuauserv`), BITS, and CryptSvc services
  - PnP hardware driver re-enumeration (`pnputil /scan-devices`)
- **Standard User (Un-elevated)**:
  - Hardware SMART status and CPU/RAM metrics
  - CBS log audit for component store errors
  - Event log reading (BSOD 41, crashes)
  - User temp junk calculation and cleaning
  - Running diagnostics in advisory mode

> [!IMPORTANT]
> The agent automatically detects privilege level. If launched un-elevated with the `--elevate` flag (Python) or `$AutoElevate = $true` (PowerShell), it invokes a UAC prompt or `Start-Process -Verb RunAs`.

---

## 2. Deployment Strategies

### Strategy A: Zero-Python Endpoint Deployment (Pure PowerShell 5.1+)
For environments where Python is not pre-installed on managed PCs, use `agent/ApexAgent.ps1`. It utilizes the native .NET WebSocket client (`System.Net.WebSockets.ClientWebSocket`) and CIM/WMI modules.

```powershell
# Run from an elevated PowerShell terminal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\agent\ApexAgent.ps1 -ServerUrl "ws://<COMMANDER_IP>:8000"
```

### Strategy B: Python Client Agent
For technical workstations or environments with Python 3.10+ installed:

```bash
# Install dependencies
pip install psutil websockets requests

# Start the agent
python run_agent.py --server ws://<COMMANDER_IP>:8000 --elevate
```

### Strategy C: Active Directory Group Policy (GPO)
To run ApexSys autonomously across domain-joined computers on startup:
1. Open **Group Policy Management Console** (`gpmc.msc`).
2. Navigate to **Computer Configuration** > **Policies** > **Windows Settings** > **Scripts (Startup/Shutdown)** > **Startup**.
3. Add a PowerShell script with parameters:
   - **Script Name**: `powershell.exe`
   - **Script Parameters**: `-ExecutionPolicy Bypass -WindowStyle Hidden -File "\\domain\netlogon\ApexAgent.ps1" -ServerUrl "ws://192.168.1.100:8000"`
4. Because GPO Startup scripts execute under the **NT AUTHORITY\SYSTEM** account, the agent runs with maximum privileges with zero user disruption.

### Strategy D: Microsoft Intune Deployment
Deploy `ApexAgent.ps1` via Intune **Scripts**:
1. Sign in to the **Microsoft Intune Admin Center**.
2. Go to **Devices** > **Scripts** > **Add** > **Windows 10 and later**.
3. Upload `ApexAgent.ps1`.
4. Configure script settings:
   - **Run this script using the logged on credentials**: No (runs as SYSTEM)
   - **Enforce script signature check**: No
   - **Run script in 64-bit PowerShell Host**: Yes
5. Assign to target Device Groups.

### Strategy E: Remote Execution via WinRM / PSRemoting
Trigger an instant diagnostic or remediation pass across a remote subnet:

```powershell
$servers = @("PC-ENG-01", "PC-SALES-04", "PC-DEV-12")
Invoke-Command -ComputerName $servers -ScriptBlock {
    param($commander)
    Invoke-WebRequest -Uri "http://$commander:8000/static/ApexAgent.ps1" -OutFile "$env:TEMP\ApexAgent.ps1"
    Start-Process powershell.exe -ArgumentList "-ExecutionPolicy Bypass -File `"$env:TEMP\ApexAgent.ps1`" -ServerUrl `"ws://$commander:8000`""
} -ArgumentList "192.168.1.50"
```

---

## 3. Network & Firewall Configuration

| Port | Protocol | Direction | Source | Destination | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **8000** | TCP / HTTP & WS | Outbound from Client | Client PC | ApexSys Server | Real-time WebSocket telemetry & command streaming |
| **8000** | TCP / HTTP | Inbound to Server | IT Admin Browser | ApexSys Server | Web Command Dashboard & REST API access |
| **8501** | TCP / HTTP | Inbound to Server | IT Admin Browser | Streamlit App | Executive Companion Dashboard |

### Reverse Proxy & HTTPS / WSS Configuration (Recommended for Production)
For production environments, place NGINX or Caddy in front of the FastAPI backend to terminate TLS 1.3:

```nginx
server {
    listen 443 ssl http2;
    server_name commander.apexsys.internal;

    ssl_certificate /etc/ssl/apex_cert.pem;
    ssl_certificate_key /etc/ssl/apex_key.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
```
Client agents can then connect securely via `wss://commander.apexsys.internal/ws/agent/{client_id}`.
