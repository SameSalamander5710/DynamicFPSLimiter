# Sapmple codes for reference

import wmi
w = wmi.WMI(namespace="root\\CIMV2")

def get_gpu_utilization():
    try:
        gpu_data = w.query("SELECT * FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine")
        usage_values = []
        for item in gpu_data:
            if "engtype_3D" in item.Name:
                usage_values.append(float(item.UtilizationPercentage))
        if usage_values:
            avg_usage = sum(usage_values) / len(usage_values)
            return round(avg_usage, 2)
        return 0.0
    except Exception as e:
        print("WMI query failed:", e)
        return None

print("GPU Utilization:", get_gpu_utilization(), "%")

gpu_engines = w.query("SELECT * FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine")
for engine in gpu_engines:
    print(engine.Name, engine.UtilizationPercentage)

#To see all available classes in the WMI namespace
for cls in w.classes:
    if "GPU" in cls:
        print(cls)

# PowerShell command to get GPU usage within loop from all GPUs
ps_command = '''
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
 Where-Object { $_.Name -like '*_engtype_*' } |
 ForEach-Object {
     if ($_.Name -match "luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys") {
         [PSCustomObject]@{
             LUID = $matches[1]
             Utilization = $_.UtilizationPercentage
         }
     }
 } |
 Group-Object -Property LUID |
 ForEach-Object {
     ($_.Group.Utilization | Measure-Object -Sum).Sum
 } |
 Measure-Object -Maximum).Maximum
'''

def get_top_luid_and_utilization():

    global luid

    ps_get_top_luid = '''
Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
    Where-Object { $_.Name -like '*_engtype_3D*' } |
    ForEach-Object {
        if ($_.Name -match "luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys") {
            [PSCustomObject]@{
                LUID = $matches[1]
                Utilization = $_.UtilizationPercentage
            }
        }
    } |
    Group-Object -Property LUID |
    ForEach-Object {
        [PSCustomObject]@{
            LUID = $_.Name
            TotalUtilization = ($_.Group.Utilization | Measure-Object -Sum).Sum
        }
    } | Sort-Object -Property TotalUtilization -Descending | Select-Object -First 1 |
    ForEach-Object { "$($_.LUID),$($_.TotalUtilization)" }
'''
    result = send_ps_command(ps_get_top_luid)
    if result:
        luid, util = result[0].split(',')
        #add_log(f"Tracking LUID: {luid} | Current Utilization: {util}%")
        return luid.strip(), util.strip()
    else:
        add_log("> Failed to detect LUID.")
    
    return None, None

def get_gpu_usage():
    # Run the PowerShell command to get GPU usage
    global luid

    if luid and luid != "All":
        ps_command_top_luid = f'''
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
        Write-Output (
            (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
            Where-Object {{ $_.Name -like "*_{luid}_phys*" }} |
            Measure-Object -Property UtilizationPercentage -Sum).Sum
        )
        '''
        #add_log(f"Running command for LUID {luid}: {ps_command_top_luid}")
        gpu_usage_str = run_powershell_command(ps_command_top_luid)
        #add_log(f"GPU usage for LUID {luid}: {gpu_usage_str}")
    else:
        gpu_usage_str = run_powershell_command(ps_command)
        #add_log(f"GPU usage general: {gpu_usage_str}")

    # Check if the output is non-empty and a valid float
    if gpu_usage_str.strip():  # Strip to remove any extra whitespace
        try:
            gpu_usage = float(gpu_usage_str.strip().replace(',', '.'))
            return gpu_usage
        except ValueError:
            add_log(f"> ValueError in GPU usage readout: {gpu_usage_str.strip()}")
            return None  # or handle the error as appropriate
    else:
        add_log("> GPU usage: No output from PowerShell")
        return None  # or handle the error as appropriate
