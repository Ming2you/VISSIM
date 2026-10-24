"""Completed coupling268 three-arm traffic comparison; no simulation or calibration."""
from pathlib import Path
import csv,hashlib,json,math,os,sys,time,traceback
ROOT=Path(r"C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926")
sys.path.insert(0,str(ROOT))
OUT=Path('E:/VISSIM_analysis/20261010_coupling268_three8100_v2')
os.environ['MPLCONFIGDIR']=str(OUT/'mplconfig')
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200 import analyze_pair as canonical
from scripts.measure_control_area import read_fzp_frames,measure_frames,terminal_lengths,sha256
from diagnostics.fast_fixed_profile_verify import prefix_digest
from diagnostics.capture_native_runtime_errors import parse_bytes
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE=ROOT/'diagnostics/repin_v3c3_review_20261001/goal8_265'
CACHE=BASE/'current_native_analysis_to8100'
MEMBER=ROOT/'diagnostics/repin_v3c3_review_20261001/urban_area263/approaches_only/membership.json'
GEO=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
QROOT=Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three')
NC=Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc')
ARMS=['nc','window','optimized','off']
LABELS={'nc':'무제어','window':'시간창 VSL90','optimized':'SDMPC VSL','off':'VSL OFF'}
read=canonical.load
save=canonical.save

def run():
    assert not (OUT/'progress.json').exists() and not (OUT/'summary.json').exists(), 'Preserve existing analysis; do not duplicate'
    assert not any((OUT/a).exists() for a in ARMS), 'Preserve any started arm'
    OUT.mkdir(parents=True,exist_ok=True)  # matplotlib may have created its font cache at import.
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    started=time.perf_counter()
    queue=read(QROOT/'queue_state.json');assert queue['stage']=='complete_unanalyzed'
    old=read(CACHE/'summary.json')
    ledger,membership,receipt=canonical.measurement_area(MEMBER)
    assert receipt['inside_links']==701 and old['physical_area']['sha256']==sha256(MEMBER)
    assert old['end_sec']==8100 and old['arms']['nc']['native_execution_passed']
    terminals=terminal_lengths(ledger)
    geo=read(GEO);assert sha256(GEO)=='91a584ab779330f928a79855d68bcdbb133dfaaef57a2de66d5d415e9a474ee2'
    chains={str(x['link']):(r,x['offset_m']) for r,chain in geo['chains'].items() for x in chain}
    lengths={r:geo['bounds'][r][-1] for r in ('FW_E','FW_W')}
    edges={r:np.r_[np.arange(0,L,100.),L] for r,L in lengths.items()}
    time_edges=np.arange(0,8101,15)
    output={'start_sec':0,'end_sec':8100,'seed':29,'area':receipt,'conditions':{},
            'definition':'5s native sampled Omega701 residence; final4.9s holds last stock, never counted as exit.',
            'heatmap':'Vehicle-weighted native speed per15s x100m; empty bins masked; mainline only.',
            'new_native':0,'new_predictions':0,'new_calibration':False,
            'limitations':['Signals/offset/RM jointly differ: not isolated VSL causal effects.',
                'Optimized VSL has eight internal zones; window VSL uses one east bottleneck zone.',
                'One seed, no independent-seed robustness claim.',
                'NC terminal9000 costs and uninserted count are not8100 values and are excluded.',
                'Sampled exits include observed area exits plus inferred terminal exits; residual stock is not exit.',
                'Native LSA coverage is reported separately; previously authorized LDP evidence is retained.']}
    pins={str(p):sha256(p) for p in (Path(__file__),GEO,MEMBER,CACHE/'summary.json',CACHE/'nc/area_metrics.json',
        CACHE/'nc/area_timeseries.csv',CACHE/'nc/execution.json',QROOT/'plan.json')}
    heat={};series={};prefixes={};reference_prov=None
    for arm in ARMS:
        arm_start=time.perf_counter();folder=OUT/arm;folder.mkdir()
        if arm=='nc':
            run_dir=NC;name='sdmpc31_nc9000_s29';end=9000
        else:
            q=queue['conditions'][arm]
            assert q['status']=='native_complete' and q['normal_sim_done']==8100 and q['owners_closed']
            assert q['native_exit_code']==0 and q['native_launches']==1
            run_dir=Path(q['results_root'])/'sdmpc';name='sdmpc31_sdmpc8100_s29';end=8100
            status=read(run_dir.parent/'native_status.json')
            assert status['details']['terminal']==8100
        print('BEGIN '+arm,flush=True)
        prov=read(run_dir/f'run_provenance_{name}.json')
        assert prov['seed']==29 and prov['sim_period_sec']==end
        assert prov['files']['network']['sha256']==receipt['network_sha256']
        if reference_prov is None:reference_prov=prov
        else:
            for k in ('network','demand_profile','vehicle_input_roles'):
                assert prov['files'][k]['sha256']==reference_prov['files'][k]['sha256'],(arm,k)
        pins[str(run_dir/f'run_provenance_{name}.json')]=sha256(run_dir/f'run_provenance_{name}.json')
        if arm=='nc':
            execution=read(CACHE/'nc/execution.json')
            assert execution['run_id']==prov['run_id'] and execution['terminal_sec']==9000
            assert Path(execution['run_directory']).resolve()==run_dir.resolve()
            metrics=read(CACHE/'nc/area_metrics.json')
            with (CACHE/'nc/area_timeseries.csv').open(encoding='utf-8-sig') as f:
                times=[{k:v if k=='source' else float(v) for k,v in row.items()} for row in csv.DictReader(f)]
            error_records=read(CACHE/'nc/native_errors.json')
            events=error_records['unique_events']
            prefixes[arm]=old['prefixes']['nc']
        else:
            execution=canonical.verify_native_execution(run_dir,8100,run_name=name)
            events=[]
            for p in sorted(run_dir.rglob('*.err')):
                parsed=parse_bytes(p.read_bytes())
                assert not parsed['unparsed_removal_lines'],str(p)
                events.extend(parsed['events'])
            events=[json.loads(s) for s in sorted({json.dumps(e,sort_keys=True) for e in events})]
            events=[e for e in events if e.get('time_sec',0)<=8100]
        save(folder/'execution.json',execution)
        save(folder/'native_errors.json',{'unique_events':events})
        removals={str(e['vehicle_id']):e for e in events if e['kind']=='lane_change_removal'}
        fzp,=(run_dir/'vissim_eval').glob('*.fzp')
        if arm!='nc':prefixes[arm]=prefix_digest(fzp,900,recording_grid=(5,.1))
        before=fzp.stat();previous=None;rowcount=0;framecount=0;last=None
        sums={r:np.zeros((len(ed)-1,len(time_edges)-1)) for r,ed in edges.items()}
        counts={r:np.zeros_like(mat) for r,mat in sums.items()}
        def frames():
            nonlocal previous,rowcount,framecount,last
            for frame in read_fzp_frames(fzp):
                if frame.time_sec>8100:break
                rowcount+=len(frame.vehicles);framecount+=1;last=frame.time_sec
                ti=min(len(time_edges)-2,int(frame.time_sec//15))
                for v in frame.vehicles.values():
                    address=chains.get(v.link)
                    if address is None:continue
                    r,offset=address
                    pos=offset+v.position_m
                    ci=min(len(edges[r])-2,max(0,int(pos//100)))
                    sums[r][ci,ti]+=v.speed_kph;counts[r][ci,ti]+=1
                if previous:
                    dt=frame.time_sec-previous.time_sec
                    for no in previous.vehicles.keys()-frame.vehicles.keys():
                        v=previous.vehicles[no]
                        if no in removals and v.link in terminals:
                            reach=v.speed_kph/3.6*dt+1.5*dt*dt+10
                            overshoot=v.speed_kph/3.6*.1+.015+10
                            assert not -overshoot<=terminals[v.link]-v.position_m<=reach,('removal mistaken for exit',arm,no)
                previous=frame
                if framecount%400==0:print(f'SCAN {arm} {frame.time_sec:g}s',flush=True)
                yield frame
        if arm=='nc':
            for _ in frames():pass
            assert metrics['sampling']['fzp_rows']==rowcount
            assert metrics['sampling']['fzp_snapshots']==framecount
            assert metrics['boundaries']['last_fzp_sec']==last
        else:
            metrics,times=measure_frames(frames(),membership,terminals,end_sec=8100,
                                        simulation_step_sec=.1,include_distance=True)
        after=fzp.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        assert metrics['sampling']['nominal_step_sec']==5 and metrics['sampling']['missing_snapshot_gaps']==0
        assert metrics['closure']['max_abs_residual_veh']==0
        save(folder/'area_metrics.json',metrics);canonical.table(folder/'area_timeseries.csv',times)
        heat[arm]={r:np.divide(sums[r],counts[r],out=np.full_like(sums[r],np.nan),where=counts[r]>0) for r in sums}
        np.savez_compressed(folder/'native_speed.npz',time_edges=time_edges,
            **{r+'_speed':heat[arm][r] for r in heat[arm]},**{r+'_distance_edges':edges[r] for r in edges},
            **{r+'_count':counts[r] for r in counts})
        cost={'FW_E':0.,'FW_W':0.,'urban_ramps_inside':0.,'outside':0.}
        for link,row in metrics['physical_link_residence'].items():
            group=chains[link][0] if link in chains else 'urban_ramps_inside' if row['inside'] else 'outside'
            cost[group]+=row['ttt_veh_h']
        assert abs(cost['FW_E']+cost['FW_W']+cost['urban_ramps_inside']-metrics['ttt_veh_h'])<1e-7
        row=dict(ttt_veh_h=metrics['ttt_veh_h'],components_veh_h=cost,
            observed_and_inferred_omega_exits=metrics['ttd_observed_plus_terminal_events'],
            last_observed_inside_vehicles=metrics['censored_last_observed_inside_vehicles'],
            native_removals=len(removals),unresolved_inside_disappearances=metrics['unresolved_inside_disappearances'],
            uninserted_at_end=None if arm=='nc' else sum(e['remaining_vehicles'] for e in events if e['kind']=='unfinished_vehicle_input'),
            native_execution_passed=execution['native_execution_passed'],lsa_passed=execution['native_lsa_com_coverage_passed'],
            native_execution_failed_checks=[k for k,v in execution['checks'].items() if isinstance(v,dict) and v.get('passed') is False],
            run_dir=str(run_dir),fzp_path=str(fzp),fzp_bytes=before.st_size,fzp_mtime_ns=before.st_mtime_ns,
            fzp_rows=rowcount,last_fzp_sec=last,wall_sec=time.perf_counter()-arm_start)
        output['conditions'][arm]=row;series[arm]=times
        save(OUT/'progress.json',output)
        print('DONE '+arm+' '+json.dumps(row,ensure_ascii=False),flush=True)
    assert all(v==prefixes['nc'] for v in prefixes.values()),'Common900 prefix mismatch'
    output['precontrol_prefix_exact']=True;output['prefixes']=prefixes
    for arm,row in output['conditions'].items():
        nc=output['conditions']['nc']
        row['delta_ttt_veh_h']=row['ttt_veh_h']-nc['ttt_veh_h']
        row['improvement_percent']=100*(1-row['ttt_veh_h']/nc['ttt_veh_h'])
        row['component_improvement_percent']={k:100*(1-v/nc['components_veh_h'][k]) for k,v in row['components_veh_h'].items()}
    output['all_native_execution_passed']=all(x['native_execution_passed'] for x in output['conditions'].values())
    output['source_pins']=pins;output['wall_sec']=time.perf_counter()-started
    save(OUT/'summary.json',output)
    canonical.table(OUT/'comparison.csv',[dict(condition=arm,**{k:v for k,v in row.items() if not isinstance(v,(dict,list))},
        **row['components_veh_h']) for arm,row in output['conditions'].items()])
    plot(output,heat,edges,time_edges,geo,series)
    save(OUT/'completion.json',dict(status='complete',summary=str(OUT/'summary.json'),wall_sec=output['wall_sec']))
    print('COMPLETE '+str(OUT),flush=True)

def plot(report,heat,edges,time_edges,geo,series):
    for road,title in (('FW_E','동측'),('FW_W','서측')):
        for zoom in (False,True) if road=='FW_E' else (False,):
            fig,axes=plt.subplots(4,1,figsize=(14,12),sharex=True,layout='constrained')
            for ax,arm in zip(axes,ARMS):
                mesh=ax.pcolormesh(time_edges,edges[road]/1000,heat[arm][road],cmap='RdYlBu',vmin=0,vmax=110,rasterized=True)
                for boundary in geo['boundaries']:
                    if boundary['road']==road and boundary['kind'] in ('ramp','offramp'):
                        ax.axhline(boundary['chain_pos_m']/1000,color='black',ls='--',lw=.55,alpha=.4)
                ax.set_title(LABELS[arm],loc='left',fontweight='bold');ax.set_ylabel('하류 방향 거리 [km]')
                ax.set_xlim(0,8100)
                if zoom:ax.set_ylim(3.3,9)
            axes[-1].set_xlabel('시뮬레이션 시간 [초]')
            fig.colorbar(mesh,ax=axes,label='차량 가중 평균속도 [km/h]',shrink=.7)
            fig.suptitle(f'{title} 고속도로 | seed29 · FW80/도시90 · 0–8100초\n실측 FZP 5초 기록 → 15초 × 100m 집계',fontsize=15,fontweight='bold')
            suffix='_zoom' if zoom else ''
            fig.savefig(OUT/(road+'_heatmap'+suffix+'.png'),dpi=150);plt.close(fig)
    colors=['#808080','#2476b8','#d47720','#239379']
    fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    for arm,c in zip(ARMS,colors):
        rows=series[arm];t=[r['sim_sec'] for r in rows];v=[r['ttt_veh_h_cumulative'] for r in rows]
        axes[0].plot(t,v,label=LABELS[arm],color=c,lw=2)
    axes[0].set(xlabel='시뮬레이션 시간 [초]',ylabel='누적 Ω701 TTT [대·시간]',xlim=(0,8100))
    axes[0].legend();axes[0].grid(alpha=.25)
    keys=['FW_E','FW_W','urban_ramps_inside'];names=['동측 본선','서측 본선','도시부·램프 등 Ω 내부']
    x=np.arange(4);bottom=np.zeros(4)
    for k,name,c in zip(keys,names,['#5e91ba','#8cc2d8','#dda465']):
        values=np.array([report['conditions'][a]['components_veh_h'][k] for a in ARMS])
        axes[1].bar(x,values,bottom=bottom,label=name,color=c);bottom+=values
    for i,arm in enumerate(ARMS):
        r=report['conditions'][arm]
        label=f"{r['ttt_veh_h']:,.1f}"+('' if arm=='nc' else f"\n{r['improvement_percent']:+.2f}% 개선")
        axes[1].text(i,bottom[i]+90,label,ha='center',va='bottom',fontsize=10)
    axes[1].set_xticks(x,[LABELS[a] for a in ARMS]);axes[1].set_ylabel('TTT [대·시간]')
    axes[1].set_ylim(0,max(bottom)*1.2);axes[1].legend(loc='upper left',fontsize=9)
    fig.suptitle('동일 Ω701·0–8100초 TTT 비교 | 도시 신호·RM은 세 조건 모두 SDMPC',fontsize=14,fontweight='bold')
    fig.savefig(OUT/'TTT_comparison.png',dpi=160);plt.close(fig)

if __name__=='__main__':
    try:run()
    except Exception:
        if OUT.exists():save(OUT/'failure.json',dict(error=traceback.format_exc()))
        raise
