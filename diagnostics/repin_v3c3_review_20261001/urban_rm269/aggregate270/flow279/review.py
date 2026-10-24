"""Review the bounded10686 correction; never call a prediction or optimizer."""
import gzip,hashlib,importlib.util,json,pickle,sys
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
R=HERE.parent/'urban_clock277'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
read=lambda p:json.loads(Path(p).read_bytes())
obj=lambda p:pickle.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
M='SC1002_W_SC1001_to_S_SC105'

def main():
    out=HERE/'review.json';assert not out.exists()
    loader=importlib.util.spec_from_file_location('clock_review',R/'review_response.py')
    prior=importlib.util.module_from_spec(loader);loader.loader.exec_module(prior)
    from evaluation.controllers.signal_actuation_contract import phase_fraction
    from evaluation.controllers import sdmpc_sequence as seq
    from audit import GROUPS
    proof=read(HERE/'diagnosis.json')
    tree=ET.parse(ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx')
    edges=[]
    for node in tree.findall('./links/link'):
        a,b=node.find('fromLinkEndPt'),node.find('toLinkEndPt')
        if a is not None:
            c=int(node.get('no'));edges.extend([(int(a.get('lane').split()[0]),c),(c,int(b.get('lane').split()[0]))])
    expected={'SC1002_to_SC105':{10661,10662,10663},'SC105_to_SC1005':{10565,10570}}
    for group,links in GROUPS.items():
        assert {b for a,b in edges if a in links and b not in links}==expected[group]
    replay={}
    for label in ('replay3300','candidate3300'):
        root=HERE/label
        receipt=read(root/'summary.json')
        assert all(sha(p)==h for p,h in receipt['source_pins'].items())
        cfg,state,action,forecast=obj(root/'initial.pickle')
        r=json.loads(gzip.decompress((root/'response.json.gz').read_bytes()))
        states=read(root/'stocks.json')
        assert r['model_constraint_coverage']['complete'] and r['conditional_model_feasibility_witness']
        exceed=max((x['exceedance_veh'] for x in r['resource_allocations']),default=0.)
        assert exceed<1e-7
        values={}
        for group in GROUPS:
            incoming=[sum(t['vehicles'] for t in r['transfers'] if start<=t['start_sec']<start+150
                and t['target']=='storage:'+group and t['source']!=t['target']) for start in (3300,3450,3600)]
            values[group]=dict(incoming_veh=incoming,total_incoming_veh=sum(incoming))
        output={}
        for source in (M,'SC1005_N_SC105_to_W_SC1004'):
            output[source]=sum(t['vehicles'] for t in r['transfers'] if t['source']=='movement:'+source and t['target']!=t['source'])
        output['merge10681']=sum(t['vehicles'] for t in r['transfers'] if t['source']=='ramp:RM_C10681' and t['target']=='merge_pending:RM_C10681')
        fractions=[]
        for start,block in zip((3300,3450,3600),seq.actions(action,3)):
            fractions.extend(phase_fraction(block,cfg,cfg.network.urban_movements[M],t/10) for t in range(start,start+150,10))
        if label=='candidate3300':assert fractions==[1.]*45
        else:assert any(x==0 for x in fractions)
        replay[label]=dict(omega_ttt_veh_h=receipt['omega_ttt_veh_h'],corridors=values,outputs_veh=output,
            gate_fraction=fractions,resource_exceedance_veh=exceed,
            end10686_ready_veh=states[-1]['stocks']['movement:'+M]['inside'])
    recs={name:obj(HERE/(name+'_result.pickle')) for name in ('hold2400','release2400','hold2400_ad')}
    assert recs['hold2400_ad']['fallback_reasons']=={}
    errors=prior.compare(recs['hold2400_ad'],recs['hold2400'])
    for field in ('cost_jacobian','resource_jacobian'):
        mat=np.asarray(recs['hold2400_ad'][field]);assert mat.shape[1]==213 and np.isfinite(mat).all()
    rows={name:prior.row(value) for name,value in recs.items()}
    old=read(R/'response_review.json')['deltas']['urban10']
    a,b=rows['hold2400'],rows['release2400']
    delta=dict(omega_veh_h=b['omega_veh_h']-a['omega_veh_h'],
        merge10681_veh=b['merges_veh']['RM_C10681']-a['merges_veh']['RM_C10681'],
        owners={k:b['owner_costs'][k]-a['owner_costs'][k] for k in a['owner_costs']})
    assert old['omega_veh_h']*delta['omega_veh_h']>0 and delta['merge10681_veh']>40
    receipts={}
    for label in recs:
        rr=read(HERE/(label+'_execution.json'))
        assert rr['exit_code']==0 and rr['source_pins_unchanged']
        assert all(sha(p)==h for p,h in rr['source_pins'].items())
        receipts[label]=dict(wall_sec=rr['wall_sec'],mode=rr['mode'])
    report=dict(status='one_gate_correction_checked_two_states_not_whole_gain_qualified',
        replay3300=replay,native3300_corridor_inflow={g:sum(x['corridors'][g]['inflow_from_balance'] for x in proof['native']) for g in GROUPS},
        rm2400=dict(before=old,after=delta),scalar_ad_errors=errors,checks2400=receipts,
        change='Existing config unsignalized flag for SC1002_W_SC1001_to_S_SC105 only; no rate/FD/demand changes.',
        native_runs=0,full_selections=0,new_coefficient_fits=0,pushes=0,
        limits=['Two stored states of seed29, actual3300 city commands and counterfactual2400 RM hold/release; not independent-seed native gain validation.',
            'More accurate upstream inflow is not proof of matching every urban stock or totalOmega improvement.',
            'Existing10686 service remains conservative and legacy phase-group derived; no unobserved capacity bonus or new flow fit is supplied.',
            'Prior active/frozen native queue remains unchanged.'],
        pins={str(p):sha(p) for p in (HERE/'audit.py',HERE/'diagnosis.json',HERE/'predict.py',HERE/'check2400.py',HERE/'config_10686_free.json',Path(__file__))})
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('status','native3300_corridor_inflow','rm2400','scalar_ad_errors')},ensure_ascii=False))
    for label,r in replay.items():print(label,r['outputs_veh'],r['end10686_ready_veh'],r['corridors'])

if __name__=='__main__':main()
