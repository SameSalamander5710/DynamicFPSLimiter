# DFL_v5.py
# Dynamic FPS Limiter v5.0.0

import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import dearpygui.dearpygui as dpg
import threading
import time
import math
import os
import sys
import csv
from decimal import Decimal, InvalidOperation

# tweak path so "src/" (or wherever your modules live) is on sys.path
_this_dir = os.path.abspath(os.path.dirname(__file__))
_root = os.path.dirname(_this_dir)  # Gets src directory
if _root not in sys.path:
    sys.path.insert(0, _root)

from core import logger
from core.rtss_interface import RTSSInterface
from core.cpu_monitor import CPUUsageMonitor
from core.gpu_monitor import GPUUsageMonitor
from core.librehardwaremonitor import LHMSensor
from core.themes import ThemesManager
from core.config_manager import ConfigManager
from core.tooltips import get_tooltips, add_tooltip, apply_all_tooltips, update_all_tooltip_visibility
from core.warning import get_active_warnings
from core.autostart import AutoStartManager
from core.rtss_functions import RTSSController
from core.fps_utils import FPSUtils
from core.tray_functions import TrayManager
from core.autopilot import autopilot_on_check, get_foreground_process_name

# Default viewport size
Viewport_width = 610
Viewport_height = 700

# Always get absolute path to EXE or script location
Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
rtss = RTSSController(logger)
themes_manager = ThemesManager(Base_dir)
cm = ConfigManager(logger, dpg, rtss, None, themes_manager, Base_dir)

# Ensure the config folder exists in the parent directory of Base_dir
parent_dir = os.path.dirname(Base_dir)

# Paths to configuration files
error_log_file = os.path.join(parent_dir, "error_log.txt")
icon_path = os.path.join(Base_dir, 'assets/DynamicFPSLimiter.ico')
faq_path = os.path.join(Base_dir, "assets/faqs.csv")

app_title = "Dynamic FPS Limiter"

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

def tooltip_checkbox_callback(sender, app_data, user_data):
    cm.update_preference_setting('showtooltip', sender, app_data, user_data)
    update_all_tooltip_visibility(dpg, app_data, get_tooltips(), cm, logger)

def autostart_checkbox_callback(sender, app_data, user_data):
    cm.update_preference_setting('launchonstartup', sender, app_data, user_data)

    is_checked = dpg.get_value("autostart_checkbox")
    if is_checked:
        autostart.create() 
    else:
        autostart.delete() 

def autopilot_checkbox_callback(sender, app_data, user_data):
    cm.update_preference_setting('autopilot', sender, app_data, user_data)

    if cm.autopilot:
        dpg.configure_item("start_stop_button", enabled=False)
    else:
        dpg.configure_item("start_stop_button", enabled=True)

def hide_unselected_callback(sender, app_data, user_data):
    """
    When 'Hide unselected' is checked, hide all UI elements for a sensor
    unless its input_{param_id}_enable checkbox is True.
    """
    hide = bool(app_data)
    # cm.sensor_infos contains all parameters created in the LibreHM section
    for sensor in cm.sensor_infos:
        param_id = sensor.get('parameter_id')
        if not param_id:
            continue
        enable_tag = f"input_{param_id}_enable"
        try:
            enabled = bool(dpg.get_value(enable_tag))
        except Exception:
            enabled = True
        row_tag = f"param_row_{param_id}"

        if dpg.does_item_exist(row_tag):
            # show full row only if we're not hiding, or the parameter is enabled
            dpg.configure_item(row_tag, show=(not hide) or enabled)

running = False  # Flag to control the monitoring loop

cm.update_global_variables()

lhm_sensor = LHMSensor(lambda: running, logger, dpg, themes_manager, interval=(cm.lhwmonitorpollinginterval/1000), max_samples=cm.lhwmonitoringsamples, percentile=cm.lhwmonitorpercentile)
fps_utils = FPSUtils(cm, lhm_sensor, logger, dpg, Viewport_width)


def start_stop_callback(sender, app_data, user_data):

    cm = user_data

    global running
    running = not running
    dpg.configure_item("start_stop_button", label="Stop" if running else "Start")
    dpg.bind_item_theme("start_stop_button", themes_manager.themes["stop_button_theme"] if running else themes_manager.themes["start_button_theme"])
    tray.set_running_state(running)
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

    dpg.configure_item("profile_dropdown", enabled=not running)
    dpg.configure_item("autopilot_checkbox", enabled=not running)

    if running:
        
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
        lhm_sensor.start()
        logger.add_log("Monitoring started")
        plotting_thread = threading.Thread(target=plotting_loop, daemon=True)
        plotting_thread.start()
        logger.add_log("Plotting started")
    else:
        reset_stats()
        CurrentFPSOffset = 0
        
        logger.add_log("Monitoring stopped")
    logger.add_log(f"Custom FPS limits: {cm.parse_decimal_set_to_string(fps_utils.current_stepped_limits())}")

    rtss.set_fractional_fps_direct(cm.current_profile, Decimal(max(fps_utils.current_stepped_limits())))
    rtss.set_fractional_framerate(cm.current_profile, Decimal(max(fps_utils.current_stepped_limits()))) #To update GUI

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

    fps_limit_list = fps_utils.current_stepped_limits()

    current_mincap = min(fps_limit_list)
    current_maxcap = max(fps_limit_list)
    min_ft = current_mincap - round((current_maxcap - current_mincap) * Decimal('0.1'))
    max_ft = current_maxcap + round((current_maxcap - current_mincap)* Decimal('0.1'))

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

fps_values = []
gpu_values = []
cpu_values = []
CurrentFPSOffset = 0
fps_mean = 0

def monitoring_loop():
    global running, fps_values, CurrentFPSOffset, fps_mean, gpu_values, cpu_values
    global max_points

    last_process_name = None
    
    gpu_monitor.reinitialize()

    fps_limit_list = fps_utils.current_stepped_limits()

    current_mincap = min(fps_limit_list)
    current_maxcap = max(fps_limit_list)
    min_ft = current_mincap - round((current_maxcap - current_mincap) * Decimal('0.1'))
    max_ft = current_maxcap + round((current_maxcap - current_mincap) * Decimal('0.1'))

    increase_cooldown = 0 # Cooldown for increasing FPS cap

    while running:
        current_profile = cm.current_profile
        fps, process_name = rtss_manager.get_fps_for_active_window()
        #logger.add_log(f"Current highed CPU core load: {cpu_monitor.cpu_percentile}%")

        #logger.add_log(f"get_foreground_process_name {get_foreground_process_name()}")

        if cm.autopilot:
            selected_game = dpg.get_value("profile_dropdown")
            if selected_game != "Global" and get_foreground_process_name() != selected_game and running:
                start_stop_callback(None, None, cm)

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

                should_decrease = fps_utils.should_decrease_fps_cap(gpu_values, cpu_values)
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
                                    rtss.set_fractional_framerate(current_profile, next_fps)
                            else:
                                # Jump to highest value below fps_mean
                                next_fps = max(lower_values)
                                CurrentFPSOffset = next_fps - current_maxcap
                                rtss.set_fractional_framerate(current_profile, next_fps)
                    except ValueError:
                        # If current FPS not in list, find nearest lower value
                        lower_values = [x for x in fps_limit_list if x < current_fps_cap]
                        if lower_values:
                            next_fps = max(lower_values)
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss.set_fractional_framerate(current_profile, next_fps)

                should_increase = fps_utils.should_increase_fps_cap(gpu_values, cpu_values)

                # --- COOLDOWN LOGIC ---
                if increase_cooldown > 0:
                    increase_cooldown -= 1

                if CurrentFPSOffset < 0 and should_increase and increase_cooldown == 0:
                    current_fps = current_maxcap + CurrentFPSOffset
                    gpu_range = cm.gpucutofffordecrease - cm.gpucutoffforincrease
                    last_gpu = gpu_values[-1] if gpu_values else 0

                    # Determine how many steps to increase
                    steps = 1
                    threshold = cm.gpucutoffforincrease - gpu_range
                    while last_gpu < threshold and (threshold > cm.minvalidgpu):
                        steps += 1
                        threshold = cm.gpucutoffforincrease - gpu_range * steps

                    try:
                        current_index = fps_limit_list.index(current_fps)
                        next_index = min(current_index + steps, len(fps_limit_list) - 1)
                        if next_index > current_index:
                            next_fps = fps_limit_list[next_index]
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss.set_fractional_framerate(current_profile, next_fps)
                            increase_cooldown = cm.delaybeforeincrease  # Start cooldown
                    except ValueError:
                        # If current FPS not in list, find nearest higher value
                        higher_values = [x for x in fps_limit_list if x > current_fps]
                        if higher_values:
                            # Find the index of the smallest higher value
                            min_higher = min(higher_values)
                            min_higher_index = fps_limit_list.index(min_higher)
                            next_index = min(min_higher_index + steps - 1, len(fps_limit_list) - 1)
                            next_fps = fps_limit_list[next_index]
                            CurrentFPSOffset = next_fps - current_maxcap
                            rtss.set_fractional_framerate(current_profile, next_fps)
                            increase_cooldown = cm.delaybeforeincrease  # Start cooldown

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
                scaled_fps = ((fps - min_ft)/(max_ft - min_ft)) * Decimal('100')
                scaled_cap = ((Decimal(current_maxcap) + Decimal(CurrentFPSOffset) - min_ft)/(max_ft - min_ft)) * Decimal('100')
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
    global gui_running, running

    while gui_running:

        # Wait until tray is not active
        while tray.is_tray_active and gui_running:
            time.sleep(1)  # Sleep until tray is not active

        if not running:
            try:
                if fps_utils.current_stepped_limits():
                    warnings = get_active_warnings(dpg, cm, rtss_manager, int(min(fps_utils.current_stepped_limits())))
                    warning_visible = bool(warnings)
                    warning_message = "\n".join(warnings)

                    dpg.configure_item("warning_text", show=warning_visible)
                    dpg.configure_item("warning_tooltip", show=warning_visible)
                    dpg.set_value("warning_tooltip_text", warning_message)

                # Update FPS limit visualization based on current input values
                    fps_utils.update_fps_cap_visualization()
            except Exception as e:
                if gui_running:  # Only log if we're still supposed to be running
                    logger.add_log(f"Error in GUI update loop: {e}")
        time.sleep(0.1)

def autopilot_loop():
    global gui_running, running
    while gui_running:
        if cm.autopilot and not running:
            autopilot_on_check(cm, rtss_manager, dpg, logger, running, start_stop_callback)
        time.sleep(1)  # Tune interval as needed

def exit_gui():
    global running, gui_running, rtss_manager, monitoring_thread, plotting_thread
    
    gui_running = False
    running = False 

    if cm.globallimitonexit:
        rtss.set_fractional_framerate("Global", Decimal(cm.globallimitonexit_fps))

    if gpu_monitor:
        gpu_monitor.cleanup()
    if cpu_monitor:
        cpu_monitor.stop()
    if lhm_sensor:
        lhm_sensor.stop()
    if dpg.is_dearpygui_running():
        dpg.destroy_context()

tray = TrayManager(
    app_title,
    icon_path,
    on_restore=lambda: tray.restore_from_tray(),
    on_exit=exit_gui,
    viewport_width=Viewport_width,
    config_manager_instance=cm,  # Pass ConfigManager instance
    hover_text=app_title,
    start_stop_callback=start_stop_callback,  # Pass the callback
    fps_utils=fps_utils
)

cm.tray = tray  # Set tray manager in ConfigManager

def toggle_luid_selection():
    """
    Wrapper function to prevent a 'gpu_monitor' not found error when DearPyGui builds the UI.

    This function is defined early so that it can be referenced as a callback in the UI layout,
    before the actual gpu_monitor instance is initialized later in the script.
    """
    gpu_monitor.toggle_luid_selection()

# Defining short sections of the GUI
# TODO: Refactor main GUI into a separate module for better organization
# TODO: mention legacy in plot, add specifics (3D, core max)
def build_profile_section():
    with dpg.child_window(width=-1, height=140):
        with dpg.group(horizontal=True):
            #dpg.add_spacer(width=1)
            dpg.add_input_text(tag="game_name", multiline=False, readonly=True, width=400, height=10)
            #dpg.add_button(tag="game_name", label="", width=350)
            dpg.bind_item_theme("game_name", themes_manager.themes["no_padding_theme"])
            # Use ThemesManager to bind font
            themes_manager.bind_font_to_item("game_name", "bold_font_large")

            dpg.add_checkbox(label="Autopilot", tag="autopilot_checkbox",
                                default_value=cm.autopilot, 
                            callback=autopilot_checkbox_callback
            )
            dpg.add_spacer(width=5)
            dpg.add_button(label="Start", tag="start_stop_button", callback=start_stop_callback, width=50, user_data=cm)
            dpg.bind_item_theme("start_stop_button", themes_manager.themes["start_button_theme"])  # Apply start button theme

        dpg.add_spacer(height=5)

        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=45)
            dpg.add_table_column(init_width_or_weight=100)
            dpg.add_table_column(init_width_or_weight=60)

            # First row
            with dpg.table_row():
                dpg.add_text("Select Profile:")
                dpg.add_combo(tag="profile_dropdown", callback=cm.load_profile_callback, width=260, default_value="Global")
                dpg.add_button(label="Delete Profile", callback=cm.delete_selected_profile_callback, width=160)
                #TODO: Add toggle to delete in RTSS or not
            # Second row
            with dpg.table_row():
                dpg.add_text("New RTSS Profile:")
                dpg.add_input_text(tag="new_profile_input", width=260)
                dpg.add_button(label="Add Profile", callback=cm.add_new_profile_callback, width=160)

            # Third row
            with dpg.table_row():
                dpg.add_text("Last active process:")
                dpg.add_input_text(tag="LastProcess", multiline=False, readonly=True, width=260)
                dpg.bind_item_theme("LastProcess", themes_manager.themes["transparent_input_theme_2"])
                dpg.add_button(tag="process_to_profile", label="Add process to Profiles", callback=cm.add_process_profile_callback, width=160)

def build_plot_window():
    if not dpg.does_item_exist("plot_popup_window"):
        with dpg.window(label="Performance Plot", tag="plot_popup_window", width=570, height=250, 
                        modal=False, show=False, no_title_bar=True, pos=(20, 400)): #TODO: Change y position 
            with dpg.child_window(tag="plot_childwindow", width=-1, height=190, border=False):
                with dpg.plot(height=190, width=-1, tag="plot", no_menus=True, no_box_select=True, no_inputs=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis")
                    dpg.add_plot_legend(location=dpg.mvPlot_Location_North, horizontal=True, 
                                        no_highlight_item=True, no_highlight_axis=True, outside=True)
                    with dpg.plot_axis(dpg.mvYAxis, label="GPU/CPU Usage (%)", tag="y_axis_left", no_gridlines=True) as y_axis_left:
                        dpg.add_line_series([], [], label="GPU: --", parent=y_axis_left, tag="gpu_usage_series")
                        dpg.add_line_series([], [], label="CPU: --", parent=y_axis_left, tag="cpu_usage_series")
                        dpg.add_line_series([], [cm.gpucutofffordecrease, cm.gpucutofffordecrease], parent=y_axis_left, tag="line1")
                        dpg.add_line_series([], [cm.gpucutoffforincrease, cm.gpucutoffforincrease], parent=y_axis_left, tag="line2")
                    with dpg.plot_axis(dpg.mvYAxis, label="FPS", tag="y_axis_right", no_gridlines=True) as y_axis_right:
                        dpg.add_line_series([], [], label="FPS: --", parent=y_axis_right, tag="fps_series")
                        dpg.add_line_series([], [], label="FPS Cap: --", parent=y_axis_right, tag="cap_series", segments=False)
                    dpg.set_axis_limits("y_axis_left", 0, 100)
                    min_ft = cm.mincap - cm.capstep
                    max_ft = cm.maxcap + cm.capstep
                    dpg.set_axis_limits("y_axis_right", min_ft, max_ft)
                    dpg.bind_item_theme("line1", themes_manager.themes["fixed_greyline_theme"])
                    dpg.bind_item_theme("line2", themes_manager.themes["fixed_greyline_theme"])
                    dpg.bind_item_theme("cap_series", themes_manager.themes["fps_cap_theme"])
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=30)
                dpg.add_button(label="Hide Plot", width=100, callback=lambda: dpg.configure_item("plot_popup_window", show=False))
            dpg.bind_item_theme("plot_popup_window", themes_manager.themes["nested_window_theme"])

#TODO: add theme for nested window with border

def build_readings_window():
    """
    Popup window that shows the same LibreHardwareMonitor readings shown
    in the Settings -> Readings tab. The popup contains a read-only,
    monospaced input text and a Refresh / Hide set of controls.
    """
    if not dpg.does_item_exist("readings_popup_window"):
        with dpg.window(label="Readings", tag="readings_popup_window", width=570, height=420,
                        modal=False, show=False, no_title_bar=True, pos=(20, 200)):
            with dpg.child_window(tag="readings_childwindow", width=-1, height=370, border=False):
                dpg.add_text("Sensor Readings from LibreHardwareMonitor:")
                dpg.add_input_text(tag="ReadingsText", multiline=True, readonly=True, width=-1, height=330)
                dpg.bind_item_theme("ReadingsText", themes_manager.themes["transparent_input_theme"])
                themes_manager.bind_font_to_item("ReadingsText", "monospaced_font")
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=1)
                dpg.add_button(label="Hide Readings", width=100, callback=lambda: dpg.configure_item("readings_popup_window", show=False))
            dpg.bind_item_theme("readings_popup_window", themes_manager.themes["nested_window_theme"])


def build_settings_window():
    if not dpg.does_item_exist("settings_window"):
        with dpg.window(label="Settings", tag="settings_window", width=570, height=420, 
                        modal=False, show=False, no_resize=False, no_collapse=True, no_title_bar=True, pos=(20, 230)):
            tab_height = 340
            with dpg.tab_bar():
                with dpg.tab(label="  Preferences", tag="tab2"): 
                    with dpg.child_window(height=tab_height):
                        dpg.add_checkbox(label="Launch the app on Windows startup", tag="autostart_checkbox",
                                         default_value=cm.launchonstartup, callback=autostart_checkbox_callback)
                        dpg.add_checkbox(label="Minimze on Launch", tag="minimizeonstartup_checkbox",
                                         default_value=cm.minimizeonstartup, 
                                         callback=cm.make_update_preference_callback('minimizeonstartup')
                        )
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="Set", tag="profile_on_startup_checkbox",
                                            default_value=cm.profileonstartup, 
                                            callback=cm.make_update_preference_callback('profileonstartup')
                                            )
                            dpg.add_button(label="Current Profile", tag="select_profile_button",
                                            callback=cm.select_default_profile_callback, width=105)
                            dpg.add_text("as default on startup. Currently set to:")
                            dpg.add_input_text(tag="profileonstartup_name", multiline=False, readonly=True, width=150,
                                               default_value=cm.profileonstartup_name)
                            dpg.bind_item_theme("profileonstartup_name", themes_manager.themes["transparent_input_theme_2"])
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(label="Reset RTSS Global Limit on Exit: ", tag="limit_on_exit_checkbox",
                                            default_value=cm.globallimitonexit, 
                                            callback=cm.make_update_preference_callback('globallimitonexit')
                                            ) # instead of: lambda sender, app_data, user_data: cm.update_preference_setting('globallimitonexit', sender, app_data, user_data)
                            dpg.add_input_int(tag="exit_fps_input",
                                            default_value=cm.globallimitonexit_fps, callback=cm.update_exit_fps_value,
                                            width=100, step=1, step_fast=10)
                        dpg.add_checkbox(label="Show Tooltips", tag="tooltip_checkbox",
                                         default_value=cm.showtooltip, callback=tooltip_checkbox_callback)

                with dpg.tab(label=" Log", tag="tab3"):
                    with dpg.child_window(tag="LogWindow", autosize_x=True, height=tab_height, border=True):
                        dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=tab_height-20)
                        dpg.bind_item_theme("LogText", themes_manager.themes["transparent_input_theme"])
                        logger.refresh_log_display()

                with dpg.tab(label=" FAQs", tag="tab4"):
                    with dpg.child_window(height=tab_height):
                        dpg.add_text("Frequently Asked Questions (FAQs): Hover for answers")
                        for question, (key, answer) in zip(questions, FAQs.items()):
                            dpg.add_text(question, tag=key, bullet=True)
                            with dpg.tooltip(parent=key, delay=0.5):
                                dpg.add_text(answer, wrap=300)

            # Add Hide Settings button just below the tabs
            dpg.add_spacer(height=1)
            dpg.add_button(label="Hide Settings", width=100, callback=lambda: dpg.configure_item("settings_window", show=False))
            dpg.bind_item_theme("settings_window", themes_manager.themes["nested_window_theme"])

# GUI setup: Main Window
dpg.create_context()
themes_manager.create_themes()

# Create fonts using ThemesManager
fonts = themes_manager.create_fonts(logger)
default_font = fonts.get("default_font")
bold_font = fonts.get("bold_font")
bold_font_large = fonts.get("bold_font_large")
monospaced_font = fonts.get("monospaced_font")

# Load image data

def load_and_create_textures(image_names, base_dir, dpg_module):
    """
    Loads PNG images and creates static textures in DearPyGui.
    Returns a dict mapping image base names to their texture tags.
    """
    textures = {}
    with dpg_module.texture_registry():
        for image_name in image_names:
            image_path = os.path.join(base_dir, f"assets/{image_name}")
            width, height, channels, data = dpg_module.load_image(image_path)
            base = os.path.splitext(image_name)[0]  # e.g., "close_button"
            tag = f"{base}_texture"
            textures[base] = dpg_module.add_static_texture(width, height, data, tag=tag)
    return textures

# Usage:
image_files = [
    "close_button.png",
    "minimize_button.png",
    "DynamicFPSLimiter_icon.png",
    "icon_copy.png",
    "icon_paste.png",
    "icon_save.png",
    "icon_reset.png",
    "icon_settings.png"#, "icon_plot.png"
]
textures = load_and_create_textures(image_files, Base_dir, dpg)


#The actual GUI starts here
with dpg.window(label=app_title, tag="Primary Window"):

    # Title bar
    with dpg.group(horizontal=True):
        dpg.add_image(textures["DynamicFPSLimiter_icon"], tag="icon", width=20, height=20)
        dpg.add_text(app_title, tag="app_title")
        #dpg.bind_item_font("app_title", bold_font)
        dpg.add_text("v5.0.0")
        dpg.add_spacer(width=310)

        dpg.add_image_button(texture_tag=textures["minimize_button"], tag="minimize", callback=tray.minimize_to_tray, width=20, height=20)
        dpg.add_image_button(texture_tag=textures["close_button"], tag="exit", callback=exit_gui, width=20, height=20)

        dpg.bind_item_theme("minimize", themes_manager.themes["titlebar_button_theme"])
        dpg.bind_item_theme("exit", themes_manager.themes["titlebar_button_theme"])

        with dpg.handler_registry():
            dpg.add_mouse_drag_handler(button=0, threshold=0.0, callback=tray.drag_viewport)
            dpg.add_mouse_release_handler(callback=tray.on_mouse_release)
            dpg.add_mouse_click_handler(callback=tray.on_mouse_click)

    # Profiles
    dpg.add_spacer(height=5)
    build_profile_section()

    with dpg.group(horizontal=True):

        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(width_fixed=True)   # Column for text (right-aligned)
            dpg.add_table_column(width_fixed=True)   # Column for radio buttons (left-aligned)
            # Monitoring Method row
            with dpg.table_row():
                dpg.add_text("Monitoring Method:", color=(200, 200, 200), tag="monitoring_method_text")
                dpg.bind_item_font("monitoring_method_text", bold_font)
                dpg.add_radio_button(
                    items=["LibreHM", "Legacy"], 
                    horizontal=True,
                    callback=cm.monitoring_method_callback,
                    default_value="LibreHM",
                    tag="input_monitoring_method"
                )
                dpg.bind_item_theme("input_monitoring_method", themes_manager.themes["radio_theme"])
                #dpg.bind_item_theme("monitoring_method_text", themes_manager.themes["align_right_text"])  

            # Capping Method row
            with dpg.table_row():
                dpg.add_text("Capping Method:", color=(200, 200, 200), tag="capping_method_text")
                dpg.bind_item_font("capping_method_text", bold_font)
                dpg.add_radio_button(
                    items=["Ratio", "Step", "Custom"], 
                    horizontal=True,
                    callback=cm.current_method_callback,
                    default_value="Ratio",
                    tag="input_capmethod"
                )
                dpg.bind_item_theme("input_capmethod", themes_manager.themes["radio_theme"])
                #dpg.bind_item_theme("capping_method_text", themes_manager.themes["align_right_text"])  

        dpg.add_text("Warning!", tag="warning_text", color=(190, 90, 90), 
                        pos=(500+20, 200-5),
                        show=False)
        with dpg.tooltip(parent="warning_text", tag="warning_tooltip", show=False):
            dpg.add_text("", tag="warning_tooltip_text", wrap=300)
        dpg.bind_item_font("warning_text", bold_font)

    with dpg.group(horizontal=False):
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

    dpg.add_spacer(height=1)

    with dpg.group(horizontal=True):
        mid_window_height = 285
        with dpg.group(horizontal=False):
            with dpg.child_window(width=230, height=mid_window_height - 10, border=True):
                with dpg.group(horizontal=True):
                    with dpg.drawlist(width=15, height=15):
                        dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                    dpg.add_text("Framerate Limits")
                    with dpg.drawlist(width=75, height=15):
                        dpg.draw_line((0, 13), (75, 13), color=(180,180,180), thickness=1)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=1)
                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column(width_fixed=True)  # Label
                        dpg.add_table_column(width_fixed=True)  # Column for input boxes
                        with dpg.table_row():
                            dpg.add_text("Max FPS limit:", tag="label_maxcap")
                            dpg.add_input_int(
                                tag="input_maxcap", default_value=int(cm.settings["maxcap"]),
                                width=90,
                                step=1,
                                step_fast=10,
                                min_clamped=True,
                                min_value=1)
                        # Min FPS limit
                        with dpg.table_row():
                            dpg.add_text("Min FPS limit:", tag="label_mincap")
                            dpg.add_input_int(
                                tag="input_mincap", default_value=int(cm.settings["mincap"]),
                                width=90,
                                step=1,
                                step_fast=10,
                                min_clamped=True,
                                min_value=1)
                        # Framerate ratio
                        with dpg.table_row():
                            dpg.add_text("Framerate ratio:", tag="label_capratio")
                            dpg.add_input_int(
                                tag="input_capratio", default_value=int(cm.settings["capratio"]),
                                width=90,
                                step=1,
                                step_fast=10,
                                min_clamped=True,
                                min_value=1)
                        with dpg.table_row():
                            dpg.add_text("Framerate step:", tag="label_capstep")
                            dpg.add_input_int(tag=f"input_capstep", default_value=int(cm.settings["capstep"]), 
                                                width=90, step=1, step_fast=10, 
                                                min_clamped=True, min_value=1)
                        with dpg.table_row():
                            dpg.add_text("FPS drop delay:", tag="button_delaybeforedecrease")
                            dpg.add_input_int(tag=f"input_delaybeforedecrease", default_value=int(cm.settings["delaybeforedecrease"]), 
                                                width=90, step=1, step_fast=10, 
                                                min_clamped=True, min_value=1, max_value=99, max_clamped=True)
                        with dpg.table_row():
                            dpg.add_text("FPS raise delay:", tag="button_delaybeforeincrease")
                            dpg.add_input_int(tag=f"input_delaybeforeincrease", default_value=int(cm.settings["delaybeforeincrease"]), 
                                                width=90, step=1, step_fast=10, 
                                                min_clamped=True, min_value=1, max_value=99, max_clamped=True)
                dpg.add_spacer(height=1)
                dpg.add_input_text(
                    tag="input_customfpslimits",
                    default_value=cm.settings["customfpslimits"],
                    width=210,
                    callback=cm.sort_customfpslimits_callback,
                    on_enter=True)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Reset", tag="rest_fps_cap_button", width=65, callback=fps_utils.reset_custom_limits)
                    dpg.add_button(label="Copy from above", tag="autofill_fps_caps", width=135, callback=fps_utils.copy_from_plot)


            dpg.add_spacer(height=1)

            with dpg.group(horizontal=True):
                dpg.add_image_button(
                    texture_tag=textures["icon_settings"],
                    tag="show_settings_button",
                    width=24,
                    height=24,
                    callback=lambda: dpg.configure_item(
                        "settings_window",
                        show=not dpg.is_item_shown("settings_window")
                    )
                )
                dpg.add_image_button(
                    texture_tag=textures["icon_copy"],
                    tag="quick_save",
                    callback=cm.quick_save_settings,
                    width=24,
                    height=24,  # Set height as needed for your icon
                )
                dpg.add_image_button(
                    texture_tag=textures["icon_paste"],
                    tag="quick_load",
                    callback=cm.quick_load_settings,
                    width=24,
                    height=24,  # Set height as needed for your icon
                )
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Save to Profile",
                    tag="SaveToProfile",
                    callback=cm.save_to_profile,
                    width=120,
                    height=24
                )
                dpg.bind_item_theme("SaveToProfile", themes_manager.themes["revert_gpu_theme"])
                dpg.add_image_button(
                    texture_tag=textures["icon_reset"],
                    tag="Reset_Default",
                    callback=cm.reset_to_program_default,
                    width=24,
                    height=24,  # Set height as needed for your icon
                )

        with dpg.child_window(width=-1, height=mid_window_height+80, border=True, tag="LHwM_childwindow", show=False):
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("LibreHardwareMonitorLib v0.9.4")
                with dpg.drawlist(width=100, height=15):
                    dpg.draw_line((0, 13), (100, 13), color=(180,180,180), thickness=1)

            with dpg.child_window(width=-1, height=mid_window_height, border=False):
                # Group sensors by hardware name
                sensors_by_hw = {}
                for sensor in cm.sensor_infos:
                    hw_name = sensor['hw_name']
                    sensors_by_hw.setdefault(hw_name, []).append(sensor)

                dpg.add_spacer(height=1)
                for hw_name, sensors in reversed(list(sensors_by_hw.items())):
                    with dpg.collapsing_header(label=hw_name, default_open=False):
                        # Group sensors by sensor type
                        sensors_by_type = {}
                        for sensor in sensors:
                            sensor_type_str = sensor['sensor_type'].ToString() if hasattr(sensor['sensor_type'], 'ToString') else str(sensor['sensor_type'])
                            sensors_by_type.setdefault(sensor_type_str, []).append(sensor)

                        for sensor_type, params in sensors_by_type.items():
                            dpg.add_text(sensor_type, color=(180, 220, 255))  # Sensor type as section title
                            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                                dpg.add_table_column(label="Enable")
                                dpg.add_table_column(label="Parameter", width_fixed=True, init_width_or_weight=145)
                                dpg.add_table_column(label="Lower")
                                dpg.add_table_column(label="-")
                                dpg.add_table_column(label="Upper")
                                dpg.add_table_column(label="Unit")
                                for param in params:
                                    param_id = param['parameter_id']
                                    label = param['sensor_name']#[:18] + ("..." if len(param['sensor_name']) > 18 else "")
                                    indexed = param.get('sensor_name_indexed', None)
                                    unit = "°C" if "temp" in param_id or "temperature" in param_id else "%" if "load" in param_id else "W" if "power" in param_id else ""
                                    with dpg.table_row(tag=f"param_row_{param_id}"):
                                        dpg.add_checkbox(tag=f"input_{param_id}_enable", default_value=False)
                                        dpg.add_text(label)
                                        #if indexed and indexed != label:
                                            #dpg.add_text(f"({indexed})", color=(150,150,150))
                                            #TODO: Add this as a tooltip instead
                                        dpg.add_input_text(tag=f"input_{param_id}_lower", width=40, default_value=0)
                                        dpg.add_text("-", wrap=300)
                                        dpg.add_input_text(tag=f"input_{param_id}_upper", width=40, default_value=100)
                                        dpg.add_text(unit, wrap=300)
                        dpg.add_spacer(height=1)
            dpg.add_spacer(height=1)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Show readings", width=120,
                               callback=lambda: dpg.configure_item(
                                "readings_popup_window",
                                show=not dpg.is_item_shown("readings_popup_window"))
                )
                #TODO: Add function to show readings window (bring it here from the settings)
                dpg.add_text(" | ")
                dpg.add_checkbox(label="Hide unselected", tag="hide_unselected_checkbox", default_value=False, callback=hide_unselected_callback)
                #TODO: Add function + save to config

        with dpg.child_window(width=-1, height=mid_window_height+80, border=True, tag="LHwM_childwindow_old", show=False):
            dpg.add_spacer(height=1)
            with dpg.group(horizontal=True):
                dpg.add_text("GPU:")
                dpg.add_combo(
                    tag="gpu_dropdown",
                    width=200,
                    default_value="Not detected. Use 'Legacy'.",
                    callback=cm.gpu_dropdown_callback
                )
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("Load")
                with dpg.drawlist(width=200, height=15):
                    dpg.draw_line((0, 13), (200, 13), color=(180,180,180), thickness=1)
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_fixed=True)  # Label
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_load_gpucore_enable", default_value=cm.settings["load_gpucore_enable"])
                        dpg.add_button(label="GPU Total:", tag="button_gpucore", width=85)
                        dpg.bind_item_theme("button_gpucore", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_load_gpucore_lower", default_value=str(cm.settings["load_gpucore_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_load_gpucore_upper", default_value=str(cm.settings["load_gpucore_upper"]), width=40)
                        dpg.add_text("%", tag="gpu_percent_text2", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_load_d3d3d_enable", default_value=cm.settings["load_d3d3d_enable"])
                        dpg.add_button(label="GPU 3D:", tag="button_d3d3d", width=85)
                        dpg.bind_item_theme("button_d3d3d", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_load_d3d3d_lower", default_value=str(cm.settings["load_d3d3d_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_load_d3d3d_upper", default_value=str(cm.settings["load_d3d3d_upper"]), width=40)
                        dpg.add_text("%", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_load_d3dcopy1_enable", default_value=cm.settings["load_d3dcopy1_enable"])
                        dpg.add_button(label="GPU Copy 1:", tag="button_d3dcopy1", width=85)
                        dpg.bind_item_theme("button_d3dcopy1", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_load_d3dcopy1_lower", default_value=str(cm.settings["load_d3dcopy1_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_load_d3dcopy1_upper", default_value=str(cm.settings["load_d3dcopy1_upper"]), width=40)
                        dpg.add_text("%", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_load_cputotal_enable", default_value=cm.settings["load_cputotal_enable"])
                        dpg.add_button(label="CPU Total:", tag="button_cputotal", width=85)
                        dpg.bind_item_theme("button_cputotal", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_load_cputotal_lower", default_value=str(cm.settings["load_cputotal_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_load_cputotal_upper", default_value=str(cm.settings["load_cputotal_upper"]), width=40)
                        dpg.add_text("%", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_load_cpucoremax_enable", default_value=cm.settings["load_cpucoremax_enable"])
                        dpg.add_button(label="CPU Core:", tag="button_cpucoremax", width=85)
                        dpg.bind_item_theme("button_cpucoremax", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_load_cpucoremax_lower", default_value=str(cm.settings["load_cpucoremax_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_load_cpucoremax_upper", default_value=str(cm.settings["load_cpucoremax_upper"]), width=40)
                        dpg.add_text("%", wrap=300)

            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("Temperature")
                with dpg.drawlist(width=165, height=15):
                    dpg.draw_line((0, 13), (165, 13), color=(180,180,180), thickness=1)
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_fixed=True)  # Label
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_temp_gpuhotspot_enable", default_value=cm.settings["temp_gpuhotspot_enable"])
                        dpg.add_button(label="GPU Hotspot:", tag="button_temp_gpuhotspot", width=90)
                        dpg.bind_item_theme("button_temp_gpuhotspot", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_temp_gpuhotspot_lower", default_value=str(cm.settings["temp_gpuhotspot_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_temp_gpuhotspot_upper", default_value=str(cm.settings["temp_gpuhotspot_upper"]), width=40)
                        dpg.add_text("°C", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_temp_gpucore_enable", default_value=cm.settings["temp_gpucore_enable"])
                        dpg.add_button(label="GPU Core:", tag="button_temp_gpucore", width=90)
                        dpg.bind_item_theme("button_temp_gpucore", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_temp_gpucore_lower", default_value=str(cm.settings["temp_gpucore_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_temp_gpucore_upper", default_value=str(cm.settings["temp_gpucore_upper"]), width=40)
                        dpg.add_text("°C", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_temp_cpupackage_enable", default_value=cm.settings["temp_cpupackage_enable"])
                        dpg.add_button(label="CPU Package:", tag="button_temp_cpupackage", width=90)
                        dpg.bind_item_theme("button_temp_cpupackage", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_temp_cpupackage_lower", default_value=str(cm.settings["temp_cpupackage_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_temp_cpupackage_upper", default_value=str(cm.settings["temp_cpupackage_upper"]), width=40)
                        dpg.add_text("°C", wrap=300)
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("Power Draw")
                with dpg.drawlist(width=165, height=15):
                    dpg.draw_line((0, 13), (165, 13), color=(180,180,180), thickness=1)
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_fixed=True)  # Label
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_power_gpupackage_enable", default_value=cm.settings["power_gpupackage_enable"])
                        dpg.add_button(label="GPU Package:", tag="button_power_gpupackage", width=90)
                        dpg.bind_item_theme("button_power_gpupackage", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_power_gpupackage_lower", default_value=str(cm.settings["power_gpupackage_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_power_gpupackage_upper", default_value=str(cm.settings["power_gpupackage_upper"]), width=40)
                        dpg.add_text("W", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(tag="input_power_cpupackage_enable", default_value=cm.settings["power_cpupackage_enable"])
                        dpg.add_button(label="CPU Package:", tag="button_power_cpupackage", width=90)
                        dpg.bind_item_theme("button_power_cpupackage", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_power_cpupackage_lower", default_value=str(cm.settings["power_cpupackage_lower"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_power_cpupackage_upper", default_value=str(cm.settings["power_cpupackage_upper"]), width=40)
                        dpg.add_text("W", wrap=300)

#TODO Add checkboxes to legacy options as well
        with dpg.child_window(width=-1, height=mid_window_height+80, border=True, tag="legacy_childwindow", show=False):
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("Load")
                with dpg.drawlist(width=268, height=15):
                    dpg.draw_line((0, 13), (268, 13), color=(180,180,180), thickness=1)
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column(width_fixed=True)  # Label
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="GPU 3D:", tag="button_gpu3d_legacy", width=85)
                        dpg.bind_item_theme("button_gpu3d_legacy", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_gpucutoffforincrease", default_value=str(cm.settings["gpucutoffforincrease"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_gpucutofffordecrease", default_value=str(cm.settings["gpucutofffordecrease"]), width=40)
                        dpg.add_text("%", wrap=300)
                with dpg.table_row():
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="CPU Core:", tag="button_cpucore_legacy", width=85)
                        dpg.bind_item_theme("button_cpucore_legacy", themes_manager.themes["button_left_theme"])
                        dpg.add_input_text(tag="input_cpucutoffforincrease", default_value=str(cm.settings["cpucutoffforincrease"]), width=40)
                        dpg.add_text("-", wrap=300)
                        dpg.add_input_text(tag="input_cpucutofffordecrease", default_value=str(cm.settings["cpucutofffordecrease"]), width=40)
                        dpg.add_text("%", wrap=300)
            dpg.add_spacer(height=5)
            dpg.add_input_text(tag="luid_status_text", default_value="Tracking all GPU 3D usages.", readonly=True, width=260)
            dpg.add_spacer(height=5)
            dpg.add_button(label="Detect Render GPU", callback=toggle_luid_selection, tag="luid_button", width=150)
            dpg.add_button(label="Show Plot", tag="show_plot_button", width=150,
                            callback=lambda: dpg.configure_item(
                                "plot_popup_window",
                                show=not dpg.is_item_shown("plot_popup_window")
                            ))
    dpg.add_spacer(height=1)


    dpg.add_spacer(height=1)
    #TODO Remove unnecessary theme functions if unused

build_plot_window()
build_readings_window()
build_settings_window()

viewport_x_pos, viewport_y_pos = TrayManager.get_centered_viewport_position(Viewport_width, Viewport_height)

dpg.create_viewport(title="Dynamic FPS Limiter", 
                    width=Viewport_width, height=Viewport_height, 
                    resizable=False, decorated=False, x_pos=viewport_x_pos, y_pos=viewport_y_pos)
dpg.set_viewport_resizable(False)
dpg.set_viewport_max_width(Viewport_width)
dpg.set_viewport_max_height(Viewport_height)
dpg.set_viewport_small_icon(icon_path)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_viewport_vsync(True)
dpg.set_primary_window("Primary Window", True)

# Setup and Run GUI
logger.add_log("Initializing...")

#TODO: Clean this up
cm.update_dynamic_input_field_keys()
cm.update_dynamic_default_settings()
cm.update_dynamic_key_type_map()

cm.update_profile_dropdown(select_first=True)
cm.startup_profile_selection()

initial_method = dpg.get_value("input_monitoring_method")
if initial_method == "LibreHM":
    dpg.configure_item("LHwM_childwindow", show=True)
else:
    dpg.configure_item("legacy_childwindow", show=True)

#TODO: If needed, possibility of added monitoring method check for these
gpu_monitor = GPUUsageMonitor(lambda: running, logger, dpg, themes_manager, interval=(cm.gpupollinginterval/1000), max_samples=cm.gpupollingsamples, percentile=cm.gpupercentile)
cpu_monitor = CPUUsageMonitor(lambda: running, logger, dpg, interval=(cm.cpupollinginterval/1000), max_samples=cm.cpupollingsamples, percentile=cm.cpupercentile)

gpu_names = lhm_sensor.get_gpu_names()
if gpu_names:
    idx = cm.lhm_gpu_priority if cm.lhm_gpu_priority < len(gpu_names) else 0
    dpg.configure_item("gpu_dropdown", items=gpu_names, default_value=gpu_names[idx])
else:
    dpg.configure_item("gpu_dropdown", items=["Not detected. Use 'Legacy'."], default_value="Not detected. Use 'Legacy'.")

# Assuming logger and dpg are initialized
rtss.enable_limiter()

rtss_manager = RTSSInterface(logger, dpg)

gui_update_thread = threading.Thread(target=gui_update_loop, daemon=True)
gui_update_thread.start()

# Start the autopilot thread
autopilot_thread = threading.Thread(target=autopilot_loop, daemon=True)
autopilot_thread.start()

apply_all_tooltips(dpg, get_tooltips(), cm.showtooltip, cm, logger)
cm.current_method_callback()
cm.monitoring_method_callback()

autostart = AutoStartManager(app_path=os.path.join(os.path.dirname(Base_dir), "DynamicFPSLimiter.exe"))
autostart.update_if_needed(cm.launchonstartup)

if cm.autopilot:
    dpg.configure_item("start_stop_button", enabled=False)

dpg.bind_theme(themes_manager.themes["main_theme"])
dpg.bind_item_theme("plot_childwindow", themes_manager.themes["plot_bg_theme"])

logger.add_log("Initialized successfully.")

#dpg.show_style_editor()
#dpg.show_imgui_demo()

dpg.set_frame_callback(1, lambda: tray.minimize_on_startup_if_needed(cm.minimizeonstartup))

dpg.start_dearpygui()