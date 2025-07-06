import dearpygui.dearpygui as dpg
import sys

def show_missing_rtss_popup(message="Could not find RTSSHooks64.dll. Please ensure RivaTuner Statistics Server is installed.", exit_callback=None):
    with dpg.window(label="Error", modal=True, no_close=True, width=400, height=180, tag="Primary Window"):
        dpg.add_text(message, wrap=380)
        dpg.add_text("Warning 2", wrap=380)
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
    dpg.create_context()
    show_missing_rtss_popup(
        f"Could not find module '{rtss_path}' (or one of its dependencies). "
        "Please ensure RivaTuner Statistics Server is installed.\n\n"
    )
    dpg.create_viewport(title="Dynamic FPS Limiter - Error", width=420, height=200, resizable=False)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Primary Window", True)
    dpg.start_dearpygui()
    sys.exit(1)

if __name__ == "__main__":
    # Test the popup by running this file directly
    print("Testing RTSS error popup...")
    test_rtss_path = r"C:\Program Files (x86)\RivaTuner Statistics Server\RTSSHooks64.dll"
    show_rtss_error_and_exit(test_rtss_path)

