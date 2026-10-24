"""Independently recalculate the saved finite-difference matrices and outcomes."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

D=Path(__file__).resolve().parent


def main():
    completion=h.read(D/'completion.json');assert completion['status']=='COMPLETE_PENDING_ASSESSMENT'
    protocol=h.read(D/'protocol.json');rows=h.read(D/'tangents.json');assert len(rows)==6
    out=[]
    for r in rows:
        J=np.array(r['jacobian']);C=np.array(r['coarse_jacobian']);assert J.shape==C.shape==(62,62)
        eig,vec=np.linalg.eig(J);radius=float(max(abs(eig)))
        assert abs(radius-r['spectral_radius'])<1e-11
        assert abs(np.max(abs(J-C))-r['max_epsilon_difference'])<1e-15
        assert r['max_epsilon_difference']<1e-7 and max(r['max_one_sided_difference'])<1e-3
        assert r['canonical_replay_max_difference']<1e-10
        assert r['diagnostics']['density_projection_count']==0
        assert r['max_advective_courant']<1
        # Complex modes with negative generator real part outside the unit
        # disk are the diagnostic Euler risk, not every eigenvalue >1.
        risk=[v for v in eig if v.real<1-1e-6 and abs(v)>1+1e-6]
        assert len(risk)==len(r['euler_inward_but_unit_disk_outside'])
        dominant=int(np.argmax(abs(eig)));mode=vec[:,dominant]
        energies=abs(mode[:31])**2+abs(mode[31:])**2;energies/=sum(energies)
        eig_residual=float(np.max(abs(J@vec-vec*eig[None,:])))
        assert eig_residual<1e-10
        out.append(dict(arm=r['arm'],time=r['time_sec'],radius=radius,
            minimum_modulus=float(min(abs(eig))),max_singular=r['singular_max'],
            unstable_generator_mode_count=int(sum(eig.real>1+1e-6)),
            euler_risk_modes=len(risk),eigen_residual=eig_residual,
            one_sided_discrepancy=max(r['max_one_sided_difference']),
            largest_mode_cells=[dict(cell=int(i),normalized_energy=float(energies[i])) for i in np.argsort(-energies)[:5]],
            speed_projection_count=r['diagnostics']['speed_projection_count'],
            max_courant=r['max_advective_courant']))
    verification=[]
    for arm in ('release_actual','release_vsl90_actual'):
        new=h.read(D/f's67_unchanged_{arm}.json')
        base=h.read(h.R/f'deceleration248/verified/s67_base_{arm}.json')
        assert new['ttt']==base['ttt'] and new['snapshots']==base['snapshots']
        assert new['commands']==base['commands'] and new['ramps']==base['ramps']
        assert new['cost_by_stock']==base['cost_by_stock'] and new['transfers']==base['transfers']
        assert new['resource_max']<1e-7
        cost=sum(r['dt_h']*r['inside_total'] for r in new['residence'])
        assert abs(cost-new['ttt'])<1e-8
        verification.append(dict(arm=arm,ttt=new['ttt'],ledger_integral_error=abs(cost-new['ttt']),
            exact_baseline_states_commands_costs_transfers_ramps=True))
    assert all(h.sha(p)==v for p,v in protocol['pins'].items())
    assert h.sha(D/'run.py')==protocol['source_sha256']
    h.save(D/'assessment.json',dict(results=out,baseline_verification=verification,
        conclusion='No Euler-risk mode or Courant violation in these six exact projected one-second maps. Small positive generator modes are not numerical-instability proof. No complete coupled-network stability claim; VSL cost-error unchanged, no fitted or adopted model.',
        future_observation_inputs=False,production_adopted=False,
        limitations=['Port rates/capacities held fixed during each derivative; do not include RM/urban receiving feedback.',
            'Route/VSL fractions held fixed while density is perturbed; hidden inventories evolve in real forecasts, so matrix powers are not a450s full-network tangent.',
            'Six forecast states ofone seed, notallstates ornative microscopic waves. Nonlinearfinite control effects nottested here.',
            'No changes tointernaldt,geometry,objective,parameters,capacity orongoingnative run.']))
    completion['status']='COMPLETE_DIAGNOSTIC_NO_ADOPTION'
    h.save(D/'completion.json',completion)
    print(__import__('json').dumps(out),flush=True)


if __name__=='__main__':main()
