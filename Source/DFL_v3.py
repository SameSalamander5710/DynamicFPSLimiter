import dearpygui.dearpygui as dpg
import threading
import configparser
import mmap
import struct
import time
import math
import psutil
from collections import defaultdict
from ctypes import wintypes, WinDLL, byref
import subprocess
import os
import sys
import traceback
import shutil

if getattr(sys, 'frozen', False):
    # Running as an EXE
    Base_dir = os.path.dirname(sys.executable)  # Correct location of the EXE
else:
    # Running as a script
    Base_dir = os.path.dirname(os.path.abspath(__file__))

# Path to settings.ini
settings_path = os.path.join(Base_dir, "settings.ini")
profiles_path = os.path.join(Base_dir, "profiles.ini")
rtss_cli_path = os.path.join(Base_dir,'_internal', 'Resources', "rtss-cli.exe")
error_log_file = os.path.join(Base_dir, "Error_log.txt")
icon_path = os.path.join(Base_dir, '_internal','Resources', 'DynamicFPSLimiter.ico')

profiles_config = configparser.ConfigParser()
settings_config = configparser.ConfigParser()

# Check if the settings and profiles files exist, if not create them with default values
if os.path.exists(settings_path):
    settings_config.read(settings_path)
else:
    settings_config["Preferences"] = {
        'ShowPlot': 'True',
        'ShowTooltip': 'True'
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
        'delaybeforedecrease': '2',
        'usagecutoffforincrease': '70',
        'delaybeforeincrease': '2',
        'minvalidgpu': '20',
        'minvalidfps': '20'
    }
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)

# Error logging function
def error_log_exception(exc_type, exc_value, exc_traceback):
    with open(error_log_file, "a") as f:
        f.write("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)) + "\n")

# Redirect uncaught exceptions to the log file
sys.excepthook = error_log_exception

log_messages = []

def add_log(message):
    log_messages.insert(0, message)  # Add message at the top
    log_messages[:] = log_messages[:50]  # Keep only the latest 50 messages
    dpg.set_value("LogText", "\n".join(log_messages))

# Function to get values with correct types
def get_setting(key, value_type=int):
    return value_type(profiles_config["Global"].get(key, Default_settings_original[key]))

ShowPlot = str(settings_config["Preferences"].get("ShowPlot", "True")).strip().lower() == "true"
ShowTooltip = str(settings_config["Preferences"].get("ShowTooltip", "True")).strip().lower() == "true"

# Default viewport size
Viewport_width = 550
Viewport_full_height = 760
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
    "capstep": 2,
    "usagecutofffordecrease": 85,
    "delaybeforedecrease": 2,
    "usagecutoffforincrease": 75,
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
        # Update the config with values from input fields
        for key in ["maxcap", "mincap", "capstep",
                "usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease",
                "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
            value = dpg.get_value(f"input_{key}")  # Get value from input field
            profiles_config[selected_profile][key] = str(value)  # Store as string in ini file
        with open(profiles_path, "w") as configfile:
            profiles_config.write(configfile)
        add_log(f"Settings saved to profile: {selected_profile}")
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
    for key in profiles_config[profile_name]:
        dpg.set_value(f"input_{key}", profiles_config[profile_name][key])
    update_global_variables()
    dpg.set_value("new_profile_input", "")

def save_profile(profile_name):
    profiles_config[profile_name] = {}
    for key in ["maxcap", "mincap", "capstep",
                "usagecutofffordecrease", "delaybeforedecrease", 
                "usagecutoffforincrease", "delaybeforeincrease", 
                "minvalidgpu", "minvalidfps"]:
        profiles_config[profile_name][key] = str(dpg.get_value(f"input_{key}"))
    with open(profiles_path, 'w') as f:
        profiles_config.write(f)
    update_profile_dropdown()

def add_new_profile_callback():
    new_name = dpg.get_value("new_profile_input")
    if new_name and new_name not in profiles_config:
        save_profile(new_name)
        dpg.set_value("new_profile_input", "")
        add_log(f"New profile created: {new_name}")
    else:
        add_log("Profile name is empty or already exists.")

def delete_selected_profile_callback():
    profile_to_delete = dpg.get_value("profile_dropdown")
    if profile_to_delete == "Global":
        add_log("Cannot delete the default 'Global' profile.")
        return
    if profile_to_delete in profiles_config:
        profiles_config.remove_section(profile_to_delete)
        with open(profiles_path, 'w') as f:
            profiles_config.write(f)
        update_profile_dropdown(select_first=True)
        for key in profiles_config["Global"]:
            dpg.set_value(f"input_{key}", profiles_config["Global"][key])
        update_global_variables()
        add_log(f"Deleted profile: {profile_to_delete}")

#Functions for profiles end ----------------

running = False  # Flag to control the monitoring loop

# Function to sync settings with variables
def update_global_variables():
    for key, value in settings.items():
        if str(value).isdigit():  # Check if value is a number
            globals()[key] = int(value)

update_global_variables()

# Check for Windows PowerShell (powershell) or PowerShell Core (pwsh) in PATH
# If not found, raise an error
powershell_path = shutil.which("powershell") or shutil.which("pwsh")
if not powershell_path:
    raise RuntimeError("PowerShell not found on this system's PATH.")

# Start PowerShell in a hidden window (persistent process)
ps_process = subprocess.Popen(
    [powershell_path, "-NoLogo", "-NoProfile", "-Command", "-"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=subprocess.CREATE_NO_WINDOW  # Run hidden
)

# Send the echo command
initialization_command = 'Write-Output "Persistent PowerShell process running successfully"\n'
ps_process.stdin.write(initialization_command)
ps_process.stdin.flush()

# Read the output
initialization_output = ps_process.stdout.readline().strip()

# Function to send a command to PowerShell and capture output for the monitoring loop
def run_powershell_command(command):
    #add_log(f"Running command 01: {command}")
    ps_process.stdin.write(command + "\n")
    #add_log(f"Running command 02: writing done")
    ps_process.stdin.flush()
    #add_log(f"Running command 03: flushing done")
    return ps_process.stdout.readline().strip()  # Read one line of output

# Function to send a command to PowerShell and capture output for selecting GPU
def send_ps_command(command):
    ps_process.stdin.write(command + '\n')
    ps_process.stdin.flush()
    ps_process.stdin.write("[Console]::Out.WriteLine('<END>')\n")  # Sentinel
    ps_process.stdin.flush()

    output_lines = []
    while True:
        line = ps_process.stdout.readline()
        if line.strip() == "<END>":
            break
        output_lines.append(line.strip())

    return output_lines

# PowerShell command to get GPU usage within loop from all GPUs
ps_command = '''
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
(Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
 Where-Object { $_.Name -like '*_engtype_*' } |
 ForEach-Object {
     if ($_.Name -match "luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys") {
         [PSCustomObject]@{
             LUID = $matches[1]
             Utilization = $_.UtilizationPercentage
         }
     }
 } |
 Group-Object -Property LUID |
 ForEach-Object {
     ($_.Group.Utilization | Measure-Object -Sum).Sum
 } |
 Measure-Object -Maximum).Maximum
'''
def get_top_luid_and_utilization():

    global luid

    ps_get_top_luid = '''
Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
    Where-Object { $_.Name -like '*_engtype_3D*' } |
    ForEach-Object {
        if ($_.Name -match "luid_0x[0-9A-Fa-f]+_(0x[0-9A-Fa-f]+)_phys") {
            [PSCustomObject]@{
                LUID = $matches[1]
                Utilization = $_.UtilizationPercentage
            }
        }
    } |
    Group-Object -Property LUID |
    ForEach-Object {
        [PSCustomObject]@{
            LUID = $_.Name
            TotalUtilization = ($_.Group.Utilization | Measure-Object -Sum).Sum
        }
    } | Sort-Object -Property TotalUtilization -Descending | Select-Object -First 1 |
    ForEach-Object { "$($_.LUID),$($_.TotalUtilization)" }
'''
    result = send_ps_command(ps_get_top_luid)
    if result:
        luid, util = result[0].split(',')
        #add_log(f"Tracking LUID: {luid} | Current Utilization: {util}%")
        return luid.strip(), util.strip()
    else:
        add_log("Failed to detect LUID.")
    
    return None, None

def run_rtss_cli(command):
    # Suppress console window on Windows
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # Don't capture or show stderr
            text=True,
            check=False,                # Faster, avoids raising exception
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW  # Prevent console window
        )
        return result.stdout.strip()
    except Exception as e:
        # Only catch generic failure (e.g., file not found)
        add_log(f"Subprocess failed: {e}")
        return None
 
user32 = WinDLL('user32', use_last_error=True)
 
def is_rtss_running():
	for process in psutil.process_iter(['name']):
		if process.info['name'] == 'RTSS.exe':
			return True
	return False
 
def get_foreground_window_process_id():
	hwnd = user32.GetForegroundWindow()
	if hwnd == 0:
		return None
	pid = wintypes.DWORD()
	user32.GetWindowThreadProcessId(hwnd, byref(pid))
	return pid.value
    
last_dwTime0s = defaultdict(int)

def get_fps_for_active_window():
	if not is_rtss_running():
		return None, None
 
	process_id = get_foreground_window_process_id()
	if not process_id:
		return None, None
 
	mmap_size = 4485160
	mm = mmap.mmap(0, mmap_size, 'RTSSSharedMemoryV2')
	dwSignature, dwVersion, dwAppEntrySize, dwAppArrOffset, dwAppArrSize, dwOSDEntrySize, dwOSDArrOffset, dwOSDArrSize, dwOSDFrame = struct.unpack(
		'4sLLLLLLLL', mm[0:36])
	calc_mmap_size = dwAppArrOffset + dwAppArrSize * dwAppEntrySize
	if mmap_size < calc_mmap_size:
		mm = mmap.mmap(0, calc_mmap_size, 'RTSSSharedMemoryV2')
	if dwSignature[::-1] not in [b'RTSS', b'SSTR'] or dwVersion < 0x00020000:
		return None, None
 
	for dwEntry in range(0, dwAppArrSize):
		entry = dwAppArrOffset + dwEntry * dwAppEntrySize
		stump = mm[entry:entry + 6 * 4 + 260]
		if len(stump) == 0:
			continue
		dwProcessID, szName, dwFlags, dwTime0, dwTime1, dwFrames, dwFrameTime = struct.unpack('L260sLLLLL', stump)
		if dwProcessID == process_id:
			if dwTime0 > 0 and dwTime1 > 0 and dwFrames > 0:
				if dwTime0 != last_dwTime0s.get(dwProcessID):
					fps = 1000 * dwFrames / (dwTime1 - dwTime0)
					last_dwTime0s[dwProcessID] = dwTime0
					process_name = szName.decode(errors='ignore').rstrip('\x00')
					process_name = process_name.split('\\')[-1]
					return fps, process_name
	return None, None

dpg.create_context()

# Read values from UI input fields without modifying `settings`
def apply_current_input_values():
    for key in ["maxcap", "mincap", "capstep",
                "usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease",
                "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        globals()[key] = int(dpg.get_value(f"input_{key}"))  # Convert to int

def start_stop_callback():
    global running
    running = not running
    dpg.configure_item("start_stop_button", label="Stop" if running else "Start")
    
    run_rtss_cli([rtss_cli_path, "limiter:set", "1"])
    
    global fps_values, CurrentFPSOffset, fps_mean, gpu_values

    # Reset variables to zero or their default state
    fps_values = []
    CurrentFPSOffset = 0
    fps_mean = 0
    gpu_values = []
    
    for key in settings.keys():
        dpg.configure_item(f"input_{key}", enabled=not running)
    
    if running:
        apply_current_input_values()  # Use current input values
        threading.Thread(target=monitoring_loop, daemon=True).start()
        time_series.clear()
        gpu_usage_series.clear()
        fps_series.clear()
        cap_series.clear()
        add_log("Monitoring started")
    else:
        reset_stats()
        CurrentFPSOffset = 0
        add_log("Monitoring stopped")
    
    global maxcap, current_profile
    
    if running:
        run_rtss_cli([rtss_cli_path, "property:set", current_profile, "FramerateLimit", str(maxcap)])

def quick_save_settings():
    for key in ["maxcap", "mincap", "capstep", "usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        settings[key] = dpg.get_value(f"input_{key}")
    update_global_variables()
    add_log("Settings quick saved")

def quick_load_settings():
    for key in ["maxcap", "mincap", "capstep", "usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        dpg.set_value(f"input_{key}", settings[key])
    update_global_variables()
    add_log("Settings quick loaded")

def enable_plot_callback(sender, app_data): #Currently not in use
    dpg.configure_item("plot_section", show=app_data)
    
    # Get current viewport size
    current_width, current_height = dpg.get_viewport_width(), dpg.get_viewport_height()
    
    # Compute new height based on plot visibility
    new_height = current_height + Plot_height if app_data else current_height - Plot_height

    dpg.set_viewport_height(new_height)
    
def reset_stats():
    for label in ["RTSS_running:", "Current_Cap:", "Current_FPS:", "Current_GPU_usage:", "Active_Window:"]:
        dpg.set_value(f"dynamic_{label}", "--")
   
def reset_to_program_default():
    
    global Default_settings_original
    
    for key in ["maxcap", "mincap", "capstep"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    for key in ["usagecutofffordecrease", "delaybeforedecrease", "usagecutoffforincrease", "delaybeforeincrease", "minvalidgpu", "minvalidfps"]:
        dpg.set_value(f"input_{key}", Default_settings_original[key])
    add_log("Settings reset to program default")  

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
        luid, util = get_top_luid_and_utilization()
        if luid:
            add_log(f"Tracking LUID: {luid} | Current 3D engine Utilization: {util}%")
            dpg.configure_item("luid_button", label="Revert to all GPUs")
            luid_selected = True
        else:
            add_log("Failed to detect active LUID.")
    else:
        # Second click: deselect
        luid = "All"
        add_log("Tracking all GPU engines.")
        dpg.configure_item("luid_button", label="Detect Render GPU")
        luid_selected = False


def get_gpu_usage():
    # Run the PowerShell command to get GPU usage
    global luid

    if luid and luid != "All":
        ps_command_top_luid = f'''
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
        Write-Output (
            (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
            Where-Object {{ $_.Name -like "*_{luid}_phys*" }} |
            Measure-Object -Property UtilizationPercentage -Sum).Sum
        )
        '''
        #add_log(f"Running command for LUID {luid}: {ps_command_top_luid}")
        gpu_usage_str = run_powershell_command(ps_command_top_luid)
        #add_log(f"GPU usage for LUID {luid}: {gpu_usage_str}")
    else:
        gpu_usage_str = run_powershell_command(ps_command)
        #add_log(f"GPU usage general: {gpu_usage_str}")

    # Check if the output is non-empty and a valid float
    if gpu_usage_str.strip():  # Strip to remove any extra whitespace
        try:
            gpu_usage = float(gpu_usage_str.strip().replace(',', '.'))
            return gpu_usage
        except ValueError:
            add_log(f"ValueError in GPU usage readout: {gpu_usage_str.strip()}")
            return None  # or handle the error as appropriate
    else:
        return None  # or handle the error as appropriate
        add_log("GPU usage: No output from PowerShell")

fps_values = []
gpu_values = []
CurrentFPSOffset = 0
fps_mean = 0

def monitoring_loop():

    global running, fps_values, CurrentFPSOffset, fps_mean, gpu_values, current_profile
    global mincap, maxcap, capstep, usagecutofffordecrease, delaybeforedecrease, usagecutoffforincrease, delaybeforeincrease, minvalidgpu, minvalidfps
    global max_points, minvalidgpu, minvalidfps

    start_time = time.time()
    
    last_process_name = None
    
    min_ft = mincap - capstep
    max_ft = maxcap + capstep
    
    while running:
        fps, process_name = get_fps_for_active_window()
        
        if process_name != None:
            last_process_name = process_name
            
        if fps:
            # Keep only the last 2 readings
            if len(fps_values) > 2:
                fps_values.pop(0)
            
            fps_values.append(fps)# Add the new fps to the list
            fps_mean = sum(fps_values) / len(fps_values)
        
        gpuUsage = get_gpu_usage()
        
        if len(gpu_values) > (max(delaybeforedecrease, delaybeforeincrease)+1):
            gpu_values.pop(0)
        gpu_values.append(gpuUsage)

        # Get elapsed time in seconds
        elapsed_time = time.time() - start_time

        # To prevent loading screens from affecting the fps cap
        if gpuUsage and process_name not in {"pythonw.exe", "DynamicFPSLimiter.exe"}:
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
                        run_rtss_cli([rtss_cli_path, "property:set", current_profile, "FramerateLimit", str(maxcap+CurrentFPSOffset)])
                if CurrentFPSOffset < 0:
                    if len(gpu_values) >= delaybeforeincrease and all(value <= usagecutoffforincrease for value in gpu_values[-delaybeforeincrease:]):
                        CurrentFPSOffset += capstep
                        run_rtss_cli([rtss_cli_path, "property:set", current_profile, "FramerateLimit", str(maxcap+CurrentFPSOffset)])

        if running:
            dpg.set_value("dynamic_Current_FPS:", f"{fps:.2f}" if fps else "--")
            dpg.set_value("dynamic_Current_Cap:", f"{maxcap + CurrentFPSOffset}")
            dpg.set_value("dynamic_Current_GPU_usage:", f"{gpuUsage}%")
            dpg.set_value("dynamic_Active_Window:", process_name if process_name else "--")
            dpg.set_value("dynamic_Last_Active_Window:", last_process_name if last_process_name else "--")
            dpg.set_value("dynamic_RTSS_running:", "Yes" if is_rtss_running() else "No")
            #print(f"Current Cap {maxcap + CurrentFPSOffset}")
            #print(f"Offest {CurrentFPSOffset}")
            #print(f"maxcap {maxcap}")
            #print(f"gpu_values {gpu_values}")
            #print(f"gpuUsage {gpuUsage}")
            
            # Update plot if fps is valid
            if fps and process_name not in {"pythonw.exe", "DynamicFPSLimiter.exe"}:
                # Scaling FPS value to fit 0-100 axis
                scaled_fps = ((fps - min_ft)/(max_ft - min_ft))*100
                scaled_cap = ((maxcap + CurrentFPSOffset - min_ft)/(max_ft - min_ft))*100
                update_plot(elapsed_time, gpuUsage, scaled_fps, scaled_cap)
                #print(f"scaled Cap {scaled_cap}")
        if process_name:
            last_process_name = process_name

        time.sleep(1)

# Function to close all active processes and exit the GUI
def exit_gui():
    
    global running
    running = False
    
    ps_process.stdin.close()
    ps_process.terminate() # Terminate all subprocesses
    dpg.destroy_context() # Close Dear PyGui

    #sys.exit(0)

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


with dpg.window(label="Dynamic FPS Limiter", tag="Primary Window"):
    
    # Title and Start/Stop Button
    with dpg.group(horizontal=True):
        dpg.add_text("Dynamic FPS Limiter v3.0.2")
        dpg.add_spacer(width=30)
        dpg.add_button(label="Detect Render GPU", callback=toggle_luid_selection, tag="luid_button", width=150)
        with dpg.tooltip("luid_button", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["luid_button"], wrap = 200)
        dpg.add_spacer(width=30)
        dpg.add_button(label="Start", tag="start_stop_button", callback=start_stop_callback)
        with dpg.tooltip("start_stop_button", show=ShowTooltip, delay=1):
            dpg.add_text(tooltips["Start"], wrap = 200)
        dpg.add_button(label="Exit", callback=exit_gui)  # Exit button

    # Profiles
    with dpg.child_window(width=-1, height=95):
        with dpg.table(header_row=False):
            dpg.add_table_column(init_width_or_weight=38)
            dpg.add_table_column(init_width_or_weight=55)
            dpg.add_table_column(init_width_or_weight=60)

            # First row
            with dpg.table_row():
                dpg.add_text("Select Profile:")
                dpg.add_combo(tag="profile_dropdown", callback=load_profile_callback, width=170, default_value="Global")
                dpg.add_button(label="Save Settings to Profile", callback=save_to_profile)

            # Second row
            with dpg.table_row():
                dpg.add_text("New RTSS Profile:")
                dpg.add_input_text(tag="new_profile_input", width=170)
                dpg.add_button(label="Add Profile", callback=add_new_profile_callback)

        dpg.add_spacer(height=3)        
        with dpg.group(horizontal=True):
            dpg.add_button(label="Reset Settings to Default", callback=reset_to_program_default)
            dpg.add_spacer(width=110)
            dpg.add_button(label="Delete Selected Profile", callback=delete_selected_profile_callback)
            
    #Basic and Advanced Settings Side by Side
    with dpg.group(horizontal=True):
        with dpg.group(horizontal=False):
            with dpg.child_window(width=250, height=185):
                dpg.add_text("Basic Settings")
                dpg.add_spacer(height=3)
                with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                    dpg.add_table_column(width_fixed=True)  # Column for labels
                    dpg.add_table_column(width_fixed=True)  # Column for input boxes
                    
                    for label, key in [("Max FPS limit:", "maxcap"), ("Min FPS limit:", "mincap"), 
                                       ("Frame rate step:", "capstep")]:
                         with dpg.table_row():
                            dpg.add_text(label)
                            dpg.add_input_text(tag=f"input_{key}", default_value=str(settings[key]), width=100)
                            with dpg.tooltip(f"input_{key}", show=ShowTooltip, delay=1):
                                dpg.add_text(tooltips[key], wrap = 200)
                dpg.add_spacer(height=10)
                with dpg.group(horizontal=False):
                    with dpg.tooltip(parent=dpg.last_item(), show=ShowTooltip, delay=1):
                        dpg.add_text(tooltips["Quick"], wrap = 200)
                    dpg.add_button(label="Quick Save", callback=quick_save_settings)
                    dpg.add_button(label="Quick Load", callback=quick_load_settings)
        with dpg.group(horizontal=False):        
            with dpg.child_window(width=260, height=185):
                dpg.add_text("Advanced Settings")
                dpg.add_spacer(height=3)
                with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                    dpg.add_table_column(width_fixed=True)  # Column for labels
                    dpg.add_table_column(width_fixed=True)  # Column for input boxes
                    for label, key in [("Upper GPU usage limit:", "usagecutofffordecrease"), 
                                       ("Instances before dec.:", "delaybeforedecrease"), 
                                       ("Lower GPU usage limit:", "usagecutoffforincrease"), 
                                       ("Instances before inc.:", "delaybeforeincrease"), 
                                       ("Min. valid GPU usage:", "minvalidgpu"), ("Min. valid FPS:", "minvalidfps")]:
                        with dpg.table_row():
                            dpg.add_text(label)
                            dpg.add_input_text(tag=f"input_{key}", default_value=str(settings[key]), width=70)
                            with dpg.tooltip(f"input_{key}", show=ShowTooltip, delay=1):
                                dpg.add_text(tooltips[key], wrap = 200)
 
    # Stats Section (Full Width)
    with dpg.child_window(width=-1, height=85):
        # Create a table for proper alignment
        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
            dpg.add_table_column(init_width_or_weight=100)  # Column for labels (left)
            dpg.add_table_column(init_width_or_weight=100)  # Column for dynamic values (left)
            dpg.add_table_column(init_width_or_weight=150)  # Column for labels (right)
            dpg.add_table_column(init_width_or_weight=150)  # Column for dynamic values (right)

            stats_left = ["RTSS running:", "Current Cap:", "Current FPS:"]
            stats_right = ["Current GPU usage:", "Active Window:", "Last Active Window:"]

            for label_left, label_right in zip(stats_left, stats_right):
                with dpg.table_row():
                    dpg.add_text(label_left)  # Left label
                    dpg.add_text("--", tag=f"dynamic_{label_left.replace(' ', '_')}")  # Left dynamic value
                    dpg.add_text(label_right)  # Right label
                    dpg.add_text("--", tag=f"dynamic_{label_right.replace(' ', '_')}")  # Right dynamic value

        # Checkbox below the table
        #dpg.add_spacer(height=5)
        #dpg.add_checkbox(label="Show plot", callback=enable_plot_callback, default_value=ShowPlotBoolean)

    # Third Row: Plot Section (Initially shown)
    with dpg.child_window(width=-1, height=Plot_height, show=ShowPlotBoolean, tag="plot_section"):
        #dpg.add_text("FPS & GPU Usage Plot")
        #create a theme for the plot
        with dpg.theme(tag="plot_theme") as item_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128), category = dpg.mvThemeCat_Plots)
        
        with dpg.plot(height=200, width=-1, tag="plot"):
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis")
            dpg.add_plot_legend(location=dpg.mvPlot_Location_North, horizontal = True, no_highlight_item = True, no_highlight_axis = True, outside = True)

            # Left Y-axis for GPU Usage
            with dpg.plot_axis(dpg.mvYAxis, label="GPU Usage (%)", tag="y_axis_left", no_gridlines = False) as y_axis_left:
                dpg.add_line_series([], [], label="GPU", parent=y_axis_left, tag="gpu_usage_series")
                        # Add static horizontal dashed lines
                dpg.add_line_series([], [usagecutofffordecrease, usagecutofffordecrease], parent=y_axis_left, tag="line1")
                dpg.add_line_series([], [usagecutoffforincrease, usagecutoffforincrease], parent=y_axis_left, tag="line2")
            
            # Right Y-axis for FPS
            with dpg.plot_axis(dpg.mvYAxis, label="FPS", tag="y_axis_right", no_gridlines = True) as y_axis_right:
                dpg.add_line_series([], [], label="FPS", parent=y_axis_right, tag="fps_series")
                dpg.add_line_series([], [], label="FPS Cap", parent=y_axis_right, tag="cap_series", segments=True)
                
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
        with dpg.child_window(tag="LogWindow", autosize_x=True, height=80, border=False):
            #dpg.add_text("", tag="LogText", tracked = True, track_offset = 1.0)
            dpg.add_spacer(height=2)
            dpg.add_input_text(tag="LogText", multiline=True, readonly=True, width=-1, height=65)

            with dpg.theme(tag="transparent_input_theme"):
                with dpg.theme_component(dpg.mvInputText):
                    dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                    dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

            dpg.bind_item_theme("LogText", "transparent_input_theme")



# Setup and Run GUI
update_profile_dropdown(select_first=True)
add_log(initialization_output)  # This would log: PowerShell process running successfully

dpg.create_viewport(title="Dynamic FPS Limiter", width=Viewport_width, height=Viewport_height, resizable=False)
dpg.set_viewport_resizable(False)
dpg.set_viewport_max_width(Viewport_width)
dpg.set_viewport_max_height(Viewport_height)
dpg.set_viewport_small_icon(icon_path)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("Primary Window", True)
dpg.start_dearpygui()

