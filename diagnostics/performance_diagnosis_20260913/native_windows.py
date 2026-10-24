"""One post-run pass per native FZP, preserving the interrupted-prefix scope."""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from diagnostics import summarize_fast_nc as s
from diagnostics.capture_native_runtime_errors import parse_bytes

END=8850
OUT=Path(__file__).parent/'native_windows'
RUNS={'nc':'codex_phys8_fidelity_fw080_u050_nc9000_s13_v1','cl':'codex_fid_cl9000_s13_v3'}

def write(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def analyze(name,run_id,membership,terminals,bounds,addresses):
    run=ROOT/'evaluation/runs'/run_id
    out=OUT/name;out.mkdir()
    fzp=run/'vissim_eval/baseline_001.fzp'
    before=(fzp.stat().st_size,fzp.stat().st_mtime_ns)
    removals=[];errors=[]
    for p in sorted(run.glob('*.err')):
        data=p.read_bytes();parsed=parse_bytes(data)
        removals.extend(e for e in parsed['events'] if e['kind']=='lane_change_removal' and e['time_sec']<=END)
        errors.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
                       'counts':parsed['counts'],'partial_tail_bytes':parsed['partial_tail_bytes'],
                       'unparsed_removal_lines':parsed['unparsed_removal_lines'],
                       'completed_run_error_certificate':False})
    s.require(len({(r['vehicle_id'],r['link'],r['time_sec']) for r in removals})==len(removals),'Duplicate removal warnings')
    previous={};old_counts=Counter();old_slow=Counter();old_stopped=Counter()
    bins={};pairs={};evidence={};frames=0
    def forward():
        nonlocal previous,old_counts,old_slow,old_stopped,frames
        deadline=time.monotonic()+1800
        for sec,current in s.native_frames(fzp,evidence,deadline=deadline):
            if sec>END:
                continue  # Exhaust NC's final150s only to finish the full-file integrity hash.
            frames=sec
            counts=Counter();slow=Counter();stopped=Counter();entries=Counter();departures=Counter();absent=Counter();lanes=Counter()
            block=(sec-1)//150*150
            for no,row in current.items():
                link=row[0];counts[link]+=1;slow[link]+=row[3]<5;stopped[link]+=row[3]<=1
                old=previous.get(no)
                if old is None or old[0]!=link:entries[link]+=1
                if old is not None and old[0]==link and old[1]!=row[1]:lanes[link]+=1
            for no,old in previous.items():
                new=current.get(no)
                if new is None:absent[old[0]]+=1
                elif new[0]!=old[0]:
                    departures[old[0]]+=1
                    key=(block,old[0],new[0]);pairs[key]=pairs.get(key,0)+1
            for link in counts.keys()|old_counts.keys():
                key=(block,link)
                if key not in bins:
                    bins[key]={'start_sec':block,'end_sec':block+150,'link':link,'inside_omega':membership[str(link)],
                               'start_n':old_counts[link],'end_n':0,'ttt_veh_h':0.,'slow_veh_h':0.,'stopped_veh_h':0.,
                               'entry_events':0,'observed_other_link_exits':0,'unresolved_absences':0,'same_link_lane_changes':0}
                b=bins[key]
                b['ttt_veh_h']+=(counts[link]+old_counts[link])/7200
                b['slow_veh_h']+=(slow[link]+old_slow[link])/7200
                b['stopped_veh_h']+=(stopped[link]+old_stopped[link])/7200
                b['end_n']=counts[link]
                for field,value in [('entry_events',entries[link]),('observed_other_link_exits',departures[link]),
                                    ('unresolved_absences',absent[link]),('same_link_lane_changes',lanes[link])]:b[field]+=value
                s.require(old_counts[link]+entries[link]-departures[link]-absent[link]==counts[link],'Physical road closure mismatch')
            previous=current;old_counts=counts;old_slow=slow;old_stopped=stopped
            if sec%1500==0:print(json.dumps({'run':name,'scanned_sec':sec}),flush=True)
            yield sec,current
    started=time.perf_counter()
    result=s.summarize_stream(forward(),membership,terminals,bounds,addresses,removals,end=END)
    s.require(before==(fzp.stat().st_size,fzp.stat().st_mtime_ns),'FZP changed during analysis')
    s.require(frames==END,'Incomplete prefix')
    integrated=sum(v['ttt_veh_h'] for v in bins.values() if v['inside_omega'])
    s.require(abs(integrated-result['metrics']['ttt_veh_h'])<1e-7,'Independent window sum differs from canonical TTT')
    existing=(ROOT/'diagnostics/handoff_20260913/ttt_prefix8850/area_timeseries.csv' if name=='cl' else
              ROOT/'diagnostics/control_improvement/decision_common_anchor_20260911/ramp8_physical_v1/fidelity_nc9000_s13_full_v1/area_timeseries.csv')
    with existing.open(encoding='utf-8-sig') as f:reference=next(r for r in csv.DictReader(f) if float(r['sim_sec'])==END)
    s.require(abs(float(reference['ttt_veh_h_cumulative'])-integrated)<1e-7,'Prior measurement mismatch')
    for filename,key in [('area_timeseries.csv','area_rows'),('roads_30s.csv','road_samples'),('fw_cells_30s.csv','cell_samples'),('road_windows_900s.csv','road_windows')]:
        write(out/filename,result[key])
    write(out/'links_150s.csv',[bins[k] for k in sorted(bins)])
    write(out/'observed_link_pairs_150s.csv',[{'start_sec':k[0],'end_sec':k[0]+150,'from_link':k[1],'to_link':k[2],'vehicles':v} for k,v in sorted(pairs.items())])
    s.save(out/'area_metrics.json',result['metrics'])
    report={'schema':'performance-native-prefix/v1','run':run_id,'prefix_end_sec':END,'native_run_completed':name=='nc',
            'full_execution_certified_here':False,'seed':13,'fzp':evidence,'frames':frames,'elapsed_sec':time.perf_counter()-started,
            'ttt_veh_h':integrated,'prior_prefix_ttt_matches':True,'native_error_files':errors,
            'prefix_removal_warnings':len(removals) if name=='nc' else None,'terminal_removal_collisions':result['terminal_conflicts'],
            'native_simulation_error_files':[r for r in errors if not Path(r['path']).name.startswith('runlog_')],
            'native_simulation_error_log_complete':name=='nc' and any(not Path(r['path']).name.startswith('runlog_') for r in errors),
            'native_removal_count_interpretation':'Available warning count only; CL interrupted error log does not establish zero removals.',
            'limits':['Full NC file hashed; only0–8850s measured. CL ends8850 and has no completion receipt.',
                      'NC-vs-CL intervals compare evolved policy trajectories, not same-state command counterfactuals.',
                      'Observed link-pair events may skip intermediate links between1s frames; not desired demand.',
                      'Absence is never a normal road discharge; final vehicles stay censored. ERR completeness not certified.']}
    s.save(out/'summary.json',report)
    print(json.dumps({'run':name,'complete_prefix_analysis':True,'ttt':integrated,'elapsed':report['elapsed_sec']}),flush=True)

def main():
    s.require(not OUT.exists(),'Preserve prior analysis; new output directory required')
    OUT.mkdir()
    document=s.load(s.MEMBERSHIP);membership=s.physical_membership_from_ledger(document)
    bounds,addresses,proof=s.cell_geometry();s.save(OUT/'geometry.json',proof)
    for name,run_id in RUNS.items():analyze(name,run_id,membership,s.terminal_lengths(document),bounds,addresses)

if __name__=='__main__':main()
