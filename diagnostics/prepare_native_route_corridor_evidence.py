"""Materialize source343/341 native paths from the pinned Ver2 XML."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def pin(path):return {'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def main():
    network=ROOT/'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx';tree=ET.parse(network).getroot()
    sc=tree.find('./signalControllers/signalController[@no="15"]');sig=network.parent/sc.get('supplyFile2').replace('#data#','')
    for input_no,source,decision_no,head,sg in [('1086','343','1099','110501','5'),('1087','341','1100','110101','1')]:
        decision=tree.find(f'./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no="{decision_no}"]')
        paths={};branches={};storage='native_'+input_no+'_choice'
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            key=route.get('no');path=[source]+[x.get('key') for x in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
            target=tree.find(f'./links/link[@no="{path[1]}"]/toLinkEndPt').get('lane').split()[0]
            receiver='SC1_to_SC101' if target=='1220008502' else 'SC101_to_SC1' if target=='1220008401' else None
            if receiver is None:raise ValueError('Unreviewed native branch receiver')
            paths[key]=path;branches[key]={'mode':'free_storage','destination':receiver,'service_group':'native_source:'+source,'physical_target_link':target}
        doc={'schema':'route-choice-corridor/v1','network':pin(network),'membership_path':'diagnostics/control_area_membership.json',
            'jam_source':pin(ROOT/'outputs/urban_storage_capacity_core17legs4b_20260819.json'),
            'decision':decision_no,'decision_link':source,'decision_position_m':float(decision.get('pos')),
            'prefix_storage':storage,'prefix_links':[source],'local_storage':None,'local_links':[],
            'local_connector':None,'bypass_storage':None,'bypass_connector':None,'post_stopline_projection':{},
            'native_paths':paths,'branch_specs':branches,'local_free_paths':{},'local_movements':{},'local_queue_heads':{},'incoming_turns':{},
            'generated_inputs':{input_no:{'physical_source':source,'storage':storage,'native_decision':decision_no}},
            'native_fixed_service':{'controller':'15','signal_group':sg,'head':head,'program_no':int(sc.get('progNo')),
                'controller_offset_sec':float(sc.get('offset')),'sig_file':pin(sig),
                'selected_plan':pin(ROOT/'outputs/signal_group_actuation_plan_mainline_20260825.json')},
            'model_limitations':['Native200:150 is conditional on reaching the declared decision; measured current routes are preserved, missing past choices fail explicitly.',
                'Only the source road is reassigned to this finite stock. Both branch connectors and shared downstream roads retain their existing unique receiver projection.',
                'NativeSC15 source signal is a fixed clock, not an MPC lever. Its two route tags share one source-lane service budget at the existing model capacity scale.',
                'Before-head cohorts are gated at accepted branch discharge (head-to-branch travel2–4m is not a separate reservoir); already past-head observed cohorts do not cross the source signal twice.',
                'The downstream receiver resumes existing travel and approach turn dynamics after the declared native route ends; no unobserved longer route is invented.',
                'Generation/backlog belong only to native_internal_input. Route receipt adds no demand and schedules no duplicate generic arrival.']}
        out=ROOT/f'diagnostics/route_choice_corridor_{decision_no}_ver2.json';out.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(out,hashlib.sha256(out.read_bytes()).hexdigest())
if __name__=='__main__':main()
