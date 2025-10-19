#Note: Primarily made with AI, check properly in case of error

import os
import clr
import subprocess
import re

_LOADED = False
_Computer = None
_SensorType = None
_HardwareType = None

# new helpers for runtime detection and dll selection
def _detect_dotnet_framework():
    """Return .NET Framework version string like '4.7.2' or None (Windows only)."""
    try:
        import winreg
    except Exception:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")
        release, _ = winreg.QueryValueEx(key, "Release")
    except Exception:
        return None

    release_map = [
        (528040, "4.8"),
        (461808, "4.7.2"),
        (461308, "4.7.1"),
        (460798, "4.7"),
        (394802, "4.6.2"),
        (394254, "4.6.1"),
        (393295, "4.6"),
        (379893, "4.5.2"),
        (378675, "4.5.1"),
        (378389, "4.5"),
    ]
    for rel_val, ver in release_map:
        if release >= rel_val:
            return ver
    return None


def _detect_dotnet_core():
    """Return highest installed .NET Core / .NET 5+ runtime version string (e.g. '6.0.21') or None."""
    # try `dotnet --list-runtimes`
    try:
        out = subprocess.check_output(["dotnet", "--list-runtimes"], stderr=subprocess.DEVNULL, text=True)
        versions = []
        for line in out.splitlines():
            m = re.match(r"^(?:Microsoft\.NETCore\.App|Microsoft\.AspNetCore\.App|Microsoft\.WindowsDesktop\.App)\s+([\d\.]+)", line)
            if m:
                versions.append(m.group(1))
        if versions:
            # pick highest by tuple comparison
            versions.sort(key=lambda s: tuple(int(p) for p in s.split('.')), reverse=True)
            return versions[0]
    except Exception:
        pass

    # fallback: scan C:\Program Files\dotnet\shared
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    shared = os.path.join(pf, "dotnet", "shared")
    if os.path.isdir(shared):
        max_ver = None
        for folder in os.listdir(shared):
            folder_path = os.path.join(shared, folder)
            if os.path.isdir(folder_path):
                for v in os.listdir(folder_path):
                    try:
                        # simple validation
                        tuple(map(int, v.split('.')[:3]))
                        if max_ver is None or tuple(map(int, v.split('.'))) > tuple(map(int, max_ver.split('.'))):
                            max_ver = v
                    except Exception:
                        continue
        return max_ver
    return None

def _choose_asset_variant(base_dir):
    """
    Pick best asset variant folder name (e.g. 'net472', 'net6.0', 'netstandard2.0').
    Returns folder name (string) or None.
    """
    assets_root = os.path.join(base_dir, "assets") if base_dir else None
    # available variants are folders under assets
    available = set()
    if assets_root and os.path.isdir(assets_root):
        # if assets contains a single package folder (like LHM_0.9.4_lib), descend into it
        children = [n for n in os.listdir(assets_root) if os.path.isdir(os.path.join(assets_root, n))]
        if len(children) == 1:
            nested = os.path.join(assets_root, children[0])
            # check for variant folders inside nested
            nested_children = [n for n in os.listdir(nested) if os.path.isdir(os.path.join(nested, n))]
            if nested_children:
                assets_root = nested
        available = set(n for n in os.listdir(assets_root) if os.path.isdir(os.path.join(assets_root, n)))

    # prefer modern .NET runtimes if present
    core_ver = _detect_dotnet_core()
    if core_ver:
        major = core_ver.split('.')[0]
        candidates = [f"net{major}.0", f"net{core_ver}", "netstandard2.0"]
        for c in candidates:
            if c in available:
                return c

    # fallback to .NET Framework detection
    fx = _detect_dotnet_framework()
    if fx:
        # normalize 4.7.2 -> net472
        variant = "net" + fx.replace('.', '')
        if variant in available:
            return variant
        # common alternate folder names
        if "net48" in available:
            return "net48"
        if "net472" in available:
            return "net472"

    # last resort: netstandard2.0 if provided, or any folder containing 'net'
    if "netstandard2.0" in available:
        return "netstandard2.0"
    for a in sorted(available, reverse=True):
        if a.startswith("net"):
            return a
    return None


def ensure_loaded(base_dir=None):
    """
    Ensure the LibreHardwareMonitor assembly is loaded and return (Computer, SensorType, HardwareType).
    Call with base_dir from the main module (Base_dir) when available.
    """
    global _LOADED, _Computer, _SensorType, _HardwareType
    if _LOADED:
        return _Computer, _SensorType, _HardwareType

    # choose appropriate dll variant under assets
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # project root guess

    variant = _choose_asset_variant(base_dir)
    print(f"Loading LibreHardwareMonitorLib.dll variant: {variant or 'default'}") #TODO: remove debug print
    if variant:
        dll_path = os.path.join(base_dir, 'assets', variant, 'LibreHardwareMonitorLib.dll')
        if not os.path.isfile(dll_path):
            dll_path = os.path.join(base_dir, 'assets', 'LHM_0.9.4_lib', 'net472', 'LibreHardwareMonitorLib.dll')  # fallback
    else:
        dll_path = os.path.join(base_dir, 'assets', 'LHM_0.9.4_lib', 'net472', 'LibreHardwareMonitorLib.dll')

    try:
        clr.AddReference(str(dll_path))
    except Exception:
        # best-effort; other modules may still import
        pass

    from LibreHardwareMonitor.Hardware import Computer, SensorType, HardwareType
    _Computer, _SensorType, _HardwareType = Computer, SensorType, HardwareType
    _LOADED = True
    return _Computer, _SensorType, _HardwareType

def get_types(base_dir=None):
    return ensure_loaded(base_dir)