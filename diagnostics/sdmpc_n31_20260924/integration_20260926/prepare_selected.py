"""Relocate the user-selected gain-network inputs; never copy executable code.

Original inputs in sd31 and upstream v3b remain untouched. This is an offline
comparison baseline, not a gain-qualified/native-launch configuration.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT.parent / 'sd31'
PREFIX = 'diagnostics/sdmpc_n31_20260924'
DEST = HERE / 'selected'
NETWORK_SHA = '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    old = SOURCE / PREFIX
    files = [old / name for name in ('config_n31_v2.json', 'plant_n31_v2.json',
             'reference_config_n31_v2.json', 'obs150/obs150_detectors_v2.csv',
             'obs150/obs150_detectors_v2.manifest.json')]
    files += [p for p in (old / 'network').iterdir()
              if p.name in ('native_seed29.inpx', 'sig_manifest.json') or p.suffix == '.sig']
    files += [p for p in (old / 'scenario').iterdir() if p.is_file()]
    files += [old / 'port_gain' / name for name in
              ('candidate.json', 'geometry.json', 'parameters.json', 'segment_params.json',
               'port_profile.json', 'freeze.json')]
    assert sha((old / 'network/native_seed29.inpx').read_bytes()) == NETWORK_SHA
    targets = {p: DEST / p.relative_to(old) for p in files}
    mapping = {p.relative_to(SOURCE).as_posix(): q.relative_to(ROOT).as_posix()
               for p, q in targets.items()}
    mapping.update({p.as_posix(): q.relative_to(ROOT).as_posix() for p, q in targets.items()})
    # Archived geometry names the same bytes in the handoff copy.
    alias = SOURCE / 'diagnostics/vsl_handoff_20260924/network/native_seed29.inpx'
    assert sha(alias.read_bytes()) == NETWORK_SHA
    mapping[alias.as_posix()] = mapping[PREFIX + '/network/native_seed29.inpx']

    def relocate(value):
        if isinstance(value, dict):
            return {mapping.get(k.replace('\\', '/'), k): relocate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [relocate(v) for v in value]
        if isinstance(value, str):
            return mapping.get(value.replace('\\', '/'), value)
        return value

    docs, payload, original, unchanged_bytes, unchanged_docs = {}, {}, {}, {}, {}
    for src, dst in targets.items():
        raw = src.read_bytes()
        original[dst] = {'source': src.relative_to(SOURCE).as_posix(), 'sha256': sha(raw)}
        if src.suffix == '.json':
            unchanged_bytes[dst] = raw
            unchanged_docs[dst] = json.loads(raw)
            docs[dst] = relocate(unchanged_docs[dst])
        else:
            payload[dst] = raw

    # Recompute relocated pins from their actual new bytes, including transitive
    # scenario pins. Cycles/nonconvergence fail rather than leaving stale hashes.
    def encode():
        for dst, doc in docs.items():
            payload[dst] = (unchanged_bytes[dst] if doc == unchanged_docs[dst] else
                            (json.dumps(doc, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))

    def repin(value):
        changed = False
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
                target = ROOT / value['path']
                if target in payload and value['sha256'] != sha(payload[target]):
                    value['sha256'] = sha(payload[target])
                    changed = True
            for child in value.values():
                changed |= repin(child)
        elif isinstance(value, list):
            for child in value:
                changed |= repin(child)
        return changed

    for _ in range(20):
        encode()
        changed = [repin(doc) for doc in docs.values()]
        if not any(changed):
            break
    else:
        raise ValueError('Selected source pins did not converge')
    for path, data in payload.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_bytes() != data:
            path.write_bytes(data)
    freeze = docs[DEST / 'port_gain/freeze.json']
    assert freeze['parameters_sha256'] == sha(payload[DEST / 'port_gain/parameters.json'])
    for rel, digest in freeze['code_pins'].items():
        assert sha((ROOT / rel).read_bytes()) == digest, rel
    receipt = {'selection': 1, 'network_sha256': NETWORK_SHA,
               'qualification': 'NOT_QUALIFIED', 'runner_or_adapter_copied': False,
               'scenario_vbs_declarations_copied': True,
               'native_started': False,
               'known_pending': ['legacy four-group ramp-arrival forecast must be calibrated on selected NC data',
                                 'historical urban beta priors remain priors, not current route truth',
                                 'physical response and full waiting-inclusive net gain remain unqualified'],
               'files': {p.relative_to(ROOT).as_posix(): dict(original[p], target_sha256=sha(data))
                         for p, data in payload.items()}}
    (HERE / 'selected_receipt.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('SELECTED_INPUTS_STAGED', len(payload), 'network', NETWORK_SHA)


if __name__ == '__main__':
    main()
