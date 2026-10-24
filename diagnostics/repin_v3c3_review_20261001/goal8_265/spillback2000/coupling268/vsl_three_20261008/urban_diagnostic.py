"""Matched saved-native decomposition only; no COM/FZP/plant rollout or edits."""
import csv
import ctypes
import ctypes.wintypes
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger

OUT = Path(__file__).parent / 'urban_diagnostic_to6150'
END = 6150
RUNS = {
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
    'head47': Path('D:/VISSIM_runs/20261007_goal8_head47right_verified_s29_8100/sdmpc'),
    'prevention': Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc'),
    'coupling268': Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc'),
}
PINS = {}
def read(path):
    b = path.read_bytes(); PINS[str(path)] = hashlib.sha256(b).hexdigest()
    return json.loads(b.decode('utf-8-sig'))

def main():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    k.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    assert not OUT.exists(), 'Preserve prior diagnostic'
    geo = read(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
    area = read(ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json')
    membership = physical_membership_from_ledger(area)
    links = sorted(map(int, membership)); li = {v:i for i,v in enumerate(links)}
    ramps = {int(x['connector']): x for x in geo['boundaries'] if x['kind']=='ramp'}
    offs = {int(x['connector']): x for x in geo['boundaries'] if x['kind']=='offramp'}
    freeway = {int(x['link']):road for road,chain in geo['chains'].items() for x in chain}
    group_names = ['FW_E','FW_W','onramp_connectors','offramp_connectors','urban_other','outside_Omega']
    groups = {link: ('outside_Omega' if not membership[str(link)] else freeway.get(link,
                    'onramp_connectors' if link in ramps else 'offramp_connectors' if link in offs else 'urban_other')) for link in links}
    detpath = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/obs150/obs150_detectors_v2.csv'
    dets=list(csv.DictReader(detpath.open(encoding='utf-8-sig')))
    rm_dets={link:{role:[x['dcm_no'] for x in dets if int(x['link'])==link and x['role']==role]
                   for role in ['meter_head','ramp_arrival']} for link in ramps}
    times=np.array([0,1]+list(range(150,END+1,150)),dtype=float)
    data={}; provenance={}; warmup={}
    for label,run in RUNS.items():
        paths=list(run.glob('run_provenance_*.json'));assert len(paths)==1
        prov=read(paths[0]);provenance[label]=prov
        assert prov['seed']==29 and prov['files']['network']['sha256']==area['network']['sha256']
        decisions=run/('decisions_'+paths[0].stem.removeprefix('run_provenance_'))
        stock=np.zeros((len(times),len(links)));stopped=np.zeros_like(stock)
        lane_rows=[];detector={};commands=[];signals=[]
        for j,t in enumerate(times[1:],1):
            s=read(decisions/f'state_{int(t):06d}.json');v=s['vehicle_records'];recs=v['records']
            assert s['sim_sec']==t==v['paused_at_sim_sec']==v['capture_sim_sec_before']==v['capture_sim_sec_after']
            assert v['complete'] and v['unobservable_count']==0 and len(recs)==len({x['veh_no'] for x in recs})==s['total_vehicles']
            if t<=900:
                digest=hashlib.sha256(json.dumps(recs,sort_keys=True).encode()).hexdigest()
                if label=='nc':warmup[t]=digest
                else:assert digest==warmup[t]
            for x in recs:
                idx=li[x['link_no']];stock[j,idx]+=1;stopped[j,idx]+=int(x['stopped'])
            assert stock[j].sum()==len(recs)
            assert {str(link):int(stock[j,idx]) for link,idx in li.items() if stock[j,idx]}=={str(link):n for link,n in v['full_network_link_counts'].items() if n}
            detector[int(t)]=s['obs150']['detectors_cum']
            for link in [52,66,68,121,127,129,10681,10490,10484]:
                for lane in sorted({x['lane_no'] for x in recs if x['link_no']==link}):
                    r=[x for x in recs if x['link_no']==link and x['lane_no']==lane]
                    stop=[x for x in r if x['stopped']]
                    lane_rows.append(dict(run=label,time=t,link=link,lane=lane,n=len(r),stopped=len(stop),
                                          speed=float(np.mean([x['speed_kph'] for x in r])),tail_pos=min([x['position_m'] for x in stop],default=None)))
            if 900<=t<END and label!='nc':
                f=decisions/f'action_{int(t):06d}.csv';b=f.read_bytes();PINS[str(f)]=hashlib.sha256(b).hexdigest()
                for x in csv.DictReader(b.decode('utf-8-sig').splitlines()):
                    if x['kind']=='ramp_meter':commands.append(dict(run=label,time=t,ramp=int(x['id'].split('C')[-1]),green=float(x['green_sec'])))
                    elif x['kind']=='signal':signals.append(dict(run=label,time=t,sc=int(x['sc_no']),offset=float(x['offset']),greens=[float(x[f'p{i}_green']) for i in range(1,5)]))
        cumulative=np.vstack([np.zeros(len(links)),np.cumsum((stock[1:]+stock[:-1])*.5*np.diff(times)[:,None]/3600,axis=0)])
        stop_cum=np.vstack([np.zeros(len(links)),np.cumsum((stopped[1:]+stopped[:-1])*.5*np.diff(times)[:,None]/3600,axis=0)])
        buckets={g:cumulative[:,[li[l] for l in links if groups[l]==g]].sum(axis=1) for g in group_names}
        data[label]=dict(stock=stock,stopped=stopped,cumulative=cumulative,stop_cum=stop_cum,buckets=buckets,detector=detector,commands=commands,signals=signals,lane_rows=lane_rows)
    for label,prov in provenance.items():
        for key in ['network','control_mapping','vehicle_input_roles','demand_profile','urban_input_gate_map','generated_vbs_config','signal_group_plan']:
            assert prov['files'][key]['sha256']==provenance['nc']['files'][key]['sha256'],(label,key)
    overall=[];periods=[];top={};rm=[]
    masks={g:[li[l] for l in links if groups[l]==g] for g in group_names}
    masks['urban_and_ramps']=[li[l] for l in links if membership[str(l)] and l not in freeway]
    masks['Omega']=[li[l] for l in links if membership[str(l)]]
    for label,d in data.items():
        for group,idx in masks.items():
            val=float(d['cumulative'][-1,idx].sum());nc=float(data['nc']['cumulative'][-1,idx].sum())
            overall.append(dict(run=label,group=group,TTT=val,delta_vs_nc=val-nc,improvement_pct=100*(1-val/nc) if nc else None))
        for a,b in [(900,1800),(1800,3000),(3000,4500),(4500,6150)]:
            ia=list(times).index(a);ib=list(times).index(b)
            for g,idx in masks.items():
                val=float((d['cumulative'][ib,idx]-d['cumulative'][ia,idx]).sum());nc=float((data['nc']['cumulative'][ib,idx]-data['nc']['cumulative'][ia,idx]).sum())
                periods.append(dict(run=label,start=a,end=b,group=g,TTT=val,delta_vs_nc=val-nc))
        for ramp,roles in rm_dets.items():
            greens=[x['green'] for x in d['commands'] if x['ramp']==ramp]
            row=dict(run=label,ramp=ramp,from_link=ramps[ramp]['from_link'],road=ramps[ramp]['road'],
                     TTT=float(d['cumulative'][-1,li[ramp]]),stopped_time_veh_h=float(d['stop_cum'][-1,li[ramp]]),
                     max_stock=float(d['stock'][:,li[ramp]].max()),end_stock=float(d['stock'][-1,li[ramp]]),
                     mean_green=float(np.mean(greens)) if greens else 10,
                     first_green2=next((x['time'] for x in d['commands'] if x['ramp']==ramp and x['green']<=2),None))
            for role,ds in roles.items():
                assert ds,(ramp,role)
                row[role+'_crossings_900_6150']=sum(d['detector'][END][key]-d['detector'][900][key] for key in ds)
            rm.append(row)
        for base in ['nc','head47']:
            delta=d['cumulative'][-1]-data[base]['cumulative'][-1]
            rows=[dict(link=l,group=groups[l],TTT=float(d['cumulative'][-1,li[l]]),delta=float(delta[li[l]]),stopped_time_delta=float(d['stop_cum'][-1,li[l]]-data[base]['stop_cum'][-1,li[l]])) for l in links if membership[str(l)] and l not in freeway]
            top[label+'_vs_'+base]=dict(increases=sorted(rows,key=lambda x:-x['delta'])[:18],decreases=sorted(rows,key=lambda x:x['delta'])[:18])
    # Reconcile against the already published same-method cached arrays.
    cache=ROOT/'diagnostics/repin_v3c3_review_20261001/goal8_265/interim_verified_to6150'
    for label,filename in [('nc','nc_snapshots.npz'),('head47','sdmpc_snapshots.npz')]:
        z=np.load(cache/filename);assert np.array_equal(z['times'],times)
        for j,g in enumerate(['FW_E','FW_W','urban_and_ramps','outside_Omega']):
            assert np.allclose(z['cumulative_ttt'][:,j],data[label]['cumulative'][:,masks[g]].sum(axis=1),rtol=0,atol=1e-8)
    OUT.mkdir()
    def save(leaf,obj):(OUT/leaf).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for name,rows in [('overall',overall),('periods',periods),('ramps',rm),('link_contributions',top)]:save(name+'.json',rows)
    save('commands.json',{l:dict(rm=d['commands'],signals=d['signals']) for l,d in data.items()})
    save('lane_stocks.json',[r for d in data.values() for r in d['lane_rows']])
    np.savez_compressed(OUT/'link_arrays.npz',times=times,links=links,**{l+'_'+k:d[k] for l,d in data.items() for k in ['stock','stopped','cumulative','stop_cum']})
    save('provenance.json',dict(period=[0,END],Omega_links=sum(membership.values()),warmup_exact=True,metadata_matched=True,cached_NC_head47_reconciled=True,
         grouping='Physical eight onramp connectors separated; upstream city links remain urban. No person/route attribution from aggregate stock.',
         limitation='150s snapshot TTT/stopped residence estimates; cumulative detectors are admitted entry or meter-head passage, not mainline merge. Observational policies differ; no causal counterfactual.',
         source_sha256=PINS,run_provenance={l:dict(run_id=p['run_id'],workspace_root=p.get('workspace_root')) for l,p in provenance.items()}))
    print(json.dumps(dict(overall=[r for r in overall if r['group'] in ['Omega','urban_and_ramps','urban_other','onramp_connectors']],
                         biggest_regressions_vs_head47=top['coupling268_vs_head47']['increases'][:8],ramps=rm),ensure_ascii=False))

if __name__=='__main__':main()
