# RTSS Integration

How the app talks to RivaTuner Statistics Server (RTSS). Read this before you change any FPS-cap write or FPS read code.

The app must run as Administrator because RTSS runs elevated. RTSS must be running for the hook DLL and the shared memory to exist.

## Interfaces used

| Direction | Mechanism | Module |
|---|---|---|
| Write cap | `RTSSHooks64.dll` profile API | `src/core/rtss_functions.py` |
| Write cap | Direct edit of profile `.cfg` files | `src/core/rtss_functions.py` |
| Read FPS | `RTSSSharedMemoryV2` shared memory | `src/core/rtss_interface.py` |
| Write cap (new) | `WriteProcessMemory` into the hooked game process | `src/core/rtss_memory_write.py` (callable, not wired into call sites) |

## Module map

- `rtss_functions.py` - `RTSSController` class. Owns write path A (DLL API) and write path B (`.cfg` edit). Single production instance created in `app.py` at import time, passed into `ConfigManager`.
- `rtss_interface.py` - `RTSSInterface` class. Read path (shared memory). Single instance in `app.py` (`rtss_manager`), used by `monitoring_loop`, `autopilot`, and `warning.py`.
- `rtss_memory_write.py` - converted from the standalone script into a callable module: `set_frameratelimit_memory_write(profile_name, framerate, logger=None)`. Not wired into any call site yet.

## Fractional limit encoding

RTSS stores a fractional cap as an integer numerator plus a denominator. Actual cap = numerator / denominator.

- DLL API property: `FramerateLimit` (numerator). Denominator property written through the `.cfg` key `LimitDenominator=`.
- `.cfg` keys: `Limit=` (numerator) and `LimitDenominator=`.
- Whole numbers use denominator 1. `0` is typically "unlimited" in RTSS.

Important subtlety: `set_fractional_framerate(profile, framerate, update=False, denominator=False)` writes the denominator only when the caller passes a truthy `denominator` argument. All production callers in `monitoring_loop` and `exit_gui` use the default, so they write only the numerator. The matching numerator + denominator pair is written together only by `start_stop_callback`, which first writes both keys with `set_fractional_fps_direct`, then re-applies the same value through the DLL API (call-site comment: "To update GUI").

### Value parsing (two implementations)

- `set_fractional_framerate` / `set_fractional_fps_direct`: string split on `.`; `denominator = 10 ** decimals`; `limit = int(round(float(framerate) * denominator))`. Uses float rounding.
- `parse_fps` in `rtss_memory_write.py`: exact `Decimal` parsing, rejects non-finite / negative / over-`MAX_FPS` values, enforces at most 4 decimal places, returns `(numerator, denominator)`.

## Write path A: DLL API

- Install dir resolved from registry `HKLM\SOFTWARE\WOW6432Node\Unwinder\RTSS` (`InstallPath`), fallback `HKLM\SOFTWARE\Unwinder\RTSS`, then `C:\Program Files (x86)\RivaTuner Statistics Server`. `RTSSHooks64.dll` is loaded from that dir with `ctypes.WinDLL`.
- On load failure (`OSError`) the injected `error_handler` is called with the DLL path; production passes `show_rtss_error_and_exit`, without a handler the error re-raises. Guarded by `tests/test_rtss_error_handler.py`.
- Exposed DLL functions: `LoadProfile`, `SaveProfile`, `GetProfileProperty`, `SetProfileProperty`, `DeleteProfile`, `ResetProfile`, `UpdateProfiles`, `SetFlags`.
- `set_profile_property` sequence: `LoadProfile` -> `SetProfileProperty` -> `SaveProfile` -> `UpdateProfiles`. All of it runs under `_profile_lock`.
- `set_fractional_framerate` parses the framerate, optionally writes the denominator, writes `FramerateLimit`, then ensures `UpdateProfiles` runs.
- Limiter on/off goes through `SetFlags` with `RTSSHOOKSFLAG_LIMITER_DISABLED = 4`. `enable_limiter()` runs once at app startup. `disable_limiter()` has no callers.

## Write path B: direct `.cfg` edit

- Profile files live in `<install dir>\Profiles`. The Global profile is the file `Global` (no extension, API name `""`); named profiles are `<profile_name>.cfg` (API name = profile name).
- `set_fractional_fps_direct` rewrites the `Limit=` and `LimitDenominator=` lines in place and appends them when missing (F4 fix).
- `set_limit_denominator` rewrites only `LimitDenominator=`.
- Both write through `_atomic_write_lines`: sibling `.tmp` file, flush + `fsync`, then `os.replace`. A crash or concurrent RTSS read never sees a half-written profile (F6 fix).

### Why two write paths coexist

By design, not by accident (see `docs/status.md` F6): file edits and DLL-API calls are separate writers kept apart deliberately. `start_stop_callback` uses the pair (file write persists both keys, API call makes RTSS pick it up live); the monitoring loop uses only the API path for fast live cap changes. There is no config setting that switches write paths; each call site hardcodes its path.

## Write path C (new): process memory write

`src/core/rtss_memory_write.py` writes the live numerator/denominator pair directly inside the game process, into the copy of `RTSSHooks64.dll` that RTSS injected there. It does not touch the `.cfg` file and does not use the DLL API.

Flow (`set_fps_limit(pid, num, den)`):

1. `OpenProcess` with VM read/write + query rights.
2. Find the `RTSSHooks64.dll` base in that process (`EnumProcessModulesEx` + `GetModuleFileNameExW`).
3. Verify the instruction signatures at both code offsets. Signature mismatch (different RTSS build) aborts before any write.
4. Read the current 8-byte pair, sanity-check it (`den >= 1`, value in range).
5. One 8-byte `WriteProcessMemory` so the limiter never sees a mismatched pair, then read back and compare.

Constants (specific to one RTSS build; the signature check guards this):

| Constant | Value | Meaning |
|---|---|---|
| `DLL_NAME` | `rtsshooks64.dll` | target module |
| `FIELD_OFFSET` | `0x2425D4` | numerator field (int32) |
| `DENOM_FIELD_OFFSET` | `FIELD_OFFSET + 4` | denominator field (int32) |
| `CODE_OFFSET` | `0x97684` | `mov [rbx+8D4],eax` instruction |
| `CODE_SIGNATURE` | `89 83 D4 08 00 00` | bytes at `CODE_OFFSET` |
| `DENOM_CODE_OFFSET` | `0x976A3` | `mov [rbx+8D8],eax` instruction |
| `DENOM_CODE_SIGNATURE` | `89 83 D8 08 00 00` | bytes at `DENOM_CODE_OFFSET` |
| `MAX_FPS` | `1000` | accepted range for the cap |
| `MAX_DECIMALS` | `4` | denominator capped at `10**4` |

Supporting helpers: `set_frameratelimit_memory_write()` (the callable entry point, below); `hooked_pids()` lists all processes with the RTSS hook loaded; `parse_fps()` parses the cap value; `list_rtss_profile_names()` reads the RTSS profile names from disk; `resolve_targets()` picks the processes a profile applies to; `read_mem` / `write_mem` wrap `ReadProcessMemory` / `WriteProcessMemory`.

### `set_frameratelimit_memory_write(profile_name, framerate, logger=None)`

The callable entry point. Meant to be swapped in at individual call sites alongside (not instead of) `set_fractional_framerate`:

- Parses the framerate with `parse_fps` (exact `Decimal`, accepts str/int/float/Decimal, returns `(num, den)`).
- `profile_name` is used directly as the process name - the same string the app already uses as the RTSS profile name (e.g. `mygame.exe`). Matched case-insensitively against `hooked_pids()`.
- `Global` targets every hooked process that has no specific RTSS profile: the profile names come from `list_rtss_profile_names()` (the `Profiles\*.cfg` files in the RTSS install dir, which mirrors how RTSS itself resolves a profile per exe).
- Writes with `set_fps_limit` (signature check + read-back included) into every target process. Global can hit several processes; each is written independently.
- Logs through `logger.add_log` (optional `logger` arg). Errors are logged, never raised, so the monitoring loop survives a failure (same degrade-gracefully pattern as `rtss_interface`).
- Returns `(numerator, denominator)` when at least one process was written, else `None`.

Constraints to remember:

- Bypasses `_profile_lock`; the lock only serializes `.cfg` + DLL-API writers.
- Does not persist to the `.cfg`. An RTSS profile reload (`UpdateProfiles`, RTSS UI save) overwrites the live value.
- Needs the game process to be running (no process -> logs + `None`), unlike the DLL-API path which works on profiles alone.
- Requires admin rights and the matching RTSS build (signature check). Unknown RTSS version -> refuses to write.

## Read path: shared memory

`RTSSInterface.get_fps_for_active_window()`:

1. `is_rtss_running()` checks for `RTSS.exe` via psutil. Also used by `warning.py` (shows "RTSS is not running") and `autopilot.py`.
2. Foreground window PID via `user32.GetForegroundWindow` + `GetWindowThreadProcessId`.
3. Opens mmap `RTSSSharedMemoryV2`, validates signature (`RTSS` / `SSTR`) and version >= 2.0, walks the app entry array, matches the PID.
4. FPS = `1000 * dwFrames / (dwTime1 - dwTime0)`. Returns `(Decimal fps, process_name)`; the name is the basename of the entry path.
5. Per-PID `dwTime0` cache: a repeated read of the same frame window returns `None` instead of the same FPS twice.

Missing shared memory (RTSS not running or OSD disabled) is handled as a normal "no data" case.

## Profile naming and switching

- RTSS profile name = executable name (e.g. `game.exe`), or `Global`.
- `cm.current_profile` holds the active profile; GUI dropdown sets it; default is `Global`.
- Autopilot (`monitoring_loop`): on `Global`, if the foreground process name matches a known profile section, switch to that profile. With a specific profile selected: `autopilot_only_profiles` stops monitoring when the foreground process changes, otherwise it switches back to `Global`.
- `cm.profiles_config` sections are the set of known profile names.

## Call sites (by context, no line numbers)

| Context | Call | Notes |
|---|---|---|
| `app.py` module init | `RTSSController(logger, error_handler=...)` | production instance |
| `app.py` module init | `rtss.enable_limiter()` | once, after monitors start |
| `app.py` module init | `RTSSInterface(logger, dpg)` | `rtss_manager` |
| `start_stop_callback` | `set_fractional_fps_direct` then `set_fractional_framerate` | both keys via file, then API refresh |
| `monitoring_loop` | `set_fractional_framerate` x5 | idle exit restore, cap decrease, cap increase, nearest-higher fallback, idle enter; all use `denominator=False` default |
| `exit_gui` | `set_fractional_framerate("Global", ...)` | only if `globallimitonexit` |
| `config_manager.delete_selected_profile_callback` | `delete_profile` | |

No live callers: `disable_limiter`, `get_framerate_limit`, `create_profile`, `reset_profile`, `set_flags`.

## Locking and threads

- `_profile_lock` (re-entrant `RTSSController`) serializes every `.cfg` edit and DLL-API mutation. Writers: monitoring thread (live cap changes), main/GUI thread (start/stop, exit), autopilot thread.
- Re-entrant so `set_fractional_framerate` can call `set_limit_denominator` / `set_profile_property` while holding it.
- The memory-write path takes no lock; it writes a different resource (process memory). If it ever runs next to profile reloads, ordering matters: reload wins.

## Tests

| File | Covers |
|---|---|
| `tests/test_rtss_fractional_direct.py` | F4: missing `Limit=` / `LimitDenominator=` lines get appended |
| `tests/test_rtss_atomic.py` | F6: concurrent writers serialized, atomic replace |
| `tests/test_rtss_error_handler.py` | injected `error_handler` on DLL load failure |
| `tests/test_rtss_memory_write.py` | `set_frameratelimit_memory_write`: parsing, profile/Global target resolution, log-and-return-`None` failures |
| `tests/test_smoke_import.py` | import guards for all core modules incl. `rtss_memory_write` |
| `tests/conftest.py` | `rtss_stub` fixture (file-based methods real, DLL methods stubbed) |

## Known gaps / future work

- No config toggle between write paths; each call site hardcodes one. This is the seam the memory-write method is meant to slot into.
- `set_frameratelimit_memory_write` exists but no call site uses it yet; not in the `architecture.md` module map.
- Memory-write path persists nothing; a profile reload overwrites it.
- Offsets/signatures are build-specific. RTSS update -> signature mismatch -> path stops working until the offsets are re-found (Cheat Engine search, per the script header).
- Two parsers with different rounding behavior: `set_fractional_framerate`'s inline str/float split vs exact `Decimal`. New code should prefer `parse_fps` (now accepts str and number types).
- `architecture.md` already lists "two competing RTSS write paths" as a known issue; this doc is the detail behind it.
