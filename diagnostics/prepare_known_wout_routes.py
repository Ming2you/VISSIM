"""Compatibility imports for the now-canonical known W-out route model.

Historical proposal and patch evidence remain immutable. No runtime overlay or
source rewriting is installed by this module.
"""
from contextlib import contextmanager
import argparse
import hashlib
import json
from diagnostics.probe_model_area_integration import ROOT

ROUTE=ROOT/'evaluation/controllers/route_choice_corridor.py'
URBAN=ROOT/'evaluation/controllers/urban_flow_accounting.py'
RUNTIME=ROOT/'evaluation/controllers/runtime_setup.py'


def replace_once(text,old,new):
    if text.count(old)!=1: raise ValueError('Expected one source hook: '+old[:90])
    return text.replace(old,new,1)


def sources():
    return {path:path.read_text(encoding='utf-8') for path in (ROUTE,URBAN,RUNTIME)}


@contextmanager
def installed():
    from evaluation.controllers import route_choice_corridor as route
    if not hasattr(route,'configure_known_legsplit'):
        raise RuntimeError('Canonical known W-out route implementation is required')
    yield route


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-patch',action='store_true',help='Deprecated: canonical implementation already landed')
    args=parser.parse_args()
    if args.refresh_patch:
        parser.error('Implementation is canonical; historical proposal/patch evidence must not be overwritten')
    with installed():
        print(json.dumps({'production_applied':True,'runtime_overlay':False,
            'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources()}},indent=2))


if __name__=='__main__':main()
