"""One bounded 1s interval: actual head crossings, branch IDs, COM readback."""
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.audit_movement_signal_authority import native_geometry


def main():
    started = time.monotonic()
    evidence_path = ROOT / 'diagnostics/physical_phase_authority_ver2.json'
    proof = json.loads(evidence_path.read_text(encoding='utf-8'))
    network = ROOT / proof['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == proof['network']['sha256']
    links, _, _ = native_geometry(ET.parse(network).getroot())
    run = ROOT / 'evaluation/runs/codex_signal_zero_s13_20260910'
    readback_path = run / 'decisions_codex_signal_zero_s13_20260910/signal_readback.csv'
    relevant = {(p['expected_spec']['signal'][2:], h['SG']) for p in proof['by_movement'].values() for h in p['source_heads']}
    readback, held, rb_digest = [], {}, hashlib.sha256()
    with readback_path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            sec = float(row['sim_sec'])
            if sec > 1050: break
            if 900 <= sec <= 1050 and (row['sc_no'], row['sg_no']) in relevant:
                assert row['ok'] == '1' and row['readback_state'] == row['requested_state']
                key = (row['sc_no'], row['sg_no'])
                if row['stage'] == 'immediate':
                    held[key] = (sec, row['readback_state'])
                elif row['stage'] == 'post_step' and key in held:
                    begin, aspect = held[key]
                    assert aspect == row['readback_state'], 'COM state did not persist over chunk'
                    readback.append({'begin_sec': begin, 'end_sec': sec, 'sc_sg': key, 'aspect': aspect})
                rb_digest.update(json.dumps(row, sort_keys=True).encode())
    sources = {p['path'][0] for p in proof['by_movement'].values()}
    exits = {key: row for key, row in links.items() if row.get('source') in sources}
    selected = sources | exits.keys()
    fzp = next((run / 'vissim_eval').glob('*.fzp'))
    reader = IndexedFzp(fzp, max_bytes=64 * 1024 * 1024)
    reader.seek_time(899)
    frames, digest, first_byte, last_byte, row_count = {}, hashlib.sha256(), None, None, 0
    while line := reader.line():
        fields = line.rstrip(b'\r\n').split(b';')
        second = float(fields[0])
        if second < 899: continue
        if second > 1050: break
        assert time.monotonic() - started < 45, 'bounded elapsed time exceeded'
        if first_byte is None: first_byte = reader.handle.tell() - len(line)
        last_byte = reader.handle.tell()
        digest.update(line); row_count += 1
        frame = frames.setdefault(int(second), {})
        link = fields[reader.index['LANE\\LINK\\NO']].decode()
        if link in selected:
            frame[int(fields[reader.index['NO']])] = (link, int(fields[reader.index['LANE\\INDEX']]), float(fields[reader.index['POS']]))
    reader.handle.close()
    assert sorted(frames) == list(range(899, 1051)), 'requires complete 1s cadence'
    results = {}
    for name, p in proof['by_movement'].items():
        source, target_connector, _ = p['path']
        heads = {h['lane']: h for h in p['source_heads']}
        events, branch_entries, ambiguous = {}, {}, []
        for second in range(900, 1051):
            old, new = frames[second - 1], frames[second]
            for veh in old.keys() & new.keys():
                a, b = old[veh], new[veh]
                if a[0] != source: continue
                if b[0] in exits and exits[b[0]]['source'] == source:
                    branch_entries.setdefault(veh, {'connector': b[0], 'observed_interval': [second - 1, second]})
                head = heads.get(a[1])
                if head is None or a[2] >= head['pos_m']: continue
                distance = None
                if b[0] == source and b[2] >= head['pos_m']:
                    if a[1] != b[1]:
                        ambiguous.append({'id': veh, 'interval': [second - 1, second], 'reason': 'lane changed over head plane'})
                        continue
                    distance = b[2] - a[2]
                elif b[0] in exits and exits[b[0]]['source'] == source:
                    endpoint = exits[b[0]]
                    if not endpoint['source_lane'] <= a[1] < endpoint['source_lane'] + endpoint['lanes']:
                        ambiguous.append({'id': veh, 'interval': [second - 1, second], 'reason': 'branch entry source lane changed'})
                        continue
                    distance = endpoint['source_pos'] - a[2] + b[2]
                if distance is None or distance <= 0: continue
                crossing = second - 1 + (head['pos_m'] - a[2]) / distance
                if not 900 < crossing <= 1050: continue
                assert veh not in events, 'repeat head passage needs explicit occurrence identity'
                # RunContinuous chunks have immediate/start and post_step/end
                # readbacks; FZP remains 1s. Do not pretend COM was read each second.
                bracket = [r for r in readback if r['sc_sg'] == (p['expected_spec']['signal'][2:], head['SG'])
                           and r['begin_sec'] < crossing <= r['end_sec']]
                assert len(bracket) == 1, 'crossing lacks a unique actual COM bracket'
                aspect = bracket[0]['aspect']
                events[veh] = {'id': veh, 'head': head['head'], 'source_lane': a[1], 'crossing_sec_interpolated': crossing,
                               'sample_interval': [second - 1, second], 'held_COM_aspect': aspect,
                               'actual_COM_bracket_sec': [bracket[0]['begin_sec'], bracket[0]['end_sec']],
                               'from_sample_link_lane_pos': a, 'to_sample_link_lane_pos': b}
        matched, other, unknown = [], [], []
        for veh, event in events.items():
            branch = branch_entries.get(veh)
            if branch and branch['observed_interval'][1] >= event['crossing_sec_interpolated']:
                (matched if branch['connector'] == target_connector else other).append(dict(event, branch=branch))
            else:
                unknown.append(event)
        results[name] = {'matched_target_branch': matched, 'other_observed_branch_count': len(other),
                         'outcome_unresolved_by_1050': unknown, 'ambiguous_lane_events': ambiguous,
                         'target_head_crossing_aspects': dict(Counter(e['held_COM_aspect'] for e in matched)),
                         'target_connector_entries_without_matched_head': len([v for v, b in branch_entries.items() if b['connector'] == target_connector and v not in events])}
    output = {'run': run.name, 'window': '(900,1050]', 'source_evidence_sha256': hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
              'fzp': str(fzp.relative_to(ROOT)), 'cadence_sec': 1, 'frames': len(frames), 'raw_rows': row_count,
              'bytes_read': reader.bytes_read, 'raw_range_bytes': [first_byte, last_byte], 'raw_range_sha256': digest.hexdigest(),
              'verified_COM_bracket_count': len(readback), 'selected_readback_rows_sha256': rb_digest.hexdigest(),
              'elapsed_sec': time.monotonic() - started, 'movements': results,
              'limitations': ['Head-plane time linearly interpolates recorded POS across 1s; it is not an exact simulator crossing event.',
                             'COM is read at RunContinuous chunk boundaries, not each 1s FZP sample; each crossing cites matching immediate/start and post_step/end readings.',
                             'Only same-lane source crossing or compatible source-to-connector transition is accepted; lane-change and unobserved outcomes remain separate.',
                             'A branch entry without a matched in-window head passage may have crossed earlier; never counted as a red violation or ungated movement.',
                             'A matched POS-plane crossing during AMBER/RED is retained as observed, without inferring a simulator violation or changing the phase/capacity model.',
                             'Signal-zero uses the frozen first n7 synthetic green plan, not native NC; this checks selected SG service identity, not capacity or performance.']}
    path = ROOT / 'diagnostics/physical_phase_authority_passages.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'bytes': reader.bytes_read, 'elapsed': output['elapsed_sec'], 'summary': {m: {'matched': len(v['matched_target_branch']), 'aspects': v['target_head_crossing_aspects'], 'unresolved': len(v['outcome_unresolved_by_1050'])} for m, v in results.items()}}))


if __name__ == '__main__': main()
