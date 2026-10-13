"""Verify two saved initializations; no model/native execution."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_bytes())
plan = read(HERE / 'plan.json')
for path, digest in plan['source_pins'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
rows = []
for at, base in ((2400, 'selection2400'), (3300, 'local3300')):
    before, after = HERE.parent / base, HERE / f'init{at}'
    assert read(after / 'completion.json')['status'] == 'complete'
    a, b = [read(p / 'state.json') for p in (before, after)]
    na, nb = [read(p / 'network.json') for p in (before, after)]
    assert {k for k in na.keys() | nb.keys() if na.get(k) != nb.get(k)} == {'head_queue_movement_lanes'}
    changed = {m for m in a['urban_movement_queue'] if a['urban_movement_queue'][m] != b['urban_movement_queue'][m]}
    assert changed <= set(plan['added'])
    for key in ('ramp_queue', 'urban_link_storage', 'urban_arrival_buffer', 'urban_storage_release_buffer',
                'urban_inflow_transit_buffer', 'freeway_density', 'freeway_speed', 'mainline_origin_queue',
                'boundary_queue', 'offramp_transit_buffer'):
        assert a[key] == b[key], key
    ap, bp = [d['local_observation_summary']['projection_diagnostics'] for d in (a, b)]
    av, bv = [d['physical_stock_assignment_by_link'] for d in (ap, bp)]
    assert av.keys() == bv.keys()
    for link in av:
        assert abs(sum(av[link].values()) - sum(bv[link].values())) < 1e-8
        if link not in ('1210018302', '1220021201'):
            assert av[link] == bv[link], link
    whole = read(after / 'expanded_area_check.json')
    assert abs(whole['observed_inside_veh'] - whole['seeded_inside_veh']) < 1e-8
    rows.append(dict(at=at, whole_omega_inventory_veh=whole['seeded_inside_veh'],
        queue_assignment={link: dict(before=av[link], after=bv[link],
              lane_evidence=bp['head_phase_queue_attribution'][link]) for link in ('1210018302', '1220021201')},
        services_arrivals_commands_unchanged=True, physical_inventory_preserved=True))
out = HERE / 'initialization_verification.json'
assert not out.exists()
out.write_text(json.dumps(dict(status='passed', rows=rows, forecasts=0, native_runs=0,
    qualification='Observed queue allocation only, not control benefit.'), indent=2) + '\n', encoding='utf8')
print(json.dumps(dict(status='passed', states=[r['at'] for r in rows])))
