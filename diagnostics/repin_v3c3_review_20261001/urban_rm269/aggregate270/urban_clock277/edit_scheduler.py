"""Exact-site opt-in multirate integration; originals retained."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def edit(name,changes):
 p=ROOT/'evaluation/controllers'/name;b=HERE/(name+'.before');assert not b.exists()
 raw=p.read_bytes();s=raw.decode().replace('\r\n','\n')
 for a,z in changes:
  assert s.count(a)==1,(name,a,s.count(a));s=s.replace(a,z)
 b.write_bytes(raw);p.write_text(s,encoding='utf8',newline='\n')

edit('lane_offramp_runtime.py',[
 ("        if step!=self.time:raise ValueError('City capture is not at approach time')",
  "        step=step*cfg.simulation.T_u_sec\n        if step!=self.time:raise ValueError('City capture is not at approach time')"),
 ('        out=self.advance(step,green,room)\n        result=dict(head_departed_veh=',
  '''        duration=cfg.simulation.T_u_sec
        entry=step
        if duration==1:out=self.advance(step,green,room)
        elif duration==10 and getattr(cfg.network,'multirate_urban_clock_sec',None)==10:
            from evaluation.controllers.multirate_urban_boundary import advance_shared_interval,signal_intervals
            lane_specs={g:specs[self.city_movements[row['movements'][0]]] for g,row in self.lanes.items()}
            out=advance_shared_interval(self,step*duration,duration,signal_intervals(control,cfg,lane_specs),room)
            entry=step+1
        else:raise ValueError('Shared physical head requires prepared1/10s clock')
        result=dict(head_departed_veh='''),
 ('            if not _receive_corridor(state,cfg,m,n,step):\n                due=step+uqm._link_delay_steps(state,cfg,target)',
  "            options={} if entry==step else {'entry_step':entry}\n            if not _receive_corridor(state,cfg,m,n,step,**options):\n                due=entry+uqm._link_delay_steps(state,cfg,target)"),
 ('record_ordinary_movement(state,cfg,m,n,step,due)','record_ordinary_movement(state,cfg,m,n,entry,due)'),
 ("sum(self.lanes[g]['service_veh_h']/3600.*green[g] for g in self.lanes),",
  "sum(self.lanes[g]['service_veh_h']/3600.*green[g] for g in self.lanes)*duration,"),
 ('def land(self,state,cfg,end,flows,group_flows,*,duration_sec=1.):',
  'def land(self,state,cfg,end,flows,group_flows,*,duration_sec=1.,source_owners=None,route_receipts=None):'),
 ("receipt=state.offramp_route_inventory_state['last_offramp_receipts'][row['road']]",
  "receipt=(state.offramp_route_inventory_state['last_offramp_receipts'] if route_receipts is None else route_receipts)[row['road']]"),
 ("emit_transfer(state,cfg,'freeway:'+row['road'],'storage:'+key,amount,\n                source_inside=True,target_inside=self.membership[str(row['connector'])])",
  "emit_transfer(state,cfg,'freeway:'+row['road'] if source_owners is None else source_owners[off],'storage:'+key,amount,\n                source_inside=True,target_inside=self.membership[str(row['connector'])])"),
])
edit('urban_flow_accounting.py',[
 ('    drained = _drain_offramp_storage_accounted(state, control, cfg, specs, step_idx, routing)',
  '''    coarse_head_flow=None
    if shared_head is not None and cfg.simulation.T_u_sec==10:
        coarse_head_flow=shared_head.drain_to_network(state,control,cfg,step_idx,routing)
    drained = _drain_offramp_storage_accounted(state, control, cfg, specs, step_idx, routing)'''),
 ('        shared_flow=shared_head.drain_to_network(state,control,cfg,step_idx,routing)',
  '        shared_flow=coarse_head_flow if coarse_head_flow is not None else shared_head.drain_to_network(state,control,cfg,step_idx,routing)'),
 ('        if area_enabled:\n            keys = [k for k in get_ledger(state).stocks',
  "        if area_enabled and not getattr(cfg.network,'multirate_joint_clock_enabled',False):\n            keys = [k for k in get_ledger(state).stocks"),
])
edit('area_runtime.py',[
 ('    return model_stock_values(state, cfg.network,\n                              freeway_vehicle_counts=continuity_vehicle_counts(state, cfg))',
  '''    result=model_stock_values(state, cfg.network,
                              freeway_vehicle_counts=continuity_vehicle_counts(state, cfg))
    for key,amount in getattr(state,'multirate_exchange_pending',{}).items():
        if not key.startswith('transit:exchange:') or amount<0:
            raise MembershipError('Invalid multirate boundary stock')
        result[key]=amount
    return result'''),
])
edit('lane_coupling.py',[
 ('def run_interval(state,control,demand,cfg):\n    from evaluation.controllers',
  '''def run_interval(state,control,demand,cfg):
    if getattr(cfg.network,'multirate_joint_clock_enabled',False):
        from evaluation.controllers.multirate_coupling import run_interval as coarse_interval
        return coarse_interval(state,control,demand,cfg)
    from evaluation.controllers'''),
])
edit('multirate_freeway.py',[
 ('    if cfg.simulation.T_u_sec != 1:\n        return False',
  '''    if cfg.simulation.T_u_sec != 1:
        return (cfg.simulation.T_u_sec==10 and cfg.simulation.T_f_sec==5
                and getattr(cfg.network,'multirate_joint_clock_enabled',False)
                and getattr(cfg.network,'multirate_freeway_exchange_enabled',False)
                and state.lane_freeway_runtime.time_sec==state.time_sec)'''),
])
edit('runtime_setup.py',[
 ('    metadata.update(multirate_freeway.configure(cfg,tuning,state))\n    return state, detector_mapping, metadata',
  '''    metadata.update(multirate_freeway.configure(cfg,tuning,state))
    from evaluation.controllers import multirate_coupling
    metadata.update(multirate_coupling.configure(cfg,tuning,state))
    return state, detector_mapping, metadata'''),
])
print('six opt-in scheduler integration sites updated')
