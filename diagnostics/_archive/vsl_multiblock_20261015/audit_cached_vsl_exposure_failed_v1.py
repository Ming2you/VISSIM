"""Audit passive VSL transport/FD targets in three existing forecasts.

No traffic rollout, optimization, FZP scan, fitting or native dispatch. Accepted
flows, density and stocks are read from completed response caches. The existing
passive cohort routine is replayed on those fixed flows, never fed back to them.
"""
import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import gzip
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CACHE = HERE / 'matched_off2250_v3'
OUT = HERE / 'cached_vsl_exposure_audit'
read = lambda path: json.loads(Path(path).read_bytes())
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not OUT.exists(), 'Preserve completed or failed audit; never overwrite'
    OUT.mkdir()
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT'] = str(ROOT / 'vendor/NumSim-mine')
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_fd import VSLExposure

    tuning_path = ROOT / 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
    tuning = read(tuning_path)
    network = read(CACHE / 'network.json')
    summary = read(CACHE / 'summary.json')
    assert sha(tuning_path) == summary['model_config_sha256']
    context = lpr.load_sources(tuning['freeway']['lane_plant'])
    cfg = context['component']._config('FW_E', context['parameters']['by_direction']['FW_E'])
    net = cfg.network
    params = net.freeway_segment_params['FW_E']
    # The complete-network snapshot includes the physical FD rows, but its
    # top-level optional FD flag is NOT the component's active FD flag.
    assert params == network['freeway_segment_params']['FW_E']
    assert len(params) == 31
    law = net.freeway_vsl_fd_response['FW_E']
    assert law == dict(law='carlson', A=0.5, E=2.0, alpha=0.0)
    assert not getattr(net, 'vsl_fd_two_branch', False)
    assert not (getattr(net, 'freeway_hadiuzzaman', {}) or {}).get('FW_E')
    spec = net.component_vsl_transport['FW_E']
    heads = lpr._physical_sign_heads(context, SimpleNamespace(**network), 'FW_E', network['freeway_vsl_zone_heads']['FW_E'])
    history_path = CACHE / 'vsl_history/vsl_cohorts_002250.json'
    history = read(history_path)
    assert history['cutoff'] == 2250
    assert history['audit']['FW_E']['retained_nonmaximum_veh'] == 0
    assert {cmd for row in history['cohorts']['FW_E'] for cmd in row} == {'110.0'}
    branches = {str(b['connector']): b['from_cell'] for b in context['geometry']['boundaries'] if b['road'] == 'FW_E' and b['kind'] == 'offramp'}
    merges = {'RM_C' + str(b['connector']): b['to_cell'] for b in context['geometry']['boundaries'] if b['road'] == 'FW_E' and b['kind'] == 'ramp'}
    pins = {str(p): sha(p) for p in [Path(__file__), tuning_path, CACHE / 'network.json', CACHE / 'summary.json', history_path,
        ROOT / 'evaluation/controllers/freeway_fd.py', ROOT / 'evaluation/controllers/lane_plant_runtime.py',
        ROOT / 'evaluation/controllers/lane_freeway_runtime.py', ROOT / 'evaluation/controllers/area_freeway_accounting.py']}
    pins.update({str(p): sha(p) for p in context['paths'].values()})
    active_config = dict(reference_config=str(context['paths']['reference_config']), active_component_fd=law,
        parent_network_fd=network.get('freeway_vsl_fd_response'), transport=spec, head_of_physical_cell=heads,
        parameters=params, alpha_vsl=net.alpha_vsl, rho_max=net.rho_max,
        scope='Component configuration only; no prediction or optimizer invoked')
    save(OUT / 'active_component_config.json', active_config)
    report = dict(status='in_progress', new_forecasts=0, new_native=0, new_fzp_scans=0, new_fits=0,
        production_edits=0, active_component_fd=law, cases={}, source_pins=pins)
    regions = {'upstream14_15': range(14, 16), 'approach16_18': range(16, 19),
               'bottleneck19_23': range(19, 24), 'recovery24_25': range(24, 26), 'downstream26_30': range(26, 31)}
    for result in summary['results']:
        name = result['name']
        path = CACHE / (name + '_response.json.gz')
        pins[str(path)] = sha(path)
        response = json.loads(gzip.decompress(path.read_bytes()))
        assert response['conditional_model_feasibility_witness']
        initial = response['initial_freeway_operands']
        n = list(result['snapshots'][0]['n']['FW_E'])
        rho = list(initial['freeway_density']['FW_E'])
        exp = VSLExposure(n, spec, 110.0)
        exp.cohorts = [{float(cmd): amount for cmd, amount in row.items()} for row in history['cohorts']['FW_E']]
        exp.tangents = [{cmd: 0.0 for cmd in row} for row in exp.cohorts]
        assert max(abs(sum(row.values()) - amount) for row, amount in zip(exp.cohorts, n)) < 1e-7
        steps = defaultdict(dict)
        key = lambda row: (row['start_sec'], row['end_sec'])
        for item in response['resource_allocations']:
            kind, res = item['kind'], item['resource']
            field, index = None, None
            if kind == 'freeway_mainline_sending' and res.startswith('FW_E:cell:'):
                field, index = 'mainline', int(res.split(':')[-1])
            elif kind == 'freeway_terminal_sending' and res == 'FW_E':
                field, index = 'mainline', 30
            elif kind == 'freeway_entry_request' and res == 'FW_E':
                field, index = 'entry', 0
            elif kind == 'freeway_offramp_sending' and res in branches:
                field, index = 'off', res
            if field:
                block = steps[key(item)].setdefault(field, {})
                assert index not in block
                block[index] = item['accepted_total_veh']
        for item in response['transfers']:
            if item['source'] in {'merge_pending:' + r for r in merges} and item['target'] == 'freeway:FW_E':
                steps[key(item)].setdefault('merge', defaultdict(float))[item['source'].split(':', 1)[1]] += item['vehicles']
        frames = {(f['start_sec'], f['end_sec']): f for f in response['freeway_frames']}
        assert sorted(frames) == [(t, t + 5) for t in range(2250, 2700, 5)]
        all_rows, checks = [], dict(max_stock_error=0.0, max_target_formula_error=0.0, control_blocks=[])
        for (start, end), flow in sorted(steps.items()):
            frame = frames[(start, end)]
            assert set(flow['mainline']) == set(range(31))
            q = [flow['mainline'][i] for i in range(31)]
            off, ramp = [0.0] * 31, [0.0] * 31
            for port, amount in flow['off'].items(): off[branches[port]] += amount
            for port, amount in flow.get('merge', {}).items(): ramp[merges[port]] += amount
            commands = [frame['applied_control']['vsl'][f'FW_E__seg{head}'] for head in heads]
            if start in (2250, 2400, 2550): checks['control_blocks'].append(dict(start_sec=start, commands=commands))
            for i, row in enumerate(params):
                nominal = row['v_free'] * math.exp(-(max(0.0, rho[i]) / row['rho_crit']) ** row['metanet_a_m'] / row['metanet_a_m'])
                b = 90.0 / 110.0
                vf, critical, shape = row['v_free'] * b, row['rho_crit'] * (1 + law['A'] * (1 - b)), row['metanet_a_m'] * (law['E'] - (law['E'] - 1) * b)
                target90 = vf * math.exp(-(max(0.0, rho[i]) / critical) ** shape / shape)
                restricted = exp.cohorts[i].get(90.0, 0.0)
                assert set(exp.cohorts[i]) <= {90.0, 110.0}
                legacy = target90 if commands[i] == 90 else nominal
                target = exp.target(cfg, 'FW_E', i, rho[i], legacy, commands[i])
                direct = (restricted / n[i] * (target90 - nominal)) if n[i] > 1e-12 else legacy - nominal
                err = abs(target - nominal - direct)
                checks['max_target_formula_error'] = max(checks['max_target_formula_error'], err)
                assert err < 1e-9
                all_rows.append(dict(start_sec=start, end_sec=end, cell=i, inventory=n[i], rho=rho[i], displayed=commands[i],
                    restricted_veh=restricted, fraction90=restricted / n[i] if n[i] > 1e-12 else 0.0,
                    target110=nominal, target90=target90, mixed_target=target, direct_target_delta=direct))
            nextn = [n[i] + (flow['entry'][0] if i == 0 else q[i - 1]) + ramp[i] - q[i] - off[i] for i in range(31)]
            expected = [math.fsum(row.values()) for row in frame['offramp_route_inventory_state']['cells']['FW_E']]
            err = max(abs(a - b) for a, b in zip(nextn, expected))
            checks['max_stock_error'] = max(checks['max_stock_error'], err)
            assert min(nextn) > -1e-7 and err < 1e-7
            exp.advance(n, nextn, q[:-1], [a + b for a, b in zip(q, off)], flow['entry'][0], ramp, commands)
            n, rho = nextn, list(frame['freeway_density']['FW_E'])
        assert len(all_rows) == 90 * 31
        assert max(abs(a - b) for a, b in zip(n, result['snapshots'][-1]['n']['FW_E'])) < 1e-7
        regional = {}
        for region, cells in regions.items():
            regional[region] = {}
            for block in range(3):
                rows = [r for r in all_rows if r['cell'] in cells and 2250 + 150 * block <= r['start_sec'] < 2400 + 150 * block]
                denom = math.fsum(r['inventory'] * 5 for r in rows)
                exposed = math.fsum(r['restricted_veh'] * 5 for r in rows)
                regional[region][str(block)] = dict(restricted_stock_time_fraction=exposed / denom if denom else None,
                    mass_weighted_direct_target_delta_kmh=math.fsum(r['inventory'] * 5 * r['direct_target_delta'] for r in rows) / denom if denom else None,
                    exposed_time_with_lower_target_fraction=math.fsum(r['restricted_veh'] * 5 for r in rows if r['target90'] < r['target110'] - 1e-9) / exposed if exposed else None,
                    exposed_time_with_higher_target_fraction=math.fsum(r['restricted_veh'] * 5 for r in rows if r['target90'] > r['target110'] + 1e-9) / exposed if exposed else None)
        report['cases'][name] = dict(checks=checks, regional=regional, cohort_conservation_max=exp.max_residual,
            end_restricted_stock=sum(row.get(90.0, 0.0) for row in exp.cohorts), model_delta_ttt=result['delta_veh_h'])
        (OUT / (name + '_rows.json.gz')).write_bytes(gzip.compress(json.dumps(all_rows, allow_nan=False).encode()))
        print(name, json.dumps(report['cases'][name], ensure_ascii=False), flush=True)
    report['status'] = 'cached_transport_and_active_component_fd_audited'
    report['limits'] = [
        'This is a frozen-flow algebraic reconstruction, not an additional traffic forecast or native response.',
        'A target-speed delta is the direct FD term at the same cached density, not a causal speed, capacity or TTT effect.',
        'Positive FD response in a region does not imply beneficial total network cost.',
        'Reference component FD is active even though the complete-network top-level optional FD flag is absent.',
        'The failed adjacent-zone native attempt provides no treatment response; replacement approval is still required.']
    save(OUT / 'summary.json', report)


if __name__ == '__main__':
    main()
