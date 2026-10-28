"""Run several steps of one C1 tool in order, each as its own `python -B <tool> <step>` child (stop at the first
non-zero exit).  python -B c1_chain_run.py <tool.py> <step> [<step> ...]"""
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402

tool = Path(__file__).resolve().parent / sys.argv[1]
LOG = C.make_logger(C.TC1 / 'out' / 'logs' / 'c1_chain_run.log')
C.set_below_normal()
for step in sys.argv[2:]:
    t0 = time.time()
    rc = subprocess.run([C.PY, '-B', str(tool), step], creationflags=C.BELOW_NORMAL).returncode
    LOG('CHAIN %s %s exit=%s sec=%.0f' % (tool.name, step, rc, time.time() - t0))
    if rc != 0:
        LOG('CHAIN_STOP at %s' % step)
        raise SystemExit(rc)
LOG('CHAIN_DONE %s' % ' '.join(sys.argv[2:]))
