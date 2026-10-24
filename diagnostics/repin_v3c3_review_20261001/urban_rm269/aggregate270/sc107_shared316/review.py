"""Review the completed shared-service pair without another prediction."""
from pathlib import Path
import gzip, hashlib, json

HERE=Path(__file__).resolve().parent
OLD=Path('E:/VISSIM_analysis/20261010_branch_service315/forecast2400')
NEW=Path('E:/VISSIM_analysis/20261010_sc107_shared316/forecast2400')
PINS={}

def read(p,compressed=False):
    p=Path(p); b=p.read_bytes(); PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if compressed else b)

def main():
    out=HERE/'comparison.json'; assert not out.exists()
    result={}
    for version,folder in [('previous315',OLD),('shared316',NEW)]:
        s=read(folder/'summary.json'); assert s['status']=='complete'
        for p,h in s['source_pins'].items():
            assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        result[version]={}
        for arm in ('hold','city'):
            a=s['results'][arm]; r=read(folder/(arm+'.response.json.gz'),True)
            assert r['conditional_model_feasibility_witness'] and r['model_constraint_coverage']['complete']
            assert a['writer_three_blocks'] and a['conservation_states']==4
            assert a['resource_max_exceedance']<1e-7
            flows={}
            for m in ('SC107_W_SC1004_to_E_SC108','SC107_W_SC1005_to_E_SC108',
                      'SC108_W_SC107_to_E_SC109','SC109_W_SC108_to_E'):
                flows[m]=sum(x['vehicles'] for x in r['transfers'] if x['source']=='movement:'+m and x['target']!=x['source'])
            resource=[x for x in r['resource_allocations'] if x['resource']=='1220000201:10023:p3:through']
            result[version][arm]=dict(omega_ttt_veh_h=a['omega_ttt_veh_h'],flows=flows,
                shared_constraints=a['shared_constraints'],wall_sec=a['wall_sec'],
                resource_intervals=len(resource),available_veh=sum(x['available_veh'] for x in resource),
                accepted_veh=sum(x['accepted_total_veh'] for x in resource),
                conservation_verified=True,writer_three_blocks=True)
            if version=='shared316':
                assert a['shared_constraints']['feasible'] and len(resource)==45
                assert all(x['accepted_total_veh']<=x['available_veh']+1e-7 for x in resource)
    delta={v:d['city']['omega_ttt_veh_h']-d['hold']['omega_ttt_veh_h'] for v,d in result.items()}
    native=5.28666666666649
    assert delta['shared316']<0<native
    report=dict(status='complete_shared_service_flow_improved_whole_gain_unqualified',results=result,
        delta_omega_veh_h=delta,native_delta_omega_veh_h=native,
        gain_error_improvement_veh_h=abs(native-delta['previous315'])-abs(native-delta['shared316']),
        production_adopted=False,goal_complete=False,source_pins=PINS,
        budget=dict(completed_scalar450=2,tests=6,ad=0,optimizer=0,native=0,fzp_scans=0,new_rate_fits=0),
        limits=['The904 bypass lower-bound trial is inherited unchanged and remains capacity-binding.',
                'Both commands pass sharedNP/NUF constraints, but this does not establish actual gain.',
                'Shared origin service is not yet qualified by AD, unused-state response, whole selection or native.',
                'SC109 head observations pool turns; do not equate them with through-only model counts.'],
        next_step='Reconcile SC108-to-SC109 accepted inflow, delayed arrivals, remaining transit and native head timing using retained records before proposing another correction.')
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(delta=delta,improvement=report['gain_error_improvement_veh_h'],
        both_shared_feasible=True,adopted=False)))

if __name__=='__main__': main()
