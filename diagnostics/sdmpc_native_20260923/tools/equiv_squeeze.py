r"""Randomised equivalence check for the B/C reverse-AD edits.

Loads the pre-squeeze sdmpc_tangent_reverse.py beside the live one and drives
both with identical operands, comparing the operand actually selected and every
comparison counter the receipt is built from. The unit suite exercises these
paths, but not across all four operand kinds (reverse Dual, bare forward Dual,
float, int) nor both settings of FAST_PRIMITIVES, which is where the two
predicates inside branch() could have diverged.

Usage:  python equiv_squeeze.py [cases]
"""
import importlib.util
import random
import sys
from pathlib import Path

ROOT = Path(r'D:\VISSIM-merge\sim3')
OLD = Path('C:/Users/TRLAB/AppData/Local/Temp/claude/'
           'C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/'
           'scratchpad/pre_squeeze_reverse.py')
sys.path[:0] = [str(ROOT), r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps\sdmpc',
                r'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps\sdmpc-numba']


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


new = load(ROOT / 'evaluation' / 'controllers' / 'sdmpc_tangent_reverse.py', 'rev_new')
old = load(OLD, 'rev_old')
forward = new.forward
assert old.forward is forward, 'both copies must share one forward Dual module'

KINDS = ('reverse', 'forward', 'float', 'int')


def operand(mod, kind, value, trace):
    if kind == 'reverse':
        return mod.Dual(value, {0: 1.}, trace)
    if kind == 'forward':
        # A forward Dual that is NOT a reverse Dual: the case where branch()'s two
        # predicates disagree, and so the one the inlined body had to preserve.
        # It still carries the live trace, as any real operand would.
        return forward.Dual(value, {}, trace)
    if kind == 'int':
        return int(value)
    return float(value)


def snapshot(trace):
    return (dict(trace.counts), trace.exact_support, trace.discrete_support)


def run(mod, kinds, values, op, fast, discrete):
    mod.FAST_PRIMITIVES = fast
    trace = mod.Trace([.1], track_stencils=False)
    operands = [operand(mod, k, v, trace) for k, v in zip(kinds, values)]
    if op == 'branch':
        trace.branch(operands[0], operands[1], discrete=discrete)
        return ('branch', snapshot(trace))
    function = mod.maximum if op == 'max' else mod.minimum
    if op in ('max', 'min'):
        chosen = function(operands[0], operands[1])
    tag = next((i for i, o in enumerate(operands) if o is chosen), -1)
    return (tag, float(chosen.value if isinstance(chosen, forward.Dual) else chosen), snapshot(trace))


def sequence(mod, values, op, fast):
    """The non-two-argument shapes my signature change also has to preserve."""
    mod.FAST_PRIMITIVES = fast
    trace = mod.Trace([.1], track_stencils=False)
    xs = [mod.Dual(v, {0: 1.}, trace) for v in values]
    function = mod.maximum if op == 'max' else mod.minimum

    def attempt(thunk):
        """Raising is part of the contract here -- a one-element *args call is a
        TypeError in the shipped code, and the new signature must reproduce it."""
        try:
            return ('ok', float(thunk().value))
        except Exception as exc:
            return ('raised', type(exc).__name__, str(exc))

    results = [attempt(lambda: function(xs)), attempt(lambda: function(*xs)),
               attempt(lambda: function(xs, key=lambda d: -d.value))]
    if len(values) >= 3:
        results.append(attempt(lambda: function(xs[0], xs[1], xs[2])))
    return (results, snapshot(trace))


def main():
    cases = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    rng = random.Random(20260923)
    bad = 0
    for n in range(cases):
        kinds = (rng.choice(KINDS), rng.choice(KINDS))
        # Ties matter most: draw from a small grid so equal primals are common.
        values = (rng.choice([1., 2., 3., -1., 0., 2.5]), rng.choice([1., 2., 3., -1., 0., 2.5]))
        for op in ('max', 'min', 'branch'):
            for fast in (True, False):
                for discrete in ((False, True) if op == 'branch' else (False,)):
                    a = run(old, kinds, values, op, fast, discrete)
                    b = run(new, kinds, values, op, fast, discrete)
                    if a != b:
                        bad += 1
                        if bad <= 5:
                            print('MISMATCH kinds=%s values=%s op=%s fast=%s discrete=%s\n  old=%s\n  new=%s'
                                  % (kinds, values, op, fast, discrete, a, b))
    for op in ('max', 'min'):
        for fast in (True, False):
            for size in (1, 2, 3, 5):
                values = [rng.choice([1., 2., 3., -1., 0.]) for _ in range(size)]
                a, b = sequence(old, values, op, fast), sequence(new, values, op, fast)
                if a != b:
                    bad += 1
                    print('SEQ MISMATCH op=%s fast=%s values=%s\n  old=%s\n  new=%s' % (op, fast, values, a, b))
    print('cases=%d mismatches=%d' % (cases, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
