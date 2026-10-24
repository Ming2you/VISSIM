"""Bounded retrospective lane-blockage check; no simulation or model changes.

Read only the 2670.1--3120.1 window of four completed seed67 experiments.
Stopped/queued fronts are observation proxies, never asserted causal blockers.
"""
import bisect
import collections
import csv
import gzip
import hashlib
import json
import math
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
F = I / 'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
CASE = I / 'heldout67_freeway_20260930'
ARMS = ('hold', 'release', 'hold_vsl90', 'release_vsl90')
START, END = 2670.1, 3120.1
FIELDS = ['cell', 'speed', 'x', 'lane', 'link', 'pos', 'length', 'nextlink',
          'lnchg', 'destlane', 'interaction', 'target_type', 'target', 'accel']
PINS = {}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    PINS[str(p)] = sha(p)
    with (gzip.open(p, 'rt', encoding='utf-8') if p.suffix == '.gz' else p.open(encoding='utf-8-sig')) as f:
        return json.load(f)


def rows(p):
    PINS[str(p)] = sha(p)
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(name, d):
    p = HERE / name
    with (gzip.open(p, 'wt', encoding='utf-8') if p.suffix == '.gz' else p.open('w', encoding='utf-8')) as f:
        json.dump(d, f, ensure_ascii=False, indent=None if p.suffix == '.gz' else 2, allow_nan=False)


def mean(xs):
    return math.fsum(xs) / len(xs) if xs else None


def seek_time(f, start, body_start, size):
    # Ordered native FZP: find a byte strictly before the first requested frame.
    low, high = body_start, size
    while high - low > 65536:
        mid = (low + high) // 2
        f.seek(mid); f.readline()
        line = f.readline()
        t = float(line.split(b';', 1)[0]) if line else math.inf
        if t < start - 1e-6:
            low = mid
        else:
            high = mid
    f.seek(low)
    if low != body_start:
        f.readline()
    return f.tell()


def extract(arm, offsets, bounds):
    fs = list((Path('D:/VISSIM_runs/20260930_release2670_s67') / arm / 'run/vissim_eval').glob('*.fzp'))
    assert len(fs) == 1
    p = fs[0]; stat = p.stat(); frames = {}; window_hash = hashlib.sha256(); count = 0
    with p.open('rb') as f:
        for line in f:
            if line.startswith(b'$VEHICLE:'):
                names = line.split(b':', 1)[1].strip().decode().split(';')
                ci = {n: j for j, n in enumerate(names)}
                body = f.tell(); break
        else:
            raise AssertionError('Missing native header')
        begin = seek_time(f, START, body, stat.st_size)
        previous = -math.inf
        for line in f:
            z = line.rstrip(b'\r\n').split(b';')
            t = float(z[ci['SIMSEC']]); assert t >= previous; previous = t
            if t < START - 1e-6: continue
            if t > END + 1e-6: break
            window_hash.update(line); count += 1
            link = int(z[ci['LANE\\LINK\\NO']])
            if link not in offsets: continue
            x = offsets[link] + float(z[ci['POS']])
            cell = max(0, min(30, bisect.bisect_right(bounds, x) - 1))
            vid = z[ci['NO']].decode(); t = round(t, 6)
            frame = frames.setdefault(t, {})
            assert vid not in frame
            dec = lambda key: z[ci[key]].decode()
            frame[vid] = [cell, float(dec('SPEED')), x, int(dec('LANE\\INDEX')), link,
                float(dec('POS')), float(dec('LENGTH')), dec('NEXTLINK\\NO'), dec('LNCHG'),
                dec('DESTLANE'), dec('INTERACTSTATE'), dec('INTERACTTARGTYPE'),
                dec('INTERACTTARGNO'), float(dec('ACCELERATION'))]
        read_end = f.tell()
    assert p.stat().st_size == stat.st_size and p.stat().st_mtime_ns == stat.st_mtime_ns
    assert sorted(frames) == [round(START + 5 * j, 6) for j in range(91)]
    checks = 0
    for row in rows(CASE / f'observations/{arm}/cells_30s.csv'):
        t = round(float(row['time_s']), 6)
        if row['road'] != 'FW_E' or t not in frames: continue
        vals = [v for v in frames[t].values() if v[0] == int(row['cell'])]
        assert len(vals) == int(float(row['n_veh']))
        # Existing native table uses1km/h; this diagnosis also reports slow5.
        assert sum(v[1] <= 1 for v in vals) == int(float(row['stopped_veh'])), (arm,t,row['cell'])
        if vals: assert abs(mean([v[1] for v in vals]) - float(row['v_kmh'])) < 1e-8
        checks += 1
    assert checks == 16 * 31
    source = dict(path=str(p), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns,
        read_byte_start=begin, read_byte_end=read_end, window_sha256=window_hash.hexdigest(),
        all_network_window_rows=count, mainline_rows=sum(map(len, frames.values())),
        frames=len(frames), native30s_count_speed_stop_checks=checks)
    save(arm + '_frames.json.gz', dict(fields=FIELDS, frames=frames, source=source))
    return frames, source


def longest_run(flags):
    longest = cur = 0
    for flag in flags:
        cur = cur + 1 if flag else 0
        longest = max(longest, cur)
    return longest * 5


def main():
    assert not (HERE / 'summary.json').exists(), 'Do not overwrite completed analysis'
    started = time.perf_counter()
    geometry = read(F / 'route_inventory/mapping31.json')['freeway_model_links']['FW_E']
    offsets = dict(zip(geometry['chain_links'], geometry['chain_offsets_m']))
    bounds = geometry['segment_bounds_m']
    previous = read(R / 'merge_target172/protocol.json')
    protected = {p: sha(p) for p in previous['protected_sha256']}
    stop = previous['STOP']; assert sha(stop['path']) == stop['sha256']
    pin_native = read(CASE / 'native_summary.json'); assert pin_native['common_prefix_exact']
    read(R / 'merge_split175/gain_ledger.json')
    PINS[str(Path(__file__))] = sha(__file__)
    frames = {}; sources = {}
    for arm in ARMS:
        frames[arm], sources[arm] = extract(arm, offsets, bounds)
        print('EXTRACTED', arm, sources[arm]['mainline_rows'], flush=True)
    for arm in ARMS[1:]:
        for t in frames['hold']:
            if t < 2700:
                assert frames[arm][t] == frames['hold'][t]
    blocks = [(START, END), (START, 2820.1), (2820.1, 2970.1), (2970.1, END)]
    cellrows = []; lanes = []; fronts = []; witnesses = []; flows = []; provenance = []
    for arm in ARMS:
        fr = frames[arm]
        events = rows(CASE / f'observations/{arm}/port_events.csv')
        merges = collections.defaultdict(list)
        exits = collections.defaultdict(list)
        for e in events:
            if e['connector'] in ['10639','10681','10490','10484'] and e['kind'] == 'departure':
                merges[e['vehicle']].append((float(e['time_s']), e['connector']))
            if e['connector'] in ['10643','10682','10481','10483'] and e['kind'] == 'arrival':
                exits[e['vehicle']].append((float(e['time_s']), e['connector']))
        nativeflows = rows(CASE / f'observations/{arm}/flows_30s.csv')
        ports = rows(CASE / f'observations/{arm}/ports_30s.csv')
        for lo, hi in blocks:
            times = [t for t in sorted(fr) if lo - 1e-6 <= t < hi - 1e-6]
            assert len(times) == round((hi-lo)/5)
            for cell in range(8, 26):
                allvals = [[(vid,v) for vid,v in fr[t].items() if v[0] == cell] for t in times]
                stopped = sum(v[1] < 5 for vs in allvals for _,v in vs)
                cellrows.append(dict(arm=arm,lo=lo,hi=hi,cell=cell,
                    mean_stopped=stopped/len(times),stopped_veh_s=stopped*5,
                    mean_n=sum(map(len,allvals))/len(times)))
                for lane in range(1, max((v[3] for vs in allvals for _,v in vs), default=0)+1):
                    vals = [[(vid,v) for vid,v in vs if v[3] == lane] for vs in allvals]
                    stops = [sum(v[1] < 5 for _,v in vs) for vs in vals]
                    total = sum(map(len, vals)); unique = {vid for vs in vals for vid,v in vs if v[1] < 5}
                    lanes.append(dict(arm=arm,lo=lo,hi=hi,cell=cell,lane=lane,
                        mean_n=total/len(times),mean_stopped=sum(stops)/len(times),
                        strict1_mean_stopped=sum(v[1]<=1 for vs in vals for _,v in vs)/len(times),
                        stopped_fraction=sum(stops)/total if total else None,
                        stopped_veh_s=sum(stops)*5,unique_stopped=len(unique),
                        any_stop_sample_s=sum(n>0 for n in stops)*5,
                        multiple_stop_sample_s=sum(n>=2 for n in stops)*5,
                        longest_any_stop_sample_s=longest_run([n>0 for n in stops])))
            for cell in (10,20):
                counters=collections.Counter(); deltas=[]; patterns=[]; origin=collections.Counter()
                for t in times:
                    allsame = [(vid,v) for vid,v in fr[t].items() if v[3] == 1]
                    local = [(vid,v) for vid,v in allsame if v[0] == cell]
                    stopped = [(vid,v) for vid,v in local if v[1] < 5]
                    for vid,v in stopped:
                        counters['stopped_samples'] += 1
                        counters['next_exit_'+v[7]] += 1
                        counters['interaction_'+v[10]] += 1
                        counters['lanechange_'+v[8]] += 1
                        previously_merged = any(t0 <= t for t0,_ in merges.get(vid, []))
                        later_exit = any(t0 > t for t0,_ in exits.get(vid, []))
                        origin[f'merged_{previously_merged}_laterexit_{later_exit}'] += 1
                    if not stopped: patterns.append(False); continue
                    vid,head = max(stopped,key=lambda q:q[1][2])
                    # Physical link equality avoids lane-index changes at a connector.
                    up = [(i,v) for i,v in allsame if v[4]==head[4] and 0<head[2]-v[2]<=100]
                    dn = [(i,v) for i,v in allsame if v[4]==head[4] and 0<v[2]-head[2]<=100]
                    vu=mean([v[1] for _,v in up]); vd=mean([v[1] for _,v in dn])
                    flag = len(up)>=2 and vu<20 and vd is not None and vd>=30
                    patterns.append(flag)
                    if flag:
                        counters['slow_up_fast_down_frames'] += 1; deltas.append(vd-vu)
                    if flag and lo==START and hi==END:
                        target=fr[t].get(head[12]); following=[(j,v) for j,v in up if v[11]=='Vehicle' and v[12]==vid]
                        witnesses.append(dict(arm=arm,time=t,cell=cell,head_id=vid,head=dict(zip(FIELDS,head)),
                            upstream_n=len(up),upstream_speed=vu,downstream_n=len(dn),downstream_speed=vd,
                            nearest_downstream_gap_m=min(v[2]-head[2]-v[6] for _,v in dn),
                            direct_interaction_followers=[dict(vehicle=j,speed=v[1],x=v[2],state=v[10]) for j,v in following],
                            target=dict(zip(FIELDS,target)) if target else None))
                fronts.append(dict(arm=arm,lo=lo,hi=hi,cell=cell,lane=1,counts=dict(counters),
                    slow_up_fast_down_sample_s=sum(patterns)*5,
                    longest_pattern_sample_s=longest_run(patterns),mean_speed_difference=mean(deltas)))
                provenance.append(dict(arm=arm,lo=lo,hi=hi,cell=cell,stopped_origin_samples=dict(origin)))
            for cell in (10,11,17,19,20,21,23,25):
                rs=[x for x in nativeflows if x['road']=='FW_E' and int(x['cell'])==cell and lo<float(x['window_end_s'])<=hi+1e-6]
                assert len(rs)==round((hi-lo)/30)
                totals={k:sum(float(x[k]) for x in rs) for k in ['downstream_crossings','ramp_merges','off_departures','native_removals','unexplained_losses']}
                totals.update(arm=arm,lo=lo,hi=hi,cell=cell,kind='mainline')
                flows.append(totals)
            for cid in ('10639','10681','10490','10484','10682','10483'):
                rs=[x for x in ports if x['connector']==cid and lo<float(x['window_end_s'])<=hi+1e-6]
                flows.append(dict(arm=arm,lo=lo,hi=hi,connector=cid,kind='port',
                    arrivals=sum(float(x['arrivals_veh']) for x in rs),departures=sum(float(x['departures_veh']) for x in rs),
                    start_n=float(rs[0]['start_n_veh']),end_n=float(rs[-1]['end_n_veh']),
                    mean_n=mean([float(x['end_n_veh']) for x in rs])))
    assert all(sha(p)==v for p,v in PINS.items())
    assert all(sha(p)==v for p,v in protected.items()) and sha(stop['path'])==stop['sha256']
    save('summary.json',dict(scope='Seed67 same-initial four policies2670.1..3120.1;RM hold vs legal release,not RM vsNC.',
        cell_rows=cellrows,lane_rows=lanes,fronts=fronts,flows=flows,provenance=provenance,
        source=sources,input_sha256=PINS,protected_sha256=protected,STOP=stop,
        limitations=['Five-second sample exposure is not exact stop duration. Threshold5km/h; lane blocked is not inferred from one stopped vehicle.',
          'Up/down diagnostic is within100m, same physical link/lane, upstream>=2vehicles mean<20, downstreammean>=30.',
          'A vehicle interaction target supports following, not its original reason for stopping.',
          'Retrospective merge/exit events identify provenance/destination,not cause; future labels are censored.',
          'Already congested at2670;experiment tests worsening/relief,not prevention from free flow. Seed67 already inspected,not blind.',
          'Realized admissions can differ after interventions; no mediation fraction or wholeOmega qualification.'],
        elapsed_s=time.perf_counter()-started,new_native=0,new_forecasts=0,production_changes=0,
        read_windows=4,full9000_analysis=0,common_preintervention_six_frames_exact=True,native30s_checks=1984))
    save('witnesses.json',witnesses)
    print('DONE',len(witnesses),'witnesses',time.perf_counter()-started,flush=True)


if __name__ == '__main__':
    main()
