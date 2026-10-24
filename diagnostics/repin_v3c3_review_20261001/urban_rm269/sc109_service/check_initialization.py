"""Only the proven head resource and its observed rate may change."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
plan=read(HERE/'plan.json')
for p,d in plan['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d,p
opaque={'lane_urban_runtime','lane_freeway_runtime','lane_offramp_runtime','lane_ramp_runtime','_control_area_ledger','_component_vsl_exposure','sc1001_approach'}
rows=[]
for at,old in ((2400,'init2400_checked'),(3300,'init3300')):
    before=HERE.parent/'native_beta'/old;after=HERE/f'init{at}'
    assert read(after/'completion.json')['status']=='complete'
    sa,sb=[read(x/'state.json') for x in (before,after)]
    na,nb=[read(x/'network.json') for x in (before,after)]
    changes={k for k in na.keys()|nb.keys() if na.get(k)!=nb.get(k)}
    assert changes <= {'head_service_resources','movement_capacity_by_movement_veh_h'},changes
    for k in sa.keys()|sb.keys():
        if k not in opaque:assert sa.get(k)==sb.get(k),(at,k)
    rates={m:dict(before=na['movement_capacity_by_movement_veh_h'][m],after=v)
           for m,v in nb['movement_capacity_by_movement_veh_h'].items() if v!=na['movement_capacity_by_movement_veh_h'][m]}
    assert set(rates)=={'SC109_W_SC108_to_N_SC16'},rates
    # Other physical resource contracts remain byte-equivalent as JSON values.
    a,b=na['head_service_resources'],nb['head_service_resources']
    assert {k:v for k,v in b['resources'].items() if k!='10286'}==a['resources']
    area=read(after/'expanded_area_check.json');assert abs(area['observed_inside_veh']-area['seeded_inside_veh'])<1e-8
    rows.append(dict(at=at,rate_change=rates,observed_and_seeded_omega_veh=area['seeded_inside_veh'],
        physical_state_arrivals_commands_and_other_rates_unchanged=True))
out=HERE/'initialization_verification.json';assert not out.exists()
out.write_text(json.dumps(dict(status='passed',rows=rows),indent=2)+'\n',encoding='utf8')
print(json.dumps(rows))
