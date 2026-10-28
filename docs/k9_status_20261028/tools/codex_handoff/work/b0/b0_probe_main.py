# B0 probe wrapper: run the codex adapter as __main__ unchanged, logging file opens / listings / missing stats
# of THIS process (workers are not traced). Mode 'configure' stops right after the adapter's configure steps
# (configure_runtime -> sdmpc.configure -> sdmpc.install_cost_ownership), before any prediction or optimisation,
# by wrapping sdmpc.install_cost_ownership: it calls the original, writes a marker line and raises SystemExit(0).
# Mode 'full' only logs (the decision runs to the end).  Adapter semantics are untouched in both modes.
# usage: python -B b0_probe_main.py <open_log.tsv> <configure|full> <adapter.py> <adapter args...>
import sys
import runpy
import threading
import os as _os

log_path = sys.argv[1]
mode = sys.argv[2]
adapter = sys.argv[3]
rest = sys.argv[4:]
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
            path, m = args[0], args[1]
            if isinstance(path, str):
                _write(str(m), path)
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

if mode == 'configure':
    from evaluation.controllers import sdmpc as _sdmpc
    _orig_ico = _sdmpc.install_cost_ownership

    def _probe_ico(*a, **k):
        out = _orig_ico(*a, **k)
        _write('B0_PROBE', 'CONFIGURE_DONE')
        sys.stdout.write('B0_PROBE_CONFIGURE_DONE' + NL)
        sys.stdout.flush()
        raise SystemExit(0)

    _sdmpc.install_cost_ownership = _probe_ico
elif mode != 'full':
    raise SystemExit('mode must be configure or full')

sys.argv = [adapter] + rest
runpy.run_path(adapter, run_name='__main__')
