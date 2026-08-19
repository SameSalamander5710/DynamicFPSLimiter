"""F6 regression tests: RTSS profile .cfg writes are atomic (tmp + os.replace) and
serialized (RLock), so a writer leaves no .tmp behind on success, concurrent writers
can't leave a truncated/partial profile, and UpdateProfiles fires per the update flag.

Runs against a real temp Profiles/ dir via the rtss_stub fixture (no DLL load).
"""
import re
import threading
from pathlib import Path


def _profile_file(rtss_stub, name="Global"):
    if name.lower() == "global":
        return Path(rtss_stub.rtss_install_path) / "Profiles" / "Global"
    return Path(rtss_stub.rtss_install_path) / "Profiles" / f"{name}.cfg"


def _profiles_dir(rtss_stub):
    return Path(rtss_stub.rtss_install_path) / "Profiles"


def _parse_limit(path):
    text = path.read_text(encoding="utf-8")
    limit = re.search(r"^Limit=(\d+)$", text, re.MULTILINE)
    denom = re.search(r"^LimitDenominator=(\d+)$", text, re.MULTILINE)
    return (int(limit.group(1)) if limit else None,
            int(denom.group(1)) if denom else None)


def test_direct_write_leaves_no_tmp(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    assert rtss_stub.set_fractional_fps_direct("Global", 59.94, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "Limit=5994\n" in content
    assert "LimitDenominator=100\n" in content
    assert list(_profiles_dir(rtss_stub).glob("*.tmp")) == []


def test_denominator_write_leaves_no_tmp(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\n", encoding="utf-8")

    assert rtss_stub.set_limit_denominator("Global", 100, update=False) is True

    content = path.read_text(encoding="utf-8")
    assert "LimitDenominator=100\n" in content
    assert list(_profiles_dir(rtss_stub).glob("*.tmp")) == []


def test_fractional_framerate_leaves_no_tmp(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    limit, denom = rtss_stub.set_fractional_framerate("Global", 59.94, update=False)
    assert (limit, denom) == (5994, 100)

    # The nested set_limit_denominator wrote the denominator to the file atomically.
    assert "LimitDenominator=100\n" in path.read_text(encoding="utf-8")
    assert list(_profiles_dir(rtss_stub).glob("*.tmp")) == []


def test_concurrent_writers_leave_valid_file(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    errors = []

    def _worker(framerate):
        try:
            rtss_stub.set_fractional_fps_direct("Global", framerate, update=False)
        except Exception as e:  # pragma: no cover - defensive
            errors.append(e)

    a = threading.Thread(target=_worker, args=(60,))
    b = threading.Thread(target=_worker, args=(59.94,))
    a.start()
    b.start()
    a.join()
    b.join()

    assert errors == []
    assert list(_profiles_dir(rtss_stub).glob("*.tmp")) == []

    # The lock makes each read-modify-write atomic, so the final file is a consistent
    # (limit, denominator) pair from exactly one of the two writers — never a mix.
    limit, denom = _parse_limit(path)
    assert (limit, denom) in {(60, 1), (5994, 100)}


def test_update_profiles_called_per_flag(rtss_stub):
    path = _profile_file(rtss_stub)
    path.write_text("Limit=30\nLimitDenominator=1\n", encoding="utf-8")

    rtss_stub.set_limit_denominator("Global", 10, update=False)
    assert rtss_stub.update_profiles_calls == 0

    rtss_stub.set_limit_denominator("Global", 10, update=True)
    assert rtss_stub.update_profiles_calls == 1

    rtss_stub.set_fractional_fps_direct("Global", 144, update=True)
    assert rtss_stub.update_profiles_calls == 2
