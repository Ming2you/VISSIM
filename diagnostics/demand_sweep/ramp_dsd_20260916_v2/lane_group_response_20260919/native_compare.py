"""Post-run group response comparison; these future records never enter forecasts."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import HERE, group
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.analyze_no_control_corridors import native_frames
from collections import defaultdict
import time


def main():
    out=HERE/'native_comparison_v1';out.mkdir(exist_ok=False)
    data=e.ObservationData(CASES[1][1]);observer=Observer(data.geometry);actual={};predicted={}
    for arm,run in [('none',H/'rules_4500_s23_v1/run_none'),('vsl',H/'response_late_s23_v1/run_vsl')]:
        sums=defaultdict(lambda:[0.,0.,0.,0.]);previous={};evidence={};frames=0
        for sec,frame in native_frames(run/'vissim_eval/baseline_001.fzp',evidence,deadline=time.monotonic()+600):
            if not 2400<=sec<=2850:continue
            current={}
            for vid,r in frame.items():
                loc=observer.locate(r)
                if not loc or loc[0]!='FW_E' or not 5<=loc[1]<=14:continue
                i=loc[1];g=group(i,r[1]);current[vid]=(r[0],i,g)
                if sec==2400:continue
                sums[i,g][0]+=1;sums[i,g][1]+=r[3];sums[i,g][2]+=int(r[3]<5.)
                old=previous.get(vid)
                if old and old[:2]==(r[0],i) and old[2]!=g:sums[i,g][3]+=1
            if sec>2400:frames+=1
            previous=current
        assert frames==450
        actual[arm]={f'{i}:{g}':{'n_mean':x[0]/450,'v_mean':x[1]/x[0] if x[0] else None,
                    'stopped_veh_s':x[2],'group_entries_by_lateral_exchange':x[3]} for (i,g),x in sums.items()}
        e.save(out/f'evidence_{arm}.json',{'path':str((run/'vissim_eval/baseline_001.fzp').relative_to(e.ROOT)),**evidence})
        sums=defaultdict(lambda:[0.,0.])
        pred=e.load(HERE/f'qualification_v4/prediction_23_{arm}.json')
        for r in pred['lane_groups']['FW_E']:
            if 5<=r['cell']<=14:
                x=sums[r['cell'],r['group']];x[0]+=r['n_veh'];x[1]+=r['n_veh']*r['v_kmh']
        predicted[arm]={f'{i}:{g}':{'n_mean':x[0]/45,'v_mean':x[1]/x[0] if x[0] else None} for (i,g),x in sums.items()}
        print('NATIVE GROUP COMPARE',arm,frames,flush=True)
    rows=[]
    for key in actual['none']:
        row={'cell':int(key.split(':')[0]),'group':int(key.split(':')[1])}
        for metric in ['n_mean','v_mean']:
            for source,values in [('native',actual),('predicted',predicted)]:
                row[source+'_'+metric+'_delta']=values['vsl'][key][metric]-values['none'][key][metric]
        rows.append(row)
    e.save(out/'results.json',{'seed':23,'window':[2400,2850],'actual':actual,'predicted':predicted,'deltas':rows,
        'quadrature':'Native1s end frames vs model10s end frames; group response diagnostic, not a new TTT definition',
        'future_measurements_used_as_inputs':False})


if __name__=='__main__':main()
