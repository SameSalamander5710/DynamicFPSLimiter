from core.lhm_loader import ensure_loaded, get_types
import os
from pathlib import Path
import dearpygui.dearpygui as dpg

class FPSUtils:
    def __init__(self, cm, lhm_sensor, logger=None, dpg=None, viewport_width=610, base_dir=None):
        self.cm = cm
        self.lhm_sensor = lhm_sensor
        self.logger = logger
        self.dpg = dpg or dpg  # fallback to global if not passed
        self.viewport_width = viewport_width
        self.last_fps_limits = []
        self.elapsed_time = 0.0
        self.summary_fps = []
        self.summary_cap = []

        # Ensure LHM assembly loaded and get types (pass Base_dir from caller)
        SensorType, HardwareType = None, None
        try:
            Computer, SensorType, HardwareType = get_types(base_dir)
        except Exception:
            # fallback: call ensure_loaded explicitly
            Computer, SensorType, HardwareType = ensure_loaded(base_dir)
        # store types if needed: self.SensorType = SensorType, etc.
        self.SensorType = SensorType
        self.HardwareType = HardwareType

    def current_stepped_limits(self):
        maximum = int(dpg.get_value("input_maxcap"))
        minimum = int(dpg.get_value("input_mincap"))
        step = int(dpg.get_value("input_capstep"))
        ratio = int(dpg.get_value("input_capratio"))
        use_custom = dpg.get_value("input_capmethod").lower()

        if use_custom == "custom":
            custom_limits = dpg.get_value("input_customfpslimits")
            if custom_limits and self.cm:
                try:
                    custom_limits = self.cm.parse_and_normalize_string_to_decimal_set(custom_limits)
                    return custom_limits
                except Exception as e:
                    if self.logger:
                        self.logger.add_log(f"Error parsing custom FPS limits: {e}")
        elif use_custom == "step":
            return self.make_stepped_values(maximum, minimum, step)
        elif use_custom == "ratio":
            return self.make_ratioed_values(maximum, minimum, ratio)

    def make_stepped_values(self, maximum, minimum, step):
        values = list(range(maximum, minimum - 1, -step))
        if minimum not in values:
            values.append(minimum)
        return sorted(set(values))

    def make_ratioed_values(self, maximum, minimum, ratio):
        values = []
        current = maximum
        ratio_factor = 1 - (ratio / 100.0)
        if ratio_factor <= 0 or ratio_factor >= 1:
            return sorted(set([maximum, minimum]))
        prev_diff = None
        values.append(int(round(current)))

        while current >= minimum:
            current = current * ratio_factor
            rounded_current = int(round(current))
            if len(values) >= 3:
                prev_diff = abs(values[-1] - values[-2])
            if prev_diff is not None and abs(rounded_current - values[-1]) > prev_diff:
                rounded_current = values[-1] - prev_diff

            # Duplicate detection and correction
            while rounded_current in values and rounded_current > minimum:
                rounded_current -= 1

            values.append(rounded_current)
            current = rounded_current

            if rounded_current <= minimum:
                break
        if minimum not in values:
            values.append(minimum)
        custom_limits = sorted(x for x in set(values) if x >= minimum)
        return custom_limits

    def update_fps_cap_visualization(self):
        dpg = self.dpg
        Viewport_width = self.viewport_width

        fps_limits = self.current_stepped_limits()
        if not fps_limits or len(fps_limits) < 2:
            return

        if fps_limits == self.last_fps_limits:
            return

        self.last_fps_limits = fps_limits.copy()
        dpg.delete_item("Foreground")
        with dpg.draw_layer(tag="Foreground", parent="fps_cap_drawlist"):
            draw_width = Viewport_width - 67
            layer2_height = 30
            margin = 10
            min_fps = min(fps_limits)
            max_fps = max(fps_limits)
            fps_range = max_fps - min_fps
            for cap in fps_limits:
                x_pos = margin + int((cap - min_fps) / fps_range * (draw_width - margin))
                y_pos = layer2_height // 2
                dpg.draw_circle(
                    (x_pos, y_pos),
                    7,
                    fill=(200, 200, 200),
                    parent="Foreground"
                )
                if len(fps_limits) < 20:
                    dpg.draw_text((x_pos - 10, y_pos + 8),
                                  str(cap),
                                  color=(200, 200, 200),
                                  size=16,
                                  parent="Foreground")

    def copy_from_plot(self):
        fps_limits = sorted(set(self.current_stepped_limits()))
        fps_limits_str = ", ".join(str(int(round(x))) for x in fps_limits)
        self.dpg.set_value("input_customfpslimits", fps_limits_str)

    def reset_custom_limits(self):
        lowerlimit = self.dpg.get_value("input_mincap")
        upperlimit = self.dpg.get_value("input_maxcap")
        self.dpg.set_value("input_customfpslimits", f"{lowerlimit}, {upperlimit}")

    def should_decrease_fps_cap(self, gpu_values, cpu_values):
        monitoring_method = self.dpg.get_value("input_monitoring_method")
        cm = self.cm
        lhm_sensor = self.lhm_sensor
        if monitoring_method == "Legacy":
            gpu_decrease_condition = (
                len(gpu_values) >= cm.delaybeforedecrease and
                all(value >= cm.gpucutofffordecrease for value in gpu_values[-cm.delaybeforedecrease:])
            )
            cpu_decrease_condition = (
                len(cpu_values) >= cm.delaybeforedecrease and
                all(value >= cm.cpucutofffordecrease for value in cpu_values[-cm.delaybeforedecrease:])
            )
            return gpu_decrease_condition or cpu_decrease_condition

        elif monitoring_method == "LibreHM":
            triggered = []
            # Prefer dynamic sensor list produced by librehardwaremonitor.get_all_sensor_infos()
            sensor_infos = getattr(cm, "sensor_infos", []) or []

            if sensor_infos:
                for sensor in sensor_infos:
                    param_id = sensor.get("parameter_id")
                    enable_tag = f"input_{param_id}_enable"
                    upper_tag = f"input_{param_id}_upper"

                    # Skip if UI element or sensor entry missing
                    if not param_id or not self.dpg.does_item_exist(enable_tag):
                        continue

                    try:
                        if not self.dpg.get_value(enable_tag):
                            continue
                    except Exception:
                        continue

                    try:
                        upper = float(self.dpg.get_value(upper_tag))
                    except Exception:
                        # invalid upper value -> skip
                        continue

                    sensor_type = sensor.get("sensor_type")
                    sensor_name = sensor.get("sensor_name")
                    hw_name = sensor.get("hw_name")
                    hw_type = sensor.get("hw_type")
                    value = None

                    # CPU sensors use exact name keys in cpu_percentiles
                    if hw_type == self.HardwareType.Cpu:
                        key = (sensor_type, sensor_name)
                        value = lhm_sensor.cpu_percentiles.get(key)
                    else:
                        # Prefer an indexed sensor name provided by get_all_sensor_infos()
                        sensor_name_indexed = sensor.get("sensor_name_indexed") or sensor_name
                        key = (sensor_type, sensor_name_indexed)
                        value = lhm_sensor.gpu_percentiles.get(key)
                        # If not found, fall back to the previous gpu_hw_names / suffix-matching logic
                        if value is None:
                            if hasattr(lhm_sensor, "gpu_hw_names"):
                                try:
                                    idx = lhm_sensor.gpu_hw_names.index(hw_name) + 1
                                    key2 = (sensor_type, f"{idx} {sensor_name}")
                                    value = lhm_sensor.gpu_percentiles.get(key2)
                                except ValueError:
                                    value = None
                            if value is None:
                                for k, v in lhm_sensor.gpu_percentiles.items():
                                    if k[0] == sensor_type and k[1].endswith(sensor_name):
                                        value = v
                                        break

                    self.logger.add_log(f"Checking LibreHM sensor {hw_name}/{sensor_name} against upper {upper}: {value}")
                    triggered.append(bool(value is not None and value >= upper))

                return any(triggered) if triggered else False

    def should_increase_fps_cap(self, gpu_values, cpu_values):
        monitoring_method = self.dpg.get_value("input_monitoring_method")
        cm = self.cm
        lhm_sensor = self.lhm_sensor
        if monitoring_method == "Legacy":
            gpu_increase_condition = (
                len(gpu_values) >= cm.delaybeforeincrease and
                all(value <= cm.gpucutoffforincrease for value in gpu_values[-cm.delaybeforeincrease:])
            )
            cpu_increase_condition = (
                len(cpu_values) >= cm.delaybeforeincrease and
                all(value <= cm.cpucutoffforincrease for value in cpu_values[-cm.delaybeforeincrease:])
            )
            return gpu_increase_condition and cpu_increase_condition

        elif monitoring_method == "LibreHM":
            results = []
            # Prefer dynamic sensor list produced by librehardwaremonitor.get_all_sensor_infos()
            sensor_infos = getattr(cm, "sensor_infos", []) or []

            if sensor_infos:
                for sensor in sensor_infos:
                    param_id = sensor.get("parameter_id")
                    enable_tag = f"input_{param_id}_enable"
                    lower_tag = f"input_{param_id}_lower"

                    # Skip if UI element or sensor entry missing
                    if not param_id or not self.dpg.does_item_exist(enable_tag):
                        continue

                    try:
                        if not self.dpg.get_value(enable_tag):
                            continue
                    except Exception:
                        continue

                    try:
                        lower = float(self.dpg.get_value(lower_tag))
                    except Exception:
                        # invalid lower value -> skip
                        continue

                    sensor_type = sensor.get("sensor_type")
                    sensor_name = sensor.get("sensor_name")
                    hw_name = sensor.get("hw_name")
                    hw_type = sensor.get("hw_type")
                    value = None

                    # CPU sensors use exact name keys in cpu_percentiles
                    if hw_type == self.HardwareType.Cpu:
                        key = (sensor_type, sensor_name)
                        value = lhm_sensor.cpu_percentiles.get(key)
                    else:
                        # Prefer an indexed sensor name provided by get_all_sensor_infos()
                        sensor_name_indexed = sensor.get("sensor_name_indexed") or sensor_name
                        key = (sensor_type, sensor_name_indexed)
                        value = lhm_sensor.gpu_percentiles.get(key)
                        # If not found, fall back to previous gpu_hw_names / suffix-matching logic
                        if value is None:
                            if hasattr(lhm_sensor, "gpu_hw_names"):
                                try:
                                    idx = lhm_sensor.gpu_hw_names.index(hw_name) + 1
                                    key2 = (sensor_type, f"{idx} {sensor_name}")
                                    value = lhm_sensor.gpu_percentiles.get(key2)
                                except ValueError:
                                    value = None
                            if value is None:
                                for k, v in lhm_sensor.gpu_percentiles.items():
                                    if k[0] == sensor_type and k[1].endswith(sensor_name):
                                        value = v
                                        break

                    self.logger.add_log(f"Checking LibreHM sensor {hw_name}/{sensor_name} against lower {lower}: {value}")
                    results.append(bool(value is not None and value <= lower))

                return all(results) if results else False
    
    def update_summary_statistics(self):
        dpg = self.dpg
        lhm_sensor = self.lhm_sensor

        # Update duration
        dpg.set_value("summary_duration", f"{self.elapsed_time:.2f}")



    def reset_summary_statistics(self):
        self.elapsed_time = 0.0
        self.summary_fps = []
        self.summary_cap = []