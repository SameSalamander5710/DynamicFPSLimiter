import os
from pathlib import Path
import glob
import configparser

def _unblock_alternate_data_streams(root_dirs):

    # determine config path (use first root if provided)
    parent_dir = root_dirs[0]
    config_dir = os.path.join(parent_dir, "config")
    settings_path = os.path.join(config_dir, "settings.ini")

    config = configparser.ConfigParser()
    first_done = False
    if os.path.exists(settings_path):
        try:
            config.read(settings_path)
            first_done = config.getboolean("Preferences", "first_launch_done", fallback=False)
        except Exception:
            first_done = False

    if first_done:
        return  # nothing to do

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

    # mark as completed
    try:
        os.makedirs(config_dir, exist_ok=True)
        if not config.has_section("Preferences"):
            config["Preferences"] = {}
        config["Preferences"]["first_launch_done"] = "True"
        with open(settings_path, "w") as f:
            config.write(f)
    except Exception:
        # ignore write failures
        pass