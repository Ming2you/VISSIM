"""AD of future commands from a fixed observed-history posterior; no VISSIM or fitting."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from evaluation.controllers import sdmpc_tangent_runtime

finder = sdmpc_tangent_runtime.install(ROOT,sys.argv[1] if len(sys.argv)>1 else 'forward')
ad = finder.ad
from evaluation.controllers.freeway_fd import VSLExposure
from evaluation.controllers.vsl_exposure_history import assimilate

law = dict(law='carlson', A=.5, E=4., alpha=0.)
cfg = NS(network=NS(freeway_segment_params={'FW_E': [dict(v_free=110., rho_crit=30., metanet_a_m=2.)]*2},
                   v_free=110., rho_crit=30., rho_max=150., metanet_a_m=2., alpha_vsl=0., freeway_vsl_fd_response={'FW_E': law}),
         freeway_follower=NS(vsl_set=[50., 60., 70., 80., 90., 100., 110.]))


prior = VSLExposure([10., 10.], dict(sign_cells=[0], initial_command=110., ramp_command=110.), 110.)
posterior = assimilate(prior, [10.,10.], [10.,10.], 4., [0.,0.], [0.,0.], [0.,0.], 4., [90.,None], 150., 1.)
assert all(value == 0. for row in posterior.tangents for value in row.values())
assert posterior.cohorts[0][90.] > 0.


def run(first, second):
    observed_before = copy.deepcopy(posterior.cohorts)
    x = copy.deepcopy(posterior)
    x.advance([10., 10.], [10., 10.], [2.], [2., 2.], 2., [0., 0.], [first, 110.])
    frozen = copy.deepcopy(x)
    frozen_before = copy.deepcopy(frozen.cohorts)
    x.advance([10., 10.], [10., 10.], [2.], [2., 2.], 2., [0., 0.], [second, 110.])
    x.advance([10., 10.], [10., 10.], [2.], [2., 2.], 2., [0., 0.], [110., 110.])
    assert frozen.cohorts == frozen_before, 'A candidate mutated a sibling exposure'
    assert posterior.cohorts == observed_before, 'A candidate mutated its observed posterior'
    assert all(abs(sum(z.values())-10.) < 1e-12 for z in x.cohorts)
    target = x.target(cfg, 'FW_E', 1, 25., 88., 110.)
    return target, x


trace = ad.Trace([.001, .001], track_stencils=False)
target, exposure = run(ad.Dual(80., {0: 1.}, trace), ad.Dual(80., {1: 1.}, trace))
scalar, scalar_exposure = run(80., 80.)
assert abs(ad.primal(target)-scalar) < 1e-12
checks = []
reverse_gradient = trace.jacobian([target],1)[0] if finder.backend=='reverse-v1' else None
for axis in range(2):
    hi = [80., 80.]; lo = hi.copy(); hi[axis] += .001; lo[axis] -= .001
    fd = (run(*hi)[0]-run(*lo)[0])/.002
    value = float(reverse_gradient[axis]) if reverse_gradient is not None else ad.derivative(target).get(axis, 0.)
    assert abs(value) > 1e-6
    assert abs(value-fd) < 1e-7, (axis, value, fd)
    checks.append(dict(axis=axis, ad=value, finite_difference=fd))
from evaluation.controllers.sdmpc_tangent_worker import state_error
assert state_error(exposure, scalar_exposure) < 1e-12
print(json.dumps(dict(passed=True, checks=checks, scalar_target=scalar,
    conservation=True, copy_isolation=True, full_state_primal_parity=True, backend=finder.backend, historical_commands=[90.,110.])))
