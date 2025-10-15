# ===========================
#  Instructions for Adding Functions to config_manager_LHM.py
# ===========================
# 1. Any function defined in this file will be automatically attached as a method to the ConfigManager class.
# 2. Each function MUST accept 'self' as its first argument, so it works as a method of ConfigManager.
# 3. You can access all ConfigManager attributes and methods via 'self' inside your function.
# 4. Function names should be unique and descriptive.
# 5. Example function template:
#
#    def example_function(self, arg1, arg2):
#        # Access ConfigManager attributes
#        self.logger.add_log(f"Called example_function with {arg1}, {arg2}")
#        # Your logic here
#        return arg1 + arg2
#
# 6. After saving, you can call your function from any ConfigManager instance:
#        cm.example_function(1, 2)
#
# 7. You can use these functions to handle dynamic variables, settings, or any custom logic.
#
# ===========================

def update_dynamic_input_field_keys(self):
    """
    Adds all dynamic input field keys (from sensors and legacy/static UI) to self.input_field_keys.
    Uses parameter IDs from self.sensor_infos and known static keys, instead of scanning all DPG items.
    """
    # Static keys from legacy/static UI
    #TODO: remove these from the main config_manager.py
    static_keys = [
        "maxcap", "mincap", "capstep", "capratio",
        "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease",
        "capmethod", "customfpslimits", "delaybeforedecrease", "delaybeforeincrease",
        "monitoring_method", "load_gpucore_enable", "load_gpucore_lower", "load_gpucore_upper",
        "load_d3d3d_enable", "load_d3d3d_lower", "load_d3d3d_upper", "load_d3dcopy1_enable",
        "load_d3dcopy1_lower", "load_d3dcopy1_upper", "load_cputotal_enable", "load_cputotal_lower",
        "load_cputotal_upper", "load_cpucoremax_enable", "load_cpucoremax_lower", "load_cpucoremax_upper",
        "temp_gpuhotspot_enable", "temp_gpuhotspot_lower", "temp_gpuhotspot_upper", "temp_gpucore_enable",
        "temp_gpucore_lower", "temp_gpucore_upper", "temp_cpupackage_enable", "temp_cpupackage_lower",
        "temp_cpupackage_upper", "power_gpupackage_enable", "power_gpupackage_lower", "power_gpupackage_upper",
        "power_cpupackage_enable", "power_cpupackage_lower", "power_cpupackage_upper"
    ]

    # Dynamic keys from sensors (parameter_id for each sensor)
    dynamic_keys = []
    if hasattr(self, "sensor_infos"):
        for sensor in self.sensor_infos:
            param_id = sensor.get("parameter_id")
            if param_id:
                dynamic_keys.extend([
                    f"{param_id}_enable",
                    f"{param_id}_lower",
                    f"{param_id}_upper"
                ])

    # Combine and deduplicate
    all_keys = static_keys + dynamic_keys
    new_keys = [key for key in all_keys if key not in self.input_field_keys]
    if new_keys:
        self.input_field_keys.extend(new_keys)
        self.logger.add_log(f"Added dynamic input_field_keys: {new_keys}")

def update_dynamic_default_settings(self):
    """
    Adds default values for all dynamic input field keys (from sensors) to self.Default_settings_original.
    For each parameter_id, sets:
        - enable: False
        - lower: 0
        - upper: 100
    Does not overwrite existing keys.
    """
    if not hasattr(self, "sensor_infos"):
        return

    added_keys = []
    for sensor in self.sensor_infos:
        param_id = sensor.get("parameter_id")
        if param_id:
            for suffix, default_value in [("_enable", False), ("_lower", 0), ("_upper", 100)]:
                key = f"{param_id}{suffix}"
                if key not in self.Default_settings_original:
                    self.Default_settings_original[key] = default_value
                    added_keys.append(key)
    if added_keys:
        self.logger.add_log(f"Added dynamic default settings: {added_keys}")

def update_dynamic_key_type_map(self):
    """
    Adds type mappings for all dynamic input field keys (from sensors) to self.key_type_map.
    For each parameter_id, sets:
        - enable: bool
        - lower: int
        - upper: int
    Does not overwrite existing keys.
    """
    if not hasattr(self, "sensor_infos"):
        return

    added_keys = []
    for sensor in self.sensor_infos:
        param_id = sensor.get("parameter_id")
        if param_id:
            for suffix, typ in [("_enable", bool), ("_lower", int), ("_upper", int)]:
                key = f"{param_id}{suffix}"
                if key not in self.key_type_map:
                    self.key_type_map[key] = typ
                    added_keys.append(key)
    if added_keys:
        self.logger.add_log(f"Added dynamic key_type_map entries: {added_keys}")