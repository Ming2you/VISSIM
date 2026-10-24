"""Cached cell20 spatial-state and executed speed-cap diagnosis, no forecasts."""
import math
import time
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
WINDOWS=((2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1))


def main():
    assert not (HERE/'assessment.json').exists()
    started=time.perf_counter();pins={}
    def read(p):
        pins[str(p)]=h.sha(p)
        return h.read(p)
    prior=read(h.R/'transition150/replay/protocol.json')
    data=read(h.R/'lane_interaction110/frames.json.gz')
    previous=read(h.R/'exit_sending131/attempt2/results.json')
    bounds=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    left,right=bounds[20:22];length=right-left
    assert data['bounds_m'][20:22]==bounds[20:22]
    key='NEXTLINK\\NO'
    h.save(HERE/'protocol.json',dict(previous_goal_turn='PROGRESS:154 rejected gap connection and155 corrected-physics joint calibration verified.',
        hypothesis='The hard instantaneous speed feedback affects the whole20 exit lane while real queued/moving states may be spatially separated within that lane.',
        comparisons=['Exactly reconstruct148 cap and test local+1km/h pre-cap increment at the same frozen state, not a rollout.',
                     'Native current20lane1/exit-destination states in four fixed equal spatial quarters; distinguish queues from moving inventory.'],
        windows=WINDOWS,stop_threshold_kmh=5.,quarter_lengths_m=length/4,
        evidence_reused=['Claude P_PLANT FIFO issue','135 removing cap alone failed','131 native Nv/L comparison','143/119 cell19 spatial diagnosis','150 exact speed and flow trace','155 bounded joint recalibration'],
        limits=['5s endpoint samples, not exact stop durations or microscopic causal classification.',
                'Current NEXTLINK identifies intended exit, not cause of stopping; no retrospective destination labels.',
                'Positive speed increment probe is an algebraic frozen-state test, not a feasible actuator or independent causal contribution.',
                'Future native states are diagnostic labels only, never rollout/controller inputs.'],
        budget=dict(native=0,FZP=0,forecasts=0,fits=0),protected_sha256=prior['protected_sha256'],STOP=prior['STOP']))
    native=[];caps=[];cap_steps=[];partitions=[]
    for arm in ('release','release_vsl90'):
        frames={round(f['t'],6):f['rows'] for f in data['cases'][arm]['frames']}
        ss=read(h.R/'transition150/replay'/f'corrected148_{arm}_speed.json.gz')
        tt=read(h.R/'transition150/replay'/f'corrected148_{arm}_trace.json.gz')
        speeds={round(s['time_s'],6):s for s in ss if s['cell']==20 and s['lane']==1}
        for f in tt:
            s=speeds[round(f['time_s'],6)];active=s['exit_cap'] is not None
            assert abs(s['off_request']-f['off_request'])<1e-9
            assert abs(s['off_sent']-f['accepted_off'])<1e-9
            assert f['storage_reduction']==0
            expected=max(s['v_min'],min(s['post_merge'],s['exit_cap'])) if active else max(s['v_min'],s['post_merge'])
            assert abs(expected-s['final_speed'])<1e-8
            if active:
                assert f['off_request']>0
                assert abs(s['exit_cap']-s['old_speed']*f['accepted_off']/f['off_request'])<1e-8
            probe=max(s['v_min'],min(s['post_merge']+1,s['exit_cap'])) if active else max(s['v_min'],s['post_merge']+1)
            cap_steps.append(dict(arm=arm,t=s['time_s'],active=active,binding=s['post_merge']>s['post_exit_raw']+1e-9,
                floor=s['final_speed']<=s['v_min']+1e-9,masked=abs(probe-s['final_speed'])<1e-9,
                nominal_acceleration=s['post_merge']-s['old_speed'],delta_before_cap=s['post_merge']-s['old_speed'],
                delta_after_cap=s['final_speed']-s['old_speed'],old_speed=s['old_speed'],final_speed=s['final_speed'],
                cap=s['exit_cap'],off_request=f['off_request'],accepted_off=f['accepted_off'],
                receiving_reduction=f['reciprocal_reduction']))
        for lo,hi in WINDOWS:
            seq=[f for t,f in sorted(frames.items()) if lo-1e-6<=t<hi-1e-6]
            assert len(seq)==round((hi-lo)/5)
            current=[]
            for quarter in range(4):
                counts=[];exits=[];stops=[];exitstops=[];vel=[];exitvel=[]
                for frame in seq:
                    rows=[]
                    for v in frame.values():
                        if v['cell']!=20 or v['lane']!=1:continue
                        x=data['offsets_m'][str(v['link'])]+v['pos']
                        assert left-.02<=x<=right+.02
                        p=min(3,max(0,int(4*(x-left)/length)))
                        if p==quarter:rows.append(v)
                    ex=[v for v in rows if v[key]=='10483']
                    counts.append(len(rows));exits.append(len(ex))
                    stops.append(sum(v['speed']<5 for v in rows));exitstops.append(sum(v['speed']<5 for v in ex))
                    vel += [v['speed'] for v in rows];exitvel += [v['speed'] for v in ex]
                item=dict(arm=arm,lo=lo,hi=hi,quarter=quarter,mean_n=sum(counts)/len(seq),mean_exit_n=sum(exits)/len(seq),
                    mean_stopped=sum(stops)/len(seq),mean_stopped_exit=sum(exitstops)/len(seq),
                    vehicle_weighted_speed=sum(vel)/len(vel) if vel else None,exit_weighted_speed=sum(exitvel)/len(exitvel) if exitvel else None,
                    n_samples=len(vel),exit_samples=len(exitvel),n_speed_sum=sum(vel),exit_speed_sum=sum(exitvel))
                native.append(item);current.append(item)
            lane_rows=[[v for v in frame.values() if v['cell']==20 and v['lane']==1] for frame in seq]
            total_n=sum(len(r) for r in lane_rows)/len(seq)
            total_stop=sum(sum(v['speed']<5 for v in r) for r in lane_rows)/len(seq)
            assert abs(sum(x['mean_n'] for x in current)-total_n)<1e-9
            assert abs(sum(x['mean_stopped'] for x in current)-total_stop)<1e-9
            partitions.append(dict(arm=arm,lo=lo,hi=hi,mean_n=total_n,mean_stopped=total_stop,
                stopped_tail_quarter_share=current[-1]['mean_stopped']/total_stop if total_stop else None,
                tail_stock_share=current[-1]['mean_n']/total_n if total_n else None,
                lower_half_stopped_share=sum(x['mean_stopped'] for x in current[2:])/total_stop if total_stop else None))
            rows=[r for r in cap_steps if r['arm']==arm and lo+1e-6<r['t']<=hi+1e-6]
            assert len(rows)==round(hi-lo)
            caps.append(dict(arm=arm,lo=lo,hi=hi,seconds=len(rows),active_seconds=sum(r['active'] for r in rows),
                binding_seconds=sum(r['binding'] for r in rows),floor_seconds=sum(r['floor'] for r in rows),
                masked_positive_increment_seconds=sum(r['masked'] for r in rows),
                positive_pre_cap_but_nonpositive_after_seconds=sum(r['delta_before_cap']>1e-9 and r['delta_after_cap']<=1e-9 for r in rows),
                requested=sum(r['off_request'] for r in rows),accepted=sum(r['accepted_off'] for r in rows)))
    for p,digest in {**pins,**prior['protected_sha256']}.items():assert h.sha(p)==digest,p
    assert h.sha(prior['STOP']['path'])==prior['STOP']['sha256']
    h.save(HERE/'native_quarters.json',native);h.save(HERE/'cap_steps.json',cap_steps)
    h.save(HERE/'assessment.json',dict(status='complete_cached_diagnostic',caps=caps,spatial_partitions=partitions,
        assertions=dict(speed_cap_identities=900,quarter_stock_checks=6,quarter_stop_checks=6,off_storage_never_limited=True),
        elapsed_sec=time.perf_counter()-started,source_inputs_preserved=True,production_adopted=False,goal_complete=False,
        remaining='Spatial separation alone does not establish VSL causal benefit or justify a new split. Compare observed spatial influence with scalar feedback before a physical proposal.'))
    h.save(HERE/'pins.json',pins)
    print('CAPS',caps)
    print('SPATIAL',partitions)
    for row in native:
        if row['lo']==2820.1:print(row)


if __name__=='__main__':main()
