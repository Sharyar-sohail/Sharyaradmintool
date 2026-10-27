<#
.SYNOPSIS
    ApexSys Native Windows IT Commander & GitHub Serverless Sync Agent
.DESCRIPTION
    Zero-dependency pure PowerShell 5.1+ agent. Gathers deep hardware diagnostics,
    OS integrity, storage bloat, and system telemetry, writes them to status.json,
    and automatically pushes the status to GitHub so Streamlit Community Cloud
    can display real-time machine telemetry with ZERO paid servers or open ports.
.EXAMPLE
    .\ApexAgent.ps1
    .\ApexAgent.ps1 -Continuous -IntervalSeconds 60
#>

param(
    [string]$RepoOwner = "SharyarSoahil",
    [string]$RepoName = "Sharyaradmintool",
    [string]$Branch = "main",
    [string]$GitHubToken = $env:GITHUB_TOKEN,
    $Continuous = $false,
    [int]$IntervalSeconds = 60,
    $AutoElevate = $true
)

# Parse loose boolean values
$isAutoElevate = if ($AutoElevate -is [bool]) { $AutoElevate } else { "$AutoElevate" -match '^(true|1)$' }
$isContinuous = if ($Continuous -is [bool]) { $Continuous } else { "$Continuous" -match '^(true|1)$' }

# Enforce TLS 1.2
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check Administrator Elevation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin -and $isAutoElevate) {
    Write-Warning "[ApexSys Agent] Administrative elevation required for full DISM/SFC hardware access. Elevating..."
    $scriptPath = $MyInvocation.MyCommand.Definition
    if (-not $scriptPath) { $scriptPath = "$PSScriptRoot\ApexAgent.ps1" }
    
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -RepoOwner `"$RepoOwner`" -RepoName `"$RepoName`" -Branch `"$Branch`""
    if ($GitHubToken) { $argList += " -GitHubToken `"$GitHubToken`"" }
    if ($isContinuous) { $argList += " -Continuous 1 -IntervalSeconds $IntervalSeconds" }
    
    Start-Process powershell.exe -ArgumentList $argList -Verb RunAs
    exit
}

Clear-Host
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "   APEXSYS AUTONOMOUS IT COMMANDER - GITHUB SERVERLESS SYNC AGENT" -ForegroundColor Green
Write-Host "   Target Repo : $RepoOwner/$RepoName ($Branch)" -ForegroundColor Yellow
Write-Host "   Elevated    : $isAdmin (Administrator)" -ForegroundColor Yellow
Write-Host "   Mode        : $(if ($isContinuous) { 'Continuous Loop (' + $IntervalSeconds + 's)' } else { 'Single Run' })" -ForegroundColor Yellow
Write-Host "=========================================================================" -ForegroundColor Cyan

# ----------------- Deep Diagnostic Collector -----------------
function Collect-ApexDiagnostics {
    Write-Host ""
    Write-Host "[*] [1/4] Gathering system specifications & live telemetry..." -ForegroundColor Cyan
    
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

    # IP address
    $ip = "127.0.0.1"
    try {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Ethernet*','Wi-Fi*' -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
    } catch {}

    # 1. Hardware SMART & Devices
    Write-Host "[*] [2/4] Auditing Physical Disk SMART status, CPU throttling & Devices..." -ForegroundColor Cyan
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
                    error_desc = "Device Configuration Error (Code $($dev.ConfigManagerErrorCode))"
                }
            }
        }
    } catch {}

    # Throttling
    $cpuThrottled = $false
    if ($cpu.MaxClockSpeed -gt 0 -and $cpu.CurrentClockSpeed -gt 0) {
        if (($cpu.CurrentClockSpeed / $cpu.MaxClockSpeed) -lt 0.60 -and $cpuPerf -gt 40) {
            $cpuThrottled = $true
        }
    }

    # 2. OS Integrity: DISM, SFC, CBS
    Write-Host "[*] [3/4] Inspecting Windows Component Store (DISM) & SFC CBS logs..." -ForegroundColor Cyan
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

    # Storage & Junk metrics
    $junkBytes = 0
    $targets = @("$env:TEMP", "$env:WINDIR\Temp", "$env:WINDIR\Prefetch", "$env:WINDIR\SoftwareDistribution\Download")
    foreach ($t in $targets) {
        if (Test-Path $t) {
            Get-ChildItem -Path $t -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $junkBytes += $_.Length }
        }
    }
    $junkMB = [math]::Round($junkBytes / 1MB, 1)

    # Logical Drives
    $logDrives = @()
    $sysDiskPct = 0.0
    try {
        Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 } | ForEach-Object {
            $tot = [math]::Round(($_.Used + $_.Free) / 1GB, 1)
            $fr = [math]::Round($_.Free / 1GB, 1)
            $pct = if ($tot -gt 0) { [math]::Round(($fr / $tot) * 100, 1) } else { 0 }
            if ($_.Name -eq "C") { $sysDiskPct = [math]::Round(($_.Used / ($_.Used + $_.Free)) * 100, 1) }
            $logDrives += @{
                letter = $_.Name
                total_gb = $tot
                free_gb = $fr
                free_pct = $pct
            }
        }
    } catch {}

    # 3. Performance & Event Logs (BSOD)
    Write-Host "[*] [4/4] Parsing Windows Event Logs for BSODs & Crashes..." -ForegroundColor Cyan
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

    # Score Computation
    $hwScore = 100 - ($smartFailures.Count * 40)
    if ($cpuThrottled) { $hwScore -= 15 }

    $osScore = 100
    if ($dismCorrupted) { $osScore -= 35 }
    if ($sfcCorrupted) { $osScore -= 30 }

    $storScore = 100
    if ($junkMB -gt 3000) { $storScore -= 15 }

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

    # Issues list
    $issues = @()
    if ($smartFailures.Count -gt 0) {
        $issues += @{
            category = "Hardware"
            severity = "CRITICAL"
            title = "SMART Disk Failure Detected"
            description = "One or more physical drives have predicted failure status."
            fix_id = "FIX_HARDWARE_ALERT"
        }
    }
    if ($cpuThrottled) {
        $issues += @{
            category = "Hardware"
            severity = "WARNING"
            title = "CPU Thermal/Power Throttling"
            description = "Processor frequency is restricted ($($cpu.CurrentClockSpeed) MHz vs $($cpu.MaxClockSpeed) MHz max)."
            fix_id = "FIX_POWER_OPTIMIZE"
        }
    }
    if ($dismCorrupted) {
        $issues += @{
            category = "Operating System"
            severity = "CRITICAL"
            title = "Windows Component Store Corruption"
            description = "System image damaged. Repairable via DISM RestoreHealth."
            fix_id = "FIX_DISM_RESTORE"
        }
    }
    if ($sfcCorrupted) {
        $issues += @{
            category = "Operating System"
            severity = "CRITICAL"
            title = "SFC Protected File Violations"
            description = "Damaged Windows system binaries logged in CBS.log."
            fix_id = "FIX_SFC_REPAIR"
        }
    }
    if ($junkMB -gt 2500) {
        $issues += @{
            category = "Storage"
            severity = "WARNING"
            title = "Deep Storage Cache Bloat ($([math]::Round($junkMB/1024, 2)) GB)"
            description = "Accumulated temporary caches, Prefetch, and servicing downloads."
            fix_id = "FIX_CLEAN_DEEP_JUNK"
        }
    }
    foreach ($dp in $failingPnP) {
        $issues += @{
            category = "Drivers"
            severity = "WARNING"
            title = "Driver/Device Fault: $($dp.name)"
            description = "$($dp.error_desc) (Status: $($dp.status))"
            fix_id = "FIX_DRIVER_RESCAN"
        }
    }
    if ($bsodCount -gt 0) {
        $issues += @{
            category = "Security"
            severity = "CRITICAL"
            title = "Recent System BSOD Crashes ($bsodCount events)"
            description = "System recorded Kernel-Power 41 crash events in last 48 hours."
            fix_id = "FIX_STABILITY_STACK"
        }
    }

    # Final Payload
    $nowUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $nowLocal = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

    return [ordered]@{
        client_id = $env:COMPUTERNAME
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
            ip_address = $ip
        }
        telemetry = [ordered]@{
            cpu_percent = [math]::Round($cpuPerf, 1)
            ram_percent = $ramPct
            ram_used_gb = $ramUsedGB
            disk_percent = $sysDiskPct
            net_latency_ms = 12.0
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
            storage = @{
                temp_junk_mb = $junkMB
                broken_shortcuts_count = 0
                drives = $logDrives
            }
            security = @{
                corrupt_registry_keys = @()
                bsod_events_count = $bsodCount
                latest_bsod_code = $latestBsod
                critical_errors_count = $cbsErrors
            }
        }
        issues = $issues
    }
}

# ----------------- GitHub Sync Engine -----------------
function Push-ApexStatusToGitHub {
    param([string]$StatusFilePath)

    Write-Host ""
    Write-Host "[*] Initiating GitHub State Sync for '$StatusFilePath'..." -ForegroundColor Cyan

    $pushed = $false

    # Method 1: Git CLI (Primary)
    $hasGit = Get-Command git -ErrorAction SilentlyContinue
    if ($hasGit -and (Test-Path ".git")) {
        try {
            Write-Host "  -> Attempting sync via local Git CLI..." -ForegroundColor Gray
            git add $StatusFilePath
            $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            git commit -m "ApexSys Telemetry Sync: $ts" | Out-Null
            git pull --rebase origin $Branch | Out-Null

            if ($GitHubToken) {
                $remoteAuthUrl = "https://" + $RepoOwner + ":" + $GitHubToken + "@github.com/" + $RepoOwner + "/" + $RepoName + ".git"
                $gitOut = git push $remoteAuthUrl $Branch 2>&1
            } else {
                $gitOut = git push origin $Branch 2>&1
            }

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Git CLI push succeeded!" -ForegroundColor Green
                $pushed = $true
            } else {
                Write-Warning ("  [!] Git CLI push returned code " + $LASTEXITCODE)
            }
        } catch {
            Write-Warning ("  [!] Git CLI push encountered exception: " + $_)
        }
    }

    # Method 2: GitHub REST API (Fallback if Git CLI is not installed or fails)
    if (-not $pushed -and $GitHubToken) {
        try {
            Write-Host "  -> Attempting sync via direct GitHub REST API..." -ForegroundColor Gray
            $apiUrl = "https://api.github.com/repos/" + $RepoOwner + "/" + $RepoName + "/contents/status.json"
            $headers = @{
                "Authorization" = ("token " + $GitHubToken)
                "User-Agent" = "ApexSys-Agent-PowerShell"
                "Accept" = "application/vnd.github.v3+json"
            }

            # Check existing file SHA
            $sha = $null
            try {
                $existing = Invoke-RestMethod -Uri $apiUrl -Headers $headers -Method Get -ErrorAction Stop
                if ($existing -and $existing.sha) { $sha = $existing.sha }
            } catch {
                $sha = $null
            }

            $fileBytes = [System.IO.File]::ReadAllBytes($StatusFilePath)
            $base64Content = [Convert]::ToBase64String($fileBytes)

            $commitMsg = "ApexSys Telemetry Update: " + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
            $body = @{
                message = $commitMsg
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

    if ($pushed) {
        Write-Host "[SUCCESS] Telemetry synchronized to GitHub repository!" -ForegroundColor Green
        Write-Host "          Streamlit dashboard will reflect this update instantly." -ForegroundColor Cyan
    } else {
        Write-Error "[ERROR] Could not push status.json to GitHub. Please verify git credentials or GitHub token."
    }
}

# ----------------- Execution Controller -----------------
$statusFile = Join-Path (Get-Location) "status.json"

do {
    $diagData = Collect-ApexDiagnostics
    $jsonOutput = $diagData | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($statusFile, $jsonOutput, [System.Text.Encoding]::UTF8)
    $scoreVal = $diagData.health_score
    Write-Host "[OK] Updated local $statusFile (Health Score: $scoreVal)" -ForegroundColor Green

    Push-ApexStatusToGitHub -StatusFilePath $statusFile

    if ($isContinuous) {
        Write-Host ""
        $waitMsg = "Waiting " + $IntervalSeconds + " seconds for next telemetry cycle (Press Ctrl+C to stop)..."
        Write-Host $waitMsg -ForegroundColor Yellow
        Start-Sleep -Seconds $IntervalSeconds
    }
} while ($isContinuous)
