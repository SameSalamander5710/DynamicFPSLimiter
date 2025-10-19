import os
import clr

# ...existing code...
_LOADED = False
_Computer = None
_SensorType = None
_HardwareType = None

def ensure_loaded(base_dir=None):
    """
    Ensure the LibreHardwareMonitor assembly is loaded and return (Computer, SensorType, HardwareType).
    Call with base_dir from the main module (Base_dir) when available.
    """
    global _LOADED, _Computer, _SensorType, _HardwareType
    if _LOADED:
        return _Computer, _SensorType, _HardwareType

    dll_path = os.path.join(base_dir, 'assets', 'LibreHardwareMonitorLib.dll')
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