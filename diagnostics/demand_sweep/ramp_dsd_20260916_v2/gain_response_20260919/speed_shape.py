"""Test whether a missing within-cell speed distribution explains VSL silence.

This is a bounded diagnostic closure, not a lane-changing dynamics model.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.extract_observations import Observer
from diagnostics.analyze_no_control_corridors import native_frames
import canonical_harness as ch
from collections import defaultdict
import time
import statistics
import argparse
import json

HERE=Path(__file__).resolve().parent


def extract():
    out=HERE/'speed_shapes_v1';out.mkdir(exist_ok=False)
    runs={13:H/'rules_4500_v1/run_none',23:H/'rules_4500_s23_v1/run_none',
          33:H/'state_response_20260919/native_s33_v1/run_none'}
    for seed,folder,_,_ in CASES:
        data=e.ObservationData(folder);observer=Observer(data.geometry);saved={};evidence={}
        run=runs[seed]
        assert e.load(run/'run.json')['completed'] and e.load(run/'fixed_validation.json')['passed']
        for sec,frame in native_frames(run/'vissim_eval/baseline_001.fzp',evidence,deadline=time.monotonic()+600):
            if sec not in [900,1650,2400,3600]:continue
            speeds=defaultdict(list)
            for r in frame.values():
                location=observer.locate(r)
                if location:speeds[location[:2]].append(r[3])
            rows=[]
            for observed in data.cells[sec]:
                key=(observed['road'],observed['cell']);values=speeds[key]
                assert len(values)==observed['n_veh']
                if values:assert abs(statistics.mean(values)-observed['v_kmh'])<1e-8
                rows.append({'road':key[0],'cell':key[1],'speeds_kmh':values})
            saved[str(sec)]=rows
        e.save(out/f's{seed}.json',saved)
        e.save(out/f'evidence_s{seed}.json',{'file':str((run/'vissim_eval/baseline_001.fzp').relative_to(e.ROOT)),**evidence,
            'only_saved_features':'Current vehicle speed distribution at each cutoff; no within-horizon state updates'})
        print('EXTRACTED speed shapes',seed,evidence['rows'],flush=True)


def main():
    out=HERE/'speed_shape_trial_v1';out.mkdir(exist_ok=False)
    params=e.load(MODEL/'selected_parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    actual=e.load(H/'merge_drain_response_20260919/native_audit_v1/result.json');results={}
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,MODEL/'config.json')
        shapes=e.load(HERE/f'speed_shapes_v1/s{seed}.json')[str(start)]
        samples={r['cell']:r['speeds_kmh'] for r in shapes if r['road']=='FW_E'}
        ratios={i:[v/statistics.mean(vs) for v in vs] if vs and statistics.mean(vs)>0 else [1.]
                for i,vs in samples.items()}
        protocol=e.load(bank/'protocol.json');byarm={}
        for arm in ARMS:
            reference=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
            seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
            def command(t):
                i=int((t-start)//150)
                return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
            w=e.window(data,model,start,'history_forecast',profile,command)
            original_config=model._config
            def config(road,parameters):
                cfg=original_config(road,parameters)
                if road=='FW_E':
                    for i,p in enumerate(cfg.network.freeway_segment_params[road]):p['_gain_speed_ratios']=ratios[i]
                return cfg
            original_desired=ch.accounting._mn.effective_desired_speed_kmh
            def desired(*args):
                ctx=ch.adapter._FW_SEG_CTX;p=ctx['p'] if ctx['armed'] else {}
                ratios_=p.get('_gain_speed_ratios')
                if args[5] and ratios_:
                    no_cap=list(args);no_cap[5]=False
                    mean=original_desired(*no_cap);cap=(1.+args[4])*float(args[3])
                    return statistics.mean(min(mean*r,cap) for r in ratios_)
                return original_desired(*args)
            model._config=config;ch.accounting._mn.effective_desired_speed_kmh=desired
            try:pred=e.simulate(model,w,params)
            finally:model._config=original_config;ch.accounting._mn.effective_desired_speed_kmh=original_desired
            baseline=e.load(HERE/f'fit_v2/prediction_{seed}_baseline_{arm}.json')
            if arm in ['none','rm_ramp']:
                assert json.loads(json.dumps(pred))==baseline, (seed,arm,'inactive VSL must be exactly unchanged')
            byarm[arm]={'parts':parts(pred),'state_score':e.score_rollout(reference,start,pred,'FW_E'),
                'vsl_binding':next(r['vsl_binding_audit'] for r in pred['diagnostics']['roads'] if r['road']=='FW_E')}
            e.save(out/f'prediction_{seed}_{arm}.json',pred)
        deltas={arm:{k:byarm[arm]['parts'][k]-byarm['none']['parts'][k] for k in byarm[arm]['parts']} for arm in ARMS[1:]}
        for d in deltas.values():d['total']=sum(d.values())
        results[str(seed)]={'arms':byarm,'deltas':deltas,'native_deltas':actual[str(seed)]['delta_1s']}
        print('SHAPE',seed,{a:round(d['total'],5) for a,d in deltas.items()},flush=True)
    e.save(out/'results.json',results)
    e.save(out/'protocol.json',{'formula':'E[min(V_equilibrium * current_speed / current_mean_speed, command)]',
        'initial_state_only':True,'parameters_fitted':0,'cost_or_capacity_bonus':False,
        'default_unchanged':True,'native_runs_started':0,
        'limitations':'Frozen normalized speed distribution is a diagnostic closure. It does not predict lane exchange, desired-speed cohort advection or within-horizon variance dynamics. Not adopted merely because VSL starts affecting speed.',
        'inactive_vsl_full_prediction_exact':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--extract',action='store_true')
    if parser.parse_args().extract:extract()
    else:main()
