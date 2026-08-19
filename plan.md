# DynamicFPSLimiter — Fix & Refactor Plan

Status: **Phase 1 complete; Phase 2 in progress** (F1 ✅, F2 ✅, F5 ✅, F4 ✅, F7 ✅, F8 ✅, F9 ✅, F3 ✅, F6 pending)
Branch: `repo_audit` (clean tree)
Scope: all 4 phases — test harness → glaring flaws (F1–F9) → architecture → code quality
Test framework: **pytest** (+ `pytest-cov`)

## Principles

- **No functionality breakage**: every flaw fix ships with a regression test; the suite must stay green at the end of every phase.
- **Safe order**: thin test harness first (proves the flaw fixes), then F1–F9, then architecture, then code quality.
- **Extract pure, testable logic** rather than rewriting the GUI; keep DPG / .NET / RTSS side effects behind mockable seams.
- Windows-only behavior (PDH, RTSS DLL, .NET/LHM, registry) is tested with mocks/stubs and marked `@pytest.mark.win32` where a real environment is required.

---

## Phase 1 — Test scaffolding (prerequisite)

Goal: a minimal harness capable of unit-testing the pure logic and the flaw fixes without a GUI, .NET runtime, or RTSS install.

### Tasks

1. Add `pytest` and `pytest-cov` to `src/requirements.txt`.
2. Create `tests/` package with `tests/conftest.py` providing fixtures that stub, **before** the modules under test import them:
   - **Fake `dearpygui.dearpygui`** (`dpg`): `get_value`, `set_value`, `does_item_exist`, `configure_item`, `bind_item_theme`, `delete_item`, `draw_layer`, `draw_circle`, `draw_text`, `set_axis_limits`, `set_axis_limits_auto`, backed by a dict; records call history for assertions (which thread called what).
   - **`core.lhm_loader` / `core.librehardwaremonitor` stubs**: fake `Computer`, `SensorType`, `HardwareType` (enum-like) so `ConfigManager`/`FPSUtils`/`LHMSensor` import and construct on any OS/CI.
   - **Injected `RTSSController`**: no DLL load; file-writing methods operate on a temp `Profiles/` dir; `UpdateProfiles` is a no-op counter.
3. `pytest.ini` (or `pyproject.toml` section): test paths, markers (`win32`), coverage config over `src/core`.
4. Ensure `src` is importable in tests (path setup in `conftest.py`).

### Tests

- **Smoke import test**: import every `core` module under the stubs; assert no import-time side effects (no DPI calls, no threads started, no DLL loads) beyond documented ones.

### Exit criteria

`pytest -q` runs (one smoke test green) on a clean machine with only the stubs — no GUI/.NET/RTSS required.

---

## Phase 2 — Glaring flaws (F1–F9)

Each item: fix + regression test. Order within phase: F1, F2, F5 (pure logic, highest value), then F4, F7, F8, F9 (lifecycle), then F3, F6 (cross-cutting, larger).

### F1 (High) — Cap step-down silently skipped — ✅ DONE

- **Done**: extracted pure policy `next_cap_on_decrease(fps_limit_list, current_cap, fps_mean)` into new `src/core/cap_policy.py` (no GUI/RTSS/.NET deps); rewired `DFL_v5.py` decrease branch to a 4-line call (replaces the 27-line try/except with the dead `current_index < 0` check). Policy: in-ladder at floor → `None`; in-ladder & `cap <= fps_mean` → one rung down; in-ladder & `cap > fps_mean` → highest rung below `fps_mean`; not in ladder → highest rung below `cap`; empty ladder → `None`. Regression tests in `tests/test_cap_policy.py` (15 parametrized cases + a source-level guard asserting DFL_v5 calls the policy and the dead check is gone). Suite green (45 passed).
- **Where**: `src/core/DFL_v5.py:364-390` (decrease branch of `monitoring_loop`).
- **Mechanism**: `list.index()` raises `ValueError` when the value is absent — it never returns a negative number — so `if current_index < 0:` (line 375) is dead code. When the current cap is in the list and `current_fps_cap <= fps_mean`, the branch that should step down one rung (`fps_limit_list[current_index - 1]`) never executes; the cap stalls.
- **Fix**:
  1. Extract a pure policy function, e.g. `next_cap_on_decrease(fps_limit_list, current_cap, fps_mean)` in `fps_utils.py` (or a new `src/core/cap_policy.py`):
     - `idx = fps_limit_list.index(current_cap)` inside `try`; on `ValueError` fall back to `max(x for x in fps_limit_list if x < current_cap)` (or `None` if none).
     - If found and `idx > 0`: return `fps_limit_list[idx - 1]`.
     - If found and `idx == 0`: return `None` (already at minimum).
     - If `current_cap > fps_mean`: return `max(x for x in fps_limit_list if x < fps_mean)` (or `None`).
  2. Rewire `DFL_v5.py` decrease branch to call it; only apply `CurrentFPSOffset` + `rtss.set_fractional_framerate` when the result is not `None`.
- **Tests** (pure, no DPG): parametrize — cap in list at minimum (→ `None`), cap in list mid-range with `cap <= fps_mean` (→ one rung lower), cap not in list (→ highest value below cap), `cap > fps_mean` (→ highest value below `fps_mean`), empty list (→ `None`).

### F2 (High) — LHM load failure crashes startup — ✅ DONE

- **Done**: added `LHMLoadError` (carries `dll_path`) to `lhm_loader.py`; `ensure_loaded` now raises it on `clr.AddReference` failure **and** on the `LibreHardwareMonitor.Hardware` import failure (previously `pass` + bare `ImportError`), without caching `_LOADED` so retries work. `get_all_sensor_infos(base_dir, logger=None)` catches `LHMLoadError` → logs "LibreHardwareMonitor unavailable…" → returns `[]`; `ConfigManager.__init__` passes its logger. `LHMSensor.__init__` catches `LHMLoadError` → `disabled = True`, types/computer `None`, `start()` no-ops, `stop()` guards `computer is not None` (needed because `DFL_v5.py:107` constructs it at import time). `FPSUtils.__init__` catches `LHMLoadError` → logs, `SensorType`/`HardwareType = None`, continues. Regression tests in `tests/test_lhm_failure.py` (6 tests). Suite green (51 passed).
- **Where**: `src/core/lhm_loader.py:162-171` (swallows `clr.AddReference` failure with `pass`, then line 168 `from LibreHardwareMonitor.Hardware import …` raises); `src/core/config_manager.py:52` (`get_all_sensor_infos` unguarded in `__init__`); `src/core/fps_utils.py:21-25` (the "fallback" call re-raises the same error outside the `try`).
- **Fix**:
  1. `lhm_loader.ensure_loaded`: on `AddReference` failure, raise a new `LHMLoadError` (defined in `lhm_loader.py`) carrying the attempted DLL path; do not silently `pass`.
  2. `librehardwaremonitor.get_all_sensor_infos` / `ConfigManager.__init__`: catch `LHMLoadError`, log it via the logger, and set `sensor_infos = []` so the app still starts (LibreHM monitoring method simply has no sensors).
  3. `FPSUtils.__init__`: same graceful handling — on `LHMLoadError`, set `SensorType`/`HardwareType` to `None` and continue (LibreHM path in `evaluate_cap_change` already no-ops when `sensor_infos` is empty).
- **Tests**: monkeypatch the .NET reference step to raise → `ensure_loaded` raises `LHMLoadError`; `ConfigManager` constructs with `sensor_infos == []` and no crash; `FPSUtils` constructs and `evaluate_cap_change` returns `(False, False)` for LibreHM with no sensors.

### F5 (High) — `current_stepped_limits()` can return `None` — ✅ DONE

- **Done**: made `current_stepped_limits()` total in `src/core/fps_utils.py`. The `custom` branch now returns the parsed list only when it is non-empty; a parse exception, an empty parse result, or an empty input string all log and fall back to `make_stepped_values(maxcap, mincap, capstep)`. An unknown `capmethod` (including the unselected `""`) logs and falls back to the same stepped ladder instead of falling off the end and returning `None`. The `step`/`ratio` paths are unchanged. Regression tests in `tests/test_fps_utils_limits.py` (7 tests). Suite green (58 passed).
- **Where**: `src/core/fps_utils.py:30-49` — returns `None` when `capmethod == "custom"` and parsing fails, or when the method is neither `custom`/`step`/`ratio`.
- **Consumers that crash on `None`**: `DFL_v5.py:177-180` (`max(...)` in start/stop callback), `DFL_v5.py:224-227` and `283-286` (`min`/`max` in `update_plot_FPS` / monitoring loop), `DFL_v5.py:518-519` (`min(...)` in warning check), `tray_functions.py:280` (`max(...)` in `update_hover_text`), `fps_utils.py:125` (`set(None)` in `copy_from_plot`).
- **Fix**: make the function **total** — on parse failure or unknown method, log the error and fall back to `make_stepped_values(maxcap, mincap, capstep)` (guaranteed non-empty given sane inputs); never return `None`. Keep existing logging.
- **Tests** (dpg stubbed): custom method + unparseable string → non-empty list, error logged; unknown method string → non-empty fallback; `step` and `ratio` paths return the same values as before (snapshot the current behavior first).

### F4 (High) — Uninitialized `found_limit` / `found_denominator` — ✅ DONE

- **Done**: in `src/core/rtss_functions.py` (`set_fractional_fps_direct`), `found_limit` and `found_denominator` are now initialized to `False` before the line-parsing loop, and the dead `found` flag (set but never used) was removed. A profile file missing one or both keys now gets the missing line(s) appended instead of raising `NameError`. Regression tests in `tests/test_rtss_fractional_direct.py` (5 tests, real temp `Profiles/` dir via `rtss_stub`). Suite green (63 passed).
- **Where**: `src/core/rtss_functions.py:221-235` (`set_fractional_fps_direct`). `found` (line 221) is set but never used (dead); `found_limit`/`found_denominator` are assigned only inside the loop, so a profile file lacking `Limit=` or `LimitDenominator=` hits `NameError` at lines 232/234.
- **Fix**: initialize `found_limit = found_denominator = False` before the loop; delete the unused `found`.
- **Tests** (temp `Profiles/` dir + stubbed controller): file missing both keys → both appended, no `NameError`; missing one → only that one appended; both present → values updated in place; `UpdateProfiles` called when `update=True`.

### F7 (High) — LHM lifecycle mismatch — ✅ DONE

- **Done**: `LHMSensor` now tracks an explicit `_computer_open` flag. Computer creation/open was extracted into `_create_and_open_computer()` (fresh instance, enables CPU/GPU, `Open()`, sets flag). `start()` re-creates/re-opens when `self.computer` is `None` or not open (and refreshes `cpu_name`), so Stop→Start polls live hardware; double `start()` still no-ops via the thread-alive guard without double-opening. `stop()` only `Close()`s when open and clears the flag. `get_all_sensor_infos()` wraps its one-shot enumeration in `try/finally` so its `Computer` is always `Close()`d (even on enumeration error). Regression tests in `tests/test_lhm_lifecycle.py` (4 tests, fake `Computer`/`Hardware`/type triple). Suite green (67 passed).
- **Where**: `src/core/librehardwaremonitor.py` — `stop()` calls `self.computer.Close()` but `start()` never re-opens, so Stop→Start leaves `_poll_loop` iterating a closed `Computer`. Additionally `get_all_sensor_infos` creates a `Computer()`, opens it, and never closes it (one-shot leak at startup).
- **Fix**:
  1. `start()`: idempotent — if `self.computer` is `None` or closed, create a new `Computer`, select hardware, `Open()`.
  2. `get_all_sensor_infos`: close its `Computer` when enumeration is done (try/finally).
- **Tests** (mocked `Computer`): `start()` after `stop()` re-opens (assert `Open()` called twice total); double `start()` does not double-open; `get_all_sensor_infos` closes its computer even when enumeration raises.

### F8 (Medium) — GPU monitor `reinitialize()` leaks PDH queries — ✅ DONE

- **Done**: added a `_close_query()` helper in `src/core/gpu_monitor.py` that `PdhCloseQuery`s the current `self.query_handle` (when set) and resets `self.query_handle = None` / `self.counter_handles = {}`. `initialize()` calls `_close_query()` first, so every re-init closes the previous HQUERY before opening a new one (no more per-retry handle leak). `reinitialize()` now assigns the re-setup result to `self.counter_handles` instead of a discarded local, so the poll loop reads counters on the live query. Regression tests in `tests/test_gpu_monitor_handles.py` (3 tests, monitor built via `__new__`, method-level mocks + fake no-byref `pdh`). Suite green (70 passed).
- **Where**: `src/core/gpu_monitor.py:267-279` — `reinitialize()` calls `initialize()`, which opens a **new** PDH query (`_init_gpu_state`) without closing the previous `self.query_handle` → handle leak on every read failure; the temp counter handles it builds are discarded, leaving `self.counter_handles` pointing at the orphaned query.
- **Fix**:
  1. In `initialize()` (or a `_close_query()` helper), close the existing `self.query_handle` (`pdh.PdhCloseQuery`) before opening a new one.
  2. In `reinitialize()`, assign `self.counter_handles` from the re-setup instead of discarding it.
- **Tests** (mocked `pdh`): after a failed read → `reinitialize`, assert `PdhCloseQuery` was called for the old handle before the second `PdhOpenQueryW`; assert `self.counter_handles` is the fresh dict.

### F9 (Medium) — GPU monitor cross-thread state + `get_gpu_usage()` reinitializes — ✅ DONE

- **Where**: `src/core/gpu_monitor.py:127-129` — `get_gpu_usage()` calls `self.initialize()` on every invocation (query leak + clobbers `query_handle`/`counter_handles` mid-run); `toggle_luid_selection()` (line 239, DPG thread) mutates `self.luid`, which `gpu_run` (line 201) reads without synchronization; it also calls `dpg.*` directly from the DPG thread.
- **Fix**:
  1. Remove the `initialize()` call from `get_gpu_usage()` — reuse the existing query/counters.
  2. Guard `self.luid` reads/writes with `self._lock` (or a dedicated lock).
  3. Route its `dpg.*` calls through the `GuiQueue` from F3.
- **Tests**: `get_gpu_usage` does not call `initialize` (mock spy); concurrent `toggle_luid_selection` + `gpu_run` iterations don't interleave on `luid` (deterministic lock-order test); DPG calls recorded via `GuiQueue`, not direct.
- **Done** (2026-08-18): `get_gpu_usage()` reuses `self.query_handle`/`self.counter_handles` (no re-init, no leak); `self.luid` reads in `gpu_run()` and writes in `toggle_luid_selection()` are guarded by `self._lock`; all `dpg.*` calls in `toggle_luid_selection()` route through a new `_submit_dpg` helper that defers to the `GuiQueue` (falls back to a direct call when no queue is set). **F3's `GuiQueue` was pulled forward** to unblock this fix: `src/core/gui_queue.py` (thread-safe `submit`/`drain`) is implemented and wired into `DFL_v5.py` via a single self-rescheduling per-frame `_frame_hook` (DearPyGui has no `update_callback`). **Important DPG detail (verified against source + empirically):** `dpg.set_frame_callback(N, cb)` uses **absolute** frame numbers and is one-shot — a later registration for the same frame overwrites the earlier one, so the naive `set_frame_callback(1, hook)` self-reschedule fires only once. The hook therefore re-registers for the **next** frame via `dpg.set_frame_callback(dpg.get_frame_count() + 1, _frame_hook)`; it also performs the one-shot first-frame startup work exactly once. The queue is passed to `GPUUsageMonitor(..., gui_queue=gui_queue)`. `tests/test_gui_queue.py` (5) + `tests/test_gpu_monitor_luid.py` (4) green; suite 79 passed.

### F3 (High) — Cross-thread DPG calls

- **Where**: `src/core/logger.py` (module-level `dpg` import; `add_log()` calls `dpg.set_value` from **any** thread — monitoring, plotting, tray, .NET callbacks); `src/core/tray_functions.py` — `_profile_menu_items` / `_method_menu_items` call `dpg.set_value` from the pystray thread; `update_hover_text` calls `dpg.get_value` + `max(self.fps_utils.current_stepped_limits())` (also an F5 consumer). DearPyGui is **not** thread-safe.
- **Fix**:
  1. Add `src/core/gui_queue.py`: a thread-safe `GuiQueue` — `submit(fn, *args)` buffers; a `dpg.update_callback`/render hook on the main thread drains and executes the queue each frame.
  2. `logger.add_log`: append to the log list immediately (thread-safe list + lock), submit the DPG text update via `GuiQueue`.
  3. Tray callbacks: submit DPG updates via `GuiQueue`; `update_hover_text` reads values via the queue on the main thread (or reads from a thread-safe snapshot).
  4. Wire the drain hook into `DFL_v5.py` render loop startup.
- **Tests**: queue buffers out-of-order submissions and flushes them in order on the main thread; `add_log` from a worker thread never invokes the dpg stub directly (assert via the stub's thread-recording); tray callback path only enqueues.
- **Progress**: **DONE (2026-08-18)**.
  - **Part 1 (GuiQueue, pulled forward for F9)**: `src/core/gui_queue.py` implemented (thread-safe `submit`/`drain`, per-callback error isolation, `on_error` hook) and the drain hook is wired into `DFL_v5.py` as a single self-rescheduling per-frame `_frame_hook` that re-registers for the next frame via `dpg.set_frame_callback(dpg.get_frame_count() + 1, _frame_hook)` (DearPyGui frame callbacks use **absolute** frame numbers and are one-shot — same-frame registration overwrites — and there is no `update_callback`). `tests/test_gui_queue.py` (5).
  - **Part 2 (logger)**: `logger.py` keeps a `_log_lock`-guarded `log_messages` buffer (thread-safe insert+trim); `_apply_log_text_to_widget()` reads a snapshot under the lock and is the only place `dpg.*` is touched. `add_log`/`refresh_log_display` submit that update to the `GuiQueue` (injected via `set_gui_queue`), falling back to an inline call when no queue is set.
  - **Part 3 (tray)**: `TrayManager` takes an optional `gui_queue` (injected via `set_gui_queue`); a `_run_on_main(fn)` helper submits `fn` to the queue (or runs inline when absent). Every pystray-thread action is routed through it: `_toggle_start_stop`, the `_profile_menu_items` / `_method_menu_items` lambdas, and the `on_restore` / `on_exit` paths in `_restore_window` / `_exit_app` (replacing the old raw `threading.Thread` calls, guarded for `None` callbacks). `update_hover_text` is split into a thread-checking wrapper + `_update_hover_text_impl`; it reads profile/method from the ConfigManager snapshot (`cm.current_profile` / `cm.current_method`, the latter newly maintained by `current_method_callback`) instead of `dpg.get_value`, and defers to the queue when called off the main thread so the DPG reads inside `fps_utils.current_stepped_limits` stay on the render thread.
  - **Part 4 (wiring)**: `DFL_v5.py` injects the queue into `logger` and `tray` right after `gui_queue = GuiQueue()`; the `_frame_hook` re-registration is wrapped in `try/except` so a queued `exit_gui` (which destroys the DPG context) can't raise during shutdown. `ConfigManager` gained a `current_method` snapshot (init + `current_method_callback`).
  - **Tests**: `tests/test_logger.py` (5) — `set_gui_queue`, `add_log` defers DPG to the queue (no `set_value` on the worker thread, runs on the draining main thread), inline fallback without a queue, 50-message trim, and an 8-thread buffer-consistency check; `tests/test_tray.py` (8) — `_run_on_main` defer/inline, `update_hover_text` defer-off-main-thread + inline-on-main (built from the cm snapshot), profile/method menu lambdas defer, and `_exit_app` / `_restore_window` defer. Suite **92 passed**.

### F6 (Medium) — Non-atomic / interleaved RTSS profile writes

- **Where**: `src/core/rtss_functions.py` — `set_fractional_framerate` (DLL API path + `set_limit_denominator` file edit), `set_limit_denominator` (direct `open(..., "w")`), and `set_fractional_fps_direct` (direct `open(..., "w")`) all mutate the **same** `.cfg` file non-atomically; `DFL_v5.py:179-180` calls two of them back-to-back in the start/stop callback. A crash or RTSS read mid-write corrupts the profile.
- **Fix**:
  1. Atomic file writes: write to `<file>.tmp`, flush + `os.replace(tmp, file)` (all three writers).
  2. Add a `threading.Lock` in `RTSSController` serializing profile file + API mutations.
  3. Consolidate the denominator write: `set_fractional_framerate` already writes `LimitDenominator` via file — avoid double-writing the same keys in one callback (single shared writer for `Limit`/`LimitDenominator`/`FramerateLimit`).
- **Tests**: temp `.cfg` — writer produces correct content and leaves no `.tmp` behind; two threads writing concurrently always leave a valid file (no truncation/partial lines); `UpdateProfiles` invoked per `update` flag.

### Phase 2 exit criteria

- All F1–F9 regression tests green; Phase 1 smoke test still green.
- Manual smoke (Windows, admin): start/stop monitoring, cap actually steps down under sustained load (F1), LUID toggle (F8/F9), Stop→Start (F7), custom/step/ratio caps incl. a deliberately broken custom string (F5), profile file intact after stop (F6).

---

## Phase 3 — Architecture & test infrastructure

No behavior changes; the full suite must stay green after each step.

- **A1 — Split the god module `DFL_v5.py` (1266 lines)** into:
  - `src/core/state.py`: `AppState` dataclass/object owning the shared mutable globals (`time_series`, `fps_time_series`, `gpu_usage_series`, `cpu_usage_series`, `fps_series`, `cap_series`, `fps_values`, `gpu_values`, `cpu_values`, `CurrentFPSOffset`, `fps_mean`, `idle_state`, `elapsed_time`, `running`) with a lock.
  - `src/core/loops.py`: `monitoring_loop`, `plotting_loop`, `gui_update_loop`, `update_plot_FPS`, `update_plot_usage` (rewired to take `AppState`).
  - `src/core/view.py`: GUI construction (the ~450-line `dpg` builder section).
  - `src/core/app.py`: orchestration — instance wiring, start/stop callback, render loop, exit handling.
- **A2 — Inject `dpg` instead of module-level imports**: `config_manager.py:3`, `fps_utils.py:4`, `logger.py`, `DFL_v5.py` — pass the dpg module (or a facade) via constructor/parameters so modules import cleanly under test.
- **A3 — Remove import-time coupling in `rtss_functions.py:5`** (`from core.launch_popup import show_rtss_error_and_exit`): inject an error handler into `RTSSController.__init__`; default behavior unchanged.
- **A4 — (Optional, do last) Rename `DFL_v5.py` → stable name** (e.g. `app.py`, per A1 the file is already split, so this becomes "the entry module keeps a stable name"): update `src/__main__.py` import; remove the stale `DFL_v4` reference and `__pycache__/DFL_v4.*.pyc`. *Flagged higher-risk — only after A1 lands and the suite is green.*
- **A5 — Split `ConfigManager` (765 lines)**: config I/O (`load_or_init_configs`, saving, key maps) vs GUI population (input field wiring, tooltips).
- **A6 — `idle_timer.py`**: wire `monitor_idle` into the monitoring loop (it currently only prints debug output and is never called from the app) or delete the module. Decision: wire it, since `get_idle_duration` is already used in `DFL_v5.py:350` — move that logic here.
- **Tests**: after each split, Phase 1–2 suite stays green; add import-side-effect tests (A2/A3); add `AppState` mutation tests (lock correctness).

---

## Phase 4 — Code quality / latent issues

- **L10** — `@staticmethod` on `calculate_percentile` in `cpu_monitor.py` and `gpu_monitor.py` (currently called on the class; works by accident). *Test:* call via instance and class.
- **L11** — Fix no-op `self.dpg = dpg or dpg` at `fps_utils.py:13` → `self.dpg = dpg` (or resolve the global fallback intentionally).
- **L13** — Typo `warning.py:17`: "This setting can be changes" → "can be changed".
- **L14** — `autostart.py`: drop `shell=True`; pass the `schtasks` argument list to `subprocess.run`. *Test:* assert the constructed argv for create/delete.
- **L15** — Set DPI awareness once in `src/__main__.py` (before `run_app`), remove the import-time `ctypes.windll.shcore.SetProcessDpiAwareness(2)` from `DFL_v5.py` and `launch_popup.py`.
- **L16** — `launch_popup.py`: stop constructing a full `TrayManager` just to reuse drag handling; extract the drag handler into a small reusable helper.
- **L18** — `DFL_v5.py:483`: plotting-loop sleep `time.sleep(math.lcm(gpu, cpu interval)/1000.0)` → fixed interval (e.g. 100 ms) or `min(...)`; the LCM is a meaningless coupling.
- **L20** — `DFL_v5.py:354`: `if gpuUsage and ...` → `if gpuUsage is not None and ...` for clarity (0 is a valid reading today and silently disables limiting).
- **Tests**: `calculate_percentile` (L10), autostart argv (L14), DPI call count (L15).

---

## Verification (per phase and at the end)

1. `pytest -q` green at the end of every phase (with `--cov src/core` at the end).
2. Manual smoke, Windows + admin:
   - Start/stop monitoring; cap **steps down** under sustained load (F1) and steps back up after cooldown.
   - LUID detect/revert (F8/F9); GPU read failure triggers reinit without leaking (watch PDH handle count or just stability over time).
   - Stop→Start monitoring (F7); LibreHM sensors still populate.
   - Custom/step/ratio cap methods, including a deliberately invalid custom string (F5).
   - Kill RTSS mid-run / corrupt-DLL scenario → graceful `LHMLoadError` log, app alive (F2).
   - Profile `.cfg` intact after start/stop cycles (F6).
   - Tray menu profile/method switching while monitoring (F3).
3. Packaging: `python src/__main__.py --build` produces a working exe in `output/dist` (run once at the end of Phase 3 and once after Phase 4).

## Sequencing note

Phase 1 (thin harness) intentionally precedes the flaw fixes even though the flaws are the priority — the harness is what proves each fix breaks nothing. Within Phase 2 the order is F1 → F2 → F5 → F4 → F7 → F8 → F9 → F3 → F6 (pure-logic first, cross-cutting last). A4 (rename) is optional and lands last in Phase 3.
