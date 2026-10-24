"""Compare actual runtime initialization against the previous scoped candidate."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_bytes())
plan = read(HERE/'plan.json')
for path, digest in plan['source_pins'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
members = {m for g in read(HERE/'physical_routes.json')['native_choice_groups'].values()
           if g['signal'] in ('SC12','SC16') for m in g['route_to_movement'].values()}
opaque = {'lane_urban_runtime','lane_freeway_runtime','lane_offramp_runtime','lane_ramp_runtime',
          '_control_area_ledger','_component_vsl_exposure','sc1001_approach'}
rows = []
for at, old, new in [(2400,'forecast2400_service','init2400_checked'),
                     (3300,'forecast3300_service_first150','init3300')]:
    before, after = HERE.parent/'sc6_queue'/old, HERE/new
    assert read(after/'completion.json')['status'] == 'complete'
    sa, sb = [read(x/'state.json') for x in (before,after)]
    na, nb = [read(x/'network.json') for x in (before,after)]
    assert {k for k in na.keys()|nb.keys() if na.get(k)!=nb.get(k)} <= {'urban_movements','movement_capacity_by_movement_veh_h'}
    for k in sa.keys()|sb.keys():
        if k not in opaque: assert sa.get(k)==sb.get(k), (at,k)
    changed = {m for m in na['urban_movements'] if na['urban_movements'][m]!=nb['urban_movements'][m]}
    assert changed == members
    for m in changed:
        a,b = na['urban_movements'][m],nb['urban_movements'][m]
        assert {k:v for k,v in a.items() if k!='beta'} == {k:v for k,v in b.items() if k!='beta'}
    caps = {m:dict(before=na['movement_capacity_by_movement_veh_h'][m],after=v)
            for m,v in nb['movement_capacity_by_movement_veh_h'].items()
            if na['movement_capacity_by_movement_veh_h'][m]!=v}
    assert set(caps) <= members
    area = read(after/'expanded_area_check.json')
    assert abs(area['observed_inside_veh']-area['seeded_inside_veh']) < 1e-8
    rows.append(dict(at=at, inventory_veh=area['seeded_inside_veh'], changed_movements=sorted(changed),
        capacity_redistribution=caps, all_serialized_physical_state_and_arrivals_unchanged=True,
        opaque_object_address_strings_excluded=sorted(opaque)))
out = HERE/'initialization_verification.json'
assert not out.exists()
out.write_text(json.dumps(dict(status='passed',rows=rows,forecasts=0,native_runs=0,
    limitation='Opaque objects are checked by canonical initialization and subsequent rollout conservation, not repr equality.'),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status='passed',states=[r['at'] for r in rows])))
