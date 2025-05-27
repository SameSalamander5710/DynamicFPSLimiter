# warning.py

def check_min_greater_than_max(dpg, cm):
    mincap = dpg.get_value("input_mincap")
    maxcap = dpg.get_value("input_maxcap")
    if mincap > maxcap:
        return "Minimum FPS limit is greater than maximum FPS limit."
    return None

def check_rtss_running(rtss_manager):
    if not rtss_manager or not rtss_manager.is_rtss_running():
        return "RTSS is not running!"
    return None

def get_active_warnings(dpg, cm, rtss_manager):
    warnings = []
    # Add more checks as needed
    msg = check_min_greater_than_max(dpg, cm)
    if msg:
        warnings.append(msg)
    msg = check_rtss_running(rtss_manager)
    if msg:
        warnings.append(msg)
    # Add more warning checks here...
    return warnings