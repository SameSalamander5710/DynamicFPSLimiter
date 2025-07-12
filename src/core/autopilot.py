def autopilot_check(cm, rtss_manager, dpg, logger, running):
    """
    Checks if the active process matches a profile and switches profile/running state if needed.
    Returns possibly updated running value.
    """
    if not (cm and rtss_manager and rtss_manager.is_rtss_running()):
        return running

    result = rtss_manager.get_fps_for_active_window()
    if not result or len(result) < 2:
        return running

    fps, process_name = result
    if not process_name:
        return running

    profiles = cm.profiles_config.sections() if hasattr(cm, "profiles_config") else []
    if process_name in profiles:
        # Switch profile in UI and config manager
        dpg.set_value("profile_dropdown", process_name)
        cm.load_profile_callback(None, process_name, None)
        if not running:
            logger.add_log(f"AutoPilot: Switched to profile '{process_name}' and started monitoring.")
        return True  # Set running to True
    return running