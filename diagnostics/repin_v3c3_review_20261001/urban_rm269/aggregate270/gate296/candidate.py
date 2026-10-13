"""Aggregate fixed SC10 gate for NEW accepted SC12_to_SC6 traffic only.

Diagnostic opt-in. Existing initial reservations retain their canonical owner.
Four times the global nominal movement service is an explicit provisional bound,
not a measured SC10 saturation prior. No future observations are runtime inputs.
"""
from contextlib import contextmanager
from collections import defaultdict
import copy,hashlib,importlib.util,math
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
loader=importlib.util.spec_from_file_location('sourcepath292_gate296',HERE.parent/'sourcepath292/candidate.py')
prior=importlib.util.module_from_spec(loader);loader.loader.exec_module(prior)
ORIGIN='SC12_to_SC6';MODE='aggregate_sc10_native_calendar'


def geometry(root,cfg):
    from evaluation.controllers.route_choice_corridor import _length,_travel_segments
    from plant.src.vissim_strict.signal_program import parse_sig
    data=prior.geometry(root,cfg);tree=ET.fromstring(Path(data['network_path']).read_bytes())
    nodes={n.get('no'):n for n in tree.findall('./links/link')}
    heads=[h for h in tree.findall('./signalHeads/signalHead') if h.get('sg')=='10 8']
    assert len(heads)==4 and {h.get('lane') for h in heads}=={f'1220018301 {i}' for i in range(1,5)}
    sc=tree.find("./signalControllers/signalController[@no='10']")
    assert sc.get('type')=='FIXEDTIME' and sc.get('active')=='true'
    sig=Path(data['network_path']).parent/sc.get('supplyFile2').removeprefix('#data#')
    program=parse_sig(sig,int(sc.get('progNo')))
    gate_position=min(float(h.get('pos')) for h in heads)
    for row in data['sources'].values():
        choices=[]
        for path in row['paths']:
            ii=path.index('1220018301');pre=path[:ii+1];post=path[ii:]
            length={k:_length(nodes[k]) for k in path}
            aa=_travel_segments(pre,nodes,length,gate_position)
            bb=_travel_segments(post,nodes,length,data['stop_position_m'])
            bb[0]['start']=gate_position
            left=sum(r['stop']-r['start'] for r in aa);right=sum(r['stop']-r['start'] for r in bb)
            assert abs(left+right-sum(r['stop']-r['start'] for r in _travel_segments(path,nodes,length,data['stop_position_m'])))<1e-7
            choices.append((left+right,left,right))
        _,row['pre_gate_distance_m'],row['post_gate_distance_m']=min(choices)
    data['gate']=dict(controller=10,signal_group='8',lanes=4,cycle_sec=program.cycle_length_sec,
        program_offset_sec=program.program_offset_sec,controller_offset_sec=float(sc.get('offset')),
        program_no=int(sc.get('progNo')),sig_file=dict(path=str(sig),sha256=hashlib.sha256(sig.read_bytes()).hexdigest()),
        nominal_service_veh_h=4*float(cfg.network.movement_capacity_veh_h),
        service_prior='4 physical lanes x existing global nominal movement_capacity_veh_h; NOT independently calibrated',
        initial_current_cohorts='canonical reservations unchanged; only newly accepted traffic is gated')
    return data


def step_gate(local,step,green_sec,rate,dt):
    """Conservative aggregate queue; vehicle amounts stay in the parent stock."""
    assert step==local['last_step']+1 and 0<=green_sec<=dt+1e-8
    for due,post in list(local['pending']):
        if due<=step:
            amount=local['pending'].pop((due,post))
            local['ready'][post]=local['ready'].get(post,0.)+amount
    ready=sum(local['ready'].values());budget=rate*green_sec/3600.
    accepted=min(ready,budget)
    release={}
    for post,n in list(local['ready'].items()):
        sent=n*(accepted/ready) if ready else 0.
        release[post]=sent;left=n-sent
        if left>1e-10:local['ready'][post]=left
        else:local['ready'].pop(post,None)
    local['discharged']+=accepted;local['last_step']=step
    remaining=sum(local['pending'].values())+sum(local['ready'].values())
    assert abs(local['received']-local['discharged']-remaining)<1e-7
    return release,dict(step=step,green_sec=green_sec,ready_before=ready,budget=budget,
        discharged=accepted,remaining_ready=sum(local['ready'].values()),remaining_transit=sum(local['pending'].values()),
        positive_green_capacity_binding=green_sec>0 and ready>budget+1e-8)


@contextmanager
def installed(cfg,option,geom):
    if option is None:
        yield []
        return
    if option!=MODE:raise ValueError('Unknown aggregate gate option')
    from evaluation.controllers import urban_flow_accounting as ufa,native_internal_input as nii,route_choice_corridor as rc
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
    from plant.src.vissim_strict.signal_program import parse_sig
    from src.models import urban_queue_model as uqm
    gate=geom['gate'];sig=Path(gate['sig_file']['path'])
    assert hashlib.sha256(sig.read_bytes()).hexdigest()==gate['sig_file']['sha256']
    program=parse_sig(sig,gate['program_no'])
    old_receive,old_native,old_corridor=ufa._receive_corridor,nii.advance,rc.advance
    records=[]
    def local_state(state,step):
        assert getattr(state,'_omega_travel_reservations',None) is None,'Distance objective needs explicit gate distance provider'
        if not hasattr(state,'_sc10_gate296'):
            state._sc10_gate296=dict(pending={},ready={},received=0.,discharged=0.,last_step=step-1,history=[])
        return state._sc10_gate296
    def register(state,cfg_arg,key,amount,entry,current):
        row=geom['sources'][key]
        pre=prior.delay_steps(row['pre_gate_distance_m'],state.urban_link_speed_kph[ORIGIN],geom['lane_factor'],
            cfg_arg.network.urban_avg_speed_km_h,cfg_arg.simulation.T_u_sec)
        post=prior.delay_steps(row['post_gate_distance_m'],state.urban_link_speed_kph[ORIGIN],geom['lane_factor'],
            cfg_arg.network.urban_avg_speed_km_h,cfg_arg.simulation.T_u_sec)
        local=local_state(state,current)
        assert entry>=current and amount>=0
        due=int(entry)+pre
        local['pending'][due,post]=local['pending'].get((due,post),0.)+amount
        local['received']+=amount
        records.append(dict(source=key,sec=state.time_sec,accepted_veh=amount,
            gate_due_sec=due*cfg_arg.simulation.T_u_sec,post_gate_delay_sec=post*cfg_arg.simulation.T_u_sec,
            delay_sec=(pre+post)*cfg_arg.simulation.T_u_sec))
    def receive(state,cfg_arg,movement,vehicles,step,*,entry_step=None):
        handled=old_receive(state,cfg_arg,movement,vehicles,step,entry_step=entry_step)
        if cfg_arg.network.urban_movements[movement].get('receiving_link')!=ORIGIN:return handled
        assert not handled,'Another owner already received this source'
        register(state,cfg_arg,'movement:'+movement,vehicles,step if entry_step is None else entry_step,step)
        return True
    def native(state,control,demand,cfg_arg,step):
        # Only1085 uses this ordinary receiver; all other delegated inputs keep
        # their existing route, service, admission and distance implementation.
        assert {k for k,r in cfg_arg.network.native_internal_inputs['inputs'].items() if r['target_storage']==ORIGIN}=={'1085'}
        before_a=dict(state.urban_arrival_buffer.get(ORIGIN,{}))
        before_r=dict(state.urban_storage_release_buffer.get(ORIGIN,{}))
        result=old_native(state,control,demand,cfg_arg,step)
        n=result['native_internal_input_step']['1085']['generated_inside_veh']
        for attr,before in (('urban_arrival_buffer',before_a),('urban_storage_release_buffer',before_r)):
            buffer=getattr(state,attr)[ORIGIN]
            delta={k:buffer.get(k,0.)-before.get(k,0.) for k in set(buffer)|set(before)}
            assert all(v>=-1e-8 for v in delta.values()) and abs(sum(delta.values())-n)<1e-7
            getattr(state,attr)[ORIGIN]=before
        if n:register(state,cfg_arg,'input:internal:1085',n,step,step)
        return result
    def corridor(state,control,demand,cfg_arg,step):
        result=old_corridor(state,control,demand,cfg_arg,step)
        dt=cfg_arg.simulation.T_u_sec
        local=local_state(state,step)
        green=_union_green_overlap(program,('8',),step*dt,(step+1)*dt,gate['controller_offset_sec'])
        release,row=step_gate(local,step,green,gate['nominal_service_veh_h'],dt)
        for post,n in release.items():
            if n:
                # Discharge uses this interval's green; downstream motion starts
                # at its end, preventing consumption of future same-tick space.
                due=step+1+post
                uqm._schedule(state.urban_arrival_buffer,ORIGIN,due,n)
                uqm._schedule(state.urban_storage_release_buffer,ORIGIN,due,n)
        ledger=get_ledger(state)
        if ledger is not None and ledger.captures_response:
            sources={'storage:'+ORIGIN:row['discharged']}
            ledger.record_resource_allocation('diagnostic_SC10_ready','SC10:SG8',row['ready_before'],sources)
            ledger.record_resource_allocation('diagnostic_SC10_green','SC10:SG8',row['budget'],sources)
        occupied=cfg_arg.network.urban_link_storage_veh[ORIGIN]-state.urban_link_storage[ORIGIN]
        tracked=row['remaining_transit']+row['remaining_ready']
        assert tracked<=occupied+1e-7,'Gate tracking exceeds its parent physical stock'
        row.update(sec=step*dt,parent_occupied=occupied,tracked_gate_stock=tracked)
        local['history'].append(row)
        return result
    ufa._receive_corridor=receive;nii.advance=native;rc.advance=corridor
    try:yield records
    finally:ufa._receive_corridor=old_receive;nii.advance=old_native;rc.advance=old_corridor
