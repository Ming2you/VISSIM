"""Replay178 verification plus an actual phase-flux/operator regression."""
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.queue_dynamics178 import verify as prior

HERE=Path(__file__).resolve().parent


def main():
    from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
    common.setup()
    from evaluation.controllers import physical_lane_groups as lanes
    from src.models import metanet as mn
    source=h.read(HERE/'executed_function_sources.json')
    ns={};exec(compile(source['RouteLaneRegion'],'179_verify_class','exec'),lanes.__dict__,ns)
    obj=ns['RouteLaneRegion'].__new__(ns['RouteLaneRegion'])
    obj.phase0={20:[[0.,0.,600.]],21:[[0.,0.,200.]]}
    obj.phase_next=copy.deepcopy(obj.phase0)
    obj.phase_start_n={20:[10.],21:[10.]};obj.phase_balance={20:[[0.]*6],21:[[0.]*6]}
    obj._phase_flux(20,0,0,2.,'through')
    assert obj.phase_next=={20:[[0.,0.,480.]],21:[[0.,0.,320.]]}
    transported=obj.phase_next[21][0][2]/12.
    parameters=(40.,40.,transported,1/3600,.2,18/3600,10.,17.,5.)
    bad=mn.metanet_speed_update_kmh(transported,60.,*parameters)
    good=mn.metanet_speed_update_kmh(transported,transported,*parameters)
    assert abs(good-transported)<1e-12 and bad>good+1.
    h.save(HERE/'actual_flux_regression.json',dict(actual_phase_flux_method=True,transported_kmh=transported,
        before_kmh=bad,after_kmh=good,unforced_transport_error_before=bad-transported,unforced_transport_error_after=good-transported))
    assert h.read(HERE/'coefficients.json')==h.read(h.R/'queue_dynamics178/coefficients.json')
    assert all(h.read(HERE/'forecast/old178_parity.json').values())
    prior.HERE=HERE;prior.main()
    from diagnostics.repin_v3c3_review_20261001.queue_dynamics178 import context
    context.HERE=HERE;context.main()


if __name__=='__main__':main()
