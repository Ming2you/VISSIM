"""Prepare one geometry-only connector-stage candidate and bounded fixed forecasts."""
from pathlib import Path
import json,hashlib,datetime
HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'plan.json').exists()
config=read(H/'sc1_supply/config.json');config['urban']['known_wout_connector_queue']=True
save(HERE/'config.json',config)
source=(H/'lateral_access/forecast.py').read_text(encoding='utf8').replace('lateral_access','connector_stage')
source=source.replace('same-command lane-access','same-command connector-stage')
start=source.index("            fit=read(HERE/'past_fit.json')")
end=source.index("            assert cfg.network.movement_capacity_by_movement_veh_h",start)
source=source[:start]+'''            assert spec['connector_queue_gate'] is True
            comparable=copy.deepcopy(spec);comparable.pop('connector_queue_gate')
            for entry in comparable['entry_lane_receiving']['connector_entries'].values():
                entry.pop('capacity_per_lane_veh')
            assert comparable==old_net['known_legsplit_routes']
            old_cohorts=old_state['known_legsplit_route_state']['cohorts']
            new_cohorts=state.known_legsplit_route_state['cohorts']
            from collections import Counter
            counts=lambda rows:dict(Counter(x['target'] for x in rows))
            assert counts(old_cohorts)==counts(new_cohorts)
            assert sum(x['vehicles'] for x in old_cohorts)==sum(x['vehicles'] for x in new_cohorts)
            assert sum(x['vehicles'] for x in new_cohorts if 'connector68' in x)==sum(x['vehicles'] for x in old_cohorts if x['target']=='prechoice')-sum(x['vehicles'] for x in new_cohorts if x['target']=='prechoice' and 'lane68' in x)
''' + source[end:]
source=source.replace(",\'urban_storage_release_buffer\'",'')
source=source.replace("candidate=spec['connector_stage_rate_per_sec']","candidate='finite_connector_stages',changed_aliases=['urban_storage_release_buffer','known_legsplit_route_state']")
source=source.replace("'lateral_rate', spec['connector_stage_rate_per_sec']","'connector_stages', spec['connector_queue_gate']")
source=source.replace("One past lateral rate with predicted finite adjacent room and lane-eligible RM debits; other dynamics unchanged.","Finite connector storage then actual68 admission before route choice. No new coefficient and no lateral-rate candidate.")
(HERE/'forecast.py').write_text(source,encoding='utf8')
pins=[HERE/'forecast.py',HERE/'config.json',ROOT/'evaluation/controllers/route_choice_corridor.py',ROOT/'evaluation/controllers/urban_flow_accounting.py',ROOT/'tests/test_known_wout_connector_stage.py',H.parent/'urban260/verify.py']
plan=dict(status='prepared_unit_passed',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    baseline='../sc1_supply/config.json',hypothesis='ETA was conflated with physical68 entry while connector stock consumed68 space; stage finite connector storage before shared68 receiving and route choice.',
    max_fixed_forecasts=3,new_native=0,new_full_selections=0,new_fitted_coefficients=0,
    tests=33,source_pins={str(p):sha(p) for p in pins},
    unchanged=['initial physical ownership/count/current destination','network/demand/seed29','Omega701 TTT','450s depth3 at2400','terminal OFF','active frozen queue'],
    limitations=['Aggregate connector lane FIFO and proportional competition; no native lateral gaps or explicit longitudinal headway','Initial overcapacity retained; only further admission is limited','Unused3300 is same seed; not independent seed qualification'])
save(HERE/'plan.json',plan)
print('prepared one candidate, zero fits, maximum three fixed forecasts')
