# Standalone CLI (run from src/):
#   python -m core.rtss_memory_write 60 mygame.exe
#   python -m core.rtss_memory_write 42.32 mygame.exe   # fractional fps, up to MAX_DECIMALS places
#   python -m core.rtss_memory_write 144                # all hooked processes
#   python -m core.rtss_memory_write                    # just list hooked processes
# Compatible with RTSS 7.3.7


import ctypes
import ctypes.wintypes as w
import os
import struct
import sys
from decimal import Decimal, InvalidOperation

import psutil

from core.rtss_functions import get_rtss_install_path

DLL_NAME = "rtsshooks64.dll"

# Numerator ("FramerateLimit") field + the instruction that writes it.
FIELD_OFFSET = 0x2425D4          # fps limit numerator field (int32)
CODE_OFFSET = 0x97684            # the "mov [rbx+8D4],eax" instruction
CODE_SIGNATURE = bytes.fromhex("89 83 D4 08 00 00")

# Denominator ("FramerateLimitDenominator") field, same struct, next int32
# (0x8D4 -> 0x8D8)
DENOM_FIELD_OFFSET = FIELD_OFFSET + 4
DENOM_CODE_OFFSET = 0x976A3      # the "mov [rbx+8D8],eax" instruction
DENOM_CODE_SIGNATURE = bytes.fromhex("89 83 D8 08 00 00")

MAX_FPS = 1000                   # 0 is typically "unlimited" in RTSS
MAX_DECIMALS = 4                 # denominator capped at 10**MAX_DECIMALS

PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
ACCESS = (PROCESS_VM_OPERATION | PROCESS_VM_READ |
          PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION)
LIST_MODULES_ALL = 0x03

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

k32.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
k32.OpenProcess.restype = w.HANDLE
k32.CloseHandle.argtypes = [w.HANDLE]
k32.ReadProcessMemory.argtypes = [w.HANDLE, w.LPCVOID, w.LPVOID,
                                  ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = w.BOOL
k32.WriteProcessMemory.argtypes = [w.HANDLE, w.LPVOID, w.LPCVOID,
                                   ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
k32.WriteProcessMemory.restype = w.BOOL
psapi.EnumProcessModulesEx.argtypes = [w.HANDLE, ctypes.POINTER(w.HMODULE),
                                       w.DWORD, ctypes.POINTER(w.DWORD),
                                       w.DWORD]
psapi.GetModuleFileNameExW.argtypes = [w.HANDLE, w.HMODULE, w.LPWSTR, w.DWORD]


def find_module_base(h):
    """Return base address of RTSSHooks64.dll in the process, or None."""
    needed = w.DWORD()
    psapi.EnumProcessModulesEx(h, None, 0, ctypes.byref(needed),
                               LIST_MODULES_ALL)
    count = needed.value // ctypes.sizeof(w.HMODULE)
    if count == 0:
        return None
    arr = (w.HMODULE * count)()
    if not psapi.EnumProcessModulesEx(h, arr, needed.value,
                                      ctypes.byref(needed),
                                      LIST_MODULES_ALL):
        return None
    buf = ctypes.create_unicode_buffer(1024)
    for m in arr:
        if psapi.GetModuleFileNameExW(h, m, buf, 1024) and \
                buf.value.lower().endswith(DLL_NAME):
            return m
    return None


def read_mem(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, addr, buf, size, ctypes.byref(got)) \
            or got.value != size:
        raise OSError(f"read failed at {addr:#x}: {ctypes.get_last_error()}")
    return buf.raw


def write_mem(h, addr, data):
    put = ctypes.c_size_t()
    if not k32.WriteProcessMemory(h, addr, data, len(data),
                                  ctypes.byref(put)) or put.value != len(data):
        raise OSError(f"write failed at {addr:#x}: {ctypes.get_last_error()}")


def parse_fps(text):
    """Parse exactly as typed (no float). Accepts str or any number type.
    Returns (numerator, denominator).

    42.32 -> (4232, 100), 60 -> (60, 1), 60.0 -> (60, 1)
    """
    if not isinstance(text, str):
        text = str(text)
    try:
        d = Decimal(text.strip())
    except InvalidOperation:
        raise ValueError(f"not a number: {text!r}")
    if not d.is_finite() or d < 0 or d > MAX_FPS:
        raise ValueError(f"fps must be 0..{MAX_FPS}")
    d = d.normalize()                          # 60.0 -> 6E+1, 42.320 -> 42.32
    decimals = max(0, -d.as_tuple().exponent)  # negative exponent = decimals
    if decimals > MAX_DECIMALS:
        raise ValueError(f"at most {MAX_DECIMALS} decimal places allowed")
    den = 10 ** decimals
    num = int(d * den)
    return num, den


def list_rtss_profile_names():
    """Lowercase exe names of every specific RTSS profile on disk.

    Reads <RTSS install>\\Profiles\\*.cfg (mygame.exe.cfg -> mygame.exe).
    The Global profile itself is not included.
    """
    profiles_dir = os.path.join(get_rtss_install_path(), "Profiles")
    names = set()
    try:
        entries = os.listdir(profiles_dir)
    except OSError:
        return names
    for entry in entries:
        if entry.lower().endswith(".cfg"):
            names.add(entry[:-4].lower())
    return names


def resolve_targets(hooked, profile_name, profile_names=frozenset()):
    """Pick the hooked (pid, name) pairs a profile applies to.

    profile_name is matched directly against the process name (same string
    the app uses as the RTSS profile name). "Global" keeps only processes
    with no specific RTSS profile.
    """
    name = str(profile_name).lower()
    if name == "global":
        return [(pid, pname) for pid, pname in hooked
                if pname.lower() not in profile_names]
    return [(pid, pname) for pid, pname in hooked if pname.lower() == name]


def set_fps_limit(pid, num, den):
    h = k32.OpenProcess(ACCESS, False, pid)
    if not h:
        raise PermissionError(
            f"OpenProcess failed ({ctypes.get_last_error()}); try admin")
    try:
        base = find_module_base(h)
        if base is None:
            raise RuntimeError("RTSSHooks64.dll not loaded in this process")

        # Version check on BOTH instructions
        if (read_mem(h, base + CODE_OFFSET, len(CODE_SIGNATURE)) != CODE_SIGNATURE
                or read_mem(h, base + DENOM_CODE_OFFSET,
                            len(DENOM_CODE_SIGNATURE)) != DENOM_CODE_SIGNATURE):
            raise RuntimeError("Signature mismatch: different RTSS version. "
                               "Redo the CE search; refusing to write.")

        # Numerator and denominator are adjacent int32s: read/write together
        addr = base + FIELD_OFFSET
        old_num, old_den = struct.unpack("<ii", read_mem(h, addr, 8))
        # RTSS stores denominator 1 for whole numbers, so require >= 1
        if old_den < 1 or not (0 <= old_num / old_den <= MAX_FPS):
            raise RuntimeError(
                f"Current value {old_num}/{old_den} looks wrong; aborting.")
        old_fps = old_num / old_den

        # Single 8-byte write so the limiter never sees a mismatched pair
        write_mem(h, addr, struct.pack("<ii", num, den))
        got = struct.unpack("<ii", read_mem(h, addr, 8))
        if got != (num, den):
            raise RuntimeError(f"Read-back mismatch: got {got}")
        return old_fps, num / den
    finally:
        k32.CloseHandle(h)


def set_frameratelimit_memory_write(profile_name, framerate, logger=None):
    """Set the RTSS framerate limit by writing into hooked game processes.

    profile_name is the process name (e.g. mygame.exe); "Global" targets
    every hooked process that has no specific RTSS profile.
    Returns (numerator, denominator) when at least one process was written,
    else None. Errors are logged, not raised.
    """
    def log(message):
        if logger is not None:
            logger.add_log(message)

    profile_name = str(profile_name)
    try:
        num, den = parse_fps(framerate)
    except ValueError as e:
        log(f"Memory write {profile_name}: {e}")
        return None

    try:
        hooked = hooked_pids()
        if profile_name.lower() == "global":
            targets = resolve_targets(hooked, profile_name,
                                      list_rtss_profile_names())
        else:
            targets = resolve_targets(hooked, profile_name)
    except Exception as e:
        log(f"Memory write {profile_name}: process search failed: {e}")
        return None

    if not targets:
        log(f"Memory write {profile_name}: no hooked process found "
            "(is the game running?)")
        return None

    written = 0
    for pid, name in targets:
        try:
            set_fps_limit(pid, num, den)
            written += 1
        except Exception as e:
            log(f"Memory write {name} (PID {pid}) failed: {e}")

    if written == 0:
        return None
    total = len(targets)
    suffix = "" if written == total else f" ({written}/{total} ok)"
    log(f"Memory write {profile_name}: {num / den:g} ({num}/{den}) "
        f"on {total} process(es){suffix}")
    return num, den


def hooked_pids():
    """All processes that currently have the RTSS hook loaded."""
    out = []
    for p in psutil.process_iter(["pid", "name"]):
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                            False, p.info["pid"])
        if not h:
            continue
        try:
            if find_module_base(h):
                out.append((p.info["pid"], p.info["name"]))
        finally:
            k32.CloseHandle(h)
    return out


if __name__ == "__main__":
    # usage: python -m core.rtss_memory_write <fps> [pid|exe_name]
    if len(sys.argv) < 2:
        print("Hooked processes:", hooked_pids())
        print("usage: python -m core.rtss_memory_write <fps> [pid|exe_name]")
        sys.exit(1)

    try:
        num, den = parse_fps(sys.argv[1])
    except ValueError as e:
        print(e)
        sys.exit(1)
    target = sys.argv[2] if len(sys.argv) > 2 else None

    candidates = hooked_pids()
    if target:
        candidates = [(pid, n) for pid, n in candidates
                      if str(pid) == target or n.lower() == target.lower()]
    if not candidates:
        print("No matching hooked process found (is RTSS running?)")
        sys.exit(2)

    for pid, name in candidates:
        try:
            old, new = set_fps_limit(pid, num, den)
            print(f"{name} (PID {pid}): {old:g} -> {new:g}  ({num}/{den})")
        except Exception as e:
            print(f"{name} (PID {pid}): FAILED - {e}")
