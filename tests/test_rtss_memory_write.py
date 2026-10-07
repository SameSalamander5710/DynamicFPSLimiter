"""set_frameratelimit_memory_write: target resolution + value parsing.

profile_name is used directly as the process name; "Global" means every
hooked process that has no specific RTSS profile.
"""
from decimal import Decimal

from conftest import requires_win32
from core import rtss_memory_write as mw


def test_parse_fps_accepts_number_types():
    assert mw.parse_fps(Decimal("42.32")) == (4232, 100)
    assert mw.parse_fps(60) == (60, 1)
    assert mw.parse_fps(59.94) == (5994, 100)


def test_resolve_targets_matches_profile_name_directly():
    hooked = [(101, "mygame.exe"), (102, "other.exe")]
    assert mw.resolve_targets(hooked, "mygame.exe") == [(101, "mygame.exe")]


def test_resolve_targets_global_skips_profiled_processes():
    hooked = [(101, "mygame.exe"), (102, "random.exe")]
    assert mw.resolve_targets(hooked, "Global", {"mygame.exe"}) == [
        (102, "random.exe")
    ]


@requires_win32
def test_list_rtss_profile_names(tmp_path, monkeypatch):
    profiles = tmp_path / "Profiles"
    profiles.mkdir()
    (profiles / "mygame.exe.cfg").write_text("Limit=60\n", encoding="utf-8")
    (profiles / "Other.exe.cfg").write_text("Limit=60\n", encoding="utf-8")
    (profiles / "Global").write_text("Limit=0\n", encoding="utf-8")
    monkeypatch.setattr(mw, "get_rtss_install_path", lambda: str(tmp_path))
    assert mw.list_rtss_profile_names() == {"mygame.exe", "other.exe"}


def test_set_frameratelimit_writes_only_matching_process(monkeypatch, stub_logger):
    monkeypatch.setattr(
        mw, "hooked_pids",
        lambda: [(101, "mygame.exe"), (102, "other.exe")])
    written = []

    def fake_set_fps_limit(pid, num, den):
        written.append((pid, num, den))
        return (59.94, num / den)

    monkeypatch.setattr(mw, "set_fps_limit", fake_set_fps_limit)

    result = mw.set_frameratelimit_memory_write(
        "mygame.exe", Decimal("59.94"), stub_logger)

    assert result == (5994, 100)
    assert written == [(101, 5994, 100)]
    assert stub_logger.messages


def test_set_frameratelimit_global_excludes_profiled(monkeypatch, stub_logger):
    monkeypatch.setattr(
        mw, "hooked_pids",
        lambda: [(101, "mygame.exe"), (102, "random.exe")])
    monkeypatch.setattr(mw, "list_rtss_profile_names", lambda: {"mygame.exe"})
    written = []
    monkeypatch.setattr(
        mw, "set_fps_limit",
        lambda pid, num, den: written.append((pid, num, den)) or (0.0, 60.0))

    result = mw.set_frameratelimit_memory_write("Global", 60, stub_logger)

    assert result == (60, 1)
    assert written == [(102, 60, 1)]


def test_set_frameratelimit_no_process_logs_and_returns_none(
        monkeypatch, stub_logger):
    monkeypatch.setattr(mw, "hooked_pids", lambda: [(101, "mygame.exe")])

    result = mw.set_frameratelimit_memory_write(
        "other.exe", 60, stub_logger)

    assert result is None
    assert any("no hooked process" in m for m in stub_logger.messages)
