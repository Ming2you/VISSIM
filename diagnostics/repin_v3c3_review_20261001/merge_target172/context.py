"""Matched-time state and receiving geometry context for completed172."""
from diagnostics.repin_v3c3_review_20261001.merge_target172 import check as c


def main():
    assert not (c.HERE/'context.json').exists()
    c.pin(c.Path(__file__))
    base = c.read(c.HERE/'results.json')
    protocol = c.read(c.HERE/'protocol.json')
    c.read(c.HERE/'verification.json')
    merge_x = protocol['geometry']['10639']['x_m']
    blocks = []
    witnesses = []
    for arm in ('release', 'release_vsl90'):
        d = c.read(c.F/f'flow67/{arm}_frames.json.gz')
        frames = {round(float(t), 6): {str(vid):dict(zip(d['fields'], v)) for vid,v in rows.items()}
                  for t,rows in d['frames'].items()}
        pred = c.read(c.R/f'prehead_storage171/forecast/state/s67_late_{arm}.json.gz')
        cells = {round(x['time_s'], 6):x for x in pred['cells'] if x['road']=='FW_E' and x['cell']==10}
        folder = c.I/f'heldout67_freeway_20260930/observations/{arm}'
        ports = c.csvrows(folder/'ports_30s.csv')
        cohorts = c.read(folder/'port_cohorts_30s.json')
        events = c.csvrows(folder/'port_events.csv')
        from_ramp = {e['vehicle'] for e in events if e['connector']=='10639' and e['kind']=='departure'}
        exits = {e['vehicle']:float(e['time_s']) for e in events if e['connector']=='10682' and e['kind']=='arrival'}
        for lo,hi in c.WINDOWS:
            pairs = []
            for t,p in sorted(cells.items()):
                if not lo < t <= hi+1e-6:continue
                vals = [x for x in frames[t].values() if x['cell']==10]
                lane = [x for x in vals if x['lane']==1]
                pairs.append(dict(time=t,native_n=len(vals),native_v=c.mean(x['speed_kmh'] for x in vals),
                    native_lane1_n=len(lane),native_lane1_v=c.mean(x['speed_kmh'] for x in lane),
                    predicted_n=p['n_veh'],predicted_v=p['v_kmh']))
            assert len(pairs)==5
            rows = [x for x in ports if x['connector']=='10682' and lo<float(x['window_end_s'])<=hi+1e-6]
            post = [x for x in pred['ports'] if x['connector']=='10682' and lo<x['time_s']<=hi+1e-6]
            assert len(rows)==5 and len(post)==150
            native = {k:sum(float(x[k]) for x in rows) for k in ['arrivals_veh','departures_veh','unresolved_absences_veh']}
            native['end_n_veh']=float(rows[-1]['end_n_veh'])
            native['max_30s_n_veh']=max(float(x['end_n_veh']) for x in rows)
            native['stopped_snapshot_max']=max(sum(v[1]<5 for v in cohorts[str(round(float(x['window_end_s']),1))]['10682']) for x in rows)
            assert native['unresolved_absences_veh']==0
            assert abs(float(rows[0]['start_n_veh'])+native['arrivals_veh']-native['departures_veh']-native['end_n_veh'])<1e-8
            sample_count = upstream = downstream = future_exit = total = ramp_stops = 0
            for t,fr in sorted(frames.items()):
                if not lo <= t < hi-1e-6:continue
                sample_count+=1
                stopped=[(vid,x) for vid,x in fr.items() if x['lane']==1 and x['cell']==10 and x['speed_kmh']<5]
                for vid,x in stopped:
                    total+=1;upstream+=x['x_m']<merge_x;downstream+=x['x_m']>=merge_x
                    future_exit+=exits.get(vid,-1)>t;ramp_stops+=vid in from_ramp
                if stopped:
                    vid,x=max(stopped,key=lambda z:z[1]['x_m'])
                    witnesses.append(dict(arm=arm,time=t,vehicle=vid,x_m=x['x_m'],speed_kmh=x['speed_kmh'],
                         position_from_merge_m=x['x_m']-merge_x,previously_on10639=vid in from_ramp,
                         observed_future10682_exit=exits.get(vid,-1)>t))
            blocks.append(dict(arm=arm,start=lo,end=hi,matched_30s_pairs=pairs,
                matched_mean={k:c.mean(p[k] for p in pairs) for k in pairs[0] if k!='time'},
                off10682_native=native,off10682_prediction=dict(arrivals_veh=sum(x['admitted_veh'] for x in post),
                    departures_veh=sum(x['departed_veh'] for x in post),end_n_veh=post[-1]['n_veh']),
                lane1_stopped_vehicle_samples=dict(total=total,before_merge=upstream,after_merge=downstream,
                    eventually10682=future_exit,previously10639=ramp_stops,samples=sample_count)))
    for p,digest in {**c.PINS,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():
        assert c.sha(p)==digest,p
    c.save('context.json',dict(blocks=blocks,frontmost_stopped_samples=witnesses,input_sha256=c.PINS,
         limitations='Stopped counts are vehicle-samples, not unique vehicles or causal blockers. Five-second snapshots and30s port stock cannot exclude transient subinterval blockage. Future exits are retrospective and right-censored; no new forecast or fit.',
         protected_and_STOP_preserved=True))
    for b in blocks:
        print(b['arm'],b['start'],b['matched_mean'],b['off10682_native'],b['lane1_stopped_vehicle_samples'])


if __name__=='__main__':main()
