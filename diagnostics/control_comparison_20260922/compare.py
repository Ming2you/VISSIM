"""One post-run FZP pass per completed arm; existing Omega accounting, no COM."""
from pathlib import Path
from collections import Counter
import csv, hashlib, importlib.util, json, math, re, sys, time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / '.review-deps'), str(ROOT)]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.measure_control_area import Frame, Vehicle, measure_frames
from diagnostics.capture_native_runtime_errors import parse_bytes
source = ROOT/'diagnostics/demand_sweep/user_native_20260914/native_fixed_profile_v2/analysis/analyze_four_arms.py'
spec = importlib.util.spec_from_file_location('existing_area_proof', source)
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
GEOMETRY = ROOT/'diagnostics/demand_sweep/ramp_dsd_20260916_v2/segment_resolution_20260921/geometry_200_branch_guard.json'
Q = Path('D:/VISSIM_runs/20260922_fw080_urban090_controls')
RUNS = {'none': Path('D:/VISSIM_runs/20260922_both_off_half/fw080_urban090_nc9000/run'),
        **{a: Q/a/'run' for a in ('rm','vsl','both')}}
LABEL = {'none':'No control', 'rm':'ALINEA RM', 'vsl':'Rule VSL', 'both':'RM + VSL'}
END = 9000

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, data): p.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
def table(p, rows):
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def raw_frames(path, evidence, observers=()):
    digest=hashlib.sha256(); prefix=hashlib.sha256(); current={}; last=None; rows=0; hashes=[]
    observed_frame={}
    framehash=hashlib.sha256()
    with path.open('rb') as f:
        columns=None
        for raw in f:
            digest.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                columns=raw.strip().split(b':',1)[1].split(b';')
                assert columns[:7]==[b'SIMSEC',b'NO',b'LANE\\LINK\\NO',b'LANE\\INDEX',b'POS',b'POSLAT',b'SPEED']
            if not raw[:1].isdigit(): continue
            assert columns is not None and raw.endswith(b'\n')
            p=raw.split(b';',7); t=float(p[0]); no=p[1].decode('ascii'); link=p[2].decode('ascii')
            if t != last:
                if last is not None:
                    for observer in observers: observer.advance(last,observed_frame)
                    hashes.append((last,framehash.hexdigest())); yield last,current
                    assert abs(t-last-5)<1e-7, (last,t)
                last=t; current={}; framehash=hashlib.sha256()
                observed_frame={}
            assert no not in current and 0<t<END
            current[no]=(link,float(p[4]),float(p[6]))
            if observers: observed_frame[int(no)]=(int(link),int(p[3]),float(p[4]),float(p[6]))
            rows+=1
            if t<900: prefix.update(raw); framehash.update(raw)
        if last is not None:
            for observer in observers: observer.advance(last,observed_frame)
            hashes.append((last,framehash.hexdigest())); yield last,current
    assert last >= END-5
    evidence.update(sha256=digest.hexdigest(), prefix_before900_sha256=prefix.hexdigest(),
                    rows=rows, frames=len(hashes), last_sec=last,
                    precontrol_frame_hashes=[h for h in hashes if h[0]<900])

def analyze(arm, run, geometry, observers=(), *, seed=23):
    out=HERE/arm; out.mkdir(exist_ok=True)
    receipt=load(run/'run.json'); network=Path(receipt['network'])
    assert receipt['completed'] and receipt['exit_code']==0 and receipt['terminal_sec']==END and receipt['seed']==seed
    assert receipt.get('owned_native_alive') is False and receipt.get('error') is None
    log=(run/'stdout.txt').read_text(encoding='utf-8-sig')
    assert 'STAGE=SIM_DONE' in log and float(re.findall(r'^SIM_SEC=([^\r\n]+)',log,re.M)[-1])==END
    with (run/'readback.csv').open(encoding='utf-8-sig') as f: readback=list(csv.DictReader(f))
    assert any(r['no']=='SimRes' and float(r['actual'])==10 for r in readback)
    assert any(r['no']=='VehRecResolution' and float(r['actual'])==50 for r in readback)
    validation=None
    if arm!='none':
        v=load(run/'fixed_validation.json'); assert v['passed'] and receipt['fixed_profile_validation_exit_code']==0
        validation={k:v[k] for k in ('passed','event_readbacks','native_ldp_row_count','unrecorded_signal_groups','native_meter_samples_checked','native_lsa_scope')}
        assert not v['unrecorded_signal_groups']
    proof,membership,omega_terminals=old.area_proof(network,geometry)
    save(out/'omega_membership_proof.json',proof); assert proof['status']=='PASS',proof
    links,edges=old.physical_network(network)
    outgoing={e['from_link'] for e in edges.values()}
    terminals={n:r['length_m'] for n,r in links.items() if n not in edges and n not in outgoing}
    chain={str(r['link']):(d,r) for d,rs in geometry['chains'].items() for r in rs}
    for n,(_,r) in chain.items(): assert abs(links[n]['length_m']-r['length_m'])<.02
    events=[]; errors=[]
    for p in sorted(run.glob('*.err')):
        parsed=parse_bytes(p.read_bytes()); assert not parsed['unparsed_removal_lines']
        errors.append({'file':str(p),'counts':parsed['counts'],'unparsed':parsed['unparsed']})
        events.extend(parsed['events'])
    removals={str(e['vehicle_id']):e for e in events if e['kind']=='lane_change_removal'}
    save(out/'native_errors.json', {'files':errors,'removals':list(removals.values()),
                                  'uninserted':[e for e in events if e['kind']=='unfinished_vehicle_input']})
    ys={d:np.append(np.arange(0,geometry['bounds'][d][-1],100),geometry['bounds'][d][-1]) for d in geometry['chains']}
    count={d:np.zeros((len(y)-1,300)) for d,y in ys.items()}; moment={d:np.zeros_like(n) for d,n in count.items()}
    audit=Counter(); all_ids=set(); ended=set(); unknown=[]; previous={}; previous_time=0; evidence={}; snapshot=[]
    fzps=list((run/'vissim_eval').glob('*.fzp'))
    assert len(fzps)==1, 'Exactly one native FZP per isolated run is required'
    fzp=fzps[0]; before=fzp.stat()
    def frames():
        nonlocal previous,previous_time
        for t,current in raw_frames(fzp,evidence,observers):
            assert not (ended & current.keys()), 'Inferred terminal exit reappeared'
            dt=t-previous_time
            for no,(link,pos,speed) in previous.items():
                if no in current: continue
                gap=terminals.get(link, math.inf)-pos
                reachable=(-speed/3.6*.1-.5*3*.1**2-10 <= gap <= speed/3.6*dt+.5*3*dt**2+10)
                removed=no in removals and previous_time-.11 <= removals[no]['time_sec'] <= t+.11
                if removed:
                    audit['observed_native_removal']+=1
                    assert not (reachable and link in omega_terminals), 'Removal conflicts with existing terminal inference'
                elif reachable:
                    audit['normal_network_termination_inferred']+=1; ended.add(no)
                else:
                    audit['unresolved_network_disappearance']+=1
                    unknown.append({'time_s':t,'vehicle':no,'last_link':link,'last_position_m':pos,'inside_omega':membership[link]})
            all_ids.update(current)
            group=Counter()
            for link,pos,speed in current.values():
                if link in chain:
                    d,r=chain[link]; x=r['offset_m']+pos
                    if 0<=x<ys[d][-1]:
                        i=min(int(x//100),len(ys[d])-2); j=int(t//30)
                        count[d][i,j]+=1; moment[d][i,j]+=speed
                    else: audit['heatmap_outside_chain_rows']+=1
                    group[d]+=1
            snapshot.append({'time_s':t,'network_n':len(current),'FW_E_n':group['FW_E'],'FW_W_n':group['FW_W']})
            previous=current; previous_time=t
            yield Frame(t,{no:Vehicle(*row) for no,row in current.items()})
    area, times=measure_frames(frames(),membership,omega_terminals,end_sec=END,max_tail_extrap_sec=5,simulation_step_sec=.1)
    after=fzp.stat(); assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert area['sampling']['missing_snapshot_gaps']==0 and area['sampling']['nominal_step_sec']==5
    audit['observed_unique_vehicles']=len(all_ids); audit['last_network_n']=len(previous)
    # Every disappeared observed vehicle belongs to one of these groups; none of the final vehicles is an exit.
    assert len(all_ids)==len(previous)+audit['normal_network_termination_inferred']+audit['observed_native_removal']+audit['unresolved_network_disappearance']
    audit['native_removals_total']=len(removals)
    audit['uninserted_at_end']=sum(e['remaining_vehicles'] for e in events if e['kind']=='unfinished_vehicle_input')
    save(out/'area_metrics.json',area); table(out/'area_timeseries.csv',times); table(out/'stocks.csv',snapshot)
    if unknown: table(out/'unresolved_disappearances.csv',unknown)
    save(out/'fzp_evidence.json',evidence); save(out/'audit.json',dict(audit)); save(out/'actuator_validation.json',validation)
    np.savez_compressed(out/'heatmap.npz',**{f'{d}_{k}':v for d in count for k,v in [('count',count[d]),('speed_sum',moment[d]),('y_m',ys[d])]})
    groups=Counter()
    for n,r in area['physical_link_residence'].items():
        if r['inside']: groups[chain[n][0] if n in chain else 'urban_ramps_other']+=r['ttt_veh_h']
    row={'arm':arm,'TTT_veh_h':area['ttt_veh_h'], 'Omega_TTD_events':area['ttd_observed_plus_terminal_events'],
         'Omega_live_exits':area['ttd_observed_exit_events'],'Omega_terminal_exits_inferred':area['ttd_terminal_exit_inferred_events'],
         'network_termination_vehicles_inferred':audit['normal_network_termination_inferred'],
         'Omega_end_n':area['censored_last_observed_inside_vehicles'],
         'native_removed':len(removals),'uninserted_at_end':audit['uninserted_at_end'],
         'unresolved_Omega_disappearances':area['unresolved_inside_disappearances'],
         'unresolved_network_disappearances':audit['unresolved_network_disappearance'],
         'TTT_FW_E':groups['FW_E'],'TTT_FW_W':groups['FW_W'],'TTT_urban_ramps_other':groups['urban_ramps_other'],
         'tail_hold_TTT_veh_h':area['ttt_censored_tail_extrapolation_veh_h']}
    save(out/'performance.json',row)
    print(arm, json.dumps(row), flush=True)
    return row

def figures(geometry, *, seed=23):
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':11})
    cmap=plt.get_cmap('RdYlBu').copy(); cmap.set_bad('#ececec')
    for d,label in [('FW_E','동측'),('FW_W','서측')]:
        plot_rows=math.ceil(len(RUNS)/2)
        fig,axs=plt.subplots(plot_rows,2,figsize=(15,4.7*plot_rows),sharex=True,sharey=True,layout='constrained',squeeze=False)
        for ax,arm in zip(axs.flat,RUNS):
            data=np.load(HERE/arm/'heatmap.npz'); n=data[d+'_count']; m=data[d+'_speed_sum']
            speed=np.divide(m,n,out=np.full_like(m,np.nan),where=n>0)
            im=ax.pcolormesh(np.arange(0,END+1,30),data[d+'_y_m']/1000,speed,cmap=cmap,vmin=0,vmax=120,shading='flat',rasterized=True)
            ax.set_title(LABEL[arm],weight='bold'); ax.axvline(900,color='black',ls=':',lw=1)
            for b in geometry['boundaries']:
                if b['road']==d and b['kind'] in ('ramp','offramp'):
                    ax.axhline(b['chain_pos_m']/1000,ls='--',color='black',alpha=.25,lw=.65)
            ax.set_xticks(np.arange(0,9001,1800)); ax.set_xlim(0,9000)
        for ax in list(axs.flat)[len(RUNS):]: ax.set_visible(False)
        for ax in axs[-1]: ax.set_xlabel('시뮬레이션 시간 [초]')
        for ax in axs[:,0]: ax.set_ylabel('본선 진입점부터 거리 [km] → 하류')
        fig.colorbar(im,ax=axs,label='차량 가중 평균속도 [km/h]',shrink=.88)
        fig.suptitle(f'{label} 고속도로 · 80% / 도시 90% · seed {seed}\nFZP 5초 → 30초 × 100m | 세로선: 제어 시작 900초 · 가로선: 램프 접속 | 동일 색 범위',fontsize=15)
        fig.savefig(HERE/f'{d}_four_conditions.png',dpi=150); plt.close(fig)

def main():
    assert load(Q/'queue_status.json')['status']=='complete'
    geometry=load(GEOMETRY); rows=[]
    for arm,run in RUNS.items():
        if (HERE/arm/'performance.json').exists(): row=load(HERE/arm/'performance.json')
        else: row=analyze(arm,run,geometry)
        rows.append(row)
    for r in rows: r['TTT_change_percent']=100*(r['TTT_veh_h']/rows[0]['TTT_veh_h']-1)
    prefixes={a:load(HERE/a/'fzp_evidence.json')['prefix_before900_sha256'] for a in RUNS}
    save(HERE/'summary.json',{'performance':rows,'precontrol_raw_FZP_prefix_equal':len(set(prefixes.values()))==1,
         'precontrol_prefixes':prefixes,'scope':'Omega = freeway plus canonical protected urban network; 0–9000 seconds; final 4.9 seconds last stock held without exit credit.',
         'termination_definition':'Observed vehicle disappearing from a verified physical terminal within speed/acceleration reach, excluding explicit native removals; FZP5s inference, not exact native total.',
         'TTD_definition':'Observed live exits from Omega plus inferred terminal departures inside Omega; internal moves, native removals, unresolved disappearances and terminal censored stock excluded.',
         'warning':'5s FZP can miss short links, between-frame exits/reentries and entire short trips. Uninserted vehicles are outside Omega TTT; compare their backlog separately. One seed; not MPC or a calibrated-plant gain test.'})
    table(HERE/'performance.csv',rows); figures(geometry)
    print('COMPLETE',flush=True)

if __name__=='__main__': main()
