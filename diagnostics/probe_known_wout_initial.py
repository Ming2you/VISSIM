"""Classify the existing W_out stock by current native routes, no rollout."""
from collections import Counter
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected
from diagnostics.known_wout_fixtures import input_path
from evaluation.controllers.vehicle_routes import complete_vehicle_routes
from evaluation.controllers.projection_support import complete_records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New diagnostic output; historical classification is never overwritten')
    output=parser.parse_args().output.resolve()
    if not output.is_relative_to(ROOT/'diagnostics'): raise ValueError('Diagnostic output required')
    if output.exists(): raise FileExistsError(output)
    from diagnostics.probe_known_wout_replay import provenance
    config=ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
    tree=ET.parse(ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx').getroot()
    native={}
    for d in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
            native[d.get('no')+':'+r.get('no')]={'decision':d.attrib,'route':r.attrib,
                'path':[d.get('link')]+[x.get('key') for x in r.findall('./linkSeq/intObjectRef')]+[r.get('destLink')]}
    cases=[]
    for sec in (1200,3300):
        sp,prev=input_path(f'state_{sec:06d}.json'),input_path(f'action_{sec-150:06d}.json')
        cfg,state,detectors,tuning,raw,mapping,metadata=build_projected(config,sp,prev,fixture_inputs=False)
        assignments=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
        storage='SC1004_W_out'; key='storage:'+storage
        supports={p:a for p,a in assignments.items() if a.get(key,0)>0}
        current=complete_vehicle_routes(raw,required=True); records=[]
        for r in complete_records(raw):
            if str(r['link_no']) not in supports: continue
            tag=current[r['veh_no']]; identity=(str(tag['route_decision_no'])+':'+str(tag['route_no'])) if tag['route_decision_type']=='STATIC' else 'unresolved'
            records.append(dict(r,current_route=identity))
        n=cfg.network.urban_link_storage_veh[storage]-state.urban_link_storage[storage]
        # Require exclusive physical ownership before assigning per-ID subsets.
        exclusive=all(set(a)=={key} for a in supports.values())
        assert exclusive and len(records)==n
        cases.append({'sim_sec':sec,'source':str(sp.relative_to(ROOT)),'N':n,'supports':supports,
            'route_counts':dict(Counter(r['current_route'] for r in records)), 'records':records,
            'release_buffer':state.urban_storage_release_buffer.get(storage,{}),
            'arrival_buffer':state.urban_arrival_buffer.get(storage,{}),
            'direct_tail_by_offramp':cfg.network.offramp_direct_tail_by_offramp,
            'sink_spec':cfg.network.boundary_out_ramp_split[storage],
            'receiving_movements':{m:s for m,s in cfg.network.urban_movements.items() if s.get('receiving_link')==storage},
            'source_sha256':provenance(config,sp,prev,Path(__file__))})
    used={r['current_route'] for c in cases for r in c['records'] if r['current_route']!='unresolved'}|{'1130:3','1135:2','1135:3','1135:4'}
    report={'schema':'known-wout-initial-fixture/v1','cases':cases,'native_routes':{k:native[k] for k in sorted(used)},
        'scope':'Complete paused current records and exclusive existing storage ownership; no forecast/endpoint, classification not yet a routing correction.'}
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:c[k] for k in ('sim_sec','N','supports','route_counts','release_buffer','direct_tail_by_offramp')} for c in cases],indent=2))

if __name__=='__main__': main()
