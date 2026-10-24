"""Reconcile native and model departures by physical boundary edge."""
from collections import Counter, defaultdict
from pathlib import Path
import gzip
import hashlib
import json
import pickle
import xml.etree.ElementTree as ET

from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.matched280.review import model_boundary

HERE=Path(__file__).resolve().parent
A=HERE.parent
ROOT=HERE.parents[4]
CACHE=Path('E:/VISSIM_analysis/20261010_exit_timing309')
PINS={}


def raw(path):
    path=Path(path);b=path.read_bytes();PINS[str(path)]=hashlib.sha256(b).hexdigest();return b


def read(path):return json.loads(raw(path))


def boundary_path_candidates(start,target,edges,inside,max_edges=7):
    """Bounded topology witnesses, not reconstructed exact vehicle routes."""
    found=[]
    def walk(path):
        if path[-1]==target:
            outward=[(a,b) for a,b in zip(path,path[1:]) if inside[a] and not inside[b]]
            inward=[(a,b) for a,b in zip(path,path[1:]) if not inside[a] and inside[b]]
            if len(outward)==1 and not inward:found.append((outward[0],path))
            return
        if len(path)-1>=max_edges:return
        for nxt in edges.get(path[-1],()):
            if nxt in path:continue
            walk(path+[nxt])
    walk([start])
    candidates={edge for edge,_ in found}
    return dict(edge=list(next(iter(candidates))) if len(candidates)==1 else None,
                distinct_edges=[list(x) for x in sorted(candidates)],path_count=len(found),
                shortest_edges=min((len(p)-1 for _,p in found),default=None))


def main():
    assert not (HERE/'assessment.json').exists()
    completion=read(CACHE/'completion.json')
    assert completion['status']=='complete_closed_exit_timing_cache'
    cfg,_,_=pickle.loads(raw(A/'citysplit287/forecast2400/initial.pickle'))
    tuning=read(A/'flow279/config_10686_free.json')
    document=read(ROOT/tuning['control_area_objective']['membership_path'])
    inside=physical_membership_from_ledger(document)
    network=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
    tree=ET.fromstring(raw(network))
    edges=defaultdict(set)
    for link in tree.findall('./links/link'):
        fr,to=link.find('fromLinkEndPt'),link.find('toLinkEndPt')
        if fr is not None:
            edges[fr.get('lane').split()[0]].add(link.get('no'))
            edges[link.get('no')].add(to.get('lane').split()[0])
    native={};pair_map={};native_events={}
    for arm in ('hold','city'):
        p=Path(completion['arms'][arm]['cache']);b=raw(p)
        assert hashlib.sha256(b).hexdigest()==completion['arms'][arm]['sha256']
        events=json.loads(gzip.decompress(b))['events']
        native_events[arm]=[r for r in events if r['kind']=='observed_exit']
        groups=defaultdict(lambda:dict(count=0.,cost=0.,observed_pairs=Counter()))
        for r in native_events[arm]:
            pair=(r['from_link'],r['to_link'])
            key='->'.join(pair)
            if key not in pair_map: pair_map[key]=boundary_path_candidates(*pair,edges,inside)
            match=pair_map[key]
            group='->'.join(match['edge']) if match['edge'] else 'unresolved_native_topology'
            row=groups[group];row['count']+=1;row['cost']-=(2850-r['mid_sec'])/3600
            row['observed_pairs'][key]+=1
        native[arm]=dict(groups)
    models={};ownership={}
    for version,folder in [('306',Path('E:/VISSIM_analysis/20261010_sc12_initial306/forecast2400_v2')),
                           ('308',Path('E:/VISSIM_analysis/20261010_sc109_composite308/forecast2400_v2'))]:
        summary=read(folder/'summary.json');models[version]={}
        initial=read(A/'matched280/authority/hold.stocks.json')[0]
        for arm in ('hold','city'):
            response=json.loads(gzip.decompress(raw(folder/(arm+'.response.json.gz'))))
            final={'stocks':{k:dict(inside=v) for k,v in response['residence'][-1]['inside_veh'].items()}}
            account=model_boundary(response,[initial,final],summary['results'][arm]['omega_ttt_veh_h'],cfg)
            grouped=defaultdict(lambda:dict(count=0.,cost=0.,routes=Counter()))
            for key,row in account['routes'].items():
                if abs(row['departed'])<1e-10:continue
                spec=cfg.network.control_area_routes.get(key,{})
                possible=set()
                for turn in spec.get('physical_turns',[]):
                    for e in turn.get('crossing_edges',[]):
                        if e['from_inside'] and not e['to_inside']:possible.add(e['source']+'->'+e['target'])
                group=next(iter(possible)) if len(possible)==1 else 'unresolved_model_physical_route'
                ownership[key]=dict(possible=sorted(possible),group=group)
                g=grouped[group];g['count']+=row['departed'];g['cost']+=row['departure_cost'];g['routes'][key]+=row['departed']
            models[version][arm]=dict(grouped)
    def difference(arms):
        return {key:{field:arms['city'].get(key,{}).get(field,0.)-arms['hold'].get(key,{}).get(field,0.)
                     for field in ('count','cost')} for key in arms['city'].keys()|arms['hold'].keys()}
    nd=difference(native);md={k:difference(v) for k,v in models.items()}
    assert abs(sum(v['cost'] for v in nd.values())-completion['native_delta_reproduced']['cost'])<1e-8
    ranked=[]
    for edge in nd.keys()|md['308'].keys():
        n=nd.get(edge,dict(count=0.,cost=0.));m=md['308'].get(edge,dict(count=0.,cost=0.))
        ranked.append(dict(edge=edge,native=n,model308=m,model306=md['306'].get(edge,dict(count=0.,cost=0.)),
                           model308_minus_native_cost=m['cost']-n['cost']))
    ranked.sort(key=lambda r:abs(r['model308_minus_native_cost']),reverse=True)
    for p in [A/'timing307/README.md',A/'sc109_composite308/completion.json',
              A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3_r2/U7.md',
              A.parent.parent/'upstream_worklog/02_urban_b2/diag_c3/C3_DIAGNOSIS.md',Path(__file__)]:raw(p)
    doc=dict(status='complete_boundary_exit_time_reconciliation',previous_goal_turn='progress308_two450_composite_and_supply_validation',
        goal_complete=False,native=native,model=models,native_delta=nd,model_delta=md,ranked_edge_differences=ranked,
        native_observed_pair_topology=pair_map,model_route_ownership=ownership,
        source_pins=PINS,budget=dict(new_forecasts=0,new_native=0,new_fits=0,fzp_passes_in_preceding_extraction=2),
        limitations=['Bounded local paths are topology witnesses. Unique within7edges is not proof of the complete actual vehicle route.',
                    'All sampled exit costs are retained including unresolved groups; no inferred missing normal outflow.',
                    'Model has only normal modeled departures; native terminal-inferred exits and unexplained disappearances are separate.',
                    'Native5s midpoint and model10s endpoint quadratures differ. Individual edge differences are diagnosis, not standalone causal control effects.',
                    'Same offered demand does not force identical actual admissions. No native future state is used as an input.'])
    (HERE/'assessment.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print('RANKED',json.dumps(ranked[:15],ensure_ascii=False))
    print('UNRESOLVED',[(a,native[a].get('unresolved_native_topology',{})) for a in native])


if __name__=='__main__':main()
