# cpu_monitor.py

import time
import threading
import psutil
import numpy as np
import dearpygui.dearpygui as dpg

class CPUUsageMonitor:
    def __init__(self, logger_instance, dpg_instance, interval=0.1, max_samples=20, percentile=70):
        self.interval = interval
        self.max_samples = max_samples
        self.samples = []
        self.cpu_percentile = 0
        self._lock = threading.Lock()
        self.percentile = percentile
        self.logger = logger_instance
        self.dpg = dpg_instance
        self._running = True
        # Start background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        
        while self._running:  # Changed to always run
            try:
                if self.dpg.get_item_label("start_stop_button") == "Stop":  # Check if monitoring is active
                    self.core_usages = psutil.cpu_percent(percpu=True)
                    highest_usage = max(self.core_usages)
                    

                    with self._lock:
                        self.samples.append(highest_usage)
                        if len(self.samples) > self.max_samples:
                            self.samples.pop(0)
                        self.cpu_percentile = round(np.percentile(self.samples, self.percentile))

                    self.logger.add_log(f"> CPU usage: {highest_usage}% (highest core)")
            except Exception as e:
                self.logger.add_log(f"> CPU monitor error: {e}")
            
            time.sleep(self.interval)

    def stop(self):
        """Gracefully stop the background monitor thread."""
        self._running = False
        if self._thread.is_alive():
            self._thread.join()

if __name__ == "__main__":
    try:
        # Create monitor instance
        cpu_monitor = CPUUsageMonitor(logger_instance, dpg_instance, interval=0.1, max_samples=20, percentile=70)
        print("CPU Monitor started. Press Ctrl+C to stop.")
        
        # Monitor for 10 seconds
        for _ in range(10):
            #print(f"Per CPU core load: {cpu_monitor.core_usages}")
            #print(f"Last 20 samples: {cpu_monitor.samples}%")
            print(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nStopping CPU monitor...")
    finally:
        # Clean shutdown
        cpu_monitor.stop()
        print("Monitor stopped.")
