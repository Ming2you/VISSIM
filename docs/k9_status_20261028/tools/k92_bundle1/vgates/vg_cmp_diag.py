"""VerifyGates post-data diagnosis (disclosed; vg_cmp.py verdict is NOT changed): explain each DIFFERENT file of the
rerun comparison by recomputation.  For J (jb, s31 900) and F (f_b1, s43 1050), each side separately:
  D1 replay state file sha: replay_manifest raw_sha256/replay, state/replay_sha256 and obs150 derived inputs/raw_sha256
     = sha256 of that side's own state_<T>.json bytes; the two state files are equal after the root swap.
  D2 capture.json template_sha256 = sha256 of that side's template.pickle.
  D3 template.pickle bootstrap runtime_sources: after the root swap in keys, the two dicts differ only in the state
     file entry, whose value = that side's state file sha (D1).
  D4 capture joint.json: source_sha256 entry of the state file = that side's state sha; source_fingerprint = sha256 of
     pickle.dumps(runtime_sources of that side, protocol 5) (the adapter's source_token, area_follower_objective.py
     :1776); worker_cleanup_wall_sec is a wall time; parallel_transport_token is a hash with bootstrap bytes (runtime
     sources) and source_fingerprint among its inputs (area_follower_objective.py :829-830; code reading only).
  D5 job log.txt line 2 'continuous_scalar_done <x>': x = result.pickle scalar_sec of that side (a perf_counter
     duration, sdmpc_tangent_worker.py :303-307).
Names, sha and booleans only.

    python -B vg_cmp_diag.py --dest <json>
"""
import argparse
import io
import json
import pickle
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
SIDES = {'orig': OK2 / 'k92t', 'rerun': OK2 / 'vg2t'}
CASES = {'J': ('jb', 'replays/000900', 900, 'sa/cap/k92t/TL3/000900/SAF', 'sa/jobs/k92t/TL3_900_SAF_OBS_H3'),
         'F': ('f_b1', 'replays/s43/001050', 1050, 'sa/cap/k92t/TL3/001050_s43/SAF',
               'sa/jobs/k92t/TL3_1050_s43_SAF_OBS_H3')}


def swap(s):
    return s.replace('k92_b1\\vg2t', 'k92_b1\\k92t').replace('k92_b1/vg2t', 'k92_b1/k92t')


def runtime_sources(tpl):
    t = V.load_stub(tpl)
    boot = V.attr(t, 'bootstrap')
    return dict(V.attr(boot, 'runtime_sources'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    res = {'schema': 'vgates-rerun-diag/v1', 'cases': {}}
    for key, (arm, rep, T, cap, job) in CASES.items():
        row = {}
        st = {s: root / arm / rep / ('state_%06d.json' % T) for s, root in SIDES.items()}
        sha = {s: V.sha_file(p) for s, p in st.items()}
        b_o = open(V.lp(st['orig']), 'rb').read()
        b_r = open(V.lp(st['rerun']), 'rb').read()
        row['D1_state_equal_after_swap'] = b_o == swap(b_r.decode('utf-8')).encode('utf-8') or b_o == b_r.replace(
            b'k92_b1\\\\vg2t', b'k92_b1\\\\k92t').replace(b'k92_b1\\vg2t', b'k92_b1\\k92t').replace(
            b'k92_b1/vg2t', b'k92_b1/k92t')
        d1 = {}
        for s, root in SIDES.items():
            man = V.rjson(root / arm / rep / 'replay_manifest.json') or {}
            der = V.rjson(root / arm / rep / 'obs150' / ('derived_%06d.json' % T)) or {}
            d1[s] = {'manifest_raw_replay': (man.get('raw_sha256') or {}).get('replay') == sha[s],
                     'manifest_state_replay': (man.get('state') or {}).get('replay_sha256') == sha[s],
                     'derived_inputs_raw': (der.get('inputs') or {}).get('raw_sha256') == sha[s]}
        row['D1'] = d1
        d2, rsrc = {}, {}
        for s, root in SIDES.items():
            c = V.rjson(root / arm / cap / 'capture.json') or {}
            d2[s] = c.get('template_sha256') == V.sha_file(root / arm / cap / 'template.pickle')
            rsrc[s] = runtime_sources(root / arm / cap / 'template.pickle')
        row['D2_template_sha_is_file_sha'] = d2
        ko = {swap(k): v for k, v in rsrc['orig'].items()}
        kr = {swap(k): v for k, v in rsrc['rerun'].items()}
        diffk = sorted(k for k in set(ko) | set(kr) if ko.get(k) != kr.get(k))
        state_key = [k for k in diffk if k.lower().endswith('state_%06d.json' % T)]
        row['D3'] = {'n_sources': [len(ko), len(kr)], 'keys_equal_after_swap': set(ko) == set(kr),
                     'differing_keys': len(diffk), 'only_state_file': diffk == state_key and len(diffk) == 1,
                     'state_values_are_side_sha': bool(state_key) and ko[state_key[0]] == sha['orig']
                     and kr[state_key[0]] == sha['rerun']}
        d4 = {}
        for s, root in SIDES.items():
            jj = V.rjson(root / arm / cap / ('action_%06d.joint.json' % T)) or {}
            src = jj.get('source_sha256') or {}
            st_entries = [v for k, v in src.items() if k.lower().endswith('state_%06d.json' % T)]
            fp = (jj.get('physical_response_cache') or {}).get('source_fingerprint')
            d4[s] = {'source_sha256_state_is_side_sha': st_entries == [sha[s]],
                     'source_sha256_equals_runtime_sources': src == rsrc[s],
                     'fingerprint_is_sha_of_runtime_sources': fp == V.sha_bytes(pickle.dumps(rsrc[s], protocol=5))}
        row['D4'] = d4
        d5 = {}
        for s, root in SIDES.items():
            lines = open(V.lp(root / arm / job / 'log.txt'), 'rb').read().decode('utf-8').splitlines()
            val = float(lines[1].split()[1]) if len(lines) > 1 and lines[1].startswith('continuous_scalar_done') else None
            r = V.load_stub(root / arm / job / 'result.pickle')
            ss = r.get('scalar_sec') if isinstance(r, dict) else V.attr(r, 'scalar_sec')
            d5[s] = {'line1': lines[0] if lines else None, 'log_value_is_result_scalar_sec': val is not None
                     and repr(val) == repr(float(ss))}
        row['D5'] = d5
        res['cases'][key] = row
    V.wjson(args.dest, res)
    print('VG_CMP_DIAG', json.dumps(res['cases']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
