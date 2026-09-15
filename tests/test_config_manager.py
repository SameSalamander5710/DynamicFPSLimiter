"""Exercise settings callbacks without a Windows GUI or hardware sensors."""

import configparser
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

dpg = ModuleType("dearpygui.dearpygui")
dearpygui = ModuleType("dearpygui")
dearpygui.dearpygui = dpg
sensors = ModuleType("core.librehardwaremonitor")
sensors.get_all_sensor_infos = lambda base_dir: []
with patch.dict(sys.modules, {
    "dearpygui": dearpygui,
    "dearpygui.dearpygui": dpg,
    "core.librehardwaremonitor": sensors,
}):
    from core.config_manager import ConfigManager


class GlobalSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.values = {}
        dpg.get_value = self.values.get
        dpg.set_value = self.values.__setitem__
        dpg.configure_item = Mock()
        self.cm = self.make_manager()
        self.values.update({
            f"input_{key}": self.cm.settings[key]
            for key in self.cm.input_field_keys
        })
        self.values["profile_dropdown"] = "Global"

    def make_manager(self):
        cm = ConfigManager(Mock(), dpg, Mock(), None,
                           SimpleNamespace(themes={}),
                           str(Path(self.temp.name) / "core"))
        cm.refresh_ui_callbacks = Mock()
        cm.update_global_variables()
        return cm

    def assert_idle_settings(self, cm):
        self.assertEqual(cm.idle_fps_cap, 10)
        self.assertEqual(cm.idle_fps_delay, 25)
        saved = configparser.ConfigParser()
        saved.read(cm.settings_path)
        for key in ("idle_fps_cap", "idle_fps_delay"):
            self.assertEqual(cm.settings[key], getattr(cm, key))
            self.assertEqual(saved.getint("GlobalSettings", key), getattr(cm, key))

    def test_idle_settings_survive_profile_operations_and_restart(self):
        cm = self.cm
        for key, value in (("idle_fps_cap", 10), ("idle_fps_delay", 25)):
            cm.update_GlobalSettings_settings_callback(key)(key, value, None)
        cm.make_update_preference_callback("idle_mode")(None, True, None)

        self.values["LastProcess"] = "bf6.exe"
        cm.add_process_profile_callback()
        self.assertEqual(cm.current_profile, "bf6.exe")
        self.assert_idle_settings(cm)
        self.values["new_profile_input"] = "manual.exe"
        cm.add_new_profile_callback()
        cm.save_to_profile()
        cm.load_profile_callback(None, "Global", None)
        cm.load_profile_callback(None, "bf6.exe", None)
        cm.quick_save_settings()
        cm.quick_load_settings()
        cm.reset_to_program_default()
        cm.apply_current_input_values()
        cm.delete_selected_profile_callback()
        self.assert_idle_settings(cm)
        self.assertTrue(cm.idle_mode)

        restarted = self.make_manager()
        restarted.load_profile_callback(None, "bf6.exe", None)
        self.assert_idle_settings(restarted)
        self.assertTrue(restarted.idle_mode)
        self.assertNotIn("idle_fps_cap", restarted.profiles_config["bf6.exe"])
        self.assertNotIn("idle_fps_delay", restarted.profiles_config["bf6.exe"])

    def test_invalid_idle_settings_leave_last_valid_values(self):
        for key, value in (("idle_fps_cap", 10), ("idle_fps_delay", 25)):
            callback = self.cm.update_GlobalSettings_settings_callback(key)
            callback(key, value, None)
            for invalid in (0, -1):
                callback(key, invalid, None)
                self.assertEqual(self.values[key], value)
        self.cm.update_global_variables()
        self.assert_idle_settings(self.cm)


if __name__ == "__main__":
    unittest.main()
