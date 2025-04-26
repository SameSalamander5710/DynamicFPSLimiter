# cpu_monitor.py

import time
import threading
import psutil
import numpy as np

class CPUUsageMonitor:
    def __init__(self, interval=0.1, max_samples=20, percentile=70):
        self.interval = interval
        self.max_samples = max_samples
        self.samples = []
        self.cpu_percentile = 0.0
        self._lock = threading.Lock()
        self._running = True
        self.percentile = percentile
        # Start background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while self._running:
            self.core_usages = psutil.cpu_percent(percpu=True)
            highest_usage = max(self.core_usages)
            
            with self._lock:
                self.samples.append(highest_usage)
                if len(self.samples) > self.max_samples:
                    self.samples.pop(0)
                self.cpu_percentile = round(np.percentile(self.samples, self.percentile))

            time.sleep(self.interval)

    def stop(self):
        """Gracefully stop the background monitor thread."""
        self._running = False
        self._thread.join()

    def get_percentile(self):
        """Thread-safe access to the latest 70th percentile."""
        with self._lock:
            return self.cpu_percentile

if __name__ == "__main__":
    try:
        # Create monitor instance
        cpu_monitor = CPUUsageMonitor(interval=0.1, max_samples=20, percentile=70)
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
