# Engineering Notes — Lessons Learned

> Durable notes from bug fixes and refactors in this codebase. Read before touching GUI
> threading, DearPyGui callbacks, or PDH code. Companion to [`architecture.md`](./architecture.md),
> [`flaws.md`](./flaws.md), and [`../plan.md`](../plan.md).

## N1 — DearPyGui 2.x threading model (verified against the v2.0.0 C++ source)

- **All Python callbacks run on one dedicated background thread** — button clicks *and*
  frame callbacks alike. `setup_dearpygui` starts it (`std::async(mvRunCallbacks)`); there is
  no per-callback thread and no way to opt out.
- **`dpg.set_frame_callback(N, cb)` defers registration to that same callback thread** (via
  `mvSubmitCallback`). The main render thread checks `frameCallbacks[current_frame]`
  **once per frame, by exact absolute frame number**. Entries for past frames are never
  re-checked and never deleted; registering for an already-used frame overwrites the earlier
  callback.
- **`dpg.get_frame_count()`** returns the frame counter set at the start of `Render()` on the
  main thread.
- **`dpg.start_dearpygui()` is literally**
  `while is_dearpygui_running(): render_dearpygui_frame()` — so an explicit app-side loop is
  behaviorally identical and gives us a place to do our own per-frame work.
- **DearPyGui is not thread-safe.** Only the main render thread may call `dpg.*`.

Consequence: any work done inside a callback delays *every* other callback (same thread),
including pending frame-callback registrations.

## N2 — Never use a self-rescheduling frame callback as a per-frame hook

**The 2026-08-20 regression.** Phase 2 (F3/F9) drained the `GuiQueue` from a
self-rescheduling `_frame_hook`: `dpg.set_frame_callback(dpg.get_frame_count() + 1, hook)`.
Kill sequence:

1. The hook for frame M runs on the callback thread, reads `get_frame_count()` → M, and
   enqueues the registration for frame M+1.
2. A button callback (`toggle_luid_selection`) runs next on the *same* thread and blocks it
   ≥100 ms (`time.sleep(0.1)` + two `PdhCollectQueryData`).
3. Meanwhile the main thread keeps rendering and checks `frameCallbacks[M+1]` — still absent.
4. The registration finally lands, but frame M+1 has already been checked, and past-frame
   entries are never re-checked → the hook is orphaned **forever**.
5. `gui_queue.drain()` never runs again → the log widget freezes (messages still accumulate
   in the buffer) and all queued button feedback is invisible. No exception anywhere.

**Rule:** the only reliable per-frame drain point is the **explicit main render loop**.
`DFL_v5.py` ends with:

```python
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()
    gui_queue.drain()
```

Regression guards: `tests/test_dfl_main_loop.py` (main loop drains; no
`dpg.set_frame_callback(` / `_frame_hook` wiring) — a refactor that reintroduces frame-hook
draining fails this test.

## N3 — DPG callbacks must never block

Button handlers run on the DPG callback thread (N1). Never do this inside a callback:
`time.sleep`, blocking I/O, PDH double-collects, .NET calls — anything taking more than a few
ms. Offload to a short-lived worker thread and return the result via the `GuiQueue`.
(Done: S1 — `toggle_luid_selection` now spawns a daemon worker for the PDH read; a single
queued closure applies state + UI on the main thread; a `_detecting` flag ignores double-clicks.)

## N4 — Shared native handles need their own synchronization

Python locks guard Python-visible state (`self.luid`, `self.samples`); native handles have
their own concurrency rules. PDH: `PdhCollectQueryData` on a shared HQUERY from two threads
without a lock is unsafe, and a reinit (close + open + add counters) can race an in-flight
read. Enumerate **every thread that touches a handle** and guard all calls with a dedicated
lock. (Done: S2 — every `Pdh*` call on the shared query in `gpu_monitor.py` is serialized on
`self._pdh_lock`, an `RLock` because `reinitialize()` re-enters from inside a locked read.)

## N5 — Make queue-drain failures visible

`GuiQueue(on_error=...)` must be wired to `logging.error`. A silent drain failure is how the
N2 bug hid for days — every visible symptom (frozen log, dead buttons) pointed at the queue,
but the queue itself swallowed the evidence. (Done: S3 — `DFL_v5.py` constructs
`GuiQueue(on_error=_gui_queue_error)`, which logs via `logging.error(..., exc_info=exc)`.)
Note: root `logging` is configured by `logger.init_logging` at startup, so `logging.error(...)`
reaches `error_log.txt`.

## N6 — Testing patterns that catch this class of bug

- **Source-level wiring guards** for module-level scripts that cannot be imported in tests
  (`DFL_v5` runs the app on import): assert the required wiring is present *and* the banned
  pattern is absent (`tests/test_dfl_main_loop.py`).
- **"Across frames" simulation**: interleave slow and failing queue items across repeated
  drain cycles and assert order, isolation, and an eventually-empty queue
  (`tests/test_gui_queue.py::test_drain_survives_long_running_items_across_frames`).
- **Every refactor that moves threading-sensitive wiring ships its regression test in the
  same commit** (plan.md principle, enforced).

## N7 — A D3D app lights up TWO GPU LUIDs in PDH `engtype_3D` (render + DWM)

**Verified 2026-08-21** with an 8K (7680×4320) DearPyGui overdraw workload
(`tests/fake_game.py --width 7680 --height 4320 --load 8 --no-vsync`) read through the app's
real `GPUUsageMonitor` (`src/core/gpu_monitor.py`).

- With no 3D app running, **every** LUID's `engtype_3D` utilization is `0%`. A local LLM
  (compute engine, not the 3D engine) does **not** contaminate the counter.
- Once a D3D app renders, **two** LUIDs go non-zero:
  - the **render GPU** — the adapter the app's D3D device lives on (highest usage);
  - the **display / DWM GPU** — the adapter that composites & presents the window (lower usage).
- On this machine (RX 6700 XT primary render + RX 9070 XT display): render LUID `0x000100F7`
  ≈ 15–19%, display LUID `0x000136CC` ≈ 13–14%, third LUID `0x0001365B` = 0%.

**Consequence for "Detect Render GPU":** the heuristic that picks the **highest-usage** LUID as
the render GPU is correct while the game's render load exceeds the DWM compositing load (true
for the 8K workload: 16–19% vs 13%). It is a **latent misattribution** if a light game's render
load drops below the display GPU's compositing load — the detector would then pick the display
GPU. A robust fix should attribute by per-LUID *delta from a no-game baseline* and, ideally, by
the DXGI adapter LUID the target process actually owns, rather than by absolute peak.

**Testing consequence:** a per-LUID PDH test must (a) read a **persistent, warm**
`GPUUsageMonitor` (a one-shot PDH query reads `0.0` for GPU Engine utilization), and (b) expect
**two** non-zero LUIDs (render + display), not one. `tests/spike_fake_game.py` M1 verifies the
app's `get_gpu_usage()` LUID matches the LUID with the largest rise over baseline.
