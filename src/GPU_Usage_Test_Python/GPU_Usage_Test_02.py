# Too slow to practically use
# This script uses WMI to query GPU engine utilization on Windows.

import wmi
from collections import defaultdict
import re
import time

w = wmi.WMI(namespace="root\\CIMV2")

def get_top_luid_utilization():
    engines = w.query("SELECT * FROM Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine")

    usage_by_luid = defaultdict(list)

    for e in engines:
        name = e.Name
        usage = float(e.UtilizationPercentage)
        # Match the LUID right before "_phys"
        match = re.search(r"luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys", name)
        if match:
            luid = match.group(1)
            usage_by_luid[luid].append(usage)

    if not usage_by_luid:
        print("No matching LUIDs found.")
        return None

    # Return the top LUID by total utilization
    top_luid = max(usage_by_luid.items(), key=lambda item: sum(item[1]))
    luid, usages = top_luid
    total_usage = round(sum(usages), 2)
    print(f"Top LUID: {luid} with total 3D utilization: {total_usage}%")
    return luid, total_usage

while True:
    get_top_luid_utilization()
    time.sleep(1)