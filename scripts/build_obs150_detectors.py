"""obs150 detector generator (WP-B2, plan B1): the one detector table of the v2 network.

python -B scripts\\build_obs150_detectors.py [--tuning <config_n31_v2.json>] [--check]
       [--network ...] [--geometry ...] [--runner-config ...] [--plan ...]
       [--head-resource-contract ...] [--head-free-contract ...] [--sig-dir ...] [--out <csv>]

One tuning file decides every source (plan 1.1): its freeway.lane_plant manifest
gives the network and the geometry, execution.signal_vbs_config the runner config
(chain lists), urban.plan.actuation_plan_json the plan physical_groups reads, and
urban.capacity the head-resource and head-free contracts. The .sig files are the
byte copies next to the manifest's sig_manifest. An explicit option overrides
one source (used before the scenario copies existed).

Writes the canonical CSV (CONTRACT 7, obs150_contract.format_detector_csv) and,
next to it, its verification manifest <stem>.manifest.json: every source pin,
the per-role counts, the through-station placements and the list of assertions
that passed. The table itself is build_detector_rows of obs150_observation, the
same function load_context uses to re-derive the table from the pinned sources.

Assertions (plan B1): keys 960001.. unused in the network; lane and position on
the link; no connector outside the chain touches an offset segment; no bypass
pair (LPO:218-220); chain exits = 8 off connectors + 2 network ends and chain
entries = the 8 metered ramps (RW_FW_*_CHAIN_LINKS + inpx connectors); head set =
physical_groups (210 heads, 105 groups) and contains the contract heads (head
resource join, head-free 403 collector heads); every .sig program progNo has
whole-second times; every source station shares its point 1:1 with one RULE
measurement (910030-33 / 910045-47, the runner's rule_crosscheck); RD 1126
applies to all vehicle types; every off-ramp diverges inside its from_cell.
--check re-builds and compares bytes, writing nothing. The manifest records this
script by the sha256 of its LF text (sha256_lf), so a CRLF checkout still checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.controllers import obs150_contract as oc  # noqa: E402
from evaluation.controllers import obs150_observation as ob  # noqa: E402

N31D = 'diagnostics/sdmpc_n31_20260924'
DEFAULT_TUNING = N31D + '/config_n31_v2.json'
SOURCES = ('network', 'geometry', 'runner_config', 'plan', 'head_resource_contract', 'head_free_contract', 'sig_dir')
# The runtime network: v3b be0075bf since the 2026-09-25 re-pin (v2 f475ce42 before; the detector table is
# byte-identical on both, only the sidecar's source pins moved).
NETWORK_SHA256 = 'be0075bf4d5e9e239ffc1e9efb6d70d11c6ec6136e46f1a92d910bc79d813cdc'


def resolve_sources(args):
    """{source: path} from the tuning (and its plant manifest), explicit options first."""
    explicit = {key: getattr(args, key, None) for key in SOURCES}
    if all(explicit[key] for key in SOURCES if key != 'sig_dir'):
        tuning = plant = None
    else:
        if not args.tuning:
            raise oc.ObsContractError('--tuning is required unless every source is given explicitly')
        tuning = json.loads(ob.resolve_repo(args.tuning).read_text(encoding='utf-8-sig'))
        plant = json.loads(ob.resolve_repo(tuning['freeway']['lane_plant']).read_text(encoding='utf-8-sig'))
        oc.validate_tuning_v2(tuning, plant)
    derived = {} if tuning is None else {
        'network': plant['sources']['network']['path'],
        'geometry': plant['sources']['geometry']['path'],
        'runner_config': tuning['execution']['signal_vbs_config'],
        'plan': tuning['urban']['plan']['actuation_plan_json'],
        'head_resource_contract': tuning['urban']['capacity']['head_resource_contract'],
        'head_free_contract': tuning['urban']['capacity']['head_free_service'],
        'sig_dir': str(ob.resolve_repo(plant['sources']['sig_manifest']['path']).parent)}
    return {key: explicit[key] or derived.get(key) for key in SOURCES}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _text_sha_lf(path):
    """sha256 of a text file read with CRLF as LF. This script is committed as text
    (core.autocrlf=true checks it out CRLF); its record must not change with that."""
    return _sha(Path(path).read_bytes().replace(b'\r\n', b'\n'))


def _pin(path):
    data = Path(path).read_bytes()
    return {'path': ob.repo_path(path), 'sha256': _sha(data)}, data


def contract_head_checks(net, groups, resource, head_free):
    """The contract heads must be eligible exactly as their consumers compare them (HSR:57, SHO:303-323)."""
    checks = []
    for connector, row in sorted(resource['resources'].items()):
        key = tuple(row['group'].split('|'))
        if key not in groups:
            raise oc.ObsContractError(f'Head resource {connector}: group {row["group"]} is not a physical group')
        if groups[key] != row['heads']:
            raise oc.ObsContractError(f'Head resource {connector}: group {row["group"]} heads differ from physical_groups')
        checks.append(f'head resource {connector} group {row["group"]} = physical_groups')
    eligible = {h['head_id'] for members in groups.values() for h in members}
    for connector, row in sorted(head_free['resources'].items()):
        link = net.links[int(connector)]
        if ((link.from_link, link.to_link) != (int(row['source_link']), int(row['target_link']))
                or list(range(link.from_lane, link.from_lane + link.lanes)) != row['source_lanes']
                or link.from_pos_m != row['source_position_m']):
            raise oc.ObsContractError(f'Head-free connector {connector} geometry differs from its contract')
        source_heads = {h['head_id'] for h in net.heads if h['link'] == int(row['source_link'])}
        if not source_heads or not source_heads <= eligible:
            raise oc.ObsContractError(f'Head-free {connector}: collector heads on {row["source_link"]} are not all eligible')
        checks.append(f'head-free {connector}: collector heads {sorted(source_heads, key=int)} are eligible')
    return checks


def sig_checks(net, sig_dir):
    """Every native program progNo of the network has whole-second times (B4 reads them)."""
    from evaluation.controllers.obs150_signal_clock import sig_program_from_file
    files = {}
    for sc, controller in sorted(net.controllers.items(), key=lambda kv: int(kv[0])):
        name = controller['sig_file']
        if name is None:
            continue
        path = Path(sig_dir) / name
        sig_program_from_file(sc, path, controller['prog_no'])
        files[name] = _sha(path.read_bytes())
    return dict(sorted(files.items()))


def build(args):
    sources = resolve_sources(args)
    network_path = ob.resolve_repo(sources['network'])
    net = ob.InpxNetwork(network_path)
    if net.sha256 != NETWORK_SHA256:
        raise oc.ObsContractError('Network is not the runtime network v3b be0075bf: ' + str(network_path))
    geometry_pin, geometry_bytes = _pin(ob.resolve_repo(sources['geometry']))
    plan_pin, plan_bytes = _pin(ob.resolve_repo(sources['plan']))
    runner_pin, runner_bytes = _pin(ob.resolve_repo(sources['runner_config']))
    resource_pin, resource_bytes = _pin(ob.resolve_repo(sources['head_resource_contract']))
    free_pin, free_bytes = _pin(ob.resolve_repo(sources['head_free_contract']))
    plan = json.loads(plan_bytes.decode('utf-8'))
    rows, report = ob.build_detector_rows(net, json.loads(geometry_bytes.decode('utf-8-sig')), plan,
                                          ob.parse_runner_config(runner_bytes.decode('latin-1')))
    from evaluation.controllers.signal_head_observation import physical_groups
    groups = physical_groups(str(network_path), plan)
    contract = contract_head_checks(net, groups, json.loads(resource_bytes.decode('utf-8')),
                                    json.loads(free_bytes.decode('utf-8')))
    sig_dir = ob.resolve_repo(sources['sig_dir']) if sources['sig_dir'] else network_path.parent
    sig_files = sig_checks(net, sig_dir)
    csv_bytes = oc.format_detector_csv(rows)
    parsed = oc.parse_detector_csv(csv_bytes)            # canonical round trip
    if parsed != rows:
        raise oc.ObsContractError('Detector CSV does not round-trip')
    out = ob.resolve_repo(args.out)
    generator = Path(__file__).resolve()
    manifest = {
        'schema': ob.DETECTOR_BUILD_SCHEMA,
        'generator': {'path': ob.repo_path(generator), 'sha256_lf': _text_sha_lf(generator)},
        'network': {'path': ob.repo_path(network_path), 'sha256': net.sha256},
        'sources': {'geometry': geometry_pin, 'plan': plan_pin, 'runner_config': runner_pin,
                    'head_resource_contract': resource_pin, 'head_free_contract': free_pin,
                    'sig_dir': ob.repo_path(sig_dir), 'sig_files': sig_files},
        'output': {'path': ob.repo_path(out), 'sha256': _sha(csv_bytes), 'rows': len(rows)},
        'report': report,
        'contract_heads': contract,
        'sig_programs_whole_seconds': len(sig_files),
    }
    manifest_bytes = (json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=True) + '\n').encode('ascii')
    return out, csv_bytes, manifest_bytes, manifest


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Build the obs150 detector table of the v2 network (plan B1)')
    parser.add_argument('--tuning', default=DEFAULT_TUNING, help='the n31 tuning that decides every source')
    for key in SOURCES:
        parser.add_argument('--' + key.replace('_', '-'), default=None, help='override the tuning-derived ' + key)
    parser.add_argument('--out', default=ob.DETECTOR_CSV_PATH)
    parser.add_argument('--check', action='store_true', help='rebuild and compare bytes; write nothing')
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    out, csv_bytes, manifest_bytes, manifest = build(args)
    sidecar = Path(str(out)[:-len('.csv')] + ob.SIDECAR_SUFFIX)
    if args.check:
        if out.read_bytes() != csv_bytes or sidecar.read_bytes() != manifest_bytes:
            sys.stderr.write('OBS150_DETECTORS_DIFFER %s\n' % out)
            return 1
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        for path, data in ((out, csv_bytes), (sidecar, manifest_bytes)):
            temporary = path.with_name(path.name + '.tmp')
            temporary.write_bytes(data)
            temporary.replace(path)
    counts = ' '.join('%s=%d' % kv for kv in manifest['report']['counts'].items())
    sys.stdout.write('OBS150_DETECTORS_OK rows=%d sha256=%s %s\n' % (manifest['output']['rows'],
                                                                     manifest['output']['sha256'], counts))
    return 0


if __name__ == '__main__':
    sys.exit(main())
