"""Read completed six forecasts; no model calls or native trajectory scans."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
pins={}
def read(path):
    b=path.read_bytes();pins[str(path)]=hashlib.sha256(b).hexdigest();return json.loads(b)

def main():
    prior=HERE.parent/'urban66_u7'; old=read(prior/'assessment.json'); native=read(prior/'native.json')
    result=dict(status='LOCAL_DISCHARGE_IMPROVED_CONTROL_GAIN_NOT_QUALIFIED',forecasts=6,tests_passed=15,
                fit=0,new_native=0,new_fzp=0,cases={},wall_sec=0.,unchanged_commands=True)
    for seed,names,folder in [(47,['held_actual','selected'],'closedloop_recorded2700_select_check_trace10681_service66_after47_service66_after47'),
                              (43,['held_actual','rm','vsl','both'],'closedloop_recorded2250_lever450_trace10681_service66_after43')]:
        traces=read(HERE/f'after{seed}_local.json')
        points={n:read(I/folder/(n+'.json')) for n in names}; base=points['held_actual']
        for name,t in zip(names,traces):
            p=points[name]; before=old['cases'][f'after{seed}'][name]
            assert p['commands']==before['commands'],name
            witness=p.get('saved_state_stock_witness')
            if witness is not None:assert witness['passed']
            assert t['resource_max']<1e-8
            members={'storage:in_SC1004_S','transit:gate:in_SC1004_S',
                     *('movement:'+m for m in t['states'][0]['queue'])}
            total=lambda st:sum(st['queue'].values())+st['storage']+st['gate_transit']
            external_delta=sum(tr['vehicles']*((tr['target'] in members)-(tr['source'] in members)) for tr in t['transfers'])
            balance_error=total(t['states'][-1])-total(t['states'][0])-external_delta
            assert abs(balance_error)<1e-7
            if name=='selected':
                assert p['validation']['written_command_binding_passed'] and p['validation']['prewrite_binding_passed']
            else:assert p['validation']['all_actuator_and_step_constraints_checked']
            result['wall_sec']+=p['wall_sec']; flows={}
            for tr in t['transfers']:
                if tr['source'] and tr['source'].startswith('movement:'):
                    m=tr['source'][9:];flows[m]=flows.get(m,0.)+tr['vehicles']
            last=t['states'][-1]
            result['cases'][f'{seed}_{name}']=dict(departure_veh=flows,
                end_approach_veh=sum(last['queue'].values())+last['storage']+last['gate_transit'],
                omega_veh_h=p['ttt_omega_veh_h'],outside_veh_h=p['tracked_outside_residence_veh_h'],
                total_veh_h=p['ttt_with_tracked_outside_veh_h'],
                delta_omega_veh_h=p['ttt_omega_veh_h']-base['ttt_omega_veh_h'],
                delta_total_veh_h=p['ttt_with_tracked_outside_veh_h']-base['ttt_with_tracked_outside_veh_h'],
                before_omega_veh_h=before['ttt_omega_veh_h'],before_total_veh_h=before['total_veh_h'],
                before_departure_veh=before['departure_veh'],max_resource_exceedance=t['resource_max'],
                local66_balance_error_veh=balance_error,
                global_saved_stock_witness='passed' if witness is not None else 'not exported by this existing four-arm probe',
                quantity_constraints=p.get('canonical_quantity_constraints'))
    initial={v['veh_no'] for v in read(prior/'after47.json')['current_records']}
    result['native_validation_only']={}
    for case in ['47hold','47selected','43nc']:
        n=native['cases'][case]; out={}
        for w in n['windows']:
            for lane,count in w['head_crossings'].items():
                label='N' if int(lane)<=3 else 'W';out[label]=out.get(label,0)+count
        row=dict(head_veh=out,link66_stock=[s['link66_vehicles'] for s in n['states']])
        if case.startswith('47'):
            row['N_initial66_by150s']=[sum(e['vehicle'] in initial for k,es in w['events'].items() if int(k)<=3 for e in es) for w in n['windows']]
            row['N_all_by150s']=[sum(count for k,count in w['head_crossings'].items() if int(k)<=3) for w in n['windows']]
        result['native_validation_only'][case]=row
    result['native43_delta_omega']=old['native43_delta_omega_veh_h']
    result['findings']=[
        'Other service rates, all compared commands and initial source/tag projection unchanged.',
        '43 RM/VSL cost differences unchanged to numerical tolerance despite increased N discharge.',
        '47 N absolute discharge error decreases but selected-minus-held N sign remains wrong.',
        'Achieved past rate is a measured lower bound, not identified saturation capacity.',
        '10632 already ungated in route_choice_corridor.intended_departure; phase label alone was insufficient to diagnose signal gating.']
    result['source_pins']=pins
    (HERE/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'wall_sec':result['wall_sec'],'native':result['native_validation_only'],
        'cases':{k:{q:v[q] for q in ['departure_veh','end_approach_veh','delta_omega_veh_h','delta_total_veh_h']} for k,v in result['cases'].items()}},indent=2))

if __name__=='__main__':main()
