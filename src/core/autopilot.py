import ctypes
import os

def get_foreground_process_name():
    """
    Returns the process name of the currently focused (foreground) window.
    Works for any application, not just 3D apps.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process_id = pid.value
    if not process_id:
        return None

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, process_id)
    if not h_process:
        return None

    exe_name = (ctypes.c_wchar * 260)()
    if psapi.GetModuleBaseNameW(h_process, None, exe_name, 260) == 0:
        kernel32.CloseHandle(h_process)
        return None

    kernel32.CloseHandle(h_process)
    return os.path.basename(exe_name.value)

def autopilot_on_check(cm, rtss_manager, dpg, logger, running, start_stop_callback):
    """
    Checks if the active process matches a profile and switches profile/running state if needed.
    """
    if not (cm and rtss_manager and rtss_manager.is_rtss_running()):
        return

    result = rtss_manager.get_fps_for_active_window()
    if not result or len(result) < 2:
        return

    fps, process_name = result
    if not process_name:
        return

    profiles = cm.profiles_config.sections() if hasattr(cm, "profiles_config") else []
    if process_name in profiles:
        # Switch profile in UI and config manager
        dpg.set_value("profile_dropdown", process_name)
        cm.load_profile_callback(None, process_name, None)
        if not running:
            logger.add_log(f"AutoPilot: Switched to profile '{process_name}' and started monitoring.")
            start_stop_callback(None, None, cm)  # Call with expected arguments
