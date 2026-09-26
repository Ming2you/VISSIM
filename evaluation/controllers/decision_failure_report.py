"""Bounded failure report for a decision process whose stdio may never be drained.

run_real_world_stackelberg_controller.vbs RunCapture3 (and RunCapture3Timeout)
connect the adapter's stdout/stderr to anonymous pipes and read them only after
the process has exited. A write larger than the free pipe buffer (4,096 B on
Windows) then blocks forever, so the process never exits. An uncaught
exception's traceback is such a write: at decision 7650 of sdmpc31_v3b_s31d a
tangent worker failed, the adapter reached sys.excepthook 31 s later with a
6,860 B traceback behind 406 B of warnings, blocked inside it, and the run sat
idle until the 2,400 s watchdog killed it instead of failing the decision.

run() leaves a successful decision untouched. On an exception it writes the
complete traceback (a worker's traceback travels in the exception message) to
<out-action-json stem>.error.txt, prints one line of at most SUMMARY_LIMIT_BYTES
to stderr naming the error and that file, and exits 1, the exit status of an
uncaught exception. The runner's DECISION_EXIT_NONZERO / fail-fast path then
runs at once. SystemExit (argparse usage errors, explicit exits) passes through.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path

SUMMARY_LIMIT_BYTES = 1024
FAILURE_EXIT_CODE = 1
OUTPUT_OPTION = '--out-action-json'


def report_path(argv, option=OUTPUT_OPTION):
    """<stem>.error.txt beside the action JSON named on the command line, else None."""
    value = None
    for index, arg in enumerate(argv):
        if arg == option and index+1 < len(argv):
            value = argv[index+1]
        elif arg.startswith(option+'='):
            value = arg.split('=', 1)[1]
    return Path(value).with_suffix('.error.txt') if value else None


def _clip(text, limit):
    data = text.encode('utf-8', 'replace')
    if len(data) <= limit:
        return text
    return data[:max(0, limit-3)].decode('utf-8', 'ignore')+'...'


def _write_report(text, preferred):
    fallback = Path(tempfile.gettempdir())/f'decision_failure_{os.getpid()}_{time.time_ns()}.txt'
    for candidate in ([preferred] if preferred is not None else [])+[fallback]:
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_text(text, encoding='utf-8', errors='replace')
            return candidate
        except OSError:
            continue
    return None


def summary_line(exc, full_text, path):
    """One stderr line: type, first message line, root error line, report file."""
    try:
        message = str(exc)
    except Exception:  # noqa: BLE001 - a broken __str__ must not hide the failure
        message = '<unprintable exception message>'
    first = next((line.strip() for line in message.splitlines() if line.strip()), '')
    root = next((line.strip() for line in reversed(full_text.splitlines()) if line.strip()), '')
    line = (f'DECISION_FAILED type={type(exc).__name__} message={_clip(first, 240)} '
            f'root_error={_clip(root, 400)} traceback={path if path is not None else "<unwritable>"}')
    return _clip(' '.join(line.split()), SUMMARY_LIMIT_BYTES-1)+'\n'


def _emit(line):
    try:
        sys.stderr.flush()
        buffer = getattr(sys.stderr, 'buffer', None)
        if buffer is not None:
            buffer.write(line.encode('utf-8', 'replace'))
            buffer.flush()
        else:
            sys.stderr.write(line)
            sys.stderr.flush()
    except Exception:  # noqa: BLE001 - the exit status still reports the failure
        pass


def run(entry, argv=None):
    """Call entry(); on failure report it boundedly and exit FAILURE_EXIT_CODE."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        return entry()
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - KeyboardInterrupt is a failed decision too
        full = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        try:
            preferred = report_path(argv)
        except ValueError:  # e.g. an --out-action-json without a file name
            preferred = None
        path = _write_report(full, preferred)
        _emit(summary_line(exc, full, path))
        raise SystemExit(FAILURE_EXIT_CODE) from None
