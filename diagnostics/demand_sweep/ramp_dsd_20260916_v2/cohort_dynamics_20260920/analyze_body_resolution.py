"""Closed-file coordinate/step diagnostic, not control gain qualification."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import lateral_body_observation as a

K, e = a.K, a.e
BASE = K / 'body_geometry_native_v1'


def polygon(row, width):
    fx, fy, rx, ry = row['front_x'], row['front_y'], row['rear_x'], row['rear_y']
    dx, dy = fx-rx, fy-ry
    length = math.hypot(dx, dy)
    if length <= 0:
        raise ValueError('Zero recorded body axis')
    nx, ny = -dy/length*width/2, dx/length*width/2
    return [(fx+nx, fy+ny), (fx-nx, fy-ny), (rx-nx, ry-ny), (rx+nx, ry+ny)]


def overlap(first, second):
    """Strict convex rectangle intersection, no position correction."""
    margins = []
    for p in (first, second):
        for i in (0, 1):
            x, y = p[i+1][0]-p[i][0], p[i+1][1]-p[i][1]
            norm = math.hypot(x,y); axis = (-y/norm, x/norm)
            pa = [x*axis[0]+y*axis[1] for x,y in first]
            pb = [x*axis[0]+y*axis[1] for x,y in second]
            margins.append(min(max(pa), max(pb))-max(min(pa), min(pb)))
    return min(margins)


def rows(path):
    with path.open('rb') as stream:
        for line in stream:
            if line[:1].isdigit():
                yield line.rstrip(b'\r\n').split(b';')


def digest_prefix(path):
    digest = hashlib.sha256(); count = 0; end = None
    for fields in rows(path):
        digest.update(b';'.join(fields[:20])+b'\n'); count += 1; end = float(fields[0])
    return dict(rows=count, end_s=end, original20_sha256=digest.hexdigest())


def analyze(resolution, run_name='run', partial_cutoff=None):
    folder = BASE/f'none_s23_res{resolution}'
    run_dir = folder/run_name
    run = e.load(run_dir/'run.json')
    if partial_cutoff is None:
        assert run['completed'] and run['exit_code']==0 and not run['owned_native_alive']
        validation=e.load(run_dir/'fixed_validation.json');assert validation['passed']
    else:
        failure=e.load(run_dir/'terminal_failure_confirmed.json')
        assert failure['owned_processes_terminal'] and failure['reason']=='disk_full'
        assert resolution==10 and 0<partial_cutoff<1501
    path=run_dir/'vissim_eval/baseline_001.fzp'
    stamp=(path.stat().st_size,path.stat().st_mtime_ns)
    geo=a.geometry(a.d.H/'source_dsd/baseline.inpx')
    frames={};series=[];overlaps=[];history={};current={};last_time=None
    wanted={t for start in a.STARTS for t in range(start-10,start+31)}
    digest=hashlib.sha256();count=0;closed_prefix=False

    def consume(t, frame):
        counts=Counter(vehicles=len(frame),slow_vehicles=sum(r['v']<40 for r in frame.values()))
        counts['speed_sum']=sum(r['v'] for r in frame.values())
        for lane in (1,2,3):
            ordered=sorted((r for r in frame.values() if r['lane']==lane),key=lambda r:r['pos'])
            for back,front in zip(ordered,ordered[1:]):
                counts['adjacent_pairs']+=1
                if back['v']<40 and front['v']<40:counts['slow_adjacent_pairs']+=1
                gap=front['pos']-front['length']-back['pos']
                if gap>=0:continue
                margin=overlap(polygon(back,geo['vehicle_width_by_length'][round(back['length'],3)]),
                               polygon(front,geo['vehicle_width_by_length'][round(front['length'],3)]))
                stable=all(len(history.get(r['vehicle'],[]))>=3 and
                    all(h['lane']==lane and h['lane_change']=='None' and h['poslat']==.5
                        for h in history[r['vehicle']][-3:]) and r['lane_change']=='None' and r['poslat']==.5
                    for r in (back,front))
                counts['projected_overlap_pairs']+=1
                counts['projected_gap_below_minus1']+=gap < -1
                counts['oriented_rectangle_intersections']+=margin>0
                counts['three_prior_seconds_centered_no_lanechange']+=stable
                overlaps.append(dict(t=t,lane=lane,gap_m=gap,rectangle_margin_m=margin,
                    centered_stable_prior3=stable,back=back,front=front,
                    previous_back=history.get(back['vehicle'],[])[-3:],previous_front=history.get(front['vehicle'],[])[-3:]))
        series.append(dict(t=t,**counts))
        if math.floor(t) in wanted:frames[t]=frame
        for vid,row in frame.items():history[vid]=(history.get(vid,[])+[row])[-3:]
        for vid in set(history)-set(frame):del history[vid]

    for f in rows(path):
        t=float(f[0])
        if partial_cutoff is not None and t>partial_cutoff+1e-8:
            closed_prefix=True;break
        digest.update(b';'.join(f[:20])+b'\n');count+=1
        if last_time is not None and t!=last_time:
            assert abs(t-last_time-1)<1e-8, 'Expected a one-second recording interval'
            consume(int(last_time) if last_time.is_integer() else last_time,current);current={}
        last_time=t
        if int(f[2])!=24:continue
        vid=int(f[1]);assert vid not in current
        current[vid]=dict(vehicle=vid,lane=int(f[3]),pos=float(f[4]),poslat=float(f[5]),v=float(f[6]),
            length=float(f[10]),destination_lane=int(f[15]) if f[15] else None,lane_change=f[16].decode(),
            target_type=f[18].decode(),target=int(f[19]) if f[19] else None,
            front_x=float(f[20]),front_y=float(f[21]),rear_x=float(f[22]),rear_y=float(f[23]),accel=float(f[24]))
    consume(int(last_time) if last_time.is_integer() else last_time,current)
    assert stamp==(path.stat().st_size,path.stat().st_mtime_ns)
    if partial_cutoff is None:
        assert 2999<=last_time<=3000 and len(series) in (2999,3000)
    else:
        assert closed_prefix and abs(last_time-partial_cutoff)<1e-8
    totals={}
    for lo,hi in ((0,900),(900,1800),(1800,2400),(2400,2700),(2700,3001)):
        counts=Counter()
        for row in series:
            if lo<=row['t']<hi:counts.update({k:v for k,v in row.items() if k!='t'})
        totals[f'{lo}_{hi}']=dict(counts)
    suffix='' if partial_cutoff is None else '_prefix'+str(partial_cutoff).replace('.','p')
    output=BASE/f'analysis_res{resolution}{suffix}';output.mkdir(exist_ok=False)
    e.save(output/'frames.json',frames);e.save(output/'series.json',series);e.save(output/'overlaps.json',overlaps)
    proof=dict(qualified=False,production_adopted=False,resolution=resolution,seed=23,
        terminal_s=3000 if partial_cutoff is None else None,requested_terminal_s=3000,
        source_receipt=dict(path=path.relative_to(a.d.ROOT).as_posix(),bytes=stamp[0],mtime_ns=stamp[1]),
        prefix=dict(rows=count,end_s=last_time,original20_sha256=digest.hexdigest()),totals=totals,
        native_validation_passed=partial_cutoff is None,stored_frames=len(frames),new_control_commands=0,run_name=run_name,
        failed_run_prefix_only=partial_cutoff is not None,partial_cutoff=partial_cutoff,closed_prefix=closed_prefix,
        sampling=dict(interval_s=1,first_s=series[0]['t'],last_s=series[-1]['t'],frames=len(series),
                      phase_s=round(series[0]['t']%1,8),times_rounded_or_interpolated=False),
        limits=['Same seed at different internal resolution is not an identical initial-state pair.',
                'Oriented rectangles use recorded front/rear centers and nominal model width; not a native collision flag.',
                'Resolution changes require new calibration/benefit evaluation, not baseline relabeling.'],
        source_pins={p.relative_to(a.d.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (Path(__file__),folder/'profile.json',folder/'protocol.json',run_dir/'readback.csv')})
    e.save(output/'result.json',proof)
    print(json.dumps(dict(resolution=resolution,totals=totals)))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--resolution',type=int,choices=(1,10));ap.add_argument('--reference-prefix',action='store_true')
    ap.add_argument('--run-name',choices=('run','run_retry1'),default='run')
    ap.add_argument('--partial-cutoff',type=float,default=None);args=ap.parse_args()
    if args.reference_prefix:
        result=digest_prefix(K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp')
        e.save(BASE/'reference_original20_prefix.json',result);print(json.dumps(result))
    else:
        if args.resolution is None:ap.error('Select a resolution')
        analyze(args.resolution,args.run_name,args.partial_cutoff)
