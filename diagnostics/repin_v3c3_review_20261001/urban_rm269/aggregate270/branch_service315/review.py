"""Review retained autonomous forecasts and identify where added flow stops."""
from pathlib import Path
import gzip,hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc108_geometry311/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_branch_service315/forecast2400')
PINS={}


def read(path,compressed=False):
    path=Path(path);raw=path.read_bytes();PINS[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if compressed else raw)


def main():
    assert not (HERE/'comparison.json').exists()
    results={}
    for version,folder in (('old',OLD),('new',NEW)):
        summary=read(folder/'summary.json')
        for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        results[version]={}
        for arm in ('hold','city'):
            item=summary['results'][arm]
            r=read(folder/(arm+'.response.json.gz'),True)
            assert r['conditional_model_feasibility_witness'] and r['model_constraint_coverage']['complete']
            assert item['writer_three_blocks'] and item['conservation_states']==4
            assert item['resource_max_exceedance']<1e-7
            service=[x for x in r['resource_allocations'] if x['resource']=='1129:branch:bypass']
            amount=lambda s,t:sum(x['vehicles'] for x in r['transfers'] if x['source']==s and x['target']==t)
            counts=dict(
                bypass=amount('storage:SC1004_E_choice','storage:SC1004_to_SC107'),
                local=amount('storage:SC1004_E_choice','storage:SC1004_to_SC1005'),
                sc1004_through_arrival=amount('storage:SC1004_to_SC107','movement:SC107_W_SC1004_to_E_SC108'),
                sc1004_through_departure=amount('movement:SC107_W_SC1004_to_E_SC108','storage:SC107_to_SC108'),
                sc1005_through_departure=amount('movement:SC107_W_SC1005_to_E_SC108','storage:SC107_to_SC108'),
                sc108_through_departure=amount('movement:SC108_W_SC107_to_E_SC109','storage:SC108_to_SC109'))
            results[version][arm]=dict(omega_ttt_veh_h=item['omega_ttt_veh_h'],counts=counts,
                bypass_intervals=len(service),bypass_binding_intervals=sum(abs(x['accepted_total_veh']-x['available_veh'])<1e-8 for x in service),
                shared_constraints=item['shared_constraints'],wall_sec=item['wall_sec'],costs_by_stock=item['costs_by_stock'])
    delta={v:d['city']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h'] for v,d in results.items()}
    assert abs(delta['new']-delta['old'])<.01
    increments={}
    for arm in ('hold','city'):
        old=results['old'][arm];new=results['new'][arm]
        assert old['counts']['local']==new['counts']['local']
        assert old['counts']['sc1005_through_departure']==new['counts']['sc1005_through_departure']
        assert old['counts']['sc108_through_departure']==new['counts']['sc108_through_departure']
        increments[arm]={k:new['counts'][k]-old['counts'][k] for k in old['counts']}
        assert new['bypass_intervals']==new['bypass_binding_intervals']==44
    evidence=read(A/'branch_service314/assessment.json')
    # Fixed, disjoint historical60s intervals; no horizon/outcome fitting.
    historical60=[dict(start_sec=t,end_sec=t+60,
        witnessed_crossings=sum(t<=e['low_sec'] and e['high_sec']<t+60 for e in evidence['certain_observed_crossings']))
        for t in range(1800,2220,60)]
    assert max(x['witnessed_crossings'] for x in historical60)*60==1440
    assert not results['new']['hold']['shared_constraints']['feasible']
    report=dict(status='complete_bounded_branch_rate_response_not_gain_qualified',goal_complete=False,adopted=False,
        results=results,delta_omega_veh_h=delta,native_delta_omega_veh_h=5.28666666666649,
        increments=increments,past60sec_lower_bound=historical60,
        source_pins=PINS,budget=dict(full450=2,ad=0,optimizer=0,native=0,fzp_passes=0,coefficient_grid=False),
        next_action='Do not repeat scalar-rate search. Reconcile physical SC107 common-head service with retained source tags and pre/post-diverge position. Existing413cap and trial904 remain below witnessed short-window flow; trial does not remove the binding cap or refute its role. Check service/resource structure and source shortage together before another bounded comparison.',
        limits=['904 is only a conservative achieved-flow lower bound, not an identified physical capacity.',
                'Both arms remain bypass-cap-limited throughout44active intervals; this is not an ablation that removes the cap.',
                'Hold still violates NP by about3.986 vehicles; physical conservation alone does not qualify a controller candidate.',
                'Existing model numbers and actual head counts have different boundaries; never equate them without intervening stock accounting.',
                'No fullAD, wholeSDMPC, unused-state response or native validation for this candidate.'])
    (HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('DELTA',delta,'INCREMENTS',increments)


if __name__=='__main__':main()
