"""One bounded fit of published incoming/outgoing lateral-friction terms.

Uses the existing component runner. Never modifies the live frozen plant.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ast
import copy
import ctypes
import time
from pathlib import Path
import numpy as np
from scipy.optimize import lsq_linear
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.state_lateral168 import run as runner
from diagnostics.repin_v3c3_review_20261001.vsl_response243.calibrate import packed, scores

HERE = Path(__file__).resolve().parent


def make_source(original, coefficients):
    incoming, outgoing = map(float, coefficients)
    assert 0 <= incoming <= 1 and 0 <= outgoing <= 1
    result = copy.deepcopy(original)
    source = original['RouteLaneRegion']
    replacements = [
        ('        self.exchange_v = {}\n',
         '        self.exchange_v = {}\n        self.friction251 = {}\n'),
        ('            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n',
         '            self.friction251[i] = [dict(incoming=sum(matrix[g][k] for g in range(self.groups)),\n'
         '                outgoing=sum(matrix[k]), speed=self.oldv[i][k], length_km=self.lengths[i],\n'
         '                matrix_in=[matrix[g][k] for g in range(self.groups)], matrix_out=list(matrix[k]))\n'
         '                for k in range(self.groups)]\n'
         '            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n'),
        ('            requests = sum(row[g] for off,row in self.off_requests.items() if self.off_access[off] == g\n',
         '            friction = self.friction251[i][g]\n'
         '            denominator = self.lengths[i]*(rho+kappa)\n'
         '            basis_in = self.oldv[i][g]*friction["incoming"]/denominator\n'
         '            basis_out = self.oldv[i][g]*friction["outgoing"]/denominator\n'
         f'            loss = {incoming!r}*basis_in + {outgoing!r}*basis_out\n'
         '            friction.update(rho=rho, kappa=kappa, basis_in=basis_in, basis_out=basis_out,\n'
         f'                delta_in={incoming!r}, delta_out={outgoing!r}, loss=loss, before=velocity)\n'
         '            velocity -= loss\n'
         '            requests = sum(row[g] for off,row in self.off_requests.items() if self.off_access[off] == g\n'),
        ('                    mainline_in_veh=self.incoming[i][g],mainline_out_veh=self.outgoing[i][g]))\n',
         '                    mainline_in_veh=self.incoming[i][g],mainline_out_veh=self.outgoing[i][g]))\n'
         '                if i in self.friction251:self.rows[-1]["friction251"]=self.friction251[i][g]\n'),
    ]
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    old_functions = {n.name: ast.dump(n) for n in ast.parse(original['RouteLaneRegion']).body[0].body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: ast.dump(n) for n in ast.parse(source).body[0].body if isinstance(n, ast.FunctionDef)}
    assert all(new_functions[k] == v for k, v in old_functions.items() if k not in ('plan', 'speed', 'commit'))
    result['RouteLaneRegion'] = source
    return result


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve all completed/failed attempts'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    started = time.perf_counter()
    source_path = h.R/'spatial_context148/forecast/executed_function_sources.json'
    source = h.read(source_path)
    spec = h.read(h.R/'queue_dynamics178/spec.json'); spec.pop('queue178')
    manifest = h.R/'lane_state132/eval_01/manifest.json'
    center_path = HERE.parent/'lateral_friction244/center/forecast/rows.json'
    center_rows = h.read(center_path)
    center = dict(tag='reused244_center', z=[0., 0.], rows=center_rows, scores=scores(center_rows),
                  objective=float(packed(center_rows)@packed(center_rows)))
    protected = {str(p): h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop = h.read(HERE.parent/'protocol.json')['STOP']
    pins = {str(p): h.sha(p) for p in (Path(__file__), Path(runner.__file__), manifest, source_path,
        center_path, h.R/'lane_state132/eval_01/reference_config.json', h.R/'lmetanet251/source.pdf')}
    protocol = dict(
        reference='https://arxiv.org/pdf/2609.35152, Eq20, page16; preprint2026-09-28',
        hypothesis='Actual accepted lateral entry and exit can induce distinct speed losses beyond transported speed mixing; fit nonnegative coefficients, allowing zero/no effect.',
        distinction_from244='Self-speed times incoming AND outgoing accepted lateral counts divided by current lane stock plus kappa*length. 244 used only incoming positive target-minus-origin speed divided by critical stock.',
        equation='dv=-(delta_in*C_in+delta_out*C_out)*v/(L*(rho+kappa)); C is accepted veh per internal1s, so no extra dt. Both terms nonpositive.',
        adaptation='Only extra friction terms, not the full paper model. Preserve existing lateral momentum mixing; zero coefficient is nested null and may win. Do not add paper geometric convection already rejected165.',
        scope='Experimental148 regional lanes20--25 +132 coefficients +171 storage, east31+4on/4off. NOT deployed233/235 aggregate/fullOmega.',
        fixed='FD, all existing speed coefficients, merge, receiving, route inventories, actual ramp waits, dynamic off storage/drain, split19 and VSL cohort history.',
        train='Previously inspected seed67late4 arms; not blind and already used by earlier132.',
        validation='Known29late4/43early2/61late2 excluded from this selection. Freeze before reading candidate validation.',
        budget=dict(fit_steps=1, parity=1, train=16, validation=8, total450=25, reused_baseline=4, native=0, FZP=0),
        design='Reuse exact244 zero-reaction center; one-sided0.25 axes, ridge0.1 bounded [0,1]^2 step and half only. Baseline can win; no expanded grid.',
        gates='Both150/450: response error >=10% reduction; absolute <=110%; meaningful pair signs correct; selection regret <=0.5vehh. Not fullOmega qualification.',
        future_measurement_inputs=False, adopted=False, protected_sha256=protected, STOP=stop)
    h.save(HERE/'protocol.json', protocol); h.save(HERE/'pins.json', pins)
    evaluations = [center]; count = 0

    def evaluate(z, tag, scope='train'):
        nonlocal count
        z = list(map(float, z)); folder = HERE/tag; folder.mkdir()
        candidate = make_source(source, z)
        for name, value in [('setting.json', dict(manifest=str(manifest), structure='response243', records=scope)),
                            ('spec.json', spec), ('coefficients.json', dict(values=z)), ('protocol.json', protocol),
                            ('pins.json', pins), ('executed_function_sources.json', candidate)]:
            h.save(folder/name, value)
        expected = 1 if scope == 'parity' else 4 if scope == 'train' else 8
        assert count + expected <= 25
        runner.queue178(calibration243=folder)
        assert h.read(folder/'forecast/status.json')['forecasts'] == expected
        count += expected
        rows = h.read(folder/'forecast/rows.json')
        if scope == 'parity':
            for p in (folder/'forecast/response243').glob('*.json.gz'):
                predicted = h.read(p); baseline = h.read(h.R/'queue_dynamics178/forecast/baseline'/p.name)
                assert all(predicted[k] == baseline[k] for k in ('cells', 'flows', 'ports', 'ramps')), p
        result = dict(tag=tag, z=z, scope=scope, rows=rows, scores=scores(rows),
                      objective=float(packed(rows)@packed(rows)))
        evaluations.append(result); h.save(HERE/'evaluations.json', evaluations)
        h.save(HERE/'status.json', dict(status='running', forecasts=count, tag=tag))
        print('FRICTION251', tag, z, result['objective'], flush=True)
        return result

    try:
        evaluate([0, 0], 'parity', 'parity')
        a = evaluate([.25, 0], 'incoming_probe'); b = evaluate([0, .25], 'outgoing_probe')
        residual = packed(center_rows)
        J = np.column_stack([(packed(a['rows'])-residual)/.25, (packed(b['rows'])-residual)/.25])
        fit = lsq_linear(np.vstack([J, np.sqrt(.1)*np.eye(2)]),
                         np.r_[-residual, 0., 0.], bounds=(0, 1), tol=1e-12, max_iter=100)
        assert fit.success and fit.optimality < 1e-7
        step = fit.x
        h.save(HERE/'linear_step.json', dict(J=J.tolist(), residual=residual.tolist(), step=step.tolist(),
                gradient=(J.T@(residual+J@step)+.1*step).tolist(), optimality=fit.optimality, iterations=fit.nit,
                ridge=.1, lower=[0,0], upper=[1,1]))
        full = evaluate(step, 'full_step'); half = evaluate(step*.5, 'half_step')
        best = min((center, full, half), key=lambda e:e['objective'])
        h.save(HERE/'selection_frozen.json', dict(tag=best['tag'], z=best['z'], objective=best['objective'],
                baseline=center['objective'], before_validation=True))
        val = evaluate(best['z'], 'validation', 'validation')
        validation_base = scores([r for r in h.read(h.R/'queue_dynamics178/forecast/rows.json')
                                  if r['mode'] == 'baseline' and r['case'] != 's67_late'])
        gates = {}
        for label, cur, old in [('train', best['scores'], center['scores']), ('validation', val['scores'], validation_base)]:
            gates[label] = {t:dict(response=cur[t]['response'] <= .9*old[t]['response'],
                                  absolute=cur[t]['absolute'] <= 1.1*old[t]['absolute'],
                                  signs=all(p['sign_correct'] for p in cur[t]['pairs'] if p['meaningful']))
                            for t in ('150', '450')}
        regrets = []
        for group in (best, val):
            for t in (150, 450):
                for case in sorted({r['case'] for r in group['rows']}):
                    rows = [r for r in group['rows'] if r['case'] == case and r['horizon'] == t]
                    chosen = min(rows, key=lambda r:r['predicted']['ttt'])
                    regrets.append(dict(case=case, horizon=t, chosen=chosen['arm'],
                                        regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in rows)))
        passed = all(v for g in gates.values() for p in g.values() for v in p.values()) and all(r['regret'] <= .5 for r in regrets)
        h.save(HERE/'validation.json', dict(gates=gates, regrets=regrets, baseline=validation_base))
        result = dict(status='complete', forecasts450=count, wall_sec=time.perf_counter()-started,
                      component_gate_passed=passed, production_adopted=False, goal='ACTIVE_NOT_QUALIFIED', native=0, FZP=0)
        h.save(HERE/'completion.json', result); h.save(HERE/'status.json', result); print(result, flush=True)
    except BaseException as error:
        h.save(HERE/'status.json', dict(status='failed', forecasts=count, error=repr(error))); raise
    finally:
        assert all(h.sha(p) == digest for p, digest in {**pins, **protected, stop['path']:stop['sha256']}.items())
        h.save(HERE/'preservation.json', dict(production_inputs_STOP_unchanged=True))


if __name__ == '__main__':
    main()
