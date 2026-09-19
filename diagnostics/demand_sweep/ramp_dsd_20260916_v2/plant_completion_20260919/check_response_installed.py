"""Full no-option replay and installed paired-response qualification."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
H=HERE.parent
sys.path.insert(0,str(H.parents[2]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2 import evaluate_response as e

def main():
    out=HERE/'response_installed_v2';out.mkdir(exist_ok=False)
    base=H/'controller_response_4500_v1/model_v4'
    new=H/'controller_response_4500_v1/model_v5_node'
    params=e.load(base/'selected_parameters.json')['parameters']
    profile=e.load(base/'port_profile.json')
    results={}
    for name,bank,folder in [('early13',H/'response_pairs_v1',H/'controller_response_4500_v1/none'),
                             ('late23',H/'response_late_s23_v1',H/'controller_response_s23_v1/none')]:
        protocol=e.load(bank/'protocol.json');start=protocol['start_s']
        data=e.ObservationData(folder)
        results[name]={'start_s':start,'variants':{},'actual':{}}
        for arm in ['none','rm_ramp','vsl','both']:
            source=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            model=e.load_base_model(data.geometry,base/'config.json')
            results[name]['actual'][arm]=e.component(source,model,start)
        for version,modeldir in [('baseline',base),('node',new)]:
            model=e.load_base_model(data.geometry,modeldir/'config.json')
            results[name]['variants'][version]={}
            for arm in ['none','rm_ramp','vsl','both']:
                sequence=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({protocol.get('meter_id','RM_C10490'):sequence['green'][i]} if sequence['green'] else {},
                            {d:sequence['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if sequence['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',profile,command)
                pred=e.simulate(model,w,params)
                if version=='baseline':
                    archived=e.load(H/'response_late_s23_v1/mechanism_ablation_v3'/f'{name}_baseline_{arm}.json')
                    if json.loads(json.dumps(pred))!=archived:raise AssertionError(('Default full prediction differs',name,arm))
                else:
                    hypothesis=e.load(HERE/'response_v1'/f'{name}_node_{arm}.json')
                    for key in ['cells','flows','ports']:
                        if pred[key]!=hypothesis[key]:raise AssertionError(('Installed response changed',name,arm,key))
                results[name]['variants'][version][arm]=e.component(data,model,start,pred)
                e.save(out/f'{name}_{version}_{arm}.json',pred)
        a=results[name]['actual'];v=results[name]['variants']['node']
        for arm in ['rm_ramp','vsl','both']:
            print(name,arm,'actual delta',round(a[arm]['component_ttt_veh_h']-a['none']['component_ttt_veh_h'],5),
                  'node delta',round(v[arm]['component_ttt_veh_h']-v['none']['component_ttt_veh_h'],5),flush=True)
    e.save(out/'results.json',{'default_full_prediction_replay_exact':True,'default_rollouts':8,
        'node_mainline_port_flow_probe_replay_exact':True,'results':results,
        'qualification':'Receiving forecast improved; joint RM/VSL cost-direction qualification FAILED'})

if __name__=='__main__':main()
