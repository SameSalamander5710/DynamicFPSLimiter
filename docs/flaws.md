# Dynamic FPS Limiter — Flaws (fix ASAP)

> Only **glaring** issues are listed here: crashes, wrong cap behavior, data corruption,
> security, and resource leaks. Lower-priority smells (dead code, log spam, type hazards,
> GUI coupling, non-atomic INI, one-shot import leaks) are tracked under
> **Known issues & tech debt** in [`architecture.md`](./architecture.md).
>
> Severity: **High** = breaks core behavior or crashes a real user path; **Med** = crash /
> corruption / leak on a plausible path.

---

## F1 — Cap step-down silently skipped (wrong cap behavior)
**Severity:** High
**Where:** `src/core/DFL_v5.py:375` (`monitoring_loop`, decrease branch)

`list.index()` never returns a negative value, so the guard `if current_index < 0:` is dead.
When the current cap is already at or below `fps_mean`, the intended "move to the next lower
stepped value" step is skipped, so the limiter can fail to lower the cap when it should.

**Impact:** Core decision logic is wrong — the FPS cap may stay too high exactly when load is
rising (the primary use case).
**Fix:** Compute the index robustly (e.g. `bisect` over the sorted ladder, or
`next(i for i, v in enumerate(ladder) if v < fps_mean)`), and drop the bogus `< 0` check.

---

## F2 — LHM load failure crashes startup with no fallback
**Severity:** High
**Where:** `src/core/lhm_loader.py:162-171` + `src/core/config_manager.py` (`get_all_sensor_infos` in `ConfigManager.__init__`)

`ensure_loaded` swallows the `clr.AddReference` error, then the subsequent `from
LibreHardwareMonitor.Hardware import …` raises. That exception propagates out of
`ConfigManager.__init__` (called at import, no try/except) and kills the app.

**Impact:** On any machine where the .NET runtime or the matching LHM DLL is unavailable, the
app crashes at startup instead of falling back to the Legacy (Performance Counter) method.
**Fix:** Wrap the LHM bootstrap in try/except; on failure set `monitoring_method = Legacy`,
disable the LHM UI, and continue.

---

## F3 — Systemic cross-thread DearPyGui calls (crash / corruption)
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

---

## F4 — `set_fractional_fps_direct` NameError (live crash path)
**Severity:** Med
**Where:** `src/core/rtss_functions.py:222-235`, called live from `src/core/DFL_v5.py:179`

`found_limit` / `found_denominator` are assigned only inside the line-parsing loop. If the
profile `.cfg` is empty or contains only one of the two keys, the "append if not found" step
raises `NameError`.

**Impact:** The "Rest FPS cap" action (and Start/Stop, which call this) can crash on a
malformed or fresh profile file.
**Fix:** Initialize both flags to `False` before the loop.

---

## F5 — `current_stepped_limits()` can return `None` → `max(None)` crash
**Severity:** Med
**Where:** `src/core/fps_utils.py:30-49`; consumers at `src/core/DFL_v5.py:179` and
`tray_functions.py:280` (`update_hover_text`)

For an unknown/unselected `capmethod` (e.g. radio unselected → `""`), the function falls off
the end and returns `None`. Callers do `max(current_stepped_limits())`.

**Impact:** `TypeError` in the main loop or in the tray thread (which also kills the tray
icon). Ties into the `capmethod` default-case mismatch (see architecture.md).
**Fix:** Always return a non-empty list (fall back to `[mincap, maxcap]`), and/or validate the
`capmethod` value before use.

---

## F6 — Two competing, non-atomic RTSS profile write paths (corruption)
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

---

## F7 — Stop→Start polls a closed LibreHardwareMonitor `Computer`
**Severity:** Med
**Where:** `src/core/librehardwaremonitor.py:202-207`

`LHMSensor.stop()` calls `self.computer.Close()`, but `start()` never re-`Open()`s it.

**Impact:** After a Stop→Start cycle the LHM poll loop reads a closed `Computer` → empty/stale
sensor data, so LibreHM monitoring silently stops working until the app is restarted.
**Fix:** Re-open (or recreate) the `Computer` in `start()`.

---

## F8 — PDH query-handle leak + orphaned counters in `gpu_monitor`
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

---

## F9 — GUI/monitoring race on LUID selection
**Severity:** Med
**Where:** `src/core/gpu_monitor.py:239-265` (`toggle_luid_selection`)

The DPG-thread `toggle_luid_selection` mutates `self.query_handle` / `self.luid` while the
`gpu_run` thread uses them, with no lock.

**Impact:** A race can trigger repeated re-initialization (compounding F8's leak) or read
torn state.
**Fix:** Guard all shared monitor state with the existing lock; have the GUI request a
re-initialization via a flag that the monitor thread consumes.

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
