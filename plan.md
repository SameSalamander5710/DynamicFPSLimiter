# DynamicFPSLimiter — Fix & Refactor Plan

Status: **Phase 1 complete; Phase 2 complete** (F1 ✅, F2 ✅, F5 ✅, F4 ✅, F7 ✅, F8 ✅, F9 ✅, F3 ✅, F6 ✅); **Phase 2.5 complete** (S1 ✅, S2 ✅, S3 ✅, S4 ✅)
Branch: `repo_audit` (clean tree)
Scope: all 4 phases — test harness → glaring flaws (F1–F9) → architecture → code quality
Test framework: **pytest** (+ `pytest-cov`)

> 2026-08-20: a post-Phase-2 regression (the self-rescheduling frame-hook drain orphaned by a
> long LUID-detection callback, freezing all queued GUI updates) was fixed by draining the
> `GuiQueue` from an explicit main render loop (commit `a8fac09`, manually verified). See
> **Phase 2.5** and `docs/notes.md`. Line references to `DFL_v5.py` below are as of the Phase 2
> commits; the 2026-08-20 fix added `import logging` at the top, shifting all later lines by +1.

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
- **Superseded (2026-08-20):** the self-rescheduling `_frame_hook` drain was removed after it orphaned in production — a long callback (LUID detection: `sleep(0.1)` + two PDH collects) ran on the same DPG callback thread that the hook's re-registration was queued on, so the registration for frame M+1 landed *after* the main thread had already checked frame M+1; frame-callback entries are keyed by exact absolute frame number and never re-checked, so the hook died forever and every queued GUI update silently froze. The `GuiQueue` is now drained by the explicit main render loop at the end of `DFL_v5.py` (`while dpg.is_dearpygui_running(): dpg.render_dearpygui_frame(); gui_queue.drain()`), and the one-shot first-frame startup work runs synchronously on the main thread before the loop. See **Phase 2.5** and `docs/notes.md` (N1/N2).

### F3 (High) — Cross-thread DPG calls

- **Where**: `src/core/logger.py` (module-level `dpg` import; `add_log()` calls `dpg.set_value` from **any** thread — monitoring, plotting, tray, .NET callbacks); `src/core/tray_functions.py` — `_profile_menu_items` / `_method_menu_items` call `dpg.set_value` from the pystray thread; `update_hover_text` calls `dpg.get_value` + `max(self.fps_utils.current_stepped_limits())` (also an F5 consumer). DearPyGui is **not** thread-safe.
- **Fix**:
  1. Add `src/core/gui_queue.py`: a thread-safe `GuiQueue` — `submit(fn, *args)` buffers; a `dpg.update_callback`/render hook on the main thread drains and executes the queue each frame.
  2. `logger.add_log`: append to the log list immediately (thread-safe list + lock), submit the DPG text update via `GuiQueue`.
  3. Tray callbacks: submit DPG updates via `GuiQueue`; `update_hover_text` reads values via the queue on the main thread (or reads from a thread-safe snapshot).
  4. Wire the drain hook into `DFL_v5.py` render loop startup.
- **Tests**: queue buffers out-of-order submissions and flushes them in order on the main thread; `add_log` from a worker thread never invokes the dpg stub directly (assert via the stub's thread-recording); tray callback path only enqueues.
- **Progress**: **DONE (2026-08-18)**.
  - **Part 1 (GuiQueue, pulled forward for F9)**: `src/core/gui_queue.py` implemented (thread-safe `submit`/`drain`, per-callback error isolation, `on_error` hook) and the drain hook was wired into `DFL_v5.py` as a single self-rescheduling per-frame `_frame_hook` that re-registered for the next frame via `dpg.set_frame_callback(dpg.get_frame_count() + 1, _frame_hook)` (DearPyGui frame callbacks use **absolute** frame numbers and are one-shot — same-frame registration overwrites — and there is no `update_callback`). `tests/test_gui_queue.py` (5). **Superseded (2026-08-20):** the `_frame_hook` drain was replaced by the explicit main render loop — see the F9 addendum and Phase 2.5.
  - **Part 2 (logger)**: `logger.py` keeps a `_log_lock`-guarded `log_messages` buffer (thread-safe insert+trim); `_apply_log_text_to_widget()` reads a snapshot under the lock and is the only place `dpg.*` is touched. `add_log`/`refresh_log_display` submit that update to the `GuiQueue` (injected via `set_gui_queue`), falling back to an inline call when no queue is set.
  - **Part 3 (tray)**: `TrayManager` takes an optional `gui_queue` (injected via `set_gui_queue`); a `_run_on_main(fn)` helper submits `fn` to the queue (or runs inline when absent). Every pystray-thread action is routed through it: `_toggle_start_stop`, the `_profile_menu_items` / `_method_menu_items` lambdas, and the `on_restore` / `on_exit` paths in `_restore_window` / `_exit_app` (replacing the old raw `threading.Thread` calls, guarded for `None` callbacks). `update_hover_text` is split into a thread-checking wrapper + `_update_hover_text_impl`; it reads profile/method from the ConfigManager snapshot (`cm.current_profile` / `cm.current_method`, the latter newly maintained by `current_method_callback`) instead of `dpg.get_value`, and defers to the queue when called off the main thread so the DPG reads inside `fps_utils.current_stepped_limits` stay on the render thread.
  - **Part 4 (wiring)**: `DFL_v5.py` injects the queue into `logger` and `tray` right after `gui_queue = GuiQueue()`; the `_frame_hook` re-registration was wrapped in `try/except` so a queued `exit_gui` (which destroys the DPG context) can't raise during shutdown. `ConfigManager` gained a `current_method` snapshot (init + `current_method_callback`). **Superseded (2026-08-20):** the `_frame_hook` (and its try/except wrapper) is gone with the hook; the main render loop wraps `gui_queue.drain()` in its own `try/except` + `logging.error`.
  - **Tests**: `tests/test_logger.py` (5) — `set_gui_queue`, `add_log` defers DPG to the queue (no `set_value` on the worker thread, runs on the draining main thread), inline fallback without a queue, 50-message trim, and an 8-thread buffer-consistency check; `tests/test_tray.py` (8) — `_run_on_main` defer/inline, `update_hover_text` defer-off-main-thread + inline-on-main (built from the cm snapshot), profile/method menu lambdas defer, and `_exit_app` / `_restore_window` defer. Suite **92 passed**.

### F6 (Medium) — Non-atomic / interleaved RTSS profile writes

- **Where**: `src/core/rtss_functions.py` — `set_fractional_framerate` (DLL API path + `set_limit_denominator` file edit), `set_limit_denominator` (direct `open(..., "w")`), and `set_fractional_fps_direct` (direct `open(..., "w")`) all mutate the **same** `.cfg` file non-atomically; `DFL_v5.py:179-180` calls two of them back-to-back in the start/stop callback. A crash or RTSS read mid-write corrupts the profile.
- **Fix**:
  1. Atomic file writes: write to `<file>.tmp`, flush + `os.fsync` + `os.replace(tmp, file)` (all three file writers).
  2. Add a `threading.RLock` in `RTSSController` serializing profile file + API mutations.
  3. Consolidate the denominator write: `set_fractional_framerate` already writes `LimitDenominator` via file — avoid double-writing the same keys in one callback (single shared writer for `Limit`/`LimitDenominator`/`FramerateLimit`).
- **Progress**: **DONE (2026-08-19)**.
  - **Atomic writes**: new `RTSSController._atomic_write_lines(profile_file, lines)` writes to `<file>.tmp`, `f.flush()` + `os.fsync(f.fileno())`, then `os.replace(tmp, file)` (atomic on the same NTFS volume). `set_limit_denominator` and `set_fractional_fps_direct` now route their final file write through it instead of a bare `open(..., "w")`.
  - **Serialization**: `self._profile_lock = threading.RLock()` in `__init__`; `set_limit_denominator`, `set_fractional_fps_direct`, `set_fractional_framerate`, and `set_profile_property` (whose `SaveProfile` also writes the `.cfg`) each run their body under `with self._profile_lock:`. **`RLock` (not `Lock`)** because `set_fractional_framerate` calls `set_limit_denominator` + `set_profile_property` while holding it — re-entrancy is required. `DFL_v5.py:181-182` (start/stop, main thread) and the monitoring loop (`DFL_v5.py:359/371/395/407/414`, background thread) plus the exit path (`DFL_v5.py:550`) are the concurrent callers this protects.
  - **Method consolidation (deliberately NOT done)**: the two public writers were **kept separate** rather than merged into one shared writer. `set_fractional_fps_direct` is a pure file edit (`Limit=` + `LimitDenominator=`), while `set_fractional_framerate` pushes `FramerateLimit` through the **DLL API** (`SetProfileProperty` + `SaveProfile`) *and* writes the denominator to file. They have distinct file-vs-DLL semantics, so merging them would change behavior; the idempotent denominator double-write is harmless under the lock. (The `update`-flag refresh counts are left as-is — pre-existing, out of F6 scope.)
  - **Tests**: `tests/test_rtss_atomic.py` (5) — each writer leaves correct content and **no `.tmp`** behind, `set_fractional_framerate` returns the right `(limit, denominator)` and writes the denominator via its nested writer, two threads writing concurrently leave a **valid, consistent** `(limit, denominator)` pair (never a mixed/truncated file), and `UpdateProfiles` fires per the `update` flag. The `rtss_stub` fixture (which bypasses `__init__`) now sets `ctrl._profile_lock = threading.RLock()`. Suite **97 passed**.

### Phase 2 exit criteria

- All F1–F9 regression tests green; Phase 1 smoke test still green.
- Manual smoke (Windows, admin): start/stop monitoring, cap actually steps down under sustained load (F1), LUID toggle (F8/F9), Stop→Start (F7), custom/step/ratio caps incl. a deliberately broken custom string (F5), profile file intact after stop (F6).

---

## Phase 2.5 — GUI-threading hardening (post-Phase-2 regression follow-ups)

**Context (2026-08-20):** After Phase 2, "Detect Render GPU" appeared to do nothing and the in-app log froze. Root cause (verified against DPG v2.0.0 C++ source): all Python callbacks — button clicks *and* frame callbacks — run on one dedicated background thread, and `set_frame_callback(N, cb)` defers its registration to that same thread. The self-rescheduling `_frame_hook` re-registered for `get_frame_count() + 1` from inside the callback thread; `toggle_luid_selection` then blocked that thread ≥100 ms (`time.sleep(0.1)` + two `PdhCollectQueryData`), so the re-registration for frame M+1 landed *after* the main thread had already checked frame M+1. Frame-callback entries are keyed by exact absolute frame number and never re-checked → the hook was orphaned forever → `gui_queue.drain()` never ran again → log widget and all queued button feedback silently froze.

**Main fix (DONE, commit `a8fac09`, manually verified 2026-08-20):** deleted the frame hook; the one-shot startup work runs synchronously on the main thread pre-loop, and the app ends with an explicit main render loop that drains `gui_queue` every frame on the main thread (`DFL_v5.py` bottom). Regression guards: `tests/test_dfl_main_loop.py` (drain wiring present; `dpg.set_frame_callback(`/`_frame_hook` absent) + `tests/test_gui_queue.py::test_drain_survives_long_running_items_across_frames`.

Remaining hardening items, in order:

### S3 — Make `GuiQueue` drain failures visible — DONE

- **Where:** `DFL_v5.py` — `gui_queue = GuiQueue()` is constructed without `on_error`, so a failing queued callback is swallowed silently (this is how the regression above hid).
- **Fix:** pass an `on_error` that calls `logging.error` (root logging is configured by `logger.init_logging` at DFL_v5.py:67, so it reaches `error_log.txt`).
- **Tests:** unit — a failing callback invokes `on_error` with the exception; source guard — DFL_v5 constructs `GuiQueue` with an `on_error`.

### S1 — Move LUID detection off the DPG callback thread — DONE

- **Where:** `gpu_monitor.py` `toggle_luid_selection` — a button callback running on the DPG callback thread; `get_gpu_usage()` does `PdhCollectQueryData` + `time.sleep(0.1)` + `PdhCollectQueryData` + per-counter reads inline (≥100 ms block), delaying *every* other DPG callback.
- **Fix:** spawn a short-lived daemon worker that runs the PDH read; a single queued closure then applies the state (`self.luid`, `self.luid_selected`) and all `_submit_dpg` updates on the main thread. A `_detecting` flag under `self._lock` ignores double-clicks mid-detection.
- **Tests:** toggle performs no `pdh` calls on the calling thread (thread-recording mock); result applied on drain; double-click → one worker; failure path queues "Failed to detect".

### S2 — Lock the shared PDH query — DONE

- **Where:** `gpu_monitor.py` — `get_gpu_usage` (DPG/worker thread) and `gpu_run` (monitor thread) both call `PdhCollectQueryData`/`PdhGetFormattedCounterValue` on the same `query_handle`/`counter_handles` without synchronization; `reinitialize` can close/re-open the query mid-read.
- **Fix:** new `self._pdh_lock` (re-entrant — `reinitialize` is called from inside a locked read section on read failure) around every `Pdh*` call on the shared query in `gpu_run` (collect + reads), `get_gpu_usage` (both collects + reads), and `initialize`/`_close_query`/`reinitialize`/`cleanup` (open/close/add/collect). Known trade-off: `get_gpu_usage` holds the lock across its 0.1 s sleep, so with the default 100 ms poll interval the monitor tick slips ≤1 interval during a detection — acceptable, documented.
- **Tests:** concurrency test (mock `pdh` recording thread+event order, short sleep inside collect) — `get_gpu_usage` and a reinit/collect from another thread never interleave; reinit serializes against an in-flight collect.

### S4 — LUID detect/revert verification — **DONE**

> **Result (verified 2026-09-09):** S4a/S4b/S4c all PASS in `tests/spike_fake_game.py`
> (full spike OVERALL PASS, run without `--test-limit`); `pytest -q` = 106 passed; the app
> launches cleanly as admin (no startup errors in `src/error_log.txt`). The real button path
> (`DFL_v5.py:1154` → `gpu_monitor.py:266`) selects the highest-`engtype_3D` LUID under real
> PDH, flips the button label/theme and status text correctly, reverts to all-GPU tracking,
> and shows no PDH handle growth over 5 toggles. Note: LUID values are **per-boot dynamic** —
> on this run the workload LUID was `0x0000FE69` (not the `0x000100F7` seen on an earlier
> boot), so the test keys off the M1-attributed LUID rather than a hardcoded value.

> **Workflow state:** S1, S2, S3 and S4 are DONE. The fake game (`tests/fake_game.py`) and
> the PDH/RTSS spike (`tests/spike_fake_game.py`, now including S4a/b/c) are the verification
> harness. **Phase 3 is the next phase**, but per the user's directive it is **not** to be
> started automatically — keep scope to S4 and wait for the user to proceed.

**Goal.** Verify the legacy "Detect Render GPU" button end-to-end against a real workload
under real PDH: selecting picks the LUID with the highest 3D-engine usage, the status text
and button label/theme flip correctly, "Revert to all GPUs" restores all-GPU tracking, and
repeated toggles do not grow the PDH handle count.

> **Clarification (user, 2026-08-21):** we do **not** care whether the button truly
> identifies the *render* GPU. It only needs to select whichever LUID has the highest
> `engtype_3D` usage **at the moment of the click**. Under the fake 8K workload that LUID
> is unambiguous (see `docs/notes.md` N7) — on this machine it is `0x000100F7`. "Render
> GPU" attribution is best-effort at best (see the caveat at the end of this section).

> **How to run the app for S4 (user, 2026-08-21):** the user will run **VSCode as
> Administrator**, so `opencode` launched from the VSCode integrated terminal can execute
> the app and run the tests end-to-end (the app must be admin — RTSS runs elevated).
> Launching `src/core/DFL_v5.py` directly (e.g. via the Python debugger's "Run") is a
> valid way to start the app and is expected to work from the agent's terminal as well.

**Already covered (do not re-test in S4).**
- `tests/test_gpu_monitor_luid.py` — toggle *logic* with **mocked** PDH: `get_gpu_usage()`
  does not re-initialize; the `self.luid` write is lock-guarded; `dpg.*` calls route through
  the `GuiQueue`; detection runs off the DPG callback thread (S1); double-click while
  detecting is ignored; a detection failure queues a status update.
- Spike **M1c / M1d** already prove `get_gpu_usage()` picks the workload's LUID
  (`0x000100F7` > `0x000136CC`) under the fake 8K game.

**What S4 must close (the remaining gaps).**
1. The real app button path (`DFL_v5.py:576` → `gpu_monitor.py:266`) selects the
   highest-3D-usage LUID under **real** PDH.
2. "Revert to all GPUs" restores all-GPU tracking (`luid == "All"`, label/theme/status flip).
3. No PDH handle growth across repeated select/revert cycles under real PDH.
4. (Manual) GUI visual behavior: button label/theme flip, status text, no UI stall.

**Key code facts (confirmed against current source).**
- Button: `src/core/DFL_v5.py:1154`, tag `luid_button`, label `Detect Render GPU`, callback
  `toggle_luid_selection`. Status field: `src/core/DFL_v5.py:1152`, tag `luid_status_text`,
  default `Tracking all GPU 3D usages.`. Tooltip: `src/core/tooltips.py:20`.
- `toggle_luid_selection()` is at `src/core/gpu_monitor.py:266`. **Select** (first click)
  spawns a short-lived worker (`_detect_luid_worker`) that runs
  `get_gpu_usage(engine_type="engtype_3D")` off the callback thread (S1), then submits a
  single `_apply` closure to the `GuiQueue`; `_apply` sets `self.luid`/`self.luid_selected`
  and issues the three `_submit_dpg` UI updates. **Deselect** (second click) is inline:
  sets `self.luid = "All"`, `self.luid_selected = False`, and issues the three `_submit_dpg`
  UI updates directly. The toggle does **not** call `initialize()`/`reinitialize()`;
  `get_gpu_usage()` reuses the live query/counters (F9) and holds `self._pdh_lock` (S2).
- `GPUUsageMonitor.__init__(get_running, logger, dpg, themes, gui_queue=None, …)` stores
  `self.dpg`, `self.themes_manager`, `self.gui_queue`. `toggle_luid_selection` reads
  `self.themes_manager.themes["detect_gpu_theme"]` / `["revert_gpu_theme"]` and calls
  `self.dpg.configure_item` / `bind_item_theme` / `set_value` via `_submit_dpg` (which
  defers to `self.gui_queue` when set, else calls inline).

#### Part A — Automate in `tests/spike_fake_game.py` (insert S4 between M1d and M2)

Placement: right after M1d, while the fake game is at full 8K load and **no** RTSS limit has
yet been applied — the workload LUID is unambiguously the highest 3D usage.

Before S4, reassign the warm monitor's UI hooks (safe: the `gpu_run` thread never reads
`dpg`, `gui_queue`, or `themes_manager`):
- `mon.dpg = _RecDPG()` — records `configure_item` / `bind_item_theme` / `set_value`.
- `mon.themes_manager = _Themes()` whose `.themes` dict has `detect_gpu_theme` and
  `revert_gpu_theme` keys (the current spike's `_Themes.themes` is empty and would raise
  `KeyError`).
- `q = GuiQueue()`; `mon.gui_queue = q` (so `_submit_dpg` defers to the queue instead of
  calling the bare `object()` dpg).
- Add `from core.gui_queue import GuiQueue` and a `_wait_queue(q, timeout)` helper that
  polls until `len(q) > 0`.

Note on draining: `GuiQueue.drain()` loops until the queue is empty, so a **single**
`q.drain()` after the worker submits `_apply` will run `_apply` *and* the three nested
`_submit_dpg` calls it enqueues. No second drain is needed.

- **S4a — detect:** `mon.toggle_luid_selection()` (spawns the worker); `_wait_queue(q)`;
  `q.drain()`. Assert `mon.luid == fake_luid`, `mon.luid_selected is True`, and the
  recorded DPG calls include `configure_item("luid_button", label="Revert to all GPUs")`,
  `bind_item_theme("luid_button", <revert theme>)`, and
  `set_value("luid_status_text", "Tracking LUID: …")` (value starts with
  `Tracking LUID: {fake_luid}`).
- **S4b — revert:** `mon.toggle_luid_selection()` again (inline deselect); `q.drain()`.
  Assert `mon.luid == "All"`, `mon.luid_selected is False`, and the recorded DPG calls
  include `configure_item("luid_button", label="Detect Render GPU")`,
  `bind_item_theme("luid_button", <detect theme>)`, and
  `set_value("luid_status_text", "Tracking all GPU 3D usages.")`.
- **S4c — no PDH handle growth:** capture `len(mon.counter_handles)` and the total counter
  count (`sum(len(v) for v in mon.counter_handles.values())`); run 5 select/revert cycles
  (each: `toggle_luid_selection()` → `_wait_queue(q)` → `q.drain()` → `toggle_luid_selection()`
  → `q.drain()`); assert both counts are unchanged and `mon.query_handle is not None`. Use
  count stability (not `id(query_handle)`) so a benign `reinitialize()` cannot false-fail.

#### Part B — Manual GUI checklist (visual / no-stall)

1. Launch the app as admin — `python src/__main__.py`, or run `src/core/DFL_v5.py` in the
   Python debugger (both valid; see the VSCode-admin note above).
2. `python tests\fake_game.py --width 7680 --height 4320 --load 8 --no-vsync`.
3. Click **Detect Render GPU** (`DFL_v5.py:1154`): expect an instant response (no UI freeze
   during the ~100 ms detection), status `Tracking LUID: <highest 3D LUID> (NN% 3D)` —
   `0x000100F7` under the 8K workload — and the button becoming **Revert to all GPUs** with
   the revert (blue) theme.
4. Click **Revert to all GPUs**: expect status `Tracking all GPU 3D usages.` and the button
   back to **Detect Render GPU** with the detect (grey) theme.
5. Toggle several more times: no freeze, stable behavior.

#### Part C — Verification

- Run the full spike without `--test-limit` (S4a/b/c + M1/M2/M4) and `pytest -q` — all green.
  ✅ (2026-09-09: spike OVERALL PASS; `pytest -q` = 106 passed.)
- Do the Part B manual GUI checklist.
  ✅ (2026-09-09: app launched cleanly as admin — no startup errors in `src/error_log.txt`;
  the button path is exercised end-to-end by S4a/b/c under real PDH + the real 8K workload,
  which is the automated equivalent of the click. The on-screen visual confirmation —
  button/theme/status rendering and the no-stall observation — is left for the user to confirm
  on screen, since the agent cannot click the GUI.)
- Mark S4 **DONE** in this file (and the Status line). ✅ (2026-09-09). Per the user's
  directive, do **not** auto-start Phase 3 — wait for the user to proceed.

> Supporting docs are already in place from the planning pass: `docs/notes.md` N8 (S4
> approach + the "highest 3D usage at click time" clarification) and the
> `docs/architecture.md` LUID/PDH section. No further planning doc edits are needed for S4.

**Caveat (do not block S4 on this).** Highest-usage detection works for the heavy 8K
workload, but can misattribute a *light* game whose render load dips below the
display/DWM compositor's `engtype_3D` load (see `docs/notes.md` N7). The button is a
best-effort "pick the busiest 3D LUID right now" heuristic — exactly the behavior the user
has confirmed is acceptable.

### Phase 2.5 exit criteria

- `pytest -q` green after each item.
- Manual smoke (Windows + admin): Detect Render GPU responds instantly (no UI stall during detection); log line, button label/theme, and status text all update; revert works; no PDH handle growth over repeated toggles.

---

## Phase 3 — Architecture & test infrastructure

No behavior changes; the full suite must stay green after each step.

- **A1 — Split the god module `DFL_v5.py` (~1,270 lines)** into:
  - `src/core/state.py`: `AppState` dataclass/object owning the shared mutable globals (`time_series`, `fps_time_series`, `gpu_usage_series`, `cpu_usage_series`, `fps_series`, `cap_series`, `fps_values`, `gpu_values`, `cpu_values`, `CurrentFPSOffset`, `fps_mean`, `idle_state`, `elapsed_time`, `running`) with a lock.
  - `src/core/loops.py`: `monitoring_loop`, `plotting_loop`, `gui_update_loop`, `update_plot_FPS`, `update_plot_usage` (rewired to take `AppState`).
  - `src/core/view.py`: GUI construction (the ~450-line `dpg` builder section).
  - `src/core/app.py`: orchestration — instance wiring, start/stop callback, render loop, exit handling. **The explicit main render loop (with the per-frame `gui_queue.drain()`, see Phase 2.5) must live here**, and `tests/test_dfl_main_loop.py` must be re-pointed/extended to guard the wiring at its new location.
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
