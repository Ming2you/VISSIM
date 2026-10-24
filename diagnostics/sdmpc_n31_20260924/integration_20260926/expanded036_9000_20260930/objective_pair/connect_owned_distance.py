"""One-time checked edits: passive observers at existing travel reservations."""
from pathlib import Path

def edit(name, pairs):
    path=Path('evaluation/controllers')/(name+'.py')
    text=path.read_text(encoding='utf-8')
    for old,new in pairs:
        if text.count(old)!=1:
            raise ValueError((name,text.count(old),old))
        text=text.replace(old,new)
    compile(text,str(path),'exec')
    path.write_bytes(text.encode('utf-8'))

edit('shared_approach',[
    ("        branches[key] = {**choice, 'weight': weight, 'relFlow_raw': raw_weight, 'path': path_links,",
     "        from evaluation.controllers.sc2001_corridor import _travel_segments\n"
     "        geometry = _travel_segments(links, path_links[:path_links.index(receiving_link)+1])\n"
     "        travel_segments = [dict(link=s['link'],start=s['start_m'],stop=s['stop_m']) for s in geometry]\n"
     "        branches[key] = {**choice, 'travel_segments': travel_segments, 'weight': weight, 'relFlow_raw': raw_weight, 'path': path_links,"),
    ("            bins[key][due] = bins[key].get(due, 0.0) + (1.0 if selected is not None else branch['share'])",
     "            bins[key][due] = bins[key].get(due, 0.0) + (1.0 if selected is not None else branch['share'])\n"
     "            from evaluation.controllers.omega_distance import record_shared\n"
     "            record_shared(state,cfg,key,1.0 if selected is not None else branch['share'],\n"
     "                          vehicle['position_m'],index,due)"),
    ("            bins[due] = bins.get(due, 0.0) + admitted * branch['share']",
     "            bins[due] = bins.get(due, 0.0) + admitted * branch['share']\n"
     "            from evaluation.controllers.omega_distance import record_shared\n"
     "            record_shared(state,cfg,key,admitted*branch['share'],0.,urban_step_index,due)")])

edit('sc2001_corridor',[
    ("before_78_m=0., speed):", "before_78_m=0., speed, state=None):"),
    ("        bins[due] = bins.get(due, 0.) + amount*share",
     "        bins[due] = bins.get(due, 0.) + amount*share\n"
     "        from evaluation.controllers.omega_distance import record_sc2001\n"
     "        record_sc2001(state,cfg,branch,amount*share,physical_link,position,origin,before_78_m,index,due)"),
    ("position=float(row['position_m']), speed=_speed(state, cfg, row['speed_kph']))",
     "position=float(row['position_m']), speed=_speed(state, cfg, row['speed_kph']), state=state)"),
    ("before_78_m=row['pre_78_distance_m'], speed=_speed(state, cfg))",
     "before_78_m=row['pre_78_distance_m'], speed=_speed(state, cfg), state=state)")])

edit('route_choice_corridor',[
    ("                            'source':'initial_current_route','speed_kph':speed})\n            continue",
     "                            'source':'initial_current_route','speed_kph':speed})\n"
     "            from evaluation.controllers.omega_distance import record_known\n"
     "            record_known(state,cfg,target,1.,start,due,link,r['position_m'])\n            continue"),
    ("        _schedule(state.urban_storage_release_buffer,spec['storage'],due,vehicles)\n    local['received']+=vehicles",
     "        _schedule(state.urban_storage_release_buffer,spec['storage'],due,vehicles)\n"
     "        from evaluation.controllers.omega_distance import record_known\n"
     "        record_known(state,cfg,target,vehicles,entry_step,due,connector if movement is not None else entry['link'],\n"
     "                     0. if movement is not None else entry['position_m'])\n    local['received']+=vehicles"),
    ("                    _schedule(state.urban_storage_release_buffer,storage,chosen['due'],chosen['vehicles'])\n                cohorts.append(chosen)",
     "                    _schedule(state.urban_storage_release_buffer,storage,chosen['due'],chosen['vehicles'])\n"
     "                    from evaluation.controllers.omega_distance import record_known\n"
     "                    record_known(state,cfg,target,chosen['vehicles'],step,chosen['due'],'68',spec['choice_position_m'])\n"
     "                cohorts.append(chosen)")])
print('Connected shared approach, SC2001 and known legsplit distance; no travel or flow formula changed.')
