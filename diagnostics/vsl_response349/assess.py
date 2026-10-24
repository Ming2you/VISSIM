"""Assess already completed bounded forecasts; never start another prediction."""
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(Path(p).read_bytes())

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def targets(folder,at,tuning):
    from evaluation.controllers import offramp_routing as routing
    document=read(ROOT/read(tuning)['freeway']['offramp_route_inventory'])
    mapping=json.loads(routing._pinned(document['mapping']))
    runtime=routing.compile_inventory(document,mapping)
    result=[];pins={}
    for t in range(at,at+451,150):
        path=folder/f'state_{t:06}.json';raw=read(path);pins[str(path)]=digest(path)
        assert raw['sim_sec']==t and raw['vehicle_records']['complete']
        cells={fw:[[] for _ in range(len(bounds)-1)] for fw,bounds in runtime['bounds'].items()}
        ports={k:[] for k in runtime['branches']}
        for item in raw['vehicle_records']['records']:
            physical=str(item['link_no'])
            if physical in ports:ports[physical].append(item)
            if physical not in runtime['physical']:continue
            road,_,cell=routing._position(runtime,physical,item['position_m'])
            cells[road][cell].append(item)
        result.append(dict(time_sec=t,
            n={fw:[len(row) for row in rows] for fw,rows in cells.items()},
            speed={fw:[math.fsum(x['speed_kph'] for x in row)/len(row) if row else None for row in rows] for fw,rows in cells.items()},
            stopped={fw:[sum(x['stopped'] for x in row) for row in rows] for fw,rows in cells.items()},
            ports={k:dict(n=len(row),stopped=sum(x['stopped'] for x in row)) for k,row in ports.items()},
            obs150_detectors=raw['obs150']['detectors']))
    return result,pins

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--arm',required=True);ap.add_argument('--at',type=int,required=True)
    ap.add_argument('--legacy-urban',action='store_true');a=ap.parse_args()
    assert not (a.out/'assessment.json').exists(),'Preserve completed assessment'
    folder=Path(f'E:/VISSIM_runs/20261008_coupling268_{a.arm}_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
    tuning=HERE/'legacy_urban_diagnostic_config.json' if a.legacy_urban else ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native348/optimized_config.json'
    truth,pins=targets(folder,a.at,tuning)
    progress=read(a.out/'prediction_progress.json');snap=read(a.out/'recorded_snapshots.json')
    err=max(abs(x-y) for fw in truth[0]['n'] for x,y in zip(snap[0]['n'][fw],truth[0]['n'][fw]))
    assert err<1e-7,('Initial physical31 counts differ',err)
    rows=[]
    for pred,obs in zip(snap[1:],truth[1:]):
        assert pred['time_sec']==obs['time_sec']
        for fw in obs['n']:
            nerr=[x-y for x,y in zip(pred['n'][fw],obs['n'][fw])]
            verr=[x-y for x,y in zip(pred['speed'][fw],obs['speed'][fw]) if y is not None]
            rows.append(dict(time_sec=obs['time_sec'],freeway=fw,n_mae=sum(map(abs,nerr))/len(nerr),
                n_total_error=sum(nerr),speed_mae=sum(map(abs,verr))/len(verr),speed_bias=sum(verr)/len(verr),
                cells=[dict(cell=i,n_pred=pred['n'][fw][i],n_observed=obs['n'][fw][i],speed_pred=pred['speed'][fw][i],
                    speed_observed=obs['speed'][fw][i],stopped_observed=obs['stopped'][fw][i]) for i in range(len(nerr))]))
    areas={p['name']:read(a.out/(p['name']+'_control_area.json')) for p in progress}
    comparison=None
    if 'vsl90' in areas and 'vsl110' in areas:
        lo,hi=areas['vsl90'],areas['vsl110']
        comparison=dict(omega_delta_veh_h=lo['ttt_veh_h']-hi['ttt_veh_h'],
            flow_delta={k:lo['flow_counts'].get(k,0.)-hi['flow_counts'].get(k,0.) for k in sorted(set(lo['flow_counts'])|set(hi['flow_counts']))
                if abs(lo['flow_counts'].get(k,0.)-hi['flow_counts'].get(k,0.))>1e-7},
            native_counterfactual_available=False)
    cache=Path('E:/VISSIM_analysis/20261010_coupling268_three8100_v2')/a.arm/'area_timeseries.csv'
    native=None
    if cache.exists():
        with cache.open(encoding='utf-8-sig',newline='') as f:points={float(row['sim_sec']):float(row['ttt_veh_h_cumulative']) for row in csv.DictReader(f)}
        def cumulative(t):
            if t in points:return points[t]
            low=max(x for x in points if x<t);high=min(x for x in points if x>t)
            assert high-low<=5.01,'Unexpected native sample gap'
            return points[low]+(points[high]-points[low])*(t-low)/(high-low)
        native=cumulative(a.at+450)-cumulative(a.at)
    for p in [tuning,HERE/'forecast.py',Path(__file__),a.out/'prediction_progress.json']:
        pins[str(p)]=digest(p)
    def save(name,value):(a.out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    save('native_targets.json',truth)
    save('assessment.json',dict(status='assessed_completed_forecasts',arm=a.arm,at_sec=a.at,
        scope='Actual commands are conditional inputs. Legacy urban initialization explicitly excludes native348 urban recipe.' if a.legacy_urban else 'Actual commands are conditional inputs.',
        latest_full_plant_validation=not a.legacy_urban,initial_stock_max_error=err,errors=rows,
        new_predictions_in_assessment=0,completed_predictions=len(progress),native_omega_ttt_cached_interpolated_veh_h=native,
        native_ttt_note='Existing 5s FZP cumulative cache, linear interpolation only at 0.1s-offset endpoints; diagnostic approximation, not exact event-time integral.',
        predicted_omega_ttt_veh_h=areas['recorded']['ttt_veh_h'],vsl90_minus110=comparison,source_pins=pins))
    print(json.dumps(dict(arm=a.arm,at=a.at,native_ttt=native,predicted_ttt=areas['recorded']['ttt_veh_h'],
        errors=[{k:v for k,v in row.items() if k!='cells'} for row in rows],vsl_delta=None if comparison is None else comparison['omega_delta_veh_h']),indent=2))

if __name__=='__main__':main()
