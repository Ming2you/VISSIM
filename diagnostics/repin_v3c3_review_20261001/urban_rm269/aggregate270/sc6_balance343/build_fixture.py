"""Capture the real pre-topology contract installation point, no forecast."""
import importlib.util,json,pickle,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;A=HERE.parent
def main():
    out=HERE/'configure_fixture';assert not out.exists()
    source=json.loads((A/'transfer331/build2400_v2/summary.json').read_bytes())['source']
    sys.argv=['verify.py','--at','2400','--out',str(out),'--no-prediction','--cold-prices',
        '--tuning',str(A/'flow279/config_10686_free.json'),'--decisions',source]
    spec=importlib.util.spec_from_file_location('head343_fixture',A.parents[1]/'urban260/verify.py')
    v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
    from evaluation.controllers import head_service_resources as h
    old=h.configure
    def capture(cfg,tuning,raw,plan):
        blob=pickle.dumps((cfg,tuning,raw,plan),protocol=5)
        old(cfg,tuning,raw,plan)
        (out/'fixture.pickle').write_bytes(blob)
        raise v.Done()
    h.configure=capture
    v.main()
    assert (out/'fixture.pickle').exists()
if __name__=='__main__':main()
