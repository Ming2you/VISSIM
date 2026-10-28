"""Run a pinned read-only scanner by sha256 (PRE_VP section 9): python -B vp_pinned.py <sha256> <script.py> <args...>
Refuses when the script bytes differ from the pinned sha; otherwise runs it as __main__ with the given argv."""
import hashlib
import runpy
import sys

sys.dont_write_bytecode = True
want, script = sys.argv[1], sys.argv[2]
got = hashlib.sha256(open(script, 'rb').read()).hexdigest()
if got != want:
    raise SystemExit('PINNED_SHA_MISMATCH %s %s != %s' % (script, got, want))
sys.argv = [script] + sys.argv[3:]
runpy.run_path(script, run_name='__main__')
