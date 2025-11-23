# warning.py

def check_min_greater_than_max(dpg, cm):
    mincap = dpg.get_value("input_mincap")
    maxcap = dpg.get_value("input_maxcap")
    if mincap >= maxcap:
        return "[WARNING]: Minimum FPS limit should be less than maximum FPS limit."
    return None

def check_rtss_running(rtss_manager):
    if not rtss_manager or not rtss_manager.is_rtss_running():
        return "[WARNING]: RTSS is not running!"
    return None

def check_min_greater_than_minvalidfps(dpg, cm, mincap):
    if mincap < cm.minvalidfps:
        return "[WARNING]: Minimum FPS limit should be > minimum valid FPS of {}. This setting can be changes in settings.ini".format(cm.minvalidfps)
    return None

def check_non_global_profile_for_autopilot(cm):
    profiles = cm.profiles_config.sections() if hasattr(cm, "profiles_config") else []
    if getattr(cm, "autopilot", False) and (getattr(cm, "autopilot_only_profiles", False)) and (len(profiles) <= 1 or profiles == ["Global"]):
        return "[WARNING]: Moded autopilot requires at least one non-Global profile to function properly."
    return None
def get_active_warnings(dpg, cm, rtss_manager, mincap):
    warnings = []
    # Add more checks as needed
    msg = check_min_greater_than_max(dpg, cm)
    if msg:
        warnings.append(msg)

    msg = check_rtss_running(rtss_manager)
    if msg:
        warnings.append(msg)
    
    msg = check_min_greater_than_minvalidfps(dpg, cm, mincap)
    if msg:
        warnings.append(msg)

    msg = check_non_global_profile_for_autopilot(cm)
    if msg:
        warnings.append(msg)
    # Add more warning checks here...
    return warnings