# Trace wrapper: run the codex adapter as __main__ unchanged, logging file opens / dir listings /
# failed stats (missing files) of THIS process only (worker subprocesses are not traced).
# Adapter semantics are untouched: os.stat is wrapped only to log FileNotFoundError and re-raise it.
import sys
import runpy
import threading
import os as _os

log_path = sys.argv[1]
adapter = sys.argv[2]
rest = sys.argv[3:]
_log = open(log_path, 'w', encoding='utf-8', buffering=1)
_lock = threading.Lock()
_seen = set()
TAB = chr(9)
NL = chr(10)


def _write(kind, path):
    key = (path, kind)
    if key in _seen:
        return
    _seen.add(key)
    with _lock:
        _log.write(kind + TAB + path + NL)


def _hook(event, args):
    try:
        if event == 'open':
            path, mode = args[0], args[1]
            if isinstance(path, str):
                _write(str(mode), path)
        elif event in ('os.listdir', 'os.scandir'):
            if isinstance(args[0], str):
                _write(event, args[0])
        elif event == 'subprocess.Popen':
            _write('popen', str(args[1])[:400])
    except Exception:
        pass


sys.addaudithook(_hook)
_orig_stat = _os.stat


def _stat(path, *a, **k):
    try:
        return _orig_stat(path, *a, **k)
    except FileNotFoundError:
        try:
            _write('stat_missing', _os.fspath(path) if not isinstance(path, int) else str(path))
        except Exception:
            pass
        raise


_os.stat = _stat
sys.argv = [adapter] + rest
runpy.run_path(adapter, run_name='__main__')
