"""Explicit current-state input contract; no development snapshot fallback."""
from pathlib import Path
import hashlib
import json

def validate(raw, frame, at):
    records = raw['vehicle_records']
    if (raw['sim_sec'] != at or frame['time_s'] != at
            or not records.get('complete') or not frame.get('complete')
            or frame.get('schema') != 'lane-plant-frame/v1'
            or any(records[k] != at for k in
                   ('paused_at_sim_sec', 'capture_sim_sec_before', 'capture_sim_sec_after'))):
        raise ValueError('Complete simultaneous current records required')
    rows = records['records']
    ids = [v['veh_no'] for v in rows]
    current = {int(v[0]): v for v in frame['vehicles']}
    if len(set(ids)) != len(ids) or len(current) != len(frame['vehicles']) or set(ids) != set(current):
        raise ValueError('Current frame and physical roster differ')
    for v in rows:
        r = current[v['veh_no']]
        if (int(r[1]) != v['link_no'] or int(r[2]) != v['lane_no']
                or abs(r[3]-v['position_m']) > 1e-8 or abs(r[4]-v['speed_kph']) > 1e-8):
            raise ValueError('Current frame geometry differs')

def load(folder, at):
    raw_path = Path(folder) / f'state_{at:06}.json'
    raw = json.loads(raw_path.read_bytes())
    spec = raw['obs150']['frames']['current']
    frame_path = raw_path.parent / spec['path']
    blob = frame_path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != spec['sha256']:
        raise ValueError('Current frame checksum differs')
    frame = json.loads(blob)
    validate(raw, frame, at)
    pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (raw_path, frame_path)}
    return raw, frame, pins

def require_past(cutoff, at):
    if at < cutoff:
        raise ValueError('Frozen support is future data for this state')
