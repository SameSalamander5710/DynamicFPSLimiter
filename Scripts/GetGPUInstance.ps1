# Fetch and display GPU performance data
Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | 
    Select-Object Name, UtilizationPercentage | 
    Format-Table -AutoSize

# Pause to keep the window open after the output is shown
Read-Host -Prompt "Replace the (*_phys_0_eng_0_engtype_3D) with the correct instance if you have multiple GPUs running. Press Enter to exit"
