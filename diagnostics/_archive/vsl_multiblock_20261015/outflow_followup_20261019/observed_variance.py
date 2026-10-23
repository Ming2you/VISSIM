"""Native cross-sections: lane versus longitudinal heterogeneity, without fit.

Long approach cells14/15 are split into three equal175m pieces, matching the
existing short approach cells16/17/18. These are observations, not new states
fed into any forecast;150s snapshots do not identify continuous lane changes.
"""
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=Path('D:/VISSIM_packages/vsl_multizone355_20261015')
B=Path('E:/VISSIM_analysis/20261011_vsl_response349')
PINS={}
def read(path):
    path=Path(path);blob=path.read_bytes();PINS[str(path)]=hashlib.sha256(blob).hexdigest()
    return json.loads(blob)
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def stats(vehicles):
    n=len(vehicles)
    if not n:return dict(n=0,mean=None,variance=None,stopped=0,under40=0)
    mean=math.fsum(v['speed_kph'] for v in vehicles)/n
    variance=math.fsum((v['speed_kph']-mean)**2 for v in vehicles)/n
    return dict(n=n,mean=mean,variance=variance,stopped=sum(bool(v['stopped']) for v in vehicles),under40=sum(v['speed_kph']<40 for v in vehicles))


def decomposition(vehicles,key):
    total=stats(vehicles);groups=defaultdict(list)
    for v in vehicles:groups[key(v)].append(v)
    parts=[stats(vs) for vs in groups.values()]
    within=math.fsum(p['n']*p['variance'] for p in parts)/total['n'] if total['n'] else 0.
    between=math.fsum(p['n']*(p['mean']-total['mean'])**2 for p in parts)/total['n'] if total['n'] else 0.
    assert abs(within+between-(total['variance'] or 0))<1e-8
    return dict(within=within,between=between)


def main():
    assert not (OUT/'observed_variance.json').exists()
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    from evaluation.controllers import offramp_routing as route
    contract=read(ROOT/'diagnostics/repin_v3c3_review_20261001/unrouted10646/route_contract.json')
    mapping=read(ROOT/contract['mapping']['path']);runtime=route.compile_inventory(contract,mapping)
    boundaries=runtime['bounds']['FW_E']
    cases=[(29,'hold',2250,Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')),
           (29,'single90',2250,Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/vsl90/decisions_sdmpc31_g_2250_vsl90_s29')),
           (29,'selected',2250,Path('D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29/selected/decisions_sdmpc31_g_2250_selected_s29'))]
    proofs={}
    for seed,arms in [(67,('release','release_vsl90')),(71,('rm','both'))]:
        proof=read(B/f'matched_seed{seed}_v3/matched_assessment.json');proofs[seed]=proof
        for arm in arms:
            sources=[Path(p) for p in proof['source_pins'] if f'/{arm}/' in p.replace('\\','/') and Path(p).name.startswith('state_')]
            assert len(sources)==4
            cases.append((seed,arm,proof['start'],sources[0].parent))
    rows=[];subcells=[];initials={};saved_vehicles={}
    for seed,arm,start,folder in cases:
        for elapsed in (0,150,300,450):
            path=folder/f'state_{start+elapsed:06d}.json';raw=read(path)
            if seed in proofs:assert PINS[str(path)]==proofs[seed]['source_pins'][str(path)]
            assert raw['vehicle_records']['complete'] and raw['sim_sec']==start+elapsed
            vehicles=[]
            for original in raw['vehicle_records']['records']:
                link=str(original['link_no'])
                if link not in runtime['physical']:continue
                road,pos,cell=route._position(runtime,link,original['position_m'])
                if road!='FW_E' or not 14<=cell<=23:continue
                v=dict(original,chain_m=pos,cell=cell)
                pieces=3 if cell in (14,15) else 1
                v['piece']=min(pieces-1,int(pieces*(pos-boundaries[cell])/(boundaries[cell+1]-boundaries[cell])))
                vehicles.append(v)
            assert len({v['veh_no'] for v in vehicles})==len(vehicles)
            if elapsed==0:
                current=sorted((v['veh_no'],v['link_no'],v['lane_no'],v['position_m'],v['speed_kph']) for v in vehicles)
                if seed in initials:assert current==initials[seed]
                else:initials[seed]=current
            saved_vehicles[(seed,arm,elapsed)]=vehicles
            for region,lo,hi in [('approach14_18',14,18),('bottleneck19_23',19,23)]:
                part=[v for v in vehicles if lo<=v['cell']<=hi]
                row=dict(seed=seed,arm=arm,elapsed=elapsed,region=region,**stats(part))
                row['lane_decomposition']=decomposition(part,lambda v:v['lane_no'])
                row['longitudinal_decomposition']=decomposition(part,lambda v:(v['cell'],v['piece']))
                row['cell_lane_decomposition']=decomposition(part,lambda v:(v['cell'],v['lane_no']))
                rows.append(row)
            for cell in range(14,19):
                pieces=3 if cell in (14,15) else 1
                for piece in range(pieces):
                    part=[v for v in vehicles if v['cell']==cell and v['piece']==piece]
                    subcells.append(dict(seed=seed,arm=arm,elapsed=elapsed,cell=cell,piece=piece,length_m=(boundaries[cell+1]-boundaries[cell])/pieces,**stats(part)))
    contrasts=[]
    for seed,base,arms in [(29,'hold',('single90','selected')),(67,'release',('release_vsl90',)),(71,'rm',('both',))]:
        for arm in arms:
            for elapsed in (150,300,450):
                for region in ('approach14_18','bottleneck19_23'):
                    a=next(r for r in rows if (r['seed'],r['arm'],r['elapsed'],r['region'])==(seed,base,elapsed,region))
                    b=next(r for r in rows if (r['seed'],r['arm'],r['elapsed'],r['region'])==(seed,arm,elapsed,region))
                    row=dict(seed=seed,arm=arm,elapsed=elapsed,region=region)
                    for key in ('n','mean','variance','stopped','under40'):row['delta_'+key]=b[key]-a[key]
                    for key in ('lane_decomposition','longitudinal_decomposition','cell_lane_decomposition'):
                        row[key]={k:b[key][k]-a[key][k] for k in ('within','between')}
                    contrasts.append(row)
    # Check observed prior157/195/213 proposals rather than repeating them.
    prior={}
    oldroot=ROOT/'diagnostics/repin_v3c3_review_20261001'
    for name in ('variance_pressure213','merge_cohort212','aggregate_recovery247','characteristic195'):
        protocol=read(oldroot/name/'protocol.json');completion=read(oldroot/name/'completion.json')
        prior[name]=dict(protocol={k:v for k,v in protocol.items() if k in ('hypothesis','question','scope','limitations','gate')},completion=completion)
    for p in (Path(__file__),Path(route.__file__),ROOT/contract['network']['path']):PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    for path,h in PINS.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==h,path
    save(OUT/'observed_variance.json',dict(status='complete_cross_sectional_heterogeneity_audit',rows=rows,contrasts=contrasts,subcells=subcells,
        prior_review=prior,source_pins=PINS,new_native=0,new_forecasts=0,new_fzp_scans=0,parameter_fits=0,production_edits=0,
        limitations=['Cross-sectional population variance is not acceleration, desired-speed variance, or lane-change frequency.',
                     'Variance effects may be cause or consequence of density/front position; no causal coefficient is identified.',
                     'Lane and longitudinal decompositions are alternatives and must not be added together.',
                     '150s observations do not resolve the time of breakdown/recovery or identify a future boundary input.']))
    print(json.dumps([r for r in contrasts if r['region']=='approach14_18'],indent=2))


if __name__=='__main__':main()
