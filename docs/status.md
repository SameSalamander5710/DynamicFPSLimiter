# DynamicFPSLimiter — Status & Issue Tracker

> **Single source of truth** for everything that is done, pending, or deferred.
> Every fix / change adds/updates one row here — see [Borrowing the rule](#how-to-record-a-fix).
> Companion docs: [`README.md`](./README.md) (nav), [`architecture.md`](./architecture.md)
> (design), [`lessons.md`](./lessons.md) (engineering lessons).

Status legend: ✅ Done · 🟨 Pending · ⏸️ Deferred · ❌ Not started

---

## 1. Done

### 1.1 Test harness (previously "Phase 1")

| Item | Fix | Tests |
|---|---|---|
| pytest scaffolding | `pytest` + `pytest-cov` in `src/requirements.txt`; stub fixtures (`dpg`, LHM, RTSS controller) in `tests/conftest.py`; `pytest.ini`; import-safe `src` | `tests/test_harness.py`, `tests/test_smoke_import.py` |

### 1.2 Glaring flaws (previously F1–F9)

| ID | Severity | What was fixed | Tests |
|---|---|---|---|
| F1 | High | Cap step-down silently skipped — dead `current_index < 0` check meant the cap stalled under load. Extracted pure `next_cap_on_decrease()` into `src/core/cap_policy.py`; `DFL_v5.monitoring_loop` decrease branch calls it. | `tests/test_cap_policy.py` |
| F2 | High | LHM load failure crashed startup. `lhm_loader.ensure_loaded` now raises `LHMLoadError` (carries DLL path); all bootstrap sites degrade gracefully: `get_all_sensor_infos` → `[]`, `LHMSensor` disabled, `FPSUtils` keeps `None` types. | `tests/test_lhm_failure.py` |
| F3 | Med | Cross-thread `dpg.*` calls (logger, tray, monitoring, autopilot, LHM poll). New `src/core/gui_queue.py` (`GuiQueue`: thread-safe `submit`/`drain`, per-callback error isolation); logger + `TrayManager` route through it via `set_gui_queue`; `update_hover_text` reads the ConfigManager snapshot. | `tests/test_logger.py`, `tests/test_tray.py`, `tests/test_gui_queue.py` |
| F4 | Med | `set_fractional_fps_direct` `NameError` on profile files missing `Limit=`/`LimitDenominator=`. Flags initialized to `False`; missing lines appended; dead `found` flag removed. | `tests/test_rtss_fractional_direct.py` |
| F5 | Med | `current_stepped_limits()` returned `None` → `max(None)` crash. Now total: bad/empty custom list or unknown `capmethod` logs + falls back to the stepped ladder. | `tests/test_fps_utils_limits.py` |
| F6 | Med | Two competing non-atomic RTSS profile write paths could corrupt `.cfg`. All mutations serialized on `RTSSController._profile_lock` (`RLock`); file writes go through `_atomic_write_lines` (tmp + fsync + `os.replace`). Writers kept separate (file-edit vs DLL API) by design. | `tests/test_rtss_atomic.py` |
| F7 | Med | Stop→Start polled a closed LHM `Computer`. `LHMSensor` tracks `_computer_open`; `start()` re-creates/re-opens; `get_all_sensor_infos` closes its one-shot `Computer` in `try/finally`. | `tests/test_lhm_lifecycle.py` |
| F8 | Med | PDH query-handle leak + orphaned counters on `reinitialize()`. New `_close_query()`; `initialize()` closes the old HQUERY first; `reinitialize()` assigns fresh `counter_handles`. | `tests/test_gpu_monitor_handles.py` |
| F9 | Med | Race on LUID selection + `get_gpu_usage()` re-initializing each call. `get_gpu_usage()` reuses the live query; `self.luid` reads/writes lock-guarded; `dpg.*` calls route through the `GuiQueue` via `_submit_dpg`. | `tests/test_gpu_monitor_luid.py`, `tests/test_gui_queue.py` |

### 1.3 GUI-threading hardening (previously "Phase 2.5" S1–S4)

| ID | What was fixed | Tests |
|---|---|---|
| Main-loop fix | The self-rescheduling `_frame_hook` drain could be orphaned by a long callback (froze every queued GUI update). Replaced with an **explicit main render loop** at the end of `DFL_v5.py` that drains `GuiQueue` every frame; one-shot startup work runs synchronously pre-loop. | `tests/test_dfl_main_loop.py` (+ source guard: no `set_frame_callback`/`_frame_hook`) |
| S1 | Moved LUID detection off the DPG callback thread → short-lived daemon worker + queued `_apply` closure; `_detecting` flag ignores double-clicks. | `tests/test_gpu_monitor_luid.py` |
| S2 | Locked the shared PDH query (`self._pdh_lock`, RLock) around every `Pdh*` call in `gpu_run`/`get_gpu_usage`/`initialize`/`reinitialize`/`cleanup`. | `tests/test_gpu_monitor_luid.py` (concurrency cases) |
| S3 | `GuiQueue` drain failures visible — `DFL_v5.py` constructs `GuiQueue(on_error=...)` → `logging.error`. | `tests/test_gui_queue.py` (+ source guard) |
| S4 | End-to-end "Detect Render GPU" verification (S4a detect / S4b revert / S4c no-handle-growth). Spike OVERALL PASS; app launches clean as admin. | `tests/spike_fake_game.py` (S4a/b/c), `tests/fake_game.py` |

### 1.4 Idle-FPS persistence fix (merged from `origin/main`, `0a857c1`/`f3dbeab`)

| What was fixed | Where |
|---|---|
| Idle FPS settings reverted after profile changes. `ConfigManager` now persists/stores idle settings across profile switches; merged into `repo_audit` (2026-09-18) as `e1ab654`. | `src/core/config_manager.py` (+1 line net) |

### 1.5 Code-quality / latent issues (previously "Phase 4", L-items)

| ID | What was fixed | Tests |
|---|---|---|
| L10 | `calculate_percentile` is now a real `@staticmethod` in both monitors (was silently working by accident as a plain class function). | `tests/test_percentile_staticmethod.py` |
| L11 | Removed the no-op `self.dpg = dpg or dpg` fallback in `FPSUtils`; plain `self.dpg = dpg` with `dpg=None` default retained. | `tests/test_fps_utils_dpg_assignment.py` |
| L13 | Typo fixed: "This setting can be changes" → "can be changed" in the min-valid-FPS warning. | `tests/test_warning_typo.py` |
| L14 | Dropped `shell=True` from all four `schtasks` `subprocess.run` calls in `autostart.py`; argument lists passed instead. | `tests/test_autostart.py` |
| L15 | DPI awareness set **once** in `src/__main__.py` (`run_app`, failure-tolerant); removed import-time `SetProcessDpiAwareness(2)` from `DFL_v5.py` and `launch_popup.py`. | `tests/test_dpi_awareness.py` |
| L16 | Extracted a reusable `ViewportDragHandler` into `src/core/drag_helper.py`; popups no longer construct a full `TrayManager` just for drag handling. | `tests/test_drag_helper.py` |
| L18 | Plotting-loop sleep now `min(gpupollinginterval, cpupollinginterval)` instead of meaningless `math.lcm`; removed unused `import math`. | `tests/test_dfl_main_loop.py` |
| L20 | Limiting gate now uses `gpuUsage is not None` so a valid 0% GPU reading doesn't silently disable limiting. | `tests/test_dfl_main_loop.py` |

### 1.6 Architecture refactor steps (previously "Phase 3", A-items)

| ID | What was fixed | Tests |
|---|---|---|
| A2 | Inject `dpg` instead of module-level imports (`config_manager.py:3`, `fps_utils.py:4`, `logger.py:1`, `DFL_v5.py:9`, plus `cpu_monitor.py`, `launch_popup.py`, `themes.py`, `rtss_interface.py`, `tray_functions.py`, `autostart.py`, and `drag_helper.py`). `DFL_v5.py` is now the single module that imports dpg and injects it downstream (`logger.set_dpg`, ctor/function params on themes/tray/drag/launch-popup; `self.dpg` everywhere else). | `tests/test_dpg_injection.py`, source guards |
| A3 | Remove `rtss_functions.py:6` import-time coupling (`from core.launch_popup import show_rtss_error_and_exit`) → inject an error handler into `RTSSController.__init__` as `error_handler=None` (called with the DLL path on `OSError`, or re-raise). `DFL_v5.py` passes `show_rtss_error_and_exit`. | `tests/test_rtss_error_handler.py` |
| A6 | `idle_timer.monitor_idle` rewritten from a blocking debug print-loop into a stateless, error-tolerant check (`True` when idle ≥ threshold) and wired into the `DFL_v5.py` monitoring loop (`not monitor_idle(cm.idle_fps_delay) or not cm.idle_mode`); raw `get_idle_duration()` call dropped. Module kept, not deleted. | `tests/test_idle_timer.py` |

---

## 2. Pending

### 2.1 Architecture / scalability refactor (previously "Phase 3", A1–A6)

> Deliberately deferred — "future scalability". Not a bug-fix pass. No behavior changes; the
> suite must stay green after each step.

| ID | Item | Current state / why |
|---|---|---|
| A1 | Split the god module `DFL_v5.py` (**1,102 lines**) into `src/core/state.py`, `loops.py`, `view.py`, `app.py`. The explicit main render loop (`gui_queue.drain()`) must live in the new orchestration module; `tests/test_dfl_main_loop.py` re-pointed to guard it there. | Not started |
| A4 | (Optional, last) Rename `DFL_v5.py` to a stable name; update `src/__main__.py`; remove stale `DFL_v4` references. | Not started |
| A5 | Split `ConfigManager` (**690 lines**): config I/O (`load_or_init_configs`, saving, key maps) vs GUI population (input field wiring, tooltips). | Not started |

---

## 3. Known issues & tech debt (carried forward from `architecture.md` §11)

Lower-priority debt; glaring issues are all resolved (see §1.2).

- **Single-file orchestrator** — `DFL_v5.py` is a ~1,100-line module-level script with heavy
  global state and import-order-dependent startup (tracked as **A1**; the dpg-coupling part was
  resolved by **A2**).
- **Undeclared direct dependency** — `PIL`/Pillow used by `tray_functions` but only present as a
  transitive dependency of pystray.
- **Non-atomic INI writes** — `settings.ini`/`profiles.ini` are rewritten immediately on every
  preference change with no tmp+rename; a crash mid-write can corrupt them (RTSS `.cfg` writes
  are already atomic — F6; INI is not).
- **Dead / stray code** — `video2gif.py` and `backup_snippets.py` (not part of the app; the latter is not even valid Python).
- **Latent type hazards** — `Decimal` vs `float` in plot math (consistent today only because the
  FPS reader returns `Decimal`); `copy_from_plot` truncates fractional custom limits.
- **`faqs.csv`** present in both dev and frozen builds — its import-time `open()` only crashes if
  the asset is genuinely missing ("latent, low").

---

## 4. How to record a fix

1. Fix the code, add a regression test, keep the suite green (`python -m pytest -q`).
2. Update this file:
   - new bug/change → add a row under the relevant Done table (or §2 if not yet fixed),
   - same-listing: if an item's ID goes away, drop the empty table, renumber nothing else.
3. Do **not** create new per-phase narrative docs. Durable design info goes in `architecture.md`;
   reusable "gotcha" lessons go in `lessons.md`. This file is only status.