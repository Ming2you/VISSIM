"""Isolate the failed7050 balance using closed native evidence; never rewrite it."""
import ast
from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RUN=Path('D:/VISSIM_runs/20261003_service66_queuezero_s29_9000')
DEC=RUN/'sdmpc/decisions_sdmpc31_sdmpc9000_s29'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def function(path,name):
    tree=ast.parse(path.read_text(encoding='utf-8-sig'))
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    namespace=dict(bisect_right=bisect_right,math=math)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    return namespace[name]

def main():
    out=HERE/'balance.json'
    if out.exists():raise FileExistsError(out)
    source=ROOT/'evaluation/controllers/vsl_exposure_history.py'
    bsource=ROOT/'evaluation/controllers/lane_plant_runtime.py'
    cell_fluxes=function(source,'cell_fluxes');bin_frame=function(bsource,'bin_frame')
    geom_path=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/port_gain/geometry.json'
    g=read(geom_path);raw=read(DEC/'state_007050.json');obs=raw['obs150']
    derived_path=DEC/'obs150/derived_007050.json';d=read(derived_path)
    meta_path=DEC/'obs150/capture_007050.json';meta=read(meta_path)
    err_path=Path(meta['err']['source']);err=err_path.read_bytes()
    pins={str(p):sha(p) for p in [source,bsource,geom_path,derived_path,meta_path,err_path,DEC/'state_007050.json',DEC/'obs150/err_007050.jsonl']}
    frames=[]
    for role in ['previous','current']:
        ref=obs['frames'][role];p=DEC/ref['path'];assert sha(p)==ref['sha256']
        frames.append(read(p));pins[str(p)]=sha(p)
    pattern=re.compile(rb'Simulation second ([0-9.]+): After ([0-9.]+) seconds of waiting for lane change the vehicle (\d+) \(on Static Vehicle Route [^\r\n]*?\) was removed from link (\d+) at position ([0-9.]+)\.')
    removed=[]
    for m in pattern.finditer(err):
        t,wait,veh,link,pos=m.groups();t=float(t)
        if 6900<t<=7050:removed.append(dict(time_s=t,vehicle=int(veh),link=int(link),pos=float(pos),byte_offset=m.start()))
    result=dict(previous_turn='PROGRESS: literature review and authoritative7050 termination change next action',
        qualification='post-run cause isolation only; finalERR unavailable to original online capture',
        captured_err=meta['err'],closed_err_sha256=sha(err_path),removals=removed,roads={},pins=pins)
    assert not d['removals']['rows']
    for road in ['FW_E','FW_W']:
        cells,a,drop=bin_frame(g,frames[0]['vehicles'],road,drop_before_start=True)
        _,b,drop2=bin_frame(g,frames[1]['vehicles'],road,drop_before_start=True)
        assert not drop and not drop2 and len(cells)==31
        old=list(map(len,a));new=list(map(len,b));merges=[0]*31;exits=[0]*31;deleted=[0]*31
        count=lambda f,l:sum(z[1]==int(l) for z in f['vehicles'])
        for boundary in g['boundaries']:
            if boundary['road']!=road:continue
            connector=str(boundary['connector']) if 'connector' in boundary else ''
            if boundary['kind']=='offramp':exits[boundary['from_cell']]+=d['boundaries']['off_entry:'+connector]['cross']
            elif boundary['kind']=='ramp':
                merges[boundary['to_cell']]+=d['boundaries']['ramp_arrival:RM_C'+connector]['cross']+count(frames[0],connector)-count(frames[1],connector)
        assigned=[]
        for r in removed:
            _,bins,_=bin_frame(g,[[r['vehicle'],r['link'],1,r['pos'],0.,1.]],road,drop_before_start=True)
            for i,z in enumerate(bins):
                deleted[i]+=len(z)
                if z:assigned.append(dict(**r,cell=i))
        entry=d['boundaries']['source:'+road]['cross'];terminal=d['boundaries']['chain_end:'+road]['cross']
        try:cell_fluxes(old,new,entry,merges,exits,[0]*31,terminal)
        except ValueError as e:original_error=str(e)
        else:raise AssertionError('Original error was not reproduced')
        corrected=cell_fluxes(old,new,entry,merges,exits,deleted,terminal)
        assert corrected[-1]==terminal and sum(deleted)==1
        result['roads'][road]=dict(old=sum(old),new=sum(new),entry=entry,merges=sum(merges),off=sum(exits),terminal=terminal,
            missing_removal=sum(deleted),assigned_removals=assigned,original_error=original_error,corrected_internal_counts=corrected)
    assert len(removed)==6  # four urban losses, one on each mainline
    assert all(sha(Path(p))==v for p,v in pins.items())
    result['source_and_failed_artifacts_unchanged']=True
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:{x:v for x,v in r.items() if x not in ('corrected_internal_counts','assigned_removals')} for k,r in result['roads'].items()},ensure_ascii=False))

if __name__=='__main__':main()
