"""Pure-formula and nominal-command checks; no forecast or native activity."""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common

D=Path(__file__).resolve().parent/'verified'


def main():
    assert not (D/'fd_verification.json').exists()
    chosen=h.read(D/'selection_frozen.json')
    context,_,_=common.setup()
    from evaluation.controllers import freeway_fd as fd
    cfg=context['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
    from diagnostics.repin_v3c3_review_20261001.vsl_fd253.run import fd_coefficients
    original=fd._literature_speed
    p=cfg.network.freeway_segment_params['FW_E']
    spec=cfg.network.freeway_vsl_fd_response['FW_E']
    stats={};checks=nominal=outside=0;maximum=0.;capacity=[]
    with fd_coefficients([chosen['A'],chosen['E']],stats):
        for cell in range(31):
            row=p[cell]
            for command in (50.,60.,70.,80.,90.,100.,110.):
                A,E=(chosen['A'],chosen['E']) if 16<=cell<=25 else (.5,2.)
                b=command/110.;vf=row['v_free']*b
                critical=row['rho_crit']*(1+A*(1-b))
                shape=row['metanet_a_m']*(E-(E-1)*b)
                assert 0<critical<cfg.network.rho_max and shape>0
                for rho in (0.,20.,60.,100.):
                    expected=vf*math.exp(-(rho/critical)**shape/shape)
                    actual=fd._literature_speed(spec,cfg,'FW_E',cell,rho,command)
                    maximum=max(maximum,abs(actual-expected));assert abs(actual-expected)<1e-10
                    checks+=1
                    before=original(spec,cfg,'FW_E',cell,rho,command)
                    if command==110.:assert actual==before;nominal+=1
                    if not 16<=cell<=25:assert actual==before;outside+=1
                if 16<=cell<=25 and command in (90.,110.):
                    capacity.append(dict(cell=cell,command=command,critical=critical,shape=shape,
                        theoretical_fd_peak_veh_h_lane=vf*critical*math.exp(-1/shape)))
    assert fd._literature_speed is original
    # FD peaks are formula implications, not measured VISSIM capacities.
    h.save(D/'fd_verification.json',dict(status='PASS',checks=checks,maximum_error=maximum,
        nominal_exact=nominal,other_cells_exact=outside,theoretical_fd_peaks=capacity,
        capacity_measured=False,AD_verified=False,adopted=False))
    print('FD formula PASS',checks,maximum,'nominal',nominal,'other',outside)


if __name__=='__main__':main()
