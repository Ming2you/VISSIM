"""Read existing receipts only; no forecast, calibration, FZP scan or native run."""
import ast
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
ROOT = REVIEW.parents[1]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def model(trace):
    local = trace['local_receiver_diagnostics']
    start = int(trace['start_sec'])
    geometry = local['states'][0]['geometry']
    last = len(geometry['edges']['126']) - 2
    blocks = [defaultdict(Counter) for _ in range(3)]
    for r in local['resources']:
        if r['kind'] != 'lane_urban_receiving':
            continue
        road, lane, cell = ast.literal_eval(r['resource'])
        b = int((r['start_sec'] - start) // 150)
        if road == 126 and cell == last:
            a = blocks[b][f'join_lane{lane}']
            a['steps'] += 1
            a['receiving_sum'] += r['available_veh']
            a['used_sum'] += r['accepted_total_veh']
            off = other = 0.
            for name, n in r['accepted_by_source_veh'].items():
                source = ast.literal_eval(name)
                if source == ('external', f'off:{lane-1}'):
                    off += n
                elif source == (126, lane, last-1):
                    a['upstream_accepted'] += n
                    other += n
                else:
                    a['other_accepted'] += n
                    other += n
            a['off_accepted'] += off
            a['both_served_steps'] += int(off > 1e-8 and other > 1e-8)
            a['low_room_steps'] += int(r['available_veh'] < .1 * geometry['capacity_rate'])
            a['unused_room_sum'] += max(0., r['available_veh'] - r['accepted_total_veh'])
        if road == 126 and cell == 0:
            for name, n in r['accepted_by_source_veh'].items():
                if ast.literal_eval(name)[0] == 'external':
                    blocks[b]['upstream_input'][f'lane{lane}'] += n
        if road == 10641 and cell == 0:
            blocks[b]['merge_downstream'][f'lane{lane}'] += r['accepted_by_source_veh'].get(str((126,lane,last)), 0.)
    ports = trace['offramp_network_diagnostics']['states']
    result = []
    for b, a in enumerate(blocks):
        before, after = [p['ports']['10643'] for p in ports[b:b+2]]
        entry = after['admitted'] - before['admitted']
        drain = after['departed'] - before['departed']
        assert abs(before['stock'] + entry - drain - after['stock']) < 1e-8
        assert all(a[f'join_lane{l}']['steps'] == 150 for l in (1,2))
        assert abs(sum(a[f'join_lane{l}']['off_accepted'] for l in (1,2)) - drain) < 1e-8
        result.append(dict(start=start+150*b,end=start+150*(b+1),
            entry=entry,drain=drain,stock_end=after['stock'],resources=dict(a)))
    return dict(geometry=geometry,blocks=result)


def native(cache, cohorts, geometry, endpoint_stocks):
    rows = cache['rows']
    epochs = defaultdict(list)
    for row in rows:
        epochs[round(row[0],3)].append(row)
    assert all(t in epochs for t in (2700.1,2850.1,3000.1))
    for t in (2700,2850,3000):
        assert sum(r[2]==10643 for r in epochs[t+.1])==sum(endpoint_stocks[str(t)])
    last_start = geometry['edges']['126'][-2]
    merge = geometry['merge_position']
    blocks = [dict(pair_events=[],sampled=defaultdict(Counter)) for _ in range(3)]
    previous = {}
    downstream = {10641,71,10634,10635,10642}
    for row in rows:
        old = previous.get(row[1])
        if old is not None and 2700.1-1e-6 <= old[0] < row[0] <= 3150.1+1e-6 and row[0]-old[0] <= 5.00001:
            kinds = []
            if old[2] == 10643 and row[2] != 10643:
                kinds.append('off_departure')
            if old[2] in (70,10776) and row[2] == 126:
                kinds.append('upstream_entry_pair')
            if old[2] == 126 and old[4] < last_start and ((row[2] == 126 and row[4] >= last_start) or row[2] in downstream):
                kinds.append('upstream_final_cell_crossing')
            if old[2] == 126 and old[4] < merge and ((row[2] == 126 and row[4] >= merge) or row[2] in downstream):
                kinds.append('upstream_merge_plane_crossing')
            if old[2] == 126 and row[2] in downstream:
                kinds.append('combined_merge_outlet_pair')
            if kinds:
                b = min(2,int((row[0]-2700.100001)//150))
                blocks[b]['pair_events'].append(dict(vehicle=row[1],kinds=kinds,
                    time_bracket=[old[0],row[0]],from_link=old[2],to_link=row[2],
                    from_lane=old[3],to_lane=row[3],from_speed=old[5],to_speed=row[5]))
        previous[row[1]]=row
        if 2700.1-1e-6 <= row[0] < 3150.1-1e-6 and row[2]==126:
            b = min(2,int((row[0]-2700.1+1e-6)//150))
            key = f'lane{row[3]}'
            a = blocks[b]['sampled'][key]
            a['all_records'] += 1
            a['speed_sum_kph'] += row[5]
            a['stopped_records'] += int(row[5]<5.)
            if row[4]>=last_start:
                a['final_cell_position_records'] += 1
                a['final_cell_slow_records'] += int(row[5]<5.)
                if row[4]>=merge:
                    a['beyond_merge_position_records'] += 1
    for b, a in enumerate(blocks):
        times = [2700+150*b,2850+150*b]
        stock = [sum(endpoint_stocks[str(t)]) for t in times]
        entry = sum(2700+150*b <= e['time_sec'] < 2850+150*b for e in cohorts['witnesses'])
        a.update(start=2700+150*b,end=2850+150*b,entry=entry,
                 stock_start=stock[0],stock_end=stock[1],drain_balance=stock[0]+entry-stock[1])
        a['counts'] = dict(Counter(k for e in a['pair_events'] for k in e['kinds']))
        a['pair_last_lane_counts'] = {kind:dict(Counter(e['from_lane'] for e in a['pair_events'] if kind in e['kinds'])) for kind in a['counts']}
        for lane,v in a['sampled'].items():
            v['mean_speed_kph']=v['speed_sum_kph']/v['all_records'] if v['all_records'] else None
        a['sampled']=dict(a['sampled'])
    assert sum(a['entry'] for a in blocks)==96
    assert sum(a['drain_balance'] for a in blocks)==94
    assert sum(a['counts'].get('off_departure',0) for a in blocks)==93
    return blocks


def main():
    assert not (HERE/'assessment.json').exists()
    protocol=read(HERE/'protocol.json')
    for path,pin in protocol['production_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin,path
    manifest=read(REVIEW/'retained10638/candidate_manifest.json')
    source=manifest['sources']['network']; network=ROOT/source['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest()==source['sha256']
    PINS[str(network)]=source['sha256']
    root=ET.parse(network).getroot()
    links={int(x.get('no')):x for x in root.findall('./links/link')}
    conflicts=[dict(c.attrib) for c in root.findall('./conflictAreas/conflictArea') if {c.get('link1'),c.get('link2')}=={'126','10643'}]
    models={}
    for name,folder,key in protocol['model_receipts']:
        models[name]=model(read(I/folder/(key+'_RM_C10681_trace.json.gz')))
    geom=models['baseline_hold']['geometry']
    native_cache=read(REVIEW/'lane10643_native/rows.json.gz')
    native_rows=native(native_cache,
                       read(REVIEW/'entry10643/native_cohorts.json')['cases']['hold'],geom,
                       read(REVIEW/'frozen10643_receiver/assessment.json')['cases']['hold']['native_stock_by_lane'])
    pins=dict(PINS)
    for path,pin in protocol['production_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==pin,path
    out=dict(status='completed_receipt_audit_not_calibration',
        network_merge=dict(actual_merge_m=geom['merge_position'],model_cell_start_m=geom['edges']['126'][-2],
            actual_outlet_m=geom['edges']['126'][-1],model_join_upstream_shift_m=geom['merge_position']-geom['edges']['126'][-2],
            exact_remaining_length_m=geom['edges']['126'][-1]-geom['merge_position'],
            model_remaining_cell_length_m=geom['edges']['126'][-1]-geom['edges']['126'][-2],
            extra_free_travel_seconds=(geom['merge_position']-geom['edges']['126'][-2])/geom['speed'],conflict_areas=conflicts),
        native_hold=native_rows,native_cache_time_range=[min(r[0] for r in native_cache['rows']),max(r[0] for r in native_cache['rows'])],
        models=models,source_pins=pins,production_unchanged=True,
        full_forecasts=0,new_native=0,new_fzp_scan=0,fit=0,
        limitations=['Native event pairs bound crossings within5s and can miss skipped links; they are not exact crossing counts or exact lanes.',
          'Native per-block balance uses saved snapshot phase0.1s and existing MER entry bins; final totals verified against prior audit. Cached pair events end3145.1; final stock is from the separate saved3150 snapshot, not an empty cache.',
          'A recorded position beyond the merge is not a full vehicle footprint or proof of an empty gap.',
          'Model receiving is a reusable per-step budget, not a unique physical capacity count.',
          'PASSIVE conflict metadata alone does not identify the microscopic merging priority.',
          'All future native values are evaluation only. No candidate or coefficient is adopted.'])
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('GEOMETRY',out['network_merge'])
    for b in native_rows:print('NATIVE',b['start'],b['entry'],b['drain_balance'],b['stock_end'],b['counts'],b['sampled'])
    for name,m in models.items():
        for b in m['blocks']:print(name,b['start'],'entry/drain/stock',b['entry'],b['drain'],b['stock_end'],'join',b['resources'])


if __name__=='__main__':main()
