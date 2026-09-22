"""Closed-file coordinate/step diagnostic, not control gain qualification."""
from pathlib import Path
from collections import Counter
import argparse
import bisect
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


def require_closed_native(run_dir):
    """A failed supervisor is not a failed native run, nor proof of success."""
    run=e.load(run_dir/'run.json')
    if run['completed']:
        assert run['exit_code']==0 and not run['owned_native_alive']
        return None
    recovery=e.load(run_dir/'terminal_recovery.json')
    assert recovery['failure_kind']=='watchdog_file_size_int32_overflow'
    assert recovery['native_completed'] and recovery['owned_processes_terminal'] and recovery['fixed_validation_passed']
    assert recovery['native_terminal_sec']==3000 and recovery['wrapper_exit_code']==1
    assert recovery['native_runner_exit_code'] is None
    assert set(recovery['owned_pids'])=={run['cscript_pid'],run['vissim']['pid']}
    for name,digest in recovery['proof_pins'].items():
        assert Path(name).name==name and hashlib.sha256((run_dir/name).read_bytes()).hexdigest()==digest
    text=(run_dir/'stdout.txt').read_text()
    assert 'STAGE=SIM_DONE' in text and 'SIM_SEC=3000' in text
    fp=run_dir/'vissim_eval/baseline_001.fzp';stamp=fp.stat()
    assert dict(bytes=stamp.st_size,mtime_ns=stamp.st_mtime_ns)==recovery['fzp']
    assert e.load(run_dir/'fixed_validation.json')['passed']
    return recovery


def analyze(resolution, run_name='run', partial_cutoff=None):
    folder = BASE/f'none_s23_res{resolution}'
    run_dir = folder/run_name
    run = e.load(run_dir/'run.json')
    recovery=None
    if partial_cutoff is None:
        recovery=require_closed_native(run_dir)
        validation=e.load(run_dir/'fixed_validation.json');assert validation['passed']
    else:
        failure=e.load(run_dir/'terminal_failure_confirmed.json')
        assert failure['owned_processes_terminal'] and failure['reason']=='disk_full'
        assert resolution==10 and 0<partial_cutoff<1501
    path=run_dir/'vissim_eval/baseline_001.fzp'
    stamp=(path.stat().st_size,path.stat().st_mtime_ns)
    geo=a.geometry(a.d.H/'source_dsd/baseline.inpx')
    frames={};series=[];overlaps=[];history={};current={};last_time=None
    cell_series=[]
    cell_geometry_path=K.parent/'segment_resolution_20260921/geometry_200_branch_guard.json'
    cell_geometry=e.load(cell_geometry_path)
    road_cells={c['cell']:c for c in cell_geometry['cells'] if c['road']=='FW_E'}
    offset=next(p['offset_m'] for p in cell_geometry['chains']['FW_E'] if p['link']==24)
    ends=[road_cells[i]['end_m'] for i in sorted(road_cells)]
    assert all(c['physical_pieces'][0]['link']==24 and len(c['physical_pieces'])==1 for i,c in road_cells.items() if i>=25)
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
        if 2249<=t<3000:
            groups={i:[] for i in range(25,31)}
            for row in frame.values():
                i=bisect.bisect_right(ends,offset+row['pos'])
                if i in groups:groups[i].append(row)
            for i,rs in groups.items():
                known=[(r,history[r['vehicle']][-1]) for r in rs if r['vehicle'] in history]
                cell_series.append(dict(t=t,cell=i,n=len(rs),moment=sum(r['v'] for r in rs),
                    speed_squared_sum=sum(r['v']**2 for r in rs),slow30=sum(r['v']<30 for r in rs),stop5=sum(r['v']<5 for r in rs),
                    native_acceleration_sum=sum(r['accel'] for r in rs),history_n=len(known),
                    same_vehicle_sample_speed_change_sum=sum(r['v']-before['v'] for r,before in known),
                    lanes=[dict(n=sum(r['lane']==lane for r in rs),moment=sum(r['v'] for r in rs if r['lane']==lane)) for lane in (1,2,3)]))
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
    e.save(output/'cell_series.json',cell_series)
    proof=dict(qualified=False,production_adopted=False,resolution=resolution,seed=23,native_completion_recovered=recovery is not None,
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
                     for p in (Path(__file__),folder/'profile.json',folder/'protocol.json',run_dir/'readback.csv',cell_geometry_path)})
    e.save(output/'result.json',proof)
    print(json.dumps(dict(resolution=resolution,totals=totals)))


def control_response(arm):
    """Closed native response at the actual fractional clock; no model inputs."""
    from collections import defaultdict
    from diagnostics.capture_native_runtime_errors import parse_bytes
    from diagnostics.fast_fixed_profile_verify import native_recording_grid, rows as csv_rows
    base=K/'resolution_control_v1/paired'
    run_dir=(BASE/'none_s23_res10/run_retry2' if arm=='none' else base/f'run_{arm}')
    recovery=require_closed_native(run_dir)
    receipt=e.load(run_dir/'run.json');valid=e.load(run_dir/'fixed_validation.json')
    assert valid['passed'] and receipt['seed']==23
    if arm!='none':assert valid['paired_native_signals_passed'] and valid['paired_comparison_end_sec']==2400
    grid=native_recording_grid(csv_rows(run_dir/'readback.csv'),10)
    assert tuple(map(float,grid))==(1,.1)
    geometry_path=K.parent/'segment_resolution_20260921/geometry_200_branch_guard.json'
    geo=e.load(geometry_path);chain={r['link']:r for r in geo['chains']['FW_E']};bounds=geo['bounds']['FW_E']
    ports={r['connector']:r for r in geo['boundaries'] if r['road']=='FW_E' and r['kind'] in ('ramp','offramp')}
    on={c for c,p in ports.items() if p['kind']=='ramp'};off=set(ports)-on
    error_rows=[];error_pins={}
    if recovery is None:
        error_files=receipt['error_files']
    else:
        # Original failed supervisor receipt is immutable. Use its separately
        # completed and pinned error audit, never invent receipt completion.
        audit=e.load(BASE/'full_resolution_comparison/error_audit.json')
        target=run_dir/'baseline_001.err'
        relative=str(target.relative_to(a.d.ROOT))
        assert hashlib.sha256(target.read_bytes()).hexdigest()==audit['source_pins'][relative]
        error_files=[{'name':'baseline_001.err'},{'name':'baseline.err'}]
    for r in error_files:
        path=run_dir/r['name'];parsed=parse_bytes(path.read_bytes());assert not parsed['unparsed_removal_lines']
        error_rows+=parsed['events'];error_pins[r['name']]=hashlib.sha256(path.read_bytes()).hexdigest()
    removals=defaultdict(list)
    for r in error_rows:
        if r['kind']=='lane_change_removal':removals[r['vehicle_id']].append(r)
    def located(row):
        if row is None or row[0] not in chain:return None
        x=chain[row[0]]['offset_m']+row[2]
        return (bisect.bisect_right(bounds,x)-1,x) if 0<=x<bounds[-1] else None
    previous={};priorloc={};series=[];cells=[];events=[];checks=0
    def consume(t,frame):
        nonlocal previous,priorloc,checks
        loc={vid:located(r) for vid,r in frame.items()};loc={vid:x for vid,x in loc.items() if x is not None}
        stocks={str(c):sum(r[0]==c for r in frame.values()) for c in ports}
        counts=Counter();local={c:Counter() for c in range(len(bounds)-1)}
        for vid,(cell,x) in loc.items():
            r=frame[vid];z=local[cell];z['n']+=1;z['speed_sum']+=r[3];z['slow30']+=r[3]<30;z['stop5']+=r[3]<5
            z[f'lane{r[1]}_n']+=1
            old=previous.get(vid)
            if old and old[0]==r[0] and old[1]!=r[1]:z['lane_index_changes']+=1
        if previous:
            for vid in priorloc.keys()|loc.keys():
                before,after=priorloc.get(vid),loc.get(vid);old,new=previous.get(vid),frame.get(vid)
                kind=None;sign=0
                if after and not before:
                    sign=1
                    if old and old[0] in on and new[0]==ports[old[0]]['to_link']:kind=f'merge:{old[0]}'
                    elif new[0]==74 and (old is None or (old[0]==74 and old[2]<0)):kind='source'
                    else:kind='unverified_entry'
                elif before and not after:
                    sign=-1
                    if new and new[0] in off and old[0]==ports[new[0]]['from_link']:kind=f'off_entry:{new[0]}'
                    elif any(t-1.1<=r['time_sec']<=t+.1 and int(r['link'])==old[0] for r in removals.get(vid,[])):kind='removal'
                    elif old[0]==24 and bounds[-1]-before[1]<=old[3]/3.6+11.5 and (new is None or new[0]==24):kind='terminal_inferred'
                    else:kind='unverified_loss'
                if kind:
                    counts[kind]+=sign;events.append(dict(time_s=t,vehicle=vid,kind=kind,mainline_sign=sign))
            assert len(loc)-len(priorloc)==sum(counts.values());checks+=1
            for vid,old in previous.items():
                if old[0] not in ports:continue
                new=frame.get(vid)
                if new is not None and new[0]!=old[0]:
                    kind='port_normal_departure' if new[0]==ports[old[0]]['to_link'] else 'port_other_transition'
                    events.append(dict(time_s=t,vehicle=vid,kind=kind,connector=old[0],mainline_sign=0))
                elif new is None:events.append(dict(time_s=t,vehicle=vid,kind='port_disappearance',connector=old[0],mainline_sign=0))
        series.append(dict(time_s=t,mainline=len(loc),on=sum(stocks[str(c)] for c in on),off=sum(stocks[str(c)] for c in off),ports=stocks,
                           mainline_net_changes=dict(counts),observed_network_n=len(frame)))
        cells.extend(dict(time_s=t,cell=c,**z) for c,z in local.items())
        previous,priorloc=frame,loc
    path=run_dir/'vissim_eval/baseline_001.fzp';before=path.stat();digest=hashlib.sha256();count=0;last=None;frame={};columns=None
    with path.open('rb') as stream:
        for raw in stream:
            digest.update(raw)
            if raw.startswith(b'$VEHICLE:'):
                columns=raw.strip().split(b':',1)[1].decode().split(';')
                assert len(columns)==25 and columns[:7]==['SIMSEC','NO','LANE\\LINK\\NO','LANE\\INDEX','POS','POSLAT','SPEED']
                continue
            if not raw[:1].isdigit():continue
            assert columns is not None
            count+=1;parts=raw.rstrip(b'\r\n').split(b';');assert len(parts)==25
            t=float(parts[0]);assert abs((t-.1)-round(t-.1))<1e-7
            if t<2399:continue
            assert t<=2999.1
            if last is not None and t!=last:
                assert abs(t-last-1)<1e-8;consume(last,frame);frame={}
            last=t;vid=int(parts[1]);assert vid not in frame
            frame[vid]=(int(parts[2]),int(parts[3]),float(parts[4]),float(parts[6]))
    assert last==2999.1;consume(last,frame)
    after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    assert len(series)==601 and checks==600
    windows=[]
    for lo,hi in ((2400,2550),(2550,2700),(2700,2850),(2850,3000),(2400,2850),(2400,3000)):
        ss=[r for r in series if lo<=r['time_s']<hi];assert len(ss)==hi-lo
        cs=[r for r in cells if lo<=r['time_s']<hi]
        totals={k:sum(r[k] for r in ss)/3600 for k in ('mainline','on','off')}
        flow=Counter()
        for r in ss:flow.update(r['mainline_net_changes'])
        initial=next(r for r in series if abs(r['time_s']-(lo-.9))<1e-7)['mainline']
        assert initial+sum(flow.values())==ss[-1]['mainline']
        moment=initial*len(ss)/3600+sum(sum(r['mainline_net_changes'].values())*(hi-.9-r['time_s']+1)/3600 for r in ss)
        assert abs(moment-totals['mainline'])<1e-8
        port_departures=Counter(str(r['connector']) for r in events if r['kind']=='port_normal_departure' and lo<=r['time_s']<hi)
        windows.append(dict(start=lo,end=hi,samples=len(ss),first_sample=ss[0]['time_s'],last_sample=ss[-1]['time_s'],
            component_ttt_veh_h={**totals,'total':sum(totals.values())},per_port_ttt_veh_h={str(c):sum(r['ports'][str(c)] for r in ss)/3600 for c in ports},
            signed_mainline_boundaries=dict(flow),normal_port_departures=dict(port_departures),
            mean_speed_kmh=sum(r.get('speed_sum',0) for r in cs)/sum(r.get('n',0) for r in cs),
            slow30_vehicle_s=sum(r.get('slow30',0) for r in cs),stop5_vehicle_s=sum(r.get('stop5',0) for r in cs),
            lane_index_changes=sum(r.get('lane_index_changes',0) for r in cs),initial_mainline_n=initial,final_mainline_n=ss[-1]['mainline'],
            boundary_moment_ttt_veh_h=moment))
    output=base/f'analysis_{arm}';output.mkdir(exist_ok=False)
    result=dict(arm=arm,qualified=False,native_completion_recovered=recovery is not None,windows=windows,conservation_checks=checks,whole_fzp_sha256=digest.hexdigest(),rows=count,
        fzp=dict(path=str(path),bytes=before.st_size,mtime_ns=before.st_mtime_ns),error_counts=dict(Counter(r['kind'] for r in error_rows)),
        east_removals=[r for r in error_rows if r['kind']=='lane_change_removal' and int(r['link']) in (set(chain)|set(ports))],
        errors=error_rows,error_pins=error_pins,source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),geometry_path,run_dir/'run.json',run_dir/'fixed_validation.json')},
        scope='East physical mainline + four on-ramp connectors + four off-ramp connectors; not full Omega or urban approach queues.',
        sampling='One-second sampled residence at actual .1 phase. Nominal [lo,hi) uses lo+.1..hi-.9, not exact continuous residence. Boundary moment identity uses those same samples. No timestamp rounding.',
        limits=['Terminal disappearance remains inferred and is NOT Omega TTD.','Unfinished-input warning is not a count of abnormal deletions or all uninserted vehicles before3000.','Native normal port departures require observing the declared downstream link.'])
    for name,value in [('result',result),('series',series),('cells',cells),('events',events)]:e.save(output/f'{name}.json',value)
    print(json.dumps(dict(arm=arm,windows=windows[-2:],errors=result['error_counts'],east_removals=len(result['east_removals']))))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--resolution',type=int,choices=(1,10));ap.add_argument('--reference-prefix',action='store_true')
    ap.add_argument('--run-name',choices=('run','run_retry1','run_retry2'),default='run')
    ap.add_argument('--partial-cutoff',type=float,default=None)
    ap.add_argument('--control-response',choices=('none','rm_ramp','vsl','both'));args=ap.parse_args()
    if args.control_response:
        control_response(args.control_response)
    elif args.reference_prefix:
        result=digest_prefix(K/'route_state_native_v1/none_s23/run_retry1/vissim_eval/baseline_001.fzp')
        e.save(BASE/'reference_original20_prefix.json',result);print(json.dumps(result))
    else:
        if args.resolution is None:ap.error('Select a resolution')
        analyze(args.resolution,args.run_name,args.partial_cutoff)
