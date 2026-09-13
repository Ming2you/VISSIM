"""Summarize already completed private replays; no model execution or raw run reads."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'diagnostics'


def main():
    inputs=[];rows=[]
    def read(name):
        path=D/name;inputs.append(path)
        return json.loads(path.read_text(encoding='utf-8'))
    for t in (1200,3300):
        a=read(f'known_wout_baseline_current_{t}.json')
        b=read(f'known_wout_replay_final_{t}.json')
        historical=read(f'source_interval_{t}_{t+150}.json')
        prior=read(f'known_wout_replay_{t}.json')
        # Final added guards/metadata did not change valid-input arithmetic.
        assert b['metrics']==prior['metrics']
        assert a['metrics']==historical['model']['metrics']
        assert a['input_objects_unchanged'] and b['input_objects_unchanged']
        assert a['stock_closure'] and b['stock_closure']
        assert a['held_control_all15_exact'] and b['held_control_all15_exact']
        assert not a['source_changes'] and not b['source_changes']
        runtime_diffs={p for p,h in a['source_sha256'].items()
            if p.startswith(('evaluation\\controllers\\','vendor\\'))
            and p in b['source_sha256'] and b['source_sha256'][p]!=h}
        assert not runtime_diffs
        fa=a['metrics']['flow_counts'];fb=b['metrics']['flow_counts']
        changed={k:{'before':fa.get(k,0.),'after':fb.get(k,0.),'delta':fb.get(k,0.)-fa.get(k,0.)}
                 for k in sorted(set(fa)|set(fb)) if abs(fb.get(k,0.)-fa.get(k,0.))>1e-8}
        e8=next(r for r in historical['freeway_cell_comparison']['rows']
                if r['link']=='FW_E' and r['cell_index_zero_based']==8)
        metrics={k:{'before':a['metrics'][k],'after':b['metrics'][k],
                    'delta':b['metrics'][k]-a['metrics'][k]}
                 for k in ('ttt_veh_h','ttd_veh','entered_veh')}
        rows.append({'start_sec':t,'metrics':metrics,'flow_category_changes':changed,
            'before_E8_speed_kph':a['final_E8_speed_kph'],'after_E8_speed_kph':b['final_E8_speed_kph'],
            'before_E9_speed_kph':a['final_E9_speed_kph'],'after_E9_speed_kph':b['final_E9_speed_kph'],
            'observed_E8_speed_kph_at_end_reference_only':e8['observed_speed_kph'],
            'before_ramp_queues':a['final_ramp_queues'],'after_ramp_queues':b['final_ramp_queues'],
            'observed_ramp_queues_reference_only':historical['comparison']['ramp_final_com_veh'],
            'physical_TTT_reference_only':historical['comparison']['residence']['omega']['physical_veh_h'],
            'physical_TD_reference_only':historical['physical']['ttd_observed_plus_terminal_veh'],
            'before_W_out_veh':a['trace'][-1]['W_out_stock'],'after_W_out_veh':b['trace'][-1]['W_out_stock'],
            'current_OFF_matches_historical_metrics_exact':True,'final_guards_preserve_prior_candidate_metrics_exact':True,
            'common_loaded_runtime_source_differences':sorted(runtime_diffs)})
    result={'schema':'known-wout-route-comparison/v1','production_applied':False,
        'scope':'Held150s prediction sensitivity to retained destination aliases and explicit native-unique future direct path prior. Not an actual control improvement or calibrated speed model.',
        'rows':rows,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        'physical_reference_not_used_by_predictor':True,
        'remaining_limitations':['Freeway off group stays cell8 and both R_F_E physical merges stay cell9.',
            'No lane exchange, partial FIFO or route-conditioned freeway sending/receiving state.',
            'Existing legsplit free-exit clock stays coarse and does not simulate all of10773/123.',
            'Only coupled endpoint path and fresh runtime worker tested; no full optimizer/local proxy support claim.',
            'Future direct free destination is the unique native static path through10682, not an observed future route ID.']}
    (D/'known_wout_route_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for row in rows:print(json.dumps({k:row[k] for k in ('start_sec','metrics','observed_E8_speed_kph_at_end_reference_only')},indent=2))


if __name__=='__main__':main()
