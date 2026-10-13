"""One-shot, exact-site implementation; preserves every original source."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
def edit(name,changes):
    p=ROOT/'evaluation/controllers'/name
    backup=HERE/(name+'.before')
    assert not backup.exists(),name
    original=p.read_bytes();text=original.decode('utf8').replace('\r\n','\n')
    for old,new in changes:
        assert text.count(old)==1,(name,old,text.count(old))
        text=text.replace(old,new)
    backup.write_bytes(original);p.write_text(text,encoding='utf8',newline='\n')

edit('urban_flow_accounting.py',[
 ('def _receive_corridor(state, cfg, movement, vehicles, urban_step_index):',
 '''def _receive_corridor(state, cfg, movement, vehicles, urban_step_index, *, entry_step=None):
    # Service is charged to the current allocator visit; travel starts at the
    # actual exchange endpoint, which may be the next coarse urban tick.
    entry = urban_step_index if entry_step is None else entry_step
    if not math.isfinite(entry) or int(entry)!=entry or entry<urban_step_index:
        raise ValueError('Urban receipt entry step must not precede service')
    options = {} if entry_step is None else {'entry_step':entry}'''),
 ('direct_exit_movement_receive(state,cfg,movement,vehicles,urban_step_index)',
  'direct_exit_movement_receive(state,cfg,movement,vehicles,entry)'),
 ('urban_step_index + _uqm._link_delay_steps(state, cfg, target),\n                movement=movement, entry_step=urban_step_index)',
  'entry + _uqm._link_delay_steps(state, cfg, target),\n                movement=movement, entry_step=entry)'),
 ('if receive_accepted(state, cfg, movement, vehicles, urban_step_index):\n            return True\n    if getattr(cfg.network, \'route_choice_corridor\'',
  'if receive_accepted(state, cfg, movement, vehicles, urban_step_index, **options):\n            return True\n    if getattr(cfg.network, \'route_choice_corridor\''),
 ('if receive_accepted(state, cfg, movement, vehicles, urban_step_index):\n            return True\n    if getattr(cfg.network, \'sc2001_corridor\'',
  'if receive_accepted(state, cfg, movement, vehicles, urban_step_index, **options):\n            return True\n    if getattr(cfg.network, \'sc2001_corridor\''),
 ('return receive_accepted(state, cfg, movement, vehicles, urban_step_index)\n    return False',
  'return receive_accepted(state, cfg, movement, vehicles, urban_step_index, **options)\n    return False'),
])
edit('route_choice_corridor.py',[
 ('def receive_accepted(state,cfg,movement,vehicles,urban_step_index):',
  '''def receive_accepted(state,cfg,movement,vehicles,urban_step_index,*,entry_step=None):
    entry=urban_step_index if entry_step is None else entry_step
    if not math.isfinite(entry) or int(entry)!=entry or entry<urban_step_index:
        raise ValueError('Route receipt entry cannot precede current service')'''),
 ("_due(cfg,urban_step_index,distance,speed),source=movement,speed=speed)",
  "_due(cfg,entry,distance,speed),source=movement,speed=speed)"),
 ('record_choice(state,cfg,spec,cohort,urban_step_index,group,0.)','record_choice(state,cfg,spec,cohort,entry,group,0.)'),
])
edit('native_input_routes.py',[
 ('def receive_accepted(state, cfg, movement, vehicles, step):',
  'def receive_accepted(state, cfg, movement, vehicles, step, *, entry_step=None):'),
 ('    inputs = _inputs(cfg)\n    if not inputs: return False\n    from evaluation.controllers import sdmpc_aggregate as aggregate\n    if aggregate.enabled(cfg):return aggregate.route_accept(state,cfg,movement,vehicles,step)',
  '''    entry=step if entry_step is None else entry_step
    if not math.isfinite(entry) or int(entry)!=entry or entry<step:
        raise ValueError('Native receipt entry cannot precede current service')
    inputs = _inputs(cfg)
    if not inputs: return False
    from evaluation.controllers import sdmpc_aggregate as aggregate
    if aggregate.enabled(cfg):return aggregate.route_accept(state,cfg,movement,vehicles,step,entry_step=entry)'''),
 ('_transit_cohort(cohort[\'input\'],index,accepted,step,state,cfg)',"_transit_cohort(cohort['input'],index,accepted,entry,state,cfg)"),
 ('due = step+uqm._link_delay_steps(state,cfg,target)','due = entry+uqm._link_delay_steps(state,cfg,target)'),
 ('record_ordinary_movement(state,cfg,movement,ordinary,step,due)','record_ordinary_movement(state,cfg,movement,ordinary,entry,due)'),
])
edit('sdmpc_aggregate.py',[
 ('def route_accept(state,cfg,movement,vehicles,step):',
  '''def route_accept(state,cfg,movement,vehicles,step,*,entry_step=None):
    entry=step if entry_step is None else entry_step
    if not math.isfinite(entry) or int(entry)!=entry or entry<step:
        raise ValueError('Aggregate receipt entry cannot precede current service')'''),
 ('legacy._transit_cohort(no,k+1,accepted,step,state,cfg)','legacy._transit_cohort(no,k+1,accepted,entry,state,cfg)'),
 ('due=step+uqm._link_delay_steps(state,cfg,target)','due=entry+uqm._link_delay_steps(state,cfg,target)'),
 ('record_ordinary_movement(state,cfg,movement,ordinary,step,due)','record_ordinary_movement(state,cfg,movement,ordinary,entry,due)'),
])
edit('sc2001_corridor.py',[
 ('def receive_accepted(state, cfg, movement, vehicles, urban_step_index):',
  'def receive_accepted(state, cfg, movement, vehicles, urban_step_index, *, entry_step=None):'),
 ('    """Reserve only: caller already moved actual accepted vehicles into storage."""\n    spec =',
  '''    """Reserve only: caller already moved actual accepted vehicles into storage."""
    entry=urban_step_index if entry_step is None else entry_step
    if not math.isfinite(entry) or int(entry)!=entry or entry<urban_step_index:
        raise ValueError('SC2001 receipt entry cannot precede current service')
    spec ='''),
 ("_reserve(local, cfg, row['origin'], vehicles, urban_step_index, position=row['entry_78_position_m'],",
  "_reserve(local, cfg, row['origin'], vehicles, entry, position=row['entry_78_position_m'],"),
])
edit('lane_urban_runtime.py',[
 ('    def advance(self,state,control,cfg,step):\n        from src.models',
  '''    def advance(self,state,control,cfg,step):
        from evaluation.controllers.control_area_objective import get_ledger
        duration=cfg.simulation.T_u_sec
        if (duration not in (1,10) or step!=self.last_step+1
                or step*duration!=self.port.urban.time):
            raise ValueError('Noncontiguous coupled local urban step')
        if duration==10 and getattr(cfg.network,'multirate_urban_clock_sec',None)!=10:
            raise ValueError('Local10s exchange needs explicit urban clock preparation')
        signal_cfg=cfg
        if duration==10:
            signal_cfg=copy.copy(cfg);signal_cfg.simulation=copy.copy(cfg.simulation)
            signal_cfg.simulation.T_u=1
        departed=0.
        for offset in range(int(duration)):
            row=self._advance_physical(state,control,cfg,step*duration+offset,
                service_step=step,arrival_step=step+1 if duration==10 else step,
                signal_cfg=signal_cfg)
            departed+=row['lane_urban_exit_veh']
        ledger=get_ledger(state)
        if ledger is not None and ledger.captures_response:
            ledger.complete_constraint_coverage('lane_urban_allocator')
        self.last_step=step
        return {**row,'lane_urban_exit_veh':departed}

    def _advance_physical(self,state,control,cfg,step,*,service_step,arrival_step,signal_cfg):
        from src.models'''),
 ("        if step != self.last_step+1 or step != self.port.urban.time:\n            raise ValueError('Noncontiguous coupled local urban step')\n",''),
 ('urban.program.control,urban.program.cfg=control,cfg','urban.program.control,urban.program.cfg=control,signal_cfg'),
 ('service=intended_departure(state,control,cfg,m,room,step)','service=intended_departure(state,control,cfg,m,room,service_step)'),
 ('if not _receive_corridor(state,cfg,m,n,step):\n                    due=step+uqm._link_delay_steps(state,cfg,receiver)',
  '''options={} if arrival_step==service_step else {'entry_step':arrival_step}
                if not _receive_corridor(state,cfg,m,n,service_step,**options):
                    due=arrival_step+uqm._link_delay_steps(state,cfg,receiver)'''),
 ('record_ordinary_movement(state,cfg,m,n,step,due)','record_ordinary_movement(state,cfg,m,n,arrival_step,due)'),
 ("            ledger.complete_constraint_coverage('lane_urban_allocator')\n        self.last_step=step\n        from evaluation.controllers.omega_distance",'        from evaluation.controllers.omega_distance'),
])
print('six source files updated; backups retained')
