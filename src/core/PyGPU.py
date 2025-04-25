# PyGPU.py
# This Python module provides a fast and lightweight way to access GPU usage data on Windows by directly querying Performance Data Helper (PDH) counters for the "GPU Engine" object. 
# It bypasses slower or more resource-intensive methods like WMI or PowerShell.
# To-do: Change prints to runtime errors

import ctypes
import time
from collections import defaultdict
import re
from typing import Optional, Dict, List, Tuple

pdh = ctypes.windll.pdh

PDH_MORE_DATA = 0x800007D2
PDH_FMT_DOUBLE = 0x00000200

class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]

class GPUMonitor:
    """Class to monitor GPU usage through Windows PDH counters."""
    
    def __init__(self):
        """Initialize the GPU monitor."""
        self.query_handle = None
        self.counter_handles = {}
        self.instances = []  # Add this line
        self.initialize()

    def initialize(self) -> None:
        """Initialize PDH query."""
        self.query_handle = self._init_gpu_state()
        self.instances = self._setup_gpu_instances()  # Store instances
        self.query_handle, self.counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, "engtype_" 
        )

    def _init_gpu_state(self) -> ctypes.c_void_p:
        """Initialize PDH query and return the handle."""
        query_handle = ctypes.c_void_p()
        status = pdh.PdhOpenQueryW(None, 0, ctypes.byref(query_handle))
        
        if status != 0:
            raise RuntimeError(f"Failed to open PDH query. Error: {status}")
        
        return query_handle

    def _setup_gpu_instances(self) -> List[str]:
        """Set up GPU instances and return a list of them."""
        counter_buf_size = ctypes.c_ulong(0)
        instance_buf_size = ctypes.c_ulong(0)

        pdh.PdhEnumObjectItemsW(
            None, None, "GPU Engine",
            None, ctypes.byref(counter_buf_size),
            None, ctypes.byref(instance_buf_size),
            0, 0
        )

        counter_buf = (ctypes.c_wchar * counter_buf_size.value)()
        instance_buf = (ctypes.c_wchar * instance_buf_size.value)()

        ret = pdh.PdhEnumObjectItemsW(
            None, None, "GPU Engine",
            counter_buf, ctypes.byref(counter_buf_size),
            instance_buf, ctypes.byref(instance_buf_size),
            0, 0
        )

        if ret != 0:
            raise RuntimeError(f"Failed to enumerate GPU Engine instances. Error: {ret}")

        instances = list(filter(None, instance_buf[:].split('\x00')))
        if not instances:
            raise RuntimeError("No GPU engine instances found.")
            
        return instances

    def _setup_gpu_query_from_instances(
        self, 
        query_handle: ctypes.c_void_p, 
        instances: List[str], 
        engine_type: str = "engtype_"
    ) -> Tuple[ctypes.c_void_p, Dict]:
        """Set up GPU query and counters from instances."""
        counter_handles_by_luid = defaultdict(list)

        for inst in instances:
            if engine_type not in inst:
                continue

            match = re.search(r"luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)", inst)
            if not match:
                continue

            luid = match.group(1)
            counter_path = f"\\GPU Engine({inst})\\Utilization Percentage"
            counter_handle = ctypes.c_void_p()
            
            status = pdh.PdhAddEnglishCounterW(
                query_handle, 
                counter_path, 
                None, 
                ctypes.byref(counter_handle)
            )
            
            if status == 0:
                counter_handles_by_luid[luid].append(counter_handle)
            else:
                raise RuntimeError(f"Failed to add counter: {counter_path}, status={status}")

        return query_handle, dict(counter_handles_by_luid)

    def get_gpu_usage(self, target_luid: Optional[str] = None, engine_type: str = "engtype_") -> Tuple[int, str]:
        """
        Get GPU usage from the query handle and counter handles.
        
        Args:
            target_luid: Optional specific LUID to monitor
            engine_type: Type of GPU engine to monitor (e.g. "engtype_", "engtype_3D", "engtype_Copy")
            
        Returns:
            Tuple of (usage percentage, LUID)
        """
        if self.query_handle is None or not self.counter_handles:
            raise RuntimeError("Query handle or counter handles are not set up.")

        # Setup counters for the specified engine type
        _, self.counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, engine_type  # Use stored instances
        )

        pdh.PdhCollectQueryData(self.query_handle)
        time.sleep(0.1)
        pdh.PdhCollectQueryData(self.query_handle)

        usage_by_luid = {}
        handles_to_use = (
            {target_luid: self.counter_handles[target_luid]}
            if target_luid and target_luid in self.counter_handles
            else self.counter_handles
        )

        for luid, handles in handles_to_use.items():
            total = 0.0
            for h in handles:
                val = PDH_FMT_COUNTERVALUE()
                status = pdh.PdhGetFormattedCounterValue(h, PDH_FMT_DOUBLE, None, ctypes.byref(val))
                if status == 0 and val.CStatus == 0:
                    total += val.doubleValue
                else:
                    raise RuntimeError(f"Failed to read counter (LUID: {luid}): status={status}")
            usage_by_luid[luid] = total

        if not usage_by_luid:
            return 0, ""

        max_luid, max_usage = max(usage_by_luid.items(), key=lambda item: item[1])
        return int(max_usage), str(max_luid)

    def list_all_luids(self) -> List[str]:
        """
        List all available GPU LUIDs.
        
        Returns:
            List[str]: List of GPU LUIDs found in the system
        """
        if not self.counter_handles:
            raise RuntimeError("Counter handles are not set up.")
            
        return list(self.counter_handles.keys())

    def cleanup(self) -> None:
        """Clean up PDH query handle."""
        if self.query_handle:
            pdh.PdhCloseQuery(self.query_handle)
            self.query_handle = None

    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()


if __name__ == '__main__':
    # Example usage
    try:
        monitor = GPUMonitor()
        
        # List all GPU LUIDs
        print("Available GPU LUIDs:")
        for luid in monitor.list_all_luids():
            usage, _ = monitor.get_gpu_usage(luid)
            print(f"LUID: {luid}, Usage: {usage}%")
            
        # Get highest usage GPU
        usage, luid = monitor.get_gpu_usage(engine_type="engtype_3D")
        print(f"\nHighest GPU Usage - LUID: {luid}, 3D engine usage: {usage}%")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        monitor.cleanup()