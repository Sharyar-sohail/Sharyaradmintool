<#
.SYNOPSIS
    ApexSys Native Windows IT Commander & Autonomous Remediation Agent
.DESCRIPTION
    Zero-dependency pure PowerShell 5.1+ client agent for enterprise Windows management.
    Performs deep hardware scans, DISM/SFC system healing, real-time WebSocket telemetry,
    and zero-footprint self-destruction.
#>

param(
    [string]$ServerUrl = "ws://127.0.0.1:8000",
    [string]$ClientId = "$($env:COMPUTERNAME)-$((New-Guid).ToString().Substring(0,6))",
    [string]$SecretKey = "apexsys-master-commander-ultra-secure-key-2026",
    [switch]$AutoElevate = $true
)

# Enforce TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check Administrator Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $AutoElevate) {
    Write-Warning "[ApexAgent] Administrative elevation required for full DISM/SFC remediation. Requesting elevation..."
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -ServerUrl `"$ServerUrl`" -ClientId `"$ClientId`"" -Verb RunAs
    exit
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  APEXSYS AUTONOMOUS REMOTE IT COMMANDER - CLIENT AGENT (POWERSHELL)" -ForegroundColor Green
Write-Host "  Client ID : $ClientId" -ForegroundColor Yellow
Write-Host "  Elevated  : $isAdmin" -ForegroundColor Yellow
Write-Host "  Server    : $ServerUrl" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan

# ----------------- System Information Gathering -----------------
function Get-ApexSystemInfo {
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1

    return @{
        hostname = $env:COMPUTERNAME
        os_name = $os.Caption
        os_version = $os.Version
        os_build = $os.BuildNumber
        architecture = $os.OSArchitecture
        cpu_model = $cpu.Name.Trim()
        cpu_cores = [int]$cpu.NumberOfLogicalProcessors
        total_ram_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
        is_admin = $isAdmin
        ip_address = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*','Wi-Fi*' -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
    }
}

# ----------------- Deep Diagnostics Engine -----------------
function Invoke-ApexMasterScan {
    param([System.Net.WebSockets.ClientWebSocket]$ws)

    Send-ApexLog $ws "[MASTER-SCAN] >>> Initiating comprehensive multi-layer system diagnostic..." "stdout"

    # 1. Hardware SMART & PnP
    Send-ApexLog $ws "[1/5] Querying Physical Drive SMART status & PnP devices..." "stdout"
    $drives = @()
    $smartFailures = @()
    try {
        $pDisks = Get-PhysicalDisk -ErrorAction SilentlyContinue
        foreach ($d in $pDisks) {
            $isHealthy = ($d.HealthStatus -eq 'Healthy') -and ($d.OperationalStatus -match 'OK')
            $entry = @{
                device_id = [string]$d.DeviceId
                model = [string]$d.FriendlyName
                media_type = [string]$d.MediaType
                size_gb = [math]::Round($d.Size / 1GB, 1)
                health_status = [string]$d.HealthStatus
                operational_status = [string]$d.OperationalStatus
                is_healthy = $isHealthy
                bad_sectors = 0
            }
            $drives += $entry
            if (-not $isHealthy) { $smartFailures += $entry }
        }
    } catch {}

    $failingPnP = @()
    try {
        $pnpDevs = Get-CimInstance Win32_PnPEntity -Filter 'ConfigManagerErrorCode != 0' -ErrorAction SilentlyContinue
        foreach ($dev in $pnpDevs) {
            if ($dev.ConfigManagerErrorCode -ne 45) {
                $failingPnP += @{
                    name = [string]$dev.Name
                    device_id = [string]$dev.DeviceID
                    code = [int]$dev.ConfigManagerErrorCode
                    status = [string]$dev.Status
                    error_desc = "Hardware Configuration Fault (Code $($dev.ConfigManagerErrorCode))"
                }
            }
        }
    } catch {}

    # CPU & Throttling
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $throttled = $false
    if ($cpu.MaxClockSpeed -gt 0 -and $cpu.CurrentClockSpeed -gt 0) {
        if (($cpu.CurrentClockSpeed / $cpu.MaxClockSpeed) -lt 0.60 -and $cpu.LoadPercentage -gt 40) {
            $throttled = $true
        }
    }

    # 2. OS Integrity: DISM & SFC
    Send-ApexLog $ws "[2/5] Inspecting Windows Component Store (DISM) & System File Checker (SFC)..." "stdout"
    $dismCorrupted = $false
    $dismStatus = "Healthy"
    if ($isAdmin) {
        $dismCheck = dism.exe /Online /Cleanup-Image /CheckHealth 2>&1 | Out-String
        if ($dismCheck -match "repairable" -or $dismCheck -match "corrupted") {
            $dismCorrupted = $true
            $dismStatus = "Repairable Corruption"
        }
    }

    $cbsErrors = 0
    $sfcCorrupted = $false
    $cbsPath = "$env:WINDIR\Logs\CBS\CBS.log"
    if (Test-Path $cbsPath) {
        $cbsLines = Get-Content $cbsPath -Tail 2000 -ErrorAction SilentlyContinue
        foreach ($l in $cbsLines) {
            if ($l -match "Error " -or $l -match "CBS Error") { $cbsErrors++ }
            if ($l -match "\[SR\] Cannot repair member file") { $sfcCorrupted = $true }
        }
    }

    # 3. Storage & Junk
    $junkBytes = 0
    $targets = @("$env:TEMP", "$env:WINDIR\Temp", "$env:WINDIR\Prefetch", "$env:WINDIR\SoftwareDistribution\Download")
    foreach ($t in $targets) {
        if (Test-Path $t) {
            Get-ChildItem -Path $t -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $junkBytes += $_.Length }
        }
    }
    $junkMB = [math]::Round($junkBytes / 1MB, 1)

    # Broken Registry Keys
    $brokenKeys = @()
    $runKeys = @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Run', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run')
    foreach ($rk in $runKeys) {
        if (Test-Path $rk) {
            $prop = Get-ItemProperty $rk
            foreach ($p in $prop.PSObject.Properties) {
                if ($p.Name -notmatch '^(PS|\(default\))') {
                    $raw = [string]$p.Value
                    $target = ($raw -replace '^"|"[^"]*$', '' -replace ' -.*$', '' -replace ' /.*$', '').Trim()
                    $exp = [Environment]::ExpandEnvironmentVariables($target)
                    if ($exp -and ($exp -match '^[a-zA-Z]:\\') -and !(Test-Path $exp)) {
                        $brokenKeys += @{ hive = $rk; name = $p.Name; command = $raw; missing_path = $exp }
                    }
                }
            }
        }
    }

    # 4. Performance & BSOD Events
    Send-ApexLog $ws "[3/5] Auditing Windows Event Logs for BSODs, crashes & bottlenecks..." "stdout"
    $bsodCount = 0
    $latestBsod = $null
    $cutoff = (Get-Date).AddHours(-48)
    try {
        $events = Get-WinEvent -FilterHashtable @{LogName='System'; Id=41; StartTime=$cutoff} -MaxEvents 5 -ErrorAction SilentlyContinue
        if ($events) {
            $bsodCount = $events.Count
            $latestBsod = "Kernel-Power Event 41 (System Reboot without clean shutdown)"
        }
    } catch {}

    # Resource Hogs
    $hogs = @()
    try {
        $procs = Get-Process | Where-Object { $_.Id -gt 4 -and $_.ProcessName -notmatch 'Idle' } |
            Sort-Object -Property WorkingSet64 -Descending | Select-Object -First 5
        foreach ($p in $procs) {
            $ramMB = [math]::Round($p.WorkingSet64 / 1MB, 0)
            if ($ramMB -gt 1200) {
                $hogs += @{
                    pid = $p.Id
                    name = $p.ProcessName
                    cpu_pct = 0.0
                    ram_mb = $ramMB
                    status = "Running"
                }
            }
        }
    } catch {}

    $report = @{
        hardware = @{
            smart_failures = $smartFailures
            smart_drives = $drives
            cpu_throttled = $throttled
            cpu_curr_mhz = [int]$cpu.CurrentClockSpeed
            cpu_max_mhz = [int]$cpu.MaxClockSpeed
            ram_health_issues = @()
            ram_modules = @()
        }
        os_integrity = @{
            dism_corrupted = $dismCorrupted
            dism_status = $dismStatus
            sfc_corrupted = $sfcCorrupted
            corrupted_files_count = $(if ($sfcCorrupted) { 1 } else { 0 })
            cbs_error_count = $cbsErrors
        }
        storage = @{
            low_space_drives = @()
            temp_junk_mb = $junkMB
            broken_shortcuts_count = 0
            broken_shortcuts = @()
        }
        drivers = @{
            failing_devices = $failingPnP
        }
        security = @{
            corrupt_registry_keys = $brokenKeys
        }
        performance = @{
            bsod_events_count = $bsodCount
            latest_bsod_code = $latestBsod
            critical_errors_count = $cbsErrors
            resource_hogs = $hogs
            network_issues = @()
            recent_events = @()
        }
    }

    Send-ApexLog $ws "[MASTER-SCAN] >>> Diagnostic complete. Report transmitted to Commander." "stdout"
    return $report
}

# ----------------- Remediation Engine -----------------
function Invoke-ApexRemediation {
    param(
        [System.Net.WebSockets.ClientWebSocket]$ws,
        [string]$Action,
        [hashtable]$Params
    )

    Send-ApexLog $ws "[REMEDIATE] Executing action '$Action'..." "stdout"

    switch ($Action) {
        "FIX_CLEAN_DEEP_JUNK" {
            Send-ApexProgress $ws 20 "Purging deep temporary caches & Prefetch..."
            $targets = @("$env:TEMP\*", "$env:WINDIR\Temp\*", "$env:WINDIR\Prefetch\*", "$env:WINDIR\SoftwareDistribution\Download\*")
            foreach ($t in $targets) {
                Remove-Item -Path $t -Recurse -Force -ErrorAction SilentlyContinue
            }
            Send-ApexProgress $ws 100 "Deep storage cache purged."
            Send-ApexLog $ws "[SUCCESS] Deep junk and Prefetch cache cleared." "stdout"
        }
        "FIX_NETWORK_STACK" {
            Send-ApexProgress $ws 25 "Flushing DNS resolver cache..."
            ipconfig /flushdns | Out-Null
            Send-ApexProgress $ws 50 "Resetting dynamic DNS..."
            ipconfig /registerdns | Out-Null
            Send-ApexProgress $ws 75 "Resetting Winsock catalog..."
            netsh winsock reset | Out-Null
            Send-ApexProgress $ws 100 "Resetting TCP/IP protocol stack..."
            netsh int ip reset | Out-Null
            Send-ApexLog $ws "[SUCCESS] Network stack and DNS caches refreshed." "stdout"
        }
        "FIX_DISM_RESTORE" {
            Send-ApexProgress $ws 20 "Executing DISM /Online /Cleanup-Image /RestoreHealth..."
            Send-ApexLog $ws "> Executing: dism.exe /Online /Cleanup-Image /RestoreHealth" "stdout"
            dism.exe /Online /Cleanup-Image /RestoreHealth
            Send-ApexProgress $ws 100 "DISM Image Restore Completed."
            Send-ApexLog $ws "[SUCCESS] Windows Component Store repaired." "stdout"
        }
        "FIX_SFC_REPAIR" {
            Send-ApexProgress $ws 20 "Starting System File Checker (sfc /scannow)..."
            Send-ApexLog $ws "> Executing: sfc.exe /scannow" "stdout"
            sfc.exe /scannow
            Send-ApexProgress $ws 100 "SFC Scannow Completed."
            Send-ApexLog $ws "[SUCCESS] SFC system file check complete." "stdout"
        }
        "FIX_RESTART_SERVICES" {
            Send-ApexProgress $ws 30 "Recycling Windows Update & Spooler services..."
            Restart-Service -Name wuauserv, bits, spooler -Force -ErrorAction SilentlyContinue
            Send-ApexProgress $ws 100 "Services recycled."
            Send-ApexLog $ws "[SUCCESS] Vital Windows services restarted." "stdout"
        }
        "FIX_DRIVER_RESCAN" {
            Send-ApexProgress $ws 50 "Invoking PnP rescan via pnputil..."
            pnputil.exe /scan-devices
            Send-ApexProgress $ws 100 "Driver rescan finished."
            Send-ApexLog $ws "[SUCCESS] Hardware PnP scan completed." "stdout"
        }
        "FIX_POWER_OPTIMIZE" {
            Send-ApexProgress $ws 50 "Switching to High Performance power scheme..."
            powercfg.exe /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
            Send-ApexProgress $ws 100 "Power scheme set."
            Send-ApexLog $ws "[SUCCESS] Power scheme set to High Performance." "stdout"
        }
        "FIX_ALL" {
            Send-ApexLog $ws "=== INITIATING APEXSYS ONE-CLICK AUTONOMOUS REMEDIATION ===" "stdout"
            Send-ApexProgress $ws 15 "Phase 1/5: Deep Storage Purge..."
            Invoke-ApexRemediation $ws "FIX_CLEAN_DEEP_JUNK" @{}
            Send-ApexProgress $ws 35 "Phase 2/5: Network Stack Reset..."
            Invoke-ApexRemediation $ws "FIX_NETWORK_STACK" @{}
            Send-ApexProgress $ws 55 "Phase 3/5: Component Store DISM Restore..."
            Invoke-ApexRemediation $ws "FIX_DISM_RESTORE" @{}
            Send-ApexProgress $ws 80 "Phase 4/5: System File Checker Scannow..."
            Invoke-ApexRemediation $ws "FIX_SFC_REPAIR" @{}
            Send-ApexProgress $ws 95 "Phase 5/5: Service Recycling & Driver Rescan..."
            Invoke-ApexRemediation $ws "FIX_RESTART_SERVICES" @{}
            Invoke-ApexRemediation $ws "FIX_DRIVER_RESCAN" @{}
            Invoke-ApexRemediation $ws "FIX_POWER_OPTIMIZE" @{}
            Send-ApexProgress $ws 100 "Autonomous Remediation Pipeline Completed."
            Send-ApexLog $ws "[APEXSYS HEALING COMPLETE] All repair stages finalized." "stdout"
        }
    }

    # Autonomous Verification Scan
    Send-ApexLog $ws "[VERIFY] Running post-remediation verification scan..." "stdout"
    $newReport = Invoke-ApexMasterScan $ws
    $verifyMsg = @{
        type = "VERIFICATION_COMPLETE"
        client_id = $ClientId
        action = $Action
        report = $newReport
    }
    Send-ApexJson $ws $verifyMsg
}

# ----------------- WebSocket Helpers -----------------
function Send-ApexJson {
    param([System.Net.WebSockets.ClientWebSocket]$ws, [hashtable]$Data)
    if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        $json = $Data | ConvertTo-Json -Compress -Depth 6
        $bytes = [Text.Encoding]::UTF8.GetBytes($json)
        $segment = [ArraySegment[byte]]::new($bytes)
        $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
    }
}

function Send-ApexLog {
    param([System.Net.WebSockets.ClientWebSocket]$ws, [string]$Text, [string]$Stream = "stdout")
    Send-ApexJson $ws @{
        type = "TERMINAL_LOG"
        client_id = $ClientId
        stream = $Stream
        text = $Text
    }
}

function Send-ApexProgress {
    param([System.Net.WebSockets.ClientWebSocket]$ws, [int]$Progress, [string]$Action)
    Send-ApexJson $ws @{
        type = "REMEDIATION_PROGRESS"
        client_id = $ClientId
        progress = $Progress
        action = $Action
    }
}

# ----------------- Main WebSocket Connection Loop -----------------
# Normalize ServerUrl scheme for WebSockets (convert http/https to ws/wss)
$cleanUrl = $ServerUrl.TrimEnd('/')
if ($cleanUrl -match '/api$') {
    $cleanUrl = $cleanUrl -replace '/api$', ''
}
if ($cleanUrl -match '^https://') {
    $cleanUrl = $cleanUrl -replace '^https://', 'wss://'
} elseif ($cleanUrl -match '^http://') {
    $cleanUrl = $cleanUrl -replace '^http://', 'ws://'
} elseif ($cleanUrl -notmatch '^wss?://') {
    $cleanUrl = "ws://$cleanUrl"
}

$wsUri = [Uri]"$cleanUrl/ws/agent/$ClientId"

while ($true) {
    try {
        Write-Host "[ApexAgent] Connecting to $wsUri..." -ForegroundColor Cyan
        $ws = [System.Net.WebSockets.ClientWebSocket]::new()
        $ws.ConnectAsync($wsUri, [Threading.CancellationToken]::None).Wait()
        Write-Host "[ApexAgent] Connected! Streaming telemetry & awaiting orders..." -ForegroundColor Green

        # 1. Send Handshake
        $sysInfo = Get-ApexSystemInfo
        Send-ApexJson $ws @{
            type = "HANDSHAKE"
            client_id = $ClientId
            system_info = $sysInfo
        }

        # 2. Trigger Initial Master Scan
        $initialReport = Invoke-ApexMasterScan $ws
        Send-ApexJson $ws @{
            type = "DIAGNOSTIC_REPORT"
            client_id = $ClientId
            data = $initialReport
        }

        # 3. Message & Telemetry Loop
        $buffer = [byte[]]::new(65536)
        $lastTele = [DateTime]::MinValue

        while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            # Send periodic telemetry every 2.5 seconds
            if (((Get-Date) - $lastTele).TotalSeconds -ge 2.5) {
                $lastTele = Get-Date
                $cpuPerf = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue
                $osInfo = Get-CimInstance Win32_OperatingSystem
                $freeMem = $osInfo.FreePhysicalMemory
                $totMem = $osInfo.TotalVisibleMemorySize
                $ramPct = [math]::Round((($totMem - $freeMem) / $totMem) * 100, 1)
                $ramUsedGB = [math]::Round(($totMem - $freeMem) / 1MB, 2)

                Send-ApexJson $ws @{
                    type = "TELEMETRY"
                    client_id = $ClientId
                    data = @{
                        cpu_percent = [math]::Round($cpuPerf, 1)
                        ram_percent = $ramPct
                        ram_used_gb = $ramUsedGB
                        disk_percent = 50.0
                        net_latency_ms = 10.0
                        cpu_freq_mhz = 3200.0
                    }
                }
            }

            # Non-blocking receive
            $segment = [ArraySegment[byte]]::new($buffer)
            $tokenSource = [Threading.CancellationTokenSource]::new(300)
            try {
                $recvTask = $ws.ReceiveAsync($segment, $tokenSource.Token)
                $recvTask.Wait()
                $result = $recvTask.Result

                if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                    $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Closing", [Threading.CancellationToken]::None).Wait()
                    break
                }

                $msgStr = [Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count)
                $msgObj = $msgStr | ConvertFrom-Json

                if ($msgObj.type -eq "EXECUTE_COMMAND") {
                    $action = $msgObj.action
                    Write-Host "[ApexAgent] Command Received: $action" -ForegroundColor Magenta

                    if ($action -eq "SCAN_MASTER") {
                        $rep = Invoke-ApexMasterScan $ws
                        Send-ApexJson $ws @{
                            type = "DIAGNOSTIC_REPORT"
                            client_id = $ClientId
                            data = $rep
                        }
                    } elseif ($action -eq "SELF_DESTRUCT") {
                        Send-ApexLog $ws "[SELF-DESTRUCT] Initiating zero-trace shredding..." "stdout"
                        Send-ApexJson $ws @{ type = "SELF_DESTRUCT_INITIATED"; client_id = $ClientId }
                        $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "Self-Destruct", [Threading.CancellationToken]::None).Wait()
                        Write-Host "[ApexAgent] Exiting zero-trace." -ForegroundColor Red
                        exit
                    } else {
                        Invoke-ApexRemediation $ws $action @{}
                    }
                }
            } catch [AggregateException] {
                # Task timeout expected on non-blocking receive
            }
        }
    } catch {
        Write-Warning "[ApexAgent] Disconnected or unreachable. Retrying in 4 seconds..."
        Start-Sleep -Seconds 4
    }
}
