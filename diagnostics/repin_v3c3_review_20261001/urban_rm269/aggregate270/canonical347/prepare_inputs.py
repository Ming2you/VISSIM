"""Pin the current runtime for a fresh paired experiment; no prediction."""
from pathlib import Path
import hashlib,json,pickle,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
old=HERE.parent/'worker334/capture_v2'
summary=json.loads((old/'summary.json').read_bytes())
raw=(old/'request.pickle').read_bytes()
assert hashlib.sha256(raw).hexdigest()==summary['request_sha256']
request=pickle.loads(raw)
pins={};changes=[]
for p,h in {**summary['source_pins'],**request['bootstrap']['runtime_sources']}.items():
    current=hashlib.sha256(Path(p).read_bytes()).hexdigest()
    if Path(p).suffix!='.py':assert h==current,p
    if h!=current:changes.append(dict(path=p,old=h,current=current))
    pins[p]=current
for p in HERE.glob('*.py'):pins[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf8')
(out/'preparation.json').write_text(json.dumps(dict(request_sha256=summary['request_sha256'],
    runtime_source_count=len(request['bootstrap']['runtime_sources']),changed_since334=changes,
    earlier_attempt='../legacy_scalar/completion.json',earlier_failure='Manifest missed external config; no prediction ran.',
    maximum_predictions=4,full_optimizer=0,native=0,fits=0,goal_complete=False),indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(pins=len(pins),changed=len(changes),runtime_sources=len(request['bootstrap']['runtime_sources']))))

