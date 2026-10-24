"""Locate remaining whole-Omega error before further local corrections."""
from pathlib import Path
from collections import defaultdict
import gzip,hashlib,json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent;A=HERE.parent
MODEL=Path('E:/VISSIM_analysis/20261010_sc109_transport317/forecast2400');PINS={}
def raw(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b
def read(p):return json.loads(raw(p))
def main():
    out=HERE/'residual_budget.json';assert not out.exists()
    cfg,_,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    summary=read(MODEL/'summary.json');native=read(A/'exit_timing309/assessment.json')
    nb=read(A/'cityresponse290/assessment.json')['native_boundary']['delta']
    initial=read(A/'matched280/authority/hold.stocks.json')[0]
    allarms={};grouped={}
    for arm in ('hold','city'):
        r=json.loads(gzip.decompress(raw(MODEL/(arm+'.response.json.gz'))))
        final=dict(stocks={k:dict(inside=v) for k,v in r['residence'][-1]['inside_veh'].items()})
        account=model_boundary(r,[initial,final],summary['results'][arm]['omega_ttt_veh_h'],cfg)
        allarms[arm]=account
        groups=defaultdict(lambda:dict(count=0.,cost=0.))
        for key,row in account['routes'].items():
            if abs(row['departed'])<1e-10:continue
            possible={e['source']+'->'+e['target'] for t in cfg.network.control_area_routes.get(key,{}).get('physical_turns',[]) for e in t.get('crossing_edges',[]) if e['from_inside'] and not e['to_inside']}
            group=next(iter(possible)) if len(possible)==1 else 'unresolved_model_physical_route'
            groups[group]['count']+=row['departed'];groups[group]['cost']+=row['departure_cost']
        grouped[arm]=dict(groups)
    delta={k:sum(v[k] for v in allarms['city']['routes'].values())-sum(v[k] for v in allarms['hold']['routes'].values()) for k in ('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')}
    assert abs(sum(delta[k] for k in ('entry_cost','departure_cost','generation_cost'))-(summary['results']['city']['omega_ttt_veh_h']-summary['results']['hold']['omega_ttt_veh_h']))<1e-7
    md={k:{f:grouped['city'].get(k,{}).get(f,0)-grouped['hold'].get(k,{}).get(f,0) for f in ('count','cost')} for k in set(grouped['hold'])|set(grouped['city'])}
    ranked=[]
    for edge in set(md)|set(native['native_delta']):
        n=native['native_delta'].get(edge,dict(count=0,cost=0));m=md.get(edge,dict(count=0,cost=0))
        ranked.append(dict(edge=edge,native=n,model=m,model_minus_native_cost=m['cost']-n['cost']))
    ranked.sort(key=lambda x:abs(x['model_minus_native_cost']),reverse=True)
    cohorts=read(A/'exit_timing309/sc109_chain.json')['native_exit_cohorts']
    local=cohorts['city']['initial_local']['cost']-cohorts['hold']['initial_local']['cost']
    result=dict(status='complete_whole_error_budget',model_boundary_delta=delta,native_boundary_delta=nb,
        ranked_exit_errors=ranked,model_boundary=allarms,sc109_native_initial_local_delta_veh_h=local,
        source_pins=PINS,budget=dict(forecasts=0,ad=0,optimizer=0,native=0,fzp_scans=0,fits=0),goal_complete=False,
        limits=['Boundary decomposition is an accounting identity, not independently causal component effects.',
          'Native actual insertions differ despite identical offered demand. Do not subtract their cost to claim matched-control gain.',
          'Inside appearances include births and missed sampled entries; unexplained disappearances remain separate.',
          'Model10s endpoint/native5s midpoint and topology witness limits are retained.',
          'SC109 initial local cohort improves slightly in native; do not assume its lumped initial ETA explains the large whole loss.'])
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('MODEL_DELTA',delta);print('NATIVE',nb);print('TOP',json.dumps(ranked[:7]));print('SC109_INITIAL_NATIVE',local)

if __name__=='__main__':main()
