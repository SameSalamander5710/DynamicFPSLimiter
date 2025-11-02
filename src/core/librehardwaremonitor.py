from core.lhm_loader import ensure_loaded, get_types
from pathlib import Path
from collections import deque, defaultdict
import time
import threading
import numpy as np
import os
import sys

def get_selected_sensor_values(hardware, sensor_map):
    """Return a dict of selected sensor values for the given hardware, only for specified sensor types."""
    result = {}
    name_counts = {}  # Track counts for duplicate sensor names

    for sensor in hardware.Sensors:
        if sensor.Value is None:
            continue
        # Only process sensor types in sensor_map
        if sensor.SensorType not in sensor_map:
            continue

        wanted_names = sensor_map.get(sensor.SensorType)
        if wanted_names is None or sensor.Name in wanted_names:
            # Handle duplicate sensor names
            base_name = sensor.Name
            count = name_counts.get(base_name, 0)
            if count == 0:
                name = base_name
            else:
                name = f"{base_name} ({count})"
            name_counts[base_name] = count + 1

            result.setdefault(sensor.SensorType, {})[name] = sensor.Value
    return result

def get_all_sensor_infos(base_dir):

    try:
        Computer, SensorType, HardwareType = get_types(base_dir)
    except Exception:
        # fallback: call ensure_loaded explicitly
        Computer, SensorType, HardwareType = ensure_loaded(base_dir)

    sensors = []
    cpu_count = 0
    gpu_count = 0

    computer = Computer()

    computer.IsGpuEnabled = True
    computer.IsCpuEnabled = True
    computer.Open()

    for hw in computer.Hardware:
        hw.Update()
        if hw.HardwareType == HardwareType.Cpu:
            cpu_count += 1
            param_indices = {"Load": 0, "Power": 0, "Temperature": 0}
            for sensor in hw.Sensors:
                if sensor.SensorType in [SensorType.Load, SensorType.Power, SensorType.Temperature]:
                    sensor_type_str = sensor.SensorType.ToString() if hasattr(sensor.SensorType, "ToString") else str(sensor.SensorType)
                    param_indices[sensor_type_str] += 1
                    parameter_id = f"cpu{cpu_count}_{sensor_type_str.lower()}_{param_indices[sensor_type_str]:02d}"
                    hw_id = f"cpu{cpu_count}"
                    sensors.append({
                        "hw_type": hw.HardwareType,
                        "hw_name": hw.Name,
                        "sensor_type": sensor.SensorType,
                        "sensor_name": sensor.Name,
                        "sensor_name_indexed": sensor.Name,   # CPU not indexed
                        "parameter_id": parameter_id,
                        "hw_id": hw_id
                    })
        elif hw.HardwareType in (HardwareType.GpuAmd, HardwareType.GpuNvidia):
            gpu_count += 1
            param_indices = {"Load": 0, "Power": 0, "Temperature": 0}
            for sensor in hw.Sensors:
                if sensor.SensorType in [SensorType.Load, SensorType.Power, SensorType.Temperature]:
                    sensor_type_str = sensor.SensorType.ToString() if hasattr(sensor.SensorType, "ToString") else str(sensor.SensorType)
                    param_indices[sensor_type_str] += 1
                    parameter_id = f"gpu{gpu_count}_{sensor_type_str.lower()}_{param_indices[sensor_type_str]:02d}"
                    hw_id = f"gpu{gpu_count}"
                    # Build the indexed sensor name exactly as LHMSensor._poll_loop uses for gpu_percentiles keys
                    sensor_name_indexed = f"{gpu_count} {sensor.Name}"
                    sensors.append({
                        "hw_type": hw.HardwareType,
                        "hw_name": hw.Name,
                        "sensor_type": sensor.SensorType,
                        "sensor_name": sensor.Name,
                        "sensor_name_indexed": sensor_name_indexed,
                        "parameter_id": parameter_id,
                        "hw_id": hw_id
                    })
    return sensors

class LHMSensor:
    def __init__(self, get_running, logger_instance, dpg_instance, themes_instance, interval=0.1, max_samples=20, percentile=70, base_dir=None):
        self._running = get_running  # This should be a callable, e.g. lambda: running
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.themes = themes_instance
        self.interval = interval
        self.max_samples = max_samples
        self.percentile = percentile
        self.cpu_history = defaultdict(lambda: deque(maxlen=max_samples))
        self.gpu_history = defaultdict(lambda: deque(maxlen=max_samples))
        self.cpu_percentiles = defaultdict(float)
        self.gpu_percentiles = defaultdict(float)
        self._thread = None
        self._lock = threading.Lock()
        self._should_stop = threading.Event()

        # Ensure assembly loaded and types available
        Computer, SensorType, HardwareType = ensure_loaded(base_dir, self.logger)

        self.Computer = Computer
        self.SensorType = SensorType
        self.HardwareType = HardwareType

        # Initialize computer
        self.computer = Computer()
        self.computer.IsGpuEnabled = True
        self.computer.IsCpuEnabled = True
        self.computer.Open()


        # Define which sensors to extract for each hardware type and sensor type
        self.CPU_SENSORS = {
            SensorType.Load: None, #['CPU Total', 'CPU Core Max'],
            SensorType.Temperature: None, #['CPU Package'],
            SensorType.Power: None,  #['CPU Package'],
        }

        self.GPU_SENSORS = {
            SensorType.Load: None,  # None means all available
            SensorType.Temperature: None, #['GPU Core', 'GPU Hot Spot'],
            SensorType.Power: None, #['GPU Package'],
        }

        self.cpu_name = self.get_cpu_name()
        self.gpu_name = self.get_gpu_name()

    def get_cpu_name(self):
        for hw in self.computer.Hardware:
            if hw.HardwareType == self.HardwareType.Cpu:
                return hw.Name
        return None

    def get_gpu_name(self): #TODO Remove this if unused
        for hw in self.computer.Hardware:
            if hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                return hw.Name
        return None

    def get_gpu_names(self):
        """Return a list of all detected GPU names."""
        names = []
        for hw in self.computer.Hardware:
            if hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                names.append(hw.Name)
        return names

    def start(self):
    # Reset histories and percentiles
        with self._lock:
            self.cpu_history.clear()
            self.gpu_history.clear()
            self.cpu_percentiles.clear()
            self.gpu_percentiles.clear()
        if self._thread and self._thread.is_alive():
            return  # Already running
        self._should_stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._should_stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        self.computer.Close()
        self.logger.add_log("Stopped LibreHardwareMonitor polling.")

    def _poll_loop(self):
        def calculate_percentile(data, percentile):
            if not data:
                return None
            return float(np.percentile(data, percentile))

        self.cpu_percentiles = defaultdict(float)
        self.gpu_percentiles = defaultdict(float)

        while not self._should_stop.is_set() and self._running():
            gpu_index = 1
            for hw in self.computer.Hardware:
                # CPU logic unchanged
                if hw.Name == self.cpu_name and hw.HardwareType == self.HardwareType.Cpu:
                    hw.Update()
                    values = get_selected_sensor_values(hw, self.CPU_SENSORS)
                    with self._lock:
                        for sensor_type, sensors in values.items():
                            for name, value in sensors.items():
                                key = (sensor_type, name)
                                self.cpu_history[key].append(round(value, 2))
                                self.cpu_percentiles[key] = round(
                                    calculate_percentile(self.cpu_history[key], self.percentile), 2
                                )
                    cpu_hw_name = hw.Name  # Save for display
                # Loop through all GPUs
                elif hw.HardwareType in (self.HardwareType.GpuAmd, self.HardwareType.GpuNvidia):
                    hw.Update()
                    values = get_selected_sensor_values(hw, self.GPU_SENSORS)
                    with self._lock:
                        for sensor_type, sensors in values.items():
                            for name, value in sensors.items():
                                key = (sensor_type, f"{gpu_index} {name}")
                                self.gpu_history[key].append(round(value, 2))
                                self.gpu_percentiles[key] = round(
                                    calculate_percentile(self.gpu_history[key], self.percentile), 2
                                )
                    # Save GPU name for display
                    if not hasattr(self, 'gpu_hw_names'):
                        self.gpu_hw_names = []
                    if hw.Name not in self.gpu_hw_names:
                        self.gpu_hw_names.append(hw.Name)
                    gpu_index += 1

            # Update ReadingsText in the GUI
            cpu_str = self.format_history(self.cpu_history, self.cpu_percentiles, cpu_hw_name if 'cpu_hw_name' in locals() else "CPU")
            gpu_titles = self.gpu_hw_names if hasattr(self, 'gpu_hw_names') else ["GPU"]
            gpu_str = ""
            # Split GPU history by index for display
            for idx, gpu_name in enumerate(gpu_titles, start=1):
                gpu_str += self.format_history(
                    {k: v for k, v in self.gpu_history.items() if k[1].startswith(f"{idx} ")},
                    self.gpu_percentiles,
                    gpu_name
                ) + "\n\n"
            readings = cpu_str + "\n\n" + gpu_str
            try:
                self.dpg.set_value("ReadingsText", readings)
            except Exception as e:
                print("Failed to update ReadingsText:", e)
                self.logger.add_log(f"Failed to update ReadingsText: {e}")
            time.sleep(self.interval)

    def format_history(self, hist, percentiles, title):
        # Define column widths
        type_w = 12
        name_w = 26
        last_w = 8
        perc_w = 10
        header = f"{'Type':<{type_w}}| {'Name':<{name_w}}| {'Current':>{last_w}}| {'70th %ile':>{perc_w}}"
        lines = [f"{title}:"]
        lines.append(header)
        lines.append("-" * len(header))
        for (sensor_type, name), values in hist.items():
            sensor_type_str = getattr(sensor_type, 'name', str(sensor_type))
            last_val = values[-1] if values else 'N/A'
            percentile_val = percentiles.get((sensor_type, name), 'N/A')
            lines.append(
                f"{sensor_type_str:<{type_w}}| {name:<{name_w}}| {str(last_val):>{last_w}}| {str(percentile_val):>{perc_w}}"
            )
        return "\n".join(lines)

    def get_cpu_history(self):
        with self._lock:
            return dict(self.cpu_history)

    def get_gpu_history(self):
        with self._lock:
            return dict(self.gpu_history)

