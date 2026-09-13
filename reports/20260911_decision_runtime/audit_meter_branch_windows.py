"""Read three bounded windows of the completed selected NC run, never run COM.

Reuses the existing binary-seek FZP reader. Counts observed link transitions
and lane-specific signal-head passages; these are not intended OD demand.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp

OUT = Path(__file__).resolve().parent
RESULT = ROOT / 'diagnostics/demand_sweep/fw080_urban050_cooldown9000/results'
WINDOWS = ((1650, 1800, 'formation'), (3750, 3900, 'peak'), (6600, 6750, 'recovery'))


def frames(reader, start, end):
    reader.seek_time(start)
    second, values, digest = None, {}, hashlib.sha256()
    first, final, rows = None, None, 0
    while raw := reader.line():
        fields = raw.rstrip(b'\r\n').split(b';')
        t = float(fields[0])
        if t < start:
            continue
        if t > end:
            break
        if int(t) != t:
            raise ValueError('Require native one-second observations')
        t = int(t)
        if second is not None and t != second:
            if t != second + 1:
                raise ValueError('Incomplete FZP window')
            yield second, values
            values = {}
        second = t
        idx = reader.index
        veh = int(fields[idx['NO']])
        if veh in values:
            raise ValueError('Duplicate vehicle in FZP frame')
        values[veh] = (int(fields[idx['LANE\\LINK\\NO']]), int(fields[idx['LANE\\INDEX']]),
                       float(fields[idx['POS']]), float(fields[idx['SPEED']]))
        digest.update(raw)
        rows += 1
        if first is None:
            first = reader.handle.tell() - len(raw)
        final = reader.handle.tell()
    if second != end:
        raise ValueError('Incomplete terminal frame')
    yield second, values
    reader.selected[f'{start}:{end}'] = {'rows': rows, 'first_byte': first,
        'last_byte_exclusive': final, 'raw_rows_sha256': digest.hexdigest()}


def main():
    tick = time.perf_counter()
    targets = [OUT / 'METER_BRANCH_WINDOWS.json', OUT / 'METER_BRANCH_WINDOWS.md']
    if any(p.exists() for p in targets):
        raise FileExistsError('Preserve prior results; use a fresh version')
    summary_path = RESULT / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    path = Path(summary['fzp']['path'])
    network = Path(summary['network'])
    mapping_path = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    small = [Path(__file__), summary_path, mapping_path, network, RESULT / 'fw_cells_30s.csv']
    pin = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p.relative_to(ROOT)): pin(p) for p in small}
    doc = ET.parse(network).getroot()
    links = {int(x.get('no')): x for x in doc.findall('./links/link')}
    meters = {}
    for meter in mapping['ramp_meters']:
        link = int(meter['connector'])
        node = links[link]
        endpoints = {tag: int(node.find(tag).get('lane').split()[0])
                     for tag in ('fromLinkEndPt', 'toLinkEndPt')}
        if endpoints != {'fromLinkEndPt': meter['from_link'], 'toLinkEndPt': meter['to_link']}:
            raise ValueError('Meter mapping differs from pinned geometry')
        heads = {int(h.get('lane').split()[1]): float(h.get('pos'))
                 for h in doc.iter('signalHead') if int(h.get('lane').split()[0]) == link
                 and h.get('sg') == f"{meter['sc_no']} {meter['sg_no']}"}
        if len(heads) != len(node.findall('./lanes/lane')):
            raise ValueError('Missing lane-specific signal-head position')
        meters[link] = {'group': meter['model_ramp_key'], 'meter': meter['id'],
            'from_link': meter['from_link'], 'to_link': meter['to_link'], 'heads_by_lane': heads}
    if len(meters) != 8 or path.stat().st_size != summary['fzp']['bytes']:
        raise ValueError('Require eight meters and unchanged completed FZP size')
    stat_before = path.stat()
    reader = IndexedFzp(path, max_bytes=160 * 1024 * 1024)
    output = []
    try:
        for start, end, label in WINDOWS:
            bins = {k: Counter() for k in meters}
            opening = {}
            previous = None
            for sec, current in frames(reader, start, end):
                present = {k: {v: r for v, r in current.items() if r[0] == k} for k in meters}
                if previous is None:
                    if sec != start:
                        raise ValueError('Missing start frame')
                    opening = {k: len(rows) for k, rows in present.items()}
                    previous = current
                    continue
                for link, meta in meters.items():
                    b, now = bins[link], present[link]
                    old = {v: r for v, r in previous.items() if r[0] == link}
                    b['vehicle_seconds'] += len(now)
                    b['stopped_vehicle_seconds_lt5'] += sum(r[3] < 5 for r in now.values())
                    b['stopped_vehicle_seconds_lt1'] += sum(r[3] < 1 for r in now.values())
                    b['max_inventory'] = max(b['max_inventory'], len(now))
                    b['max_stopped_lt5'] = max(b['max_stopped_lt5'], sum(r[3] < 5 for r in now.values()))
                    b['end_n'] = len(now)
                    b['end_stopped_lt5'] = sum(r[3] < 5 for r in now.values())
                    for v, row in now.items():
                        if row[1] not in meta['heads_by_lane']:
                            raise ValueError('Unmapped meter lane')
                        if v not in old:
                            b['entry'] += 1
                            source = previous.get(v)
                            b['entry_from_expected_link' if source and source[0] == meta['from_link']
                              else 'entry_other_or_previously_absent'] += 1
                        else:
                            before = old[v]
                            b['lane_changes'] += before[1] != row[1]
                            if (before[2] < meta['heads_by_lane'][before[1]]
                                    and row[2] >= meta['heads_by_lane'][row[1]]):
                                b['head_crossing_observed_within_connector'] += 1
                    for v, row in old.items():
                        if v in now:
                            continue
                        target = current.get(v)
                        if target is None:
                            b['absent'] += 1
                        elif target[0] == meta['to_link']:
                            b['exit_expected_freeway'] += 1
                            if row[2] < meta['heads_by_lane'][row[1]]:
                                b['head_crossing_observed_on_exit'] += 1
                        else:
                            b['exit_other_link'] += 1
                previous = current
            for link, b in bins.items():
                row = {'window': label, 'start_sec': start, 'end_sec': end, 'connector': link,
                    'group': meters[link]['group'], 'initial_n': opening[link], **dict(b)}
                row['closure'] = opening[link] + b['entry'] - b['exit_expected_freeway'] - b['exit_other_link'] - b['absent'] - b['end_n']
                if row['closure']:
                    raise ValueError('Connector vehicle-count closure failed')
                row['observed_arrival_rate_veh_h'] = b['entry'] * 3600 / (end-start)
                row['mean_stopped_lt5_veh'] = b['stopped_vehicle_seconds_lt5'] / (end-start)
                output.append(row)
    finally:
        reader.handle.close()
    stat_after = path.stat()
    if (stat_before.st_size, stat_before.st_mtime_ns) != (stat_after.st_size, stat_after.st_mtime_ns):
        raise ValueError('FZP changed during bounded read')
    if any(pin(ROOT / k) != v for k, v in pins.items()):
        raise ValueError('Small source changed during audit')
    report = {'schema': 'bounded-selected-meter-branch-windows/v1', 'run': summary['run'],
        'seed': summary['seed'], 'network_sha256': pins[str(network.relative_to(ROOT))],
        'window_selection': 'Cached E 30s cells: first speed<30 with n>=5 at1800; maximum stopped397 at3870; last slow cell6720. Aligned150s windows ending1800/3900/6750.',
        'definitions': {'events': '(start,end] observed one-second transitions; initial/end stock excluded from event counts',
            'arrival': 'Observed entry to the connector, not intended origin/destination demand or all upstream queues',
            'stop': 'SPEED<5km/h and separately<1km/h; moving connector inventory is not stopped queue',
            'exit': 'Same ID observed on mapped receiving freeway; absent/other separately, never count as completed exit',
            'head': 'Observed lane-specific below-to-above position or mapped freeway exit from below head; short unobserved traversals are not inferred',
            'comparison': 'Completed fast NC9000 only. Not exact paired baseline for the canonical1050 native tests; no controller or model ranking claim'},
        'source_pins': pins, 'fzp': {'path': str(path), 'bytes': stat_before.st_size,
            'previous_full_sha256': summary['fzp']['file_sha256'], 'full_sha_recomputed': False,
            'selected_windows': reader.selected, 'bytes_read': reader.bytes_read},
        'meters': meters, 'rows': output, 'wall_sec': time.perf_counter()-tick,
        'COM_calls': 0, 'model_calls': 0, 'full_scan': False}
    targets[0].write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 선정80–50 무제어의 램프별 세 구간 확인', '',
        '새 런 없이 기존9000초 FZP에서 형성1650–1800, 첨두3750–3900, 회복6600–6750초만 읽었다. 도착은 connector 진입 관측이며 원점별 희망 수요가 아니다. 정지는 속도5km/h 미만이다.', '',
        '| 구간 | connector | 도착/본선 방출 [대] | 재고 처음→끝 | 평균/최대 정지 [대] | 소멸 |',
        '|---|---:|---:|---:|---:|---:|']
    for r in output:
        lines.append(f"| {r['window']} | {r['connector']} | {r.get('entry',0)}/{r.get('exit_expected_freeway',0)} | {r['initial_n']}→{r['end_n']} | {r['mean_stopped_lt5_veh']:.2f}/{r.get('max_stopped_lt5',0)} | {r.get('absent',0)} |")
    lines += ['', '모든 관측 재고 수지는 닫혔다. 이 창 밖의 삭제·미삽입·상류 대기 문제까지 해소됐다는 뜻은 아니다. 본선 혼잡이 있어도 모든 진입램프가 과수요라는 결론은 나오지 않는다. 각 명령의 효과는 같은 정본 실행 조건의 짧은 대조 런으로 따로 검증해야 한다.', '',
        f"실제 읽기 {reader.bytes_read:,} bytes / 파일 {stat_before.st_size:,} bytes, 총 {report['wall_sec']:.3f}초. 원본의 기존 전체SHA는 기록만 참조했고 읽은 창은 별도SHA로 보존했다."]
    targets[1].write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'completed': True, 'rows': len(output), 'bytes_read': reader.bytes_read,
                      'wall_sec': report['wall_sec'], 'report': str(targets[1])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
