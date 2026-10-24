"""Pin positional routing/head evidence before any SC107 calibration candidate."""
from collections import Counter
from pathlib import Path
import gzip, hashlib, json, pickle, xml.etree.ElementTree as ET
from evaluation.controllers import obs150_contract as oc

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]
OUT=Path('E:/VISSIM_analysis/20261010_sc107_composition312')
PINS={}

def read_bytes(path):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest();return b


def connector_support(node):
    start=node.find('fromLinkEndPt');link,lane=start.get('lane').split()
    return dict(link=link,pos=float(start.get('pos')),
        lanes=list(range(int(lane),int(lane)+len(node.findall('./lanes/lane')))))


def reachable(row, geometry):
    return [name for name,g in geometry.items() if row['lane_no'] in g['lanes'] and row['position_m']<=g['pos']+1e-6]


def main():
    done=json.loads(read_bytes(OUT/'retained_completion.json'))
    data_bytes=read_bytes(done['cache']);assert hashlib.sha256(data_bytes).hexdigest()==done['cache_sha256']
    past=json.loads(gzip.decompress(data_bytes))
    network=next(p for p in past['source_pins'] if p.endswith('.inpx'))
    tree=ET.fromstring(read_bytes(network));assert PINS[network]==past['source_pins'][network]
    links={l.get('no'):l for l in tree.findall('./links/link')}
    geom={k:dict(connector=c,**connector_support(links[c])) for k,c in [('through','10023'),('left','10622'),('right','10616')]}
    decision=tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1061']")
    entries={c:float(links[c].find('toLinkEndPt').get('pos')) for c in ('10499','10621')}
    assert all(links[c].find('toLinkEndPt').get('lane').split()[0]==decision.get('link') for c in entries)
    folder=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
    raw=json.loads(read_bytes(folder/'state_002400.json'))
    physical=[r for r in raw['vehicle_records']['records'] if r['link_no']==1220000201]
    rows=[dict(r,eligible_connectors=reachable(r,geom)) for r in physical]
    cfg,state,forecast=pickle.loads(read_bytes(A/'citysplit287/forecast2400/initial.pickle'))
    provenance=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['1220000201']
    model={m:dict(spec=s,queue=state.urban_movement_queue[m],capacity=cfg.network.movement_capacity_by_movement_veh_h[m])
        for m,s in cfg.network.urban_movements.items() if m.startswith('SC107_W')}
    native={}
    folders={'hold':folder,'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
    for arm,f in folders.items():
        counts=Counter();events=[]
        for at in (2550,2700,2850):
            r=json.loads(read_bytes(f/f'state_{at:06}.json'));bundle=oc.load_bundle(r)
            detectors,_=oc.read_detector_csv(bundle.obs['detector_config']['path'],bundle.obs['detector_config']['sha256'])
            read_bytes(bundle.obs['detector_config']['path']);read_bytes(f/bundle.obs['mer']['chunk'])
            w=oc.assign_window(bundle.obs,bundle.mer_rows)
            for d in detectors:
                if d.role!='head' or d.link!=1220000201:continue
                sg=oc.parse_head_ref(d.ref)[2]
                assert w.tails[d.dcp_no]==0,'Uncovered final detector second'
                for e in w.entries[d.dcp_no]:
                    if 2400<=e.t_entry<2850:
                        counts[(str(d.lane),sg)]+=1
                        events.append(dict(vehicle=e.veh,time=e.t_entry,lane=d.lane,sg=sg))
        b=json.loads(gzip.decompress(read_bytes(Path('E:/VISSIM_analysis/20261010_exit_timing309')/(arm+'.json.gz'))))
        missing=[e for e in b['events'] if e['from_link']=='1220000201' and e['kind']=='disappeared_inside' and 2400<=e['mid_sec']<2850]
        native[arm]=dict(head_counts={f'lane{k[0]}_sg{k[1]}':v for k,v in counts.items()},head_events=events,
            head_time_cost=-sum(2850-e['time'] for e in events)/3600,
            unclassified_disappearances=missing,unclassified_disappearance_count=len(missing),
            unclassified_inventory_removal_cost=-sum(2850-e['mid_sec'] for e in missing)/3600)
    unsupported=[r for r in rows if not r['eligible_connectors']]
    summary=dict(status='confirmed_sc107_position_and_head_phase_contract_mismatch',goal_complete=False,
        adopted=False,geometry=geom,current_sec=2400,current_stock=rows,projection=provenance,model_movements=model,
        current_stopped_count=sum(r['stopped'] for r in rows),current_right_reachable_count=sum('right' in r['eligible_connectors'] for r in rows),
        unsupported_current_count=len(unsupported),unsupported_current_vehicles=[r['veh_no'] for r in unsupported],
        through_lane5_also_allowed=5 in geom['through']['lanes'],
        route_decision=dict(link=decision.get('link'),pos=float(decision.get('pos')),incoming_landing_positions=entries,
            entrants_land_after_decision=all(pos>float(decision.get('pos')) for pos in entries.values())),
        past_head_turn_counts=past['head_turn_counts'],native_validation=native,
        paired_head_time_cost_delta=native['city']['head_time_cost']-native['hold']['head_time_cost'],
        paired_unclassified_removal_cost_delta=native['city']['unclassified_inventory_removal_cost']-native['hold']['unclassified_inventory_removal_cost'],
        scope=['Physical geometry and current records are available at initialization.',
            'Past1800..2250 witnesses end strictly before2400; achieved turns do not establish future demand fractions.',
            'Future2400..2850 head events and boundary cache are diagnosis only, never forecast input.',
            'No inference that lane5 vehicles changed lane; through connector itself spans2..5.',
            'No inference that unresolved disappearance is a normal exit or an explicit VISSIM deletion.',
            'Do not move native decision/connector in immutable same-network comparison.',
            'A parameter-only service increase cannot repair a head-phase/destination mismatch.'],
        budget=dict(additional_closed_fzp_passes=1,total312_closed_passes=2,new_forecasts=0,new_native=0,coefficient_fits=0),
        next_action='Use a finite physical SC107 pre-diverge/post-diverge head/lane stock contract; preserve positive observed stock with unresolved destinations. Verify phase5-to-through discharge and pre-head right service separately before any whole-gain calibration. Existing simple beta queue projection is insufficient here.')
    read_bytes(Path(__file__));summary['source_pins']=PINS
    (HERE/'assessment.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:summary[k] for k in ('status','current_stopped_count','current_right_reachable_count','unsupported_current_count','paired_head_time_cost_delta','paired_unclassified_removal_cost_delta','route_decision')},ensure_ascii=False))
    print('HEADS',{a:r['head_counts'] for a,r in native.items()})


if __name__=='__main__':main()
