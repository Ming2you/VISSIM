"""Canonical initial projection audit with explicit state/history pairs; no rollout."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]


def inspect_one(config_path,state_path,previous_path):
    from diagnostics.probe_model_area_integration import build_projected,adapter,replay_provenance,route_information
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from evaluation.controllers.area_runtime import model_inventory
    cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config_path,state_path,previous_path,fixture_inputs=False)
    if not hasattr(state,'_control_area_ledger'): raise ValueError('Explicit area config required')
    physical=physical_membership_from_ledger(adapter.load_optional_json(str(ROOT/tuning['control_area_objective']['membership_path'])))
    fw_links={str(link) for row in mapping['freeway_model_links'].values() for link in row['chain_links']}
    counts=raw['vehicle_records']['full_network_link_counts']
    assigned=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    differences={link:count-sum(assigned.get(link,{}).values()) for link,count in counts.items()
                 if physical[link] and link not in fw_links and abs(count-sum(assigned.get(link,{}).values()))>1e-7}
    continuity=continuity_vehicle_counts(state,cfg)
    cell_errors={link:[modeled-row['count'] for modeled,row in zip(values,raw['freeway_segments'][link])]
                 for link,values in continuity.items()}
    raw_omega=sum(count for link,count in counts.items() if physical[link])
    model_omega=sum(row['inside'] for row in state._control_area_ledger.stocks.values())
    exact=bool(getattr(cfg.network,'physical_vehicle_counts',False))
    if exact:
        if adapter._freeway_vehicle_count_by_link(state,cfg)!=continuity or state.freeway_vehicle_count_by_link(cfg.network)!=continuity:
            raise AssertionError('FW getter/model coordinates differ')
        if differences or max(abs(x) for values in cell_errors.values() for x in values)>1e-9 or abs(model_omega-raw_omega)>1e-7:
            raise AssertionError('Exact physical initial stock projection failed')
    state._control_area_ledger.assert_stocks(model_inventory(state,cfg))
    return {'snapshot_sec':state.time_sec,'snapshot_path':str(state_path),'previous_path':str(previous_path),
            'raw_omega_veh':raw_omega,'model_omega_veh':model_omega,
            'urban_physical_assignment_differences':differences,'fw_per_cell_errors_veh':cell_errors,
            'physical_vehicle_counts_enabled':exact,'all_stock_closures_pass':True,
            'initial_area_entries':state._control_area_ledger.metrics.entered_veh,
            'initial_route_information':route_information(state,cfg),
            'source_sha256':replay_provenance(tuning,config_path,state_path,previous_path,Path(__file__))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,action='append',required=True,help='Repeat with corresponding explicit --previous inputs.')
    parser.add_argument('--previous',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError('Choose a new output: '+str(args.output))
    if len(args.snapshot)!=len(args.previous): raise ValueError('Each snapshot needs exactly one explicit previous action')
    rows=[inspect_one(args.config,snapshot,previous) for snapshot,previous in zip(args.snapshot,args.previous)]
    result={'implementation':'installed configure_runtime initial projection only','records':rows,'all_stock_closures_pass':True,
            'scope':'No endpoint/search. Exact geometry follows supplied config; OFF residuals keep original meaning. Route completeness differs from stock closure.'}
    with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(args.output),'snapshots':len(rows)}))


if __name__=='__main__': main()
