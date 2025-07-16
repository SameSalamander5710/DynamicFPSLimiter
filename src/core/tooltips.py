# tooltips.py

def get_tooltips():
    return {
    "maxcap": "Defines the maximum FPS limit for the game. Hold CTRL for steps of 10.",
    "mincap": "Specifies the minimum FPS limit that may be reached. For optimal performance, set this to the lowest value you're comfortable with. Hold CTRL for steps of 10.",
    "capratio": "Percentage decrease used to generate FPS limits. Each limit is (100 - value)% of the previous one. Hold CTRL for steps of 10.",
    "capstep": "Increment size for adjusting the FPS cap. Smaller step sizes provide finer control. Hold CTRL for steps of 10.",
    "gpucutofffordecrease": "Sets the upper threshold for GPU usage. If GPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "delaybeforedecrease": "Specifies how many times in a row GPU usage must exceed the upper threshold before the FPS cap begins to drop.",
    "gpucutoffforincrease": "Defines the lower threshold for GPU usage. If GPU usage falls below this value, the FPS cap may increase to improve performance.",
    "delaybeforeincrease": "Specifies how many times in a row GPU usage must fall below the lower threshold before the FPS cap begins to rise.",
    "cpucutofffordecrease": "Sets the upper threshold for CPU usage. If CPU usage exceeds this value, the FPS cap will be lowered to maintain system performance.",
    "cpucutoffforincrease": "Defines the lower threshold for CPU usage. If CPU usage falls below this value, the FPS cap may increase to improve performance.",
    "minvalidgpu": "Sets the minimum valid GPU usage percentage required for adjusting the FPS. If the GPU usage is below this threshold, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "minvalidfps": "Defines the minimum valid FPS required for adjusting the FPS. If the FPS falls below this value, the FPS cap will not change. This helps prevent FPS fluctuations during loading screens.",
    "quick_save": "Save settings to memory temporarily. Useful to copy settings between profiles.",
    "quick_load": "Loads input values from memory.",
    "start_stop_button": "Starts maintaining the FPS cap dynamically based on GPU/CPU utilization.",
    "luid_button": "Detects the render GPU based on CURRENT highest 3D engine utilization, and sets it as the target GPU for FPS limiting. Click again to deselect.",
    "exit_fps_input": "The specific FPS limit to apply globally when the application exits, if 'Set Global FPS Limit on Exit' is checked.",
    "SaveToProfile": "Saves the current settings to the selected profile. Settings are NOT saved automatically.",
    "Reset_Default": "Resets all settings to the program's default values.",
    "Reset_CustomFPSLimits": "Resets the custom FPS limits to 'max FPS limit' and 'min FPS limit'.",
    "DeleteProfile": "Deletes the selected profile. Be cautious, as this action cannot be undone.",
    "checkbox_globallimitonexit": "Enables or disables the application of a global FPS limit when exiting the program. When enabled, the specified FPS limit will be applied to all processes.",
    "autofill_fps_caps": "Click with the method set to 'ratio' or 'step' to copy the calculated limits.",
    "process_to_profile": "Add the current settings to a new profile based on the last used process.",
    "button_cpucutofffordecrease": "(Optional) Set values below 100 to enable CPU-based FPS limiting.",
    "button_cpucutoffforincrease": "(Optional) Set values below 100 to enable CPU-based FPS limiting.",
    "rest_fps_cap_button": "Clears the input fields and resets to Min/Max values",
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
            with dpg.tooltip(parent=widget_id, tag=tooltip_tag, show=ShowTooltip, delay=0.5):
                dpg.add_text(tooltips[key], wrap=200)

def apply_all_tooltips(dpg, tooltips, ShowTooltip, cm, logger):
    """Automatically adds tooltips to all widgets that have entries in the tooltips dictionary"""
    for key in tooltips:
        try:
            add_tooltip(dpg, key, tooltips, ShowTooltip, cm, logger)
        except Exception as e:
            logger.add_log(f"Failed to add tooltip for {key}: {e}")

def update_all_tooltip_visibility(dpg, ShowTooltip, tooltips, cm, logger):
    """
    Updates the visibility of all tooltips based on ShowTooltip value.
    """
    for key in tooltips.keys():
        parent_tag = f"input_{key}" if key in cm.input_field_keys else key
        tooltip_specific_tag = f"{parent_tag}_tooltip"

        if dpg.does_item_exist(tooltip_specific_tag):
            try:
                dpg.configure_item(tooltip_specific_tag, show=ShowTooltip)
            except SystemError as e:
                logger.add_log(f"Minor issue configuring tooltip '{tooltip_specific_tag}' for key '{key}': {e}")