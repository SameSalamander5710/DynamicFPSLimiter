import dearpygui.dearpygui as dpg
import ctypes
import os

ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Enable DPI awareness

class FPSCapSelector:
    def __init__(self, x_min=10, x_max=240):
        self.x_min = x_min  # Minimum value for the slider range
        self.x_max = x_max  # Maximum value for the slider range
        self.selected_fps_caps = {self.x_min, self.x_max}  # Initialize with x_min and x_max
        self.create_context()
        with dpg.font_registry():
            default_font = dpg.add_font(os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf"), 18)
            if default_font:
                dpg.bind_font(default_font)


    def create_context(self):
        dpg.create_context()

    def update_fps_cap_display(self):
        dpg.delete_item("fps_cap_group", children_only=True)
        with dpg.group(horizontal=True, parent="fps_cap_group"):  # Group all buttons horizontally
            for cap in sorted(self.selected_fps_caps):
                with dpg.group(horizontal=False):  # Group each cap's buttons vertically
                    dpg.add_button(label=str(cap), width=40, enabled=False)
                    dpg.add_button(label="X", width=40, callback=self.remove_fps_cap, user_data=cap)
        self.update_fps_cap_visualization()

    def update_fps_cap_visualization(self):
        dpg.delete_item("fps_cap_drawlist", children_only=True)  # Clear the drawlist
        if self.selected_fps_caps:
            draw_width = 400  # Width of the drawlist
            draw_height = 50  # Height of the drawlist
            margin = 10  # Margin around the drawlist

            # Draw the base line
            dpg.draw_line((margin, draw_height // 2), (draw_width + margin, draw_height // 2), color=(200, 200, 200), thickness=2, parent="fps_cap_drawlist")

            # Draw rectangles and their corresponding values
            for cap in sorted(self.selected_fps_caps):
                # Map the FPS cap value to the drawlist width
                x_pos = margin + int((cap - self.x_min) / (self.x_max - self.x_min) * draw_width)
                y_pos = draw_height // 2
                rect_width = 10  # Width of the rectangle
                rect_height = 20  # Height of the rectangle

                # Draw the rectangle
                dpg.draw_rectangle(
                    (x_pos - rect_width // 2, y_pos - rect_height // 2),
                    (x_pos + rect_width // 2, y_pos + rect_height // 2),
                    color=(255, 0, 0),
                    fill=(255, 0, 0),
                    parent="fps_cap_drawlist"
                )

                # Draw the corresponding value below the rectangle
                text_y_pos = y_pos + rect_height // 2 + 5  # Position the text slightly below the rectangle
                dpg.draw_text(
                    (x_pos - 5, text_y_pos),  # Center the text horizontally
                    str(cap),
                    color=(255, 255, 255),  # White text color
                    size=18,  # Font size
                    parent="fps_cap_drawlist"
                )

    def add_fps_cap(self, sender, app_data, user_data):
        cap = dpg.get_value("fps_slider")
        self.selected_fps_caps.add(cap)
        self.update_fps_cap_display()

    def remove_fps_cap(self, sender, app_data, user_data):
        self.selected_fps_caps.discard(user_data)
        self.update_fps_cap_display()

    def create_ui(self):
        with dpg.window(label="Custom FPS Cap Selector", width=450, height=400):
            dpg.add_text("Select an FPS cap and add it to the list:")

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=1)
                dpg.add_slider_int(tag="fps_slider", default_value=self.x_min, min_value=self.x_min, max_value=self.x_max, clamped=True, width=300)
                dpg.add_button(label="+ Add", callback=self.add_fps_cap)

            #dpg.add_spacer(height=5)
            #dpg.add_text("Visual Representation of FPS Caps:")

            # Add a drawlist to represent the FPS caps
            with dpg.drawlist(width=420, height=70, tag="fps_cap_drawlist"):
                pass  # Populated dynamically
            
            dpg.add_spacer(height=10)
            dpg.add_text("Active FPS Caps:")

            with dpg.child_window(tag="fps_cap_group", height=100, width=420):
                pass  # Populated dynamically



        # Ensure x_min and x_max are displayed by default
        self.update_fps_cap_display()

    def start(self):
        dpg.create_viewport(title="FPS Cap Selector", width=500, height=450)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

# If this script is run directly, create and start the UI
if __name__ == "__main__":
    fps_cap_selector = FPSCapSelector(x_min=30, x_max=60)  # Example of custom range
    fps_cap_selector.create_ui()
    fps_cap_selector.start()