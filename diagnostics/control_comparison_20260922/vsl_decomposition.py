"""Separate observed VSL policy differences in space and time; no new native run."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, json, math, sys
import compare as base
import numpy as np
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE/'vsl_decomposition'; OUT.mkdir(exist_ok=True)
g=base.load(base.GEOMETRY)
chain={str(r['link']):(d,r) for d,rs in g['chains'].items() for r in rs}
at={b['id']:b['chain_pos_m'] for b in g['boundaries']}
limits={'FW_E':[0,chain['2'][1]['offset_m'],at['OR_F_E_signal'],at['RM_C10681'],at['OR_D_E_signal'],at['RM_C10484'],g['bounds']['FW_E'][-1]],
        'FW_W':[0,2694.4232696497,at['RM_C10482'],at['OR_F_W_direct'],at['RM_C10644'],g['bounds']['FW_W'][-1]]}
names=['E 입구 VSL 구간','E 첫 진출부 상류','E 앞 램프군','E 두 램프군 사이','E 뒤 램프군','E 하류',
       'W 입구 VSL 구간','W 앞 램프군','W 두 램프군 사이','W 뒤 램프군','W 하류','도시·램프 등']
sections={'E_entry':('FW_E',300.,2500.),'E_middle':('FW_E',5300.,6600.),
          'E_rear':('FW_E',6900.,7700.),'W_entry':('FW_W',300.,2500.)}
offset={'FW_E':0,'FW_W':6}
pairs={'VSL - NC':('vsl','none'),'Both - RM':('both','rm')}

def integrate(times,values,a,b):
    ids=(times>a)&(times<b)
    t=np.r_[a,times[ids],b]
    if values.ndim==1: values=values[:,None]
    ends=np.array([[np.interp(x,times,values[:,k]) for k in range(values.shape[1])] for x in (a,b)])
    v=np.concatenate([ends[:1],values[ids],ends[1:]])
    return np.trapezoid(v,t,axis=0)/3600

def extract(arm):
    out=OUT/arm;out.mkdir(exist_ok=True)
    if (out/'stocks.npz').exists(): return
    membership=base.old.physical_membership_from_ledger(base.load(base.ROOT/'diagnostics/control_area_membership.json'))
    counts=[]; classes=[]; times=[]; prev={}; prev_t=0.; entered={}; passages=[]; cuts=Counter(); evidence={}
    for t,current in base.raw_frames(base.RUNS[arm]/'vissim_eval/baseline_001.fzp',evidence):
        n=np.zeros(12); speedclass=np.zeros((12,3)); located={}
        for no,(link,pos,speed) in current.items():
            if not membership[link]: continue
            if link in chain:
                d,r=chain[link]; x=r['offset_m']+pos
                idx=offset[d]+int(np.clip(np.searchsorted(limits[d],x,side='right')-1,0,len(limits[d])-2))
                located[no]=(d,x)
                if no in prev and prev[no][0]==d and x>=prev[no][1]:
                    x0=prev[no][1]
                    for name,(road,a,b) in sections.items():
                        if road!=d:continue
                        for kind,point in [('in',a),('out',b)]:
                            if x0<point<=x:
                                cross=prev_t+(t-prev_t)*(point-x0)/(x-x0)
                                cuts[(name,kind,min(int(cross//150),59))]+=1
                                key=(name,no)
                                if kind=='in': entered[key]=cross
                                elif key in entered:
                                    start=entered.pop(key)
                                    passages.append({'section':name,'vehicle':no,'entry_s':start,'exit_s':cross,'travel_s':cross-start})
            else: idx=11
            n[idx]+=1; speedclass[idx,0 if speed<30 else 1 if speed<80 else 2]+=1
        counts.append(n); classes.append(speedclass); times.append(t); prev=located; prev_t=t
    assert evidence['sha256']==base.load(HERE/arm/'fzp_evidence.json')['sha256']
    tt=np.r_[0,times,9000]; nn=np.vstack([np.zeros(12),counts,counts[-1]])
    cc=np.concatenate([np.zeros((1,12,3)),classes,[classes[-1]]])
    original=base.load(HERE/arm/'performance.json')
    sums=integrate(tt,nn,0,9000)
    assert math.isclose(sums.sum(),original['TTT_veh_h'],abs_tol=1e-8)
    assert math.isclose(sums[:6].sum(),original['TTT_FW_E'],abs_tol=1e-8)
    assert math.isclose(sums[6:11].sum(),original['TTT_FW_W'],abs_tol=1e-8)
    np.savez_compressed(out/'stocks.npz',times=tt,counts=nn,speedclasses=cc)
    base.table(out/'passages.csv',passages)
    base.table(out/'cut_flows.csv',[dict(section=s,kind=k,start_s=i*150,crossings=n) for (s,k,i),n in sorted(cuts.items())])
    base.save(out/'evidence.json',dict(fzp_sha256=evidence['sha256'],rows=evidence['rows'],frames=evidence['frames'],
        pending_section_entries=len(entered),scope='Completed same-direction mainline crossings interpolated between5s positions; no skipped ramp paths inferred. Cohort travel times are conditional on completion.'))
    print(arm,'EXTRACTED',flush=True)

def commands():
    rows=[]; duration=[]; rm_changes=[]
    for arm in ('vsl','both'):
        policy=base.load(base.Q/'rules'/f'prepared_{arm}'/'rule_policy.json')
        detector={r['target']:r for r in policy['detectors']['stations'] if r['role']=='vsl_zones'}
        tally=Counter(); state={}; zone_all=policy['zone_dsds']
        for t in range(900,9000,150):
            dec=base.load(base.RUNS[arm]/f'decision_{t}.json'); state.update(dec['history']['vsl'])
            if arm=='both':
                alone=base.load(base.RUNS['rm']/f'decision_{t}.json')
                for mid,v in dec['meters'].items():
                    if v['green_sec']!=alone['meters'][mid]['green_sec']:
                        rm_changes.append(dict(sec=t,meter=mid,rm=alone['meters'][mid]['green_sec'],both=v['green_sec']))
            for z,dsds in zone_all.items():
                # A zone initially retaining native120 may not yet appear in history.
                speeds={float(state.get(str(no),120)) for no in dsds}; assert len(speeds)==1
                v=speeds.pop(); obs=dec['observations'][z]; d=detector[z]
                row=dict(arm=arm,time_s=t,zone=z,command_kph=v,link=d['link_no'],position_m=d['position_m'],**obs)
                rows.append(row); tally[(z,v)]+=150
        duration.extend(dict(arm=arm,zone=z,command_kph=v,duration_sec=n) for (z,v),n in sorted(tally.items()))
    base.table(OUT/'commands.csv',rows); base.table(OUT/'command_durations.csv',duration)
    base.save(OUT/'meter_interaction.json',{'different_meter_cycle_count':len(rm_changes),'differences':rm_changes,
        'interpretation':'Both-minus-RM is a policy interaction comparison, not VSL added while replaying identical RM commands.'})
    return rows,duration

def main():
    for a in base.RUNS:extract(a)
    arrays={a:np.load(OUT/a/'stocks.npz') for a in base.RUNS}
    cost={a:np.array([integrate(v['times'],v['counts'],t,t+150) for t in range(0,9000,150)]) for a,v in arrays.items()}
    command_rows,duration=commands();summary={}; region_rows=[]; window_rows=[];cohorts=[]
    for arm in base.RUNS:
        with (OUT/arm/'passages.csv').open(encoding='utf-8-sig') as f: p=list(csv.DictReader(f))
        for section in sections:
            for lo,hi in [(900,8100),(900,2700),(2700,4500),(4500,6300),(6300,8100)]:
                ts=[float(r['travel_s']) for r in p if r['section']==section and lo<=float(r['entry_s'])<hi]
                cohorts.append(dict(arm=arm,section=section,start_s=lo,end_s=hi,completed=len(ts),
                    mean_travel_s=float(np.mean(ts)) if ts else None,median_travel_s=float(np.median(ts)) if ts else None))
    base.table(OUT/'cohort_travel_times.csv',cohorts)
    for pair,(a,b) in pairs.items():
        delta=cost[a]-cost[b]; total=delta.sum(axis=1); groups=delta.sum(axis=0)
        negative=float(delta[delta<0].sum()); positive=float(delta[delta>0].sum())
        periods=[]
        for lo in range(900,9000,900):
            d=delta[lo//150:(lo+900)//150].sum(axis=0)
            r=dict(pair=pair,start_s=lo,end_s=lo+900,delta_TTT=float(d.sum()),E=float(d[:6].sum()),W=float(d[6:11].sum()),urban_ramps=float(d[11]))
            window_rows.append(r); periods.append(r)
        local=[]
        for k,name in enumerate(names):
            slower=[]
            for arm in (a,b):
                v=arrays[arm];sc=v['speedclasses'][:,k,:]
                slower.append(integrate(v['times'],sc,0,9000))
            r=dict(pair=pair,region=name,delta_TTT=float(groups[k]),delta_under30_veh_h=float((slower[0]-slower[1])[0]),
                   delta_30to80_veh_h=float((slower[0]-slower[1])[1]),delta_over80_veh_h=float((slower[0]-slower[1])[2]))
            local.append(r);region_rows.append(r)
        summary[pair]=dict(delta_TTT=float(groups.sum()),negative_space_time_contributions=negative,
            positive_space_time_contributions=positive,better_150s_windows=int(sum(total[6:]<0)),total_150s_windows=54,
            regions=local,windows900=periods)
    base.save(OUT/'summary.json',{'comparisons':summary,'limits':limits,'region_names':names,'command_durations':duration,
        'interpretation':'Exact residence-cost decomposition of observed policies, not isolated zone causal benefits. Space/time positive-negative sums depend on chosen bins. Lower stock can reflect displaced or uninserted traffic. Same seed only.',
        'spatial_speed_class_note':'<30,30–80,>=80km/h residence partitions; descriptive thresholds, not a causal split into congestion and speed-command loss.'})
    base.table(OUT/'regions.csv',region_rows);base.table(OUT/'windows900.csv',window_rows)
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10})
    fig,axs=plt.subplots(2,2,figsize=(15,9),layout='constrained')
    for j,(pair,(a,b)) in enumerate(pairs.items()):
        delta=cost[a]-cost[b]; total=delta.sum(axis=1)
        for idx,label in [(slice(0,6),'동측 본선'),(slice(6,11),'서측 본선'),(slice(11,12),'도시·램프 등')]:
            axs[0,j].plot(np.arange(60)*150+150,np.cumsum(delta[:,idx].sum(axis=1)),label=label)
        axs[0,j].plot(np.arange(60)*150+150,np.cumsum(total),color='black',lw=2,label='Ω 합계')
        axs[0,j].axhline(0,color='#777',lw=.7);axs[0,j].set_title(pair);axs[0,j].set_ylabel('누적 TTT 변화 [veh·h]');axs[0,j].legend(fontsize=9)
        mat=delta[6:].T; im=axs[1,j].imshow(mat,aspect='auto',cmap='RdBu_r',vmin=-12,vmax=12,extent=(900,9000,11.5,-.5),interpolation='nearest')
        axs[1,j].set_yticks(range(12),names);axs[1,j].set_xlabel('시간 [초]');axs[1,j].set_title('구간 × 150초 TTT 변화: 파랑 감소 / 빨강 증가')
    fig.colorbar(im,ax=axs[1,:],label='TTT 변화 [veh·h / 150초]',shrink=.8)
    fig.suptitle('VSL의 국소 이득과 손해가 섞이는가? | 80–90 · seed23 · 0–9000초\n실행 결과의 비용 분해이며, 특정 VSL 구간만 켰을 때의 인과 효과는 아님',fontsize=15)
    fig.savefig(OUT/'vsl_cost_decomposition.png',dpi=150);plt.close(fig)
    print(json.dumps({p:{k:v for k,v in s.items() if k not in ('regions','windows900')} for p,s in summary.items()}),flush=True)

if __name__=='__main__':main()
