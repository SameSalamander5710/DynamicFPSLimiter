"""Spike: prove the fake game is a valid stand-in for a 3D game.

Verifies, end to end, against a *real* GPU and (if running) *real* RTSS:

  M1  PDH visibility  -- the app's real GPUUsageMonitor.get_gpu_usage() reports
      non-zero 3D-engine utilization, and the LUID whose utilization jumps when the
      fake game starts is attributed to the fake game (before/after PDH).
  S4  LUID detect/revert -- the real "Detect Render GPU" button path
      (GPUUsageMonitor.toggle_luid_selection) picks the highest-3D-usage LUID under
      real PDH, flips the button label/theme + status text, reverts to all-GPU
      tracking, and does not grow the PDH handle count over repeated toggles.
  M2  RTSS recognition-- the fake game's PID appears in RTSS shared memory
      (RTSSSharedMemoryV2), i.e. RTSS has hooked it, and its FPS is readable.
  M3  RTSS limiting   -- (opt-in, --test-limit) a Global FramerateLimit is applied
      via the real RTSSController, the fake game's FPS drops to ~the limit, and the
      original limit is restored. This briefly changes your real RTSS Global limit.

Run:
    python tests/spike_fake_game.py                 # M1 + S4 + M2 (read-only w.r.t. RTSS)
    python tests/spike_fake_game.py --test-limit    # also M3 (applies + restores limit)
        [--limit 30] [--load 8] [--title "DFL Fake Game"]

This is a manual verification script (not a pytest module). It is the seed for the
future gated pytest integration tests.
"""
import argparse
import json
import mmap
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FAKE_GAME = Path(__file__).resolve().parent / "fake_game.py"
PY = sys.executable

# --------------------------------------------------------------------------- #
# LUID attribution                                                             #
# --------------------------------------------------------------------------- #
def attribute_luid(base: dict, current: dict, min_delta: float):
    """Return the LUID whose utilization rose the most vs ``base`` (the fake
    game's adapter), or None if nothing rose by at least ``min_delta``."""
    all_luids = set(base) | set(current)
    best_luid, best_delta = None, 0.0
    for luid in all_luids:
        delta = current.get(luid, 0.0) - base.get(luid, 0.0)
        if delta > best_delta:
            best_luid, best_delta = luid, delta
    if best_luid is None or best_delta < min_delta:
        return None
    return best_luid


# --------------------------------------------------------------------------- #
# RTSS shared memory (read-only) -- layout mirrors core.rtss_interface         #
# --------------------------------------------------------------------------- #
def read_rtss_entry(target_pid: int):
    """Return (found, fps, process_name) for ``target_pid`` from RTSS shared memory."""
    try:
        mm = mmap.mmap(0, 4485160, "RTSSSharedMemoryV2")
    except FileNotFoundError:
        return False, None, None
    except OSError:
        return False, None, None
    try:
        (dwSignature, dwVersion, dwAppEntrySize, dwAppArrOffset, dwAppArrSize,
         dwOSDEntrySize, dwOSDArrOffset, dwOSDArrSize, dwOSDFrame
         ) = struct.unpack("4sLLLLLLLL", mm[0:36])
        calc = dwAppArrOffset + dwAppArrSize * dwAppEntrySize
        if 4485160 < calc:
            mm.close()
            mm = mmap.mmap(0, calc, "RTSSSharedMemoryV2")
        if dwSignature[::-1] not in (b"RTSS", b"SSTR") or dwVersion < 0x00020000:
            return False, None, None
        for i in range(dwAppArrSize):
            entry = dwAppArrOffset + i * dwAppEntrySize
            stump = mm[entry:entry + 6 * 4 + 260]
            if len(stump) == 0:
                continue
            dwProcessID, szName, dwFlags, dwTime0, dwTime1, dwFrames, dwFrameTime \
                = struct.unpack("L260sLLLLL", stump)
            if dwProcessID == target_pid:
                name = szName.decode(errors="ignore").rstrip("\x00").split("\\")[-1]
                fps = None
                if dwTime0 > 0 and dwTime1 > 0 and dwFrames > 0:
                    fps = 1000.0 * dwFrames / (dwTime1 - dwTime0)
                return True, fps, name
        return False, None, None
    finally:
        mm.close()


# --------------------------------------------------------------------------- #
# small helpers                                                                #
# --------------------------------------------------------------------------- #
def wait_for_file(path: Path, timeout: float, poll: float = 0.1) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if path.exists():
            return True
        time.sleep(poll)
    return path.exists()


def read_fps_file(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("fps")
    except (OSError, ValueError):
        return None


def read_all_usage(mon, luids) -> dict:
    """Return ``{luid: usage_pct}`` using the app's *persistent* (warm)
    GPUUsageMonitor. A one-shot reader (two collects on a fresh query) reads 0.0
    for the GPU Engine utilization counter; the monitor's background thread keeps
    the query warm so every read is a meaningful rate."""
    out = {}
    for luid in luids:
        try:
            u, _ = mon.get_gpu_usage(target_luid=luid)
            out[luid] = float(u)
        except Exception:
            out[luid] = 0.0
    return out


class _Result:
    def __init__(self):
        self.rows = []

    def add(self, name, passed, detail=""):
        self.rows.append((name, bool(passed), detail))

    def print_summary(self):
        print("\n" + "=" * 72)
        print("SPIKE SUMMARY")
        print("=" * 72)
        ok = True
        for name, passed, detail in self.rows:
            ok = ok and passed
            mark = "PASS" if passed else "FAIL"
            print(f"  [{mark}] {name}" + (f"  -- {detail}" if detail else ""))
        print("-" * 72)
        print(f"  OVERALL: {'PASS' if ok else 'FAIL'}")
        print("=" * 72)
        return ok


# --------------------------------------------------------------------------- #
# main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Fake-game verification spike")
    ap.add_argument("--title", default="DFL Fake Game")
    ap.add_argument("--load", type=int, default=8)
    # 8K default: at 1080p the per-rect CPU rebuild cost exceeds the GPU fill cost,
    # so the CPU is always the bottleneck and the 3D engine never saturates. At 8K the
    # per-layer GPU fill (~200us) exceeds the CPU cost (~35us), making the GPU the
    # bottleneck -> a strong, stable engtype_3D signal (~16-19% at load 8).
    ap.add_argument("--width", type=int, default=7680)
    ap.add_argument("--height", type=int, default=4320)
    ap.add_argument("--vsync", action="store_true",
                    help="enable vsync (default: no-vsync, matches the measured signal)")
    ap.add_argument("--min-usage", type=float, default=10.0,
                    help="fake-game LUID must reach at least this %% 3D utilization")
    ap.add_argument("--min-delta", type=float, default=2.0,
                    help="minimum utilization jump (vs baseline) to attribute a LUID")
    ap.add_argument("--test-limit", action="store_true",
                    help="also apply a Global RTSS FramerateLimit and verify the drop")
    ap.add_argument("--limit", type=float, default=30.0, help="frame limit for --test-limit")
    ap.add_argument("--rtss-timeout", type=float, default=12.0,
                    help="seconds to wait for RTSS recognition / limit effect")
    args = ap.parse_args()

    tmp = Path(os.environ.get("TEMP", os.environ.get("TMP", ".")))
    ready = tmp / "spike_fg_ready.json"
    fps_file = tmp / "spike_fg_fps.json"
    for p in (ready, fps_file):
        p.unlink(missing_ok=True)

    res = _Result()
    proc = None
    orig_limit = None  # (limit_int, denominator, file_content)

    print(f"[spike] fake game: {FAKE_GAME}")
    print(f"[spike] python:    {PY}")

    # Persistent (warm) PDH query via the app's real GPUUsageMonitor. A one-shot
    # reader reads 0.0 for the GPU Engine utilization counter; the monitor's
    # background thread keeps the query warm so reads are meaningful.
    from core.gpu_monitor import GPUUsageMonitor

    class _Logger:
        def add_log(self, m):
            pass

    class _Themes:
        # S4: toggle_luid_selection reads these keys; give them distinct sentinel
        # values so the spike can assert which theme the button was bound to.
        themes = {"detect_gpu_theme": "detect_theme_id",
                  "revert_gpu_theme": "revert_theme_id"}

    running = {"v": True}
    mon = GPUUsageMonitor(lambda: running["v"], _Logger(), object(), _Themes(),
                          gui_queue=None, interval=0.1)
    time.sleep(2.0)  # let the background thread warm the query
    luids = mon.list_all_luids()
    print(f"[spike] LUIDs: {luids}")

    # ---- baseline (fake game not running) ---------------------------------- #
    print("\n[spike] M1 reading baseline 3D utilization (fake game not running)...")
    base = read_all_usage(mon, luids)
    print(f"[spike] baseline: { {k: round(v, 1) for k, v in base.items()} }")

    # ---- launch fake game -------------------------------------------------- #
    print(f"\n[spike] launching fake game (title={args.title!r}, load={args.load}, "
          f"{args.width}x{args.height}, vsync={args.vsync})...")
    cmd = [PY, str(FAKE_GAME), "--title", args.title, "--ready-file", str(ready),
           "--fps-file", str(fps_file), "--load", str(args.load),
           "--width", str(args.width), "--height", str(args.height)]
    if not args.vsync:
        cmd.append("--no-vsync")
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    pid = None
    try:
        if not wait_for_file(ready, timeout=20.0):
            raise RuntimeError("fake game did not become ready in 20s")
        pid = json.loads(ready.read_text(encoding="utf-8"))["pid"]
        print(f"[spike] fake game ready pid={pid}")

        # ---- M1: PDH visibility + attribution ------------------------------ #
        print("\n[spike] M1 waiting for the fake game's 3D utilization to rise...")
        fake_luid = None
        end = time.time() + 20.0
        while time.time() < end:
            cur = read_all_usage(mon, luids)
            fake_luid = attribute_luid(base, cur, args.min_delta)
            if fake_luid is not None and cur.get(fake_luid, 0.0) >= args.min_usage:
                break
            time.sleep(0.5)
        cur = read_all_usage(mon, luids)
        fake_usage = cur.get(fake_luid, 0.0) if fake_luid else 0.0
        res.add("M1a LUID attributed (utilization jumped)", fake_luid is not None,
                f"luid={fake_luid} usage={fake_usage:.1f}% delta="
                f"{(fake_usage - base.get(fake_luid, 0.0)) if fake_luid else 0:.1f}%")
        res.add("M1b fake-game 3D utilization >= threshold",
                fake_luid is not None and fake_usage >= args.min_usage,
                f"{fake_usage:.1f}% (threshold {args.min_usage}%)")

        # App's real code path: GPUUsageMonitor.get_gpu_usage() (reuses the warm
        # monitor created above; it already returns the max-usage LUID).
        print("\n[spike] M1 querying the app's real GPUUsageMonitor.get_gpu_usage()...")
        app_usage, app_luid = 0, ""
        for _ in range(3):
            u, l = mon.get_gpu_usage(engine_type="engtype_3D")
            if u > app_usage:
                app_usage, app_luid = u, l
        res.add("M1c app get_gpu_usage() sees non-zero 3D usage", app_usage > 0,
                f"usage={app_usage}% luid={app_luid}")
        res.add("M1d app get_gpu_usage() LUID == attributed LUID",
                fake_luid is not None and app_luid == fake_luid,
                f"app={app_luid} attributed={fake_luid}")

        # ---- S4: LUID detect/revert verification (real PDH, real workload) -- #
        # Inserted between M1d and M2: the fake game is at full 8K load and no RTSS
        # limit has been applied, so the workload LUID is unambiguously the highest
        # 3D usage. Verifies the real app button path end-to-end (status.md S4).
        print("\n[spike] S4 verifying LUID detect/revert (real PDH, real workload)...")
        from core.gui_queue import GuiQueue

        class _RecDPG:
            """Records dpg calls so S4 can assert the button/status flips."""
            def __init__(self):
                self.calls = []
            def configure_item(self, *a, **k):
                self.calls.append(("configure_item", a, k))
            def bind_item_theme(self, *a, **k):
                self.calls.append(("bind_item_theme", a, k))
            def set_value(self, *a, **k):
                self.calls.append(("set_value", a, k))

        def _wait_queue(q, timeout=10.0):
            end = time.time() + timeout
            while time.time() < end:
                if len(q) > 0:
                    return True
                time.sleep(0.02)
            return len(q) > 0

        def _last_call(rec, name):
            for c in reversed(rec.calls):
                if c[0] == name:
                    return c
            return None

        # Reassign the warm monitor's UI hooks (safe: gpu_run never reads dpg /
        # gui_queue / themes_manager). mon.themes_manager already carries the
        # detect/revert theme keys (see _Themes above).
        rec = _RecDPG()
        mon.dpg = rec
        q = GuiQueue()
        mon.gui_queue = q

        # S4a -- detect: first click spawns a worker; wait for _apply, then a single
        # drain() runs _apply AND the three nested dpg calls it enqueues.
        mon.toggle_luid_selection()
        _wait_queue(q)
        q.drain()
        s4a_cfg = _last_call(rec, "configure_item")
        s4a_bind = _last_call(rec, "bind_item_theme")
        s4a_val = _last_call(rec, "set_value")
        s4a_ok = (
            mon.luid == fake_luid
            and mon.luid_selected is True
            and s4a_cfg is not None and s4a_cfg[1] == ("luid_button",)
            and s4a_cfg[2].get("label") == "Revert to all GPUs"
            and s4a_bind is not None and s4a_bind[1] == ("luid_button", "revert_theme_id")
            and s4a_val is not None and s4a_val[1][0] == "luid_status_text"
            and str(s4a_val[1][1]).startswith(f"Tracking LUID: {fake_luid}")
        )
        res.add("S4a detect picks highest-3D LUID + flips UI", s4a_ok,
                f"luid={mon.luid} selected={mon.luid_selected} "
                f"cfg={s4a_cfg[2].get('label') if s4a_cfg else None} "
                f"status={s4a_val[1][1] if s4a_val else None}")

        # S4b -- revert: second click is an inline deselect; one drain() flushes its
        # three dpg calls.
        rec.calls.clear()
        mon.toggle_luid_selection()
        q.drain()
        s4b_cfg = _last_call(rec, "configure_item")
        s4b_bind = _last_call(rec, "bind_item_theme")
        s4b_val = _last_call(rec, "set_value")
        s4b_ok = (
            mon.luid == "All"
            and mon.luid_selected is False
            and s4b_cfg is not None and s4b_cfg[1] == ("luid_button",)
            and s4b_cfg[2].get("label") == "Detect Render GPU"
            and s4b_bind is not None and s4b_bind[1] == ("luid_button", "detect_theme_id")
            and s4b_val is not None
            and s4b_val[1] == ("luid_status_text", "Tracking all GPU 3D usages.")
        )
        res.add("S4b revert restores all-GPU tracking + flips UI back", s4b_ok,
                f"luid={mon.luid} selected={mon.luid_selected} "
                f"cfg={s4b_cfg[2].get('label') if s4b_cfg else None} "
                f"status={s4b_val[1][1] if s4b_val else None}")

        # S4c -- no PDH handle growth over repeated toggles (count stability, not
        # id(query_handle), so a benign reinitialize() cannot false-fail).
        handles_before = len(mon.counter_handles)
        counters_before = sum(len(v) for v in mon.counter_handles.values())
        for _ in range(5):
            mon.toggle_luid_selection()  # detect
            _wait_queue(q)
            q.drain()
            mon.toggle_luid_selection()  # revert
            q.drain()
        handles_after = len(mon.counter_handles)
        counters_after = sum(len(v) for v in mon.counter_handles.values())
        s4c_ok = (
            handles_after == handles_before
            and counters_after == counters_before
            and mon.query_handle is not None
        )
        res.add("S4c no PDH handle growth over 5 toggles", s4c_ok,
                f"handles {handles_before}->{handles_after} "
                f"counters {counters_before}->{counters_after} "
                f"query={'ok' if mon.query_handle is not None else 'None'}")

        # ---- M2: RTSS recognition (read-only) ------------------------------ #
        print("\n[spike] M2 checking RTSS recognition (shared memory)...")
        found, rtss_fps, rtss_name = (False, None, None)
        end = time.time() + args.rtss_timeout
        while time.time() < end:
            found, rtss_fps, rtss_name = read_rtss_entry(pid)
            # RTSS adds the PID entry before it has computed an FPS; wait for both.
            if found and rtss_fps is not None:
                break
            time.sleep(0.5)
        if found and rtss_fps is not None:
            m2_detail = f"name={rtss_name!r} fps={rtss_fps:.1f}"
        elif found:
            m2_detail = f"name={rtss_name!r} (recognized, no FPS yet)"
        else:
            m2_detail = "pid not in RTSS shared memory"
        res.add("M2a RTSS has hooked the fake game", found and rtss_fps is not None, m2_detail)
        if found and rtss_fps is not None:
            print(f"[spike] M2 RTSS reports fake-game FPS = {rtss_fps:.1f}")

        # fake game self-reported FPS (baseline, pre-limit)
        self_fps = None
        end = time.time() + 3.0
        while time.time() < end:
            self_fps = read_fps_file(fps_file)
            if self_fps:
                break
            time.sleep(0.3)
        print(f"[spike] M2 fake-game self-reported FPS (baseline) = {self_fps}")

        # ---- M3: RTSS limiting (opt-in) ------------------------------------ #
        if args.test_limit:
            print(f"\n[spike] M3 applying Global FramerateLimit={args.limit} (will restore)...")
            try:
                from core.rtss_functions import RTSSController

                class _RLogger:
                    def add_log(self, m):
                        print(f"    [rtss] {m}")

                ctrl = RTSSController(_RLogger())
                profiles_dir = os.path.join(ctrl.rtss_install_path, "Profiles")
                global_file = os.path.join(profiles_dir, "Global")

                raw = ctrl.get_profile_property("", "FramerateLimit", 4)
                orig_limit_int = int.from_bytes(raw, "little", signed=True) if raw is not None else 0
                orig_denom = 1
                orig_content = None
                if os.path.isfile(global_file):
                    orig_content = Path(global_file).read_text(encoding="utf-8")
                    for line in orig_content.splitlines():
                        if line.strip().startswith("LimitDenominator="):
                            try:
                                orig_denom = int(line.strip().split("=")[1])
                            except ValueError:
                                orig_denom = 1
                            break
                orig_limit = (orig_limit_int, orig_denom, orig_content)
                print(f"[spike] M3 original Global limit = {orig_limit_int} "
                      f"(denom={orig_denom}); captured for restore")

                ctrl.enable_limiter()
                ctrl.set_fractional_framerate("Global", args.limit)
                print(f"[spike] M3 limit applied; waiting for FPS to drop to ~{args.limit}...")

                limited = False
                end = time.time() + args.rtss_timeout
                last_self = None
                while time.time() < end:
                    last_self = read_fps_file(fps_file)
                    if last_self is not None and last_self <= args.limit * 1.3:
                        limited = True
                        break
                    time.sleep(0.5)
                rtss_found, rtss_limited_fps, _ = read_rtss_entry(pid)
                res.add("M3a fake-game FPS dropped to ~limit", limited,
                        f"self-reported={last_self} (limit {args.limit}, band<={args.limit * 1.3:.0f})"
                        + (f" | RTSS={rtss_limited_fps:.1f}" if rtss_found and rtss_limited_fps else ""))
            except Exception as e:  # noqa: BLE001 - report, don't crash the spike
                res.add("M3 RTSS limit test", False, f"error: {e!r}")
        else:
            print("\n[spike] M3 skipped (pass --test-limit to exercise RTSS limiting)")

        # ---- verify utilization drops after stopping the fake game --------- #
        print("\n[spike] stopping fake game and verifying 3D utilization drops...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        proc = None
        time.sleep(1.5)  # let PDH settle
        after = read_all_usage(mon, luids)
        after_usage = after.get(fake_luid, 0.0) if fake_luid else 0.0
        base_usage = base.get(fake_luid, 0.0) if fake_luid else 0.0
        res.add("M4 fake-game LUID utilization dropped after stop",
                fake_luid is not None and after_usage <= max(base_usage + 3.0, args.min_usage * 0.5),
                f"after={after_usage:.1f}% (baseline was {base_usage:.1f}%)")

    except Exception as e:  # noqa: BLE001 - surface as a failed spike
        res.add("spike", False, f"unhandled error: {e!r}")
    finally:
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # restore RTSS Global limit (M3)
        if orig_limit is not None:
            limit_int, denom, content = orig_limit
            try:
                from core.rtss_functions import RTSSController

                class _RLogger2:
                    def add_log(self, m):
                        pass

                ctrl = RTSSController(_RLogger2())
                if content is not None:
                    gf = os.path.join(ctrl.rtss_install_path, "Profiles", "Global")
                    tmpf = gf + ".tmp"
                    with open(tmpf, "w", encoding="utf-8") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmpf, gf)
                ctrl.set_profile_property("", "FramerateLimit", limit_int, update=False)
                ctrl.set_limit_denominator("Global", denom, update=False)
                ctrl.UpdateProfiles()
                print(f"\n[spike] restored Global FramerateLimit={limit_int} (denom={denom})")
            except Exception as e:  # noqa: BLE001
                print(f"\n[spike] WARNING: failed to restore RTSS Global limit: {e!r}")
        # stop the persistent PDH monitor
        running["v"] = False
        try:
            mon.cleanup()
        except Exception:
            pass

    ok = res.print_summary()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
