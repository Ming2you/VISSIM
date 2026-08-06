"""Emit one Windows cross-process monotonic performance-counter reading."""

from __future__ import annotations

import sys
import time


def main() -> int:
    if sys.platform != "win32" or sys.version_info < (3, 10):
        return 1
    try:
        value = time.perf_counter_ns()
    except Exception:
        return 1
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return 1
    sys.stdout.buffer.write(f"python_perf_counter_ns={value}\n".encode("ascii"))
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
