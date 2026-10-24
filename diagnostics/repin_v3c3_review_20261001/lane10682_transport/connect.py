"""Surgical, pinned reuse of the archived accepted-flow implementation."""
import ast
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/baseline_reproduction_20260929/cellwise_calibration/freeway_first/joint_lane_fifo/executed_sources'
before=json.loads((HERE/'before.json').read_bytes())
for p,h in before.items(): assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
def replace(text,old,new):
    assert text.count(old)==1,old[:120]
    return text.replace(old,new)
def load(name):return (ROOT/'evaluation/controllers'/name).read_text(encoding='utf8')
def save(name,text):
    ast.parse(text)
    (ROOT/'evaluation/controllers'/name).write_text(text,encoding='utf8',newline='\n')

archive=(OLD/'physical_lane_groups.py').read_text(encoding='utf8')
node=next(n for n in ast.parse(archive).body if isinstance(n,ast.ClassDef) and n.name=='RouteLaneRegion')
body=ast.get_source_segment(archive,node)+'\n\n\n'
body=body.replace("physical['lane_index']","physical['lane_no']")
body=replace(body,"self.stocks = {i:[{} for _ in range(self.groups)] for i in self.cells}",
    "self.stocks = {i:state.offramp_route_inventory_state['lane_cells'][road][i] for i in self.cells}\n        if any(len(rows) != self.groups for rows in self.stocks.values()):\n            raise ValueError('Lane region dimensions differ from the canonical partition')")
body=replace(body,"                _add(self.stocks[i][g], classes)\n","")
body=body.replace("p['weights']","p['route_weights']")
body=replace(body,"        self.before = copy.deepcopy(self.stocks)",
    "        if any(type(x) not in (int, float) for rows in self.stocks.values() for row in rows for x in row.values()):\n            raise ValueError('Route-lane tangents are not qualified')\n        self.planned_time = state.time_sec\n        self.before = copy.deepcopy(self.stocks)")
body=replace(body,"        self.stocks = self.next;self.v = self.next_v",
    "        if self.planned_time != state.time_sec or set(self.next_v) != set(self.cells):\n            raise ValueError('Missing or stale accepted lane transition')\n        self.stocks = self.next;self.v = self.next_v\n        for i, rows in self.stocks.items():\n            state.offramp_route_inventory_state['lane_cells'][self.road][i] = rows")
text=load('physical_lane_groups.py')
text=replace(text,'def hadi_receiving_vph(',body+'def hadi_receiving_vph(')
save('physical_lane_groups.py',text)

text=load('offramp_routing.py')
text=replace(text,"    lane_cells = None\n", "    lane_cells = None\n    lane_specs = getattr(cfg.network, 'freeway_route_lane_regions', {}) or {}\n    lane_observations = [] if lane_specs else None\n    if lane_specs and lane_partition is None:\n        raise ValueError('Route lane dynamics requires its canonical lane partition')\n")
anchor="        _add(cells[fw][cell], classes)"
text=replace(text,anchor,anchor+"\n        if lane_observations is not None:\n            lane_observations.append((physical, fw, cell, classes))")
anchor="    metadata = {'offramp_route_inventory_initial_known_veh': known,"
text=replace(text,anchor,"    if lane_specs:\n        from evaluation.controllers.physical_lane_groups import RouteLaneRegion\n        state._route_lane_regions = {fw: RouteLaneRegion(spec, state, cfg, fw, lane_observations)\n                                     for fw, spec in lane_specs.items()}\n"+anchor)
text=replace(text,"    if 'lane_cells' in inv:\n        raise ValueError('Lane route partition transport is not yet integrated; aggregate transport would discard lane identity')",
    "    joint = (getattr(state, '_route_lane_regions', {}) or {}).get(fw)\n    if 'lane_cells' in inv:\n        if any(len(rows) != 1 and (joint is None or i not in joint.cells)\n               for i, rows in enumerate(inv['lane_cells'][fw])):\n            raise ValueError('Lane route partition transport is not yet integrated for these cells')\n        if joint is not None and joint.planned_time != state.time_sec:\n            raise ValueError('Stale accepted lane transition')")
anchor="        movements = [(through, (mainline[i] if i < len(old)-1 else terminal)*duration_h, i+1, None)]"
text=replace(text,anchor,"        if joint is not None and i in joint.face_classes:\n            through = joint.face_classes[i]\n            if not math.isclose(math.fsum(through.values()), mainline[i]*duration_h, abs_tol=1e-8, rel_tol=1e-10):\n                raise ValueError('Accepted lane face differs from physical continuity')\n"+anchor)
text=replace(text,"        movements.extend((values, offramps.get(target,0.)*duration_h, None, target) for target,values in targets.items())",
    "        for target, values in targets.items():\n            if joint is not None and target in joint.off_classes:\n                values = joint.off_classes[target]\n                if not math.isclose(math.fsum(values.values()), offramps.get(target,0.)*duration_h, abs_tol=1e-8, rel_tol=1e-10):\n                    raise ValueError('Accepted lane exit differs from physical off-ramp receipt')\n            movements.append((values, offramps.get(target,0.)*duration_h, None, target))")
anchor="    # This is a receipt of already-debited stock, not another population."
text=replace(text,anchor,"    if 'lane_cells' in inv:\n        for i, row in enumerate(inv['cells'][fw]):\n            if joint is None or i not in joint.cells:\n                inv['lane_cells'][fw][i] = [dict(row)]\n        if joint is not None:\n            joint.commit(state, cfg)\n"+anchor)
save('offramp_routing.py',text)

text=load('area_freeway_accounting.py')
anchor="        q_inter = [min(mainline_sending[i], receiving_for_mainline[i + 1]) for i in range(len(rho_for_flow) - 1)]"
text=replace(text,anchor,anchor+"\n        joint = (getattr(state, '_route_lane_regions', {}) or {}).get(link)\n        if joint is not None:\n            if (not routed or cap_factor != 1. or phi_cd != 1. or buf_n\n                    or any(abs(lanes_now[i]-joint.groups)>1e-9 for i in joint.cells)):\n                raise ValueError('Joint route lanes require canonical physical-width routed receiving')\n            joint.assert_partition(state)\n            joint.plan(state, cfg, mainline_sending, route_requests, q_inter,\n                       receiving_for_mainline, ramp_release, offramp_capacity_veh_h)")
anchor="                effective_off = normal_off if cap is None else min(normal_off, max(0.0, cap))"
text=replace(text,anchor,anchor+"\n                if joint is not None and off_ramp in joint.off_sent:\n                    effective_off = sum(joint.off_sent[off_ramp])/dt_h")
anchor="            if v_new <= net.v_min + 1e-09:"
text=replace(text,anchor,"            if joint is not None and i in joint.cells:\n                merge_kappa = (net.freeway_segment_params[link][i]['metanet_kappa_veh_km_lane']\n                    if direction_params else net.metanet_kappa_veh_km_lane)\n                v_new = joint.speed(i, state, cfg, control, _mn, exposure, delta_i, merge_kappa)\n                boundary_speed_cap = None  # Exit FIFO is applied to its accessible lane only.\n"+anchor)
save('area_freeway_accounting.py',text)

text=load('lane_freeway_runtime.py')
text=replace(text,'def initialize_route_inventory(self, state, full_cfg, raw, contract_path):',
    'def initialize_route_inventory(self, state, full_cfg, raw, contract_path, *, lane_regions=None):')
anchor="        metadata = routing.initialize_inventory(state, scope, raw)"
text=replace(text,anchor,"        partition = None\n        if lane_regions is not None:\n            from evaluation.controllers.projection_support import complete_records\n            if not isinstance(lane_regions, dict) or not lane_regions or set(lane_regions)-set(self.roads):\n                raise ValueError('Explicit road-indexed route lane regions required')\n            scope.network.freeway_route_lane_regions = copy.deepcopy(lane_regions)\n            dimensions = {road:[1]*len(state.freeway_density[road]) for road in self.roads}\n            for road, spec in lane_regions.items():\n                for i in spec['cells']:\n                    dimensions[road][i] = spec['lanes']\n            assignments = {}\n            for physical in complete_records(raw):\n                if str(physical['link_no']) not in runtime['physical']:\n                    continue\n                road, _, cell = routing._position(runtime, physical['link_no'], physical['position_m'])\n                assignments[physical['veh_no']] = physical['lane_no']-1 if dimensions[road][cell]>1 else 0\n            partition = dict(groups_per_cell=dimensions, vehicle_group=assignments)\n        metadata = routing.initialize_inventory(state, scope, raw, lane_partition=partition)")
save('lane_freeway_runtime.py',text)
text=load('runtime_setup.py')
text=replace(text,'                state, cfg, state_json, route_inventory))',
    "                state, cfg, state_json, route_inventory,\n                lane_regions=(tuning.get('freeway', {}) or {}).get('route_lane_regions')))")
save('runtime_setup.py',text)
text=load('lane_ramp_runtime.py')
anchor="                rate = canonical_rate = selected[name]"
text=replace(text,anchor,anchor+"\n                joint = (getattr(state, '_route_lane_regions', {}) or {}).get(road)\n                if joint is not None:\n                    rate = min(rate, joint.ramp_supply(name, cfg))")
save('lane_ramp_runtime.py',text)
print('Connected conserved regional accepted flows; default remains off')
