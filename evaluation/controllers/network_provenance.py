"""Read the network fingerprint actually attached to a VISSIM snapshot."""
import json
from pathlib import Path


def snapshot_network_sha256(state_json):
    provenance = state_json.get('run_provenance') or {}
    if provenance.get('manifest_path'):
        manifest = json.loads(Path(provenance['manifest_path']).read_text(encoding='utf-8-sig'))
        if not provenance.get('run_id') or manifest.get('run_id') != provenance['run_id']:
            raise ValueError('Snapshot and provenance manifest run IDs differ')
        provenance = manifest
    value = ((provenance.get('files') or {}).get('network') or {}).get('sha256')
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError('Snapshot lacks a valid network fingerprint')
    return value
