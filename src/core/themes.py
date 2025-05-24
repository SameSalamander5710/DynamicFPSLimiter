import dearpygui.dearpygui as dpg

def create_themes(background_colour=(37, 37, 38)):
    # Rounded widget theme
    with dpg.theme(tag="main_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (0, 200, 255, 255))  # Cyan, RGBA
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3.0)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55))

        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 30, 60, 255))  # Example: dark blue

            #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0.0, 1.0, category=dpg.mvThemeCat_Core)
            #dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 150, 250))  # Button color
            #dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 170, 255))  # Hover color
            #dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 190, 255))  # Active color

        # Customize specific widget types
        #with dpg.theme_component(dpg.mvInputInt):

        #with dpg.theme_component(dpg.mvInputText):
        with dpg.theme_component(dpg.mvCheckbox):
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (50, 150, 250))

    with dpg.theme(tag="radio_theme"):
        with dpg.theme_component(dpg.mvRadioButton):
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (200, 200, 200))  # White selection circle
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (120, 120, 120))  # Grey hover highlight

    # RTSS running theme
    with dpg.theme(tag="rtss_running_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 100, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 120, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 140, 0))

    # RTSS not running theme
    with dpg.theme(tag="rtss_not_running_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (170, 70, 70))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 90, 90))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (190, 90, 90))

    # Detect GPU theme
    with dpg.theme(tag="detect_gpu_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (15, 86, 135))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (15, 86, 135))

    # Revert GPU theme
    with dpg.theme(tag="revert_gpu_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (15, 86, 135))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (6, 96, 158))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 105, 176))

    # Button right theme
    with dpg.theme(tag="button_right"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 1.00, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Button, background_colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, background_colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, background_colour, category=dpg.mvThemeCat_Core)

    # Plot themes
    with dpg.theme(tag="fixed_greyline_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128), category=dpg.mvThemeCat_Plots)
    with dpg.theme(tag="fps_cap_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128, 150), category=dpg.mvThemeCat_Plots)

    # Transparent input theme (for log window)
    with dpg.theme(tag="transparent_input_theme"):
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="border_theme"):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 0, 0, 255))

    with dpg.theme(tag="plot_bg_theme"):
        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (0, 200, 255, 255))  # Example: cyan
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, (255, 200, 0, 255))  # Example: yellow