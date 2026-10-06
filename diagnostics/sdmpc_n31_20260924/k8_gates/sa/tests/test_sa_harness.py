"""Module-level tests of the SA gate harness (synthetic inputs only: no adapter, capture, rollout, VISSIM or run folder).

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests -q
"""
import json
import os
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import pytest

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import sa_common as sc  # noqa: E402
import sa_stats as ss  # noqa: E402
import sa_fh  # noqa: E402
import sa_compare  # noqa: E402
import sa_hookcount  # noqa: E402
import sa_anchors  # noqa: E402
import sa_gates  # noqa: E402
import sa_smoke  # noqa: E402
import sa_inputs as si  # noqa: E402
import sa_worker  # noqa: E402
import sa_s3parity  # noqa: E402


@pytest.fixture
def out_root(tmp_path):
    sc.c.configure(out=tmp_path / 'gates_out')
    yield tmp_path / 'gates_out'
    sc.c.configure()


# Traceback texts as a child records them (K8 amendment 7 section 2): harness frames outside, the raising frame
# innermost.  Paths are those of a code root; only their place (evaluation/, vendor/, k8_gates/ ...) matters.
RUNTIME_SA = 'D:/VISSIM-merge/tree/evaluation/controllers/stopline_approach.py'
AREA = 'D:/VISSIM-merge/tree/evaluation/controllers/control_area_objective.py'
HARNESS = 'D:/VISSIM-merge/tree/diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_worker.py'
INV = 'evaluation.controllers.stopline_approach.StoplineInvariantError: I3: lane 1 stock 82.0 exceeds 81.0'
INIT = 'evaluation.controllers.stopline_approach.StoplineInitError: 129 tail exceeds the seeded 129 residual'   # a reachable init refusal (amendment 8 section 1 removed 'Posthead rehome overfills')


def _tb(exc_line, where=RUNTIME_SA):
    return ('Traceback (most recent call last):\n'
            f'  File "{HARNESS}", line 760, in main\n'
            '    out = standard.run(request, finder, result)\n'
            '  File "D:/VISSIM-merge/tree/evaluation/controllers/sdmpc_tangent_worker.py", line 410, in run\n'
            '    rollout(request)\n'
            f'  File "{where}", line 1345, in f\n'
            '    raise Error(message)\n'
            f'{exc_line}\n')


# ------------------------------------------------------------------------------------------------ stats
def test_pair_stats_and_pearson():
    st = ss.pair_stats([1.0, 2.0, 4.0], [0.0, 2.0, 3.0])
    assert st['n'] == 3 and st['bias'] == pytest.approx(2.0 / 3.0) and st['mae'] == pytest.approx(2.0 / 3.0)
    assert st['r'] == pytest.approx(ss.pearson([1.0, 2.0, 4.0], [0.0, 2.0, 3.0]))
    assert ss.pearson([1.0, 2.0], [1.0, 2.0]) is None
    assert ss.pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


def test_bootstrap_deterministic_and_bounds():
    x = [0.5, -0.2, 0.1, 0.3, -0.4, 0.2, 0.0, 0.1]
    a = ss.boot_ci_iid(x, n=500, seed=0)
    b = ss.boot_ci_iid(x, n=500, seed=0)
    assert a == b and a['lo'] <= a['mean'] <= a['hi']
    cl = ss.boot_ci_cluster(x, [1, 1, 2, 2, 3, 3, 4, 4], n=500, seed=0)
    assert cl['n_clusters'] == 4 and cl['lo'] <= cl['hi']
    assert ss.boot_ci_cluster([1.0] * 4, ['a', 'a', 'b', 'b'], n=50)['lo'] == 1.0


# ------------------------------------------------------------------------------------------------ sa_fh (child side)
def _merged():
    recs = [dict(veh_no=1, link_no=127, lane_no=1, position_m=600.0, speed_kph=0.0, stopped=True),
            dict(veh_no=2, link_no=26, lane_no=1, position_m=100.0, speed_kph=90.0, stopped=False),
            dict(veh_no=3, link_no=999, lane_no=1, position_m=5.0, speed_kph=30.0, stopped=False)]
    merged = {'vehicle_records': {'records': recs, 'record_count': 3, 'collection_count_before': 3,
                                  'collection_count_after': 3,
                                  'full_network_link_counts': {'127': 1, '26': 1, '999': 1},
                                  'full_network_link_stopped_counts': {'127': 1, '26': 0, '999': 0}},
              'local_observation': {'link_counts': {'127': 1, '26': 1, '999': 1, '129': 0},
                                    'link_stopped_counts': {'127': 1, '26': 0, '999': 0, '129': 0},
                                    'link_speeds_kph': {'127': 0.0, '26': 90.0, '999': 30.0, '129': 0.0},
                                    'link_queue_tail_pos_m': {'127': 600.0, '26': 0.0, '999': 0.0, '129': 0.0},
                                    'queue_bins': {'127|1|85': [1.0, 1.0], '999|1|0': [1.0, 0.0]},
                                    'observed_vehicle_count': 3}}
    frame = {'time_s': 2700, 'vehicles': [[1, 127, 1, 600.0, 0.0, 4.2, 1117.0, 3.0, 'STATIC', 10118.0] + [None] * 5,
                                          [2, 26, 1, 100.0, 90.0, 4.2, 1132.0, 3.0, 'STATIC', 10771.0] + [None] * 5,
                                          [3, 999, 1, 5.0, 30.0, 4.2, None, None, None, None] + [None] * 5]}
    obs = {'frames': [frame], 'off_split_ratio': {'10491': 0.2, '10479': 0.1, '10638': 0.3}}
    ctx = {'geometry': {'chains': {'FW_W': [{'link': 26}, {'link': 10771}, {'link': 120}],
                                   'FW_E': [{'link': k} for k in (74, 10699, 2, 10613, 119, 10702, 24)]}}}
    return ctx, merged, obs


def _spec(rows):
    return {'seed': 41, 'island_T': 2700, 'template_T': 2700, 'id_offset': sa_fh.ID_OFFSET,
            'sub_links': list(sa_fh.SUB_LINKS), 'rows': rows,
            'exit_counts': {'10491': {'n_exit': 2, 'n_through': 8, 'ratio': 0.2 + 0.05},
                            '10479': {'n_exit': 0, 'n_through': 0, 'ratio': None}}}


def test_transplant_substitutes_records_metrics_bins_frame_and_exit_share():
    ctx, merged, obs = _merged()
    rows = [[7, 127, 2, 610.0, 0.5, 4.0, 1117.0, 3.0, 'Static', 10118.0],
            [8, 127, 2, 590.0, 12.0, 4.0, 1117.0, 3.0, 'Static', 10118.0],
            [9, 26, 2, 3000.0, 80.0, 4.5, 1132.0, 2.0, 'Static', 10771.0],
            [10, 129, 1, -3.0, 20.0, 4.5, None, None, None, None]]
    tr = sa_fh.Transplant(_spec(rows))
    merged2, obs2 = tr.substitute(ctx, merged, obs)
    recs = merged2['vehicle_records']['records']
    links = sorted((r['link_no'], r['veh_no']) for r in recs)
    assert (999, 3) in links and all(v > sa_fh.ID_OFFSET for k, v in links if k != 999)
    assert merged2['vehicle_records']['record_count'] == 5
    assert merged2['vehicle_records']['full_network_link_counts']['127'] == 2
    lo = merged2['local_observation']
    assert lo['link_counts']['127'] == 2 and lo['link_stopped_counts']['127'] == 1
    assert lo['link_queue_tail_pos_m']['127'] == 610.0 and lo['link_counts']['999'] == 1
    assert lo['link_counts']['129'] == 1 and lo['observed_vehicle_count'] == 5
    assert '127|1|85' not in lo['queue_bins'] and lo['queue_bins']['127|2|87'] == [1.0, 1.0]
    assert lo['queue_bins']['129|1|0'] == [1.0, 0.0]          # entry row clamped to Pos 0
    fr = obs2['frames'][0]['vehicles']
    assert sorted(r[0] for r in fr) == sorted(r['veh_no'] for r in recs) and all(len(r) == 15 for r in fr)
    assert {r[8] for r in fr if r[1] == 127} == {'STATIC'}
    assert obs2['off_split_ratio']['10491'] == pytest.approx(0.25) and obs2['off_split_ratio']['10479'] == 0.1
    assert tr.record['exit_shares']['10491']['template_ratio'] == 0.2 and tr.record['clamped_entry_rows'] == 1
    with pytest.raises(RuntimeError):
        tr.substitute(ctx, merged2, obs2)


def test_transplant_disabled_is_a_no_op_and_chain_mismatch_refused():
    ctx, merged, obs = _merged()
    before = json.dumps(merged, sort_keys=True)
    tr = sa_fh.Transplant(_spec([]), enabled=False)
    tr.substitute(ctx, merged, obs)
    assert json.dumps(merged, sort_keys=True) == before and tr.record['after'] == tr.record['before']
    ctx['geometry']['chains']['FW_W'] = [{'link': 26}, {'link': 120}]
    with pytest.raises(RuntimeError):
        sa_fh.Transplant(_spec([])).substitute(ctx, *_merged()[1:])


def test_eo_entry_rates_full_and_partial_tail(tmp_path):
    rows = ['window_start_s,window_end_s,id,kind,road,cumulative_crossings']
    for i, t in enumerate(range(0, 9000, 30)):
        if t + 30.1 > 8970.2:
            break
        for road, sid, rate in (('FW_W', 'source_1099', 1), ('FW_E', 'source_1098', 2)):
            rows.append(f'{t if t else 0},{t + 30.1:.1f},{sid},source,{road},{(i + 1) * 10 * rate}')
    (tmp_path / 'boundaries_30s.csv').write_text('\n'.join(rows), encoding='utf-8')
    r = sa_fh.eo_entry_rates(tmp_path, 2700, 2)
    assert r['FW_W'] == [1200.0, 1200.0] and r['FW_E'] == [2400.0, 2400.0] and '_partial_blocks' not in r
    tail = sa_fh.eo_entry_rates(tmp_path, 8700, 2)
    assert tail['FW_W'][1] == pytest.approx(1200.0) and tail['_partial_blocks'][0][3] == 8970.1


def test_exit_counts_and_gate_rates():
    pd = pytest.importorskip('pandas')
    geometry = {'chains': {'FW_W': [{'link': 26, 'offset_m': 0.0}, {'link': 10771, 'offset_m': 3818.552},
                                    {'link': 120, 'offset_m': 3822.359}]},
                'bounds': {'FW_W': [0.0] + [100.0 * i for i in range(1, 9)] + [3638.35, 3822.359, 4000.0]},
                'boundaries': [{'kind': 'offramp', 'connector': 10491, 'from_cell': 9},
                               {'kind': 'offramp', 'connector': 10479, 'from_cell': 9}]}
    T = 2700
    rows = []
    for k, t in enumerate((2545.1, 2550.1, 2555.1)):
        rows.append(dict(SIMSEC=t, NO=1, LINK=26 if k < 2 else 10491, POS=3640.0 + k, SPEED=80.0))
        rows.append(dict(SIMSEC=t, NO=2, LINK=26 if k < 2 else 120, POS=3810.0 + k if k < 2 else 5.0, SPEED=80.0))
    df = pd.DataFrame(rows)
    out = sa_fh.exit_counts(df, T - 145, geometry)            # window (2555-150, 2555] holds both transitions
    assert out['10491']['n_exit'] == 1 and out['10491']['n_through'] == 1 and out['10491']['ratio'] == 0.5
    ext = pd.DataFrame([dict(SIMSEC=2705.1 + 5 * i, NO=100 + i, LINK=32) for i in range(10)]
                       + [dict(SIMSEC=2710.1, NO=100, LINK=32), dict(SIMSEC=2700.1, NO=99, LINK=32)])
    assert sa_fh.gate_rates(ext, 2700, 2) == [10 * 3600.0 / 150, 0.0]


# ------------------------------------------------------------------------------------------------ compare / hooks / anchors
@dataclass
class _Obj:
    a: float = 1.0
    sub: dict = field(default_factory=lambda: {'x': [1, 2], 'wall_sec': 3.0})


def test_flatten_compare_timing_and_one_sided():
    fa, fb = sa_compare.flatten(_Obj()), sa_compare.flatten(_Obj(sub={'x': [1, 2], 'wall_sec': 9.0}))
    r = sa_compare.compare_flat(fa, fb)
    assert r['equal'] and r['differ'] == 1 and r['differ_excl_timing'] == 0
    r2 = sa_compare.compare_flat(fa, sa_compare.flatten(_Obj(a=2.0, sub={'x': [1], 'wall_sec': 3.0})))
    assert not r2['equal'] and r2['differ_excl_timing'] == 1 and r2['only_a'] == 1
    loop = {'k': 1.0}
    loop['self'] = loop
    assert sa_compare.flatten(loop) == {'/k': 1.0}


def test_hookcount_classification():
    cls, f = sa_hookcount.classify_chain('urban_queue_model:_queue_max:10 < urban_flow_accounting:urban_substep_accounted:500')
    assert (cls, f) == ('plant', 'urban_flow_accounting:urban_substep_accounted')
    assert sa_hookcount.classify_chain('urban_queue_model:movement_balance_summary:1 < urban_flow_accounting:x:2')[0] == \
        'diagnostic'
    assert sa_hookcount.classify_chain('local_signal_plant:build:90 < distributed_coordinator:run:5')[0] == 'leader_or_other'
    cap = {'_movement_capacity_flow': {'local_signal_plant:build:90 < x:y:1 | SC1001_W_to_E_SC1002': 2.0},
           'member': {'urban_flow_accounting:f:12:cap_flow_of[:m | z:w:3': 1.0}, 'table': {'a:b:1:tok': 4.0}}
    out = sa_hookcount.classify_cap(cap)
    assert out['leader_or_other'] == {'local_signal_plant:build [_movement_capacity_flow]': 2.0}
    assert out['plant'] == {'urban_flow_accounting:f [cap_flow_of[]': 1.0} and out['table'] == {'a:b:1:tok': 4.0}


def test_anchor_projection(monkeypatch, tmp_path):
    old = ['a', 'if departed <= 0.0:', 'b', 'if departed <= 0.0:', 'c']
    new = ['a', 'NEW1', 'if departed <= 0.0:', 'b', 'NEW2', 'if departed <= 0.0:', 'c']
    m = sa_anchors.line_map(old, new)
    assert m[2] == 3 and m[4] == 6
    root = tmp_path / 'r'
    (root / 'evaluation' / 'controllers').mkdir(parents=True)
    (root / 'evaluation' / 'controllers' / 'urban_flow_accounting.py').write_text('\n'.join(new), encoding='utf-8')
    monkeypatch.setattr(sa_anchors, 'git', lambda r, *a: '\n'.join(old))
    rows, detail = sa_anchors.reanchor(root, [('UFA:345', 'urban_flow_accounting.py', 2, 'if departed <= 0.0:', 'le0',
                                               'departed', 'B5'),
                                              ('UFA:585', 'urban_flow_accounting.py', 4, 'if departed <= 0.0:', 'le0',
                                               'departed', 'B5')], 'REV')
    assert [r[2] for r in rows] == [3, 6] and all(d['method'] == 'mapped' for d in detail)


def test_hook_site_chain_fold_and_capacity_counts(tmp_path):
    """sa_hooks/sitecustomize.py in a fresh process on a fake code root (floats only, no model code)."""
    root = tmp_path / 'root'
    (root / 'evaluation' / 'controllers').mkdir(parents=True)
    (root / 'src' / 'models').mkdir(parents=True)
    for d in (root / 'evaluation', root / 'evaluation' / 'controllers', root / 'src', root / 'src' / 'models'):
        (d / '__init__.py').write_text('', encoding='utf-8')
    (root / 'evaluation' / 'controllers' / 'stopline_approach.py').write_text(textwrap.dedent('''
        def _fold_service_residual(st, lane, member, residual):
            st['carry'][lane][member] = st['carry'][lane][member] + residual
        def _fold_city_share(st, lane, member, amount):
            st['carry'][lane][member] = st['carry'][lane][member] + amount
        def _merge_tiny_transfer(st, kept, tiny):
            return kept + tiny
        def _skip_tiny_port_share(st, lane, member, amount):
            return None
        '''), encoding='utf-8')
    (root / 'src' / 'models' / 'urban_queue_model.py').write_text(textwrap.dedent('''
        def _movement_capacity_flow(control, cfg, movement, spec):
            return 1400.0
        '''), encoding='utf-8')
    (root / 'evaluation' / 'controllers' / 'reader.py').write_text(textwrap.dedent('''
        from src.models import urban_queue_model as uqm
        def leader(model, members):
            out = 0.0
            for m in members:
                out += model.cap_flow_of[m]
                out += uqm._movement_capacity_flow(None, None, m, {})
            return out
        '''), encoding='utf-8')
    chain = tmp_path / 'base_site.py'
    chain.write_text(textwrap.dedent('''
        import os
        ANCHORS = os.environ.get('K8_S3_ANCHORS', 'k81')
        if ANCHORS not in ('k81', 'k82'):
            raise SystemExit('K8_S3_ANCHORS must be k81 or k82')
        SITES = SITES_K82 if ANCHORS == 'k82' else SITES_K81
        '''), encoding='utf-8')
    chain.write_text('SITES_K81 = []\nSITES_K82 = []\n' + chain.read_text(encoding='utf-8'), encoding='utf-8')
    table = tmp_path / 'table.json'
    table.write_text(json.dumps({'rows': [['X:1', 'f.py', 1, 'a', 'bool', 'x', 'B5']]}), encoding='utf-8')
    script = tmp_path / 'drive.py'
    script.write_text(textwrap.dedent('''
        import sys
        from evaluation.controllers import stopline_approach as SA, reader
        st = {'carry': {1: {'E': 0.0}}}
        SA._fold_service_residual(st, 1, 'E', 1e-13)
        SA._fold_city_share(st, 1, 'E', 0.0)
        SA._merge_tiny_transfer(st, 1.0, 1e-13)
        SA._skip_tiny_port_share(st, 3, 'N', 1e-14)
        from types import SimpleNamespace
        reader.leader(SimpleNamespace(cap_flow_of={'SC1001_W_to_E_SC1002': 1.0, 'X': 2.0}), ['SC1001_W_to_E_SC1002', 'X'])
        print('SITES', sys.modules['k8_chained_site'].SITES)
        '''), encoding='utf-8')
    hook = tmp_path / 'hook'
    env = {k: v for k, v in os.environ.items() if not k.startswith(('K8_', 'K8G_'))}
    env.update(PYTHONPATH=str(SA / 'sa_hooks') + os.pathsep + str(root), K8_HOOK_DIR=str(hook), K8_SA_HOOK='1',
               K8_SA_CHAIN_SITE=str(chain), K8_S3_TABLE_JSON=str(table), K8G_ROOT=str(root), PYTHONHASHSEED='0')
    p = subprocess.run([sys.executable, '-B', str(script)], env=env, capture_output=True, text=True, cwd=str(tmp_path))
    assert p.returncode == 0, p.stderr
    assert "('X:1', 'f.py', 1, 'a', 'bool', 'x', 'B5')" in p.stdout
    files = list(hook.glob('sahook_*.json'))
    assert len(files) == 1 and not list(hook.glob('sa_*error*'))
    rec = json.loads(files[0].read_text(encoding='utf-8'))
    fold = rec['fold']
    assert fold['_fold_service_residual']['calls'] == 1 and fold['_fold_service_residual']['values_float'] == 1
    assert fold['_fold_city_share']['primal_nonzero'] == 0 if 'primal_nonzero' in fold['_fold_city_share'] else True
    assert fold['_skip_tiny_port_share']['calls'] == 1
    cap = rec['cap_reads']
    assert sum(cap['_movement_capacity_flow'].values()) == 1
    assert any(k.startswith('reader:leader:') and 'cap_flow_of[' in k for k in cap['member'])
    out = sa_hookcount.classify_cap(cap)
    assert sum(out['leader_or_other'].values()) == 2 and not out['plant']
    # review r3 B-r3-4: hookcount keeps the hook's install list; this run's instrument is valid
    run = sa_hookcount.run_record(hook)
    assert 'src.models.urban_queue_model._movement_capacity_flow' in run['fold_extra']['patched']
    assert 'evaluation.controllers.reader:1 lines' in run['fold_extra']['patched']
    assert run['fold_extra']['hook_errors'] == 0 and run['fold_extra']['errors'] == [] and run['setup_errors'] == []
    assert sa_gates.g13_instrument_problems(run, {m: 0 for m in sa_hookcount.PLANT_MODULES}) == []
    assert sa_gates.g13_instrument_problems(run, {**{m: 0 for m in sa_hookcount.PLANT_MODULES},
                                                  'urban_flow_accounting': 1}) == [
        'no line patch urban_flow_accounting:1 lines']


def test_hookcount_install_list_and_line_patch_expectation(tmp_path):
    """Review r3 B-r3-4: merge_counters collects the sa_hooks install list ('patched') and the error counters of every
    sahook file; line_patch_expected counts the capacity token lines of each plant module source by the hook's rule
    (token before '#'); CAP_TOKENS equals the hook site's."""
    import ast
    hook = tmp_path / 'hook'
    hook.mkdir()
    for pid, patched, n_err in ((1, ['a.urban_queue_model._movement_capacity_flow', 'b'], 0), (2, ['b', 'c:2 lines'], 3)):
        (hook / f'sahook_{pid}.json').write_text(json.dumps({
            'counters': {'hook_errors': n_err}, 'fold': {}, 'cap_reads': {},
            'extra': {'errors': ['RuntimeError()'] if n_err else [], 'patched': patched}}), encoding='utf-8')
    run = sa_hookcount.run_record(hook)
    assert run['fold_extra']['patched'] == ['a.urban_queue_model._movement_capacity_flow', 'b', 'c:2 lines']
    assert run['fold_extra']['hook_errors'] == 3 and run['fold_extra']['errors'] == ['RuntimeError()']
    why = sa_gates.g13_instrument_problems(run, {m: 0 for m in sa_hookcount.PLANT_MODULES})
    assert why[0] == 'hook_errors 3' and why[1].startswith('SA hook errors (1)') and len(why) == 2
    root = tmp_path / 'root'
    (root / 'evaluation' / 'controllers').mkdir(parents=True)
    (root / 'evaluation' / 'controllers' / 'urban_flow_accounting.py').write_text(
        'x = net.cap_flow_of[m]\n# cap_flow_of[m] in a comment\ny = 1  # movement_capacity_by_movement_veh_h\n'
        'z = net.movement_capacity_by_movement_veh_h.get(m)\n', encoding='utf-8')
    (root / 'evaluation' / 'controllers' / 'lane_coupling.py').write_text('pass\n', encoding='utf-8')
    exp = sa_hookcount.line_patch_expected(root)
    assert exp['urban_flow_accounting'] == 2 and exp['lane_coupling'] == 0 and exp['stopline_approach'] is None
    real = sa_hookcount.line_patch_expected(SA.parents[3])          # this tree: every plant source is present
    assert set(real) == set(sa_hookcount.PLANT_MODULES) and all(isinstance(v, int) for v in real.values())
    tree = ast.parse((SA / 'sa_hooks' / 'sitecustomize.py').read_text(encoding='utf-8'))
    site_tokens = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                       and any(getattr(t, 'id', None) == 'CAP_TOKENS' for t in n.targets))
    assert site_tokens == sa_hookcount.CAP_TOKENS


# ------------------------------------------------------------------------------------------------ worker pieces
@dataclass
class _Demand:
    freeway_mainline: dict
    urban_boundary: dict


def test_worker_entry_override_and_summary_blocking():
    fc = [_Demand({'FW_W': 4000.0, 'FW_E': 7000.0}, {sc.GATE: 100.0}) for _ in range(3)]
    out, applied = sa_worker.apply_entry(fc, {'obs_entry': {'FW_W': [1.0, 2.0, 3.0], '_partial_blocks': []},
                                              'gate_demand': {sc.GATE: [5.0, 6.0, 7.0]}})
    assert [d.freeway_mainline['FW_W'] for d in out] == [1.0, 2.0, 3.0] and out[2].freeway_mainline['FW_E'] == 7000.0
    assert [d.urban_boundary[sc.GATE] for d in out] == [5.0, 6.0, 7.0] and fc[0].freeway_mainline['FW_W'] == 4000.0
    with pytest.raises(ValueError):
        sa_worker.apply_entry(fc, {'obs_entry': {'FW_W': [1.0]}})
    sa_worker.STATE.update(T0=2700.0, dt=150.0, job={'label': 'x'})
    res = {'steps': {'t': [2701.0, 2851.0, 2852.0], 'stock_10491': [10.0, 37.6, 38.0]}, 'cap': {'10491': 38.58},
           'summary': {'blocks': [{'k': 1}, {'k': 2}]}}
    s = sa_worker.to_summary(res)
    assert s['first_block_t']['10491'] == 2851.0 and s['blocks'][1]['blocked_steps']['10491'] == 2.0
    assert s['blocks'][0]['blocked_steps']['10491'] == 0.0 and s['ok']
    assert sa_worker.error_kind('...StoplineInvariantError: I4') == 'invariant'


# ------------------------------------------------------------------------------------------------ calculators
def _summary(arm, T, blocks, ok=True, **extra):
    return {'schema': 'k8-sa-job/v1', 'job': {'arm': arm, 'T': T}, 'ok': ok, 'blocks': blocks, 'wall_sec': 100.0,
            'costs': [1.0, 2.0], 'costs_order': ['A', 'B'], 'sa': {'end_step_calls': 450} if arm != 'BASE' else None,
            **extra}


def _block(k, total, port91=1.0, port81=0.0, ready=50.0, blocked=0.0, fw=900.0, wout=10.0):
    return {'k': k, 't_end': 0.0, 'w_ports': {'total': total, 'port_10491': port91, 'port_10481': port81,
                                              'movement_w_all': 0, 'gate_occ': 0, 'transit_gate': 0},
            'w_ready': ready, 'w_out_occ': wout, 'fw_w_stock': fw, 'cell9_v': 80.0,
            'blocked_steps': {'10491': blocked, '10481': 0.0, '10638': 0.0}}


def _write_job(tree, label, summary):
    d = sc.job_dir(tree, label)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')


def _fake_ref(event=frozenset()):
    seeds = {}
    for s in sc.FH_SEEDS:
        states = {}
        for T in sc.GRID9:
            states[str(T)] = {'event_state': (s, T) in event, 'nonevent_state': (s, T) not in event,
                              'w_ports_T': {'total': 200.0, '10491': 2, '10481': 1},
                              'w_ports_T150': {'total': 210.0, '10491': 2, '10481': 1},
                              'stop127_T150': 48.0 + (T % 7), 'wout_T150': 10, 'ext127_first500': T + 100.0,
                              'fw_w_stock': {str(T + 450): 900}}
        seeds[str(s)] = {'states': states, 'spill_windows_W': [[2700, 2730]]}
    return {'seeds': seeds}


def test_gate_verdict_and_combination():
    g = sa_gates.gate('X', 't', 'h', {'a': sa_gates.item(1, 'x', True), 'b': sa_gates.item(2, 'y', None, judged=False)})
    assert g['verdict'] == 'PASS'
    assert sa_gates.gate('X', 't', 'h', {'a': sa_gates.item(1, 'x', None)})['verdict'] == 'INCOMPLETE'
    assert sa_gates.gate('X', 't', 'h', {'a': sa_gates.item(1, 'x', False), 'b': sa_gates.item(1, 'x', None)})[
        'verdict'] == 'FAIL'
    res = {gid: {'verdict': 'PASS'} for gid in sa_gates.JUDGED_FOR_PROMOTION}
    assert sa_gates.combine(res) == 'PROMOTE_ELIGIBLE'
    res['G-EB-6'] = {'verdict': 'FAIL'}
    assert sa_gates.combine(res) == 'STOP'
    del res['G-EB-6']
    assert sa_gates.combine(res) == 'INCOMPLETE'


def test_g3_g6_on_synthetic_outputs(out_root):
    tree = 'k86'
    events = {(41, 2700), (41, 3000), (43, 3600)}
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(events))
    sc.write_json(sc.sa_out() / 'gates' / f'smoke_{tree}.json',
                  {'checks': {'H-5': {'excluded_G_EB_3': [[53, 4950]], 'n5_exclusion_ok': True}}})
    for s in sc.FH_SEEDS:
        for T in sc.GRID9:
            blocked = 3.0 if (s, T) in events else 0.0
            for arm, total, p91 in (('SAF', 205.0 + (T % 3), 2.5), ('BASE', 230.0, 4.0)):
                _write_job(tree, sc.job_label('FH', T, arm, 'OBS', 3, seed=s),
                           _summary(arm, T, [_block(1, total, p91, ready=49.0 + (T % 7), blocked=blocked),
                                             _block(2, total), _block(3, total)]))
                if (s, T) in events:
                    _write_job(tree, sc.job_label('FH', T, arm, 'OBS', 6, seed=s),
                               _summary(arm, T, [_block(k, total) for k in range(1, 7)],
                                        first_block_t={'10491': T + 200.0}))
    I = si.Inputs(tree)
    g3 = sa_gates.g3(I, None)
    # K8 amendment 13: the FH 45 values are reports (the former judged form: 45 minus the H-5 list), never judged
    fh = g3['items']['FH_report']
    assert fh['judged'] is False and fh['pass_'] is None and fh['value']['states_used'] == 44
    assert fh['value']['H5_excluded'] == [(53, 4950)] and fh['value']['N5_exclusion_ok'] is True
    assert abs(fh['value']['a']['bias']) <= sc.G3_BIAS_MAX and fh['value']['a']['mae'] <= 10.0
    assert fh['value']['c']['10491']['iid']['lo'] <= 0.0 and fh['value']['c']['10491']['cluster']['n_clusters'] == 5
    # without TL3m inputs (no R-obs validity record, no TL3m job) every judged item is INCOMPLETE
    assert all(g3['items'][k]['pass_'] is None and g3['items'][k]['judged'] for k in ('a_bias', 'a_mae', 'b_G6_7',
                                                                                     'c_ports'))
    assert g3['items']['d_W_out_DP']['pass_'] is None and g3['verdict'] == 'INCOMPLETE'
    assert any('validity' in m for m in g3['missing'])
    g6 = sa_gates.g6(I, None)
    rep = g6['items']['FH_report']
    assert rep['judged'] is False and rep['value']['e_hit_rate']['hits'] == 3 and rep['value']['e_hit_rate']['n_states'] == 3
    assert all(g6['items'][k]['pass_'] is None for k in ('a_10481', 'b_nonevent', 'c_timing', 'e_hit_rate'))


def test_h5_exclusion_and_range(out_root):
    tree = 'k86'
    for s in sc.FH_SEEDS:
        for T in sc.GRID9:
            for f in (T - 150, T, T + 150):
                b = _block(1, 200.0 + (6.0 if (s, T) == (31, 900) and f == T + 150 else 0.0))
                b['w_green_sec'] = {m: 45.0 for m in sc.W_MEMBERS}
                b['w_recv_limited_sec'] = {m: (20.0 if (s, T) == (47, 1200) else 0.0) for m in sc.W_MEMBERS}
                _write_job(tree, sc.job_label('FH', T, sc.JUDGING_ARM, 'OBS', 1, seed=s, frame_T=f),
                           _summary(sc.JUDGING_ARM, T, [b]))
    r = sa_smoke.h5(si.Inputs(tree))
    assert r['n'] == 45 and r['n_ok'] == 44 and r['pass'] is True
    assert r['excluded_G_EB_3'] == [[47, 1200]] and r['n5_exclusion_ok'] is True


def test_g7_non_event_blocks():
    assert sa_gates._non_event_blocks(2700, 3, [[2700, 2730]]) == [2, 3]
    assert sa_gates._non_event_blocks(2700, 3, [[2850, 2880], [3060, 3090]]) == [1]


def test_operationalisations_declared():
    for key in ('G-EB-3(c)', 'G-EB-6 blocked', 'G-EB-7 slow ratio', 'G-EB-8 tangent', 'H-5 exclusion', 'OBS entry tail',
                'judging arm', 'G-EB-2 arms', 'SAG scope', 'G-EB-6(a)', 'G-EB-13 complete', 'G-EB-14 harness',
                'H-2b lane stock', 'G-EB-3(d)', 'G-EB-5 10491 flow', 'G-EB-5 EB discharge', 'unit log',
                'G-EB-2 complete', 'G-EB-5 series', 'G-EB-2 SAG', 'capture records', 'G-EB-13 instrument',
                'job inputs', 'G-EB-13 run complete', 'G-EB-14 capture rows', 'failure classification',
                'G-EB-1 runs', 'G-EB-13 positive control', 'G-EB-11(d) instrument', 'G-EB-11(e) S3 rule',
                'TL3m sample', 'R-obs validity', 'G-EB-3 TL3m', 'G-EB-6 TL3m', 'G-EB-14 R-obs seeds', 'G-EB-2 TL3m',
                'G-EB-4/5/7/8 TL3m'):
        assert key in sc.OPERATIONALISATIONS
    assert sc.G13_JUDGED_HOOK_JOB == sc.job_label('TL3', sc.G13_HOOK_T, 'SAF', 'OBS', 3, variant='HOOK')
    assert sc.G13_JUDGED_HOOK_JOB in sc.OPERATIONALISATIONS['G-EB-13 complete']
    ops = sc.OPERATIONALISATIONS
    assert '8970.1' in ops['G-EB-5 10491 flow'] and '9000.1' in ops['G-EB-5 10491 flow']      # "no 9000.1 key"
    assert '8970.1' in ops['G-EB-5 EB discharge'] and 'no axis' in ops['G-EB-8 tangent']
    assert 'strict' in ops['G-EB-3(d)'] and '|b| <= 5' in ops['G-EB-3(d)']
    assert 'N_tail129' in ops['H-2b lane stock'] and 'M_other' in ops['H-2b lane stock']
    assert 'N_shortfall_kept' in ops['H-2b lane stock'] and 'forecast_long_len' in ops['job inputs']
    assert 'Ledger' in ops['failure classification'] and 'final' in ops['G-EB-13 instrument']
    assert sc.A_K8_SA['resource_summary_kinds'] == ('stopline_lane_room',)
    with pytest.raises(SystemExit):
        sc.guard_seed(37)
    assert sc.job_label('FH', 2700, 'SAF', 'OBS', 1, seed=41, frame_T=2550) == 'FH_2700_s41_f2550_SAF_OBS_H1'
    assert len(sc.ROBS61_T) == 61 and len(sc.DP_T) == 17 and sc.DP_T[-1] == 8100


# ------------------------------------------------------------------------------------------------ amendment 5
EVENTS14 = frozenset(list(((s, T) for s in sc.FH_SEEDS for T in sc.GRID9))[:14])


def _fh_jobs_for_g6(tree, *, saf_blocked=0.0, base_blocked=0.0, sag_blocked=0.0, drop=None):
    for s in sc.FH_SEEDS:
        for T in sc.GRID9:
            for arm, b81 in (('BASE', base_blocked), ('SAF', saf_blocked)):
                blk = _block(1, 200.0)
                blk['blocked_steps']['10481'] = b81
                if (s, T, arm, 3) != drop:
                    _write_job(tree, sc.job_label('FH', T, arm, 'OBS', 3, seed=s), _summary(arm, T, [blk]))
            if (s, T) in EVENTS14:
                for arm, b81 in (('BASE', base_blocked), ('SAF', saf_blocked), ('SAG', sag_blocked)):
                    blk = _block(1, 200.0)
                    blk['blocked_steps']['10481'] = b81
                    if (s, T, arm, 6) != drop:
                        _write_job(tree, sc.job_label('FH', T, arm, 'OBS', 6, seed=s), _summary(arm, T, [blk]))


def test_g6_fh_values_are_a_report_per_arm(out_root):
    """K8 amendment 13: the FH 45 H3 + 14 event H6 values of G-EB-6 are reports (the former judged form, every arm
    listed: SAF and BASE H3 + H6, SAG H6 only); FH blocking never fails or holds the gate.  The judged TL3m rules are
    in test_sa_tl3m.py."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    _fh_jobs_for_g6(tree, sag_blocked=5.0, base_blocked=2.0, saf_blocked=1.0)
    g = sa_gates.g6(si.Inputs(tree), None)
    rep = g['items']['FH_report']
    assert rep['judged'] is False and rep['pass_'] is None
    a = rep['value']['a_10481']
    assert a['SAF']['n_H3'] == 45 and a['SAF']['n_H6'] == 14 and a['SAF']['blocked_steps'] == 59.0
    assert a['SAG']['n_H3'] == 0 and a['SAG']['blocked_steps'] == 70.0 and a['BASE']['blocked_steps'] == 2.0 * 59
    assert g['items']['a_10481']['pass_'] is None and g['verdict'] == 'INCOMPLETE'     # no TL3m input: never FAIL


def _long_summary(T, H, *, rate_vph=600.0, tail_vph=0.0, dep_vph=1200.0, cut=sc.G5_PLANT_END_S):
    ts = [float(T + i) for i in range(1, H * sc.BLOCK_SEC + 1)]
    inflow = [(rate_vph if t <= cut else tail_vph) / 3600.0 for t in ts]
    blocks = []
    for k in range(1, H + 1):
        b = _block(k, 200.0)
        b.update(t_end=float(T + k * sc.BLOCK_SEC), port_inflow={'10491': 0.0}, port_release={'10491': 0.0},
                 w_departures={m: 0.0 for m in sc.W_MEMBERS}, origin_fw_w=0.0)
        blocks.append(b)
    return _summary('SAF', T, blocks, steps={'t': ts, 'inflow_10491': inflow},
                    w_departures_steps={'t': ts, 'veh': [(dep_vph if t <= cut else 0.0) / 3600.0 for t in ts]},
                    recorder_errors=[])


def _eo_cum(rate_vph, end=8970.1):
    out, k = {}, 0
    while 30.0 * k + 0.1 <= end + 1e-9:
        out[str(round(30.0 * k + 0.1, 1))] = rate_vph * 30.0 * k / 3600.0
        k += 1
    return out


def test_g5_flow_and_discharge_cut_at_8970(out_root):
    """B-2 / amendment 5 section 2-4: both sides end at 8970.1 s; plant steps after 8970 s are not counted."""
    tree = 'k86'
    cross = [t + 0.1 for t in range(3, 9001, 3)]                      # 1200 veh/h of 127 head crossings
    ref = _fake_ref()
    ref['seeds']['31'].update(eo_or_d_w_signal_cum=_eo_cum(600.0), eb_crossing_times=cross)
    sc.write_json(sc.sa_out() / 'vissim_ref.json', ref)
    for T, H in sc.LONG_H.items():
        _write_job(tree, sc.job_label('TL3', T, 'SAF', 'OBS', H), _long_summary(T, H, tail_vph=50000.0))
    assert '9000.1' not in ref['seeds']['31']['eo_or_d_w_signal_cum']
    assert '8970.1' in ref['seeds']['31']['eo_or_d_w_signal_cum']
    g5 = sa_gates.g5(si.Inputs(tree), None)
    for T in (2700, 4950):
        flow = g5['items'][f'{T}_flow10491']
        assert flow['value']['period_s'] == [T, 8970.0] and flow['value']['vissim_keys'][1] == '8970.1'
        assert flow['value']['plant_inflow_vph'] == pytest.approx(600.0)     # the 50000 veh/h tail is cut off
        assert flow['value']['vissim_vph'] == pytest.approx(600.0) and flow['pass_'] is True
        eb = g5['items'][f'{T}_eb']
        assert eb['value']['plant_vph'] == pytest.approx(1200.0) and eb['value']['vissim_vph'] == pytest.approx(1200.0)
        assert eb['pass_'] is True
    assert g5['items']['900_flow10491']['value']['period_s'] == [900, 4500.0]
    assert g5['items']['900_flow10491']['judged'] is False
    p, v, end, keys = sa_gates.g5_flow10491(_long_summary(2700, 42), {'2700.1': 0.0, '9000.1': 1000.0}, 2700, 42)
    assert v is None and keys == ['2700.1', '8970.1'] and end == 8970.0       # a 9000.1-only table is INCOMPLETE
    old = _long_summary(2700, 42)
    del old['steps']['inflow_10491']
    assert sa_gates.g5_flow10491(old, _eo_cum(600.0), 2700, 42)[0] is None      # no per-second record -> None
    assert sc.g5_period_end(900, 24) == 4500.0 and sc.g5_period_end(4950, 27) == 8970.0


def _hooks(runs, expected=None, control=True):
    """hooks_<tree>.json; with `control` the BASE full 2700 / 4950 positive control runs (plant reads > 0, amendment
    7 section 3) are added unless the test gives its own."""
    runs = dict(runs)
    if control:
        for T in sc.DP_FULL_T:
            runs.setdefault(f'full_{T}_BASE', _hook_run(plant=5.0))
    return {'schema': 'k8-sa-hooks/v1', 'runs': runs,
            'line_patch_expected': {m: 0 for m in sa_hookcount.PLANT_MODULES} if expected is None else expected}


VALID_PATCHED = ['evaluation.controllers.stopline_approach', 'src.models.urban_queue_model._movement_capacity_flow',
                 'src.models.urban_queue_model:1 lines']


def _hook_run(sa_files=1, plant=0.0, **instrument):
    fold_extra = {'errors': [], 'hook_errors': 0, 'patch_errors': 0, 'patched': list(VALID_PATCHED), 'non_final': [],
                  'final_files': sa_files}
    fold_extra.update(instrument.pop('fold_extra', {}))
    s3_extra = {'errors': [], 'hook_errors': 0, 'patch_errors': 0, 'anchor_mismatch': [], 'non_final': [],
                'final_files': 1}                     # the chained S3 / site hook files (amendment 7 section 3)
    s3_extra.update(instrument.pop('s3_extra', {}))
    return {'sa_files': sa_files, 's3_files': 1, 'cap_classified': {'plant': {'x:y [cap]': plant} if plant else {},
                                                                    'diagnostic': {}, 'leader_or_other': {}},
            'fold_extra': fold_extra, 's3_extra': s3_extra, 'setup_errors': instrument.pop('setup_errors', [])}


G13_ARGS = type('A', (), {'leader_review': None, 'hooks_tag': 'hooks', 'unit_log': None})


def _g13_finished(tree, names, tag='hooks'):
    """Review r4 B-r4-2: the judged runs ran to their end (full run.json exit 0 + action JSON, hook job summary ok
    with SA.end_step called)."""
    for n in names:
        if n.startswith('full_'):
            _, T, arm = n.split('_', 2)
            sc.write_json(sc.full_dir(tree, int(T), arm, tag) / 'run.json',
                          {'T': int(T), 'arm': arm, 'exit': 0, 'action_json_bytes': 123456})
        else:
            lb = n[len('job_'):]
            _write_job(tree, lb, {'job': {'label': lb, 'arm': 'SAF'}, 'ok': True, 'sa': {'end_step_calls': 450}})


def test_g13_requires_the_tl3_saf_hook_job(out_root):
    """B-5 / amendment 5 section 4 (+ amendment 6 section 3): without the judged TL3 SAF hook job (with an SA hook
    record) G-EB-13 is INCOMPLETE."""
    tree = 'k86'
    full = {f'full_{T}_SAF': _hook_run() for T in sc.DP_FULL_T}
    args = G13_ARGS()
    _g13_finished(tree, [*full, 'job_' + sc.G13_JUDGED_HOOK_JOB])

    def plant_reads(runs):
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks(runs))
        return sa_gates.g13(si.Inputs(tree), args)
    assert plant_reads(dict(full))['items']['plant_reads']['pass_'] is None
    assert plant_reads({**full, 'job_TL3_2700_BASE_OBS_H3_HOOK': _hook_run()})['items']['plant_reads']['pass_'] is None
    assert plant_reads({**full, 'job_TL3_2700_SAF_OBS_H3_HOOK': _hook_run(sa_files=0)})['items']['plant_reads'][
        'pass_'] is None
    g = plant_reads({**full, 'job_TL3_2700_SAF_OBS_H3_HOOK': _hook_run()})
    assert g['items']['plant_reads']['pass_'] is True and g['verdict'] == 'PASS'
    assert plant_reads({**full, 'job_TL3_2700_SAF_OBS_H3_HOOK': _hook_run(plant=2.0)})['items']['plant_reads'][
        'pass_'] is False
    assert plant_reads({'full_2700_SAF': _hook_run(), 'job_TL3_2700_SAF_OBS_H3_HOOK': _hook_run()})['items'][
        'plant_reads']['pass_'] is None


def test_g13_judges_the_fixed_job_and_every_other_tl3_saf_hook_job(out_root):
    """Amendment 6 section 3 (review N-r2-2): judged job = TL3_2700_SAF_OBS_H3_HOOK (fixed); every other TL3 SAF hook
    job present is judged with it (plant reads 0); a judged run with sa_files 0 is INCOMPLETE, never skipped."""
    tree = 'k86'
    full = {f'full_{T}_SAF': _hook_run() for T in sc.DP_FULL_T}
    judged = 'job_' + sc.G13_JUDGED_HOOK_JOB
    args = G13_ARGS()
    _g13_finished(tree, [*full, judged, 'job_TL3_900_SAF_OBS_H3_HOOK', 'job_TL3_2700_SAF_A1_H3_HOOK'])

    def g13(runs):
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks(runs))
        return sa_gates.g13(si.Inputs(tree), args)
    other = 'job_TL3_900_SAF_OBS_H3_HOOK'                       # sorts before the judged job
    g = g13({**full, other: _hook_run()})
    assert g['items']['plant_reads']['pass_'] is None and g['verdict'] == 'INCOMPLETE'      # judged job absent
    assert any(sc.G13_JUDGED_HOOK_JOB in m for m in g['missing'])
    g = g13({**full, judged: _hook_run(), other: _hook_run(), 'job_TL3_2700_SAF_A1_H3_HOOK': _hook_run()})
    assert g['items']['plant_reads']['pass_'] is True and g['verdict'] == 'PASS'
    assert {r[0] for r in g['items']['plant_reads']['rows']} == {*full, judged, other, 'job_TL3_2700_SAF_A1_H3_HOOK'}
    g = g13({**full, judged: _hook_run(), other: _hook_run(plant=1.0)})                     # another job reads
    assert g['items']['plant_reads']['pass_'] is False and g['verdict'] == 'FAIL'
    g = g13({**full, judged: _hook_run(), other: _hook_run(sa_files=0)})                    # not skipped
    assert g['items']['plant_reads']['pass_'] is None and g['items']['plant_reads']['no_sa_record'] == [other]
    g = g13({**full, judged: _hook_run(), 'job_TL3_2700_BASE_OBS_H3_HOOK': _hook_run(plant=3.0)})
    assert g['items']['plant_reads']['pass_'] is True                                       # BASE is not judged


def test_unit_log_rows_and_summary_lines(tmp_path):
    """Amendment 6 section 1 on hand-written pytest 9 lines: >= 1 PASSED and 0 SKIPPED; absence INCOMPLETE; a summary
    SUBFAILED/FAILED line FAILs its row even under a PASSED progress row; unattributed session failures INCOMPLETE."""
    f = 'diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach_captured.py'
    log = tmp_path / 'unit.log'
    a, b = f'{f}::T9bPostheadDeployedTemplateTests::test_a', f'{f}::T9cRehomeProjectionEquivalenceTests::test_b'

    def judged(lines, session='2 passed in 0.10s'):
        log.write_text('\n'.join(lines + ([f'==== {session} ===='] if session else [])), encoding='utf-8')
        res = sa_gates.parse_unit_log(log)
        return [sa_gates.unit_item(res, (sa_gates.CAPTURED_TESTS + '::' + i,), i)['pass_'] for i in ('T9b', 'T9c')]
    ok = [f'{a} PASSED [ 10%]', f'{b} PASSED [ 20%]']
    assert judged(ok) == [True, True]
    assert judged([f'{a} SKIPPED (K8_SA_CAPTURE_ROOT not set) [ 10%]', ok[1]]) == [None, True]
    assert judged([ok[0]]) == [True, None]
    assert judged(ok, session=None) == [None, None]                      # no session summary: not attributable
    summary = ['=== short test summary info ===', f"SUBFAILED(buffer='x', due=2) {b} - AssertionError: 2 != 1"]
    assert judged(ok + summary, session='1 failed, 2 passed in 0.1s') == [True, False]
    assert judged(ok, session='1 failed, 2 passed in 0.1s') == [None, None]   # -rN: failure not attributable
    orphan = [f'{a} ', 'some printed output', 'PASSED [ 10%]', f'{b} ', 'FAILED [ 20%]']
    assert judged(orphan + ['=== short test summary info ===', f'FAILED {b} - x'],
                  session='1 failed, 1 passed in 0.1s') == [True, False]
    other = 'diagnostics/sdmpc_n31_20260924/tests/test_stopline_approach.py::PostheadRehomeTests::test_two PASSED'
    assert judged([other]) == [None, None]                     # synthetic rows never count for G-EB-14
    assert sa_gates.unit_item(None, ('x',), 'x')['pass_'] is None
    res = sa_gates.parse_unit_log([log, tmp_path / 'absent.log'])
    assert sa_gates.unit_item(res, ('T9b',), 'T9b')['pass_'] is None      # a named log that does not exist


def test_g14_reads_the_captured_rows(out_root, tmp_path):
    tree = 'k86'
    log = tmp_path / 'unit.log'
    log.write_text('', encoding='utf-8')
    args = type('A', (), {'unit_log': str(log)})()
    g = sa_gates.g14(si.Inputs(tree), args)
    assert g['items']['unit_T9b']['pass_'] is None and g['items']['unit_T9c']['pass_'] is None
    assert g['items']['unit_T9b']['judged'] is True and g['verdict'] == 'INCOMPLETE'


def _h2b_caps(tree, *, lanes, terms, kept10695=0.0, share10695=None):
    """FH s41 2700 SAF capture with the H-2b inputs; `kept10695` = the amendment 8 section 1 (d) share SA kept as a
    lane 3 head packet (the N queue on 10695's provenance, SA metadata posthead_rehome_shortfall_veh)."""
    p10695 = {'storage:SC1001_to_SC2002': 2.0 - kept10695 if share10695 is None else share10695}
    if kept10695:
        p10695['movement:' + sc.W_MEMBERS[2]] = kept10695
    pr = {'sa': {'stock': {'1': lanes, '2': 0.0, '3': 0.0}},
          'records': dict({'rehome_member': kept10695, 'n_rehome_kept': kept10695}, **terms, n10695=2),
          'provenance': {'10695': p10695,
                         '127': {'storage:SC1001_to_SC1002': terms.get('recv127') or 0.0}},
          'occupancy': {'OR_D_W_storage': 1.0, 'OR_D_E_storage': 0.0},
          'ports': {'10491': {'stock': 1.0}, '10481': {'stock': 0.0}},
          'freeway_density': {'FW_W': [20.0, 21.0], 'FW_E': [15.0]}}
    tr = {'expected_density': {'FW_W': [20.0, 21.0], 'FW_E': [15.0]}, 'exit_shares': {}}
    init = {'tail129_port_veh': terms.get('n_tail129'), 'other_link_ready_veh': terms.get('m_other'),
            'posthead_veh': terms.get('posthead_127'),
            'posthead_receiver_shortfall_veh': terms.get('init_shortfall', terms.get('n_shortfall_kept')),
            'posthead_rehome_shortfall_veh': terms.get('init_rehome', kept10695)}
    d = sc.cap_dir(tree, 'FH', 2700, 'SAF', seed=41)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'capture.json').write_text(json.dumps({'ok': True, 'probes': pr, 'transplant': tr,
                                                'metadata': {'stopline_approach_initial': init}}), encoding='utf-8')


def test_h2b_uses_the_corrected_lane_stock_identity(out_root):
    """B-3 / amendment 5 section 3 + amendment 7 section 1: N_127 + N_10777 - |A| + N_tail129 + M_other +
    N_shortfall_kept (the T8 case 13 + 1 - 3 + 1 + 0 + 0); the kept share equals SA's reported shortfall and
    |A| - the 127 receiver provenance."""
    tree = 'k86'
    terms = {'n127': 13, 'n10777': 1, 'posthead_127': 3, 'n_tail129': 1, 'm_other': 0.0, 'n_shortfall_kept': 0.0,
             'recv127': 3.0}
    _h2b_caps(tree, lanes=12.0, terms=terms)
    out = sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']
    chk = out['checks']
    assert chk['sa_lane_stock_eq_fzp'] == (12.0, 12.0, True) and chk['sa_terms_eq_probe'][2] is True
    assert out['pass'] is True
    _h2b_caps(tree, lanes=11.0, terms=terms)                         # the superseded target 13 + 1 - 3 = 11 fails
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_lane_stock_eq_fzp'][2] is False
    _h2b_caps(tree, lanes=12.0, terms={k: v for k, v in terms.items() if k != 'm_other'})
    out = sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']
    assert out['checks']['sa_lane_stock_eq_fzp'][2] is None and out['pass'] is None   # unrecorded term: INCOMPLETE
    assert sa_smoke.lane_stock_target(dict(terms, m_other=0.5)) == 12.5
    # amendment 7 section 1: 0.5 of one post-head vehicle kept on 127 -> target 12.5, receivers hold 2.5
    kept = dict(terms, n_shortfall_kept=0.5, recv127=2.5)
    _h2b_caps(tree, lanes=12.5, terms=kept)
    out = sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']
    assert out['checks']['sa_lane_stock_eq_fzp'] == (12.5, 12.5, True) and out['pass'] is True
    _h2b_caps(tree, lanes=12.0, terms=kept)                          # the kept share is part of the identity
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_lane_stock_eq_fzp'][2] is False
    _h2b_caps(tree, lanes=12.5, terms=dict(kept, recv127=3.0))       # receivers hold the kept share too: mismatch
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_terms_eq_probe'][2] is False
    _h2b_caps(tree, lanes=12.5, terms=dict(kept, init_shortfall=0.0))   # SA reports another shortfall
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_terms_eq_probe'][2] is False
    _h2b_caps(tree, lanes=12.5, terms={k: v for k, v in kept.items() if k != 'n_shortfall_kept'})
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['pass'] is None     # term not recorded: INCOMPLETE
    # amendment 8 section 1: 0.5 of the 10695 share kept as a lane 3 head packet too -> N_shortfall_kept 1.0 (both
    # branches), target 13.0; 10695 holds 1.5 in its receiver + 0.5 N queue = its 2 vehicles
    both = dict(terms, n_shortfall_kept=1.0, recv127=2.5)
    _h2b_caps(tree, lanes=13.0, terms=both, kept10695=0.5)
    out = sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']
    chk = out['checks']
    assert chk['sa_lane_stock_eq_fzp'] == (13.0, 13.0, True) and chk['sa_terms_eq_probe'][2] is True
    assert chk['10695_share_full'] == (2.0, 2.0, True) and out['pass'] is True
    assert chk['sa_terms_eq_probe'][0]['shortfall_eq_posthead_minus_receivers_plus_10695'] == (1.0, 1.0)
    _h2b_caps(tree, lanes=13.0, terms=dict(both, init_rehome=0.0), kept10695=0.5)   # SA reports no (d) share
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_terms_eq_probe'][2] is False
    _h2b_caps(tree, lanes=13.0, terms=both, kept10695=0.5, share10695=2.0)          # kept share also in the receiver
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['10695_share_full'][2] is False
    _h2b_caps(tree, lanes=12.5, terms=dict(both, n_shortfall_kept=0.5), kept10695=0.5)   # (a) share only: mismatch
    assert sa_smoke.h2b(si.Inputs(tree))['arms']['SAF']['checks']['sa_terms_eq_probe'][2] is False


def test_h2b_base_reservation_reads_the_k84_seed_split_schema(out_root):
    """Rebase check (amendment 5 N-12, PLAN O1): the BASE reservation check sums the K8-4 (ce8fe80) rows
    {link: {storage: {moving, stopped, due_*}}} and the unattributed row {storage: {moving, stopped}}."""
    tree = 'k86'
    rows = {'127': {sc.GATE: {'moving': 2.0, 'stopped': 1.0, 'due_moving_step': 2715, 'due_stopped_step': 2805}},
            '32': {sc.GATE: {'moving': 4.0, 'stopped': 0.0, 'due_moving_step': 2715, 'due_stopped_step': 2805},
                   'other': {'moving': 9.0, 'stopped': 9.0, 'due_moving_step': 2715, 'due_stopped_step': 2805}}}
    pr = {'seed_split': dict(rows, unattributed={sc.GATE: {'moving': 0.5, 'stopped': 0.25}}), 'seed_split_present': True,
          'arrival': {sc.GATE: {'2715': 6.5, '2805': 1.25}}, 'freeway_density': {'FW_W': [1.0], 'FW_E': [1.0]},
          'occupancy': {'OR_D_W_storage': 1.0, 'OR_D_E_storage': 0.0},
          'ports': {'10491': {'stock': 1.0}, '10481': {'stock': 0.0}}, 'records': {'n10695': 2},
          'provenance': {'10695': {'storage:SC1001_to_SC2002': 1.0}}}
    tr = {'expected_density': {'FW_W': [1.0], 'FW_E': [1.0]}, 'exit_shares': {}}
    d = sc.cap_dir(tree, 'FH', 2700, 'BASE', seed=41)
    d.mkdir(parents=True, exist_ok=True)

    def check(probes):
        (d / 'capture.json').write_text(json.dumps({'ok': True, 'probes': probes, 'transplant': tr}), encoding='utf-8')
        return sa_smoke.h2b(si.Inputs(tree))['arms']['BASE']['checks']['reservation_eq_seeded_residual']
    assert check(pr) == (7.75, 7.75, True)
    assert check(dict(pr, seed_split=dict(rows, unattributed={}))) == (7.75, 7.0, False)
    assert check(dict(pr, seed_split=dict(rows, unattributed={sc.GATE: 0.75}))) == (7.75, 7.75, True)
    assert check(dict(pr, seed_split=None, seed_split_present=False))[2] is None


def test_identity_terms_of_the_capture_probe():
    import sa_identity
    recs = [dict(veh_no=1, link_no=127, lane_no=2, position_m=626.47),
            dict(veh_no=2, link_no=127, lane_no=1, position_m=600.0),
            dict(veh_no=3, link_no=10777, lane_no=1, position_m=0.5),
            dict(veh_no=4, link_no=129, lane_no=1, position_m=260.0),
            dict(veh_no=5, link_no=129, lane_no=1, position_m=100.0),
            dict(veh_no=6, link_no=129, lane_no=1, position_m=300.0)]
    routes = [dict(veh_no=4, route_decision_no=1132, route_no=2), dict(veh_no=5, route_decision_no=1132, route_no=2),
              dict(veh_no=6, route_decision_no=1136, route_no=2)]
    prov = {'127': {'movement:' + sc.W_MEMBERS[0]: 9.0}, '10777': {'movement:' + sc.W_MEMBERS[1]: 0.25},
            '32': {'movement:' + sc.W_MEMBERS[1]: 0.3, 'storage:' + sc.GATE: 4.0},
            '129': {'movement:' + sc.W_MEMBERS[0]: 0.4}, '10778': {'movement:SC1001_W_to_onE': 7.0}}
    bound = {'vehicle_records': {'records': recs}, 'vehicle_routes': {'records': routes}}
    t = sa_identity.identity_terms(bound, prov, None)
    assert (t['n127'], t['n10777'], t['posthead_127'], t['n_tail129']) == (2, 1, 1, 1)
    assert t['m_other'] == pytest.approx(0.7) and t['target_lane_stock'] == pytest.approx(2 + 1 - 1 + 1 + 0.7)
    assert t['n_shortfall_kept'] == 0.0 and t['recv127'] == 0.0          # BASE (no SA key): nothing kept
    # amendment 7 section 1: the SA metadata shortfall is the sixth term; without it (key present) no target
    spec = {'tail129_from_m': sa_identity.TAIL129_FROM_M, 'port_progress_route': ['1132:2'], 'members': sc.W_MEMBERS,
            'receiver_of': dict(zip(sc.W_MEMBERS, sc.RECEIVERS))}
    prov['127'] = {'movement:' + sc.W_MEMBERS[0]: 1.0, 'storage:SC1001_to_SC1003': 0.25, 'storage:' + sc.GATE: 4.0}
    t = sa_identity.identity_terms(bound, prov, spec, shortfall_kept=0.75, rehome_kept=0.0)
    assert t['n_shortfall_kept'] == 0.75 and t['recv127'] == 0.25 and t['rehome_member'] == 0.0
    assert t['target_lane_stock'] == pytest.approx(2 + 1 - 1 + 1 + 0.7 + 0.75)
    # amendment 8 section 1: the (d) share kept on lane 3 is the N queue on 10695's provenance; M_other is read net
    # of it and N_shortfall_kept (both branches) carries it, so the target counts it once
    prov['10695'] = {'storage:SC1001_to_SC2002': 1.5, 'movement:' + sc.W_MEMBERS[2]: 0.5}
    t = sa_identity.identity_terms(bound, prov, dict(spec, posthead_rehome={'10695': 'SC1001_to_SC2002'}),
                                   shortfall_kept=1.25, rehome_kept=0.5)
    assert t['m_other'] == pytest.approx(0.7) and t['rehome_member'] == 0.5 and t['n_rehome_kept'] == 0.5
    assert t['target_lane_stock'] == pytest.approx(2 + 1 - 1 + 1 + 0.7 + 1.25)
    t = sa_identity.identity_terms(bound, prov, spec, shortfall_kept=1.25)       # (d) share not passed: no target
    assert t['m_other'] is None and t['target_lane_stock'] is None and sa_smoke.lane_stock_target(t) is None
    t = sa_identity.identity_terms(bound, prov, None)                              # BASE: nothing is net
    assert t['m_other'] == pytest.approx(1.2) and t['rehome_member'] == 0.5 and t['n_rehome_kept'] == 0.0
    t = sa_identity.identity_terms(bound, prov, spec)
    assert t['n_shortfall_kept'] is None and t['target_lane_stock'] is None
    assert sa_smoke.lane_stock_target(t) is None


def _plan_args(family, arms=None, hooks=False, T=None, eo_root='.'):
    return type('A', (), dict(family=family, arms=arms, T=T, seeds='31,41,43,47,53', tree='k86', eo_root=eo_root,
                              hooks=hooks, chain='site', s3_table=None, plan_only=False, dry_run=True))()


def test_sag_jobs_only_at_the_declared_places(out_root, monkeypatch):
    """Amendment 5 section 1 / review N-7: SAG = FH event H6 and TL3 9 H3 OBS only; refused elsewhere."""
    import sa_jobs
    monkeypatch.setattr(sa_fh, 'eo_entry_rates', lambda *a, **k: {})
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    tl3 = sa_jobs.plan(_plan_args('tl3'))
    sag = [j for j in tl3 if j['arm'] == 'SAG']
    assert len(sag) == 9 and {j['entry'] for j in sag} == {'OBS'} and {j['H'] for j in sag} == {3}
    for fam in ('long', 'c11', 'tan', 'dp', 'h3', 'h5', 'adfull'):
        assert all(j['arm'] != 'SAG' for j in sa_jobs.plan(_plan_args(fam)))
        with pytest.raises(SystemExit):
            sa_jobs.plan(_plan_args(fam, arms='BASE,SAF,SAG'))
    fh = sa_jobs.plan(_plan_args('fh'))
    sag_fh = [j for j in fh if j['arm'] == 'SAG']
    assert len(sag_fh) == 14 and {j['H'] for j in sag_fh} == {6}
    assert {(j['seed'], j['T']) for j in sag_fh} == set(EVENTS14)
    hooked = sa_jobs.plan(_plan_args('tl3', hooks=True, T='2700'))
    assert {j['arm'] for j in hooked} == {'BASE', 'SAF'} and all(j['label'].endswith('_HOOK') for j in hooked)
    assert sc.sag_allowed('TL3', 'OBS', 3) and not sc.sag_allowed('TL3', 'OBS', 3, variant='C11')
    assert not sc.sag_allowed('TL3', 'A1', 3) and not sc.sag_allowed('FH', 'OBS', 3, event_state=True)
    assert sc.sag_allowed('FH', 'OBS', 6, event_state=True) and not sc.sag_allowed('DP', 'A1', 1)


def test_worker_records_the_g5_per_second_series():
    sa_worker.STATE.update(T0=2700.0, dt=150.0, job={'label': 'x'})
    per = {}
    resp = {'transfers': [{'source': 'movement:' + sc.W_MEMBERS[0], 'end_sec': 2701.0, 'vehicles': 0.25},
                          {'source': 'movement:' + sc.W_MEMBERS[2], 'end_sec': 2701.0, 'vehicles': 0.5},
                          {'source': 'movement:' + sc.W_MEMBERS[1], 'end_sec': 2851.0, 'vehicles': 1.0},
                          {'source': 'movement:SC1001_W_to_onE', 'end_sec': 2701.0, 'vehicles': 9.0},
                          {'source': 'storage:x', 'end_sec': 2701.0, 'vehicles': 9.0}]}
    dep = sa_worker.transfer_flows(resp, 2700.0, 150.0, per)
    assert per == {2701.0: 0.75, 2851.0: 1.0} and dep[1][sc.W_MEMBERS[0]] == 0.25 and dep[2][sc.W_MEMBERS[1]] == 1.0
    res = {'steps': {'t': [2701.0], 'stock_10491': [1.0], 'inflow_10491': [0.1]}, 'cap': {'10491': 38.58},
           'summary': {'blocks': [{'k': 1}], 'w_departures_steps': {'t': [2701.0], 'veh': [0.75]}},
           'probes': {'T15b': {'error': None}}}
    s = sa_worker.to_summary(res)
    assert s['w_departures_steps'] == {'t': [2701.0], 'veh': [0.75]} and s['steps']['inflow_10491'] == [0.1]
    assert s['probes'] == {'T15b': {'error': None}}


def test_g8_reports_no_p4_axis(out_root):
    """Amendment 5 section 2-10: the SDMPC SC1001 green axis is the balanced (+p3, -p4) pair; p4 has no axis."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref())
    for T in sc.GRID9:
        tan = {'axes': [{'index': 0, 'key': 'p3', 'block': 0, 'scale': 1.0, 'green_vector': {'SC1001_p3': 1.0,
                                                                                              'SC1001_p4': -1.0}}],
               'values': {'0': 0.1}}
        _write_job(tree, sc.job_label('TL3', T, 'SAF', 'OBS', 3, variant='TAN', mode='ad'),
                   _summary('SAF', T, [_block(k, 200.0) for k in (1, 2, 3)], tangent=tan))
    g8 = sa_gates.g8(si.Inputs(tree), None)
    rows = g8['items']['nonevent']['value']
    assert all(r[3] == 'no axis' for r in rows)
    vec = g8['items']['p3_axis_green_vectors_report']['value']
    assert vec[2700] == [{'SC1001_p3': 1.0, 'SC1001_p4': -1.0}]


# ------------------------------------------------------------------------------------------------ amendment 6
CAPTURED_REAL = SA.parents[1] / 'tests' / 'test_stopline_approach_captured.py'
TOY_CAPTURED = textwrap.dedent('''
    import importlib.util
    import unittest
    _spec = importlib.util.spec_from_file_location('k8_sa_captured_real', {path!r})
    cap = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(cap)               # the real module: CapturedRowTests, _capture, _emit
    MODE = {mode!r}


    class T9bPostheadDeployedTemplateTests(cap.CapturedRowTests):
        def test_posthead_side_effects_equal_the_departure_path(self):
            request, record = cap._capture('TL3', 'BASE')
            self.assertEqual(request['toy'], 'TL3')


    class T9cRehomeProjectionEquivalenceTests(cap.CapturedRowTests):
        def test_rehome_equals_scratch_projection(self):
            cap._capture('TL3', 'BASE')
            request, record = cap._capture('T9C', 'BASE')
            if MODE == 'subfail':
                for due in (1, 2):
                    with self.subTest(buffer='urban_arrival_buffer', due=due):
                        self.assertEqual(due, 1)
            if MODE == 'fail':
                self.assertEqual(request['toy'], 'not the scratch projection')
            self.assertEqual(request['toy'], 'T9C')
    ''')
TOY_UNIT = textwrap.dedent('''
    import unittest
    MODE = {mode!r}


    class KeyAbsentStructureTests(unittest.TestCase):
        def test_hooks(self):
            for name in ('a', 'b'):
                with self.subTest(name):
                    self.assertTrue(MODE != 'subfail' or name == 'a')
    ''')


def _toy_captures(root):
    """<root>/{TL3,T9C}/002700/BASE/{template.pickle, capture.json} with the capture child's template_sha256."""
    import hashlib
    import pickle
    for harness in ('TL3', 'T9C'):
        d = root / harness / '002700' / 'BASE'
        d.mkdir(parents=True, exist_ok=True)
        tbytes = pickle.dumps({'toy': harness}, protocol=5)
        (d / 'template.pickle').write_bytes(tbytes)
        (d / 'capture.json').write_text(json.dumps({'ok': True, 'harness': harness, 'T': 2700, 'arm': 'BASE',
                                                    'template_sha256': hashlib.sha256(tbytes).hexdigest()}),
                                        encoding='utf-8')


def _real_pytest(work, name, files, *args, capture_root=None):
    """Run the installed pytest (9.1.1 here) on toy files in a fresh process; returns the -v log path."""
    proj = work / name
    proj.mkdir(parents=True)
    (proj / 'pytest.ini').write_text('[pytest]\n', encoding='utf-8')
    for fname, text in files.items():
        (proj / fname).write_text(text, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('K8_', 'K8G_', 'PYTEST_'))}
    env.update(PYTHONHASHSEED='0', PYTHONIOENCODING='utf-8')
    if capture_root is not None:
        env['K8_SA_CAPTURE_ROOT'] = str(capture_root)
    p = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', *args], cwd=str(proj),
                       env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    log = work / f'{name}.log'
    log.write_text(p.stdout + p.stderr, encoding='utf-8')
    assert 'pytest-9.' in p.stdout, p.stdout[-2000:]            # the parser rules are pytest 9 rules
    return log


def _items(log, tree='k86'):
    res = sa_gates.parse_unit_log(log)
    return {i: sa_gates.unit_item(res, (sa_gates.CAPTURED_TESTS + '::' + i,), i,
                                  provenance=sa_gates.captured_provenance(res, tree, needs))
            for i, needs in (('T9b', (('TL3', 'BASE'),)), ('T9c', (('TL3', 'BASE'), ('T9C', 'BASE'))))}


def test_unit_log_on_real_pytest_output(out_root, tmp_path):
    """B-r2-1 / B-r2-2 / amendment 6 section 1 on real pytest output: pass, subTest failure (PASSED progress row +
    SUBFAILED summary line), plain failure, -rN (failure not attributable), missing row, skip."""
    root = sc.sa_out() / 'cap' / 'k86'
    _toy_captures(root)
    work = tmp_path / 'runs'
    run = lambda name, mode, *a, cr=root: _real_pytest(
        work, name, {'test_stopline_approach_captured.py': TOY_CAPTURED.format(path=str(CAPTURED_REAL), mode=mode)},
        '-v', *a, capture_root=cr)
    ok = run('ok', 'ok')
    text = ok.read_text(encoding='utf-8')
    assert sa_gates.PROVENANCE_TAG in text                     # printed through pytest's capture into the -v log
    got = _items(ok)
    assert got['T9b']['pass_'] is True and got['T9c']['pass_'] is True, got
    assert got['T9c']['value']['provenance']['captures'] == ['T9C/2700/BASE', 'TL3/2700/BASE']
    sub = run('subfail', 'subfail')
    assert 'SUBFAILED' in sub.read_text(encoding='utf-8')
    rows = sa_gates.parse_unit_log(sub)['rows']
    assert rows[next(k for k in rows if '::T9c' in k)] == 'FAILED'            # the progress row said PASSED
    got = _items(sub)
    assert got['T9b']['pass_'] is True and got['T9c']['pass_'] is False
    got = _items(run('fail', 'fail'))
    assert got['T9b']['pass_'] is True and got['T9c']['pass_'] is False
    got = _items(run('rN', 'subfail', '-rN'))                  # no summary lines: "1 failed" unattributable
    assert got['T9b']['pass_'] is None and got['T9c']['pass_'] is None
    assert got['T9c']['value']['unattributed_logs']
    got = _items(run('only_b', 'ok', '-k', 'T9b'))             # T9c row missing -> INCOMPLETE, never FAIL
    assert got['T9b']['pass_'] is True and got['T9c']['pass_'] is None
    got = _items(run('skip', 'ok', cr=None))                   # no K8_SA_CAPTURE_ROOT: skipped
    assert got['T9b']['pass_'] is None and got['T9c']['pass_'] is None
    assert got['T9b']['value']['provenance']['ok'] is None


def test_captured_rows_need_the_gate_capture_provenance(out_root, tmp_path):
    """Amendment 6 section 1 (review N-r2-4): a log of another capture root (toy captures, sawip/fakecap) or with a
    template sha256 that differs from <out>/sa/cap/<tree>/.../capture.json is INCOMPLETE, even when it passes."""
    root = sc.sa_out() / 'cap' / 'k86'
    _toy_captures(root)
    fake = tmp_path / 'fakecap' / 'sa' / 'cap' / 'k86'
    _toy_captures(fake)
    work = tmp_path / 'runs'
    files = lambda mode: {'test_stopline_approach_captured.py': TOY_CAPTURED.format(path=str(CAPTURED_REAL),
                                                                                     mode=mode)}
    got = _items(_real_pytest(work, 'fake', files('ok'), '-v', capture_root=fake))
    assert got['T9b']['pass_'] is None and got['T9b']['value']['provenance']['reason'] == 'provenance mismatch'
    got = _items(_real_pytest(work, 'fakefail', files('fail'), '-v', capture_root=fake))
    assert got['T9c']['pass_'] is None                         # a toy failure never STOPs the gate either
    good = _real_pytest(work, 'good', files('ok'), '-v', capture_root=root)
    assert _items(good, tree='k85')['T9b']['pass_'] is None    # the log names another tree
    rec = json.loads((root / 'T9C' / '002700' / 'BASE' / 'capture.json').read_text(encoding='utf-8'))
    (root / 'T9C' / '002700' / 'BASE' / 'capture.json').write_text(json.dumps(dict(rec, template_sha256='0' * 64)),
                                                                  encoding='utf-8')
    got = _items(good)
    assert got['T9b']['pass_'] is None and got['T9c']['pass_'] is None       # every provenance line must agree
    # G-EB-14 reads the same rule from --unit-log (repeatable)
    args = type('A', (), {'unit_log': [str(good)]})()
    g = sa_gates.g14(si.Inputs('k86'), args)
    assert g['items']['unit_T9c']['pass_'] is None and g['verdict'] == 'INCOMPLETE'


def test_unit_items_from_several_logs_and_a_captured_only_log(out_root, tmp_path):
    """B-r2-2 / amendment 6 section 1: a captured-only log leaves G-EB-1 T2 INCOMPLETE (not FAIL); the SA unit log
    and the captured log are read together from repeated --unit-log; a SUBFAILED T2 subTest FAILs T2."""
    root = sc.sa_out() / 'cap' / 'k86'
    _toy_captures(root)
    work = tmp_path / 'runs'
    cap_log = _real_pytest(work, 'cap', {'test_stopline_approach_captured.py': TOY_CAPTURED.format(
        path=str(CAPTURED_REAL), mode='ok')}, '-v', capture_root=root)
    unit_ok = _real_pytest(work, 'unit_ok', {'test_stopline_wiring.py': TOY_UNIT.format(mode='ok')}, '-v')
    unit_bad = _real_pytest(work, 'unit_bad', {'test_stopline_wiring.py': TOY_UNIT.format(mode='subfail')}, '-v')
    t2 = lambda logs: sa_gates.unit_item(sa_gates.parse_unit_log(logs), ('KeyAbsent',), 'T2')['pass_']
    assert t2(cap_log) is None                                 # captured-only log: T2 row absent -> INCOMPLETE
    assert t2([unit_ok, cap_log]) is True and t2([unit_bad, cap_log]) is False
    g1 = sa_gates.g1(si.Inputs('k86', 'k85'), type('A', (), {'unit_log': [str(cap_log)]})())
    assert g1['items']['unit_T2']['pass_'] is None and g1['verdict'] != 'FAIL'
    g14 = sa_gates.g14(si.Inputs('k86'), type('A', (), {'unit_log': [str(unit_ok), str(cap_log)]})())
    assert g14['items']['unit_T9b']['pass_'] is True and g14['items']['unit_T9c']['pass_'] is True


def _declared_outputs(tree):
    import sa_jobs
    labels, caps, n_sag = sa_jobs.declared_keyed(tree)
    for lb in labels:
        arm = 'SAG' if '_SAG_' in lb else 'SAF'
        _write_job(tree, lb, {'job': {'label': lb, 'arm': arm}, 'ok': True, 'sa': {'end_step_calls': 450}})
    for d in caps:
        Path(d).mkdir(parents=True, exist_ok=True)
        (Path(d) / 'capture.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
    return labels, caps, n_sag


def test_g2_needs_every_declared_key_on_run(out_root):
    """Amendment 6 section 3 (review N-r2-3): all SAF jobs + the SAG 23 + the G-EB-13 hook job and their captures
    (+ ROBS61 61) must be present; a missing one is INCOMPLETE; a violation found still fails."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    labels, caps, n_sag = _declared_outputs(tree)
    assert n_sag == sc.SAG_JOBS_DECLARED == 23 and len(labels) == 294 + 27 + 23 and len(caps) == 254 + 18 + 122
    assert 'TL3_2700_s43_SAF_OBS_H3' in labels and 'TL3_2700_SAF_OBS_H6' in labels      # amendment 13 TL3m
    assert str(sc.cap_dir(tree, 'ROBS61', 150, 'SAF', seed=47)) in caps
    assert sc.G13_JUDGED_HOOK_JOB in labels and 'TL3_2700_SAG_OBS_H3' in labels
    assert not [lb for lb in labels if '_SAG_' in lb and not (lb.startswith('TL3_') and lb.endswith('_OBS_H3')
                                                              or lb.endswith('_OBS_H6'))]
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'PASS' and g['items']['declared_runs']['value']['jobs'] == 344
    sag = next(lb for lb in labels if lb.endswith('_SAG_OBS_H6'))
    (sc.job_dir(tree, sag) / 'summary.json').unlink()
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'INCOMPLETE' and g['items']['violations']['pass_'] is None
    assert any(sag in m for m in g['missing'])
    _write_job(tree, 'TL3_900_SAF_OBS_H3', {'job': {'arm': 'SAF'}, 'ok': False, 'error_kind': 'invariant',
                                             'error': _tb(INV)})
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'FAIL'
    _write_job(tree, 'TL3_900_SAF_OBS_H3', {'job': {'arm': 'SAF'}, 'ok': False, 'error_kind': 'invariant',
                                             'error': 'StoplineInvariantError: I4'})     # no traceback: unreadable
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'INCOMPLETE'
    robs = sc.cap_dir(tree, 'ROBS61', 150, 'SAF') / 'capture.json'
    _write_job(tree, 'TL3_900_SAF_OBS_H3', {'job': {'arm': 'SAF'}, 'ok': True, 'sa': {'end_step_calls': 1}})
    _write_job(tree, sag, {'job': {'arm': 'SAG'}, 'ok': True, 'sa': {'end_step_calls': 1}})
    robs.unlink()
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'INCOMPLETE' and any('ROBS61' in m for m in g['missing'])
    (sc.sa_out() / 'vissim_ref.json').unlink()
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'INCOMPLETE'      # no event states: list unknown


def test_g5_needs_a_complete_plant_series(out_root):
    """Amendment 6 section 3 (review N-r2-5): (T, end] 1 s steps complete, t strictly increasing, recorder_errors
    empty on the judged job; otherwise INCOMPLETE (never PASS, never FAIL)."""
    tree = 'k86'
    ref = _fake_ref()
    ref['seeds']['31'].update(eo_or_d_w_signal_cum=_eo_cum(600.0), eb_crossing_times=[t + 0.1 for t in range(3, 9001, 3)])
    sc.write_json(sc.sa_out() / 'vissim_ref.json', ref)

    def flow_item(mutate):
        s = _long_summary(2700, 42)
        mutate(s)
        _write_job(tree, sc.job_label('TL3', 2700, 'SAF', 'OBS', 42), s)
        g5 = sa_gates.g5(si.Inputs(tree), None)
        return g5['items']['2700_series'], g5['items']['2700_flow10491'], g5['items']['2700_eb']
    series, flow, eb = flow_item(lambda s: None)
    assert series['pass_'] is True and flow['pass_'] is True and eb['pass_'] is True
    assert series['value']['steps_in_period'] == 8970 - 2700 == series['value']['expected_steps']

    def drop(s):
        i = s['steps']['t'].index(5000.0)
        del s['steps']['t'][i], s['steps']['inflow_10491'][i]

    def dup(s):
        s['steps']['t'][10] = s['steps']['t'][9]
    for mutate in (drop, dup, lambda s: s.update(recorder_errors=['KeyError']), lambda s: s.pop('recorder_errors'),
                   lambda s: s['w_departures_steps']['t'].reverse()):
        series, flow, eb = flow_item(mutate)
        assert series['pass_'] is None and flow['pass_'] is None and eb['pass_'] is None, series['value']
        assert 'incomplete' in flow['note']
    assert sa_gates.g5_series_check(_long_summary(4950, 27), 4950, 27)['expected_steps'] == 8970 - 4950


# ------------------------------------------------------------------------------------------------ review r3 (round 2)
def _combine_with(gid, g):
    res = {k: {'verdict': 'PASS'} for k in sa_gates.JUDGED_FOR_PROMOTION}
    res[gid] = g
    return sa_gates.combine(res)


def test_g2_failure_classification(out_root):
    """K8 amendment 7 section 2 (D-K8-1, reviews B-r3-2, N-r4-2, N-r4-3): one classification table (sa_errors).
    SAF fails only with a traceback raised in runtime code (invariant / other / init), a job without SA.end_step
    fails, a harness or infrastructure failure (no traceback, harness frame, killed, input absent) is INCOMPLETE.
    SAG fails only for an invariant / route / stocks violation raised in runtime code; every other SAG failure, an SAG
    job without SA.end_step, a killed SAG capture and an input-absent SAG job are reported (sag_reported, not judged)
    and do not hold G-EB-2 (an attempt record is present)."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    labels, caps, n_sag = _declared_outputs(tree)
    sag = next(lb for lb in labels if lb.endswith('_SAG_OBS_H6'))
    saf = 'TL3_900_SAF_OBS_H3'
    good = lambda arm, lb: {'job': {'label': lb, 'arm': arm}, 'ok': True, 'sa': {'end_step_calls': 450}}

    def g2_with(label, summary):
        _write_job(tree, label, summary)
        g = sa_gates.g2(si.Inputs(tree), None)
        _write_job(tree, label, good('SAG' if '_SAG_' in label else 'SAF', label))
        return g

    def failed(arm, label, error, **kw):
        return dict({'job': {'label': label, 'arm': arm}, 'ok': False, 'error': error}, **kw)
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    val = 'ValueError: available storage SC1001_to_SC1003 must be finite and nonnegative: -0.5'
    # SAG: non-invariant failures (runtime or not) and a missing SA.end_step are reported, G-EB-2 stays PASS
    for err in (_tb(val, AREA), _tb(INIT), _tb('StoplineConfigError: y'), val, _tb(INV, HARNESS)):
        g = g2_with(sag, failed('SAG', sag, err))
        assert g['verdict'] == 'PASS' and _combine_with('G-EB-2', g) == 'PROMOTE_ELIGIBLE', err
        assert g['items']['sag_reported']['value'] == 1 and g['items']['sag_reported']['judged'] is False
    g = g2_with(sag, {'job': {'label': sag, 'arm': 'SAG'}, 'ok': True, 'sa': {'end_step_calls': 0}})
    assert g['verdict'] == 'PASS' and g['items']['sag_reported']['value'] == 1
    g = g2_with(sag, failed('SAG', sag, _missing_file_traceback(sc.cap_dir(tree, 'FH', 2700, 'SAG', seed=31)
                                                                / 'template.pickle')))
    assert g['verdict'] == 'PASS'                                  # an input-absent SAG attempt is reported
    # SAG: an invariant / route / stocks violation raised in runtime code fails ('Ledger' is stocks, one table)
    for err in (_tb(INV), _tb('evaluation.controllers.stopline_approach.StoplineRouteError: I10'),
                _tb('evaluation.controllers.control_area_objective.MembershipError: area cohort/model stock mismatch '
                    '(assert_stocks)', AREA), _tb('RuntimeError: ModelAreaLedger overdraw', AREA)):
        g = g2_with(sag, failed('SAG', sag, err))
        assert g['verdict'] == 'FAIL' and g['items']['violations']['pass_'] is False, err
        assert _combine_with('G-EB-2', g) == 'STOP'
    # the child's own classification (written on its full traceback) wins over a truncated text without frames
    g = g2_with(sag, failed('SAG', sag, '...StoplineInvariantError: I3', error_kind='invariant', error_site='runtime'))
    assert g['verdict'] == 'FAIL'
    # SAF: a runtime traceback fails (other / invariant), otherwise INCOMPLETE (rerun)
    g = g2_with(saf, failed('SAF', saf, _tb(val, AREA)))
    assert g['verdict'] == 'FAIL' and g['items']['other_failures']['pass_'] is False
    g = g2_with(saf, failed('SAF', saf, _tb(INV)))
    assert g['verdict'] == 'FAIL' and g['items']['violations']['pass_'] is False
    for err in (val, _tb(val, HARNESS), _tb(INV, HARNESS), 'Traceback (most recent call last):\nKeyboardInterrupt'):
        g = g2_with(saf, failed('SAF', saf, err))
        assert g['verdict'] == 'INCOMPLETE' and _combine_with('G-EB-2', g) == 'INCOMPLETE', err
        assert g['items']['other_failures']['pass_'] is None and g['items']['violations']['pass_'] is None
        assert [r[0] for r in g['items']['unreadable_runs']['rows']] == [saf]
    g = g2_with(saf, {'job': {'label': saf, 'arm': 'SAF'}, 'ok': True, 'sa': {'end_step_calls': 0}})
    assert g['verdict'] == 'FAIL' and g['items']['checks_ran']['pass_'] is False
    # a summary written before the job was read (empty job, review N-r3-6): the arm comes from the label
    g = g2_with(sag, {'job': {}, 'ok': False, 'error': _tb(val, AREA)})
    assert g['verdict'] == 'PASS'
    g = g2_with(saf, {'job': {}, 'ok': False, 'error': _tb(INV)})
    assert g['verdict'] == 'FAIL'
    # captures: SAG init / other reported, SAG invariant fails, SAG killed reported; SAF init / other in runtime
    # code fail, SAF without a runtime traceback / harness stage / killed INCOMPLETE
    sag_cap = Path(next(f for f in caps if Path(f).name == 'SAG'))
    saf_cap = sc.cap_dir(tree, 'ROBS61', 150, 'SAF')

    def cap_with(folder, rec):
        (folder / 'capture.json').unlink()
        (folder / 'capture_failed.json').write_text(json.dumps(rec), encoding='utf-8')
        g = sa_gates.g2(si.Inputs(tree), None)
        (folder / 'capture_failed.json').unlink()
        (folder / 'capture.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
        return g['verdict']
    child = lambda err, **kw: dict({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': err}, **kw)
    killed = {'ok': False, 'exit': 1, 'error_kind': 'killed', 'child_record': False, 'log_tail': INV}
    assert cap_with(sag_cap, child(_tb(INIT))) == 'PASS' and cap_with(sag_cap, child(_tb(val, AREA))) == 'PASS'
    assert cap_with(sag_cap, killed) == 'PASS'
    assert cap_with(sag_cap, child(_tb(INV))) == 'FAIL'
    assert cap_with(saf_cap, child(_tb(INIT))) == 'FAIL' and cap_with(saf_cap, child(_tb(val, AREA))) == 'FAIL'
    for rec in (child(val), child(_tb(val, HARNESS)), child(_tb(INIT), harness_stage_error='Traceback ...'),
                child(None), killed):
        assert cap_with(saf_cap, rec) == 'INCOMPLETE', rec
    # a child record without error_kind is re-classified from its error (review N-r4-2)
    assert sc.capture_failure_kind(child(_tb(INV))) == 'invariant'
    assert sc.capture_failure_kind(child(_tb('RuntimeError: Ledger overdraw', AREA))) == 'stocks'
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'


def test_g2_counts_an_sag_job_not_started_for_its_failed_capture(out_root):
    """K8 amendment 8 section 2 (review N-r6-2): an SAG job that sa_jobs never started because its capture failed is
    present and reported when the capture folder holds an attempt record -- a failed capture (capture_failed.json,
    killed included, or capture.json ok false) or an ok capture whose own record cannot serve the job (forecast_long
    shorter than H) -- so a deterministic SAG capture failure does not leave G-EB-2 INCOMPLETE forever.  An SAG job
    whose capture inputs are complete but which has not run, an ok capture that misses a file (unfinished folder), an
    SAG job without any capture record and an absent SAF job stay absent (INCOMPLETE); an SAG invariant violation in
    the capture still fails."""
    import sa_jobs
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    labels, caps, n_sag = _declared_outputs(tree)
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    sag_jobs = {j['label']: j for j in sa_jobs.declared_keyed_jobs(tree) if j['arm'] == 'SAG'}
    assert len(sag_jobs) == sc.SAG_JOBS_DECLARED and set(sag_jobs) <= set(labels)
    folder_of = lambda lb: Path(sag_jobs[lb]['template']).parent
    label = sorted(lb for lb in sag_jobs if lb.startswith('TL3_'))[0]
    job, folder = sag_jobs[label], folder_of(label)
    assert [lb for lb in sag_jobs if folder_of(lb) == folder] == [label]
    good = {'job': {'label': label, 'arm': 'SAG'}, 'ok': True, 'sa': {'end_step_calls': 450}}
    (sc.job_dir(tree, label) / 'summary.json').unlink()                   # sa_jobs never started it
    child = lambda err: {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': err}

    def g2_with(capture_json=None, capture_failed=None):
        for name, rec in (('capture.json', capture_json), ('capture_failed.json', capture_failed)):
            if (folder / name).exists():
                (folder / name).unlink()
            if rec is not None:
                (folder / name).write_text(json.dumps(rec), encoding='utf-8')
        return sa_gates.g2(si.Inputs(tree), None)
    # the capture failed (child record, SAG init failure in runtime code): the capture and its job are reported
    g = g2_with(capture_failed=dict(child(_tb(INIT)), error_kind='init', error_site='runtime'))
    assert sc.sag_capture_attempt(job).startswith('capture_failed.json')
    assert g['verdict'] == 'PASS' and _combine_with('G-EB-2', g) == 'PROMOTE_ELIGIBLE'
    assert g['items']['sag_reported']['value'] == 2 and [label, 'not_started'] in [r[:2] for r in
                                                                                    g['items']['sag_reported']['rows']]
    assert g['items']['declared_runs']['value'] == {'jobs': 344, 'captures': 394, 'sag_jobs': 23, 'absent_jobs': 0,
                                                    'absent_captures': 0}
    # a killed capture (parent-only record) and a child failure written to capture.json are attempt records too
    assert g2_with(capture_failed={'ok': False, 'exit': 1, 'error_kind': 'killed', 'child_record': False})[
        'verdict'] == 'PASS'
    g = g2_with(capture_json=child(_tb(INIT)))
    assert g['verdict'] == 'PASS' and sc.sag_capture_attempt(job).startswith('capture.json ok false')
    # an SAG invariant violation in the capture still fails G-EB-2
    assert g2_with(capture_failed=child(_tb(INV)))['verdict'] == 'FAIL'
    # no capture record at all: the capture and its job are absent -> INCOMPLETE
    g = g2_with()
    assert sc.sag_capture_attempt(job) is None
    assert g['verdict'] == 'INCOMPLETE' and g['items']['declared_runs']['value']['absent_jobs'] == 1
    assert any(label in m for m in g['missing'])
    # an ok capture that misses its template.pickle is an unfinished folder, not a failed capture: absent
    g = g2_with(capture_json={'ok': True, 'forecast_len': 3})
    assert sc.job_inputs_missing(job) == ['template.pickle'] and sc.sag_capture_attempt(job) is None
    assert g['verdict'] == 'INCOMPLETE' and g['items']['declared_runs']['value']['absent_jobs'] == 1
    # an ok capture with every job input: the job can start, it is merely not run yet -> absent (INCOMPLETE)
    (folder / 'template.pickle').write_bytes(b'x')
    assert int(job['H']) <= 3 and sc.job_inputs_missing(job) == [] and sc.sag_capture_attempt(job) is None
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'INCOMPLETE'
    _write_job(tree, label, good)
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    # an SAG H6 job whose ok capture records a forecast_long shorter than H cannot be started: reported
    h6 = sorted(lb for lb in sag_jobs if lb.endswith('_OBS_H6'))[0]
    job6, folder6 = sag_jobs[h6], folder_of(h6)
    assert int(job6['H']) == 6 and [lb for lb in sag_jobs if folder_of(lb) == folder6] == [h6]
    (folder6 / 'capture.json').write_text(json.dumps({'ok': True, 'forecast_len': 3, 'forecast_long_len': 3,
                                                      'forecast_long_prefix_equal': True}), encoding='utf-8')
    (folder6 / 'template.pickle').write_bytes(b'x')
    (folder6 / 'forecast_long.pickle').write_bytes(b'x')
    (sc.job_dir(tree, h6) / 'summary.json').unlink()
    assert sc.job_inputs_missing(job6) == ['forecast_long_len >= H']
    assert sc.sag_capture_attempt(job6).startswith('capture.json ok, its record cannot serve the job')
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'PASS' and [h6, 'not_started'] in [r[:2] for r in g['items']['sag_reported']['rows']]
    # review r8 N-r8-1: only a record that says so -- ok true and both forecast fields recorded -- is an attempt
    # record; an absent field or an absent ok key is not a record of failure: the label stays absent (INCOMPLETE)
    short = {'ok': True, 'forecast_len': 3, 'forecast_long_len': 3, 'forecast_long_prefix_equal': True}
    for rec in ({k: v for k, v in short.items() if k != 'forecast_long_len'},
                {k: v for k, v in short.items() if k != 'forecast_long_prefix_equal'},
                {k: v for k, v in short.items() if k != 'ok'},
                dict(short, forecast_long_prefix_equal=None), dict(short, forecast_long_len=True)):
        (folder6 / 'capture.json').write_text(json.dumps(rec), encoding='utf-8')
        assert sc.job_inputs_missing(job6) and sc.sag_capture_attempt(job6) is None, rec
        assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'INCOMPLETE', rec
    (folder6 / 'capture.json').write_text(json.dumps(dict(short, forecast_long_len=6, forecast_long_prefix_equal=False)),
                                          encoding='utf-8')                # recorded, long enough, not prefix-equal
    assert sc.job_inputs_missing(job6) == ['forecast_long_prefix_equal']
    assert sc.sag_capture_attempt(job6).startswith('capture.json ok, its record cannot serve the job')
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    (folder6 / 'capture.json').write_text(json.dumps(short), encoding='utf-8')
    (folder6 / 'forecast_long.pickle').unlink()                           # a missing file: unfinished, absent
    assert sc.sag_capture_attempt(job6) is None and sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'INCOMPLETE'
    _write_job(tree, h6, dict(good, job={'label': h6, 'arm': 'SAG'}))
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    # SAF: a job never started for its failed capture stays absent (judging arm: INCOMPLETE until rerun)
    saf = 'TL3_900_SAF_OBS_H3'
    (sc.job_dir(tree, saf) / 'summary.json').unlink()
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'INCOMPLETE' and any(saf in m for m in g['missing'])

def test_g2_truncated_capture_record_is_an_unreadable_row(out_root):
    """Review r8 N-r8-2: a truncated (or non-object) capture.json / capture_failed.json is an unreadable folder row
    in the report (INCOMPLETE, rerun), not a calculator exception; either arm (the record cannot tell what it was)."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    labels, caps, n_sag = _declared_outputs(tree)
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    for arm in ('SAF', 'SAG'):
        folder = next(Path(d) for d in caps if Path(d).name == arm)
        rel = str(folder.relative_to(sc.sa_out()))
        for name, text in (('capture.json', '{"ok": tr'), ('capture.json', '[1, 2]'),
                           ('capture_failed.json', '{"ok": false, "err')):
            (folder / 'capture.json').unlink(missing_ok=True)
            (folder / name).write_text(text, encoding='utf-8')
            g = sa_gates.g2(si.Inputs(tree), None)
            rows = g['items']['unreadable_runs']['rows']
            assert g['verdict'] == 'INCOMPLETE' and [r[0] for r in rows] == [rel], (arm, name, text)
            assert name in rows[0][2] and any(rel in m for m in g['missing'])
            (folder / name).unlink()
        (folder / 'capture.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
        assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'


def _valid_robs(seeds=sc.TL3M_SEEDS, status='valid'):
    """K8 amendment 13: R-obs validity records (sa_tl3m.py validity) for the TL3m seeds."""
    for s in seeds:
        sc.write_json(sc.validity_path(s), {'schema': sc.VALIDITY_SCHEMA, 'seed': s, 'status': status,
                                            'reasons': [] if status == 'valid' else ['synthetic']})


def _g14_captures(tree):
    ok = {'schema': sc.CAPTURE_SCHEMA, 'ok': True, 'metadata': {'stopline_approach_install_check': {'ok': True}}}
    folders = [sc.cap_dir(tree, 'ROBS61', T, 'SAF') for T in sc.ROBS61_T]
    folders += [sc.cap_dir(tree, 'FH', T, 'SAF', seed=s) for s in sc.FH_SEEDS for T in sc.GRID9]
    folders += [sc.cap_dir(tree, 'ROBS61', T, 'SAF', seed=s) for s in sc.TL3M_SEEDS if not sc.is_robs3(s)
                for T in sc.ROBS61_T]                                  # amendment 13: every R-obs seed
    _valid_robs()
    for d in folders:
        d.mkdir(parents=True, exist_ok=True)
        (d / 'capture.json').write_text(json.dumps(ok), encoding='utf-8')


def test_stale_capture_failure_is_ignored_and_a_killed_capture_is_incomplete(out_root):
    """Review r3 B-r3-3: a capture_failed.json beside capture.json is stale (G-EB-2 and I.cap read the capture); a
    capture_failed.json the child never wrote (no k8-sa-capture/v1 record, or child_record false) is 'killed' ->
    G-EB-2 unreadable and G-EB-14 (i) INCOMPLETE, never FAIL; a child-written failure still fails both."""
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    _declared_outputs(tree)
    _g14_captures(tree)
    args = type('A', (), {'unit_log': None})()
    d = sc.cap_dir(tree, 'ROBS61', 150, 'SAF')
    i_init = lambda: sa_gates.g14(si.Inputs(tree), args)['items']['i_init']['pass_']
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS' and i_init() is True
    for stale in ({'ok': False, 'exit': 1, 'error_kind': 'other', 'log_tail': '(killed)'},
                  {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error_kind': 'invariant', 'error': 'I4'}):
        (d / 'capture_failed.json').write_text(json.dumps(stale), encoding='utf-8')
        assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
        assert si.Inputs(tree).cap('ROBS61', 150, 'SAF')['ok'] is True and i_init() is True
    (d / 'capture.json').unlink()
    for killed in ({'ok': False, 'exit': 1, 'error_kind': 'other', 'log_tail': 'StoplineInvariantError in the tail'},
                   {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error_kind': 'killed', 'child_record': False}):
        (d / 'capture_failed.json').write_text(json.dumps(killed), encoding='utf-8')
        assert sc.capture_failure_kind(killed) == 'killed'
        g = sa_gates.g2(si.Inputs(tree), None)
        assert g['verdict'] == 'INCOMPLETE' and g['items']['unreadable_runs']['rows'][0][1] == 'killed'
        assert _combine_with('G-EB-2', g) == 'INCOMPLETE'
        I = si.Inputs(tree)
        assert I.cap('ROBS61', 150, 'SAF') is None and any('killed' in m for m in I.missing)
        g14 = sa_gates.g14(si.Inputs(tree), args)
        assert g14['items']['i_init']['pass_'] is None and 'ROBS61 150' in g14['missing']
    (d / 'capture_failed.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error_kind': 'other',
                                                       'error': _tb('ValueError: x')}), encoding='utf-8')
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'FAIL' and i_init() is False
    # amendment 7 section 2: a child record without a runtime traceback is a harness / infrastructure failure
    for rec in ({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error_kind': 'other', 'error': 'ValueError'},
                {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb('ValueError: x', HARNESS)},
                {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb('ValueError: x'),
                 'harness_stage_error': 'Traceback ... demand_from_state'}):
        (d / 'capture_failed.json').write_text(json.dumps(rec), encoding='utf-8')
        g = sa_gates.g2(si.Inputs(tree), None)
        assert g['verdict'] == 'INCOMPLETE' and i_init() is None, rec
        assert [r[0] for r in g['items']['unreadable_runs']['rows']] == [str(d.relative_to(sc.sa_out()))]


def test_capture_attempt_sets_aside_an_old_failure_and_marks_a_killed_child(out_root, monkeypatch):
    """Review r3 B-r3-3, sa_capture.py: a new attempt first moves an earlier capture_failed.json to
    stale_capture_failed_<k>.json (never merged into the new record); a child that wrote no record gives error_kind
    'killed' whatever the log tail says; a child record is kept and classified from tail + error."""
    import sa_capture
    from types import SimpleNamespace
    monkeypatch.setattr(sc.c, 'adapter_args', lambda replay, out, tuning=None: (2700, []))
    monkeypatch.setattr(sc.c, 'base_env', lambda *a, **k: {})
    plan = []

    def fake_run(cmd, log, env, cwd=None):
        out = Path(cmd[3])
        mode = plan.pop(0)
        Path(log).write_text('adapter output\n' + ('StoplineInvariantError: I4 (tail of a stopped run)\n'
                                                   if mode == 'killed' else ''), encoding='utf-8')
        if mode == 'child_error':
            (out / 'capture_failed.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': False,
                                                                 'error': 'ValueError: storage -0.5'}), encoding='utf-8')
        elif mode == 'ok':
            (out / 'capture.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': True}), encoding='utf-8')
        return (4 if mode == 'child_error' else 0 if mode == 'ok' else 1), 0.1
    monkeypatch.setattr(sc.c, 'run', fake_run)
    args = SimpleNamespace(tree='k86', arm='SAF', kind='tl3', dry_run=False, fh_disabled=False)
    row = dict(harness='TL3', T=2700, seed=31, frame_T=2700)
    tuning = {'path': 'tuning.json', 'sha256': None}
    out = sc.cap_dir('k86', 'TL3', 2700, 'SAF')
    out.mkdir(parents=True)
    old = {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': 'StoplineRouteError: old attempt', 'error_kind': 'route'}
    (out / 'capture_failed.json').write_text(json.dumps(old), encoding='utf-8')
    plan.append('killed')
    sa_capture.run_capture(args, row, tuning)
    rec = json.loads((out / 'capture_failed.json').read_text(encoding='utf-8'))
    assert rec['error_kind'] == 'killed' and rec['child_record'] is False and rec['log_error_kind'] == 'invariant'
    assert 'error' not in rec and rec['stale_failure_set_aside'] == 'stale_capture_failed_1.json'
    assert json.loads((out / 'stale_capture_failed_1.json').read_text(encoding='utf-8')) == old
    assert sc.capture_failure_kind(rec) == 'killed'
    plan.append('child_error')
    sa_capture.run_capture(args, row, tuning)
    rec = json.loads((out / 'capture_failed.json').read_text(encoding='utf-8'))
    assert rec['child_record'] is True and rec['error'] == 'ValueError: storage -0.5' and rec['exit'] == 4
    assert rec['error_kind'] == 'other' == sc.capture_failure_kind(rec)              # tail + error, as before
    assert rec['stale_failure_set_aside'] == 'stale_capture_failed_2.json'
    plan.append('ok')
    sa_capture.run_capture(args, row, tuning)
    assert (out / 'capture.json').is_file() and not (out / 'capture_failed.json').exists()
    assert sorted(p.name for p in out.glob('stale_capture_failed_*.json')) == ['stale_capture_failed_1.json',
                                                                              'stale_capture_failed_2.json',
                                                                              'stale_capture_failed_3.json']


def test_g13_needs_a_valid_instrument_on_every_judged_run(out_root):
    """Review r3 B-r3-4: hook_errors / patch_errors > 0, an SA hook error, a setup error file, a missing
    _movement_capacity_flow patch, a missing plant-module line patch or a hooks file without the line expectation make
    the judged run INCOMPLETE (a dropped read cannot make plant reads 0); plant reads > 0 still fail; BASE runs are
    reported as the positive control only."""
    tree = 'k86'
    judged = ['full_2700_SAF', 'full_4950_SAF', 'job_' + sc.G13_JUDGED_HOOK_JOB, 'job_TL3_900_SAF_OBS_H3_HOOK']
    args = G13_ARGS()
    _g13_finished(tree, judged)

    def g13(runs, expected=None, raw=None):
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', raw or _hooks(runs, expected))
        return sa_gates.g13(si.Inputs(tree), args)
    good = {n: _hook_run() for n in judged}
    g = g13({**good, 'full_2700_BASE': _hook_run(plant=7.0),
             'full_4950_BASE': _hook_run(plant=2.0, fold_extra={'patched': []})})
    assert g['verdict'] == 'PASS' and g['items']['plant_reads']['invalid_instrument'] == {}
    ctrl = g['items']['base_plant_reads_control']
    assert ctrl['judged'] is True and ctrl['pass_'] is True and ctrl['value'][2700]['plant_reads'] == 7.0
    assert ctrl['value'][4950]['instrument_problems'] == ['no patch ' + sa_hookcount.CAPFLOW_PATCH]
    broken = {'hook_errors': dict(fold_extra={'hook_errors': 5000.0}),
              'patch_errors': dict(fold_extra={'patch_errors': 1}),
              'errors': dict(fold_extra={'errors': ["AttributeError('frame')"]}),
              'setup': dict(setup_errors=["RuntimeError('no free sys.monitoring tool id')"]),
              'no capflow patch': dict(fold_extra={'patched': ['evaluation.controllers.stopline_approach']}),
              # amendment 7 section 3: the S3 / site hook files of the same run and the final records
              'S3 hook_errors': dict(s3_extra={'hook_errors': 5000.0}),
              'S3 patch_errors': dict(s3_extra={'patch_errors': 2}),
              'S3 errors': dict(s3_extra={'errors': ['UFA:887 KeyError(x)']}),
              'S3 non-final': dict(s3_extra={'non_final': ['hook_4242.json']}),
              'SA non-final': dict(fold_extra={'non_final': ['sahook_4242.json']})}
    for name in judged:
        for what, kw in broken.items():
            g = g13({**good, name: _hook_run(**kw)})
            assert g['verdict'] == 'INCOMPLETE' and g['items']['plant_reads']['pass_'] is None, (name, what)
            assert list(g['items']['plant_reads']['invalid_instrument']) == [name]
            assert any('invalid instrument' in m and name in m for m in g['missing'])
            assert g13({**good, name: _hook_run(plant=1.0, **kw)})['verdict'] == 'FAIL'
    no_fold = _hook_run()
    del no_fold['fold_extra']
    assert g13({**good, 'full_2700_SAF': no_fold})['verdict'] == 'INCOMPLETE'
    for key in ('s3_extra', 'fold_extra'):                  # a hooks json without the final flags (before amendment 7)
        old = _hook_run()
        del old[key]['non_final']
        g = g13({**good, 'job_' + sc.G13_JUDGED_HOOK_JOB: old})
        assert g['verdict'] == 'INCOMPLETE' and any('final flags not recorded' in m for m in g['missing'])
    # the review probe: every judged run with hook_errors 5000, 10 errors and a setup error -> INCOMPLETE, not PASS
    bad = _hook_run(fold_extra={'hook_errors': 5000.0, 'errors': ["AttributeError('frame has no cfg')"] * 10},
                    setup_errors=["RuntimeError('sys.monitoring tool id in use')"])
    assert g13({n: bad for n in judged})['verdict'] == 'INCOMPLETE'
    # plant module line patches: required where the source has capacity token lines
    exp = {**{m: 0 for m in sa_hookcount.PLANT_MODULES}, 'urban_flow_accounting': 2}
    assert g13(good, exp)['verdict'] == 'INCOMPLETE'
    with_lines = {n: _hook_run(fold_extra={'patched': VALID_PATCHED + ['evaluation.controllers.urban_flow_accounting:2 '
                                                                       'lines']}) for n in judged}
    assert g13(with_lines, exp)['verdict'] == 'PASS'
    assert g13(with_lines, {**exp, 'urban_flow_accounting': 3})['verdict'] == 'INCOMPLETE'
    assert g13(good, {**exp, 'urban_flow_accounting': None})['verdict'] == 'INCOMPLETE'
    assert g13(None, raw={'schema': 'k8-sa-hooks/v1', 'runs': good})['verdict'] == 'INCOMPLETE'   # no expectation


# ------------------------------------------------------------------------------------------------ review r4 (round 3)
def _missing_file_traceback(path):
    """The traceback text a worker leaves when Path(path).read_bytes() finds no file (real Python wording)."""
    import traceback
    try:
        Path(path).read_bytes()
    except FileNotFoundError:
        return traceback.format_exc()
    raise AssertionError('file exists: %s' % path)


def test_job_without_capture_inputs_is_not_started_and_never_fails(out_root, monkeypatch, capsys):
    """Review r4 B-r4-1: sa_jobs.run_job starts no worker while the job's capture inputs are missing (capture.json,
    template.pickle, forecast_long.pickle for H beyond the captured forecast): the label stays absent -> G-EB-2
    INCOMPLETE.  A summary that ended on FileNotFoundError of the job's own template / forecast_long is unreadable in
    G-EB-2 and an absent job for every other reader (never FAIL / STOP); once the inputs exist it is set aside (hook/
    too) and the job rerun.  The review probe (killed SAF capture + its job's worker summary) is INCOMPLETE."""
    import pickle
    import sa_jobs
    from types import SimpleNamespace
    tree = 'k86'
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _fake_ref(EVENTS14))
    labels, caps, _ = _declared_outputs(tree)
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    launched = []

    def fake_run(cmd, log, env, cwd=None):                    # stands in for the worker process (never started)
        job = pickle.loads(Path(cmd[-2]).read_bytes())
        launched.append(job['label'])
        Path(cmd[-1]).with_name('summary.json').write_text(json.dumps(
            {'job': {k: job[k] for k in ('label', 'arm', 'template', 'forecast_long')}, 'ok': True,
             'sa': {'end_step_calls': 450}}), encoding='utf-8')
        return 0, 0.1
    monkeypatch.setattr(sc.c, 'run', fake_run)
    monkeypatch.setattr(sc.c, 'base_env', lambda *a, **k: {'PYTHONPATH': 'a;b'})
    args = SimpleNamespace(tree=tree, dry_run=False, plan_only=False, hooks=False, chain='site', s3_table=None)

    def mk(H):
        return sa_jobs.base_job(SimpleNamespace(tree=tree, labels_only=True, hooks=False), 'TL3', 2700, 'SAF', 'OBS', H)
    job = mk(3)
    label, d, cap = job['label'], sc.job_dir(tree, job['label']), Path(job['template']).parent
    assert label == 'TL3_2700_SAF_OBS_H3' and label in labels and str(cap) in caps
    # (1) killed SAF capture (no child record): G-EB-2 INCOMPLETE (B-r3-3); run_job starts nothing, writes nothing
    (d / 'summary.json').unlink()
    (cap / 'capture.json').unlink()
    (cap / 'capture_failed.json').write_text(json.dumps({'ok': False, 'exit': 1, 'error_kind': 'killed',
                                                        'child_record': False}), encoding='utf-8')
    assert sc.job_inputs_missing(job) == ['capture.json', 'template.pickle']
    sa_jobs.run_job(args, job)
    assert launched == [] and not (d / 'summary.json').exists() and 'SA_JOB_SKIP_NO_CAPTURE ' + label in \
        capsys.readouterr().out
    g = sa_gates.g2(si.Inputs(tree), None)
    assert g['verdict'] == 'INCOMPLETE' and _combine_with('G-EB-2', g) == 'INCOMPLETE'
    # (2) the review probe: the dependent job's worker summary (FileNotFoundError of its own template) is unreadable,
    # with or without the input paths in the summary; every other reader sees an absent job
    tb = _missing_file_traceback(cap / 'template.pickle')
    assert sa_worker.error_kind(tb) == 'other'
    own = {'label': label, 'arm': 'SAF', 'template': job['template'], 'forecast_long': job['forecast_long']}
    hand = ('Traceback (most recent call last):\n  File "sa_worker.py", line 708, in main\n'
            "FileNotFoundError: [Errno 2] No such file or directory: '%s'" % (cap / 'template.pickle'))  # review probe
    for rec, err in (({'label': label, 'arm': 'SAF'}, tb), (own, tb), ({'label': label, 'arm': 'SAF'}, hand)):
        _write_job(tree, label, {'job': rec, 'ok': False, 'error_kind': 'other', 'error': err})
        g = sa_gates.g2(si.Inputs(tree), None)
        assert g['verdict'] == 'INCOMPLETE' and _combine_with('G-EB-2', g) == 'INCOMPLETE'
        assert g['items']['other_failures']['pass_'] is None
        assert [r[1] for r in g['items']['unreadable_runs']['rows'] if r[0] == label] == ['input_absent']
        I = si.Inputs(tree)
        assert I.job(label) is None and any(m.startswith('job input absent') for m in I.missing)
        assert sc.job_summary(tree, label) is None
    # a FileNotFoundError of anything else is no missing input: raised in harness code (this file, under k8_gates/)
    # it is a harness failure -> INCOMPLETE (amendment 7 section 2); raised in runtime code it fails
    for path, rec in ((sc.sa_out() / 'tuning' / 'config_absent.json', {'label': label, 'arm': 'SAF'}),
                      (sc.cap_dir(tree, 'TL3', 900, 'SAF') / 'template.pickle', own)):
        _write_job(tree, label, {'job': rec, 'ok': False, 'error_kind': 'other',
                                 'error': _missing_file_traceback(path)})
        g = sa_gates.g2(si.Inputs(tree), None)
        assert g['verdict'] == 'INCOMPLETE' and g['items']['other_failures']['pass_'] is None, path
        assert [r[1] for r in g['items']['unreadable_runs']['rows'] if r[0] == label] == ['other']
        assert si.Inputs(tree).job(label) is not None
        runtime = _tb("FileNotFoundError: [Errno 2] No such file or directory: '%s'" % path)
        _write_job(tree, label, {'job': rec, 'ok': False, 'error_kind': 'other', 'error': runtime})
        g = sa_gates.g2(si.Inputs(tree), None)
        assert g['verdict'] == 'FAIL' and g['items']['other_failures']['pass_'] is False, path
    # (3) still no inputs: the input-absent summary is kept and skipped; once the capture exists it is set aside
    # (hook/ too) and the job rerun; plan-only moves nothing; an ordinary summary keeps the label skipped
    _write_job(tree, label, {'job': own, 'ok': False, 'error_kind': 'other', 'error': tb})
    (d / 'hook').mkdir()
    sa_jobs.run_job(args, job)
    assert launched == [] and json.loads((d / 'summary.json').read_text(encoding='utf-8'))['ok'] is False
    (cap / 'capture_failed.json').unlink()
    (cap / 'capture.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': True, 'forecast_len': 3}),
                                      encoding='utf-8')
    (cap / 'template.pickle').write_bytes(b'template')
    assert sc.job_inputs_missing(job) == []
    sa_jobs.run_job(SimpleNamespace(**{**vars(args), 'plan_only': True}), job)
    assert launched == [] and (d / 'summary.json').is_file() and not (d / 'stale_input_absent_1.json').exists()
    sa_jobs.run_job(args, job)
    assert launched == [label] and json.loads((d / 'summary.json').read_text(encoding='utf-8'))['ok'] is True
    assert (d / 'stale_input_absent_1.json').is_file() and (d / 'stale_hook_1').is_dir() and not (d / 'hook').exists()
    sa_jobs.run_job(args, job)
    assert launched == [label] and 'SA_JOB_SKIP ' + label in capsys.readouterr().out
    assert sa_gates.g2(si.Inputs(tree), None)['verdict'] == 'PASS'
    # (4) forecast_long.pickle: needed when H exceeds the captured forecast (capture.json forecast_len, else H > 3)
    long_job = mk(42)
    (sc.job_dir(tree, long_job['label']) / 'summary.json').unlink()             # a declared job (long family)
    long_need = ['forecast_long.pickle', 'forecast_long_len >= H', 'forecast_long_prefix_equal']
    assert Path(long_job['template']).parent == cap and sc.job_inputs_missing(long_job) == long_need
    sa_jobs.run_job(args, long_job)
    assert launched == [label] and not (sc.job_dir(tree, long_job['label']) / 'summary.json').exists()
    (cap / 'forecast_long.pickle').write_bytes(b'long')
    assert sc.job_inputs_missing(long_job) == long_need[1:]            # amendment 7 section 4: length and prefix
    good_long = {'schema': sc.CAPTURE_SCHEMA, 'ok': True, 'forecast_len': 3, 'forecast_long_len': 42,
                 'forecast_long_prefix_equal': True}
    (cap / 'capture.json').write_text(json.dumps(good_long), encoding='utf-8')
    assert sc.job_inputs_missing(long_job) == []
    (cap / 'forecast_long.pickle').unlink()
    h6 = dict(long_job, H=6)
    (cap / 'capture.json').write_text(json.dumps({'ok': True, 'forecast_len': 6}), encoding='utf-8')
    assert sc.job_inputs_missing(h6) == []
    (cap / 'capture.json').write_text(json.dumps({'ok': True}), encoding='utf-8')
    assert sc.job_inputs_missing(h6) == long_need and sc.job_inputs_missing(job) == []
    (cap / 'capture.json').write_text('{"ok": tr', encoding='utf-8')               # truncated record
    assert sc.job_inputs_missing(job) == ['capture.json']
    capsys.readouterr()
    sa_jobs.run_job(SimpleNamespace(**{**vars(args), 'dry_run': True}), long_job)
    assert 'inputs=MISSING capture.json,' + ','.join(long_need) in capsys.readouterr().out


def test_worker_summary_names_the_job_inputs():
    """Review r4 B-r4-1: sa_worker.to_summary records the job's own template / forecast_long paths (the paths
    sc.job_input_absent compares a FileNotFoundError with)."""
    job = {'label': 'TL3_2700_SAF_OBS_H3', 'arm': 'SAF', 'template': 'C:/x/template.pickle',
           'forecast_long': 'C:/x/forecast_long.pickle'}
    old = sa_worker.STATE.get('job')
    sa_worker.STATE['job'] = job
    try:
        s = sa_worker.to_summary({'error': 'boom', 'steps': {}, 'cap': {}})
    finally:
        sa_worker.STATE['job'] = old
    assert s['job']['template'] == job['template'] and s['job']['forecast_long'] == job['forecast_long']


def test_g13_needs_finished_judged_runs(out_root):
    """Review r4 B-r4-2: a judged run counts only when it ran to its end -- full run.json exit 0 with an action JSON,
    hook job summary ok with SA.end_step called; otherwise INCOMPLETE (the hook's atexit record of a run that stopped
    before its rollout shows 'patched, 0 errors, 0 plant reads').  Plant reads > 0 still fail."""
    tree = 'k86'
    judged = ['full_2700_SAF', 'full_4950_SAF', 'job_' + sc.G13_JUDGED_HOOK_JOB, 'job_TL3_900_SAF_OBS_H3_HOOK']
    args = G13_ARGS()

    def g13(plant_run=None):
        runs = {n: _hook_run(plant=1.0 if n == plant_run else 0.0) for n in judged}
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks(runs))
        return sa_gates.g13(si.Inputs(tree), args)
    g = g13()
    assert g['verdict'] == 'INCOMPLETE' and set(g['items']['plant_reads']['run_not_finished']) == set(judged)
    _g13_finished(tree, judged)
    assert g13()['verdict'] == 'PASS'
    full = sc.full_dir(tree, 2700, 'SAF', 'hooks') / 'run.json'
    job = sc.job_dir(tree, sc.G13_JUDGED_HOOK_JOB) / 'summary.json'
    good = {full: json.loads(full.read_text(encoding='utf-8')), job: json.loads(job.read_text(encoding='utf-8'))}
    names = {full: 'full_2700_SAF', job: 'job_' + sc.G13_JUDGED_HOOK_JOB}
    cases = [(full, {'exit': 1}), (full, {'exit': None}), (full, {'action_json_bytes': None}),
             (full, {'action_json_bytes': 0}), (job, {'ok': False, 'error_kind': 'other', 'error': 'ValueError'}),
             (job, {'sa': None}), (job, {'sa': {'end_step_calls': 0}}),
             (job, {'ok': False, 'error_kind': 'other', 'job': {'label': sc.G13_JUDGED_HOOK_JOB, 'arm': 'SAF'},
                    'error': _missing_file_traceback(sc.cap_dir(tree, 'TL3', 2700, 'SAF') / 'template.pickle')})]
    for path, change in cases:
        path.write_text(json.dumps({**good[path], **change}), encoding='utf-8')
        g = g13()
        assert g['verdict'] == 'INCOMPLETE' and g['items']['plant_reads']['pass_'] is None, change
        assert list(g['items']['plant_reads']['run_not_finished']) == [names[path]], change
        assert any('not finished' in m and names[path] in m for m in g['missing'])
        assert g13(plant_run=names[path])['verdict'] == 'FAIL'                     # a read made still fails
        path.write_text(json.dumps(good[path]), encoding='utf-8')
    for path in (full, job):
        path.unlink()
        assert g13()['verdict'] == 'INCOMPLETE'
        path.write_text(json.dumps(good[path]), encoding='utf-8')
    assert g13()['verdict'] == 'PASS'
    # the review probe: full 2700 / 4950 SAF exit 1 without an action JSON, the judged hook job ok False, hook records
    # valid with 0 plant reads -> INCOMPLETE (was PASS)
    for T in sc.DP_FULL_T:
        sc.write_json(sc.full_dir(tree, T, 'SAF', 'hooks') / 'run.json', {'T': T, 'arm': 'SAF', 'exit': 1, 'wall': 3.0})
    _write_job(tree, sc.G13_JUDGED_HOOK_JOB, {'job': {'label': sc.G13_JUDGED_HOOK_JOB, 'arm': 'SAF'}, 'ok': False,
                                              'error_kind': 'other', 'error': 'ValueError: storage -0.5'})
    g = g13()
    assert g['verdict'] == 'INCOMPLETE' and _combine_with('G-EB-13', g) == 'INCOMPLETE'
    assert set(g['items']['plant_reads']['run_not_finished']) == set(judged[:3])
    # BASE positive control: judged on its plant reads (amendment 7 section 3); its run problems are reported
    sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks({**{n: _hook_run() for n in judged},
                                                               'full_2700_BASE': _hook_run(plant=3.0)}))
    ctrl = sa_gates.g13(si.Inputs(tree), args)['items']['base_plant_reads_control']
    assert ctrl['judged'] is True and ctrl['pass_'] is True
    assert ctrl['value'][2700]['run_problems'] == ['run.json absent']


def _g14_rec(**over):
    rec = {'schema': sc.CAPTURE_SCHEMA, 'ok': True,
           'metadata': {'stopline_approach_install_check': {'ok': True},
                        'stopline_approach_initial': {'posthead_veh': 2.0, 'posthead_rehomed_veh': 0.0,
                                                      'posthead_receiver_shortfall_veh': 0.0,
                                                      'posthead_rehome_shortfall_veh': 0.0}},
           'probes': {'provenance': {'127': {'storage:SC1001_to_SC1002': 1.0, 'storage:SC1001_to_SC2002': 1.0},
                                     '10695': {'storage:SC1001_to_SC2002': 2.0}},
                      'records': {'n10695': 2}}}
    rec.update(over)
    return {k: v for k, v in rec.items() if v is not None}


def test_g14_rows_without_probes_or_metadata_are_incomplete(out_root):
    """Review r4 B-r4-3: a capture whose probe block raised (probes_error, no probes) or that lacks
    metadata.stopline_approach_initial.posthead_veh / probes.records.n10695 leaves its (ii)(iii) row INCOMPLETE
    (never PASS on 0 vehicles past the head, never FAIL on > 0); an ok capture without its metadata block is
    INCOMPLETE in (i); metadata without install_check is still an initialization failure."""
    tree = 'k86'
    args = type('A', (), {'unit_log': None})()
    folders = [sc.cap_dir(tree, 'ROBS61', T, 'SAF') for T in sc.ROBS61_T]
    folders += [sc.cap_dir(tree, 'FH', T, 'SAF', seed=s) for s in sc.FH_SEEDS for T in sc.GRID9]
    folders += [sc.cap_dir(tree, 'ROBS61', T, 'SAF', seed=s) for s in (43, 47) for T in sc.ROBS61_T]   # amendment 13
    _valid_robs()

    def write(rec, only=None):
        for f in ([only] if only is not None else folders):
            f.mkdir(parents=True, exist_ok=True)
            (f / 'capture.json').write_text(json.dumps(rec), encoding='utf-8')

    def items():
        g = sa_gates.g14(si.Inputs(tree), args)
        return g['items']['i_init']['pass_'], g['items']['ii_iii_posthead']['pass_'], g
    write(_g14_rec())
    assert items()[:2] == (True, True)
    # the review probe: probes failed on every capture (probes_error, no probes) -> (ii)(iii) INCOMPLETE, (i) PASS
    err = 'Traceback (most recent call last):\nAttributeError: no lane_offramp_runtime'
    write(_g14_rec(probes=None, probes_error=err))
    i, ii, g = items()
    assert (i, ii) == (True, None) and g['verdict'] == 'INCOMPLETE'
    assert any('capture probes failed: AttributeError' in m for m in g['missing'])
    assert all(r[-1] is None for r in g['items']['ii_iii_posthead']['rows'])
    bad_post = _g14_rec(probes=None, probes_error=err)
    bad_post['metadata']['stopline_approach_initial']['posthead_veh'] = 5.0          # > 0 vehicles past the head
    write(bad_post)
    assert items()[:2] == (True, None)                                                  # not FAIL -> STOP
    write(_g14_rec())
    one = folders[70]
    for rec in (_g14_rec(probes_error=err), _g14_rec(probes={'records': {'n10695': 2}}),
                _g14_rec(probes={'provenance': {}, 'records': {}}),
                _g14_rec(metadata={'stopline_approach_install_check': {'ok': True}}),
                _g14_rec(metadata={'stopline_approach_install_check': {'ok': True},
                                   'stopline_approach_initial': {'packets': 3.0}})):
        write(rec, one)
        i, ii, g = items()
        assert i is True and ii is None and g['verdict'] == 'INCOMPLETE', rec
        assert sum(1 for r in g['items']['ii_iii_posthead']['rows'] if r[-1] is None) == 1
    # (i): an ok capture without its metadata block is unreadable; metadata without install_check fails
    write(_g14_rec(metadata=None), folders[3])
    i, ii, g = items()
    assert i is None and any('capture metadata absent' in m for m in g['missing'])
    write(_g14_rec())
    write(_g14_rec(metadata={'stopline_approach_initial': {'posthead_veh': 2.0}}), folders[80])
    assert items()[0] is False
    # a readable row still fails on a mismatch
    write(_g14_rec())
    mism = _g14_rec()
    mism['metadata']['stopline_approach_initial']['posthead_veh'] = 3.0
    write(mism, folders[10])
    assert items()[:2] == (True, False)
    # amendment 7 section 1: 3 vehicles past the head, 1 kept on 127 for want of receiver room -> receivers hold 2
    kept = _g14_rec()
    kept['metadata']['stopline_approach_initial'].update(posthead_veh=3.0, posthead_receiver_shortfall_veh=1.0)
    write(kept, folders[10])
    i, ii, g = items()
    assert (i, ii) == (True, True)
    rep = g['items']['posthead_shortfall_report']                 # the frequency is reported, never judged
    assert rep['judged'] is False and rep['value']['captures_with_shortfall'] == 1
    assert rep['value']['kept_veh_total'] == 1.0 and rep['rows'] == [['robs_1500', 1.0, 0.0]]
    kept['metadata']['stopline_approach_initial']['posthead_receiver_shortfall_veh'] = 0.5
    write(kept, folders[10])
    assert items()[:2] == (True, False)
    del kept['metadata']['stopline_approach_initial']['posthead_receiver_shortfall_veh']
    write(kept, folders[10])
    i, ii, g = items()
    assert (i, ii) == (True, None) and any('posthead_receiver_shortfall_veh absent' in m for m in g['missing'])
    # amendment 8 section 1: 0.5 of the 10695 share kept as a lane 3 head packet (reported in both keys); the 127
    # receivers still hold |A| = 2, 10695 holds 1.5 in its receiver + the kept 0.5 = its 2 vehicles
    rehome = _g14_rec()
    rehome['metadata']['stopline_approach_initial'].update(posthead_receiver_shortfall_veh=0.5,
                                                           posthead_rehome_shortfall_veh=0.5)
    rehome['probes']['provenance']['10695'] = {'storage:SC1001_to_SC2002': 1.5, 'movement:SC1001_W_to_N_SC2002': 0.5}
    write(_g14_rec())
    write(rehome, folders[10])
    i, ii, g = items()
    assert (i, ii) == (True, True)
    rep = g['items']['posthead_shortfall_report']
    assert rep['value']['kept_10695_veh_total'] == 0.5 and rep['rows'] == [['robs_1500', 0.5, 0.5]]
    rehome['probes']['provenance']['10695'] = {'storage:SC1001_to_SC2002': 2.0}     # the kept share also booked
    write(rehome, folders[10])
    assert items()[:2] == (True, False)
    rehome['probes']['provenance']['10695'] = {'storage:SC1001_to_SC2002': 1.5}     # the kept N queue not on 10695
    write(rehome, folders[10])
    assert items()[:2] == (True, False)
    rehome['probes']['provenance']['10695'] = {'storage:SC1001_to_SC2002': 1.5, 'movement:SC1001_W_to_N_SC2002': 0.5}
    rehome['metadata']['stopline_approach_initial']['posthead_rehome_shortfall_veh'] = 0.0   # read as an (a) share
    write(rehome, folders[10])
    assert items()[:2] == (True, False)
    del rehome['metadata']['stopline_approach_initial']['posthead_rehome_shortfall_veh']
    write(rehome, folders[10])
    i, ii, g = items()
    assert (i, ii) == (True, None) and any('posthead_rehome_shortfall_veh absent' in m for m in g['missing'])
    # (i) on a failed capture (amendment 7 section 2): FAIL only with a runtime traceback recorded by the child
    write(_g14_rec())
    (folders[5] / 'capture.json').unlink()
    for rec, want in (({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb(INIT)}, False),
                      ({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb(INIT, HARNESS)}, None),
                      ({'schema': sc.CAPTURE_SCHEMA, 'ok': False}, None)):
        (folders[5] / 'capture_failed.json').write_text(json.dumps(rec), encoding='utf-8')
        assert items()[0] is want, rec


# ------------------------------------------------------------------------------------------------ amendment 7
def test_one_failure_classification_table():
    """Amendment 7 section 2 (review N-r4-2): one table (sa_errors) for the worker, the capture child and parent and
    the gates; the site is the innermost project frame of the child's traceback (standard library / installed
    packages skipped; runtime = evaluation/, vendor/, runtime-imported diagnostics/ modules; harness = k8_gates/)."""
    import sa_capture
    import sa_errors
    assert sa_worker.error_kind is sa_errors.error_kind and sa_capture.error_kind is sa_errors.error_kind
    assert sc.error_kind is sa_errors.error_kind and sc.INVARIANT_KINDS == ('invariant', 'route', 'stocks')
    for text, kind in ((INV, 'invariant'), ('x StoplineRouteError: I10', 'route'), (INIT, 'init'),
                       ('StoplineConfigError: c', 'config'), ('in assert_stocks', 'stocks'),
                       ('RuntimeError: ModelAreaLedger overdraw', 'stocks'), ('ValueError: v', 'other'), ('', None),
                       (None, None)):
        assert sa_errors.error_kind(text) == kind, text
    for path, site in ((RUNTIME_SA, 'runtime'), ('C:\\r\\vendor\\NumSim-mine\\src\\models\\urban_queue_model.py', 'runtime'),
                       ('D:/r/diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py',
                        'runtime'),
                       (HARNESS, 'harness'), ('D:/r/diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_cap_child.py', 'harness'),
                       ('D:/r/diagnostics/sdmpc_n31_20260924/k8_gates/site/sitecustomize.py', 'harness'),
                       ('sa_worker.py', 'harness'),
                       ('C:/Python312/Lib/site-packages/numpy/core/fromnumeric.py', None),
                       ('C:/Python312/Lib/runpy.py', None), ('<frozen runpy>', None), ('<string>', None)):
        assert sa_errors.frame_site(path) == site, path
    numpy_inside = _tb('ValueError: shape').replace(
        'f\n    raise Error(message)\n',
        'f\n    np.sum(x)\n  File "C:/Python312/Lib/site-packages/numpy/core/fromnumeric.py", line 3, in sum\n'
        '    raise ValueError\n')
    assert sa_errors.error_site(numpy_inside) == 'runtime'               # numpy raised under runtime code
    assert sa_errors.error_site(_tb('KeyError: x', HARNESS)) == 'harness'
    assert sa_errors.error_site('ValueError: no traceback') is None
    wrapped = ('Traceback (most recent call last):\n  File "%s", line 765, in main\n    raise RuntimeError(...)\n'
               'RuntimeError: summary failed: %s' % (HARNESS, _tb(INV)))
    assert sa_errors.error_site(wrapped) == 'runtime'                    # the recorder's inner runtime traceback
    assert sa_errors.classify(_tb(INIT)) == ('init', 'runtime')
    # a process log: only the traceback that ends the run counts
    log = 'adapter start\n' + _tb(INV)
    assert sa_errors.log_error_site(log) == 'runtime'
    assert sa_errors.log_error_site(log + 'SA_CAPTURE_FAILED exception\n') == 'runtime'
    assert sa_errors.log_error_site(log + '\n'.join('decision step %d' % k for k in range(20))) is None
    assert sa_errors.log_error_site('adapter start\nkilled\n') is None
    assert sa_errors.log_error_site(_tb('KeyError: x', HARNESS)) == 'harness'


def test_worker_summary_and_capture_record_carry_the_child_classification(out_root):
    """Amendment 7 section 2: sa_worker.to_summary and the capture parent keep the child's own kind / site (computed
    on the full traceback); record_site prefers it; the capture child's harness stage is 'harness'."""
    import sa_capture
    old = sa_worker.STATE.get('job')
    sa_worker.STATE['job'] = {'label': 'TL3_2700_SAF_OBS_H3', 'arm': 'SAF'}
    try:
        long_tb = _tb('evaluation.controllers.control_area_objective.MembershipError: area cohort/model stock '
                      'mismatch: ' + 'x' * 5000, AREA)
        s = sa_worker.to_summary({'error': long_tb, 'steps': {}, 'cap': {}})
        assert (s['error_kind'], s['error_site']) == ('other', 'runtime') and len(s['error']) == 2000
        assert sa_errors_site_of_text(s['error']) is None                  # the kept tail alone has no frame...
        assert sc.record_site(s) == 'runtime' and sc.failed_in_runtime(s)   # ...the child's own site counts
        s = sa_worker.to_summary({'error': _tb('KeyError: blocks', HARNESS), 'steps': {}, 'cap': {}})
        assert (s['error_kind'], s['error_site']) == ('other', 'harness') and not sc.failed_in_runtime(s)
        assert sa_worker.to_summary({'steps': {}, 'cap': {}})['error_site'] is None
    finally:
        sa_worker.STATE['job'] = old
    out = sc.cap_dir('k86', 'TL3', 2700, 'SAF')
    out.mkdir(parents=True)
    (out / 'capture_failed.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': 'tail',
                                                         'error_kind': 'stocks', 'error_site': 'runtime'}),
                                             encoding='utf-8')
    rec = sa_capture.failure_record(out, 4, 1.0)
    assert (rec['error_kind'], rec['error_site'], rec['child_record']) == ('stocks', 'runtime', True)
    (out / 'capture_failed.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb(INIT),
                                                         'harness_stage_error': 'Traceback ...'}), encoding='utf-8')
    rec = sa_capture.failure_record(out, 4, 1.0)
    assert rec['error_site'] == 'harness' and not sc.failed_in_runtime(rec)
    (out / 'capture_failed.json').write_text('{"schema": "k8-sa', encoding='utf-8')     # child stopped mid-write
    rec = sa_capture.failure_record(out, 1, 1.0)
    assert rec['error_kind'] == 'killed' and rec['child_record'] is False
    src = (SA / 'sa_cap_child.py').read_text(encoding='utf-8')
    assert "REC['error_kind'], REC['error_site'] = sa_errors.classify(_tb)" in src
    assert "REC['harness_stage_error']" in src


def sa_errors_site_of_text(text):
    import sa_errors
    return sa_errors.error_site(text)


def test_full_run_records_the_site_of_its_last_traceback(out_root, monkeypatch):
    """Amendment 7 section 2: run.json of a full adapter run that exits != 0 records the site of the traceback that
    ends adapter_log.txt; sc.full_outcome reads it (killed / harness -> unfinished, runtime -> failed)."""
    import sa_capture
    from types import SimpleNamespace
    monkeypatch.setattr(sc.c, 'adapter_args', lambda replay, out, tuning=None: (2700, []))
    monkeypatch.setattr(sc.c, 'base_env', lambda *a, **k: {'PYTHONPATH': 'a;b'})
    logs = []

    def fake_run(cmd, log, env, cwd=None):
        text, code = logs.pop(0)
        Path(log).write_text(text, encoding='utf-8')
        return code, 0.1
    monkeypatch.setattr(sc.c, 'run', fake_run)
    tuning = {'path': 'tuning.json', 'sha256': None}
    for tag, text, code, site, outcome in (('a', 'start\n' + _tb(INV), 1, 'runtime', 'failed'),
                                           ('b', 'start\nstep 1\n', 1, None, 'unfinished'),
                                           ('c', 'start\n' + _tb('KeyError: x', HARNESS), 1, 'harness', 'unfinished'),
                                           ('d', 'start\n', 0, None, 'unfinished')):
        logs.append((text, code))
        args = SimpleNamespace(tree='k86', arm='BASE', tag=tag, chain='site', s3_table=None, dry_run=False)
        sa_capture.run_full(args, {'T': 2700}, tuning)
        run = sc.read_json(sc.full_dir('k86', 2700, 'BASE', tag) / 'run.json')
        assert run['exit'] == code and run.get('error_site') == site, tag
        assert sc.full_outcome(run) == outcome, tag
    assert sc.full_outcome({'exit': 0, 'action_json_bytes': 10}) == 'ok' and sc.full_outcome(None) is None
    assert sc.full_outcome({'exit': 1}, log_text='x\n' + _tb(INV)) == 'failed'      # run.json without error_site


def test_full_run_records_the_selected_objective(out_root, monkeypatch):
    """K8 amendment 11 (K8-0f): run.json objective is joint_leader_selection.selected_objective of the action JSON (the
    deployed key; the former read of the absent key 'objective' was None on every run) with objective_key, next to
    held_objective and the CSV sha256; an action JSON without the key leaves objective None (no fallback key)."""
    import sa_capture
    from types import SimpleNamespace
    monkeypatch.setattr(sc.c, 'adapter_args', lambda replay, out, tuning=None: (2700, []))
    monkeypatch.setattr(sc.c, 'base_env', lambda *a, **k: {'PYTHONPATH': 'a;b'})
    selections = [{'selected_objective': 496.8425457870215, 'held_objective': 506.0624474786317,
                   'warm_start_objective': 499.5, 'selection_status': 'best_observed_feasible_sdmpc'},
                  {'objective': 1.0, 'held_objective': 2.0}]

    def fake_run(cmd, log, env, cwd=None):
        Path(log).write_text('start\n', encoding='utf-8')
        out = Path(log).parent
        (out / 'action_002700.json').write_text(json.dumps({'metadata': {'joint_leader_selection': selections.pop(0)}}),
                                                encoding='utf-8')
        (out / 'action_002700.csv').write_bytes(b'a,b\n1,2\n')
        return 0, 0.1
    monkeypatch.setattr(sc.c, 'run', fake_run)
    tuning = {'path': 'tuning.json', 'sha256': None}
    assert sa_capture.FULL_OBJECTIVE_KEY == 'selected_objective'
    for tag, objective, held in (('sel', 496.8425457870215, 506.0624474786317), ('old', None, 2.0)):
        args = SimpleNamespace(tree='k86', arm='BASE', tag=tag, chain='site', s3_table=None, dry_run=False)
        sa_capture.run_full(args, {'T': 2700}, tuning)
        run = sc.read_json(sc.full_dir('k86', 2700, 'BASE', tag) / 'run.json')
        assert repr(run['objective']) == repr(objective) and repr(run['held_objective']) == repr(held), tag
        assert run['objective_key'] == 'selected_objective' and run['csv_sha256'] and run['exit'] == 0, tag
        assert sc.full_outcome(run) == 'ok', tag


def _g1_world(tree, base, *, dp=None, tl3=None, full=None):
    """Synthetic G-EB-1 inputs: DP 17 BASE captures, TL3 9 x 2 BASE summaries and the full 2700 BASE run of both
    trees, all finished and equal; dp/tl3/full map a side ('tree' | 'base_tree') to a record override."""
    import pickle
    trees = {'tree': tree, 'base_tree': base}
    for T in sc.DP_T:
        for side, t in trees.items():
            d = sc.cap_dir(t, 'DP', T, 'BASE')
            d.mkdir(parents=True, exist_ok=True)
            (d / 'template.pickle').write_bytes(pickle.dumps({'x': float(T)}))
            (d / 'capture.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': True}), encoding='utf-8')
    for T in sc.GRID9:
        for entry in sc.ENTRIES:
            for side, t in trees.items():
                lb = sc.job_label('TL3', T, 'BASE', entry, 3)
                _write_job(t, lb, {'job': {'label': lb, 'arm': 'BASE'}, 'ok': True, 'objective_repr': '1.5',
                                   'objective': 1.5})
    for side, t in trees.items():
        sc.write_json(sc.full_dir(t, 2700, 'BASE') / 'run.json', {'exit': 0, 'action_json_bytes': 99,
                                                                  'objective': 2.0, 'held_objective': 2.0,
                                                                  'csv_sha256': 'a'})
    for side, rec in (dp or {}).items():
        d = sc.cap_dir(trees[side], 'DP', 900, 'BASE')
        (d / 'capture.json').unlink()
        (d / 'template.pickle').unlink()
        if rec is not None:
            (d / 'capture_failed.json').write_text(json.dumps(rec), encoding='utf-8')
    lb = sc.job_label('TL3', 900, 'BASE', 'OBS', 3)
    for side, rec in (tl3 or {}).items():
        if rec is None:
            (sc.job_dir(trees[side], lb) / 'summary.json').unlink()
        else:
            _write_job(trees[side], lb, rec)
    for side, rec in (full or {}).items():
        p = sc.full_dir(trees[side], 2700, 'BASE') / 'run.json'
        if rec is None:
            p.unlink()
        else:
            sc.write_json(p, rec)


def _g1_items(tree='k86', base='k85'):
    args = type('A', (), {'tree': tree, 'base_tree': base})()
    res = sa_compare.g1(args)
    sc.write_json(sc.sa_out() / 'compare' / f'g1_{tree}_vs_{base}.json', {'result': res})
    g = sa_gates.g1(si.Inputs(tree, base), type('A', (), {'unit_log': None})())
    return {k: g['items'][k]['pass_'] for k in ('dp17', 'tl3', 'full2700')}, res


def test_g1_pairs_need_both_runs_finished(out_root, monkeypatch):
    """Amendment 7 section 2 (review N-r5-1): a pair with a run that did not finish (absent, killed, input absent,
    failed without a runtime traceback) is INCOMPLETE; both finished and exactly one failed -> FAIL; both failed ->
    INCOMPLETE."""
    import pickle
    monkeypatch.setattr(sa_compare, 'load_pickle', lambda p: pickle.loads(Path(p).read_bytes()))   # no sys.path edit
    _g1_world('k86', 'k85')
    assert _g1_items()[0] == {'dp17': True, 'tl3': True, 'full2700': True}
    rt_fail = {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb(INIT)}
    harness_fail = {'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'error': _tb('KeyError: x', HARNESS)}
    killed = {'ok': False, 'exit': 1, 'error_kind': 'killed', 'child_record': False}
    for dp, want in (({'tree': None}, None), ({'tree': killed}, None), ({'base_tree': harness_fail}, None),
                     ({'tree': rt_fail}, False), ({'tree': rt_fail, 'base_tree': rt_fail}, None)):
        _g1_world('k86', 'k85', dp=dp)
        items, res = _g1_items()
        assert items['dp17'] is want, dp
        assert items['tl3'] is True and items['full2700'] is True
    lb = sc.job_label('TL3', 900, 'BASE', 'OBS', 3)
    tpl = sc.cap_dir('k86', 'TL3', 900, 'BASE') / 'template.pickle'
    absent_input = {'job': {'label': lb, 'arm': 'BASE'}, 'ok': False, 'error': _missing_file_traceback(tpl)}
    rt = {'job': {'label': lb, 'arm': 'BASE'}, 'ok': False, 'error': _tb(INV)}
    harness = {'job': {'label': lb, 'arm': 'BASE'}, 'ok': False, 'error': _tb('KeyError: x', HARNESS)}
    for tl3, want in (({'tree': None}, None), ({'tree': absent_input}, None), ({'base_tree': harness}, None),
                      ({'tree': rt}, False), ({'tree': rt, 'base_tree': rt}, None)):
        _g1_world('k86', 'k85', tl3=tl3)
        items, res = _g1_items()
        assert items['tl3'] is want, tl3
        assert items['dp17'] is True and items['full2700'] is True
    done_fail = {'exit': 1, 'error_site': 'runtime'}
    for full, want in (({'tree': None}, None), ({'tree': {'exit': 1}}, None),
                       ({'base_tree': {'exit': 1, 'error_site': 'harness'}}, None),
                       ({'tree': {'exit': 0}}, None), ({'tree': done_fail}, False),
                       ({'tree': done_fail, 'base_tree': done_fail}, None)):
        _g1_world('k86', 'k85', full=full)
        items, res = _g1_items()
        assert items['full2700'] is want, full
    assert sa_compare.pair_state({'tree': 'ok', 'base_tree': 'ok'}) is None
    assert sa_compare.pair_state({'tree': 'failed', 'base_tree': 'ok'})['equal'] is False


def test_g1_full_objective_absent_is_incomplete(out_root, monkeypatch):
    """K8 amendment 11 (K8-0f): both full 2700 runs finished but a side without objective or held objective (the
    pre-K8-0f run.json, objective None on both sides) is missing -> INCOMPLETE, never None == None -> PASS; equal
    values pass, a differing objective fails."""
    import pickle
    monkeypatch.setattr(sa_compare, 'load_pickle', lambda p: pickle.loads(Path(p).read_bytes()))
    done = {'exit': 0, 'action_json_bytes': 99, 'objective': 2.0, 'held_objective': 2.0, 'csv_sha256': 'a'}
    pre = dict(done, objective=None)
    for full, want in (({}, True), ({'tree': pre, 'base_tree': pre}, None), ({'tree': pre}, None),
                       ({'base_tree': dict(done, held_objective=None)}, None),
                       ({'tree': dict(done, objective=2.5)}, False)):
        _g1_world('k86', 'k85', full=full)
        items, res = _g1_items()
        assert items['full2700'] is want, full
        assert items['dp17'] is True and items['tl3'] is True
        assert ('missing' in res['full']['2700']) is (want is None), full


def test_g1_t11_follows_the_g9_missing_rule(out_root):
    """Amendment 7 section 4 (review B-r5-1): unit_T11 is None (INCOMPLETE) when a DP row is missing or the row count
    is not 17, like G-EB-9; never FAIL for an absent capture."""
    tree = 'k86'
    args = type('A', (), {'unit_log': None})()
    ok_row = {'meters': True, 'normalisation': True, 'sc109': True, 'n_meters': 8, 'n_sc109': 4}

    def t11(rows):
        sc.write_json(sc.sa_out() / 'compare' / f'g9_{tree}.json', {'result': rows})
        g1 = sa_gates.g1(si.Inputs(tree, 'k85'), args)
        g9 = sa_gates.g9(si.Inputs(tree, 'k85'), args)
        return g1['items']['unit_T11']['pass_'], g9['verdict'], g1['verdict']
    full = {str(T): dict(ok_row) for T in sc.DP_T}
    assert t11(full)[:2] == (True, 'PASS')
    one = dict(full, **{str(sc.DP_T[3]): {'missing': ['SAF']}})
    p, v9, v1 = t11(one)
    assert p is None and v9 == 'INCOMPLETE' and v1 != 'FAIL'           # the review probe: was False -> STOP
    assert t11({k: v for k, v in full.items() if k != str(sc.DP_T[0])})[:2] == (None, 'INCOMPLETE')
    bad = dict(full, **{str(sc.DP_T[0]): dict(ok_row, meters=False)})
    assert t11(bad)[:2] == (False, 'FAIL')


def _s3_sites(n=31, **row):
    return {f'S{k}': dict({'patched': 1, 'reached': 3, 'ev_exact_nonzero': 0.0, 'ev_unevaluated': 0}, **row)
            for k in range(n)}


def _g11d_run(**over):
    r = _hook_run()
    r['s3_sites'] = _s3_sites()
    r['fold_sites'] = {k: {'calls': 2, 'dropped': 0.0, 'ev_unevaluated': 0} for k in sa_hookcount.RULE3_SITES}
    r['fold_sites']['_skip_tiny_port_share'] = {'ev_exact_nonzero': 1.0, 'abs_dir_tangent_sum': 1e-14}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(r.get(k), dict) and k in ('s3_extra', 'fold_extra'):
            r[k] = {**r[k], **v}
        else:
            r[k] = v
    return r


def test_g11d_needs_a_valid_instrument_of_a_finished_run(out_root):
    """Amendment 7 section 3 (review B-r5-2) and section 2 (N-r5-3): G-EB-11(d) is judged only when the S3 hook of the
    same run has hook_errors = patch_errors = 0 and no errors, the fold hook has no error, every hook file is final,
    the run finished (exit 0 + action JSON) and no fold event was left unmeasured; else INCOMPLETE.  Observed exact
    != 0 S3 events or dropped fold tangents on a valid S3 count fail."""
    tree = 'k86'
    args = type('A', (), {'hooks_tag': 'hooks', 'unit_log': None})()
    _g13_finished(tree, [f'full_{T}_SAF' for T in sc.DP_FULL_T])

    def d(saf=None, T=2700):
        runs = {f'full_{t}_SAF': _g11d_run() for t in sc.DP_FULL_T}
        if saf is not None:
            runs[f'full_{T}_SAF'] = saf
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks(runs))
        g = sa_gates.g11(si.Inputs(tree), args)
        return g['items']['d_s3_hooks']['pass_'], g
    assert d()[0] is True
    # the review probe: S3 hook_errors 5000, 8 errors, patch_errors 2 on both runs -> INCOMPLETE (was PASS)
    for bad in (_g11d_run(s3_extra={'hook_errors': 5000.0}), _g11d_run(s3_extra={'errors': ['UFA:887 KeyError']}),
                _g11d_run(s3_extra={'patch_errors': 2}), _g11d_run(fold_extra={'hook_errors': 7.0}),
                _g11d_run(fold_extra={'errors': ['AttributeError']}), _g11d_run(s3_extra={'non_final': ['hook_1.json']}),
                _g11d_run(fold_extra={'non_final': ['sahook_1.json']}), _g11d_run(setup_errors=['chain error']),
                _g11d_run(fold_extra={'patched': ['src.models.urban_queue_model._movement_capacity_flow']}),
                _g11d_run(fold_sites={k: {'dropped': 0.0, 'ev_unevaluated': 3} for k in sa_hookcount.RULE3_SITES}),
                _g11d_run(s3_extra={'anchor_mismatch': ['UFA:887']}), _g11d_run(s3_sites=_s3_sites(30)),
                _g11d_run(s3_sites=_s3_sites(patched=0))):
        p, g = d(bad)
        assert p is None and g['verdict'] == 'INCOMPLETE', bad
        assert any(m.startswith('G-EB-11(d)') for m in g['missing'])
    # an unfinished run (exit 1, no action JSON) -> INCOMPLETE
    sc.write_json(sc.full_dir(tree, 2700, 'SAF', 'hooks') / 'run.json', {'exit': 1})
    assert d()[0] is None
    _g13_finished(tree, ['full_2700_SAF'])
    # observed events fail; fold ev_unevaluated alone is INCOMPLETE, not FAIL (N-r5-3)
    assert d(_g11d_run(s3_sites=_s3_sites(ev_exact_nonzero=1.0)))[0] is False
    dropped = {k: {'dropped': 0.0, 'ev_unevaluated': 0} for k in sa_hookcount.RULE3_SITES}
    dropped['_fold_city_share']['dropped'] = 1.0
    assert d(_g11d_run(fold_sites=dropped))[0] is False
    assert d(_g11d_run(s3_sites=_s3_sites(ev_exact_nonzero=1.0), s3_extra={'hook_errors': 1.0}))[0] is False
    assert d(_g11d_run(s3_sites=_s3_sites(ev_exact_nonzero=1.0), s3_extra={'anchor_mismatch': ['x']}))[0] is None
    assert d(_g11d_run(s3_sites=_s3_sites(ev_unevaluated=2)))[0] is True       # S3 pending: reported in the row
    p, g = d(_g11d_run(s3_sites=_s3_sites(ev_unevaluated=2)))
    assert g['items']['d_s3_hooks']['value'][0][-1] == 62


def _s3par(**over):
    """A worker s3_parity record (sa_s3parity.S3Log.report shape) of one passing ad_full comparison."""
    rec = {'schema': sa_s3parity.SCHEMA, 'installed': True, 'compares': 1, 'first_pass_compares': 0,
           's3_calls': 1, 'sa_created': 0, 'sa_created_by_origin': {}, 'excluded_records': 1,
           'excluded_by_site': {**{s: 0 for s, *_ in sa_s3parity.S3_SITES}, sa_s3parity.LEDGER_SITE: 1},
           'excluded_by_origin': {'evaluation/controllers/lane_ramp_runtime.py:152': 1}, 'not_excluded': [],
           'not_excluded_count': 0, 'compare_errors': []}
    rec.update(over)
    return rec


def test_g11e_failed_adfull_job_needs_a_runtime_traceback(out_root):
    """Amendment 7 section 2: a failed G-EB-11(e) SAF ad_full job fails only with a runtime traceback."""
    tree = 'k86'
    labels = [sc.job_label('TL3', int(T), 'SAF', 'A1', 3, variant='AD' + act, mode='ad_full') for T, act in sc.AD_FULL]
    for lb in labels:
        _write_job(tree, lb, {'job': {'label': lb, 'arm': 'SAF'}, 'ok': True, 'max_primal_state_error': 0.0,
                              'complete_primal_state_match': True, 's3_parity': _s3par()})
    e = lambda: sa_gates.g11(si.Inputs(tree), type('A', (), {'hooks_tag': 'hooks', 'unit_log': None})())[
        'items']['e_state_error']['pass_']
    assert e() is True
    _write_job(tree, labels[0], {'job': {'label': labels[0], 'arm': 'SAF'}, 'ok': False,
                                 'error': _tb('KeyError: x', HARNESS)})
    assert e() is None
    _write_job(tree, labels[0], {'job': {'label': labels[0], 'arm': 'SAF'}, 'ok': False, 'error': _tb(INV)})
    assert e() is False


def test_g11e_reads_the_amendment10_s3_record(out_root):
    """K8 amendment 10 decision 2: G-EB-11(e) is judged on the S3-rule comparison; its counts are reported per site;
    a job without the record (or whose comparison bypassed the wrapper) is INCOMPLETE; SA-created S3 records, keys
    outside the rule or a comparator error fail."""
    tree = 'k86'
    labels = [sc.job_label('TL3', int(T), 'SAF', 'A1', 3, variant='AD' + act, mode='ad_full') for T, act in sc.AD_FULL]

    def e(**over):
        for lb in labels:
            _write_job(tree, lb, {'job': {'label': lb, 'arm': 'SAF'}, 'ok': True, 'max_primal_state_error': 0.0,
                                  'complete_primal_state_match': True, **over})
        it = sa_gates.g11(si.Inputs(tree), type('A', (), {'hooks_tag': 'hooks', 'unit_log': None})())['items'][
            'e_state_error']
        return it['pass_'], it
    ok, it = e(s3_parity=_s3par())
    assert ok is True and it['row_header'][5:] == ['S3 excluded records', 'S3 excluded by site', 'SA-created S3 calls']
    assert it['value'][0][5] == 1 and it['value'][0][6][sa_s3parity.LEDGER_SITE] == 1 and it['value'][0][7] == 0
    assert e()[0] is None                                               # no record: comparison not readable
    assert e(s3_parity=_s3par(compares=0))[0] is None                   # the comparison bypassed the wrapper
    assert e(s3_parity=_s3par(installed=False))[0] is None
    assert e(s3_parity=_s3par(sa_created=1, sa_created_by_origin={'evaluation/controllers/'
                                                                   'stopline_approach.py:1361': 1}))[0] is False
    assert e(s3_parity=_s3par(not_excluded_count=1, not_excluded=[{'key': 'x', 'why': 'other'}]))[0] is False
    assert e(s3_parity=_s3par(compare_errors=['after setting aside 1 S3 records: x']))[0] is False
    assert e(s3_parity=_s3par(), max_primal_state_error=2e-8)[0] is False
    assert e(s3_parity=_s3par(), complete_primal_state_match=False)[0] is False


# ------------------------------------------------------------------------------------------------ amendment 10
S3_RULE_SCRIPT = textwrap.dedent("""
    # K8 amendment 10 rule cases on real CAO / SA code under the forward tangent runtime (one case per process).
    import json
    import sys
    from pathlib import Path
    from types import SimpleNamespace as NS
    ROOT, SADIR, CASE = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    sys.path.insert(0, SADIR)
    import sa_s3parity as P                                   # before the finder: untransformed
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    from evaluation.controllers import sdmpc_tangent_runtime as rt
    rt.install(ROOT, backend='forward')
    from evaluation.controllers import sdmpc_dual as ad
    from evaluation.controllers import control_area_objective as cao
    from evaluation.controllers.sdmpc_tangent_state import state_error
    log = P.install(cao, root=ROOT)
    CFG = NS(network=NS(control_area_routes={'movement:M': {'target_inside': True, 'inside_to_inside': 1.0,
                                                            'outside_to_inside': 1.0}}))
    STOCKS = {'storage:A': {'inside': 3.0, 'outside': 0.0}, 'storage:B': {'inside': 1.0, 'outside': 0.0},
              'movement:M': {'inside': 2.0, 'outside': 0.0}}

    def toy_site(st, amount, target='storage:B', key='toy:zero'):          # a non-SA emitter (this file)
        cao.emit_transfer(st, CFG, 'storage:A', target, amount, route_key=key, target_inside=True)  # TOY_SITE

    def sa_site(st, amount):                                                # the real SA site (SA._internal)
        from evaluation.controllers import stopline_approach as SA
        SA._internal(st, CFG, st._control_area_ledger, 'M', 'storage:B', amount)

    def run(zero):
        led = cao.ModelAreaLedger(STOCKS, capture_response=True)
        led.begin_response_step('urban', 0.0, 10.0)
        st = NS(_control_area_ledger=led)
        cao.emit_transfer(st, CFG, 'storage:A', 'storage:B', 1.0, route_key='common', target_inside=True)
        if CASE == 'a_s3_only':
            toy_site(st, zero)
        elif CASE == 'b_sa_site':
            sa_site(st, zero)
        elif CASE == 'b_sa_site_existing_key':
            cao.emit_transfer(st, CFG, 'movement:M', 'storage:B', 0.5, route_key='stopline_internal:M',
                              target_inside=True)
            sa_site(st, zero)
        elif CASE == 'c_other_site':
            if isinstance(zero, ad.Dual):
                led.flow_counts['direct:zero'] += zero
        elif CASE == 'd_new_stock_key':
            toy_site(st, zero, target='storage:NEW')
        elif CASE == 'e_nonzero_primal':
            if isinstance(zero, ad.Dual):
                toy_site(st, zero + 0.25)
        return {'ledger': led}

    scalar = run(0.0)
    trace = ad.Trace([1.0])
    tangent = run(ad.Dual(0.0, {0: 1.0}, trace))
    out = {'case': CASE}
    try:
        out['error'] = P.compare(scalar, tangent, log, comparator=state_error)
        out['raised'] = None
    except Exception as exc:
        out['error'], out['raised'] = None, repr(exc)
    rep = log.report()
    out['verdict'] = list(P.verdict(rep, out['error']))
    out['report'] = {k: rep[k] for k in ('s3_calls', 's3_rows', 'sa_created', 'excluded_records', 'excluded_by_site',
                                         'excluded_by_origin', 'excluded_keys', 'not_excluded_count', 'not_excluded',
                                         'sa_created_by_origin', 's3_calls_by_origin')}
    out['restored'] = sorted(tangent['ledger'].flow_counts)
    print('RESULT ' + json.dumps(out, default=repr))
    """)
S3_CASES = ('a_s3_only', 'b_sa_site', 'b_sa_site_existing_key', 'c_other_site', 'd_new_stock_key', 'e_nonzero_primal')


@pytest.fixture(scope='module')
def s3_rule(tmp_path_factory):
    script = tmp_path_factory.mktemp('s3rule') / 's3_rule_case.py'
    script.write_text(S3_RULE_SCRIPT, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('K8_', 'K8G_'))}
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1')
    out = {}
    for case in S3_CASES:
        p = subprocess.run([sys.executable, '-B', str(script), str(SA.parents[3]), str(SA), case], env=env,
                           capture_output=True, text=True, cwd=str(script.parent), timeout=600)
        assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
        out[case] = json.loads([x for x in p.stdout.splitlines() if x.startswith('RESULT ')][-1][7:])
    return out


def test_s3_rule_a_s3_site_only_difference_passes_with_count_1(s3_rule):
    """(a) the tangent run differs only by one zero-primal taped ledger record admitted by the K8-2 S3 gate outside
    SA: set aside, the comparison passes, counted once at CAO:608 with its emitting origin; keys put back."""
    r = s3_rule['a_s3_only']
    assert r['raised'] is None and r['error'] == 0.0 and r['verdict'] == [True, []]
    rep = r['report']
    assert rep['excluded_records'] == 1 and rep['excluded_keys'] == {'toy:zero': 1}
    assert rep['excluded_by_site'] == {**{s: 0 for s, *_ in sa_s3parity.S3_SITES}, 'CAO:608': 1}
    line = next(i for i, x in enumerate(S3_RULE_SCRIPT.splitlines(), 1) if x.endswith('# TOY_SITE'))
    assert rep['excluded_by_origin'] == {'s3_rule_case.py:%d' % line: 1} == rep['s3_calls_by_origin']
    assert rep['s3_calls'] == 1 and rep['s3_rows'] == 1 and rep['sa_created'] == 0 and rep['not_excluded_count'] == 0
    assert r['restored'] == ['common', 'toy:zero']


def test_s3_rule_b_same_record_from_an_sa_site_fails(s3_rule):
    """(b) the same-shaped record emitted by SA (stopline_approach._internal, a real SA site): SA-created, never set
    aside; the comparison raises; verdict FAIL.  Into a key the scalar run also has, the comparison passes but the
    SA-created count alone fails."""
    r = s3_rule['b_sa_site']
    assert r['error'] is None and 'State keys mismatch' in r['raised'] and r['verdict'][0] is False
    rep = r['report']
    assert rep['sa_created'] == 1 and rep['excluded_records'] == 0
    assert list(rep['sa_created_by_origin'])[0].startswith('evaluation/controllers/stopline_approach.py:')
    assert rep['not_excluded'][0]['key'] == 'stopline_internal:M' and 'SA' in rep['not_excluded'][0]['why']
    r = s3_rule['b_sa_site_existing_key']
    assert r['raised'] is None and r['error'] == 0.0 and r['verdict'][0] is False
    assert r['report']['sa_created'] == 1 and any('SA created' in w for w in r['verdict'][1])


def test_s3_rule_c_other_site_and_other_differences_fail(s3_rule):
    """(c) a tangent-only zero-primal flow_counts key written outside the S3 ledger gate fails; so do (d) a stocks key
    the S3 transfer created and (e) a tangent-only key with nonzero primal (anything else still FAILs)."""
    r = s3_rule['c_other_site']
    assert r['error'] is None and 'State keys mismatch' in r['raised'] and r['verdict'][0] is False
    assert r['report']['s3_calls'] == 0 and r['report']['excluded_records'] == 0
    assert 'another site' in r['report']['not_excluded'][0]['why']
    r = s3_rule['d_new_stock_key']
    assert r['error'] is None and 'stocks' in r['raised'] and r['verdict'][0] is False
    assert r['report']['s3_calls'] == 1
    r = s3_rule['e_nonzero_primal']
    assert r['error'] is None and 'State keys mismatch' in r['raised'] and r['verdict'][0] is False
    assert r['report']['s3_calls'] == 0 and 'nonzero' in r['report']['not_excluded'][0]['why']


def test_s3_rule_sites_are_anchored_in_this_tree():
    """The six K8-2 S3 sites resolve by their exact K8-2 text, each exactly once (amendment 10 numbering = K8-2)."""
    sites = sa_s3parity.site_table(SA.parents[3])
    assert list(sites) == ['PRB-bd:307', 'PRB-bd:332', 'PRB-bd:370', 'CAO:608', 'AFA:247', 'AFA:393']
    assert all(v['k82_line'] == int(k.rsplit(':', 1)[1]) and v['line'] > 0 for k, v in sites.items())


def test_g13_positive_control(out_root):
    """Amendment 7 section 3: G-EB-13 is judged only when BASE full 2700 and 4950 show W member plant reads > 0;
    absent or 0 -> INCOMPLETE (never FAIL); SAF plant reads > 0 still fail."""
    tree = 'k86'
    judged = ['full_2700_SAF', 'full_4950_SAF', 'job_' + sc.G13_JUDGED_HOOK_JOB]
    args = G13_ARGS()
    _g13_finished(tree, judged)

    def g13(base, saf_plant=0.0):
        runs = {n: _hook_run(plant=saf_plant if n == 'full_2700_SAF' else 0.0) for n in judged}
        runs.update(base)
        sc.write_json(sc.sa_out() / f'hooks_{tree}.json', _hooks(runs, control=False))
        g = sa_gates.g13(si.Inputs(tree), args)
        return g['verdict'], g['items']['base_plant_reads_control']['pass_'], g
    both = {'full_2700_BASE': _hook_run(plant=4.0), 'full_4950_BASE': _hook_run(plant=1.0)}
    assert g13(both)[:2] == ('PASS', True)
    for base in ({'full_2700_BASE': both['full_2700_BASE']}, {**both, 'full_4950_BASE': _hook_run(plant=0.0)},
                 {**both, 'full_2700_BASE': {'missing': 'x'}}):
        v, p, g = g13(base)
        assert (v, p) == ('INCOMPLETE', None) and any('positive control' in m for m in g['missing'])
        assert _combine_with('G-EB-13', g) == 'INCOMPLETE'
        assert g13(base, saf_plant=2.0)[0] == 'FAIL'                    # a read made still fails


def test_hookcount_records_final_flags(tmp_path):
    """Amendment 7 section 3 (review N-r4-1): sa_hookcount records per hook file kind the files whose last record is
    not final (killed or still running), for S3 / site hook files and SA hook files alike."""
    hook = tmp_path / 'hook'
    hook.mkdir()
    (hook / 'hook_1.json').write_text(json.dumps({'final': True, 'counters': {}, 'by_site': {}, 'extra': {}}),
                                      encoding='utf-8')
    (hook / 'hook_2.json').write_text(json.dumps({'final': False, 'counters': {'hook_errors': 2}, 'by_site': {},
                                                  'extra': {'errors': ['x']}}), encoding='utf-8')
    (hook / 'sahook_3.json').write_text(json.dumps({'counters': {}, 'fold': {}, 'cap_reads': {},
                                                    'extra': {'patched': ['a']}}), encoding='utf-8')
    run = sa_hookcount.run_record(hook)
    assert run['s3_extra']['non_final'] == ['hook_2.json'] and run['s3_extra']['final_files'] == 1
    assert run['s3_extra']['hook_errors'] == 2 and run['s3_extra']['errors'] == ['x']
    assert run['fold_extra']['non_final'] == ['sahook_3.json'] and run['fold_extra']['final_files'] == 0
    why = sa_gates.hook_run_problems(run)
    assert any(w.startswith('S3 hook hook_errors 2') for w in why)
    assert any('S3 hook files without their final record' in w for w in why)
    assert any('SA fold hook files without their final record' in w for w in why)


TAN_PATCH_SCRIPT = textwrap.dedent("""
    # K8-0i: the TAN instrument reaches the reverse module the tangent finder imported before the Post hook.
    import json
    import sys
    from pathlib import Path
    ROOT, SADIR = Path(sys.argv[1]), sys.argv[2]
    sys.path.insert(0, SADIR)
    import sa_worker as W                                     # before the finder: untransformed, as the worker
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    from evaluation.controllers.sdmpc_tangent_runtime import install
    install(ROOT, 'reverse-v1')                               # as sa_worker.main
    name = 'evaluation.controllers.sdmpc_tangent_reverse'
    out = {'preloaded': name in sys.modules}
    rev = sys.modules[name]
    rev.Trace.jacobian = lambda self, outputs, workers=8: 'original'   # the compiled sweep needs the pinned Numba
    callbacks = {name: W.patch_reverse}
    sys.meta_path.insert(0, W.Post(callbacks))
    out['late_patched'] = W.apply_loaded(callbacks)
    out['instrument'] = bool(getattr(rev.Trace.jacobian, 'k8_tan_instrument', False))
    tr = rev.Trace([0, 1])
    x, y = rev.Dual(2.0, {0: 1.0}, tr), rev.Dual(3.0, {1: 1.0}, tr)
    z = x * y + x
    W.TANGENT.update(nodes=[z.node], axes=[{'index': 0}, {'index': 1}], trace_id=id(tr), values=None, error=None)
    out['returned'] = tr.jacobian([z], 1)
    out['values'] = W.TANGENT['values']
    out['error'] = W.TANGENT['error']
    out['again'] = W.apply_loaded({'not.imported.module': W.patch_reverse})
    print('RESULT ' + json.dumps(out))
    """)


def test_tan_instrument_reaches_the_reverse_module_the_finder_preloaded(tmp_path):
    """K8-0i (G-EB-8 INCOMPLETE on k86h): install(R, 'reverse-v1') imports sdmpc_tangent_reverse before sa_worker puts
    its Post hook on sys.meta_path, so patch_reverse was never applied and every TAN summary kept tangent values None.
    apply_loaded patches the already imported module; the wrapped Trace.jacobian then records d(sum of the recorded
    nodes)/d(axis) by the forward sweep and still returns the original result (real reverse module, new process)."""
    script = tmp_path / 'tan_patch_case.py'
    script.write_text(TAN_PATCH_SCRIPT, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith(('K8_', 'K8G_'))}
    env.update(PYTHONHASHSEED='0', NUMBA_NUM_THREADS='1', OMP_NUM_THREADS='1')
    p = subprocess.run([sys.executable, '-B', str(script), str(SA.parents[3]), str(SA)], env=env,
                       capture_output=True, text=True, cwd=str(tmp_path), timeout=600)
    assert p.returncode == 0, p.stdout[-3000:] + p.stderr[-3000:]
    r = json.loads([x for x in p.stdout.splitlines() if x.startswith('RESULT ')][-1][7:])
    assert r['preloaded'] is True                              # the premise: Post alone never sees this import
    assert r['late_patched'] == ['evaluation.controllers.sdmpc_tangent_reverse'] and r['instrument'] is True
    assert r['returned'] == 'original' and r['error'] is None
    assert r['values'] == {'0': 4.0, '1': 2.0}                 # z = x*y + x at (2, 3): dz/dx = y + 1, dz/dy = x
    assert r['again'] == []
