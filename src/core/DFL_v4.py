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

from core import PyGPU as gpu
from core import logger
from core.rtss_interface import RTSSInterface
from core.cpu_monitor import CPUUsageMonitor

# Always get absolute path to EXE or script location
Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# Ensure the config folder exists in the parent directory of Base_dir
config_dir = os.path.join(os.path.dirname(Base_dir), "config")
parent_dir = os.path.dirname(Base_dir)
os.makedirs(config_dir, exist_ok=True)

# Paths to configuration files
settings_path = os.path.join(config_dir, "settings.ini")
profiles_path = os.path.join(config_dir, "profiles.ini")
rtss_cli_path = os.path.join(Base_dir, "assets/rtss-cli.exe")
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
        'ShowPlot': 'True',
        'ShowTooltip': 'True'
    }
    # Add GlobalSettings section
    settings_config["GlobalSettings"] = {
        'delaybeforedecrease': '2',
        'delaybeforeincrease': '2',
        'minvalidgpu': '20',
        'minvalidfps': '20'
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
        'usagecutofffordecrease': '80',
        'usagecutoffforincrease': '70'
    }
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)



# Function to get values with correct types
def get_setting(key, value_type=int):
    """Get setting from appropriate config section based on key type."""
    if key in ["delaybeforedecrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        return value_type(settings_config["GlobalSettings"].get(key, Default_settings_original[key]))
    return value_type(profiles_config["Global"].get(key, Default_settings_original[key]))

ShowPlot = str(settings_config["Preferences"].get("ShowPlot", "True")).strip().lower() == "true"
ShowTooltip = str(settings_config["Preferences"].get("ShowTooltip", "True")).strip().lower() == "true"

# Default viewport size
Viewport_width = 550
Viewport_full_height = 700
Plot_height = 220  # Height of the plot when shown

if ShowPlot:
    global Viewport_height
    ShowPlotBoolean = True
    Viewport_height = Viewport_full_height
else:
    ShowPlotBoolean = False
    Viewport_height = Viewport_full_height - Plot_height

# Default values
Default_settings_original = {
    "maxcap": 60,
    "mincap": 30,
    "capstep": 5,
    "usagecutofffordecrease": 80,
    "delaybeforedecrease": 2,
    "usagecutoffforincrease": 70,
    "delaybeforeincrease": 2,
    "minvalidgpu": 20,
    "minvalidfps": 20
}

Default_settings = {key: get_setting(key, str if isinstance(Default_settings_original[key], str) else int) for key in Default_settings_original}

def save_to_profile():
    # Get current selected profile from the dropdown
    selected_profile = dpg.get_value("profile_dropdown")
    
    # Only proceed if a profile is selected
    if selected_profile:
        # Update profile-specific settings
        for key in ["maxcap", "mincap", "capstep",
                "usagecutofffordecrease", "usagecutoffforincrease"]:
            value = dpg.get_value(f"input_{key}")  # Get value from input field
            profiles_config[selected_profile][key] = str(value)  # Store as string in ini file
        
        # Update global settings
        for key in ["delaybeforedecrease", "delaybeforeincrease", 
                   "minvalidgpu", "minvalidfps"]:
            settings_config["GlobalSettings"][key] = str(get_setting(key))
        
        # Save both configs
        with open(profiles_path, "w") as configfile:
            profiles_config.write(configfile)
        with open(settings_path, "w") as configfile:
            settings_config.write(configfile)
            
        logger.add_log(f"> Settings saved to profile: {selected_profile}")
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
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        dpg.set_value(f"input_{key}", profiles_config[profile_name][key])
    update_global_variables()
    dpg.set_value("new_profile_input", "")

def save_profile(profile_name):
    profiles_config[profile_name] = {}
    # Save input fields
    for key in ["maxcap", "mincap", "capstep",
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        profiles_config[profile_name][key] = str(dpg.get_value(f"input_{key}"))
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)
    update_profile_dropdown()

def add_new_profile_callback():
    new_name = dpg.get_value("new_profile_input")
    if new_name and new_name not in profiles_config:
        save_profile(new_name)
        dpg.set_value("new_profile_input", "")
        logger.add_log(f"> New profile created: {new_name}")
    else:
        logger.add_log("> Profile name is empty or already exists.")

def add_process_profile_callback():
    new_name = dpg.get_value("LastProcess")
    if new_name and new_name not in profiles_config:
        save_profile(new_name)
        logger.add_log(f"> New profile created: {new_name}")
    else:
        logger.add_log("> Profile name is empty or already exists.")

def delete_selected_profile_callback():
    
    global current_profile
    
    profile_to_delete = dpg.get_value("profile_dropdown")
    if profile_to_delete == "Global":
        logger.add_log("> Cannot delete the default 'Global' profile.")
        return
    if profile_to_delete in profiles_config:
        profiles_config.remove_section(profile_to_delete)
        with open(profiles_path, 'w') as f:
            profiles_config.write(f)
        update_profile_dropdown(select_first=True)
        for key in profiles_config["Global"]:
            dpg.set_value(f"input_{key}", profiles_config["Global"][key])
        update_global_variables()
        logger.add_log(f"> Deleted profile: {profile_to_delete}")
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
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        globals()[key] = int(dpg.get_value(f"input_{key}"))  # Convert to int

def start_stop_callback():
    global running, maxcap, current_profile
    running = not running
    dpg.configure_item("start_stop_button", label="Stop" if running else "Start")
    apply_current_input_values()
    
    # Reset variables to zero or their default state
    global fps_values, CurrentFPSOffset, fps_mean, gpu_values
    fps_values = []
    CurrentFPSOffset = 0
    fps_mean = 0
    gpu_values = []

    # Freeze input fields

    for key in ["maxcap", "mincap", "capstep", 
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        dpg.configure_item(f"input_{key}", enabled=not running)

    if running:
        # Initialize RTSS
        rtss_manager.run_rtss_cli(["limiter:set", "1"])
        rtss_manager.run_rtss_cli(["property:set", current_profile, "FramerateLimit", str(maxcap)])
        
        # Apply current settings and start monitoring
        
        time_series.clear()
        gpu_usage_series.clear()
        fps_series.clear()
        cap_series.clear()
        
        # Start monitoring thread
        threading.Thread(target=monitoring_loop, daemon=True).start()
        logger.add_log("> Monitoring started")
    else:
        reset_stats()
        CurrentFPSOffset = 0
        logger.add_log("> Monitoring stopped")

def quick_save_settings():
    for key in ["maxcap", "mincap", "capstep", 
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        settings[key] = dpg.get_value(f"input_{key}")
    update_global_variables()
    logger.add_log("> Settings quick saved")

def quick_load_settings():
    for key in ["maxcap", "mincap", "capstep", 
                "usagecutofffordecrease", "usagecutoffforincrease"]:
        dpg.set_value(f"input_{key}", settings[key])
    update_global_variables()
    logger.add_log("> Settings quick loaded")

def enable_plot_callback(sender, app_data): #Currently not in use
    dpg.configure_item("plot_section", show=app_data)
    
    # Get current viewport size
    current_width, current_height = dpg.get_viewport_width(), dpg.get_viewport_height()
    
    # Compute new height based on plot visibility
    new_height = current_height + Plot_height if app_data else current_height - Plot_height

    dpg.set_viewport_height(new_height)
    
def reset_stats():
    
    dpg.configure_item("gpu_usage_series", label="GPU: --")
    dpg.configure_item("fps_series", label="FPS: --")
    dpg.configure_item("cap_series", label="FPS Cap: --")

def reset_to_program_default():
    
    global Default_settings_original
    
    for key in ["maxcap", "mincap", "capstep"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    for key in ["usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    logger.add_log("> Settings reset to program default")  

time_series = []
gpu_usage_series = []
fps_series = []
cap_series = []  # New series for CurrentFPSOffset
max_points = 60  # Keep last 60 seconds of data

def update_plot(time_val, gpu_val, fps_val, cap_val):
    
    global time_series, gpu_usage_series, fps_series, cap_series
    global max_points, mincap, maxcap, capstep, usagecutofffordecrease, usagecutoffforincrease
    
    if len(time_series) > max_points:
        time_series.pop(0)
        gpu_usage_series.pop(0)
        fps_series.pop(0)
        cap_series.pop(0)
    
    if gpu_val is None:
        gpu_val = 0
    
    time_series.append(time_val)
    gpu_usage_series.append(gpu_val)
    fps_series.append(fps_val)
    cap_series.append(cap_val)

    dpg.set_value("gpu_usage_series", [time_series, gpu_usage_series])
    dpg.set_value("fps_series", [time_series, fps_series])
    dpg.set_value("cap_series", [time_series, cap_series])  
    
    dpg.set_axis_limits_auto("x_axis")  # Keep X-axis dynamic
    dpg.set_axis_limits("x_axis", time_series[0], time_series[-1] + 1) if time_series else None
    if time_series:
        dpg.set_axis_limits("x_axis", time_series[0], time_series[-1] + 1)
        
        # Update static lines to extend across the entire X range
        dpg.set_value("line1", [[time_series[0], time_series[-1] + 1], [usagecutofffordecrease, usagecutofffordecrease]])
        dpg.set_value("line2", [[time_series[0], time_series[-1] + 1], [usagecutoffforincrease, usagecutoffforincrease]])
    else:
        None

    dpg.set_axis_limits("y_axis_right", mincap - capstep, maxcap + capstep) 

luid_selected = False  # default state
luid = "All" # Placeholder for LUID

def toggle_luid_selection():
    global luid_selected, luid

    if not luid_selected:
        # First click: detect top LUID
        usage, luid = monitor.get_gpu_usage(engine_type="engtype_3D")
        if luid:
            logger.add_log(f"> Tracking LUID: {luid} | Current 3D engine Utilization: {usage}%")
            dpg.configure_item("luid_button", label="Revert to all GPUs")
            luid_selected = True
        else:
            logger.add_log("> Failed to detect active LUID.")
    else:
        # Second click: deselect
        luid = "All"
        logger.add_log("> Tracking all GPU engines.")
        dpg.configure_item("luid_button", label="Detect Render GPU")
        luid_selected = False

fps_values = []
gpu_values = []
CurrentFPSOffset = 0
fps_mean = 0

def monitoring_loop():
    global running, fps_values, CurrentFPSOffset, fps_mean, gpu_values, current_profile
    global mincap, maxcap, capstep, usagecutofffordecrease, delaybeforedecrease, usagecutoffforincrease, delaybeforeincrease, minvalidgpu, minvalidfps
    global max_points, minvalidgpu, minvalidfps, luid_selected, luid

    start_time = time.time()
    last_process_name = None
    min_ft = mincap - capstep
    max_ft = maxcap + capstep
    
    while running:
        fps, process_name = rtss_manager.get_fps_for_active_window()
        
        if process_name != None:
            last_process_name = process_name #Make exception for DynamicFPSLimiter.exe and pythonw.exe
            
        if fps:
            if len(fps_values) > 2:
                fps_values.pop(0)
            fps_values.append(fps)
            fps_mean = sum(fps_values) / len(fps_values)
        
        # Get GPU usage using the new monitor
        if luid_selected:
            gpuUsage, target_luid = monitor.get_gpu_usage(luid)
        else:
            gpuUsage, target_luid = monitor.get_gpu_usage()

        if len(gpu_values) > (max(delaybeforedecrease, delaybeforeincrease)+1):
            gpu_values.pop(0)
        gpu_values.append(gpuUsage)

        # Get elapsed time in seconds
        elapsed_time = time.time() - start_time

        # To prevent loading screens from affecting the fps cap
        if gpuUsage and process_name not in {"pythonw.exe", "DynamicFPSLimiter.exe", "python.exe"}:
            if gpuUsage > minvalidgpu and fps_mean > minvalidfps: 
                # If GPU usage is greater than (= usagecutofffordecrease%) for at least (= delaybeforedecrease) consecutive seconds
                if CurrentFPSOffset > (mincap - maxcap):
                    if len(gpu_values) >= delaybeforedecrease and all(value >= usagecutofffordecrease for value in gpu_values[-delaybeforedecrease:]):
                        X = math.ceil(((maxcap + CurrentFPSOffset) - (fps_mean)) / capstep)
                        print(f"X {X}")
                        if X > 0:
                            CurrentFPSOffset -= (capstep * X)
                        else:
                            CurrentFPSOffset -= capstep
                        rtss_manager.run_rtss_cli(["property:set", current_profile, "FramerateLimit", str(maxcap+CurrentFPSOffset)])
                if CurrentFPSOffset < 0:
                    if len(gpu_values) >= delaybeforeincrease and all(value <= usagecutoffforincrease for value in gpu_values[-delaybeforeincrease:]):
                        CurrentFPSOffset += capstep
                        rtss_manager.run_rtss_cli(["property:set", current_profile, "FramerateLimit", str(maxcap+CurrentFPSOffset)])

        if running:
            # Update legend labels with current values
            dpg.configure_item("gpu_usage_series", label=f"GPU: {gpuUsage}%")
            dpg.configure_item("fps_series", label=f"FPS: {fps:.1f}" if fps else "FPS: --")
            dpg.configure_item("cap_series", label=f"FPS Cap: {maxcap + CurrentFPSOffset}")

            # Update plot if fps is valid
            if fps and process_name not in {"pythonw.exe", "DynamicFPSLimiter.exe", "python.exe"}:
                # Scaling FPS value to fit 0-100 axis
                scaled_fps = ((fps - min_ft)/(max_ft - min_ft))*100
                scaled_cap = ((maxcap + CurrentFPSOffset - min_ft)/(max_ft - min_ft))*100
                update_plot(elapsed_time, gpuUsage, scaled_fps, scaled_cap)
        if process_name:
            last_process_name = process_name

        time.sleep(0.9)

# Function to close all active processes and exit the GUI
def exit_gui():
    global running, rtss_manager, monitor
    running = False # Signal monitoring_loop to stop
    if rtss_manager:
        rtss_manager.stop_monitor_thread()  # Signal RTSS monitor thread to stop
    if monitor:
        monitor.cleanup()  # Clean up GPU monitor
    if cpu_monitor:
        cpu_monitor.stop()  # Stop CPU monitor
    if dpg.is_dearpygui_running():
        dpg.destroy_context() # Close Dear PyGui

# Main Window

tooltips = {
    "maxcap": "Defines the maximum FPS limit for the game.",
    "mincap": "Specifies the minimum FPS limit that may be reached. For optimal performance, set this to the lowest value you're comfortable with.",
    "capstep": "Indicates the increment size for adjusting the FPS cap. Smaller step sizes provide finer control",
    "usagecutofffordecrease": "Sets the upper threshold for GPU usage. If GPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "delaybeforedecrease": "Specifies how many times in a row GPU usage must exceed the upper threshold before the FPS cap begins to drop.",
    "usagecutoffforincrease": "Defines the lower threshold for GPU usage. If GPU usage falls below this value, the FPS cap will increase to improve performance.",
    "delaybeforeincrease": "Specifies how many times in a row GPU usage must fall below the lower threshold before the FPS cap begins to rise.",
    "minvalidgpu": "Sets the minimum valid GPU usage percentage required for adjusting the FPS. If the GPU usage is below this threshold, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "minvalidfps": "Defines the minimum valid FPS required for adjusting the FPS. If the FPS falls below this value, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "Quick": "Saves and loads input values from memory. This is temporary storage, useful for testing and fine-tuning configurations.",
    "Start": "Starts maintaining the FPS cap dynamically based on GPU utilization",
    "luid_button": "Detects the render GPU based on highest 3D engine utilization, and sets it as the target GPU for FPS limiting. Click again to deselect."
}

# GUI setup
dpg.create_context()

with dpg.font_registry():
    try:
        default_font = dpg.add_font(font_path, 16)
        if default_font:
            dpg.bind_font(default_font)
    except Exception as e:
        logger.add_log(f"> Failed to load system font: {e}")
        # Will use DearPyGui's default font as fallback

# Create themes for RTSS status
with dpg.theme(tag="rtss_running_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 100, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 120, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 140, 0))

with dpg.theme(tag="rtss_not_running_theme"):
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (120, 0, 0))
        dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (140, 0, 0))

with dpg.window(label="Dynamic FPS Limiter", tag="Primary Window"):
    
    # Title and Start/Stop Button
    with dpg.group(horizontal=True):
        dpg.add_text("Dynamic FPS Limiter v4.0.0")
        dpg.add_spacer(width=30)
        dpg.add_button(label="Detect Render GPU", callback=toggle_luid_selection, tag="luid_button", width=150)
        with dpg.tooltip("luid_button", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["luid_button"], wrap = 200)
        dpg.add_spacer(width=30)
        dpg.add_button(label="Start", tag="start_stop_button", callback=start_stop_callback, width=50)
        with dpg.tooltip("start_stop_button", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["Start"], wrap = 200)
        dpg.add_button(label="Exit", callback=exit_gui, width=50)  # Exit button

    # Profiles
    with dpg.child_window(width=-1, height=135):
        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=55)
            dpg.add_table_column(init_width_or_weight=120)
            dpg.add_table_column(init_width_or_weight=60)

            # First row
            with dpg.table_row():
                dpg.add_text("Select Profile:")
                dpg.add_combo(tag="profile_dropdown", callback=load_profile_callback, width=240, default_value="Global")
                dpg.add_button(label="Delete Profile", callback=delete_selected_profile_callback, width=120)

            # Second row
            with dpg.table_row():
                dpg.add_text("New RTSS Profile:")
                dpg.add_input_text(tag="new_profile_input", width=240)
                dpg.add_button(label="Add Profile", callback=add_new_profile_callback, width=120)

        dpg.add_spacer(height=3)        
        with dpg.group(horizontal=True):
            dpg.add_text("Last active process:")
            dpg.add_spacer(width=250)
            dpg.add_button(label="Add process to Profiles", callback=add_process_profile_callback)
        dpg.add_spacer(height=1)
        dpg.add_input_text(tag="LastProcess", multiline=False, readonly=True, width=-1)    
            
    #Settings
    with dpg.group(horizontal=True):
        dpg.add_spacer(height=3)
        with dpg.group(horizontal=False):
            dpg.add_spacer(height=3)
            dpg.add_text("Settings:")
        dpg.add_spacer(width=65)
        with dpg.child_window(width=160, height=140, border=False):
            dpg.add_spacer(height=3)
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_fixed=True)  # Column for labels
                dpg.add_table_column(width_fixed=True)  # Column for input boxes
                
                for label, key in [("Max FPS limit:", "maxcap"), 
                                   ("Min FPS limit:", "mincap"),
                                   ("Frame rate step:", "capstep"),
                                   ("Upper GPU limit:", "usagecutofffordecrease"),
                                   ("Lower GPU limit:", "usagecutoffforincrease")]:
                    with dpg.table_row():
                        dpg.add_text(label)
                        dpg.add_input_text(tag=f"input_{key}", default_value=str(settings[key]), width=50)
                        with dpg.tooltip(f"input_{key}", show=ShowTooltip, delay=1):
                            dpg.add_text(tooltips[key], wrap = 200)

        with dpg.child_window(width=240, height=140, border=False):
            dpg.add_spacer(height=6)
            with dpg.group(horizontal=False):
                with dpg.tooltip(parent=dpg.last_item(), show=ShowTooltip, delay=1):
                    dpg.add_text(tooltips["Quick"], wrap = 200)
                dpg.add_button(label="Quick Save", callback=quick_save_settings, width=200)
                dpg.add_button(label="Quick Load", callback=quick_load_settings, width=200)
                dpg.add_button(label="Reset Settings to Default", callback=reset_to_program_default, width=200)
                dpg.add_spacer(height=3)
                dpg.add_button(label="Save Settings to Profile", callback=save_to_profile, width=200)

    # Third Row: Plot Section
    with dpg.child_window(width=-1, height=Plot_height, show=ShowPlotBoolean):
        with dpg.plot(height=200, width=-1, tag="plot"):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis")
            dpg.add_plot_legend(location=dpg.mvPlot_Location_North, horizontal=True, 
                              no_highlight_item=True, no_highlight_axis=True, outside=True)

            # Left Y-axis for GPU Usage
            with dpg.plot_axis(dpg.mvYAxis, label="GPU Usage (%)", tag="y_axis_left", no_gridlines=False) as y_axis_left:
                dpg.add_line_series([], [], label="GPU: --", parent=y_axis_left, tag="gpu_usage_series")
                # Add static horizontal dashed lines
                dpg.add_line_series([], [usagecutofffordecrease, usagecutofffordecrease], parent=y_axis_left, tag="line1")
                dpg.add_line_series([], [usagecutoffforincrease, usagecutoffforincrease], parent=y_axis_left, tag="line2")
            
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

# Dynamic log
    with dpg.group(horizontal=True):
        dpg.add_text("Log:")
        # Scrollable child window for log output
        with dpg.child_window(tag="LogWindow", autosize_x=True, height=105, border=False):
            #dpg.add_text("", tag="LogText", tracked = True, track_offset = 1.0)
            dpg.add_spacer(height=2)
            dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=85)

            with dpg.theme(tag="transparent_input_theme"):
                with dpg.theme_component(dpg.mvInputText):
                    dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

            dpg.bind_item_theme("LogText", "transparent_input_theme")

# Setup and Run GUI
update_profile_dropdown(select_first=True)

logger.add_log("Initializing...")
monitor = gpu.GPUMonitor()  # Create a single GPU monitor instance
usage, luid = monitor.get_gpu_usage(engine_type="engtype_3D")
logger.add_log(f"Current Top LUID: {luid}, 3D engine usage: {usage}%")

cpu_monitor = CPUUsageMonitor(logger, dpg, interval=0.1, max_samples=20, percentile=70)

logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")

logger.add_log("Initialized successfully.")

# Assuming logger and dpg are initialized, and rtss_cli_path is defined
rtss_manager = RTSSInterface(rtss_cli_path, logger, dpg)
if rtss_manager:
    rtss_manager.start_monitor_thread()
    rtss_manager.run_rtss_cli(["limiter:set", "1"]) # Ensure limiter is enabled

dpg.create_viewport(title="Dynamic FPS Limiter", width=Viewport_width, height=Viewport_height, resizable=False)
dpg.set_viewport_resizable(False)
dpg.set_viewport_max_width(Viewport_width)
dpg.set_viewport_max_height(Viewport_height)
dpg.set_viewport_small_icon(icon_path)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)
dpg.start_dearpygui()

