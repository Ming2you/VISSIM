"""Always use archived shared-service inputs, never the ignored original run."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore

ARCHIVE = ROOT/'diagnostics/fixtures/shared_service_v1.zip'
ENVIRONMENT = 'VISSIM_SHARED_SERVICE_FIXTURE_ROOT'
RUN = 'codex_area_sources_beta0_s13_20260910'
DECISIONS = Path('evaluation/runs')/RUN/('decisions_'+RUN)
INPUTS = ('state_000900.json', 'action_000750.json', 'action_000900.json')


@lru_cache(maxsize=None)
def _root(setting):
    destination = Path(setting).resolve() if setting else ROOT/'.review-fixtures'/('sp_'+uuid4().hex[:8])
    if not destination.is_relative_to((ROOT/'.review-fixtures').resolve()):
        raise ValueError('Shared fixtures must stay under this checkout .review-fixtures')
    if not setting:
        restore(destination, archive=ARCHIVE)
    marker = destination/'restoration.json'
    if not marker.is_file():
        raise FileNotFoundError('Shared fixture root was not restored: '+str(destination))
    record = json.loads(marker.read_text(encoding='utf-8'))
    if record['archive_sha256'] != hashlib.sha256(ARCHIVE.read_bytes()).hexdigest():
        raise ValueError('Shared fixture restoration belongs to a different archive')
    # Existing restore records each whole-path relocation. Validate its exact
    # products once per root; traffic values and raw originals stay untouched.
    for row in record['raw_files']:
        raw = (destination/'raw'/row['path']).read_bytes()
        moved = (destination/'relocated'/row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Shared fixture raw fingerprint changed: '+row['path'])
        if hashlib.sha256(moved).hexdigest() != record['relocated_sha256'][row['path']]:
            raise ValueError('Shared fixture relocated fingerprint changed: '+row['path'])
    return destination


def input_path(name):
    if name not in INPUTS:
        raise ValueError('Unknown shared-service fixture input: '+str(name))
    path = _root(os.environ.get(ENVIRONMENT, ''))/'relocated'/DECISIONS/name
    if not path.is_file():
        raise FileNotFoundError('Shared-service fixture input missing: '+str(path))
    return path
