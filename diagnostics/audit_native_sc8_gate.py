"""Read-only native 1096 route geometry and unactuated SC8 clock evidence.

An explicit new output is required. No model, input, native program or run changes.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET

from evaluation.controllers.route_choice_corridor import _length, _travel_segments, _validate_path
from evaluation.controllers.fixed_signal_schedule import _union_green_overlap
from plant.src.vissim_strict.signal_program import parse_sig

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
SIG = ROOT / 'network/real_world_gaepo_modi/개포동 test-bed15.sig'
PLAN = ROOT / 'outputs/signal_group_actuation_plan_mainline_20260825.json'
MEMBERSHIP = ROOT / 'diagnostics/control_area_membership.json'
CONTRACT = ROOT / 'diagnostics/control_area_route_contract_physical_routes.json'
LSA = ROOT / 'evaluation/runs/codex_area_observed_nc_s13_20260910/vissim_eval/modi_eval_userfix Ver2_001.lsa'
PATH = ['201', '10319', '199', '10314', '194', '10322', '1210009600',
        '10333', '1220007402', '10304', '1220007401', '10298', '1220044400']


def pin(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def geometry(tree, plan):
    links = {n.get('no'): n for n in tree.findall('./links/link')}
    heads = {n.get('no'): n for n in tree.findall('./signalHeads/signalHead')}
    sc = tree.find('./signalControllers/signalController[@no="8"]')
    if (sc is None or sc.get('active') != 'true' or sc.get('type') != 'FIXEDTIME'
            or sc.get('progNo') != '1' or float(sc.get('offset')) != 0
            or sc.get('supplyFile2') != '#data#개포동 test-bed15.sig'
            or '8' in plan['controllers']):
        raise ValueError('SC8 must remain this unactuated native fixed-time controller')
    dec = tree.find('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no="1102"]')
    routes = dec.findall('./vehRoutSta/vehicleRouteStatic')
    if (dec.get('link') != '201' or dec.get('allVehTypes') != 'true'
            or dec.get('routeChoiceMeth') != 'STATIC' or len(routes) != 1):
        raise ValueError('1096 requires the single native source route')
    route = routes[0]
    path = ['201'] + [n.get('key') for n in route.findall('./linkSeq/intObjectRef')] + [route.get('destLink')]
    if path != PATH or route.get('no') != '1':
        raise ValueError('Native 1102:1 ordered path changed')
    _validate_path(path, links)
    lengths = {k: _length(links[k]) for k in path}
    segment_path = path[path.index('10333'):path.index('10298')]
    next_head = min(float(heads[k].get('pos')) for k in ('1080401', '1080402'))
    whole = _travel_segments(segment_path, links, lengths, next_head)
    whole_distance = sum(s['stop'] - s['start'] for s in whole)
    gate_heads = []
    expected = {'150401': ('2', 200.803081), '150402': ('1', 200.859711)}
    for key, (lane, pos) in expected.items():
        h = heads[key]
        if (h.get('lane') != '1220007402 '+lane or h.get('sg') != '8 4'
                or h.get('allVehTypes') != 'true' or float(h.get('complRate')) != 1
                or not math.isclose(float(h.get('pos')), pos, abs_tol=1e-9, rel_tol=0)):
            raise ValueError('SC8 source head authority or position changed')
        pre = _travel_segments(segment_path[:2], links, lengths, pos)
        post = [dict(s) for s in whole[1:]]
        post[0]['start'] = pos
        before = sum(s['stop']-s['start'] for s in pre)
        after = sum(s['stop']-s['start'] for s in post)
        if any(s['stop'] < s['start'] for s in pre+post) or not math.isclose(before+after, whole_distance, abs_tol=1e-9):
            raise ValueError('Native gate split must preserve exactly the existing transit distance')
        gate_heads.append({'head': key, 'lane': lane, 'position_m': pos,
                           'pre_gate_segments': pre, 'post_gate_segments': post,
                           'pre_gate_distance_m': before, 'post_gate_distance_m': after})
    on_link = {k for k, h in heads.items() if h.get('lane').split()[0] == '1220007402' and h.get('sg') == '8 4'}
    if on_link != set(expected) or len(links['1220007402'].findall('./lanes/lane')) != 2:
        raise ValueError('SC8 gate must cover exactly these two native lanes')
    return {'input': '1096', 'decision': '1102', 'route': '1', 'path': path,
            'decision_position_m': float(dec.get('pos')), 'controller': '8', 'signal_group': '4',
            'program_no': 1, 'controller_offset_sec': 0., 'unique_lanes': 2,
            'selected_plan_excludes_controller': True, 'existing_storage': 'SC7_to_SC108',
            'upstream_movement': 'SC7_E_SC16_to_S_SC108', 'downstream_movement': 'SC108_N_SC7_to_S',
            'heads': gate_heads, 'existing_stage_segments': whole, 'existing_stage_distance_m': whole_distance,
            'upstream_head_to_receipt_connector_m': float(links['10333'].find('fromLinkEndPt').get('pos'))-float(heads['140101'].get('pos')),
            'downstream_head_lane_spread_m': abs(float(heads['1080401'].get('pos'))-float(heads['1080402'].get('pos'))),
            'clock_capacity_claim': 'Timing and geometry only; no new or empirically identified saturation capacity.'}


def clock_audit(program, lsa_path):
    rows = []
    with lsa_path.open(encoding='utf-8-sig', errors='replace') as stream:
        for line in stream:
            c = [s.strip() for s in line.split(';')]
            if len(c) >= 5 and c[2:4] == ['8', '4']:
                rows.append({'sec': float(c[0]), 'native_cycle_sec': float(c[1]), 'state': c[4].upper()})
    if not rows or any(b['sec'] <= a['sec'] for a, b in zip(rows, rows[1:])):
        raise ValueError('Native SC8 events missing or out of order')
    mismatch = {'event_state': [], 'event_cycle_phase': [], 'dense_state': [], 'one_second_green_overlap': []}
    for row in rows:
        t = row['sec']
        if program.state_at(t, '4', controller_offset_sec=0) != row['state']:
            mismatch['event_state'].append(row)
        if not math.isclose((t-program.program_offset_sec)%program.cycle_length_sec, row['native_cycle_sec'], abs_tol=1e-9):
            mismatch['event_cycle_phase'].append(row)
    i = 0
    for t in range(math.ceil(rows[0]['sec']), 5400):
        while i+1 < len(rows) and rows[i+1]['sec'] <= t:
            i += 1
        if program.state_at(t, '4', controller_offset_sec=0) != rows[i]['state']:
            mismatch['dense_state'].append(t)
        if _union_green_overlap(program, ('4',), t, t+1, 0) != float(rows[i]['state'] == 'GREEN'):
            mismatch['one_second_green_overlap'].append(t)
    return {'event_count': len(rows), 'first_event_sec': rows[0]['sec'], 'last_event_sec': rows[-1]['sec'],
            'dense_window_sec': [math.ceil(rows[0]['sec']), 5399], 'mismatches': mismatch,
            'first_three_events': rows[:3], 'last_three_events': rows[-3:],
            'canonical_green_seconds_0_5400': _union_green_overlap(program, ('4',), 0, 5400, 0),
            'valid': not any(mismatch.values())}


def build():
    proof = geometry(ET.parse(NETWORK), json.loads(PLAN.read_text(encoding='utf-8-sig')))
    program = parse_sig(SIG, 1)
    membership = set(map(str, json.loads(MEMBERSHIP.read_text())['inside_links']))
    if not all(s['link'] in membership for s in proof['existing_stage_segments']):
        raise ValueError('Native intermediate gate must remain wholly inside the existing area')
    contract = json.loads(CONTRACT.read_text())
    for key, expected in [(proof['upstream_movement'], ('1210009600', '10333', '1220007402')),
                          (proof['downstream_movement'], ('1220007401', '10298', '1220044400'))]:
        turns = contract['movement:'+key]['physical_turns']
        if len(turns) != 1 or tuple(turns[0][k] for k in ('from_link', 'connector', 'to_link')) != expected:
            raise ValueError('Existing movement physical receipt contract changed')
    proof.update({'schema': 'native-1096-sc8-gate-proof/v1', 'network': pin(NETWORK),
                  'selected_plan': pin(PLAN), 'sig_file': pin(SIG), 'membership': pin(MEMBERSHIP),
                  'physical_route_contract': pin(CONTRACT), 'native_lsa': pin(LSA),
                  'sig_internal_controller_id': program.controller_id,
                  'cycle_sec': program.cycle_length_sec, 'program_offset_sec': program.program_offset_sec,
                  'phase_intervals': [dict(start_sec=x.start_sec, end_sec=x.end_sec, state=x.state)
                                      for x in program.sg_timelines['4'].intervals],
                  'clock': 'Canonical parse_sig state_at and fixed_signal_schedule._union_green_overlap; phase=(t-1)%120.',
                  'clock_audit': clock_audit(program, LSA),
                  'limits': ['LSA validates only unactuated native SC8; it is not a COM override readback.',
                             'No observed state is claimed before the first recorded SC8/4 event.',
                             'Tagged source201/10319 cohort only; ordinary shared-road traffic is not newly route-resolved.',
                             'Per-lane boundaries are recorded; min-head collapse is an explicit 0.05663m aggregate approximation.',
                             'Distance split preserves existing stage convention; its upstream head-to-connector gap is reported separately.',
                             'A common capacity pool must serve eligible cohorts once; two heads do not mean two separately duplicated pools.']})
    proof['producer'] = pin(Path(__file__))
    if not proof['clock_audit']['valid']:
        raise ValueError('Native SC8 clock differs from completed NC events')
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build()
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps({'output': str(args.output), 'clock': report['clock_audit'],
                      'distance_m': report['existing_stage_distance_m']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
