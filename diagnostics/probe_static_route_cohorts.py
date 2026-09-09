"""Bounded, matched-ID native routing cohorts; no model or VISSIM calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from diagnostics.probe_e8_lane_receiving import IndexedFzp
from diagnostics.probe_e8_window_passages import frames

RUN = 'codex_meter10639_g5_s13_20260910'
START, END, FOLLOW = 600., 750., 1200.
NETWORK = ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx'
GROUPS = {'OR_F_E': ('1130', 10682, 10643, 10639),
          'OR_D_E': ('1131', 10483, 10481, 10490),
          'OR_D_W': ('1132', 10479, 10491, 10480),
          'OR_F_W': ('1133', 10645, 10638, 10646)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def gate_event(old, new, link, position, t0, t1):
    """A gate crossing is proved only by observations on that same road link."""
    if old[0] != link or new[0] != link or not old[2] < position <= new[2]:
        return None
    return {'t0': t0, 't1': t1, 'estimated_sec': t0 + (t1-t0)*(position-old[2])/(new[2]-old[2]),
            'old_link': old[0], 'new_link': new[0], 'old_pos': old[2], 'new_pos': new[2],
            'lane_before': old[1], 'lane_after': new[1], 'gate_lane_ambiguous': old[1] != new[1]}


def connector_event(old, new, spec, t0, t1, entering):
    source, target = (spec['source_link'], spec['connector']) if entering else (spec['connector'], spec['target_link'])
    if (old[0], new[0]) != (source, target):
        return None
    before = spec['source_pos_m']-old[2] if entering else spec['length_m']-old[2]
    after = new[2] if entering else new[2]-spec['target_pos_m']
    valid = before >= -1e-6 and after >= -1e-6 and before+after > 0
    return {'t0': t0, 't1': t1, 'estimated_sec': t0+(t1-t0)*before/(before+after) if valid else None,
            'old_link': old[0], 'new_link': new[0], 'old_pos': old[2], 'new_pos': new[2],
            'method': 'linear_path_distance' if valid else 'observed_transition_interval_only'}


def in_cohort(event):
    return event is not None and event['estimated_sec'] is not None and START < event['estimated_sec'] <= END


def main():
    import math
    root = ET.parse(NETWORK).getroot()
    mapping_path = ROOT / 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    mapping = load(mapping_path)
    prior_path = ROOT / 'diagnostics/total_offramp_ratio_audit.json'
    priors = {r['group']: r['total_off_prior'] for r in load(prior_path)['table']}
    specs, cohort, bypass = {}, {}, {}
    counts, ambiguous_appearance = {}, {}
    for group, (decision, direct, signal, merge) in GROUPS.items():
        d = root.find(f'.//vehicleRoutingDecisionStatic[@no="{decision}"]')
        chain = mapping['freeway_model_links']['FW_'+group[-1]]
        offsets = dict(zip(map(int, chain['chain_links']), chain['chain_offsets_m']))
        connectors = {}
        for no in (direct, signal, merge):
            node = root.find(f'./links/link[@no="{no}"]')
            source, target = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
            points = [(float(p.get('x')), float(p.get('y')), float(p.get('zOffset', 0)))
                      for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
            connectors[no] = {'connector': no, 'source_link': int(source.get('lane').split()[0]),
                              'source_pos_m': float(source.get('pos')), 'target_link': int(target.get('lane').split()[0]),
                              'target_pos_m': float(target.get('pos')), 'length_m': sum(math.dist(a,b) for a,b in zip(points,points[1:]))}
        last = max((connectors[direct], connectors[signal]), key=lambda r: offsets[r['source_link']]+r['source_pos_m'])
        specs[group] = {'decision_id': decision, 'decision_link': int(d.get('link')), 'decision_pos_m': float(d.get('pos')),
                        'through_link': last['source_link'], 'through_pos_m': last['source_pos_m']+1.,
                        'through_definition': 'Mainline plane 1m downstream of the later of the two offconnector source positions',
                        'direct': connectors[direct], 'signal': connectors[signal], 'intermediate_merge': connectors[merge],
                        'native_conditional_prior': priors[group]}
        assert offsets[connectors[merge]['target_link']]+connectors[merge]['target_pos_m'] > offsets[int(d.get('link'))]+float(d.get('pos'))
        cohort[group], bypass[group] = {}, {}
        counts[group], ambiguous_appearance[group] = Counter(), []
    paths = list((ROOT/'evaluation/runs'/RUN/'vissim_eval').glob('*.fzp'))
    assert len(paths) == 1
    path = paths[0]
    stat = path.stat()
    native_evidence = ROOT/'diagnostics/native_trajectory_repeat_check.json'
    immutable = {str(p): sha(p) for p in (NETWORK, mapping_path, prior_path, native_evidence, Path(__file__))}
    reader = IndexedFzp(path, max_bytes=240*1024*1024)  # Reserve16MiB for the aborted first duplicate-ID diagnostic.
    provenance, prev, prev_t = [], None, None
    started = time.monotonic()
    frame_count, cadence = 0, Counter()
    try:
        for sec, current in frames(reader, START-1, FOLLOW, started+45, provenance):
            frame_count += 1
            if prev is not None:
                cadence[sec-prev_t] += 1
                assert sec-prev_t == 1., 'Native 1s cohort requires complete 1s frames'
                for group, spec in specs.items():
                    for no in current.keys()-prev.keys():
                        row = current[no]
                        if START < sec <= END and row[0] == spec['decision_link'] and row[2] >= spec['decision_pos_m']:
                            ambiguous_appearance[group].append({'vehicle_id': no, 'first_seen_sec': sec, 'row': row})
                    for no in prev.keys() & current.keys():
                        old, new = prev[no], current[no]
                        gate = gate_event(old, new, spec['decision_link'], spec['decision_pos_m'], prev_t, sec)
                        if in_cohort(gate):
                            if no in cohort[group]:
                                cohort[group][no].setdefault('repeated_gate_crossings', []).append(gate)
                            else:
                                cohort[group][no] = {'vehicle_id': no, 'gate_crossing': gate, 'outcome': None}
                        merge = connector_event(old, new, spec['intermediate_merge'], prev_t, sec, False)
                        if merge is not None:
                            counts[group]['intermediate_merge_events_bracket599_to_1200'] += 1
                            if in_cohort(merge):
                                if no in bypass[group]:
                                    bypass[group][no].setdefault('repeated_merge_crossings', []).append(merge)
                                else:
                                    bypass[group][no] = {'vehicle_id': no, 'merge_crossing': merge, 'outcome': None}
                        event = None
                        for kind in ('direct','signal'):
                            event = connector_event(old, new, spec[kind], prev_t, sec, True)
                            if event is not None:
                                event = {'kind': kind, 'connector': spec[kind]['connector'], **event}
                                break
                        if event is None:
                            event = gate_event(old, new, spec['through_link'], spec['through_pos_m'], prev_t, sec)
                            if event is not None:
                                event = {'kind': 'through', **event}
                        for table in (cohort[group], bypass[group]):
                            if no in table:
                                record = table[no]
                                record['last_seen'] = {'sim_sec': sec, 'row': new}
                                if event is not None and record['outcome'] is None:
                                    record['outcome'] = event
                    for table in (cohort[group], bypass[group]):
                        for no in table.keys() & (prev.keys()-current.keys()):
                            if table[no]['outcome'] is None:
                                table[no]['disappearance_before_outcome'] = {'t0': prev_t, 't1': sec, 'last_row': prev[no]}
            prev, prev_t = current, sec
    finally:
        reader.handle.close()
    assert prev_t == FOLLOW and frame_count == 602
    summaries = []
    for group in GROUPS:
        for label, table in [('decision_gate',cohort[group]), ('intermediate_merge_bypass',bypass[group])]:
            distribution = Counter(r['outcome']['kind'] if r['outcome'] else 'unclassified_or_censored' for r in table.values())
            n = len(table); off = distribution['direct'] + distribution['signal']
            resolved = off + distribution['through']
            censored = n-resolved
            summaries.append({'group': group, 'cohort': label, 'cohort_n': n, **dict(distribution),
                              'off_n': off, 'resolved_n': resolved, 'off_fraction_resolved_only': off/resolved if resolved else None,
                              'off_fraction_full_cohort_lower': off/n if n else None,
                              'off_fraction_full_cohort_upper': (off+censored)/n if n else None,
                              'gate_lane_ambiguous_n': sum(r.get('gate_crossing',{}).get('gate_lane_ambiguous',False) for r in table.values()),
                              'unclassified_disappearance_n': sum('disappearance_before_outcome' in r and r['outcome'] is None for r in table.values()),
                              'right_censored_alive_at1200_n': sum(r['outcome'] is None and r['last_seen']['sim_sec']==FOLLOW for r in table.values()),
                              'repeated_gate_ids': [no for no,r in table.items() if r.get('repeated_gate_crossings')],
                              'repeated_merge_ids': [no for no,r in table.items() if r.get('repeated_merge_crossings')],
                              'overlap_gate_and_merge_ids': sorted(cohort[group].keys() & bypass[group].keys()),
                              'native_total_off_prior': priors[group], 'model_total_off_prior': .2})
    assert stat.st_size == path.stat().st_size and stat.st_mtime_ns == path.stat().st_mtime_ns
    assert immutable == {p: sha(Path(p)) for p in immutable}
    output = {'schema': 'static-route-matched-cohorts/v1', 'run': RUN, 'gate_cohort_window': [START, END],
              'window_convention': '(600,750] by interpolated crossing time; exact 599..1200 complete1s observations',
              'follow_until_sec': FOLLOW, 'fzp': {'path':str(path), 'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns,
              'bytes_read':reader.bytes_read, 'elapsed_wall_seconds':time.monotonic()-started, 'bounded_ranges':provenance,
              'frame_count':frame_count,'cadence_counts':dict(cadence)}, 'source_sha256':immutable,
              'native_equivalence_evidence':str(native_evidence), 'gates':specs, 'summary':summaries,
              'decision_cohorts':cohort, 'intermediate_merge_bypass_cohorts':bypass,
              'unclassified_appearances_beyond_gate':ambiguous_appearance, 'other_counts':counts,
              'limitations':['Decision passage is observed; assigned native route attribute is not in FZP.',
                             'No outcome is inferred from disappearance or presumed shortest path.',
                             'Lane differences bracket ambiguity; equal endpoint lanes do not prove no intervening lane change.',
                             'Native default1 is official-document supported, not live COM RelFlow readback.',
                             'Bypass cohorts enter intermediate merge in the same600–750 window; their travel time and upstream origin differ from decision cohorts.']}
    target = ROOT/'diagnostics/static_route_matched_cohorts.json'
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'summary':summaries,'read':output['fzp'],'ambiguous_appearance_n':{g:len(r) for g,r in ambiguous_appearance.items()}},indent=2))


if __name__ == '__main__':
    main()
