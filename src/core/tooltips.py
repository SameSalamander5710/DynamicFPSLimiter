# tooltips.py

def get_tooltips():
    return {
    "maxcap": "Defines the maximum FPS limit for the game. Hold CTRL for steps of 10.",
    "mincap": "Specifies the minimum FPS limit that may be reached. For optimal performance, set this to the lowest value you're comfortable with. Hold CTRL for steps of 10.",
    "capratio": "Generate FPS limits based on given ratio. The FPS cap will be set to the maximum FPS limit multiplied by this ratio.",
    "capstep": "Indicates the increment size for adjusting the FPS cap. Smaller step sizes provide finer control. Hold CTRL for steps of 10.",
    "gpucutofffordecrease": "Sets the upper threshold for GPU usage. If GPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "delaybeforedecrease": "Specifies how many times in a row GPU usage must exceed the upper threshold before the FPS cap begins to drop.",
    "gpucutoffforincrease": "Defines the lower threshold for GPU usage. If GPU usage falls below this value, the FPS cap will increase to improve performance.",
    "delaybeforeincrease": "Specifies how many times in a row GPU usage must fall below the lower threshold before the FPS cap begins to rise.",
    "cpucutofffordecrease": "Sets the upper threshold for CPU usage. If CPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "cpucutoffforincrease": "Defines the lower threshold for CPU usage. If CPU usage falls below this value, the FPS cap will increase to improve performance.",
    "minvalidgpu": "Sets the minimum valid GPU usage percentage required for adjusting the FPS. If the GPU usage is below this threshold, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "minvalidfps": "Defines the minimum valid FPS required for adjusting the FPS. If the FPS falls below this value, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "quick_save": "Saves input values from memory. This is temporary storage, useful for testing and fine-tuning configurations.",
    "quick_load": "Loads input values from memory. This is temporary storage, useful for testing and fine-tuning configurations.",
    "start_stop_button": "Starts maintaining the FPS cap dynamically based on GPU/CPU utilization.",
    "luid_button": "Detects the render GPU based on highest 3D engine utilization, and sets it as the target GPU for FPS limiting. Click again to deselect.",
    "exit_fps_input": "The specific FPS limit to apply globally when the application exits, if 'Set Global FPS Limit on Exit' is checked.",
    "SaveToProfile": "Saves the current settings to the selected profile. This allows you to quickly switch between different configurations.",
    "Reset_Default": "Resets all settings to the program's default values. This is useful if you want to start fresh or if you encounter issues.",
    "Reset_CustomFPSLimits": "Resets the custom FPS limits to 'max FPS limit' and 'min FPS limit'.",
    "DeleteProfile": "Deletes the selected profile. Be cautious, as this action cannot be undone.",
    "checkbox_enablecustomfpslimits": "Enables or disables the use of custom FPS limits. When enabled, the FPS limits will be applied based on the specified list.",
    "checkbox_globallimitonexit": "Enables or disables the application of a global FPS limit when exiting the program. When enabled, the specified FPS limit will be applied to all processes.",
    "autofill_fps_caps": "Generates FPS limits from `max FPS limit` down to `min FPS limit` such that each step reduces expected GPU usage from `upper limit` to just above `lower limit` when triggered.",
}

def add_tooltip(dpg, key, tooltips, ShowTooltip, cm, logger):
    """
    Adds a tooltip to a widget using consistent naming convention.
    key: The key used in the tooltips dictionary
    """
    if key in tooltips:
        # Determine the actual widget ID
        widget_id = f"input_{key}" if key in cm.input_field_keys else key
        
        # Only create tooltip if widget exists
        if dpg.does_item_exist(widget_id):
            tooltip_tag = f"{widget_id}_tooltip"
            with dpg.tooltip(parent=widget_id, tag=tooltip_tag, show=ShowTooltip, delay=1):
                dpg.add_text(tooltips[key], wrap=200)

def apply_all_tooltips(dpg, tooltips, ShowTooltip, cm, logger):
    """Automatically adds tooltips to all widgets that have entries in the tooltips dictionary"""
    for key in tooltips:
        try:
            add_tooltip(dpg, key, tooltips, ShowTooltip, cm, logger)
        except Exception as e:
            logger.add_log(f"Failed to add tooltip for {key}: {e}")

def update_tooltip_setting(dpg, sender, app_data, user_data, tooltips, cm, logger):
    ShowTooltip = app_data
    cm.settings_config["Preferences"]["ShowTooltip"] = str(app_data)
    with open(cm.settings_path, 'w') as f:
        cm.settings_config.write(f)
    logger.add_log(f"Tooltip visibility set to: {ShowTooltip}")

    for key in tooltips.keys():
        parent_tag = f"input_{key}" if key in cm.input_field_keys else key
        tooltip_specific_tag = f"{parent_tag}_tooltip"

        if dpg.does_item_exist(tooltip_specific_tag):
            try:
                dpg.configure_item(tooltip_specific_tag, show=ShowTooltip)
            except SystemError as e:
                logger.add_log(f"Minor issue configuring tooltip '{tooltip_specific_tag}' for key '{key}': {e}")

