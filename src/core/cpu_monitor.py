# cpu_monitor.py

import time
import threading
import psutil
import dearpygui.dearpygui as dpg

class CPUUsageMonitor:
    def __init__(self, get_running, logger_instance, dpg_instance, interval=0.1, max_samples=20, percentile=70):
        self.interval = interval
        self.max_samples = max_samples
        self.samples = []
        self.cpu_percentile = 0
        self._lock = threading.Lock()
        self.percentile = percentile
        self.logger = logger_instance
        self.dpg = dpg_instance
        self._running = get_running
        self.looping = True
        # Start background thread
        self._thread = threading.Thread(target=self.cpu_run, daemon=True)
        self._thread.start()

    def cpu_run(self):
        
        while self.looping:
            if self._running():
                try:
                    self.core_usages = psutil.cpu_percent(percpu=True)
                    highest_usage = max(self.core_usages)
                    

                    with self._lock:
                        self.samples.append(highest_usage)
                        if len(self.samples) > self.max_samples:
                            self.samples.pop(0)
                        self.cpu_percentile = round(CPUUsageMonitor.calculate_percentile(self.samples, self.percentile))
                        #self.logger.add_log(f"> CPU usage percentile: {self.cpu_percentile}%")
                except Exception as e:
                    self.logger.add_log(f"> CPU monitor error: {e}")
            
            time.sleep(self.interval)

    def stop(self):
        """Gracefully stop the background monitor thread."""
        self.looping = False
        if self._thread.is_alive():
            self._thread.join()

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