# TODO: Change prints to runtime errors

import ctypes
import time
from collections import defaultdict
import re
from typing import Optional, Dict, List, Tuple
import threading

pdh = ctypes.windll.pdh

PDH_MORE_DATA = 0x800007D2
PDH_FMT_DOUBLE = 0x00000200

class PDH_FMT_COUNTERVALUE(ctypes.Structure):
    _fields_ = [("CStatus", ctypes.c_ulong), ("doubleValue", ctypes.c_double)]

class GPUUsageMonitor:
    def __init__(self, get_luid, get_running, logger_instance, dpg_instance, themes_instance, interval=0.1, max_samples=20, percentile=70):
        self.interval = interval
        self.max_samples = max_samples
        self.samples = []
        self.gpu_percentile = 0
        self.percentile = percentile
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.themes_manager = themes_instance
        self.query_handle = None
        self.counter_handles = {}
        self.instances = []  # Add this line
        self.initialize()
        self.get_luid = get_luid
        self.luid_selected = False
        self.luid = "All"

        # Start background thread
        self._running = get_running
        self.looping = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self.gpu_run, daemon=True)
        self._thread.start()
        self.logger.add_log(f"GPU monitoring started with interval: {round(self.interval*1000)} ms, max_samples: {self.max_samples}, percentile: {self.percentile}")

    def initialize(self) -> None:
        """Initialize PDH query."""
        self.query_handle = self._init_gpu_state()
        self.instances = self._setup_gpu_instances()  # Store instances
        self.query_handle, self.counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, "engtype_3D"
        )
        if self.query_handle is None:
            raise RuntimeError("Query handle not set up.")

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
        
        self.initialize()
        temp_counter_handles = {}
        # Setup counters for the specified engine type
        _, temp_counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, engine_type  # Use stored instances
        )

        pdh.PdhCollectQueryData(self.query_handle)
        time.sleep(0.1)
        pdh.PdhCollectQueryData(self.query_handle)

        usage_by_luid = {}
        handles_to_use = (
            {target_luid: temp_counter_handles[target_luid]}
            if target_luid and target_luid in temp_counter_handles
            else temp_counter_handles
        )

        for luid, handles in handles_to_use.items():
            total = 0.0
            for h in handles:
                val = PDH_FMT_COUNTERVALUE()
                status = pdh.PdhGetFormattedCounterValue(h, PDH_FMT_DOUBLE, None, ctypes.byref(val))
                if status == 0 and val.CStatus == 0:
                    total += val.doubleValue
                else:
                    raise RuntimeError(f"01_Failed to read counter (LUID: {luid}): status={status}")
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
        self.looping = False
        if self._thread.is_alive():
            self._thread.join()
        if self.query_handle:
            pdh.PdhCloseQuery(self.query_handle)
            self.query_handle = None

    def gpu_run(self, engine_type: str = "engtype_3D"):

        # Setup counters for the specified engine type
        _, self.counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, engine_type  # Use stored instances
        )

        pdh.PdhCollectQueryData(self.query_handle)
        
        while self.looping:
            time.sleep(self.interval)
            if self._running():
                try:
                    pdh.PdhCollectQueryData(self.query_handle)

                    usage_by_luid = {}
                    target_luid = self.get_luid()
                    handles_to_use = (
                        {target_luid: self.counter_handles[target_luid]}
                        if target_luid and target_luid in self.counter_handles
                        else self.counter_handles
                    )

                    for luid, handles in handles_to_use.items():
                        total = 0.0
                        #max_value = 0.0
                        for h in handles:
                            val = PDH_FMT_COUNTERVALUE()
                            status = pdh.PdhGetFormattedCounterValue(h, PDH_FMT_DOUBLE, None, ctypes.byref(val))
                            if status == 0 and val.CStatus == 0:
                                total += val.doubleValue
                                #max_value = max(max_value, val.doubleValue)
                            else:
                                self.logger.add_log(f"02_Failed to read counter (LUID: {luid}): status={status}")
                                self.reinitialize()
                        usage_by_luid[luid] = total #max_value or total

                    if not usage_by_luid:
                        return 0, ""

                    max_luid, max_usage = max(usage_by_luid.items(), key=lambda item: item[1])
                    #self.logger.add_log(f"target: {target_luid}, Current max LUID: {max_luid}, engine type: {engine_type}")
                    highest_usage = max_usage

                    with self._lock:
                        self.samples.append(highest_usage)
                        if len(self.samples) > self.max_samples:
                            self.samples.pop(0)
                        self.gpu_percentile = round(GPUUsageMonitor.calculate_percentile(self.samples, self.percentile))
                        #self.logger.add_log(f"GPU usage percentile: {self.gpu_percentile}%")

                except Exception as e:
                    self.logger.add_log(f"GPU monitor error: {e}")

    def toggle_luid_selection(self):
        """
        Toggle between tracking all GPUs and the most active LUID.
        Updates internal state and returns the new luid and selection state.
        """
        if not self.luid_selected:
            # First click: detect top LUID
            usage, luid = self.get_gpu_usage(engine_type="engtype_3D")
            if luid:
                self.logger.add_log(f"Tracking LUID: {luid} | Current 3D engine Utilization: {usage}%")
                self.dpg.configure_item("luid_button", label="Revert to all GPUs")
                self.dpg.bind_item_theme("luid_button", self.themes_manager.themes["revert_gpu_theme"])  # Apply blue theme
                self.luid = luid
                self.luid_selected = True
            else:
                self.logger.add_log("Failed to detect active LUID.")
        else:
            # Second click: deselect
            self.luid = "All"
            self.logger.add_log("Tracking all GPU engines.")
            self.dpg.configure_item("luid_button", label="Detect Render GPU")
            self.dpg.bind_item_theme("luid_button", self.themes_manager.themes["detect_gpu_theme"])  # Apply default grey theme
            self.luid_selected = False
        return self.luid, self.luid_selected

    def reinitialize(self, engine_type: str = "engtype_3D"):
        self.logger.add_log("Reinitializing GPU monitor.")
        self.initialize()

        temp_counter_handles = {}
        # Setup counters for the specified engine type
        _, temp_counter_handles = self._setup_gpu_query_from_instances(
            self.query_handle, self.instances, engine_type  # Use stored instances
        )

        pdh.PdhCollectQueryData(self.query_handle)
        time.sleep(0.1)
        pdh.PdhCollectQueryData(self.query_handle)

    def calculate_percentile(data: list, percentile: float) -> float:
        """
        Calculate the percentile of a list of numbers.

        Args:
            data (list): The list of numbers.
            percentile (float): The desired percentile (0-100).

        Returns:
            float: The value at the specified percentile.
        """
        if not data:
            raise ValueError("Data list is empty.")
        if not (0 <= percentile <= 100):
            raise ValueError("Percentile must be between 0 and 100.")

        # Sort the data
        sorted_data = sorted(data)

        # Calculate the index
        k = (len(sorted_data) - 1) * (percentile / 100.0)
        f = int(k)  # Floor index
        c = f + 1  # Ceiling index

        if c >= len(data):
            return data[f]

        # If the index is an integer, return the value at that index
        if f == k:
            return sorted_data[f]

        # Otherwise, interpolate between the two closest values
        return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])