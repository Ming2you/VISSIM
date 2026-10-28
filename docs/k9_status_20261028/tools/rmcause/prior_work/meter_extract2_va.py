# -*- coding: utf-8 -*-
"""Lens METER part 2: NUF/NP cap slack and central duals per decision (read-only joint.json)."""
import ctypes, glob, json, os, re, statistics, time
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)
except Exception:
    pass
ROOT = 'D:/VISSIM_runs/20261023_sdmpc31_k92'
RUNS = {'v3c3-s31': 'sdmpc31_v3c3_k92va_s31', 'v3c3-s41': 'sdmpc31_v3c3_k92va_s41', 'v3c3-s43': 'sdmpc31_v3c3_k92va_s43'}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meter_extract2_va.json')


def s(xs):
    xs = sorted(xs)
    return {'n': len(xs), 'min': xs[0], 'median': statistics.median(xs), 'max': xs[-1]} if xs else None


out = {'schema': 'lens-meter-extract2/v1', 'runs': {}}
t0 = time.time()
for label, name in RUNS.items():
    files = sorted(glob.glob(os.path.join(ROOT, name, 'decisions_' + name, 'action_*.joint.json')))
    nuf_res, np_res, nuf_sat, np_sat = [], [], 0, 0
    dual_nonzero_dec, dual_after_max = 0, 0.0
    nuf_cap_margin, merge_owner = [], {'FW_E': [], 'FW_W': []}
    for f in files:
        d = json.load(open(f, encoding='utf-8'))
        sel = d['selection']
        fc = sel.get('final_constraints', {})
        nuf, np_ = fc.get('nuf', {}), fc.get('np', {})
        nuf_res.append(nuf.get('residual')); np_res.append(np_.get('residual'))
        nuf_sat += bool(nuf.get('satisfied')); np_sat += bool(np_.get('satisfied'))
        anyd = False
        for u in sel.get('iteration_dual_updates', []):
            for x in (u.get('after') or []) + (u.get('prices_used') or []):
                if abs(x) > 0:
                    anyd = True
                    dual_after_max = max(dual_after_max, abs(x))
        dual_nonzero_dec += anyd
        bi = sel.get('budget_initialization', {}) or {}
        if 'nuf_cap_margin_veh_h' in bi:
            nuf_cap_margin.append(bi['nuf_cap_margin_veh_h'])
        pm = fc.get('physical_ramp_merge', {}) or {}
        for o, v in (pm.get('rate_veh_h_by_owner') or {}).items():
            merge_owner.setdefault(o, []).append(v)
        del d
    out['runs'][label] = {'files': len(files), 'nuf_residual_final': s([x for x in nuf_res if x is not None]),
                          'np_residual_final': s([x for x in np_res if x is not None]),
                          'nuf_satisfied': nuf_sat, 'np_satisfied': np_sat,
                          'decisions_with_nonzero_central_dual': dual_nonzero_dec,
                          'max_abs_central_dual': dual_after_max,
                          'nuf_cap_margin_veh_h': s(nuf_cap_margin),
                          'final_merge_rate_by_owner': {o: s(v) for o, v in merge_owner.items() if v}}
    print(label, round(time.time() - t0, 1), flush=True)
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote', OUT)
