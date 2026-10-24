"""Portable current-route replay inputs; no fallback to the ignored run."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4
from diagnostics.review_fixtures import ROOT, restore
from diagnostics.build_known_wout_fixture_archive import ARCHIVE, RUN

ENVIRONMENT = 'VISSIM_KNOWN_WOUT_FIXTURE_ROOT'
INPUTS = {'state_001200.json', 'state_003300.json', 'action_001050.json',
          'action_001200.json', 'action_003150.json', 'action_003300.json'}


@lru_cache(maxsize=None)
def _root(setting):
    destination = Path(setting).resolve() if setting else ROOT/'.review-fixtures'/('kw_'+uuid4().hex[:8])
    if not destination.is_relative_to((ROOT/'.review-fixtures').resolve()):
        raise ValueError('Known-route fixtures must stay under this checkout .review-fixtures')
    if not setting:
        restore(destination, archive=ARCHIVE)
    record = json.loads((destination/'restoration.json').read_text(encoding='utf-8'))
    if record['archive_sha256'] != hashlib.sha256(ARCHIVE.read_bytes()).hexdigest():
        raise ValueError('Known-route restoration belongs to another archive')
    for row in record['raw_files']:
        raw = (destination/'raw'/row['path']).read_bytes()
        moved = (destination/'relocated'/row['path']).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Known-route raw fingerprint changed: '+row['path'])
        if hashlib.sha256(moved).hexdigest() != record['relocated_sha256'][row['path']]:
            raise ValueError('Known-route relocated fingerprint changed: '+row['path'])
    return destination


def input_path(name):
    if name not in INPUTS:
        raise ValueError('Unknown known-route fixture input: '+str(name))
    return _root(os.environ.get(ENVIRONMENT, ''))/'relocated/evaluation/runs'/RUN/('decisions_'+RUN)/name
