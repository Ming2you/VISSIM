"""Reconfigure the diagnostic's already-built spec cache after a static edit.

Normal bootstrap compiles static specs once. This experiment changes a bound
after bootstrap; refresh just that network's cache, never the native runtime.
"""
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc104_service345.candidate import M,support,fixed_clock,install as prior_install
def install(cfg,network,frame,*,service=False):
    from src.models import urban_queue_model as uqm
    result=prior_install(cfg,network,frame,service=service)
    old=uqm.movement_specs(cfg)
    stale=not old[M].get('sc104_qualified_fixed_clock')
    uqm._SPECS_CACHE[:]=[(net,specs) for net,specs in uqm._SPECS_CACHE if net is not cfg.network]
    assert uqm.movement_specs(cfg)[M]['sc104_qualified_fixed_clock']
    result['diagnostic_static_spec_cache_refreshed']=True
    result['previous_cached_spec_was_stale']=stale
    return result
