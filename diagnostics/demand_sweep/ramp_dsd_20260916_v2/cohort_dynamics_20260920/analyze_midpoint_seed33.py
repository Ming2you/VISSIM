"""Post-run three-level comparison for the frozen development-seed repeat."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import prepare_midpoint_seed33 as p
from diagnostics.fast_fixed_profile_verify import verify, prefix_digest

e, OUT, BANK = p.e, p.OUT, p.BANK


def native(arm):
    old = arm=='rm_ramp'
    folder = (BANK if old else OUT)/'observations'/arm
    data = p.m.prepare_data(folder)
    stockpath = BANK/'analysis'/arm/'stocks_1s.csv' if old else folder/'component_stocks_1s.csv'
    stocks = {int(r['time_s']):r for r in e.rows(stockpath)}
    main = sum(float(stocks[t]['FW_E_n']) if old else
        float(stocks[t]['FW_E_mainline'])+float(stocks[t]['FW_E_source_negative'])
        for t in range(2551,3001))/3600
    component = dict(mainline=main,on=0.,off=0.)
    ports = {}
    for spec in data.definitions.values():
        if spec['road']!='FW_E' or spec['kind'] not in ('ramp','offramp'): continue
        c = str(spec['connector']); initial = len(data.port_cohorts['2550'][c]); n = initial
        arrivals = departures = stock_seconds = 0
        for t in range(2551,3001):
            incoming,outgoing=data.arrivals[t,c],data.departures[t,c]
            arrivals+=incoming;departures+=outgoing;n+=incoming-outgoing
            assert n>=0;stock_seconds+=n
            if t%30==0:
                assert n==len(data.port_cohorts[str(t)][c])
                assert float(data.ports[t,c]['unresolved_absences_veh'])==0
            if spec['kind']=='ramp':
                h=data.headstocks[t,c];assert n==int(h['prehead_n'])+int(h['posthead_n'])
        cost=stock_seconds/3600;component['on' if spec['kind']=='ramp' else 'off']+=cost
        ports[c]=dict(initial=initial,final=n,arrivals=arrivals,departures=departures,ttt_veh_h=cost)
    if not old:
        for kind in ('on','off'):
            assert abs(component[kind]-sum(float(stocks[t]['FW_E_'+kind]) for t in range(2551,3001))/3600)<1e-8
    return dict(component=component,ports=ports),data


def main():
    protocol=e.load(OUT/'protocol.json')
    for name,digest in protocol['source_pins'].items():
        assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest()==digest,name
    reference=BANK/'run_rm_ramp'; checks={}
    ref_prefix=prefix_digest(reference/'vissim_eval/baseline_001.fzp',2550)
    ref_later=prefix_digest(reference/'vissim_eval/baseline_001.fzp',2700)
    for arm in ('rm8','rm6'):
        run=OUT/('run_'+arm);receipt=e.load(run/'run.json')
        assert receipt['completed'] and receipt['terminal_sec']==3000 and not receipt['owned_native_alive']
        checks[arm]=verify(OUT/('prepared_'+arm),run,reference)
        assert checks[arm]['passed']
        own=prefix_digest(run/'vissim_eval/baseline_001.fzp',2550);assert own==ref_prefix
        if arm=='rm6':assert prefix_digest(run/'vissim_eval/baseline_001.fzp',2700)==ref_later
    actual={};data={}
    for arm in ('rm8','rm6','rm_ramp'):actual[arm],data[arm]=native(arm)
    for arm in ('rm6','rm_ramp'):
        assert data[arm].cells[2550]==data['rm8'].cells[2550]
        assert data[arm].port_cohorts['2550']==data['rm8'].port_cohorts['2550']
    assert data['rm6'].cells[2700]==data['rm_ramp'].cells[2700]
    assert data['rm6'].port_cohorts['2700']==data['rm_ramp'].port_cohorts['2700']
    predictions=e.load(OUT/'predictions.json');deltas={}
    for arm in ('rm6','rm_ramp'):
        values={k:actual[arm]['component'][k]-actual['rm8']['component'][k] for k in ('mainline','on','off')}
        deltas[arm]=dict(**values,total=sum(values.values()))
    source=[Path(__file__),OUT/'protocol.json',OUT/'predictions.json']
    for arm in ('rm8','rm6'):
        source.extend(OUT/'observations'/arm/name for name in
            ('manifest.json','component_stocks_1s.csv','port_events.csv','port_cohorts_30s.json','head_stock_1s.csv'))
    source.extend(BANK/'observations/rm_ramp'/name for name in
        ('manifest.json','port_events.csv','port_cohorts_30s.json','head_stock_1s.csv'))
    source.append(BANK/'analysis/rm_ramp/stocks_1s.csv')
    report=dict(qualified=False,status='COMPLETED_SECOND_DEVELOPMENT_SEED',actual=actual,
        actual_deltas_vs_g8=deltas,predicted=predictions,source_pins={q.relative_to(e.ROOT).as_posix():p.sha(q) for q in source},
        native_checks=checks,exact_prefix2550=ref_prefix,exact_prefix2700_rm6_vs_strong=ref_later,
        cost_convention='Whole-link native1s mainline includes just-inserted negative-position rows;physical on/off connector event residence.',
        new_native_runs=2,reused_native_runs=1,frozen_predictions=3,
        limitations=['Seed33 was already used for development,not fresh holdout.',
            'FW_E component,not whole Omega or fullGNE.',
            'Two development seeds do not identify a distribution of treatment effects or qualify gain prediction.'])
    e.save(OUT/'result.json',report)
    print(json.dumps(dict(actual_deltas_vs_g8=deltas,predicted_deltas_vs_g8={a:predictions[a]['delta_vs_g8'] for a in deltas})),flush=True)


if __name__=='__main__':main()
