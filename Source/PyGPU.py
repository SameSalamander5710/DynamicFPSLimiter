# PyGPU.py
# This Python module provides a fast and lightweight way to access GPU usage data on Windows by directly querying Performance Data Helper (PDH) counters for the "GPU Engine" object. 
# It bypasses slower or more resource-intensive methods like WMI or PowerShell.
# To-do: Change prints to runtime errors

import ctypes
import time
from collections import defaultdict
import re

pdh = ctypes.windll.pdh

PDH_MORE_DATA = 0x800007D2
PDH_FMT_DOUBLE = 0x00000200

class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]

def init_gpu_state():
    """Initializes the PDH query and returns the handle."""
    query_handle = ctypes.c_void_p()
    status = pdh.PdhOpenQueryW(None, 0, ctypes.byref(query_handle))

    if status != 0:
        raise RuntimeError(f"Failed to open PDH query. Error: {status}")
    
    return query_handle

# Function to set up GPU instances and return a list of them
def setup_gpu_instances():

    # Get buffer size
    counter_buf_size = ctypes.c_ulong(0)
    instance_buf_size = ctypes.c_ulong(0)

    pdh.PdhEnumObjectItemsW(
        None, None,
        "GPU Engine",
        None, ctypes.byref(counter_buf_size),
        None, ctypes.byref(instance_buf_size),
        0, 0
    )

    counter_buf = (ctypes.c_wchar * counter_buf_size.value)()
    instance_buf = (ctypes.c_wchar * instance_buf_size.value)()

    ret = pdh.PdhEnumObjectItemsW(
        None, None,
        "GPU Engine",
        counter_buf, ctypes.byref(counter_buf_size),
        instance_buf, ctypes.byref(instance_buf_size),
        0, 0
    )

    if ret != 0:
        print(f"Failed to enumerate GPU Engine instances. Error: {ret}")
        return None, []

    instances = list(filter(None, instance_buf[:].split('\x00')))
    #print(f"Found {len(instances)} GPU Engine instances.")
   
    if instances:
        return instances
    else:    
        print("No GPU engine instances found.")
        return None, []

# Function to set up GPU query and counters from instances; filtered by engine type
# Returns query_handle and a dictionary of counter handles grouped by LUID
def setup_gpu_query_from_instances(query_handle, instances, engine_type="engtype_"):

    counter_handles_by_luid = defaultdict(list)

    for inst in instances:
        #print(f"Processing instance: {inst}")

        if engine_type not in inst:
            #print(f"Skipping instance: {inst} (not a GPU engine type)")
            continue

        #print(f"Found GPU engine type: {inst}")

        # Extract LUID (middle part before "_phys" or before "_engtype_")
        match = re.search(r"luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)", inst)

        #print(f"Match: {match}")

        if not match:
            continue

        #print(f"Found LUID: {match.group(1)}")

        luid = match.group(1)

        counter_path = f"\\GPU Engine({inst})\\Utilization Percentage"
        #print(f"Adding counter: {counter_path}")

        counter_handle = ctypes.c_void_p()
        status = pdh.PdhAddEnglishCounterW(query_handle, counter_path, None, ctypes.byref(counter_handle))
        if status == 0:
            #print(f"Added counter: {counter_path}")
            counter_handles_by_luid[luid].append(counter_handle)
            #print(f"Added counter: {counter_path}, counter_handle={counter_handle}")
            #print(f"query handle: {query_handle}, counter_handle={counter_handle}")
        else:
            print(f"Failed to add counter: {counter_path}, status={status}")

    return query_handle, dict(counter_handles_by_luid)

# Function to get GPU usage from the query handle and counter handles, and selected LUID if provided
# Returns the maximum utilization across all LUIDs and the corresponding LUID
def get_gpu_usage(query_handle, counter_handles_by_luid, target_luid=None):
    if query_handle is None or not counter_handles_by_luid:
        print("Query handle or counter handles are not set up.")
        return 0.0

    # Collect data twice for valid readings
    pdh.PdhCollectQueryData(query_handle)
    time.sleep(0.1)
    pdh.PdhCollectQueryData(query_handle)

    usage_by_luid = {}

    handles_to_use = (
        {target_luid: counter_handles_by_luid[target_luid]}
        if target_luid and target_luid in counter_handles_by_luid
        else counter_handles_by_luid
    )

    for luid, handles in handles_to_use.items():
        total = 0.0
        for h in handles:
            val = PDH_FMT_COUNTERVALUE()
            status = pdh.PdhGetFormattedCounterValue(h, PDH_FMT_DOUBLE, None, ctypes.byref(val))
            if status == 0 and val.CStatus == 0:
                total += val.doubleValue
            else:
                print(f"Failed to read counter (LUID: {luid}): status={status}, CStatus={val.CStatus}")
        usage_by_luid[luid] = total

    if not usage_by_luid:
        return 0.0

    # Get the max utilization across all LUIDs

    max_luid, max_usage = max(usage_by_luid.items(), key=lambda item: item[1])
    #print(f"Max LUID: {max_luid}, Usage: {max_usage:.1f}%")
    return int(max_usage), str(max_luid)

