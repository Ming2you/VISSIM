"""Correct178's double advection; freeze all fitted rates and other equations."""
import ast
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists()
    previous=h.R/'queue_dynamics178';pins=h.read(previous/'pins.json')
    for p,d in pins.items():assert h.sha(p)==d,p
    source=h.read(previous/'executed_function_sources.json')
    old='mn.metanet_speed_update_kmh(phase_u,up,rho,down,target,dt,self.lengths[i],'
    new='mn.metanet_speed_update_kmh(phase_u,phase_u,rho,down,target,dt,self.lengths[i],'
    assert source['RouteLaneRegion'].count(old)==1
    changed=dict(source,RouteLaneRegion=source['RouteLaneRegion'].replace(old,new))
    before=ast.parse(source['RouteLaneRegion']);after=ast.parse(changed['RouteLaneRegion'])
    methods=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body[0].body if isinstance(n,ast.FunctionDef)}
    a,b=methods(before),methods(after)
    assert [k for k in a if a[k]!=b[k]]==['speed']
    # Test against the actual canonical operator, not a reimplementation.
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from src.models import metanet as mn
    n,local,incoming,upstream=10.,20.,2.,60.
    transported=(n*local+incoming*upstream)/(n+incoming)
    args=(40.,40.,transported,1/3600,.2,18/3600,10.,17.,5.)
    double=mn.metanet_speed_update_kmh(transported,upstream,*args)
    once=mn.metanet_speed_update_kmh(transported,transported,*args)
    assert abs(double-transported)>1 and abs(once-transported)<1e-12
    # A uniform velocity field stays uniform, irrespective of positive mass.
    assert mn.metanet_speed_update_kmh(60.,60.,40.,40.,60.,*args[3:])==60.
    h.save(HERE/'unit.json',dict(status='pass',transported_kmh=transported,old_double_kmh=double,
        corrected_kmh=once,extra_convection_kmh=double-once,uniform_velocity_preserved=True,
        only_speed_method_changed=True,changed_call_argument='upstream=phase_u removes analytic convection after accepted-flow speed transport'))
    protocol=copy.deepcopy(h.read(previous/'protocol.json'))
    protocol.update(previous_goal_turn='PROGRESS178:24forecasts;179 audit reproduced double convection, so178 rejection is not a clean test of intended transport-once queue dynamics.',
        hypothesis='Accepted-flow momentum transport already advects moving speed; retaining METANET analytic convection repeats upstream influence. Replace only that convection with zero; retain relaxation/anticipation/merge and slow dynamics.',
        fit='NONE; frozen178 coefficients and all132 parameters.',
        budget=dict(autonomous450_max=13,new_fits=0,native=0,FZP=0),
        prior_evidence='133 already avoids double convection in its different accepted-flow candidate;Claude P_PLANT reviewed for shared-lane/branch feedback and no parameter transfer.')
    for name in ('coefficients.json','spec.json'):
        (HERE/name).write_bytes((previous/name).read_bytes());pins[str(previous/name)]=h.sha(previous/name)
    pins[str(previous/'executed_function_sources.json')]=h.sha(previous/'executed_function_sources.json')
    pins[str(Path(__file__))]=h.sha(__file__)
    h.save(HERE/'executed_function_sources.json',changed);h.save(HERE/'pins.json',pins);h.save(HERE/'protocol.json',protocol)
    runner=h.R/'state_lateral168/run.py'
    (HERE/'completed178_runner.py.txt').write_bytes(runner.read_bytes())
    h.save(HERE/'source_archive.json',dict(path=str(runner),historical_sha256=h.sha(runner),archive=str(HERE/'completed178_runner.py.txt')))
    print(h.read(HERE/'unit.json'))


if __name__=='__main__':main()
