"""Local receiving-law checks; not a full SDMPC derivative qualification."""
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
backend = sys.argv[1] if len(sys.argv) > 1 else None
if backend:
    from evaluation.controllers import sdmpc_tangent_runtime
    finder = sdmpc_tangent_runtime.install(ROOT, backend)
from evaluation.controllers.physical_ramp_boundary import origin_density_supply_vph as supply

assert supply(0., 40., 180., 1800.) == 1800.
assert supply(40., 40., 180., 1800.) == 1800.
assert supply(110., 40., 180., 1800.) == 900.
assert supply(180., 40., 180., 1800.) == 0.
assert supply(190., 40., 180., 1800.) == 0.
for args in ((math.nan,40,180,1800),(-1,40,180,1800),(50,180,180,1800),
             (50,40,180,-1),(True,40,180,1800)):
    try:
        supply(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(args)
checks = []
if backend:
    ad = finder.ad
    for rho, expected in ((20.,0.), (110.,-1800./140.), (190.,0.)):
        trace = ad.Trace([.001], track_stencils=False)
        value = supply(ad.Dual(rho, {0:1.}, trace),40.,180.,1800.)
        gradient = (float(trace.jacobian([value],1)[0,0]) if backend == 'reverse-v1'
                    else ad.derivative(value).get(0,0.))
        fd = (supply(rho+.001,40.,180.,1800.)-supply(rho-.001,40.,180.,1800.))/.002
        assert abs(gradient-expected)<1e-9 and abs(gradient-fd)<1e-7
        assert ad.primal(value)==supply(rho,40.,180.,1800.)
        checks.append(dict(density=rho,gradient=gradient,finite_difference=fd))
print(json.dumps(dict(passed=True,backend=backend,checks=checks,
                      full_rollout_ad_qualified=False)))
