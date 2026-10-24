"""Diagnostic in-process connection of frozen148 route/lanes to full physics.

Uses the existing full-network initializer/rollout. No new runner or adapter,
no coefficient fitting, no future traffic boundaries, no production adoption.
"""
import copy
import inspect
import hashlib
import json
import textwrap
from contextlib import contextmanager
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'


def install(captured,enabled,report_dir=None):
    report_dir=HERE if report_dir is None else report_dir
    from evaluation.controllers import physical_lane_groups as lanes,offramp_routing as routing
    from evaluation.controllers import area_freeway_accounting as area, lane_plant_runtime as lpr
    from evaluation.controllers import lane_ramp_runtime,obs150_contract as oc
    source=json.loads((R/'spatial_context148/forecast/executed_function_sources.json').read_bytes())
    hooks=[]
    assert not hasattr(lanes,'RouteLaneRegion')
    namespace={}
    exec(compile(source['RouteLaneRegion'],'frozen148_RouteLaneRegion','exec'),lanes.__dict__,namespace)
    lanes.RouteLaneRegion=namespace['RouteLaneRegion'];hooks.append((lanes,'RouteLaneRegion',None))
    stats=dict(commits=0,ramp_supply_queries=0,max_route_residual=0.,max_split19_residual=0.)
    commit=lanes.RouteLaneRegion.commit
    def checked_commit(obj,*args,**kwargs):
        result=commit(obj,*args,**kwargs)
        stats['commits']+=1
        stats['max_route_residual']=max(stats['max_route_residual'],obj.max_residual)
        stats['max_split19_residual']=max(stats['max_split19_residual'],obj.split19_error)
        return result
    supply=lanes.RouteLaneRegion.ramp_supply
    def checked_supply(obj,*args,**kwargs):
        stats['ramp_supply_queries']+=1
        return supply(obj,*args,**kwargs)
    lanes.RouteLaneRegion.commit=checked_commit
    lanes.RouteLaneRegion.ramp_supply=checked_supply
    for module,name in ((routing,'initialize_inventory'),(routing,'advance_inventory'),(area,'_freeway_substep_events')):
        original=getattr(module,name);namespace={}
        exec(compile(source[name],'frozen148_'+name,'exec'),original.__globals__,namespace)
        setattr(module,name,namespace[name]);hooks.append((module,name,original))
    # The regional receiving budget must constrain the actual conserved ramp
    # discharge BEFORE mainline stepping, just as in the148 component rollout.
    cls=lane_ramp_runtime.LaneRampRuntime
    original=cls.advance
    before=textwrap.dedent(inspect.getsource(original))
    needle='            rate = canonical_rate = selected[name]\n'
    assert before.count(needle)==1
    after=before.replace(needle,needle+
        "            region = (getattr(state, '_route_lane_regions', {}) or {}).get(road)\n"
        "            if region is not None:\n"
        "                rate = min(rate, region.ramp_supply(name, cfg))\n")
    namespace={};exec(compile(after,'coupled_lane200_ramp_receiving','exec'),original.__globals__,namespace)
    cls.advance=namespace['advance'];hooks.append((cls,'advance',original))
    if enabled:
        # Regional cells call scalar METANET once PER LANE (and split19 part),
        # rather than once per cell. Filter those multiple scalar rows and keep
        # one explicit aggregate before/after witness, not a fake decomposition.
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        observe=probe.observe_first_interval_speed_terms
        @contextmanager
        def observe_regions(start,rows,*,horizon_sec=150,cells=(0,4,*range(9,26))):
            regional=captured['state']._route_lane_regions['FW_E'].cells
            scalar_cells=tuple(c for c in cells if c not in regional)
            with observe(start,rows,horizon_sec=horizon_sec,cells=scalar_cells):
                step=area._freeway_substep_events
                def witness(state,control,demand,cfg,*args,**kwargs):
                    mark=len(rows)
                    region=(getattr(state,'_route_lane_regions',{}) or {}).get('FW_E')
                    before=[]
                    if region is not None and 'FW_E' in cfg.network.freeway_links and state.time_sec<start+horizon_sec:
                        before=[dict(time_sec=state.time_sec,cell=i,kind='regional_lane_update',
                            speed_before=state.freeway_speed['FW_E'][i],rho=state.freeway_density['FW_E'][i],
                            lane_speeds_before=list(region.v[i])) for i in region.cells if i in cells]
                    result=step(state,control,demand,cfg,*args,**kwargs)
                    for row in before:
                        i=row['cell']
                        row.update(speed_final=state.freeway_speed['FW_E'][i],lane_speeds_final=list(region.v[i]))
                        rows.append(row)
                    if before:
                        assert len(rows[mark:])==len(cells)
                        assert {r['cell'] for r in rows[mark:]}==set(cells)
                    return result
                area._freeway_substep_events=witness
                try:yield
                finally:area._freeway_substep_events=step
            assert len({(r['time_sec'],r['cell']) for r in rows})==len(rows)
        probe.observe_first_interval_speed_terms=observe_regions
        hooks.append((probe,'observe_first_interval_speed_terms',observe))
    report=dict(enabled=enabled,source='frozen148 structural functions only; deployed FD coefficients retained',
                whole_goal_qualified=False,AD_verified=False,initial_partition_verified=False,
                ramp_receiving_query_connected=True)
    report['unchanged_cell_parameters_sha256']={road:hashlib.sha256(json.dumps(
        cfg.network.freeway_segment_params,sort_keys=True).encode()).hexdigest()
        for road,cfg in captured['state'].lane_freeway_runtime.configs.items()}
    if enabled:
        assert json.loads((HERE/'disabled_parity.json').read_bytes())['enable_allowed']
        state=captured['state'];cfg=captured['cfg'];freeway=state.lane_freeway_runtime
        assert not freeway.lanes and not hasattr(state,'_route_lane_regions')
        assert state.time_sec==2700 and cfg.simulation.T_f_sec==1
        spec=json.loads((F/'joint_lane_25/protocol.json').read_bytes())['candidate']
        spec.update(congested_receiving_cells=[21],reciprocal_off='10483')
        scope=copy.copy(cfg);scope.network=copy.copy(cfg.network)
        # Controller addresses retain their parent segment arrays. The lane
        # partition is physical31 and must use the already-installed runtime
        # dimensions/FD, not those coarser controller-address arrays.
        for name in ('freeway_segment_lanes','freeway_segment_length_profile_km','freeway_segment_params'):
            values={road:copy.deepcopy(getattr(pc.network,name)[road]) for road,pc in freeway.configs.items()}
            assert all(len(v)==len(state.freeway_density[road])==31 for road,v in values.items())
            setattr(scope.network,name,values)
        scope.network.freeway_variable_cell_lengths=True
        scope.network.rho_max=freeway.configs['FW_E'].network.rho_max
        scope.network.offramp_route_inventory=freeway.configs['FW_E'].network.offramp_route_inventory
        scope.network.freeway_route_lane_regions={'FW_E':copy.deepcopy(spec)}
        raw=captured['raw'];bundle=oc.load_bundle(raw)
        routed=lpr.bind_current_routes(raw,{'frames':[bundle.frame_end]})
        # The archived component snapshot called the same one-based physical
        # lane "lane_index"; the canonical COM observation calls it "lane_no".
        # Add the name only on this private initializer copy, never to raw data.
        routed=copy.deepcopy(routed)
        for row in routed['vehicle_records']['records']:
            assert 'lane_no' in row and int(row['lane_no'])==row['lane_no'] and row['lane_no']>=1
            assert 'lane_index' not in row or row['lane_index']==row['lane_no']
            row['lane_index']=row['lane_no']
        report['lane_field_binding']='lane_no -> lane_index, identical one-based values on private initializer copy'
        before_stock=copy.deepcopy(state.offramp_route_inventory_state)
        before_main=(copy.deepcopy(state.freeway_density),copy.deepcopy(state.freeway_speed),copy.deepcopy(state.ramp_queue))
        routing.initialize_inventory(state,scope,routed)
        assert state.offramp_route_inventory_state==before_stock
        assert before_main==(state.freeway_density,state.freeway_speed,state.ramp_queue)
        region=state._route_lane_regions['FW_E'];region.assert_partition(state)
        region._split19_check(freeway.configs['FW_E'])
        report.update(initial_partition_verified=True,spec=spec,
            initial_lane_stock={str(i):[sum(row.values()) for row in region.stocks[i]] for i in region.cells},
            initial_lane_speed=region.v,max_initial_route_residual=region.max_residual,
            initial_split19_residual=region.split19_error)
    (report_dir/('enabled_binding.json' if enabled else 'disabled_binding.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    (report_dir/'ramp_advance_executed.py.txt').write_text(after,encoding='utf-8')
    return hooks,stats


def restore(hooks):
    for module,name,old in reversed(hooks):
        if old is None:delattr(module,name)
        else:setattr(module,name,old)
