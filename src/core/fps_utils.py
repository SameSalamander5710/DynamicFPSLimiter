from core.lhm_loader import ensure_loaded, get_types
import os
from pathlib import Path
import dearpygui.dearpygui as dpg
import statistics
from collections import deque

class FPSUtils:
    def __init__(self, cm, lhm_sensor, logger=None, dpg=None, viewport_width=610, base_dir=None):
        self.cm = cm
        self.lhm_sensor = lhm_sensor
        self.logger = logger
        self.dpg = dpg or dpg  # fallback to global if not passed
        self.viewport_width = viewport_width
        self.last_fps_limits = []

        self.reset_summary_statistics()

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
        
    def evaluate_cap_change(self, gpu_values, cpu_values):
        """
        Returns a tuple (should_decrease, should_increase).
        Preserves existing semantics:
          - Legacy: decrease = (gpu_decrease OR cpu_decrease), increase = (gpu_increase AND cpu_increase)
          - LibreHM: decrease = any(enabled sensor value >= upper), increase = all(enabled sensor value <= lower)
        """
        monitoring_method = self.dpg.get_value("input_monitoring_method")
        cm = self.cm
        lhm_sensor = self.lhm_sensor

        # Legacy behavior: GPU/CPU thresholds and delays
        if monitoring_method == "Legacy":
            gpu_decrease_condition = (
                len(gpu_values) >= cm.delaybeforedecrease and
                all(value >= cm.gpucutofffordecrease for value in gpu_values[-cm.delaybeforedecrease:])
            )
            cpu_decrease_condition = (
                len(cpu_values) >= cm.delaybeforedecrease and
                all(value >= cm.cpucutofffordecrease for value in cpu_values[-cm.delaybeforedecrease:])
            )
            should_decrease = gpu_decrease_condition or cpu_decrease_condition

            gpu_increase_condition = (
                len(gpu_values) >= cm.delaybeforeincrease and
                all(value <= cm.gpucutoffforincrease for value in gpu_values[-cm.delaybeforeincrease:])
            )
            cpu_increase_condition = (
                len(cpu_values) >= cm.delaybeforeincrease and
                all(value <= cm.cpucutoffforincrease for value in cpu_values[-cm.delaybeforeincrease:])
            )
            should_increase = gpu_increase_condition and cpu_increase_condition

            return (should_decrease, should_increase)

        # LibreHM behavior: evaluate enabled sensors once and derive decrease/increase
        elif monitoring_method == "LibreHM":
            decrease_checks = []
            increase_checks = []
            lines = []
            sensor_infos = getattr(cm, "sensor_infos", []) or []

            if not sensor_infos:
                return (False, False)

            for sensor in sensor_infos:
                param_id = sensor.get("parameter_id")
                enable_tag = f"input_{param_id}_enable"
                upper_tag = f"input_{param_id}_upper"
                lower_tag = f"input_{param_id}_lower"

                if not param_id or not self.dpg.does_item_exist(enable_tag):
                    continue

                try:
                    if not self.dpg.get_value(enable_tag):
                        continue
                except Exception:
                    continue

                # read thresholds; if invalid, skip corresponding check
                upper = None
                lower = None
                try:
                    upper = float(self.dpg.get_value(upper_tag))
                except Exception:
                    pass
                try:
                    lower = float(self.dpg.get_value(lower_tag))
                except Exception:
                    pass

                sensor_type = sensor.get("sensor_type")
                sensor_name = sensor.get("sensor_name")
                hw_name = sensor.get("hw_name")
                hw_type = sensor.get("hw_type")
                value = None

                # CPU sensors use exact name keys in cpu_percentiles
                if hw_type == self.HardwareType.Cpu:
                    key = (sensor_type, sensor_name)
                    value = lhm_sensor.cpu_percentiles.get(key)
                    values_long = lhm_sensor.cpu_history_long.get(key, [])
                else:
                    sensor_name_indexed = sensor.get("sensor_name_indexed") or sensor_name
                    key = (sensor_type, sensor_name_indexed)
                    value = lhm_sensor.gpu_percentiles.get(key)
                    values_long = lhm_sensor.gpu_history_long.get(key, [])
                    if value is None:
                        if hasattr(lhm_sensor, "gpu_hw_names"):
                            try:
                                idx = lhm_sensor.gpu_hw_names.index(hw_name) + 1
                                key2 = (sensor_type, f"{idx} {sensor_name}")
                                value = lhm_sensor.gpu_percentiles.get(key2)
                                values_long = lhm_sensor.gpu_history_long.get(key2, [])
                            except ValueError:
                                value = None
                                values_long = []
                        if value is None:
                            for k, v in lhm_sensor.gpu_percentiles.items():
                                if k[0] == sensor_type and k[1].endswith(sensor_name):
                                    value = v
                                    break
                        
                        if not values_long:
                            for k, v in lhm_sensor.gpu_history_long.items():
                                if k[0] == sensor_type and k[1].endswith(sensor_name):
                                    values_long = v
                                    break

                # compute avg/std/median for this sensor
                try:
                    avg = statistics.mean(values_long)
                    std = statistics.stdev(values_long) if len(values_long) > 1 else 0.0
                    med = statistics.median(values_long)
                    lines.append(f"{hw_name}/{sensor_type}/{sensor_name}: avg={avg:.2f} std={std:.2f} med={med:.2f}")
                except Exception:
                    # skip sensors that fail stats computation
                    continue

                # Log once per sensor
                self.logger.add_log(f"LibreHM check {hw_name}/{sensor_type}/{sensor_name}: value={value} lower={lower} upper={upper}")

                if value is not None:
                    if upper is not None:
                        decrease_checks.append(value >= upper)
                    if lower is not None:
                        increase_checks.append(value <= lower)

            should_decrease = any(decrease_checks) if decrease_checks else False
            should_increase = all(increase_checks) if increase_checks else False

            summary_text = "\n".join(lines) if lines else "No enabled LibreHM sensors with data."
            try:
                dpg.set_value("SummaryText", summary_text)
            except Exception:
                pass

            return (should_decrease, should_increase)

    def update_summary_statistics(self):
        dpg = self.dpg
        lhm_sensor = self.lhm_sensor

        # Update duration. Format elapsed_time (seconds) as HH:MM:SS
        total_seconds = int(self.elapsed_time)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        dpg.set_value("summary_duration", f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        def compute_stats(values):
            if not values:
                return ("--", "--", "--", "--")

            avg = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            median = statistics.median(values)
            try:
                mode = statistics.mode(values)
            except statistics.StatisticsError:
                mode = "--"
            return (f"{avg:.2f}", f"{std_dev:.2f}", f"{median:.2f}", f"{mode:.2f}")

        # Compute for FPS and cap summaries
        fps_avg, fps_std, fps_med, fps_mode = compute_stats(self.summary_fps)
        cap_avg, cap_std, cap_med, cap_mode = compute_stats(self.summary_cap)

        # Write to DPG fields (tags defined in DFL_v5.py)
        try:
            dpg.set_value("summary_fps_avg", fps_avg)
            dpg.set_value("summary_fps_std", fps_std)
            dpg.set_value("summary_fps_median", fps_med)
            dpg.set_value("summary_fps_mode", fps_mode)

            dpg.set_value("summary_cap_avg", cap_avg)
            dpg.set_value("summary_cap_std", cap_std)
            dpg.set_value("summary_cap_median", cap_med)
            dpg.set_value("summary_cap_mode", cap_mode)

        except Exception:
            # silently ignore any GUI update errors
            pass

    def reset_summary_statistics(self):
        self.elapsed_time = 0.0
        self.summary_fps = []
        self.summary_cap = []

        self.lhm_sensor.cpu_history_long.clear()
        self.lhm_sensor.gpu_history_long.clear()