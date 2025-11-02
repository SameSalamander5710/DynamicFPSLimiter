import os
from pathlib import Path
import glob
import configparser

def _settings_path_for_base(base):
    config_dir = os.path.join(base, "config")
    settings_path = os.path.join(config_dir, "settings.ini")
    return config_dir, settings_path

def _is_first_launch(base):
    """Return True if settings.ini missing or first_launch_done is False."""
    _, settings_path = _settings_path_for_base(base)
    config = configparser.ConfigParser()
    if not os.path.exists(settings_path):
        return True
    try:
        config.read(settings_path)
        #print(config.get("Preferences", "first_launch_done", fallback=False))
        return not config.getboolean("Preferences", "first_launch_done", fallback=False)
    except Exception:
        return True

def _unblock_alternate_data_streams(root_dirs):

    base = root_dirs[0] if root_dirs else None
    if not _is_first_launch(base):
        return 

    for root in root_dirs:
        if not root:
            continue
        for pattern in ('*.dll', '*.exe', '*.pyd'):
            for path in Path(root).rglob(pattern):
                ads = f"{path}:Zone.Identifier"
                if os.path.exists(ads):
                    try:
                        os.remove(ads)
                    except Exception:
                        pass
    #print("unblocked dlls")
    return True

def mark_first_launch_done(base, cm):
    cm = cm
    config_dir, settings_path = _settings_path_for_base(base)
    config = configparser.ConfigParser()
    try:
        cm.update_preference_setting('first_launch_done', None, True, None)
        #print(f"Marked first_launch_done=True at {settings_path}")

        return True
    except Exception as exc:
        print(f"Failed to write settings.ini at {settings_path}: {exc!r}")