r"""Copy the SDMPC-31 v2 network into one run folder (plan section 5 / V5 step 3; WP-E).

    python -B D:\VISSIM-merge\tools\prepare_sdmpc31_network.py --name <Name> --out-dir <run>\network
                                                             [--root <tree>] [--source <dir>] [--manifest <json>]
                                                             [--verify-only]

run_sdmpc_n31.ps1 calls this from the frozen tree FRZ (current directory), then checks the result itself with
launch_plan.py verify-network. What is copied, byte for byte, and nothing else:

    <out-dir>\sdmpc31_<Name>.inpx      the pinned .inpx (the file name puts 'sdmpc' in the VISSIM window title,
                                       which the stage-1 seat guard counts as the dev seat)
    <out-dir>\<42 .sig>                the supply files the .inpx references (#data# resolves to the .inpx folder)
    <out-dir>\sdmpc31_network_copy.json  receipt (launch_plan allows .json beside the network)

Not copied: *.err and *.results (run outputs; a stale .err would corrupt the obs150 .err capture) and the
#data# background image (graphics only). The source is <root>\diagnostics\sdmpc_n31_20260924\network, the
pinned copy of D:\VISSIM_runs\20260923_stage1\s31_v2nc\prepared\network made by repin_scenario_v2.py. Every
byte is checked against a sig_manifest.json (the .inpx sha and each .sig sha), <source>\sig_manifest.json unless
--manifest names another, and the .inpx supplyFile2 set must equal the manifest set. --source may name another
folder with the same bytes; the NET folder itself has no sig_manifest.json, so copying from it takes
--source <NET> --manifest <root>\diagnostics\sdmpc_n31_20260924\network\sig_manifest.json.
The target folder must be absent or empty. The receipt records this tool's sha256 (the tool lives outside git
and outside the frozen tree).

stdout: exactly one line, NETWORK_COPY_OK ... or NETWORK_COPY_ERROR <reason>. Exit 0 ok, 1 refused.
--verify-only checks an existing folder the same way and copies nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NETWORK_REL = Path('diagnostics') / 'sdmpc_n31_20260924' / 'network'
MANIFEST_NAME = 'sig_manifest.json'
MANIFEST_SCHEMA = 'sdmpc31-sig-manifest/v1'
RECEIPT_NAME = 'sdmpc31_network_copy.json'
RECEIPT_SCHEMA = 'sdmpc31-network-copy/v1'
NETWORK_PREFIX = 'sdmpc31_'                           # launch_plan.py / n31_common.NETWORK_PREFIX
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')   # launch_plan.py NAME_RE
SIG_COUNT = 42                                        # NEW-1: the v2 network references 42 .sig files


class CopyError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise CopyError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def bare_name(name, suffix):
    """A plain file name in the folder: no directory part and no drive (C:x would leave the folder)."""
    return (isinstance(name, str) and name.lower().endswith(suffix) and len(name) > len(suffix)
            and not any(c in name for c in '/\\:'))


def load_manifest(source, manifest_path=None):
    path = Path(manifest_path) if manifest_path else source / MANIFEST_NAME
    require(path.is_file(), f'sig manifest missing: {path}')
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    # Shape checks first, so a malformed manifest ends in the one NETWORK_COPY_ERROR line, not a traceback.
    require(isinstance(manifest, dict), 'sig manifest is not a JSON object')
    require(manifest.get('schema') == MANIFEST_SCHEMA, f'sig manifest schema is not {MANIFEST_SCHEMA}')
    network = manifest.get('network') or {}
    require(isinstance(network, dict), 'sig manifest network entry is not an object')
    require(bare_name(network.get('name'), '.inpx')
            and re.fullmatch(r'[0-9a-f]{64}', str(network.get('sha256'))) is not None,
            f'sig manifest network entry {network.get("name")!r}')
    files = manifest.get('files') or []
    require(isinstance(files, list), 'sig manifest files is not a list of rows')
    table = {}
    for row in files:
        require(isinstance(row, dict), f'sig manifest row is not an object: {row!r}')
        name, sha = row.get('name'), row.get('sha256')
        require(bare_name(name, '.sig'), f'sig manifest row name {name!r}')
        require(isinstance(sha, str) and re.fullmatch(r'[0-9a-f]{64}', sha) is not None, f'sig manifest sha for {name}')
        require(name not in table, f'sig manifest lists {name} twice')
        table[name] = sha
    return manifest, path, sha256_file(path), network, dict(sorted(table.items()))


def supply_files(inpx):
    """The .sig names the network's signal controllers load (#data# = the .inpx folder)."""
    names = set()
    for sc in ET.parse(inpx).getroot().findall('./signalControllers/signalController'):
        value = sc.get('supplyFile2', '')
        if not value:
            continue
        require(value.startswith('#data#') and '/' not in value and '\\' not in value,
                f'SC {sc.get("no")} supply file is not a #data# sibling: {value}')
        names.add(value[len('#data#'):])
    return names


def check_folder(folder, inpx_name, network, table):
    """The folder holds exactly the .inpx and the manifest .sig files (plus the receipt), all pinned bytes."""
    present = sorted(p.name for p in folder.iterdir())
    expected = sorted([inpx_name, *table])
    extra = sorted(set(present) - set(expected) - {RECEIPT_NAME})
    missing = sorted(set(expected) - set(present))
    require(not extra and not missing, f'{folder} holds unexpected {extra} / lacks {missing}')
    require(sha256_file(folder / inpx_name) == network['sha256'], f'{inpx_name} differs from the pinned network')
    for name, sha in table.items():
        require(sha256_file(folder / name) == sha, f'{name} differs from sig_manifest')
    referenced = supply_files(folder / inpx_name)
    require(referenced == set(table), f'.inpx references {sorted(referenced - set(table))} beyond the manifest, '
                                      f'manifest lists {sorted(set(table) - referenced)} it does not use')


def copy_network(name, out_dir, source, *, expected_sig_count=SIG_COUNT, manifest_path=None):
    require(NAME_RE.match(name) is not None, f'run name must match {NAME_RE.pattern}: {name!r}')
    source = Path(source)
    out_dir = Path(out_dir)
    _, manifest_file, manifest_sha, network, table = load_manifest(source, manifest_path)
    require(len(table) == expected_sig_count, f'sig manifest lists {len(table)} .sig files, expected {expected_sig_count}')
    source_inpx = source / network['name']
    require(source_inpx.is_file(), f'source network missing: {source_inpx}')
    require(sha256_file(source_inpx) == network['sha256'], f'source {network["name"]} differs from sig_manifest')
    for sig, sha in table.items():
        require((source / sig).is_file() and sha256_file(source / sig) == sha, f'source {sig} missing or differs')
    referenced = supply_files(source_inpx)
    require(referenced == set(table), f'source .inpx references {sorted(referenced - set(table))} beyond the manifest, '
                                      f'manifest lists {sorted(set(table) - referenced)} it does not use')
    require(not out_dir.exists() or (out_dir.is_dir() and not any(out_dir.iterdir())),
            f'target folder is not empty (a run folder is never reused): {out_dir}')
    out_dir.mkdir(parents=True, exist_ok=True)
    inpx_name = f'{NETWORK_PREFIX}{name}.inpx'
    for src, dst in [(source_inpx, out_dir / inpx_name)] + [(source / sig, out_dir / sig) for sig in table]:
        part = dst.with_name(dst.name + '.part')
        with open(src, 'rb') as reader, open(part, 'wb') as writer:
            for block in iter(lambda: reader.read(1 << 20), b''):
                writer.write(block)
        os.replace(part, dst)
    check_folder(out_dir, inpx_name, network, table)
    receipt = {
        'schema': RECEIPT_SCHEMA, 'name': name,
        'inpx': {'name': inpx_name, 'sha256': network['sha256'], 'bytes': (out_dir / inpx_name).stat().st_size,
                 'source_name': network['name']},
        'source': {'folder': str(source.resolve()), 'sig_manifest': str(manifest_file.resolve()),
                   'sig_manifest_sha256': manifest_sha},
        'sig': [{'name': sig, 'sha256': sha} for sig, sha in table.items()],
        'not_copied': 'run outputs (*.err, *.results) and the #data# background image',
        'tool': str(Path(__file__).resolve()),
        'tool_sha256': sha256_file(Path(__file__).resolve()),
    }
    (out_dir / RECEIPT_NAME).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n', encoding='utf-8',
                                        newline='\n')
    return out_dir / inpx_name, network['sha256'], len(table)


def verify_network(name, out_dir, source, *, expected_sig_count=SIG_COUNT, manifest_path=None):
    require(NAME_RE.match(name) is not None, f'run name must match {NAME_RE.pattern}: {name!r}')
    _, _, _, network, table = load_manifest(Path(source), manifest_path)
    require(len(table) == expected_sig_count, f'sig manifest lists {len(table)} .sig files, expected {expected_sig_count}')
    out_dir = Path(out_dir)
    require(out_dir.is_dir(), f'network folder missing: {out_dir}')
    inpx_name = f'{NETWORK_PREFIX}{name}.inpx'
    check_folder(out_dir, inpx_name, network, table)
    return out_dir / inpx_name, network['sha256'], len(table)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Copy the SDMPC-31 v2 network (.inpx + 42 .sig) into a run folder.')
    parser.add_argument('--name', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--root', default=None, help='tree holding diagnostics/sdmpc_n31_20260924/network (default: cwd)')
    parser.add_argument('--source', default=None, help='folder with the .inpx and the .sig files (and sig_manifest.json)')
    parser.add_argument('--manifest', default=None, help='sig_manifest.json to check against (default: <source>/sig_manifest.json)')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.source:
            source = Path(args.source)
        else:
            root = Path(args.root) if args.root else Path.cwd()
            source = root / NETWORK_REL
            require(source.is_dir(), f'{source} missing: run from the frozen tree (FRZ) or pass --root/--source')
        action = verify_network if args.verify_only else copy_network
        inpx, sha, count = action(args.name, args.out_dir, source, manifest_path=args.manifest)
        print(f'NETWORK_COPY_OK inpx={inpx} sha256={sha} sig={count} verify_only={int(args.verify_only)}')
        return 0
    except (CopyError, OSError, ET.ParseError, ValueError) as error:
        print(f'NETWORK_COPY_ERROR {error}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
