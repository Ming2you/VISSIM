"""Self-test of c1_probe.py before its pin (no probe computation; synthetic arrays, the declared input records
(run_provenance, action_000750 of the 5 probe decision states) and the development smoke decision output of a state
outside every declared list: R-obs v3c3-s43 T=3000, dev tree).  Prints / writes flags and counts only.
    python -B c1_probe_selftest.py <out.json>"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402
import c1_probe as P  # noqa: E402


def main(out):
    import numpy as np
    P.LOG = C.make_logger(C.TC1 / 'out' / 'selftest' / 'c1_probe_selftest.log')
    cases = []

    def case(name, ok, **info):
        cases.append(dict(name=name, ok=bool(ok), **info))

    # 1. states, seeds from provenance, tags
    tags = set()
    for st in P.STATES['probe_decisions_T900']:
        d = P.run_dir_of(st['run'])
        prov = json.loads((d / ('run_provenance_%s.json' % st['run'])).read_text(encoding='utf-8-sig'))
        case('seed_from_provenance ' + P.label_of(st['run']), int(prov['seed']) == P.seed_of(st['run']))
        for arm in P.DEC_ARMS:
            t = P.dec_tag(st, arm)
            tags.add(t)
            case('tag_pattern ' + t, re.fullmatch(r't[0-9]{6}(?:_[a-z0-9]+)*', t) is not None)
        js, cs, has_state = P.prev_greens(st['run'], st['T'])
        case('prev_greens_json_eq_csv_all10 ' + P.p0_key(st),
             js == cs and all(v == 10.0 for v in js.values()) and set(js) == set(C.METERS) and not has_state)
    case('tags_unique_35', len(tags) == 35)
    sys.path.insert(0, str(P.PROBE / P.SA_REL))
    import k92_common as k92c
    for st in P.STATES['probe_plant_jobs']:
        P.run_dir_of(st['run'])
        case('plant_state_F_SECOND %s %d' % (P.label_of(st['run']), st['T']),
             (P.seed_of(st['run']), int(st['T'])) in k92c.F_SECOND_STATES and int(st['H']) == 3)
    case('plant_states_16', len(P.STATES['probe_plant_jobs']) == 16)
    # 2. series comparison
    keys = np.array(['a', 'b', 'c'], dtype=object)
    base = {'keys': keys, 'model': np.array([[1., np.nan, 2.], [3., 4., 5.]]), 't_end': np.array([1., 2.]),
            'stage': np.array([0, 1], dtype=np.int16)}
    same = {k: (v.copy() if hasattr(v, 'copy') else v) for k, v in base.items()}
    diff = {k: (v.copy() if hasattr(v, 'copy') else v) for k, v in base.items()}
    diff['model'][1, 2] = 5.000000001
    other = dict(base, keys=np.array(['a', 'b', 'd'], dtype=object))
    case('series_equal_with_nan', P.same_series(base, same)[0] is True)
    case('series_one_cell_differs', P.same_series(base, diff)[0] is False)
    case('series_keys_differ', P.same_series(base, other)[0] is False)
    case('series_missing', P.same_series(base, None)[0] is None)
    # 3. decision standing
    good = {'replay_run': {'exit_code': 0}, 'standing': {'error_files': [], 'decision_failed': [0, 0]},
            'action_json_sha256': 'x'}
    case('clean_good', P.decision_clean(good))
    case('clean_exit1', not P.decision_clean(dict(good, replay_run={'exit_code': 1})))
    case('clean_df', not P.decision_clean(dict(good, standing={'error_files': [], 'decision_failed': [0, 1]})))
    case('clean_df_none', not P.decision_clean(dict(good, standing={'error_files': [], 'decision_failed': [None, 0]})))
    case('clean_err', not P.decision_clean(dict(good, standing={'error_files': ['a.error.txt'], 'decision_failed': [0, 0]})))
    case('clean_infra', not P.decision_clean(dict(good, infra_failure='stall_killed')))
    case('clean_no_action', not P.decision_clean(dict(good, action_json_sha256=None)))
    # 4. decision_row on the dev smoke output (state outside every declared list)
    dev = C.TC1 / 'out' / 'dev' / 'dec_robs_s43_t003000__c1' / 'replay'
    st = {'run': 'sdmpc31_v3c3_nc_s43', 'kind': 'robs', 'T': 3000}
    rr = C.read_json(dev / 'replay_run.json') or {}
    s = {'replay_run': {'exit_code': rr.get('exit_code'), 'wall_sec': rr.get('wall_sec')},
         'standing': {'error_files': [], 'decision_failed': [0, 0]}, 'action_json_sha256': 'dev'}
    row = P.decision_row(st, 'c1', s, {}, rd=dev)
    case('dev_row_blocks_3x8', len(row['block_greens']) == 3 and all(all(v is not None for v in b.values())
                                                                     for b in row['block_greens']))
    case('dev_row_audit_incumbents', len(row['audit_per_incumbent']) >= 1
         and all(x['rows'] == x['without_combined'] + x['combined_rows'] for x in row['audit_per_incumbent']))
    case('dev_row_audit_rows_named', all(x['tighten_rows'] + x['release_rows'] == x['without_combined']
                                         for x in row['audit_per_incumbent']))
    case('dev_row_floors_8', isinstance(row['floors'], dict) and all(row['floors'][m] is not None for m in C.METERS))
    case('dev_row_fill_8', isinstance(row['fill_fraction'], dict) and all(row['fill_fraction'][m] for m in C.METERS))
    case('dev_row_held', isinstance(row['held'], dict) and row['held'].get('evaluated') is not None)
    case('dev_row_cap_targets', len(row['cap_targets']) >= 1)
    case('dev_row_sg2_sg5', row['sg2_block0'] is not None and row['sg5_block0'] is not None)
    case('dev_row_rollouts', isinstance(row['rollouts_total'], int))
    case('dev_row_omega', isinstance(row['omega_model_veh_h'], float) and row['omega_kind'] == 'Omega701')
    case('dev_row_token_ne_off', row['token_sdmpc_state'] not in (None, C.TOKEN_OFF)
         and row['token_sdmpc_state'] == row['token_price_state'])
    case('dev_row_c1_port_keys_7', sorted(row['metadata_c1_port_keys'] or []) == sorted(P.ARMS['c1']['keys']))
    case('dev_row_manifest_93f17143', row['lane_plant_manifest_sha256'] == '93f171437fbc55420e234a98efb262e83010566902a691a0cc438f17d247a4f7')
    case('dev_row_dropped_4', sorted((row['head_normalisation_dropped'] or {})) == sorted(C.FWE))
    case('dev_row_prev_json', len(row['previous_greens_json']) == 8)
    # 5. halt marker in a scratch place
    P.HALT = C.TC1 / 'out' / 'selftest' / ('halt_%d.json' % __import__('os').getpid())
    P.halt('selftest', {'x': 1})
    try:
        P.refuse_if_halted()
        refused = False
    except SystemExit:
        refused = True
    case('halt_refuses', refused)
    P.HALT.unlink()
    res = {'schema': 'c1-probe-selftest/v1', 'probe_sha256': C.sha256_file(Path(P.__file__)),
           'n': len(cases), 'n_ok': sum(c['ok'] for c in cases), 'ok': all(c['ok'] for c in cases), 'cases': cases}
    C.write_json(out, res)
    print('C1_PROBE_SELFTEST ok=%s %d/%d' % (res['ok'], res['n_ok'], res['n']))
    for c in cases:
        if not c['ok']:
            print('FAIL', c['name'])


if __name__ == '__main__':
    main(sys.argv[1])
