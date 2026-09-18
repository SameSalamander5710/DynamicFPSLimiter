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
    def __init__(self, get_running, logger_instance, dpg_instance, themes_instance, gui_queue=None, interval=0.1, max_samples=20, percentile=70):
        self.interval = interval
        self.max_samples = max_samples
        self.samples = []
        self.gpu_percentile = 0
        self.percentile = percentile
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.themes_manager = themes_instance
        self.gui_queue = gui_queue
        self.query_handle = None
        self.counter_handles = {}
        self.instances = []  # Add this line
        # S2: serializes every Pdh* call on the shared query/counter handles. Re-entrant
        # because reinitialize() (called from inside a locked read section in gpu_run)
        # re-enters initialize()/_close_query() on the same thread.
        self._pdh_lock = threading.RLock()
        self._detecting = False  # S1: True while a LUID-detection worker is in flight
        self.initialize()
        self.luid_selected = False
        self.luid = "All"

        # Start background thread
        self._running = get_running
        self.looping = True
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self.gpu_run, daemon=True)
        self._thread.start()
        self.logger.add_log(f"GPU monitoring started with interval: {round(self.interval*1000)} ms, max_samples: {self.max_samples}, percentile: {self.percentile}")

    def _close_query(self) -> None:
        """Close the current PDH query (if any) and reset its state.

        Counter handles belong to the query, so they are invalidated and cleared
        when the query is closed. Serialized on self._pdh_lock so a close can never
        race an in-flight collect/read from another thread (S2).
        """
        with self._pdh_lock:
            if self.query_handle:
                pdh.PdhCloseQuery(self.query_handle)
                self.query_handle = None
                self.counter_handles = {}

    def initialize(self) -> None:
        """Initialize PDH query. Serialized on self._pdh_lock (S2)."""
        with self._pdh_lock:
            self._close_query()
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

        # Reuse the existing PDH query and counter handles instead of re-initializing
        # (F9 fix). This method runs on the LUID-detection worker thread (S1) while
        # gpu_run uses the same handles on the monitor thread; every Pdh* call on the
        # shared query is therefore serialized on self._pdh_lock (S2). Holding the lock
        # across the 0.1 s gap between the two collects means a monitor tick slips at
        # most one interval during a detection — an accepted trade-off (lessons.md S2).
        with self._pdh_lock:
            counter_handles = self.counter_handles

            pdh.PdhCollectQueryData(self.query_handle)
            time.sleep(0.1)
            pdh.PdhCollectQueryData(self.query_handle)

            usage_by_luid = {}
            handles_to_use = (
                {target_luid: counter_handles[target_luid]}
                if target_luid and target_luid in counter_handles
                else counter_handles
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
        with self._pdh_lock:
            if self.query_handle:
                pdh.PdhCloseQuery(self.query_handle)
                self.query_handle = None

    def gpu_run(self, engine_type: str = "engtype_3D"):

        # Setup counters for the specified engine type
        with self._pdh_lock:
            _, self.counter_handles = self._setup_gpu_query_from_instances(
                self.query_handle, self.instances, engine_type  # Use stored instances
            )

            pdh.PdhCollectQueryData(self.query_handle)

        while self.looping:
            time.sleep(self.interval)
            if self._running():
                try:
                    with self._pdh_lock:
                        pdh.PdhCollectQueryData(self.query_handle)

                        usage_by_luid = {}
                        with self._lock:
                            target_luid = self.luid
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

        Detection (a ~100 ms PDH double-collect) runs on a short-lived worker thread so
        the DPG callback thread is never blocked (lessons.md N3); state + UI updates are
        applied on the main thread via the GuiQueue (S1). A second click while a
        detection is in flight is ignored.
        """
        if not self.luid_selected:
            # First click: detect top LUID on a worker thread (S1).
            with self._lock:
                if self._detecting:
                    return self.luid, self.luid_selected
                self._detecting = True
            threading.Thread(target=self._detect_luid_worker, daemon=True).start()
        else:
            # Second click: deselect (cheap, no PDH work — safe inline).
            with self._lock:
                self.luid = "All"
            self.logger.add_log("Tracking all GPU 3D usages.")
            self._submit_dpg(self.dpg.configure_item, "luid_button", label="Detect Render GPU")
            self._submit_dpg(self.dpg.bind_item_theme, "luid_button", self.themes_manager.themes["detect_gpu_theme"])  # Apply default grey theme
            self.luid_selected = False
            self._submit_dpg(self.dpg.set_value, "luid_status_text", "Tracking all GPU 3D usages.")
        return self.luid, self.luid_selected

    def _detect_luid_worker(self):
        """Run the PDH LUID detection off the DPG callback thread (S1), then apply
        the state + UI updates on the main thread via the GuiQueue."""
        try:
            usage, luid = self.get_gpu_usage(engine_type="engtype_3D")
        except Exception as e:
            self.logger.add_log(f"LUID detection error: {e}")
            usage, luid = 0, ""

        def _apply():
            with self._lock:
                self._detecting = False
            if luid:
                self.logger.add_log(f"Tracking LUID: {luid} | Current 3D engine Utilization: {usage}%")
                self._submit_dpg(self.dpg.configure_item, "luid_button", label="Revert to all GPUs")
                self._submit_dpg(self.dpg.bind_item_theme, "luid_button", self.themes_manager.themes["revert_gpu_theme"])  # Apply blue theme
                with self._lock:
                    self.luid = luid
                self.luid_selected = True
                self._submit_dpg(self.dpg.set_value, "luid_status_text", f"Tracking LUID: {luid} ({usage}% 3D)")
            else:
                self.logger.add_log("Failed to detect active LUID.")
                self._submit_dpg(self.dpg.set_value, "luid_status_text", "Failed to detect active LUID.")

        self._submit_dpg(_apply)

    def _submit_dpg(self, fn, *args, **kwargs) -> None:
        """Route a ``dpg`` call through the GuiQueue so it runs on the main thread.

        Falls back to calling ``fn`` directly if no GuiQueue is configured (e.g. in
        tests that construct the monitor without one), preserving prior behavior.
        """
        if self.gui_queue is not None:
            self.gui_queue.submit(fn, *args, **kwargs)
        else:
            fn(*args, **kwargs)

    def reinitialize(self, engine_type: str = "engtype_3D"):
        self.logger.add_log("Reinitializing GPU monitor.")
        self.initialize()

        # Setup counters for the specified engine type
        with self._pdh_lock:
            _, self.counter_handles = self._setup_gpu_query_from_instances(
                self.query_handle, self.instances, engine_type  # Use stored instances
            )

            pdh.PdhCollectQueryData(self.query_handle)
            time.sleep(0.1)
            pdh.PdhCollectQueryData(self.query_handle)

    @staticmethod
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