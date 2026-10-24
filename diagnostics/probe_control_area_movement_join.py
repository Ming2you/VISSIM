"""Build the physical join and observe actual accepted vendor urban transfers."""
from collections import Counter,defaultdict
from pathlib import Path
import ast
import copy
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from diagnostics.probe_model_area_integration import build_projected
from evaluation.controllers.control_area_join import build_movement_join,route_contract
from src.models import urban_queue_model
from src.models.state import ControlAction


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def source(path):return {'path':str(path),'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}


def accepted_movements(state,cfg,control,demand):
    """Read actual transfer locals without changing vendor code or runtime state.

    The trace hook is diagnostic only; no production controller uses it. It
    records the value immediately after the vendor's min(before, departed).
    """
    path=Path(urban_queue_model.__file__).resolve()
    tree=ast.parse(path.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='urban_substep')
    line=None
    for node in ast.walk(function):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='actual' for t in node.targets):
            if ast.unparse(node.value)=='min(before, departed)':line=node.end_lineno+1
    if line is None:raise ValueError('Vendor actual accepted movement assignment changed')
    observed=Counter()
    def trace(frame,event,arg):
        if event=='line' and frame.f_code.co_filename==str(path) and frame.f_lineno==line:
            value=float(frame.f_locals['actual'])
            if value>0:observed[str(frame.f_locals['movement'])]+=value
        return trace
    old=sys.gettrace()
    projected=copy.deepcopy(state)
    try:
        sys.settrace(trace)
        urban_queue_model.urban_substep(projected,control,demand,cfg,
            urban_step_index=int(round(state.time_sec/cfg.simulation.T_u_sec)))
    finally:sys.settrace(old)
    return dict(observed)


def main():
    turns=read('outputs/pn_boundary_turns_v2_20260907.json')
    membership=read('diagnostics/control_area_membership.json')
    network=ET.parse(ROOT/membership['network']['path']).getroot()
    links={x.get('no'):x for x in network.findall('./links/link')}
    successors=defaultdict(list)
    for connector,link in links.items():
        origin=link.find('fromLinkEndPt');target=link.find('toLinkEndPt')
        if origin is not None and target is not None:
            successors[origin.get('lane').split()[0]].append((connector,target.get('lane').split()[0]))
    for turn in turns['turns']:
        connector=links[str(turn['connector'])]
        actual=(connector.find('fromLinkEndPt').get('lane').split()[0],connector.find('toLinkEndPt').get('lane').split()[0])
        if actual!=(str(turn['from_link']),str(turn['to_link'])):raise ValueError('Canonical turn endpoint mismatch')
    outputs=[]
    for run,t in [('codex_nc_s13_6056c94_20260909_retry',900),('codex_n7_s13_6056c94_20260909',3300)]:
        base=Path('evaluation/runs')/run/('decisions_'+run)
        state_path=base/f'state_{t:06d}.json'
        previous=base/('action_000001.json' if t==900 else 'action_003150.json')
        config=Path('evaluation/configs/n21_n7_20260908.json')
        cfg,state,det,tuning,raw,mapping,metadata=build_projected(ROOT/config,ROOT/state_path,ROOT/previous)
        join=build_movement_join(cfg,det,turns,membership,physical_successors=successors)
        from evaluation.controllers import vissim_stackelberg_adapter as adapter
        from src.models.demand import DemandStep
        control=adapter.control_from_json(ROOT/previous,cfg,ControlAction)
        demand=adapter.demand_from_state(raw,cfg,DemandStep,1)[0]
        accepted=accepted_movements(state,cfg,control,demand)
        totals=Counter();unresolved=[]
        for movement,value in accepted.items():
            row=join['by_movement'][movement]
            totals[row['status']]+=value
            if row['status'] not in ('unique','same_transition'):
                unresolved.append({'movement':movement,'actual_accepted_veh':value,**row})
        outputs.append({'run':run,'time_sec':t,'duration_sec':cfg.simulation.T_u_sec,
            'accepted_movement_veh_by_join_status':dict(totals),'unresolved_positive_movements':unresolved,
            'all_actual_accepted_movements':accepted,'join_counts':join['counts'],
            'source_files':[source(config),source(state_path),source(previous),source('outputs/pn_boundary_turns_v2_20260907.json'),
                            source('diagnostics/control_area_membership.json')],
            'trace_semantics':'Diagnostic Python line observation of vendor actual=min(before,departed), one copied-state urban step, no source modification.'})
        if t==3300:
            join['source_files']=outputs[-1]['source_files']
            (ROOT/'diagnostics/control_area_movement_join.json').write_text(json.dumps(join,indent=2,ensure_ascii=False),encoding='utf-8')
            (ROOT/'diagnostics/control_area_route_contract.json').write_text(json.dumps(route_contract(join),indent=2,ensure_ascii=False),encoding='utf-8')
    (ROOT/'diagnostics/control_area_movement_flow_coverage.json').write_text(json.dumps(outputs,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps([{k:v for k,v in row.items() if k in ('run','join_counts','accepted_movement_veh_by_join_status')} for row in outputs],indent=2))


if __name__=='__main__':main()
