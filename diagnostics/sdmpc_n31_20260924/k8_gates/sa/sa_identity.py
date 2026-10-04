"""Lane-stock ledger identity terms of K8 amendment 5 section 3 (pure stdlib; imported by sa_cap_child.py inside the
adapter process and by the harness tests).

    sum_l stock_l = N_127 + N_10777 - |A| + N_tail129 + M_other + N_shortfall_kept   (+-1e-9)

replaces the amendment 1 H-2b / spec 5.8-9 T8 target "N_127 + N_10777 - |A|", which contradicted spec 5.8-5 (129 tail
init:port packets) and 5.8-6 (other-link W member ready mass) that SA implements (review B-3); K8 amendment 7 §1 adds
N_shortfall_kept, the post-head share beyond its receiver's room that SA keeps as a 127 head ready packet; K8 amendment
8 §1 adds the posthead connector (d) share kept the same way to N_shortfall_kept (its provenance stays on the connector
as the member queue, so M_other is read net of it)."""

W_MEMBERS = ('SC1001_W_to_E_SC1002', 'SC1001_W_to_S_SC1003', 'SC1001_W_to_N_SC2002')
RECEIVERS = ('SC1001_to_SC1002', 'SC1001_to_SC1003', 'SC1001_to_SC2002')
HEADS = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}
# Spec 5.8-5 129 tail (evidence tail129_from_m / port_progress_route); read from cfg.network.stopline_approach when the
# key is present, these evidence values otherwise (BASE captures record the same terms for reference).
TAIL129_FROM_M = 239.38422422843928
PORT_PROGRESS_ROUTES = ('1132:2',)
POSTHEAD_REHOME = ('10695',)     # evidence posthead_rehome connectors (cfg.network.stopline_approach when present)


def _f(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    v = getattr(x, 'value', None)
    if v is None:
        v = getattr(x, '_validation_primal', None)
    return float(v) if v is not None else float('nan')


def _route_key(row):
    if not row or row.get('route_decision_no') is None:
        return None
    return f"{row['route_decision_no']}:{row['route_no']}"


def identity_terms(bound, provenance, sa_spec, shortfall_kept=None, rehome_kept=None):
    """K8 amendment 5 section 3 + amendment 7 §1 + amendment 8 §1: the six terms of the lane-stock ledger identity,
    each recorded separately.

      sum_l stock_l = N_127 + N_10777 - |A| + N_tail129 + M_other + N_shortfall_kept   (+-1e-9)
    N_127 / N_10777  observed vehicles on 127 / 10777 (bound complete records)
    |A|              127 vehicles at or past their lane head (spec 5.8-4(a))
    N_tail129        129 vehicles at POS >= tail129_from_m on a port_progress_route (spec 5.8-5 init:port packets)
    M_other          W member queue mass projected on links other than 127 and 10777 (spec 5.8-6 ready packets),
                     read from the captured provenance net of the posthead connector (d) kept share, which SA books on
                     its connector as the member queue after 5.8-6 (amendment 8 §1; `rehome_kept` = the SA metadata
                     posthead_rehome_shortfall_veh; 0 without the SA key, None when the key is present but the value
                     was not passed -> the identity is not read)
    N_shortfall_kept the post-head share kept as 127 head ready packets because its receiver had no room, branch (a)
                     (amendment 7 §1) and the posthead connector branch (d) (amendment 8 §1): `shortfall_kept` = the
                     SA metadata stopline_approach_initial.posthead_receiver_shortfall_veh (both branches); 0 without
                     the SA key (BASE), None (not recorded -> the identity is not read) when the key is present but
                     the value was not passed
    recv127          (cross-check, not a term) the 127 provenance booked into the three receivers = |A| - the (a) share
                     of N_shortfall_kept
    rehome_member    (cross-check, not a term) the W member queue mass read on the posthead rehome connectors = the
                     (d) share of N_shortfall_kept (amendment 8 §1; 0 when nothing was kept)
    """
    recs = (bound.get('vehicle_records') or {}).get('records') or []
    routes = {r.get('veh_no'): r for r in ((bound.get('vehicle_routes') or {}).get('records') or [])}
    tail_from = float(sa_spec['tail129_from_m']) if sa_spec else TAIL129_FROM_M
    progress = set(sa_spec['port_progress_route']) if sa_spec else set(PORT_PROGRESS_ROUTES)
    members = tuple(sa_spec['members']) if sa_spec else W_MEMBERS
    n = {k: 0 for k in ('127', '10777', '10695')}
    posthead = tail = 0
    for r in recs:
        k = str(r['link_no'])
        if k in n:
            n[k] += 1
        if k == '127' and float(r['position_m']) >= HEADS.get(int(r['lane_no']), 1e9):
            posthead += 1
        if k == '129' and float(r['position_m']) >= tail_from and _route_key(routes.get(r['veh_no'])) in progress:
            tail += 1
    rehome = {str(k) for k in (sa_spec.get('posthead_rehome', POSTHEAD_REHOME) if sa_spec else POSTHEAD_REHOME)}
    m_other = rehome_member = 0.0
    for link, row in (provenance or {}).items():
        if str(link) in ('127', '10777'):
            continue
        for m in members:
            v = _f((row or {}).get('movement:' + m, 0.0))
            if v is not None and v > 0.0:
                m_other += v
                if str(link) in rehome:
                    rehome_member += v
    kept_d = _f(rehome_kept) if rehome_kept is not None else (0.0 if sa_spec is None else None)
    m_other = None if kept_d is None else m_other - kept_d
    receivers = tuple(sa_spec['receiver_of'].values()) if sa_spec else RECEIVERS
    recv127 = 0.0
    for key, v in ((provenance or {}).get('127') or {}).items():
        if str(key).startswith('storage:') and str(key)[len('storage:'):] in receivers:
            x = _f(v)
            recv127 += x if x is not None else float('nan')
    kept = _f(shortfall_kept) if shortfall_kept is not None else (0.0 if sa_spec is None else None)
    return {'n127': n['127'], 'n10777': n['10777'], 'n10695': n['10695'], 'posthead_127': posthead,
            'n_tail129': tail, 'm_other': m_other, 'n_shortfall_kept': kept, 'recv127': recv127,
            'n_rehome_kept': kept_d, 'rehome_member': rehome_member,
            'target_lane_stock': (None if kept is None or m_other is None
                                  else n['127'] + n['10777'] - posthead + tail + m_other + kept)}
