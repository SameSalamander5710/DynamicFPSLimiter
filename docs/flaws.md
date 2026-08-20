# Dynamic FPS Limiter — Flaws (fix ASAP)

> Only **glaring** issues are listed here: crashes, wrong cap behavior, data corruption,
> security, and resource leaks. Lower-priority smells (dead code, log spam, type hazards,
> GUI coupling, non-atomic INI, one-shot import leaks) are tracked under
> **Known issues & tech debt** in [`architecture.md`](./architecture.md).
>
> Severity: **High** = breaks core behavior or crashes a real user path; **Med** = crash /
> corruption / leak on a plausible path.

---

## F1 — Cap step-down silently skipped (wrong cap behavior) — **FIXED**
**Severity:** High
**Where:** `src/core/DFL_v5.py:375` (`monitoring_loop`, decrease branch)

`list.index()` never returns a negative value, so the guard `if current_index < 0:` is dead.
When the current cap is already at or below `fps_mean`, the intended "move to the next lower
stepped value" step is skipped, so the limiter can fail to lower the cap when it should.

**Impact:** Core decision logic is wrong — the FPS cap may stay too high exactly when load is
rising (the primary use case).
**Fix:** Compute the index robustly (e.g. `bisect` over the sorted ladder, or
`next(i for i, v in enumerate(ladder) if v < fps_mean)`), and drop the bogus `< 0` check.

**Resolution (2026-08-18):** The decrease policy was extracted to a pure, dependency-free
function `next_cap_on_decrease(fps_limit_list, current_cap, fps_mean)` in
`src/core/cap_policy.py`; `DFL_v5.monitoring_loop` now calls it and applies the result only
when it is not `None` (one-rung step-down when `cap <= fps_mean`, jump to the highest rung
below `fps_mean` when `cap > fps_mean`, highest rung below `cap` when the cap is not in the
ladder, `None` at the floor / empty ladder). The dead `< 0` branch is gone. Covered by
`tests/test_cap_policy.py` (parametrized policy table + a source-level guard on the DFL_v5
call site).

---

## F2 — LHM load failure crashes startup with no fallback — **FIXED**
**Severity:** High
**Where:** `src/core/lhm_loader.py:162-171` + `src/core/config_manager.py` (`get_all_sensor_infos` in `ConfigManager.__init__`)

`ensure_loaded` swallows the `clr.AddReference` error, then the subsequent `from
LibreHardwareMonitor.Hardware import …` raises. That exception propagates out of
`ConfigManager.__init__` (called at import, no try/except) and kills the app.

**Impact:** On any machine where the .NET runtime or the matching LHM DLL is unavailable, the
app crashes at startup instead of falling back to the Legacy (Performance Counter) method.
**Fix:** Wrap the LHM bootstrap in try/except; on failure set `monitoring_method = Legacy`,
disable the LHM UI, and continue.

**Resolution (2026-08-18):** `lhm_loader.ensure_loaded` now raises a dedicated
`LHMLoadError` (carrying the attempted DLL path) on both `clr.AddReference` failure and the
`LibreHardwareMonitor.Hardware` import failure, instead of `pass`-ing and letting a bare
`ImportError` escape; a failed load is not cached in `_LOADED`, so later calls can retry.
Every LHM bootstrap site degrades gracefully: `get_all_sensor_infos(base_dir, logger)` catches
`LHMLoadError`, logs it, and returns `[]` (so `ConfigManager` starts with no LibreHM sensors);
`LHMSensor` enters a `disabled` state (`computer = None`, `start()` no-ops, `stop()` skips
`Close()`) — required because `DFL_v5` constructs it at import time; `FPSUtils` logs and keeps
`SensorType`/`HardwareType = None` (the LibreHM path of `evaluate_cap_change` already no-ops
with empty `sensor_infos`). The bogus "fallback" re-raise in `fps_utils.py`/
`librehardwaremonitor.py` is gone. Covered by `tests/test_lhm_failure.py` (6 tests: loader
raises on AddReference failure, loader raises on import failure, `get_all_sensor_infos` →
`[]` + log, `ConfigManager` constructs with `sensor_infos == []`, disabled `LHMSensor`
start/stop no-ops, `FPSUtils` constructs and `evaluate_cap_change` → `(False, False)`).

---

## F3 — Systemic cross-thread DearPyGui calls (crash / corruption) — **FIXED**
**Severity:** Med (systemic)
**Where:** `tray_functions.py` (menu callbacks, restore/exit), `DFL_v5.py:312,559` (monitoring
& autopilot loops), `autopilot.py:62-79`, `logger.py` (`add_log`), `librehardwaremonitor.py`
(`_poll_loop` → `ReadingsText`), `fps_utils.py` (`SummaryText`/`LogText`)

Multiple background threads call `dpg.set_value` / `dpg.configure_item` directly
(`profile_dropdown`, `input_capmethod`, `LogText`, `SummaryText`, `ReadingsText`). DearPyGui is
**not** thread-safe.

**Impact:** Latent crashes or corrupted UI state whenever a tray menu action, an autopilot
profile switch, a log line, or an LHM reading lands off the main thread. The app "usually
works," which makes this the hardest bug to reproduce.
**Fix:** Marshal all DPG calls onto the main thread (e.g. a thread-safe queue drained in the
frame callback, or `dpg`-safe wrappers). Never call `dpg.*` from a worker thread.

**Resolution (2026-08-18):** All DPG calls are now marshalled onto the main render thread via
`src/core/gui_queue.py` (a thread-safe `GuiQueue` drained once per frame by a self-rescheduling
`_frame_hook` in `DFL_v5.py` — DearPyGui frame callbacks use **absolute** frame numbers and are
one-shot, so the hook re-registers via `dpg.set_frame_callback(dpg.get_frame_count() + 1, hook)`;
there is no `update_callback`).

> **Update (2026-08-20):** the self-rescheduling `_frame_hook` drain was replaced by the
> explicit main render loop at the end of `DFL_v5.py`, which drains the `GuiQueue` once per
> frame on the main thread (the hook could be orphaned forever by a long callback — see
> [`plan.md` Phase 2.5](../plan.md) and [notes.md N2](./notes.md)). Everything else in this
> resolution (the queue itself, logger and tray routing) is unchanged.
- **`logger.py`**: `log_messages` is guarded by a module `_log_lock` (thread-safe insert + trim to
  50). `_apply_log_text_to_widget()` reads a snapshot under the lock and is the only place `dpg.*`
  is touched; `add_log` / `refresh_log_display` submit it to the injected `GuiQueue` (via
  `set_gui_queue`), falling back to an inline call when no queue is set.
- **`tray_functions.py`**: `TrayManager` accepts an optional `gui_queue` (injected via
  `set_gui_queue`) and a `_run_on_main(fn)` helper (submit to the queue, or inline when absent).
  Every pystray-thread action is routed through it — `_toggle_start_stop`, the
  `_profile_menu_items` / `_method_menu_items` lambdas, and the `on_restore` / `on_exit` paths in
  `_restore_window` / `_exit_app` (the old raw `threading.Thread` calls are gone, guarded for
  `None` callbacks). `update_hover_text` is split into a thread-checking wrapper +
  `_update_hover_text_impl`; it reads profile/method from the ConfigManager snapshot
  (`cm.current_profile` / `cm.current_method`) instead of `dpg.get_value`, and defers to the queue
  when called off the main thread so the DPG reads inside `fps_utils.current_stepped_limits` stay
  on the render thread.
- **`config_manager.py`**: gained a `current_method` snapshot (init + `current_method_callback`).
- **`DFL_v5.py`**: injects the queue into `logger` and `tray` right after `gui_queue = GuiQueue()`;
  the `_frame_hook` re-registration is wrapped in `try/except` so a queued `exit_gui` (which
  destroys the DPG context) can't raise during shutdown.

Covered by `tests/test_logger.py` (5: `set_gui_queue`, `add_log` defers DPG off the worker thread
and runs on the draining main thread, inline fallback without a queue, 50-message trim, 8-thread
buffer-consistency) and `tests/test_tray.py` (8: `_run_on_main` defer/inline, `update_hover_text`
defer-off-main-thread + inline-on-main built from the cm snapshot, profile/method menu lambdas
defer, `_exit_app` / `_restore_window` defer). Suite **92 passed**.

---

## F4 — `set_fractional_fps_direct` NameError (live crash path) — **FIXED**
**Severity:** Med
**Where:** `src/core/rtss_functions.py:222-235`, called live from `src/core/DFL_v5.py:179`

`found_limit` / `found_denominator` are assigned only inside the line-parsing loop. If the
profile `.cfg` is empty or contains only one of the two keys, the "append if not found" step
raises `NameError`.

**Impact:** The "Rest FPS cap" action (and Start/Stop, which call this) can crash on a
malformed or fresh profile file.
**Fix:** Initialize both flags to `False` before the loop.

**Resolution (2026-08-18):** `found_limit` and `found_denominator` are now initialized to
`False` before the line-parsing loop, and the dead `found` flag (set but never used) was
removed. A profile file missing one or both keys now gets the missing line(s) appended
instead of raising `NameError`. Covered by `tests/test_rtss_fractional_direct.py`
(missing-both-appends-both, missing-one-appends-only-that-one, both-present-updates-in-place,
`UpdateProfiles` called only when `update=True`, and missing-profile-file-returns-False, all
run against a real temp `Profiles/` dir via the `rtss_stub` fixture).

---

## F5 — `current_stepped_limits()` can return `None` → `max(None)` crash — **FIXED**
**Severity:** Med
**Where:** `src/core/fps_utils.py:30-49`; consumers at `src/core/DFL_v5.py:179` and
`tray_functions.py:280` (`update_hover_text`)

For an unknown/unselected `capmethod` (e.g. radio unselected → `""`), the function falls off
the end and returns `None`. Callers do `max(current_stepped_limits())`.

**Impact:** `TypeError` in the main loop or in the tray thread (which also kills the tray
icon). Ties into the `capmethod` default-case mismatch (see architecture.md).
**Fix:** Always return a non-empty list (fall back to `[mincap, maxcap]`), and/or validate the
`capmethod` value before use.

**Resolution (2026-08-18):** `current_stepped_limits()` is now total. The `custom` branch
returns the parsed list only when it is non-empty; a parse exception, an empty parse result, or
an empty input string all log and fall back to `make_stepped_values(maxcap, mincap, capstep)`.
An unknown `capmethod` (including the unselected `""`) logs and falls back to the same stepped
ladder instead of falling off the end. The `step` and `ratio` paths are unchanged. Covered by
`tests/test_fps_utils_limits.py` (valid custom passthrough, parse-exception fallback,
empty-parse-result fallback, empty-string fallback, unknown-method fallback, and snapshot
checks that `step`/`ratio` still return their previous values).

---

## F6 — Two competing, non-atomic RTSS profile write paths (corruption) — **FIXED**
**Severity:** Med
**Where:** `src/core/rtss_functions.py` — `set_limit_denominator` / `set_fractional_fps_direct`
(direct `.cfg` text edits) vs `set_fractional_framerate` (`LoadProfile`/`SetProfileProperty`/
`SaveProfile` API)

The API path and the direct-file path interleave on the same profile file, and none of the
writes are atomic.

**Impact:** A concurrent or interleaved write can clobber the other's changes or leave a
half-written `.cfg`, corrupting the user's RTSS profile.
**Fix:** Pick a single write path (prefer the RTSS API), serialize writes behind a lock, and
write files atomically (temp file + rename).

**Resolution (2026-08-19):** All profile mutations are now serialized behind a re-entrant lock
and the file writes are atomic. `RTSSController.__init__` creates `self._profile_lock =
threading.RLock()`; `set_limit_denominator`, `set_fractional_fps_direct`, `set_fractional_framerate`,
and `set_profile_property` (whose `SaveProfile` also writes the `.cfg`) each run their body under
`with self._profile_lock:`. `RLock` (not `Lock`) is required because `set_fractional_framerate`
calls `set_limit_denominator` + `set_profile_property` while already holding the lock. A new
`_atomic_write_lines(profile_file, lines)` helper writes to `<file>.tmp`, `f.flush()`s,
`os.fsync`s the fd, then `os.replace`s it over the target (atomic on the same NTFS volume);
`set_limit_denominator` and `set_fractional_fps_direct` route their final write through it instead
of a bare `open(..., "w")`, so a crash or a concurrent RTSS read can never observe a half-written
profile. The two public writers were **kept separate** (not merged): `set_fractional_fps_direct`
is a pure file edit of `Limit=`/`LimitDenominator=`, whereas `set_fractional_framerate` pushes
`FramerateLimit` through the **DLL API** and also writes the denominator to file — distinct
file-vs-DLL semantics, so merging would change behavior; the idempotent denominator double-write
is harmless under the lock. This protects the real concurrent callers: the start/stop callback
(`DFL_v5.py:181-182`, main thread) and the monitoring loop (`DFL_v5.py:359/371/395/407/414`,
background thread) plus the exit path (`DFL_v5.py:550`). Covered by `tests/test_rtss_atomic.py`
(5 writers/flags: correct content + no `.tmp`, `set_fractional_framerate` return value + nested
denominator write, two concurrent threads always leave a consistent `(limit, denominator)` pair,
`UpdateProfiles` per `update` flag); the `rtss_stub` fixture now sets `ctrl._profile_lock`.

---

## F7 — Stop→Start polls a closed LibreHardwareMonitor `Computer` — **FIXED**
**Severity:** Med
**Where:** `src/core/librehardwaremonitor.py:202-207`

`LHMSensor.stop()` calls `self.computer.Close()`, but `start()` never re-`Open()`s it.

**Impact:** After a Stop→Start cycle the LHM poll loop reads a closed `Computer` → empty/stale
sensor data, so LibreHM monitoring silently stops working until the app is restarted.
**Fix:** Re-open (or recreate) the `Computer` in `start()`.

**Resolution (2026-08-18):** `LHMSensor` now tracks an explicit `_computer_open` flag. Computer
creation/open was extracted into `_create_and_open_computer()` (always builds a fresh instance,
enables CPU/GPU, `Open()`s, sets the flag). `start()` re-creates and re-opens the `Computer`
when it is `None` or not open (and refreshes `cpu_name`), so a Stop→Start cycle polls live
hardware again; a double `start()` still no-ops via the thread-alive guard and does not
double-open. `stop()` only `Close()`s when open and clears the flag. Separately,
`get_all_sensor_infos()` now wraps its one-shot enumeration in `try/finally` so its `Computer`
is always `Close()`d (previously leaked at startup), even if enumeration raises. Covered by
`tests/test_lhm_lifecycle.py` (start-after-stop reopens a new Computer, double-start does not
double-open, `get_all_sensor_infos` closes its Computer on the success path and on an
enumeration error, all against a fake `Computer`/`Hardware`/type triple).

---

## F8 — PDH query-handle leak + orphaned counters in `gpu_monitor` — **FIXED**
**Severity:** Med
**Where:** `src/core/gpu_monitor.py:267-279` (`reinitialize` / `initialize`)

`reinitialize()` builds new counter handles but **discards** them (never assigns
`self.counter_handles`), and `initialize()` opens a new PDH query without closing the previous
one.

**Impact:** After any counter-read failure (or a LUID toggle) the monitor thread keeps reading
counters registered on an orphaned query, and a query handle leaks on every retry — both wrong
GPU readings and unbounded handle growth.
**Fix:** Close the old query before opening a new one, and assign the new handles to
`self.counter_handles`.

**Resolution (2026-08-18):** Added a `_close_query()` helper that calls `pdh.PdhCloseQuery` on
the current `self.query_handle` (when set) and resets `self.query_handle = None` and
`self.counter_handles = {}` (counter handles belong to the query, so they are invalidated with
it). `initialize()` now calls `_close_query()` first, so every re-init closes the previous HQUERY
before opening a new one — no more per-retry handle leak. `reinitialize()` now assigns the
re-setup result to `self.counter_handles` (previously it was written to a discarded local
`temp_counter_handles`), so the poll loop reads counters on the live query instead of orphaned
ones. Covered by `tests/test_gpu_monitor_handles.py` (initialize closes the prior query before
opening a new one; `_close_query` resets state and is a no-op when no handle is open;
`reinitialize` assigns the latest setup's handles, verified with a call-counting mock, all
against a monitor built via `__new__` so no real PDH query or thread is involved).

---

## F9 — GUI/monitoring race on LUID selection — **FIXED**
**Severity:** Med
**Where:** `src/core/gpu_monitor.py:239-265` (`toggle_luid_selection`)

The DPG-thread `toggle_luid_selection` mutates `self.query_handle` / `self.luid` while the
`gpu_run` thread uses them, with no lock.

**Impact:** A race can trigger repeated re-initialization (compounding F8's leak) or read
torn state.
**Fix:** Guard all shared monitor state with the existing lock; have the GUI request a
re-initialization via a flag that the monitor thread consumes.

**Resolution (2026-08-18):** Three-part fix in `gpu_monitor.py`. (1) `get_gpu_usage()` no longer
calls `self.initialize()` on every invocation — it reuses the existing `self.query_handle` and
`self.counter_handles`, so a LUID toggle no longer clobbers the live query/counters mid-run or
leaks a query (compounding F8). (2) `self.luid` is now guarded by `self._lock`: `gpu_run()` reads
it under the lock, and `toggle_luid_selection()` writes it under the lock, so the DPG thread and
the monitor thread can no longer tear the value. (3) Every `dpg.*` call in
`toggle_luid_selection()` now routes through a new `_submit_dpg()` helper that defers the call to
the F3 `GuiQueue` (falling back to a direct call when no queue is set), so no DearPyGui call is
made from a non-main thread. To unblock this, **F3's `GuiQueue` was pulled forward**:
`src/core/gui_queue.py` is a thread-safe `submit`/`drain` queue (per-callback exception isolation,
optional `on_error` hook), and `DFL_v5.py` drains it once per frame via a single self-rescheduling
`_frame_hook` that re-registers for the next frame via `dpg.set_frame_callback(dpg.get_frame_count() + 1, _frame_hook)` — DearPyGui frame callbacks use **absolute** frame numbers and are one-shot (a later registration for the same frame overwrites the earlier one, so the naive `set_frame_callback(1, hook)` self-reschedule fires only once), and there is no `update_callback`; the queue is passed to
`GPUUsageMonitor(..., gui_queue=gui_queue)`.

> **Update (2026-08-20):** the `_frame_hook` drain described above was replaced by the
> explicit main render loop draining the `GuiQueue` once per frame (see
> [`plan.md` Phase 2.5](../plan.md) and [notes.md N2](./notes.md)). The F9 code-level fixes
> (no re-init in `get_gpu_usage`, lock-guarded `luid`, `_submit_dpg`) are unchanged.

Covered by `tests/test_gpu_monitor_luid.py`
(`get_gpu_usage` does not call `initialize`; the `self.luid` write is lock-guarded; `dpg.*` calls
are buffered in the `GuiQueue` and only executed on drain — for both the select and deselect
paths) and `tests/test_gui_queue.py` (ordering, kwargs, concurrent-submission safety, and that a
failing callback does not stall the queue).

---

## Notes on items investigated and **not** included here
- `src/error_log.txt` and `src/config/*.ini` are gitignored and untracked (no repo-hygiene flaw).
- `ConfigManager(logger, dpg, rtss, None, …)` — the `None` is the `tray` argument (set later);
  `rtss` is wired correctly (not a flaw).
- `faqs.csv` is present in both dev and frozen builds, so its import-time `open()` only crashes
  if the asset is genuinely missing (latent, low).
- One-shot import-time `Computer` leak in `get_all_sensor_infos`, the missing try/except in
  `_poll_loop`, non-atomic INI writes, and the `copy_from_plot` int-truncation are real but
  lower-priority — see architecture.md §11.
