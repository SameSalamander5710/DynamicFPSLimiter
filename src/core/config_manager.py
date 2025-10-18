import os
import configparser
import dearpygui.dearpygui as dpg
from decimal import Decimal, InvalidOperation
from core.librehardwaremonitor import get_all_sensor_infos
import importlib.util
import inspect

class ConfigManager:
    def __init__(self, logger_instance, dpg_instance, rtss_instance, tray_instance, themes_manager, base_dir):
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.rtss = rtss_instance
        self.tray = tray_instance
        self.themes = themes_manager.themes
        self.config_dir = os.path.join(os.path.dirname(base_dir), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_path = os.path.join(self.config_dir, "settings.ini")
        self.profiles_path = os.path.join(self.config_dir, "profiles.ini")
        self.Default_settings_original = {
            "maxcap": 114,
            "mincap": 40,
            "capratio": 10,
            "capstep": 5,
            "gpucutofffordecrease": 85,
            "gpucutoffforincrease": 70,
            'cpucutofffordecrease': 105,
            'cpucutoffforincrease': 101,
            "delaybeforedecrease": 2,
            "delaybeforeincrease": 10,
            "capmethod": "ratio",
            "customfpslimits": '30.01, 45.00, 59.99',
            "monitoring_method": "librehm",
            "lhm_gpu_priority": 0,
            "load_gpucore_enable": True,
            "load_gpucore_lower": 75,
            "load_gpucore_upper": 90,
            "load_d3d3d_enable": True,
            "load_d3d3d_lower": 75,
            "load_d3d3d_upper": 90,
            "load_d3dcopy1_enable": False,
            "load_d3dcopy1_lower": 75,
            "load_d3dcopy1_upper": 90,
            "load_cputotal_enable": True,
            "load_cputotal_lower": 75,
            "load_cputotal_upper": 90,
            "load_cpucoremax_enable": True,
            "load_cpucoremax_lower": 75,
            "load_cpucoremax_upper": 90,
            "temp_gpuhotspot_enable": True,
            "temp_gpuhotspot_lower": 75,
            "temp_gpuhotspot_upper": 90,
            "temp_gpucore_enable": True,
            "temp_gpucore_lower": 75,
            "temp_gpucore_upper": 90,
            "temp_cpupackage_enable": True,
            "temp_cpupackage_lower": 75,
            "temp_cpupackage_upper": 90,
            "power_gpupackage_enable": True,
            "power_gpupackage_lower": 75,
            "power_gpupackage_upper": 90,
            "power_cpupackage_enable": True,
            "power_cpupackage_lower": 75,
            "power_cpupackage_upper": 90,
            "minvalidgpu": 14,
            "minvalidfps": 14,
            "globallimitonexit_fps": 98,
            'cpupercentile': 70,
            'cpupollinginterval': 100,
            'cpupollingsamples': 20,
            'gpupercentile': 70,
            'gpupollinginterval': 100,
            'gpupollingsamples': 20,
            'lhwmonitorpollinginterval': 100,
            'lhwmonitorpercentile': 70,
            'lhwmonitoringsamples': 20,
            'profileonstartup_name': 'Global',
        }
        self.settings_config = configparser.ConfigParser()
        self.profiles_config = configparser.ConfigParser()
        self.load_or_init_configs()
        self.load_preferences()
        self._attach_lhm_functions()
        self.sensor_infos = get_all_sensor_infos()

    def _attach_lhm_functions(self):
        """Dynamically import all functions from config_manager_LHM.py and attach them as methods."""
        lhm_path = os.path.join(os.path.dirname(__file__), "LHM_config", "config_manager_LHM.py")
        spec = importlib.util.spec_from_file_location("config_manager_LHM", lhm_path)
        lhm_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lhm_module)

        for name, func in inspect.getmembers(lhm_module, inspect.isfunction):
            # Attach as bound method to self
            setattr(self, name, func.__get__(self, self.__class__))

    def load_or_init_configs(self):
        # Settings
        if os.path.exists(self.settings_path):
            self.settings_config.read(self.settings_path)
        else:
            self.settings_config["Preferences"] = {
                'showtooltip': 'True',
                'globallimitonexit': 'False',
                'profileonstartup': 'True',
                'launchonstartup': 'False',
                'minimizeonstartup': 'False',
                'autopilot': 'False',
                'hide_unselected': 'False'
            }
            self.settings_config["GlobalSettings"] = {
                'minvalidgpu': '14',
                'minvalidfps': '14',
                'globallimitonexit_fps': '98',
                'cpupercentile': '70',
                'cpupollinginterval': '100',
                'cpupollingsamples': '20',
                'gpupercentile': '70',
                'gpupollinginterval': '100',
                'gpupollingsamples': '20',
                'lhwmonitorpercentile': '70',
                'lhwmonitorpollinginterval': '100',
                'lhwmonitoringsamples': '20',
                'profileonstartup_name': 'Global',
            }
            with open(self.settings_path, 'w') as f:
                self.settings_config.write(f)
        # Profiles
        if os.path.exists(self.profiles_path):
            self.profiles_config.read(self.profiles_path)
        else:
            self.profiles_config["Global"] = {
                'maxcap': '114',
                'mincap': '40',
                'capratio': '10',
                'capstep': '5',
                'gpucutofffordecrease': '85',
                'gpucutoffforincrease': '70',
                'cpucutofffordecrease': '105',
                'cpucutoffforincrease': '101',
                'delaybeforedecrease': '2',
                'delaybeforeincrease': '10',
                'capmethod': 'ratio',
                'customfpslimits': '30.01, 45.00, 59.99',
                'monitoring_method': 'librehm',
                'lhm_gpu_priority': '0',
                'load_gpucore_enable': 'True',
                'load_gpucore_lower': '75',
                'load_gpucore_upper': '90',
                'load_d3d3d_enable': 'True',
                'load_d3d3d_lower': '75',
                'load_d3d3d_upper': '90',
                'load_d3dcopy1_enable': 'False',
                'load_d3dcopy1_lower': '75',
                'load_d3dcopy1_upper': '90',
                'load_cputotal_enable': 'True',
                'load_cputotal_lower': '75',
                'load_cputotal_upper': '90',
                'load_cpucoremax_enable': 'True',
                'load_cpucoremax_lower': '75',
                'load_cpucoremax_upper': '90',
                'temp_gpuhotspot_enable': 'True',
                'temp_gpuhotspot_lower': '75',
                'temp_gpuhotspot_upper': '90',
                'temp_gpucore_enable': 'True',
                'temp_gpucore_lower': '75',
                'temp_gpucore_upper': '90',
                'temp_cpupackage_enable': 'True',
                'temp_cpupackage_lower': '75',
                'temp_cpupackage_upper': '90',
                'power_gpupackage_enable': 'True',
                'power_gpupackage_lower': '75',
                'power_gpupackage_upper': '90',
                'power_cpupackage_enable': 'True',
                'power_cpupackage_lower': '75',
                'power_cpupackage_upper': '90'
            }
            with open(self.profiles_path, 'w') as f:
                self.profiles_config.write(f)
        
        self.input_field_keys = ["maxcap", "mincap", "capstep", "capratio",
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

        self.input_button_tags = ["rest_fps_cap_button", "autofill_fps_caps", "quick_save", "quick_load", "Reset_Default", "SaveToProfile"]

        self.key_type_map = {
            "maxcap": int,
            "mincap": int,
            "capratio": int,
            "capstep": int,
            "gpucutofffordecrease": int,
            "gpucutoffforincrease": int,
            "cpucutofffordecrease": int,
            "cpucutoffforincrease": int,
            "capmethod": str,
            "customfpslimits": str,
            "monitoring_method": str,
            "lhm_gpu_priority": int,
            "load_gpucore_enable": bool,
            "load_gpucore_lower": int,
            "load_gpucore_upper": int,
            "load_d3d3d_enable": bool,
            "load_d3d3d_lower": int,
            "load_d3d3d_upper": int,
            "load_d3dcopy1_enable": bool,
            "load_d3dcopy1_lower": int,
            "load_d3dcopy1_upper": int,
            "load_cputotal_enable": bool,
            "load_cputotal_lower": int,
            "load_cputotal_upper": int,
            "load_cpucoremax_enable": bool,
            "load_cpucoremax_lower": int,
            "load_cpucoremax_upper": int,
            "temp_gpuhotspot_enable": bool,
            "temp_gpuhotspot_lower": int,
            "temp_gpuhotspot_upper": int,
            "temp_gpucore_enable": bool,
            "temp_gpucore_lower": int,
            "temp_gpucore_upper": int,
            "temp_cpupackage_enable": bool,
            "temp_cpupackage_lower": int,
            "temp_cpupackage_upper": int,
            "power_gpupackage_enable": bool,
            "power_gpupackage_lower": int,
            "power_gpupackage_upper": int,
            "power_cpupackage_enable": bool,
            "power_cpupackage_lower": int,
            "power_cpupackage_upper": int,
            "delaybeforedecrease": int,
            "delaybeforeincrease": int,
            "minvalidgpu": int,
            "minvalidfps": int,
            "globallimitonexit_fps": int,
            "cpupercentile": int,
            "cpupollinginterval": int,
            "cpupollingsamples": int,
            "gpupercentile": int,
            "gpupollinginterval": int,
            "gpupollingsamples": int,
            "lhwmonitorpollinginterval": int,
            "lhwmonitorpercentile": int,
            "lhwmonitoringsamples": int,
            'showtooltip': bool,
            'globallimitonexit': bool,
            'profileonstartup': bool,
            'profileonstartup_name': str,
            'launchonstartup': bool,
            'minimizeonstartup': bool,
            'autopilot': bool,
            'hide_unselected': bool
        }

        self.current_profile = "Global"
        self.Default_settings = {
            key: self.get_setting(key, self.key_type_map.get(key, int))
            for key in self.Default_settings_original
        }
        self.settings = self.Default_settings.copy()

    def load_preferences(self):
        for key in self.settings_config["Preferences"]:
            value = self.settings_config["Preferences"][key]
            value_type = self.key_type_map.get(key, str)
            if value_type is bool:
                value = str(value).strip().lower() == "true"
            else:
                value = value_type(value)
            setattr(self, key, value)

    def parse_input_value(self, key, value):
        value_type = self.key_type_map.get(key, int)
        try:
            if value_type is bool:
                # Accept bool, "True"/"False", 1/0, etc.
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.strip().lower() == "true"
                return bool(value)
            return value_type(value)
        except Exception:
            return value

    def parse_and_normalize_string_to_decimal_set(self, input_string):
        """Parse a comma-separated string into a set of unique Decimals normalized to max decimal places."""
        values = [x.strip() for x in input_string.split(',') if x.strip()]

        if not values:
            self.logger.add_log("Input string is empty or contains only whitespace.")
            return []

        try:
            decimal_set = {Decimal(x) for x in values}
        except InvalidOperation:
            self.logger.add_log("Invalid decimal in input string.")
            return []
        sorted_decimals = sorted(decimal_set)

        # Determine max number of decimal places   
        max_decimals = max(
            -d.normalize().as_tuple().exponent if d.normalize().as_tuple().exponent < 0 else 0
            for d in sorted_decimals
        )

        # Create the quantize pattern, e.g., Decimal('0.0001') for 4 decimal places
        quantize_pattern = Decimal(f"1.{'0' * max_decimals}") if max_decimals > 0 else Decimal("1")
        
        normalized_list = sorted({d.quantize(quantize_pattern) for d in sorted_decimals})
        return normalized_list

    def parse_decimal_set_to_string(self, decimal_set):
        original_string = ', '.join(str(d) for d in decimal_set)
        return  original_string

    def sort_customfpslimits_callback(self, sender, app_data, user_data):
        value = self.dpg.get_value("input_customfpslimits")
        try:
            sorted_limits = self.parse_and_normalize_string_to_decimal_set(value)
            sorted_str = ", ".join(str(x) for x in sorted_limits)
            self.dpg.set_value("input_customfpslimits", sorted_str)
        except Exception:
            pass

    # Function to get values with correct types
    def get_setting(self, key, value_type=None):
        """Get setting from appropriate config section based on key type."""
        if value_type is None:
            value_type = self.key_type_map.get(key, str)
        # Get the raw value from the appropriate config section
        if key in self.settings_config["GlobalSettings"]:
            raw_value = self.settings_config["GlobalSettings"].get(key, self.Default_settings_original[key])
        else:
            raw_value = self.profiles_config["Global"].get(key, self.Default_settings_original[key])

        # Convert to the correct type
        if value_type is set:
            try:
                values = []
                for x in str(raw_value).split(","):
                    x = x.strip()
                    if x.isdigit():
                        values.append(int(x))
                    else:
                        self.logger.add_log(f"Warning: Skipped non-integer value '{x}' in key '{key}'")
                return set(values)
            except Exception:
                self.logger.add_log(f"Error parsing set for key '{key}', using default.")
                values = []
                for x in str(self.Default_settings_original[key]).split(","):
                    x = x.strip()
                    if x.isdigit():
                        values.append(int(x))
                return set(values)

        # Robust boolean parsing
        if value_type is bool:
            if isinstance(raw_value, bool):
                return raw_value
            if isinstance(raw_value, str):
                return raw_value.strip().lower() == "true"
            if isinstance(raw_value, int):
                return raw_value != 0
            return bool(raw_value)

        try:
            return value_type(raw_value)
        except Exception:
            try:
                return value_type(self.Default_settings_original[key])
            except Exception:
                return self.Default_settings_original[key]
            
    def save_to_profile(self):
        selected_profile = dpg.get_value("profile_dropdown")

        if selected_profile:
            # Update profile-specific settings
            for key in self.input_field_keys:
                value = dpg.get_value(f"input_{key}")
                parsed_value = self.parse_input_value(key, value)
                # Store as string for config file
                self.profiles_config[selected_profile][key] = str(parsed_value)
            
            with open(self.profiles_path, "w") as configfile:
                self.profiles_config.write(configfile)

            self.logger.add_log(f"Settings saved to profile: {selected_profile}")
    
    def update_profile_dropdown(self, select_first=False):
        profiles = self.profiles_config.sections()
        dpg.configure_item("profile_dropdown", items=profiles)

        if select_first and profiles:
            dpg.set_value("profile_dropdown", profiles[0])  # Set combo selection

        current_profile = dpg.get_value("profile_dropdown")
        dpg.set_value("game_name", current_profile)

    def load_profile_callback(self, sender, app_data, user_data):
        
        self.current_profile = app_data
        profile_name = app_data

        if profile_name not in self.profiles_config:
            return
        for key in self.input_field_keys:
            value = self.profiles_config[profile_name].get(key, self.Default_settings_original[key])
            parsed_value = self.parse_input_value(key, value)
            dpg.set_value(f"input_{key}", parsed_value)
        self.update_global_variables()
        dpg.set_value("new_profile_input", "")
        dpg.set_value("game_name", profile_name)

        # Set GPU dropdown based on lhm_gpu_priority
        gpu_names = dpg.get_item_configuration("gpu_dropdown").get("items", [])
        idx = int(self.profiles_config[profile_name].get("lhm_gpu_priority", 0))
        if gpu_names and idx < len(gpu_names):
            dpg.set_value("gpu_dropdown", gpu_names[idx])
        #dpg.configure_item("game_name", label=profile_name)
        self.refresh_ui_callbacks()

    def save_profile(self, profile_name):
        self.profiles_config[profile_name] = {}
        # Save input fields
        for key in self.input_field_keys:
            value = dpg.get_value(f"input_{key}")
            parsed_value = self.parse_input_value(key, value)
            self.profiles_config[profile_name][key] = str(parsed_value)
        with open(self.profiles_path, 'w') as f:
            self.profiles_config.write(f)
        self.update_profile_dropdown()
        dpg.set_value("profile_dropdown", profile_name)
        self.load_profile_callback(None, profile_name, None)

    def add_new_profile_callback(self):
        new_name = dpg.get_value("new_profile_input")
        if new_name and new_name not in self.profiles_config:
            self.save_profile(new_name)
            dpg.set_value("new_profile_input", "")
            self.logger.add_log(f"New profile created: {new_name}")
        else:
            self.logger.add_log("Profile name is empty or already exists.")

    def add_process_profile_callback(self):
        new_name = dpg.get_value("LastProcess")
        if new_name and new_name not in self.profiles_config:
            self.save_profile(new_name)
            self.logger.add_log(f"New profile created: {new_name}")
        else:
            self.logger.add_log("Profile name is empty or already exists.")

    def delete_selected_profile_callback(self):
        
        profile_to_delete = dpg.get_value("profile_dropdown")
        if profile_to_delete == "Global":
            self.logger.add_log("Cannot delete the default 'Global' profile.")
            return
        if profile_to_delete in self.profiles_config:
            self.profiles_config.remove_section(profile_to_delete)
            self.rtss.delete_profile(profile_to_delete)
            with open(self.profiles_path, 'w') as f:
                self.profiles_config.write(f)
            self.update_profile_dropdown(select_first=True)

            # Reset input fields to the "Global" profile values
            if "Global" in self.profiles_config:
                for key in self.profiles_config["Global"]:
                    try:
                        value = self.profiles_config["Global"][key]
                        parsed_value = self.parse_input_value(key, value)
                        dpg.set_value(f"input_{key}", parsed_value)
                    except Exception as e:
                        self.logger.add_log(f"Error: Unable to convert value for key '{key}': {e}")
                self.update_global_variables()  # Ensure global variables are updated
            else:
                self.logger.add_log("Error: 'Global' profile not found in configuration.")

            self.logger.add_log(f"Deleted profile: {profile_to_delete}")
            self.current_profile = "Global"
        self.refresh_ui_callbacks()

    # Function to sync settings with variables
    def update_global_variables(self):
        for key, value in self.settings.items():
            #value_type = self.key_type_map.get(key, type(value))
            if str(value).isdigit():
                #globals()[key] = int(value)
                setattr(self, key, int(value))
            else:
                #globals()[key] = value
                setattr(self, key, value)

    # Read values from UI input fields without modifying `settings`
    def apply_current_input_values(self):
        for key in self.input_field_keys:
            value = dpg.get_value(f"input_{key}")
            #globals()[key] = self.parse_input_value(key, value)
            setattr(self, key, self.parse_input_value(key, value))

    def quick_save_settings(self):
        for key in self.input_field_keys:
            value = dpg.get_value(f"input_{key}")
            self.settings[key] = self.parse_input_value(key, value)
        self.update_global_variables()
        self.logger.add_log("Settings quick saved")

    def quick_load_settings(self):
        for key in self.input_field_keys:
            value = self.settings[key]
            parsed_value = self.parse_input_value(key, value)
            dpg.set_value(f"input_{key}", parsed_value)
        self.update_global_variables()
        self.logger.add_log("Settings quick loaded")
        self.refresh_ui_callbacks()

    def reset_to_program_default(self):
        for key in self.input_field_keys:
            value = self.Default_settings_original[key]
            parsed_value = self.parse_input_value(key, value)
            dpg.set_value(f"input_{key}", parsed_value)
        self.refresh_ui_callbacks()
        self.logger.add_log("Settings reset to program default")

    def startup_profile_selection(self):

        profile_name = self.settings_config["GlobalSettings"].get("profileonstartup_name", "Global")
        if self.profileonstartup:
            if profile_name in self.profiles_config:
                dpg.set_value("profile_dropdown", profile_name)
                self.load_profile_callback(None, profile_name, None)
            else:
                self.logger.add_log(f"Profile '{profile_name}' not found. Defaulting to 'Global'.")
                dpg.set_value("profile_dropdown", "Global")
                self.load_profile_callback(None, "Global", None)

    def current_method_callback(self, sender=None, app_data=None, user_data=None):

        method = app_data.lower() if app_data else dpg.get_value("input_capmethod").lower()

        dpg.bind_item_theme("input_capratio", self.themes["enabled_text_theme"] if method == "ratio" else self.themes["disabled_text_theme"])
        dpg.bind_item_theme("label_capratio", self.themes["enabled_text_theme"] if method == "ratio" else self.themes["disabled_text_theme"])
        dpg.bind_item_theme("label_capstep", self.themes["enabled_text_theme"] if method == "step" else self.themes["disabled_text_theme"])
        dpg.bind_item_theme("input_capstep", self.themes["enabled_text_theme"] if method == "step" else self.themes["disabled_text_theme"])
        dpg.bind_item_theme("input_customfpslimits", self.themes["enabled_text_theme"] if method == "custom" else self.themes["disabled_text_theme"])
        dpg.bind_item_theme("label_maxcap", self.themes["disabled_text_theme"] if method == "custom" else self.themes["enabled_text_theme"])
        dpg.bind_item_theme("label_mincap", self.themes["disabled_text_theme"] if method == "custom" else self.themes["enabled_text_theme"])
        dpg.bind_item_theme("input_maxcap", self.themes["disabled_text_theme"] if method == "custom" else self.themes["enabled_text_theme"])
        dpg.bind_item_theme("input_mincap", self.themes["disabled_text_theme"] if method == "custom" else self.themes["enabled_text_theme"])

        if self.tray:
            self.tray.update_hover_text() #Add  max_fps if easy
            
            # self.tray.update_hover_text(self.tray.app_name, profile_name, method, self.tray.running)

        self.logger.add_log(f"Method selection changed: {method}")

    def monitoring_method_callback(self, sender=None, app_data=None, user_data=None):
        # app_data is the selected value

        app_data = app_data.lower() if app_data else dpg.get_value("input_monitoring_method").lower()

        if app_data == "librehm":
            self.dpg.configure_item("LHwM_childwindow", show=True)
            self.dpg.configure_item("legacy_childwindow", show=False)
        else:
            self.dpg.configure_item("LHwM_childwindow", show=False)
            self.dpg.configure_item("legacy_childwindow", show=True)

        self.logger.add_log(f"Method selection changed: {app_data}")

    def hide_unselected_callback(self, sender=None, app_data=None, user_data=None):
        """
        When 'Hide unselected' is toggled, save preference and hide/show LibreHM parameter rows
        unless the parameter's enable checkbox is True.
        """
        # Persist preference using existing helper so behaviour matches other preference callbacks
        self.update_preference_setting('hide_unselected', sender, app_data, user_data)

        # Resolve boolean value (fallback to the checkbox value if app_data is None)
        try:
            hide = bool(app_data) if app_data is not None else bool(self.dpg.get_value("hide_unselected_checkbox"))
        except Exception:
            hide = False

        # Iterate sensor infos created for the LibreHM UI and hide/show rows
        for sensor in self.sensor_infos:
            param_id = sensor.get('parameter_id')
            if not param_id:
                continue
            enable_tag = f"input_{param_id}_enable"
            try:
                enabled = bool(self.dpg.get_value(enable_tag))
            except Exception:
                enabled = True
            row_tag = f"param_row_{param_id}"

            if self.dpg.does_item_exist(row_tag):
                # show full row only if we're not hiding, or the parameter is enabled
                self.dpg.configure_item(row_tag, show=(not hide) or enabled)

    def refresh_ui_callbacks(self, sender=None, app_data=None, user_data=None):
        """
        Centralized place to run common UI update callbacks.
        Call this whenever you need to run all UI-refresh callbacks (method, monitoring, hide_unselected).
        """
        # call each callback but protect against exceptions so one failing callback doesn't stop others
        try:
            self.current_method_callback(sender, app_data, user_data)
        except Exception as e:
            self.logger.add_log(f"Error in current_method_callback: {e}")
        try:
            self.monitoring_method_callback(sender, app_data, user_data)
        except Exception as e:
            self.logger.add_log(f"Error in monitoring_method_callback: {e}")
        try:
            self.hide_unselected_callback(sender, app_data, user_data)
        except Exception as e:
            self.logger.add_log(f"Error in hide_unselected_callback: {e}")

    def gpu_dropdown_callback(self, sender, app_data, user_data):
        gpu_names = self.dpg.get_item_configuration(sender).get("items", [])
        if app_data in gpu_names:
            idx = gpu_names.index(app_data)
            self.lhm_gpu_priority = idx
            # Save to current profile in profiles_config
            profile = self.current_profile
            self.profiles_config[profile]["lhm_gpu_priority"] = str(idx)
            with open(self.profiles_path, 'w') as f:
                self.profiles_config.write(f)
            self.logger.add_log(f"Selected GPU index set to {idx} ({app_data}) for profile {profile}")

    def update_preference_setting(self, key, sender, app_data, user_data):
        """
        Generic method to update a boolean preference setting.
        key: The attribute and config key to update (e.g., 'launchonstartup').
        """
        setattr(self, key, app_data)
        self.settings_config["Preferences"][key] = str(app_data)
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"{key.replace('_', ' ').title()} set to: {getattr(self, key)}")

    def make_update_preference_callback(self, key):
        def callback(sender, app_data, user_data):
            self.update_preference_setting(key, sender, app_data, user_data)
        return callback

    def update_exit_fps_value(self, sender, app_data, user_data):

        new_value = app_data

        if isinstance(new_value, int) and new_value > 0:
            self.globallimitonexit_fps = new_value
            self.settings_config["GlobalSettings"]["globallimitonexit_fps"] = str(new_value)
            with open(self.settings_path, 'w') as f:
                self.settings_config.write(f)
            self.logger.add_log(f"Global Limit on Exit FPS value set to: {self.globallimitonexit_fps}")
        else:
            self.logger.add_log(f"Invalid value entered for Global Limit on Exit FPS: {app_data}. Reverting.")
            dpg.set_value(sender, self.globallimitonexit_fps)

    def select_default_profile_callback(self, sender, app_data, user_data):

        current_profile = dpg.get_value("profile_dropdown")
        dpg.set_value("profileonstartup_name", current_profile)
        self.settings_config["GlobalSettings"]["profileonstartup_name"] = current_profile
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"Profile on Startup set to: {self.profileonstartup_name}")