"""F4 regression tests: set_fractional_fps_direct must handle profile files
missing Limit=/LimitDenominator= lines (previously a NameError on
found_limit/found_denominator) and update values in place when present."""
from pathlib import Path


def _profile_file(rtss_stub, name="Global"):
    if name.lower() == "global":
        return Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    return Path(rtss_stub.rtss_install_path) / "Profiles" / f"{name}.cfg"


def test_direct_write_missing_both_keys_appends_both(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Resolution=1920x1080\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 59.94, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "Limit=5994\n" in content
    assert "LimitDenominator=100\n" in content
    assert rtss_stub.update_profiles_calls == 0


def test_direct_write_missing_one_key_appends_only_that_one(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 45.5, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "Limit=455\n" in content
    assert "LimitDenominator=10\n" in content
    assert content.count("LimitDenominator=") == 1


def test_direct_write_both_present_updates_in_place(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 60, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "Limit=60\n" in content
    assert "LimitDenominator=1\n" in content
    assert content.count("Limit=") == 1
    assert content.count("LimitDenominator=") == 1


def test_direct_write_calls_update_profiles_when_requested(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 144, update=True) is True
    assert rtss_stub.update_profiles_calls == 1


def test_direct_write_missing_profile_file_returns_false(rtss_stub):
    assert rtss_stub.set_fractional_fps_direct("NoSuchProfile", 60, update=False) is False
