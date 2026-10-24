"""Small post-run ramp table from existing 150s FZP aggregates; no COM/model calls."""
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
MAPPING = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
ramps = json.loads(MAPPING.read_text(encoding='utf-8'))['ramp_meters']
rows = []
pins = {str(MAPPING.relative_to(ROOT)): hashlib.sha256(MAPPING.read_bytes()).hexdigest()}
for run in ('nc', 'cl'):
    folder = BASE / 'native_windows' / run
    linkfile = folder / 'links_150s.csv'
    pairfile = folder / 'observed_link_pairs_150s.csv'
    for path in (linkfile, pairfile):
        pins[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with linkfile.open(newline='', encoding='utf-8-sig') as stream:
        links = {(int(r['start_sec']), r['link']): r for r in csv.DictReader(stream)}
    with pairfile.open(newline='', encoding='utf-8-sig') as stream:
        pairs = {(int(r['start_sec']), r['from_link'], r['to_link']): int(r['vehicles']) for r in csv.DictReader(stream)}
    for ramp in ramps:
        connector = str(ramp['connector'])
        approach = str(ramp['from_link'])
        mainline = str(ramp['to_link'])
        for start in range(1800, 3300, 150):
            source = links.get((start, approach), {})
            meter = links.get((start, connector), {})
            rows.append({
                'run': run, 'start_sec': start, 'end_sec': start+150,
                'meter': ramp['id'], 'direction': ramp['to_model_link'],
                'merge_cell_index': ramp['to_model_segment_index'],
                'approach_link': approach, 'connector': connector, 'mainline_link': mainline,
                'connector_start_n': int(meter.get('start_n', 0)),
                'connector_end_n': int(meter.get('end_n', 0)),
                'connector_ttt_veh_h': float(meter.get('ttt_veh_h', 0)),
                'connector_stopped_veh_h': float(meter.get('stopped_veh_h', 0)),
                'connector_all_observed_entries': int(meter.get('entry_events', 0)),
                'observed_approach_to_connector': pairs.get((start, approach, connector), 0),
                'observed_connector_to_mainline': pairs.get((start, connector, mainline), 0),
                'approach_all_destinations_start_n': int(source.get('start_n', 0)),
                'approach_all_destinations_end_n': int(source.get('end_n', 0)),
                'approach_all_destinations_stopped_veh_h': float(source.get('stopped_veh_h', 0)),
            })
out = BASE / 'native_ramps_1800_3300.csv'
with out.open('w', newline='', encoding='utf-8') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
(BASE / 'native_ramps_1800_3300.provenance.json').write_text(json.dumps({
    'source_sha256': pins,
    'output_sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'rows': len(rows),
    'scope': 'Observed 1s FZP link pairs and 150s residence. Short connectors can be skipped between observations; these are not complete desired-demand or validated total merge counts. Approach counts include all destinations and must not be called ramp queues. No route-demand inference. Connector occupancy is all vehicles, not necessarily stopped.',
}, ensure_ascii=False, indent=2), encoding='utf-8')
for row in rows:
    if row['run'] == 'cl' and row['meter'] in ('RM_C10639', 'RM_C10681', 'RM_C10490') and row['start_sec'] in (2250, 2400, 2550):
        print(json.dumps(row))
