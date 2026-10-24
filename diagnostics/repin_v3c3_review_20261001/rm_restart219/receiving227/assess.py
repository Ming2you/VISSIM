"""Bounded geometry/receiving screen from saved observations and prediction receipts."""
import ctypes
import hashlib
import importlib.util
import json
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.physical_ramp_boundary import gap_acceptance_supply_vph

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
R = ROOT / 'diagnostics/repin_v3c3_review_20261001'
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def posthead(trace, observed, mode, budgets):
    """One changed component, frozen upstream/mainline feedback, conserved stock."""
    meta = trace['initial_buffer']
    speed = meta.get('posthead_travel_speed_kmh', meta['travel_speed_kmh']) / 3.6
    travel = (meta['length_m'] - meta['head_position_m']) / speed
    cohorts = [[(trace['start_sec'] + (meta['length_m']-pos)/speed, 1.)
                for pos, _, lane in meta['initial_cohorts']
                if lane == j+1 and pos >= meta['head_position_m']] for j in (0, 1)]
    initial = [len(c) for c in cohorts]
    ready, admitted, merged = [0., 0.], [0., 0.], [0., 0.]
    events = defaultdict(lambda: [0., 0.])
    if mode == 'native_head':
        for event in observed['head_events']:
            events[math.floor(event['time'])][event['lane']-1] += 1.
    rows, windows, max_balance = [], [], 0.
    for saved in trace['lane_interval_receipts']:
        t = saved['arguments']['start_sec']
        flow, stock = [], []
        for j in (0, 1):
            lane = saved['receipt']['lane_receipts'][j]
            ready[j] += sum(n for eta, n in cohorts[j] if eta <= t+1)
            cohorts[j] = [(eta, n) for eta, n in cohorts[j] if eta > t+1]
            moved = min(ready[j], budgets[t][j])
            ready[j] -= moved
            merged[j] += moved
            head = lane['head_service_veh'] if mode == 'model_head' else events[t][j]
            admitted[j] += head
            if head:
                cohorts[j].append((t+1+travel, head))
            stock.append(ready[j] + sum(n for _, n in cohorts[j]))
            max_balance = max(max_balance, abs(initial[j]+admitted[j]-merged[j]-stock[j]))
            flow.append(moved)
        rows.append(flow)
        if t+1 in (2850, 3000, 3150):
            windows.append(dict(end_sec=t+1, merge_by_lane=[sum(r[j] for r in rows[-150:]) for j in (0, 1)],
                                post_stock_by_lane=stock))
    assert max_balance < 1e-8
    return dict(mode=mode, conditional_only=True, future_native_head=mode == 'native_head',
        merge=sum(merged), merge_by_lane=merged, head_by_lane=admitted,
        windows=windows, max_conservation_residual=max_balance)


def main():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    protocol = read(HERE/'protocol.json')
    previous_protocol = read(HERE.parent/'link52_225/protocol.json')
    for relative, digest in previous_protocol['source_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == digest, relative
    stop = previous_protocol['STOP']
    assert hashlib.sha256(Path(stop['path']).read_bytes()).hexdigest() == stop['sha256']
    previous = read(HERE.parent/'receiving226/assessment.json')
    audit = read(I/'closedloop_recorded2700_native_selected_sc1001_corrected47/analysis/ramp_response_audit.json')
    geometry = read(I/'selected/port_gain/geometry.json')
    network = ROOT/geometry['network']['path']
    data = network.read_bytes()
    assert hashlib.sha256(data).hexdigest() == geometry['network']['sha256']
    PINS[str(network)] = geometry['network']['sha256']
    xml = ET.fromstring(data)
    connector = xml.find('./links/link[@no="10681"]')
    end = connector.find('toLinkEndPt')
    assert end.get('lane') == '2 1'
    assert len(connector.findall('./lanes/lane')) == 2
    mainline = xml.find('./links/link[@no="2"]')
    assert len(mainline.findall('./lanes/lane')) == 4
    merge_position = float(end.get('pos'))
    boundary = next(b for b in geometry['boundaries'] if b['id'] == 'RM_C10681')
    assert boundary['to_cell'] == 12 and boundary['to_pos_m'] == merge_position
    spec = importlib.util.spec_from_file_location('receiving_audit', R/'ramp10681_receiving/assess.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = dict(status='CONDITIONAL_CONNECTED_LANE_SCREEN_NOT_ADOPTED', input_sha256=PINS,
        geometry=dict(connector=10681, connector_lanes=2, mainline_link=2, mainline_lanes=4,
                      connected_mainline_lanes=[1, 2], merge_pos_m=merge_position, merge_cell=12),
        source_sha256=previous_protocol['source_sha256'], evidence={}, arms={},
        full_forecasts=0, new_native_runs=0, FZP_reads=0, fit=0, optimizer=0,
        limitations=[
            'The through detector lies147.5m upstream of the physical merge. Lane changes, inventory and travel time between the planes are not identified by equal-time flow.',
            'Low observed conflicting flow on a congested lane does not prove large usable gaps or receiving space.',
            'The current225 aggregate gap bound is inverted only where strictly below the canonical bound, then redistributed with pre2700 observed shares. This is a frozen component screen.',
            'The lane proportions are held constant in the screen; no causal autonomous evolution of local lane density or space is claimed.',
            'Future native head events are only a component diagnostic. No full-network TTT, RM causal gain, or policy selection is inferred.',
            'This native comparison changes urban green/offset only; all eight RM and VSL commands match.'
        ])
    for arm, case in [('hold', 'held_actual'), ('selected', 'selected')]:
        paths = sorted(Path(p) for p in audit['input_sha256'] if arm in Path(p).parts)
        evidence = []
        for path in paths:
            raw = read(path)
            assert PINS[str(path)] == audit['input_sha256'][str(path)]
            bundle = oc.load_bundle(raw)
            detectors, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'], bundle.obs['detector_config']['sha256'])
            through = sorted((d for d in detectors if d.boundary_ref == 'through:10682'), key=lambda d: d.lane)
            assert [d.lane for d in through] == [1, 2, 3, 4]
            start = through[0].pos
            assert all(d.link == 2 and d.pos == start and d.orientation == 'at' for d in through)
            assigned = oc.assign_window(bundle.obs, bundle.mer_rows)
            counts = [bundle.obs['detectors'][str(d.dcm_no)] for d in through]
            tails = [assigned.tails[d.dcp_no] for d in through]
            mer_counts = [len(assigned.entries[d.dcp_no]) for d in through]
            assert counts == [n+tail for n, tail in zip(mer_counts, tails)]
            if raw['sim_sec'] == 2700:
                assert tails == [0, 0, 0, 0]
            groups = [[v for v in bundle.frame_end['vehicles'] if v[1] == 2 and v[2] == j and start <= v[3] < merge_position] for j in (1, 2, 3, 4)]
            evidence.append(dict(end_sec=raw['sim_sec'], through_counts_150=counts,
                count_source='native per-window detector counters', mer_entry_counts=mer_counts,
                mer_unflushed_tail=tails, individual_entry_events_complete=not any(tails),
                through_pos_m=start, distance_to_merge_m=merge_position-start,
                premerge_vehicles=[len(v) for v in groups],
                premerge_density_veh_km=[len(v)*1000/(merge_position-start) for v in groups],
                premerge_speed_kmh=[sum(v[4] for v in vs)/len(vs) if vs else None for vs in groups],
                gap_from_all_lane_mean_vph=gap_acceptance_supply_vph(sum(counts)*24/4,3.5,1.5),
                gap_from_connected_lane_vph=[gap_acceptance_supply_vph(c*24,3.5,1.5) for c in counts[:2]]))
        shares = [n/sum(evidence[0]['through_counts_150']) for n in evidence[0]['through_counts_150']]
        assert evidence[0]['end_sec'] == 2700
        trace_path = I/'closedloop_recorded2700_select_check_trace10681_rm225_candidate52_response'/f'{case}_RM_C10681_trace.json.gz'
        trace = mod.read(trace_path)
        assert mod.PINS[str(trace_path)] == previous['input_sha256'][str(trace_path)]
        out['input_sha256'].update(mod.PINS)
        canonical = {r['start_sec']: r['available_veh'] for r in trace['resources'] if r['kind'] == 'physical_ramp_merge_canonical_receiving'}
        budgets, diagnostic_rows = {}, []
        for row in trace['lane_interval_receipts']:
            t = row['arguments']['start_sec']
            old = row['arguments']['receiving_budget_veh']
            assert old < canonical[t]-1e-8
            low, high = 0., 100000.
            for _ in range(60):
                middle = (low+high)/2
                if gap_acceptance_supply_vph(middle,3.5,1.5) > old*3600/2:
                    low = middle
                else:
                    high = middle
            q = (low+high)/2
            assert abs(2*gap_acceptance_supply_vph(q,3.5,1.5)/3600-old) < 1e-10
            budgets[t] = [min(canonical[t]/2, gap_acceptance_supply_vph(q*4*share,3.5,1.5)/3600) for share in shares[:2]]
            assert sum(budgets[t]) <= canonical[t]+1e-12
            diagnostic_rows.append(dict(time_sec=t, inferred_frozen_conflict_all_lane_mean_vph=q,
                old_receiving_by_lane=[old/2]*2, candidate_by_lane=budgets[t], canonical_total=canonical[t]))
        observed = previous['arms'][case]['observed']
        out['evidence'][case] = evidence
        out['arms'][case] = dict(pre2700_shares=shares, native_actual=previous['arms'][case]['actual'],
            old_posthead=previous['arms'][case]['posthead'],
            connected_lanes={mode: posthead(trace,observed,mode,budgets) for mode in ('model_head','native_head')},
            frozen_budget_rows=diagnostic_rows)
    assert out['arms']['held_actual']['pre2700_shares'] == out['arms']['selected']['pre2700_shares']
    out['local_posthead_replays'] = 4
    assert out['local_posthead_replays'] <= protocol['max_local_posthead_replays']
    (HERE/'assessment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({arm: dict(actual=d['native_actual']['merge'], prior={m:r['merge'] for m,r in d['old_posthead'].items()}, connected={m:r['merge'] for m,r in d['connected_lanes'].items()}) for arm,d in out['arms'].items()}))


if __name__ == '__main__':
    main()
