"""Bounded turnover diagnostic with current-source lane conservation as well."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())
ap=argparse.ArgumentParser();ap.add_argument('--at',type=int,choices=(2400,2700,3300),required=True)
args=ap.parse_args()


def main():
    for p,digest in read(HERE/'plan.json')['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
    assert read(HERE/'preflight.json')['status']=='passed'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    source=H/('recovery2700/forecast.py' if args.at==2700 else 'connector_lane/forecast.py')
    if args.at!=2700:sys.argv=['forecast.py','--at',str(args.at)]
    loader=importlib.util.spec_from_file_location('canonical_fixed',source)
    m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
    m.OUT=HERE/f'forecast{args.at}'
    if args.at!=2700:
        m.HERE=HERE;m.tuning=H/'connector_lane/config.json';m.args.variant='turnover_current_lane'
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import install
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lane_transfer_binding.probe import install as bind
    install();rows=bind();m.main()
    assert rows and all('ramp_lane_admission' in row for row in rows)
    (HERE/f'lane_trace{args.at}.json').write_text(json.dumps(dict(rows=rows,production_changes=False),
        indent=2,allow_nan=False)+'\n',encoding='utf8')


if __name__=='__main__':main()
