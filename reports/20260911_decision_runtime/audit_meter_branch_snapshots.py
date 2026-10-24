"""Bounded saved-snapshot inventory; no model, COM, prediction, or demand fit."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'evaluation/runs/codex_native_clock_fw080_u050_open_v2'
DECISIONS = RUN / 'decisions_codex_native_clock_fw080_u050_open_v2'
MAPPING = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
DESIRED = ROOT / 'diagnostics/demand_sweep/global050/desired_destinations.csv'
CHECKS = ROOT / 'diagnostics/demand_sweep/global050/checks.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    targets = [OUT / 'METER_BRANCH_OBSERVATIONS.json', OUT / 'METER_BRANCH_OBSERVATIONS.md']
    if any(p.exists() for p in targets):
        raise FileExistsError('Preserve previous evidence; choose a fresh version')
    states = {sec: load(DECISIONS / f'state_{sec:06d}.json') for sec in (900, 1050)}
    network_paths = {Path(s['network_path']) for s in states.values()}
    assert len(network_paths) == 1
    network_path = next(iter(network_paths))
    source_paths = [Path(__file__), MAPPING, DESIRED, CHECKS, network_path]
    source_paths += [DECISIONS / f'state_{sec:06d}.json' for sec in states]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    doc = ET.parse(network_path).getroot()
    links = {int(x.get('no')): x for x in doc.findall('./links/link')}
    mapping = load(MAPPING)
    meters = {int(m['connector']): m for m in mapping['ramp_meters']}
    assert len(meters) == 8
    endpoints = {}
    for link, node in links.items():
        f, t = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if f is not None and t is not None:
            endpoints[link] = {'from_link': int(f.get('lane').split()[0]), 'from_pos_m': float(f.get('pos')),
                               'to_link': int(t.get('lane').split()[0]), 'to_pos_m': float(t.get('pos'))}

    def adjacent(a, b):
        return ((a in endpoints and endpoints[a]['to_link'] == b)
                or (b in endpoints and endpoints[b]['from_link'] == a))

    routes, support, route_evidence = {}, defaultdict(set), {}
    for decision in doc.iter('vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path = [int(decision.get('link'))]
            path += [int(x.get('key')) for x in route.findall('./linkSeq/intObjectRef')]
            path.append(int(route.get('destLink')))
            # A route wholly inside one link can repeat its source as destination.
            path = [x for i, x in enumerate(path) if i == 0 or x != path[i-1]]
            key = (int(decision.get('no')), int(route.get('no')))
            assert key not in routes
            item = {'decision_no': key[0], 'route_no': key[1], 'path': path,
                    'start_pos_m': float(decision.get('pos')), 'end_pos_m': float(route.get('destPos')),
                    'all_links_exist': all(x in links for x in path),
                    'continuous': all(adjacent(a, b) for a, b in zip(path, path[1:]))}
            routes[key] = item
            for i, link in enumerate(path):
                if link in meters:
                    support[link].update(path[:i])
                    route_evidence[f'{key[0]}:{key[1]}'] = item
    # Explicit partial source-cohort paths extend the inspection scope only.
    # Their probabilities NEVER allocate current vehicles to a ramp.
    partial_rows = list(csv.DictReader(DESIRED.open(encoding='utf-8-sig', newline='')))
    for row in partial_rows:
        if row['input_no'] not in {'1100', '1101'}:
            continue
        path = [int(x) for x in row['ordered_path'].split('→')]
        for i, link in enumerate(path):
            if link in meters:
                support[link].update(path[:i])
    ownership = {}
    for ramp, meter in meters.items():
        assert ramp in endpoints
        assert meter['from_link'] == endpoints[ramp]['from_link']
        assert meter['to_link'] == endpoints[ramp]['to_link']
        support[ramp].add(endpoints[ramp]['from_link'])
        heads = [x for x in doc.iter('signalHead') if int(x.get('lane').split()[0]) == ramp
                 and x.get('sg') == f"{meter['sc_no']} {meter['sg_no']}"]
        head_by_lane = {int(h.get('lane').split()[1]): float(h.get('pos')) for h in heads}
        assert len(heads) == len(head_by_lane) == len(links[ramp].findall('./lanes/lane'))
        ownership[str(ramp)] = {'meter_id': meter['id'], 'model_group': meter['model_ramp_key'],
            'freeway_owner': meter['to_model_link'], 'sg': heads[0].get('sg'),
            'head_pos_m_by_lane': head_by_lane,
            'physical_endpoints': endpoints[ramp], 'approach_scope_links': sorted(support[ramp])}

    def locate(record, route_record):
        if route_record.get('route_decision_type') != 'STATIC':
            return None, 'missing_or_nonstatic_route'
        k = (route_record.get('route_decision_no'), route_record.get('route_no'))
        if k not in routes:
            return None, 'route_id_not_in_pinned_static_network'
        r = routes[k]
        if not r['all_links_exist'] or not r['continuous']:
            return None, 'static_path_geometry_not_continuous'
        path, link, pos = r['path'], int(record['link_no']), float(record['position_m'])
        indices = [i for i, x in enumerate(path) if x == link]
        if len(indices) != 1:
            return None, 'current_link_absent_or_repeated_in_route'
        i = indices[0]
        lo = r['start_pos_m'] if i == 0 else 0.0
        hi = r['end_pos_m'] if i == len(path)-1 else float('inf')
        if i > 0 and path[i-1] in endpoints:
            lo = max(lo, endpoints[path[i-1]]['to_pos_m'])
        if i + 1 < len(path) and path[i+1] in endpoints:
            hi = min(hi, endpoints[path[i+1]]['from_pos_m'])
        if pos < lo - 1e-6 or pos > hi + 1e-6:
            return None, 'position_outside_current_route_interval'
        future = [x for x in path[i+1:] if x in meters]
        if len(future) == 0:
            return None, 'no_explicit_future_meter_in_current_route'
        if len(future) != 1:
            return None, 'multiple_future_meters_in_current_route'
        return future[0], 'explicit_unique_future_meter'

    result = {'schema': 'saved-snapshot-physical-meter-branches/v2', 'source_sha256': pins,
        'network': str(network_path.relative_to(ROOT)), 'run': str(RUN.relative_to(ROOT)),
        'method': {'stopped_threshold_kph': 1.0, 'stock_is_not_stopped_queue': True,
            'approach_scope': 'Union of pinned static-route prefixes containing a physical meter, its immediate feeder link, and existing partial1100/1101 source paths. A scoped inspection region, not all upstream OD paths.',
            'known_upstream': 'Same vehicle ID joins location and current STATIC route. Current link occurs once, path is physically continuous, position fits current segment, exactly one future meter is explicit.',
            'unknown': 'No route, unavailable or stale route, no explicit future meter before a current route ending within the inspection scope, or ambiguous location. A valid current route ending outside the scope without an explicit future meter is reported separately as current_route_leaves_scope, not forever-nonramp OD. No static probability multiplies observed vehicle counts. Unknown lists per meter can overlap and must not be summed.',
            'connector_stock': 'Physical current link membership, independent of route classification; before/after head and stopped subsets shown separately.',
            'classification_scope': 'Current active static route only. Combined/look-ahead route chains and future unselected decisions are not inferred. Known counts are conservative lower bounds, not complete ramp OD or arrival-rate estimates.',
            'source_generation_demand': 'Existing72-row desired table covers only origins1098/1100/1101; selected80/50 reuses only urban1100/1101 rows unchanged. No complete8branch or4group desired lambda certificate.'},
        'ownership': ownership, 'static_routes_with_meter': route_evidence, 'snapshots': {},
        'full_origin_helper_inventory': {'found': 'diagnostics/demand_sweep_origin_routes.py',
            'scope': 'Isolated input1098/1130 intervention producer, not a general full-origin routing-graph solver. It was read but not executed.',
            'full_origin_graph_computed': False},
        'execution': {'COM': 0, 'model': 0, 'VISSIM': 0, 'FZP_reads': 0, 'source_config_writes': 0}}
    for sec, state in states.items():
        a, b = state['vehicle_records'], state['vehicle_routes']
        assert a['complete'] and b['complete'] and a['record_count'] == b['record_count']
        assert a['capture_sim_sec_before'] == a['capture_sim_sec_after'] == b['sim_sec_before'] == b['sim_sec_after'] == sec
        vehicles = {int(x['veh_no']): x for x in a['records']}
        assignments = {int(x['veh_no']): x for x in b['records']}
        assert len(vehicles) == a['record_count'] and set(vehicles) == set(assignments)
        classifications = {v: locate(r, assignments[v]) for v, r in vehicles.items()}
        snap = {'vehicle_count': len(vehicles), 'ramp_counts_model_groups': state['ramp_counts'],
                'all_vehicle_route_classification_counts': dict(Counter(reason for _, reason in classifications.values())), 'branches': {}}
        for ramp in meters:
            heads = ownership[str(ramp)]['head_pos_m_by_lane']
            physical = [r for r in vehicles.values() if int(r['link_no']) == ramp]
            stopped = lambda r: float(r['speed_kph']) <= 1.0
            before = [r for r in physical if float(r['position_m']) <= heads[int(r['lane_no'])]]
            known = [r for v, r in vehicles.items() if classifications[v][0] == ramp and int(r['link_no']) != ramp]
            other, leaves_scope, unknown = [], [], defaultdict(list)
            for v, r in vehicles.items():
                if int(r['link_no']) not in support[ramp] or int(r['link_no']) in meters:
                    continue
                destination, reason = classifications[v]
                if destination == ramp:
                    continue
                if destination is not None:
                    other.append(v)
                elif (reason == 'no_explicit_future_meter_in_current_route'
                      and routes[(assignments[v]['route_decision_no'], assignments[v]['route_no'])]['path'][-1] not in support[ramp]):
                    # The complete currently selected route leaves the inspection
                    # region. Do not mix an explicit city turn with an unselected
                    # downstream ramp decision. Later re-entry remains unmodelled.
                    leaves_scope.append(v)
                else:
                    unknown[reason].append(v)
            known_details = [{'veh_no': r['veh_no'], 'link_no': r['link_no'], 'lane_no': r['lane_no'],
                'position_m': r['position_m'], 'speed_kph': r['speed_kph'], 'stopped': stopped(r),
                'route': f"{assignments[int(r['veh_no'])]['route_decision_no']}:{assignments[int(r['veh_no'])]['route_no']}"}
                for r in sorted(known, key=lambda r: r['veh_no'])]
            reasons = {reason: {'count': len(ids), 'stopped': sum(stopped(vehicles[v]) for v in ids),
                'vehicle_ids': sorted(ids)} for reason, ids in sorted(unknown.items())}
            snap['branches'][str(ramp)] = {'physical_inventory': len(physical), 'physical_stopped': sum(map(stopped, physical)),
                'inventory_before_head': len(before), 'stopped_before_head': sum(map(stopped, before)),
                'inventory_after_head': len(physical)-len(before), 'physical_vehicle_ids': sorted(int(r['veh_no']) for r in physical),
                'known_upstream_inventory': len(known), 'known_upstream_stopped': sum(map(stopped, known)),
                'known_upstream_by_link': dict(Counter(str(r['link_no']) for r in known)), 'known_upstream_vehicles': known_details,
                'scoped_known_other_meter_count': len(other), 'scoped_unknown_count': sum(len(v) for v in unknown.values()),
                'scoped_current_route_leaves_scope_count': len(leaves_scope),
                'scoped_current_route_leaves_scope_stopped': sum(stopped(vehicles[v]) for v in leaves_scope),
                'scoped_current_route_leaves_scope_vehicle_ids': sorted(leaves_scope),
                'scoped_unknown_stopped': sum(stopped(vehicles[v]) for ids in unknown.values() for v in ids),
                'scoped_unknown_by_reason': reasons}
            assert len(physical) == state['local_observation']['link_counts'].get(str(ramp), 0)
            assert sum(map(stopped, physical)) == state['local_observation']['link_stopped_counts'].get(str(ramp), 0)
        result['snapshots'][str(sec)] = snap
    result['source_changes'] = [name for name, value in pins.items() if sha(ROOT / name) != value]
    assert result['source_changes'] == []
    targets[0].write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    lines = ['# 8개 미터의 저장 snapshot 관측', '',
        '고속도로80%·도시50%·seed13의 open_v2 실행에서 900초와1050초의 저장 상태만 비교했다. 새 COM·모델·VISSIM·FZP 스캔은 없다. 물리 connector 재고와 정지 차량을 분리했고, 현재 static route에 목적 미터가 명시된 상류 차량만 램프행으로 셌다. 이것은 접근 재고의 보수적 부분 집계이며 희망 수요나 실제 도착률 추정치가 아니다.', '',
        '위치/경로는 같은 차량 번호와 같은 정지 시각으로 조인했다. 현재 link가 경로에 한 번만 등장하고, 경로 연결이 연속이며, 차량 위치가 현재 경로 구간 안에 있고, 미래 미터가 한 개만 명시돼야 확정했다. 66의1124:1처럼68까지만 정해진 경로에서 다음1135 선택은 추정하지 않았다. 상류 조사 범위는 미터를 포함한 정적 경로의 prefix+직접 feeder+기존1100/1101 부분 원점 경로다. 조사 범위 밖의 미선택 차량은 추가로 있을 수 있다.', '',
        '표의 `connector`는 재고/정지, `확정 상류`는 명시적 램프행 재고/정지, `미확정`은 해당 조사 범위의 미확정 재고/정지다. `현재 타경로`는 현재 선택 경로에 미래 미터가 없고 경로가 조사 범위 밖에서 끝나는 차량으로, 도시47행1124:2 등을 미확정 램프 선택과 분리한다. 향후 다른 경로로 재진입하지 않는다는 뜻은 아니다. 같은 미확정 차량이 여러 램프 조사 범위에 포함될 수 있으므로 램프 간 합산하지 않는다. 미확정 차량 전부가 나중에 램프로 가는 것도 아니다.', '',
        '| 초 | 미터·그룹·소유자 | connector 재고/정지 | 정지선 이전 재고/정지 | 확정 상류 재고/정지 | 미확정 재고/정지 | 현재 타경로 재고/정지 |',
        '|---:|---|---:|---:|---:|---:|---:|']
    for sec, snap in result['snapshots'].items():
        for ramp, values in snap['branches'].items():
            o = ownership[ramp]
            lines.append(f"| {sec} | {ramp} · {o['model_group']} · {o['freeway_owner']} | {values['physical_inventory']}/{values['physical_stopped']} | {values['inventory_before_head']}/{values['stopped_before_head']} | {values['known_upstream_inventory']}/{values['known_upstream_stopped']} | {values['scoped_unknown_count']}/{values['scoped_unknown_stopped']} | {values['scoped_current_route_leaves_scope_count']}/{values['scoped_current_route_leaves_scope_stopped']} |")
    lines += ['', '8SG의 주소, 실제 망에서 확인한 진입/합류 link와 정지선, 모든 확정 상류 차량 ID·경로·위치, 미확정 사유별 차량 ID, 입력 파일 SHA는 동명 JSON에 있다. 지도 설명문의 오래된 도로 명칭은 사용하지 않았다. 순간 정지 기준은 속도≤1km/h다. connector 재고나 4그룹 ramp_counts를 모두 대기열 Q로 바꾸지 않는다.', '',
        '희망 수요는 별도의 `METER_DEMAND_EXISTING_EVIDENCE.md`를 따른다. 기존 72행 표는 세 원점의 부분 분해이며, 80/50에서는 도시1100/1101 수치만 그대로 대응한다. 전체8branch 또는4group의 완전한 λ가 아니다. 기존 helper 검색에서 찾은 demand_sweep_origin_routes.py는 고립 원점1098의1130 경로 개입 생산기다. 일반적인 전 원점 그래프 풀이가 아니므로 실행하지 않았고, 새 큰 경로 프레임워크도 만들지 않았다.', '',
        '다음 진단은 이 확정/미확정 구분을 유지하면서 10646/10681로 이어지는 다른 원점과 아직 선택되지 않은 다음 경로를 필요한 범위에서 보완해야 한다. 단일 snapshot 간 차량 수 차이를 도착률로 만들지 않으며, 신호 방출·이동 시간·미삽입 때문에 원점 cohort 수요와 같은 시각 도착은 다를 수 있다.', '',
        '재현: 이 폴더의 audit_meter_branch_snapshots.py. 기존 결과가 있으면 덮어쓰지 않고 실패한다. 첫 v1은 현재 타경로를 미확정에 포함한 보수적 집계였으며, 원본 MD/JSON/script를 v1 이름으로 보존한 뒤 이 v2에서 분리했다. 첫 진단 script의 단일 차로 정지선 가정은 두 차로인10482/10681에서 assertion으로 중단됐고, 모든 차로의 실제 정지선 위치를 각각 읽도록 수정한 뒤 집계했다.', '']
    targets[1].write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'outputs': [str(p.relative_to(ROOT)) for p in targets], 'source_changes': [],
        'snapshots': {sec: {r: {k: v[k] for k in ('physical_inventory','physical_stopped','known_upstream_inventory','known_upstream_stopped','scoped_unknown_count','scoped_unknown_stopped')} for r,v in s['branches'].items()} for sec,s in result['snapshots'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
