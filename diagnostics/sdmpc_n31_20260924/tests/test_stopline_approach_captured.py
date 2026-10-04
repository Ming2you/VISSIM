"""K8-6 SA captured-state tests: gate-stage rows T3-N7, T6b, T8b, T9b, T9c, T15b (OPT1_V2_SPEC_AMENDMENT_1 r2 section
8, K8_PREDECLARATION_AMENDMENT_5 section 4).  They need captured request templates, so they run in the K8-6 gate phase:

    sa_capture.py tl3 BASE 2700 ; sa_capture.py tl3 SAF 2700 ; sa_capture.py t9c BASE 2700      (K8-4 rebased tree)
    set K8_SA_CAPTURE_ROOT=<K8G_OUT>/sa/cap/<tree>        [optional K8_SA_CAPTURE_T, default 2700]
    PYTHONHASHSEED=0 python -B run_pytest_bn.py -v <the SA unit test files>
        diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach_captured.py > unit_<tree>.log 2>&1

(one combined -v run, or one log per run passed as repeated sa_gates.py --unit-log; k8_gates/sa/README.md step 4c).
Without K8_SA_CAPTURE_ROOT every row skips with SKIP_NO_ROOT (fixed text) and G-EB-14 reads T9b / T9c as INCOMPLETE
(sa_gates.py unit-log rule, AMENDMENT_6 section 1: >= 1 PASSED and 0 SKIPPED; a missing row is INCOMPLETE).  A missing
capture or precondition is a skip with its own explicit reason, never a pass.

Capture provenance (AMENDMENT_6 section 1): every capture a row reads prints one line
    K8_SA_CAPTURE_PROVENANCE {"root", "tree", "harness", "T", "arm", "template_sha256", "capture_json_template_sha256"}
to the terminal (pytest capture disabled for that line only, so it lands in the -v log); sa_gates.py counts the
T9b / T9c rows only when every such line names <out>/sa/cap/<tree> and equals that tree's capture.json.  The T9b / T9c
equivalence asserts run outside subTest, so a failure fails the progress row itself (pytest 9 reports a failed
unittest subTest only as a SUBFAILED summary line under a PASSED row).

T8b / T9b / T9c are in-process (templates unpickled, SA.initialize on a copy of the deployed BASE state with synthetic
vehicle records).  T6b / T3-N7 / T15b share ONE sa_worker.py rollout of the TL3 SAF template (H3, A1 entry, REFERENCE,
job probes T3N7 + T15b) in a BELOW_NORMAL subprocess (k8common.run), i.e. the gate harness's own worker path.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import pickle
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import pytest
except ImportError:                     # plain unittest run: provenance lines go to stdout
    pytest = None

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATES = HERE.parent / 'k8_gates'
SA_DIR = GATES / 'sa'
for extra in (ROOT, ROOT / 'vendor/NumSim-mine', HERE):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

ENV_ROOT = 'K8_SA_CAPTURE_ROOT'
CAPTURE_ROOT = os.environ.get(ENV_ROOT)
CAPTURE_T = int(os.environ.get('K8_SA_CAPTURE_T', '2700'))
SKIP_NO_ROOT = ('K8_SA_CAPTURE_ROOT not set: captured-state rows run in the K8-6 gate phase '
                '(sa_capture.py tl3 BASE/SAF 2700 + t9c BASE 2700)')
EVIDENCE_REL = 'diagnostics/sdmpc_n31_20260924/stopline/sc1001eb_evidence_v3c3_20261004.json'
GATE = 'in_SC1001_W'
TOL = 1e-9
# T9b positions (amendment 1 r2 section 8 / N11): 127 lane 2 @626.47, lane 1 @624.15, lane 3 @621.9.
POSTHEAD = ((2, 626.47, '1117:3'), (1, 624.15, '1117:1'), (3, 621.9, '1117:2'))
PROVENANCE_TAG = 'K8_SA_CAPTURE_PROVENANCE'          # read by sa_gates.captured_provenance (AMENDMENT_6 section 1)
_CACHE = {}
_TERMINAL = {'capsys': None}


class CapturedRowTests(unittest.TestCase):
    """Base of the captured-state rows: hands _emit the running test's capsys (pytest), so that a provenance line
    reaches the terminal and therefore the -v log."""

    if pytest is not None:
        @pytest.fixture(autouse=True)
        def _k8_terminal(self, capsys):
            _TERMINAL['capsys'] = capsys
            yield
            _TERMINAL['capsys'] = None


def _emit(line):
    """One line on its own row of the terminal (a leading newline keeps the -v progress row parseable)."""
    capsys = _TERMINAL['capsys']
    if capsys is None:
        print('\n' + line, flush=True)
        return
    with capsys.disabled():
        print('\n' + line, flush=True)


def _root():
    if not CAPTURE_ROOT:
        raise unittest.SkipTest(SKIP_NO_ROOT)
    return Path(CAPTURE_ROOT)


def _provenance_line(harness, arm, tbytes, record):
    root = _root().resolve()
    return PROVENANCE_TAG + ' ' + json.dumps(
        {'root': str(root), 'tree': root.name, 'harness': harness, 'T': CAPTURE_T, 'arm': arm,
         'template_sha256': hashlib.sha256(tbytes).hexdigest(),
         'capture_json_template_sha256': record.get('template_sha256')}, sort_keys=True)


def _capture(harness, arm):
    """(request, capture.json) of <root>/<harness>/<T>/<arm>; skip with the missing path otherwise.  Prints the
    capture provenance line on every call (AMENDMENT_6 section 1)."""
    key = (harness, arm)
    if key not in _CACHE:
        cap = _root() / harness / f'{CAPTURE_T:06d}' / arm
        tpl, rec = cap / 'template.pickle', cap / 'capture.json'
        if not tpl.is_file() or not rec.is_file():
            raise unittest.SkipTest(f'capture missing: {cap} (sa_capture.py {harness.lower()} {arm} {CAPTURE_T})')
        _model_path()
        tbytes = tpl.read_bytes()
        record = json.loads(rec.read_text(encoding='utf-8'))
        _CACHE[('provenance',) + key] = _provenance_line(harness, arm, tbytes, record)
        _CACHE[key] = (pickle.loads(tbytes), record)
    _emit(_CACHE[('provenance',) + key])
    return _CACHE[key]


def _model_path():
    """sys.path of the adapter process for unpickling (code root, vendor, sdmpc deps; evaluation/controllers last)."""
    sys.path.insert(0, str(GATES)) if str(GATES) not in sys.path else None
    import k8common as c                      # noqa: F401  (configure() at import: default roots)
    for extra in (c.DEPS + r'\sdmpc', c.DEPS + r'\sdmpc-numba', str(ROOT / 'evaluation' / 'controllers')):
        if extra not in sys.path:
            sys.path.append(extra)


def _evidence():
    data = (ROOT / EVIDENCE_REL).read_bytes()
    return json.loads(data.decode('utf-8')), hashlib.sha256(data).hexdigest()


def _install_view(cfg, storage='observed_full'):
    from evaluation.controllers import stopline_approach as SA
    doc, digest = _evidence()
    section = {'schema': SA.SCHEMA, 'evidence': {'path': EVIDENCE_REL, 'sha256': digest}, 'approaches': ['SC1001_EB'],
               'lane_model': 'lane_fifo', 'storage': storage, 'merge_rule': 'zipper',
               'city_admission': 'unconditional', 'origin_tags': 'report'}
    cfg.network.stopline_approach = SA.build_view(cfg, section, doc, digest)
    return cfg.network.stopline_approach


def _provenance(state):
    return state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']


def _occupancy(state, cfg):
    cap = cfg.network.urban_link_storage_veh
    return {k: float(cap[k]) - float(state.urban_link_storage.get(k, cap[k])) for k in cap}


def _raw(t0, vehicles):
    from evaluation.controllers.vehicle_routes import ATTRIBUTES
    records, routes, counts = [], [], {}
    for veh, link, lane, pos, kph, route in vehicles:
        records.append({'veh_no': veh, 'link_no': int(link), 'lane_no': lane, 'position_m': pos, 'speed_kph': kph})
        decision, number = (route.split(':') if route else (None, None))
        routes.append({'veh_no': veh, 'route_decision_no': int(decision) if decision else None,
                       'route_no': int(number) if number else None,
                       'route_decision_type': 'STATIC' if route else None})
        counts[str(link)] = counts.get(str(link), 0) + 1
    n = len(records)
    return {'sim_sec': t0,
            'vehicle_records': {'complete': True, 'records': records, 'collection_count_before': n,
                                'collection_count_after': n, 'record_count': n, 'capture_sim_sec_before': t0,
                                'capture_sim_sec_after': t0, 'full_network_link_counts': counts},
            'vehicle_routes': {'schema_version': 'vissim-vehicle-routes-v1', 'complete': True, 'records': routes,
                               'source_attributes': ATTRIBUTES, 'record_count': n, 'collection_count_before': n,
                               'collection_count_after': n, 'sim_sec_before': t0, 'sim_sec_after': t0}}


def _count(row, label):
    total = math.fsum(float(v) for v in (row or {}).values())
    n = int(round(total))
    if abs(total - n) > 1e-7:
        raise AssertionError(f'{label} provenance is not a vehicle count: {total}')
    return n


def _vehicles(state, seed_split, *, posthead):
    """Synthetic records consistent with the captured provenance counts of 127 / 10777 (+ one 129 tail vehicle when
    the 129 seed row can carry it); queued 127 count = the projected contiguous queue (movement shares of 127)."""
    from evaluation.controllers import stopline_approach as SA
    prov = _provenance(state)
    n127, n10777 = _count(prov.get('127'), '127'), _count(prov.get('10777'), '10777')
    head = list(POSTHEAD) if posthead else []
    if n127 < len(head):
        raise unittest.SkipTest(f'captured 127 holds {n127} vehicles, fewer than the {len(head)} T9b post-head rows')
    queued = int(round(math.fsum(v for k, v in (prov.get('127') or {}).items() if k.startswith('movement:'))))
    rest = n127 - len(head)
    queued = min(queued, rest)
    out, veh, per_lane, queue = [], 9_000_001, {1: 0, 2: 0, 3: 0}, {}
    for lane, pos, route in head:
        out.append((veh, '127', lane, pos, 25.0, route))
        veh += 1
    route_of = {1: '1117:3', 2: '1117:3', 3: '1117:2'}
    for i in range(rest):
        lane = 1 + i % 3
        j = per_lane[lane]
        per_lane[lane] += 1
        if i < queued:
            out.append((veh, '127', lane, 615.0 - 6.5 * j, 0.0, route_of[lane]))
            queue[('127', str(lane))] = queue.get(('127', str(lane)), 0.0) + 1.0
        else:
            out.append((veh, '127', lane, max(1.0, 400.0 - 8.0 * (j - queue.get(('127', str(lane)), 0.0))), 30.0,
                        route_of[lane]))
        veh += 1
    for i in range(n10777):
        out.append((veh, '10777', 1 + i % 3, 0.5, 20.0, None))
        veh += 1
    tail = 0
    row129 = SA._seed_row(seed_split, '129', GATE)
    if row129 is not None and row129[0] + row129[1] >= 1.0 + TOL:
        out.append((veh, '129', 1, 260.0, 30.0, '1132:2'))
        tail = 1
    return out, queue, {'n127': n127, 'n10777': n10777, 'posthead': len(head), 'n_tail129': tail}


def _posthead_fits(run):
    """[(member, booked share)] of the three synthetic post-head vehicles (E lane 2, S lane 1, N lane 3; one vehicle
    per receiver) under amendment 7 section 1: min(1, max(0, room)) of the receiver room before SA.initialize (steps
    3-4(a) touch no receiver before branch (a))."""
    spec, before = run['spec'], run['before']
    out = []
    for d in ('E', 'S', 'N'):
        member = spec['member_of'][d]
        out.append((member, min(1.0, max(0.0, float(before.urban_link_storage[spec['receiver_of'][member]])))))
    return out


def _rehome_fit(run, fits):
    """(a_c, fit_d) of the posthead rehome connector under K8 amendment 8 section 1: branch (a) took its receiver's room
    first (`fits`, the booked post-head shares), then the connector's in_SC1001_W share a_c books
    min(a_c, max(0, room left)); the rest a_c - fit_d is kept as a lane head ready packet."""
    spec, before = run['spec'], run['before']
    (c_link, recv), = spec['posthead_rehome'].items()
    a_c = float((_provenance(before).get(c_link) or {}).get('storage:' + GATE, 0.0))
    if a_c <= 0.0:
        return a_c, 0.0
    room = float(before.urban_link_storage[recv])
    taken = math.fsum(f for m, f in fits if spec['receiver_of'][m] == recv)
    return a_c, min(a_c, max(0.0, room - taken if taken > 0.0 else room))


def _expected_kept(run):
    """N_shortfall_kept: the synthetic post-head vehicles' kept shares (amendment 7 section 1) + the posthead rehome
    connector's kept share (amendment 8 section 1)."""
    fits = _posthead_fits(run) if run['counts']['posthead'] else []
    a_c, fit_d = _rehome_fit(run, fits)
    return math.fsum(1.0 - f for _m, f in fits) + (a_c - fit_d)


def _m_other(prov, members):
    return math.fsum(float(v) for link, row in prov.items() if str(link) not in ('127', '10777')
                     for m in members for k, v in (row or {}).items() if k == 'movement:' + m and float(v) > 0.0)


def _old_post_block(state, cfg, movement, actual, step_idx, routing, spec):
    """Frozen copy of UFA:600-612 at fef1e76 (unchanged through ec063ff; the departure-path body before the K8-6
    extraction)."""
    from src.models import urban_queue_model as uqm
    from evaluation.controllers import urban_flow_accounting as ufa
    receiving_link = str(spec.get("receiving_link", ""))
    if receiving_link in state.urban_link_storage:
        state.urban_link_storage[receiving_link] = max(
            0.0,
            state.urban_link_storage.get(receiving_link, 0.0) - actual,
        )
        if not ufa._receive_corridor(state, cfg, movement, actual, step_idx):
            delay_steps = uqm._link_delay_steps(state, cfg, receiving_link)
            arrival_step = step_idx + delay_steps
            if receiving_link in routing:
                uqm._schedule(state.urban_arrival_buffer, receiving_link, arrival_step, actual)
            uqm._schedule(state.urban_storage_release_buffer, receiving_link, arrival_step, actual)


def _deployed_init(*, posthead, spy=False):
    """SA.initialize on a copy of the captured deployed BASE state (key absent there) with synthetic vehicles."""
    from evaluation.controllers import stopline_approach as SA
    from evaluation.controllers import urban_flow_accounting as ufa
    from evaluation.controllers.observation_projection import audit_projection_provenance
    request, _rec = _capture('TL3', 'BASE')
    follower, state = copy.deepcopy(request['owned'][:2])
    cfg = follower.cfg
    if getattr(cfg.network, 'stopline_approach', None) is not None:
        raise unittest.SkipTest('the BASE capture already carries the stopline approach key')
    seed_split = SA.seed_split_of(state)
    if seed_split is None:
        raise unittest.SkipTest('K8-4 storage_seed_split_by_link absent in the captured BASE state '
                                '(pre-K8-4 base): rerun after the rebase')
    try:
        audit_projection_provenance(_provenance(state), _occupancy(state, cfg), state.urban_movement_queue,
                                    state.ramp_queue)
    except Exception as exc:
        raise unittest.SkipTest(f'captured BASE template is not provenance-consistent before SA (not the RS:253 '
                                f'point): {exc!r}'[:400])
    spec = _install_view(cfg)
    vehicles, queue, counts = _vehicles(state, seed_split, posthead=posthead)
    raw = _raw(float(state.time_sec), vehicles)
    before = copy.deepcopy(state)
    calls = []
    real = ufa._post_service

    def recorder(st, cfg_, movement, actual, step, routing, receiving_link):
        pre = copy.deepcopy(st)
        real(st, cfg_, movement, actual, step, routing, receiving_link)
        calls.append(dict(movement=movement, actual=actual, step=step, routing=routing,
                          receiving_link=receiving_link, pre=pre, post=copy.deepcopy(st)))
    with mock.patch.object(ufa, '_post_service', recorder if spy else real):
        meta = SA.initialize(state, cfg, raw, request['bootstrap']['detector_mapping'], seed_split,
                             queue_by_lane=queue)
    return dict(request=request, cfg=cfg, spec=spec, state=state, before=before, meta=meta, counts=counts,
                seed_split=seed_split, calls=calls)


# ================================================================================================ T8b
class T8bLedgerOnDeployedTemplateTests(CapturedRowTests):
    """Spec 5.8-9 identities (amendment 5 section 3 lane-stock form) on the deployed captured BASE template."""

    def test_ledger_identities(self):
        from evaluation.controllers import stopline_approach as SA
        from evaluation.controllers.observation_projection import audit_projection_provenance
        run = _deployed_init(posthead=True)
        cfg, spec, st, before, meta = run['cfg'], run['spec'], run['state'], run['before'], run['meta']
        info, counts = meta['stopline_approach_initial'], run['counts']
        s = st.stopline_approach_state
        # Lane-stock identity: N_127 + N_10777 - |A| + N_tail129 + M_other + N_shortfall_kept (+-1e-9; amendment 7
        # section 1: the post-head share beyond its receiver's room stays on 127; amendment 8 section 1: so does the
        # 10695 share beyond the room left), each term also as SA reports it.
        m_other = _m_other(_provenance(before), spec['members'])
        kept = _expected_kept(run)
        a_c, fit_d = _rehome_fit(run, _posthead_fits(run))
        self.assertAlmostEqual(info['posthead_receiver_shortfall_veh'], kept, delta=TOL)
        self.assertAlmostEqual(info['posthead_rehome_shortfall_veh'], a_c - fit_d, delta=TOL)
        target = counts['n127'] + counts['n10777'] - counts['posthead'] + counts['n_tail129'] + m_other + kept
        self.assertAlmostEqual(math.fsum(s['stock'].values()), target, delta=TOL)
        self.assertEqual(info['posthead_veh'], float(counts['posthead']))
        self.assertEqual(info['tail129_port_veh'], float(counts['n_tail129']))
        self.assertAlmostEqual(info['other_link_ready_veh'], m_other, delta=TOL)
        # Provenance after: per-link totals = observed counts; 10695 has no in_SC1001_W share (its receiver share +
        # the kept N queue, amendment 8 section 1).
        prov, prov0 = _provenance(st), _provenance(before)
        for link, n in (('127', counts['n127']), ('10777', counts['n10777'])):
            self.assertAlmostEqual(math.fsum(prov.get(link, {}).values()), n, delta=1e-7)
        n10695 = math.fsum((prov0.get('10695') or {}).values())
        self.assertNotIn('storage:' + GATE, prov.get('10695', {}))
        self.assertAlmostEqual(math.fsum(prov.get('10695', {}).values()), n10695, delta=TOL)
        # Mass: storages + queues + ramp queues unchanged.
        total = lambda x: (math.fsum(_occupancy(x, cfg).values()) + math.fsum(float(v) for v in x.urban_movement_queue.values())
                           + math.fsum(float(v) for v in x.ramp_queue.values()))
        self.assertAlmostEqual(total(st), total(before), delta=TOL)
        # in_SC1001_W reservations: before - seeds(127, 10777, rehome connectors) - 129 tail + new moving reservations.
        removed = math.fsum(sum(r[:2]) for r in (SA._seed_row(run['seed_split'], k, GATE)
                                                 for k in ('127', '10777', *spec['posthead_rehome'])) if r)
        tags = math.fsum(v for row in s['tags'].values() for v in row.values())
        expected = (math.fsum(before.urban_arrival_buffer.get(GATE, {}).values()) - removed - counts['n_tail129']
                    + tags + info['tiny_moving_veh'])
        self.assertAlmostEqual(math.fsum(st.urban_arrival_buffer.get(GATE, {}).values()), expected, delta=TOL)
        # I1 / I3 / I7 / I8 at t0 and the provenance audit (spec step 8).
        SA._check_index(st, cfg, spec, s, info['step'])
        audit_projection_provenance(prov, _occupancy(st, cfg), st.urban_movement_queue, st.ramp_queue)


# ================================================================================================ T9b
class T9bPostheadDeployedTemplateTests(CapturedRowTests):
    """Branch (a) on the deployed captured template (N11): side effects = the UFA departure path's.  Asserts outside
    subTest (AMENDMENT_6 section 1)."""

    def test_posthead_side_effects_equal_the_departure_path(self):
        from src.models import urban_queue_model as uqm
        from evaluation.controllers import urban_flow_accounting as ufa
        run = _deployed_init(posthead=True, spy=True)
        cfg, spec, calls = run['cfg'], run['spec'], run['calls']
        t0 = run['meta']['stopline_approach_initial']['step']
        self.assertEqual(run['meta']['stopline_approach_initial']['posthead_veh'], 3.0)
        # Amendment 7 section 1 (review N-r3-2): each post-head vehicle books min(1, receiver room) through the
        # departure path; the rest is kept on 127 and reported.  The captured receiver rooms decide the split, so the
        # row is judged whatever they are (no premise of ample room).
        fits = _posthead_fits(run)                                           # lane 2 E, lane 1 S, lane 3 N
        # (amendment 8 section 1: the reported shortfall also carries the 10695 share beyond the room (a) left)
        self.assertAlmostEqual(run['meta']['stopline_approach_initial']['posthead_receiver_shortfall_veh'],
                               _expected_kept(run), delta=TOL)
        expected = [(m, f) for m, f in fits if f > 0.0]
        self.assertEqual([(c['movement'], c['actual']) for c in calls], expected)
        for _m, _f in fits:
            self.assertGreaterEqual(run['state'].urban_link_storage[spec['receiver_of'][_m]], 0.0)
        specs = uqm.movement_specs(cfg)
        for call in calls:
            movement = call['movement']
            self.assertEqual(call['step'], t0, movement)
            self.assertEqual(call['receiving_link'], str(specs[movement].get('receiving_link', '')), movement)
            old = copy.deepcopy(call['pre'])
            _old_post_block(old, cfg, movement, call['actual'], call['step'], call['routing'], specs[movement])
            if pickle.dumps(old, protocol=5) != pickle.dumps(call['post'], protocol=5):
                differ = sorted(k for k in vars(old) if pickle.dumps(getattr(old, k), protocol=5)
                                != pickle.dumps(getattr(call['post'], k, None), protocol=5))
                self.fail(f'{movement}: (a) differs from the departure path in {differ}')
            probe = copy.deepcopy(call['pre'])
            self.assertIs(ufa._receive_corridor(probe, cfg, movement, call['actual'], call['step']), False,
                          movement)                                           # W members: receive_accepted False


# ================================================================================================ T9c
class T9cRehomeProjectionEquivalenceTests(CapturedRowTests):
    """Branch (d) = the projection with 10695 fixed to its receiver in the support table (scratch capture t9c),
    occupancy and receiver reservations +-1e-9 (speed fields excluded, the declared difference).  K8 amendment 8
    section 1: when the receiver lacks room for the whole share a_c, SA books fit_d = min(a_c, room) and that share
    of the scratch's moved reservation cells; the rest a_c - fit_d is the kept N queue on 10695 (a lane 3 head
    packet).  Asserts outside subTest (AMENDMENT_6 section 1)."""

    def test_rehome_equals_scratch_projection(self):
        from evaluation.controllers import stopline_approach as SA
        base_req, _ = _capture('TL3', 'BASE')
        scratch_req, scratch_rec = _capture('T9C', 'BASE')
        run = _deployed_init(posthead=False)
        cfg, spec = run['cfg'], run['spec']
        (c_link, recv), = spec['posthead_rehome'].items()
        base, sa, scratch = run['before'], run['state'], scratch_req['owned'][1]
        p_base, p_scratch, p_sa = _provenance(base), _provenance(scratch), _provenance(sa)
        a_c = float((p_base.get(c_link) or {}).get('storage:' + GATE, 0.0))
        n_c = math.fsum(float(v) for v in (p_base.get(c_link) or {}).values())
        _a_c, fit_d = _rehome_fit(run, [])
        kept_d = a_c - fit_d
        ratio = fit_d / a_c if a_c > 0.0 else 1.0
        note = (f'{c_link}: {n_c} vehicles, in_SC1001_W share {a_c} at T={CAPTURE_T}, receiver room '
                f'{float(base.urban_link_storage[recv])}, kept {kept_d}')
        self.assertAlmostEqual(run['meta']['stopline_approach_initial']['posthead_rehome_shortfall_veh'], kept_d,
                               delta=TOL, msg=note)
        # The scratch projection itself: c wholly in recv, nothing else on c.
        self.assertEqual(set(p_scratch.get(c_link, {})) - {'storage:' + recv}, set(), note)
        self.assertAlmostEqual(math.fsum(p_scratch.get(c_link, {}).values()), n_c, delta=TOL, msg=note)
        kept_key = 'movement:' + next(m for m, r in spec['receiver_of'].items() if r == recv)
        self.assertEqual(set(p_sa.get(c_link, {})),
                         set(p_scratch.get(c_link, {})) | ({kept_key} if kept_d > 0.0 else set()), note)
        self.assertAlmostEqual(p_sa.get(c_link, {}).get('storage:' + recv, 0.0) + kept_d,
                               p_scratch.get(c_link, {}).get('storage:' + recv, 0.0), delta=TOL, msg=note)
        self.assertAlmostEqual(p_sa.get(c_link, {}).get(kept_key, 0.0), kept_d, delta=TOL, msg=note)
        occ_b, occ_s, occ_sa = _occupancy(base, cfg), _occupancy(scratch, cfg), _occupancy(sa, cfg)
        # Premise: the scratch projection differs from BASE by the gate share of c only.
        self.assertAlmostEqual(occ_b[GATE] - occ_s[GATE], a_c, delta=TOL, msg=note)
        self.assertAlmostEqual(occ_s[recv] - occ_b[recv], a_c, delta=TOL, msg=note)
        seed_c = SA._seed_row(run['seed_split'], c_link, GATE)
        seed_total = 0.0 if seed_c is None else seed_c[0] + seed_c[1]
        total = lambda st, key: math.fsum(float(v) for v in st.urban_arrival_buffer.get(key, {}).values())
        self.assertAlmostEqual(total(base, GATE) - total(scratch, GATE), seed_total, delta=TOL, msg=note)
        # SA (d) on BASE = scratch: receiver occupancy and reservations cell by cell (no post-head vehicle here);
        # amendment 8 section 1: the booked share fit_d of them when the receiver lacks room (ratio fit_d / a_c).
        self.assertAlmostEqual(occ_sa[recv] + kept_d, occ_s[recv], delta=TOL, msg=note)
        differ = []
        for name in ('urban_arrival_buffer', 'urban_storage_release_buffer'):
            a, b = getattr(sa, name).get(recv, {}), getattr(scratch, name).get(recv, {})
            o = getattr(base, name).get(recv, {})
            for due in sorted(set(a) | set(b) | set(o)):
                want = float(o.get(due, 0.0)) + (float(b.get(due, 0.0)) - float(o.get(due, 0.0))) * ratio
                if not abs(float(a.get(due, 0.0)) - want) <= TOL:
                    differ.append((name, due, float(a.get(due, 0.0)), want))
        self.assertEqual(differ, [], f'{note}: receiver reservations differ beyond {TOL} (buffer, due, SA, '
                                     'scratch-based expectation)')
        self.assertTrue(scratch_rec.get('ok', True))


# ================================================================================================ rollout rows
def _worker():
    """One sa_worker.py rollout of the TL3 SAF template: H3, A1 entry (no EO), REFERENCE, probes T3N7 + T15b."""
    if 'worker' in _CACHE:
        return _CACHE['worker']
    _capture('TL3', 'SAF')
    cap = _root() / 'TL3' / f'{CAPTURE_T:06d}' / 'SAF'
    sys.path.insert(0, str(GATES)) if str(GATES) not in sys.path else None
    import k8common as c
    out = Path(tempfile.mkdtemp(prefix='k8sa_captured_'))
    try:
        job = dict(schema='k8-sa-job/v1', label=f'CAPTEST_TL3_{CAPTURE_T}_SAF_A1_H3', harness='TL3', T=CAPTURE_T,
                   seed=31, frame_T=CAPTURE_T, arm='SAF', entry='A1', H=3, variant='REF', mode='scalar',
                   tree='captured-test', template=str(cap / 'template.pickle'),
                   forecast_long=str(cap / 'forecast_long.pickle'), coord=str(cap / 'coord.pickle'),
                   x10490_m=None, action='REFERENCE', obs_entry=None, gate_demand=None, vsl110=False, segment=3,
                   probes=['T3N7', 'T15b'])
        (out / 'job.pickle').write_bytes(pickle.dumps(job, protocol=5))
        code, wall = c.run([c.PY, '-B', str(SA_DIR / 'sa_worker.py'), str(out / 'job.pickle'),
                            str(out / 'result.pickle')], out / 'log.txt', c.base_env())
        summary = json.loads((out / 'summary.json').read_text(encoding='utf-8'))
        log = (out / 'log.txt').read_text(encoding='utf-8', errors='replace')[-3000:]
    finally:
        shutil.rmtree(out, ignore_errors=True)
    _CACHE['worker'] = (code, summary, log)
    return _CACHE['worker']


class T6bRolloutInvariantsTests(CapturedRowTests):
    """Real UFA / LOR / LC rollout on the captured SAF template: I1-I8 every step (SA.end_step), LC assert_stocks
    every step (capture_response), I9 / I11 at initialization (the capture itself)."""

    def test_rollout_runs_every_check(self):
        _req, rec = _capture('TL3', 'SAF')
        self.assertTrue(rec.get('ok', True))
        self.assertTrue(((rec.get('metadata') or {}).get('stopline_approach_install_check') or {}).get('passed'))
        self.assertIsNotNone((rec.get('metadata') or {}).get('stopline_approach_initial'))
        code, summary, log = _worker()
        self.assertEqual(code, 0, log)
        self.assertTrue(summary['ok'], summary.get('error'))
        self.assertIsNone(summary['error_kind'])
        self.assertEqual(summary['recorder_errors'], [])
        urban_steps = ((summary.get('probes') or {}).get('T15b') or {}).get('urban_steps')
        self.assertIsNotNone(urban_steps, 'T15b probe (urban step count) missing')
        self.assertEqual(summary['sa']['end_step_calls'], urban_steps)          # SA.end_step on every urban step


class T3N7PhaseFractionTests(CapturedRowTests):
    """phi_l of SA = the general-path phi of each lane member under the worker runtime (patches, wrap_clock)."""

    def test_phi_is_the_general_path_value(self):
        code, summary, log = _worker()
        self.assertEqual(code, 0, log)
        probe = (summary.get('probes') or {}).get('T3N7')
        self.assertIsNotNone(probe, 'T3N7 probe missing')
        self.assertEqual(probe['errors'], 0)
        self.assertEqual(probe['calls'], ((summary.get('probes') or {}).get('T15b') or {}).get('urban_steps'))
        self.assertLessEqual(probe['max_abs_diff'], 1e-12)
        self.assertEqual(sorted(probe['positive']), ['1', '2', '3'])            # p3 and p4 both green somewhere


class T15bKindServiceTests(CapturedRowTests):
    """shared-urban-kind-service of the captured response agrees with the SA ledger keys (amendment 5.6, T15)."""

    def test_kind_service_matches_sa_counters(self):
        code, summary, log = _worker()
        self.assertEqual(code, 0, log)
        probe = (summary.get('probes') or {}).get('T15b')
        self.assertIsNotNone(probe, 'T15b probe missing')
        self.assertIsNone(probe['error'], probe['error'])
        self.assertEqual(probe['schema'], 'shared-urban-kind-service/v1')
        delta = probe['counters_delta']
        offramp = math.fsum(probe['served_offramp'].values())
        self.assertAlmostEqual(offramp, delta['port_release_veh_10491'] + delta['port_release_veh_10481'], delta=TOL)
        self.assertAlmostEqual(math.fsum(probe['served_members'].values()), delta['np_boundary_in_veh'], delta=TOL)
        self.assertAlmostEqual(math.fsum(probe['internal_by_member'].values()), delta['internal_crossing_veh'],
                               delta=TOL)
        by_kind = (probe['owner_SC1001'] or {}).get('by_kind_veh') or {}
        self.assertGreaterEqual(by_kind.get('off_ramp', 0.0), offramp - TOL)
        self.assertGreaterEqual(by_kind.get('boundary_in', 0.0), math.fsum(probe['served_members'].values()) - TOL)


if __name__ == '__main__':
    unittest.main()
