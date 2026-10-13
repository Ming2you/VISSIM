"""Validate the bounded transport pair and its limits from saved evidence."""
from pathlib import Path
import gzip,hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
OLD=Path('E:/VISSIM_analysis/20261010_sc107_shared316/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc109_transport317/forecast2400')
PINS={}
def read(p,gz=False):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if gz else b)

def main():
    out=HERE/'comparison.json';assert not out.exists()
    results={}
    for name,folder in [('shared316',OLD),('transport317',NEW)]:
        s=read(folder/'summary.json');assert s['status']=='complete' and s['forecasts']==2
        for p,h in s['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        results[name]={}
        for arm in ('hold','city'):
            a=s['results'][arm];r=read(folder/(arm+'.response.json.gz'),True)
            assert a['shared_constraints']['feasible'] and a['writer_three_blocks']
            assert a['conservation_states']==4 and a['resource_max_exceedance']<1e-7
            assert r['conditional_model_feasibility_witness'] and r['model_constraint_coverage']['complete']
            stocks={'movement:SC109_W_SC108_to_E','movement:SC109_W_SC108_to_N_SC16','storage:SC108_to_SC109'}
            last=[x for x in r['residence'] if x['stage']=='urban'][-1]
            flows={m:sum(x['vehicles'] for x in r['transfers'] if x['source']=='movement:'+m) for m in
                ('SC108_W_SC107_to_E_SC109','SC109_W_SC108_to_E','SC109_W_SC108_to_N_SC16')}
            sources={}
            for x in r['transfers']:
                if x['target']=='storage:SC108_to_SC109':sources[x['source']]=sources.get(x['source'],0.)+x['vehicles']
            results[name][arm]=dict(omega_ttt_veh_h=a['omega_ttt_veh_h'],flows=flows,incoming_by_source=sources,
                terminal_veh={k:last['model_stock_veh'][k] for k in stocks},
                local_cost_veh_h=sum(a['costs_by_stock'].get(k,0) for k in stocks),
                costs_by_stock=a['costs_by_stock'],feasible=True,wall_sec=a['wall_sec'])
    receipts=read(NEW/'transport_receipts.json');geom=read(NEW/'source_geometry.json')
    # Both arms share identical initial geometry/speed; commands and accepted source flows remain unchanged.
    assert set(geom['delay_sec'].values())=={60}
    for arm in ('hold','city'):
        for source,n in results['shared316'][arm]['incoming_by_source'].items():
            assert abs(n-results['transport317'][arm]['incoming_by_source'][source])<1e-7
    for source in geom['sources']:
        actual=sum(x['vehicles'] for x in receipts if x['source']==source)
        expected=sum(results['transport317'][arm]['incoming_by_source'].get('movement:'+source,0.) for arm in ('hold','city'))
        assert abs(actual-expected)<1e-7
    delta={v:d['city']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h'] for v,d in results.items()}
    native=read(A/'sc107_shared316/comparison.json')['native_delta_omega_veh_h']
    assert delta['transport317']<0<native
    local_delta={v:d['city']['local_cost_veh_h']-d['hold']['local_cost_veh_h'] for v,d in results.items()}
    report=dict(status='complete_transport_clock_improves_local_exit_response_whole_gain_unqualified',
        results=results,delta_omega_veh_h=delta,local_delta_veh_h=local_delta,native_delta_omega_veh_h=native,
        gain_error_improvement_veh_h=abs(native-delta['shared316'])-abs(native-delta['transport317']),
        delay_sec=geom['delay_sec'],source_pins=PINS,goal_complete=False,production_adopted=False,
        budget=dict(scalar450=2,tests=6,ad=0,optimizer=0,native=0,fzp_scans=0,fits=0),
        limits=['The total gain direction remains wrong. Do not adopt for whole-controller gain.',
          'Equal60s delays arise from current path/speed and10s rounding; they are not fixed fitted constants.',
          'Initial calendars are preserved, so this does not claim to fix current-state projection.',
          'Source service shortages and baseline904 lower-bound cap persist.',
          'No AD, unused-state, whole-selection or new native qualification for this candidate.'])
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(delta=delta,improvement=report['gain_error_improvement_veh_h'],local_delta=local_delta,adopted=False)))

if __name__=='__main__':main()
