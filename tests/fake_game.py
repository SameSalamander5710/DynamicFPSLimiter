"""Fake 3D game: a minimal DearPyGui window that renders continuously via D3D11.

The app's GPU monitoring reads the PDH "GPU Engine" (``engtype_3D``) counter and
RTSS limits frame rate by hooking a D3D swap chain's ``Present``. A real commercial
game is the natural workload for both, but it is not scriptable. DearPyGui is a
D3D11 application, so a DPG window that renders every frame:

  * drives the GPU 3D engine (shows up in PDH ``engtype_3D``), and
  * is detected by RTSS as a DirectX app whose FPS can be limited.

This makes it a controllable stand-in for the "fake 3D game" in automated testing.
It is launched as a *separate process* so it has its own PID, a real window, and its
own D3D device -- exactly what PDH and RTSS observe for a game.

Run:
    python tests/fake_game.py --title "DFL Fake Game" --ready-file <path>
        [--width 1024] [--height 768] [--load 8] [--fps-file <path>] [--duration 0]

The process writes ``--ready-file`` (JSON) once the first frame has been presented,
then keeps rendering until the window is closed, ``--duration`` elapses, or it is
killed. It is intentionally not a pytest module (no ``test_`` prefix).
"""
import argparse
import json
import os
import time


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Fake 3D game (DearPyGui D3D11 render loop)")
    ap.add_argument("--title", default="DFL Fake Game", help="window title (identifies the process)")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=768)
    ap.add_argument("--load", type=int, default=8,
                    help="number of full-screen filled quads drawn per frame (3D engine load)")
    ap.add_argument("--ready-file", default=None, help="write JSON readiness signal here after first frame")
    ap.add_argument("--fps-file", default=None, help="write measured FPS here every ~0.5s")
    ap.add_argument("--duration", type=float, default=0.0,
                    help="auto-exit after N seconds (0 = run until window closed/killed)")
    ap.add_argument("--no-vsync", action="store_true", help="disable vsync (uncapped, heavier load)")
    return ap


def main() -> int:
    args = build_arg_parser().parse_args()

    import dearpygui.dearpygui as dpg

    pid = os.getpid()
    print(f"[fake_game] starting pid={pid} title={args.title!r} "
          f"{args.width}x{args.height} load={args.load} vsync={not args.no_vsync}", flush=True)

    dpg.create_context()
    dpg.create_viewport(title=args.title, width=args.width, height=args.height,
                        resizable=True, decorated=True)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_viewport_vsync(not args.no_vsync)

    # Content that guarantees per-frame rasterization so the 3D engine is clearly busy.
    # DPG's immediate-mode renderer redraws the viewport (and this drawlist) every frame.
    with dpg.window(label="FakeGame", tag="fg_window"):
        dpg.add_text("DFL Fake Game - rendering (close to stop)", wrap=600)
        dpg.add_progress_bar(default_value=0.5, width=args.width - 40)
        dl = dpg.add_drawlist(parent="fg_window", width=args.width, height=args.height)
        for i in range(max(1, args.load)):
            # Slightly inset, slightly differently tinted full-screen quads (overdraw = load).
            inset = (i % 5) * 8
            tint = (40 + i * 12) % 200
            dpg.draw_rectangle((inset, inset), (args.width - inset, args.height - inset),
                               fill=(tint, 60, 90, 255), parent=dl)

    # FPS measurement (self-reported; RTSS shared memory is the authoritative source).
    fps_state = {"frames": 0, "t0": time.time(), "last_write": 0.0}

    def measure_fps() -> None:
        fps_state["frames"] += 1
        if not args.fps_file:
            return
        now = time.time()
        if now - fps_state["last_write"] < 0.5:
            return
        span = now - fps_state["t0"]
        fps = fps_state["frames"] / span if span > 0 else 0.0
        try:
            with open(args.fps_file, "w", encoding="utf-8") as f:
                json.dump({"fps": round(fps, 2), "frames": fps_state["frames"], "t": now}, f)
        except OSError:
            pass
        fps_state["frames"] = 0
        fps_state["t0"] = now
        fps_state["last_write"] = now

    def write_ready() -> None:
        if not args.ready_file:
            return
        try:
            with open(args.ready_file, "w", encoding="utf-8") as f:
                json.dump({"ready": True, "pid": pid, "title": args.title,
                           "width": args.width, "height": args.height,
                           "load": args.load, "started": time.time()}, f)
            print(f"[fake_game] ready pid={pid}", flush=True)
        except OSError as e:
            print(f"[fake_game] failed to write ready-file: {e}", flush=True)

    start = time.time()
    first_frame = True
    try:
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            measure_fps()
            if first_frame:
                first_frame = False
                write_ready()
            if args.duration and (time.time() - start) >= args.duration:
                dpg.stop_dearpygui()
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            dpg.destroy_context()
        except Exception:
            pass
        print(f"[fake_game] exited pid={pid}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
