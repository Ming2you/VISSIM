"""Summarize already saved two-arm term traces and native caches only."""
import csv
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROUTED='--route-inventory' in sys.argv
EARLY_RESET='--reset-at-cell25' in sys.argv
assert not (ROUTED and EARLY_RESET)
OUT=HERE/('vsl_reset_location_trace' if EARLY_RESET else 'vsl_route_inventory_trace' if ROUTED else 'vsl_response_trace')
ARMS=('held_actual','vsl_release')


def load(path):
    return json.loads(path.read_bytes())


def native_reset_location():
    """Audit previously extracted desired-speed samples; no trajectory reread."""
    import statistics
    root=HERE.parent/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
    source=root/'vsl_native_exposure';manifest=load(source/'extraction.json')
    protocol=load(source/'protocol.json');geometry=load(root/'route_inventory/compiled.json')
    signs=[r for r in protocol['signs'] if r['no'] in (67,68,69)]
    assert len(signs)==3 and len({s['x_m'] for s in signs})==1
    actual=signs[0]['x_m'];bounds=geometry['bounds']['FW_E'];lo,hi=bounds[25:27]
    assert lo<actual<hi and all(s['cell']==25 for s in signs)
    results=[];pins={str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    for case,a,b in (('s29_early','none','vsl'),('s29_late','hold','hold_vsl90')):
        data={}
        for arm in (a,b):
            p=source/(case+'_'+arm+'_frames.json.gz')
            expected=next(r for r in manifest['results'] if (r['case'],r['arm'])==(case,arm))
            digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==expected['frame_sha256']
            pins[str(p)]=digest
            with gzip.open(p,'rt',encoding='utf-8') as f:data[arm]=json.load(f)
        assert data[a]['initial_whole_network_ids']==data[b]['initial_whole_network_ids']
        ids=set(data[a]['initial_whole_network_ids']);samples={'before':[],'after':[]}
        counts={'before':0,'after':0};tracks={}
        for key,rows in data[b]['frames'].items():
            current={r[0]:r for r in rows};other={r[0]:r for r in data[a]['frames'][key]}
            for r in rows:
                if r[1]==25:counts['before' if r[2]<actual else 'after']+=1
                tracks.setdefault(r[0],[]).append((float(key),r[2]))
            for vehicle in ids & set(current) & set(other):
                x,y=other[vehicle],current[vehicle]
                if x[1]!=25 or y[1]!=25:continue
                label='before' if x[2]<actual and y[2]<actual else 'after' if x[2]>=actual and y[2]>=actual else None
                if label:samples[label].append(dict(desired_delta=y[5]-x[5],speed_delta=y[4]-x[4]))
        delays=[]
        for track in tracks.values():
            track.sort()
            crosses={}
            for (t0,x0),(t1,x1) in zip(track,track[1:]):
                if abs(t1-t0-5)>1e-6 or x1<x0:continue
                for name,threshold in [('native_reset',actual),('cell26',hi)]:
                    if x0<threshold<=x1:crosses.setdefault(name,(t0,t1))
            if len(crosses)==2:
                p0,p1=crosses['native_reset'];q0,q1=crosses['cell26']
                delays.append(dict(observed_frame_delay=q1-p1,lower_sec=max(0.,q0-p1),upper_sec=q1-p0))
        summary={}
        for label,rows in samples.items():
            summary[label]=dict(paired_initial_vehicle_samples=len(rows),
                mean_desired_delta_kmh=statistics.mean(r['desired_delta'] for r in rows) if rows else None,
                mean_speed_delta_kmh=statistics.mean(r['speed_delta'] for r in rows) if rows else None,
                desired_same_within_002=sum(abs(r['desired_delta'])<=.02 for r in rows))
        results.append(dict(case=case,cell25_all_vsl_samples=counts,
            paired_same_region_initial_vehicles=summary,crossing_samples=len(delays),
            median_frame_delay_sec=statistics.median(r['observed_frame_delay'] for r in delays) if delays else None,
            mean_delay_bracket_sec=[statistics.mean(r[k] for r in delays) for k in ('lower_sec','upper_sec')] if delays else None))
    result=dict(native_reset_m=actual,cell25_start_m=lo,model_reset_m=hi,
        model_late_distance_m=hi-actual,test_early_distance_m=actual-lo,
        cases=results,pins=pins,new_fzp_scans=0,new_native_runs=0,new_forecasts=0,
        caveat='Common initial IDs at the same later time/region are a conditional sample. Delays are5s crossing brackets, not exact event times or causal speed gains.')
    target=HERE/'vsl_reset_location_native.json'
    assert not target.exists(), 'Preserve completed diagnostic'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='pins'},ensure_ascii=False,indent=2))


def main():
    assert load(OUT/'completion.json')['stage']==('two_reset_location_forecasts_traced' if EARLY_RESET else 'two_route_inventory_forecasts_traced' if ROUTED else 'two_unchanged_forecasts_traced')
    traces={}
    reference=HERE.parent/'baseline_reproduction_20260929/cellwise_calibration/expanded_joint/eval_036/reference_config.json'
    assert hashlib.sha256(reference.read_bytes()).hexdigest()=='7f6df2d14795b22d858aa772f5813e42b67f9d1ec4296cc6203bd854c28d83a4'
    fw=load(reference)['freeway'];law=fw['vsl_fd_response']['FW_E']
    assert law==dict(law='carlson',A=.5,E=2.,alpha=0.)
    def at_command(r,command):
        shape=fw['physical_cell_fd']['FW_E'][str(r['cell'])]['metanet_a_m']
        ratio=max(0.,r['rho'])/r['critical'];b=command/110.
        changed_shape=shape*(law['E']-(law['E']-1)*b)
        return r['nominal_fd_speed']*b*math.exp(ratio**shape/shape
            -(ratio/(1+law['A']*(1-b)))**changed_shape/changed_shape)
    for arm in ARMS:
        with gzip.open(OUT/(arm+'.json.gz'),'rt',encoding='utf-8') as stream:traces[arm]=json.load(stream)
    native=list(csv.DictReader((HERE/'analysis/mainline_snapshots.csv').open(encoding='utf-8-sig')))
    lookup={(r['arm'],int(r['sim_sec']),int(r['cell'])):r for r in native if r['road']=='FW_E'}
    summaries=[];checks={};indices={}
    for arm,rows in traces.items():
        idx={(r['time'],r['cell']):r for r in rows};assert len(idx)==31*450
        indices[arm]=idx
        mass=max(abs(r['next_stock']-r['stock']-r['dt_h']*(r['q_in']-r['q_out'])) for r in rows)
        stock_next=max(abs(r['next_stock']-idx[r['time']+1,r['cell']]['stock']) for r in rows if r['time']<2699)
        speed_next=max(abs(r['final_speed']-idx[r['time']+1,r['cell']]['speed']) for r in rows if r['time']<2699)
        cohort=max(abs(sum(r['cohorts'].values())-r['stock']) for r in rows)
        assert max(mass,stock_next,speed_next,cohort)<1e-7,(arm,mass,stock_next,speed_next,cohort)
        target_residual=max(abs(sum(n*at_command(r,float(k)) for k,n in r['cohorts'].items())/r['stock']-r['desired'])
            for r in rows if r['stock']>1e-9)
        assert target_residual<1e-7,(arm,target_residual)
        checks[arm]=dict(mass_max=mass,stock_next_max=stock_next,speed_next_max=speed_next,cohort_max=cohort,
            carlson_cohort_target_reconstruction_max=target_residual)
        for begin in (2250,2400,2550):
            for cell in range(31):
                part=[idx[t,cell] for t in range(begin,begin+150)]
                actual=lookup[arm,begin+150,cell]
                row=dict(arm=arm,start_sec=begin,cell=cell,end_stock=part[-1]['next_stock'],
                    end_speed=part[-1]['final_speed'],native_end_stock=float(actual['vehicles']),
                    native_end_speed=float(actual['speed_kph']),
                    mainline_out=sum(r['mainline_out']*r['dt_h'] for r in part),
                    in_veh=sum(r['q_in']*r['dt_h'] for r in part),
                    off_out=sum(r['off_out']*r['dt_h'] for r in part),
                    ramp=sum(r['ramp']*r['dt_h'] for r in part),
                    entry=sum(r['entry']*r['dt_h'] for r in part),
                    receiving_binding_seconds=sum(r['downstream_receiving'] is not None and r['downstream_receiving']<r['mainline_sending']-1e-8 for r in part),
                    fd_below_nominal_seconds=sum(r['nominal_fd_speed']-r['desired']>1e-8 for r in part),
                    same_density_V90_minus_V110=sum(at_command(r,90)-r['nominal_fd_speed'] for r in part)/len(part),
                    same_density_V90_greater_seconds=sum(at_command(r,90)>r['nominal_fd_speed']+1e-8 for r in part),
                    active_cohort_seconds=sum(any(float(k)<109.5 and n>1e-8 for k,n in r['cohorts'].items()) for r in part))
                for field in ('speed','rho','desired','nominal_fd_speed','relaxation','convection','anticipation','lane_drop','merge','boundary_cap','q_raw','q_values'):
                    row['mean_'+field]=sum(r[field] for r in part)/len(part)
                summaries.append(row)
    with (OUT/'cell_windows.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0]));writer.writeheader();writer.writerows(summaries)
    impacts=[]
    for cell in range(31):
        differences={key:max(abs(indices[ARMS[1]][t,cell][key]-indices[ARMS[0]][t,cell][key]) for t in range(2250,2700))
            for key in ('desired','speed','stock','mainline_out')}
        first={key:next((t for t in range(2250,2700) if abs(indices[ARMS[1]][t,cell][key]-indices[ARMS[0]][t,cell][key])>1e-7),None)
            for key in differences}
        impacts.append(dict(cell=cell,max_absolute_differences=differences,first_nonzero_sec=first))
    delta=[]
    for begin in (2250,2400,2550):
        subsets={arm:[r for r in summaries if r['arm']==arm and r['start_sec']==begin] for arm in ARMS}
        a,b=subsets[ARMS[0]],subsets[ARMS[1]]
        delta.append(dict(start_sec=begin,model_delta_end_stock=sum(r['end_stock'] for r in b)-sum(r['end_stock'] for r in a),
            native_delta_end_stock=sum(r['native_end_stock'] for r in b)-sum(r['native_end_stock'] for r in a),
            model_delta_terminal=b[-1]['mainline_out']-a[-1]['mainline_out'],
            model_delta_source=b[0]['entry']-a[0]['entry']))
    value=dict(checks=checks,impacts_by_cell=impacts,window_deltas=delta,
        receiving_binding_seconds_by_arm={arm:sum(r['downstream_receiving'] is not None and r['downstream_receiving']<r['mainline_sending']-1e-8 for r in rows) for arm,rows in traces.items()},
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),reference,OUT/'completion.json',HERE/'analysis/mainline_snapshots.csv')},
        forecasts=0,new_fzp_scans=0,new_native_runs=0,coefficient_fits=0)
    (OUT/'assessment.json').write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(checks=checks,window_deltas=delta,receiving=value['receiving_binding_seconds_by_arm']),indent=2))
    for cell in range(31):
        row=impacts[cell]
        if row['max_absolute_differences']['speed']>1e-6:
            print(json.dumps(row))
    print('ACTIVE COHORT CELLS; all 450s')
    for arm in ARMS:
        for cell in range(31):
            part=[r for r in summaries if r['arm']==arm and r['cell']==cell]
            if sum(r['active_cohort_seconds'] for r in part):
                print(json.dumps(dict(arm=arm,cell=cell,below_nominal_sec=sum(r['fd_below_nominal_seconds'] for r in part),
                    active_sec=sum(r['active_cohort_seconds'] for r in part),
                    V90_greater_seconds=sum(r['same_density_V90_greater_seconds'] for r in part),
                    V90_minus_V110=[r['same_density_V90_minus_V110'] for r in part],
                    nominal=[r['mean_nominal_fd_speed'] for r in part],desired=[r['mean_desired'] for r in part],
                    final_speed=[r['end_speed'] for r in part],native=[r['native_end_speed'] for r in part])))


if __name__=='__main__':
    if '--native-reset-location' in sys.argv:native_reset_location()
    else:main()
