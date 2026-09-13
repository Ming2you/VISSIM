"""Explicit-input canonical main preflight; preparation runs no optimizer."""
import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','snapshot','previous','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare-only',action='store_true',help='Stop before actual decide_with_info; no search.')
    mode.add_argument('--decide',action='store_true',help='Explicitly run actual canonical MPC; may be expensive.')
    args=parser.parse_args()
    for path in (args.config,args.snapshot,args.previous):
        if not path.is_file(): raise FileNotFoundError(path)
    output=args.output.resolve(); folder=output.parent/(output.stem+'_files')
    if output.exists() or folder.exists(): raise FileExistsError('Choose a new output: '+str(output))
    if not output.is_relative_to((ROOT/'diagnostics').resolve()): raise ValueError('Output must remain in diagnostics')
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from diagnostics.probe_model_area_integration import replay_provenance,route_information
    tuning=adapter.load_optional_json(str(args.config))
    writer=tuning.get('actuation',{}).get('real_world_signal_control',{}).get('offset_writer','intent_only')
    inputs=(args.config,args.snapshot,args.previous,Path(__file__))
    before=replay_provenance(tuning,*inputs); prepared={}
    original_build=adapter.build_priced_wu_link_controller
    class PreparationComplete(BaseException): pass
    def capture_build(cfg,resolved_tuning):
        controller=original_build(cfg,resolved_tuning)
        if args.prepare_only:
            def stop(state,forecast,previous,cfg_arg):
                from evaluation.controllers.area_runtime import model_inventory
                if not hasattr(state,'_control_area_ledger'): raise ValueError('Explicit area config required')
                state._control_area_ledger.assert_stocks(model_inventory(state,cfg_arg))
                bootstrap=getattr(controller,'price_worker_bootstrap',None) or {}
                prepared.update(reached_actual_main_decide=True,decide_executed=False,
                    horizon_steps=len(forecast),parallel_workers=controller.price_parallel_workers,
                    beta_seconds=cfg_arg.network.control_area_beta_seconds,
                    initial_omega_veh=sum(row['inside'] for row in state._control_area_ledger.stocks.values()),
                    worker_bootstrap={key:bootstrap.get(key) for key in ('module','func')},
                    physical_vehicle_counts=bool(getattr(cfg_arg.network,'physical_vehicle_counts',False)),
                    initial_route_information=route_information(state,cfg_arg))
                raise PreparationComplete()
            controller.decide_with_info=stop
        return controller
    folder.mkdir(parents=True)
    argv=[str(Path(adapter.__file__)),'--state-json',str(args.snapshot.resolve()),
        '--previous-action-json',str(args.previous.resolve()),'--out-action-json',str(folder/'action.json'),
        '--out-action-csv',str(folder/'action.csv'),'--repo-root',str(ROOT/'vendor/NumSim-mine'),
        '--mapping-json',str(ROOT/tuning['mapping_json']),
        '--detector-mapping-json',str(ROOT/tuning['detector_mapping_json']),
        '--calibration-json',str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json',str(args.config.resolve()),'--controller','wu-link','--mode','fast-smoke']
    try:
        with patch.dict(os.environ,{'RW_OFFSET_WRITER':writer}),patch.object(sys,'argv',argv),patch.object(adapter,'build_priced_wu_link_controller',capture_build):
            adapter.main()
    except PreparationComplete:
        if not args.prepare_only or not prepared: raise
    if args.prepare_only:
        if not prepared or (folder/'action.json').exists() or (folder/'action.csv').exists():
            raise AssertionError('Preparation did not stop before decision/output')
    else:
        action=json.loads((folder/'action.json').read_text(encoding='utf-8')); metadata=action['metadata']
        if metadata.get('controller_status')=='fallback_fixed': raise RuntimeError('Actual main fell back: '+str(metadata.get('controller_error')))
        prepared={'reached_actual_main_decide':True,'decide_executed':True,
                  'action_json':str(folder/'action.json'),'action_csv':str(folder/'action.csv'),'metadata':metadata}
    after=replay_provenance(tuning,*inputs)
    if any(after.get(key)!=value for key,value in before.items()): raise AssertionError('Input/source changed')
    prepared.update(implementation='actual canonical adapter.main; original production worker bootstrap',
                    source_sha256=after,source_unchanged=True,config_path=str(args.config.resolve()),
                    snapshot_path=str(args.snapshot.resolve()),previous_path=str(args.previous.resolve()),
                    scope='Preparation validates runtime only; no optimizer result or VISSIM outcome is inferred.')
    with output.open('x',encoding='utf-8') as stream: json.dump(prepared,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(output),'decide_executed':prepared['decide_executed']}))


if __name__=='__main__': main()
