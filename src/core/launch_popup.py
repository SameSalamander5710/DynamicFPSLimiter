import sys
import os
import configparser

# Add the src directory to the Python path for imports
_this_dir = os.path.abspath(os.path.dirname(__file__))
_src_dir = os.path.dirname(_this_dir)  # Gets src directory
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from core.themes import ThemesManager
from core.tray_functions import TrayManager
from core.drag_helper import ViewportDragHandler

def _default_dpg():
    import dearpygui.dearpygui as dpg
    return dpg

def show_missing_rtss_popup(message="Could not find RTSSHooks64.dll. Please ensure RivaTuner Statistics Server is installed before running this app.", exit_callback=None, themes_manager=None, dpg=None):
    dpg_mod = dpg if dpg is not None else _default_dpg()
    # Create drag handler for the popup
    drag_handler = ViewportDragHandler(viewport_width=420, dpg=dpg_mod)
    
    with dpg_mod.window(label="Error", modal=True, no_close=True, tag="Primary Window"):
        # Split the message to handle "Error:" separately
        if message.startswith("Error:"):
            error_part = "Error:"
            rest_of_message = message[6:].strip()  # Remove "Error:" and any following whitespace
            
            # Add "Error:" in bold
            error_text = dpg_mod.add_text(error_part, wrap=400)
            if themes_manager:
                themes_manager.bind_font_to_item(error_text, "bold_font")
            
            # Add the rest of the message
            dpg_mod.add_text(rest_of_message, wrap=400)
        else:
            dpg_mod.add_text(message, wrap=400)
        
        # Add "Notice:" in bold
        notice_text = dpg_mod.add_text("Notice:", wrap=400)
        if themes_manager:
            themes_manager.bind_font_to_item(notice_text, "bold_font")
            
        dpg_mod.add_text("Please also ensure that the DynamicFPSLimiter app is downloaded from:", wrap=400)
        dpg_mod.add_spacer(height=5)
        dpg_mod.add_input_text(tag="notice_link", multiline=False, readonly=True, width=400)
        dpg_mod.set_value("notice_link", "https://github.com/SameSalamander5710/DynamicFPSLimiter")
        
        # Apply blue text color to the link
        if themes_manager:
            with dpg_mod.theme() as link_theme:
                with dpg_mod.theme_component(dpg_mod.mvInputText):
                    dpg_mod.add_theme_color(dpg_mod.mvThemeCol_Text, (0, 150, 255, 255))  # Blue color
            dpg_mod.bind_item_theme("notice_link", link_theme)

        dpg_mod.add_spacer(height=5)
        dpg_mod.add_text("This is currently the only official source of the app.")
        dpg_mod.add_spacer(height=20)
        def _exit_app():
            if exit_callback:
                exit_callback()
            else:
                dpg_mod.destroy_context()
                sys.exit(1)
        with dpg_mod.group(horizontal=True):
            dpg_mod.add_spacer(width=132)
            dpg_mod.add_button(label="Close", width=120, callback=lambda: _exit_app())
        
        # Set up drag handlers for the popup
        with dpg_mod.handler_registry():
            dpg_mod.add_mouse_click_handler(callback=drag_handler.on_mouse_click)
            dpg_mod.add_mouse_drag_handler(callback=drag_handler.drag_viewport)
            dpg_mod.add_mouse_release_handler(callback=drag_handler.on_mouse_release)

def show_rtss_error_and_exit(rtss_path, dpg=None):
    """
    Shows an RTSS error popup with full DearPyGui context creation and execution.
    This function handles the complete workflow and exits the application.
    """
    dpg_mod = dpg if dpg is not None else _default_dpg()
    # Get the base directory for themes manager (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    dpg_mod.create_context()
    
    # Create themes and fonts for the popup
    themes_manager = ThemesManager(Base_dir, dpg_mod)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    show_missing_rtss_popup(
        f"Error: Could not find 'RTSSHooks64.dll' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed before running this app.\n\n",
        themes_manager=themes_manager,
        dpg=dpg_mod
    )
    
    # Apply the main theme to the popup
    dpg_mod.bind_theme(themes_manager.themes["main_theme"])
    
    # Calculate center position for the viewport
    viewport_width = 420
    viewport_height = 320
    x_pos, y_pos = TrayManager.get_centered_viewport_position(viewport_width, viewport_height)
    
    dpg_mod.create_viewport(title="Dynamic FPS Limiter - Error", width=viewport_width, height=viewport_height, 
                       resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    dpg_mod.setup_dearpygui()
    dpg_mod.show_viewport()
    dpg_mod.set_primary_window("Primary Window", True)
    dpg_mod.start_dearpygui()
    sys.exit(1)

def show_loading_popup(message="Loading...", width=300, height=50, title="Dynamic FPS Limiter - Loading", Base_dir=None, dpg=None):
    """
    Creates a minimal DearPyGui context + viewport and shows a simple loading window.
    This is self-contained so it can be shown early and later completely destroyed
    with hide_loading_popup() before the main GUI context is created.
    """ 
    dpg_mod = dpg if dpg is not None else _default_dpg()

    try:
        parent_dir = os.path.dirname(Base_dir)
        settings_path = os.path.join(parent_dir, "config", "settings.ini")
        cfg = configparser.ConfigParser()
        if os.path.exists(settings_path):
            cfg.read(settings_path)
            hide_popup = cfg.getboolean("Preferences", "hide_loading_popup", fallback=False)
            if hide_popup:
                return  # user preference requests no loading popup
    except Exception:
        # If anything goes wrong reading prefs, continue and show the popup
        pass

    # If a context already exists, don't try to recreate it here.
    try:
        dpg_mod.create_context()
    except Exception:
        # context may already exist; ignore
        pass

    # Create themes and fonts for the popup
    themes_manager = ThemesManager(Base_dir, dpg_mod)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()

    # Basic window content
    with dpg_mod.window(label="", tag="LoadingWindow", no_title_bar=True, no_resize=True,
                    no_move=False, no_collapse=True, width=width, height=height):
        dpg_mod.add_spacer(height=1)
        dpg_mod.add_text(message, tag="loading_text", wrap=width - 20)
        dpg_mod.add_spacer(height=1)


    # If a themes manager is provided, bind the app font/theme to the loading text
    if themes_manager:
        try:
            # If themes/fonts were already created, bind the regular font (fallback if missing)
            themes_manager.bind_font_to_item("loading_text", "regular_font")
            # Bind the main theme so styles match other popups
            dpg_mod.bind_theme(themes_manager.themes["main_theme"])
        except Exception:
            # Don't fail popup creation just because theming couldn't be applied
            pass

    # Center viewport on screen
    x_pos, y_pos = TrayManager.get_centered_viewport_position(width, height)
    try:
        dpg_mod.create_viewport(title=title, width=width, height=height,
                            resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    except Exception:
        # viewport may already exist
        pass

    dpg_mod.setup_dearpygui()
    dpg_mod.show_viewport()
    dpg_mod.set_primary_window("LoadingWindow", True)

    # Render a single frame so the window appears immediately
    try:
        dpg_mod.render_dearpygui_frame()
    except Exception:
        pass

def hide_loading_popup(dpg=None):
    """
    Destroys the temporary loading viewport/context created by show_loading_popup.
    Call this before creating the main application context/viewport.
    """
    dpg_mod = dpg if dpg is not None else _default_dpg()
    try:
        # destroy viewport if present
        try:
            dpg_mod.destroy_viewport()
        except Exception:
            pass
        # destroy context
        try:
            dpg_mod.destroy_context()
        except Exception:
            pass
    except Exception:
        pass

if __name__ == "__main__":
    # Test the popup by running this file directly using: python src\core\launch_popup.py
    print("Testing RTSS error popup...")
    
    # Get the base directory (same as in DFL_v4.py)
    Base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    dpg_mod = _default_dpg()
    # Create context and apply fonts/themes
    dpg_mod.create_context()
    themes_manager = ThemesManager(Base_dir, dpg_mod)
    themes_manager.create_themes()
    fonts = themes_manager.create_fonts()
    
    # Test with a sample RTSS path
    show_missing_rtss_popup(
        "Error: Could not find 'RTSSHooks64.dll' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed before running this app.\n\n",
        themes_manager=themes_manager,
        dpg=dpg_mod
    )
    
    # Apply theme
    dpg_mod.bind_theme(themes_manager.themes["main_theme"])
    
    # Calculate center position for the viewport
    viewport_width = 420
    viewport_height = 320
    x_pos, y_pos = TrayManager.get_centered_viewport_position(viewport_width, viewport_height)
    
    dpg_mod.create_viewport(title="Dynamic FPS Limiter - Error", width=viewport_width, height=viewport_height, 
                       resizable=False, decorated=False, x_pos=x_pos, y_pos=y_pos)
    dpg_mod.setup_dearpygui()
    dpg_mod.show_viewport()
    dpg_mod.set_primary_window("Primary Window", True)
    dpg_mod.start_dearpygui()

