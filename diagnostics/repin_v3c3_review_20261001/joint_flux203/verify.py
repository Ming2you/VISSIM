"""Verify retained forecasts and preservation independently of optimization."""
import ast
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(p):
    raw=p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    completion=read(HERE/'completion.json');assert completion['status']=='complete'
    before=ast.parse((HERE/'runner_before203.py.txt').read_text(encoding='utf8'))
    after=ast.parse((HERE.parent/'state_lateral168/run.py').read_text(encoding='utf8'))
    fn=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='queue178')
    index=next(i for i,a in enumerate(fn.args.kwonlyargs) if a.arg=='calibration203')
    del fn.args.kwonlyargs[index];del fn.args.kw_defaults[index]
    new=[n for n in fn.body if isinstance(n,ast.If) and ast.unparse(n.test)=='calibration203 is not None']
    assert len(new)==1;fn.body.remove(new[0]);assert ast.dump(before)==ast.dump(after)
    core=read(HERE.parent/'regional_audit202/protocol.json')['source_sha256']
    for name,d in core.items():assert sha(ROOT/name)==d,name
    protocol=read(HERE/'protocol.json');assert sha(Path(protocol['STOP']['path']))==protocol['STOP']['sha256']
    counts=defaultdict(int);errors=defaultdict(float)
    def check(kind,x):
        counts[kind]+=1;errors[kind]=max(errors[kind],abs(x));assert abs(x)<1e-8,(kind,x)
    files=[]
    for evaluation in read(HERE/'evaluations.json'):
        folder=HERE/evaluation['tag'];coeff=read(folder/'coefficients.json')
        for row in evaluation['rows']:
            path=folder/'forecast/priority'/(row['case']+'_'+row['arm']+'.json.gz')
            pred=read(path);files.append(dict(path=str(path.relative_to(HERE)),sha256=sha(path)))
            cells={(round(z['time_s'],5),z['cell']):z['n_veh'] for z in pred['cells']}
            flows={(round(z['window_end_s'],5),z['cell']):z for z in pred['flows']}
            for (t,i),z in flows.items():
                start=round(z['window_start_s'],5)
                if (start,i) not in cells:continue  # First30s initial stock not in these output tables.
                incoming=z['source_admissions']+(flows[t,i-1]['downstream_crossings'] if i else 0.)
                check('cell_stock_balance',cells[t,i]-cells[start,i]-incoming-z['ramp_merges']+z['downstream_crossings']+z['off_departures']+z['terminal_exits'])
            for z in pred['ramps']:
                check('ramp_stock_balance',z['end']['connector_veh']-z['start']['connector_veh']-z['admitted_arrivals_veh']+z['accepted_merge_veh'])
                assert z['accepted_merge_veh']>=0 and z['end']['connector_veh']>=0
            audit=read(path.with_name(path.name.replace('.json.gz','_allocation.json.gz')))
            for z in audit['allocation']:
                assert z['priority']==coeff['p']
                R,D,p=z['receiving_vph'],z['mainline_feasible_vph'],z['priority']
                check('priority_budget',z['ramp_budget_vph']-min(R,max(p*R,R-D)))
            counts['forecasts450']+=1
    assert counts['forecasts450']==completion['forecasts450']
    linear=read(HERE/'linear_step.json');J=np.asarray(linear['J']);r=np.asarray(linear['r0']);x=np.asarray(linear['step'])
    gradient=J.T@(r+J@x)+linear['ridge']*x
    check('linear_gradient',float(np.max(np.abs(gradient-np.asarray(linear['gradient'])))))
    for i in range(2):
        assert (abs(x[i])<.25-1e-8 and abs(gradient[i])<1e-7) or (x[i]<=-.25+1e-8 and gradient[i]>=-1e-7) or (x[i]>=.25-1e-8 and gradient[i]<=1e-7)
    for name in ('calibrate.py','verify.py'):
        (HERE/(name+'.executed.txt')).write_bytes((HERE/name).read_bytes())
    (HERE/'runner_executed.py.txt').write_bytes((HERE.parent/'state_lateral168/run.py').read_bytes())
    result=dict(status='PASS',checks=dict(counts),max_errors=dict(errors),old_default_AST_exact=True,
                core_files_unchanged=len(core),old_STOP_preserved=True,forecasts=files,
                limitation='First30s cell mass not rederived from absent initial table; full ramp and later30s mass independently checked.',
                production_adopted=False)
    (HERE/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='forecasts'}))


if __name__=='__main__':main()
