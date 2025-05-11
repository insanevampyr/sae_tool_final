# Define paths
$projectDir = "C:\Users\VampyrLee\Desktop\sae_tool_final"
$venvActivate = "$projectDir\venv\Scripts\Activate.ps1"
$scriptPath = "$projectDir\price_monitor.py"
$logPath = "$projectDir\logs\price_monitor_log.txt"

# Ensure log directory exists
if (-not (Test-Path "$projectDir\logs")) {
    New-Item -Path "$projectDir\logs" -ItemType Directory
}

# Activate the virtual environment and run script with logging
& $venvActivate
Write-Output "`n=========================" >> $logPath
Write-Output "Started at: $(Get-Date)" >> $logPath

try {
    python $scriptPath >> $logPath 2>&1
    Write-Output "✅ Completed at: $(Get-Date)" >> $logPath
} catch {
    Write-Output "❌ ERROR at: $(Get-Date)" >> $logPath
    Write-Output $_.Exception.Message >> $logPath
}
