"""Regression guard: no debug ``print()`` calls left in shipped core code.

A pre-release audit found ``print()`` statements in runtime paths
(viewport dragging, LHM reading updates, DLL-load info, first-launch error).
Those flood the console and add useless I/O on monitoring threads. Anything
under ``if __name__ == "__main__":`` is a manual-dev harness and is exempt.
"""
import re
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "core"


def test_no_active_prints_in_shipped_core_modules():
    offenders = []
    for path in SRC_DIR.glob("*.py"):
        # video2gif.py is a standalone dev CLI script (gitignored, not part of
        # the app); its prints are its CLI output, so it is exempt.
        if path.name == "video2gif.py":
            continue
        text = path.read_text(encoding="utf-8")
        # Keep only the shipped (module) portion of the file.
        module_src = text.split('if __name__ == "__main__":', 1)[0]
        for lineno, line in enumerate(module_src.splitlines(), start=1):
            if re.match(r"^\s*print\(", line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "active print() calls in shipped core code:\n" + "\n".join(offenders)