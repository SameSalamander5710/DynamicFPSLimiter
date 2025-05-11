import dearpygui.dearpygui as dpg

# Internal set to track selected FPS caps
selected_fps_caps = set()

# Updates the cap buttons display
def update_fps_cap_display():
    dpg.delete_item("fps_cap_group", children_only=True)
    with dpg.group(horizontal=True, parent="fps_cap_group"):  # Group all buttons horizontally
        for cap in sorted(selected_fps_caps):
            with dpg.group(horizontal=False):  # Group each cap's buttons vertically
                dpg.add_button(label=str(cap), width=40, enabled=False)
                dpg.add_button(label="X", width=40, callback=remove_fps_cap, user_data=cap)

# Add selected slider value to the cap list
def add_fps_cap(sender, app_data, user_data):
    cap = dpg.get_value("fps_slider")
    selected_fps_caps.add(cap)
    update_fps_cap_display()

# Remove a selected cap
def remove_fps_cap(sender, app_data, user_data):
    selected_fps_caps.discard(user_data)
    update_fps_cap_display()

# Create DearPyGui context
dpg.create_context()

# Main UI window
with dpg.window(label="Custom FPS Cap Selector", width=450, height=300):
    dpg.add_text("Select an FPS cap and add it to the list:")

    with dpg.group(horizontal=True):
        dpg.add_slider_int(tag="fps_slider", default_value=60, min_value=10, max_value=240, width=300)
        dpg.add_button(label="+ Add", callback=add_fps_cap)

    dpg.add_spacer(height=5)
    dpg.add_text("Active FPS Caps:")

    with dpg.child_window(tag="fps_cap_group", height=100, width=420):
        pass  # Populated dynamically

# Setup and start DearPyGui
dpg.create_viewport(title="FPS Cap Selector", width=500, height=350)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()