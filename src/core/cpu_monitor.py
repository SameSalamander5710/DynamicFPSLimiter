# cpu_monitor.py

import time
import threading
import psutil
import numpy as np
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
                        self.cpu_percentile = round(np.percentile(self.samples, self.percentile))

                            #self.logger.add_log(f"> CPU usage percentile: {self.cpu_percentile}%")
                except Exception as e:
                    self.logger.add_log(f"> CPU monitor error: {e}")
            
            time.sleep(self.interval)

    def stop(self):
        """Gracefully stop the background monitor thread."""
        self.looping = False
        if self._thread.is_alive():
            self._thread.join()
