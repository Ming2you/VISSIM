"""Compile a pinned native command diagnostic; no COM/model/controller imports."""
import argparse
from contextlib import redirect_stdout
import csv
import hashlib
import io
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    from .fast_nc_prepare import prepare_native_preserve
except ImportError:
    from fast_nc_prepare import prepare_native_preserve

CLASSES = (10, 20, 30, 70)
SCHEMA = 'native-fixed-profile/v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Expected integer ' + label)
    return value


def compile_profile(network, profile):
    if profile.get('schema') != SCHEMA or profile.get('network_sha256') != sha(network):
        raise ValueError('Profile schema or exact network SHA differs')
    native = ET.parse(network).getroot()
    simulation = native.find('./simulation')
    if profile.get('seed') != int(simulation.get('randSeed')):
        raise ValueError('Profile must retain saved seed')
    resolution_probe = profile.get('native_resolution_probe')
    if resolution_probe is not None:
        if (type(resolution_probe) is not int or resolution_probe not in (1, 10)
                or int(simulation.get('simRes')) != resolution_probe
                or profile.get('vsl_commands') or profile.get('meter_commands')):
            raise ValueError('Resolution probe requires matching saved resolution and no control commands')
    elif int(simulation.get('simRes')) != 1:
        raise ValueError('Fixed profile requires saved SimRes1')
    start = integer(profile['control_start_sec'], 'control start', 150)
    end = integer(profile['terminal_sec'], 'terminal', 1)
    if start % 150 or end not in (1050, 1800, 2250, 3000, 4500, 5400, 7200, 9000) or start >= end:
        raise ValueError('Fixed profile start/horizon is unsupported')
    saved_period = integer(int(simulation.get('simPeriod')), 'saved SimPeriod', 1)
    effective_period = max(saved_period, end + 1)
    if native.find('./evaluation/scDetRec').get('writeFile') != 'true':
        raise ValueError('Native full-scope LDP recording must already be enabled')
    dsds = {int(n.get('no')): n for n in native.findall('./desSpeedDecisions/desSpeedDecision')}
    distributions = {int(n.get('no')): {**n.attrib, 'points': [dict(p.attrib) for p in n.findall('./speedDistrDatPts/speedDistributionDataPoint')]}
                     for n in native.findall('./desSpeedDistributions/desSpeedDistribution')}
    signals = {int(n.get('no')): n for n in native.findall('./signalControllers/signalController')}
    groups = {sc: [int(s.get('no')) for s in n.findall('./sgs/signalGroup')] for sc, n in signals.items()}
    ldp_groups = {}
    for sc, node in signals.items():
        selected = [int(p.get('sg').split()[1]) for p in node.findall('./scDetRecConf/signalOutputConfigurationElement') if p.get('configName') == 'SG_BILD']
        if selected:
            if len(selected) != len(set(selected)) or not set(selected) <= set(groups[sc]):
                raise ValueError('Invalid native LDP SG address declaration')
            ldp_groups[sc] = selected
    initial = []
    for no, node in sorted(dsds.items()):
        for pair in node.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution'):
            cls = int(pair.get('vehClass'))
            initial.append([0, 'vsl', no, cls, int(pair.get('desSpeedDistr'))])
    for sc, sgs in sorted(groups.items()):
        for sg in sgs:
            initial.append([0, 'signal', sc, sg, 'READ'])
    events, seen = [], set()
    previous = {}
    vsl_locations = {}
    for command in sorted(profile.get('vsl_commands', []), key=lambda r: (r['time_s'], r['dsd_no'])):
        sec = integer(command['time_s'], 'VSL time')
        no = integer(command['dsd_no'], 'DSD', 1)
        value = integer(command['speed_id'], 'speed distribution ID', 1)
        if sec < start or sec >= end or sec % 150 or no not in dsds or value not in distributions:
            raise ValueError('Invalid VSL time/address/distribution')
        key = ('vsl', sec, no)
        if key in seen:
            raise ValueError('Duplicate VSL command')
        seen.add(key)
        node = dsds[no]
        native_ids = {int(p.get('vehClass')): int(p.get('desSpeedDistr')) for p in node.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')}
        if any(c not in native_ids for c in CLASSES):
            raise ValueError('Target DSD lacks a required vehicle class')
        prior_time, prior = previous.get(no, (-150, native_ids))
        if sec - prior_time < 150 or any(abs(value - prior[c]) > 20 for c in CLASSES):
            raise ValueError('VSL exceeds20 distribution-ID units per150s')
        for cls in CLASSES:
            events.append([sec, 'vsl', no, cls, value])
        previous[no] = (sec, dict.fromkeys(CLASSES, value))
        vsl_locations[no] = {**node.attrib, 'native_class_distribution_ids': native_ids}
    meter_schedules = {}
    for command in sorted(profile.get('meter_commands', []), key=lambda r: (r['time_s'], r['sc_no'])):
        sec = integer(command['time_s'], 'meter time')
        sc = integer(command['sc_no'], 'meter SC', 1)
        green = integer(command['green_sec'], 'green')
        if sec < start or sec >= end or sec % 150 or sc not in range(9101, 9109) or groups.get(sc) != [1] or ldp_groups.get(sc) != [1] or green > 10:
            raise ValueError('Invalid physical meter time/address/green')
        if profile.get('native_off_service_anchor_green_sec') != 10:
            raise ValueError('Explicit OFF service anchor10 required; it is not a GREEN observation')
        schedule = meter_schedules.setdefault(sc, [])
        last_sec, last_green = schedule[-1] if schedule else (-150, 10)
        if sec - last_sec < 150 or abs(green - last_green) > 2:
            raise ValueError('Meter exceeds actual-command2s/150s trust')
        schedule.append((sec, green))
    for sc, schedule in meter_schedules.items():
        current = None
        index = 0
        green = schedule[0][1]
        for sec in range(schedule[0][0], end):
            if index + 1 < len(schedule) and sec == schedule[index + 1][0]:
                index += 1
                green = schedule[index][1]
            state = 'GREEN' if sec % 10 < green else 'RED'
            if state != current:
                events.append([sec, 'meter', sc, 1, state])
                current = state
    events.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    proof = {'schema': SCHEMA, 'network_sha256': sha(network), 'seed': profile['seed'],
             'control_start_sec': start, 'terminal_sec': end, 'event_rows': len(events),
             'saved_simulation_period_sec': saved_period, 'effective_simulation_period_sec': effective_period,
             'simulation_period_policy': 'Preserve saved SimPeriod when beyond requested terminal; otherwise increase only to terminal+1; stop with SimBreakAt',
             'initial_rows': len(initial), 'signal_groups': groups, 'ldp_signal_groups': ldp_groups,
             'unrecorded_signal_groups': {sc: sorted(set(sgs) - set(ldp_groups.get(sc, []))) for sc, sgs in groups.items() if set(sgs) - set(ldp_groups.get(sc, []))},
             'vsl_locations': vsl_locations, 'speed_distributions': distributions, 'meter_schedules': meter_schedules,
             'native_off_service_anchor_green_sec': profile.get('native_off_service_anchor_green_sec'),
             'off_anchor_scope': 'OFF is retained in evidence;10 is a declared open-service trust anchor only, not observed GREEN or demonstrated equivalence',
             'event_clock': 'Write after native frame at time t; first affected LDP frame is t+1; RED/GREEN uses absolute time modulo10',
             'scope': 'Fixed-command causal diagnostic; no controller optimization, N_UF feasibility or GNE certification'}
    if resolution_probe is not None:
        proof['native_resolution_probe'] = resolution_probe
        proof['event_clock'] = 'No control writes; native resolution is a diagnostic scenario variable, not equivalent traffic'
    return events, initial, proof


def prepare(network, profile_path, output):
    network, profile_path, output = Path(network).resolve(), Path(profile_path).resolve(), Path(output).resolve()
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    events, initial, proof = compile_profile(network, profile)
    with redirect_stdout(io.StringIO()):
        prepare_native_preserve(network, output, profile['terminal_sec'])
    with (output/'native_simulation.csv').open('a', encoding='ascii', newline='') as stream:
        csv.writer(stream).writerow(['SimPeriod', proof['saved_simulation_period_sec']])
    for name, rows in [('fixed_events.csv', events), ('fixed_initial.csv', initial)]:
        with (output/name).open('x', encoding='ascii', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['time_s', 'kind', 'no', 'veh_class', 'value'])
            writer.writerows(rows)
    (output/'fixed_profile.json').write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding='utf-8')
    (output/'fixed_profile_proof.json').write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding='utf-8')
    path = output/'prepared.json'
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta.update(mode='fixed_profile', command_rows=len(events), control_start_sec=profile['control_start_sec'],
                saved_simulation_period_sec=proof['saved_simulation_period_sec'],
                effective_simulation_period_sec=proof['effective_simulation_period_sec'],
                traffic_settings_policy='Exact approved VSL/meter events only; zero demand/route/urban/seed/SimRes writes',
                profile_source={'path': str(profile_path), 'sha256': sha(profile_path)},
                fixed_profile_proof=proof)
    for name in ('fixed_events.csv', 'fixed_initial.csv', 'fixed_profile.json', 'fixed_profile_proof.json', 'native_simulation.csv'):
        meta['snapshot_sha256'][str(output/name)] = sha(output/name)
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return meta


def rule_step(prepared, output, sec):
    """Generate just the next interval's events using the canonical pure rules."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from evaluation.controllers.diagnostic_profile import alinea_meter_step, rule_vsl_speed
    prepared, output, sec = Path(prepared), Path(output), int(sec)
    cfg = json.loads((prepared/'rule_policy.json').read_text(encoding='utf-8'))
    meta = json.loads((prepared/'prepared.json').read_text(encoding='utf-8'))
    spec = cfg['rule']
    if sec < spec['control_start_sec'] or sec % 150 or sec >= meta['terminal_sec']:
        raise ValueError('Rule decision time outside complete controlled intervals')
    obs = list(csv.DictReader((output/f'observation_{sec}.csv').open(encoding='ascii')))
    by_id = {int(r['measurement']): r for r in obs}
    ids = {i for station in cfg['detectors']['stations'] for i in station['measurement_ids']}
    if len(by_id) != len(obs) or set(by_id) != ids:
        raise ValueError('Missing/duplicate detector lanes')
    observations = {}
    import math
    for station in cfg['detectors']['stations']:
        values = []
        for i in station['measurement_ids']:
            r = by_id[i]
            n, speed, occ = (float(r[k]) for k in ('vehicles', 'speed', 'occupancy'))
            if not all(math.isfinite(v) for v in (n, speed, occ)) or n < 0 or not 0 <= speed <= 300 or not 0 <= occ <= 1:
                raise ValueError('Invalid raw native detector measurement')
            values.append((n, speed, occ))
        count = sum(v[0] for v in values)
        observations[station['target']] = {'flow_vph_per_lane': count*24/len(values),
            'occupancy_pct': 100*sum(v[2] for v in values)/len(values),
            'speed_kph': sum(v[0]*v[1] for v in values)/count if count else 0}
    state_path = output/'rule_history.json'
    history = json.loads(state_path.read_text()) if state_path.exists() else {
        'sec': sec-150, 'greens': {m: 10 for m in cfg['meters']},
        'requests': {m: r['table']['10'] for m,r in cfg['meters'].items()},
        'vsl': {}, 'states': {}}
    if history['sec'] != sec-150:
        raise ValueError('Missing preceding applied decision')
    mpc=None
    if (prepared/'mpc_policy.json').exists():
        from diagnostics.demand_sweep.ramp_dsd_20260916_v2.evaluate_response import mpc_choice
        mpc=mpc_choice(prepared,output,sec,history,cfg)
    events, audit = [], {}
    stop = min(sec+150, meta['terminal_sec'])
    for mid, meter in cfg['meters'].items():
        params = {k: v[mid] if isinstance(v, dict) else v for k,v in spec['alinea'].items()}
        active = spec['arm'] in ('rm', 'both')
        green, request, raw, bounded = alinea_meter_step(meter['table'], history['greens'][mid],
            history['requests'][mid], params if active else None, observations[mid]['occupancy_pct'],
            cfg['minimum_green'], cfg['max_green_change'])
        if mpc is not None:
            green=mpc['greens'][mid]
            request=raw=bounded=meter['table'][str(green)]
            if abs(green-history['greens'][mid])>cfg['max_green_change']:
                raise ValueError('MPC meter exceeds actual-command trust region')
            # Native OFF remains until this meter first actually restricts flow.
            active=spec['arm'] in ('rm','both') and (green<10 or mid in history['states'])
        audit[mid] = {'green_sec': green, 'previous_green': history['greens'][mid],
            'raw_request_vph': raw, 'bounded_request_vph': bounded, 'next_request_vph': request}
        history['greens'][mid], history['requests'][mid] = green, request
        if active:
            for t in range(sec, stop):
                value = 'GREEN' if t % 10 < green else 'RED'
                if history['states'].get(mid) != value:
                    events.append([t, 'meter', meter['sc'], 1, value])
                    history['states'][mid] = value
    for station in cfg['detectors']['stations']:
        if station['role'] != 'vsl_zones': continue
        value = rule_vsl_speed(observations[station['target']], spec['vsl_rule']) if spec['arm'] in ('vsl','both') else spec['reference_speed_kph']
        if mpc is not None:value=mpc['zones'][station['target']]
        for no in cfg['zone_dsds'][station['target']]:
            if history['vsl'].get(str(no), spec['reference_speed_kph']) != value:
                for cls in CLASSES: events.append([sec, 'vsl', no, cls, value])
                history['vsl'][str(no)] = value
    events.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    with (output/'rule_events.csv').open('w', encoding='ascii', newline='') as f:
        writer=csv.writer(f); writer.writerow(['time_s','kind','no','veh_class','value']); writer.writerows(events)
    with (output/'fixed_events.csv').open('a', encoding='ascii', newline='') as f:
        writer=csv.writer(f)
        if f.tell()==0: writer.writerow(['time_s','kind','no','veh_class','value'])
        writer.writerows(events)
    history['sec'] = sec
    state_path.write_text(json.dumps(history), encoding='ascii')
    (output/f'decision_{sec}.json').write_text(json.dumps({'sec':sec, 'arm':spec['arm'],
        'observations':observations, 'meters':audit, 'history':history, 'events':events,
        **({'mpc':mpc} if mpc is not None else {})}, indent=2), encoding='ascii')


if __name__ == '__main__' and len(sys.argv) == 5 and sys.argv[1] == '--rule-step':
    try:
        rule_step(*sys.argv[2:])
    except Exception:
        import traceback
        (Path(sys.argv[3])/('decision_failure_'+sys.argv[4]+'.txt')).write_text(traceback.format_exc(),encoding='utf-8')
        raise
elif __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', required=True, type=Path)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.network, args.profile, args.output)
    print(json.dumps({'mode': result['mode'], 'network': result['network'], 'event_rows': result['command_rows']}))
