"""Score the MPC's own candidate set under three objective variants, offline.

No VISSIM. Uses the archived no-control observations as the common initial state and the
evaluate_response rollout path (which DOES install ramp_dynamics), bypassing online_data()
because that path still rejects the 0.1s FZP phase (defect D4).

Objectives compared, all on the identical prediction:
  A  component_ttt + ramp_wait + source_wait   (current code)
  B  component_ttt + ramp_wait                 (Omega-aligned: ramp approach links ARE in Omega)
  C  component_ttt                             (pure component TTT)
"""
import json, sys, time, importlib.util
from pathlib import Path

ROOT = Path(r'D:\VISSIM-merge\sim3')
CAL  = ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
RD   = ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2'
MODEL= RD/'controller_response_4500_v1/model_v3'
BASE = CAL/'res10_20260922/boundary_literature_v1'
FAMILY = 'boundary'
Q    = Path(r'D:\VISSIM_runs\20260922_fw080_urban090_controls')
OUT  = Path(r'D:\VISSIM-merge\evidence/objective_compare')
sys.path[:0] = [str(CAL), str(RD), str(ROOT/'.review-deps'), str(ROOT)]

from canonical_harness import load_base_model
import evaluate_response as er

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def corrected_data():
    helper = ROOT/'diagnostics/offramp_dynamic_20260922/study.py'
    spec = importlib.util.spec_from_file_location('existing_off_port_review', helper)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.corrected_data()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    data, correction = corrected_data()
    model   = load_base_model(data.geometry, BASE/f'{FAMILY}_config.json')
    params  = load(BASE/'family_parameters.json')[FAMILY]
    profile = load(MODEL/'port_profile.json')
    policy  = load(Q/'rules/prepared_rm/rule_policy.json')
    meters  = list(policy['meters']) if isinstance(policy['meters'], dict) else list(policy['meters'])
    zone_dsds = policy['zone_dsds']
    print(f'meters={len(meters)} zones={len(zone_dsds)} load={time.perf_counter()-t0:.1f}s', flush=True)

    CUTOFFS = [float(x) for x in (1800.1, 2700.1, 4500.1)]
    rows = []
    for cutoff in CUTOFFS:
        sec = cutoff
        greens = {m: 10 for m in meters}          # no-control baseline: all meters open
        zones  = {z: 120. for z in zone_dsds}     # no-control baseline: no VSL
        states = {}                               # nothing activated yet

        cands = [('hold', greens, zones)]
        # single-lever moves: exactly what mpc_choice generates today
        for m, g in greens.items():
            if g > 2: cands.append(('rm_restrict_'+m, {**greens, m: max(2, g-2)}, zones))
        for z, v in zones.items():
            if v > 60: cands.append(('vsl_restrict_'+z, greens, {**zones, z: max(60., v-20)}))
        # NEW: simultaneous restriction of all meters, at several depths.
        # mpc_choice has no such candidate (it restricts one meter but releases all eight).
        for g in (8, 6, 4, 2):
            cands.append((f'rm_ALL_g{g}', {m: g for m in greens}, zones))
        # NEW: simultaneous restriction of all VSL zones, for the same reason
        for v in (100., 80., 60.):
            cands.append((f'vsl_ALL_{int(v)}', greens, {z: v for z in zones}))
        # NEW: combined all-meter + all-zone
        cands.append(('both_ALL_g4_80', {m: 4 for m in greens}, {z: 80. for z in zones}))

        for name, gs, zs in cands:
            schedule = []
            for k in range(3):
                fg = {m: max(2, min(10, greens[m] + (k+1)*(g-greens[m]))) for m, g in gs.items()}
                fz = {z: max(60., min(120., zones[z] + (k+1)*(v-zones[z]))) for z, v in zs.items()}
                schedule.append({'sec': sec+150*k, 'greens': fg, 'zones': fz})
            def command(t, schedule=schedule):
                move = schedule[min(2, int((t-sec)//150))]
                active = {m: g for m, g in move['greens'].items() if g < 10 or m in states}
                ids = {d: move['zones'][z] for z, vals in zone_dsds.items() for d in vals}
                return active, ids
            try:
                w = er.window(data, model, sec, 'history_forecast', profile, command)
                pred = er.simulate(model, w, params)
                parts = er.component(data, model, sec, pred)
                bs=w['boundary_steps']
                dt=float(bs[0]['window_end_s']-bs[0]['window_start_s'])
                assert all(abs(float(x['window_end_s'])-float(x['window_start_s'])-dt)<1e-9 for x in bs)
                back=sum(r['start']['outside_component_backlog_veh']+r['end']['outside_component_backlog_veh']
                         for r in pred['ramps'])
                ramp_wait_bug = back*10/7200          # as the code is today (hardcoded 10)
                ramp_wait_fix = back*dt/7200          # D5-corrected: use the real step
                def src(weight):
                    tot=0.
                    for road in model.roads:
                        backlog=0.
                        for k in range(15):
                            a=round(sec+30*k,6); b=round(a+30,6)
                            req=sum(x['source_demand_vph'][road]*weight/3600 for x in bs
                                    if a-1e-7<=x['window_start_s']<b-1e-7)
                            adm=sum(f['source_admissions'] for f in pred['flows']
                                    if f['road']==road and abs(f['window_end_s']-b)<1e-7)
                            after=max(0.,backlog+req-adm); tot+=(backlog+after)*30/7200; backlog=after
                    return tot
                source_wait_bug = src(10.)
                source_wait_fix = src(dt)
                comp = parts['component_ttt_veh_h']
                byroad = {r['road']: r['model_residence_10s_veh_h'] for r in pred['diagnostics']['roads']}
                rows.append(dict(cutoff=cutoff, candidate=name, kind=name.split('_')[0], dt=dt,
                    component_ttt=comp, FW_E=byroad.get('FW_E'), FW_W=byroad.get('FW_W'),
                    freeway_ttt=parts['freeway_ttt_veh_h'], off_ttt=parts['off_ttt_veh_h'],
                    ramp_ttt=parts['ramp_ttt_veh_h'], ramp_wait_bug=ramp_wait_bug, ramp_wait_fix=ramp_wait_fix,
                    source_wait_bug=source_wait_bug, source_wait_fix=source_wait_fix,
                    A_current = comp+ramp_wait_bug+source_wait_bug,
                    A_fixed   = comp+ramp_wait_fix+source_wait_fix,
                    B_omega   = comp+ramp_wait_fix,
                    C_pure    = comp,
                    error=None))
                print(f'  {cutoff} {name:26} comp={comp:9.4f} ramp={ramp_wait_fix:7.4f} src={source_wait_fix:8.4f} (bug src={source_wait_bug:9.3f})', flush=True)
            except Exception as e:
                rows.append(dict(cutoff=cutoff, candidate=name, kind=name.split('_')[0], error=f'{type(e).__name__}: {e}'))
                print(f'  {cutoff} {name:28} FAILED {type(e).__name__}: {str(e)[:120]}', flush=True)
    (OUT/'rows.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'\n총 {len(rows)} 행, {time.perf_counter()-t0:.1f}초 -> {OUT/"rows.json"}')

if __name__ == '__main__':
    main()
