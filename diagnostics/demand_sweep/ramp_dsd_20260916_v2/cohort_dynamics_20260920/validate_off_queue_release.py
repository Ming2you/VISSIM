"""Verify receipts and record nonzero entry flow before a5km/h restart."""
from pathlib import Path
import sys,hashlib,statistics
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.off_queue_release import predict

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'off_queue_release_validation_v1.json'
    if out.exists():raise FileExistsError(out)
    controlled=e.load(HERE/'off_queue_release_controlled_v1/result.json')
    wave=e.load(HERE/'off_initial_wave_response_v1/result.json')
    first=e.load(HERE/'off_queue_release_v1/result.json')
    pins_checked=0
    for protocol in (first,e.load(HERE/'off_queue_release_controlled_v1/protocol.json'),
                     e.load(HERE/'off_initial_wave_response_v1/protocol.json')):
        for file,pin in protocol['pins'].items():
            assert hashlib.sha256((e.ROOT/file).read_bytes()).hexdigest()==pin,file
            pins_checked+=1
    results={};reproduced=event_checks=stock_checks=0
    for case,result in controlled['results'].items():
        seed,arm=case.split('_',1)
        path=HERE/(f'off_space_wave_v2/s{seed}_frames.json' if arm=='none'
                   else f'off_queue_release_controlled_v1/s{seed}_{arm}_frames.json')
        data=e.load(path);frames={r['time_s']:r['vehicles'] for r in data['frames']}
        if arm!='none':event_checks+=data['event_checks'];stock_checks+=data['stock_checks']
        lookup={t:{vid:(l,p,v) for vid,l,p,v in rows} for t,rows in frames.items()}
        unique={};pre_start=[]
        for row in result['samples']:
            t=row['time_s'];lane=row['lane'];p=predict(frames[t],lane,2)
            assert p is not None and all(row[key]==v for key,v in p.items())
            assert predict(list(reversed(frames[t])),lane,2)==p
            reproduced+=1
            if p['status']!='moving_front_observed':continue
            # Earliest prediction per tracked entrance vehicle avoids counting
            # the same vehicle at every overlapping10s forecast start.
            unique.setdefault((lane,p['vehicle']),row)
            end=t+int(p['predicted_restart_delay_s']);events=[]
            for sec in range(t+1,end):
                for vid in lookup[sec].keys()-lookup[sec-1].keys():
                    if lookup[sec][vid][0]==lane:
                        events.append(dict(time_s=sec,vehicle=vid,entry_state=lookup[sec][vid],
                            original_entrance_vehicle=lookup[sec].get(p['vehicle'])))
            if events:pre_start.append(dict(start=t,predicted_delay=p['predicted_restart_delay_s'],
                actual_restart=row['actual_restart_s'],lane_change_before_restart=row['lane_change_before_restart_s'],events=events))
        rows=list(unique.values());known=[r for r in rows if r['actual_restart_s'] is not None]
        results[case]=dict(first_observation_per_entrance_vehicle=len(rows),comparable=len(known),
            censored_or_changed=len(rows)-len(known),
            restart_mae_s=statistics.mean(abs(r['predicted_restart_delay_s']-r['actual_restart_s']) for r in known) if known else None,
            constant_pair_lag_mae_s=statistics.mean(abs(2-r['actual_restart_s']) for r in known) if known else None,
            nonzero_entries_strictly_before_predicted_restart=pre_start)
    assert reproduced==132 and wave['disabled_json_exact']==12 and wave['lane_interface_checks']==1080
    assert wave['source_pins_verified'] and controlled['source_pins_verified']
    files=[Path(__file__),HERE/'off_queue_release_controlled_v1/result.json',HERE/'off_initial_wave_response_v1/result.json',HERE/'off_queue_release_v1/result.json']
    e.save(out,dict(status='LOCAL_STARTUP_RELATION_VERIFIED_GAIN_NOT_QUALIFIED',pins_checked=pins_checked,
        current_snapshot_and_permutation_checks=reproduced,controlled_native_event_checks=event_checks,
        controlled_native_stock_checks=stock_checks,results=results,disabled_full_json_exact=wave['disabled_json_exact'],
        lane_interface_checks=wave['lane_interface_checks'],state_guards_passed=sum(r['guards_passed'] for r in wave['results'].values()),
        source_pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        caveats=['Earliest-per-vehicle observations still share traffic waves and are not independent experimental replications.',
            'A stopped entrance vehicle can creep below5km/h or leave the lane; zero admission until its5km/h restart is not a valid general capacity bound.',
            'The450s probe changes only initial known-queue recovery, not newly forming blockages; no full dynamic closure or gain qualification.'],
        native_runs_started=0,production_adopted=False,qualified=False))
    print('PASS',reproduced,'current snapshots,',event_checks,'native events,',stock_checks,'stocks')
    for key,row in results.items():print(key,{k:v for k,v in row.items() if k!='nonzero_entries_strictly_before_predicted_restart'})


if __name__=='__main__':main()
