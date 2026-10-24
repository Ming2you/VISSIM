"""Review retained fixed-command responses without fitting a gain sign."""
from pathlib import Path
import gzip,hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc108_geometry311/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc107_head313/forecast2400_v3')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from candidate import SG5,UNKNOWN,THROUGH,RIGHT
    out=HERE/'comparison.json';assert not out.exists()
    results={};pins={}
    for version,folder in (('old',OLD),('new',NEW)):
        d=read(folder/'summary.json');assert d['status']=='complete' and d['forecasts']==2
        for p,h in d['source_pins'].items():assert sha(p)==h,p
        pins[str(folder/'summary.json')]=sha(folder/'summary.json')
        results[version]={}
        for arm in ('hold','city'):
            r=d['results'][arm];path=folder/(arm+'.response.json.gz');pins[str(path)]=sha(path)
            response=json.loads(gzip.decompress(path.read_bytes()))
            assert response['conditional_model_feasibility_witness'] and response['model_constraint_coverage']['complete']
            assert r['writer_three_blocks'] and r['resource_max_exceedance']<1e-7
            keys=['SC107_W_SC1004_to_E_SC108',THROUGH,RIGHT,SG5,UNKNOWN]
            counts={}
            for key in keys:
                rows=[x for x in response['transfers'] if x['source']=='movement:'+key and x['source']!=x['target']]
                counts[key]=dict(total=sum(x['vehicles'] for x in rows),count150=[sum(x['vehicles'] for x in rows if at<=x['start_sec']<at+150) for at in (2400,2550,2700)])
            incoming={}
            for source in ('SC1004_to_SC107','SC1005_to_SC107'):
                rows=[x for x in response['transfers'] if x['target']=='storage:'+source and x['source']!=x['target']]
                incoming[source]=sum(x['vehicles'] for x in rows)
            results[version][arm]=dict(omega_ttt=r['omega_ttt_veh_h'],movement_departures=counts,incoming_to_approach=incoming,
                shared_constraints=r['shared_constraints'],wall_sec=r['wall_sec'],unknown_cost=r['costs_by_stock'].get('movement:'+UNKNOWN,0))
            if version=='new':
                assert counts[UNKNOWN]['total']==0 and abs(counts[SG5]['total']-11)<1e-7
                assert abs(results[version][arm]['unknown_cost']-.125)<1e-8
    delta={v:r['city']['omega_ttt']-r['hold']['omega_ttt'] for v,r in results.items()}
    native=5.28666666666649
    projection=read(NEW/'sc107_initial_application.json');pins[str(NEW/'sc107_initial_application.json')]=sha(NEW/'sc107_initial_application.json')
    initial_ids={r['vehicle']:r for r in projection['records_used_at_initialization_only']}
    head_audit=read(A/'sc107_composition312/assessment.json');pins[str(A/'sc107_composition312/assessment.json')]=sha(A/'sc107_composition312/assessment.json')
    initial_lane5_head={}
    for arm in ('hold','city'):
        rows=[r for r in head_audit['native_validation'][arm]['head_events'] if r['vehicle'] in initial_ids and initial_ids[r['vehicle']]['lane']==5]
        initial_lane5_head[arm]={sg:sum(r['sg']==sg for r in rows) for sg in ('2','5')}
    report=dict(status='complete_current_head_diagnostic_not_adopted',goal_complete=False,adopted=False,
        results=results,delta_omega_veh_h=delta,native_delta_omega_veh_h=native,
        absolute_error_reduction=abs(delta['old']-native)-abs(delta['new']-native),
        current_projection=projection,initial_lane5_actual_head_diagnostic=initial_lane5_head,
        next_action='Do not tune initial head partition to match gain. Initial lane is not a fixed future service head: verify aggregate lateral access and future pre/post-diverge arrivals using existing caches; current beta/head-only prediction is structurally incomplete.',
        scope=['No route/phase/demand coefficient fit. Same two actual command sequences, same450horizon and Omega.',
            'Only initial current cohort changed. Future route beta/head assignment and pre-head right handling remain unrepaired.',
            'Current lane5 starts are not proof of future SG5 use; future head records are diagnostic only.',
            'Unresolved1veh remains stored, .125vehh in BOTH arms; not silently deleted or counted as a normal exit.',
            'Physical witness does not establish NP/NUF feasibility. Report per-arm constraints unchanged.',
            'No fullAD/SDMPC/native validation or production adoption;3300check is initialization only.'],
        budget=dict(retained_full450=2,unretained_full450=1,failed_partial450=1,setup_failure_before_forecast=1,
            new_native=0,ad=0,full_selection=0,new_fzp=0,fits=0),source_pins=pins)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print('DELTA',delta,'NATIVE',native,'ERROR_REDUCTION',report['absolute_error_reduction'])
    print('INITIAL_LANE5_ACTUAL_HEAD',initial_lane5_head)
    print('CONSTRAINTS',{v:{a:r['shared_constraints']['feasible'] for a,r in arms.items()} for v,arms in results.items()})
    print('SC107_INCOMING',{v:{a:r['incoming_to_approach'] for a,r in arms.items()} for v,arms in results.items()})


if __name__=='__main__':main()
