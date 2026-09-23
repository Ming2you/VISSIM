r"""Measure what the three edits actually bought, on this box.

(a) the marshal cache: transform+compile the instrumented module set cold vs warm
(b) Trace.branch and maximum(): per-call, old body vs new body

End-to-end decision time is NOT measurable here -- the archived request.pickle
predates the plant merge -- so these are the component numbers only.
"""
import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(r'D:\VISSIM-merge\sim3')
SCRATCH = Path('C:/Users/TRLAB/AppData/Local/Temp/claude/'
               'C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad')
sys.path[:0] = [str(ROOT), r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps\sdmpc',
                r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps\sdmpc-numba']


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new = load(ROOT / 'evaluation' / 'controllers' / 'sdmpc_tangent_reverse.py', 'rev_new')
old = load(SCRATCH / 'pre_squeeze_reverse.py', 'rev_old')
rt = load(ROOT / 'evaluation' / 'controllers' / 'sdmpc_tangent_runtime.py', 'rt_new')

REPS = 4


def best(thunk, reps=REPS):
    return min(thunk() for _ in range(reps))


# ----------------------------------------------------------------- (a) cache
FILES = sorted((ROOT / 'evaluation' / 'controllers').glob('*.py'))
SOURCES = [(str(p), p.read_bytes()) for p in FILES]
import hashlib


def pipeline(use_cache):
    def run():
        t0 = time.perf_counter()
        for name, src in SOURCES:
            digest = hashlib.sha256(src).hexdigest()
            if use_cache:
                rt._transformed_code(name, src, digest)
            else:
                import ast
                tree = rt.Transform().visit(ast.parse(src, filename=name))
                compile(ast.fix_missing_locations(tree), name, 'exec')
        return time.perf_counter() - t0
    return run


cold = best(pipeline(False))
pipeline(True)()                       # populate
warm = best(pipeline(True))
print('(a) AST transform+compile over %d modules' % len(SOURCES))
print('    no cache : %.3f s' % cold)
print('    cached   : %.3f s   -> saves %.3f s per worker spawn' % (warm, cold - warm))

# ----------------------------------------------------------------- (b) per-call
N = 200000


def time_branch(mod, kind):
    mod.FAST_PRIMITIVES = True
    trace = mod.Trace([.1], track_stencils=False)
    a = mod.Dual(2., {0: 1.}, trace)
    b = mod.Dual(2. if kind == 'tie' else 3., {0: 1.}, trace)
    branch = trace.branch
    discrete = kind == 'discrete'

    def run():
        t0 = time.perf_counter()
        for _ in range(N):
            branch(a, b, discrete=discrete)
        return (time.perf_counter() - t0) / N * 1e9
    return best(run)


def time_max(mod):
    mod.FAST_PRIMITIVES = True
    trace = mod.Trace([.1], track_stencils=False)
    a = mod.Dual(2., {0: 1.}, trace)
    b = mod.Dual(3., {0: 1.}, trace)
    f = mod.maximum

    def run():
        t0 = time.perf_counter()
        for _ in range(N):
            f(a, b)
        return (time.perf_counter() - t0) / N * 1e9
    return best(run)


print('\n(b) per call, nanoseconds (min of %d x %d)' % (REPS, N))
rows = []
for kind in ('plain', 'tie', 'discrete'):
    o, n = time_branch(old, kind), time_branch(new, kind)
    rows.append(('branch ' + kind, o, n))
o, n = time_max(old), time_max(new)
rows.append(('maximum(Dual,Dual)', o, n))
for label, o, n in rows:
    print('    %-22s old %7.1f   new %7.1f   saves %6.1f  (%+.1f%%)'
          % (label, o, n, o - n, -100. * (o - n) / o))

# ------------------------------------------------------- projected per rollout
# Comparison mix recorded in decision_v1/result.json for one taped rollout.
MIX = {'branch plain': 7630347, 'branch tie': 381946, 'branch discrete': 856909}
saved = sum(MIX[k] * (o - n) for k, o, n in rows if k in MIX) / 1e9
mx = next((o - n) for k, o, n in rows if k == 'maximum(Dual,Dual)')
print('\n    branch mix over one taped rollout (%s comparisons): saves %.2f s'
      % (format(sum(MIX.values()), ','), saved))
print('    if every non-discrete comparison is a 2-arg max/min, the max/min')
print('    entry adds up to %.2f s more per taped rollout' % (8012293 * mx / 1e9))
