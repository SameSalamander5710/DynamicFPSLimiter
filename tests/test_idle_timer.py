"""Check Windows idle timing across the 32-bit tick counter boundaries."""

import ctypes
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.idle_timer import get_idle_duration


class IdleTimerTests(unittest.TestCase):
    def test_elapsed_time_survives_signed_ticks_and_wraparound(self):
        for uptime, elapsed in (
            (100_000, 1_000),
            (100_000, 30_000),
            ((1 << 31) - 500, 1_000),
            ((1 << 31) + 500, 1_000),
            ((1 << 31) + 5_000, 1_000),
            ((1 << 32) + 500, 1_000),
            ((1 << 32) + 5_000, 1_000),
        ):
            with self.subTest(uptime=uptime, elapsed=elapsed):
                def last_input(pointer):
                    info = pointer._obj
                    self.assertEqual(info.cbSize, ctypes.sizeof(info))
                    info.dwTime = (uptime - elapsed) & 0xFFFFFFFF
                    return 1

                # ctypes uses a signed int return type unless told otherwise.
                ticks = Mock(return_value=ctypes.c_int(uptime).value)
                windll = SimpleNamespace(
                    user32=SimpleNamespace(GetLastInputInfo=last_input),
                    kernel32=SimpleNamespace(GetTickCount=ticks, GetTickCount64=ticks),
                )
                with patch.object(ctypes, "windll", windll, create=True):
                    self.assertEqual(get_idle_duration(), elapsed / 1000)


if __name__ == "__main__":
    unittest.main()
