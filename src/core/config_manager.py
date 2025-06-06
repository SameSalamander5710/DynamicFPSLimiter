import os
import configparser
import dearpygui.dearpygui as dpg

class ConfigManager:
    def __init__(self, logger_instance, dpg_instance, rtss_instance, base_dir):
        self.logger = logger_instance
        self.dpg = dpg_instance
        self.rtss = rtss_instance
        self.config_dir = os.path.join(os.path.dirname(base_dir), "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_path = os.path.join(self.config_dir, "settings.ini")
        self.profiles_path = os.path.join(self.config_dir, "profiles.ini")
        self.Default_settings_original = {
            "maxcap": 60,
            "mincap": 30,
            "capratio": 15,
            "capstep": 5,
            "gpucutofffordecrease": 85,
            "gpucutoffforincrease": 65,
            'cpucutofffordecrease': 95,
            'cpucutoffforincrease': 85,
            "delaybeforedecrease": 2,
            "delaybeforeincrease": 3,
            "capmethod": "ratio",
            "customfpslimits": {30, 60},
            "minvalidgpu": 14,
            "minvalidfps": 14,
            "globallimitonexit_fps": 98,
            'cpupercentile': 70,
            'cpupollinginterval': 100,
            'cpupollingsamples': 20,
            'gpupercentile': 70,
            'gpupollinginterval': 100,
            'gpupollingsamples': 20,
            'profileonstartup_name': 'Global',
        }
        self.settings_config = configparser.ConfigParser()
        self.profiles_config = configparser.ConfigParser()
        self.load_or_init_configs()


    def load_or_init_configs(self):
        # Settings
        if os.path.exists(self.settings_path):
            self.settings_config.read(self.settings_path)
        else:
            self.settings_config["Preferences"] = {
                'ShowTooltip': 'True',
                'globallimitonexit': 'False',
                'profileonstartup': 'True',
                'launchonstartup': 'False',
            }
            self.settings_config["GlobalSettings"] = {
                'delaybeforedecrease': '2',
                'delaybeforeincrease': '3',
                'minvalidgpu': '14',
                'minvalidfps': '14',
                'globallimitonexit_fps': '98',
                'cpupercentile': '70',
                'cpupollinginterval': '100',
                'cpupollingsamples': '20',
                'gpupercentile': '70',
                'gpupollinginterval': '100',
                'gpupollingsamples': '20',
                'profileonstartup_name': 'Global',
            }
            with open(self.settings_path, 'w') as f:
                self.settings_config.write(f)
        # Profiles
        if os.path.exists(self.profiles_path):
            self.profiles_config.read(self.profiles_path)
        else:
            self.profiles_config["Global"] = {
                'maxcap': '60',
                'mincap': '30',
                'capratio': '15',
                'capstep': '5',
                'gpucutofffordecrease': '85',
                'gpucutoffforincrease': '65',
                'cpucutofffordecrease': '95',
                'cpucutoffforincrease': '85',
                'capmethod': 'ratio',
                'customfpslimits': '30, 60',
            }
            with open(self.profiles_path, 'w') as f:
                self.profiles_config.write(f)
        
        self.input_field_keys = ["maxcap", "mincap", "capstep", "capratio",
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease",
                "capmethod", "customfpslimits"]

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
            "customfpslimits": set,
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
            'ShowTooltip': bool,
            'globallimitonexit': bool,
            'profileonstartup': bool,
            'profileonstartup_name': str,
            'launchonstartup': bool,
        }

        self.current_profile = "Global"
        self.Default_settings = {
            key: self.get_setting(key, self.key_type_map.get(key, int))
            for key in self.Default_settings_original
        }
        self.settings = self.Default_settings.copy()


    def parse_input_value(self, key, value):
        value_type = self.key_type_map.get(key, int)
        if value_type is set:
            if isinstance(value, set):
                return value
            # Remove curly braces if present
            if isinstance(value, str):
                value = value.strip()
                if value.startswith("{") and value.endswith("}"):
                    value = value[1:-1]
            try:
                return set(int(x.strip()) for x in str(value).split(",") if x.strip().isdigit())
            except Exception:
                return set()
        else:
            try:
                return value_type(value)
            except Exception:
                return value

    def format_output_value(self, key, value):
        value_type = self.key_type_map.get(key, int)
        if value_type is set:
            if isinstance(value, set):
                return ", ".join(str(x) for x in sorted(value))
            return str(value)
        return value

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
                self.profiles_config[selected_profile][key] = str(self.format_output_value(key, parsed_value))
            
            with open(self.profiles_path, "w") as configfile:
                self.profiles_config.write(configfile)

            self.logger.add_log(f"Settings saved to profile: {selected_profile}")
    
    def update_profile_dropdown(self, select_first=False):
        profiles = self.profiles_config.sections()
        dpg.configure_item("profile_dropdown", items=profiles)

        if select_first and profiles:
            dpg.set_value("profile_dropdown", profiles[0])  # Set combo selection
    
    def load_profile_callback(self, sender, app_data, user_data):
        
        self.current_profile = app_data
        profile_name = app_data

        if profile_name not in self.profiles_config:
            return
        for key in self.input_field_keys:
            value = self.profiles_config[profile_name].get(key, self.Default_settings_original[key])
            parsed_value = self.parse_input_value(key, value)
            dpg.set_value(f"input_{key}", self.format_output_value(key, parsed_value))
        self.update_global_variables()
        dpg.set_value("new_profile_input", "")

    def save_profile(self, profile_name):
        self.profiles_config[profile_name] = {}
        # Save input fields
        for key in self.input_field_keys:
            value = dpg.get_value(f"input_{key}")
            parsed_value = self.parse_input_value(key, value)
            self.profiles_config[profile_name][key] = str(self.format_output_value(key, parsed_value))
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
                        dpg.set_value(f"input_{key}", self.format_output_value(key, parsed_value))
                    except Exception as e:
                        self.logger.add_log(f"Error: Unable to convert value for key '{key}': {e}")
                self.update_global_variables()  # Ensure global variables are updated
            else:
                self.logger.add_log("Error: 'Global' profile not found in configuration.")

            self.logger.add_log(f"Deleted profile: {profile_to_delete}")
            self.current_profile = "Global"

    # Function to sync settings with variables
    def update_global_variables(self):
        for key, value in self.settings.items():
            value_type = self.key_type_map.get(key, type(value))
            if value_type is set:
                # If value is a string, parse it to a set of ints
                if isinstance(value, set):
                    #globals()[key] = value
                    setattr(self, key, value)
                else:
                    try:
                        values = [int(x.strip()) for x in str(value).split(",") if x.strip().isdigit()]
                        #globals()[key] = set(values)
                        setattr(self, key, set(values))
                    except Exception:
                        #globals()[key] = set()
                        setattr(self, key, set())
            elif str(value).isdigit():
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
            dpg.set_value(f"input_{key}", self.format_output_value(key, self.settings[key]))
        self.update_global_variables()
        self.logger.add_log("Settings quick loaded")

    def reset_to_program_default(self):
        
        for key in self.input_field_keys:
            dpg.set_value(f"input_{key}", self.format_output_value(key, self.Default_settings_original[key]))
        self.logger.add_log("Settings reset to program default")

    def update_limit_on_exit_setting(self, sender, app_data, user_data):

        self.globallimitonexit = app_data
        self.settings_config["Preferences"]["globallimitonexit"] = str(app_data)
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"Global Limit on Exit set to: {self.globallimitonexit}")

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

    def update_profile_on_startup_setting(self, sender, app_data, user_data):
        self.profileonstartup = app_data
        self.settings_config["Preferences"]["profileonstartup"] = str(app_data)
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"Profile on Startup set to: {self.profileonstartup}")

    def select_default_profile_callback(self, sender, app_data, user_data):

        current_profile = dpg.get_value("profile_dropdown")
        dpg.set_value("profileonstartup_name", current_profile)
        self.settings_config["GlobalSettings"]["profileonstartup_name"] = current_profile
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"Profile on Startup set to: {self.profileonstartup_name}")

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

#TODO: Refactor this to use a more generic method for updating preference settings
    def update_launch_on_startup_setting(self, sender, app_data, user_data):
        self.launchonstartup = app_data
        self.settings_config["Preferences"]["launchonstartup"] = str(app_data)
        with open(self.settings_path, 'w') as f:
            self.settings_config.write(f)
        self.logger.add_log(f"Launch on Startup set to: {self.launchonstartup}")