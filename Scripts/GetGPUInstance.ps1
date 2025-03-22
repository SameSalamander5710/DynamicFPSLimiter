# Use the following to identify the right instance for your GPU utilization

Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine | Select-Object Name, UtilizationPercentage

# Replace the (*_phys_0_eng_0_engtype_3D) with the correct instance if you have multiple GPUs running and its affecting your GPU utilization parameter