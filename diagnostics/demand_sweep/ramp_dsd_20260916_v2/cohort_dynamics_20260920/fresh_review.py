"""Prospective frozen-model response audit; never fits to these outcomes."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import group,geometry_profile
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.analyze_no_control_corridors import native_frames
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.fast_fixed_profile_verify import verify
from collections import defaultdict
import argparse
import hashlib
import time

HERE=Path(__file__).resolve().parent
ARMS=('none','rm_ramp','vsl','both')


def check_freeze(bank):
    freeze=e.load(bank/'model_freeze.json')
    for file,digest in freeze['pins'].items():
        assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==digest,('Frozen source changed',file)
    return freeze


def initial_lane_state(path,data,model,cutoffs):
    """Current position and preceding150s only; future frames never label state."""
    observer=Observer(data.geometry);geometry=geometry_profile(data.geometry)
    exposures={t:defaultdict(float) for t in cutoffs};moves={t:defaultdict(float) for t in cutoffs}
    east={str(p['connector']):(r,p) for r,p in model.ramps.items() if p['road']=='FW_E'}
    past={t:{} for t in cutoffs}
    for row in e.rows(data.folder/'port_events.csv'):
        if row['kind']!='departure' or row['connector'] not in east:continue
        sec=float(row['time_s']);ramp,spec=east[row['connector']];vid=int(row['vehicle'])
        for t in cutoffs:
            if sec<=t and (vid not in past[t] or sec>past[t][vid][0]):past[t][vid]=(sec,ramp,spec['to_cell'])
    result={};populations={};previous={};evidence={}
    for sec,frame in native_frames(path,evidence,deadline=time.monotonic()+600):
        if sec>max(cutoffs):break
        relevant=[t for t in cutoffs if t-150<sec<=t]
        if not relevant:previous={};continue
        located={};moments=defaultdict(lambda:[0.,0.])
        origin={r:[0.]*len(geometry['widths'][p['to_cell']]) for r,p in east.values()}
        for vid,row in frame.items():
            loc=observer.locate(row)
            if not loc or loc[0]!='FW_E':continue
            cell=loc[1];g=group(cell,row[1]);located[vid]=(row[0],cell,g)
            moments[cell,g][0]+=1;moments[cell,g][1]+=row[3]
            for t in relevant:
                exposures[t][cell,g]+=1
                old=previous.get(vid)
                if old and old[:2]==(row[0],cell) and old[2]!=g:moves[t][cell,old[2],g]+=1
            if sec in past:
                source=past[sec].get(vid)
                if source is not None and source[2]==cell:origin[source[1]][g]+=1
        if sec in cutoffs:
            populations[str(sec)]={str(vid):{'link':frame[vid][0],'cell':loc[1],'group':loc[2],
                'position_m':frame[vid][2]} for vid,loc in located.items()}
            groups=[];rates=[]
            for c,widths in enumerate(geometry['widths']):
                gs=[{'n_veh':moments[c,g][0],'v_kmh':moments[c,g][1]/moments[c,g][0] if moments[c,g][0] else None}
                    for g in range(len(widths))]
                obs=next(r for r in data.cells[sec] if r['road']=='FW_E' and r['cell']==c)
                assert sum(r['n_veh'] for r in gs)==obs['n_veh']
                groups.append(gs)
                rates.append([[moves[sec][c,g,k]/exposures[sec][c,g] if exposures[sec][c,g] else 0.
                               for k in range(len(widths))] for g in range(len(widths))])
            result[str(sec)]={**geometry,'initial_groups':groups,'exchange_rates_per_sec':rates,
                'initial_ramp_origin':origin,'observation_end_s':sec,'history_start_s':sec-150}
        previous=located
    assert set(result)==set(map(str,cutoffs))
    return result,populations


def actual_parts(data,start):
    stocks=e.rows(data.folder/'component_stocks_1s.csv')
    rows=[r for r in stocks if start<int(r['time_s'])<=start+450]
    assert len(rows)==450
    for r in rows:
        t=int(r['time_s'])
        if t%30==0:
            assert int(r['FW_E_mainline'])==sum(x['n_veh'] for x in data.cells[t] if x['road']=='FW_E')
            for kind,label in [('ramp','on'),('offramp','off')]:
                assert int(r['FW_E_'+label])==sum(len(data.port_cohorts[str(t)][str(b['connector'])])
                    for b in data.definitions.values() if b['road']=='FW_E' and b['kind']==kind)
    return {k:sum(int(r['FW_E_'+k]) for r in rows)/3600 for k in ('mainline','on','off')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--bank',type=Path,required=True)
    parser.add_argument('--phase',choices=['verify','predict'],required=True);args=parser.parse_args()
    bank=args.bank.resolve();freeze=check_freeze(bank);protocol=e.load(bank/'protocol.json')
    for arm in ARMS:
        receipt=e.load(bank/arm/'run/run.json')
        assert receipt['completed'] and receipt['terminal_sec']==3000 and not receipt['owned_native_alive']
    if args.phase=='verify':
        result={}
        for arm in ARMS:
            result[arm]=verify(bank/arm/'prepared',bank/arm/'run',bank/'none/run' if arm!='none' else None)
            print(arm,'LDP/readback/exact warmup PASS',flush=True)
        e.save(bank/'paired_verification.json',result);return
    assert all(r['passed'] for r in e.load(bank/'paired_verification.json').values())
    out=bank/'predictions';out.mkdir(exist_ok=False)
    data=e.ObservationData(bank/'observations/none');start=protocol['start_s']
    reference=e.load_base_model(data.geometry,e.ROOT/freeze['models']['reference']/'config.json')
    lane,populations=initial_lane_state(bank/'none/run/vissim_eval/baseline_001.fzp',data,reference,[900,1650,start])
    e.save(out/'initial_lane_states.json',lane)
    e.save(out/'initial_vehicle_locations.json',populations)
    profile=e.load(e.ROOT/freeze['port_profile']);results={}
    actual={arm:actual_parts(e.ObservationData(bank/'observations'/arm),start) for arm in ARMS}
    evidence={}
    for arm in ARMS:
        folder=bank/'observations'/arm;manifest=e.load(folder/'manifest.json')
        component_links={int(k) for k,v in data.geometry['addresses'].items() if v[0]=='FW_E'}
        component_links.update(int(b['connector']) for b in data.definitions.values()
                               if b['road']=='FW_E' and b['kind'] in ('ramp','offramp'))
        removals=[r for r in manifest['removals'] if start<float(r['time_sec'])<=start+450
                  and int(r['link']) in component_links]
        assert not removals,('Component deletion confound',arm,removals)
        stocks=e.rows(folder/'component_stocks_1s.csv')
        evidence[arm]={'component_removals':removals,'outside_source_negative_veh_h':
            sum(int(r['FW_E_source_negative']) for r in stocks if start<int(r['time_s'])<=start+450)/3600,
            'exclusion_events_in_window':[r for r in manifest['exclusions'] if start<r['upper_sec']<=start+450]}
    for name,path in freeze['models'].items():
        folder=e.ROOT/path;model=e.load_base_model(data.geometry,folder/'config.json')
        params=e.load(folder/'selected_parameters.json')['parameters'];arms={};guards={}
        for arm,seq in protocol['candidate_bank'].items():
            def command(t):
                i=int((t-start)//150)
                return ({protocol['meter_id']:seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol['dsd_ids']} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command)
            if name=='port_travel':w['lane_group_dynamics']={'FW_E':lane[str(start)]}
            pred=e.simulate(model,w,params)
            observed=e.ObservationData(bank/'observations'/arm)
            score=e.score_rollout(observed,start,pred,'FW_E');assert not score['invalid']
            arms[arm]={'predicted':parts(pred),'actual':actual[arm],'state_score':score}
            e.save(out/f'{name}_{arm}.json',pred)
        for arm in ARMS:
            arms[arm]['delta']={kind:{k:arms[arm][kind][k]-arms['none'][kind][k] for k in ('mainline','on','off')}
                                for kind in ('predicted','actual')}
            for d in arms[arm]['delta'].values():d['total']=sum(d.values())
        for cutoff in [900,1650,start]:
            w=e.window(data,model,cutoff,'history_forecast',profile,lambda _: ({},{}))
            if name=='port_travel':w['lane_group_dynamics']={'FW_E':lane[str(cutoff)]}
            guards[str(cutoff)]=e.score_rollout(data,cutoff,e.simulate(model,w,params),'FW_E')
        predicted_choice=min(ARMS,key=lambda a:sum(arms[a]['predicted'].values()))
        observed_choice=min(ARMS,key=lambda a:sum(actual[a].values()))
        results[name]={'arms':arms,'state_guards':guards,
            'predicted_ranking':sorted(ARMS,key=lambda a:sum(arms[a]['predicted'].values())),
            'actual_ranking':sorted(ARMS,key=lambda a:sum(actual[a].values())),
            'selected_arm':predicted_choice,'best_observed_arm':observed_choice,
            'selection_regret_veh_h':sum(actual[predicted_choice].values())-sum(actual[observed_choice].values()),
            'component_delta_errors':{a:{k:arms[a]['delta']['predicted'][k]-arms[a]['delta']['actual'][k]
                for k in ('mainline','on','off','total')} for a in ARMS[1:]}}
        print(name,{arm:{k:round(d['total'],6) for k,d in row['delta'].items()} for arm,row in arms.items()},flush=True)
    check_freeze(bank)
    e.save(out/'result.json',{'seed':protocol['seed'],'start_s':start,'horizon_s':450,'models':results,
        'native_evidence':evidence,
        'parameters_frozen_before_run':True,'future_state_features':False,'qualified':False,
        'scope':protocol['scope'],'native_TTT_convention':'1s end-frame inventory; model uses its native conservative residence integrals',
        'warning':'Qualification requires component and material-response checks, not only a matching total sign.'})


if __name__=='__main__':main()
