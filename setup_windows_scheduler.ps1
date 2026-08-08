# ╔══════════════════════════════════════════════════════════════════╗
# ║  9REALMS — WINDOWS TASK SCHEDULER SETUP                         ║
# ║                                                                  ║
# ║  Creates a daily 6AM task to run the 9realms update loop.        ║
# ║  Run this script as Administrator in PowerShell.                 ║
# ╚══════════════════════════════════════════════════════════════════╝

$ErrorActionPreference = "Stop"

# ── Configuration ──
$TaskName = "9REALMS_Daily_Update"
$TaskDescription = "9REALMS daily benchmark → evolve → deploy loop (ODIN PDUFA model)"
$RealmsRoot = "C:\Users\dcmoo\Documents\Python\9realms"
$PythonExe = "python"  # Change to full path if needed, e.g., "C:\Python311\python.exe"
$ScriptPath = "$RealmsRoot\mcp_core\9realms_update_loop.py"
$LogDir = "$RealmsRoot\alerts"
$LogFile = "$LogDir\scheduler_log.txt"

# ── Verify paths ──
if (-not (Test-Path $ScriptPath)) {
    Write-Error "Script not found: $ScriptPath"
    exit 1
}

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# ── Create the scheduled task ──

# Action: run python with the update loop, redirecting output to log
$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScriptPath`" >> `"$LogFile`" 2>&1" `
    -WorkingDirectory $RealmsRoot

# Trigger: daily at 6:00 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At "06:00AM"

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# Principal: run whether user is logged on or not
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

# Register (or update if exists)
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Updating existing task: $TaskName"
    Set-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings
} else {
    Write-Host "Creating new task: $TaskName"
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════"
Write-Host "  9REALMS Task Scheduler Setup Complete"
Write-Host "═══════════════════════════════════════════════════"
Write-Host "  Task Name:    $TaskName"
Write-Host "  Schedule:     Daily at 6:00 AM"
Write-Host "  Script:       $ScriptPath"
Write-Host "  Log:          $LogFile"
Write-Host ""
Write-Host "  To run manually:  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  To check status:  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  To disable:       Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  To remove:        Unregister-ScheduledTask -TaskName '$TaskName'"
Write-Host "═══════════════════════════════════════════════════"
