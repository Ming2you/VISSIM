"""Closed matched replay, using the existing native verifier and Omega meter."""
import ctypes, csv, json, sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics.sdmpc_n31_20260924.integration_20260926.native_pair1200.analyze_pair import (
    verify_native_execution, prefix_digest, parse_bytes, read_fzp_frames, measure_frames,
    terminal_lengths, sha256, physical_membership_from_ledger, native_network_cost)
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PROTOCOL=I/'native_rm10480_spill256/protocol.json'
RUNS=Path('D:/VISSIM_runs/20261005_rm10480_spill256')
OLD=Path('D:/VISSIM_runs/20261005_rm233_235_fixed90_s29_9000/sdmpc')
OUT=HERE/'analysis'
read=lambda p:json.loads(p.read_bytes())
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def table(p,rows):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True,layout='constrained')
    for arm,color,label in [('hold','#c43b35','기존 명령'),('release','#197b9c','10480만 단계적으로 개방')]:
        with (OUT/arm/'queue_trace.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        t=[float(r['time']) for r in rows]
        for ax,key in zip(axes,['stopped_124','n_10483','n_10480']):
            ax.plot(t,[float(r[key]) for r in rows],color=color,label=label,lw=1.8)
    for ax,title in zip(axes,['124번 도로 정지 차량','10483 동측 진출램프 재고','10480 서측 진입램프 재고']):
        ax.set_title(title,loc='left',weight='bold');ax.set_ylabel('차량 수 [대]')
        ax.axvline(3150,color='#555',ls='--',lw=1);ax.grid(alpha=.2);ax.set_ylim(bottom=0)
    axes[0].legend(loc='upper left',frameon=False);axes[-1].set_xlabel('시뮬레이션 시간 [초]')
    fig.suptitle('공유 차로 차단: 10480 → 124 → 10483\n3150초 이후 10480만 2→4→6초 녹색으로 완화',weight='bold')
    fig.text(.01,-.018,'seed29 · 동일 차량 상태/나머지 명령 · native FZP 5초 관측 · 짧은 고정 명령 비교이며 9000초 성능 결과가 아님',fontsize=10)
    fig.savefig(OUT/'spillback_response.png',dpi=160,bbox_inches='tight');plt.close(fig)

def main():
    assert not (RUNS/'STOP').exists() and not (OUT/'summary.json').exists()
    closure=read(HERE/'native_closure.json')
    assert closure['all_owned_processes_closed'] and closure['owner_exit_code']==0
    status=read(PROTOCOL.parent/'status.json');assert status['stage']=='both_native_complete_unanalyzed'
    protocol=read(PROTOCOL)
    for p,h in protocol['command_pins'].items(): assert sha256(Path(p))==h,p
    ledger=read(I/'selected/scenario/control_area_membership_213a5d.json')
    for pin in [ledger['network'],*ledger['sources']]:assert sha256(ROOT/pin['path'])==pin['sha256']
    membership=physical_membership_from_ledger(ledger);terminals=terminal_lengths(ledger)
    mapping=read(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json')
    chains={k:set(map(str,v['chain_links'])) for k,v in mapping['freeway_model_links'].items()}
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p;k.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_uint32];assert k.SetPriorityClass(k.GetCurrentProcess(),0x4000)
    original_fzp,=(OLD/'vissim_eval').glob('*.fzp')
    prefixes={'original':prefix_digest(original_fzp,3150,recording_grid=(5,.1))}
    results={};initial=None
    for arm in ('hold','release'):
        run=RUNS/arm;name=f'sdmpc31_g_3150_{arm}_s29';dec=run/('decisions_'+name)
        execution=verify_native_execution(run,3600,run_name=name)
        save(OUT/arm/'execution.json',execution);assert execution['native_execution_passed']
        prov=read(run/('run_provenance_'+name+'.json'))
        assert prov['seed']==29 and prov['files']['network']['sha256']==protocol['network_sha256']
        for t in (1,*range(150,3601,150)):
            for ext in ('csv','json'):
                file=f'action_{t:06d}.{ext}'
                assert sha256(dec/file)==sha256(PROTOCOL.parent/arm/'commands'/file)
        current=read(dec/'state_003150.json')['vehicle_records']
        assert current['complete']
        if initial is None:initial=current['records']
        assert current['records']==initial==read(OLD/'decisions_sdmpc31_sdmpc9000_s29/state_003150.json')['vehicle_records']['records']
        fzp,=(run/'vissim_eval').glob('*.fzp');before=fzp.stat()
        prefixes[arm]=prefix_digest(fzp,3150,recording_grid=(5,.1))
        trace=[]
        def frames():
            for frame in read_fzp_frames(fzp):
                assert frame.time_sec<=3600
                if frame.time_sec>=2700:
                    n=Counter();slow=Counter()
                    for v in frame.vehicles.values():
                        n[v.link]+=1
                        if v.speed_kph<=5:slow[v.link]+=1
                    trace.append(dict(time=frame.time_sec,**{f'n_{x}':n[x] for x in ('10480','10483','124','31','10774','127')},
                        **{f'stopped_{x}':slow[x] for x in ('10480','10483','124','31')}))
                yield frame
        metrics,times=measure_frames(frames(),membership,terminals,end_sec=3600,simulation_step_sec=.1,include_distance=True)
        assert metrics['sampling']['nominal_step_sec']==5 and not metrics['sampling']['missing_snapshot_gaps']
        after=fzp.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        save(OUT/arm/'area_metrics.json',metrics);table(OUT/arm/'area_timeseries.csv',times);table(OUT/arm/'queue_trace.csv',trace)
        events=[]
        for p in sorted(run.rglob('*.err')):
            e=parse_bytes(p.read_bytes());assert not e['unparsed_removal_lines'];events+=e['events']
        events=[json.loads(x) for x in sorted({json.dumps(e,sort_keys=True) for e in events})]
        save(OUT/arm/'errors.json',events)
        road_ttt={road:sum(metrics['physical_link_residence'].get(link,{}).get('ttt_veh_h',0.) for link in ids) for road,ids in chains.items()}
        results[arm]=dict(ttt_omega=metrics['ttt_veh_h'],road_ttt=road_ttt,
            observed_outside_ttt=sum(r['ttt_veh_h'] for r in metrics['physical_link_residence'].values() if not r['inside']),
            normal_exit_events_sampled=metrics['ttd_observed_plus_terminal_events'],
            unresolved_disappearances=metrics['unresolved_inside_disappearances'],residual_omega=metrics['censored_last_observed_inside_vehicles'],
            errors_by_kind=dict(Counter(e['kind'] for e in events)),native= native_network_cost(run,3600),
            last_trace=trace[-1],execution_passed=True)
        print(arm,results[arm]['ttt_omega'],flush=True)
    assert prefixes['original']==prefixes['hold']==prefixes['release'],'Reject causal comparison on any microscopic prefix difference'
    summary=dict(status='complete',start=3150,end=3600,prefix_exact=True,initial_vehicle_records_exact=True,prefixes=prefixes,
        results=results,delta_omega=results['release']['ttt_omega']-results['hold']['ttt_omega'],
        delta_observed_outside=results['release']['observed_outside_ttt']-results['hold']['observed_outside_ttt'],
        delta_roads={r:results['release']['road_ttt'][r]-results['hold']['road_ttt'][r] for r in chains},
        scope='Only10480 g2/4/6 after3150 versus recorded0/0/2; all prior traffic exact and other commands identical.450s conditional response, not full9000 gain.',
        limits=['5s FZP sampling; crossing events can be missed between samples.','Terminal exits are inferred by the existing validated estimator; deletions are reported separately.','LSA incomplete; approved native LDP and application readback verification required.'])
    save(OUT/'summary.json',summary)
    plot()
    print(json.dumps(dict(status='complete',delta_omega=summary['delta_omega'],delta_roads=summary['delta_roads'])))

if __name__=='__main__':main()
