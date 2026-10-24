"""Verify only current terminal-road cohorts change, before any rollout."""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'plan.json')
for p,d in plan['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
sources={'SC12_to_SC6','SC1_to_SC101'}
opaque={'lane_urban_runtime','lane_freeway_runtime','lane_offramp_runtime','lane_ramp_runtime','_control_area_ledger','_component_vsl_exposure','sc1001_approach'}
allowed={'urban_movement_queue','urban_arrival_buffer','urban_storage_release_buffer','gate_initial_route_tags','local_observation_summary'}
rows=[]
for at,old in ((2400,'init2400_checked'),(3300,'init3300')):
    before=HERE.parent/'native_beta'/old;after=HERE/f'init{at}'
    assert read(after/'completion.json')['status']=='complete'
    a,b=[read(x/'state.json') for x in (before,after)]
    na,nb=[read(x/'network.json') for x in (before,after)]
    assert {k for k in na.keys()|nb.keys() if na.get(k)!=nb.get(k)}=={'kinematic_queue_zero_links'}
    for k in a.keys()|b.keys():
        if k not in opaque|allowed:assert a.get(k)==b.get(k),(at,k)
    affected={m for m,spec in na['urban_movements'].items() if spec.get('origin') in sources}
    assert {k:v for k,v in a['urban_movement_queue'].items() if k not in affected}=={k:v for k,v in b['urban_movement_queue'].items() if k not in affected}
    assert abs(sum(a['urban_movement_queue'].values())-sum(b['urban_movement_queue'].values()))<1e-8
    for key in ('urban_arrival_buffer','urban_storage_release_buffer','gate_initial_route_tags'):
        assert {k:v for k,v in a[key].items() if k not in sources}=={k:v for k,v in b[key].items() if k not in sources}
    for source in sources:
        assert b['urban_arrival_buffer'][source]==b['urban_storage_release_buffer'][source]
        assert abs(sum(a['urban_arrival_buffer'][source].values())-sum(b['urban_arrival_buffer'][source].values()))<1e-8
        assert source not in a['gate_initial_route_tags']
        for step,tag in b['gate_initial_route_tags'][source].items():
            assert sum(tag.values())<=b['urban_arrival_buffer'][source][step]+1e-8
            assert set(tag)<=affected and min(tag.values())>=0
    area=read(after/'expanded_area_check.json');assert abs(area['observed_inside_veh']-area['seeded_inside_veh'])<1e-8
    rows.append(dict(at=at,observed_and_seeded_omega_veh=area['seeded_inside_veh'],
        all_service_rates_demand_future_travel_and_other_physical_stocks_unchanged=True,
        reallocated_cohort_veh={s:sum(sum(tag.values()) for tag in b['gate_initial_route_tags'][s].values()) for s in sources}))
p=HERE/'initialization_verification.json';assert not p.exists()
p.write_text(json.dumps(dict(status='passed',rows=rows),indent=2)+'\n',encoding='utf8')
print(json.dumps(rows))
