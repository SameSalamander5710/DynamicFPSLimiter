# Dynamic FPS Limiter — Architecture

> Companion to `flaws.md` (glaring issues) and `HOW_IT_WORKS.md` (marked outdated, v4 logic only).
> This document describes the **current v5.0.0-beta.1** codebase.

## 1. Overview

**Dynamic FPS Limiter (DFL)** is a Windows-only desktop companion for **RivaTuner Statistics
Server (RTSS)**. It continuously watches GPU/CPU load, power draw and temperature, and
dynamically raises or lowers the **FPS cap** of the active game's RTSS profile — preserving
GPU headroom (especially for Lossless Scaling frame generation) without a manually chosen
fixed cap.

- **GUI**: DearPyGui (Dear ImGui) single window + a pystray system-tray icon.
- **Hardware reads (primary)**: LibreHardwareMonitorLib (a .NET DLL loaded via `pythonnet`),
  exposing per-sensor Load / Power / Temperature for CPU and every GPU.
- **Hardware reads (fallback "Legacy")**: Windows Performance Counters (PDH via `ctypes`) for
  per-LUID 3D-engine GPU utilization, and `psutil` for per-core CPU usage.
- **Actuation**: writes the FPS limit into RTSS profiles through the `RTSSHooks64.dll` API and
  direct edits to the profile `.cfg` files; reads the live FPS back from RTSS shared memory.
- **Privileges**: must run as **Administrator** (RTSS runs elevated).
- **Packaging**: PyInstaller `--onedir`, `--uac-admin`, code-signed.
- **Author / license**: SameSalamander5710, Apache 2.0 (relicensed from MIT on 2025-04-25).

### Design intent
A fixed cap set below average FPS causes input lag when the GPU saturates; a cap set far below
the lowest FPS wastes frame rate in light scenes. DFL closes the loop: it lowers the cap when
sustained load is high and raises it (with a cooldown) when load is low, reacting to **trends**
(rolling buffers + percentiles + delay counters) rather than instantaneous spikes.

## 2. System diagram

```
                        ┌────────────────────────────────────────────────────────┐
                        │                     MAIN THREAD                        │
                        │            DearPyGui render loop (blocking)            │
                        │                                                        │
                        │   UI (profile, cap params, plots, LHM tables, FAQ)     │
                        │   gui_update_loop (0.1s)   autopilot_loop (1s)         │
                        └───────────────▲───────────────────────────▲────────────┘
                                        │ dpg.* (NOT thread-safe)   │
        ┌───────────────────────────────┴──────────────┐            │
        │              BACKGROUND THREADS (daemon)      │            │
        │                                              │            │
        │  monitoring_loop (1s)  ──► decision engine    │            │
        │  plotting_loop         ──► usage plots        │            │
        │  LHMSensor._poll_loop  ──► LHM percentiles    │            │
        │  GPUUsageMonitor       ──► PDH 3D utilization │            │
        │  CPUUsageMonitor       ──► psutil CPU         │            │
        │  pystray tray thread   ──► menu/restore/exit ─┘            │
        └───────┬───────────────────────────────┬───────────────────┘
                │ sense                         │ act
                ▼                               ▼
   ┌───────────────────────────┐     ┌───────────────────────────────┐
   │  SENSORS                  │     │  RTSS                         │
   │  • LibreHardwareMonitorLib│     │  • RTSSHooks64.dll API        │
   │  • PDH (ctypes)           │     │  • Profiles\<name>.cfg edits  │
   │  • psutil                 │     │  • RTSSSharedMemoryV2 (FPS in)│
   │  • Win32 GetLastInputInfo │     └───────────────────────────────┘
   └───────────────────────────┘
```

## 3. Threading model

The **main thread** owns the DearPyGui render loop (the explicit loop at the end of
`DFL_v5.py`). Everything else is a daemon thread. **DearPyGui is not thread-safe**; all
background-thread DPG calls are marshalled onto the main thread via the `GuiQueue`, which the
main render loop drains once per frame (F3 fix — see `flaws.md`).

| Thread | Started by | Period | Touches DPG? |
|---|---|---|---|
| Main (render) | explicit loop, end of `DFL_v5.py` | continuous | yes (owner) |
| `gui_update_loop` | module init (DFL_v5:1213) | 0.1 s | yes (warnings, log, cap viz) |
| `autopilot_loop` | module init (DFL_v5:1217) | 1 s | yes (profile switch) |
| `monitoring_loop` | Start button | 1 s | yes (series, plots) |
| `plotting_loop` | Start button | `lcm(gpu,cpu interval)` | yes (usage plot) |
| `LHMSensor._poll_loop` | Start | `lhwmonitorpollinginterval` ms | yes (readings table) |
| `GPUUsageMonitor.gpu_run` | constructed | `gpupollinginterval` ms | no (PDH only) |
| `CPUUsageMonitor.cpu_run` | constructed | `cpupollinginterval` ms | no (psutil only) |
| pystray tray | `TrayManager.show_tray` | event-driven | yes (menu callbacks) |
| `logger.add_log` | from many threads | — | yes (log text) |

**Synchronization**: sensor history/percentile state is guarded by `threading.Lock` inside
`LHMSensor`, `GPUUsageMonitor` and `CPUUsageMonitor`. The DPG UI state and the module-level
decision globals (`running`, `CurrentFPSOffset`, `fps_values`, `gpu_values`, `idle_state`, …)
are shared **without locks**; `monitoring_loop` writes them while GUI callbacks read/write them.

## 4. Module map

| Module | Role |
|---|---|
| `src/__main__.py` | Entry point: UAC self-elevation (dev mode), `--build` PyInstaller runner |
| `src/core/DFL_v5.py` | Main app: all DPG UI, the four background loops, orchestration (~1,270 lines, no app class) |
| `src/core/config_manager.py` | INI load/save, defaults, profile management, GUI↔config sync, dynamic LHM keys; maintains a `current_method` snapshot (init + `current_method_callback`) for the tray hover text (F3 fix) |
| `src/core/fps_utils.py` | FPS-cap ladder (custom/step/ratio) + core `evaluate_cap_change` decision engine; `current_stepped_limits()` is total — always returns a non-empty list, falling back to the stepped ladder on bad/unknown capmethod (F5 fix) |
| `src/core/cap_policy.py` | Pure cap **decrease** policy (`next_cap_on_decrease`), extracted from `DFL_v5` (F1 fix); no GUI/RTSS/.NET deps |
| `src/core/librehardwaremonitor.py` | `LHMSensor` polling thread + `get_all_sensor_infos` hardware discovery; degrades to a disabled no-sensor state when LHM is unavailable (F2 fix); `start()` re-opens a closed `Computer` so Stop→Start keeps working and `get_all_sensor_infos` closes its one-shot `Computer` (F7 fix) |
| `src/core/lhm_loader.py` | pythonnet CLR bootstrap, .NET runtime detection, DLL-variant selection; raises `LHMLoadError` on load failure (F2 fix) |
| `src/core/gpu_monitor.py` | Legacy GPU usage via PDH performance counters (per-LUID 3D engine); `initialize()` closes the prior PDH query before re-opening and `reinitialize()` re-assigns `counter_handles` (F8 fix); `get_gpu_usage()` reuses the live query (no re-init), `self.luid` reads/writes are lock-guarded, and its `dpg.*` calls defer to the `GuiQueue` (F9 fix) |
| `src/core/gui_queue.py` | Thread-safe `GuiQueue` — background threads `submit(fn, *args, **kwargs)`; the main render loop in `DFL_v5.py` `drain()`s the queue once per frame on the main thread (per-callback exception isolation, optional `on_error`) so DearPyGui is only touched on the main thread. Injected into `GPUUsageMonitor`, `logger`, and `TrayManager` (F3 fix — complete) |
| `src/core/cpu_monitor.py` | Legacy CPU usage via psutil (per-core max) |
| `src/core/rtss_functions.py` | `RTSSController`: loads `RTSSHooks64.dll`, profile API + `.cfg` edits; `set_fractional_fps_direct` safely appends missing `Limit=`/`LimitDenominator=` lines (F4 fix); all profile file + API mutations are serialized behind an `RLock` and file writes are atomic via `_atomic_write_lines` (tmp + `os.replace`) (F6 fix) |
| `src/core/rtss_interface.py` | `RTSSInterface`: reads live FPS from `RTSSSharedMemoryV2` |
| `src/core/tray_functions.py` | pystray tray icon + Win32 taskbar show/hide + title-bar drag; every pystray-thread action (start/stop toggle, profile/method menu, restore/exit) and `update_hover_text` are routed to the main DPG thread via an injected `GuiQueue` (`_run_on_main`), and the hover text reads profile/method from the ConfigManager snapshot (F3 fix) |
| `src/core/themes.py` | DearPyGui theme + font definitions (`ThemesManager`) |
| `src/core/tooltips.py` | Central tooltip text registry + DPG apply helpers |
| `src/core/launch_popup.py` | Loading / missing-RTSS / RTSS-error popups (own DPG lifecycles) |
| `src/core/pre_launch.py` | First-launch detection + Zone.Identifier ADS unblock |
| `src/core/warning.py` | Active-warning computation (min>max, RTSS not running, …) |
| `src/core/autopilot.py` | Foreground-process detection + autopilot start/stop |
| `src/core/autostart.py` | `AutoStartManager`: `schtasks` Run-key create/delete |
| `src/core/idle_timer.py` | Win32 `GetLastInputInfo` idle duration (idle FPS-cap mode) |
| `src/core/logger.py` | logging setup, DPG log-text refresh, uncaught-exception hook; `log_messages` is lock-guarded (thread-safe) and the DPG `LogText` refresh is the only `dpg.*` touch point, run on the main thread via an injected `GuiQueue` (F3 fix) |
| `src/core/video2gif.py` | **Dev-only** CLI (MP4→GIF); not imported by the app |
| `src/core/backup_snippets.py` | **Not Python** — a notes snippet; not imported (see `flaws.md` #7) |

## 5. Core control loop (the decision engine)

`monitoring_loop` (DFL_v5, 1 s tick) is the heart of the app. Each tick:

1. **Read FPS** — `rtss_manager.get_fps_for_active_window()` → `(Decimal fps, process_name)`
   from RTSS shared memory.
2. **Autopilot** (if enabled) — detect the foreground process; switch to the matching profile
   (or `Global`), auto-start/stop as focus moves.
3. **On window change** — log it, update the "Last process" field, `gpu_monitor.reinitialize()`.
4. **Fill rolling buffers** — `fps_values` (last 3 → `fps_mean`), `gpu_values`/`cpu_values`
   (Legacy percentiles) or read LHM per-sensor percentiles.
5. **Idle check** — `get_idle_duration()` (seconds since last input).
6. **Cap decision** (only when GPU usage is valid and the active window isn't DFL itself):
   - **Active**: `fps_utils.evaluate_cap_change(gpu_values, cpu_values)` →
     `(should_decrease, should_increase)`.
      - **Decrease**: if not already at `mincap`, `cap_policy.next_cap_on_decrease` picks the
        next rung — one step down when `cap <= fps_mean`, a jump to the highest rung below
        `fps_mean` when `cap > fps_mean`, or the highest rung below the current cap when it is
        not on the ladder; `None` (no change) at the floor or empty ladder.
     - **Increase**: if below `maxcap` and the increase-cooldown has expired, step the cap
       **up one** ladder value; reset the cooldown to `delaybeforeincrease`.
   - **Idle**: record the active cap, drop to `idle_fps_cap` for `idle_fps_delay` seconds.
7. **Update UI** — series labels, FPS/cap plot (scaled to the cap range), summary statistics.

`evaluate_cap_change`:
- **Legacy**: `should_decrease` = all of the last `delaybeforedecrease` GPU samples
  ≥ `gpucutofffordecrease` **or** the same for CPU; `should_increase` = all of the last
  `delaybeforeincrease` samples ≤ the respective increase cutoffs (GPU **and** CPU).
- **LibreHM**: for each enabled sensor, compare its live percentile against the per-sensor
  `upper`/`lower` thresholds read from the GUI; `should_decrease = any(value ≥ upper)`,
  `should_increase = all(value ≤ lower)`.

The cap ladder (`current_stepped_limits`) depends on the profile's `capmethod`:
`custom` (user list), `step` (arithmetic), or `ratio` (geometric, `factor = 1 − ratio/100`).

## 6. Configuration system

Config lives in `<app dir>/config/` (`src/config/` in dev, next to the exe when frozen):

- **`settings.ini`**
  - `[Preferences]` (bools): `showtooltip`, `globallimitonexit`, `idle_mode`,
    `profileonstartup`, `launchonstartup`, `minimizeonstartup`, `autopilot`, `hide_unselected`,
    `autopilot_only_profiles`, `first_launch_done`, `hide_loading_popup`.
  - `[GlobalSettings]`: `minvalidgpu`, `minvalidfps`, `globallimitonexit_fps`, `idle_fps_cap`,
    `idle_fps_delay`, `cpu/gpu/lhwmonitor percentile`, `cpu/gpu/lhwmonitor polling interval`,
    `cpu/gpu/lhwmonitor samples`, `profileonstartup_name`.
- **`profiles.ini`** — one section per RTSS profile (`Global` is required/undeletable). Per
  profile: `maxcap`, `mincap`, `capratio`, `capstep`, the four cutoffs, the two delays,
  `capmethod`, `customfpslimits`, `monitoring_method` (LibreHM|Legacy), plus one
  `{param_id}_enable/_lower/_upper` row per discovered LHM sensor and `collapsing_{hw_id}` UI state.

`ConfigManager` is the state hub. Key behaviors:
- Discovers LHM hardware **at construction** (this is why the loading popup shows at import).
- Registers **dynamic** input keys for every discovered sensor after the UI is built.
- `apply_current_input_values()` pushes GUI fields → attributes (called on Start/Stop and
  profile switch); the monitoring loop reads thresholds from these attributes.
- Every preference change rewrites the full INI to disk immediately (non-atomic — see flaws).

## 7. External integrations

- **RTSS** — hard dependency. `RTSSController` locates the install dir via the
  `HKLM\…\Unwinder\RTSS` registry key and loads `RTSSHooks64.dll`. Missing DLL → the app shows a
  popup and exits. Caps are written via the profile API **and** direct `.cfg` text edits.
- **LibreHardwareMonitor** — `lhm_loader` boots the .NET CLR (`pythonnet`), detects the
  available .NET runtime (Framework 4.x / .NET Core), and picks the matching
  `LibreHardwareMonitorLib.dll` variant (net472 / net6.0 / net8.0 / netstandard2.0). Load
  failure raises `LHMLoadError` (with the attempted DLL path); every bootstrap site degrades
  gracefully — `get_all_sensor_infos` returns `[]`, `LHMSensor` runs disabled, `FPSUtils`
  keeps `None` types — so the app still starts with LibreHM simply missing its sensors (F2 fix).
- **Windows Performance Counters** (Legacy GPU) — PDH via `ctypes`, per-LUID
  `\GPU Engine(...)\Utilization Percentage` (3D engine only). The "Detect Render GPU" button
  (`gpu_monitor.toggle_luid_selection`) selects the LUID with the **highest** `engtype_3D`
  usage **at click time** — a best-effort render-GPU heuristic, **not** a guaranteed
  attribution (a light game can dip below the display/DWM compositor's load; see
   `notes.md` N7/N8). Verified end-to-end (2026-09-09) by `tests/spike_fake_game.py` S4a/b/c
   under the 8K fake game (spike OVERALL PASS; `pytest -q` = 106 passed) plus a clean admin
   app launch (`plan.md` Phase 2.5 S4). LUID values are per-boot dynamic, so the test keys off
   the M1-attributed LUID, never a hardcoded value.
- **psutil** (Legacy CPU) — per-core `cpu_percent`, max core.
- **Win32** — `GetForegroundWindow`/`GetWindowThreadProcessId` (foreground process),
  `GetLastInputInfo` (idle), `Get/SetWindowLongW` (tray/taskbar), `shcore` DPI awareness.
- **schtasks** — autostart (logon task, `/RL HIGHEST`).

## 8. Packaging & build

- **Dev run**: `python -m venv .venv` → activate → `pip install -r src/requirements.txt`
  → `python src/__main__.py` (relaunches elevated if not admin).
- **Build**: `python src/__main__.py --build` → PyInstaller with entry `src/core/DFL_v5.py`,
  `--onedir --uac-admin --noconsole`, dynamic `--add-data` for every file under
  `src/core/assets`, `--version-file src/metadata/version.txt`, output to `output/dist/`.
- **Frozen layout**: `Base_dir = sys._MEIPASS` (`_internal`), so assets resolve under
  `_internal/assets/` and config/error-log resolve next to the exe.
- `DynamicFPSLimiter.spec` at the repo root is a **stale artifact** (hardcoded `E:\…` paths,
  gitignored, not used by the build).

## 9. Error handling

- `sys.excepthook` → `logger.error_log_exception` writes uncaught exceptions to
  `error_log.txt`.
- RTSS missing → dedicated popup + exit (by design).
- LHM load failure → **uncaught** at import (no fallback to Legacy) — see `flaws.md` #17.
- Most per-sensor / per-counter read failures are logged and skipped, but several daemon
  threads have **no** try/except around their main work, so a single exception kills the thread
  silently (see flaws #18, #21).
- INI writes are non-atomic; a crash mid-write can corrupt `settings.ini`/`profiles.ini`
  (flaw #14).

## 10. File inventory

See the module map (§4) for Python sources. Non-code:

| Path | Role |
|---|---|
| `src/config/settings.ini`, `profiles.ini` | Runtime config (gitignored, created on first run) |
| `src/metadata/version.txt` | PyInstaller `VSVersionInfo` (5.0.0.0) |
| `src/requirements.txt` | dearpygui, psutil, pyinstaller, pystray, pythonnet, numpy |
| `src/core/assets/*.ico`, `*.png` | App/tray icons + window-control icons |
| `src/core/assets/faqs.csv` | FAQ rows shown in the GUI |
| `src/core/assets/LHM_0.9.4_lib/` | LibreHardwareMonitorLib.dll (4 .NET variants) + license |
| `src/Public_SameSalamander5710.cer` | Code-signing public certificate |
| `README.md`, `CHANGELOG.md`, `docs/HOW_IT_WORKS.md`, `src/BUILD.md` | User/release docs |

## 11. Known issues & tech debt

Glaring, fix-first issues are in **`flaws.md`**. Lower-priority debt worth noting:

- **Single-file orchestrator** — `DFL_v5.py` is ~1,270 lines of module-level script with heavy
  global state and import-order-dependent startup; hard to test or reason about.
- **GUI coupling in core** — several non-GUI modules (`logger`, `cpu_monitor`, `autostart`,
  `tray_functions`) import DearPyGui at module top, preventing headless use.
- **Undeclared direct dependency** — `PIL`/Pillow is used by `tray_functions` but only present
  as a transitive dependency of pystray.
- **Two competing RTSS write paths** (API vs direct `.cfg` edits) and non-atomic INI writes.
- **Dead / stray code** — `idle_timer.monitor_idle` (debug loop), `video2gif.py` and
  `backup_snippets.py` (not part of the app; the latter is not even valid Python).
- **Outdated doc** — `docs/HOW_IT_WORKS.md` describes the v4 Legacy logic only.
- **Latent type hazards** — `Decimal` vs `float` in the plot math (currently consistent because
  the FPS reader returns `Decimal`), and `copy_from_plot` truncates fractional custom limits.

## 12. Flaws cross-reference

See **[`flaws.md`](./flaws.md)** for the prioritized list of glaring issues (crash / wrong-cap /
data-corruption / security / resource-leak) with `file:line` references and fix guidance.
