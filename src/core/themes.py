import dearpygui.dearpygui as dpg

bg_colour = (21, 20, 21, 255)
bg_colour_2_child = (27, 31, 37, 255)
bg_colour_3_button = (35, 39, 47, 255)
bg_colour_4_buttonhover = (32, 60, 68, 255)
bg_colour_5_buttonactive = (30, 85, 205, 255)
bg_colour_6_buttonstateactive = (200, 88, 45, 255) 
bg_colour_7_text_faded = (150, 152, 161, 255)
bg_colour_8_text_stateactive = (238, 230, 224, 255)


def create_themes(background_colour=(37, 37, 38, 0)):
    # Rounded widget theme
    with dpg.theme(tag="main_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (0, 200, 255, 255))  # Cyan, RGBA
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3.0)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (51, 51, 55))
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 4)
            dpg.add_theme_style(dpg.mvStyleVar_TabBarBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 4)

            dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, bg_colour)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, bg_colour_2_child)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_colour_3_button)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, bg_colour_5_buttonactive)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (255, 255, 255, 11)) # Example: light shadow for 3D effect
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_3_button)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, bg_colour_2_child)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, bg_colour_3_button)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, bg_colour)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, bg_colour_5_buttonactive)
            #dpg.add_theme_color(dpg.mvThemeCol_PopupActive, (30, 144, 255, 255))

            # Plot-specific styles
            dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MinorAlpha, 0.20, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MajorTickLen, 5, 5, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_style(dpg.mvPlotStyleVar_LabelPadding, 5, 2, category=dpg.mvThemeCat_Plots)
        
        #with dpg.theme_component(dpg.mvChildWindow):
            #dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 30, 60, 255))  # Example: dark blue

            #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0.0, 1.0, category=dpg.mvThemeCat_Core)
            #dpg.add_theme_color(dpg.mvThemeCol_Button, (50, 150, 250))  # Button color
            #dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (70, 170, 255))  # Hover color
            #dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (90, 190, 255))  # Active color

        # Customize specific widget types
        #with dpg.theme_component(dpg.mvInputInt):

        #with dpg.theme_component(dpg.mvInputText):
        with dpg.theme_component(dpg.mvCheckbox):
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (50, 150, 250))
        
        with dpg.theme_component(dpg.mvTab):
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 3)

    with dpg.theme(tag="radio_theme"):
        with dpg.theme_component(dpg.mvRadioButton):
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (200, 200, 200))  # White selection circle
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 18, 4)  # Spacing between radio buttons
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 5, 4)  # Spacing within the radio button

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
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_3_button)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)

    # Revert GPU theme
    with dpg.theme(tag="revert_gpu_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_6_buttonstateactive)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
        #with dpg.theme_component(dpg.mvAll):
            #dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_8_text_stateactive)

    # Button right theme
    with dpg.theme(tag="button_right"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 1.00, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_Button, background_colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, background_colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, background_colour, category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)

    # Plot themes
    with dpg.theme(tag="fixed_greyline_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (160, 160, 200, 255), category=dpg.mvThemeCat_Plots)

    with dpg.theme(tag="fps_cap_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128, 150), category=dpg.mvThemeCat_Plots)

    # Transparent input theme (for log window)
    with dpg.theme(tag="transparent_input_theme"):
        with dpg.theme_component(dpg.mvInputText):
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

    # Transparent input theme (for dynamic text display)
    with dpg.theme(tag="transparent_input_theme_2"):
        with dpg.theme_component(dpg.mvInputText):
            #dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)

    with dpg.theme(tag="plot_bg_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (0, 200, 255, 255))  # Example: cyan
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 200, 255, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_7_text_faded)