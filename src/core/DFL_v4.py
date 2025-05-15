# DFL_v4.py
# Dynamic FPS Limiter v4.0.0

import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import dearpygui.dearpygui as dpg
import threading
import configparser
import time
import math
import os
import sys
import csv

# tweak path so "src/" (or wherever your modules live) is on sys.path
_this_dir = os.path.abspath(os.path.dirname(__file__))
_root = os.path.dirname(_this_dir)  # Gets src directory
if _root not in sys.path:
    sys.path.insert(0, _root)

from core import logger
from core.rtss_interface import RTSSInterface
from core.rtss_cli import RTSSCLI
from core.cpu_monitor import CPUUsageMonitor
from core.gpu_monitor import GPUUsageMonitor

# Always get absolute path to EXE or script location
Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# Ensure the config folder exists in the parent directory of Base_dir
config_dir = os.path.join(os.path.dirname(Base_dir), "config")
parent_dir = os.path.dirname(Base_dir)
os.makedirs(config_dir, exist_ok=True)

# Paths to configuration files
settings_path = os.path.join(config_dir, "settings.ini")
profiles_path = os.path.join(config_dir, "profiles.ini")
rtss_dll_path = os.path.join(Base_dir, "assets/rtss.dll")
error_log_file = os.path.join(parent_dir, "error_log.txt")
icon_path = os.path.join(Base_dir, 'assets/DynamicFPSLimiter.ico')
font_path = os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf") #segoeui, Verdana, Tahoma, Calibri, micross
faq_path = os.path.join(Base_dir, "assets/faqs.csv")

logger.init_logging(error_log_file)
rtss_manager = None

profiles_config = configparser.ConfigParser()
settings_config = configparser.ConfigParser()

# Check if the settings and profiles files exist, if not create them with default values
if os.path.exists(settings_path):
    settings_config.read(settings_path)
else:
    # Initialize Preferences section
    settings_config["Preferences"] = {
        'ShowTooltip': 'True',
        'GlobalLimitOnExit': 'True',
    }
    # Add GlobalSettings section
    settings_config["GlobalSettings"] = {
        'delaybeforedecrease': '2',
        'delaybeforeincrease': '2',
        'minvalidgpu': '20',
        'minvalidfps': '20',
        'globallimitonexit_fps': '98',
        'cpupercentile': '70',
        'cpupollinginterval': '100',
        'cpupollingsamples': '20',
        'gpupercentile': '70',
        'gpupollinginterval': '100',
        'gpupollingsamples': '20',
    }
    with open(settings_path, 'w') as f:
        settings_config.write(f)

if os.path.exists(profiles_path):
    profiles_config.read(profiles_path)
else:
    profiles_config["Global"] = {
        'maxcap': '60',
        'mincap': '30',
        'capstep': '5',
        'gpucutofffordecrease': '85',
        'gpucutoffforincrease': '75',
        'cpucutofffordecrease': '95',
        'cpucutoffforincrease': '85',
        'enablecustomfpslimits': '0',
        'customfpslimits': '30, 60',
    }
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)

Default_settings_original = {
    "maxcap": 60,
    "mincap": 30,
    "capstep": 5,
    "gpucutofffordecrease": 85,
    "gpucutoffforincrease": 75,
    'cpucutofffordecrease': 95,
    'cpucutoffforincrease': 85,
    "delaybeforedecrease": 2,
    "delaybeforeincrease": 2,
    "enablecustomfpslimits": 0,
    "customfpslimits": {30, 60},
    "minvalidgpu": 20,
    "minvalidfps": 20,
    "globallimitonexit_fps": 98,
    'cpupercentile': 70,
    'cpupollinginterval': 100,
    'cpupollingsamples': 20,
    'gpupercentile': 70,
    'gpupollinginterval': 100,
    'gpupollingsamples': 20
}

input_field_keys = ["maxcap", "mincap", "capstep", 
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease",
                "enablecustomfpslimits", "customfpslimits"]

key_type_map = {
    "maxcap": int,
    "mincap": int,
    "capstep": int,
    "gpucutofffordecrease": int,
    "gpucutoffforincrease": int,
    "cpucutofffordecrease": int,
    "cpucutoffforincrease": int,
    "enablecustomfpslimits": int,
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
    "gpupollingsamples": int
}

questions = []
FAQs = {}

with open(faq_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for idx, row in enumerate(reader, start=1):
        key = f"faq_{idx}"
        questions.append(row["question"])
        FAQs[key] = row["answer"]

def parse_input_value(key, value):
    """Parse input value from UI based on key_type_map."""
    value_type = key_type_map.get(key, int)
    if value_type is set:
        if isinstance(value, set):
            return value
        try:
            return set(int(x.strip()) for x in str(value).split(",") if x.strip().isdigit())
        except Exception:
            return set()
    else:
        try:
            return value_type(value)
        except Exception:
            return value

def format_output_value(key, value):
    value_type = key_type_map.get(key, int)
    if value_type is set:
        if isinstance(value, set):
            return ", ".join(str(x) for x in sorted(value))
        return str(value)
    return value

# Function to get values with correct types
def get_setting(key, value_type=None):
    """Get setting from appropriate config section based on key type."""
    if value_type is None:
        value_type = key_type_map.get(key, str)
    # Get the raw value from the appropriate config section
    if key in settings_config["GlobalSettings"]:
        raw_value = settings_config["GlobalSettings"].get(key, Default_settings_original[key])
    else:
        raw_value = profiles_config["Global"].get(key, Default_settings_original[key])

    # Convert to the correct type
    if value_type is set:
        try:
            values = []
            for x in str(raw_value).split(","):
                x = x.strip()
                if x.isdigit():
                    values.append(int(x))
                else:
                    logger.add_log(f"Warning: Skipped non-integer value '{x}' in key '{key}'")
            return set(values)
        except Exception:
            logger.add_log(f"Error parsing set for key '{key}', using default.")
            values = []
            for x in str(Default_settings_original[key]).split(","):
                x = x.strip()
                if x.isdigit():
                    values.append(int(x))
            return set(values)
    
    try:
        return value_type(raw_value)
    except Exception:
        try:
            return value_type(Default_settings_original[key])
        except Exception:
            return Default_settings_original[key]

Default_settings = {key: get_setting(key, set if isinstance(Default_settings_original[key], set) else int) for key in Default_settings_original}

ShowTooltip = str(settings_config["Preferences"].get("ShowTooltip", "True")).strip().lower() == "true"
GlobalLimitonExit = str(settings_config["Preferences"].get("GlobalLimitOnExit", "True")).strip().lower() == "true"

for key in settings_config["GlobalSettings"]:
    value_type = key_type_map.get(key, str)
    value = get_setting(key, value_type)
    if value is not None:
        globals()[key] = value

# Default viewport size
Viewport_width = 600
Viewport_height = 705
Plot_height = 220

def save_to_profile():
    selected_profile = dpg.get_value("profile_dropdown")

    if selected_profile:
        # Update profile-specific settings
        for key in input_field_keys:
            value = dpg.get_value(f"input_{key}")
            parsed_value = parse_input_value(key, value)
            # Store as string for config file
            if isinstance(parsed_value, set):
                profiles_config[selected_profile][key] = ", ".join(str(x) for x in sorted(parsed_value))
            else:
                profiles_config[selected_profile][key] = str(parsed_value)
        
        with open(profiles_path, "w") as configfile:
            profiles_config.write(configfile)

        logger.add_log(f"Settings saved to profile: {selected_profile}")

settings = Default_settings.copy()

#continue from here

def update_profile_dropdown(select_first=False):
    profiles = profiles_config.sections()
    dpg.configure_item("profile_dropdown", items=profiles)

    if select_first and profiles:
        dpg.set_value("profile_dropdown", profiles[0])  # Set combo selection

current_profile = "Global"

def load_profile_callback(sender, app_data, user_data):
    global current_profile
    current_profile = app_data
    profile_name = app_data

    if profile_name not in profiles_config:
        return
    for key in input_field_keys:
        value = profiles_config[profile_name].get(key, Default_settings_original[key])
        parsed_value = parse_input_value(key, value)
        if isinstance(parsed_value, set):
            value_str = ", ".join(str(x) for x in sorted(parsed_value))
            dpg.set_value(f"input_{key}", value_str)
        else:
            dpg.set_value(f"input_{key}", parsed_value)
    update_global_variables()
    dpg.set_value("new_profile_input", "")

def save_profile(profile_name):
    profiles_config[profile_name] = {}
    # Save input fields
    for key in input_field_keys:
        value = dpg.get_value(f"input_{key}")
        parsed_value = parse_input_value(key, value)
        if isinstance(parsed_value, set):
            profiles_config[profile_name][key] = ", ".join(str(x) for x in sorted(parsed_value))
        else:
            profiles_config[profile_name][key] = str(parsed_value)
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)
    update_profile_dropdown()

def add_new_profile_callback():
    new_name = dpg.get_value("new_profile_input")
    if new_name and new_name not in profiles_config:
        save_profile(new_name)
        dpg.set_value("new_profile_input", "")
        logger.add_log(f"New profile created: {new_name}")
    else:
        logger.add_log("Profile name is empty or already exists.")

def add_process_profile_callback():
    new_name = dpg.get_value("LastProcess")
    if new_name and new_name not in profiles_config:
        save_profile(new_name)
        logger.add_log(f"New profile created: {new_name}")
    else:
        logger.add_log("Profile name is empty or already exists.")

def delete_selected_profile_callback():
    global current_profile

    profile_to_delete = dpg.get_value("profile_dropdown")
    if profile_to_delete == "Global":
        logger.add_log("Cannot delete the default 'Global' profile.")
        return
    if profile_to_delete in profiles_config:
        profiles_config.remove_section(profile_to_delete)
        with open(profiles_path, 'w') as f:
            profiles_config.write(f)
        update_profile_dropdown(select_first=True)

        # Reset input fields to the "Global" profile values
        if "Global" in profiles_config:
            for key in profiles_config["Global"]:
                try:
                    value = profiles_config["Global"][key]
                    parsed_value = parse_input_value(key, value)
                    if isinstance(parsed_value, set):
                        value_str = ", ".join(str(x) for x in sorted(parsed_value))
                        dpg.set_value(f"input_{key}", value_str)
                    else:
                        dpg.set_value(f"input_{key}", parsed_value)
                except Exception as e:
                    logger.add_log(f"Error: Unable to convert value for key '{key}': {e}")
            update_global_variables()  # Ensure global variables are updated
        else:
            logger.add_log("Error: 'Global' profile not found in configuration.")

        logger.add_log(f"Deleted profile: {profile_to_delete}")
        current_profile = "Global"

running = False  # Flag to control the monitoring loop

# Function to sync settings with variables
def update_global_variables():
    for key, value in settings.items():
        value_type = key_type_map.get(key, type(value))
        if value_type is set:
            # If value is a string, parse it to a set of ints
            if isinstance(value, set):
                globals()[key] = value
            else:
                try:
                    values = [int(x.strip()) for x in str(value).split(",") if x.strip().isdigit()]
                    globals()[key] = set(values)
                except Exception:
                    globals()[key] = set()
        elif str(value).isdigit():
            globals()[key] = int(value)
        else:
            globals()[key] = value

update_global_variables()

# Read values from UI input fields without modifying `settings`
def apply_current_input_values():
    for key in input_field_keys:
        value = dpg.get_value(f"input_{key}")
        globals()[key] = parse_input_value(key, value)

def start_stop_callback():
    global running, maxcap, current_profile
    running = not running
    dpg.configure_item("start_stop_button", label="Stop" if running else "Start")
    apply_current_input_values()
    
    # Reset variables to zero or their default state
    global fps_values, CurrentFPSOffset, fps_mean, gpu_values, cpu_values
    fps_values = []
    CurrentFPSOffset = 0
    fps_mean = 0
    gpu_values = []
    cpu_values = []

    # Freeze input fields

    for key in input_field_keys:
        dpg.configure_item(f"input_{key}", enabled=not running)

    if running:
        # Initialize RTSS
        rtss_cli.enable_limiter()
        rtss_cli.set_property(current_profile, "FramerateLimit", int(maxcap))
        
        # Apply current settings and start monitoring
        
        time_series.clear()
        fps_time_series.clear()
        gpu_usage_series.clear()
        cpu_usage_series.clear()
        fps_series.clear()
        cap_series.clear()
        global elapsed_time
        elapsed_time = 0 # Reset elapsed time
        
        # Start threads
        monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitoring_thread.start()
        logger.add_log("Monitoring started")
        plotting_thread = threading.Thread(target=plotting_loop, daemon=True)
        plotting_thread.start()
        logger.add_log("Plotting started")
    else:
        reset_stats()
        CurrentFPSOffset = 0
        rtss_cli.set_property(current_profile, "FramerateLimit", int(maxcap))
        logger.add_log("Monitoring stopped")

def quick_save_settings():
    for key in input_field_keys:
        value = dpg.get_value(f"input_{key}")
        settings[key] = parse_input_value(key, value)
    update_global_variables()
    logger.add_log("Settings quick saved")

def quick_load_settings():
    for key in input_field_keys:
        dpg.set_value(f"input_{key}", format_output_value(key, settings[key]))
    update_global_variables()
    logger.add_log("Settings quick loaded")

def reset_stats():
    
    dpg.configure_item("gpu_usage_series", label="GPU: --")
    dpg.configure_item("cpu_usage_series", label="CPU: --")
    dpg.configure_item("fps_series", label="FPS: --")
    dpg.configure_item("cap_series", label="FPS Cap: --")
    time_series.clear()
    fps_time_series.clear()
    gpu_usage_series.clear()
    cpu_usage_series.clear()
    fps_series.clear()
    cap_series.clear()
    global elapsed_time
    elapsed_time = 0

def reset_to_program_default():
    
    global Default_settings_original
    
    for key in input_field_keys:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    logger.add_log("Settings reset to program default")  

def reset_customFPSLimits():

    lowerlimit = dpg.get_value(f"input_mincap")
    upperlimit = dpg.get_value(f"input_maxcap")
    dpg.set_value("input_customfpslimits", f"{lowerlimit}, {upperlimit}")

time_series = []
fps_time_series = []
gpu_usage_series = []
cpu_usage_series = []
fps_series = []
cap_series = []
max_points = 600
elapsed_time = 0 # Global time updated by plotting_loop

def update_plot_FPS(fps_val, cap_val):
# Uses fps_time_series    
    global fps_time_series, fps_series, cap_series, elapsed_time
    global max_points, mincap, maxcap, capstep

    while len(fps_time_series) >= max_points:
        fps_time_series.pop(0)
        fps_series.pop(0)
        cap_series.pop(0)

    current_time = elapsed_time
    fps_time_series.append(current_time)
    fps_series.append(fps_val)
    cap_series.append(cap_val)

    dpg.set_value("fps_series", [fps_time_series, fps_series])
    dpg.set_value("cap_series", [fps_time_series, cap_series])  

    min_ft = mincap - capstep
    max_ft = maxcap + capstep
    dpg.set_axis_limits("y_axis_right", min_ft, max_ft) 

def update_plot_usage(time_val, gpu_val, cpu_val):
   
    global time_series, gpu_usage_series, cpu_usage_series
    global max_points, gpucutofffordecrease, gpucutoffforincrease # Add needed globals
    
    while len(time_series) >= max_points:
        time_series.pop(0)
        gpu_usage_series.pop(0)
        cpu_usage_series.pop(0)
    
    gpu_val = gpu_val or 0
    cpu_val = cpu_val or 0

    # Append passed-in time and new values
    time_series.append(time_val)
    gpu_usage_series.append(gpu_val)
    cpu_usage_series.append(cpu_val)

    dpg.set_value("gpu_usage_series", [time_series, gpu_usage_series])
    dpg.set_value("cpu_usage_series", [time_series, cpu_usage_series])

    if time_series:
        start_x = time_series[0]
        end_x = time_series[-1]
        # Add a small buffer to the end time for better visibility
        dpg.set_axis_limits("x_axis", start_x, end_x + 1)
        
        # Update static lines to extend across the current X range of the main time_series
        # Ensure gpucutoff... variables are up-to-date globals
        dpg.set_value("line1", [[start_x, end_x + 1], [gpucutofffordecrease, gpucutofffordecrease]])
        dpg.set_value("line2", [[start_x, end_x + 1], [gpucutoffforincrease, gpucutoffforincrease]])
    else:
        dpg.set_axis_limits_auto("x_axis")

luid_selected = False  # default state
luid = "All"

def toggle_luid_selection():
    global luid_selected, luid

    if not luid_selected:
        # First click: detect top LUID
        usage, luid = gpu_monitor.get_gpu_usage(engine_type="engtype_3D")
        if luid:
            logger.add_log(f"Tracking LUID: {luid} | Current 3D engine Utilization: {usage}%")
            dpg.configure_item("luid_button", label="Revert to all GPUs")
            dpg.bind_item_theme("luid_button", "revert_gpu_theme")  # Apply blue theme
            luid_selected = True
        else:
            logger.add_log("Failed to detect active LUID.")
    else:
        # Second click: deselect
        luid = "All"
        logger.add_log("Tracking all GPU engines.")
        dpg.configure_item("luid_button", label="Detect Render GPU")
        dpg.bind_item_theme("luid_button", "detect_gpu_theme")  # Apply default grey theme
        luid_selected = False

fps_values = []
gpu_values = []
cpu_values = []
CurrentFPSOffset = 0
fps_mean = 0

def monitoring_loop():
    global running, fps_values, CurrentFPSOffset, fps_mean, gpu_values, current_profile, cpu_values
    global mincap, maxcap, capstep, gpucutofffordecrease, delaybeforedecrease, gpucutoffforincrease, delaybeforeincrease, minvalidgpu, minvalidfps, cpucutofffordecrease, cpucutoffforincrease
    global max_points, minvalidgpu, minvalidfps, luid_selected, luid

    last_process_name = None
    min_ft = mincap - capstep
    max_ft = maxcap + capstep
    
    gpu_monitor.reinitialize()

    while running:
        fps, process_name = rtss_manager.get_fps_for_active_window()
        #logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")
        
        if process_name and process_name != last_process_name:
            last_process_name = process_name
            logger.add_log(f"Active window changed to: {last_process_name}") 
            if process_name != "DynamicFPSLimiter.exe":
                dpg.set_value("LastProcess", last_process_name)
            gpu_monitor.reinitialize()

        if fps:
            if len(fps_values) > 2:
                fps_values.pop(0)
            fps_values.append(fps)
            fps_mean = sum(fps_values) / len(fps_values)
        
        gpuUsage = gpu_monitor.gpu_percentile
        if len(gpu_values) > (max(delaybeforedecrease, delaybeforeincrease)+1):
            gpu_values.pop(0)
        gpu_values.append(gpuUsage)

        cpuUsage = cpu_monitor.cpu_percentile
        if len(cpu_values) > (max(delaybeforedecrease, delaybeforeincrease)+1):
            cpu_values.pop(0)
        cpu_values.append(cpuUsage)

        # To prevent loading screens from affecting the fps cap
        if gpuUsage and process_name not in {"DynamicFPSLimiter.exe"}:
            if gpuUsage > minvalidgpu and fps_mean > minvalidfps: 

                should_decrease = False
                gpu_decrease_condition = (len(gpu_values) >= delaybeforedecrease and
                                          all(value >= gpucutofffordecrease for value in gpu_values[-delaybeforedecrease:]))
                cpu_decrease_condition = (len(cpu_values) >= delaybeforedecrease and
                                          all(value >= cpucutofffordecrease for value in cpu_values[-delaybeforedecrease:]))
                if gpu_decrease_condition or cpu_decrease_condition:
                    should_decrease = True
                if CurrentFPSOffset > (mincap - maxcap) and should_decrease:
                    X = math.ceil(((maxcap + CurrentFPSOffset) - (fps_mean)) / capstep)
                    X = max(1, X)
                    CurrentFPSOffset -= (capstep * X)
                    CurrentFPSOffset = max(CurrentFPSOffset, mincap - maxcap)
                    rtss_cli.set_property(current_profile, "FramerateLimit", int(maxcap+CurrentFPSOffset))

                should_increase = False
                gpu_increase_condition = (len(gpu_values) >= delaybeforeincrease and
                                          all(value <= gpucutoffforincrease for value in gpu_values[-delaybeforeincrease:]))
                cpu_increase_condition = (len(cpu_values) >= delaybeforeincrease and
                                          all(value <= cpucutoffforincrease for value in cpu_values[-delaybeforeincrease:]))
                if gpu_increase_condition and cpu_increase_condition:
                     should_increase = True
                if CurrentFPSOffset < 0 and should_increase:
                    CurrentFPSOffset += capstep
                    CurrentFPSOffset = min(CurrentFPSOffset, 0)
                    rtss_cli.set_property(current_profile, "FramerateLimit", int(maxcap+CurrentFPSOffset))

        if running:
            # Update legend labels with current values
            dpg.configure_item("gpu_usage_series", label=f"GPU: {gpuUsage}%")
            dpg.configure_item("fps_series", label=f"FPS: {fps:.1f}" if fps else "FPS: --")
            dpg.configure_item("cap_series", label=f"FPS Cap: {maxcap + CurrentFPSOffset}")
            dpg.configure_item("cpu_usage_series", label=f"CPU: {cpuUsage}%")

            # Update plot if fps is valid
            if fps and process_name not in {"DynamicFPSLimiter.exe"}:
                # Scaling FPS value to fit 0-100 axis
                scaled_fps = ((fps - min_ft)/(max_ft - min_ft))*100
                scaled_cap = ((maxcap + CurrentFPSOffset - min_ft)/(max_ft - min_ft))*100
                actual_cap = maxcap + CurrentFPSOffset
                # Pass actual values, update_plot_FPS handles timing and lists
                update_plot_FPS(scaled_fps, scaled_cap)

        # Update last_process_name
        if process_name:
            last_process_name = process_name

        time.sleep(1) # This loop runs every 1 second

def plotting_loop():
    global running, elapsed_time, gpupollinginterval, cpupollinginterval# Make sure elapsed_time is global

    start_time = time.time()
    while running:
        # Calculate elapsed time SINCE start_time
        elapsed_time = time.time() - start_time

        gpuUsage = gpu_monitor.gpu_percentile
        cpuUsage = cpu_monitor.cpu_percentile

        # CALL update_plot_usage with the current time and usage values
        update_plot_usage(elapsed_time, gpuUsage, cpuUsage)

        time.sleep(math.lcm(gpupollinginterval, cpupollinginterval) / 1000.0)  # Convert to seconds

def update_tooltip_setting(sender, app_data, user_data):
    global ShowTooltip, input_field_keys, tooltips
    ShowTooltip = app_data
    settings_config["Preferences"]["ShowTooltip"] = str(app_data)
    with open(settings_path, 'w') as f:
        settings_config.write(f)
    logger.add_log(f"Tooltip visibility set to: {ShowTooltip}")

    for key in tooltips.keys():
        parent_tag = ""
        # Determine the parent tag first
        if key in input_field_keys:
            parent_tag = f"input_{key}"
        else:
            parent_tag = key # Assume key matches parent tag for others

        # Construct the specific TOOLTIP tag
        tooltip_specific_tag = f"{parent_tag}_tooltip"

        # Check if the TOOLTIP item exists and configure it
        if dpg.does_item_exist(tooltip_specific_tag):
            try:
                # Configure the tooltip item itself using its specific tag
                dpg.configure_item(tooltip_specific_tag, show=ShowTooltip)
            except SystemError as e:
                # This error is less likely now but kept for safety
                logger.add_log(f"Minor issue configuring tooltip '{tooltip_specific_tag}' for key '{key}': {e}")

def update_limit_on_exit_setting(sender, app_data, user_data):
    global GlobalLimitonExit
    GlobalLimitonExit = app_data
    settings_config["Preferences"]["GlobalLimitOnExit"] = str(app_data)
    with open(settings_path, 'w') as f:
        settings_config.write(f)
    logger.add_log(f"Global Limit on Exit set to: {GlobalLimitonExit}")

def update_exit_fps_value(sender, app_data, user_data):
    global globallimitonexit_fps 
    new_value = app_data

    if isinstance(new_value, int) and new_value > 0:
        globallimitonexit_fps = new_value
        settings_config["GlobalSettings"]["globallimitonexit_fps"] = str(new_value)
        with open(settings_path, 'w') as f:
            settings_config.write(f)
        logger.add_log(f"Global Limit on Exit FPS value set to: {globallimitonexit_fps}")
    else:
        logger.add_log(f"Invalid value entered for Global Limit on Exit FPS: {app_data}. Reverting.")
        dpg.set_value(sender, globallimitonexit_fps)

def exit_gui():
    global running, rtss_manager, monitoring_thread, plotting_thread, globallimitonexit_fps, GlobalLimitonExit

    if GlobalLimitonExit:
        rtss_cli.set_property("Global", "FramerateLimit", int(globallimitonexit_fps))

    running = False 
    if rtss_manager:
        rtss_manager.stop_monitor_thread()
    if gpu_monitor:
        gpu_monitor.cleanup()
    if cpu_monitor:
        cpu_monitor.stop()
    if dpg.is_dearpygui_running():
        dpg.destroy_context()
    
    if monitoring_thread and monitoring_thread.is_alive():
        logger.add_log("Waiting for monitoring thread to stop...")
        monitoring_thread.join(timeout=0.1)
        if monitoring_thread.is_alive():
            logger.add_log("Warning: Monitoring thread did not stop gracefully.")
        else:
            logger.add_log("Monitoring thread stopped.")
    if plotting_thread and plotting_thread.is_alive():
        logger.add_log("Waiting for monitoring thread to stop...")
        plotting_thread.join(timeout=0.1)
        if plotting_thread.is_alive():
            logger.add_log("Warning: Plotting thread did not stop gracefully.")
        else:
            logger.add_log("Plotting thread stopped.")

# Define keys used for input fields (used to construct tooltip tags)

tooltips = {
    "maxcap": "Defines the maximum FPS limit for the game.",
    "mincap": "Specifies the minimum FPS limit that may be reached. For optimal performance, set this to the lowest value you're comfortable with.",
    "capstep": "Indicates the increment size for adjusting the FPS cap. Smaller step sizes provide finer control",
    "gpucutofffordecrease": "Sets the upper threshold for GPU usage. If GPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "delaybeforedecrease": "Specifies how many times in a row GPU usage must exceed the upper threshold before the FPS cap begins to drop.",
    "gpucutoffforincrease": "Defines the lower threshold for GPU usage. If GPU usage falls below this value, the FPS cap will increase to improve performance.",
    "delaybeforeincrease": "Specifies how many times in a row GPU usage must fall below the lower threshold before the FPS cap begins to rise.",
    "cpucutofffordecrease": "Sets the upper threshold for CPU usage. If CPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "cpucutoffforincrease": "Defines the lower threshold for CPU usage. If CPU usage falls below this value, the FPS cap will increase to improve performance.",
    "minvalidgpu": "Sets the minimum valid GPU usage percentage required for adjusting the FPS. If the GPU usage is below this threshold, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "minvalidfps": "Defines the minimum valid FPS required for adjusting the FPS. If the FPS falls below this value, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "quick_save_load": "Saves and loads input values from memory. This is temporary storage, useful for testing and fine-tuning configurations.",
    "start_stop_button": "Starts maintaining the FPS cap dynamically based on GPU/CPU utilization. Green = RTSS running. Red = RTSS not running.",
    "luid_button": "Detects the render GPU based on highest 3D engine utilization, and sets it as the target GPU for FPS limiting. Click again to deselect.",
    "exit_fps_input": "The specific FPS limit to apply globally when the application exits, if 'Set Global FPS Limit on Exit' is checked.",
    "SaveToProfile": "Saves the current settings to the selected profile. This allows you to quickly switch between different configurations.",
    "Reset_Default": "Resets all settings to the program's default values. This is useful if you want to start fresh or if you encounter issues."
}

# GUI setup: Main Window
dpg.create_context()

with dpg.font_registry():
    try:
        default_font = dpg.add_font(font_path, 18)
        if default_font:
            dpg.bind_font(default_font)
    except Exception as e:
        logger.add_log(f"Failed to load system font: {e}")
        # Will use DearPyGui's default font as fallback

# Create a theme for rounded buttons
background_colour = (37, 37, 38)  # Default grey background

with dpg.theme(tag="rounded_widget_theme"):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3.0)  # Set corner rounding to 10.0
        dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55)) 
        #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0.0, 1.0, category=dpg.mvThemeCat_Core)
        #dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 150, 250))  # Button color
        #dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 170, 255))  # Hover color
        #dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 190, 255))  # Active color

    # Customize specific widget types
    #with dpg.theme_component(dpg.mvInputInt):

    #with dpg.theme_component(dpg.mvInputText):

    with dpg.theme_component(dpg.mvCheckbox):
        dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (50, 150, 250))  # Checkmark color

# Bind the rounded button theme globally
dpg.bind_theme("rounded_widget_theme")

# Create themes for specific buttons
with dpg.theme(tag="rtss_running_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 100, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 120, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 140, 0))

with dpg.theme(tag="rtss_not_running_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (170, 70, 70)) #Reds
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 90, 90))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (190, 90, 90))

with dpg.theme(tag="detect_gpu_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55))  # Defualt grey button background
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (15, 86, 135))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (15, 86, 135))

with dpg.theme(tag="revert_gpu_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135))  # Blue color botton background
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (6, 96, 158))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 105, 176))

with dpg.theme(tag="button_right"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 1.00, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_Button, background_colour, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, background_colour, category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, background_colour, category=dpg.mvThemeCat_Core)

#The actual GUI starts here
with dpg.window(label="Dynamic FPS Limiter", tag="Primary Window"):
    
    # Title and Start/Stop Button
    with dpg.group(horizontal=True):
        dpg.add_text("Dynamic FPS Limiter v4.0.0")
        dpg.add_spacer(width=30)
        dpg.add_button(label="Detect Render GPU", callback=toggle_luid_selection, tag="luid_button", width=150)
        # Give the tooltip its own tag
        with dpg.tooltip(parent="luid_button", tag="luid_button_tooltip", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["luid_button"], wrap = 200)
        dpg.add_spacer(width=30)
        dpg.add_button(label="Start", tag="start_stop_button", callback=start_stop_callback, width=50)
        # Give the tooltip its own tag
        with dpg.tooltip(parent="start_stop_button", tag="start_stop_button_tooltip", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["start_stop_button"], wrap = 200)
        dpg.add_button(label="Exit", callback=exit_gui, width=50)  # Exit button

    # Profiles
    with dpg.child_window(width=-1, height=145):
        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=55)
            dpg.add_table_column(init_width_or_weight=140)
            dpg.add_table_column(init_width_or_weight=60)

            # First row
            with dpg.table_row():
                dpg.add_text("Select Profile:")
                dpg.add_combo(tag="profile_dropdown", callback=load_profile_callback, width=260, default_value="Global")
                dpg.add_button(label="Delete Profile", callback=delete_selected_profile_callback, width=120)

            # Second row
            with dpg.table_row():
                dpg.add_text("New RTSS Profile:")
                dpg.add_input_text(tag="new_profile_input", width=260)
                dpg.add_button(label="Add Profile", callback=add_new_profile_callback, width=120)

        dpg.add_spacer(height=3)        
        with dpg.group(horizontal=True):
            dpg.add_text("Last active process:")
            dpg.add_spacer(width=260)
            dpg.add_button(label="Add process to Profiles", callback=add_process_profile_callback)
        dpg.add_spacer(height=1)
        dpg.add_input_text(tag="LastProcess", multiline=False, readonly=True, width=-1)    
    
    #Tabs
    tab_height = 200
    dpg.add_spacer(height=1)
    with dpg.tab_bar():
        with dpg.tab(label="Profile Settings", tag="tab1"):
            with dpg.child_window(height=tab_height):
                with dpg.group(horizontal=True):
                    with dpg.group(width=200):
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column(width_fixed=True)  # Column for labels
                            dpg.add_table_column(width_fixed=True)  # Column for input boxes
                            for label, key in [("Max FPS limit:", "maxcap"), 
                                            ("Min FPS limit:", "mincap"),
                                            ("Frame rate step:", "capstep")]:
                                with dpg.table_row():
                                    dpg.add_text(label)
                                    dpg.add_input_int(tag=f"input_{key}", default_value=int(settings[key]), width=90, step=1, step_fast=10)
                                    # Give the tooltip its own tag
                                    with dpg.tooltip(parent=f"input_{key}", tag=f"input_{key}_tooltip", show=ShowTooltip, delay=1):
                                        dpg.add_text(tooltips[key], wrap = 200)
                        dpg.add_spacer(height=1)
                        dpg.add_checkbox(label="Define custom FPS limits", tag="custom_fps_limits_checkbox", default_value=True)#CustomFPSLimits, callback=update_custom_fps_limits)
                    dpg.add_spacer(width=0.5)
                    with dpg.group(width=160):
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column(width_fixed=True)
                            dpg.add_table_column(width_fixed=True)
                            for label, key in [("GPU: Upper limit", "gpucutofffordecrease"),
                                            ("Lower limit", "gpucutoffforincrease"),
                                            ("CPU: Upper limit", "cpucutofffordecrease"),
                                            ("Lower limit", "cpucutoffforincrease")]:
                                with dpg.table_row():
                                    dpg.add_button(label=label, tag=f"button_{key}", width=110)
                                    dpg.bind_item_theme(f"button_{key}", "button_right")
                                    dpg.add_input_text(tag=f"input_{key}", default_value=str(settings[key]), width=40)
                                    # Give the tooltip its own tag
                                    with dpg.tooltip(parent=f"input_{key}", tag=f"input_{key}_tooltip", show=ShowTooltip, delay=1):
                                        dpg.add_text(tooltips[key], wrap=200)
                    
                    dpg.add_spacer(width=0.5)
                    with dpg.group(width=160):
                        #dpg.add_spacer(height=3)
                        with dpg.group(horizontal=False):
                            with dpg.group(tag="quick_save_load"):
                                # Give the tooltip its own tag
                                with dpg.tooltip(parent="quick_save_load", tag="quick_save_load_tooltip", show=ShowTooltip, delay=1):
                                    dpg.add_text(tooltips["quick_save_load"], wrap = 200)
                                dpg.add_button(label="Quick Save", callback=quick_save_settings)
                                dpg.add_button(label="Quick Load", callback=quick_load_settings)
                            dpg.add_button(tag="Reset_Default", label="Reset Settings to Default", callback=reset_to_program_default)
                            # Give the tooltip its own tag
                            with dpg.tooltip(parent="Reset_Default", tag="Reset_Default_tooltip", show=ShowTooltip, delay=1):
                                dpg.add_text(tooltips["Reset_Default"], wrap = 200)
                            dpg.add_spacer(height=3)
                            dpg.add_button(tag="SaveToProfile", label="Save Settings to Profile", callback=save_to_profile)
                            # Give the tooltip its own tag
                            with dpg.tooltip(parent="SaveToProfile", tag="SaveToProfile_tooltip", show=ShowTooltip, delay=1):
                                dpg.add_text(tooltips["SaveToProfile"], wrap = 200)
                
                draw_height = 30
                draw_width = Viewport_width - 60
                margin = 10
                with dpg.drawlist(width= draw_width, height=draw_height, tag="fps_cap_drawlist"):
                    dpg.draw_line((margin, draw_height // 2), (draw_width + margin, draw_height // 2), color=(200, 200, 200), thickness=2)
                
                with dpg.group(horizontal=True):
                    dpg.add_input_text(
                        tag="input_customfpslimits",
                        default_value=f"{mincap}, {maxcap}",#", ".join(map(str, sorted(self.selected_fps_caps))),
                        width=draw_width - 100,
                        #pos=(10, 140),  # Center the input horizontally
                        #callback=self.update_fps_caps_from_input,
                        on_enter=True)
                    dpg.add_button(label="Reset", tag="rest_fps_cap_button", width=100, callback=reset_customFPSLimits)
    
        with dpg.tab(label="Preferences", tag="tab2"):
            with dpg.child_window(height=tab_height):
                dpg.add_checkbox(label="Show Tooltips", tag="tooltip_checkbox",
                                 default_value=ShowTooltip, callback=update_tooltip_setting)
                dpg.add_checkbox(label="Reset Global RTSS Framerate Limit on Exit", tag="limit_on_exit_checkbox",
                                 default_value=GlobalLimitonExit, callback=update_limit_on_exit_setting)
                dpg.add_spacer(height=3)
                with dpg.group(horizontal=True):
                    dpg.add_text("Framerate limit:")
                    dpg.add_input_int(tag="exit_fps_input",
                                    default_value=globallimitonexit_fps, callback=update_exit_fps_value,
                                    width=100, step=1, step_fast=10)
                # Give the tooltip its own tag
                with dpg.tooltip(parent="exit_fps_input", tag="exit_fps_input_tooltip", show=ShowTooltip, delay=1):
                    dpg.add_text(tooltips["exit_fps_input"], wrap = 200)

        with dpg.tab(label="Log", tag="tab3"):
            with dpg.child_window(tag="LogWindow", autosize_x=True, height=tab_height, border=True):
                #dpg.add_text("", tag="LogText", tracked = True, track_offset = 1.0)
                dpg.add_spacer(height=2)
                dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=110)

                with dpg.theme(tag="transparent_input_theme"):
                    with dpg.theme_component(dpg.mvInputText):
                        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

                dpg.bind_item_theme("LogText", "transparent_input_theme")

        with dpg.tab(label="FAQs", tag="tab4"):
            with dpg.child_window(height=tab_height):
                dpg.add_text("Frequently Asked Questions (FAQs): Hover for answers")
                dpg.add_spacer(height=3)
                for question, (key, answer) in zip(questions, FAQs.items()):
                    dpg.add_text(question, tag=key, bullet=True)
                    with dpg.tooltip(parent=key, delay=0.5):
                        dpg.add_text(answer, wrap=300)
    
    # Third Row: Plot Section
    dpg.add_spacer(height=1)
    with dpg.child_window(width=-1, height=Plot_height):
        with dpg.theme(tag="plot_theme") as item_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128), category = dpg.mvThemeCat_Plots)

        with dpg.plot(height=200, width=-1, tag="plot"):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis")
            dpg.add_plot_legend(location=dpg.mvPlot_Location_North, horizontal=True, 
                              no_highlight_item=True, no_highlight_axis=True, outside=True)

            # Left Y-axis for GPU Usage
            with dpg.plot_axis(dpg.mvYAxis, label="GPU/CPU Usage (%)", tag="y_axis_left", no_gridlines=True) as y_axis_left:
                dpg.add_line_series([], [], label="GPU: --", parent=y_axis_left, tag="gpu_usage_series")
                dpg.add_line_series([], [], label="CPU: --", parent=y_axis_left, tag="cpu_usage_series")
                # Add static horizontal dashed lines
                dpg.add_line_series([], [gpucutofffordecrease, gpucutofffordecrease], parent=y_axis_left, tag="line1")
                dpg.add_line_series([], [gpucutoffforincrease, gpucutoffforincrease], parent=y_axis_left, tag="line2")
            
            # Right Y-axis for FPS
            with dpg.plot_axis(dpg.mvYAxis, label="FPS", tag="y_axis_right", no_gridlines=True) as y_axis_right:
                dpg.add_line_series([], [], label="FPS: --", parent=y_axis_right, tag="fps_series")
                dpg.add_line_series([], [], label="FPS Cap: --", parent=y_axis_right, tag="cap_series", segments=True)
                
            # Set axis limits
            dpg.set_axis_limits("y_axis_left", 0, 100)  # GPU usage range
            min_ft = mincap - capstep
            max_ft = maxcap + capstep
            dpg.set_axis_limits("y_axis_right", min_ft, max_ft)  # FPS range
            
            # apply theme to series
            dpg.bind_item_theme("line1", "plot_theme")
            dpg.bind_item_theme("line2", "plot_theme")

dpg.create_viewport(title="Dynamic FPS Limiter", width=Viewport_width, height=Viewport_height, resizable=False)
dpg.set_viewport_resizable(False)
dpg.set_viewport_max_width(Viewport_width)
dpg.set_viewport_max_height(Viewport_height)
dpg.set_viewport_small_icon(icon_path)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)

# Setup and Run GUI
update_profile_dropdown(select_first=True)

logger.add_log("Initializing...")

gpu_monitor = GPUUsageMonitor(lambda: luid, lambda: running, logger, dpg, interval=(gpupollinginterval/1000), max_samples=gpupollingsamples, percentile=gpupercentile)
#logger.add_log(f"Current highed GPU core load: {gpu_monitor.gpu_percentile}%")

#usage, luid = gpu_monitor.get_gpu_usage(engine_type="engtype_3D")
#logger.add_log(f"Current Top LUID: {luid}, 3D engine usage: {usage}%")

cpu_monitor = CPUUsageMonitor(lambda: running, logger, dpg, interval=(cpupollinginterval/1000), max_samples=cpupollingsamples, percentile=cpupercentile)
#logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")

# Assuming logger and dpg are initialized, and rtss_dll_path is defined
rtss_cli = RTSSCLI(logger, rtss_dll_path)
rtss_cli.enable_limiter()

rtss_manager = RTSSInterface(logger, dpg)
if rtss_manager:
    rtss_manager.start_monitor_thread()

logger.add_log("Initialized successfully.")

#Always make sure the corresponding GUI element exists before trying to get/set its value
dpg.start_dearpygui()

