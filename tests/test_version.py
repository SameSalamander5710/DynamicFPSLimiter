"""Version single-source-of-truth tests.

Bump the version in exactly one place — ``src/core/version.py`` — and these
tests guarantee every derived artifact stays consistent:

- ``src/metadata/version.txt`` (the PyInstaller ``--version-file`` resource)
  matches what the build regenerates (``src/__main__.py --build``).
- the committed ``version.txt`` actually parses through PyInstaller's own
  deserializer, so the exe version metadata can never be broken.
- ``app.py`` shows the version only via ``display_version()`` (nothing
  hardcoded).
"""
import subprocess
import sys
from pathlib import Path

import pytest

from core.version import VERSION, display_version, full_version, version_file_text

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
VERSION_TXT = SRC_DIR / "metadata" / "version.txt"
APP = SRC_DIR / "core" / "app.py"


def test_version_is_a_four_part_tuple():
    assert len(VERSION) == 4
    assert all(isinstance(part, int) and part >= 0 for part in VERSION)


def test_version_strings_follow_the_version():
    assert full_version() == ".".join(str(p) for p in VERSION)
    assert display_version() == "v" + ".".join(str(p) for p in VERSION[:3])


def test_version_txt_in_sync_with_single_source():
    assert VERSION_TXT.read_text(encoding="utf-8") == version_file_text()


def test_version_txt_contains_no_other_version():
    text = version_file_text()
    assert text.count(full_version()) >= 2  # FileVersion + ProductVersion
    assert f"filevers={VERSION}" in text
    assert f"prodvers={VERSION}" in text


def test_app_shows_version_only_via_display_version():
    src = APP.read_text(encoding="utf-8")
    assert "from core.version import display_version" in src
    assert "display_version()" in src
    assert 'v5.0.0' not in src


@pytest.mark.win32
def test_version_txt_deserializes_with_pyinstaller():
    code = (
        "import sys\n"
        "from PyInstaller.utils.win32.versioninfo import "
        "load_version_info_from_text_file\n"
        "info = load_version_info_from_text_file(sys.argv[1])\n"
        "print(info.ffi.fileVersionMS, info.ffi.productVersionMS)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(VERSION_TXT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    ms = (VERSION[0] << 16) | VERSION[1]
    file_ms, product_ms = (int(v) for v in proc.stdout.split()[:2])
    assert file_ms == ms and product_ms == ms