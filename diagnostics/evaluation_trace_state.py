"""Explicit operational state evidence; names containing 'cache' are not ignored."""
from diagnostics import evaluation_trace as base

FOLLOWER_FIELDS=(
    '_prev_coupling','_lambda_P','_lambda_UF','_seg_traj',
    '_phase_resolved_active_signals','_gne_phase_override',
    '_phase_ctx_cache',
    '_np_last_sum_nin','_np_prev_accum','_np_step_time','_np_corrector_pending',
    '_np_last_real_q','_np_bias_ratio',
)
WU_FIELDS=('_last_offramp_flow','_has_last_offramp_flow','_omega_p','_omega_f')
OUTER_FIELDS=('previous_control','_pfo_fallback_previous_control','_pfo_incumbent_center',
              '_signal_price_last_step','price_refresh_interval','_link_share_ctx',
              'nuf_link_share_mode','candidate_dedupe_enabled')
GUARD_DIAGNOSTICS=('distributed_response_terminal_proxy_vehicles',
                   'distributed_response_mainline_exit_veh','distributed_response_boundary_out_sink_veh',
                   'distributed_response_rollout_ttt','distributed_response_rollout_active')
MISSING_DEMAND=object()


def _phase_cache_identity(value, current_demand, identity_sink):
    """Normalize only the proven signature[1] == id(ctx['demand']) address.

    The signature is from priced_wu_link_controller._phase_refine_signature.
    Its other five operands and the full context/demand stay in comparison.
    Address values remain in a separate provenance stream. A stale/broken
    signature-to-context relation is an evidence error, never silently erased.
    """
    if value is None:return None
    if not isinstance(value,(tuple,list)) or len(value)!=2:
        raise ValueError('Unknown phase cache identity contract')
    signature,context=value
    if (not isinstance(signature,(tuple,list)) or len(signature)!=6
            or not isinstance(context,dict) or 'demand' not in context
            or type(signature[1]) is not int):
        raise ValueError('Unknown phase cache signature shape')
    cached_demand=context['demand']
    if signature[1]!=id(cached_demand):
        raise ValueError('Phase cache signature does not identify its context demand')
    present=current_demand is not MISSING_DEMAND
    if isinstance(current_demand,(tuple,list)):
        current_demand=current_demand[0] if current_demand else None
    relation=(current_demand is cached_demand) if present else 'not_observed_at_this_boundary'
    identity_sink({'field':'follower._phase_ctx_cache[0][1]',
                   'signature_demand_id':signature[1],'context_demand_id':id(cached_demand),
                   'current_demand_id':id(current_demand) if present else None,
                   'current_demand_observed':present})
    marker={'identity_contract':'phase_signature_context_demand/v1',
            'signature_identifies_context_demand':True,'current_is_context_demand':relation}
    if present:marker['current_demand_value']=current_demand
    normalized=list(signature);normalized[1]=marker
    return (normalized,context)


def _response(value):
    if value is None:return None
    response=base.result(value)
    nash=getattr(value,'nash',value)
    control=getattr(nash,'control',None)
    merged=dict(getattr(nash,'diagnostics',{}) or {})
    merged.update(getattr(control,'diagnostics',{}) or {})
    response['guard_consumed_diagnostics']=base.canonical({k:merged[k] for k in GUARD_DIAGNOSTICS if k in merged})
    return response


def operational(obj, *, current_demand=MISSING_DEMAND, identity_sink=None):
    if obj is None:return None
    follower=getattr(obj,'nash_solver',obj)
    wu=getattr(follower,'_wu',None)
    outer={k:getattr(obj,k) for k in OUTER_FIELDS if hasattr(obj,k)}
    # These cached results are real response inputs. Preserve score/control and
    # the exact diagnostics read by the generic fallback guard, not elapsed/progress metadata.
    if hasattr(obj,'_pfo_incumbent_eval'):
        outer['_pfo_incumbent_eval']=_response(obj._pfo_incumbent_eval)
    if hasattr(obj,'_nuf_solve_cache'):
        outer['_nuf_solve_cache']=[(key,{'nash':_response(value[0]),'states':value[1],
                                       'follower_objective':value[2],'rollout_used':value[3]})
                                   for key,value in obj._nuf_solve_cache.items()]
    fields={k:getattr(follower,k) for k in FOLLOWER_FIELDS if hasattr(follower,k)}
    if identity_sink is not None and '_phase_ctx_cache' in fields:
        fields['_phase_ctx_cache']=_phase_cache_identity(fields['_phase_ctx_cache'],current_demand,identity_sink)
    return base.canonical({
        'follower':fields,
        'wu':{k:getattr(wu,k) for k in WU_FIELDS if hasattr(wu,k)},
        'outer':outer,
    })
