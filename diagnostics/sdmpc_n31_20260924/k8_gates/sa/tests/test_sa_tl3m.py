"""K8 amendment 13 (595eb450, D-K8-7) rule tests of the SA harness, synthetic inputs only (no adapter, capture,
rollout, VISSIM or run folder): the TL3m sample, G-EB-3 / G-EB-6 judged on TL3m, G-EB-14 per R-obs seed with the
T = 1 / 150 identical-to-BASE rule, the G-EB-2 list with TL3m, the R-obs validity checker (GB-6 method), the tl3m job
plan and the --robs-seed capture paths.

    PYTHONHASHSEED=0 python -B -m pytest -p no:cacheprovider diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests -q
"""
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SA))
import sa_common as sc  # noqa: E402
import sa_errors  # noqa: E402
import sa_gates  # noqa: E402
import sa_inputs as si  # noqa: E402
import sa_tl3m  # noqa: E402

TREE = 'k86'
EVENTS = {31: (2700, 3000, 3600, 4200, 4950), 43: (3000, 3600, 4200, 4950), 47: (3600, 4200, 4950)}  # p4 958275ac
P4_SHA = '958275ac3093055c1e26336fb3f4cb73fd8fe4580773526fbdd40cace0d236dd'


@pytest.fixture
def out_root(tmp_path):
    sc.c.configure(out=tmp_path / 'gates_out', robs=tmp_path / 'runs' / 'sdmpc31_v3c3_nc_s31', nc3=tmp_path / 'nc3')
    yield tmp_path / 'gates_out'
    sc.c.configure()


def _ref(events=EVENTS, p4=P4_SHA):
    seeds = {}
    for s in sc.FH_SEEDS:
        states = {}
        for T in sc.GRID9:
            ev = T in events.get(s, ())
            states[str(T)] = {'event_state': ev, 'nonevent_state': not ev,
                              'w_ports_T': {'total': 200.0, '10491': 2, '10481': 1},
                              'w_ports_T150': {'total': 210.0, '10491': 2, '10481': 1},
                              'stop127_T150': 48.0 + (T % 7) + s % 3, 'wout_T150': 10,
                              'ext127_first500': T + 100.0, 'fw_w_stock': {str(T + 450): 900}}
        seeds[str(s)] = {'states': states, 'spill_windows_W': []}
    return {'inputs': {'p4': {'path': 'p4_states_grid9_v3c3.json', 'sha256': p4}}, 'seeds': seeds}


def _valid(seeds=sc.TL3M_SEEDS, status='valid'):
    for s in seeds:
        sc.write_json(sc.validity_path(s), {'schema': sc.VALIDITY_SCHEMA, 'seed': s, 'status': status,
                                            'reasons': [] if status == 'valid' else ['synthetic']})


def _summary(arm, T, seed, blocks, H=3, **extra):
    return {'schema': 'k8-sa-job/v1', 'job': {'arm': arm, 'T': T, 'seed': seed, 'harness': 'TL3', 'H': H}, 'ok': True,
            'blocks': blocks, 'wall_sec': 100.0, 'sa': {'end_step_calls': 450} if arm != 'BASE' else None, **extra}


def _block(k, total=205.0, p91=2.5, ready=50.0, b91=0.0, b81=0.0):
    return {'k': k, 't_end': 0.0, 'w_ports': {'total': total, 'port_10491': p91, 'port_10481': 0.0,
                                              'movement_w_all': 0, 'gate_occ': 0, 'transit_gate': 0},
            'w_ready': ready, 'w_out_occ': 10.0, 'fw_w_stock': 900.0, 'cell9_v': 80.0,
            'blocked_steps': {'10491': b91, '10481': b81, '10638': 0.0}}


def _write_job(label, summary):
    d = sc.job_dir(TREE, label)
    d.mkdir(parents=True, exist_ok=True)
    (d / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')


def _tl3m_world(*, bias=0.0, saf_p91=2.5, base=True, block91=(), block81=(), base81=0.0, first=None, drop=()):
    """Every TL3m job of the three R-obs seeds: SAF + BASE H3 OBS, SAF H6 OBS on the declared event states.
    block91: (seed, T) whose SAF H3 job blocks 10491 in block 1; block81: (seed, T, H) whose SAF job blocks 10481;
    first: {(seed, T): first 10491 block time of the H6 job} (default T + 150); drop: (seed, T, arm, H) not written."""
    shutil.rmtree(sc.sa_out() / 'jobs' / TREE, ignore_errors=True)        # each world starts without jobs
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _ref())
    _valid()
    for s in sc.TL3M_SEEDS:
        for T in sc.GRID9:
            ready = 49.0 + (T % 7) + s % 3
            for arm, total, p91 in (('SAF', 205.0 + (T % 3) + bias, saf_p91), ('BASE', 230.0, 4.0)):
                if (arm == 'BASE' and not base) or (s, T, arm, 3) in drop:
                    continue
                b91 = 3.0 if arm == 'SAF' and (s, T) in block91 else 0.0
                b81 = (1.0 if (s, T, 3) in block81 else 0.0) if arm == 'SAF' else base81
                _write_job(sc.job_label('TL3', T, arm, 'OBS', 3, seed=s),
                           _summary(arm, T, s, [_block(1, total, p91, ready, b91, b81), _block(2, total),
                                                _block(3, total)]))
            if T in EVENTS[s] and (s, T, 'SAF', 6) not in drop:
                t1 = (first or {}).get((s, T), T + 150.0)
                b81 = 1.0 if (s, T, 6) in block81 else 0.0
                _write_job(sc.job_label('TL3', T, 'SAF', 'OBS', 6, seed=s),
                           _summary('SAF', T, s, [_block(k, b81=b81 if k == 1 else 0.0) for k in range(1, 7)], H=6,
                                    first_block_t={'10491': t1, '10481': None, '10638': None}))


# ------------------------------------------------------------------------------------------------ paths and sample
def test_tl3m_paths_keep_every_s31_folder_and_label(out_root):
    assert sc.cap_dir(TREE, 'TL3', 2700, 'SAF', seed=31) == sc.cap_dir(TREE, 'TL3', 2700, 'SAF')
    assert sc.cap_dir(TREE, 'TL3', 2700, 'SAF', seed=43).parent.name == '002700_s43'
    assert sc.cap_dir(TREE, 'ROBS61', 1, 'BASE', seed=47).parent.name == '000001_s47'
    assert sc.cap_dir(TREE, 'ROBS61', 150, 'SAF', seed=31) == sc.cap_dir(TREE, 'ROBS61', 150, 'SAF')
    assert sc.job_label('TL3', 2700, 'SAF', 'OBS', 3, seed=31) == 'TL3_2700_SAF_OBS_H3'
    assert sc.job_label('TL3', 2700, 'SAF', 'OBS', 6, seed=43) == 'TL3_2700_s43_SAF_OBS_H6'
    assert sc.job_label('FH0', 900, 'SAF', 'OBS', 3, seed=31) == 'FH0_900_SAF_OBS_H3'
    assert sc.job_label('FH', 900, 'SAF', 'OBS', 3, seed=31) == 'FH_900_s31_SAF_OBS_H3'     # FH: island seed, as before
    assert sc.job_label('DP', 900, 'SAF', 'A1', 1, seed=43) == 'DP_900_SAF_A1_H1'           # DP stays R-obs3 only
    assert sc.replay_dir(2700) == sc.replay_dir(2700, 31) == sc.c.REPLAYS / '002700'
    assert sc.replay_dir(2700, 43) == sc.c.REPLAYS / 's43' / '002700'
    assert sc.robs_dir(31) == sc.c.ROBS and sc.robs_dir(43) == sc.c.ROBS.parent / 'sdmpc31_v3c3_nc_s43'
    assert sc.robs_wmi_log(47) == sc.c.ROBS.parent / 'wmi_sdmpc31_v3c3_nc_s47.log'
    assert sc.nc_fzp(43) == sc.c.NC3 / 's43_v3c3nc' / 'run' / 'vissim_eval' / 'baseline_s43_v3c3nc_001.fzp'
    for bad in (41, 37):
        with pytest.raises(SystemExit):
            sc.guard_tl3m_seed(bad)


def test_tl3m_sample_counts_bounds_and_validity(out_root):
    """Amendment 13: 27 states, events 12 / non-events 15, bounds 3 / 6; a seed counts only with a valid R-obs record;
    an invalid run leaves the sample (reported) with the declared ratios on the rest; anything else is INCOMPLETE."""
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _ref())
    sample = lambda: sa_gates.tl3m_sample(si.Inputs(TREE))
    S = sample()
    assert not S['complete'] and set(S['unknown']) == {31, 43, 47} and S['states'] == []
    _valid()
    S = sample()
    assert S['complete'] and len(S['states']) == 27 and len(S['events']) == 12 and len(S['nonevents']) == 15
    assert (S['b_max'], S['e_min']) == (sc.TL3M_G6_B_MAX, sc.TL3M_G6_E_MIN) == (3, 6)
    _valid((47,), 'invalid')
    S = sample()
    assert S['complete'] and S['seeds'] == [31, 43] and S['excluded'] == {47: 'synthetic'}
    assert (len(S['states']), len(S['events']), len(S['nonevents'])) == (18, 9, 9) and (S['b_max'], S['e_min']) == (1, 5)
    for rec in ({'schema': sc.VALIDITY_SCHEMA, 'seed': 47, 'status': 'not_finished'},
                {'schema': sc.VALIDITY_SCHEMA, 'seed': 47, 'status': 'error'},
                {'schema': sc.VALIDITY_SCHEMA, 'seed': 43, 'status': 'valid'},            # another seed's record
                {'seed': 47, 'status': 'valid'}):                                         # no schema
        sc.write_json(sc.validity_path(47), rec)
        S = sample()
        assert not S['complete'] and 47 in S['unknown'], rec
    (sc.validity_path(47)).write_text('{"schema": "k8-sa-robs', encoding='utf-8')         # truncated -> unknown
    assert 47 in sample()['unknown']
    _valid()
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _ref(p4='deadbeef' * 8))
    S = sample()
    assert not S['complete'] and any('classification sha' in p for p in S['problems'])
    ev = {**EVENTS, 43: (3600, 4200, 4950)}
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _ref(ev))
    S = sample()
    assert not S['complete'] and any(p.startswith('s43:') for p in S['problems'])


# ------------------------------------------------------------------------------------------------ G-EB-3
def test_g3_is_judged_on_tl3m_with_seed_clusters(out_root):
    _tl3m_world()
    g = sa_gates.g3(si.Inputs(TREE), None)
    it = g['items']
    assert it['a_bias']['pass_'] is True and it['a_mae']['pass_'] is True and it['b_G6_7']['pass_'] is True
    assert it['b_G6_7']['value']['n'] == 27 and it['b_G6_7']['value']['r'] == pytest.approx(1.0)
    c = it['c_ports']
    assert c['pass_'] is True and c['value']['10491']['iid']['n_items'] == 27
    assert c['value']['10491']['cluster']['n_clusters'] == 3 and c['value']['10481']['cluster']['n_clusters'] == 3
    assert c['value']['10491']['iid']['draws'] == 2000 and c['value']['10491']['iid']['seed'] == 0
    assert it['FH_report']['judged'] is False and it['TL3m_sample']['judged'] is False
    assert it['d_W_out_DP']['pass_'] is None and g['verdict'] == 'INCOMPLETE'      # (d) unchanged: DP / TL3 s31 absent
    # (a): |bias| <= 50 and MAE <= the persistence MAE of the same states (10 here)
    _tl3m_world(bias=20.0)
    it = sa_gates.g3(si.Inputs(TREE), None)['items']
    assert it['a_bias']['pass_'] is True and it['a_mae']['pass_'] is False
    _tl3m_world(bias=60.0)
    g = sa_gates.g3(si.Inputs(TREE), None)
    assert g['items']['a_bias']['pass_'] is False and g['verdict'] == 'FAIL'
    # (c): SAF further from VISSIM than BASE on 10491 in every state -> the lower bounds are > 0
    _tl3m_world(saf_p91=10.0)
    assert sa_gates.g3(si.Inputs(TREE), None)['items']['c_ports']['pass_'] is False


def test_g3_tl3m_completeness_base_comparator_and_seed_check(out_root):
    _tl3m_world(base=False)                         # BASE is the comparator of (c) only
    g = sa_gates.g3(si.Inputs(TREE), None)
    assert g['items']['a_bias']['pass_'] is True and g['items']['b_G6_7']['pass_'] is True
    assert g['items']['c_ports']['pass_'] is None and any('TL3m BASE' in m for m in g['missing'])
    _tl3m_world(drop={(43, 2250, 'SAF', 3)})
    g = sa_gates.g3(si.Inputs(TREE), None)
    assert all(g['items'][k]['pass_'] is None for k in ('a_bias', 'a_mae', 'b_G6_7', 'c_ports'))
    assert any('TL3m s43 2250' in m for m in g['missing'])
    _tl3m_world()                                   # a summary of another seed under an s47 label is not that job
    _write_job(sc.job_label('TL3', 900, 'SAF', 'OBS', 3, seed=47), _summary('SAF', 900, 31, [_block(1)]))
    I = si.Inputs(TREE)
    assert sa_gates.g3(I, None)['items']['a_bias']['pass_'] is None
    assert any('seed/harness mismatch TL3 s47 900' in m for m in I.missing)
    _tl3m_world()
    _valid((47,), 'invalid')                        # an invalid R-obs run leaves the sample, the rest is judged
    g = sa_gates.g3(si.Inputs(TREE), None)
    assert g['items']['b_G6_7']['value']['n'] == 18 and g['items']['c_ports']['pass_'] is True
    assert g['items']['c_ports']['value']['10491']['cluster']['n_clusters'] == 2
    assert g['items']['TL3m_sample']['value']['excluded_invalid_robs'] == {47: 'synthetic'}
    sc.validity_path(43).unlink()                   # no record -> INCOMPLETE, never PASS
    g = sa_gates.g3(si.Inputs(TREE), None)
    assert g['items']['a_bias']['pass_'] is None and any('TL3m R-obs s43' in m for m in g['missing'])


# ------------------------------------------------------------------------------------------------ G-EB-6
EV12 = [(s, T) for s in EVENTS for T in EVENTS[s]]
NEV15 = [(s, T) for s in EVENTS for T in sc.GRID9 if T not in EVENTS[s]]


def _g6(**kw):
    _tl3m_world(**kw)
    g = sa_gates.g6(si.Inputs(TREE), None)
    return g, {k: g['items'][k]['pass_'] for k in ('a_10481', 'b_nonevent', 'c_timing', 'e_hit_rate')}


def test_g6_is_judged_on_tl3m(out_root):
    g, p = _g6(block91=set(EV12))
    assert p == {'a_10481': True, 'b_nonevent': True, 'c_timing': True, 'e_hit_rate': True} and g['verdict'] == 'PASS'
    assert g['items']['a_10481']['value'] == {'blocked_steps': 0.0, 'n_H3': 27, 'n_H6': 12, 'missing': 0}
    assert g['items']['e_hit_rate']['value'] == {'hits': 12, 'n': 12, 'min_hits': 6}
    assert g['items']['FH_report']['judged'] is False
    # (a) 10481: SAF blocking in an H3 or an event H6 job fails; BASE blocking is only reported
    assert _g6(block91=set(EV12), block81={(47, 3600, 6)})[1]['a_10481'] is False
    assert _g6(block91=set(EV12), block81={(31, 900, 3)})[1]['a_10481'] is False
    g, p = _g6(block91=set(EV12), base81=2.0)
    assert p['a_10481'] is True and g['items']['a_10481_BASE_report']['value']['blocked_steps'] == 54.0
    # a missing judging-arm job leaves the item INCOMPLETE
    g, p = _g6(block91=set(EV12), drop={(43, 3000, 'SAF', 6)})
    assert p['a_10481'] is None and p['c_timing'] is None and g['verdict'] == 'INCOMPLETE'
    # (b) <= 3 of the 15 non-event states blocking 10491 in [T, T+450]
    assert _g6(block91=set(EV12) | set(NEV15[:3]))[1]['b_nonevent'] is True
    assert _g6(block91=set(EV12) | set(NEV15[:4]))[1]['b_nonevent'] is False
    # (e) >= 6 of the 12 event states
    assert _g6(block91=set(EV12[:6]))[1]['e_hit_rate'] is True
    g, p = _g6(block91=set(EV12[:5]))
    assert p['e_hit_rate'] is False and g['verdict'] == 'FAIL'
    # (c) the plant's first block may not lead VISSIM's 500 m extent by more than 30 s (here T + 100 - 30)
    assert _g6(block91=set(EV12), first={(43, 3600): 3600 + 70.0})[1]['c_timing'] is True
    assert _g6(block91=set(EV12), first={(43, 3600): 3600 + 69.0})[1]['c_timing'] is False


def test_g6_bounds_follow_the_sample_when_a_seed_leaves(out_root):
    _tl3m_world(block91=set(EV12) | {(31, 900), (43, 900)})
    _valid((47,), 'invalid')                        # 9 non-events -> (b) <= 1; 9 events -> (e) >= 5
    g = sa_gates.g6(si.Inputs(TREE), None)
    assert g['items']['b_nonevent']['value'] == {'blocked_states': 2, 'n_states': 9, 'max_states': 1}
    assert g['items']['b_nonevent']['pass_'] is False and g['items']['e_hit_rate']['value']['min_hits'] == 5
    assert g['items']['a_10481']['value']['n_H3'] == 18 and g['items']['a_10481']['pass_'] is True


# ------------------------------------------------------------------------------------------------ G-EB-14 / G-EB-2
def _tb(root, exc='ValueError: Previous command must be the immediately preceding action in this run', line=13062):
    return ('Traceback (most recent call last):\n'
            f'  File "{root}/evaluation/controllers/decision_failure_report.py", line 94, in run\n'
            '    return entry()\n'
            f'  File "{root}/diagnostics/sdmpc_n31_20260924/k8_gates/site/sitecustomize.py", line 75, in k8_realpath\n'
            '    return orig_realpath(path)\n'
            f'  File "{root}/evaluation/controllers/vissim_stackelberg_adapter.py", line 13158, in run_joint_owner_decision\n'
            '    historical, history_pins = load_joint_historical_reference(previous_path, previous, cfg,\n'
            '                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n'
            f'  File "{root}/evaluation/controllers/vissim_stackelberg_adapter.py", line {line}, in '
            'load_joint_historical_reference\n'
            "    raise ValueError('Previous command must be the immediately preceding action in this run')\n"
            '  File "<frozen ntpath>", line 722, in realpath\n'
            f'{exc}\n')


def test_traceback_signature():
    a, b = sa_errors.traceback_signature(_tb('D:/tree')), sa_errors.traceback_signature(_tb('E:\\other\\root'))
    assert a == b and a[0].startswith('ValueError: Previous command')
    assert [f[0] for f in a[1]] == ['evaluation/controllers/decision_failure_report.py',
                                    'evaluation/controllers/vissim_stackelberg_adapter.py',
                                    'evaluation/controllers/vissim_stackelberg_adapter.py']   # harness / frozen left out
    assert a[1][-1] == ('evaluation/controllers/vissim_stackelberg_adapter.py', 13062, 'load_joint_historical_reference')
    assert sa_errors.traceback_signature(_tb('D:/tree', line=13063)) != a
    assert sa_errors.traceback_signature(_tb('D:/tree', exc='ValueError: other')) != a
    chained = _tb('D:/x', exc='KeyError: k') + '\nDuring handling of the above exception, another exception occurred:\n\n' \
        + _tb('D:/tree')
    assert sa_errors.traceback_signature(chained) == a                    # the last traceback counts
    assert sa_errors.traceback_signature('no traceback here') is None and sa_errors.traceback_signature(None) is None
    assert sa_errors.traceback_signature('Traceback (most recent call last):\n  File "a.py", line 1, in f\n') is None


def _ok_cap(seed):
    return {'schema': sc.CAPTURE_SCHEMA, 'ok': True, 'seed': seed,
            'metadata': {'stopline_approach_install_check': {'ok': True},
                         'stopline_approach_initial': {'posthead_veh': 2.0, 'posthead_rehomed_veh': 0.0,
                                                       'posthead_receiver_shortfall_veh': 0.0,
                                                       'posthead_rehome_shortfall_veh': 0.0}},
            'probes': {'provenance': {'127': {'storage:SC1001_to_SC1002': 1.0, 'storage:SC1001_to_SC2002': 1.0},
                                      '10695': {'storage:SC1001_to_SC2002': 2.0}},
                       'records': {'n10695': 2}}}


def _fail_cap(folder, T, text, *, error_file=True):
    """A child-written failure record like the R-obs3 T = 1 / 150 captures (exit 3, no traceback in the record; the
    adapter's decision failure report action_<T>.error.txt beside it)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'capture_failed.json').write_text(json.dumps({'schema': sc.CAPTURE_SCHEMA, 'ok': False, 'exit': 3,
                                                            'error_kind': 'other', 'error_site': None,
                                                            'child_record': True}), encoding='utf-8')
    if error_file:
        (folder / f'action_{T:06d}.error.txt').write_text(text, encoding='utf-8')


def _robs_world():
    _valid()
    for s in sc.TL3M_SEEDS:
        for T in sc.ROBS61_T:
            if T in sc.ROBS_PRE_T:
                _fail_cap(sc.cap_dir(TREE, 'ROBS61', T, 'SAF', seed=s), T, _tb('D:/k86'))
                _fail_cap(sc.cap_dir(TREE, 'ROBS61', T, 'BASE', seed=s), T, _tb('D:/k86'))
                continue
            d = sc.cap_dir(TREE, 'ROBS61', T, 'SAF', seed=s)
            d.mkdir(parents=True, exist_ok=True)
            (d / 'capture.json').write_text(json.dumps(_ok_cap(s)), encoding='utf-8')
    for s in sc.FH_SEEDS:
        for T in sc.GRID9:
            d = sc.cap_dir(TREE, 'FH', T, 'SAF', seed=s)
            d.mkdir(parents=True, exist_ok=True)
            (d / 'capture.json').write_text(json.dumps(_ok_cap(s)), encoding='utf-8')


def _g14():
    g = sa_gates.g14(si.Inputs(TREE), SimpleNamespace(unit_log=None))
    return g, g['items']['i_init'], g['items']['ii_iii_posthead']


def test_g14_per_robs_seed_with_identical_pre_failures_reported(out_root):
    _robs_world()
    g, i, ii = _g14()
    assert i['pass_'] is True and ii['pass_'] is True
    assert i['value'] == {'ROBS61': [59, 59], 'ROBS61_s43': [59, 59], 'ROBS61_s47': [59, 59], 'FH': [45, 45]}
    assert sorted((r[0], r[1]) for r in i['reported_identical_to_base']) == [(s, T) for s in (31, 43, 47)
                                                                               for T in (1, 150)]
    assert ii['value'] == 45 + 3 * 59 and any(r[0] == 'robs_s43_300' for r in ii['rows'])
    assert g['items']['robs_pre_T_report']['judged'] is False and len(g['items']['robs_pre_T_report']['value']) == 6
    # G-EB-2 reads the same folders as reported rows, never as unreadable
    g2 = sa_gates.g2(si.Inputs(TREE), None)
    assert g2['items']['robs_identical_to_base']['value'] == 6 and g2['items']['robs_identical_to_base']['judged'] is False
    assert not [r for r in g2['items']['unreadable_runs']['rows'] if 'ROBS61' in str(r[0])]


def test_g14_pre_failures_that_differ_from_base_keep_the_capture_rule(out_root):
    _robs_world()
    d = sc.cap_dir(TREE, 'ROBS61', 150, 'SAF', seed=43)
    (d / 'action_000150.error.txt').write_text(_tb('D:/k86', exc='ValueError: lane 1 stock'), encoding='utf-8')
    (sc.cap_dir(TREE, 'ROBS61', 1, 'BASE', seed=47) / 'capture_failed.json').unlink()     # no BASE record
    g, i, _ = _g14()
    assert i['pass_'] is None and any(m.startswith('ROBS61 s43 150 capture failed') for m in g['missing'])
    assert any(m.startswith('ROBS61 s47 1 capture failed') for m in g['missing'])
    assert not any(m.startswith('ROBS61 s47 150') for m in g['missing'])          # still identical: reported
    pre = {(r['seed'], r['T']): r for r in g['items']['robs_pre_T_report']['value']}
    assert pre[(43, 150)]['identical'] is False and pre[(43, 150)]['reason'] == 'SAF and BASE failures differ'
    assert pre[(47, 1)]['reason'].startswith('BASE: no capture record')
    g2 = sa_gates.g2(si.Inputs(TREE), None)
    assert g2['items']['robs_identical_to_base']['value'] == 4
    assert any(r[0].endswith('000150_s43\\SAF') or r[0].endswith('000150_s43/SAF')
               for r in g2['items']['unreadable_runs']['rows'])
    # the rule is for T = 1 / 150 only (amendment 9 precedent): a later identical failure is not set aside
    for arm in ('SAF', 'BASE'):
        f = sc.cap_dir(TREE, 'ROBS61', 300, arm, seed=31)
        if (f / 'capture.json').is_file():
            (f / 'capture.json').unlink()
        _fail_cap(f, 300, _tb('D:/k86'))
    assert sc.robs_identical_failure(TREE, 31, 300)['identical'] is False
    g, i, _ = _g14()
    assert 'ROBS61 300' in ' '.join(g['missing'])
    # a runtime traceback recorded by the child still fails (i), identical BASE or not
    _robs_world()
    f = sc.cap_dir(TREE, 'ROBS61', 1, 'SAF', seed=31)
    rec = json.loads((f / 'capture_failed.json').read_text(encoding='utf-8'))
    rec.update(error=_tb('D:/k86', exc='evaluation.controllers.stopline_approach.StoplineInitError: x'),
               error_kind='init', error_site='runtime')
    (f / 'capture_failed.json').write_text(json.dumps(rec), encoding='utf-8')
    (f / 'action_000001.error.txt').unlink()          # the record's own traceback differs from BASE's error file
    assert _g14()[1]['pass_'] is False


def test_g14_seed_validity(out_root):
    _robs_world()
    _valid((47,), 'invalid')
    for T in sc.ROBS61_T:                             # an invalid run's captures are not read
        for name in ('capture.json', 'capture_failed.json'):
            p = sc.cap_dir(TREE, 'ROBS61', T, 'SAF', seed=47) / name
            if p.is_file():
                p.unlink()
    g, i, ii = _g14()
    assert i['pass_'] is True and 'ROBS61_s47' not in i['value'] and i['excluded_invalid_robs'] == {47: 'synthetic'}
    sc.validity_path(43).unlink()
    g, i, _ = _g14()
    assert i['pass_'] is None and any('G-EB-14 R-obs s43' in m for m in g['missing'])
    _valid()
    _robs_world()
    d = sc.cap_dir(TREE, 'ROBS61', 900, 'SAF', seed=43)
    (d / 'capture.json').write_text(json.dumps(_ok_cap(31)), encoding='utf-8')     # a capture of another seed
    g, i, _ = _g14()
    assert i['pass_'] is None and any('ROBS61 s43 900 capture records seed 31' in m for m in g['missing'])


# ------------------------------------------------------------------------------------------------ G-EB-2 list / jobs
def _plan_args(**over):
    a = dict(family='tl3m', arms=None, T=None, seeds=None, tree=TREE, eo_root='.', hooks=False, chain='site',
             s3_table=None, plan_only=False, dry_run=True)
    a.update(over)
    return SimpleNamespace(**a)


def test_tl3m_job_plan_and_the_g2_list(out_root, monkeypatch):
    import sa_fh
    import sa_jobs
    monkeypatch.setattr(sa_fh, 'eo_entry_rates', lambda d, T, H: {'eo': Path(d).name})
    sc.write_json(sc.sa_out() / 'vissim_ref.json', _ref())
    jobs = sa_jobs.plan(_plan_args())
    labels = [j['label'] for j in jobs]
    assert len(jobs) == len(set(labels)) == 66 == 3 * 18 + 12
    assert 'TL3_2700_SAF_OBS_H3' in labels and 'TL3_2700_SAF_OBS_H6' in labels and 'TL3_900_SAF_OBS_H6' not in labels
    assert 'TL3_3000_s43_SAF_OBS_H6' in labels and 'TL3_2700_s43_SAF_OBS_H6' not in labels
    assert not [lb for lb in labels if '_BASE_' in lb and lb.endswith('_H6')] and not [lb for lb in labels if 'SAG' in lb]
    by = {j['label']: j for j in jobs}
    j47 = by['TL3_900_s47_BASE_OBS_H3']
    assert Path(j47['template']).parent == sc.cap_dir(TREE, 'TL3', 900, 'BASE', seed=47) and j47['seed'] == 47
    assert j47['eo_dir'].endswith('s47_v3c2nc') and j47['obs_entry'] == {'eo': 's47_v3c2nc'}
    j31 = by['TL3_900_SAF_OBS_H3']
    assert Path(j31['template']).parent == sc.cap_dir(TREE, 'TL3', 900, 'SAF') and j31['eo_dir'].endswith('s31_v3c2nc')
    tl3 = {j['label']: j for j in sa_jobs.plan(_plan_args(family='tl3'))}       # the s31 H3 jobs are the tl3 jobs
    assert tl3['TL3_900_SAF_OBS_H3']['template'] == j31['template']
    for bad in (dict(arms='SAF,SAG'), dict(seeds='31,41')):
        with pytest.raises(SystemExit):
            sa_jobs.plan(_plan_args(**bad))
    labels_k, caps, n_sag = sa_jobs.declared_keyed(TREE)
    assert 'TL3_4950_s47_SAF_OBS_H6' in labels_k and 'TL3_4950_SAF_OBS_H6' in labels_k
    assert not [lb for lb in labels_k if '_BASE_' in lb]
    assert str(sc.cap_dir(TREE, 'TL3', 900, 'SAF', seed=43)) in caps and str(sc.cap_dir(TREE, 'ROBS61', 1, 'SAF',
                                                                                        seed=47)) in caps
    _valid((47,), 'invalid')                       # an invalid R-obs run leaves the plan and the declared list
    assert len(sa_jobs.plan(_plan_args())) == 66 - 21
    labels_k, caps, _ = sa_jobs.declared_keyed(TREE)
    assert not [lb for lb in labels_k if lb.startswith('TL3_') and '_s47_' in lb]
    assert str(sc.cap_dir(TREE, 'ROBS61', 1, 'SAF', seed=47)) not in caps
    assert str(sc.cap_dir(TREE, 'TL3', 900, 'SAF', seed=47)) not in caps
    assert str(sc.cap_dir(TREE, 'ROBS61', 1, 'SAF', seed=43)) in caps


def test_jobs_and_captures_use_the_seed_run(out_root, monkeypatch):
    import sa_capture
    monkeypatch.setattr(sc.c, 'base_env', lambda **kw: dict(robs=str(sc.c.ROBS), **kw))
    s31 = sc.c.ROBS
    assert sc.base_env_for(43)['robs'] == str(s31.parent / 'sdmpc31_v3c3_nc_s43') and sc.c.ROBS == s31
    assert sc.base_env_for(31)['robs'] == str(s31) and sc.base_env_for(None, hook_dir='h')['hook_dir'] == 'h'
    args = SimpleNamespace(kind='dp', robs_seed=43, T=[900], dry_run=False, arm='SAF', tree=TREE, seeds='31',
                           frames='T', fh_disabled=False)
    with pytest.raises(SystemExit):
        sa_capture.plan(args)                      # only tl3 / robs61 capture from another R-obs run
    args.kind = 'tl3'
    rows = sa_capture.plan(args)
    assert rows == [dict(harness='TL3', T=900, seed=43, frame_T=900)]
    with pytest.raises(SystemExit):
        sa_capture.use_robs_seed(args)            # no valid R-obs record: refused (a run in progress is never read)
    _valid((43,), 'not_finished')
    with pytest.raises(SystemExit):
        sa_capture.use_robs_seed(args)
    _valid((43,))
    sa_capture.use_robs_seed(args)
    assert sc.c.ROBS == s31.parent / 'sdmpc31_v3c3_nc_s43' and sc.c.DEC.name == 'decisions_sdmpc31_v3c3_nc_s43'
    rep = sc.replay_dir(900, 43)
    rep.mkdir(parents=True)
    (rep / 'replay_manifest.json').write_text(json.dumps({'source_decisions': str(s31 / 'decisions_x')}),
                                              encoding='utf-8')
    monkeypatch.setattr(sc.c, 'run', lambda *a, **k: pytest.fail('a child was started'))
    with pytest.raises(SystemExit):
        sa_capture.run_capture(args, rows[0], {'path': 't.json', 'sha256': None})
    assert not sc.cap_dir(TREE, 'TL3', 900, 'SAF', seed=43).exists()
    (rep / 'replay_manifest.json').write_text(json.dumps({'source_decisions': str(sc.c.DEC)}), encoding='utf-8')
    assert sa_capture.replay_source_problem(rep) is None


def test_g4_reports_s43_s47_and_g5_g7_g8_say_not_computed(out_root):
    _tl3m_world()
    I = si.Inputs(TREE)
    rep = sa_gates.g4(I, None)['items']['TL3m_s43_s47_report']
    assert rep['judged'] is False and len(rep['value']) == 18 and rep['value'][0] == [43, 900, 900.0, 900, 0.0]
    for g in (sa_gates.g5, sa_gates.g7, sa_gates.g8):
        it = g(I, SimpleNamespace())['items']['TL3m_s43_s47_report']
        assert it['judged'] is False and it['value'] is None and 'not computed' in it['threshold']


# ------------------------------------------------------------------------------------------------ R-obs validity
HEAD = (b'$VISION\r\n* File: {path}\r\n* Comment: \r\n* Date: {date}\r\n* \r\n'
        b'$VEHICLE:SIMSEC;NO;LINK;POS\r\n')
BODY = b''.join(b'%.2f;%d;%d;%.1f\r\n' % (t, n, 10 * n, 1.5 * n) for t in (5.1, 10.1, 15.1) for n in (1, 2, 3))


def _fzp(path, *, head_path=b'D:\\x.inpx', date=b'2026-10-05 a', pre=b'', body=BODY, comment=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    head = HEAD.replace(b'{path}', head_path).replace(b'{date}', date)
    if comment is not None:
        head = head.replace(b'* Comment: \r\n', b'* Comment: ' + comment + b'\r\n')
    path.write_bytes(head + pre + body)


def _robs_run(seed, *, finished=True, code=0, n_dec=61, counters=None, runlog=True, robs_fzp=True, nc=True,
              **fzp):
    run = sc.robs_dir(seed)
    name = run.name
    lines = [f'2026-10-05 19:10:26  START {name} out_dir={run}', '2026-10-05 21:07:00  WATCHDOG_EXIT code=0']
    if finished:
        lines.append(f'2026-10-05 21:07:00  EXIT {name} code={code}')
    sc.robs_wmi_log(seed).parent.mkdir(parents=True, exist_ok=True)
    sc.robs_wmi_log(seed).write_bytes(('\r\n'.join(lines) + '\r\n').encode('utf-8'))
    dec = run / f'decisions_{name}'
    dec.mkdir(parents=True, exist_ok=True)
    for T in sc.ROBS61_T[:n_dec]:
        (dec / f'state_{T:06d}.json').write_text('{}', encoding='utf-8')
        (dec / f'action_{T:06d}.json').write_text('{}', encoding='utf-8')
    if runlog:
        kv = dict({'DECISIONS_OK': '61', 'DECISIONS_FAILED': '0', 'STAGE': 'SIM_DONE', 'SIM_SEC': '9000'},
                  **(counters or {}))
        (run / f'runlog_{name}.txt').write_text('CONTROLLER_DECISION sim_sec=9000\n' + ''.join(
            f'{k}={v}\n' for k, v in kv.items()), encoding='utf-8')
    if robs_fzp:
        _fzp(run / 'vissim_eval' / f'sdmpc31_{name}_001.fzp', head_path=str(run).encode(),
             pre=fzp.pop('pre', b'0.10;1;90;0.5\r\n'), **fzp)
    if nc:
        _fzp(sc.nc_fzp(seed), head_path=b'D:\\nc\\baseline.inpx', date=b'2026-10-01 b')
    return run


def _v(seed=43):
    return sa_tl3m.validity(seed)


def test_validity_checker_gb6_method(out_root):
    _robs_run(43)
    rec = _v()
    assert rec['status'] == 'valid' and rec['schema'] == sc.VALIDITY_SCHEMA and rec['seed'] == 43 and not rec['reasons']
    f = rec['checks']['fzp']
    assert f['c1_header']['ok'] and len(f['c1_header']['differing']) == 2 and f['c2_payload']['pre51_lines_robs'] == 1
    assert f['c2_payload']['body_sha256_robs'] == f['c2_payload']['body_sha256_nc'] and f['c3_size']['ok']
    assert sc.validity_status(rec, 43) == ('valid', '')
    assert rec['checks']['exit']['code'] == 0 and rec['checks']['exit']['watchdog_exit'] == 0
    assert rec['checks']['decisions']['n_state'] == 61 and rec['checks']['decisions']['ok'] is True


@pytest.mark.parametrize('case, want, reason', [
    (dict(code=1), 'invalid', 'run exit 1'),
    (dict(n_dec=60), 'invalid', 'decisions: 60 state'),
    (dict(counters={'DECISIONS_FAILED': '1'}), 'invalid', 'decisions:'),
    (dict(counters={'STAGE': 'SIM_RUNNING'}), 'invalid', 'decisions:'),
    (dict(body=BODY[:-3] + b'7\r\n'), 'invalid', 'GB-6 c2_payload'),
    (dict(comment=b'other'), 'invalid', 'GB-6 c1_header'),
    (dict(pre=b'1.10;1;90;0.5\r\n'), 'invalid', 'c2_payload'),
    (dict(robs_fzp=False), 'invalid', 'R-obs FZP: 0'),
    (dict(nc=False), 'error', 'NC FZP absent'),
    (dict(runlog=False), 'error', 'runlog absent'),
    (dict(pre=b''), 'valid', None),                                     # no 0.10 frame at all: same trajectory
])
def test_validity_checker_cases(out_root, case, want, reason):
    _robs_run(47, **case)
    rec = _v(47)
    assert rec['status'] == want, rec['reasons']
    if reason:
        assert any(reason in r for r in rec['reasons']), rec['reasons']
    if want == 'invalid':
        assert sc.validity_status(rec, 47)[0] == 'invalid'
    if case.get('code'):
        assert rec['checks']['fzp'] == {'skipped': 'run already invalid'}


def test_validity_never_reads_a_run_in_progress(out_root):
    run = _robs_run(43, finished=False)
    for p in sorted(run.rglob('*'), reverse=True):     # the run folder is not read at all: remove it
        p.unlink() if p.is_file() else p.rmdir()
    rec = _v()
    assert rec['status'] == 'not_finished' and set(rec['checks']) == {'exit'} and sc.validity_status(rec, 43)[0] is None
    sc.robs_wmi_log(43).unlink()
    assert _v()['status'] == 'error'


def test_write_validity_keeps_a_final_record(out_root):
    _robs_run(43, finished=False)
    assert sa_tl3m.write_validity(43)['status'] == 'not_finished'
    _robs_run(43)                                      # the run finished: an unfinished record is redone
    assert sa_tl3m.write_validity(43)['status'] == 'valid'
    assert sc.validity_path(43).with_name('robs_validity_s43.stale_1.json').is_file()
    _robs_run(43, code=2)
    assert sa_tl3m.write_validity(43)['status'] == 'valid'                     # a final record is kept
    assert sa_tl3m.write_validity(43, recheck=True)['status'] == 'invalid'      # --recheck redoes it
    assert sc.validity_path(43).with_name('robs_validity_s43.stale_2.json').is_file()
    assert sc.validity_status(sc.read_validity(43), 43)[0] == 'invalid'
