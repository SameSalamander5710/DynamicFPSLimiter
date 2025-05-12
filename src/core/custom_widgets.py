import dearpygui.dearpygui as dpg
import ctypes
import os

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Enable DPI awareness

class FPSCapSelector:
    def __init__(self, x_min=10, x_max=240):
        self.x_min = x_min  # Minimum value for the slider range
        self.x_max = x_max  # Maximum value for the slider range
        self.selected_fps_caps = {self.x_min, self.x_max}  # Initialize with x_min and x_max
        dpg.create_context()
        self.create_transparent_button_theme()
        with dpg.font_registry():
            default_font = dpg.add_font(os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf"), 18)
            if default_font:
                dpg.bind_font(default_font)

    def update_fps_cap_display(self):
        dpg.delete_item("fps_cap_group", children_only=True)
        with dpg.group(horizontal=True, parent="fps_cap_group"):  # Group all buttons horizontally
            for cap in sorted(self.selected_fps_caps):
                with dpg.group(horizontal=False):  # Group each cap's buttons vertically
                    dpg.add_button(label=str(cap), width=40, enabled=False)
                    dpg.add_button(label="X", width=40, callback=self.remove_fps_cap, user_data=cap)
        self.update_fps_cap_visualization()

    def update_fps_cap_visualization(self):
        dpg.delete_item("fps_cap_window", children_only=True)  # Clear the fps_cap_window
        if self.selected_fps_caps:
            draw_width = 380  # Width of the fps_cap_window
            draw_height = 100  # Height of the fps_cap_window
            margin = 10  # Margin around the fps_cap_window

            # Add a draw layer for the line
            with dpg.draw_layer(parent="fps_cap_window"):
                # Draw the base line
                dpg.draw_line((margin, draw_height // 2), (draw_width + margin, draw_height // 2), color=(200, 200, 200), thickness=2)

            # Draw rectangles and their corresponding values
            for cap in sorted(self.selected_fps_caps):
                # Map the FPS cap value to the fps_cap_window width
                x_pos = margin + int((cap - self.x_min) / (self.x_max - self.x_min) * draw_width)
                y_pos = draw_height // 2
                rect_width = 10  # Width of the rectangle
                rect_height = 20  # Height of the rectangle

                # Add the rectangle button
                button_opaque = dpg.add_button(
                    label="",
                    width=15,
                    height=25,
                    pos=(x_pos, y_pos + 20),  # Center the button horizontally
                    #callback=self.remove_fps_cap,
                    user_data=cap,
                    parent="fps_cap_window"
                )

                # Add an input field to display and edit the FPS cap value
                input_y_pos = y_pos - 10  # Position the input slightly above the rectangle
                dpg.add_input_text(
                    default_value=cap,
                    width=30,
                    pos=(x_pos-5, input_y_pos),  # Center the input horizontally
                    callback=self.update_fps_cap_value,
                    user_data=cap,
                    parent="fps_cap_window",
                    on_enter=True
                )

                # Add the "X" button below the rectangle
                button_y_pos = y_pos + 45  # Position the button slightly below the rectangle
                button_id = dpg.add_button(
                    label="x",
                    width=15,
                    height=25,
                    pos=(x_pos, button_y_pos),  # Center the button horizontally
                    callback=self.remove_fps_cap,
                    user_data=cap,
                    parent="fps_cap_window"
                )

                # Bind the transparent theme to the button
                dpg.bind_item_theme(button_id, "transparent_button_theme")
                dpg.bind_item_theme(button_opaque, "opaque_button_theme")

    def update_fps_cap_value(self, sender, app_data, user_data):
        """Update the FPS cap value when the input field is changed."""
        old_cap = user_data  # The original FPS cap value
        new_cap = int(app_data)  # The new value entered by the user

        # Ensure the new value is within the valid range
        if self.x_min <= new_cap <= self.x_max:
            self.selected_fps_caps.discard(old_cap)  # Remove the old value
            self.selected_fps_caps.add(new_cap)  # Add the new value
            self.update_fps_cap_display()  # Refresh the display
        else:
            # Reset the input field to the old value if the new value is invalid
            dpg.set_value(sender, old_cap)

    def add_fps_cap(self, sender, app_data, user_data):
        cap = dpg.get_value("fps_slider")
        self.selected_fps_caps.add(cap)
        self.update_fps_cap_display()

    def remove_fps_cap(self, sender, app_data, user_data):
        self.selected_fps_caps.discard(user_data)
        self.update_fps_cap_display()

    def create_transparent_button_theme(self):
        """Create a theme to make buttons transparent."""
        with dpg.theme(tag="transparent_button_theme"):
            with dpg.theme_component(dpg.mvButton):
                # Set the button's background color to transparent
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))  # Fully transparent
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (170, 70, 70))  # Slightly visible on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (190, 90, 90))  # Slightly more visible when active
        with dpg.theme(tag="opaque_button_theme"):
            with dpg.theme_component(dpg.mvButton):
                # Set the button's background color to transparent
                dpg.add_theme_color(dpg.mvThemeCol_Button, (120, 120, 120, 100))  # Fully opaque
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 255, 50))  # Slightly visible on hover
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 255, 100))  # Slightly more visible when active

    def create_ui(self):
        with dpg.window(label="Custom FPS Cap Selector", width=450, height=400):
            dpg.add_text("Select an FPS cap and add it to the list:")

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=1)

                dpg.add_button(label="<", width=30, callback=lambda: self.adjust_slider(None, None, increment=False))

                # Add the slider
                dpg.add_slider_int(
                    tag="fps_slider",
                    default_value=self.x_min,
                    min_value=self.x_min,
                    max_value=self.x_max,
                    clamped=True,
                    width=250,
                )

                dpg.add_button(label=">", width=30, callback=lambda: self.adjust_slider(None, None, increment=True))

                # Add the "Add" button
                dpg.add_button(label="Add", callback=self.add_fps_cap)

            # Add a window to represent the FPS caps + buttons
            with dpg.window(width=420, height=150, tag="fps_cap_window"):
                pass  # Populated dynamically

            dpg.add_spacer(height=10)
            dpg.add_text("Active FPS Caps:")

            with dpg.child_window(tag="fps_cap_group", height=85, width=420, horizontal_scrollbar=True, border=True):
                pass  # Populated dynamically

            # Ensure x_min and x_max are displayed by default
            self.update_fps_cap_display()

    def adjust_slider(self, sender, app_data, increment=True):
        """Adjust the slider value by incrementing or decrementing."""
        current_value = dpg.get_value("fps_slider")
        if increment and current_value < self.x_max:  # Increment the value
            dpg.set_value("fps_slider", current_value + 1)
        elif not increment and current_value > self.x_min:  # Decrement the value
            dpg.set_value("fps_slider", current_value - 1)

    def start(self):
        dpg.create_viewport(title="FPS Cap Selector", width=500, height=450)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

# If this script is run directly, create and start the UI
if __name__ == "__main__":
    fps_cap_selector = FPSCapSelector(x_min=15, x_max=200)  # Example of custom range
    fps_cap_selector.create_ui()
    fps_cap_selector.start()