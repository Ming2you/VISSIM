"""Causal current/past vehicle observations for the lane-resolved plant.

The collector starts empty and follows the declared1s or5s sample clock.
Ramp-origin tags survive longer than the rolling observation window: a vehicle
queued for more than 150s must not become an upstream through vehicle. Nothing
here assigns a new route to VISSIM or accepts a future trajectory.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict, deque
import copy
import math
import hashlib
import json
from pathlib import Path


def sample_times(start, end, interval):
    """Native startup at0/1; thereafter only exact sample boundaries."""
    return sorted({s for s in (0,1) if start<=s<=end} |
                  set(range(((start+interval-1)//interval)*interval,end+1,interval)))


class LanePlantObserver:
    def __init__(self, geometry, lane_geometry, routes, *, history_sec, sample_interval_sec=1):
        if type(history_sec) is not int or history_sec <= 0:
            raise ValueError('Positive integer observation history required')
        self.geometry = copy.deepcopy(geometry)
        self.lane_geometry = copy.deepcopy(lane_geometry)
        self.routes = dict(routes)
        self.history_sec = history_sec
        if type(sample_interval_sec) is not int or sample_interval_sec not in (1,5) or history_sec%sample_interval_sec:
            raise ValueError('Declared sample interval must be1 or5 and divide observation history')
        self.sample_interval_sec=sample_interval_sec
        self.addresses = {int(k): (v[0], float(v[1])) for k, v in geometry['addresses'].items()}
        self.bounds = geometry['bounds']
        self.ramps = {int(p['connector']): p for p in geometry['boundaries'] if p['kind'] == 'ramp'}
        self.offramps = {str(p['connector']): p for p in geometry['boundaries'] if p['kind'] == 'offramp'}
        self.frames = deque(maxlen=history_sec//sample_interval_sec + (1 if sample_interval_sec==1 else 2))
        self.origins = {}
        self.previous = {}
        self.time_sec = None

    def locate(self, row):
        address = self.addresses.get(int(row[1]))
        if address is None:
            return None
        road, offset = address
        position = offset + float(row[3])
        if position < 0 or position > self.bounds[road][-1] + .01:
            raise ValueError('Vehicle lies outside observed mainline geometry')
        cell = min(len(self.bounds[road])-2, bisect_right(self.bounds[road], position)-1)
        return road, cell, position

    def group(self, road, cell, lane):
        widths = self.lane_geometry[road]['widths'][cell]
        if lane > sum(widths) + 1e-7:
            raise ValueError('Observed lane exceeds physical cell width')
        # The reference groups actual lanes1,2,3+; unsplit cells have one group.
        if len(widths) not in (1, 3):
            raise ValueError('Unsupported lane-group observation topology')
        return min(lane-1, 2) if len(widths) == 3 else 0

    def push(self, frame):
        sec = frame.get('time_s')
        if type(sec) is not int or sec < 0 or frame.get('complete') is not True:
            raise ValueError('Complete integer-second vehicle snapshot required')
        if self.time_sec is None:
            if sec != 0 or frame['vehicles']:
                raise ValueError('Observer must start from the empty native state')
        elif sec != (1 if self.time_sec==0 else (self.time_sec//self.sample_interval_sec+1)*self.sample_interval_sec):
            raise ValueError('Declared observation cadence gap')
        current = {}
        for row in frame['vehicles']:
            if not isinstance(row, (list, tuple)) or len(row) != 15:
                raise ValueError('Explicit 15-field vehicle observation required')
            vehicle, link, lane, position, speed, length = row[:6]
            if any(type(v) is not int or v <= 0 for v in (vehicle, link, lane)):
                raise ValueError('Positive vehicle/link/lane identity required')
            if any(type(v) not in (float, int) or not math.isfinite(v) or v < 0
                   for v in (position, speed, length)) or length == 0:
                raise ValueError('Invalid observed position/speed/body length')
            if vehicle in current:
                raise ValueError('Duplicate vehicle in complete snapshot')
            current[vehicle] = list(row)
        origins = {}
        for vehicle, row in current.items():
            located = self.locate(row)
            if located is None:
                continue
            old = self.previous.get(vehicle)
            ramp = self.ramps.get(old[1]) if old else None
            name = ramp['id'] if ramp else self.origins.get(vehicle)
            if name:
                definition = next(p for p in self.ramps.values() if p['id'] == name)
                if located[:2] == (definition['road'], definition['to_cell']):
                    origins[vehicle] = name
        self.origins, self.previous, self.time_sec = origins, current, sec
        self.frames.append({'time_s': sec, 'vehicles': list(current.values()), 'complete': True,
                            'ramp_origin_tags':dict(origins)})
        while self.frames and self.frames[0]['time_s'] < max(0,sec-self.history_sec):
            self.frames.popleft()

    def snapshot(self, cutoff_sec):
        if cutoff_sec != self.time_sec or [f['time_s'] for f in self.frames] != sample_times(max(0,cutoff_sec-self.history_sec),cutoff_sec,self.sample_interval_sec):
            raise ValueError('Exact current cutoff and full past history required')
        start = max(0,cutoff_sec - self.history_sec)
        exposure, exchange = Counter(), Counter()
        previous = {}
        previous_sec=start
        for frame in self.frames:
            located = {}
            for row in frame['vehicles']:
                where = self.locate(row)
                if where is None or where[0] not in self.lane_geometry:
                    continue
                road, cell, _ = where
                group = self.group(road, cell, row[2])
                located[row[0]] = (row[1], road, cell, group)
                if frame['time_s'] > start:
                    exposure[road, cell, group] += frame['time_s']-previous_sec
                    old = previous.get(row[0])
                    if old and old[:3] == located[row[0]][:3] and old[3] != group:
                        exchange[road, cell, old[3], group] += 1.
            # Match the reference estimator:150 exposures and149 transitions.
            previous = located if frame['time_s'] > start else {}
            previous_sec=frame['time_s']
        mainline, moments = [], defaultdict(list)
        for row in self.previous.values():
            where = self.locate(row)
            if where is None:
                continue
            road, cell, position = where
            if road not in self.lane_geometry:
                continue
            group = self.group(road, cell, row[2])
            moments[road, cell, group].append(row)
            mainline.append((row, road, cell, group, position))
        dynamics = {}
        for road, geometry in self.lane_geometry.items():
            spec = copy.deepcopy(geometry)
            spec.update(observation_end_s=cutoff_sec, history_start_s=start)
            spec['initial_groups'], spec['exchange_rates_per_sec'] = [], []
            for cell, widths in enumerate(spec['widths']):
                groups = []
                for group in range(len(widths)):
                    rows = moments[road, cell, group]
                    groups.append({'n_veh': float(len(rows)),
                        'v_kmh': sum(r[4] for r in rows)/len(rows) if rows else None})
                spec['initial_groups'].append(groups)
                spec['exchange_rates_per_sec'].append([
                    [exchange[road, cell, g, k]/exposure[road, cell, g]
                     if exposure[road, cell, g] else 0. for k in range(len(widths))]
                    for g in range(len(widths))])
            spec['initial_ramp_origin'] = {
                name: [float(sum(self.origins.get(row[0]) == name for row in moments[road, p['cell'], g]))
                       for g in range(len(spec['widths'][p['cell']]))]
                for name, p in spec['ramp_access'].items()}
            spec['initial_off_eligible'], spec['branch_partition_initial'] = {}, {}
            for off, p in spec['off_access'].items():
                cut = self.offramps[off]['chain_pos_m']
                rows = [(r, g, pos) for r, link, cell, g, pos in mainline
                        if link == road and cell == p['cell']]
                parts = {}
                for side in ('pre', 'post'):
                    parts[side] = []
                    for g in range(len(spec['widths'][p['cell']])):
                        selected = [r for r, group, pos in rows if group == g and (pos < cut) == (side == 'pre')]
                        fallback = spec['initial_groups'][p['cell']][g]['v_kmh']
                        parts[side].append({'n_veh': float(len(selected)),
                            'v_kmh': sum(r[4] for r in selected)/len(selected) if selected else fallback})
                spec['initial_off_eligible'][off] = [r['n_veh'] for r in parts['pre']]
                spec['branch_partition_initial'][off] = parts
            dynamics[road] = spec
        exit_labels = {}
        for road, spec in dynamics.items():
            table = {}
            for off, port in spec['off_access'].items():
                cut = self.offramps[off]['chain_pos_m']
                by_group = {}
                for cell in range(port['cell']+1):
                    for group in range(len(spec['widths'][cell])):
                        counts = dict(n=0., known_off=0., known_through=0., unknown=0.)
                        for row, link, c, g, position in mainline:
                            if (link, c, g) != (road, cell, group) or position >= cut:
                                continue
                            counts['n'] += 1.
                            path = (self.routes.get((row[6], row[7]))
                                    if isinstance(row[8], str) and row[8].lower() == 'static' else None)
                            key = 'unknown' if path is None else 'known_off' if int(off) in path else 'known_through'
                            counts[key] += 1.
                        by_group[f'{cell}:{group}'] = counts
                table[off] = by_group
            exit_labels[road] = table
        downstream, off_entries, ramp_merges = Counter(), Counter(), Counter()
        last = {r[0]:r for r in self.frames[0]['vehicles']}
        for frame in list(self.frames)[1:]:
            now = {r[0]:r for r in frame['vehicles']}
            for vehicle, row in now.items():
                prior = last.get(vehicle)
                if prior is None:
                    continue
                old, new = self.locate(prior), self.locate(row)
                if old and new and old[0] == new[0] and new[1] > old[1]:
                    for cell in range(old[1],new[1]):
                        downstream[old[0],cell] += 1.
                if old and str(row[1]) in self.offramps and row[1] != prior[1]:
                    off_entries[str(row[1])] += 1.
                if prior[1] in self.ramps and new and row[1] != prior[1]:
                    ramp_merges[self.ramps[prior[1]]['id']] += 1.
            last = now
        splits, split_evidence = {}, {}
        first_origins = Counter(self.frames[0]['ramp_origin_tags'].values())
        end_origins = Counter(self.origins.values())
        for off, p in self.offramps.items():
            road, cell = p['road'], p['from_cell']
            ramps = [r['id'] for r in self.ramps.values() if r['road'] == road
                     and r['to_cell'] == cell and r['chain_pos_m'] > p['chain_pos_m']]
            bypass = math.fsum(ramp_merges[r]+first_origins[r]-end_origins[r] for r in ramps)
            through, exiting = downstream[road,cell], off_entries[off]
            if bypass < -1e-7 or bypass > through+1e-7:
                raise ValueError('Past ramp-origin continuity contradicts downstream crossings')
            eligible = through+exiting-max(0.,bypass)
            splits[off] = exiting/eligible if eligible > 1e-7 else 0.
            split_evidence[off] = dict(downstream_veh=through,off_veh=exiting,
                post_branch_ramp_bypass_veh=bypass,eligible_exits_veh=eligible)
        result = {'schema': 'lane-plant-observation/v1', 'information_cutoff_s': cutoff_sec,
                'history_start_s': start, 'future_traffic_inputs': False,
                'lane_group_dynamics': dynamics,
                'current_exit_labels': exit_labels,
                'off_split_ratio':splits, 'off_split_history':split_evidence,
                'frames': copy.deepcopy(list(self.frames)),
                'ramp_origin_tags': dict(self.origins)}
        if self.sample_interval_sec!=1:
            result['sample_interval_sec']=self.sample_interval_sec
            result['sampling_limitations']='Only observed endpoints; intermediate lane changes and boundary passages can be missed. No synthetic1s frames.'
        return result


def load_causal_snapshot(folder, observer, cutoff_sec, *, run_id, configuration_sha256,use_checkpoint=True):
    """Resume a JSON observer checkpoint and consume only completed past frames.

    The checkpoint is an acceleration cache. Its current/history source hashes
    are rechecked; a future or differently configured checkpoint is rejected.
    No pickle or executable cache content is loaded into the native adapter.
    """
    folder = Path(folder).resolve(strict=True)
    if type(cutoff_sec) is not int or cutoff_sec < 0 or not run_id:
        raise ValueError('Complete observation history and native run identity required')
    identity = {'run_id':run_id, 'configuration_sha256':configuration_sha256,
                'history_sec':observer.history_sec}
    interval=observer.sample_interval_sec
    if interval!=1:identity['sample_interval_sec']=interval
    checkpoint = folder/'observer_checkpoint.json'
    history_pins = {}

    def read_frame(sec, expected=None):
        raw = (folder/f'frame_{sec:06d}.json').read_bytes()
        pin = hashlib.sha256(raw).hexdigest()
        if expected is not None and pin != expected:
            raise ValueError('Cached physical observation source changed')
        frame = json.loads(raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig'))
        if (frame.get('schema') != 'lane-plant-frame/v1' or frame.get('time_s') != sec
                or frame.get('run_id') != run_id or frame.get('complete') is not True
                or frame.get('sample_interval_sec',1)!=interval):
            raise ValueError('Physical observation schema/time/run identity differs')
        history_pins[str(sec)] = pin
        return frame

    if use_checkpoint and checkpoint.exists():
        cached = json.loads(checkpoint.read_text(encoding='utf-8'))
        payload = cached['payload']
        encoded = json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if (cached.get('schema') != 'lane-plant-observer-checkpoint/v1'
                or cached.get('sha256') != hashlib.sha256(encoded).hexdigest()
                or payload['identity'] != identity):
            raise ValueError('Lane observation checkpoint identity or contents differ')
        last = payload['time_s']
        if type(last) is not int or not 0 <= last <= cutoff_sec:
            raise ValueError('Lane observation checkpoint is from an invalid/future cutoff')
        if set(payload['history_sha256']) != {str(s) for s in sample_times(max(0,last-observer.history_sec),last,interval)}:
            raise ValueError('Lane checkpoint history is incomplete')
        for sec in sample_times(max(0,last-observer.history_sec),last,interval):
            raw_frame = read_frame(sec,payload['history_sha256'][str(sec)])
            frame = {k:raw_frame[k] for k in ('time_s','vehicles','complete')}
            frame['ramp_origin_tags'] = {int(k):v for k,v in payload['origin_history'][str(sec)].items()}
            observer.frames.append(frame)
        observer.previous = {r[0]:list(r) for r in observer.frames[-1]['vehicles']}
        observer.origins = {int(k):v for k,v in payload['ramp_origin_tags'].items()}
        if not set(observer.origins) <= set(observer.previous):
            raise ValueError('Lane checkpoint contains departed vehicle origin tags')
        observer.time_sec = last
        first = last+1
    else:
        first = 0
    for sec in sample_times(first,cutoff_sec,interval):
        observer.push(read_frame(sec))
    result = observer.snapshot(cutoff_sec)
    pins = {str(s):history_pins[str(s)] for s in sample_times(max(0,cutoff_sec-observer.history_sec),cutoff_sec,interval)}
    result['source'] = {**identity,'directory':str(folder),'history_sha256':pins}
    if not use_checkpoint:
        return result  # Offline replay never reads or changes the live cache.
    payload = {'identity':identity,'time_s':cutoff_sec,'ramp_origin_tags':observer.origins,
               'history_sha256':pins,
               'origin_history':{str(f['time_s']):f['ramp_origin_tags'] for f in observer.frames}}
    payload = json.loads(json.dumps(payload))  # Stable JSON keys before hashing.
    encoded = json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    saved = {'schema':'lane-plant-observer-checkpoint/v1','payload':payload,
             'sha256':hashlib.sha256(encoded).hexdigest()}
    temporary = checkpoint.with_suffix('.tmp')
    temporary.write_text(json.dumps(saved,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(checkpoint)
    return result
