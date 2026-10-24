"""Compile a pinned native command diagnostic; no COM/model/controller imports."""
import argparse
from contextlib import redirect_stdout
import csv
import hashlib
import io
import json
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
    if int(simulation.get('simRes')) != 1:
        raise ValueError('Fixed profile requires saved SimRes1')
    start = integer(profile['control_start_sec'], 'control start', 150)
    end = integer(profile['terminal_sec'], 'terminal', 1)
    if start % 150 or end not in (1800, 2250, 5400, 7200, 9000) or start >= end:
        raise ValueError('Fixed profile start/horizon is unsupported')
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
             'initial_rows': len(initial), 'signal_groups': groups, 'ldp_signal_groups': ldp_groups,
             'unrecorded_signal_groups': {sc: sorted(set(sgs) - set(ldp_groups.get(sc, []))) for sc, sgs in groups.items() if set(sgs) - set(ldp_groups.get(sc, []))},
             'vsl_locations': vsl_locations, 'speed_distributions': distributions, 'meter_schedules': meter_schedules,
             'native_off_service_anchor_green_sec': profile.get('native_off_service_anchor_green_sec'),
             'off_anchor_scope': 'OFF is retained in evidence;10 is a declared open-service trust anchor only, not observed GREEN or demonstrated equivalence',
             'event_clock': 'Write after native frame at time t; first affected LDP frame is t+1; RED/GREEN uses absolute time modulo10',
             'scope': 'Fixed-command causal diagnostic; no controller optimization, N_UF feasibility or GNE certification'}
    return events, initial, proof


def prepare(network, profile_path, output):
    network, profile_path, output = Path(network).resolve(), Path(profile_path).resolve(), Path(output).resolve()
    profile = json.loads(profile_path.read_text(encoding='utf-8-sig'))
    events, initial, proof = compile_profile(network, profile)
    with redirect_stdout(io.StringIO()):
        prepare_native_preserve(network, output, profile['terminal_sec'])
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
                traffic_settings_policy='Exact approved VSL/meter events only; zero demand/route/urban/seed/SimRes writes',
                profile_source={'path': str(profile_path), 'sha256': sha(profile_path)},
                fixed_profile_proof=proof)
    for name in ('fixed_events.csv', 'fixed_initial.csv', 'fixed_profile.json', 'fixed_profile_proof.json', 'native_simulation.csv'):
        meta['snapshot_sha256'][str(output/name)] = sha(output/name)
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    return meta


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', required=True, type=Path)
    parser.add_argument('--profile', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = prepare(args.network, args.profile, args.output)
    print(json.dumps({'mode': result['mode'], 'network': result['network'], 'event_rows': result['command_rows']}))
