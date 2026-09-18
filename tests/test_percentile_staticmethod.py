"""L10 regression tests: calculate_percentile is a true @staticmethod.

Both CPUUsageMonitor.calculate_percentile and GPUUsageMonitor.calculate_percentile
must be callable directly on the class, without constructing an instance and
without Python implicitly binding ``self``. Importing gpu_monitor pulls in
PDH/ctypes (Windows-only), matching the pattern used by
tests/test_gpu_monitor_handles.py.
"""
import pytest

from core.cpu_monitor import CPUUsageMonitor
from core.gpu_monitor import GPUUsageMonitor

DATA = [5, 1, 3, 2, 4]
PERCENTILE = 80
EXPECTED = pytest.approx(4.2)


@pytest.mark.parametrize(
    "cls",
    [CPUUsageMonitor, GPUUsageMonitor],
    ids=["cpu", "gpu"],
)
def test_calculate_percentile_is_a_real_staticmethod(cls):
    assert isinstance(cls.__dict__["calculate_percentile"], staticmethod)


@pytest.mark.parametrize(
    "cls",
    [CPUUsageMonitor, GPUUsageMonitor],
    ids=["cpu", "gpu"],
)
def test_calculate_percentile_called_on_class_without_instance(cls):
    result = cls.calculate_percentile(DATA, PERCENTILE)
    assert result == EXPECTED