# ApexSys Architecture Specification

ApexSys is an enterprise-grade autonomous remote IT administration and deep remediation suite designed to function as an autonomous "Master IT Doctor". It pairs a central real-time command dashboard with high-throughput client agents capable of deep OS/hardware diagnostics, DISM/SFC system healing, and zero-footprint lifecycle termination.

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Control_Plane ["ApexSys Commander (Server Side)"]
        FastAPI["FastAPI Command Hub (:8000)"]
        WSHub["WebSocket Event & Telemetry Broker"]
        NodeMgr["Node Manager & Scoring Engine"]
        RemedEngine["Remediation & Payload Orchestrator"]
        SecEngine["Cryptographic HMAC-SHA256 Engine"]
        WebUI["Futuristic Glassmorphic Web Dashboard"]
        StreamlitUI["Streamlit Executive Companion (:8501)"]
    end

    subgraph Client_Plane ["Managed Endpoint (Client Side)"]
        subgraph Agent_Core ["ApexSys Agent (Python / PowerShell)"]
            WSClient["Client WebSocket Streamer"]
            SecValidator["HMAC Payload Verifier"]
            TeleSampler["Rolling Telemetry Sampler (2s)"]
            SelfDestruct["DoD 5220.22-M Wiper"]
        end

        subgraph Diagnostic_Sensors ["Master Scan Diagnostic Core"]
            HW_Sensor["Hardware Diagnostics (SMART / RAM / CPU Throttling / PnP)"]
            OS_Sensor["OS Integrity (DISM CheckHealth / SFC / CBS Logs / Registry)"]
            Perf_Sensor["Performance & Bottlenecks (Event Logs / BSOD / Hogs / Network)"]
        end

        subgraph Remediation_Actuators ["Autonomous Remediation Actuators"]
            Act_DISM["DISM Component Store RestoreHealth"]
            Act_SFC["System File Checker Scannow"]
            Act_Net["Winsock / TCP-IP / DNS Stack Reset"]
            Act_Junk["Deep Storage & Cache Purger"]
            Act_Reg["Registry Startup Pruner"]
            Act_Svc["Vital Windows Services Recycler"]
            Act_PnP["pnputil Device Rescan"]
        end
    end

    WebUI <-->|WebSocket & REST| FastAPI
    StreamlitUI <-->|REST API| FastAPI
    FastAPI <--> WSHub
    WSHub <--> NodeMgr
    RemedEngine --> SecEngine
    SecEngine -->|Signed Payloads| WSHub

    WSHub <-->|Bi-directional WebSocket (:8000)| WSClient
    WSClient --> SecValidator
    SecValidator --> Remediation_Actuators
    Diagnostic_Sensors --> WSClient
    TeleSampler --> WSClient
    Remediation_Actuators -->|Live stdout/stderr| WSClient
    Remediation_Actuators --> SelfDestruct
```

---

## 2. Core Subsystems

### 2.1 Python Backend & Real-Time Broker (`backend/`)
- **FastAPI Core (`backend/server.py`)**: Asynchronous, high-concurrency HTTP/WebSocket server.
  - `/ws/agent/{client_id}`: Dedicated persistent bidirectional channel per client agent.
  - `/ws/dashboard`: Broadcast bus streaming fleet status, live telemetry ticks, progress updates, and terminal outputs to browser frontends.
  - REST Management API: Endpoints for node inspection, scan triggers, single-issue remediations, One-Click "Fix All", and self-destruct.
- **Node & Telemetry Manager (`backend/node_manager.py`)**:
  - Tracks live client connections, timestamps, and connection status (`ONLINE`, `SCANNING`, `REMEDIATING`, `OFFLINE`).
  - Computes holistic 0-100 Health Score across five weighted categories:
    - **Hardware (20%)**: SMART disk health, bad sector count, CPU throttling, RAM errors.
    - **Operating System (25%)**: DISM component store corruption, SFC hash mismatches, CBS log error spikes.
    - **Storage (15%)**: Free space %, deep junk cache volume, broken shortcuts.
    - **Drivers (20%)**: PnP Yellow-bang devices (Device Manager error codes 10, 28, 43, etc.).
    - **Security & Stability (20%)**: Damaged registry startup keys, BSOD crashes (Kernel-Power 41, BugCheck), runaway processes, network anomalies.
- **Remediation Catalog & Payload Orchestrator (`backend/remediation_engine.py`)**:
  - Prepares execution directives and sequences the multi-stage One-Click Master Fix pipeline.
  - Automatically computes pre-repair vs post-repair verification score deltas.
- **Security Engine (`backend/security.py`)**:
  - Signs every command using HMAC-SHA256 with timestamp, nonce, and target client identity.
  - Enforces a 300-second execution window and prevents replay attacks.

### 2.2 Client-Side Deep Diagnostic Engine (`agent/modules/`)
- **Hardware Diagnostics (`agent/modules/hardware.py`)**:
  - Queries `Get-PhysicalDisk` and `Win32_DiskDrive` for SMART status, media type, and failure predictions.
  - Queries `Win32_Processor` for current vs. maximum clock frequencies to detect thermal/power throttling.
  - Queries `Win32_PhysicalMemory` for module status and memory capacity.
  - Queries `Win32_PnPEntity` for devices with `ConfigManagerErrorCode != 0`, identifying uninstalled, stopped, or failing hardware devices.
- **OS & File System Integrity (`agent/modules/os_integrity.py`)**:
  - Executes `DISM /Online /Cleanup-Image /CheckHealth` (or inspects `CBS.log` fallback) for component store integrity.
  - Parses `C:\Windows\Logs\CBS\CBS.log` for System File Checker (`[SR]`) corruption markers and servicing faults.
  - Audits registry startup hives (`HKLM/HKCU\Software\Microsoft\Windows\CurrentVersion\Run`) to find invalid commands pointing to deleted or missing binaries.
  - Detects dead `.lnk` shortcuts on Desktop and Start Menu.
  - Calculates size of temporary caches (`%TEMP%`, `C:\Windows\Temp`, `Prefetch`, and `SoftwareDistribution\Download`).
- **Performance & Bottleneck Diagnostics (`agent/modules/performance.py`)**:
  - Queries Windows Event Logs for Critical (Level 1) and Error (Level 2) events in the last 48 hours.
  - Detects BSOD events: Event ID 41 (`Kernel-Power`), Event ID 1001 (`BugCheck`), Event ID 1000 (`Application Crash`), and Event ID 7/11 (`Disk controller errors`).
  - Audits startup items and task scheduler triggers.
  - Detects runaway background resource hogs (CPU > 45% or RAM > 1.2 GB).
  - Benchmarks network stack: DNS query latency, default gateway reachability, and packet loss.

### 2.3 Autonomous Remediation & One-Click Engine (`agent/modules/remediator.py`)
- Standardized low-level remediation actions:
  - `FIX_DISM_RESTORE`: Executes `dism.exe /Online /Cleanup-Image /RestoreHealth`.
  - `FIX_SFC_REPAIR`: Executes `sfc.exe /scannow`.
  - `FIX_NETWORK_STACK`: Executes `ipconfig /flushdns`, `ipconfig /registerdns`, `netsh winsock reset`, and `netsh int ip reset`.
  - `FIX_CLEAN_DEEP_JUNK`: Purges user temp, Windows temp, Prefetch, and servicing download caches.
  - `FIX_REGISTRY_INTEGRITY`: Prunes invalid startup entries with automated safety backups.
  - `FIX_ORPHAN_SHORTCUTS`: Prunes dead desktop and start menu shortcuts.
  - `FIX_RESTART_SERVICES`: Recycles `wuauserv`, `bits`, `cryptsvc`, and `spooler`.
  - `FIX_DRIVER_RESCAN`: Executes `pnputil.exe /scan-devices`.
  - `FIX_POWER_OPTIMIZE`: Restores High Performance power plan profile.
  - `FIX_ALL`: Sequences all phases with progress tracking (0% to 100%) and triggers an autonomous post-repair verification scan.

### 2.4 Zero-Footprint Lifecycle & Self-Destruct (`agent/self_destruct.py`)
- DoD 5220.22-M 3-pass file overwriting:
  1. Pass 1: 0x00 (All zeros)
  2. Pass 2: 0xFF (All ones)
  3. Pass 3: Cryptographically secure random bytes
- File truncation to 0 bytes followed by unlinking.
- Self-deleting batch runner spawned out-of-process to erase agent binaries and scratch folders after termination.
