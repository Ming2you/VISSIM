"""Explicit portable inputs for the stopped1350 route/input regressions."""
import os
from pathlib import Path
from diagnostics.review_fixtures import ROOT

ENVIRONMENT = 'VISSIM_ROUTE_INPUT_FIXTURE_ROOT'
ARCHIVE = ROOT/'diagnostics/fixtures/route_input_v1.zip'
RUN = 'codex_area_beta0_retry_s13_20260910'
ORIGINAL_FOLDER = ROOT/'evaluation/runs'/RUN/('decisions_'+RUN)
BASELINE = ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json'


def fixture_path(path, *, raw=False):
    """Use verified restored inputs when enabled; missing records never fall back."""
    path = Path(path)
    location = os.environ.get(ENVIRONMENT)
    if not location:
        return path
    destination = Path(location).resolve()
    if not (destination/'restoration.json').is_file():
        raise FileNotFoundError(f'{ENVIRONMENT} requires verified restored fixtures')
    if path.is_relative_to(destination):
        return path
    relative = path.relative_to(ROOT)
    if relative.parts[:2] != ('evaluation', 'runs'):
        return path
    result = destination/('raw' if raw else 'relocated')/relative
    if not result.exists():
        raise FileNotFoundError(f'Route/input regression input is absent: {relative}')
    return result


def decisions():
    return fixture_path(ORIGINAL_FOLDER)
