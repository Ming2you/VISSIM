"""One bounded, process-local Chen-inspired friction/merge calibration.

Uses the existing component runner; never changes the native frozen plant.
"""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import ast
import copy
import ctypes
import itertools
import math
import time
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.state_lateral168 import run as runner
from diagnostics.repin_v3c3_review_20261001.vsl_response243.calibrate import packed, scores

HERE = Path(__file__).resolve().parent


def make_source(original, z):
    """Keep every transfer unchanged; add a calibrated reaction beyond mixing."""
    merge_scale, phi = map(float, z)
    assert .75 <= merge_scale <= 1.25 and 0 <= phi <= 1
    output = copy.deepcopy(original)
    s = original['RouteLaneRegion']
    changes = [
        ('        self.exchange_v = {}\n',
         '        self.exchange_v = {}\n        self.friction244 = {}\n'),
        ('            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n',
         "            critical = cfg.network.freeway_segment_params[self.road][i]['rho_crit']\n"
         "            self.friction244[i] = [dict(incoming=[matrix[g][k] for g in range(self.groups)],\n"
         "                origin_speeds=list(self.oldv[i]), target_speed=self.oldv[i][k],\n"
         "                length_km=self.lengths[i], rho_crit=critical,\n"
         f"                phi={phi!r}, merge_scale={merge_scale!r}) for k in range(self.groups)]\n"
         '            moment = [n*v for n,v in zip(ns,self.oldv[i])]\n'),
        ('                velocity -= delta*self.merge[i][g]*self.oldv[i][g]/(self.lengths[i]*(rho+kappa))\n',
         f'                velocity -= {merge_scale!r}*delta*self.merge[i][g]*self.oldv[i][g]/(self.lengths[i]*(rho+kappa))\n'),
        ('            requests = sum(row[g] for off,row in self.off_requests.items() if self.off_access[off] == g\n',
         "            friction = self.friction244[i][g]\n"
         "            raw = sum(amount*max(friction['target_speed']-v,0.)\n"
         "                      for amount,v in zip(friction['incoming'],friction['origin_speeds']))\n"
         "            loss = friction['phi']*raw/(friction['length_km']*friction['rho_crit'])\n"
         "            friction.update(raw=raw, loss=loss, before=velocity)\n"
         "            velocity -= loss\n"
         '            requests = sum(row[g] for off,row in self.off_requests.items() if self.off_access[off] == g\n'),
        ('                    mainline_in_veh=self.incoming[i][g],mainline_out_veh=self.outgoing[i][g]))\n',
         '                    mainline_in_veh=self.incoming[i][g],mainline_out_veh=self.outgoing[i][g]))\n'
         "                if i in self.friction244:self.rows[-1]['friction244']=self.friction244[i][g]\n"),
    ]
    for old, new in changes:
        assert s.count(old) == 1, old
        s = s.replace(old, new)
    output['RouteLaneRegion'] = s
    oldfunc = {n.name: ast.dump(n) for n in ast.parse(original['RouteLaneRegion']).body[0].body if isinstance(n, ast.FunctionDef)}
    newfunc = {n.name: ast.dump(n) for n in ast.parse(s).body[0].body if isinstance(n, ast.FunctionDef)}
    assert all(newfunc[k] == v for k, v in oldfunc.items() if k not in ('plan', 'speed', 'commit'))
    return output


def boxed(J, r):
    # Solve the two-dimensional convex box QP directly, no repeated optimizer.
    low = np.array([-.25, 0.]); high = np.array([.25, 1.])
    A = J.T @ J + .1*np.eye(2); b = -J.T @ r
    options = []
    for codes in itertools.product((-1, 0, 1), repeat=2):
        x = np.array([low[i] if c == -1 else high[i] if c == 1 else 0. for i,c in enumerate(codes)])
        free = [i for i,c in enumerate(codes) if c == 0]; fixed = [i for i,c in enumerate(codes) if c]
        if free:x[free] = np.linalg.solve(A[np.ix_(free,free)], b[free]-A[np.ix_(free,fixed)]@x[fixed])
        if np.all(x >= low-1e-10) and np.all(x <= high+1e-10):
            options.append((float(np.linalg.norm(r+J@x)**2 + .1*(x@x)), x))
    _, x = min(options, key=lambda item:item[0]); x = np.clip(x,low,high)
    grad = A@x-b
    for i in range(2):
        assert (low[i]+1e-8 < x[i] < high[i]-1e-8 and abs(grad[i]) < 1e-7) or (x[i] <= low[i]+1e-8 and grad[i] >= -1e-7) or (x[i] >= high[i]-1e-8 and grad[i] <= 1e-7)
    return x, dict(J=J.tolist(),r=r.tolist(),step=x.tolist(),gradient=grad.tolist(),low=low.tolist(),high=high.tolist(),ridge=.1)


def main():
    assert not (HERE/'protocol.json').exists(), 'Preserve failed/completed attempts'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    began = time.perf_counter()
    source = h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    spec = h.read(h.R/'queue_dynamics178/spec.json'); spec.pop('queue178')
    manifest = h.R/'lane_state132/eval_01/manifest.json'
    protected = {str(p):h.sha(p) for p in (h.ROOT/'evaluation/controllers').glob('*.py')}
    stop = h.read(HERE.parent/'protocol.json')['STOP']
    pins = {str(p):h.sha(p) for p in (Path(__file__), Path(runner.__file__), manifest,
        h.R/'lane_state132/eval_01/reference_config.json', h.R/'spatial_context148/forecast/executed_function_sources.json')}
    proto = dict(source='Exact148 regional lane component +132 coefficients +171 storage. NOT current deployed wholeOmega.',
        reference='Chen,Cheng,Chang2021 equation12: https://attap.umd.edu/wp-content/uploads/2022/08/JTEPBS.0000481.pdf',
        adaptation='Generalize adjacent incoming lane changes to both directions; actual accepted vehicles per1s, positive target-minus-origin speed, divide by lane critical stock. Keep existing lateral momentum mixing; fitted extra reaction can be zero. Not a literal full LGB implementation.',
        equation='dv_extra_k=-phi*sum_g(accepted_lateral_gk*max(v_k-v_g,0))/(L*rho_crit)',
        parameters=['Existing merge_delta multiplier for cells21,23, bounds0.75--1.25','Extra lateral reaction phi for cells20--25, bounds0--1'],
        preserved='All FD/relaxation/anticipation coefficients, actual transfers, route stock, shared receiving, off FIFO/storage/drain, ramp wait and VSL cohort history. Cell19 split unchanged.',
        train='Known seed67 late4 arms, not blind. Prior132 also used this seed.',
        validation='Known29late4/43early2/61late2; selected coefficients frozen before these8 results.',
        budget=dict(parity=1,train=24,validation=8,total450=33,fit_steps=1,native=0,FZP=0),
        design='Base[1,0], delta +/-0.1, phi forward0.25. One ridge0.1 box step and half step; allow base to win. No grid or bound expansion.',
        criterion='Existing125 residual weighted150/450 equally; >=10% response improvement, absolute<=110%, meaningful signs, regret<=0.5. Omega controller objective unchanged.',
        prior_review='Claude FWW_STRUCT_CHECK/N1F +110/111/168/177/192/212/243 and merge_speed_audit/population. Those do not implement this accepted-lateral speed-difference term.',
        protected_sha256=protected,STOP=stop,adopted=False,future_measurements=False)
    h.save(HERE/'protocol.json',proto);h.save(HERE/'pins.json',pins)
    evaluations=[];count=0

    def evaluate(z,tag,scope='train'):
        nonlocal count
        z=list(map(float,z)); folder=HERE/tag;folder.mkdir()
        candidate=make_source(source,z)
        for name,value in [('setting.json',dict(manifest=str(manifest),structure='response243',records=scope)),
            ('spec.json',spec),('coefficients.json',dict(values=z)),('protocol.json',proto),('pins.json',pins),('executed_function_sources.json',candidate)]:h.save(folder/name,value)
        expected=1 if scope=='parity' else 4 if scope=='train' else 8
        assert count+expected <= 33
        runner.queue178(calibration243=folder)
        assert h.read(folder/'forecast/status.json')['forecasts']==expected
        count+=expected; rows=h.read(folder/'forecast/rows.json')
        if scope=='parity' or tag=='center':
            for p in (folder/'forecast/response243').glob('*.json.gz'):
                pred=h.read(p); ref=h.read(h.R/'queue_dynamics178/forecast/baseline'/p.name)
                assert all(pred[k]==ref[k] for k in ('cells','flows','ports','ramps')),p
        result=dict(tag=tag,z=z,scope=scope,rows=rows,scores=scores(rows),objective=float(packed(rows)@packed(rows)))
        evaluations.append(result);h.save(HERE/'evaluations.json',evaluations)
        h.save(HERE/'status.json',dict(status='running',forecasts=count,tag=tag))
        print('FRICTION244',tag,z,result['objective'],flush=True)
        return result

    try:
        evaluate([1,0],'parity','parity')
        center=evaluate([1,0],'center');plus=evaluate([1.1,0],'merge_plus');minus=evaluate([.9,0],'merge_minus')
        friction=evaluate([1,.25],'friction_forward')
        r=packed(center['rows'])
        J=np.column_stack([(packed(plus['rows'])-packed(minus['rows']))/.2,(packed(friction['rows'])-r)/.25])
        step,linear=boxed(J,r);h.save(HERE/'linear_step.json',linear)
        full=evaluate(np.array([1.,0.])+step,'full_step');half=evaluate(np.array([1.,0.])+.5*step,'half_step')
        best=min((center,full,half),key=lambda e:e['objective'])
        h.save(HERE/'selection_frozen.json',dict(tag=best['tag'],z=best['z'],objective=best['objective'],base=center['objective'],before_validation=True))
        val=evaluate(best['z'],'validation','validation')
        baseline=[r for r in h.read(h.R/'queue_dynamics178/forecast/rows.json') if r['mode']=='baseline' and r['case']!='s67_late']
        validation=scores(baseline); gates={}
        for label,cur,old in [('train',best['scores'],center['scores']),('validation',val['scores'],validation)]:
            gates[label]={t:dict(response=cur[t]['response']<=.9*old[t]['response'],absolute=cur[t]['absolute']<=1.1*old[t]['absolute'],signs=all(p['sign_correct'] for p in cur[t]['pairs'] if p['meaningful'])) for t in ('150','450')}
        regrets=[]
        for t in (150,450):
            for case in sorted({r['case'] for r in val['rows']}):
                rs=[r for r in val['rows'] if r['case']==case and r['horizon']==t]
                chosen=min(rs,key=lambda r:r['predicted']['ttt'])
                regrets.append(dict(case=case,horizon=t,selected=chosen['arm'],regret=chosen['actual']['ttt']-min(r['actual']['ttt'] for r in rs)))
        h.save(HERE/'validation.json',dict(gates=gates,regrets=regrets,baseline=validation))
        passed=all(v for group in gates.values() for period in group.values() for v in period.values()) and all(r['regret']<=.5 for r in regrets)
        result=dict(status='complete',forecasts450=count,wall_sec=time.perf_counter()-began,component_gate_passed=passed,production_adopted=False,goal='ACTIVE_NOT_QUALIFIED',native=0,FZP=0)
        h.save(HERE/'completion.json',result);h.save(HERE/'status.json',result);print(result,flush=True)
    except BaseException as exc:
        h.save(HERE/'status.json',dict(status='failed',forecasts=count,error=repr(exc)));raise
    finally:
        assert all(h.sha(p)==v for p,v in {**pins,**protected,stop['path']:stop['sha256']}.items())
        h.save(HERE/'preservation.json',dict(production_and_inputs_and_STOP_unchanged=True))


if __name__=='__main__':main()
