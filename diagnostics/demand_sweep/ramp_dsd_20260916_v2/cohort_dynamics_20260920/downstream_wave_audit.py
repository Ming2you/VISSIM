"""Retrospective lane/space audit of the missed RM downstream response.

No fitting or future observations enter the plant. 100m occupancy is an
observation scale, NOT an inferred capacity or proposed binary closure law.
"""
from pathlib import Path
from collections import defaultdict, Counter
import csv, json, math, hashlib, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES

START, END = 2400, 2850


def extract(path, extended):
    stamp = (path.stat().st_size, path.stat().st_mtime_ns)
    frames = defaultdict(dict)
    header = None
    with path.open('rb') as stream:
        for line in stream:
            if line.startswith(b'$VEHICLE:'):
                header = line.rstrip().decode('ascii')
            if line[:1] not in b'0123456789' or not line.strip():
                continue
            t = float(line.split(b';', 1)[0])
            if t > END:
                break
            if t < START-150:
                continue
            assert t == int(t)
            fields = [x.strip() for x in line.rstrip(b'\r\n').split(b';')]
            link = int(fields[2])
            if link not in (119, 10702, 24):
                continue
            row = dict(time_s=int(t), vehicle=int(fields[1]), link=link,
                       lane=int(fields[3]), pos=float(fields[4]), v=float(fields[6]))
            if extended:
                row.update(desired=float(fields[9]), length=float(fields[10]),
                           lane_change=fields[16].decode(), interaction=fields[17].decode(),
                           target_type=fields[18].decode(), target=int(fields[19]) if fields[19] else None)
            assert row['vehicle'] not in frames[int(t)]
            row['original9'] = fields[:9]
            frames[int(t)][row['vehicle']] = row
    assert set(frames) == set(range(START-150, END+1))
    assert stamp == (path.stat().st_size, path.stat().st_mtime_ns)
    assert header and ('DESSPEED' in header) == extended
    return frames, dict(path=str(path.relative_to(ROOT)), size=stamp[0], mtime_ns=stamp[1],
                        header=header, selected_rows=sum(map(len, frames.values())),
                        hash_policy='size/mtime unchanged; matches archived native10s snapshots below, no whole-file rehash')


def aggregate(frames, geometry, critical, binsize):
    cells = {r['cell']: r for r in geometry['cells'] if r['road']=='FW_E'}
    shifts = {r['link']: r['offset_m'] for r in geometry['chains']['FW_E']}
    states, local, traces = {}, [], []
    for t, frame in frames.items():
        grouped = defaultdict(list)
        for v in frame.values():
            x=shifts[v['link']]+v['pos']
            eligible=[c for c,r in cells.items() if r['start_m']<=x<r['end_m']]
            if not eligible:
                # Native1s records may overshoot the terminal during the
                # final step. Retain the canonical observer's last-cell
                # stock convention, but do not pack overshoot into a100m bin.
                assert x>=cells[20]['end_m'] and x-cells[20]['end_m']<=v['v']/3.6+11.5
                c=20
            else:c=eligible[0]
            v['cell']=c;v['chain_m']=x
            grouped[c,v['lane']].append(v)
        for c in range(14,21):
            geo=cells[c]
            for lane in range(1,4):
                vs=grouped[c,lane]; n=len(vs)
                states[t,c,lane]=dict(n=n,v=sum(x['v'] for x in vs)/n if n else None)
                # Equal subsegments avoid an arbitrarily tiny end bin.
                count=math.ceil(geo['length_km']*1000/binsize)
                length=geo['length_km']*1000/count
                bins=defaultdict(list)
                for v in vs:
                    if v['chain_m']<geo['end_m']:
                        bins[int((v['chain_m']-geo['start_m'])/length)].append(v)
                dense=[b for b,x in bins.items() if len(x)/(length/1000)>critical[c]]
                slow=sum(v['v']<30 for v in vs);stopped=sum(v['v']<5 for v in vs)
                masked=n/geo['length_km']<critical[c] and any(any(v['v']<5 for v in bins[b]) for b in dense)
                local.append(dict(time_s=t,cell=c,lane=lane,n=n,speed=states[t,c,lane]['v'],
                                  rho=n/geo['length_km'],slow_veh=slow,stopped_veh=stopped,
                                  local_max_rho=max((len(x)/(length/1000) for x in bins.values()),default=0),
                                  masked_stopped_cluster=masked,bin_length_m=length))
        if t in (2490,2550,2580,2640,2760,2820):
            for c in range(14,21):
                vs=[v for v in frame.values() if v['cell']==c]
                if not vs:continue
                target=min(vs,key=lambda v:v['v'])
                trace=[];seen=set()
                for _ in range(12):
                    if target['vehicle'] in seen:break
                    seen.add(target['vehicle'])
                    trace.append({k:v for k,v in target.items() if k!='original9'})
                    if target.get('target_type')!='Vehicle' or target.get('target') not in frame:break
                    target=frame[target['target']]
                if trace[0]['v']<30:traces.append(dict(time_s=t,cell=c,target_chain=trace))
    return states,local,traces


def main():
    out=HERE/'downstream_wave_v2';out.mkdir(exist_ok=False)
    _,folder,bank,start=next(r for r in CASES if r[0]==23)
    assert start==START
    geom=e.load(folder/'geometry.json')
    config=HERE/'transport_step1_exchange_off_v2/config.json'
    params_path=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(params_path)['parameters']
    model=e.load_base_model(geom,config)
    cfg=model._config('FW_E',params['by_direction']['FW_E'])
    critical={i:float(r['rho_crit']) for i,r in enumerate(cfg.network.freeway_segment_params['FW_E'])}
    sources={
        'none':HERE/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp',
        'rm_ramp':bank/'run_rm_ramp/vissim_eval/baseline_001.fzp',
    }
    frames={};receipts={};native={};rows={};validation={};traces={}
    files=[Path(__file__),config,params_path,folder/'geometry.json']
    for arm,path in sources.items():
        frames[arm],receipts[arm]=extract(path,arm=='none')
        native[arm],rows[arm],traces[arm]=aggregate(frames[arm],geom,critical,100.)
        moments=HERE/f'rm_moments_v1/s23_{arm}.json';files.append(moments)
        checks=0
        for r in e.load(moments)['rows']:
            t,c=r['time_s'],r['cell']
            if START<=t<=END and 14<=c<=20 and r['lane']!='all':
                actual=native[arm][t,c,int(r['lane'])]
                assert actual['n']==r['n']
                if actual['n']:assert abs(actual['v']-r['speed_mean'])<1e-8
                checks+=1
        validation[arm]=checks
        with (out/f'{arm}_lane_1s.csv').open('x',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[arm][0]));writer.writeheader();writer.writerows(rows[arm])
        print('EXTRACTED',arm,receipts[arm]['selected_rows'],checks,flush=True)
    exact=0
    for t in range(START-150,START+1):
        assert {i:r['original9'] for i,r in frames['none'][t].items()}=={i:r['original9'] for i,r in frames['rm_ramp'][t].items()}
        exact+=len(frames['none'][t])
    summaries={}
    for arm in sources:
        summaries[arm]={}
        for c in range(14,21):
            use=[r for r in rows[arm] if r['cell']==c and START<r['time_s']<=END]
            summaries[arm][str(c)]={
                'ttt_1s_veh_h':sum(r['n'] for r in use)/3600,
                'stopped_vehicle_sec':sum(r['stopped_veh'] for r in use),
                'slow30_vehicle_sec':sum(r['slow_veh'] for r in use),
                'lane_seconds_masked_stopped_cluster':sum(r['masked_stopped_cluster'] for r in use),
                'weighted_speed_kmh':sum(r['n']*r['speed'] for r in use if r['n'])/sum(r['n'] for r in use),
            }
    # Identical clock/physical cell comparison to saved model; no refitting.
    spatial=[];preds={};snapshot_checks=0
    for arm in sources:
        path=HERE/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json';files.append(path)
        preds[arm]=e.load(path)
    for c in range(14,21):
        row=dict(cell=c,critical=critical[c],by_150s=[])
        for lo in (2400,2550,2700):
            modes={}
            for arm in sources:
                observed=[r for r in rows[arm] if r['cell']==c and lo<r['time_s']<=lo+150]
                predicted=[r for r in preds[arm]['lane_groups']['FW_E'] if r['cell']==c and lo<r['time_s']<=lo+150]
                assert len(predicted) in (150,450)
                modes[arm]=dict(native_ttt=sum(r['n'] for r in observed)/3600,
                               model_ttt=sum(r['n_veh'] for r in predicted)/3600,
                               native_speed=sum(r['n']*r['speed'] for r in observed if r['n'])/sum(r['n'] for r in observed),
                               model_speed=sum(r['n_veh']*r['v_kmh'] for r in predicted)/sum(r['n_veh'] for r in predicted))
                snapshot_checks+=1
            row['by_150s'].append(dict(start_s=lo,arms=modes,deltas={k:modes['rm_ramp'][k]-modes['none'][k] for k in modes['none']}))
        spatial.append(row)
    # Check whether the masked-cluster observation relies on one100m grid.
    sensitivity={}
    for scale in (75.,150.):
        sensitivity[str(scale)]={}
        for arm in sources:
            _,rr,_=aggregate(frames[arm],geom,critical,scale)
            sensitivity[str(scale)][arm]=sum(r['masked_stopped_cluster'] for r in rr if START<r['time_s']<=END)
    e.save(out/'interaction_examples.json',traces['none'])
    result=dict(status='OBSERVATION_DIAGNOSIS_NOT_CALIBRATION',scope='Seed23 RM10490 vs NC, cells14..20; no Omega claim',
                previous_goal_turn='no progress: answered status only; next safe action is this matched trajectory audit',
                summaries=summaries,spatial=spatial,sensitivity=sensitivity,
                validation=dict(snapshot_stock_and_speed=validation,identical_precontrol_original9_rows=exact,
                                matched_clock_cost_comparisons=snapshot_checks),
                critical_density=critical,source_receipts=receipts,
                interpretation_limits=['Subcell critical exceedance is a diagnostic scale comparison, not measured capacity.',
                    'Interaction target chains show simultaneous dependency, not proof that a lane change caused a stop.',
                    'Only pre-intervention IDs are interchangeable between arms; post-intervention IDs were not paired.',
                    'No causal model feature or closure coefficient is fitted from future stop flags.'],
                sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                future_inputs_to_plant=False,new_native_runs=0,qualified=False)
    e.save(out/'result.json',result)
    print('VERIFIED',result['validation'],flush=True)
    print('COSTS',{a:sum(r['ttt_1s_veh_h'] for r in d.values()) for a,d in summaries.items()},flush=True)
    print('MASKED',{a:sum(r['lane_seconds_masked_stopped_cluster'] for r in d.values()) for a,d in summaries.items()},sensitivity,flush=True)


if __name__=='__main__':main()
