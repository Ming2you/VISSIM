"""Post-run only: bounded 900..1050 native meter-response comparison.

No COM, model calls, or full FZP scan. Execute only after both owned runs finish.
This establishes observed execution/traffic response, never target-flow attainment.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
from itertools import zip_longest
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.validate_native_signal_record import read_ldp_frames

SPEC = importlib.util.spec_from_file_location('meter_windows', Path(__file__).with_name('audit_meter_branch_windows.py'))
WINDOWS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WINDOWS)
START, END = 900, 1050
TARGETS = (10646, 10644)
D = ROOT / 'diagnostics/control_improvement/decision_common_anchor_20260911'
GEOMETRY = D / 'native_meter_fw9_local_v1/local_ramp_audit.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def pinned_geometry(network, mapping, reference):
    doc = ET.parse(network).getroot()
    links = {int(x.get('no')): x for x in doc.findall('./links/link')}
    out = {}
    for meter in mapping['ramp_meters']:
        link = int(meter['connector'])
        node = links[link]
        ends = {tag: dict(node.find(tag).attrib) for tag in ('fromLinkEndPt', 'toLinkEndPt')}
        if (int(ends['fromLinkEndPt']['lane'].split()[0]) != meter['from_link']
                or int(ends['toLinkEndPt']['lane'].split()[0]) != meter['to_link']):
            raise ValueError(f'Mapping/actual network endpoint mismatch: {link}')
        heads = [dict(h.attrib) for h in doc.iter('signalHead')
                 if int(h.get('lane').split()[0]) == link]
        expected_sg = f"{meter['sc_no']} {meter['sg_no']}"
        if (len(heads) != len(node.findall('./lanes/lane'))
                or any(h['sg'] != expected_sg or h['allVehTypes'] != 'true'
                       or float(h['complRate']) != 1 for h in heads)):
            raise ValueError(f'Incomplete/mixed meter heads: {link}')
        by_lane = {int(h['lane'].split()[1]): float(h['pos']) for h in heads}
        if len(by_lane) != len(heads):
            raise ValueError(f'Duplicate lane-specific head: {link}')
        if str(link) in reference:
            prior = reference[str(link)]
            if (heads != [prior['signal_head']] or ends['fromLinkEndPt'] != prior['from']
                    or ends['toLinkEndPt'] != prior['to']):
                raise ValueError(f'Prior local audit geometry changed: {link}')
        out[link] = {'sc_no': meter['sc_no'], 'sg_no': meter['sg_no'],
                     'group': meter['model_ramp_key'], 'meter': meter['id'],
                     'from_link': meter['from_link'], 'to_link': meter['to_link'],
                     'heads_by_lane': by_lane, 'signal_heads': heads, 'endpoints': ends}
    if len(out) != 8:
        raise ValueError('Require all eight physical meters')
    return out


def load_run(name):
    run = ROOT / 'evaluation/runs' / name
    receipt_path = run / 'completion_receipt.json'
    receipt = read_json(receipt_path)
    if (receipt.get('completed') is not True or receipt.get('owned_native_alive') is not False
            or receipt.get('exit_code') != 0 or receipt.get('terminal_sec') != END):
        raise ValueError(f'Require completed, closed, successful {END}s run: {name}')
    provenance_path = run / f'run_provenance_{name}.json'
    provenance = read_json(provenance_path)
    if (sha(provenance_path) != receipt['provenance_sha256']
            or provenance['run_id'] != receipt['run_id'] or provenance['name'] != name
            or provenance['sim_period_sec'] != END or provenance['control_interval_sec'] != 150):
        raise ValueError(f'Run provenance/completion mismatch: {name}')
    pinned = {}
    for key in ('network', 'control_mapping', 'demand_profile'):
        item = provenance['files'][key]
        path = Path(item['path'])
        if not path.is_absolute():
            path = ROOT / path
        if sha(path) != item['sha256']:
            raise ValueError(f'Pinned {key} changed: {name}')
        pinned[key] = path
    native = []
    for item in receipt['native_files']:
        path = Path(item['path'])
        if not path.resolve().is_relative_to(run.resolve()) or path.stat().st_size != item['bytes']:
            raise ValueError(f'Native output path/size mismatch: {path}')
        native.append(path)
    fzps = [p for p in native if p.suffix.lower() == '.fzp']
    if len(fzps) != 1:
        raise ValueError('Require one completed native FZP')
    meters = pinned_geometry(pinned['network'], read_json(pinned['control_mapping']),
                             read_json(GEOMETRY)['geometry'])
    ldp_paths = {}
    for sc in range(9101, 9109):
        paths = [p for p in native if p.name.endswith(f'_{sc}_001.ldp')]
        if len(paths) != 1:
            raise ValueError(f'Missing/duplicate native LDP for {sc}')
        ldp_paths[sc] = paths[0]
    ldp = read_ldp_frames(ldp_paths, {sc: [1] for sc in ldp_paths}, START - 1, END)
    small = [receipt_path, provenance_path, GEOMETRY, *pinned.values(), *ldp_paths.values()]
    return {'name': name, 'directory': run, 'provenance': provenance, 'fzp': fzps[0],
            'meters': meters, 'ldp': ldp, 'pins': {str(p): sha(p) for p in small}}


def execution_records(run):
    directory = run['directory'] / f"decisions_{run['name']}"
    commands_path = directory / f'action_{START:06d}.csv'
    readback_path = directory / 'signal_readback.csv'
    with commands_path.open(encoding='utf-8-sig', newline='') as stream:
        commands = [r for r in csv.DictReader(stream) if r['kind'] == 'ramp_meter']
    if len(commands) != 8 or {int(r['sc_no']) for r in commands} != set(range(9101, 9109)):
        raise ValueError('Incomplete physical meter command table')
    retained, last, count = [], {}, 0
    with readback_path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if not (9101 <= int(row['sc_no']) <= 9108 and START <= float(row['sim_sec']) <= END):
                continue
            count += 1
            if row['ok'] != '1' or row['requested_state'] != row['readback_state']:
                raise ValueError(f'Meter readback failure: {row}')
            key = row['sc_no'], row['sg_no'], row['stage']
            state = row['requested_state'], row['readback_state']
            if last.get(key) != state or float(row['sim_sec']) in (START, END):
                retained.append(row)
            last[key] = state
    if {int(k[0]) for k in last} != set(range(9101, 9109)):
        raise ValueError('Missing meter application/check records')
    state_path = directory / f'state_{END:06d}.json'
    raw = read_json(state_path)
    raw = raw.get('raw', raw)
    window = raw.get('local_observation', {}).get('signal_observation_window', {})
    heads = [h for h in window.get('heads', []) if 9101 <= int(h.get('sc', 0)) <= 9108]
    if heads and (window.get('start_sec') != START or window.get('end_sec') != END
                  or window.get('clock_complete') is not True):
        raise ValueError('Saved meter head window incomplete/misaligned')
    for path in (commands_path, readback_path, state_path):
        run['pins'][str(path)] = sha(path)
    return {'command_at_sec': START, 'meter_commands': commands,
            'readback_window_rows': count, 'readback_first_and_state_changes_by_stage': retained,
            'clock_convention': 'Commands/immediate readback at t apply before advancing beyond t; native LDP(t) precedes a new write at t. Preserve pre-step writes separately.',
            'saved_meter_head_observations': heads,
            'saved_meter_head_observation_status': 'available' if heads else 'meter heads absent; no COM reconstruction'}


def green_windows(ldp, key, *, start=START, end=END):
    opportunities, lookup = [], {}
    for sec in range(start, end + 1):
        if ldp[sec][key] != 'GREEN':
            continue
        if not opportunities or opportunities[-1]['last_native_green_frame_sec'] != sec - 1:
            opportunities.append({'first_native_green_frame_sec': sec,
                'last_native_green_frame_sec': sec, 'left_censored': sec == start,
                'right_censored': False, 'left_frame_green_crossings': 0,
                'stable_green_crossings': 0, 'boundary_left_green_crossings': 0,
                'boundary_right_green_crossings': 0, 'examples': []})
        opportunities[-1]['last_native_green_frame_sec'] = sec
        opportunities[-1]['right_censored'] = sec == end
        lookup[sec] = opportunities[-1]
    return opportunities, lookup


def collect(run, *, max_bytes=80 * 1024 * 1024):
    meters, ldp = run['meters'], run['ldp']['frames']
    opportunities, lookup = {}, {}
    for link, meta in meters.items():
        opportunities[link], lookup[link] = green_windows(ldp, f"{meta['sc_no']}:{meta['sg_no']}", start=START, end=END)
    bins, examples = {k: Counter() for k in meters}, {k: [] for k in meters}
    opening, previous = {}, None
    reader = IndexedFzp(run['fzp'], max_bytes=max_bytes)
    stat = run['fzp'].stat()

    def crossing(link, sec, veh, before, after, method):
        meta, b = meters[link], bins[link]
        key = f"{meta['sc_no']}:{meta['sg_no']}"
        left, right = ldp[sec - 1][key], ldp[sec][key]
        b['head_crossings'] += 1
        b[method] += 1
        classification = 'stable_green' if left == right == 'GREEN' else 'state_boundary' if left != right else 'stable_non_green'
        b[f'crossing_{classification}'] += 1
        event = {'vehicle': veh, 'observed_interval_sec': [sec - 1, sec],
                 'before_link_lane_pos_speed': before, 'after_link_lane_pos_speed': after,
                 'left_ldp_frame_sec': sec - 1, 'left_ldp_state': left,
                 'right_ldp_frame_sec': sec, 'right_ldp_state': right,
                 'classification': classification, 'method': method}
        if len(examples[link]) < 4:
            examples[link].append(event)
        if left == 'GREEN':
            op = lookup[link][sec - 1]
            op['left_frame_green_crossings'] += 1
            op['stable_green_crossings' if right == 'GREEN' else 'boundary_left_green_crossings'] += 1
            if len(op['examples']) < 2:
                op['examples'].append(event)
        if right == 'GREEN' and left != 'GREEN':
            lookup[link][sec]['boundary_right_green_crossings'] += 1
            if len(lookup[link][sec]['examples']) < 2:
                lookup[link][sec]['examples'].append(event)

    try:
        for sec, current in WINDOWS.frames(reader, START, END):
            present = {k: {} for k in meters}
            for veh, row in current.items():
                if row[0] in present:
                    present[row[0]][veh] = row
            if previous is None:
                if sec != START:
                    raise ValueError('Missing opening FZP frame')
                opening = {k: len(v) for k, v in present.items()}
                for link, rows in present.items():
                    bins[link]['initial_stopped_lt5'] = sum(r[3] < 5 for r in rows.values())
                    bins[link]['max_inventory'] = len(rows)
                    bins[link]['max_stopped_lt5'] = bins[link]['initial_stopped_lt5']
                previous = current
                continue
            for link, meta in meters.items():
                b, now = bins[link], present[link]
                old = {v: r for v, r in previous.items() if r[0] == link}
                stops = sum(r[3] < 5 for r in now.values())
                b.update(vehicle_seconds=len(now), stopped_vehicle_seconds_lt5=stops,
                         stopped_vehicle_seconds_lt1=sum(r[3] < 1 for r in now.values()))
                b['max_inventory'] = max(b['max_inventory'], len(now))
                b['max_stopped_lt5'] = max(b['max_stopped_lt5'], stops)
                b['end_n'], b['end_stopped_lt5'] = len(now), stops
                for veh, row in now.items():
                    if row[1] not in meta['heads_by_lane']:
                        raise ValueError(f'Unmapped ramp lane: {link}/{row[1]}')
                    if veh not in old:
                        b['entry'] += 1
                        source = previous.get(veh)
                        b['entry_from_expected_link' if source and source[0] == meta['from_link'] else 'entry_other_or_previously_absent'] += 1
                        if row[2] >= meta['heads_by_lane'][row[1]]:
                            b['entry_first_seen_beyond_head_not_counted_as_head_crossing'] += 1
                    else:
                        before = old[veh]
                        b['lane_changes'] += before[1] != row[1]
                        if before[2] < meta['heads_by_lane'][before[1]] and row[2] >= meta['heads_by_lane'][row[1]]:
                            crossing(link, sec, veh, before, row, 'head_within_connector')
                for veh, row in old.items():
                    if veh in now:
                        continue
                    target = current.get(veh)
                    if target is None:
                        b['absent'] += 1
                    elif target[0] == meta['to_link']:
                        b['exit_expected_freeway'] += 1
                        if row[2] < meta['heads_by_lane'][row[1]]:
                            crossing(link, sec, veh, row, target, 'head_on_expected_freeway_exit')
                    else:
                        b['exit_other_link'] += 1
            previous = current
    finally:
        reader.handle.close()
    after = run['fzp'].stat()
    if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('FZP changed during analysis')
    rows = []
    execution = execution_records(run)
    for link, b in bins.items():
        row = {'connector': link, 'initial_n': opening[link], **dict(b)}
        row['closure'] = opening[link] + b['entry'] - b['exit_expected_freeway'] - b['exit_other_link'] - b['absent'] - b['end_n']
        if row['closure']:
            raise ValueError('Connector inventory balance failure')
        row['mean_stopped_lt5'] = b['stopped_vehicle_seconds_lt5'] / (END - START)
        observed = [h for h in execution['saved_meter_head_observations'] if int(h['link']) == link]
        if observed:
            row['saved_head_crossings'] = sum(float(h['crossings']) for h in observed)
            row['fzp_minus_saved_head_crossings'] = b['head_crossings'] - row['saved_head_crossings']
        rows.append(row)
    return {'name': run['name'], 'seed': run['provenance']['seed'],
            'ramp_meter_timing': run['provenance'].get('ramp_meter_timing'),
            'rows': rows, 'execution_records': execution,
            'target_green_opportunities': {k: opportunities[k] for k in TARGETS},
            'limited_crossing_examples': examples, 'geometry': meters,
            'ldp': {k: v for k, v in run['ldp'].items() if k != 'frames'},
            'fzp': {'path': str(run['fzp']), 'bytes': stat.st_size, 'full_scan': False,
                    'selected': reader.selected, 'bytes_read': reader.bytes_read}}


def first_raw_difference(left, right, *, max_bytes=80 * 1024 * 1024):
    """Compare all native data columns in this window, including POSLAT/delay."""
    readers = [IndexedFzp(r['fzp'], max_bytes=max_bytes) for r in (left, right)]
    stats = [(r['fzp'].stat().st_size, r['fzp'].stat().st_mtime_ns) for r in (left, right)]

    def data(reader):
        reader.seek_time(START)
        while raw := reader.line():
            fields = raw.rstrip(b'\r\n').split(b';')
            sec = float(fields[0])
            if sec < START:
                continue
            if sec > END:
                break
            yield raw, fields
    result = {'window_sec': [START, END], 'all_raw_data_rows_equal': True,
              'equal_rows_before_difference': 0, 'first_difference': None}
    try:
        if readers[0].names != readers[1].names:
            raise ValueError('FZP columns differ')
        for a, b in zip_longest(data(readers[0]), data(readers[1])):
            if a is not None and b is not None and a[0] == b[0]:
                result['equal_rows_before_difference'] += 1
                continue
            result['all_raw_data_rows_equal'] = False
            result['first_difference'] = {'baseline_raw': a[0].decode('ascii').rstrip() if a else None,
                'candidate_raw': b[0].decode('ascii').rstrip() if b else None,
                'different_columns': [name for name, av, bv in zip(readers[0].names, a[1], b[1]) if av != bv] if a and b else ['missing_row'],
                'note': f'First ordered data-row mismatch in {START}..{END}; no claim outside that comparison window.'}
            break
    finally:
        for reader in readers:
            reader.handle.close()
    for run, before in zip((left, right), stats):
        current = run['fzp'].stat()
        if before != (current.st_size, current.st_mtime_ns):
            raise ValueError('FZP changed during row comparison')
    result['bytes_read_by_run'] = [r.bytes_read for r in readers]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default='codex_native_clock_fw080_u050_open_v2')
    parser.add_argument('--run', default='codex_native_clock_fw080_u050_fw8_rg_v1')
    parser.add_argument('--output', type=Path, default=D / 'native_meter_fw8_rg_local_v1')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output folder; preserve existing results')
    tick = time.perf_counter()
    sources = [Path(__file__), Path(WINDOWS.__file__), ROOT / 'diagnostics/probe_e8_lane_receiving.py',
               ROOT / 'diagnostics/validate_native_signal_record.py']
    source_pins = {str(p): sha(p) for p in sources}
    # Both completion guards run before any native trajectory is read.
    baseline, candidate = load_run(args.baseline), load_run(args.run)
    if baseline['meters'] != candidate['meters']:
        raise ValueError('Actual ramp geometry differs between runs')
    if (baseline['provenance']['seed'] != candidate['provenance']['seed']
            or baseline['provenance']['files']['network']['sha256'] != candidate['provenance']['files']['network']['sha256']
            or baseline['provenance']['files']['demand_profile']['sha256'] != candidate['provenance']['files']['demand_profile']['sha256']):
        raise ValueError('Paired seed/network/demand pins differ; investigate before response comparison')
    outputs = [collect(run) for run in (baseline, candidate)]
    for index, output in enumerate(outputs):
        for command in output['execution_records']['meter_commands']:
            expected_green = 8 if index == 1 and int(command['sc_no']) in (9103, 9104) else 10
            if float(command['green_sec']) != expected_green:
                raise ValueError(f'Unexpected fixed-command contrast: {command}')
    if candidate['provenance'].get('ramp_meter_timing', {}).get('amber_sec') != 0:
        raise ValueError('Candidate does not declare the intended zero-amber timing')
    difference = first_raw_difference(baseline, candidate)
    pins = {**source_pins, **baseline['pins'], **candidate['pins']}
    if any(sha(path) != digest for path, digest in pins.items()):
        raise ValueError('Pinned input/source changed during analysis')
    report = {'schema': 'post-run-fw8-rg-meter-response/v1', 'window_sec': [START, END],
        'analysis_completed': True, 'target_flow_attainment_verified': False,
        'native_execution_validation_replaced': False, 'source_pins': pins, 'runs': outputs,
        'first_raw_fzp_difference': difference, 'wall_sec': time.perf_counter() - tick,
        'definitions': {
            'events': 'Observed one-second transitions (900,1050]; initial/end inventory are stocks.',
            'arrivals': 'Connector entries are observed arrivals, not intended OD demand or all upstream ramp-destined vehicles.',
            'head_crossing': 'Below-to-above lane-specific head, or below-head connector to mapped freeway. Unseen traversal/first appearance beyond head is not inferred.',
            'native_green_opportunity': 'Contiguous GREEN LDP samples; sample endpoints are not inferred exact subsecond switching times.',
            'attribution': 'Left LDP frame attribution retained. Stable GREEN requires both bounding LDP states GREEN. State-change intervals remain boundary/uncertain; immediate command writes at the left frame may follow its native sample.',
            'no_quantity_guarantee': 'Counts are response evidence, not commanded-rate attainment or exactly one car per green.',
            'absence': 'Missing vehicle is separate, not a freeway exit, TTD, or proven deletion.',
            'scope': 'Connector inventory only. Upstream other destinations are excluded; no Omega TTT/TTD claim or full-run/warmup equivalence claim.'}}
    args.output.mkdir(parents=True)
    (args.output / 'meter_response.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lines = ['# 900–1050초 8개 램프의 관측 반응', '',
        '1초 FZP와 실제 native LDP를 사용했다. 신호 전환 경계는 확정적인 녹색 통과에 합치지 않았다. 이 결과는 목표 유량 달성 또는 전체 native 실행 검증을 대신하지 않는다.', '',
        '| 조건 | connector | 진입 / 정지선 / 본선 방출 | 재고 처음→끝 | 평균 정지(<5km/h) | 소멸 관측 | 수지 오차 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for output in outputs:
        for row in output['rows']:
            lines.append(f"| {output['name']} | {row['connector']} | {row.get('entry',0)} / {row.get('head_crossings',0)} / {row.get('exit_expected_freeway',0)} | {row['initial_n']}→{row['end_n']} | {row['mean_stopped_lt5']:.2f} | {row.get('absent',0)} | {row['closure']} |")
    lines += ['', '| 조건 | connector | native GREEN 관측 프레임 | 양쪽 GREEN 통과 | 경계: 좌측 GREEN / 우측 GREEN |',
              '|---|---:|---|---:|---:|']
    for output in outputs:
        for link, opportunities in output['target_green_opportunities'].items():
            for op in opportunities:
                lines.append(f"| {output['name']} | {link} | {op['first_native_green_frame_sec']}–{op['last_native_green_frame_sec']} | {op['stable_green_crossings']} | {op['boundary_left_green_crossings']} / {op['boundary_right_green_crossings']} |")
    lines += ['', '녹색 연속 관측 중 2대 이상 통과하면 한 대 제한이 아님을 직접 보여준다. 0–1대만 관측되어도 한 대 제한 또는 목표 유량 달성의 증거가 되지 않는다.', '',
              '첫 FZP 행 차이: `' + json.dumps(difference['first_difference'], ensure_ascii=False) + '`', '',
              '원시 신호 양쪽 상태, 실제 명령/즉시 readback, 선택 프레임 SHA, 소수의 차량 사건은 JSON에 보존했다. 900초 이전 전체 궤적 동일성은 별도 검증 대상이다.']
    (args.output / 'meter_response.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'analysis_completed': True, 'output': str(args.output), 'wall_sec': report['wall_sec']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
