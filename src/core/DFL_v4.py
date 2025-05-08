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
        'gpucutofffordecrease': '80',
        'gpucutoffforincrease': '70',
        'cpucutofffordecrease': '100',
        'cpucutoffforincrease': '95'
    }
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)

# Default values
Default_settings_original = {
    "maxcap": 60,
    "mincap": 30,
    "capstep": 5,
    "gpucutofffordecrease": 80,
    "delaybeforedecrease": 2,
    "gpucutoffforincrease": 70,
    'cpucutofffordecrease': 100,
    'cpucutoffforincrease': 95,
    "delaybeforeincrease": 2,
    "minvalidgpu": 20,
    "minvalidfps": 20,
    "globallimitonexit_fps": 98,
}

# Function to get values with correct types
def get_setting(key, value_type=int):
    """Get setting from appropriate config section based on key type."""
    if key in ["delaybeforedecrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps", "globallimitonexit_fps"]:
        return value_type(settings_config["GlobalSettings"].get(key, Default_settings_original[key]))
    return value_type(profiles_config["Global"].get(key, Default_settings_original[key]))

Default_settings = {key: get_setting(key, str if isinstance(Default_settings_original[key], str) else int) for key in Default_settings_original}

ShowTooltip = str(settings_config["Preferences"].get("ShowTooltip", "True")).strip().lower() == "true"
GlobalLimitonExit = str(settings_config["Preferences"].get("GlobalLimitOnExit", "True")).strip().lower() == "true"

for key in settings_config["GlobalSettings"]:
    # Assuming these are integers
    value = get_setting(key, int)
    if value is not None:
        globals()[key] = value

# Default viewport size
Viewport_width = 600
Viewport_height = 640
Plot_height = 220  # Height of the plot when shown

def save_to_profile():
    # Get current selected profile from the dropdown
    selected_profile = dpg.get_value("profile_dropdown")
    
    # Only proceed if a profile is selected
    if selected_profile:
        # Update profile-specific settings
        for key in ["maxcap", "mincap", "capstep",
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
            value = dpg.get_value(f"input_{key}")  # Get value from input field
            profiles_config[selected_profile][key] = str(value) 
        
        # Update global settings
        for key in ["delaybeforedecrease", "delaybeforeincrease", 
                   "minvalidgpu", "minvalidfps"]:
            settings_config["GlobalSettings"][key] = str(get_setting(key))
        
        # Save both configs
        with open(profiles_path, "w") as configfile:
            profiles_config.write(configfile)
        with open(settings_path, "w") as configfile:
            settings_config.write(configfile)
            
        logger.add_log(f"Settings saved to profile: {selected_profile}")
settings = Default_settings.copy()

#Functions for profiles start --------------

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
    for key in ["maxcap", "mincap", "capstep",
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        value = profiles_config[profile_name].get(key, Default_settings_original[key])
        dpg.set_value(f"input_{key}", int(value))
    update_global_variables()
    dpg.set_value("new_profile_input", "")

def save_profile(profile_name):
    profiles_config[profile_name] = {}
    # Save input fields
    for key in ["maxcap", "mincap", "capstep",
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        profiles_config[profile_name][key] = str(dpg.get_value(f"input_{key}"))
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
        for key in profiles_config["Global"]:
            dpg.set_value(f"input_{key}", profiles_config["Global"][key])
        update_global_variables()
        logger.add_log(f"Deleted profile: {profile_to_delete}")
        current_profile = "Global"

#Functions for profiles end ----------------

running = False  # Flag to control the monitoring loop

# Function to sync settings with variables
def update_global_variables():
    for key, value in settings.items():
        if str(value).isdigit():  # Check if value is a number
            globals()[key] = int(value)

update_global_variables()

# Read values from UI input fields without modifying `settings`
def apply_current_input_values():
    for key in ["maxcap", "mincap", "capstep", 
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        globals()[key] = int(dpg.get_value(f"input_{key}"))  # Convert to int

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

    for key in ["maxcap", "mincap", "capstep", 
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        dpg.configure_item(f"input_{key}", enabled=not running)

    if running:
        # Initialize RTSS
        rtss_cli.enable_limiter()
        rtss_cli.set_property(current_profile, "FramerateLimit", int(maxcap))
        
        # Apply current settings and start monitoring
        
        time_series.clear()
        fps_time_series.clear() # Clear the new list too
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
    for key in ["maxcap", "mincap", "capstep", 
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        settings[key] = dpg.get_value(f"input_{key}")
    update_global_variables()
    logger.add_log("Settings quick saved")

def quick_load_settings():
    for key in ["maxcap", "mincap", "capstep", 
                "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        dpg.set_value(f"input_{key}", settings[key])
    update_global_variables()
    logger.add_log("Settings quick loaded")

def enable_plot_callback(sender, app_data): #Currently not in use
    dpg.configure_item("plot_section", show=app_data)
    
    # Get current viewport size
    current_width, current_height = dpg.get_viewport_width(), dpg.get_viewport_height()
    
    # Compute new height based on plot visibility
    new_height = current_height + Plot_height if app_data else current_height - Plot_height

    dpg.set_viewport_height(new_height)
    
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
    
    for key in ["maxcap", "mincap", "capstep"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    for key in ["gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    logger.add_log("Settings reset to program default")  

time_series = []        # For GPU/CPU usage (updated every 0.2s)
fps_time_series = []    # For FPS/Cap (updated every 1s)
gpu_usage_series = []
cpu_usage_series = []
fps_series = []
cap_series = []
max_points = 300
elapsed_time = 0 # Global time updated by plotting_loop

def update_plot_FPS(fps_val, cap_val):
# Uses fps_time_series    
    global fps_time_series, fps_series, cap_series, elapsed_time
    global max_points, mincap, maxcap, capstep

    # Apply max_points limit to FPS-specific lists
    while len(fps_time_series) >= max_points: # Use while for safety
        fps_time_series.pop(0)
        fps_series.pop(0)
        cap_series.pop(0)

# Append current global time and new values
    current_time = elapsed_time # Capture the time when this function is called
    fps_time_series.append(current_time)
    fps_series.append(fps_val)
    cap_series.append(cap_val)

# Update DPG series using the FPS-specific time series
    dpg.set_value("fps_series", [fps_time_series, fps_series])
    dpg.set_value("cap_series", [fps_time_series, cap_series])  

# Set Y-axis limits for FPS/Cap (Right Axis)
    # Ensure mincap, maxcap, capstep are up-to-date globals if they can change
    min_ft = mincap - capstep
    max_ft = maxcap + capstep
    dpg.set_axis_limits("y_axis_right", min_ft, max_ft) 

def update_plot_usage(time_val, gpu_val, cpu_val):
# Uses the main time_series    
    global time_series, gpu_usage_series, cpu_usage_series
    global max_points, gpucutofffordecrease, gpucutoffforincrease # Add needed globals
    
    # Apply max_points limit to Usage-specific lists
    while len(time_series) >= max_points: # Use while for safety
        time_series.pop(0)
        gpu_usage_series.pop(0)
        cpu_usage_series.pop(0)
    
    gpu_val = gpu_val or 0
    cpu_val = cpu_val or 0

# Append passed-in time and new values
    time_series.append(time_val)
    gpu_usage_series.append(gpu_val)
    cpu_usage_series.append(cpu_val)

# Update DPG series using the main time series
    dpg.set_value("gpu_usage_series", [time_series, gpu_usage_series])
    dpg.set_value("cpu_usage_series", [time_series, cpu_usage_series])

    # Update X-axis limits based on the main time_series
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
luid = "All" # Placeholder for LUID

def toggle_luid_selection():
    global luid_selected, luid

    if not luid_selected:
        # First click: detect top LUID
        usage, luid = gpu_monitor.get_gpu_usage(engine_type="engtype_3D")
        if luid:
            logger.add_log(f"Tracking LUID: {luid} | Current 3D engine Utilization: {usage}%")
            dpg.configure_item("luid_button", label="Revert to all GPUs")
            dpg.bind_item_theme("luid_button", "revert_gpu_theme")  # Apply red theme
            luid_selected = True
        else:
            logger.add_log("Failed to detect active LUID.")
    else:
        # Second click: deselect
        luid = "All"
        logger.add_log("Tracking all GPU engines.")
        dpg.configure_item("luid_button", label="Detect Render GPU")
        dpg.bind_item_theme("luid_button", "detect_gpu_theme")  # Apply blue theme
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
    
    while running:
        fps, process_name = rtss_manager.get_fps_for_active_window()
        #logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")
        
        if process_name is not None and process_name != "DynamicFPSLimiter.exe":
            last_process_name = process_name #Make exception for DynamicFPSLimiter.exe and pythonw.exe
            dpg.set_value("LastProcess", last_process_name)
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
        if gpuUsage and process_name not in {"pythonw.exe"}:#, "DynamicFPSLimiter.exe", "python.exe"}:
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
            if fps and process_name not in {"pythonw.exe"}:#, "DynamicFPSLimiter.exe", "python.exe"}:
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
    global running, elapsed_time # Make sure elapsed_time is global

    start_time = time.time()
    while running:
# Calculate elapsed time SINCE start_time
        elapsed_time = time.time() - start_time

        gpuUsage = gpu_monitor.gpu_percentile
        cpuUsage = cpu_monitor.cpu_percentile

        # CALL update_plot_usage with the current time and usage values
        update_plot_usage(elapsed_time, gpuUsage, cpuUsage)

        time.sleep(0.2) # This loop runs every 0.2 seconds

def update_tooltip_setting(sender, app_data, user_data):
    global ShowTooltip, input_field_keys, tooltips
    ShowTooltip = app_data
    settings_config["Preferences"]["ShowTooltip"] = str(app_data)
    with open(settings_path, 'w') as f:
        settings_config.write(f)
    logger.add_log(f"Tooltip visibility set to: {ShowTooltip}")
    logger.add_log(f"Applying tooltip visibility: {ShowTooltip}")

    for key in tooltips.keys():
        parent_tag = ""
        # Determine the PARENT tag first
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

# Callback for the exit FPS limit input
def update_exit_fps_value(sender, app_data, user_data):
    global globallimitonexit_fps # Ensure this global variable exists and is loaded
    new_value = app_data
    # Optional: Add validation (e.g., ensure it's within a reasonable range)
    if isinstance(new_value, int) and new_value > 0:
        globallimitonexit_fps = new_value
        settings_config["GlobalSettings"]["globallimitonexit_fps"] = str(new_value)
        with open(settings_path, 'w') as f:
            settings_config.write(f)
        logger.add_log(f"Global Limit on Exit FPS value set to: {globallimitonexit_fps}")
    else:
        logger.add_log(f"Invalid value entered for Global Limit on Exit FPS: {app_data}. Reverting.")
        # Revert UI to the current global value if input is invalid
        dpg.set_value(sender, globallimitonexit_fps)

# Function to close all active processes and exit the GUI
def exit_gui():
    global running, rtss_manager, monitoring_thread, plotting_thread, globallimitonexit_fps, GlobalLimitonExit

    if GlobalLimitonExit:
        rtss_cli.set_property("Global", "FramerateLimit", int(globallimitonexit_fps))

    running = False # Signal monitoring_loop to stop
    if rtss_manager:
        rtss_manager.stop_monitor_thread()  # Signal RTSS monitor thread to stop
    if gpu_monitor:
        gpu_monitor.cleanup()  # Clean up GPU monitor
    if cpu_monitor:
        cpu_monitor.stop()  # Stop CPU monitor
    if dpg.is_dearpygui_running():
        dpg.destroy_context() # Close Dear PyGui
    
        # Wait for the monitoring thread to finish
    if monitoring_thread and monitoring_thread.is_alive():
        logger.add_log("Waiting for monitoring thread to stop...")
        monitoring_thread.join(timeout=0.1) # Wait up to 2 seconds
        if monitoring_thread.is_alive():
            logger.add_log("Warning: Monitoring thread did not stop gracefully.")
        else:
            logger.add_log("Monitoring thread stopped.")
    if plotting_thread and plotting_thread.is_alive():
        logger.add_log("Waiting for monitoring thread to stop...")
        plotting_thread.join(timeout=0.1) # Wait up to 2 seconds
        if plotting_thread.is_alive():
            logger.add_log("Warning: Plotting thread did not stop gracefully.")
        else:
            logger.add_log("Plotting thread stopped.")


# Main Window

# Define keys used for input fields (used to construct tooltip tags)
input_field_keys = ["maxcap", "mincap", "capstep", "gpucutofffordecrease", "gpucutoffforincrease", "cpucutofffordecrease", "cpucutoffforincrease"]

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
    "start_stop_button": "Starts maintaining the FPS cap dynamically based on GPU utilization. Green = RTSS running. Red = RTSS not found.",
    "luid_button": "Detects the render GPU based on highest 3D engine utilization, and sets it as the target GPU for FPS limiting. Click again to deselect.",
    "exit_fps_input": "The specific FPS limit to apply globally when the application exits, if 'Set Global FPS Limit on Exit' is checked.",
    "SaveToProfile": "Saves the current settings to the selected profile. This allows you to quickly switch between different configurations.",
    "Reset_Default": "Resets all settings to the program's default values. This is useful if you want to start fresh or if you encounter issues."
}

# GUI setup
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
with dpg.theme(tag="rounded_widget_theme"):
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3.0)  # Set corner rounding to 10.0
        dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55)) 
        #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0.0, 1.0, category=dpg.mvThemeCat_Core)
        #dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 150, 250))  # Button color
        #dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 170, 255))  # Hover color
        #dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 190, 255))  # Active color

    # Customize specific widget types
    with dpg.theme_component(dpg.mvInputInt):
        #dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (100, 100, 100))  # Background color
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (150, 150, 150))  # Hovered background color
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (200, 200, 200))  # Active background color

    with dpg.theme_component(dpg.mvInputText):
        #dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (100, 100, 100))  # Background color
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (150, 150, 150))  # Hovered background color
        dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (200, 200, 200))  # Active background color

    with dpg.theme_component(dpg.mvCheckbox):
        #dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (100, 100, 100))  # Background color
        #dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (150, 150, 150))  # Hovered background color
        #dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (200, 200, 200))  # Active background color
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
        dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135))  # Blue color background
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (6, 96, 158))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 105, 176))

background_colour = (37, 37, 38)  # Default grey background

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
    dpg.add_spacer(height=1)
    with dpg.tab_bar():
        with dpg.tab(label="Profile Settings", tag="tab1"):
            with dpg.child_window(height=135):
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

        with dpg.tab(label="Preferences", tag="tab2"):
            with dpg.child_window(height=135):
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
            with dpg.child_window(tag="LogWindow", autosize_x=True, height=135, border=True):
                #dpg.add_text("", tag="LogText", tracked = True, track_offset = 1.0)
                dpg.add_spacer(height=2)
                dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=110)

                with dpg.theme(tag="transparent_input_theme"):
                    with dpg.theme_component(dpg.mvInputText):
                        dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                        dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

                dpg.bind_item_theme("LogText", "transparent_input_theme")

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
            with dpg.plot_axis(dpg.mvYAxis, label="GPU/CPU Usage (%)", tag="y_axis_left", no_gridlines=False) as y_axis_left:
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

gpu_monitor = GPUUsageMonitor(lambda: luid, lambda: running, logger, dpg, interval=0.1, max_samples=20, percentile=70)
#logger.add_log(f"Current highed GPU core load: {gpu_monitor.gpu_percentile}%")

#usage, luid = gpu_monitor.get_gpu_usage(engine_type="engtype_3D")
#logger.add_log(f"Current Top LUID: {luid}, 3D engine usage: {usage}%")

cpu_monitor = CPUUsageMonitor(lambda: running, logger, dpg, interval=0.1, max_samples=20, percentile=70)
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

