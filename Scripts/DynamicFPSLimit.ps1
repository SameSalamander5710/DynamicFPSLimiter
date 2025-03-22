# Set user specific values
$ahkExePath = "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" # change this to your specific directory
$UsageCutoffForDecrease = 80
$DelayBeforeDecrease = 2 
$UsageCutoffForIncrease = 70
$DelayBeforeIncrease = 3

# Initialize counters, states and file paths
$highUsageCounter = 0
$lowUsageCounter = 0
$lastState = "High" 
$ahkScriptPath_Dec = ".\DecreaseLimit.ahk"
$ahkScriptPath_Inc = ".\IncreaseLimit.ahk"

while ($true) {
    # Get GPU usage value
    $gpuUsage = [math]::Round((((Get-Counter "\GPU Engine(*_phys_0_eng_0_engtype_3D)\Utilization Percentage").CounterSamples | Where-Object { $_.CookedValue }).CookedValue | Measure-Object -Sum).Sum, 2)

    # Output the GPU usage
    Write-Host "Current GPU Usage: $gpuUsage%"

       # If GPU usage is greater than 80% (= UsageCutoffForDecrease%) for at least 2 (= DelayBeforeDecrease) consecutive seconds
    if ($gpuUsage -gt $UsageCutoffForDecrease) {
        $highUsageCounter++
        if ($highUsageCounter -ge $DelayBeforeDecrease -and $lastState -eq "High") {
            Start-Process $ahkExePath -ArgumentList $ahkScriptPath_Dec
            Write-Host "Started process for high usage."
            $lastState = "Low"
            $highUsageCounter = 0
        }
    } else {
        $highUsageCounter = 0
    }

    # If GPU usage is less than 70% (or UsageCutoffForIncrease) for at least 3 (= DelayBeforeIncrease) consecutive seconds
    if ($gpuUsage -lt $UsageCutoffForIncrease) {
        $lowUsageCounter++
        if ($lowUsageCounter -ge $DelayBeforeIncrease -and $lastState -eq "Low") {
            Start-Process $ahkExePath -ArgumentList $ahkScriptPath_Inc
            Write-Host "Started process for low usage."
            $lastState = "High"
            $lowUsageCounter = 0
        }
    } else {
        $lowUsageCounter = 0
    }

    # Wait for 1 second before checking again
    Start-Sleep -Seconds 1
}

