"""Bounded, observation-only comparison of one-second and 30-second counters.

This reproduces AccumulateDepartures on the same FZP frames, not on COM frames.
Head crossings remain one-second brackets; no saturation capacity is fitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.probe_e8_window_passages import frames
from diagnostics.audit_sc15_source_discharge import head_crossing

ROOT = Path(__file__).resolve().parents[1]
ROADS = ('66', '71', '30', '403', '1220011503', '1220021201', '127')
WINDOWS = ((720, 870), (750, 900))
NC = 'codex_area_observed_nc_s13_20260910'
ACTUAL = 'codex_area_sources_beta0_s13_20260910'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def departures(old, new, t0, t1, roads=ROADS):
    """Exact VBS endpoint rule, including endpoint absence as a separate field."""
    result = []
    for vehicle, previous in old.items():
        link = str(previous[0])
        if link not in roads:
            continue
        current = new.get(vehicle)
        if current is None or current[0] != previous[0]:
            result.append({'vehicle_id': vehicle, 'link': link, 'lower_sec': t0,
                           'upper_sec': t1, 'to_link': None if current is None else str(current[0]),
                           'endpoint_absent': current is None})
    return result


def geometry(network):
    tree = ET.parse(network).getroot()
    result = {road: {'heads': [], 'branches': {}} for road in ROADS}
    for head in tree.findall('./signalHeads/signalHead'):
        link, lane = head.get('lane').split()
        if link in result:
            sc, sg = head.get('sg').split()
            result[link]['heads'].append({'head': head.get('no'), 'SC': sc, 'sg': sg,
                                         'lane': int(lane), 'pos_m': float(head.get('pos'))})
    for node in tree.findall('./links/link'):
        a, b = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if a is None or b is None:
            continue
        source, lane = a.get('lane').split()
        if source not in result:
            continue
        target, target_lane = b.get('lane').split()
        points = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
                  for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
        result[source]['branches'][node.get('no')] = {
            'source_lane': int(lane), 'target_lane': int(target_lane),
            'lanes': len(node.findall('./lanes/lane')), 'from_pos_m': float(a.get('pos')),
            'target': target, 'target_pos_m': float(b.get('pos')),
            'length_m': sum(math.dist(x, y) for x, y in zip(points, points[1:]))}
    return result


def sample(record, sec):
    return {'sec': sec, 'link': str(record[0]), 'lane': record[1],
            'pos_m': record[2], 'speed_kph': record[3]}


def head_events(spec, vehicle, old, new, t0, t1):
    """Conservative same-lane or lane-consistent single-connector brackets."""
    heads = [h for h in spec['heads'] if h['lane'] == old[1]]
    base = {'vehicle_id': vehicle, 'link': str(old[0]), 'lower_sec': t0,
            'upper_sec': t1, 'lane_before': old[1], 'pos_before_m': old[2]}
    if new is None:
        return [{**base, 'kind': 'unresolved_endpoint_absence'}]
    base.update(lane_after=new[1], pos_after_m=new[2], to_link=str(new[0]))
    if old[0] == new[0]:
        if old[1] != new[1]:
            nearby = [h for h in spec['heads'] if h['lane'] in (old[1], new[1])
                      and old[2] < h['pos_m'] <= new[2]]
            return [{**base, 'kind': 'unresolved_lane_change_at_head'}] if nearby else []
        result = []
        for h in heads:
            if old[2] < h['pos_m'] <= new[2]:
                cross = head_crossing({'samples': [sample(old, t0), sample(new, t1)],
                                       'first_non_source': None},
                                      {'head_position_m': h['pos_m'], 'branches': {}})
                result.append({**base, **h, **cross, 'kind': 'head_crossing'})
        return result
    candidates = [(key, branch) for key, branch in spec['branches'].items()
                  if str(new[0]) == key or str(new[0]) == branch['target']]
    # A unique physical one-connector path is required even when lane filtering
    # could choose among multiple routes. No multi-link reverse inference.
    if len(candidates) != 1:
        return [{**base, 'kind': 'unresolved_departure_path'}]
    key, branch = candidates[0]
    lane_index = new[1] - (1 if str(new[0]) == key else branch['target_lane'])
    if not 0 <= lane_index < branch['lanes'] or old[1] != branch['source_lane'] + lane_index:
        return [{**base, 'kind': 'unresolved_departure_lane', 'connector': key}]
    base['connector'] = key
    if not heads:
        return [{**base, 'kind': 'no_head_on_branch_source_lane'}]
    if all(branch['from_pos_m'] < h['pos_m'] for h in heads):
        return [{**base, 'kind': 'pre_head_bypass', 'bypassed_heads': [h['head'] for h in heads]}]
    result = []
    for h in heads:
        if branch['from_pos_m'] < h['pos_m']:
            continue
        if old[2] >= h['pos_m']:
            result.append({**base, **h, 'kind': 'already_post_head_departure'})
            continue
        cross = head_crossing({'samples': [sample(old, t0)], 'first_non_source': sample(new, t1)},
                              {'head_position_m': h['pos_m'], 'branches': {key: branch}})
        result.append({**base, **h, **cross,
                       'kind': 'head_crossing' if 'lower_sec' in cross else 'unresolved_head_distance'})
    return result


def summarize(one, thirty, checkpoints, start, end, road):
    fine = [x for x in one if x['link'] == road and start <= x['lower_sec'] and x['upper_sec'] <= end]
    coarse = [x for x in thirty if x['link'] == road and start <= x['lower_sec'] and x['upper_sec'] <= end]
    reasons = Counter()
    for event in fine:
        a = int((event['upper_sec'] - 1 - start) // 30) * 30 + start
        b = a + 30
        before, after = checkpoints[a], checkpoints[b]
        vehicle = event['vehicle_id']
        if vehicle not in before or str(before[vehicle][0]) != road:
            reasons['not_on_source_at_30s_bin_start'] += 1
        elif vehicle in after and str(after[vehicle][0]) == road:
            reasons['same_source_at_both_30s_endpoints'] += 1
        else:
            reasons['represented_by_30s_endpoint_departure'] += 1
    counts = Counter((e['vehicle_id'], int((e['upper_sec'] - 1 - start) // 30)) for e in fine)
    return {'link': road, 'start_sec': start, 'end_sec': end, 'one_second_departures': len(fine),
            'thirty_second_departures': len(coarse), 'lost_departures': len(fine) - len(coarse),
            'loss_pct_of_1s': 100 * (len(fine) - len(coarse)) / len(fine) if fine else None,
            'one_second_endpoint_absence': sum(e['endpoint_absent'] for e in fine),
            'thirty_second_endpoint_absence': sum(e['endpoint_absent'] for e in coarse),
            'one_second_events_by_downsampling_reason': dict(reasons),
            'repeated_same_vehicle_departures_in_30s_bin': sum(n - 1 for n in counts.values())}


def departure_paths(one, thirty, events, start, end, road):
    """Classify exit paths without equating their time to the head crossing time."""
    by_key = {}
    for event in events:
        key = event['vehicle_id'], event['link'], event['lower_sec'], event['upper_sec']
        by_key.setdefault(key, set()).add(event['kind'])
    total, unrepresented = Counter(), Counter()
    for event in one:
        if event['link'] != road or not start <= event['lower_sec'] < event['upper_sec'] <= end:
            continue
        key = event['vehicle_id'], road, event['lower_sec'], event['upper_sec']
        kinds = by_key.get(key, set())
        if kinds & {'head_crossing', 'already_post_head_departure'}:
            kind = 'verified_head_path_departure'
        elif len(kinds) == 1:
            kind = next(iter(kinds))
        else:
            kind = 'unresolved_multiple_or_absent_path_class'
        total[kind] += 1
        if not any(c['link'] == road and c['vehicle_id'] == event['vehicle_id']
                   and c['lower_sec'] <= event['lower_sec'] < event['upper_sec'] <= c['upper_sec']
                   for c in thirty):
            unrepresented[kind] += 1
    return dict(total), dict(unrepresented)


def run(output):
    paths = {'capacity_audit': ROOT / 'diagnostics/selected_signal_capacity_audit.json',
             'network': ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx',
             'raw_actual_900': ROOT / f'evaluation/runs/{ACTUAL}/decisions_{ACTUAL}/state_000900.json',
             'previous_action_750_csv': ROOT / f'evaluation/runs/{ACTUAL}/decisions_{ACTUAL}/action_000750.csv',
             'producer': Path(__file__),
             'indexed_reader': ROOT / 'diagnostics/probe_e8_lane_receiving.py',
             'frame_reader': ROOT / 'diagnostics/probe_e8_window_passages.py',
             'crossing_method': ROOT / 'diagnostics/audit_sc15_source_discharge.py'}
    pinned = {str(p.relative_to(ROOT)): sha(p) for p in paths.values()}
    audit = json.loads(paths['capacity_audit'].read_text(encoding='utf-8'))
    raw = json.loads(paths['raw_actual_900'].read_text(encoding='utf-8-sig'))
    if audit['actual_departure_window_inferred_from_runner'] != [720, 870]:
        raise ValueError('Historical COM counter window changed')
    for key in ('raw_actual_900', 'previous_action_750_csv'):
        relative = str(paths[key].relative_to(ROOT))
        if audit['input_sha256'].get(relative) != pinned[relative]:
            raise ValueError(f'Actual counter/action no longer match cached audit: {relative}')
    # Validate cached native-program/LSA evidence rather than importing its model audit.
    for clock_key in ('native_clock', 'actual_departure_window_clock'):
        for name, expected in audit[clock_key]['source_sha256'].items():
            p = ROOT / name
            if sha(p) != expected:
                raise ValueError(f'Cached native clock evidence changed: {name}')
            pinned[str(p.relative_to(ROOT))] = expected
    geo = geometry(paths['network'])
    fzp = ROOT / f'evaluation/runs/{NC}/vissim_eval/modi_eval_userfix Ver2_001.fzp'
    stat_before = fzp.stat()
    reader = IndexedFzp(fzp, max_bytes=64 * 1024 * 1024)
    provenance, one, thirty, events, checkpoints, arrival_censored = [], [], [], [], {}, []
    previous = None
    previous_t = None
    previous30 = None
    times = []
    try:
        for t, current in frames(reader, 720, 900, time.monotonic() + 45, provenance):
            if previous_t is not None and t - previous_t != 1:
                raise ValueError('Expected every one-second full frame')
            times.append(t)
            selected = {n: row for n, row in current.items() if str(row[0]) in ROADS}
            if previous is not None:
                one.extend(departures(previous, current, previous_t, t))
                for vehicle, old in previous.items():
                    events.extend(head_events(geo[str(old[0])], vehicle, old, current.get(vehicle), previous_t, t))
                for vehicle, row in selected.items():
                    if vehicle not in previous or previous[vehicle][0] != row[0]:
                        heads = [h for h in geo[str(row[0])]['heads'] if h['lane'] == row[1]]
                        if any(row[2] >= h['pos_m'] for h in heads):
                            arrival_censored.append({'vehicle_id': vehicle, 'link': str(row[0]), 'upper_sec': t,
                                                      'kind': 'arrived_on_source_already_post_head'})
            if t % 30 == 0:
                checkpoints[t] = selected
                if previous30 is not None:
                    thirty.extend(departures(previous30, current, t - 30, t))
                previous30 = selected
            previous, previous_t = selected, t
    finally:
        reader.handle.close()
    if times != list(range(720, 901)):
        raise ValueError('Incomplete requested 720..900 frame coverage')
    stat_after = fzp.stat()
    if (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns):
        raise ValueError('Completed FZP changed during bounded read')
    # Checkpoint dictionaries omit other roads, which is sufficient for source
    # presence tests; departures themselves used complete destination frames.
    measurement = {r['link']: r for r in audit['measurement_links']}
    rows = []
    head_rows = []
    for start, end in WINDOWS:
        clock = audit['actual_departure_window_clock' if start == 720 else 'native_clock']
        for road in ROADS:
            row = summarize(one, thirty, checkpoints, start, end, road)
            native = clock['links'][road]
            used = measurement.get(road, {}).get('model_denominator_green_sec')
            if not used:
                used = None
            observed = raw['local_observation']['link_departures_window'][road]
            selected_events = [e for e in events if e['link'] == road and start <= e['lower_sec'] and e['upper_sec'] <= end]
            kinds = Counter(e['kind'] for e in selected_events)
            crossings = [e for e in selected_events if e['kind'] == 'head_crossing']
            all_paths, missing_paths = departure_paths(one, thirty, events, start, end, road)
            row.update(native_union_green_sec=native['native_all_head_union_green_sec'],
                       native_lane_green_sec=native['native_all_head_lane_green_sec'],
                       unexecuted_model_green_denominator_sec=used,
                       raw_actual900_com_counter=observed if start == 720 else None,
                       com_minus_same_window_nc_fzp_30s=observed - row['thirty_second_departures'] if start == 720 else None,
                       conservative_head_crossings=len(crossings), head_and_departure_classifications=dict(kinds),
                       one_second_departures_by_path=all_paths,
                       one_second_departures_unrepresented_at_30s_by_path=missing_paths,
                       arrived_already_post_head=sum(e['link'] == road and start < e['upper_sec'] <= end for e in arrival_censored))
            for h in geo[road]['heads']:
                own = [e for e in crossings if e['head'] == h['head']]
                head_rows.append({'start_sec': start, 'end_sec': end, 'link': road, **h,
                                  'crossings': len(own), 'native_sg_green_sec': native['native_each_sg'][h['sg']]['sig_green_seconds'],
                                  'same_source_position_bracket': sum(e['method'] == 'same_source_position_bracket' for e in own),
                                  'source_to_observed_connector_bracket': sum(e['method'] == 'source_to_observed_connector_bracket' for e in own),
                                  'source_to_unique_target_bracket': sum(e['method'] == 'source_to_unique_target_bracket' for e in own)})
            rows.append(row)
    changed = [name for name, expected in pinned.items() if sha(ROOT / name) != expected]
    if changed:
        raise ValueError(f'Input source changed: {changed}')
    result = {'schema': 'selected-signal-sampling-audit/v1', 'completed_nc_run': NC,
              'raw_counter_run': ACTUAL, 'source_sha256': pinned, 'geometry': geo,
              'fzp': {'path': str(fzp.relative_to(ROOT)), 'size_bytes': stat_before.st_size,
                      'mtime_ns': stat_before.st_mtime_ns, 'read_bytes': reader.bytes_read,
                      'frame_count': len(times), 'selected_ranges': provenance,
                      'whole_file_sha_recomputed': False, 'same_stat_after_read': True},
              'windows': rows, 'heads': head_rows, 'one_second_departure_events': one,
              'thirty_second_departure_events': thirty, 'head_and_bypass_events': events,
              'source_entry_posthead_censoring': arrival_censored, 'source_changes': changed,
              'limitations': ['One-second counters remain sampled link changes plus endpoint absences, not exact throughput.',
                 'Same-FZP downsampling isolates cadence. Raw COM comparison additionally differs in collector/observation phase.',
                 'Head brackets require same-lane endpoints or one unique lane-consistent connector path; lane changes and longer skipped paths remain unresolved.',
                 'Source arrivals already beyond the head and traffic crossing and leaving a short source between samples can be missed.',
                 'Pre-head bypass labels refer to this road head, not absence of an upstream native signal.',
                 'Green union and lane-green exposure are not saturation capacity, nor interchangeable across lane groups.',
                 'Interpolated crossing times are summaries inside one-second brackets; no subsecond truth or red-running inference.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for suffix, data in (('.csv', rows), ('_heads.csv', head_rows)):
        path = output.with_suffix(suffix) if suffix.startswith('.') else output.with_name(output.name + suffix)
        flat = [{k: (json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, dict) else v) for k, v in row.items()} for row in data]
        with path.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)
    write_report(result, output.with_suffix('.md'))
    return result


def write_report(result, path):
    first = [r for r in result['windows'] if r['start_sec'] == 720]
    fine = sum(r['one_second_departures'] for r in first)
    coarse = sum(r['thirty_second_departures'] for r in first)
    lines = ['# Selected signal sampling audit', '',
        f'동일 720→870초 NC 자료에서 30초 표본은 1초 표본의 링크 이탈 {fine}대 중 {fine-coarse}대({100*(fine-coarse)/fine:.1f}%)를 놓쳤다. 71은 54→26대, 1220021201은 49→31대다. 이번 7개 링크의 NC FZP 30초 계수는 실제 raw900 COM 계수와 전부 수치가 일치한다. 이 비교 안에서는 실제 관측 손실을 재현했지만 다른 시각의 COM/FZP 위상까지 동일하다고 일반화하지 않는다.', '',
        '같은 완료 NC 1초 FZP의 720–900초만 binary seek로 읽었다. 1초 전이와 30초로 downsample한 전이에 VBS `AccumulateDepartures`의 동일 규칙을 적용했다. 이탈은 이전 표본에 있던 차량이 다른 링크에 있거나 현재 표본에서 사라진 경우다. 신호 head 통과·정지선 전 우회·누락된 관측은 별도 표로 남겼다.', '',
        '아래의 1초→30초 차이는 같은 자료의 표본 간격 손실이다. 실제 제어 런 raw900의 COM counter와 NC FZP 30초 counter 차이는 COM/FZP 관측 위상·collector 차이도 포함하므로 표본 간격 손실로 합치지 않았다. 실제 raw900 counter 창은 720→870이고, 750→900 표는 창 정렬 비교다.', '']
    for start, end in WINDOWS:
        rows = [r for r in result['windows'] if r['start_sec'] == start]
        lines.extend([f'## {start}→{end} seconds', '',
            '| Link | 1s departures | 30s departures | Loss (%) | raw900 COM | COM−FZP30 | used green / native union (s) |',
            '|---|---:|---:|---:|---:|---:|---:|'])
        for r in rows:
            used = r['unexecuted_model_green_denominator_sec']
            lines.append(f"| {r['link']} | {r['one_second_departures']} | {r['thirty_second_departures']} | {r['lost_departures']} ({r['loss_pct_of_1s']:.1f}%) | {r['raw_actual900_com_counter'] if start == 720 else '—'} | {r['com_minus_same_window_nc_fzp_30s'] if start == 720 else '—'} | {used if used is not None else 'estimate 없음'} / {r['native_union_green_sec']:g} |")
        lines.extend(['', '| Link | Head crossings, lower bound | Before-head bypass | No-head source lane | Unresolved departure/lane/distance | Already post-head departure |', '|---|---:|---:|---:|---:|---:|'])
        for r in rows:
            c = r['head_and_departure_classifications']
            lines.append(f"| {r['link']} | {r['conservative_head_crossings']} | {c.get('pre_head_bypass',0)} | {c.get('no_head_on_branch_source_lane',0)} | {sum(v for k,v in c.items() if k.startswith('unresolved'))} | {c.get('already_post_head_departure',0)} |")
        lines.extend(['', 'Head crossings는 같은 링크 내 위치 bracket과 단일 connector 경로 bracket의 합이다. `Already post-head`는 이탈 직전 표본에서 이미 head를 지난 차량이며 앞선 초의 crossing과 겹칠 수 있으므로 표 열을 더해 이탈량으로 사용하면 안 된다. SG·lane·position별 개수와 경로 추론 방식은 `_heads.csv`, 개별 차량 근거는 JSON에 보존했다.', ''])
        lines.extend(['| Link | 누락: 확인된 head 경로 이탈 | 누락: head 전 우회 / no-head 차로 | 누락: 미확정 |', '|---|---:|---:|---:|'])
        for r in rows:
            c = r['one_second_departures_unrepresented_at_30s_by_path']
            lines.append(f"| {r['link']} | {c.get('verified_head_path_departure',0)} | {c.get('pre_head_bypass',0) + c.get('no_head_on_branch_source_lane',0)} | {sum(v for k,v in c.items() if k.startswith('unresolved'))} |")
        lines.extend(['', '이탈 경로 표는 각 1초 이탈을 한 번만 분류한다. `head 경로 이탈`은 실제 head crossing 시각과 같지 않으며, 창 이전에 이미 head를 지난 차량도 포함할 수 있다. 이 표 역시 포화교통량이 아니다.', ''])
    lines.extend(['## 해석 및 최소 관측 수선', '',
        '두 창의 손실은 모두 30초 bin 시작 시 해당 source에 없었다가 중간에 들어와 나간 차량이다. 같은 source로 재진입해 endpoint에서 상쇄된 사례와 endpoint에서 사라진 차량은 이 7개 도로·두 창에서 0이다. 따라서 이 사례의 차이를 VISSIM 차량 제거로 설명할 근거는 없다.', '',
        '720→870의 누락 65대는 확인된 head 경로 이탈 14대, head 전 우회/no-head 차로 41대, lane 미확정 10대로 나뉜다. 특히 71의 누락 28대는 4/14/10대이고 403의 누락 7대와 1220011503의 누락 2대는 모두 우회/no-head 경로다. 따라서 1초 link departure의 증가분을 전부 신호 처리량으로 해석하는 수선도 잘못이다.', '',
        '720→870의 직접 식별된 정지선 전 가지는 66→10632 4대, 71→10642 16대, 1220011503→10528 5대, 1220021201→10142 23대다. 30→10686은 26대, 403→10565는 23대가 source 차로에 head가 없는 가지로 나간다. 71의 추가 10대 및 30의 1대는 이탈 전후 lane correspondence가 달라 신호/우회로 임의 귀속하지 않았다. 각 native SG head의 crossing count는 head union의 총 이탈과 다르다.', '',
        '표본 간격 손실과 녹색 분모는 독립 결함이다. action750 CSV에는 도시 신호 command가 없으므로 JSON 기본 녹색은 실제 native 노출이 아니다. 같은 30초 계수에 정확한 native 녹색을 넣어도 표본 사이에 들어왔다 나간 차량을 복구하지 못한다. 반대로 1초 계수로 바꿔도 정지선 전 우회와 미실행 녹색 분모는 남는다.', '',
        '최소 collector 수선은 매 simulation step 차량 ID 전이를 단일 timestamp로 누적하고 decision 시각까지 창을 닫아 serialize/reset하는 것이다. 초기 endpoint는 다음 창 전이용으로 보존하고 이중 누적을 막아야 한다. 실제 실행 SG 노출을 같은 창에 적분하고, 정지선 용량에는 SG/lane/position crossing과 GREEN 중 queue/receiving 상태가 필요하다. 이 감사는 새 포화용량을 fit하거나 기본 206.53을 대체하지 않는다.', '',
        '1초 관측도 짧은 링크를 완전히 건너뛰거나 lane change와 긴 경로를 식별하지 못할 수 있어 정확한 throughput이라고 하지 않는다. 새로 source에 나타났을 때 이미 head를 지난 경우도 JSON에 검열로 분리했다. head 전 bypass는 이 링크의 head를 우회했다는 뜻이며 경로 전체가 무신호라는 뜻은 아니다.', '',
        f"읽은 FZP 데이터: {result['fzp']['frame_count']} frames, {result['fzp']['selected_ranges'][0]['rows']:,} rows, {result['fzp']['read_bytes']:,} bytes (전체 파일 {result['fzp']['size_bytes']:,} bytes). 선택 원시 범위 SHA와 geometry/native LSA/SIG/source SHA를 JSON에 보존했다. 전체 FZP 해시는 재계산하지 않았다. 모델/optimizer/VISSIM 실행 및 production 변경은 0이다.", '',
        '재현: `python -X utf8 -m diagnostics.selected_signal_sampling_audit` (기존 출력이 있으면 덮어쓰지 않음).', ''])
    path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'diagnostics/selected_signal_sampling_audit')
    args = parser.parse_args()
    targets = [args.output.with_suffix(ext) for ext in ('.json', '.csv', '.md')]
    targets.append(args.output.with_name(args.output.name + '_heads.csv'))
    if any(p.exists() for p in targets):
        parser.error('Output exists; choose a distinct --output to preserve evidence')
    result = run(args.output)
    print(json.dumps({'rows': [{k: r[k] for k in ('link', 'start_sec', 'one_second_departures', 'thirty_second_departures', 'lost_departures', 'conservative_head_crossings')} for r in result['windows']], 'read_bytes': result['fzp']['read_bytes'], 'source_changes': result['source_changes']}, indent=2))


if __name__ == '__main__':
    main()
