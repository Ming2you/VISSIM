"""Retain a declared internal input's route through existing signal queues.

Tags are subsets of existing storage/queue counts, never additional stock.
Ordinary signal service and receiving allocation remain authoritative. Mixing
within a served movement is proportional; no microscopic FIFO is inferred.
"""
from collections import Counter, defaultdict
from copy import deepcopy
import math
from functools import lru_cache

from evaluation.controllers.control_area_objective import emit_transfer, get_ledger
from evaluation.controllers.projection_support import complete_records

EPS = 1e-8


def configure_input(cfg, row, tree, links, physical, contract, raw):
    from evaluation.controllers.native_internal_input import _read
    from evaluation.controllers.route_choice_corridor import _length, _validate_path, _travel_segments
    import json
    evidence = json.loads(_read(row['route_evidence']).read_text(encoding='utf-8-sig'))
    if evidence['schema'] != 'native-input-route-sequence/v1':
        raise ValueError('Unsupported native input route sequence')
    source = row['physical_source']
    decision = tree.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{evidence['decision']}']")
    routes = decision.findall('./vehRoutSta/vehicleRouteStatic') if decision is not None else []
    if (decision is None or decision.get('link') != source or decision.get('allVehTypes') != 'true'
            or decision.get('routeChoiceMeth') != 'STATIC' or len(routes) != 1):
        raise ValueError('Native fixed route needs one all-type source decision')
    native = routes[0]
    path = [source]+[x.get('key') for x in native.findall('./linkSeq/intObjectRef')]+[native.get('destLink')]
    if native.get('no') != evidence['route'] or path != evidence['path']:
        raise ValueError('Native fixed route path differs from its source')
    _validate_path(path, links)
    if set(row['physical_projection_links']) != {source, path[1]}:
        raise ValueError('Native route initial partition must remain the exclusive source and connector')
    plan = json.loads(_read(evidence['selected_plan']).read_text(encoding='utf-8-sig'))
    selected = {(str(sc), str(sg)) for sc, definition in plan['controllers'].items()
                for groups in definition['phase_signal_groups'].values() for sg in groups}
    heads = {h.get('no'): h for h in tree.findall('./signalHeads/signalHead')}
    lengths = {link: _length(links[link]) for link in path}
    all_segments = _travel_segments(path, links, lengths, float(native.get('destPos')))
    if not 0 <= float(decision.get('pos')) <= all_segments[0]['stop']:
        raise ValueError('Native input decision is outside its source travel interval')
    expected_selected, declared_selected, stages = set(), set(), []
    expected_native, declared_native = set(), set()
    for segment in all_segments:
        expected_selected.update(key for key, h in heads.items()
            if h.get('lane').split()[0] == segment['link'] and tuple(h.get('sg').split()) in selected
            and segment['start'] <= float(h.get('pos')) <= segment['stop'])
        expected_native.update(key for key, h in heads.items()
            if h.get('lane').split()[0] == segment['link'] and tuple(h.get('sg').split()) not in selected
            and segment['start'] <= float(h.get('pos')) <= segment['stop'])
    start_index = 0
    for index, detail in enumerate(evidence['stages']):
        movement = detail['movement']; spec = cfg.network.urban_movements[movement]
        physical_turns = contract['movement:'+movement]['physical_turns']
        if len(physical_turns) != 1:
            raise ValueError('Native tagged stage needs one canonical physical turn')
        turn = physical_turns[0]
        connector_index = path.index(turn['connector'])
        if path[connector_index-1:connector_index+2] != [turn['from_link'], turn['connector'], turn['to_link']]:
            raise ValueError('Native movement is not the declared ordered physical turn')
        if connector_index <= start_index:
            raise ValueError('Native signal stages are out of order')
        phase = str(spec['phase']).rpartition('_')[2]
        groups = plan['controllers'][str(spec['signal']).removeprefix('SC')]['phase_signal_groups'][phase]
        stage_heads = [heads[key] for key in detail['heads']]
        if not stage_heads or any(h.get('lane').split()[0] != turn['from_link']
                or h.get('sg').split()[0] != str(spec['signal']).removeprefix('SC')
                or h.get('sg').split()[1] not in set(map(str, groups))
                or h.get('allVehTypes') != 'true' or float(h.get('complRate')) != 1 for h in stage_heads):
            raise ValueError('Native route phase is not its observed physical head authority')
        declared_selected.update(detail['heads'])
        stop = min(float(h.get('pos')) for h in stage_heads)
        stage_path = path[start_index:connector_index]
        segments = _travel_segments(stage_path, links, lengths, stop)
        origin, target = spec['origin'], spec['receiving_link']
        if origin not in cfg.network.urban_link_storage_veh or target not in cfg.network.urban_link_storage_veh:
            raise ValueError('Native route stage lacks existing finite storage')
        if index == 0 and origin != row['target_storage']:
            raise ValueError('Native generation must enter the first route approach')
        if stages and origin != stages[-1]['target']:
            raise ValueError('Native route stages do not share the actual accepted receiver')
        if not all(physical.get(s['link']) is True for s in segments):
            raise ValueError('Native pre-head transit unexpectedly leaves the control area')
        if index < len(evidence['stages'])-1 and contract['movement:'+movement]['outward_crossings_per_vehicle']:
            raise ValueError('Native intermediate stage would cross the area boundary')
        stage = {'movement': movement, 'origin': origin, 'target': target, 'segments': segments,
                 'distance_m': sum(s['stop']-s['start'] for s in segments)}
        if detail.get('native_fixed_gate'):
            if not stages:
                raise ValueError('Native intermediate gate needs a preceding selected movement')
            gate = _configure_native_gate(detail['native_fixed_gate'], tree, links, heads, selected,
                                          stage, stages[-1], evidence['selected_plan'])
            if declared_native.intersection(gate['heads']):
                raise ValueError('Native intermediate head is declared twice')
            declared_native.update(gate['heads'])
            stage['native_fixed_gate'] = gate
        stages.append(stage)
        start_index = connector_index
    if not stages or expected_selected != declared_selected:
        raise ValueError('Native route sequence skips or invents a selected signal head')
    if expected_native != declared_native:
        raise ValueError('Native route sequence skips or invents an unselected native signal head')
    return {'source_contract_validated': True, 'route_stages': stages,
            'minimum_approach_distance_m': stages[0]['distance_m'],
            'route_sequence_scope': evidence['scope']}


def _configure_native_gate(reference, tree, links, heads, selected, stage, previous, selected_plan):
    """Pin one intermediate native timing gate; do not invent a service capacity."""
    from evaluation.controllers.native_internal_input import _read
    from evaluation.controllers.route_choice_corridor import _length, _travel_segments
    import json
    proof = json.loads(_read(reference).read_text(encoding='utf-8-sig'))
    if proof.get('schema') != 'native-1096-sc8-gate-proof/v1':
        raise ValueError('Unsupported native intermediate timing proof')
    for key in ('network', 'selected_plan', 'sig_file', 'membership', 'physical_route_contract'):
        _read(proof[key])
    if proof['selected_plan'] != selected_plan or proof['existing_storage'] != stage['origin']:
        raise ValueError('Native intermediate gate does not match its selected plan and existing stock')
    if (proof['upstream_movement'] != previous['movement'] or proof['downstream_movement'] != stage['movement']
            or (proof['controller'], proof['signal_group']) in selected):
        raise ValueError('Native intermediate gate is not between these selected movements')
    sc = tree.find(f"./signalControllers/signalController[@no='{proof['controller']}']")
    sig = _read(proof['sig_file'])
    if (sc is None or sc.get('active') != 'true' or sc.get('type') != 'FIXEDTIME'
            or int(sc.get('progNo')) != proof['program_no']
            or float(sc.get('offset')) != proof['controller_offset_sec']
            or sc.get('supplyFile2') != '#data#'+sig.name):
        raise ValueError('Native intermediate controller/program binding changed')
    declared = proof['heads']
    if not declared or len({r['head'] for r in declared}) != len(declared):
        raise ValueError('Native intermediate gate has missing or repeated heads')
    source_links = set()
    for row in declared:
        h = heads[row['head']]
        source, lane = h.get('lane').split()
        if (lane != row['lane'] or float(h.get('pos')) != row['position_m']
                or h.get('sg').split() != [proof['controller'], proof['signal_group']]
                or h.get('allVehTypes') != 'true' or float(h.get('complRate')) != 1):
            raise ValueError('Native intermediate head authority changed')
        source_links.add(source)
    if len(source_links) != 1:
        raise ValueError('Native timing gate needs a single physical source link')
    source = source_links.pop()
    if set(r['lane'] for r in declared) != {str(i+1) for i in range(len(links[source].findall('./lanes/lane')))}:
        raise ValueError('Native intermediate gate does not cover every source lane')
    index = next(i for i, s in enumerate(stage['segments']) if s['link'] == source)
    position = min(r['position_m'] for r in declared)
    path = [s['link'] for s in stage['segments'][:index+1]]
    pre = _travel_segments(path, links, {k: _length(links[k]) for k in path}, position)
    if not stage['segments'][index]['start'] <= position <= stage['segments'][index]['stop']:
        raise ValueError('Native intermediate head is outside its travel interval')
    before = sum(s['stop']-s['start'] for s in pre)
    after = stage['distance_m']-before
    if before < 0 or after < 0 or not math.isfinite(before+after):
        raise ValueError('Native intermediate gate has invalid physical distances')
    gate = {'heads': [r['head'] for r in declared], 'controller': proof['controller'],
            'signal_group': proof['signal_group'], 'sig_file': proof['sig_file'],
            'program_no': proof['program_no'], 'controller_offset_sec': proof['controller_offset_sec'],
            'pre_gate_distance_m': before, 'post_gate_distance_m': after,
            'timing_only': True, 'lane_position_spread_m': max(r['position_m'] for r in declared)-position}
    program = _native_program(str(sig), proof['sig_file']['sha256'], proof['program_no'])
    if (program.cycle_length_sec != proof['cycle_sec'] or program.program_offset_sec != proof['program_offset_sec']
            or proof['signal_group'] not in program.sg_timelines):
        raise ValueError('Native intermediate source clock changed')
    return gate


@lru_cache(maxsize=16)
def _native_program(path, sha256, program_no):
    from evaluation.controllers.native_internal_input import _read
    from plant.src.vissim_strict.signal_program import parse_sig
    return parse_sig(_read({'path': path, 'sha256': sha256}), program_no)


def _first_native_green(gate, start, end):
    """Earliest actual native GREEN in [start,end), or None; timing only."""
    from evaluation.controllers.native_internal_input import ROOT
    from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
    from pathlib import Path
    source = Path(gate['sig_file']['path'])
    if not source.is_absolute(): source = ROOT/source
    program = _native_program(str(source), gate['sig_file']['sha256'], gate['program_no'])
    group, offset = gate['signal_group'], gate['controller_offset_sec']
    if _union_green_overlap(program, (group,), start, end, offset) <= 0: return None
    if program.state_at(start, group, controller_offset_sec=offset) == 'GREEN': return start
    # Use the parsed canonical timeline's boundaries, including program offset.
    epoch = program.program_offset_sec+offset
    cycle = program.cycle_length_sec
    first_cycle = math.floor((start-epoch)/cycle)
    candidates = [epoch+k*cycle+x.start_sec
                  for k in range(first_cycle, math.floor((end-epoch)/cycle)+1)
                  for x in program.sg_timelines[group].intervals if x.state == 'GREEN'
                  and start <= epoch+k*cycle+x.start_sec < end]
    if not candidates: raise ValueError('Canonical native overlap has no matching GREEN boundary')
    return min(candidates)


def _inputs(cfg):
    return {no: row for no, row in getattr(cfg.network, 'native_internal_inputs', {}).get('inputs', {}).items()
            if row.get('route_stages')}


def _travel(state, cfg, stage, distance=None, speed=None):
    from src.models import urban_queue_model as uqm
    speed = max(float(speed if speed is not None else state.urban_link_speed_kph.get(stage['origin'], cfg.network.urban_avg_speed_km_h)),
                cfg.network.urban_avg_speed_km_h/uqm.OBSERVED_SPEED_DELAY_CAP_RATIO)
    length = stage['distance_m'] if distance is None else distance
    return max(1, math.ceil(length/(speed/3.6)/cfg.simulation.T_u_sec))


def _cohort(no, index, amount, due):
    return {'input': no, 'stage': index, 'vehicles': amount, 'due': due, 'queued': False}


def _transit_cohort(no, index, amount, step, state, cfg):
    stage = _inputs(cfg)[no]['route_stages'][index]
    gate = stage.get('native_fixed_gate')
    distance = gate['pre_gate_distance_m'] if gate else None
    result = _cohort(no, index, amount, step+_travel(state,cfg,stage,distance))
    if gate: result['native_gate_passed'] = False
    return result


def _check(state, cfg):
    local = state.native_input_route_state
    inputs = _inputs(cfg)
    grouped = defaultdict(float)
    for cohort in local['cohorts']:
        if not math.isfinite(cohort['vehicles']) or cohort['vehicles'] < 0:
            raise ValueError('Native route tag is negative/nonfinite')
        stage = inputs[cohort['input']]['route_stages'][cohort['stage']]
        key = ('queue', stage['movement']) if cohort['queued'] else ('storage', stage['origin'])
        grouped[key] += cohort['vehicles']
    for (kind, key), amount in grouped.items():
        actual = state.urban_movement_queue.get(key, 0.) if kind == 'queue' else cfg.network.urban_link_storage_veh[key]-state.urban_link_storage[key]
        if amount > actual+EPS: raise ValueError('Native route tags exceed their actual '+kind+': '+key)
    expected = local['initial_veh']+local['received_veh']-local['completed_veh']
    if not math.isclose(sum(grouped.values()), expected, rel_tol=0, abs_tol=EPS):
        raise ValueError('Native input route cohort accounting does not close')


def initialize(state, cfg, raw):
    inputs = _inputs(cfg)
    if not inputs: return {}
    if hasattr(state, 'native_input_route_state'):
        raise ValueError('Native input route tags must initialize once')
    start = int(round(state.time_sec/cfg.simulation.T_u_sec))
    local = {'last_step': start-1, 'cohorts': [], 'completed_veh': 0., 'received_veh': 0.}
    tagged = defaultdict(float)
    for no, row in inputs.items():
        first = row['route_stages'][0]
        for record in complete_records(raw):
            link = str(record['link_no'])
            if link not in row['physical_projection_links']: continue
            segment_index = next(i for i, s in enumerate(first['segments']) if s['link'] == link)
            remaining = max(0., first['segments'][segment_index]['stop']-record['position_m'])
            remaining += sum(s['stop']-s['start'] for s in first['segments'][segment_index+1:])
            local['cohorts'].append(_cohort(no, 0, 1., start+_travel(state,cfg,first,remaining,record['speed_kph'])))
            tagged[first['origin']] += 1.
    # Remove these tags' proportional share from old aggregate reservations;
    # their own physical travel below replaces it. Inventory is unchanged.
    for origin, n in tagged.items():
        occupied = cfg.network.urban_link_storage_veh[origin]-state.urban_link_storage[origin]
        if n > occupied+EPS: raise ValueError('Initial native tags exceed observed approach stock')
        fraction = max(0., 1.-n/occupied) if occupied else 1.
        for buffer in (state.urban_arrival_buffer, state.urban_storage_release_buffer):
            if origin in buffer:
                buffer[origin] = {step: amount*fraction for step, amount in buffer[origin].items()}
    local['initial_veh'] = sum(tagged.values())
    state.native_input_route_state = local
    _check(state, cfg)
    return {'native_input_route_initial_veh': sum(tagged.values()),
            'native_input_route_initial_scope': 'Exclusive input source and first connector; initial vehicles already in shared downstream roads retain the existing aggregate route approximation.'}


def receive_generated(state, cfg, no, vehicles, step):
    inputs = _inputs(cfg)
    if no not in inputs: return False
    local = state.native_input_route_state
    if local['last_step'] != step: raise ValueError('Native route generation requires current urban advance')
    first = inputs[no]['route_stages'][0]
    local['cohorts'].append(_cohort(no, 0, vehicles, step+_travel(state,cfg,first)))
    local['received_veh'] += vehicles
    _check(state, cfg)
    return True


def advance(state, cfg, step):
    inputs = _inputs(cfg)
    if not inputs: return {}
    from src.models import urban_queue_model as uqm
    local = state.native_input_route_state
    ledger = get_ledger(state)
    capture = ledger is not None and ledger.captures_response
    if step != local['last_step']+1: raise ValueError('Native route tags require sequential private steps')
    additions = []
    for cohort in local['cohorts']:
        if cohort['queued'] or cohort['due'] > step: continue
        stage = inputs[cohort['input']]['route_stages'][cohort['stage']]
        gate = stage.get('native_fixed_gate')
        if gate and not cohort.get('native_gate_passed', False):
            start_sec = step*cfg.simulation.T_u_sec
            green_at = _first_native_green(gate, start_sec, start_sec+cfg.simulation.T_u_sec)
            if capture:
                # This existing gate is timing-only. Its eligible tag quantity
                # is not a saturation capacity or a physical stock transfer.
                eligible = cohort['vehicles'] if green_at is not None else 0.
                ledger.record_resource_allocation('native_timing_eligibility',
                    'SC'+str(gate['controller'])+':SG'+str(gate['signal_group']), eligible,
                    {'input:'+cohort['input']+':stage:'+str(cohort['stage']):eligible})
            if green_at is None: continue
            # Gate crossing only changes a tag's transit phase. The existing
            # storage remains the sole stock owner; no area event is emitted.
            cohort['native_gate_passed'] = True
            cohort['native_gate_passage_sec'] = green_at
            cohort['due'] = math.ceil(green_at/cfg.simulation.T_u_sec)+_travel(
                state,cfg,stage,gate['post_gate_distance_m'])
            continue
        movement, origin = stage['movement'], stage['origin']
        queue = state.urban_movement_queue.get(movement, 0.)
        available = max(0., uqm._queue_max(cfg,movement,cfg.network.urban_movements[movement])-queue)
        n = min(cohort['vehicles'], available)
        if capture:
            ledger.record_resource_allocation('native_route_queue_receiving', 'movement:'+movement,
                available, {'input:'+cohort['input']+':stage:'+str(cohort['stage']):n})
        if n <= 0: continue
        state.urban_link_storage[origin] += n
        state.urban_movement_queue[movement] = queue+n
        emit_transfer(state,cfg,'storage:'+origin,'movement:'+movement,n,preserve_area=True)
        if n < cohort['vehicles']:
            cohort['vehicles'] -= n
            additions.append(dict(cohort, vehicles=n, queued=True))
        else:
            cohort['queued'] = True
    local['cohorts'].extend(additions)
    local['last_step'] = step
    _check(state, cfg)
    return {'native_input_route_tagged_veh': sum(c['vehicles'] for c in local['cohorts'])}


def receive_accepted(state, cfg, movement, vehicles, step):
    """Called after the ordinary single queue debit, receipt and area event."""
    inputs = _inputs(cfg)
    if not inputs: return False
    local = state.native_input_route_state
    matching = [c for c in local['cohorts'] if c['queued'] and
                inputs[c['input']]['route_stages'][c['stage']]['movement'] == movement]
    if not matching: return False
    from src.models import urban_queue_model as uqm
    if local['last_step'] != step: raise ValueError('Native accepted route transfer has wrong step')
    before = state.urban_movement_queue.get(movement, 0.)+vehicles
    tagged = sum(c['vehicles'] for c in matching)
    if tagged > before+EPS: raise ValueError('Native route tags exceed shared movement queue')
    accepted_tagged = 0.; additions = []
    for cohort in matching:
        accepted = vehicles*cohort['vehicles']/before if before else 0.
        cohort['vehicles'] -= accepted
        accepted_tagged += accepted
        stages = inputs[cohort['input']]['route_stages']
        if accepted > 0 and cohort['stage']+1 < len(stages):
            index = cohort['stage']+1
            additions.append(_transit_cohort(cohort['input'],index,accepted,step,state,cfg))
        else:
            local['completed_veh'] += accepted
    # Every positive residual remains physical stock. Dropping several values
    # individually below EPS would accumulate an unaccounted route loss.
    local['cohorts'] = [c for c in local['cohorts'] if c['vehicles'] > 0.]+additions
    # Keep final receipts on the existing sink travel path. Only intermediate
    # tagged receipts bypass the ordinary downstream beta draw.
    intermediate = sum(c['vehicles'] for c in additions)
    ordinary = max(0., vehicles-intermediate)
    target = cfg.network.urban_movements[movement]['receiving_link']
    due = step+uqm._link_delay_steps(state,cfg,target)
    if ordinary:
        if target in uqm.approach_routing(cfg): uqm._schedule(state.urban_arrival_buffer,target,due,ordinary)
        uqm._schedule(state.urban_storage_release_buffer,target,due,ordinary)
    _check(state, cfg)
    return True
