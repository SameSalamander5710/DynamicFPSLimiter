import subprocess

ps_script_1 = 'Write-Output "PowerShell is running from EXE"'

p_1 = subprocess.Popen(
    ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script_1],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = p_1.communicate()
print("STDOUT:", stdout.strip())
print("STDERR:", stderr.strip())

ps_script_2 = r'''
[math]::Round((
    Get-Counter "\GPU Engine(*_phys_0_eng_0_engtype_3D)\Utilization Percentage",
                "\GPU Engine(*_phys_0_eng_0_engtype_Copy)\Utilization Percentage" |
    Select-Object -ExpandProperty CounterSamples |
    Where-Object { $_.Path -match "luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys_" } |
    Group-Object { $matches[1] } |
    ForEach-Object { ($_.Group.CookedValue | Measure-Object -Sum).Sum } |
    Measure-Object -Maximum
).Maximum, 2)
'''

p_2 = subprocess.Popen(
    ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script_2],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = p_2.communicate()
print("STDOUT: GPU usage = ", stdout.strip(), "%")
print("STDERR:", stderr.strip())

input("\nPress Enter to exit...")
