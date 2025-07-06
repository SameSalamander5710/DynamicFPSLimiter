import dearpygui.dearpygui as dpg
import sys
import os
import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)

# Add the src directory to the Python path for imports
_this_dir = os.path.abspath(os.path.dirname(__file__))
_src_dir = os.path.dirname(_this_dir)  # Gets src directory
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from core.themes import ThemesManager

def show_missing_rtss_popup(message="Could not find RTSSHooks64.dll. Please ensure RivaTuner Statistics Server is installed.", exit_callback=None, themes_manager=None):
    with dpg.window(label="Error", modal=True, no_close=True, tag="Primary Window"):
        # Split the message to handle "Error:" separately
        if message.startswith("Error:"):
            error_part = "Error:"
            rest_of_message = message[6:].strip()  # Remove "Error:" and any following whitespace
            
            # Add "Error:" in bold
            error_text = dpg.add_text(error_part, wrap=380)
            if themes_manager:
                themes_manager.bind_font_to_item(error_text, "bold_font")
            
            # Add the rest of the message
            dpg.add_text(rest_of_message, wrap=380)
        else:
            dpg.add_text(message, wrap=380)
        
        # Add "Notice:" in bold
        notice_text = dpg.add_text("Notice:", wrap=380)
        if themes_manager:
            themes_manager.bind_font_to_item(notice_text, "bold_font")
            
        dpg.add_text("Please ensure that the DynamicFPSLimiter app is downloaded from:", wrap=380)
        dpg.add_spacer(height=5)
        dpg.add_text("https://github.com/SameSalamander5710/DynamicFPSLimiter", color=(0, 150, 255))
        dpg.add_spacer(height=5)
        dpg.add_text("This is currently the only official source of the app.")
        dpg.add_spacer(height=20)
        def _exit_app():
            if exit_callback:
                exit_callback()
            else:
                dpg.destroy_context()
                sys.exit(1)
        dpg.add_button(label="Exit", width=120, callback=lambda: _exit_app())

def show_rtss_error_and_exit(rtss_path):
    """
    Shows an RTSS error popup with full DearPyGui context creation and execution.
    This function handles the complete workflow and exits the application.
    """
    # Get the base directory for themes manager (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    dpg.create_context()
    
    # Create themes and fonts for the popup
    themes_manager = ThemesManager(Base_dir)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    show_missing_rtss_popup(
        f"Error: Could not find module '{rtss_path}' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed.\n\n",
        themes_manager=themes_manager
    )
    
    # Apply the main theme to the popup
    dpg.bind_theme(themes_manager.themes["main_theme"])
    
    dpg.create_viewport(title="Dynamic FPS Limiter - Error", width=420, height=320, resizable=False, decorated=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()
    sys.exit(1)

if __name__ == "__main__":
    # Test the popup by running this file directly using: python src\core\launch_popup.py
    print("Testing RTSS error popup...")
    
    # Get the base directory (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # Create context and apply fonts/themes
    dpg.create_context()
    themes_manager = ThemesManager(Base_dir)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    # Test with a sample RTSS path
    show_missing_rtss_popup(
        "Error: Could not find module 'C:\\Program Files (x86)\\RivaTuner Statistics Server\\RTSSHooks64.dll' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed.\n\n",
        themes_manager=themes_manager
    )
    
    # Apply theme
    dpg.bind_theme(themes_manager.themes["main_theme"])
    
    dpg.create_viewport(title="Dynamic FPS Limiter - Error", width=420, height=320, resizable=False, decorated=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()

