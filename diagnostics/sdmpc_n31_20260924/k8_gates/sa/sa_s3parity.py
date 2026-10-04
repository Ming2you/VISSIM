"""K8 amendment 10: scalar / tangent structure comparison that sets aside the K8-2 S3 ledger records (harness only).

    import sa_s3parity as S3P                       # BEFORE the tangent finder is installed: this module runs untransformed
    log = S3P.install(cao_module)                    # call-site instrument of the K8-2 S3 ledger gate (this process only)
    error = S3P.compare(scalar, tangent, log, comparator=state_error)    # the runtime comparator, unchanged
    ok, why = S3P.verdict(log.report(), error)

Binding text: K8_PREDECLARATION_AMENDMENT_10.md (sha256 d7bcdc9e...) decisions 1-3.  Users: T20
(diagnostics/sdmpc_n31_20260924/tests/stopline_tangent_probe.py parity) and the G-EB-11(e) non-surrogate AD state
comparison (sa_worker.py mode ad_full routes evaluation.controllers.sdmpc_tangent_state.state_error through compare()
in its own process).  The runtime comparator and every file under evaluation/ stay unchanged: compare() calls the
comparator as it is; only on its ValueError does it set aside the excluded keys in place, call it again on the same
objects and put the keys back (same values, same order) before returning or raising.

Rule.  A record is set aside only when ALL hold:
  (1) it is a key of a ledger `flow_counts` (attribute of a ModelAreaLedger anywhere in the compared states, or a
      declared top-level snapshot key such as T20's 'flow_counts' = dict(get_ledger(st).flow_counts)) that is present
      in the tangent run and absent from the paired scalar flow_counts;
  (2) its tangent value has primal exactly 0.0;
  (3) the key was created by a ModelAreaLedger.transfer call that only the K8-2 S3 gate admits: the amount has primal
      exactly 0.0 AND carries tape (sdmpc_dual.has_tape), i.e. a call the K8-1 test `count == 0` dropped and the K8-2
      test `count == 0 and not has_tape(count)` records;
  (4) that call was not SA-created (no frame of evaluation/controllers/stopline_approach.py was active) and no
      SA-created S3 call created the same key.
Nothing else is set aside, so the unchanged comparator raises (or returns its error) exactly as without this module:
another tangent-only key (another writer, nonzero primal, SA-created), a scalar-only key, a stocks key, a sequence
length, ... all FAIL.  SA must create none: every S3-admitted transfer call made with an SA frame on the stack is
counted (`sa_created`) and verdict() fails on any, whether or not it created a new key.

Transfer records of the same ledger (`_response['transfers']` rows, packed or compact rows): the runtime comparator
already compares them grouped by (stage, start, end, source, target, route_key) with an absent group read as 0, so a
zero-primal tangent-only row compares equal and nothing is set aside; the rows the S3-admitted calls appended are
counted (`s3_rows`).  The captured-ledger event check (event_count - captured rows) is unchanged by those calls (one
event, one row).  A ledger without response capture compares event_count as a field: an S3 call there stays a
numeric difference (FAIL), as declared ("anything else still FAILs").

Site identification (method: call-site instrumentation, amendment 10 decision 3).  The six K8-2 S3 sites are anchored
by their exact K8-2 text (the K8-2 -> K8-1 table of diagnostics/test_k8_s3_has_transfer.py, each text exactly once)
and reported with the amendment's K8-2 line (5eef6be) and this tree's line.  Only one of them writes ledger records:
the CAO ModelAreaLedger.transfer gate.  PRB-bd :307/:332/:370 append ramp packets and AFA :247/:393 shape freeway
values; their zero-primal taped amounts reach a ledger only through a later transfer call, which passes the CAO gate.
So the instrument wraps ModelAreaLedger.transfer (class attribute, this process, memory only) and records, for every
call whose amount is primal 0.0 with tape: the flow_counts keys it created, the response rows it appended, the
emitting frame (first frame outside control_area_objective.py and this module: file:line) and whether an SA frame
was active.  Per-site counts are by ledger gate site (only CAO:608 can be nonzero; the other five are listed with 0)
and by emitting origin.  The wrapper reads primals and tape by attribute only (no Dual comparison, no branch event)
and calls the original transfer unchanged.
"""
from __future__ import annotations

import os
import sys
from collections import Counter, deque
from pathlib import Path

if '_tangent_float' in globals():      # injected by the tangent runtime Loader into every module it transforms
    raise ImportError('sa_s3parity must be imported before the tangent finder is installed (it must run untransformed)')

SCHEMA = 'k8-s3-parity/v1'
AMENDMENT = 'K8_PREDECLARATION_AMENDMENT_10.md sha256 d7bcdc9eaa724367ae651f4f63545c451704f8bfdef09f29a3dd48e6ec943e51'
ROOT = Path(os.environ.get('K8G_ROOT') or Path(__file__).resolve().parents[4]).resolve()
PRB = 'evaluation/controllers/physical_ramp_boundary.py'
CAO = 'evaluation/controllers/control_area_objective.py'
AFA = 'evaluation/controllers/area_freeway_accounting.py'
SA_REL = 'evaluation/controllers/stopline_approach.py'
# (site id = amendment 10 name with its K8-2 5eef6be line, file, exact K8-2 text (exactly once), K8-2 line)
S3_SITES = (
    ('PRB-bd:307', PRB, '        if has_transfer(served):\n', 307),
    ('PRB-bd:332', PRB, '        if has_transfer(admitted):\n', 332),
    ('PRB-bd:370', PRB, '        if has_transfer(amount):\n', 370),
    ('CAO:608', CAO, '        if count == 0 and not has_tape(count):  # S3: a zero-primal transfer with tape is recorded\n',
     608),
    ('AFA:247', AFA, '[max(0.0, receiving[i] - max(ramp_in_by_link[link][i], 0.0)) for i in range(len(rho_for_flow))]',
     247),
    ('AFA:393', AFA,
     '            if delta_m > 0.0 and (ramp_in_by_link[link][i] > 0.0 or has_tape(ramp_in_by_link[link][i])):\n', 393),
)
LEDGER_SITE = 'CAO:608'          # the one S3 site on the ledger write path
_CAP = 50                        # listed keys / mismatches per report (counts are complete)


def _norm(path) -> str:
    return os.path.normcase(os.path.abspath(str(path))).replace('\\', '/')


def site_table(root=None) -> dict:
    """The six K8-2 S3 sites in this tree: {site: {file, k82_line, line}}; ValueError unless each text occurs once."""
    root = Path(root or ROOT)
    out, texts = {}, {}
    for site, rel, text, k82 in S3_SITES:
        if rel not in texts:
            texts[rel] = (root / rel).read_bytes().decode('utf-8').replace('\r\n', '\n')
        body = texts[rel]
        if body.count(text) != 1:
            raise ValueError(f'K8-2 S3 anchor {site} not found exactly once in {rel}')
        out[site] = {'file': rel, 'k82_line': k82, 'line': body[:body.index(text)].count('\n') + 1}
    return out


class S3Log:
    """Process-local record of the S3-admitted ModelAreaLedger.transfer calls and of the comparisons."""

    def __init__(self, root, cao_file):
        from evaluation.controllers.sdmpc_dual import Dual, has_tape     # excluded from the tangent finder
        self._dual, self._has_tape = Dual, has_tape
        self.root = Path(root or ROOT)
        self.sites = site_table(self.root)
        self.installed = False
        self._cao = _norm(cao_file)
        self._self = _norm(__file__)
        self._sa = _norm(self.root / SA_REL)
        self.calls = 0
        self.rows = 0
        self.by_origin = Counter()
        self.sa_calls = 0
        self.sa_by_origin = Counter()
        self.created = {}               # key -> {'non_sa': n, 'sa': n, 'origins': Counter (non-SA)}
        self.compares = 0
        self.first_pass = 0
        self.excluded_records = 0
        self.excluded_keys = Counter()
        self.excluded_by_origin = Counter()
        self.not_excluded = []
        self.not_excluded_count = 0
        self.compare_errors = []

    # ------------------------------------------------------------------ instrument
    def admitted(self, value) -> bool:
        """The calls only the K8-2 S3 gate admits: an AD value with primal exactly 0.0 that carries tape."""
        if not isinstance(value, self._dual):
            return False
        primal = value.value
        return type(primal) in (float, int) and primal == 0.0 and self._has_tape(value)

    def origin(self, frame):
        emitter, sa = None, False
        while frame is not None:
            name = _norm(frame.f_code.co_filename)
            if name == self._sa:
                sa = True
            if emitter is None and name not in (self._cao, self._self):
                emitter = (name, frame.f_lineno)
            frame = frame.f_back
        if emitter is None:
            return '?', sa
        name, line = emitter
        root = _norm(self.root) + '/'
        return (name[len(root):] if name.startswith(root) else name.rsplit('/', 1)[-1]) + ':' + str(line), sa

    def note(self, origin, sa, created, rows):
        self.calls += 1
        self.rows += rows
        self.by_origin[origin] += 1
        if sa:
            self.sa_calls += 1
            self.sa_by_origin[origin] += 1
        for key in created:
            rec = self.created.setdefault(key, {'non_sa': 0, 'sa': 0, 'origins': Counter()})
            if sa:
                rec['sa'] += 1
            else:
                rec['non_sa'] += 1
                rec['origins'][origin] += 1

    # ------------------------------------------------------------------ report
    def report(self) -> dict:
        by_site = {site: 0 for site, *_ in S3_SITES}
        by_site[LEDGER_SITE] = self.excluded_records
        return {'schema': SCHEMA, 'amendment': AMENDMENT,
                'method': 'call-site instrument of ModelAreaLedger.transfer (the K8-2 S3 ledger gate CAO:608): calls '
                          'with an amount of primal 0.0 carrying tape, keys created, emitting frame, SA frame on the '
                          'stack (sa_s3parity docstring)',
                'installed': self.installed, 'sites': self.sites,
                's3_calls': self.calls, 's3_rows': self.rows, 's3_calls_by_origin': dict(self.by_origin),
                'sa_created': self.sa_calls, 'sa_created_by_origin': dict(self.sa_by_origin),
                'compares': self.compares, 'first_pass_compares': self.first_pass,
                'excluded_records': self.excluded_records, 'excluded_by_site': by_site,
                'excluded_by_origin': dict(self.excluded_by_origin),
                'excluded_keys': dict(sorted(self.excluded_keys.items(), key=lambda kv: str(kv[0]))[:_CAP]),
                'excluded_keys_distinct': len(self.excluded_keys),
                'not_excluded': self.not_excluded[:_CAP], 'not_excluded_count': self.not_excluded_count,
                'compare_errors': self.compare_errors[:_CAP]}


def install(cao_module, root=None) -> S3Log:
    """Wrap cao_module.ModelAreaLedger.transfer once in this process; returns the log (the same log on a repeat)."""
    cls = cao_module.ModelAreaLedger
    current = cls.__dict__.get('transfer')
    log = getattr(current, '__k8_s3parity__', None)
    if log is not None:
        return log
    log = S3Log(root, cao_module.__file__)
    original = current

    def transfer(self, source, target, vehicles, *args, **kwargs):
        if not log.admitted(vehicles):
            return original(self, source, target, vehicles, *args, **kwargs)
        before = set(self.flow_counts)
        response = self.__dict__.get('_response')
        rows_before = len(response['transfers']) if isinstance(response, dict) else None
        origin, sa = log.origin(sys._getframe(1))
        out = original(self, source, target, vehicles, *args, **kwargs)
        created = [k for k in self.flow_counts if k not in before]
        rows = len(response['transfers']) - rows_before if rows_before is not None else 0
        log.note(origin, sa, created, rows)
        return out

    transfer.__k8_s3parity__ = log
    transfer.__wrapped__ = original
    transfer.__name__, transfer.__qualname__ = original.__name__, original.__qualname__
    cls.transfer = transfer
    log.installed = True
    return log


# ---------------------------------------------------------------------------------------------- comparison
def _primal(value):
    from evaluation.controllers.sdmpc_dual import Dual
    if isinstance(value, Dual):
        return value.value
    if type(value) in (float, int):
        return float(value)
    try:
        import numpy as np
        if isinstance(value, (np.floating, np.integer)):
            return float(value)
    except ImportError:          # pragma: no cover
        pass
    return None


def flow_count_pairs(scalar, tangent, snapshot_keys=()):
    """Paired (where, scalar flow_counts, tangent flow_counts): every ModelAreaLedger reached at the same place in both
    state trees, plus the declared top-level snapshot keys.  Containers only; numbers, strings, AD values, arrays,
    modules and callables are not entered."""
    from evaluation.controllers.sdmpc_dual import Dual
    try:
        import numpy as np
        leaf = (str, bytes, bytearray, int, float, complex, Dual, np.ndarray, np.generic)
    except ImportError:          # pragma: no cover
        leaf = (str, bytes, bytearray, int, float, complex, Dual)
    out = []
    if isinstance(scalar, dict) and isinstance(tangent, dict):
        for key in snapshot_keys:
            a, b = scalar.get(key), tangent.get(key)
            if isinstance(a, dict) and isinstance(b, dict):
                out.append(('states.' + str(key), a, b))
    seen = set()
    stack = [(scalar, tangent, 'states')]
    while stack:
        x, y, where = stack.pop()
        if x is None or y is None or isinstance(x, leaf) or isinstance(y, leaf):
            continue
        if isinstance(x, type(sys)) or callable(x):
            continue
        pair = (id(x), id(y))
        if pair in seen:
            continue
        seen.add(pair)
        if isinstance(x, dict) and isinstance(y, dict):
            for k, v in x.items():
                if k in y:
                    stack.append((v, y[k], where + '.' + str(k)))
        elif isinstance(x, (list, tuple, deque)) and isinstance(y, (list, tuple, deque)):
            for i, (v, w) in enumerate(zip(x, y)):
                stack.append((v, w, f'{where}[{i}]'))
        elif type(x) is type(y) and hasattr(x, '__dict__'):
            if type(x).__name__ == 'ModelAreaLedger':
                a, b = x.__dict__.get('flow_counts'), y.__dict__.get('flow_counts')
                if isinstance(a, dict) and isinstance(b, dict):
                    out.append((where + '.flow_counts', a, b))
            stack.append((vars(x), vars(y), where))
        elif type(x) is type(y) and hasattr(type(x), '__slots__'):
            slots = type(x).__slots__
            for name in ((slots,) if isinstance(slots, str) else slots):
                stack.append((getattr(x, name, None), getattr(y, name, None), where + '.' + name))
    return out


def classify(pairs, log):
    """(set aside [(tangent dict, key)], not excluded [row]) by the rule of the docstring."""
    setaside, other, done = [], [], set()
    for where, a, b in pairs:
        for key, value in b.items():
            if key in a:
                continue
            rec = log.created.get(key)
            primal = _primal(value)
            if primal is None or primal != 0.0:
                why = 'tangent-only key with nonzero or unreadable primal'
            elif rec is None:
                why = 'tangent-only zero-primal key not created by an S3-admitted ledger transfer (another site)'
            elif rec['sa']:
                why = 'tangent-only zero-primal key created by an SA (stopline_approach) S3 transfer'
            elif not rec['non_sa']:
                why = 'tangent-only zero-primal key without a non-SA S3 creation'
            else:
                if (id(b), key) not in done:
                    done.add((id(b), key))
                    setaside.append((where, b, key, '|'.join(sorted(rec['origins'])) or '?'))
                continue
            other.append({'where': where, 'key': str(key), 'primal': primal, 'why': why})
        for key in a:
            if key not in b:
                other.append({'where': where, 'key': str(key), 'primal': _primal(a[key]),
                              'why': 'scalar-only key'})
    return setaside, other


def compare(scalar, tangent, log, *, comparator=None, args=(), kwargs=None, snapshot_keys=()):
    """The runtime comparator on (scalar, tangent); on its ValueError, again with the excluded keys set aside.

    Returns the comparator's value.  Raises the comparator's own exception (runtime traceback) when the excluded keys
    do not explain the mismatch.  The tangent objects are restored before returning or raising."""
    if comparator is None:
        from evaluation.controllers.sdmpc_tangent_state import state_error as comparator
    kwargs = dict(kwargs or {})
    log.compares += 1
    try:
        value = comparator(scalar, tangent, *args, **kwargs)
        log.first_pass += 1
        return value
    except ValueError as exc:
        first = exc
    setaside, other = classify(flow_count_pairs(scalar, tangent, snapshot_keys), log)
    log.not_excluded.extend(other[:_CAP])
    log.not_excluded_count += len(other)
    if not setaside:
        log.compare_errors.append('first: ' + repr(first)[:300])
        raise first
    saved = {}
    for where, b, key, origin in setaside:
        saved.setdefault(id(b), (b, list(dict.items(b))))
    try:
        for where, b, key, origin in setaside:
            del b[key]
        try:
            value = comparator(scalar, tangent, *args, **kwargs)
        except Exception as exc:
            log.compare_errors.append('after setting aside %d S3 records: %r' % (len(setaside), exc))
            raise
    finally:
        for b, items in saved.values():
            dict.clear(b)
            dict.update(b, items)
    for where, b, key, origin in setaside:
        log.excluded_records += 1
        log.excluded_keys[str(key)] += 1
        log.excluded_by_origin[origin] += 1
    return value


def verdict(report, error, tolerance=0.0):
    """(ok, reasons): amendment 10 decisions 1-2 on one comparison report."""
    why = []
    if not isinstance(report, dict) or not report.get('installed'):
        return False, ['S3 parity instrument not installed']
    if report.get('compares', 0) < 1:
        why.append('no comparison went through the S3 parity wrapper')
    if report.get('sa_created'):
        why.append('SA created %s S3 zero-primal ledger transfer(s): %s'
                   % (report['sa_created'], report.get('sa_created_by_origin')))
    if report.get('not_excluded_count'):
        why.append('%s tangent/scalar ledger key mismatch(es) outside the S3 rule' % report['not_excluded_count'])
    if report.get('compare_errors'):
        why.append('comparator error: ' + report['compare_errors'][-1])
    if error is None or not error <= tolerance:
        why.append('state error %r > %r' % (error, tolerance))
    return not why, why


# ---------------------------------------------------------------------------------------------- worker
def install_worker(cao_module, tangent_state_module, root=None) -> S3Log:
    """G-EB-11(e) (sa_worker mode ad_full): instrument the ledger gate and route the runtime state comparator
    (sdmpc_tangent_state.state_error, used by sdmpc_tangent_worker.run with the reverse-v1 backend) through compare().
    Process local and in memory; the worker's own recursive fallback comparator is left alone (a job that used it
    shows compares = 0, which the gate reads as INCOMPLETE)."""
    log = install(cao_module, root)
    original = tangent_state_module.state_error
    if getattr(original, '__k8_s3parity__', None) is not None:
        return log

    def state_error(a, b, *args, **kwargs):
        return compare(a, b, log, comparator=original, args=args, kwargs=kwargs)

    state_error.__k8_s3parity__ = log
    state_error.__wrapped__ = original
    tangent_state_module.state_error = state_error
    return log
