"""Frozen component response probe; NOT the production/full-Omega controller."""
from pathlib import Path
import copy, csv, hashlib, importlib.util, json, sys, time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAL = ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
BASE = CAL/'res10_20260922/boundary_literature_v1'
OUT = HERE/'model_choice_probe'
Q = Path('D:/VISSIM_runs/20260922_fw080_urban090_controls')
sys.path[:0] = [str(CAL), str(ROOT/'.review-deps'), str(ROOT)]
import numpy as np
from canonical_harness import load_base_model, sha256
from boundary_factory import build_window


def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf8')
def table(p, rows):
    with p.open('w', newline='', encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def integrate(times, values, a, b):
    sel=(times>a)&(times<b); t=np.r_[a,times[sel],b]
    ends=np.array([[np.interp(x,times,values[:,k]) for k in range(values.shape[1])] for x in (a,b)])
    v=np.concatenate([ends[:1],values[sel],ends[1:]])
    return np.trapezoid(v,t,axis=0)/3600


def main():
    started=time.perf_counter(); OUT.mkdir(exist_ok=True)
    helper=ROOT/'diagnostics/offramp_dynamic_20260922/study.py'
    spec=importlib.util.spec_from_file_location('existing_off_port_review',helper)
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    data, correction=old.corrected_data()
    params=load(BASE/'family_parameters.json')
    policy=load(Q/'rules/prepared_vsl/rule_policy.json')
    network=Q/'rules/prepared_vsl/network/baseline.inpx'
    chain={str(r['link']):(road,r['offset_m']) for road,rs in data.geometry['chains'].items() for r in rs}
    id_to_zone={str(n):z for z,ids in policy['zone_dsds'].items() for n in ids}
    dsd=[]
    for d in ET.parse(network).findall('./desSpeedDecisions/desSpeedDecision'):
        link=d.get('lane').split()[0]
        if link in chain:
            road,offset=chain[link]
            assert {v.get('desSpeedDistr') for v in d.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}=={'120'}
            dsd.append((road,offset+float(d.get('pos')),d.get('no'),id_to_zone.get(d.get('no'))))
    dsd.sort()
    bindings=[]
    for c in data.geometry['cells']:
        # Same physical-DSD-at-cell-center projection as the existing diagnostic.
        center=(c['start_m']+c['end_m'])/2
        preceding=[x for x in dsd if x[0]==c['road'] and x[1]<=center]
        z=preceding[-1][3] if preceding else None
        bindings.append(dict(road=c['road'],cell=c['cell'],start_m=c['start_m'],end_m=c['end_m'],zone=z))
    assert set(x['zone'] for x in bindings)-{None}==set(policy['zone_dsds'])
    heads={r:list(range(len([c for c in bindings if c['road']==r]))) for r in ('FW_E','FW_W')}
    seq={}; state={}
    for t in range(900,9000,150):
        dec=load(Q/'vsl/run'/f'decision_{t}.json'); state.update(dec['history']['vsl'])
        seq[t]={z:float(state.get(str(ids[0]),120)) for z,ids in policy['zone_dsds'].items()}
        assert all(len({state.get(str(i),120) for i in ids})==1 for ids in policy['zone_dsds'].values())
    pins={str(p):sha256(p) for p in [Path(__file__),helper,BASE/'family_parameters.json',network,
        CAL/'canonical_harness.py',CAL/'boundary_factory.py',ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2/evaluate_response.py']}
    rows=[]; selections=[]; diagnostic=[]
    cutoffs=(870.1,1800.1,2700.1,4500.1,6300.1)
    for family in ('boundary','hadi','wang'):
        cfg=BASE/(family+'_config.json'); pins[str(cfg)]=sha256(cfg)
        model=load_base_model(data.geometry,cfg)
        pins.update(model.provenance['model_files'])
        for cutoff in cutoffs:
            w=build_window(data,cutoff,'history_forecast',model_step_sec=1)
            # A genuine forecast must not depend on later traffic states/flows.
            past=copy.copy(data)
            past.cells={t:r for t,r in data.cells.items() if t<=cutoff}
            past.flows={k:r for k,r in data.flows.items() if k[0]<=cutoff}
            past.boundaries={k:r for k,r in data.boundaries.items() if k[0]<=cutoff}
            assert build_window(past,cutoff,'history_forecast',model_step_sec=1)==w
            candidates=['hold']+['restrict_'+z for z in policy['zone_dsds']]
            if cutoff==870.1: candidates.append('actual_rule_replay')
            else: candidates.append('actual_rule_snapshot_hold')
            results={}
            for candidate in candidates:
                steps=copy.deepcopy(w['boundary_steps'])
                for s in steps:
                    t=s['window_start_s']; commands=dict.fromkeys(policy['zone_dsds'],120.)
                    if candidate.startswith('restrict_'):
                        z=candidate[len('restrict_'):]
                        commands[z]=max(60.,120.-20*(1+int((t-cutoff+1e-7)//150)))
                    elif candidate=='actual_rule_replay' and t>=900:
                        # Replay measured commands, not a causal policy prediction.
                        commands=seq[900+150*int((t-900)//150)]
                    elif candidate=='actual_rule_snapshot_hold':
                        commands=seq[900+150*int((cutoff-900)//150)]
                    s['vsl_commands']={f"{c['road']}__seg{c['cell']}":commands.get(c['zone'],120.) for c in bindings}
                pred=model.rollout(w['initial_cells'],steps,params[family],w['initial_origin_queue'],vsl_zone_heads=heads)
                roads=pred['diagnostics']['roads']
                assert all(r['density_projection_count']==0 and r['jam_density_exceedance_count']==0
                    and r['negative_density_count']==0 and r['continuity_residual_max_veh']<1e-6 for r in roads)
                parts={r['road']:r['model_residence_10s_veh_h'] for r in roads}
                source_wait=0.
                for road in model.roads:
                    backlog=0.
                    for i in range(15):
                        a=round(cutoff+30*i,6); b=round(a+30,6)
                        request=sum(s['source_demand_vph'][road]/3600 for s in steps if a-1e-7<=s['window_start_s']<b-1e-7)
                        admitted=sum(f['source_admissions'] for f in pred['flows'] if f['road']==road and abs(f['window_end_s']-b)<1e-7)
                        after=max(0.,backlog+request-admitted);source_wait+=(backlog+after)*30/7200;backlog=after
                row=dict(family=family,cutoff=cutoff,candidate=candidate,FW_E_TTT=parts['FW_E'],FW_W_TTT=parts['FW_W'],
                    freeway_TTT=sum(parts.values()),extra_source_wait=source_wait,screen_cost=sum(parts.values())+source_wait,
                    accepted_source_veh=sum(r['accepted_source_veh'] for r in roads),
                    predicted_merges_veh=sum(f['ramp_merges'] for f in pred['flows']),
                    vsl_binding_cell_seconds=sum(c['desired_speed_binding_samples'] for r in roads for c in r['vsl_binding_audit']['cells']))
                rows.append(row); results[candidate]=row
                if cutoff==870.1 and candidate in ('hold','actual_rule_replay'):
                    save(OUT/f'{family}_{candidate}_870.json',pred)
            baseline=results['hold']
            for row in results.values():
                for key in ('FW_E_TTT','FW_W_TTT','freeway_TTT','screen_cost','extra_source_wait'):
                    row['delta_'+key]=row[key]-baseline[key]
            eligible=[v for k,v in results.items() if not k.startswith('actual_')]
            best=min(eligible,key=lambda r:r['screen_cost'])
            selections.append(dict(family=family,cutoff=cutoff,screen_best=best['candidate'],
                screen_delta=best['delta_screen_cost'],freeway_delta=best['delta_freeway_TTT'],
                candidate_count=len(eligible),actual_controller_invoked=False))
            diagnostic.append(dict(family=family,cutoff=cutoff,**{k:v for k,v in results[candidates[-1]].items() if k.startswith('delta_')}))
            print(family,cutoff,'screen:',best['candidate'],round(best['delta_screen_cost'],3),flush=True)
    observed={}
    for arm in ('none','vsl'):
        d=np.load(HERE/'vsl_decomposition'/arm/'stocks.npz')
        v=integrate(d['times'],d['counts'],870.1,1320.1)
        observed[arm]=dict(FW_E_TTT=float(v[:6].sum()),FW_W_TTT=float(v[6:11].sum()),
            freeway_TTT=float(v[:11].sum()),Omega_TTT=float(v.sum()))
    matched=[]
    for family in params:
        p=next(r for r in rows if r['family']==family and r['candidate']=='actual_rule_replay')
        for metric in ('FW_E_TTT','FW_W_TTT','freeway_TTT'):
            actual=observed['vsl'][metric]-observed['none'][metric]
            matched.append(dict(family=family,metric=metric,actual_delta_veh_h=actual,predicted_delta_veh_h=p['delta_'+metric],
                delta_error_veh_h=p['delta_'+metric]-actual))
    assert all(sha256(p)==h for p,h in pins.items())
    table(OUT/'candidates.csv',rows);table(OUT/'screen_ranking.csv',selections);table(OUT/'common_initial_response.csv',matched)
    save(OUT/'summary.json',dict(scope='Offline fixed-component response and limited VSL screen, NOT production controller or full Omega/RM objective',
        causal_boundaries=True,parameters_refit=False,new_native_run=False,actual_controller_invoked=False,
        forecast_count=len(rows)*2,cutoffs=cutoffs,bindings=bindings,screen_ranking=selections,actual_rule_diagnostics=diagnostic,
        common_initial_observed=observed,common_initial_response=matched,pins=pins,
        paired_crossing_correction_count=correction['completed_window_events'],elapsed_sec=time.perf_counter()-started,
        limitations=['Actual replay uses recorded future commands; traffic boundaries remain identical past150s forecasts.',
            'Common initial870.1 and450s horizon; first command900 is represented at900.1 (0.1s delay).',
            'Cell-center DSD projection is instantaneous; native already-present vehicles retain prior desired speed until crossing a DSD.',
            'After870.1, native arms have divergent histories; later candidate rankings are not matched native benefit validation.',
            'Ramp release held as external historical flow, off stock fixed, no coupled urban cost or NP/NUF constraints.',
            'Screen cost is mainline TTT plus newly rejected interface flow waiting; excludes pre-existing outside queues and urban/ramp costs.',
            'Actual rule snapshot vectors can exceed single-update MPC trust region; excluded from screen ranking.']))
    print(json.dumps(dict(complete=True,road_rollouts=len(rows)*2,elapsed_sec=time.perf_counter()-started,matched=matched)),flush=True)


if __name__=='__main__': main()
