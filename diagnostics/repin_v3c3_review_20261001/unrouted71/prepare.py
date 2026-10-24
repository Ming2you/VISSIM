import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = HERE.parent / 'retained10638'

def read(p):
    return json.loads(p.read_bytes())

def save(p, obj):
    assert not p.exists(), p
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

prior = read(HERE.parent/'junction10643/completion.json')
for p,h in prior['production7_unchanged'].items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
for name in ('physical_urban_transport.py', 'lane_plant_runtime.py'):
    out = HERE/(name+'.before')
    assert not out.exists()
    out.write_bytes((ROOT/'evaluation/controllers'/name).read_bytes())
fit = read(HERE/'fit.json')
protocol = read(BASE/'local_protocol.json')
protocol['unrouted_71_balance'] = dict(rate_per_s=fit['coefficient_per_s'],
    estimator='past_route_free_pressure_exposure', source=(HERE/'fit.json').relative_to(ROOT).as_posix())
save(HERE/'local_protocol.json', protocol)
manifest = read(BASE/'candidate_manifest.json')
manifest['sources']['reference_protocol'] = dict(path=(HERE/'local_protocol.json').relative_to(ROOT).as_posix(),
    sha256=hashlib.sha256((HERE/'local_protocol.json').read_bytes()).hexdigest())
save(HERE/'candidate_manifest.json', manifest)
cfg = read(BASE/'candidate_config.json')
cfg['freeway']['lane_plant'] = (HERE/'candidate_manifest.json').relative_to(ROOT).as_posix()
save(HERE/'candidate_config.json', cfg)
for seed in (43,47):
    target=HERE/f'run{seed}.ps1'
    assert not target.exists()
    target.write_text((HERE.parent/'compatible71'/target.name).read_text(encoding='utf8').replace('compatible71','unrouted71'),encoding='utf8')
assessment=(HERE.parent/'compatible71/assess.py').read_text(encoding='utf8').replace('compatible71','unrouted71').replace('compatible_71_balance','unrouted_71_balance')
assessment=assessment.replace("exchange=lateral(local);assert exchange.get('4->5',0)>0", "exchange=lateral(local)")
target=HERE/'assess.py';assert not target.exists();target.write_text(assessment,encoding='utf8')
save(HERE/'protocol.json', dict(status='prepared_one_route_free_candidate',max_candidates=1,max_full_forecasts=6,
    source_pins=prior['production7_unchanged'],stop_sha256=prior['stop_sha256'],
    fit_sha256=hashlib.sha256((HERE/'fit.json').read_bytes()).hexdigest(),
    scope='Only current route-free continuation labels on71; shared old-state receiving advantage. No assigned route change, turn-share fitting or FD/capacity changes.',
    rationale='Conditional native arrivals did not solve underdrain; native route-free vehicles use side10642, model has no corresponding lane exchange.',
    fit_window=[2550.1,2695.1],forecast_start47=2700,heldout_seed=43,
    admission='Require material drain/storage improvement across conditions without new conservation failure or larger mainline/control-response degradation. Tiny cost signs alone are not the gate.',
    ad_compiled='Fail closed; candidate scalar-only until separate validation.',
    new_native=0,new_fzp_scan=0,coefficient_grids=0))
print('PREPARED one candidate, six autonomous forecasts; production backups exact')
