"""Build causal state/next-10s exchange pairs from completed native recordings."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, H
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.lane_group_response_20260919.extract import group, geometry_profile
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from collections import defaultdict
import csv
import hashlib
import time

HERE=Path(__file__).resolve().parent


def extract(path,geometry,start,end,out):
    observer=Observer(geometry);profile=geometry_profile(geometry)
    lengths={r['cell']:r['length_km'] for r in geometry['cells'] if r['road']=='FW_E'}
    widths=profile['widths'];previous={};snapshots={};moments=defaultdict(lambda:[0.,0.])
    exposures=defaultdict(float);moves=defaultdict(float);last=None;rows_read=0
    samples=[];skipped=0;cross_cell_changes=0
    def frame(sec):
        if sec%10:return
        if sec>start:
            initial=snapshots[sec-10]
            for c in range(5,15):
                for g in range(len(widths[c])):
                    for k in range(len(widths[c])):
                        if abs(g-k)!=1:continue
                        ns,vs=initial.get((c,g),(0.,0.));nt,vt=initial.get((c,k),(0.,0.))
                        samples.append({'time_s':sec-10,'label_end_s':sec,'cell':c,'g':g,'k':k,
                            'donor_n':ns,'recipient_n':nt,'donor_v':vs/ns if ns else None,
                            'recipient_v':vt/nt if nt else None,'donor_rho':ns/(lengths[c]*widths[c][g]),
                            'recipient_rho':nt/(lengths[c]*widths[c][k]),
                            'exposure_veh_sec':exposures[c,g],'moves':moves[c,g,k]})
            exposures.clear();moves.clear()
        snapshots[sec]=dict(moments)
        if sec-10 in snapshots:del snapshots[sec-10]
    with path.open('rb') as stream:
        for line in stream:
            if not line[:1].isdigit():continue
            p=line.rstrip(b'\r\n;').split(b';');sec=int(float(p[0]))
            if sec<start:continue
            if sec>end:break
            if last is not None and sec!=last:
                frame(last);moments=defaultdict(lambda:[0.,0.])
            last=sec;rows_read+=1
            link=int(p[2])
            if link not in observer.addresses:continue
            lane=int(p[3]);pos=float(p[4]);v=float(p[6]);loc=observer.locate((link,lane,pos,v))
            if not loc or loc[0]!='FW_E' or not 5<=loc[1]<=14:continue
            c=loc[1];g=group(c,lane);vid=int(p[1]);old=previous.get(vid)
            moments[c,g][0]+=1;moments[c,g][1]+=v
            if sec>start:
                exposures[c,g]+=1
                if old and old[0]==sec-1 and old[1]==link and old[3]!=g:
                    if old[2]!=c:cross_cell_changes+=1
                    elif abs(old[3]-g)==1:moves[c,old[3],g]+=1
                    else:skipped+=1
            previous[vid]=(sec,link,c,g)
    frame(last)
    assert last==end
    with out.open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(samples[0]));writer.writeheader();writer.writerows(samples)
    return {'source':str(path.relative_to(e.ROOT)),'source_bytes':path.stat().st_size,
        'start_s':start,'end_s':end,'observed_rows':rows_read,'samples':len(samples),
        'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
        'nonadjacent_exchanges_excluded':skipped,'cross_cell_lane_changes_excluded':cross_cell_changes}


def main():
    out=HERE/'observations_v2';out.mkdir(exist_ok=False)
    none_runs={13:H/'rules_4500_v1/run_none',23:H/'rules_4500_s23_v1/run_none',
               33:H/'state_response_20260919/native_s33_v1/run_none'}
    protocol={'training':'Only uncontrolled seeds13/23, state900..4490; target next10s exchanges',
        'development_validation':'Controlled paired banks excluded from fitting; seed33 excluded from fitting but previously inspected in other model development',
        'features':'State at interval start only. Future exposure is a likelihood offset / rate-scoring denominator, never a rollout state input.',
        'candidate_budget':'One pooled Poisson state closure, ridge selected by chronological NC validation; no fitting to TTT or treatment labels',
        'acceptance':'Conservation/default exactness; held-control exchange responses; NC state guard<=old1.10; benefit/component signs and ranking; no automatic promotion',
        'native_runs_started':0,'sources':{}}
    e.save(out/'protocol.json',protocol)
    begun=time.perf_counter()
    for seed,folder,bank,start in CASES:
        geometry=e.ObservationData(folder).geometry
        for arm in ['none','rm_ramp','vsl','both']:
            path=(none_runs[seed] if arm=='none' else bank/('run_'+arm))/'vissim_eval/baseline_001.fzp'
            a,b=(750,4500) if arm=='none' else (start-150,start+450)
            info=extract(path,geometry,a,b,out/f's{seed}_{arm}.csv')
            e.save(out/f's{seed}_{arm}_source.json',{'seed':seed,'arm':arm,**info})
            print('EXTRACT',seed,arm,info['samples'],round(time.perf_counter()-begun,1),flush=True)


if __name__=='__main__':main()
