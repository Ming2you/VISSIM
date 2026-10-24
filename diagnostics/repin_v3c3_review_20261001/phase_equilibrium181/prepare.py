"""One bounded relaxation consistency test; freeze all178/179 coefficients."""
import ast
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve the finite experiment'
    prior=h.R/'transport_once179'
    pins=h.read(prior/'pins.json')
    for p,d in pins.items():assert h.sha(p)==d,p
    sources=h.read(prior/'executed_function_sources.json')
    marker='            velocity = mn.metanet_speed_update_kmh(phase_u,phase_u,rho,down,target,dt,self.lengths[i],'
    assert sources['RouteLaneRegion'].count(marker)==1
    replacement='''            # Existing FD target is a whole-lane mean, not moving-only speed.
            # Preserve that mean equilibrium when it is kinematically attainable.
            # No new capacity, coefficient, command bonus, or future observation.
            macro_target=target
            moving_cap=max(net.v_min,float(net.v_free))
            if active:moving_cap=min(moving_cap,max(net.v_min,(1+net.alpha_vsl)*command))
            target=min(moving_cap,max(0.,(count*macro_target-phase[1])/moving)) if moving>1e-10 else 0.
            self.phase_events[-1].update(macro_target=macro_target,moving_target=target,
                moving_cap=moving_cap,moving_n=moving,phase_u=phase_u,
                aggregate_equilibrium=(phase[1]+moving*target)/count if count>1e-10 else macro_target)
            velocity = mn.metanet_speed_update_kmh(phase_u,phase_u,rho,down,target,dt,self.lengths[i],'''
    code=sources['RouteLaneRegion'].replace(marker,replacement)
    changed=dict(sources,RouteLaneRegion=code)
    methods=lambda code:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(code).body[0].body if isinstance(n,ast.FunctionDef)}
    a,b=methods(sources['RouteLaneRegion']),methods(code)
    assert [k for k in a if a[k]!=b[k]]==['speed']
    # Test actual source implementation through a narrowly configured real
    # speed method in verify.py, before launching any forecast.
    protocol=copy.deepcopy(h.read(prior/'protocol.json'))
    protocol.update(previous_goal_turn='PROGRESS179/180: duplicate transport fixed, native-state sending close; autonomous slow stock remains overpredicted.',
        hypothesis='179 applies whole-lane FD target to moving phase then dilutes by slow phase, creating additional equilibrium speed loss. Restore aggregate FD relaxation target where legal moving speed can realize it.',
        equation='u_target=min(v_free, active?(1+alpha)*VSL:infinity, max(0,(N*V_FD-M_s)/(N-S))). Aggregate attainable target=(M_s+(N-S)*u_target)/N.',
        unchanged='Formation/release two hazards, anticipation, actual merge loss, accepted route flux, physical receiving, lateral transport, off storage/drain,171 ramp storage,132 parameters.',
        fit='NONE. Same frozen178 hazards. No new fitted target or capacity.',
        gates='Same179 gates. No production adoption on conservation or absolute improvement alone. Check RM hold/release, VSL positive and negative, independent states.',
        budget=dict(autonomous450_max=13,new_fits=0,native=0,FZP=0),
        prior_evidence='Claude P_PLANT conditioned term decomposition reviewed; macro equilibrium vs moving-only target mismatch is new178 candidate-specific hypothesis, not claim about canonical METANET.')
    pins[str(prior/'executed_function_sources.json')]=h.sha(prior/'executed_function_sources.json')
    pins[str(Path(__file__))]=h.sha(__file__)
    for name in ('coefficients.json','spec.json'):
        (HERE/name).write_bytes((prior/name).read_bytes());pins[str(prior/name)]=h.sha(prior/name)
    h.save(HERE/'protocol.json',protocol);h.save(HERE/'pins.json',pins)
    h.save(HERE/'executed_function_sources.json',changed)
    runner=h.R/'state_lateral168/run.py'
    (HERE/'completed179_runner.py.txt').write_bytes(runner.read_bytes())
    h.save(HERE/'source_archive.json',dict(path=str(runner),historical_sha256=h.sha(runner),archive=str(HERE/'completed179_runner.py.txt')))
    print('181 prepared: single relaxation target interpretation, no fit.')


if __name__=='__main__':main()
