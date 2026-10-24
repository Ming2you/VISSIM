"""Rebind the existing urban260 configuration to the user-expanded area."""
import copy,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
HERE=Path(__file__).resolve().parent/'approaches_only';ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.control_area_objective import physical_membership_from_ledger
from evaluation.controllers.control_area_join import turn_membership
from evaluation.controllers.physical_movement_routes import path_membership

def read(p):return json.loads(p.read_bytes())
def data(x):return (json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf8')
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):return s.replace('\\','/')
def strings(x):
    if isinstance(x,str):yield x
    elif isinstance(x,dict):
        for v in x.values():yield from strings(v)
    elif isinstance(x,list):
        for v in x:yield from strings(v)

def main():
    source=HERE.parent.parent/'urban260/config.json';cfg=read(source)
    old=cfg['control_area_objective']['membership_path'];new=str((HERE/'membership.json').relative_to(ROOT)).replace('\\','/')
    physical=physical_membership_from_ledger(read(HERE/'membership.json'))
    route_source=cfg['control_area_objective']['route_contract_path'];routes=read(ROOT/route_source)
    refreshed=0
    for key,row in routes.items():
        if not key.startswith('movement:'):continue
        turns=row.get('physical_turns',[])
        for turn in turns:
            prior=copy.deepcopy(turn)
            turn.update(path_membership(turn['path'],physical) if 'path' in turn else turn_membership(turn,physical))
            refreshed+=int(turn!=prior)
        patterns={(t['source_inside'],t['target_inside'],t['outward_crossings_per_vehicle'],t['inward_crossings_per_vehicle']) for t in turns}
        if len(patterns)==1:
            si,ti,ex,en=patterns.pop()
            row.update(source_inside=si,target_inside=ti,inside_to_inside=float(ti),outside_to_inside=float(ti),
                       outward_crossings_per_vehicle=ex,inward_crossings_per_vehicle=en,
                       status='unique' if len(turns)==1 else 'same_transition',unresolved_reason=None)
        elif patterns:
            row.update(source_inside=None,target_inside=None,inside_to_inside=None,outside_to_inside=None,
                       outward_crossings_per_vehicle=None,inward_crossings_per_vehicle=None,
                       status='mixed_transition',unresolved_reason='Expanded area still requires separate physical branch weights.')
        sides={t['source_inside'] for t in turns}
        if len(sides)==1:
            side=sides.pop();arrival=routes['arrival:'+key.split(':',1)[1]]
            arrival.update(target_inside=side,inside_to_inside=float(side),outside_to_inside=float(side))
    for key,row in routes.items():
        if not key.startswith('input:'):continue
        sources=row.get('physical_sources',[])
        for s in sources:s['inside']=physical[str(s['link'])]
        sides={s['inside'] for s in sources}
        if len(sides)==1:
            side=sides.pop();row.update(status='unique',target_inside=side,event_kind='generation' if side else 'outside_generation',unresolved_reason=None)
        elif sides:row.update(status='mixed_transition',target_inside=None,event_kind='unresolved_generation')
    route_target=HERE/'route_contract.json';route_target.write_bytes(data(routes))
    replacements={norm(old):{'path':new,'sha256':sha((HERE/'membership.json').read_bytes())},
                  norm(route_source):{'path':str(route_target.relative_to(ROOT)).replace('\\','/'),'sha256':sha(route_target.read_bytes())}}
    # Only direct runtime dependencies; never rewrite historic source-config
    # provenance or the existing frozen inputs.
    runtime=copy.deepcopy(cfg)
    for k in ('_repin','notes','_n31_note','_canonical','_canon_note','_ver2_note','description'):runtime.pop(k,None)
    documents={norm(s):read(ROOT/s) for s in set(strings(runtime)) if s.endswith('.json') and (ROOT/s).is_file() and norm(s) not in replacements}
    support_key=norm(cfg['observation']['physical_support_repair'])
    support=copy.deepcopy(documents[support_key])
    detectors=read(ROOT/cfg['detector_mapping_json'])
    area=read(HERE/'membership.json')
    tree=ET.parse(ROOT/area['network']['path']).getroot()
    nodes={x.get('no'):x for x in tree.findall('./links/link')}
    added_support=[]
    for added in area['controlled_intersection_expansion']['added_links']:
        link=added['link'];node=nodes[link];end=node.find('toLinkEndPt')
        if end is None or link in support['link_to_storage']:continue
        target=end.get('lane').split()[0]
        origins=detectors.get('link_to_origins',{}).get(target,[])
        if len(origins)!=1:continue  # Existing route/record projection handles mixed approaches.
        support['link_to_storage'][link]=origins[0]
        support['evidence'][link]={'to_link':target,'physical_triplet':[node.find('fromLinkEndPt').get('lane').split()[0],link,target],
            'reason':'Newly included approach connector has one existing downstream storage; restore its native initial stock channel, no new generation or capacity.'}
        added_support.append(link)
    support['controlled_approach_revision']={'membership_path':new,'initial_stock_only':True,'added_unique_connector_support':added_support,
        'mixed_approaches':'Retain existing physical route/record projection; do not invent equal destination shares.'}
    # The source document remains immutable. Register the revised support first
    # so any pinned references to it are re-bound in the same dependency pass.
    support_target=HERE/'evidence'/Path(support_key).name
    replacements[support_key]={'path':str(support_target.relative_to(ROOT)).replace('\\','/'),'sha256':sha(data(support))}
    documents[support_key]=support
    def rewrite(x):
        if isinstance(x,dict):
            if isinstance(x.get('path'),str) and norm(x['path']) in replacements and 'sha256' in x:
                return {**x,**replacements[norm(x['path'])]}
            return {k:rewrite(v) for k,v in x.items()}
        if isinstance(x,list):return [rewrite(v) for v in x]
        if isinstance(x,str) and norm(x) in replacements:return replacements[norm(x)]['path']
        return x
    for _ in range(len(documents)+1):
        before=copy.deepcopy(replacements)
        for s,d in documents.items():
            revised=rewrite(d)
            if revised!=d or s==support_key:
                target=HERE/'evidence'/Path(s).name
                replacements[s]={'path':str(target.relative_to(ROOT)).replace('\\','/'),'sha256':sha(data(revised))}
        if before==replacements:break
    else:raise AssertionError('Area evidence dependency graph did not converge')
    for s,d in documents.items():
        if s not in replacements:continue
        target=ROOT/replacements[s]['path'];target.parent.mkdir(exist_ok=True)
        raw=data(rewrite(d));assert sha(raw)==replacements[s]['sha256'];target.write_bytes(raw)
    # Rewrite execution/configuration fields, leave the original repin history.
    result={k:(v if k=='_repin' else rewrite(v)) for k,v in cfg.items()}
    assert result['urban']['storage_release_guard']==cfg['urban']['storage_release_guard']
    assert result['urban']['storage_release_guard']['enabled']
    result['description']+=' | User20261006 clarified physical TTT area: controlled approaches included, downstream exit roads not newly added; urban17 storage90 guard and40 lane projection retained.'
    result['_area_revision']={'schema':'controlled-intersection-area-expansion/v1','membership':replacements[norm(old)],
        'previous_config':{'path':str(source.relative_to(ROOT)).replace('\\','/'),'sha256':sha(source.read_bytes())},
        'same_objective_form':'Omega residence only, beta_seconds0; PN/NUF resources unchanged.',
        'runtime_validation':'Requires saved-state checks before freezing/launching.'}
    (HERE/'config.json').write_bytes(data(result))
    (HERE/'preparation.json').write_bytes(data({'replacements':replacements,'physical_turns_reclassified':refreshed,
        'urban_storage_guard':result['urban']['storage_release_guard'],'original_inputs_changed':False}))
    print(json.dumps({'copies':len(replacements)-2,'refreshed_turns':refreshed,'config':str(HERE/'config.json')},ensure_ascii=False))

if __name__=='__main__':main()
