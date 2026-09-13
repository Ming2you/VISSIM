"""Prepare only native NC inputs; no controller/model/COM imports or execution.

Routing weights come from --network (prepared INPX). Optional demand override
CSV columns: input_no,start_sec,volume_vph (absolute final per-interval demand).
--global-scale multiplies all final values after profile and absolute overrides.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'diagnostics/fixed_beta300v3_network_arms_flat_v1/baseline.inpx'
ROLES = ROOT / 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv'
PROFILE = ROOT / 'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv'
ACTION = ROOT / 'evaluation/runs/codex_contract_nc_headoff_continuous_s13_5400_v3_20260910/decisions_codex_contract_nc_headoff_continuous_s13_5400_v3_20260910/action_000001.csv'


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def number(value):
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ValueError('Expected finite nonnegative value')
    return out


def demand_rows(network, overrides=(), global_scale=1.0):
    scale = number(global_scale)
    if scale <= 0:
        raise ValueError('global_scale must be positive')
    native = ET.parse(network).getroot()
    starts = [number(n.attrib['start']) for n in native.findall("./timeIntervalSets/timeIntervalSet[@no='VEHICLEINPUT']/timeInts/timeInterval")]
    if starts != [0, 900, 1800, 2700, 3600, 4500]:
        raise ValueError('Expected the original six vehicle-input intervals')
    roles = {r['no']: r['role'].lower() for r in read_csv(ROLES)}
    factors = {r['role'].lower(): number(r['multiplier']) for r in read_csv(PROFILE)}
    extra = {}
    for row in overrides:
        key = (int(row['input_no']), number(row['start_sec']))
        if key in extra:
            raise ValueError('Duplicate demand override')
        extra[key] = number(row['volume_vph'])
    rows = []
    for vi in native.findall('./vehicleInputs/vehicleInput'):
        no = vi.attrib['no']
        if no not in roles:
            raise ValueError('Unknown input role: ' + no)
        factor = factors.get('no:' + no, factors.get(roles[no], factors.get('__default__', 1.0)))
        for v in vi.findall('./timeIntVehVols/timeIntervalVehVolume'):
            group, ticks = v.attrib['timeInt'].split()
            start = number(ticks) / 1000
            if group != '1' or start not in starts:
                raise ValueError('Unexpected native interval key')
            before = number(v.attrib['volume'])
            target = number(extra.pop((int(no), start), before * factor) * scale)
            rows.append({'input_no': int(no), 'time_int': f'1-{starts.index(start)+1}',
                         'start_sec': int(start), 'before_vph': before, 'volume_vph': target})
    if extra or len(rows) != 204 or len({(r['input_no'],r['time_int']) for r in rows}) != 204:
        raise ValueError('Unmatched override or incomplete 204-input interval schedule')
    return rows


def controls(path=ACTION):
    rows = read_csv(path)
    dsds = [int(r['dsd_no']) for r in rows if r['kind'] == 'vsl' and number(r['speed_kph']) == 120]
    meters = [int(r['sc_no']) for r in rows if r['kind'] == 'ramp_meter'
              and number(r['green_sec']) == 10 and number(r['rate_vph']) == 900]
    if len(rows) != 74 or len(dsds) != 66 or len(set(dsds)) != 66 or sorted(meters) != list(range(9101,9109)):
        raise ValueError('Expected original 66 VSL120 + 8 all-GREEN meter commands')
    return [{'kind':'vsl','no':n} for n in dsds] + [{'kind':'meter','no':n} for n in meters]


def route_checks(network):
    node=ET.parse(network).find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1130']")
    if node is None: raise ValueError('Expected native decision1130')
    rows=[]
    for r in node.findall('./vehRoutSta/vehicleRouteStatic'):
        first=r.attrib['relFlow'].split()[0]
        # Native encoding is "2 0:value"; use the first interval value only.
        values=r.attrib['relFlow'].split()
        rows.append({'route_no':int(r.attrib['no']),'rel_flow':number(values[1].split(':')[1])})
    if sorted(r['route_no'] for r in rows)!=[1,2,3]: raise ValueError('Expected1130 routes1/2/3')
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--network', type=Path, default=BASE)
    p.add_argument('--demand-overrides', type=Path)
    p.add_argument('--global-scale', type=float, default=1.0)
    p.add_argument('--terminal-sec', type=int, choices=(5400, 7200, 9000), default=5400,
                   help='Extend the final native input interval without adding/resetting routing or input intervals')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    network = a.network.resolve(strict=True)
    demand = demand_rows(network, read_csv(a.demand_overrides) if a.demand_overrides else (), a.global_scale)
    command = controls()
    routes = route_checks(network)
    a.output.mkdir(parents=True, exist_ok=False)
    for name, rows in (('demand.csv',demand),('controls.csv',command),('route_checks.csv',routes)):
        with (a.output/name).open('x',encoding='ascii',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    inputs = [network, ROLES, PROFILE, ACTION] + ([a.demand_overrides.resolve()] if a.demand_overrides else [])
    report={'network':str(network),'seed':13,'terminal_sec':a.terminal_sec,'demand_rows':204,'global_scale':a.global_scale,
            'command_rows':74,'model_controller_used':False,'routing':'Native prepared INPX, unchanged by runner',
            'inputs':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs},
            'initial_step':f'Native RunSingleStep to1, then same74 commands, then RunContinuous once to{a.terminal_sec}',
            'tail_demand':'Hold final native interval starting4500 through terminal; no new input/route interval'}
    (a.output/'prepared.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'prepared':str(a.output.resolve()),'network':str(network),'demand_rows':204,'command_rows':74}))


if __name__ == '__main__':
    main()
