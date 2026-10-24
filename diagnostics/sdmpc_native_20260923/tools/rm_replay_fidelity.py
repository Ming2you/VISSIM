"""RM fidelity test: replay ALINEA's ACTUAL commands in the model from a state where the
native none/rm runs are still bit-identical, and compare the predicted TTT decomposition
against the measured native (rm - none) difference over the same window.

Common state: t=1950.1. ALINEA's first restriction decision is at t=1950 and the native
stocks first differ at 1980.1, so both native arms share the 1950.1 state exactly.
"""
import json, sys, csv, importlib.util
from pathlib import Path

ROOT = Path(r'D:\VISSIM-merge\sim3')
CAL  = ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD   = ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
BASE = CAL/'res10_20260922/boundary_literature_v1'
MODEL= RD/'controller_response_4500_v1/model_v3'
CC   = ROOT/'diagnostics/control_comparison_20260922'
Q    = Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls')
OUT  = Path(r'D:\VISSIM-merge\evidence/rm_replay')
sys.path[:0] = [str(CAL), str(RD), str(ROOT/'.review-deps'), str(ROOT)]
from canonical_harness import load_base_model
import evaluate_response as er
def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

import os
CUTOFF = float(os.environ.get('RM_CUTOFF','1950.1'))
_b0 = int(CUTOFF-0.1)
BLOCKS = (_b0, _b0+150, _b0+300)      # ALINEA decision times covering the 450s window

def native_delta(a, b):
    def rows(p):
        with open(p, encoding='utf-8-sig', newline='') as f:
            return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    out = {}
    for arm in ('none', 'rm'):
        R = rows(CC/arm/'stocks.csv'); acc = {}
        for key in ('network_n', 'FW_E_n', 'FW_W_n'):
            tot = 0.; prev = None
            for r in R:
                t = r['time_s']
                if a-1e-9 <= t <= b+1e-9:
                    if prev is not None: tot += (prev[key]+r[key])/2*(t-prev['time_s'])/3600
                    prev = r
            acc[key] = tot
        out[arm] = acc
    return {k: out['rm'][k]-out['none'][k] for k in out['none']}, out

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('h', ROOT/'diagnostics/offramp_dynamic_20260922/study.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    data, _ = m.corrected_data()
    _fam = os.environ.get('RM_FAMILY','boundary')
    if _fam == 'model_v3':
        # prepare_rules.py:99 does exactly this before pinning the MPC model.
        _cfg = json.loads((MODEL/'config.json').read_text(encoding='utf-8-sig'))
        _cfg['freeway']['physical_integration_step_sec'] = int(os.environ.get('RM_PLANT_STEP','1'))
        if os.environ.get('RM_PHI'):
            _cfg.setdefault('config_overrides',{}).setdefault('network',{})['capacity_drop_discharge_phi']=float(os.environ['RM_PHI'])
            print(f"  [probe] capacity_drop_discharge_phi={os.environ['RM_PHI']}")
        _tmp = MODEL/'_config_step_probe.json'   # must live under the repo root
        _tmp.write_text(json.dumps(_cfg), encoding='utf-8')
        model  = load_base_model(data.geometry, _tmp)
        params = load(MODEL/'selected_parameters.json')['parameters']
        _nu=os.environ.get('RM_NU'); _dm=os.environ.get('RM_DELTA')
        if _nu or _dm:
            import copy as _c; params=_c.deepcopy(params)
            for _r in params['by_direction'].values():
                if _nu: _r['nu_km2_h']=float(_nu)
                if _dm: _r['delta_merge']=float(_dm)
            print(f"  [probe] nu={_nu or 'base'} delta_merge={_dm or 'base'}")
    else:
        model  = load_base_model(data.geometry, BASE/f'{_fam}_config.json')
        params = load(BASE/'family_parameters.json')[_fam]
    print(f'  모형 family: {_fam}')
    profile = load(RD/'controller_response_4500_v1/model_v3/port_profile.json')
    _win = os.environ.get('RM_ONLINE_WINDOW')
    if _win: profile = dict(profile, online_window_sec=float(_win))
    print(f"  주행속도 모드: {'직전 '+_win+'초 실측' if _win else '현행 상수(<=900s)'}")
    policy  = load(Q/'rules/prepared_rm/rule_policy.json')
    zone_dsds = policy['zone_dsds']

    plan = {}
    for t in BLOCKS:
        d = load(Q/f'rm/run/decision_{t}.json')
        plan[t] = (dict(d['history']['greens']), dict(d['history']['states']))
    print('ALINEA 실제 명령:')
    for t in BLOCKS:
        g = plan[t][0]
        print(f'  t={t}: ' + json.dumps({k: v for k, v in g.items() if v < 10}, ensure_ascii=False) or '(제한없음)')

    def run(commands, label):
        w = er.window(data, model, CUTOFF, 'history_forecast', profile, commands)
        pred = er.simulate(model, w, params)
        parts = er.component(data, model, CUTOFF, pred)
        byroad = {r['road']: r['model_residence_10s_veh_h'] for r in pred['diagnostics']['roads']}
        back = sum(r['start']['outside_component_backlog_veh']+r['end']['outside_component_backlog_veh']
                   for r in pred['ramps'])
        dt = float(w['boundary_steps'][0]['window_end_s']-w['boundary_steps'][0]['window_start_s'])
        return dict(label=label, FW_E=byroad['FW_E'], FW_W=byroad['FW_W'],
                    freeway_ttt=parts['freeway_ttt_veh_h'], off_ttt=parts['off_ttt_veh_h'],
                    ramp_ttt=parts['ramp_ttt_veh_h'], component_ttt=parts['component_ttt_veh_h'],
                    ramp_wait=back*dt/7200)

    ids_open = {d: 120. for z, v in zone_dsds.items() for d in v}
    def hold_cmd(t): return {}, ids_open
    def replay_cmd(t):
        b = BLOCKS[min(2, int((t-CUTOFF)//150))]
        greens, states = plan[b]
        active = {mm: g for mm, g in greens.items() if g < 10 or mm in states}
        return active, ids_open

    h = run(hold_cmd, 'model_hold')
    r = run(replay_cmd, 'model_alinea_replay')
    nat, raw = native_delta(CUTOFF, CUTOFF+450)

    res = dict(cutoff=CUTOFF, window_sec=450, model_hold=h, model_replay=r,
               model_delta={k: r[k]-h[k] for k in h if k != 'label'},
               native_delta=nat, native_raw=raw)
    (OUT/'result.json').write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8')

    print('\n############ 모형 예측 (replay - hold) vs native 실측 (rm - none) ############')
    print(f"  {'항목':<16} {'모형 Δ':>12} {'native Δ':>12}")
    print(f"  {'FW_E 본선':<16} {res['model_delta']['FW_E']:+12.4f} {nat['FW_E_n']:+12.4f}")
    print(f"  {'FW_W 본선':<16} {res['model_delta']['FW_W']:+12.4f} {nat['FW_W_n']:+12.4f}")
    print(f"  {'램프 커넥터':<16} {res['model_delta']['ramp_ttt']:+12.4f} {'(분해 없음)':>12}")
    print(f"  {'off 커넥터':<16} {res['model_delta']['off_ttt']:+12.4f} {'':>12}")
    print(f"  {'component 합':<16} {res['model_delta']['component_ttt']:+12.4f} {nat['network_n']:+12.4f}  <- native 는 망 전체")
    print(f"  {'램프 대기항':<16} {res['model_delta']['ramp_wait']:+12.4f}")

if __name__ == '__main__':
    main()
