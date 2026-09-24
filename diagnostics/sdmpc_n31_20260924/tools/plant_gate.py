r"""V3b plant gate (plan D7, N31 G4): hold the 900 s action, roll the 31-cell freeway component
450 s, compare cell N and v with the G1 frames at +150/+300/+450 s. Lane loss on and off.

    plant_gate.py observe --tuning <tuning> --frame <frame_T.json> [--time T]
    plant_gate.py extract --run <G1 run | decisions_*> --cutoff 900.1 --tuning <tuning> --out <folder>
                          [--fzp F --err E] [--no-port-details]
    plant_gate.py window  --observations <folder> --cutoff 900.1 --tuning <tuning> --out window.json
                          [--reference-config <json>] [--no-port-profile]
    plant_gate.py run     --tuning <tuning> --decisions <G1 decisions_*> --window window.json
                          [--cutoff 900] [--initial frame|window] [--band FW_E=25,FW_W=17]
                          [--reference-config <json>] [--out gate.json]

G1 (plan V3b):  extract (G1 FZP up to 900.1) -> window (history_forecast at 900.1, calibration
boundary_config via --reference-config) -> run --cutoff 900 (frames 900/1050/1200/1350).

  extract     the calibration extractor's own observers (extract_observations.Observer/PortObserver,
              native_frames) on the G1 FZP, stopped at the cutoff: nothing after it is read. EO's main
              cannot take a G1 run (completion_inputs wants a fast_nc run.json ending at 5400/7200/9000,
              summarize_fast_nc.py:226-249), so this replaces only that receipt check; the geometry is the
              manifest's pinned calibration geometry (whose network sha must be the run's), the removals
              come from the run's final .err (parse_bytes, no partial tail), the FZP is the one file in the
              obs150 EvalOutDir, and the recording phase is read from its first record (G1 at SimRes 10 and
              VehRecResolution 50: records at 5.1, 10.1, ...; phase 0.1 like B110 run_extract.py). The
              cutoff must sit on that 30 s grid (900.1). Output: cells/flows/boundaries_30s.csv,
              ports_30s.csv + port_cohorts_30s.json, geometry.json, manifest.json.

What is compared (and what is not):
  plant       the component the v2 manifest pins (sources.geometry = the refined 31-cell calibration
              geometry, sources.reference_config, sources.parameters['parameters'], boundary family, base
              FD) built as canonical_harness.CanonicalFreewayModel. The pass band (FW_E 20-25, FW_W 13-17
              km/h speed RMSE) is the held-out history_forecast of the calibration's own boundary_config.json;
              --reference-config <that file> runs exactly that component (checked: B110 s31_v2nc
              observations at 2700.1 give FW_E 23.92 / FW_W 15.89). The manifest's reference_config adds
              the transport keys (C7) including the ramp receiving nodes, which need the window's
              'ramp_dynamics' (physical-ramp-boundary/v1 lane buffers, as LPR.initialize builds them); a
              window without it is refused, never run with a silent substitute.
  initial     --initial frame (default): the G1 frame at the cutoff binned into the 31 cells (chain
              offsets + cell bounds of the geometry; N = vehicles, v = mean front speed, None when empty).
              --initial window: the window file's own initial_cells.
  boundaries  the window file's boundary_steps at the component's integration step (source demand, ramp
              releases, off capacities and splits, off occupancy/drainage) exactly as
              boundary_factory.build_window(..., 'history_forecast') writes them; 'window' builds that file
              from an observation folder of the G1 run (the calibration's own extractor output; ports need
              its --port-details files, else --no-port-profile). Nothing future is read.
  action      the held action is the decision's VSL: every refined zone head h gets the command of its
              parent cell (vsl_command_space parent_21), in every step. Meter rates are NOT re-imposed:
              history_forecast releases are the realized recent ramp flows; the gate reports the held
              meter rates beside them (meter_rates_held) so a restricting meter is visible.
  lane loss   port_dynamics.occupancy_lane_loss True and False, both reported; the verdict uses the
              manifest port_profile's own setting (plan V3b: report only, keep the default).
  observed    G1 frames at cutoff+150/+300/+450 binned the same way. The rollout starts at the window's
              own start (900.1 for a G1 window); predictions are read at window start + lead and compared
              with the frames at cutoff + lead (a 0.1 s offset, reported as window_offset_s).
  metrics     scoring.score_rollout masks: speed errors on cells with observed N >= 5; cell N on all cells.
  verdict     per road, pooled speed RMSE over the three leads: PASS <= band, OUTSIDE_BAND <= 2 x band,
              STOP_ASK above (plan V3b: "2배를 넘으면 멈추고 여쭙니다"). One sample: a check, not a test.
"""
from __future__ import annotations

import argparse
import bisect
import copy
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n31_common import (ROOT, ToolError, file_sha256, find_decisions_dir, find_freeze_root,  # noqa: E402
                        load_effective_tuning, oc, read_json, repo_path, require, write_json)

CAL = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
LEADS = (150, 300, 450)
HORIZON = 450
SPEED_MASK_N = 5
DEFAULT_BAND = {'FW_E': 25.0, 'FW_W': 17.0}
CHAIN_END_TOL_M = 1.0
WINDOW_OFFSET_MAX_S = 1.0     # a window may start this much after the decision cutoff (FZP phase 0.1)
EXTRACT_SCHEMA = 'sdmpc31-g1-observations/v1'
EXTRACT_DEADLINE_SEC = 1800


# ---------------------------------------------------------------- inputs
def plant_sources(tuning_path, reference_config=None):
    """(root, manifest, {key: absolute path}) of the v2 manifest the tuning selects.

    reference_config replaces sources.reference_config (e.g. the calibration's boundary_config.json);
    every other source stays the pinned one."""
    tuning_path = Path(tuning_path).resolve()
    root = find_freeze_root(tuning_path) or ROOT
    tuning, _ = load_effective_tuning(tuning_path)
    manifest_path = repo_path(root, tuning['freeway']['lane_plant'])
    manifest = read_json(manifest_path)
    oc.validate_plant_manifest_v2(manifest)
    paths = {key: repo_path(root, pin['path']) for key, pin in manifest['sources'].items()}
    for key, pin in manifest['sources'].items():
        require(oc.file_sha256(paths[key]) == pin['sha256'], f'sources.{key} bytes differ from the manifest pin')
    if reference_config is not None:
        paths['reference_config'] = Path(reference_config).resolve()
        require(paths['reference_config'].is_file(), f'reference config missing: {reference_config}')
    return root, manifest, paths


def read_frame(path, time_s=None):
    """A lane-plant-frame/v1 (the VBS writes UTF-16 or UTF-8); time_s None takes the frame's own."""
    data = Path(path).read_bytes()
    text = data.decode('utf-16') if data.startswith((b'\xff\xfe', b'\xfe\xff')) else data.decode('utf-8-sig')
    frame = json.loads(text)
    oc.validate_frame(frame, frame.get('time_s') if time_s is None else time_s)
    return frame


# ---------------------------------------------------------------- frame -> 31 cells
class CellMap:
    def __init__(self, geometry):
        self.bounds = {road: list(values) for road, values in geometry['bounds'].items()}
        self.offsets = {}
        for road, chain in geometry['chains'].items():
            for piece in chain:
                require(piece['link'] not in self.offsets, f'link {piece["link"]} is on two chains')
                self.offsets[piece['link']] = (road, float(piece['offset_m']), float(piece['length_m']))
        self.parent = {(c['road'], int(c['cell'])): int(c.get('parent_cell', c['cell'])) for c in geometry['cells']}
        for road, bounds in self.bounds.items():
            require(len(bounds) - 1 == sum(1 for (r, _) in self.parent if r == road),
                    f'{road}: bounds and cells disagree')

    def cell_of(self, link, pos):
        found = self.offsets.get(link)
        if found is None:
            return None
        road, offset, length = found
        require(-1e-6 <= pos <= length + CHAIN_END_TOL_M, f'position {pos} outside chain link {link}')
        bounds = self.bounds[road]
        x = min(offset + pos, bounds[-1])
        return road, min(bisect.bisect_right(bounds, x) - 1, len(bounds) - 2)

    def bin(self, frame, time_s):
        """[{time_s, road, cell, n_veh, v_kmh}] of every cell; v None for an empty cell."""
        acc = {(road, c): [] for road, bounds in self.bounds.items() for c in range(len(bounds) - 1)}
        for row in frame['vehicles']:
            found = self.cell_of(row[1], row[3])
            if found is not None:
                acc[found].append(float(row[4]))
        return [{'time_s': float(time_s), 'road': road, 'cell': c, 'n_veh': float(len(v)),
                 'v_kmh': math.fsum(v) / len(v) if v else None} for (road, c), v in sorted(acc.items())]


# ---------------------------------------------------------------- held action
def held_vsl_commands(action, component, cellmap):
    """{road__seg<h>: command} for every refined zone head h, from the parent-21 action commands."""
    vsl = action.get('vsl', {})
    commands, spread = {}, {}
    for road in component.roads:
        heads = list(component.base.network.freeway_vsl_zone_heads[road])
        n = len(component.base.network.freeway_segment_lanes[road])
        for i, h in enumerate(heads):
            parent = cellmap.parent[road, h]
            key = f'{road}__seg{parent}'
            require(key in vsl, f'Held action lacks the parent VSL command {key}')
            members = {cellmap.parent[road, c] for c in range(h, heads[i + 1] if i + 1 < len(heads) else n)}
            values = {float(vsl[f'{road}__seg{p}']) for p in members if f'{road}__seg{p}' in vsl}
            if len(values) > 1:
                spread[f'{road}__seg{h}'] = sorted(values)
            commands[f'{road}__seg{h}'] = float(vsl[key])
    return commands, spread


# ---------------------------------------------------------------- metrics
def stats(errors):
    if not errors:
        return {'mae': None, 'rmse': None, 'bias': None, 'count': 0}
    return {'mae': math.fsum(abs(x) for x in errors) / len(errors),
            'rmse': math.sqrt(math.fsum(x * x for x in errors) / len(errors)),
            'bias': math.fsum(errors) / len(errors), 'count': len(errors)}


def compare_cells(predicted, observed, roads):
    """Per road: horizons {lead: {speed, cell_n, totals}} and pooled speed/cell_n stats."""
    out = {}
    for road in roads:
        pooled_v, pooled_n, horizons = [], [], {}
        for lead in LEADS:
            p = {r['cell']: r for r in predicted[lead] if r['road'] == road}
            o = {r['cell']: r for r in observed[lead] if r['road'] == road}
            require(set(p) == set(o) and p, f'{road} +{lead}: predicted and observed cells differ')
            ev, en = [], []
            for c in sorted(o):
                en.append(float(p[c]['n_veh']) - float(o[c]['n_veh']))
                if o[c]['n_veh'] >= SPEED_MASK_N and o[c]['v_kmh'] is not None:
                    ev.append(float(p[c]['v_kmh']) - float(o[c]['v_kmh']))
            horizons[str(lead)] = {'speed': stats(ev), 'cell_n': stats(en),
                                   'total_n_observed': math.fsum(float(r['n_veh']) for r in o.values()),
                                   'total_n_predicted': math.fsum(float(r['n_veh']) for r in p.values())}
            pooled_v += ev
            pooled_n += en
        out[road] = {'horizons': horizons, 'speed': stats(pooled_v), 'cell_n': stats(pooled_n)}
    return out


def verdict(metrics, band):
    result = {}
    for road, m in metrics.items():
        rmse, limit = m['speed']['rmse'], band[road]
        result[road] = ('NO_SPEED_SAMPLES' if rmse is None else 'PASS' if rmse <= limit
                        else 'OUTSIDE_BAND' if rmse <= 2 * limit else 'STOP_ASK')
    return result


def parse_band(text):
    band = dict(DEFAULT_BAND)
    if text:
        for item in text.split(','):
            road, value = item.split('=')
            require(road in band, f'Unknown road in --band: {road}')
            band[road] = float(value)
    return band


# ---------------------------------------------------------------- commands
def _component(paths):
    sys.path.insert(0, str(ROOT))
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    geometry = read_json(paths['geometry'])
    return CanonicalFreewayModel(geometry, paths['reference_config']), geometry


def fzp_phase(fzp, interval_sec):
    """Recording phase of an FZP: the first record's SIMSEC modulo the record interval."""
    with open(fzp, 'rb') as stream:
        for raw in stream:
            if raw.startswith(b'$VEHICLE:'):
                names = raw.decode('ascii').strip().split(':', 1)[1].split(';')
                break
        else:
            raise ToolError(f'{fzp}: no $VEHICLE header')
        for raw in stream:
            if raw.strip():
                first = float(raw.split(b';')[names.index('SIMSEC')])
                return round(math.fmod(first, interval_sec), 6), first
    raise ToolError(f'{fzp}: no vehicle record')


def g1_sources(run):
    """(fzp, [.err], network sha256) of a watchdog run folder: the obs150 EvalOutDir FZP, and the network
    folder's <stem>.err (when VISSIM wrote one) plus the simulation <stem>_001.err the states name."""
    decisions = find_decisions_dir(run)
    run_dir, name = decisions.parent, decisions.name[len('decisions_'):]
    provenance = read_json(run_dir / f'run_provenance_{name}.json')
    states = sorted(decisions.glob('state_*.json'))
    require(states, f'No state files in {decisions}')
    obs = read_json(states[-1])[oc.RAW_STATE_KEY]
    fzps = sorted(Path(obs['mer']['source']).parent.glob('*.fzp'))
    require(len(fzps) == 1, f'Exactly one FZP expected in {Path(obs["mer"]["source"]).parent}, found {len(fzps)}')
    simulation = Path(obs['err']['source'])
    require(simulation.name.endswith('_001.err'), f'Unexpected simulation .err name: {simulation}')
    network_err = simulation.with_name(simulation.name[:-len('_001.err')] + '.err')
    errs = [p for p in (network_err, simulation) if p.is_file()]
    return fzps[0], errs, provenance['files']['network']['sha256']


def extract_observations(fzp, errs, geometry_path, cutoff, out, *, network_sha256=None, port_details=True,
                         interval_sec=oc.VEHREC_INTERVAL_SEC):
    """EO's Observer/PortObserver over the FZP frames up to and including the cutoff (module docstring).
    errs: every .err of the run (EO reads all receipt .err files); removals come from all of them."""
    sys.path.insert(0, str(ROOT))
    from diagnostics.analyze_no_control_corridors import native_frames
    from diagnostics.capture_native_runtime_errors import parse_bytes
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1 import extract_observations as eo
    fzp, out = Path(fzp), Path(out)
    errs = [Path(e) for e in ([errs] if isinstance(errs, (str, Path)) else errs)]
    geometry = read_json(geometry_path)
    if network_sha256 is not None:
        require((geometry.get('network') or {}).get('sha256') == network_sha256,
                'The pinned calibration geometry was extracted from another network than this run')
    require(not out.exists(), f'Output folder exists (never reused): {out}')
    removals, err_proof = [], []
    for err in errs:
        require(err.is_file(), f'.err missing: {err}')
        parsed = parse_bytes(err.read_bytes())
        require(not parsed['partial_tail_bytes'] and not parsed['unparsed_removal_lines'],
                f'Incomplete removal evidence in {err} (run still writing?)')
        removals.extend(x for x in parsed['events'] if x['kind'] == 'lane_change_removal')
        err_proof.append({'path': str(err), 'sha256': file_sha256(err)})
    phase, first = fzp_phase(fzp, interval_sec)
    grid = (cutoff - phase) / 30
    require(abs(grid - round(grid)) < 1e-8,
            f'Cutoff {cutoff} is off the 30 s observation grid of phase {phase} (e.g. {math.floor(grid) * 30 + phase:g})')
    observer = eo.Observer(geometry, removals, interval_sec=interval_sec, phase_sec=phase)
    ports = eo.PortObserver(geometry, interval_sec=interval_sec, phase_sec=phase) if port_details else None
    evidence = {'path': str(fzp), 'bytes': fzp.stat().st_size, 'first_record_sec': first}
    started = time.monotonic()
    for sec, frame in native_frames(fzp, evidence, deadline=started + EXTRACT_DEADLINE_SEC,
                                    interval_sec=interval_sec, phase_sec=phase):
        observer.advance(sec, frame)
        if ports is not None:
            ports.advance(sec, frame)
        if sec >= cutoff - 1e-8:
            break
    require(abs(observer.sec - cutoff) < 1e-8, f'The FZP ends at {observer.sec} before the cutoff {cutoff}')
    if phase:      # EO main: the first bin starts at the empty initialization, not at a phase-time state
        for rows in (observer.flows, observer.boundary_rows, ports.rows if ports else []):
            for row in rows:
                if abs(row['window_end_s'] - (30 + phase)) < 1e-8:
                    row['window_start_s'] = 0
    out.mkdir(parents=True)
    write_json(out / 'geometry.json', geometry)
    for name, rows in (('cells_30s', observer.cells), ('flows_30s', observer.flows),
                       ('boundaries_30s', observer.boundary_rows)):
        eo.table(out / (name + '.csv'), rows)
    if ports is not None:
        eo.table(out / 'ports_30s.csv', ports.rows)
        if ports.events:
            eo.table(out / 'port_events.csv', ports.events)
        write_json(out / 'port_cohorts_30s.json', ports.snapshots)
    manifest = {'schema': EXTRACT_SCHEMA, 'cell_index_base': 0, 'native_phase_sec': phase,
                'observation_interval_sec': interval_sec, 'terminal_sec': observer.sec, 'causal_cutoff_s': cutoff,
                'fzp': evidence, 'errors': err_proof, 'lane_change_removals': len(removals),
                'geometry': {'path': str(geometry_path), 'sha256': file_sha256(geometry_path)},
                'extractor': {'path': eo.__file__, 'sha256': file_sha256(eo.__file__)},
                'cell_window_conservation_checks': observer.checks,
                'unmatched_native_removals_before_cutoff': sum(
                    1 for i, r in enumerate(removals) if i not in observer.removal_matched and r['time_sec'] <= cutoff),
                'note': 'extract_observations.py Observer/PortObserver stopped at the cutoff; the fast_nc completion '
                        'receipt check is the only EO step not run (a G1 watchdog run has none).'}
    write_json(out / 'manifest.json', manifest)
    print(f'PLANT_OBSERVATIONS_OK out={out} phase={phase} cutoff={cutoff} checks={observer.checks} '
          f'removals={len(removals)}')
    return manifest


def build_window_file(observations, cutoff, tuning, out, *, reference_config=None, port_profile=True):
    _, manifest, paths = plant_sources(tuning, reference_config)
    component, _ = _component(paths)
    sys.path.insert(0, str(ROOT / CAL))
    from boundary_factory import ObservationData, build_window
    # Steps at the component's own integration step (reference_config physical_integration_step_sec).
    step = int(component.base.simulation.T_f_sec)
    window = build_window(ObservationData(observations), cutoff, 'history_forecast',
                          read_json(paths['port_profile']) if port_profile else None,
                          model_step_sec=step, horizon_sec=HORIZON)
    window['meta']['source_observations'] = str(observations)
    window['meta']['reference_config'] = str(paths['reference_config'])
    sha = write_json(out, window)
    print(f'PLANT_WINDOW_OK out={out} sha256={sha} steps={len(window["boundary_steps"])}')
    return window


def run_gate(tuning, decisions, window_path, cutoff=900, initial='frame', band=None, out=None, *, reference_config=None):
    band = band or dict(DEFAULT_BAND)
    _, manifest, paths = plant_sources(tuning, reference_config)
    component, geometry = _component(paths)
    receiving = sorted(getattr(component, 'ramp_receiving_nodes', {}) or {})
    cellmap = CellMap(geometry)
    decisions = Path(decisions)
    frame = lambda t: read_frame(decisions / Path(*oc.frame_path(t).split('/')), t)
    window = read_json(window_path)
    steps = copy.deepcopy(window['boundary_steps'])
    require(steps, 'Window has no boundary steps')
    start = float(steps[0]['window_start_s'])
    require(-1e-6 < start - cutoff < WINDOW_OFFSET_MAX_S,
            f'Window starts at {start}, not at the cutoff {cutoff} (or within its FZP phase)')
    ramp_dynamics = window.get('ramp_dynamics')
    require(not receiving or ramp_dynamics is not None,
            f'The reference config declares ramp receiving nodes {receiving}; the window must carry their '
            "'ramp_dynamics' lane buffers (or pass --reference-config <calibration boundary_config.json>)")
    if initial == 'frame':
        initial_cells = cellmap.bin(frame(cutoff), start)      # the decision's frame is the state at the start
    else:
        initial_cells = copy.deepcopy(window['initial_cells'])
    action = read_json(decisions / f'action_{cutoff:06d}.json')
    commands, spread = held_vsl_commands(action, component, cellmap)
    for step in steps:
        step['vsl_commands'] = dict(commands)
    parameters = read_json(paths['parameters'])['parameters']
    observed = {lead: cellmap.bin(frame(cutoff + lead), cutoff + lead) for lead in LEADS}
    port_profile = read_json(paths['port_profile'])
    variants = {}
    base = window.get('port_dynamics')
    for lane_loss in ((True, False) if base is not None else (None,)):
        port = None if base is None else {**copy.deepcopy(base), 'occupancy_lane_loss': lane_loss}
        extra = {'ramp_dynamics': ramp_dynamics} if ramp_dynamics is not None else {}
        result = component.rollout(initial_cells, steps, parameters, window.get('initial_origin_queue'),
                                   port_dynamics=port, horizon_sec=HORIZON, **extra)
        predicted = {lead: [r for r in result['cells'] if abs(float(r['time_s']) - (start + lead)) < 1e-6]
                     for lead in LEADS}
        metrics = compare_cells(predicted, observed, component.roads)
        name = 'no_port_dynamics' if lane_loss is None else f'lane_loss_{"on" if lane_loss else "off"}'
        variants[name] = {'metrics': metrics, 'verdict': verdict(metrics, band)}
    default = ('no_port_dynamics' if base is None else
               f'lane_loss_{"on" if port_profile.get("occupancy_lane_loss") else "off"}')
    report = {'schema': 'sdmpc31-plant-gate/v1', 'cutoff_s': cutoff, 'window_start_s': start,
              'window_offset_s': round(start - cutoff, 6), 'horizon_s': HORIZON, 'initial': initial,
              'band_speed_rmse_kmh': band, 'manifest_sources': {k: str(v) for k, v in paths.items()},
              'reference_config_overridden': reference_config is not None, 'ramp_receiving_nodes': receiving,
              'window': str(window_path), 'window_meta': window.get('meta'),
              'held_vsl_commands': commands, 'held_vsl_zone_spread': spread,
              'meter_rates_held': action.get('ramp_metering'),
              'variants': variants, 'default_variant': default, 'verdict': variants[default]['verdict']}
    out = Path(out) if out else decisions.parent / f'plant_gate_{cutoff:06d}.json'
    write_json(out, report)
    for name, v in variants.items():
        for road, m in v['metrics'].items():
            print(f'PLANT_GATE {name} {road} speed_rmse={m["speed"]["rmse"]} cell_n_rmse={m["cell_n"]["rmse"]} '
                  f'verdict={v["verdict"][road]}')
    print(f'PLANT_GATE_VERDICT {json.dumps(report["verdict"], sort_keys=True)} default={default} out={out}')
    return report


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    o = sub.add_parser('observe')
    o.add_argument('--tuning', required=True)
    o.add_argument('--frame', required=True)
    o.add_argument('--time', type=int, default=None)
    e = sub.add_parser('extract')
    e.add_argument('--run', default=None, help='G1 run folder or its decisions_* folder (finds the FZP and .err)')
    e.add_argument('--fzp', default=None)
    e.add_argument('--err', action='append', default=None, help='every .err of the run (repeat the option)')
    e.add_argument('--cutoff', type=float, required=True)
    e.add_argument('--tuning', required=True)
    e.add_argument('--out', required=True)
    e.add_argument('--no-port-details', action='store_true')
    w = sub.add_parser('window')
    w.add_argument('--observations', required=True)
    w.add_argument('--cutoff', type=float, default=900.0)
    w.add_argument('--tuning', required=True)
    w.add_argument('--out', required=True)
    w.add_argument('--reference-config', default=None)
    w.add_argument('--no-port-profile', action='store_true')
    r = sub.add_parser('run')
    r.add_argument('--tuning', required=True)
    r.add_argument('--decisions', required=True)
    r.add_argument('--window', required=True)
    r.add_argument('--cutoff', type=int, default=900)
    r.add_argument('--initial', choices=('frame', 'window'), default='frame')
    r.add_argument('--band', default='')
    r.add_argument('--reference-config', default=None)
    r.add_argument('--out', default=None)
    args = parser.parse_args(argv)
    if args.command == 'observe':
        _, _, paths = plant_sources(args.tuning)
        frame = read_frame(args.frame, args.time)
        print(json.dumps(CellMap(read_json(paths['geometry'])).bin(frame, frame['time_s'])))
    elif args.command == 'extract':
        _, manifest, paths = plant_sources(args.tuning)
        network = manifest['sources']['network']['sha256']
        if args.run:
            require(args.fzp is None and args.err is None, 'Pass --run or --fzp/--err, not both')
            fzp, errs, network = g1_sources(args.run)
        else:
            require(args.fzp and args.err, 'extract needs --run, or --fzp and --err')
            fzp, errs = Path(args.fzp), [Path(e) for e in args.err]
        extract_observations(fzp, errs, paths['geometry'], args.cutoff, args.out, network_sha256=network,
                             port_details=not args.no_port_details)
    elif args.command == 'window':
        build_window_file(args.observations, args.cutoff, args.tuning, args.out,
                          reference_config=args.reference_config, port_profile=not args.no_port_profile)
    else:
        report = run_gate(args.tuning, args.decisions, args.window, args.cutoff, args.initial,
                          parse_band(args.band), args.out, reference_config=args.reference_config)
        return 0 if all(v == 'PASS' for v in report['verdict'].values()) else 1
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main(sys.argv[1:]))
    except (ToolError, oc.ObsContractError) as error:
        print(f'PLANT_GATE_ERROR {error}')
        sys.exit(2)
