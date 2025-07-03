import dearpygui.dearpygui as dpg

class FPSUtils:
    def __init__(self, cm, logger=None, dpg=None, viewport_width=610):
        self.cm = cm
        self.logger = logger
        self.dpg = dpg or dpg  # fallback to global if not passed
        self.viewport_width = viewport_width

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

    def update_fps_cap_visualization(self, last_fps_limits):
        dpg = self.dpg
        Viewport_width = self.viewport_width

        fps_limits = self.current_stepped_limits()
        if not fps_limits or len(fps_limits) < 2:
            return last_fps_limits

        if fps_limits == last_fps_limits:
            return last_fps_limits

        last_fps_limits = fps_limits.copy()
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
                    (x_pos, y_pos),  # Center point
                    7,  # Radius
                    #thickness=2,
                    #color=(128, 128, 128),  # Border color (grey)
                    fill=(200, 200, 200),  # Fill color (white)
                    parent="Foreground"
                )
                if len(fps_limits) < 20:
                    dpg.draw_text((x_pos - 10, y_pos + 8), 
                                  str(cap), 
                                  color=(200, 200, 200), 
                                  size=16, 
                                  parent="Foreground")
        return last_fps_limits

    def copy_from_plot(self):
        fps_limits = sorted(set(self.current_stepped_limits()))
        fps_limits_str = ", ".join(str(int(round(x))) for x in fps_limits)
        self.dpg.set_value("input_customfpslimits", fps_limits_str)

    def reset_custom_limits(self):
        lowerlimit = self.dpg.get_value("input_mincap")
        upperlimit = self.dpg.get_value("input_maxcap")
        self.dpg.set_value("input_customfpslimits", f"{lowerlimit}, {upperlimit}")