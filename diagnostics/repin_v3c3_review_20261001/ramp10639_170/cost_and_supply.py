"""Exact30s cost-error accounting and sampled conditional gap opportunities.

The actual-state gap values are diagnostics, never autonomous merge forecasts.
"""
import math
from diagnostics.repin_v3c3_review_20261001.ramp10639_170 import check as c


def main():
    assert not (c.HERE/'cost_and_supply.json').exists()
    c.pin(c.Path(__file__))
    data = c.read(c.HERE/'results.json')
    prior = c.read(c.HERE/'verification.json')
    for p,d in prior['input_sha256'].items():
        assert c.sha(p)==d, p
    rows = data['rows_30s']
    costs = []
    for seed in (67,61):
        arms = {}
        for arm in ('hold','release'):
            rr = [x for x in rows if x['seed']==seed and x['arm']==arm and x['connector']=='10639']
            parts = {k:sum((3120.1-(x['start']+x['end'])/2)/3600*s*(x['predicted'][k]-x['actual'][k])
                           for x in rr) for k,s in [('arrival',1),('merge',-1)]}
            delta = sum(x['predicted']['ttt']-x['actual']['ttt'] for x in rr)
            c.close(sum(parts.values()),delta,'weighted conservation cost')
            arms[arm]=dict(parts=parts,cost_error_veh_h=delta)
        response = {k:arms['release']['parts'][k]-arms['hold']['parts'][k] for k in ('arrival','merge')}
        costs.append(dict(seed=seed, arms=arms, release_minus_hold_cost_error_parts=response))
    cfg = c.read(c.R/'coupled_recovery153/candidate/reference_config.json')
    node = cfg['freeway']['physical_ramp_receiving_nodes']['RM_C10639']
    tc,tf=node['critical_gap_sec'],node['followup_sec']
    def gap(q):
        return q*math.exp(-q*tc/3600)/-math.expm1(-q*tf/3600) if q else 3600/tf
    supply=[]
    for arm in ('hold','release'):
        pred=c.read(c.R/f'recovery_lateral169/forecast/state/s67_late_{arm}.json.gz')
        rr={round(x['start_sec'],1):x for x in pred['ramps'] if x['start']['connector_id']=='10639'}
        nr=c.csvrows(c.I/f'heldout67_freeway_20260930/observations/{arm}/cells_30s.csv')
        nr={round(float(x['time_s']),1):x for x in nr if x['road']=='FW_E' and x['cell']=='9'}
        for t in c.TIMES[:-1]:
            model=rr[t]; native=nr[t];audit=model['receiving_node']
            assert audit['upstream_cell']==9
            q=float(native['rho_veh_per_km_lane'])*float(native['v_kmh'])*(1-audit['off_split_removed'])
            c.close(gap(audit['conflicting_vph_per_lane']),audit['gap_supply_vph_per_lane'],'original gap formula')
            cap=audit['unlimited_node_canonical_budget_vph']
            c.close(min(cap,audit['gap_supply_vph_per_lane']),model['receiving_budget_veh']*3600,'actual applied node budget')
            supply.append(dict(arm=arm,time_s=t,native_q_per_lane=q,
                model_q_per_lane=audit['conflicting_vph_per_lane'],
                native_state_gap_vph=gap(q),model_state_gap_vph=gap(audit['conflicting_vph_per_lane']),
                model_canonical_budget_vph=cap,
                native_q_with_model_cap_vph=min(cap,gap(q)),
                model_applied_budget_vph=model['receiving_budget_veh']*3600))
    for p,d in c.PINS.items():assert c.sha(p)==d,p
    out=dict(costs=costs,gap_samples=supply,input_sha256=c.PINS,
        cost_interpretation='Exact30s quadrature decomposition from the same initial stock; an error ledger, not independent causal contributions.',
        gap_interpretation='Native current cell9 rho*v with the unchanged model off split and cap; pointwise conditional opportunity ONLY. Does not resolve target-lane gaps, eligibility, posthead travel, receiving occupancy or causality. Not an autonomous forecast or estimated capacity.',
        new_forecasts=0,new_fits=0)
    c.save('cost_and_supply.json',out)
    print(costs)
    for arm in ('hold','release'):
        for a,b in ((2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            z=[x for x in supply if x['arm']==arm and a<=x['time_s']<b]
            print(arm,a,{k:sum(x[k] for x in z)/len(z) for k in ('native_q_with_model_cap_vph','model_applied_budget_vph')})


if __name__=='__main__':main()
