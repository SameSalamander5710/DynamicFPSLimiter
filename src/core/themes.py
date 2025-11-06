import dearpygui.dearpygui as dpg
import os

bg_colour = (21, 20, 21, 255)
bg_colour_1_transparent = (21, 20, 21, 0)
bg_colour_2_child = (27, 31, 37, 255)
#bg_colour_3_button = (35, 39, 47, 255)
bg_colour_3_button = (43, 47, 57, 255)
bg_colour_4_buttonhover = (32, 60, 68, 255)
bg_colour_4_buttonhover_blue = (15, 73, 114, 255)
bg_colour_5_buttonactive = (16, 63, 96, 255) # Blue
#bg_colour_6_buttonstateactive_orange = (200, 88, 45, 255)
bg_colour_7_text_faded = (150, 152, 161, 255) # Faded text for plot
bg_colour_8_text_enabled = (255, 255, 255, 255)
bg_colour_9_text_disabled = (150, 152, 161, 150) 
#bg_colour_10_button_disabled = (31, 35, 42, 255) 

class ThemesManager:
    def __init__(self, Base_dir):
        self.themes = {}
        self.base_dir = Base_dir
        self.fonts = {}
        
        # Font paths
        self.font_path = os.path.join(os.environ["WINDIR"], "Fonts", "segoeui.ttf")
        self.bold_font_path = os.path.join(os.environ["WINDIR"], "Fonts", "segoeuib.ttf")
        self.monospaced_font_path = os.path.join(os.environ["WINDIR"], "Fonts", "consola.ttf")

    def create_themes(self):
        with dpg.theme() as main_theme:
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
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_3_button)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
                dpg.add_theme_color(dpg.mvThemeCol_Tab, bg_colour_2_child)
                dpg.add_theme_color(dpg.mvThemeCol_TabActive, bg_colour_3_button)
                dpg.add_theme_color(dpg.mvThemeCol_TabHovered, bg_colour_4_buttonhover)
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, bg_colour)
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, bg_colour_4_buttonhover)
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, bg_colour_5_buttonactive)
                dpg.add_theme_color(dpg.mvThemeCol_Header, bg_colour_3_button)
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (255, 255, 255, 11)) # Example: light shadow for 3D effect
                #dpg.add_theme_color(dpg.mvThemeCol_PopupActive, (30, 144, 255, 255))

                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, bg_colour_2_child)
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, bg_colour_3_button)
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, bg_colour_4_buttonhover)
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, bg_colour_5_buttonactive)


                # Plot-specific styles
                dpg.add_theme_style(dpg.mvPlotStyleVar_PlotBorderSize, 0, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MinorAlpha, 0.20, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_MajorTickLen, 5, 5, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvPlotStyleVar_LabelPadding, 5, 2, category=dpg.mvThemeCat_Plots)
            
            with dpg.theme_component(dpg.mvInputInt):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 11))
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 11)) 
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_colour)

            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 0, 0, 11))
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 11))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_colour)

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

            disabled_comps = [dpg.mvInputText, dpg.mvButton, dpg.mvTabBar, dpg.mvTab, dpg.mvImage, dpg.mvMenuBar, dpg.mvViewportMenuBar, dpg.mvMenu, dpg.mvMenuItem, dpg.mvChildWindow, dpg.mvGroup, dpg.mvDragFloatMulti, dpg.mvSliderFloat, dpg.mvSliderInt, dpg.mvFilterSet, dpg.mvDragFloat, dpg.mvDragInt, dpg.mvInputFloat, dpg.mvInputInt, dpg.mvColorEdit, dpg.mvClipper, dpg.mvColorPicker, dpg.mvTooltip, dpg.mvCollapsingHeader, dpg.mvSeparator, dpg.mvCheckbox, dpg.mvListbox, dpg.mvText, dpg.mvCombo, dpg.mvPlot, dpg.mvSimplePlot, dpg.mvDrawlist, dpg.mvWindowAppItem, dpg.mvSelectable, dpg.mvTreeNode, dpg.mvProgressBar, dpg.mvSpacer, dpg.mvImageButton, dpg.mvTimePicker, dpg.mvDatePicker, dpg.mvColorButton, dpg.mvFileDialog, dpg.mvTabButton, dpg.mvDrawNode, dpg.mvNodeEditor, dpg.mvNode, dpg.mvNodeAttribute, dpg.mvTable, dpg.mvTableColumn, dpg.mvTableRow]
            for comp_type in disabled_comps:
                with dpg.theme_component(comp_type, enabled_state=False):
                    dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_9_text_disabled)
                    dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_2_child)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_2_child)
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_2_child)
                    dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (200, 200, 200))  # White selection circle
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_colour_2_child)
                    dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (255, 255, 255, 11))

            with dpg.theme_component(dpg.mvRadioButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_9_text_disabled)
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_2_child)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_2_child)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_2_child)
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (200, 200, 200))  # White selection circle
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 18, 4)  # Spacing between radio buttons
                dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 5, 4)  # Spacing within the radio button
        self.themes["main_theme"] = main_theme

        with dpg.theme() as radio_theme:
            with dpg.theme_component(dpg.mvRadioButton):
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (200, 200, 200))  # White selection circle
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 18, 4)  # Spacing between radio buttons
                dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 5, 4)  # Spacing within the radio button
        self.themes["radio_theme"] = radio_theme

        # RTSS running theme
        with dpg.theme() as start_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 100, 0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 120, 0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 140, 0))
        self.themes["start_button_theme"] = start_button_theme

        # RTSS not running theme
        with dpg.theme() as stop_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (170, 70, 70))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 90, 90))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (220, 90, 90))
        self.themes["stop_button_theme"] = stop_button_theme

        # Detect GPU theme
        with dpg.theme() as detect_gpu_theme:
            with dpg.theme_component(dpg.mvButton):
                #dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_3_button)
                #dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover_blue)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
        self.themes["detect_gpu_theme"] = detect_gpu_theme

        # Revert GPU theme
        with dpg.theme() as revert_gpu_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_5_buttonactive)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover_blue)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_5_buttonactive)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover_blue)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
            #with dpg.theme_component(dpg.mvAll):
                #dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_8_text_stateactive)
        self.themes["revert_gpu_theme"] = revert_gpu_theme

        # Button right theme
        with dpg.theme() as button_right_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 1.00, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
        self.themes["button_right_theme"] = button_right_theme

        # Button left theme
        with dpg.theme() as button_left_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.00, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
        self.themes["button_left_theme"] = button_left_theme

        # Button right theme
        with dpg.theme() as titlebar_button_theme:
            with dpg.theme_component(dpg.mvImageButton):
                #dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.50, 0.50, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour_1_transparent, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 0)
        self.themes["titlebar_button_theme"] = titlebar_button_theme

        with dpg.theme() as no_padding_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
        self.themes["no_padding_theme"] = no_padding_theme

        # Plot themes
        with dpg.theme() as fixed_greyline_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (160, 160, 200, 255), category=dpg.mvThemeCat_Plots)
        self.themes["fixed_greyline_theme"] = fixed_greyline_theme

        with dpg.theme() as fps_cap_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvPlotCol_Line, (128, 128, 128, 150), category=dpg.mvThemeCat_Plots)
        self.themes["fps_cap_theme"] = fps_cap_theme

        # Transparent input theme (for log window)
        with dpg.theme() as transparent_input_theme:
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
        self.themes["transparent_input_theme"] = transparent_input_theme

        # Transparent input theme (for dynamic text display)
        with dpg.theme() as transparent_input_theme_2:
            with dpg.theme_component(dpg.mvInputText):
                #dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                #dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 0, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0, 0, 0, 0), category=dpg.mvThemeCat_Core)
        self.themes["transparent_input_theme_2"] = transparent_input_theme_2

        with dpg.theme() as plot_bg_theme:
            with dpg.theme_component(dpg.mvAll):
                # Make plot background match the main window background
                dpg.add_theme_color(dpg.mvPlotCol_PlotBg, bg_colour, category=dpg.mvThemeCat_Plots)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                # Use child bg for plot child areas and keep frame/popup colors consistent
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, bg_colour_2_child, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_PopupBg, bg_colour, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, bg_colour, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Button, bg_colour, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, bg_colour_5_buttonactive, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, bg_colour_4_buttonhover, category=dpg.mvThemeCat_Core)
                dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_7_text_faded)
        self.themes["plot_bg_theme"] = plot_bg_theme

        with dpg.theme() as disabled_text_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_9_text_disabled)
        self.themes["disabled_text_theme"] = disabled_text_theme

        with dpg.theme() as enabled_text_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, bg_colour_8_text_enabled)
        self.themes["enabled_text_theme"] = enabled_text_theme

        with dpg.theme() as warning_text_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, (190, 90, 90))
        self.themes["warning_text_theme"] = warning_text_theme

        with dpg.theme() as nested_window_theme:
            with dpg.theme_component(dpg.mvWindowAppItem):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (180,180,180, 255))  # Border color (dark gray)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 1.0)      # Border thickness
                #dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 0.0)
            with dpg.theme_component(dpg.mvChildWindow):
                dpg.add_theme_color(dpg.mvThemeCol_Border, (255, 0, 0, 0))  
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1.0)

        self.themes["nested_window_theme"] = nested_window_theme

    def create_fonts(self, logger=None):
        """
        Create and register fonts for the application.
        Returns a dictionary of font references.
        """
        try:
            with dpg.font_registry():
                self.fonts["default_font"] = dpg.add_font(self.font_path, 18)
                self.fonts["bold_font"] = dpg.add_font(self.bold_font_path, 18)
                self.fonts["monospaced_font"] = dpg.add_font(self.monospaced_font_path, 14)
                self.fonts["bold_font_large"] = dpg.add_font(self.bold_font_path, 24)
            
                # Bind the default font globally
                if self.fonts["default_font"]:
                    dpg.bind_font(self.fonts["default_font"])
                    
            if logger:
                logger.add_log(f"Fonts loaded successfully")
                logger.add_log(f"Font {self.fonts['default_font']} set globally")
            return self.fonts
            
        except Exception as e:
            if logger:
                logger.add_log(f"Failed to load system font: {e}")
            # Will use DearPyGui's default font as fallback
            return self.fonts

    def get_font(self, font_name):
        """Get a specific font by name"""
        return self.fonts.get(font_name, None)
        
    def bind_font_to_item(self, item_id, font_name):
        """Bind a font to a specific item"""
        font = self.get_font(font_name)
        if font:
            dpg.bind_item_font(item_id, font)
            return True
        return False