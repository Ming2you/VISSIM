"""One fresh2700 diagnostic; canonical observer, action and physical checks."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys

HERE=Path(__file__).resolve().parent;H=HERE.parent;ROOT=HERE.parents[3]
read=lambda p:json.loads(p.read_bytes())


def main():
    for p,digest in read(HERE/'plan.json')['source_pins'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest,p
    assert read(HERE/'preflight.json')['status']=='passed'
    sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
    os.environ.update(NUMSIM_REPO_ROOT=str(ROOT/'vendor/NumSim-mine'),PYTHONDONTWRITEBYTECODE='1')
    loader=importlib.util.spec_from_file_location('canonical_fresh2700',H/'recovery2700/forecast.py')
    m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m);m.OUT=HERE/'forecast2700'
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.lateral_turnover.candidate import install
    install();m.main()


if __name__=='__main__':main()
