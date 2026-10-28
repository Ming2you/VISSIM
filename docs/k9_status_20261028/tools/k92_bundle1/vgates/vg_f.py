"""VerifyGates: the F-stage STOP of k92t re-checked from raw records with own code.  Blind: no v3c3-s47 output is
opened (s47 job / capture folders: names and presence only; f_vref: sha only; F job logs: not opened).  s31 / s43
second-sample job summaries: the 'ok' field only.

  steps     OUTK/steps.jsonl: every F step rc 0 except f_persist rc 1 (the last step), VISSIM counts 0
  stop      STOP_f.json = {stage f, why 'persist rc=1'}; no judge/f.json, stages/f.json, judge/jb.json, jb gates file,
            stages/jb.json, stages/post.json; f_persist output absent
  data      per F arm: 38 capture folders with capture.json (no capture_failed.json), 38 job folders with summary.json
            and k92_record.json; s31 / s43 summaries ok true; arms.json SAF sha = declared (5f0d0e40 / d179f01d /
            65cac7ea); f_vref file sha
  code      the persistence states (T - 450 of the 22 primary states) against the U4 measurer window filter (T_FROM,
            read from derive_head_saturation.py text), the VR SystemExit line, the driver's must() on f_persist,
            and whether the F judge verdict reads f_persist (k92t_judge.py cmd_f text)

    python -B vg_f.py --dest <json>
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vglib as V  # noqa: E402

OK2 = Path(r'D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1')
OUTK = OK2 / 'k92t'
TREE = Path(r'D:/VISSIM-merge/k8_gate_trees/k92b1/a27/k92t')
KB = HERE.parent
F_PRIMARY = (1050, 1650, 1950, 2400, 3300, 3750, 3900, 4650, 5100, 5550, 6000, 6150, 6450, 6600, 6900, 7050, 7350,
             7500, 7800, 7950, 8250, 8400)
F_SECOND = {31: (1500, 2850, 3900, 5250, 6000, 6600, 7500, 8250), 43: (1050, 3300, 4800, 5550, 6450, 7050, 7800, 8400)}
ARM_SHA = {'f_off': '5f0d0e40', 'f_w': 'd179f01d', 'f_b1': '65cac7ea'}
F_STEPS = ['f_f_off_cap_s47', 'f_f_off_cap_s31', 'f_f_off_cap_s43', 'f_f_off_jobs', 'f_f_w_cap_s47', 'f_f_w_cap_s31',
           'f_f_w_cap_s43', 'f_f_w_jobs', 'f_f_b1_cap_s47', 'f_f_b1_cap_s31', 'f_f_b1_cap_s43', 'f_f_b1_jobs', 'f_vref',
           'f_persist']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dest', required=True)
    args = ap.parse_args()
    res = {'schema': 'vgates-f/v1'}
    steps = [json.loads(x) for x in open(OUTK / 'steps.jsonl', encoding='utf-8') if x.strip()]
    names = [s['name'] for s in steps]
    fsteps = [s for s in steps if s['name'] in F_STEPS]
    res['steps'] = {'n_total': len(steps), 'f_names_in_order': [s['name'] for s in fsteps] == F_STEPS,
                    'rc': {s['name']: s['rc'] for s in fsteps}, 'last': names[-1],
                    'vissim_all_zero': all(s.get('vissim_pre') == 0 and s.get('vissim_post') == 0 for s in steps),
                    'only_persist_nonzero': [s['name'] for s in steps if s['rc'] != 0] == ['f_persist'],
                    'persist_sec': [s['sec'] for s in fsteps if s['name'] == 'f_persist'],
                    'persist_argv_states': [a for s in fsteps if s['name'] == 'f_persist' for a in s['argv']
                                            if a.startswith('47:')]}
    stop = V.rjson(OUTK / 'STOP_f.json') or {}
    absent = {p: not (OUTK / p).exists() for p in ('judge/f.json', 'stages/f.json', 'judge/jb.json', 'stages/jb.json',
                                                   'stages/post.json', 'jb/sa/gates/gates_k92t.json',
                                                   'f_persist/sa/k92_vissim_ref.json', 'judge/sealed_records.json')}
    res['stop'] = {'stage': stop.get('stage'), 'why': stop.get('why'), 'absent': absent,
                   'stop_files': sorted(p.name for p in OUTK.glob('STOP_*.json')),
                   'stages_done': sorted(p.stem for p in (OUTK / 'stages').glob('*.json'))}
    data = {}
    for arm in ('f_off', 'f_w', 'f_b1'):
        r = OUTK / arm
        states = [(47, T) for T in F_PRIMARY] + [(s, T) for s, Ts in F_SECOND.items() for T in Ts]
        cap_ok = job_ok = sec_ok = 0
        for s, T in states:
            tag = '%06d' % T + ('' if s == 31 else '_s%d' % s)
            cd = r / 'sa' / 'cap' / 'k92t' / 'TL3' / tag / 'SAF'
            if (cd / 'capture.json').is_file() and not (cd / 'capture_failed.json').exists():
                cap_ok += 1
            lab = 'TL3_%d%s_SAF_OBS_H3' % (T, '' if s == 31 else '_s%d' % s)
            jd = r / 'sa' / 'jobs' / 'k92t' / lab
            if (jd / 'summary.json').is_file() and (jd / 'k92_record.json').is_file():
                job_ok += 1
            if s != 47 and (V.rjson(jd / 'summary.json') or {}).get('ok') is True:
                sec_ok += 1
        arms = (V.rjson(r / 'sa' / 'tuning' / 'arms.json') or {}).get('arms') or {}
        data[arm] = {'captures_present': cap_ok, 'jobs_present': job_ok, 'second_sample_ok': sec_ok,
                     'arm_sha_ok': str((arms.get('SAF') or {}).get('sha256', ''))[:8] == ARM_SHA[arm]}
    vref = OUTK / 'f_vref' / 'sa' / 'k92_vissim_ref.json'
    data['f_vref_sha256'] = V.sha_file(vref) if vref.is_file() else None
    res['data'] = data
    dhs = (TREE / 'diagnostics/sdmpc_n31_20260924/k8b/u4/derive_head_saturation.py').read_text(encoding='utf-8')
    m = re.search(r'^T_FROM\s*=\s*([0-9.]+)', dhs, re.M)
    t_from = float(m.group(1)) if m else None
    filt = [i + 1 for i, ln in enumerate(dhs.splitlines()) if 'a >= T_FROM' in ln]
    vr = (TREE / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_vissim_ref.py').read_text(encoding='utf-8')
    vr_exit = [i + 1 for i, ln in enumerate(vr.splitlines()) if 'found {len(cyc)} times' in ln]
    persist = [T - 450 for T in F_PRIMARY]
    res['code'] = {'T_FROM': t_from, 'filter_lines': filt, 'vr_exit_lines': vr_exit,
                   'persist_states': persist,
                   'persist_states_with_window_start_below_T_FROM': [t for t in persist if t + 0.1 < (t_from or 0)],
                   'primary_states_below_T_FROM': [t for t in F_PRIMARY if t + 0.1 < (t_from or 0)]}
    drv = (KB / 'k92t' / 'k92t.py').read_text(encoding='utf-8').splitlines()
    res['code']['driver_must_persist_lines'] = [i + 1 for i, ln in enumerate(drv) if "'f', 'persist')" in ln]
    res['code']['driver_O7_text'] = [ln.strip() for ln in drv if ln.strip().startswith('O7')]
    jdg = (KB / 'k92t' / 'k92t_judge.py').read_text(encoding='utf-8').splitlines()
    res['code']['judge_persist_lines'] = [i + 1 for i, ln in enumerate(jdg) if 'pers' in ln and 'def ' not in ln]
    res['code']['judge_verdict_lines'] = [i + 1 for i, ln in enumerate(jdg) if "res['verdict'] =" in ln]
    V.wjson(args.dest, res)
    print('VG_F stop=%s/%s only_persist=%s absent=%s data=%s T_FROM=%s below=%s' % (
        stop.get('stage'), stop.get('why'), res['steps']['only_persist_nonzero'], all(absent.values()),
        {a: (d['captures_present'], d['jobs_present'], d['second_sample_ok'], d['arm_sha_ok'])
         for a, d in data.items() if isinstance(d, dict)}, t_from,
        res['code']['persist_states_with_window_start_below_T_FROM']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
