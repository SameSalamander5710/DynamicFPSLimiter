# DFL_v4.py
# Dynamic FPS Limiter v4.1.0

import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import dearpygui.dearpygui as dpg
import threading
import time
import math
import os
import sys
import csv
import pywinstyles

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
from core.themes import create_themes
from core.config_manager import ConfigManager
from core.tooltips import get_tooltips, add_tooltip, apply_all_tooltips, update_tooltip_setting
from core.warning import get_active_warnings
from core.autostart import AutoStartManager

# Always get absolute path to EXE or script location
Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cm = ConfigManager(logger, dpg, Base_dir)
tooltips = get_tooltips()

# Ensure the config folder exists in the parent directory of Base_dir
parent_dir = os.path.dirname(Base_dir)

# Paths to configuration files
rtss_dll_path = os.path.join(Base_dir, "assets/rtss.dll")
error_log_file = os.path.join(parent_dir, "error_log.txt")
icon_path = os.path.join(Base_dir, 'assets/DynamicFPSLimiter.ico')
font_path = os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf") #segoeui, Verdana, Tahoma, Calibri, micross
bold_font_path = os.path.join(os.environ["WINDIR"], "Fonts", "segoeuib.ttf")
faq_path = os.path.join(Base_dir, "assets/faqs.csv")

logger.init_logging(error_log_file)
rtss_manager = None

questions = []
FAQs = {}

with open(faq_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for idx, row in enumerate(reader, start=1):
        key = f"faq_{idx}"
        questions.append(row["question"])
        FAQs[key] = row["answer"]

def sort_customfpslimits_callback(sender, app_data, user_data):
    # Get the current value from the input field
    value = dpg.get_value("input_customfpslimits")
    # Parse to set of ints
    try:
        numbers = set(int(x.strip()) for x in value.split(",") if x.strip().isdigit())
        numbers = sorted(x for x in numbers if x > 0) 
        sorted_str = ", ".join(str(x) for x in sorted(numbers))
        dpg.set_value("input_customfpslimits", sorted_str)
    except Exception:
        # If parsing fails, do nothing or optionally reset to previous valid value
        pass

def current_stepped_limits():

    maximum = int(dpg.get_value("input_maxcap"))
    minimum = int(dpg.get_value("input_mincap"))
    step = int(dpg.get_value("input_capstep"))
    ratio = int(dpg.get_value("input_capratio"))

    use_custom  = dpg.get_value("input_capmethod")
    #logger.add_log(f"Stepped limits: {make_stepped_values(maximum, minimum, step)}")
    #logger.add_log(f"Ratio limits: {make_ratioed_values(maximum, minimum, ratio)}")
    #logger.add_log(f"Method selection: {use_custom}")

    if use_custom == "custom":
        custom_limits = dpg.get_value("input_customfpslimits")
        if custom_limits:
            try:
                custom_limits = set(int(x.strip()) for x in custom_limits.split(",") if x.strip().isdigit())
                custom_limits = sorted(x for x in custom_limits if x > 0)
                return custom_limits
            except Exception:
                logger.add_log("Error parsing custom FPS limits, using default stepped limits.")
    elif use_custom == "step":
        return make_stepped_values(maximum, minimum, step)
    elif use_custom == "ratio":
        return make_ratioed_values(maximum, minimum, ratio)
    #logger.add_log(f"Default stepped limits: {maximum}, {minimum}, {step}")
    #logger.add_log(f"Stepped limits: {make_stepped_values(maximum, minimum, step)}")

def make_stepped_values(maximum, minimum, step):
    values = list(range(maximum, minimum - 1, -step))
    if minimum not in values:
        values.append(minimum)
    return sorted(set(values))

def make_ratioed_values(maximum, minimum, ratio):
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

last_fps_limits = []

def update_fps_cap_visualization():

    global last_fps_limits
    
    fps_limits = current_stepped_limits()
    #logger.add_log(f"FPS limits: {fps_limits}")

    # Check if fps_limits has changed
    if fps_limits == last_fps_limits:
        return  # Exit if no change
    
    # Store new fps_limits for next comparison
    last_fps_limits = fps_limits.copy()

    # Clear existing items in drawlist
    dpg.delete_item("Foreground")
    
    with dpg.draw_layer(tag="Foreground", parent="fps_cap_drawlist"):
        # Get current FPS limits
        
        if fps_limits:
            draw_width = Viewport_width - 67  # Width of drawlist
            layer2_height = 30  # Height of drawlist
            margin = 10  # Margin around drawlist
            
            # Calculate min and max for scaling
            min_fps = min(fps_limits)
            max_fps = max(fps_limits)
            fps_range = max_fps - min_fps
            
            # Draw rectangles for each FPS limit
            for cap in fps_limits:
                # Map the FPS cap value to the drawlist width
                x_pos = margin + int((cap - min_fps) / fps_range * (draw_width - margin))
                y_pos = layer2_height // 2
                
                # Draw FPS marker
                dpg.draw_circle(
                    (x_pos, y_pos),  # Center point
                    7,  # Radius
                    #thickness=2,
                    #color=(128, 128, 128),  # Border color (grey)
                    fill=(200, 200, 200),  # Fill color (white)
                    parent="Foreground"
                )
                
                if len(fps_limits) < 20:
                    # Add FPS value text above rectangle
                    dpg.draw_text(
                        (x_pos - 10, y_pos + 8),
                        str(cap),
                        color=(200, 200, 200),
                        size=16,
                        parent="Foreground"
                    )

def copy_from_plot_callback():
    
    fps_limits = sorted(set(current_stepped_limits()))
    fps_limits_str = ", ".join(str(int(round(x))) for x in fps_limits)
    dpg.set_value("input_customfpslimits", fps_limits_str)

def current_method_callback(sender=None, app_data=None, user_data=None):

    method = app_data if app_data else dpg.get_value("input_capmethod")

    dpg.bind_item_theme("input_capratio", "enabled_text_theme") if method == "ratio" else dpg.bind_item_theme("input_capratio", "disabled_text_theme")
    dpg.bind_item_theme("label_capratio", "enabled_text_theme") if method == "ratio" else dpg.bind_item_theme("label_capratio", "disabled_text_theme")
    dpg.bind_item_theme("label_capstep", "enabled_text_theme") if method == "step" else dpg.bind_item_theme("label_capstep", "disabled_text_theme")
    dpg.bind_item_theme("input_capstep", "enabled_text_theme") if method == "step" else dpg.bind_item_theme("input_capstep", "disabled_text_theme")
    dpg.bind_item_theme("input_customfpslimits", "enabled_text_theme") if method == "custom" else dpg.bind_item_theme("input_customfpslimits", "disabled_text_theme")
    dpg.bind_item_theme("label_maxcap", "disabled_text_theme") if method == "custom" else dpg.bind_item_theme("label_maxcap", "enabled_text_theme")
    dpg.bind_item_theme("label_mincap", "disabled_text_theme") if method == "custom" else dpg.bind_item_theme("label_mincap", "enabled_text_theme")
    dpg.bind_item_theme("input_maxcap", "disabled_text_theme") if method == "custom" else dpg.bind_item_theme("input_maxcap", "enabled_text_theme")
    dpg.bind_item_theme("input_mincap", "disabled_text_theme") if method == "custom" else dpg.bind_item_theme("input_mincap", "enabled_text_theme")
    
    logger.add_log(f"Method selection changed: {method}")

def tooltip_checkbox_callback(sender, app_data, user_data):
    update_tooltip_setting(dpg, sender, app_data, user_data, tooltips, cm, logger)

def autostart_checkbox_callback(sender, app_data, user_data):
    cm.update_launch_on_startup_setting(sender, app_data, user_data)

    is_checked = dpg.get_value("autostart_checkbox")
    if is_checked:
        autostart.create() 
    else:
        autostart.delete() 

ShowTooltip = str(cm.settings_config["Preferences"].get("ShowTooltip", "True")).strip().lower() == "true"
cm.globallimitonexit = str(cm.settings_config["Preferences"].get("globallimitonexit", "True")).strip().lower() == "true"
cm.profileonstartup = str(cm.settings_config["Preferences"].get("profileonstartup", "True")).strip().lower() == "true"
cm.launchonstartup = str(cm.settings_config["Preferences"].get("launchonstartup", "True")).strip().lower() == "true"

#Check: Do I need this after setattr?
for key in cm.settings_config["GlobalSettings"]:
    value_type = cm.key_type_map.get(key, str)
    value = cm.get_setting(key, value_type)
    if value is not None:
        globals()[key] = value

# Default viewport size
Viewport_width = 625
Viewport_height = 700

running = False  # Flag to control the monitoring loop

cm.update_global_variables()

def start_stop_callback(sender, app_data, user_data):

    cm = user_data

    global running
    running = not running
    dpg.configure_item("start_stop_button", label="Stop" if running else "Start")
    dpg.bind_item_theme("start_stop_button", "stop_button_theme" if running else "start_button_theme")
    cm.apply_current_input_values()
    
    # Reset variables to zero or their default state
    global fps_values, CurrentFPSOffset, fps_mean, gpu_values, cpu_values
    fps_values = []
    CurrentFPSOffset = 0
    fps_mean = 0
    gpu_values = []
    cpu_values = []

    # Freeze input fields
    for key in cm.input_field_keys:
        dpg.configure_item(f"input_{key}", enabled=not running)

    for tag in cm.input_button_tags:
        dpg.configure_item(tag, enabled=not running)

    if running:
        # Initialize RTSS
        rtss_cli.enable_limiter()
        
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
        
        logger.add_log("Monitoring stopped")
    logger.add_log(f"Custom FPS limits: {current_stepped_limits()}")
    rtss_cli.set_property(cm.current_profile, "FramerateLimit", int(max(current_stepped_limits())))

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
    global max_points

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

    fps_limit_list = current_stepped_limits()

    current_mincap = min(fps_limit_list)
    current_maxcap = max(fps_limit_list)
    min_ft = current_mincap - round((current_maxcap - current_mincap) * 0.1)
    max_ft = current_maxcap + round((current_maxcap - current_mincap) * 0.1)

    dpg.set_axis_limits("y_axis_right", min_ft, max_ft) 

def update_plot_usage(time_val, gpu_val, cpu_val):
   
    global time_series, gpu_usage_series, cpu_usage_series
    global max_points# Add needed globals
    
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
        dpg.set_value("line1", [[start_x, end_x + 1], [cm.gpucutofffordecrease, cm.gpucutofffordecrease]])
        dpg.set_value("line2", [[start_x, end_x + 1], [cm.gpucutoffforincrease, cm.gpucutoffforincrease]])
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
    global running, fps_values, CurrentFPSOffset, fps_mean, gpu_values, cpu_values
    global max_points, luid_selected, luid

    last_process_name = None
    
    gpu_monitor.reinitialize()

    fps_limit_list = current_stepped_limits()

    current_mincap = min(fps_limit_list)
    current_maxcap = max(fps_limit_list)
    min_ft = current_mincap - round((current_maxcap - current_mincap) * 0.1)
    max_ft = current_maxcap + round((current_maxcap - current_mincap) * 0.1)

    while running:
        current_profile = cm.current_profile
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
        if len(gpu_values) > (max(cm.delaybeforedecrease, cm.delaybeforeincrease)+1):
            gpu_values.pop(0)
        gpu_values.append(gpuUsage)

        cpuUsage = cpu_monitor.cpu_percentile
        if len(cpu_values) > (max(cm.delaybeforedecrease, cm.delaybeforeincrease)+1):
            cpu_values.pop(0)
        cpu_values.append(cpuUsage)

        # To prevent loading screens from affecting the fps cap
        if gpuUsage and process_name not in {"DynamicFPSLimiter.exe"}:
            if gpuUsage > cm.minvalidgpu and fps_mean > cm.minvalidfps: 

                should_decrease = False
                gpu_decrease_condition = (len(gpu_values) >= cm.delaybeforedecrease and
                                          all(value >= cm.gpucutofffordecrease for value in gpu_values[-cm.delaybeforedecrease:]))
                cpu_decrease_condition = (len(cpu_values) >= cm.delaybeforedecrease and
                                          all(value >= cm.cpucutofffordecrease for value in cpu_values[-cm.delaybeforedecrease:]))
                if gpu_decrease_condition or cpu_decrease_condition:
                    should_decrease = True
                
                if CurrentFPSOffset > (current_mincap - current_maxcap) and should_decrease:
                    current_fps_cap = current_maxcap + CurrentFPSOffset
                    try:
                        # Find values lower than current fps_mean
                        lower_values = [x for x in fps_limit_list if x < fps_mean]
                        
                        if lower_values:
                            # If current cap is already lower than fps_mean
                            if current_fps_cap <= fps_mean:
                                # Get current index and move to next lower value
                                current_index = fps_limit_list.index(current_fps_cap)
                                if current_index < 0:
                                    next_fps = fps_limit_list[current_index - 1]
                                    CurrentFPSOffset = next_fps - current_maxcap
                                    rtss_cli.set_property(current_profile, "FramerateLimit", next_fps)
                            else:
                                # Jump to highest value below fps_mean
                                next_fps = max(lower_values)
                                CurrentFPSOffset = next_fps - current_maxcap
                                rtss_cli.set_property(current_profile, "FramerateLimit", next_fps)
                    except ValueError:
                        # If current FPS not in list, find nearest lower value
                        lower_values = [x for x in fps_limit_list if x < current_fps_cap]
                        if lower_values:
                            next_fps = max(lower_values)
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss_cli.set_property(current_profile, "FramerateLimit", next_fps)

                should_increase = False
                gpu_increase_condition = (len(gpu_values) >= cm.delaybeforeincrease and
                                          all(value <= cm.gpucutoffforincrease for value in gpu_values[-cm.delaybeforeincrease:]))
                cpu_increase_condition = (len(cpu_values) >= cm.delaybeforeincrease and
                                          all(value <= cm.cpucutoffforincrease for value in cpu_values[-cm.delaybeforeincrease:]))
                if gpu_increase_condition and cpu_increase_condition:
                     should_increase = True

                if CurrentFPSOffset < 0 and should_increase:
                    # Get current index in the fps_limit_list
                    current_fps = current_maxcap + CurrentFPSOffset
                    try:
                        current_index = fps_limit_list.index(current_fps)
                        # Move to next higher FPS value if available
                        if current_index < len(fps_limit_list) - 1:  # Check if we can move up in the list
                            next_fps = fps_limit_list[current_index + 1]
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss_cli.set_property(current_profile, "FramerateLimit", int(next_fps))
                    except ValueError:
                        # If current FPS not in list, find nearest higher value
                        higher_values = [x for x in fps_limit_list if x > current_fps]
                        if higher_values:
                            next_fps = min(higher_values)
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss_cli.set_property(current_profile, "FramerateLimit", int(next_fps))

        if running:
            # Update legend labels with current values
            dpg.configure_item("gpu_usage_series", label=f"GPU: {gpuUsage}%")
            if running and fps is not None:
                dpg.configure_item("fps_series", label=f"FPS: {fps:.1f}")
            dpg.configure_item("cap_series", label=f"FPS Cap: {current_maxcap + CurrentFPSOffset}")
            dpg.configure_item("cpu_usage_series", label=f"CPU: {cpuUsage}%")

            # Update plot if fps is valid
            if fps and process_name not in {"DynamicFPSLimiter.exe"}:
                # Scaling FPS value to fit 0-100 axis
                scaled_fps = ((fps - min_ft)/(max_ft - min_ft))*100
                scaled_cap = ((current_maxcap + CurrentFPSOffset - min_ft)/(max_ft - min_ft))*100
                actual_cap = current_maxcap + CurrentFPSOffset
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

        time.sleep(math.lcm(cm.gpupollinginterval, cm.cpupollinginterval) / 1000.0)  # Convert to seconds

gui_running = True

def gui_update_loop():
    global gui_running
    while gui_running:  # Changed from True to gui_running
        if not running:
            try:
                warnings = get_active_warnings(dpg, cm, rtss_manager, int(min(current_stepped_limits())))
                warning_visible = bool(warnings)
                warning_message = "\n".join(warnings)

                dpg.configure_item("warning_text", show=warning_visible)
                dpg.configure_item("warning_tooltip", show=warning_visible)
                dpg.set_value("warning_tooltip_text", warning_message)

                # Update FPS limit visualization based on current input values
                update_fps_cap_visualization()
            except Exception as e:
                if gui_running:  # Only log if we're still supposed to be running
                    logger.add_log(f"Error in GUI update loop: {e}")
        time.sleep(0.1)

def exit_gui():
    global running, gui_running, rtss_manager, monitoring_thread, plotting_thread
    
    gui_running = False
    running = False 

    if cm.globallimitonexit:
        rtss_cli.set_property("Global", "FramerateLimit", int(cm.globallimitonexit_fps))

    if gpu_monitor:
        gpu_monitor.cleanup()
    if cpu_monitor:
        cpu_monitor.stop()
    if dpg.is_dearpygui_running():
        dpg.destroy_context()

# Defining short sections of the GUI
# TODO: Refactor main GUI into a separate module for better organization
def build_profile_section():
    with dpg.child_window(width=-1, height=100):
        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=45)
            dpg.add_table_column(init_width_or_weight=100)
            dpg.add_table_column(init_width_or_weight=60)

            # First row
            with dpg.table_row():
                dpg.add_text("Select Profile:")
                dpg.add_combo(tag="profile_dropdown", callback=cm.load_profile_callback, width=260, default_value="Global")
                dpg.add_button(label="Delete Profile", callback=cm.delete_selected_profile_callback, width=160)

            # Second row
            with dpg.table_row():
                dpg.add_text("New RTSS Profile:")
                dpg.add_input_text(tag="new_profile_input", width=260)
                dpg.add_button(label="Add Profile", callback=cm.add_new_profile_callback, width=160)

            # Third row
            with dpg.table_row():
                dpg.add_text("Last active process:")
                dpg.add_input_text(tag="LastProcess", multiline=False, readonly=True, width=260)
                dpg.bind_item_theme("LastProcess", "transparent_input_theme_2")
                dpg.add_button(tag="process_to_profile", label="Add process to Profiles", callback=cm.add_process_profile_callback, width=160)

# GUI setup: Main Window
dpg.create_context()
create_themes()

with dpg.font_registry():
    try:
        default_font = dpg.add_font(font_path, 18)
        bold_font = dpg.add_font(bold_font_path, 18)
        if default_font:
            dpg.bind_font(default_font)
    except Exception as e:
        logger.add_log(f"Failed to load system font: {e}")
        # Will use DearPyGui's default font as fallback

#The actual GUI starts here
with dpg.window(label="Dynamic FPS Limiter", tag="Primary Window"):
    
    # Title and Start/Stop Button
    with dpg.group(horizontal=True):
        dpg.add_text("Dynamic FPS Limiter", tag="app_title")
        dpg.bind_item_font("app_title", bold_font)
        dpg.add_text("v4.1.0")
        dpg.add_spacer(width=30)
        dpg.add_button(label="Detect Render GPU", callback=toggle_luid_selection, tag="luid_button", width=150)

        dpg.add_spacer(width=30)
        dpg.add_button(label="Start", tag="start_stop_button", callback=start_stop_callback, width=50, user_data=cm)
        dpg.bind_item_theme("start_stop_button", "start_button_theme")  # Apply start button theme
        dpg.add_button(label="Exit", callback=exit_gui, width=50)  # Exit button

    # Profiles
    dpg.add_spacer(height=1)
    build_profile_section()
    
    #Tabs
    tab_height = 130
    dpg.add_spacer(height=2)
    with dpg.tab_bar():
        with dpg.tab(label="  Profile Settings", tag="tab1"):
            with dpg.child_window(height=tab_height, border=True):
                with dpg.group(horizontal=True):
                    with dpg.group(width=205):
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column(width_fixed=True)  # Column for labels
                            dpg.add_table_column(width_fixed=True)  # Column for input boxes
                            for label, key in [("Max FPS limit:", "maxcap"), 
                                            ("Min FPS limit:", "mincap"),
                                            ("Framerate ratio:", "capratio"),
                                            ("Framerate step:", "capstep")]:
                                with dpg.table_row():
                                    dpg.add_text(label, tag=f"label_{key}")
                                    dpg.add_input_int(tag=f"input_{key}", default_value=int(cm.settings[key]), 
                                                      width=90, step=1, step_fast=10, 
                                                      min_clamped=True, min_value=1)
                   
                    #2 dpg.add_spacer(width=1)
                    with dpg.group(width=175):
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column(width_fixed=True)
                            dpg.add_table_column(width_fixed=True)
                            for label, key in [("GPU: Upper limit", "gpucutofffordecrease"),
                                            ("Lower limit", "gpucutoffforincrease"),
                                            ("CPU: Upper limit", "cpucutofffordecrease"),
                                            ("Lower limit", "cpucutoffforincrease")]:
                                with dpg.table_row():
                                    dpg.add_button(label=label, tag=f"button_{key}", width=120)
                                    dpg.bind_item_theme(f"button_{key}", "button_right")
                                    dpg.add_input_text(tag=f"input_{key}", default_value=str(cm.settings[key]), width=40)
                    
                    #dpg.add_spacer(width=1)
                    tab1_group3_width = 170
                    with dpg.group(width=180):
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column(width_fixed=True)
                            with dpg.table_row():
                                dpg.add_button(tag="quick_save", label="Quick Save", callback=cm.quick_save_settings, width=tab1_group3_width)
                            with dpg.table_row():
                                dpg.add_button(tag="quick_load", label="Quick Load", callback=cm.quick_load_settings, width=tab1_group3_width)
                            with dpg.table_row():
                                dpg.add_button(tag="Reset_Default", label="Reset Settings to Default", callback=cm.reset_to_program_default, width=tab1_group3_width)
                            with dpg.table_row():
                                dpg.add_button(tag="SaveToProfile", label="Save Settings to Profile", callback=cm.save_to_profile, width=tab1_group3_width)
    
        with dpg.tab(label="  Preferences", tag="tab2"): 
            with dpg.child_window(height=tab_height):
                dpg.add_checkbox(label="Show Tooltips", tag="tooltip_checkbox",
                                 default_value=ShowTooltip, callback=tooltip_checkbox_callback)
                #2 dpg.add_spacer(height=3)
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Reset RTSS Global Limit on Exit: ", tag="limit_on_exit_checkbox",
                                    default_value=cm.globallimitonexit, callback=cm.update_limit_on_exit_setting)
                    dpg.add_input_int(tag="exit_fps_input",
                                    default_value=cm.globallimitonexit_fps, callback=cm.update_exit_fps_value,
                                    width=100, step=1, step_fast=10)
                
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Set", tag="profile_on_startup_checkbox",
                                    default_value=cm.profileonstartup, callback=cm.update_profile_on_startup_setting)
                    dpg.add_button(label="Current Profile", tag="select_profile_button",
                                    callback=cm.select_default_profile_callback, width=105)
                    dpg.add_text("as default on startup. Currently set to:")
                    dpg.add_input_text(tag="profileonstartup_name", multiline=False, readonly=True, width=150,
                                       default_value=cm.profileonstartup_name)
                    dpg.bind_item_theme("profileonstartup_name", "transparent_input_theme_2")
                dpg.add_checkbox(label="Launch the app on Windows startup", tag="autostart_checkbox",
                                 default_value=cm.launchonstartup, callback=autostart_checkbox_callback)

        with dpg.tab(label=" Log", tag="tab3"):
            with dpg.child_window(tag="LogWindow", autosize_x=True, height=tab_height, border=True):
                #dpg.add_text("", tag="LogText", tracked = True, track_offset = 1.0)
                #2 dpg.add_spacer(height=2)
                dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=110)

                dpg.bind_item_theme("LogText", "transparent_input_theme")

        with dpg.tab(label=" FAQs", tag="tab4"):
            with dpg.child_window(height=tab_height):
                dpg.add_text("Frequently Asked Questions (FAQs): Hover for answers")
                #2 dpg.add_spacer(height=3)
                for question, (key, answer) in zip(questions, FAQs.items()):
                    dpg.add_text(question, tag=key, bullet=True)
                    with dpg.tooltip(parent=key, delay=0.5):
                        dpg.add_text(answer, wrap=300)

    # Third Row: FPS lists and methods
    #dpg.add_spacer(height=5)
    #dpg.add_separator()
    dpg.add_spacer(height=5)
    with dpg.child_window(width=-1, height=125, border=True):
        with dpg.group(horizontal=True, width=-1):
            dpg.add_text("Method:")
            dpg.add_radio_button(
                items=["ratio", "step", "custom"], 
                horizontal=True,
                callback=current_method_callback,
                default_value="ratio",#settings["method"],
                tag="input_capmethod"
                )
            dpg.bind_item_theme("input_capmethod", "radio_theme")
            #dpg.bind_item_font("input_capmethod", bold_font)
            dpg.add_text("Warning!", tag="warning_text", color=(190, 90, 90), 
                         pos=(500, 5),
                         show=False)
            with dpg.tooltip(parent="warning_text", tag="warning_tooltip", show=False):
                dpg.add_text("", tag="warning_tooltip_text", wrap=300)
            dpg.bind_item_font("warning_text", bold_font)
        dpg.add_spacer(height=1)

        draw_height = 40
        layer1_height = 30
        layer2_height = 30
        draw_width = Viewport_width - 60
        margin = 10
        with dpg.drawlist(width= draw_width + 5, height=draw_height, tag="fps_cap_drawlist"):
            with dpg.draw_layer(tag="Baseline"):
                dpg.draw_line((margin, layer1_height // 2), (draw_width, layer1_height // 2), color=(200, 200, 200), thickness=2)
            with dpg.draw_layer(tag="Foreground"):
                dpg.draw_line((margin, layer2_height // 2), (draw_width, layer2_height // 2), color=(200, 200, 200), thickness=2)
        dpg.add_spacer(height=1)
        with dpg.group(horizontal=True):
            dpg.add_input_text(
                tag="input_customfpslimits",
                default_value=", ".join(str(x) for x in sorted(cm.settings["customfpslimits"])),#", ".join(map(str, sorted(self.selected_fps_caps))),
                width=draw_width - 205,
                #pos=(10, 140),  # Center the input horizontally
                callback=sort_customfpslimits_callback,
                on_enter=True)
            dpg.add_button(label="Reset", tag="rest_fps_cap_button", width=80, callback=reset_customFPSLimits)
            dpg.add_button(label="Copy from Plot", tag="autofill_fps_caps", width=110, callback=copy_from_plot_callback)

    # Fourth Row: Plot Section
    #dpg.add_spacer(height=5)
    #dpg.add_separator()
    #dpg.add_spacer(height=5)
    with dpg.child_window(tag = "plot_childwindow", width=-1, height=190, border=False):

        with dpg.plot(height=190, width=-1, tag="plot", no_menus=True, no_box_select=True, no_inputs=True):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis")
            dpg.add_plot_legend(location=dpg.mvPlot_Location_North, horizontal=True, 
                              no_highlight_item=True, no_highlight_axis=True, outside=True)

            # Left Y-axis for GPU Usage
            with dpg.plot_axis(dpg.mvYAxis, label="GPU/CPU Usage (%)", tag="y_axis_left", no_gridlines=True) as y_axis_left:
                dpg.add_line_series([], [], label="GPU: --", parent=y_axis_left, tag="gpu_usage_series")
                dpg.add_line_series([], [], label="CPU: --", parent=y_axis_left, tag="cpu_usage_series")
                # Add static horizontal dashed lines
                dpg.add_line_series([], [cm.gpucutofffordecrease, cm.gpucutofffordecrease], parent=y_axis_left, tag="line1")
                dpg.add_line_series([], [cm.gpucutoffforincrease, cm.gpucutoffforincrease], parent=y_axis_left, tag="line2")
            
            # Right Y-axis for FPS
            with dpg.plot_axis(dpg.mvYAxis, label="FPS", tag="y_axis_right", no_gridlines=True) as y_axis_right:
                dpg.add_line_series([], [], label="FPS: --", parent=y_axis_right, tag="fps_series")
                dpg.add_line_series([], [], label="FPS Cap: --", parent=y_axis_right, tag="cap_series", segments=False)
                
            # Set axis limits
            dpg.set_axis_limits("y_axis_left", 0, 100)  # GPU usage range
            min_ft = cm.mincap - cm.capstep
            max_ft = cm.maxcap + cm.capstep
            dpg.set_axis_limits("y_axis_right", min_ft, max_ft)  # FPS range
            
            # apply theme to series
            dpg.bind_item_theme("line1", "fixed_greyline_theme")
            dpg.bind_item_theme("line2", "fixed_greyline_theme")
            dpg.bind_item_theme("cap_series", "fps_cap_theme")

dpg.create_viewport(title="Dynamic FPS Limiter", width=Viewport_width, height=Viewport_height, resizable=False)
dpg.set_viewport_resizable(False)
dpg.set_viewport_max_width(Viewport_width*3)
dpg.set_viewport_max_height(Viewport_height*3)
dpg.set_viewport_small_icon(icon_path)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)

# Setup and Run GUI
logger.add_log("Initializing...")

cm.update_profile_dropdown(select_first=True)
cm.startup_profile_selection()



gpu_monitor = GPUUsageMonitor(lambda: luid, lambda: running, logger, dpg, interval=(cm.gpupollinginterval/1000), max_samples=cm.gpupollingsamples, percentile=cm.gpupercentile)
#logger.add_log(f"Current highed GPU core load: {gpu_monitor.gpu_percentile}%")

#usage, luid = gpu_monitor.get_gpu_usage(engine_type="engtype_3D")
#logger.add_log(f"Current Top LUID: {luid}, 3D engine usage: {usage}%")

cpu_monitor = CPUUsageMonitor(lambda: running, logger, dpg, interval=(cm.cpupollinginterval/1000), max_samples=cm.cpupollingsamples, percentile=cm.cpupercentile)
#logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")

# Assuming logger and dpg are initialized, and rtss_dll_path is defined
rtss_cli = RTSSCLI(logger, rtss_dll_path)
rtss_cli.enable_limiter()

rtss_manager = RTSSInterface(logger, dpg)

# Add after your other thread initializations
gui_update_thread = threading.Thread(target=gui_update_loop, daemon=True)
gui_update_thread.start()

apply_all_tooltips(dpg, tooltips, ShowTooltip, cm, logger)
current_method_callback()

autostart = AutoStartManager(app_path=os.path.join(os.path.dirname(Base_dir), "DynamicFPSLimiter.exe"))
autostart.update_if_needed(cm.launchonstartup)

dpg.bind_theme("main_theme")
dpg.bind_item_theme("plot_childwindow", "plot_bg_theme")
pywinstyles.apply_style(None, "acrylic")

logger.add_log("Initialized successfully.")

#dpg.show_style_editor()
#dpg.show_imgui_demo()

dpg.start_dearpygui()

