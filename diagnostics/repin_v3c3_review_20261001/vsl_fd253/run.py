"""One bounded Carlson A/E fit in the current coupled plant; no native edits."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import copy
from contextlib import contextmanager
import ctypes
import json
from pathlib import Path
import sys
import time
import numpy as np
from scipy.optimize import lsq_linear
from diagnostics.repin_v3c3_review_20261001.deceleration248 import run as d
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE = Path(__file__).resolve().parent
OUT = HERE/'verified'
OLD = h.R/'deceleration248/verified'
X0 = np.array([.5, 2.])
LOW = np.array([0., .5])
HIGH = np.array([1.5, 4.])


def save(name, value): h.save(OUT/name, value)


def off(row):
    return sum(t['vehicles'] for t in row['transfers']
               if t['source'] == 'freeway:FW_E' and t['target'].startswith('storage:'))


def vector(row, base):
    # Do not fit Omega/end-stock to absorb the observed -27 source difference.
    return np.array([off(row)/25., row['east_terminal']/25.,
                     (off(row)-off(base))/12.,
                     (row['east_terminal']-base['east_terminal'])/25.])


@contextmanager
def fd_coefficients(x, stats):
    from evaluation.controllers import freeway_fd as fd
    old = fd._literature_speed
    def changed(spec, cfg, road, cell, rho, command):
        if road == 'FW_E' and 16 <= cell <= 25:
            assert spec == {'law':'carlson', 'A':.5, 'E':2., 'alpha':0.}
            spec = dict(spec, A=float(x[0]), E=float(x[1]))
            stats[str(cell)] = stats.get(str(cell), 0)+1
        return old(spec, cfg, road, cell, rho, command)
    fd._literature_speed = changed
    try: yield
    finally:
        assert fd._literature_speed is changed
        fd._literature_speed = old


def forecast(tag, arm, x, label):
    stats = {}
    with fd_coefficients(x, stats):
        row = d.forecast(tag, arm, 1., label)
    assert stats and set(stats) <= {str(i) for i in range(16,26)}
    row['fd_candidate'] = dict(A=float(x[0]), E=float(x[1]), calls=stats)
    save(f'{tag}_{label}_{arm}.json', row)
    return row


def parity(actual, expected):
    ignored = {'seconds','label','fd_candidate'}
    assert {k:v for k,v in actual.items() if k not in ignored} == {
        k:v for k,v in expected.items() if k not in ignored}


def main():
    OUT.mkdir(exist_ok=False)
    d.HERE = OUT
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    sources = {str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop = h.read(h.R/'aggregate_recovery247/protocol.json')['STOP']
    base = h.read(OLD/'s67_base_release_actual.json')
    center = h.read(OLD/'s67_base_release_vsl90_actual.json')
    truth = h.read(h.R/'s67_full_observation/response_assessment76.json')['arms']
    a,b = (truth[n]['mainline']['FW_E']['actual'] for n in ('release','release_vsl90'))
    target = np.array([b['off']/25.,b['terminal']/25.,
                       (b['off']-a['off'])/12.,(b['terminal']-a['terminal'])/25.])
    tuning = h.read(h.R/'rm_restart219/budget235/config.json')
    tuning['adapter'].pop('sdmpc_fixed_vsl')
    save('tuning.json', tuning)
    pins = {str(p):h.sha(p) for p in (Path(__file__),Path(d.__file__),
        OLD/'s67_base_release_actual.json', OLD/'s67_base_release_vsl90_actual.json',
        h.R/'s67_full_observation/response_assessment76.json',OUT/'tuning.json')}
    save('protocol.json', dict(
        scope='Current233/235 aggregate31/fullOmega/8ramps; frozen live9000 unchanged.',
        prior='Reviewed Claude L2 A1.33/E.87 on DIFFERENT network, not transferred. Existing A reduction and E-only16--20 trials rejected; joint A/E calibration not assumed from them.',
        hypothesis='Existing final VSL FD target is applied but response small/wrong. Joint density/shape response may be identifiable from absolute and relative discharge without fitting all observed TTT.',
        change='Only current Carlson A/E jointly in fixed physical cells16--25. Same formula/cohorts; no added capacity/reward; nominal110 unchanged. Other laws/coefficients and receiving unchanged.',
        bounds=[LOW.tolist(),HIGH.tolist()], center=X0.tolist(),
        training='Knownseed67 release110/90, common2700 start; fit450 off/terminal absolute and differences. No future observation as predictor input.',
        exclusions='No source difference, endstock or TTT in fit: observedentrydifference is not extra capacity ground truth.',
        target=target.tolist(), scales=dict(absolute=25,off_difference=12,terminal_difference=25),
        budget='One bounded ridge linear fit from A+.25/E+.5 probes; one proposal and half step. At most9 new450 forecasts, no repeats/bound expansion. Baselines reused.',
        acceptance='Training flux objective improve10%; independent validation material abs>=.5 Omega sign and error<=max(.5,.5absactual), ranking regret<=.5; no10% worse absolute terminal/off errors. Conservation mandatory. No adoption based on training alone.',
        validation='Knowns71NC/RM/VSL/both ands73release pair, frozen after fit; historical exposure means not blind.',
        protected=sources, STOP=stop,pins=pins, future_observation_inputs=False))
    started = time.perf_counter()
    try:
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        original_main = probe.main
        def unique_output():
            # The shared initializer's default names belong to the earlier248
            # diagnostic. Preserve them and give this attempt separate outputs.
            sys.argv[:] = [a.replace('=d248c_', '=fd253_') if a.startswith(
                ('--probe-label=', '--output-suffix=')) else a for a in sys.argv]
            return original_main()
        probe.main = unique_output
        try: d.prepare_inputs()
        finally: probe.main = original_main
        same = forecast('s67','release_vsl90_actual',X0,'parity')
        parity(same,center)
        rA = forecast('s67','release_vsl90_actual',X0+[.25,0.],'probeA')
        rE = forecast('s67','release_vsl90_actual',X0+[0.,.5],'probeE')
        residual = vector(center,base)-target
        J = np.column_stack(((vector(rA,base)-vector(center,base))/.25,
                             (vector(rE,base)-vector(center,base))/.5))
        ridge = .1
        fit = lsq_linear(np.vstack((J,np.sqrt(ridge)*np.eye(2))),
                         np.r_[-residual,[0.,0.]],bounds=(LOW-X0,HIGH-X0),tol=1e-10)
        assert fit.success
        proposal = X0+fit.x
        save('linear_fit.json',dict(J=J.tolist(),residual=residual.tolist(),
            proposal=proposal.tolist(),ridge=ridge,status=int(fit.status),optimality=fit.optimality,
            singular=np.linalg.svd(J,compute_uv=False).tolist(),validation_used=False))
        candidates = [('base',X0,center)]
        for name,x in [('proposal',proposal),('half',(proposal+X0)/2)]:
            if np.max(abs(x-X0))<1e-10:row=center
            else:row=forecast('s67','release_vsl90_actual',x,name)
            candidates.append((name,x,row))
        loss = lambda row:float(sum((vector(row,base)-target)**2))
        chosen = min(candidates,key=lambda z:loss(z[2]))
        name,x,row = chosen
        selection = dict(label=name,A=float(x[0]),E=float(x[1]),validation_used=False,
            candidates=[dict(label=n,x=v.tolist(),loss=loss(rr),off=off(rr),terminal=rr['east_terminal'],
                             delta_ttt=rr['ttt']-base['ttt']) for n,v,rr in candidates],
            probes=[dict(label=n,loss=loss(rr),off=off(rr),terminal=rr['east_terminal'],delta_ttt=rr['ttt']-base['ttt'])
                    for n,rr in [('A',rA),('E',rE)]])
        save('selection_frozen.json',selection)
        validation=[]
        for tag,arms in [('s71',('vsl','both')),('s73',('release_vsl90_actual',))]:
            for arm in arms:
                if np.max(abs(x-X0))<1e-10:rr=h.read(OLD/f'{tag}_base_{arm}.json')
                else:rr=forecast(tag,arm,x,'chosen')
                validation.append(rr)
        save('validation.json',validation)
        assert len(d.RESULTS)<=9
        assert all(h.sha(p)==v for p,v in {**sources,**pins,stop['path']:stop['sha256']}.items())
        save('completion.json',dict(status='COMPLETE_PENDING_ASSESSMENT',forecasts=len(d.RESULTS),
            seconds=time.perf_counter()-started,fit_calls=1,protected=True,adopted=False,
            native=0,FZP=0,goal='ACTIVE_NOT_QUALIFIED'))
    except BaseException as exc:
        save('failure.json',dict(error=repr(exc),completed_forecasts=len(d.RESULTS),retry=False))
        raise


if __name__=='__main__':main()
