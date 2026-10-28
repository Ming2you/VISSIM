# -*- coding: utf-8 -*-
"""c12_declare.py (K8 amendment C1-2 Declare, 2026-10-27 KST) - writes the declared guard rule reference file.

Usage: python -B c12_declare.py <out_dir>
Writes <out_dir>/c1g_guard_rule.json with exclusive create (refuses to overwrite) and prints its sha256 and the
canonical-JSON sha256. Serialisation = codex prepare_next.py data() (the same as amendment C1 declare_values.py):
json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n', UTF-8, LF.
Input: none (constants only; the rule was chosen after data, D-K9-107 / D-K9-114). No run data, no path strings.
Review r1 (ReviewDeclare, 2026-10-27 KST; the Declare output cebd6f05... is kept in work/c12_superseded/): receiver
spans exact (codex), overlap max over positive scores only, path end cells, frame reader, short threshold tied to the
evidence, K2/K6 wording, signal order, meter path assertion.
"""
import hashlib
import json
import os
import sys

KEY_ORDER = ['segments_name', 'segments_sha256', 'unit', 'full_rule', 'capacity_threshold',
             'min_source_capacity_veh', 'feeder_attribution', 'landing_sources', 'short_receiver_rule',
             'reserve_green_sec', 'meter_rule']

RULE = {
    'schema': 'c1g-guard-rule/v1',
    'amendment': 'K8 amendment C1-2',
    'label': 'data-after rule (D-K9-107, D-K9-114); constants only, no thresholds for judging outcomes',
    'choices': {
        'GG0': 'a: storage capacity (vehicles), full means fill >= 1.0',
        'GG1': 'a: U = count_full or observed spill',
        'GG2': 'a: lane',
        'GG3': 'a: short segments (capacity < 2 veh) are not sources; short head lanes are reached by feeder chains',
        'GG4': 'a: all 416 feeder segments, cell-graph reachability with same-link lane change, overlap max',
        'GG5': 'a: off-ramp landing segments are sources',
        'GG6': 'd: M4 0.9 unchanged OR approach-chain trigger, same floor formula, RV-2 table lowering, G-A7',
        'GG7': 'a: codex weights, overlap max, equal live-phase weights zeroed, no FW_E extra weight',
        'GG8': 'a: offline evidence file (name + sha256), runtime reads only',
        'GG9': 'a: same-time lane frame vehicle lengths, frame sha256 checked',
        'GG10': 'a: narrow targeted triggers of design r2 dropped',
        'GG11': 'a: probe states S_G by categories K0-K6, <= 7 per run, <= 14 total',
        'GG12': 'a: R-b with C1G only',
        'GG13': 'b: short receivers judged by count only',
        'G6': "a': D98 r2 section 3 (D98-4' stop, T1/T2, C0E apart, stop on C3' vs C0)",
        'G7': 'a: F-D98 + F-Omega two arms',
        'G8': 'a: probe r2 from scratch, new patch/tools/pins/output root, old HALT bundle kept',
        'G9': 'a: new commit C1-G after C1-3, before C1-4; C1-4 writes 8 keys',
        'G12': 'a: G-K4 at C1-G also runs the C1 arm (no guard key) on the 5 probe states',
    },
    'key': {
        'name': 'storage_capacity_guard',
        'parent': 'c1_port',
        'key_order': KEY_ORDER,
        'fixed_values': {
            'segments_name': 'c1g_storage_segments_v3c3.json',
            'unit': 'lane',
            'full_rule': 'count_or_spill',
            'capacity_threshold': 1.0,
            'min_source_capacity_veh': 2.0,
            'feeder_attribution': 'cell_chain_max',
            'landing_sources': True,
            'short_receiver_rule': 'count',
            'reserve_green_sec': 2.0,
            'meter_rule': 'approach_chain_or_m4',
        },
        'segments_sha256_rule': 'sha256 of the evidence bytes written by P0-17 (a); recorded in the C1 LOG and in '
                                'PINS_P0_C1_2_B.sha256 at P0-17, before any P0-14/P0-15/P0-16/P0-18 or probe r2 '
                                'computation; C1_VALUES_C1_2.json /p0_17/segments_sha256 later carries the same value',
        'accepted_only': {
            'unit': ['lane'], 'full_rule': ['count_or_spill'], 'feeder_attribution': ['cell_chain_max'],
            'landing_sources': [True], 'short_receiver_rule': ['count'], 'meter_rule': ['approach_chain_or_m4'],
        },
        'ranges': {
            'capacity_threshold': 'int or float, not bool, finite, 0 < x <= 1',
            'min_source_capacity_veh': 'int or float, not bool, finite, x >= 0',
            'reserve_green_sec': 'int or float, not bool, finite, 0 < x <= 2 (CX USG:21)',
            'segments_name': 'amendment C1 section 2.0-2 name rule',
            'segments_sha256': '64 lowercase hex',
        },
        'requires_keys': ['storage_release_guard'],
        'policy_token': 'unchanged: no guard value enters cfg.network.sdmpc_options',
    },
    'capacity': {
        'spacing_m': 6.0,
        'spacing_source': 'cfg.network.urban_avg_vehicle_length_m; must equal evidence /spacing_m else ValueError',
        'capacity_veh': 'length_m / spacing_m',
        'count': 'records with link_no == link and lane_no == lane and start_m <= position_m <= end_m (CX USG:51-56, no tolerance)',
        'fill_fraction': 'count / capacity_veh',
        'count_full': 'fill_fraction >= capacity_threshold (CX USG:79-80 form, no tolerance)',
        'short': ('capacity_veh < min_source_capacity_veh; the evidence head /min_source_capacity_veh (the value the '
                  'builder used for every short flag) must equal the key value, else ValueError'),
    },
    'spill': {
        'top_window_m': 12.0,
        'stop_speed_kph': 5.0,
        'max_clear_gap_m': 20.0,
        'bottom_reach': 'max(20.0, 0.2 * length_m)',
        'short_length_m': 12.0,
        'S0': 'a vehicle with speed_kph < 5.0 and start_m <= position_m <= start_m + 12.0 (whole segment if shorter)',
        'S': ('S0 and, walking downstream from the most upstream S0 vehicle over the segment vehicles sorted by '
              'position, consecutive clear gaps (leader position - leader length - follower position) <= 20.0 m reach '
              'a vehicle with position >= end_m - max(20.0, 0.2 * length_m); if length_m <= 12.0 then S = S0'),
        'lengths': ('vehicle length = row[5] of the same-time lane frame matched by vehicle number row[0]; the frame is '
                    'located by obs150_contract.resolve(state /obs150, /obs150/frames/current/path) (directory = '
                    '/obs150/directory) and read by obs150_contract.load_frame(path, /obs150/frames/current/sha256, '
                    'state sim_sec) (UTF-16 or UTF-8 decoding, sha256 pin, schema lane-plant-frame/v1, complete, '
                    'time_s == sim_sec, 15-field rows); every counted vehicle must have a length, else ValueError'),
        'source': 'same as gd_scan.py header (scan definitions fixed before that scan); position = front',
    },
    'full': {
        'normal': 'F = count_full or S',
        'short_receiver': 'F = count_full (GG13 b)',
        'short_source': 'not a source; cells of capacity < 2 veh pass without judgement in chains',
    },
    'segments': {
        'kinds': {'A': 'controlled-phase head lane [segment start, head]',
                  'L': 'off-ramp landing [landing, next head on that lane or link end]',
                  'F': 'feeder lane without our head',
                  'M': 'meter connector lane [0, meter head]',
                  'MA': 'meter approach link lane [0, meter connector departure]',
                  'R': ('receiver lane [landing, next head on that lane or link end] (codex exact span), one segment per '
                        'distinct span; an existing segment is used only if both ends agree within 1e-6 m; id '
                        'R:<link>:<lane>:<landing m with 3 decimals>; all ids unique')},
        'excluded': ['D5:129:1 (report only)'],
        'sources': ['A', 'L', 'F', 'MA'],
        'cell_judges': ['A', 'L', 'F', 'M', 'MA', 'R'],
        'codex_excluded_heads_included': True,
        'native_head_above': 'segment = [that native head, our head]',
        'shared_stop_line': 'SC7 lane with two heads: both phases get the same head-lane score',
    },
    'receivers': {
        'definition': 'codex CX USG:68-76: connectors leaving at source position >= head position - 1e-6 m; landing lane [landing, next head or link end]',
        'all_full': 'head-lane score -1 (codex CX USG:82-83)',
        'some_full': 'no effect (CX USG:77-79)',
        'none': 'head-lane score 0 (codex)',
    },
    'cells': {
        'cut_points': ['link start and end', 'every head position on the lane', 'every connector landing on the lane',
                       'every connector departure from the lane'],
        'edges': ['next cell downstream on the same lane',
                  'connector lane mapping first+i -> landing+i (CX USG:36-45 reading) from the cell holding the departure point',
                  'same-link adjacent lane cell with the same [start, end] interval (both directions)'],
        'cell_full': 'F of the shortest cell-judge segment (kinds in segments.cell_judges) containing the cell (tie: smallest id); '
                     'non-short cell with no containing segment counts as not full; short cell (< 2 veh) passes',
        'stops': ['our head (that head is the server)', 'native or midblock head (no server)', 'sink without stop line',
                  'vehicle input', 'freeway mainline'],
    },
    'attribution': {
        'rule': ('segment s attributes to server X iff F_s and, inside the pre-built (s, X) sub-graph, some path from '
                 'the bottom cell of s (the cell holding its downstream end) to a head cell of X has every cell, both '
                 'end cells included, full or short'),
        'subgraph': 'evidence lists, per (s, X), every cell and edge lying on some s-bottom -> X-head path; the runtime '
                    'searches only inside it',
        'same_link_head_exclusion': 'an F segment on a link that carries our head is not attributed to a head on the same link',
        'score': 'max(1, count / capacity_veh); 0 if all receivers of the head lane the path ends at are full',
        'overlap': ('per server, positive scores only: head-lane scores max(1, n/C) and attributed segment scores '
                    'max(1, n/C) whose segments share lane length (overlap > 0.05 m on the same link and lane) form '
                    'groups; each group adds only its largest score; an attribution scored 0 does not enter; a '
                    'head-lane score -1 is always added (CX USG:82-83, :86-87)'),
    },
    'weights': {
        'phase_weight': 'sum over head-lane scores and attributed segment scores of that phase key (CX USG:86-87)',
        'equal_live_phase_weights': 'if all live phases of a signal (cfg.network.signal_live_phases) have the same '
                                    'weight within 1e-12 (including all zero), all weights of that signal become 0; '
                                    'receipt name equal_weights_zeroed',
        'all_signals_present': ('17 signal keys always present, in cfg.network.signals order (codex constrain '
                                'iterates them; CX USG:58)'),
    },
    'rows': {
        'form': 'codex constrain CX USG:102-145 unchanged except attribute names',
        'reserve_green_sec': 2.0,
        'required': 'min(reserve_green_sec, 0.5 * max(0, M_k)); no row if required < 0.01',
        'seed': 'codex operating_seed CX USG:148-166 when any block receipt is constrained, else current branch',
    },
    'meter': {
        'rule': 'approach_chain_or_m4',
        'trigger': ('some MA, F or L segment is attributed to the meter by the cell rule (the path passes the M cells, '
                    'so the pre-head connector must be full too); M full alone is not a trigger; the builder asserts '
                    'that every path to a meter head cell holds the non-short M cell and at least one non-short cell '
                    'on that meter MA lanes (P0-17 f)'),
        'm4': 'storage_release_guard 0.9 unchanged',
        'floor_if_guard_only': 'max(base, min(cycle_sec, previous_green + max_green_change_sec)) (CX PRB:901 form)',
        'then': 'RV-2 table lowering, then G-A7 with (triggered or guard_triggered)',
        'meters': ['RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10681', 'RM_C10480', 'RM_C10482', 'RM_C10644', 'RM_C10646'],
    },
    'probe_states': {
        'runs': ['sdmpc31_v3c3_nc_s31', 'sdmpc31_v3c3_nc_s43'],
        'times': 'T in {1050, 1200, ..., 8850}',
        'skip': 'judging states Z1 and Z2 of amendment C1 section 6.2 C1-0 guard (2)',
        'categories': {
            'K0': 'all signal weights 0 and no meter guard trigger',
            'K1': 'SC1001_p3 weight > 0',
            'K2': ('SC1004_p3 or SC1004_p4 weight > 0 and a segment scoring into that phase (its own head lanes '
                   'included) lies on link 71, 10641, 126 or 10643'),
            'K3': 'a guard trigger on RM_C10639, RM_C10681, RM_C10490 or RM_C10484',
            'K4': 'some signal with two or more phases of weight > 0',
            'K5': 'some head lane with score -1',
            'K6': ('the decision 150 s before the first K1 decision, if that T >= 1050, is not a judging state (Z1, '
                   'Z2) and is not already taken; else none'),
        },
        'order': 'K0, K1, K2, K3, K4, K5 each take the first true T not already taken; K6 after K1; one T at most once',
        'limit': '<= 7 per run, <= 14 total; a category never true is written as none',
        'state_key': '(run name, T); seed from run provenance /seed, never from a folder name',
    },
    'null_evidence': {
        'name': 'c1g_storage_segments_null_v3c3.json',
        'rule': 'the P0-17 evidence with every source flag false and every attribution sub-graph and meter path removed; '
                'used only by the C1G0 test arm',
    },
}


def data(x):
    return (json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf8')


def canon(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                     allow_nan=False).encode('utf8')).hexdigest()


def main():
    out = sys.argv[1]
    raw = data(RULE)
    path = os.path.join(out, 'c1g_guard_rule.json')
    with open(path, 'xb') as fh:
        fh.write(raw)
    print(json.dumps({'file': 'c1g_guard_rule.json', 'sha256': hashlib.sha256(raw).hexdigest(),
                      'canonical_sha256': canon(RULE), 'bytes': len(raw)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
