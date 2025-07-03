import dearpygui.dearpygui as dpg

class FPSUtils:
    def __init__(self, cm, logger=None):
        self.cm = cm
        self.logger = logger

    def current_stepped_limits(self):
        maximum = int(dpg.get_value("input_maxcap"))
        minimum = int(dpg.get_value("input_mincap"))
        step = int(dpg.get_value("input_capstep"))
        ratio = int(dpg.get_value("input_capratio"))
        use_custom = dpg.get_value("input_capmethod")

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