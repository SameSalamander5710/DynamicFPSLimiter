
#LHM GUI elements from DFL_v5

            with dpg.group(horizontal=True, tag="LHwM_group"):
                with dpg.child_window(width=280, height=205, border=False, tag="load_childwindow", show=False): 
                    dpg.add_spacer(height=1)
                    with dpg.group(horizontal=True):
                        dpg.add_text("GPU:")
                        dpg.add_combo(
                            tag="gpu_dropdown",
                            width=200,
                            default_value="Not detected. Use 'Legacy'.",
                            callback=cm.gpu_dropdown_callback
                        )
                    with dpg.group(horizontal=True):
                        with dpg.drawlist(width=15, height=15):
                            dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                        dpg.add_text("Load")
                        with dpg.drawlist(width=200, height=15):
                            dpg.draw_line((0, 13), (200, 13), color=(180,180,180), thickness=1)
                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column(width_fixed=True)  # Label
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_load_gpucore_enable", default_value=cm.settings["load_gpucore_enable"])
                                dpg.add_button(label="GPU Total:", tag="button_gpucore", width=85)
                                dpg.bind_item_theme("button_gpucore", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_load_gpucore_lower", default_value=str(cm.settings["load_gpucore_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_load_gpucore_upper", default_value=str(cm.settings["load_gpucore_upper"]), width=40)
                                dpg.add_text("%", tag="gpu_percent_text2", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_load_d3d3d_enable", default_value=cm.settings["load_d3d3d_enable"])
                                dpg.add_button(label="GPU 3D:", tag="button_d3d3d", width=85)
                                dpg.bind_item_theme("button_d3d3d", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_load_d3d3d_lower", default_value=str(cm.settings["load_d3d3d_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_load_d3d3d_upper", default_value=str(cm.settings["load_d3d3d_upper"]), width=40)
                                dpg.add_text("%", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_load_d3dcopy1_enable", default_value=cm.settings["load_d3dcopy1_enable"])
                                dpg.add_button(label="GPU Copy 1:", tag="button_d3dcopy1", width=85)
                                dpg.bind_item_theme("button_d3dcopy1", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_load_d3dcopy1_lower", default_value=str(cm.settings["load_d3dcopy1_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_load_d3dcopy1_upper", default_value=str(cm.settings["load_d3dcopy1_upper"]), width=40)
                                dpg.add_text("%", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_load_cputotal_enable", default_value=cm.settings["load_cputotal_enable"])
                                dpg.add_button(label="CPU Total:", tag="button_cputotal", width=85)
                                dpg.bind_item_theme("button_cputotal", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_load_cputotal_lower", default_value=str(cm.settings["load_cputotal_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_load_cputotal_upper", default_value=str(cm.settings["load_cputotal_upper"]), width=40)
                                dpg.add_text("%", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_load_cpucoremax_enable", default_value=cm.settings["load_cpucoremax_enable"])
                                dpg.add_button(label="CPU Core:", tag="button_cpucoremax", width=85)
                                dpg.bind_item_theme("button_cpucoremax", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_load_cpucoremax_lower", default_value=str(cm.settings["load_cpucoremax_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_load_cpucoremax_upper", default_value=str(cm.settings["load_cpucoremax_upper"]), width=40)
                                dpg.add_text("%", wrap=300)

                with dpg.child_window(width=-1, height=205, border=False, tag="temp_power_childwindow"):
                    with dpg.group(horizontal=True):
                        with dpg.drawlist(width=15, height=15):
                            dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                        dpg.add_text("Temperature")
                        with dpg.drawlist(width=165, height=15):
                            dpg.draw_line((0, 13), (165, 13), color=(180,180,180), thickness=1)
                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column(width_fixed=True)  # Label
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_temp_gpuhotspot_enable", default_value=cm.settings["temp_gpuhotspot_enable"])
                                dpg.add_button(label="GPU Hotspot:", tag="button_temp_gpuhotspot", width=90)
                                dpg.bind_item_theme("button_temp_gpuhotspot", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_temp_gpuhotspot_lower", default_value=str(cm.settings["temp_gpuhotspot_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_temp_gpuhotspot_upper", default_value=str(cm.settings["temp_gpuhotspot_upper"]), width=40)
                                dpg.add_text("°C", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_temp_gpucore_enable", default_value=cm.settings["temp_gpucore_enable"])
                                dpg.add_button(label="GPU Core:", tag="button_temp_gpucore", width=90)
                                dpg.bind_item_theme("button_temp_gpucore", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_temp_gpucore_lower", default_value=str(cm.settings["temp_gpucore_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_temp_gpucore_upper", default_value=str(cm.settings["temp_gpucore_upper"]), width=40)
                                dpg.add_text("°C", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_temp_cpupackage_enable", default_value=cm.settings["temp_cpupackage_enable"])
                                dpg.add_button(label="CPU Package:", tag="button_temp_cpupackage", width=90)
                                dpg.bind_item_theme("button_temp_cpupackage", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_temp_cpupackage_lower", default_value=str(cm.settings["temp_cpupackage_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_temp_cpupackage_upper", default_value=str(cm.settings["temp_cpupackage_upper"]), width=40)
                                dpg.add_text("°C", wrap=300)
                    with dpg.group(horizontal=True):
                        with dpg.drawlist(width=15, height=15):
                            dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                        dpg.add_text("Power Draw")
                        with dpg.drawlist(width=165, height=15):
                            dpg.draw_line((0, 13), (165, 13), color=(180,180,180), thickness=1)
                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column(width_fixed=True)  # Label
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_power_gpupackage_enable", default_value=cm.settings["power_gpupackage_enable"])
                                dpg.add_button(label="GPU Package:", tag="button_power_gpupackage", width=90)
                                dpg.bind_item_theme("button_power_gpupackage", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_power_gpupackage_lower", default_value=str(cm.settings["power_gpupackage_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_power_gpupackage_upper", default_value=str(cm.settings["power_gpupackage_upper"]), width=40)
                                dpg.add_text("W", wrap=300)
                        with dpg.table_row():
                            with dpg.group(horizontal=True):
                                dpg.add_checkbox(tag="input_power_cpupackage_enable", default_value=cm.settings["power_cpupackage_enable"])
                                dpg.add_button(label="CPU Package:", tag="button_power_cpupackage", width=90)
                                dpg.bind_item_theme("button_power_cpupackage", themes_manager.themes["button_left_theme"])
                                dpg.add_input_text(tag="input_power_cpupackage_lower", default_value=str(cm.settings["power_cpupackage_lower"]), width=40)
                                dpg.add_text("-", wrap=300)
                                dpg.add_input_text(tag="input_power_cpupackage_upper", default_value=str(cm.settings["power_cpupackage_upper"]), width=40)
                                dpg.add_text("W", wrap=300)

    with dpg.group(horizontal=True):
        mid_window_height = 280
        with dpg.child_window(width=240, height=mid_window_height, border=True):
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=15, height=15):
                    dpg.draw_line((0, 13), (15, 13), color=(180,180,180), thickness=1)
                dpg.add_text("Framerate Limits")
                with dpg.drawlist(width=85, height=15):
                    dpg.draw_line((0, 13), (85, 13), color=(180,180,180), thickness=1)
            with dpg.group(horizontal=True):
                with dpg.group(width=220, horizontal=False):
                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column(width_fixed=True)  # Column for labels
                        dpg.add_table_column(width_fixed=True)  # Column for input boxes
                        for label, key in [("Max FPS limit:", "maxcap"), 
                                        ("Min FPS limit:", "mincap"),
                                        ("Framerate ratio:", "capratio")]:
                            with dpg.table_row():
                                dpg.add_text(label, tag=f"label_{key}")
                                dpg.add_input_int(tag=f"input_{key}", default_value=int(cm.settings[key]), 
                                                    width=90, step=1, step_fast=10, 
                                                    min_clamped=True, min_value=1)
                                

                dpg.add_image_button(
                    texture_tag=textures["icon_save"],
                    tag="SaveToProfile",
                    callback=cm.save_to_profile,
                    width=120,
                    height=24
                )