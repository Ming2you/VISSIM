"""Post-run10s desired/actual speed moments; exact baseline replay proof."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_exchange_20260920.analyze_dispersion import records
from collections import defaultdict
import math
import argparse

HERE=Path(__file__).resolve().parent;H=HERE.parent


def extract_speeds(run,geometry,start=2400,end=2850):
    """Speed-only diagnostic for older nine-column FZP; no DESSPEED inferred."""
    observer=Observer(geometry);moments=defaultdict(lambda:[0.,0.]);last=None
    path=run/'vissim_eval/baseline_001.fzp';before=path.stat()
    for p in records(path):
        sec=int(float(p[0]))
        if sec>end:break
        last=sec
        if sec<start or sec%10:continue
        link,lane=int(p[2]),int(p[3]);speed=float(p[6])
        loc=observer.locate((link,lane,float(p[4]),speed))
        if not loc or loc[0]!='FW_E':continue
        for group in ['all',str(lane)]:
            r=moments[sec,loc[1],group];r[0]+=1;r[1]+=speed
    assert last==end
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    rows=[{'time_s':t,'cell':c,'lane':g,'n':int(n),'speed_mean':v/n}
          for (t,c,g),(n,v) in sorted(moments.items())]
    return {'rows':rows,'source':str(run.relative_to(e.ROOT)),'bytes':before.st_size,
        'mtime_ns':before.st_mtime_ns,'scope':'Future speed oracle only; no desired-speed field estimated.'}


def extract(run,geometry,reference=None):
    observer=Observer(geometry);moments=defaultdict(lambda:[0.,0.,0.,0.,0.]);count=0
    ref=iter(records(reference/'vissim_eval/baseline_001.fzp')) if reference else None
    last=None
    for p in records(run/'vissim_eval/baseline_001.fzp'):
        sec=int(float(p[0]))
        if sec>3000:break
        last=sec
        if ref is not None:
            old=next(ref)
            if p[:9]!=old[:9]:raise AssertionError(('Baseline traffic divergence',sec,p,old))
            count+=1
        assert len(p)==10,'Missing desired-speed native field'
        if sec%10 or sec<900:continue
        link=int(p[2]);lane=int(p[3]);pos=float(p[4]);speed=float(p[6]);desired=float(p[9])
        loc=observer.locate((link,lane,pos,speed))
        if not loc or loc[0]!='FW_E':continue
        for group in ['all',str(lane)]:
            r=moments[sec,loc[1],group]
            r[0]+=1;r[1]+=speed;r[2]+=speed*speed;r[3]+=desired;r[4]+=desired*desired
    assert last==3000
    rows=[{'time_s':t,'cell':c,'lane':g,'n':int(n),
           'speed_mean':sv/n,'speed_sd':math.sqrt(max(0.,svv/n-(sv/n)**2)),
           'desired_mean':sd/n,'desired_sd':math.sqrt(max(0.,sdd/n-(sd/n)**2))}
          for (t,c,g),(n,sv,svv,sd,sdd) in sorted(moments.items())]
    return {'rows':rows,'original9_exact_rows':count,'source':str(run.relative_to(e.ROOT)),
            'scope':'Observed10s snapshots. Future rows are diagnostic only, not forecast inputs.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rm-speeds',action='store_true')
    args=parser.parse_args()
    if args.rm_speeds:
        out=HERE/'rm_moments_v1';out.mkdir(exist_ok=False)
        for seed,run,folder in [(23,H/'response_late_s23_v1/run_rm_ramp',H/'controller_response_s23_v1/none'),
            (33,H/'state_response_20260919/native_s33_v1/run_rm_ramp',H/'state_response_20260919/native_s33_v1/observations/none')]:
            geometry=e.ObservationData(folder).geometry
            result=extract_speeds(run,geometry)
            e.save(out/f's{seed}_rm_ramp.json',result)
            reference=e.load(HERE/f'moments_v1/s{seed}_none.json')
            e.save(out/f's{seed}_none.json',reference)
            a={(r['cell'],r['lane']):(r['n'],r['speed_mean']) for r in result['rows'] if r['time_s']==2400}
            b={(r['cell'],r['lane']):(r['n'],r['speed_mean']) for r in reference['rows'] if r['time_s']==2400}
            assert a==b,(seed,'initial native moments')
            print('RM_SPEEDS',seed,len(result['rows']),'initial exact',flush=True)
        return
    out=HERE/'moments_v1';out.mkdir(exist_ok=False)
    state=H/'state_exchange_20260920'
    cases={23:{'none':HERE/'native_v1/none_s23/run',
               'vsl':H/'dsd_response_20260920/native_v2/run_retry1',
               **{arm:state/f'dispersion_native_v1/{arm}/run' for arm in ['mean_only','spread_only','affine_both']}},
           33:{'none':HERE/'native_v1/none_s33/run',
               'spread_only':state/'dispersion_seed33_v1/spread_only/run'}}
    summary={}
    for seed,arms in cases.items():
        folder=(H/'controller_response_s23_v1/none' if seed==23 else H/'state_response_20260919/native_s33_v1/observations/none')
        geometry=e.ObservationData(folder).geometry
        reference=(H/'rules_4500_s23_v1/run_none' if seed==23 else H/'state_response_20260919/native_s33_v1/run_none')
        for arm,run in arms.items():
            if arm=='none':
                completion=e.load(run/'run.json');validation=e.load(run/'fixed_validation.json')
                assert completion['completed'] and completion['terminal_sec']==3000 and validation['passed']
            result=extract(run,geometry,reference if arm=='none' else None)
            if arm=='none':assert result['original9_exact_rows']>10_000_000
            e.save(out/f's{seed}_{arm}.json',result)
            summary[f'{seed}_{arm}']={k:v for k,v in result.items() if k!='rows'}
            print(seed,arm,len(result['rows']),result['original9_exact_rows'],flush=True)
    e.save(out/'verification.json',summary)


if __name__=='__main__':main()
