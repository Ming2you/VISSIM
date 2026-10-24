"""Independent cached checks and limits of the proposed blockage mechanism."""
import collections
import gzip
import json
import math
from pathlib import Path
from analyze import HERE, R, F, CASE, ARMS, START, END, read, rows, save, sha, mean, PINS


def main():
    assert not (HERE/'verification.json').exists()
    s = read(HERE/'summary.json')
    raw = {a: read(HERE/f'{a}_frames.json.gz')['frames'] for a in ARMS}
    frames = {a:{float(t):fr for t,fr in data.items()} for a,data in raw.items()}
    cached_equal = 0
    for a in ['release','release_vsl90']:
        old=read(F/f'flow67/{a}_frames.json.gz')['frames']
        for t,fr in old.items():
            assert set(fr)==set(raw[a][t])
            for vid,v in fr.items():
                now=raw[a][t][vid]
                assert all(abs(x-y)<1e-8 for x,y in zip(v[:4],now[:4]))
                assert abs(v[4]-now[13])<1e-8
                cached_equal+=1
        old_source=read(F/f'flow67/{a}_source.json')
        # Prior hash normalizes CRLF to LF; current receipt hashes original bytes.
        # Compare content above and source identity/count, not unlike hash formats.
        assert s['source'][a]['bytes']==old_source['bytes']
        assert s['source'][a]['mtime_ns']==old_source['mtime_ns']
        assert s['source'][a]['all_network_window_rows']==old_source['window_rows']
    partition_checks=0
    for c in s['cell_rows']:
        ls=[v for v in s['lane_rows'] if all(v[k]==c[k] for k in ['arm','lo','hi','cell'])]
        assert abs(sum(x['mean_n'] for x in ls)-c['mean_n'])<1e-9
        assert abs(sum(x['stopped_veh_s'] for x in ls)-c['stopped_veh_s'])<1e-9
        partition_checks+=1
    sparse=[]; sparse_counts=[]; onset=[]; model=[]; totals=[]
    for a in ARMS:
        counters=collections.Counter()
        for t,fr in frames[a].items():
            if t>=END: continue
            for vid,v in fr.items():
                if v[0] not in [10,11,19,20,21,22,23] or v[1]>1:continue
                same=[(j,b) for j,b in fr.items() if b[4]==v[4] and b[3]==v[3] and b[2]>v[2]]
                counters['strict_stop_samples']+=1
                if not same:
                    counters['no_same_link_downstream_vehicle']+=1;continue
                j,b=min(same,key=lambda p:p[1][2]);gap=b[2]-v[2]-b[6]
                if gap<15:continue
                counters['gap15_samples']+=1
                followers=[(j,b) for j,b in fr.items() if b[4]==v[4] and b[3]==v[3] and
                           0<v[2]-b[2]<40 and b[11]=='Vehicle' and b[12]==vid]
                counters['gap15_with_direct_follower']+=bool(followers)
                sparse.append(dict(arm=a,time=t,vehicle=vid,cell=v[0],lane=v[3],speed=v[1],gap_m=gap,
                    nextlink=v[7],interaction=v[10],target_type=v[11],target_id=v[12],
                    target_in_mainline_cache=v[12] in fr,followers=[dict(vehicle=j,speed=b[1],accel=b[13]) for j,b in followers]))
        sparse_counts.append(dict(arm=a,**counters))
        for c in [10,14,15,16,17,18,19,20,21,22,23]:
            times=[t for t in sorted(frames[a]) if 2730.1<=t<END]
            seq=[sum(v[1]<5 for v in frames[a][t].values() if v[0]==c and v[3]==1)>=2 for t in times]
            run=0;first=None
            for t,b in zip(times,seq):
                run=run+1 if b else 0
                if run==3:first=t-10;break
            onset.append(dict(arm=a,cell=c,first_three_consecutive_low_speed_frames_after2730=first))
        pred=read(R/f'merge_split175/forecast/unsplit173/s67_late_{a}.json.gz')
        for c in [10,11,14,15,16,17,19,20,21,23,24,25]:
            pairs=[]
            for p in pred['cells']:
                if p['road']!='FW_E' or p['cell']!=c:continue
                t=round(p['time_s'],6)
                if not START<t<=END:continue
                vv=[v for v in frames[a][t].values() if v[0]==c]
                pairs.append(dict(t=t,n=len(vv),v=mean([v[1] for v in vv]),pn=p['n_veh'],pv=p['v_kmh']))
            assert len(pairs)==15
            model.append(dict(arm=a,cell=c,native_n=mean([p['n'] for p in pairs]),model_n=mean([p['pn'] for p in pairs]),
                native_n_weighted_speed=sum(p['n']*p['v'] for p in pairs)/sum(p['n'] for p in pairs),
                model_n_weighted_speed=sum(p['pn']*p['pv'] for p in pairs)/sum(p['pn'] for p in pairs)))
        fl=rows(CASE/f'observations/{a}/flows_30s.csv')
        selected=[v for v in fl if v['road']=='FW_E' and START<float(v['window_end_s'])<=END+1e-6]
        assert len(selected)==31*15
        for row in selected:
            assert abs(float(row['conservation_residual_veh']))<1e-9
        totals.append(dict(arm=a,source_admissions=sum(float(v['source_admissions']) for v in selected),
            mainline_removals=sum(float(v['native_removals']) for v in selected),
            unresolved_losses=sum(float(v['unexplained_losses']) for v in selected),
            merges=sum(float(v['ramp_merges']) for v in selected),
            offramp=sum(float(v['off_departures']) for v in selected)))
    # Same command history except the predeclared East ramp/VSL interventions.
    commands={a:read(CASE/f'{a}_commands.json') for a in ARMS}
    east={'RM_C10639','RM_C10681','RM_C10490','RM_C10484'}
    for a in ARMS[1:]:
        for t,v in commands['hold'].items():
            if float(t)>END:continue
            other=commands[a][t]
            if float(t)<2700:assert v==other
            for key in v['greens']:
                if key not in east:assert v['greens'][key]==other['greens'][key]
            for key in v['vsl']:
                if key not in ['63','64','65','66']:assert v['vsl'][key]==other['vsl'][key]
    save('mechanism_context.json',dict(sparse_stop_counts=sparse_counts,sparse_stop_witnesses=sparse,
        sampled_rebreakdown=onset,saved_model_comparison=model,native_boundary_totals=totals,
        cautions=['15m same-link space is an explicit diagnostic threshold,not a validated blocking detector.',
          'Missing downstream vehicle/target is unknown,not empty road. Lane-change overlap can invalidate a simple headway.',
          'First3 consecutive samples means sampled persistence,not exact onset/duration.2730 start omits common initial congestion.',
          'Model comparison uses saved173 with lane cells10--11;it is not a new or production prediction.']))
    assert all(sha(p)==v for p,v in PINS.items())
    assert all(sha(p)==v for p,v in s['protected_sha256'].items())
    assert sha(s['STOP']['path'])==s['STOP']['sha256']
    save('verification.json',dict(completed=True,old_release_cache_vehicle_rows_exact=cached_equal,
        two_prior_window_counts_and_source_metadata_exact=True,lane_cell_partition_checks=partition_checks,
        native30s_count_speed_strictstop_checks=s['native30s_checks'],mainline_mass_intervals=1860,
        command_other_values_unchanged=True,protected_and_STOP_unchanged=True,input_sha256=PINS,
        raw_extraction_failures_preserved=['run.log','run_native_threshold.log'],
        extraction_failure_reason='Verifier initially used<5 then<1 against historical<=1 stopped column; native rows/model never changed.',
        first_verify_failure='verify.log preserves comparison of normalizedLF historical hash to rawCRLF hash; repaired by exact cache-content/count/source-metadata checks, no raw rescan.',
        new_native=0,new_predictions=0,adoption=False))
    print('VERIFIED',cached_equal,partition_checks)
    print('TOTALS',totals)
    print('SPARSE',sparse_counts)
    print('ONSETS',[(v['arm'],v['cell'],v['first_three_consecutive_low_speed_frames_after2730']) for v in onset])


if __name__=='__main__':main()
