"""Bounded reuse of Claude U7/current kinematic projection, no fitted rates."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
H=HERE.parent
ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    base=H/'native_beta/config.json'
    config=read(base)
    old_contract=ROOT/config['urban']['arrival']['kinematic_contract']
    contract=read(old_contract)
    network=read(H/'native_beta/init2400_checked/network.json')
    for source,link,turns in (
        ('SC12_to_SC6','1210018302',{'through':'10205','right':'10207','left':'10206'}),
        ('SC1_to_SC101','1220011503',{'through':'10538','right':'10528','left':'10539'})):
        movements={m:dict(connector=turns[spec['turn']],expected_spec=spec)
                   for m,spec in network['urban_movements'].items() if spec.get('origin')==source}
        assert len(movements)==3
        contract['sources'][source]=dict(link=link,movements=movements)
    contract['scope']='Current terminal-road cohorts of SC6S/SC101S only; retain all other origin inventory and reservations. Current lane attribution is approximate for uncommitted vehicles; no future routes. Internal future travel, demand and service stay unchanged. Existing66 contract retained.'
    config['urban']['arrival']['kinematic_contract']=(HERE/'contract.json').relative_to(ROOT).as_posix()
    for name,data in [('contract.json',contract),('config.json',config)]:
        p=HERE/name;assert not p.exists();p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    paths=[Path(__file__),base,old_contract,HERE/'contract.json',HERE/'config.json',
           ROOT/'evaluation/controllers/observation_projection.py',ROOT/contract['network']['path'],
           H.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',H/'city_response/assessment.json']
    plan=dict(status='prepared_not_validated',source_pins={str(p):sha(p) for p in paths},
        config=str(HERE/'config.json'),max_initializations=2,max_forecasts=3,forecasts_completed=0,
        new_fitted_parameters=0,optimizations=0,native_runs=0,
        scope='One bounded current-observation candidate;2400hold/selected450s plus unused3300applied150s.',
        success='Conservation, rates and future boundaries unchanged; local response and material joint gain improve without harming unused state. Never infer native isolated effects from model action split.',
        limitations=['Current lane is not a known destination. No historical route capture is invented.',
            'Only two observed terminal-road cohorts change; future upstream arrivals and service limitations remain.',
            'Late predicted arrival beyond an observed crossing proves a timing inconsistency; early arrival alone does not prove an error because signal/queue wait follows.'],
        runtime_gate='Calibration/control qualification first; complete SDMPC wall-time optimization after.')
    (HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Prepared bounded current-cohort arrival candidate; no rate changes or forecasts.')

if __name__=='__main__':main()
