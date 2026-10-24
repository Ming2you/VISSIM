"""Score saved predictions against completed native head records, never prediction inputs."""
import hashlib
import json
from pathlib import Path
from evaluation.controllers import lane_plant_runtime, obs150_observation

HERE = Path(__file__).resolve().parent
I = HERE.parent


def main():
    cfg = json.loads((HERE/'candidate_config.json').read_bytes())
    context = lane_plant_runtime.load_sources(cfg['freeway']['lane_plant'])
    cache = HERE/'native_head_targets.json'
    if cache.exists():
        native = json.loads(cache.read_bytes())
        for path, digest in native['pins'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    else:
        native = {'scope':'SC109 native head crossings, future scoring only', 'pins':{}, 'arms':{}}
        for arm in ('hold','release'):
            rows=[]
            for end in (2850,3000,3150):
                path=Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3')/arm/f'decisions_sdmpc31_g_2700_{arm}_s47'/f'state_{end:06d}.json'
                native['pins'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
                raw=json.loads(path.read_bytes())
                derived=obs150_observation.derive(raw,context['obs150'])
                window=derived['head_window']; assert window['clock_complete']
                heads=[h for h in window['heads'] if h['sc']=='109']
                rows.append(dict(start=end-150,end=end,heads=heads))
            native['arms'][arm]=rows
        cache.write_text(json.dumps(native,indent=2),encoding='utf-8')
    targets={}
    for arm,rows in native['arms'].items():
        targets[arm]={sg:sum(h['crossings'] for row in rows for h in row['heads'] if h['sg']==sg)
                      for sg in ('2','5','6','7')}
    result={'native_head_crossings':targets,'models':{},'prediction_inputs_used_future':False}
    for name,label in [('base','sc109_base_v2'),('single_window','sc109_candidate_v2'),
                       ('candidate','sc109_candidate_pool4')]:
        folder=I/('closedloop_recorded2700_lever450_'+label)
        data=json.loads((folder/'summary.json').read_bytes())
        report={}
        for arm,row in data['results'].items():
            entry={k:row[k] for k in ('ttt_omega_veh_h','tracked_outside_residence_veh_h','ttt_with_tracked_outside_veh_h','ramps')}
            entry['delta_omega']=row.get('delta_ttt_omega_veh_h',0.)
            entry['signal_moves']={k:sum(t['vehicles'] for t in row['signal_audit']['transfers'] if t['source']=='movement:'+k)
                                   for k in row['signal_audit']['movement_specs']}
            entry['green']=[{k:v for k,v in cmd['green_times'].items() if k.startswith('SC109')} for cmd in row['commands']]
            report[arm]=entry
        result['models'][name]=report
    result['independent_s29']={}
    for name,label in [('base','sc109_base_s29'),('single_window','sc109_candidate_s29'),
                       ('candidate','sc109_candidate_s29_pool4')]:
        folder=I/('closedloop_recorded4500_lever450_'+label)
        data=json.loads((folder/'summary.json').read_bytes())
        result['independent_s29'][name]={arm:dict(
            omega=row['ttt_omega_veh_h'],delta_omega=row.get('delta_ttt_omega_veh_h',0.),
            outside=row['tracked_outside_residence_veh_h'],signal_audit=row['signal_audit'])
            for arm,row in data['results'].items()}
    result['independent_caveat']='Saved state sensitivity only: held previous greens differ from future executed greens; not a native causal outcome.'
    original=json.loads((I/'closedloop_recorded2700_lever450_rm_pair_s47_cell23_v4/summary.json').read_bytes())
    result['disabled_vs_previous']={arm:result['models']['base'][arm]['ttt_omega_veh_h']-row['ttt_omega_veh_h']
                                    for arm,row in original['results'].items()}
    assert max(map(abs,result['disabled_vs_previous'].values()))<1e-5
    (HERE/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:{a:dict(ttt=r['ttt_omega_veh_h'],delta=r['delta_omega'],departures=r['signal_moves']) for a,r in v.items()} for k,v in result['models'].items()},indent=2))


if __name__=='__main__':
    main()
