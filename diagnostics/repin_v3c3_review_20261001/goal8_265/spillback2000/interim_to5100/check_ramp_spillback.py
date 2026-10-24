"""Bounded saved-snapshot diagnosis; no COM, FZP, controller or runtime changes."""
import csv
import ctypes
import ctypes.wintypes
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
G = HERE.parent.parent
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
kernel.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
summary = json.loads((HERE / 'summary.json').read_text(encoding='utf8'))
end = summary['end_sec']
pins = {}
def read(path):
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)

network_model = read(G / 'rounding_5100/network.json')
spec = network_model['physical_ramp_branches']
bounds = read(G / 'rounding_5100/bounds.json')['ramps']
geo = read(ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json')
inside = {str(k): bool(v) for k, v in []}
# Use the same canonical physical membership parser as the preceding analysis.
import sys
sys.path.insert(0, str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
inside = physical_membership_from_ledger(read(Path(summary['membership_path'])))
fw_links = {int(x['link']) for chain in geo['chains'].values() for x in chain}
on_links = {v['connector'] for v in spec['ramps'].values()}
off_links = {b['connector'] for b in geo['boundaries'] if b['kind'] == 'offramp'}
off_links = {int(x) for x in off_links}
times = [0, 1] + list(range(150, end + 1, 150))
runs = {'nc': Path('D:/VISSIM_runs/20260927_sd31_wiring9000/nc'),
        'sdmpc': Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc')}
arrays = {}; lane_rows = []; meters = {}; link_snapshot = []
for arm, run in runs.items():
    prov_path, = run.glob('run_provenance_*.json')
    prov = read(prov_path)
    name = prov_path.stem.removeprefix('run_provenance_')
    assert prov['seed'] == 29
    xml_raw = Path(prov['files']['network']['path']).read_bytes()
    assert hashlib.sha256(xml_raw).hexdigest() == spec['network']['sha256']
    xml = ET.fromstring(xml_raw)
    heads = {(int(h.get('lane').split()[0]), int(h.get('lane').split()[1])): float(h.get('pos')) for h in xml.iter('signalHead')}
    rows = list(csv.DictReader((run / f'action_{name}.csv').open(encoding='utf-8-sig')))
    meters[arm] = [dict(sim_sec=float(x['sim_sec']), ramp=x['id'], green_sec=float(x['green_sec']), readback=x['readback']) for x in rows if x['kind']=='ramp_meter' and float(x['sim_sec']) < end]
    per_link = defaultdict(lambda: np.zeros(len(times), dtype=int))
    for index, t in enumerate(times[1:], start=1):
        state = read(run / f'decisions_{name}/state_{t:06}.json')
        block = state['vehicle_records']; vehicles = block['records']
        assert state['sim_sec'] == t == block['paused_at_sim_sec']
        assert block['complete'] and block['unobservable_count'] == 0
        assert len(vehicles) == state['total_vehicles'] == block['record_count']
        count = Counter(int(v['link_no']) for v in vehicles)
        stopped = Counter(int(v['link_no']) for v in vehicles if v['stopped'])
        for link, n in count.items(): per_link[link][index] = n
        if t >= 1500 and t % 300 == 0:
            for link in [10681,68,10629,52,46,40,10490,129,127,31,10484,70,10639]:
                q = [v for v in vehicles if v['link_no']==link and v['stopped']]
                link_snapshot.append(dict(arm=arm,sim_sec=t,link=link,n=count[link],stopped=stopped[link],stop_min_pos_m=min((v['position_m'] for v in q),default=None),stop_max_pos_m=max((v['position_m'] for v in q),default=None)))
        for ramp, bound in bounds.items():
            connector = spec['ramps'][ramp]['connector']
            head = min(pos for (link, _), pos in heads.items() if link == connector)
            resolved = len(bound['lanes']) > 1
            for lane in bound['lanes']:
                v = [x for x in vehicles if x['link_no']==connector and x['position_m'] <= head and (not resolved or x['lane_no']==lane['lane'])]
                q = [x for x in v if x['stopped']]
                lane_rows.append(dict(arm=arm,sim_sec=t,ramp=ramp,lane=lane['lane'],n=len(v),stopped=len(q),capacity_veh=lane['capacity_veh'],fill=len(v)/lane['capacity_veh'],head_m=head,stop_min_pos_m=min((x['position_m'] for x in q),default=None),stop_max_pos_m=max((x['position_m'] for x in q),default=None)))
    arrays[arm] = per_link

links = sorted(set(arrays['nc']) | set(arrays['sdmpc']))
costs=[]
for link in links:
    category = ('outside' if not inside[str(link)] else 'freeway' if link in fw_links else 'onramp' if link in on_links else 'offramp' if link in off_links else 'urban_other')
    vals={a:float(np.trapezoid(arrays[a].get(link,np.zeros(len(times))),times)/3600) for a in runs}
    costs.append(dict(link=link,category=category,**vals,delta=vals['sdmpc']-vals['nc']))
categories = {category:{a:sum(x[a] for x in costs if x['category']==category) for a in ('nc','sdmpc','delta')} for category in ('freeway','onramp','offramp','urban_other','outside')}
for arm in runs:
    assert abs(sum(categories[c][arm] for c in ('onramp','offramp','urban_other'))-summary['comparison_veh_h']['Omega_other'][arm])<1e-8
result=dict(end_sec=end,categories_veh_h=categories,links=costs,ramps=lane_rows,commands=meters,selected_link_snapshots=link_snapshot,
            limitations=['Snapshot diagnosis, not a controlled RM-only counterfactual.', 'Command-time readback is not a complete native LDP transition audit.', 'Storage fill uses existing nominal guard capacities; it is not measured continuous queue length.', 'Urban approach vehicles are not all assigned to on-ramp destinations.'],source_sha256=pins)
(HERE/'ramp_spillback_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('categories',json.dumps(categories))
print('top urban/ramp losses',json.dumps(sorted([x for x in costs if x['category'] in ('onramp','offramp','urban_other')],key=lambda x:-x['delta'])[:10]))
print('10681 lane2',json.dumps([r for r in lane_rows if r['ramp']=='RM_C10681' and r['lane']==2 and r['sim_sec'] in (1800,2100,2400,2700,3000,3300,3600,3900,4200,4500,4800,5100)]))
print('10681 commands',json.dumps([r for r in meters['sdmpc'] if r['ramp']=='RM_C10681' and r['sim_sec']>=900]))
