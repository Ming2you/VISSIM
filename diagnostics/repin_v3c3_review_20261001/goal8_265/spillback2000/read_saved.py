"""Bounded read-only diagnosis of the existing 2000s congestion episode."""
import bisect
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}
def read(p):
    raw = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
geo = read(I / 'selected/port_gain/geometry.json')
chain = {x['link']:x for x in geo['chains']['FW_E']}
times = list(range(1500, 2701, 150))
runs = {
    'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc/decisions_sdmpc31_nc9000_s29'),
    'sdmpc': Path('D:/VISSIM_runs/20261007_goal8_head47right_verified_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29'),
}
def stat(records):
    stopped = [r for r in records if r['stopped']]
    return dict(n=len(records), stopped=len(stopped),
                mean_speed=sum(r['speed_kph'] for r in records)/len(records) if records else None,
                stopped_positions_m=[r['position_m'] for r in stopped])
rows=[]; decisions=[]; detector_maps={}
for arm, folder in runs.items():
    for t in times:
        s=read(folder / f'state_{t:06d}.json')
        vr=s['vehicle_records']; records=vr['records']
        assert vr['complete'] and vr['unobservable_count']==0
        assert s['sim_sec']==vr['capture_sim_sec_before']==vr['capture_sim_sec_after']==t
        assert len(records)==len({r['veh_no'] for r in records})==vr['record_count']
        cells=defaultdict(list); lanes=defaultdict(list); links=defaultdict(list)
        for r in records:
            link=r['link_no']; links[link].append(r); lanes[(link,r['lane_no'])].append(r)
            if link in chain:
                x=chain[link]['offset_m']+r['position_m']
                c=min(30,bisect.bisect_right(geo['bounds']['FW_E'],x)-1)
                cells[c].append(r)
        config_path=s['obs150']['detector_config']['path']
        if config_path not in detector_maps:
            raw=Path(config_path).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==s['obs150']['detector_config']['sha256']
            detector_maps[config_path]=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
        flows=defaultdict(int)
        for d in detector_maps[config_path]:
            if d['ref'] in ('10481','10483','10490','10484') or (d['role']=='meter_head' and d['link'] in ('10490','10484')):
                key=f"{d['role']}:{d['ref']}"
                flows[key]+=s['obs150']['detectors'][d['dcm_no']]
        sig=s['obs150']['signal_log']
        ramp_events=[e for e in sig['events'] if e[1] in ('9107','9108')]
        rows.append(dict(arm=arm,t=t,
            measured_150s_detector_counts=dict(flows),
            signal_log_complete=sig['complete'],
            ramp_event_types=sorted({e[3] for e in ramp_events}),
            ramp_written_red_events=sum(e[3]=='write' and e[4]=='RED' for e in ramp_events),
            cells={str(c):stat(cells[c]) for c in range(16,26)},
            ports={str(l):stat(links[l]) for l in (10481,10483,10480,10490,10484,10639,10681,10643,10682)},
            city_lanes={f'{l}:{lane}':stat(lanes[l,lane]) for l in (124,127,40,47,68) for lane in range(1,5)}))
        if arm=='sdmpc':
            p=folder/f'action_{t:06d}.csv'
            data=list(csv.DictReader(p.read_text(encoding='utf-8-sig').splitlines()))
            progress=[json.loads(line) for line in (folder/f'action_{t:06d}.joint.progress.jsonl').read_text().splitlines()]
            audits=[a for a in progress if a['stage']=='sdmpc_meter_neighbors_done']
            audit=audits[-1] if audits else {}
            decisions.append(dict(t=t,
                rm={r['id']:float(r['green_sec']) for r in data if r['kind']=='ramp_meter'},
                vsl=sorted({(r['id'],float(r['speed_kph'])) for r in data if r['kind']=='vsl'}),
                rm_neighbor_selected=audit.get('selected'),
                model_deltas=[{k:r.get(k) for k in ('candidate','delta_veh_h','feasible')} for r in audit.get('candidates',[])],
                joint_written=read(folder/f'action_{t:06d}.joint_written.json')['written_command_binding_passed']))
result=dict(scope='Saved 150-second observations and command/progress files only; no FZP, COM, new rollout, or live modification',
            time_sec=times, rows=rows,decisions=decisions,source_pins=PINS,
            limitations=['Instantaneous stopped counts do not identify vehicle destination or the cause of a stop.',
                         'Command files and applied receipts do not replace native LDP verification.',
                         'No earlier-metering counterfactual was simulated.'])
(HERE/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for r in rows:
    print(json.dumps(dict(arm=r['arm'],t=r['t'],
        v18_25=[round(r['cells'][str(c)]['mean_speed'] or 0,1) for c in range(18,26)],
        stop18_25=[r['cells'][str(c)]['stopped'] for c in range(18,26)],
        off_stopped={l:r['ports'][l]['stopped'] for l in ('10481','10483')},
        city124lane1=r['city_lanes']['124:1'], measured_flows=r['measured_150s_detector_counts']),ensure_ascii=False))
for r in decisions:
    print(json.dumps(dict(t=r['t'],rm=r['rm'],neighbor_selected=r['rm_neighbor_selected'],
        east_neighbors=[v for v in r['model_deltas'] if v['candidate'].startswith(('RM_C10490','RM_C10484','FW_E'))]),ensure_ascii=False))
