"""Build a physical evaluation area without altering canonical player ownership.

Only verified short IC transfer roads and direct connectors between already
inside road endpoints are added. No graph walk through uncontrolled city roads.
"""
from pathlib import Path
import json, hashlib, sys, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from protected_ttt_from_fzp_20260828 import link_sets

NETWORK = 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
TERRITORY = 'outputs/urban_player_territory_v2_20260907.json'
DETECTOR = 'evaluation/real_world_modi_control_ver2_20260907/detector_local_mapping_ver2_20260907.json'
MAPPING = 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
RAMPS = 'outputs/freeway_ramp_split_v2_20260907.json'
PN = 'outputs/pn_boundary_turns_v2_20260907.json'
SHA = '085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317'

def digest(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def read(p): return json.loads((ROOT / p).read_text(encoding='utf-8'))
def sorted_ids(xs): return sorted(xs, key=int)

def build():
    assert digest(NETWORK) == SHA, 'Re-review geometry before changing the pinned network.'
    tree = ET.parse(ROOT / NETWORK)
    links = {x.get('no'):x for x in tree.findall('.//links/link')}
    connectors = {}
    outgoing = {}
    for no, x in links.items():
        f, t = x.find('fromLinkEndPt'), x.find('toLinkEndPt')
        if f is None or t is None: continue
        a, b = f.get('lane').split()[0], t.get('lane').split()[0]
        connectors[no] = {'connector':no, 'from_link':a,'to_link':b,'from_pos_m':float(f.get('pos')),'to_pos_m':float(t.get('pos'))}
        outgoing.setdefault(a,[]).append(no)
    sets = link_sets(ROOT / TERRITORY, ROOT / DETECTOR)
    ownership_union = sets['controlled'] | sets['freeway'] | sets['ramp']
    territory = read(TERRITORY)['territory']
    boundary = read(PN)
    owners = {}
    for sc, legs in territory['urban'].items():
        for leg, ids in legs.items():
            zone = boundary['leg_zone'][sc+'|'+leg]['zone']
            for link in ids: owners.setdefault(link,set()).add(zone)
    perimeter = {link for link,zones in owners.items() if '경계면' in zones}
    pn_internal = {link for link,zones in owners.items() if '내부' in zones} - perimeter
    base = pn_internal | sets['freeway'] | sets['ramp']
    missing = base - links.keys()
    assert not missing, f'Unknown canonical physical elements: {sorted_ids(missing)}'
    inside = set(base)
    # A canonical PN turn crosses the stopline on connector entry. Signal-owner
    # territory often retains that outgoing connector; it is not the PN border.
    turn_connector_changes = []
    for turn in boundary['turns']:
        no = turn['connector']
        want = turn['class'] in {'internal','inflow'}
        before = no in inside
        if want: inside.add(no)
        else: inside.discard(no)
        if before != want: turn_connector_changes.append({'connector':no,'class':turn['class'],'inside':want})
    # Explicitly reviewed route paths, verified against each connector endpoint.
    corridors = [
        {'road':'31','rationale':'SC1001 controlled exits 29/37/40 and FW-owned78 enter this shared approach. Route1137 continues to FW_E via10484 or FW_W via10774→124→10480; external branch10704→79 remains outside.',
         'paths':[['29','10119','31','10484','24'],['37','10121','31','10774','124','10480','26'],['40','10698','31'],['78','10703','31']]},
        {'road':'124','rationale':'Ver2 split continuation of31 and landing of FW_E off10483; returns to FW_W through10480. External branch10775→125 is the exit, not entry to124.',
         'paths':[['31','10774','124','10480','26'],['119','10483','124']]},
        {'road':'68','rationale':'SC1004 controlled exits46/52/66 enter this shared approach. Route1135 continues to FW_E via10681 or FW_W via10772→121→10646.',
         'paths':[['46','10625','68','10681','2'],['52','10629','68','10772','121','10646','120'],['66','10633','68']]},
        {'road':'121','rationale':'Ver2 continuation of68 and FW_E off10682 landing. Returns to FW_W through10646. External branch10773→123 remains outside.',
         'paths':[['68','10772','121','10646','120'],['2','10682','121']]},
        {'road':'69','rationale':'Shared 1746m input approach to metered10644 and controlled70/71/75 (route1134). Count its physical waiting vehicles once within the evaluated ramp approaches; player ownership stays unassigned.',
         'paths':[['69','10644','120'],['69','10637','70','10639','2'],['69','10640','71'],['69','10636','75']]},
        {'road':'32','rationale':'PN boundary approach also provides internal FW↔PN transfer through split continuation129→127; include shared physical corridor, not every boundary leg of controlledSC.',
         'paths':[['32','10482','120'],['32','10778','129','10777','127','10368','39']]},
        {'road':'129','rationale':'Continuation of32, receives FW_W off10491 and gives FW_E on10490; extends to PN through127.',
         'paths':[['26','10491','129','10490','119'],['129','10777','127','10118','30']]},
        {'road':'127','rationale':'FW_E off10481 landing reaches PN internal30/39; route1117 external branch10695→38 remains outside.',
         'paths':[['2','10481','127','10118','30'],['127','10368','39']]},
        {'road':'70','rationale':'FW_W off10638 landing and FW_E on10639 shared road, connecting via126→71 to PN.',
         'paths':[['120','10638','70','10639','2'],['70','10776','126','10641','71','10635','47']]},
        {'road':'126','rationale':'FW_E off10643 landing and continuation70 reaches PN through71.',
         'paths':[['2','10643','126','10641','71','10634','56'],['70','10776','126']]},
        {'road':'71','rationale':'The short junction approach joins FW landing corridor126 to PN47/56; outward branch10642→67 remains outside.',
         'paths':[['126','10700','71','10635','47']]},
        {'road':'336','rationale':'Canonical internal PN turn10528 explicitly walks this unowned carriageway to internal1210014303. Include this single verified internal gap; no ownership reassignment.',
         'paths':[['1220011503','10528','336','10529','1210014303']]},
    ]
    for c in corridors:
        assert c['road'] in links and c['road'] not in connectors
        inside.add(c['road'])
        for p in c['paths']:
            for i in range(1,len(p),2):
                edge = connectors[p[i]]
                assert (edge['from_link'],edge['to_link']) == (p[i-1],p[i+1]), p
    # Canonical PN destination semantics walk through unowned carriageways,
    # stopping at the first owned leg (derive_pn_boundary_turns.dest_zone).
    # Turn that rule into auditable short internal paths, not a city-wide fill.
    bridge_paths=[]
    fixed_inside=set(inside)
    def bridge_walk(road, path, seen, hops):
        if hops <= 0: return
        for conn in outgoing.get(road,[]):
            dest=connectors[conn]['to_link']
            if dest in seen: continue
            next_path=path+[conn,dest]
            if dest in fixed_inside:
                if len(next_path)>3: bridge_paths.append(next_path)
            elif dest not in owners:
                bridge_walk(dest,next_path,seen|{dest},hops-1)
    for road in sorted_ids(k for k in fixed_inside if k not in connectors):
        bridge_walk(road,[road],{road},6)
    bridge_elements={x for path in bridge_paths for x in path}-inside
    inside.update(bridge_elements)
    closure = sorted_ids(c for c,e in connectors.items() if e['from_link'] in inside and e['to_link'] in inside and c not in inside)
    inside.update(closure)
    transitions = []
    for c,e in connectors.items():
        flags = [e['from_link'] in inside, c in inside, e['to_link'] in inside]
        if len(set(flags)) <= 1: continue
        rec = dict(e) | dict(zip(['from_inside','connector_inside','to_inside'],flags))
        rec['source_inside'], rec['target_inside'] = flags[0],flags[2]
        rec['outward_edges'] = []
        rec['inward_edges'] = []
        path = [e['from_link'],c,e['to_link']]
        for i in range(2):
            if flags[i] and not flags[i+1]: rec['outward_edges'].append([path[i],path[i+1]])
            elif not flags[i] and flags[i+1]: rec['inward_edges'].append([path[i],path[i+1]])
        transitions.append(rec)
    mapping = read(MAPPING)
    terminals = {str(x['chain_links'][-1]) for x in mapping['freeway_model_links'].values()}
    terminals.update(k for k in inside if k not in connectors and not outgoing.get(k))
    assert terminals <= inside
    paths_verified = []
    incoming_paths_verified = []
    for c in corridors:
        for p in c['paths']:
            membership = [k in inside for k in p]
            assert True in membership, p
            assert all(membership[membership.index(True):]), p
            (paths_verified if all(membership) else incoming_paths_verified).append(p)
    ramps = read(RAMPS)
    ramp_checks=[]
    for kind in ['on_ramps','off_ramps']:
        for r in ramps[kind]:
            e=connectors[r['connector']]
            assert e['from_link']==r['from_link'] and e['to_link']==r['to_link']
            internal = all(k in inside for k in [r['from_link'],r['connector'],r['to_link']])
            if kind=='on_ramps': assert internal, r
            ramp_checks.append({'kind':kind,'name':r['name'],**e,'inside_to_inside':internal,'to_inside':r['to_link'] in inside})
    routes=[]
    for d in tree.findall('.//vehicleRoutingDecisionStatic'):
        if d.get('link') not in {c['road'] for c in corridors}: continue
        for r in d.findall('.//vehicleRouteStatic'):
            routes.append({'decision':d.get('no'),'from_link':d.get('link'),'route':r.get('no'),'destination':r.get('destLink'),'sequence':[z.get('key') for z in r.findall('.//intObjectRef')],'relflow_raw':r.get('relFlow','')})
    return {
        'schema':'control-area-membership/v1',
        'definition':'Physical union of canonical PN internal links (perimeter priority), controlled freeway and verified IC transfer corridors. Canonical inflow/outflow turn connectors place the PN boundary at stoplines; corridor closure makes urban↔freeway transfer internal. Each vehicle is counted once by physical link. Ownership files are unchanged.',
        'network':{'path':NETWORK,'sha256':SHA},
        'sources':[{'path':p,'sha256':digest(p)} for p in [TERRITORY,PN,DETECTOR,MAPPING,RAMPS,'diagnostics/build_control_area_membership.py']],
        'counts':{'pn_internal':len(pn_internal),'pn_perimeter':len(perimeter),'base_unique':len(base),'corridor_roads_added':len(corridors),'canonical_unowned_internal_bridge_elements_added':len(bridge_elements),'direct_internal_connectors_added':len(closure),'inside_total':len(inside),'outside_total':len(links.keys()-inside)},
        'pn_internal_links':sorted_ids(pn_internal),'pn_perimeter_links':sorted_ids(perimeter),
        'comparison_controlled_owner_union_links':sorted_ids(ownership_union),
        'canonical_turn_connector_changes':turn_connector_changes,
        'inside_links':sorted_ids(inside),'outside_links':sorted_ids(links.keys()-inside),
        'corridor_additions':corridors,
        'direct_internal_connector_additions':[connectors[k] for k in closure],
        'unowned_internal_bridge_paths':bridge_paths,
        'unowned_internal_bridge_elements_added':sorted_ids(bridge_elements),
        'unowned_internal_bridge_rule':'At most6connector hops from an inside road through unowned roadways to the first inside road. Stop immediately at an owned outside/perimeter road. This applies canonical PN downstream-owner semantics without changing player ownership.',
        'connector_transitions':sorted(transitions,key=lambda x:int(x['connector'])),
        'natural_inside_terminal_links':sorted_ids(terminals),
        'terminal_inside_links':sorted_ids(terminals),
        'terminal_rule':'Freeway chain tails from pinned control mapping, plus inside road links having no outgoing physical connectors. A disappearance elsewhere is unknown removal, not a completed crossing. Last records at simulation end are right-censored.',
        'ramp_checks':ramp_checks,'verified_all_inside_paths':paths_verified,'verified_incoming_paths':incoming_paths_verified,
        'mixed_transfer_road_routes':routes,
        'unresolved':[],
        'limitations':[
            {'issue':'Fixed whole-link spatial boundary includes through and external-destination vehicles while they share31/68/69/121/124.','treatment':'They are inside until a listed outward edge is crossed. No route-identity-dependent stock weight; this is a deliberate spatial area.'},
            {'issue':'Natural VISSIM removals (e.g. incomplete lane change) can disappear from an inside link.','treatment':'Count disappearance as completed only with endpoint/terminal evidence; report unknown_removal separately.'},
            {'issue':'Five-second FZP sampling can skip a short outside excursion and return.','treatment':'Report observed crossing count and missing/ambiguous transitions; do not assert exact events without transition reconstruction or higher-resolution logging.'},
            {'issue':'Model reservoirs may combine physical links on both sides of this area.','treatment':'Do not assign binary model membership by name; expose mixed memberships and derive movement transfers before changing live objective.'}
        ]
    }

if __name__=='__main__':
    doc=build()
    target=ROOT/'diagnostics/control_area_membership.json'
    target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'path':str(target),'counts':doc['counts'],'natural_inside_terminal_links':doc['natural_inside_terminal_links'],'ramp_checks':doc['ramp_checks']},ensure_ascii=False,indent=2))
