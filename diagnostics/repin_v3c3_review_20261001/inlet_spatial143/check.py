"""Current-state sending versus observed crossings; completed caches only.

This is an information diagnostic, not a rollout or a fitted sending law.
"""
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE.parent
U = R.parents[1]
F = U / 'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2), encoding='utf-8')


def main():
    started = time.perf_counter()
    assert not (HERE / 'completion.json').exists(), 'Completed diagnosis must not rerun'
    protected = read(R / 'inlet_class_speed142/protocol.json')
    pins = dict(protected['protected_sha256'])
    pins[protected['STOP']['path']] = protected['STOP']['sha256']
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in pins.items())
    mapping = read(F / 'route_inventory/mapping31.json')
    assert mapping['network']['sha256'] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    bounds = mapping['freeway_model_links']['FW_E']['segment_bounds_m']
    save('protocol.json', dict(previous_goal_turn='NO_PROGRESS: explained completed results only.',
        question='Does current measured lane N*v/L explain the upstream18 boundary during queue formation, as it explained off20 in131?',
        budget=dict(new_forecasts=0, new_native=0, new_FZP=0, fits=0),
        prior_checked=['Claude REVIEW_CHECK', '131 measured exit request', '140 initial lane balance',
                       '141/142 initial shares rejected', '119 equal-speed two-bin sending rejected',
                       'lane_joint67 future joint inlet alone failed'],
        windows=[[2670.1,2700.1],[2700.1,2820.1],[2820.1,2970.1],[2970.1,3120.1]],
        scope='seed67 RM release and release+VSL90; physical cells18 and19; known inspected data',
        protected_sha256=pins,
        limitation='Future frames are evaluation only. Observed departure-lane attribution is ambiguous when a lane change also occurs within5s. Half-cell diagnostic does not implement autonomous separate speeds.'))
    rows = []
    intervals = []
    for arm in ('release', 'release_vsl90'):
        data = read(F / 'flow67' / f'{arm}_frames.json.gz')
        assert data['fields'][:4] == ['cell','speed_kmh','x_m','lane']
        frames = data['frames']
        for begin, end in ((2670.1,2700.1),(2700.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            steps = int(round((end-begin)/5))
            for cell in (18,19):
                start, stop = bounds[cell:cell+2]
                length = stop-start
                for lane in ((2,3,4) if cell == 18 else (1,2,3)):
                    part = []
                    for k in range(steps):
                        t = round(begin+5*k,1)
                        a, b = frames[str(t)], frames[str(round(t+5,1))]
                        sa = {i:x for i,x in a.items() if x[0] == cell and x[3] == lane}
                        sb = {i:x for i,x in b.items() if x[0] == cell and x[3] == lane}
                        assert all(start-1e-3 <= x[2] <= stop+1e-3 for x in list(sa.values())+list(sb.values()))
                        arriving, leaving = set(sb)-set(sa), set(sa)-set(sb)
                        incoming = {i for i in arriving if i in a and a[i][0] < cell}
                        outgoing = {i for i in leaving if i in b and b[i][0] > cell}
                        other_in, other_out = arriving-incoming, leaving-outgoing
                        unknown = [i for i in arriving if i not in a] + [i for i in leaving if i not in b]
                        # No ramps, exits or missing observations on these retained through lanes.
                        assert not unknown, (arm, t, cell, lane, unknown)
                        assert all(a[i][0] == cell for i in other_in)
                        assert all(b[i][0] == cell for i in other_out)
                        norm = lambda x: (x[2]-start)/length
                        m0, m1 = sum(norm(x) for x in sa.values()), sum(norm(x) for x in sb.values())
                        stayed_motion = sum(norm(sb[i])-norm(sa[i]) for i in set(sa)&set(sb))
                        # Endpoint identity. These are NOT continuously observed travel distances:
                        # lateral crossings have unknown within-interval position and ordering.
                        longitudinal_motion_proxy = (stayed_motion + sum(norm(sb[i]) for i in incoming)
                                                     + sum(1-norm(sa[i]) for i in outgoing))
                        lateral_moment = sum(norm(sb[i]) for i in other_in)-sum(norm(sa[i]) for i in other_out)
                        residual = longitudinal_motion_proxy+lateral_moment-(m1-m0)-len(outgoing)
                        assert abs(residual) < 1e-10
                        count_residual = len(sb)-len(sa)-len(incoming)+len(outgoing)-len(other_in)+len(other_out)
                        assert count_residual == 0
                        q0 = sum(x[1] for x in sa.values())*5/(3.6*length)
                        q1 = sum(x[1] for x in sb.values())*5/(3.6*length)
                        half = []
                        for j in (0,1):
                            ha = [x for x in sa.values() if int(x[2]>=start+length/2)==j]
                            hb = [x for x in sb.values() if int(x[2]>=start+length/2)==j]
                            half.append(dict(n=len(ha),nv=sum(x[1] for x in ha),
                                sending_left=sum(x[1] for x in ha)*5/(3.6*length/2),
                                sending_trapezoid=(sum(x[1] for x in ha)+sum(x[1] for x in hb))*2.5/(3.6*length/2)))
                        ambiguous = []
                        for i in outgoing:
                            expected = lane-1 if cell == 18 else lane
                            if b[i][0] != cell+1 or b[i][3] != expected:
                                ambiguous.append(dict(vehicle=i,before=sa[i],after=b[i]))
                        z = dict(arm=arm,begin=begin,end=end,time_s=t,cell=cell,lane=lane,n0=len(sa),n1=len(sb),
                            incoming=len(incoming),outgoing=len(outgoing),lateral_net=len(other_in)-len(other_out),
                            request_left=q0,request_trapezoid=(q0+q1)/2,halves=half,
                            position_m0=m0,position_m1=m1,endpoint_motion_proxy=longitudinal_motion_proxy,
                            lateral_position_moment=lateral_moment,position_identity_residual=residual,
                            departure_lane_ambiguities=ambiguous)
                        part.append(z)
                    initial, final = part[0], part[-1]
                    row = dict(arm=arm,begin=begin,end=end,cell=cell,lane=lane,length_m=length,
                        n0=initial['n0'],n1=final['n1'],position_delta=final['position_m1']-initial['position_m0'])
                    for key in ('incoming','outgoing','lateral_net','request_left','request_trapezoid','endpoint_motion_proxy','lateral_position_moment'):
                        row[key] = sum(x[key] for x in part)
                    row['half_stats'] = []
                    for j in (0,1):
                        h = [x['halves'][j] for x in part]
                        n = sum(x['n'] for x in h)
                        row['half_stats'].append(dict(mean_n=n/steps,vehicle_weighted_speed=sum(x['nv'] for x in h)/n if n else None,
                            request_left=sum(x['sending_left'] for x in h),request_trapezoid=sum(x['sending_trapezoid'] for x in h)))
                    row['departure_lane_ambiguity_count'] = sum(len(x['departure_lane_ambiguities']) for x in part)
                    assert abs(row['endpoint_motion_proxy']+row['lateral_position_moment']-row['position_delta']-row['outgoing']) < 1e-9
                    rows.append(row)
                    intervals.extend(part)
    for p,h in PINS.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p,h in pins.items())
    save('assessment.json',dict(rows=rows,interval_count=len(intervals),
        max_position_identity_residual=max(abs(x['position_identity_residual']) for x in intervals),input_sha256=PINS,
        interpretation='Current-state conditional sending only; not an autonomous benefit result. No formula fitted to boundary labels.'))
    (HERE/'intervals.json.gz').write_bytes(gzip.compress(json.dumps(intervals).encode()))
    save('completion.json',dict(status='COMPLETE_INFORMATION_DIAGNOSTIC',previous_goal_turn='NO_PROGRESS',current_goal_turn='PROGRESS',
        goal_complete=False,production_adopted=False,elapsed_sec=time.perf_counter()-started,
        input_sha256=PINS,protected_sha256=pins,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        new_native=0,new_FZP=0,new_forecasts=0,fits=0,push=0))
    for x in rows:
        if x['lane'] == (2 if x['cell']==18 else 1):
            print({k:x[k] for k in ('arm','begin','end','cell','lane','n0','n1','outgoing','request_left','request_trapezoid','position_delta','endpoint_motion_proxy','lateral_position_moment')})


if __name__ == '__main__':
    main()
