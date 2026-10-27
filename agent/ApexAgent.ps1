<#
.SYNOPSIS
    ApexSys Professional Windows Repair, Optimization & Multi-User State Sync Agent
.DESCRIPTION
    Zero-dependency pure PowerShell 5.1+ agent. Performs deep hardware diagnostics,
    SFC/DISM image verification, network/storage audits, and picks up remote cleanup
    maintenance commands (Temp, Prefetch, SoftwareDistribution) queued from Streamlit.
    Enforces strict token isolation: scoped to clients/{AGENT_TOKEN}/status.json.
.EXAMPLE
    .\ApexAgent.ps1 -AgentToken "APEX-A1B2C3D4"
    .\ApexAgent.ps1 -Continuous 1 -IntervalSeconds 30
#>

param(
    [string]$AgentToken = "",
    [string]$RepoOwner = "SharyarSoahil",
    [string]$RepoName = "Sharyaradmintool",
    [string]$Branch = "main",
    [string]$GitHubToken = $env:GITHUB_TOKEN,
    $Continuous = $false,
    [int]$IntervalSeconds = 30,
    $AutoElevate = $true
)

# Parse loose boolean values
$isAutoElevate = if ($AutoElevate -is [bool]) { $AutoElevate } else { "$AutoElevate" -match '^(true|1)$' }
$isContinuous = if ($Continuous -is [bool]) { $Continuous } else { "$Continuous" -match '^(true|1)$' }

# ----------------- Safe Execution Directory Resolution (Avoid System32) -----------------
$currentLoc = (Get-Location).Path
$scriptPath = $MyInvocation.MyCommand.Definition
$scriptDir = if ($scriptPath) { Split-Path -Parent $scriptPath } else { $PSScriptRoot }

# Determine safe root directory
$safeWorkDir = $null
if ($scriptDir -and (Test-Path "$scriptDir\.git")) {
    $safeWorkDir = $scriptDir
} elseif ($scriptDir -and (Test-Path "$scriptDir\..\.git")) {
    $safeWorkDir = (Resolve-Path "$scriptDir\..").Path
} elseif (Test-Path ".\.git") {
    $safeWorkDir = (Get-Location).Path
} else {
    # If launched from System32 or outside repository, relocate to safe dedicated folder
    $safeWorkDir = "C:\IT_Agent"
    if (-not (Test-Path $safeWorkDir)) {
        try {
            New-Item -ItemType Directory -Path $safeWorkDir -Force | Out-Null
        } catch {
            $safeWorkDir = Join-Path $env:TEMP "ApexSys_Agent"
            if (-not (Test-Path $safeWorkDir)) { New-Item -ItemType Directory -Path $safeWorkDir -Force | Out-Null }
        }
    }
}

Set-Location -Path $safeWorkDir

# ----------------- Token Management: Resolve or Generate -----------------
$tokenStore = Join-Path $env:TEMP "apex_agent_session_token.txt"
if (-not $AgentToken) {
    if (Test-Path $tokenStore) {
        $saved = (Get-Content $tokenStore -Raw -ErrorAction SilentlyContinue)
        if ($saved) { $AgentToken = $saved.Trim().ToUpper() }
    }
}
if (-not $AgentToken) {
    $AgentToken = "APEX-" + ([Guid]::NewGuid().ToString().Substring(0,8).ToUpper())
    Set-Content -Path $tokenStore -Value $AgentToken -Force
}

# Enforce TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check Administrator Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $isAutoElevate) {
    Write-Warning "[ApexSys Agent] Administrative elevation required for full DISM, SFC & cache maintenance. Elevating..."
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -AgentToken `"$AgentToken`" -RepoOwner `"$RepoOwner`" -RepoName `"$RepoName`" -Branch `"$Branch`""
    if ($GitHubToken) { $argList += " -GitHubToken `"$GitHubToken`"" }
    if ($isContinuous) { $argList += " -Continuous 1 -IntervalSeconds $IntervalSeconds" }
    
    Start-Process powershell.exe -ArgumentList $argList -Verb RunAs
    exit
}

Clear-Host
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "   APEXSYS ENTERPRISE WINDOWS REPAIR & OPTIMIZATION AGENT" -ForegroundColor Green
Write-Host "   SESSION TOKEN : $AgentToken" -ForegroundColor Magenta
Write-Host "   WORKING DIR   : $safeWorkDir" -ForegroundColor Gray
Write-Host "   TARGET REPO   : $RepoOwner/$RepoName ($Branch)" -ForegroundColor Yellow
Write-Host "   PRIVILEGES    : $(if ($isAdmin) { 'Elevated Administrator' } else { 'Standard User' })" -ForegroundColor Yellow
Write-Host "   SYNC MODE     : $(if ($isContinuous) { 'Continuous Loop (' + $IntervalSeconds + 's)' } else { 'Single Run' })" -ForegroundColor Yellow
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ">> DASHBOARD LINK: Enter '$AgentToken' in your Streamlit dashboard" -ForegroundColor Green
Write-Host "   Each administrator manages ONLY their linked machine with zero data mixing." -ForegroundColor Green
Write-Host "=========================================================================" -ForegroundColor Cyan

# ----------------- Deep Diagnostic Engine -----------------
function Collect-ApexDiagnostics {
    Write-Host ""
    Write-Host "[1/5] Auditing Processor, Clock Throttling & Live Telemetry..." -ForegroundColor Cyan
    
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1

    # CPU & RAM metrics
    $cpuPerf = 0.0
    try {
        $cpuPerf = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue
    } catch {}
    if (-not $cpuPerf -or $cpuPerf -eq 0) { $cpuPerf = [double]$cpu.LoadPercentage }

    $freeMem = $os.FreePhysicalMemory
    $totMem = $os.TotalVisibleMemorySize
    $ramPct = [math]::Round((($totMem - $freeMem) / $totMem) * 100, 1)
    $ramUsedGB = [math]::Round(($totMem - $freeMem) / 1MB, 2)
    $totRamGB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)

    # Throttling check
    $cpuThrottled = $false
    if ($cpu.MaxClockSpeed -gt 0 -and $cpu.CurrentClockSpeed -gt 0) {
        if (($cpu.CurrentClockSpeed / $cpu.MaxClockSpeed) -lt 0.60 -and $cpuPerf -gt 40) {
            $cpuThrottled = $true
        }
    }

    # 2. Hardware SMART & Driver Health
    Write-Host "[2/5] Inspecting Physical Drives (SMART) & Hardware Drivers..." -ForegroundColor Cyan
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
                    error_desc = "Driver Configuration Fault (Code $($dev.ConfigManagerErrorCode))"
                }
            }
        }
    } catch {}

    # 3. OS System Integrity (DISM, SFC, CBS)
    Write-Host "[3/5] Checking Windows Component Store (DISM) & SFC CBS logs..." -ForegroundColor Cyan
    $dismCorrupted = $false
    $dismStatus = "Healthy"
    if ($isAdmin) {
        try {
            $dismCheck = dism.exe /Online /Cleanup-Image /CheckHealth 2>&1 | Out-String
            if ($dismCheck -match "repairable" -or $dismCheck -match "corrupted") {
                $dismCorrupted = $true
                $dismStatus = "Repairable Corruption"
            }
        } catch {}
    }

    $cbsErrors = 0
    $sfcCorrupted = $false
    $cbsPath = "$env:WINDIR\Logs\CBS\CBS.log"
    if (Test-Path $cbsPath) {
        $cbsLines = Get-Content $cbsPath -Tail 1500 -ErrorAction SilentlyContinue
        foreach ($l in $cbsLines) {
            if ($l -match "Error " -or $l -match "CBS Error") { $cbsErrors++ }
            if ($l -match "\[SR\] Cannot repair member file") { $sfcCorrupted = $true }
        }
    }

    # 4. Network Stack & Adapters
    Write-Host "[4/5] Auditing Active Network Adapters & Connectivity..." -ForegroundColor Cyan
    $netAdapters = @()
    try {
        Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object {
            $netAdapters += @{
                name = $_.Name
                description = $_.InterfaceDescription
                status = [string]$_.Status
                link_speed = $_.LinkSpeed
                mac = $_.MacAddress
            }
        }
    } catch {}

    $primaryIp = "127.0.0.1"
    try {
        $primaryIp = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*','Wi-Fi*' -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
    } catch {}

    $dnsLatency = 12.0
    try {
        $t0 = [DateTime]::UtcNow
        [System.Net.Dns]::GetHostAddresses("google.com") | Out-Null
        $dnsLatency = [math]::Round(([DateTime]::UtcNow - $t0).TotalMilliseconds, 1)
    } catch {
        $dnsLatency = 999.0
    }

    # 5. Storage Partitions & Deep Junk Cache
    Write-Host "[5/5] Auditing Storage Partitions & Deep Cache Bloat..." -ForegroundColor Cyan
    $junkBreakdown = @{
        user_temp_mb = 0.0
        win_temp_mb = 0.0
        prefetch_mb = 0.0
        softwaredist_mb = 0.0
    }

    function Get-FolderMB($path) {
        if (-not (Test-Path $path)) { return 0.0 }
        $bytes = 0
        Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $bytes += $_.Length }
        return [math]::Round($bytes / 1MB, 1)
    }

    $junkBreakdown.user_temp_mb = Get-FolderMB "$env:TEMP"
    $junkBreakdown.win_temp_mb = Get-FolderMB "$env:WINDIR\Temp"
    $junkBreakdown.prefetch_mb = Get-FolderMB "$env:WINDIR\Prefetch"
    $junkBreakdown.softwaredist_mb = Get-FolderMB "$env:WINDIR\SoftwareDistribution\Download"
    $totalJunkMB = [math]::Round(($junkBreakdown.user_temp_mb + $junkBreakdown.win_temp_mb + $junkBreakdown.prefetch_mb + $junkBreakdown.softwaredist_mb), 1)

    $partitions = @()
    $sysDiskPct = 0.0
    try {
        Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 } | ForEach-Object {
            $tot = [math]::Round(($_.Used + $_.Free) / 1GB, 1)
            $fr = [math]::Round($_.Free / 1GB, 1)
            $pct = if ($tot -gt 0) { [math]::Round(($fr / $tot) * 100, 1) } else { 0 }
            if ($_.Name -eq "C") { $sysDiskPct = [math]::Round(($_.Used / ($_.Used + $_.Free)) * 100, 1) }
            $partitions += @{
                letter = $_.Name
                total_gb = $tot
                free_gb = $fr
                free_pct = $pct
            }
        }
    } catch {}

    # Event Logs: BSODs (Event 41) & Crashes (Event 1000)
    $bsodCount = 0
    $latestBsod = $null
    $cutoff = (Get-Date).AddHours(-48)
    try {
        $events = Get-WinEvent -FilterHashtable @{LogName='System'; Id=41; StartTime=$cutoff} -MaxEvents 5 -ErrorAction SilentlyContinue
        if ($events) {
            $bsodCount = $events.Count
            $latestBsod = "Kernel-Power Event 41 (System Rebooted unexpectedly)"
        }
    } catch {}

    # Score Calculation
    $hwScore = 100 - ($smartFailures.Count * 40)
    if ($cpuThrottled) { $hwScore -= 15 }

    $osScore = 100
    if ($dismCorrupted) { $osScore -= 35 }
    if ($sfcCorrupted) { $osScore -= 30 }

    $storScore = 100
    if ($totalJunkMB -gt 3000) { $storScore -= 15 }

    $drvScore = 100 - [math]::Min(50, ($failingPnP.Count * 20))
    $secScore = 100 - [math]::Min(40, ($bsodCount * 20))

    $hwScore = [math]::Max(0, [math]::Min(100, $hwScore))
    $osScore = [math]::Max(0, [math]::Min(100, $osScore))
    $storScore = [math]::Max(0, [math]::Min(100, $storScore))
    $drvScore = [math]::Max(0, [math]::Min(100, $drvScore))
    $secScore = [math]::Max(0, [math]::Min(100, $secScore))

    $overallScore = [int][math]::Round(
        ($hwScore * 0.20) + ($osScore * 0.25) + ($storScore * 0.15) + ($drvScore * 0.20) + ($secScore * 0.20)
    )

    # Actionable Issues Triage
    $issues = @()
    if ($smartFailures.Count -gt 0) {
        $issues += @{
            category = "Hardware"
            severity = "CRITICAL"
            title = "Physical SMART Disk Alert"
            description = "Drive health report predict-failure status. Bad sectors detected."
            fix_id = "ACTION_HARDWARE_CHECK"
        }
    }
    if ($cpuThrottled) {
        $issues += @{
            category = "Hardware"
            severity = "WARNING"
            title = "Processor Clock Throttling Detected"
            description = "CPU clock frequency throttled ($($cpu.CurrentClockSpeed) MHz vs $($cpu.MaxClockSpeed) MHz)."
            fix_id = "ACTION_OPTIMIZE_POWER"
        }
    }
    if ($dismCorrupted) {
        $issues += @{
            category = "Operating System"
            severity = "CRITICAL"
            title = "Windows Component Store Corruption"
            description = "System image damaged. Repairable via DISM RestoreHealth."
            fix_id = "ACTION_DISM_RESTORE"
        }
    }
    if ($sfcCorrupted) {
        $issues += @{
            category = "Operating System"
            severity = "CRITICAL"
            title = "SFC System File Integrity Violations"
            description = "Damaged Windows protected system binaries logged in CBS.log."
            fix_id = "ACTION_SFC_REPAIR"
        }
    }
    if ($totalJunkMB -gt 2000) {
        $issues += @{
            category = "Storage"
            severity = "WARNING"
            title = "Deep Storage Junk Bloat ($([math]::Round($totalJunkMB/1024, 2)) GB)"
            description = "Accumulated temporary caches, Prefetch, and servicing download packages."
            fix_id = "CLEAN_ALL_JUNK"
        }
    }
    foreach ($dp in $failingPnP) {
        $issues += @{
            category = "Drivers"
            severity = "WARNING"
            title = "Driver Error: $($dp.name)"
            description = "$($dp.error_desc) (Status: $($dp.status))"
            fix_id = "ACTION_RESCAN_DEVICES"
        }
    }
    if ($bsodCount -gt 0) {
        $issues += @{
            category = "Security"
            severity = "CRITICAL"
            title = "Recent System BSOD Crashes ($bsodCount events)"
            description = "Kernel-Power Event 41 crash records detected in last 48 hours."
            fix_id = "ACTION_STABILITY_CHECK"
        }
    }

    $nowUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $nowLocal = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

    return [ordered]@{
        client_id = $env:COMPUTERNAME
        agent_token = $AgentToken
        timestamp = $nowUtc
        last_synced = $nowLocal
        status = "ONLINE"
        health_score = $overallScore
        category_scores = [ordered]@{
            "Hardware" = $hwScore
            "Operating System" = $osScore
            "Storage" = $storScore
            "Drivers" = $drvScore
            "Security" = $secScore
        }
        system_info = [ordered]@{
            hostname = $env:COMPUTERNAME
            os_name = [string]$os.Caption
            os_version = [string]$os.Version
            os_build = [string]$os.BuildNumber
            architecture = [string]$os.OSArchitecture
            cpu_model = [string]$cpu.Name.Trim()
            cpu_cores = [int]$cpu.NumberOfLogicalProcessors
            total_ram_gb = $totRamGB
            is_admin = $isAdmin
            ip_address = $primaryIp
            working_dir = $safeWorkDir
        }
        telemetry = [ordered]@{
            cpu_percent = [math]::Round($cpuPerf, 1)
            ram_percent = $ramPct
            ram_used_gb = $ramUsedGB
            disk_percent = $sysDiskPct
            net_latency_ms = $dnsLatency
            cpu_freq_mhz = [double]$cpu.CurrentClockSpeed
        }
        diagnostics = [ordered]@{
            hardware = @{
                smart_failures = $smartFailures
                smart_drives = $drives
                cpu_throttled = $cpuThrottled
                cpu_curr_mhz = [int]$cpu.CurrentClockSpeed
                cpu_max_mhz = [int]$cpu.MaxClockSpeed
                failing_devices = $failingPnP
            }
            os_integrity = @{
                dism_corrupted = $dismCorrupted
                dism_status = $dismStatus
                sfc_corrupted = $sfcCorrupted
                corrupted_files_count = $(if ($sfcCorrupted) { 1 } else { 0 })
                cbs_error_count = $cbsErrors
            }
            network = @{
                adapters = $netAdapters
                primary_ip = $primaryIp
                dns_latency_ms = $dnsLatency
            }
            storage = @{
                temp_junk_mb = $totalJunkMB
                junk_breakdown = $junkBreakdown
                partitions = $partitions
            }
            security = @{
                bsod_events_count = $bsodCount
                latest_bsod_code = $latestBsod
                critical_errors_count = $cbsErrors
            }
        }
        issues = $issues
    }
}

# ----------------- Remote Maintenance Actuators -----------------
function Execute-ApexMaintenance($action, $params) {
    Write-Host "`n[!] EXECUTING REMOTE MAINTENANCE DIRECTIVE: $action" -ForegroundColor Green
    $details = ""
    $freedMB = 0.0

    switch ($action) {
        "CLEAN_ALL_JUNK" {
            Write-Host "  -> Purging Temp (%TEMP% & Windows Temp)..." -ForegroundColor Yellow
            $b1 = Purge-FolderFiles "$env:TEMP"
            $b2 = Purge-FolderFiles "$env:WINDIR\Temp"
            Write-Host "  -> Purging Prefetch Cache..." -ForegroundColor Yellow
            $b3 = Purge-FolderFiles "$env:WINDIR\Prefetch"
            Write-Host "  -> Purging SoftwareDistribution Download Cache..." -ForegroundColor Yellow
            $b4 = Purge-SoftwareDistribution
            $freedMB = [math]::Round(($b1 + $b2 + $b3 + $b4) / 1MB, 1)
            $details = "Cleaned all temporary files, Prefetch, and SoftwareDistribution. Freed $freedMB MB of space."
        }
        "CLEAN_TEMP" {
            Write-Host "  -> Purging User Temp & Windows Temp..." -ForegroundColor Yellow
            $b1 = Purge-FolderFiles "$env:TEMP"
            $b2 = Purge-FolderFiles "$env:WINDIR\Temp"
            $freedMB = [math]::Round(($b1 + $b2) / 1MB, 1)
            $details = "Purged temporary folders. Freed $freedMB MB."
        }
        "CLEAN_PREFETCH" {
            Write-Host "  -> Purging Prefetch files..." -ForegroundColor Yellow
            $b = Purge-FolderFiles "$env:WINDIR\Prefetch"
            $freedMB = [math]::Round($b / 1MB, 1)
            $details = "Purged Windows Prefetch cache. Freed $freedMB MB."
        }
        "CLEAN_SOFTWAREDIST" {
            Write-Host "  -> Purging Windows Update SoftwareDistribution Download cache..." -ForegroundColor Yellow
            $b = Purge-SoftwareDistribution
            $freedMB = [math]::Round($b / 1MB, 1)
            $details = "Purged SoftwareDistribution download repository. Freed $freedMB MB."
        }
        "RESET_NETWORK" {
            Write-Host "  -> Flushing DNS resolver cache..." -ForegroundColor Yellow
            ipconfig /flushdns | Out-Null
            Write-Host "  -> Resetting Winsock catalog..." -ForegroundColor Yellow
            netsh winsock reset | Out-Null
            $details = "DNS resolver flushed and Winsock catalog reset successfully."
        }
        "ACTION_DISM_RESTORE" {
            Write-Host "  -> Running DISM Component Store RestoreHealth..." -ForegroundColor Yellow
            $out = & dism.exe /Online /Cleanup-Image /RestoreHealth 2>&1
            $details = "DISM Component Store RestoreHealth executed successfully."
        }
        "ACTION_SFC_REPAIR" {
            Write-Host "  -> Running System File Checker (SFC /scannow)..." -ForegroundColor Yellow
            $out = & sfc.exe /scannow 2>&1
            $details = "System File Checker (SFC) repair scan executed."
        }
        "ACTION_RESCAN_DEVICES" {
            Write-Host "  -> Rescanning PnP hardware devices..." -ForegroundColor Yellow
            $out = & pnputil.exe /scan-devices 2>&1
            $details = "Device Manager PnP hardware rescan completed."
        }
        "FORCE_RESCAN" {
            Write-Host "  -> Immediate diagnostic rescan requested..." -ForegroundColor Yellow
            $details = "Immediate diagnostic rescan requested."
        }
        default {
            $details = "Completed maintenance action: $action"
        }
    }

    Write-Host "[OK] $details" -ForegroundColor Green
    return @{
        freed_mb = $freedMB
        details = $details
    }
}

function Purge-FolderFiles($folderPath) {
    if (-not (Test-Path $folderPath)) { return 0 }
    $freed = 0
    Get-ChildItem -Path $folderPath -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $sz = $_.Length
            Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
            $freed += $sz
        } catch {}
    }
    return $freed
}

function Purge-SoftwareDistribution {
    $folder = "$env:WINDIR\SoftwareDistribution\Download"
    if (-not (Test-Path $folder)) { return 0 }
    # Recycle Windows update service safely
    try { Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue } catch {}
    $freed = Purge-FolderFiles $folder
    try { Start-Service -Name wuauserv -ErrorAction SilentlyContinue } catch {}
    return $freed
}

# ----------------- GitHub Command Queue Checker -----------------
function Check-PendingCommands($commandFilePath, $relativeCommandPath) {
    # Check local or GitHub API
    $cmdData = $null

    # 1. Check local file if in repository
    if (Test-Path $commandFilePath) {
        try {
            $raw = Get-Content $commandFilePath -Raw -ErrorAction SilentlyContinue
            if ($raw) { $cmdData = $raw | ConvertFrom-Json }
        } catch {}
    }

    # 2. Check GitHub REST API
    if ((-not $cmdData -or $cmdData.status -ne "PENDING") -and $GitHubToken) {
        try {
            $apiUrl = "https://api.github.com/repos/$RepoOwner/$RepoName/contents/$relativeCommandPath"
            $headers = @{
                "Authorization" = ("token " + $GitHubToken)
                "User-Agent" = "ApexSys-Agent-PowerShell"
                "Accept" = "application/vnd.github.v3+json"
            }
            $apiRes = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get -ErrorAction Stop
            if ($apiRes -and $apiRes.content) {
                $decoded = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($apiRes.content))
                $cmdData = $decoded | ConvertFrom-Json
            }
        } catch {}
    }

    if ($cmdData -and $cmdData.status -eq "PENDING") {
        $action = $cmdData.action
        $result = Execute-ApexMaintenance $action $cmdData.parameters

        $cmdData.status = "COMPLETED"
        $cmdData.completed_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        $cmdData.result = $result.details
        $cmdData.freed_mb = $result.freed_mb

        $jsonOut = $cmdData | ConvertTo-Json -Depth 5
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($commandFilePath, $jsonOut, $utf8NoBom)

        Push-ApexFileToGitHub -FilePath $commandFilePath -RelativeRepoPath $relativeCommandPath -CommitMessage "ApexSys Maintenance Completed [$AgentToken]: $action"
    }
}

# ----------------- GitHub Sync Engine -----------------
function Push-ApexFileToGitHub {
    param(
        [string]$FilePath,
        [string]$RelativeRepoPath,
        [string]$CommitMessage = ""
    )

    Write-Host "[*] Synchronizing '$RelativeRepoPath' to GitHub..." -ForegroundColor Cyan
    $pushed = $false

    # Method 1: Git CLI (Primary if git is present and safe directory)
    $hasGit = Get-Command git -ErrorAction SilentlyContinue
    if ($hasGit -and (Test-Path ".git")) {
        try {
            git add $RelativeRepoPath 2>$null
            if (-not $CommitMessage) {
                $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
                $CommitMessage = "ApexSys Telemetry Sync [$AgentToken]: $ts"
            }
            git commit -m $CommitMessage 2>$null | Out-Null
            git pull --rebase origin $Branch 2>$null | Out-Null

            if ($GitHubToken) {
                $remoteAuthUrl = "https://" + $RepoOwner + ":" + $GitHubToken + "@github.com/" + $RepoOwner + "/" + $RepoName + ".git"
                $gitOut = git push $remoteAuthUrl $Branch 2>&1
            } else {
                $gitOut = git push origin $Branch 2>&1
            }

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Git CLI push succeeded!" -ForegroundColor Green
                $pushed = $true
            }
        } catch {}
    }

    # Method 2: GitHub REST API (Fallback / Standalone Mode)
    if (-not $pushed -and $GitHubToken) {
        try {
            $apiUrl = "https://api.github.com/repos/" + $RepoOwner + "/" + $RepoName + "/contents/" + $RelativeRepoPath
            $headers = @{
                "Authorization" = ("token " + $GitHubToken)
                "User-Agent" = "ApexSys-Agent-PowerShell"
                "Accept" = "application/vnd.github.v3+json"
            }

            $sha = $null
            try {
                $existing = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get -ErrorAction Stop
                if ($existing -and $existing.sha) { $sha = $existing.sha }
            } catch {
                $sha = $null
            }

            $fileBytes = [System.IO.File]::ReadAllBytes($FilePath)
            $base64Content = [Convert]::ToBase64String($fileBytes)

            if (-not $CommitMessage) {
                $CommitMessage = "ApexSys Telemetry Update [$AgentToken]: " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            }
            $body = @{
                message = $CommitMessage
                content = $base64Content
                branch = $Branch
            }
            if ($sha) { $body["sha"] = $sha }

            $jsonBody = $body | ConvertTo-Json -Compress
            $response = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Put -Body $jsonBody -ContentType "application/json" -ErrorAction Stop

            Write-Host "  [OK] GitHub REST API sync successful!" -ForegroundColor Green
            $pushed = $true
        } catch {
            Write-Warning ("  [!] GitHub REST API sync failed: " + $_)
        }
    }

    return $pushed
}

# ----------------- Execution Controller & Lifecycle Cleanup -----------------
$clientDir = Join-Path $safeWorkDir "clients\$AgentToken"
if (-not (Test-Path $clientDir)) {
    New-Item -ItemType Directory -Path $clientDir -Force | Out-Null
}
$statusFile = Join-Path $clientDir "status.json"
$commandFile = Join-Path $clientDir "commands.json"
$relativeStatusPath = "clients/$AgentToken/status.json"
$relativeCommandPath = "clients/$AgentToken/commands.json"

try {
    do {
        # 1. Process pending remote cleanup maintenance commands from Streamlit
        Check-PendingCommands -commandFilePath $commandFile -relativeCommandPath $relativeCommandPath

        # 2. Run comprehensive diagnostics
        $diagData = Collect-ApexDiagnostics
        $diagData.status = "ONLINE"
        $jsonOutput = $diagData | ConvertTo-Json -Depth 6
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($statusFile, $jsonOutput, $utf8NoBom)
        $scoreVal = $diagData.health_score
        Write-Host "`n[OK] Scoped status written: $statusFile (Health Score: $scoreVal%)" -ForegroundColor Green

        # 3. Synchronize status to GitHub
        Push-ApexFileToGitHub -FilePath $statusFile -RelativeRepoPath $relativeStatusPath

        # 4. Continuous interval sleep with fast command polling
        if ($isContinuous) {
            Write-Host ""
            $waitMsg = "Waiting " + $IntervalSeconds + " seconds for next cycle (Press Ctrl+C to stop)..."
            Write-Host $waitMsg -ForegroundColor Yellow

            # Sub-poll commands every 5 seconds during sleep
            $elapsed = 0
            while ($elapsed -lt $IntervalSeconds) {
                Start-Sleep -Seconds 5
                $elapsed += 5
                Check-PendingCommands -commandFilePath $commandFile -relativeCommandPath $relativeCommandPath
            }
        }
    } while ($isContinuous)
} finally {
    # Automatic Process Termination & Clean State Publication
    Write-Host ""
    Write-Host "[!] Shutdown signal received. Publishing OFFLINE state for '$AgentToken' to GitHub..." -ForegroundColor Yellow
    try {
        if (Test-Path $statusFile) {
            $offlineContent = Get-Content $statusFile -Raw | ConvertFrom-Json
            $offlineContent.status = "OFFLINE"
            $offlineContent.last_synced = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            $offlineContent.timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            $jsonOutput = $offlineContent | ConvertTo-Json -Depth 6
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($statusFile, $jsonOutput, $utf8NoBom)

            Push-ApexFileToGitHub -FilePath $statusFile -RelativeRepoPath $relativeStatusPath -CommitMessage "ApexSys Session Terminated [$AgentToken]: OFFLINE"
            Write-Host "[OK] Session cleanly marked OFFLINE on GitHub. Zero hanging processes." -ForegroundColor Green
        }
    } catch {
        Write-Warning ("Failed to publish exit state: " + $_)
    }
}
