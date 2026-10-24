"""Always use the exact archived head windows; never an original-run fallback."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore

ARCHIVE = ROOT/'diagnostics/fixtures/head_service_resource_v2.zip'
ENVIRONMENT = 'VISSIM_HEAD_SERVICE_RESOURCE_FIXTURE_ROOT'
RUN = 'codex_contract_observed_nc_s13_1050_v2_20260910'
DECISIONS = Path('evaluation/runs')/RUN/('decisions_'+RUN)
CONFIG = Path('diagnostics/contract_candidate_configs_v2/n7_area_beta0.json')


@lru_cache(maxsize=None)
def _root(setting):
    destination = Path(setting).resolve() if setting else ROOT/'.review-fixtures'/('head_'+uuid4().hex[:8])
    if not destination.is_relative_to((ROOT/'.review-fixtures').resolve()):
        raise ValueError('Head fixtures must stay under .review-fixtures')
    if not setting:
        restore(destination, archive=ARCHIVE)
    record = json.loads((destination/'restoration.json').read_text(encoding='utf-8'))
    if record['archive_sha256'] != hashlib.sha256(ARCHIVE.read_bytes()).hexdigest():
        raise ValueError('Head fixture restoration belongs to another archive')
    for row in record['raw_files']:
        raw = (destination/'raw'/row['path']).read_bytes()
        moved = (destination/'relocated'/row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Head fixture raw fingerprint changed')
        if hashlib.sha256(moved).hexdigest() != record['relocated_sha256'][row['path']]:
            raise ValueError('Head fixture relocated fingerprint changed')
    return destination


def fixture_path(relative):
    relative = Path(relative)
    destination = _root(os.environ.get(ENVIRONMENT, ''))
    record = json.loads((destination/'restoration.json').read_text(encoding='utf-8'))
    if relative.as_posix() not in record['relocated_sha256']:
        raise FileNotFoundError('File is absent from head fixture: '+str(relative))
    return destination/'relocated'/relative


def input_path(name):
    return fixture_path(DECISIONS/name)
