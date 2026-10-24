"""The same physical-clock331 rollout hooks used by completed337 validation."""
from contextlib import contextmanager,ExitStack
from pathlib import Path


@contextmanager
def source_hooks():
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315.candidate import enabled as branch
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import enabled as north
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329.candidate import enabled as routes
    with ExitStack() as stack:
        b=stack.enter_context(branch());t=stack.enter_context(transport())
        n=stack.enter_context(north());r=stack.enter_context(routes())
        yield dict(branch=b,transport=t,north=n,routes=r)


@contextmanager
def enabled(cfg,hooks):
    from evaluation.controllers import area_follower_objective as joint
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import installed,geometry
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311.candidate import clock
    root=Path(__file__).resolve().parents[5]
    before={k:len(hooks[k]) for k in ('transport','north','routes')}
    with ExitStack() as stack:
        g=stack.enter_context(installed(cfg,'aggregate_sc10_native_calendar',geometry(root,cfg)))
        p=stack.enter_context(clock(cfg));stack.enter_context(joint.shared_query_runtime_scope())
        record={}
        yield record
        record.update(branch=hooks['branch'],**{k:len(hooks[k])-before[k] for k in before},gate=len(g),prehead=len(p),
                      physical_signal_clock=True,continuous_actuators=False)
