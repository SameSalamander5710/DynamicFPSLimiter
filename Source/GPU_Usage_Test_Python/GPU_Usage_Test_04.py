# Modify to match DynamicFPSLimiter.py

import ctypes
import time

pdh = ctypes.windll.pdh

PDH_MORE_DATA = 0x800007D2
PDH_FMT_DOUBLE = 0x00000200

class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]

def get_gpu_usage_engtype_3d():
    query_handle = ctypes.c_void_p()
    status = pdh.PdhOpenQueryW(None, 0, ctypes.byref(query_handle))
    if status != 0:
        print(f"Failed to open PDH query. Error: {status}")
        return None

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
        return None

    instances = list(filter(None, instance_buf[:].split('\x00')))
    #print(f"Found {len(instances)} GPU Engine instances.")
    if not instances:
        print("No GPU engine instances found.")
        return 0.0

    # Add relevant counters
    counter_handles = []
    for inst in instances:
        if "engtype_3D" in inst:
            counter_path = f"\\GPU Engine({inst})\\Utilization Percentage"
            #print(f"Adding counter: {counter_path}")
            h = ctypes.c_void_p()
            add_status = pdh.PdhAddEnglishCounterW(query_handle, counter_path, 0, ctypes.byref(h))
            if add_status == 0:
                counter_handles.append(h)
            else:
                print(f"Failed to add counter: {counter_path}, error: {add_status}")

    if not counter_handles:
        print("No usable 3D GPU counters found.")
        return 0.0

    # Sample twice
    pdh.PdhCollectQueryData(query_handle)
    time.sleep(0.1)
    pdh.PdhCollectQueryData(query_handle)

    total_usage = 0.0
    for h in counter_handles:
        val = PDH_FMT_COUNTERVALUE()
        status = pdh.PdhGetFormattedCounterValue(h, PDH_FMT_DOUBLE, None, ctypes.byref(val))
        if status == 0 and val.CStatus == 0:
            total_usage += val.doubleValue
        else:
            print(f"Failed to read counter: status={status}, CStatus={val.CStatus}")

    pdh.PdhCloseQuery(query_handle)

    return round(total_usage, 2)

# Example usage
usage = get_gpu_usage_engtype_3d()
print(f"GPU 3D Engine Utilization: {usage}%")

while True:
    usage = get_gpu_usage_engtype_3d()
    print(f"GPU 3D Engine Utilization: {usage}%")
    time.sleep(1)  # Adjust the sleep time as needed
