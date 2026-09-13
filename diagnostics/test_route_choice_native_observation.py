"""Actual native collector observations qualify route-cohort initialization.

This uses only the recorded native route/position captures. It does not splice
them into a different run's full model snapshot or claim a performance replay.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from types import SimpleNamespace
import csv,hashlib,json,unittest
from diagnostics.test_route_choice_1128 import ROOT,base
from evaluation.controllers import route_choice_corridor as rc
from evaluation.controllers.control_area_objective import ModelAreaLedger


def captures():
    folder=ROOT/'diagnostics/vehicle_route_collector_native_20260910_01'
    route_path=folder/'routes.csv.jsonl';physical_path=folder/'routes.csv.physical.csv'
    routes={float(row['sim_sec_before']):row for row in map(json.loads,route_path.read_text(encoding='utf-8-sig').splitlines())}
    physical=defaultdict(list)
    with physical_path.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            link,lane=row['lane'].rsplit('-',1)
            speed=float(row['speed_kph'])
            physical[float(row['sim_sec'])].append({'veh_no':int(row['veh_no']),'link_no':int(link),'lane_no':int(lane),
                'position_m':float(row['pos_m']),'speed_kph':speed,'stopped':speed==0.})
    return routes,physical,{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (route_path,physical_path)}


def initialize_capture(second,route_envelope,records):
    cfg=deepcopy(base()[0][0])
    cfg.network.route_choice_corridor['unknown_policy']='error'
    for spec in rc._specs(cfg):spec['unknown_policy']='error'
    counts=Counter(str(r['link_no']) for r in records)
    table={key:target for spec in rc._specs(cfg) for key,target in rc._projection_table(spec).items()}
    stocks=Counter()
    for spec in rc._specs(cfg):
        for key in spec['prefix_links']:stocks[spec['prefix_storage']]+=counts[key]
        for key in spec['local_links']:stocks[spec['local_storage']]+=counts[key]
    raw={'sim_sec':second,'vehicle_routes':deepcopy(route_envelope),'vehicle_records':{
        'complete':True,'collection_count_before':len(records),'collection_count_after':len(records),'record_count':len(records),
        'capture_sim_sec_before':second,'capture_sim_sec_after':second,'full_network_link_counts':dict(counts),'records':records}}
    state=SimpleNamespace(time_sec=second,
        urban_link_storage={key:cap-stocks[key] for key,cap in cfg.network.route_choice_corridor['capacity_veh'].items()},
        urban_arrival_buffer={},urban_storage_release_buffer={},
        local_observation_summary={'projection_diagnostics':{'physical_stock_assignment_by_link':{
            key:{'storage:'+target:counts[key]} for key,target in table.items()}}},
        _control_area_ledger=ModelAreaLedger({'storage:'+key:{'inside':value,'outside':0.} for key,value in stocks.items()}))
    detail=rc.initialize(state,cfg,raw)
    return cfg,state,detail,raw


class NativeObservationTests(unittest.TestCase):
    def test_actual_native_captures_require_no_unknown_posterior(self):
        routes,physical,hashes=captures();outputs={}
        for second,envelope in routes.items():
            cfg,state,detail,raw=initialize_capture(second,envelope,physical[second])
            self.assertEqual(detail['route_choice_held_unknown_route_veh'],0.,second)
            self.assertEqual(detail['route_choice_prediction_route_complete'],1.,second)
            self.assertEqual(state._control_area_ledger.event_count,0)
            self.assertEqual(sum(c['vehicles'] for c in state.route_choice_corridor_state['cohorts']),sum(detail['route_choice_stock_veh'].values()))
            outputs[str(second)]={**detail,'stages':dict(Counter(c['stage'] for c in state.route_choice_corridor_state['cohorts'])),
                'origins':dict(Counter(c['source'] for c in state.route_choice_corridor_state['cohorts']))}
        self.assertGreater(sum(outputs['1050.0']['route_choice_stock_veh'].values()),0.)
        (ROOT/'diagnostics/route_choice_native_observation_qualification.json').write_text(json.dumps({
            'scope':'actual native collector route/position initialization only, not a full model snapshot or performance arm',
            'sources_sha256':hashes,'captures':outputs},indent=2)+'\n',encoding='utf-8')

    def test_1128_past_choice_route_loss_fails_instead_of_redrawing(self):
        routes,physical,_=captures();envelope=deepcopy(routes[1050.]);records=physical[1050.]
        positions={r['veh_no']:r for r in records}
        removed=[]
        for row in envelope['records']:
            physical_row=positions[row['veh_no']]
            if row['route_decision_no']==1128 and str(physical_row['link_no'])=='1220000102' and physical_row['position_m']>20.576829873567828:
                removed.append(row['veh_no'])
                row.update(route_decision_no=None,route_no=None,route_decision_type=None)
        self.assertTrue(removed)
        with self.assertRaisesRegex(ValueError,'Current1128 route required'):
            initialize_capture(1050.,envelope,records)


if __name__=='__main__':unittest.main()
