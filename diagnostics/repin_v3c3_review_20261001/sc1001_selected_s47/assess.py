"""Score one current SC1001 replay against already completed native commands."""
import ast
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R=HERE.parent
C=R/'sc1001_connection'
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS={}

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    raw=p.read_bytes();PINS[str(p)]=hashlib.sha256(raw).hexdigest()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)

def summarize(row):
    cost=row['cost_by_stock'];flows=row['control_area']['flow_counts']
    out=dict(omega=row['ttt_omega_veh_h'],east=cost['freeway:FW_E'],west=cost['freeway:FW_W'],
        ramps=sum(v for k,v in cost.items() if k.startswith('ramp:')),outside=row['tracked_outside_residence_veh_h'],
        source=flows['origin:FW_E->freeway:FW_E'],
        merge=sum(v for k,v in flows.items() if k.startswith('merge_pending:') and k.endswith('->freeway:FW_E')),
        off=sum(v for k,v in flows.items() if k.startswith('freeway:FW_E->storage:')),
        terminal=flows['freeway:FW_E->external:terminal:FW_E'])
    out['other_omega']=out['omega']-out['east']-out['west']-out['ramps']
    out['omega_plus_tracked_outside']=out['omega']+out['outside']
    return out

def main():
    assert not (HERE/'assessment.json').exists()
    protocol=read(HERE/'protocol.json')
    wrapper=C/'check_connection.py'
    for name,expected in protocol['pins'].items():
        p=Path(name)
        if p.resolve()==wrapper.resolve():p=HERE/'wrapper_before.py.txt'
        assert digest(p)==expected,name
    old=read(I/'closedloop_recorded2700_select_check_res47v2_resv3/summary.json')
    new=read(I/'closedloop_recorded2700_select_check_sc1001_selected_s47_sc1001_selected_s47/summary.json')
    held=read(I/'closedloop_recorded2700_lever450_sc1001_causal_history_routes/summary.json')['results']['held_actual']
    native_dir=I/'closedloop_recorded2700_native_selected_res47v2/analysis'
    native=read(native_dir/'summary.json');decomp=read(native_dir/'response_decomposition.json');boundary=read(native_dir/'boundary_response.json')
    assert native['paired_prefix_exact'] and native['common_start_vehicle_records_exact'] and native['counterfactual_valid']
    assert all(a['native_execution_passed'] for a in native['arms'].values())
    assert set(new['results'])=={'held_actual','selected'} and not new['future_observation_inputs']
    assert new['optimizer_iterations']==0
    for key in new['results']:assert new['results'][key]['commands']==old['results'][key]['commands']
    fresh=new['results']['held_actual']
    for key in ('commands','ttt_omega_veh_h','tracked_outside_residence_veh_h','cost_by_stock','ramps'):
        assert fresh[key]==held[key],key
    maximum=0.;quantities={};states={}
    for j,key in enumerate(('held_actual','selected')):
        trace=read(C/f'sc1001_selected_s47_response_{j}.json.gz')
        assert len(trace['quantities']['owners'])==17
        maximum=max(maximum,trace['resource_max_exceedance'])
        quantities[key]=trace['quantities'];states[key]=trace['states']
    assert states['held_actual'][0]==states['selected'][0] and maximum<1e-7
    modes={name:{key:summarize(doc['results'][key]) for key in ('held_actual','selected')} for name,doc in (('before',old),('after',new))}
    deltas={name:{k:d['selected'][k]-d['held_actual'][k] for k in d['selected']} for name,d in modes.items()}
    native_delta=dict(omega=native['delta_TTT_veh_h'],east=decomp['actual_delta_veh_h']['FW_E'],west=decomp['actual_delta_veh_h']['FW_W'],
        ramps=decomp['actual_delta_veh_h']['eight_ramps'],other_omega=decomp['actual_delta_veh_h']['other_Omega'],outside=native['delta_outside_Omega_residence_veh_h'])
    native_delta['omega_plus_tracked_outside']=native_delta['omega']+native_delta['outside']
    for dst,src in (('source','source'),('merge','merge'),('off','off_entry'),('terminal','terminal')):
        native_delta[dst]=sum(z['mainline']['FW_E'][src] for z in boundary['selected_minus_hold'])
    deltas['native']=native_delta
    before_ast=ast.parse((HERE/'wrapper_before.py.txt').read_text(encoding='utf8'))
    after_ast=ast.parse(wrapper.read_text(encoding='utf8'))
    def funcs(t):return {n.name:ast.dump(n) for n in t.body if isinstance(n,ast.FunctionDef)}
    b,a=funcs(before_ast),funcs(after_ast)
    assert b.keys()==a.keys() and [k for k in b if b[k]!=a[k]]==['main']
    (HERE/'wrapper_executed.py.txt').write_bytes(wrapper.read_bytes())
    PINS[str(wrapper)]=digest(wrapper)
    result=dict(status='COMPLETED_FIXED_NATIVE_SELECTION_REPLAY_NOT_GLOBAL_QUALIFICATION',seed=47,start_sec=2700,horizon_sec=450,
        forecasts=2,compute_sec=sum(z['wall_sec'] for z in new['results'].values()),cases=modes,selected_minus_hold=deltas,
        absolute_delta_error={m:{k:abs(deltas[m][k]-native_delta[k]) for k in native_delta} for m in ('before','after')},
        quantities=quantities,shared_states=states,resource_max_exceedance=maximum,held_parity_exact=True,commands_exact=True,
        changed_production_functions=[],changed_diagnostic_functions=['check_connection.main'],new_native=0,fzp_reads=0,fit=0,optimizer=0,
        source_pins=PINS,limitations=protocol['limits'],goal='ACTIVE / NOT_QUALIFIED')
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('status','compute_sec','selected_minus_hold','absolute_delta_error','resource_max_exceedance')},ensure_ascii=False))

if __name__=='__main__':main()
