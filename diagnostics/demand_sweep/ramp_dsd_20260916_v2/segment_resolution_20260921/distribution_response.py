"""Diagnostic information gate before adding desired-speed transport.

Unlike the old mean-ratio oracle, evaluate the empirical E[min(V_FD,D)]
within each refined physical group and each side of the10643 partition.
This uses FUTURE native desired speeds; it is NEVER a control qualification.
"""
from pathlib import Path
import bisect,contextlib,gzip,hashlib,inspect,json,subprocess,sys,time
from collections import defaultdict
B=Path(__file__).resolve().parent;ROOT=B.parents[3];O=B/'distribution_response_v1';K=B.parent/'cohort_dynamics_20260920'
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')


def capped_mean(values,cap):
    if not values:raise ValueError('No observed desired-speed support')
    return sum(min(cap,v) for v in values)/len(values)


def extract():
    sources=c.load(B/'sources.json');chain={r['link']:r for r in c.G['chains']['FW_E']};bounds=c.G['bounds']['FW_E']
    branch=next(p for p in c.G['boundaries'] if p['connector']==10643)
    cut=branch['chain_pos_m'];cell=branch['from_cell']
    for arm in ('none','vsl'):
        source=sources[arm+'_s23'];path=ROOT/source['path'];rows=defaultdict(list);digest=hashlib.sha256();times=set();count=0
        before=path.stat();columns=None
        with path.open('rb') as stream:
            for raw in stream:
                digest.update(raw)
                if raw.startswith(b'$VEHICLE:'):
                    columns=raw.strip().split(b':',1)[1].decode().split(';');assert columns[9]=='DESSPEED';continue
                if not raw[:1].isdigit():continue
                sec=float(raw.split(b';',1)[0]);assert sec.is_integer()
                if not 2400<=sec<=2850:continue
                parts=raw.rstrip(b'\r\n').split(b';');assert len(parts)==20
                t=int(sec);times.add(t);link=int(parts[2])
                if link not in chain:continue
                x=chain[link]['offset_m']+float(parts[4])
                if not 0<=x<bounds[-1]:continue
                i=bisect.bisect_right(bounds,x)-1;lane=int(parts[3]);desired=float(parts[9])
                assert 0<desired<=250
                g=next(k for k in range(len(c.WIDTHS[i])) if lane<=sum(c.WIDTHS[i][:k+1]))
                side=('pre' if x<cut else 'post') if i==cell else 'all'
                rows[f'{t}:{i}:{g}:{side}'].append(desired);count+=1
        assert times==set(range(2400,2851)) and digest.hexdigest()==source['file_sha256']
        after=path.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
        save(O/(arm+'_observed.json'),dict(rows=rows,source=source,vehicles_over_time=count,
            geometry_sha256=c.sha(B/'geometry_200_branch_guard.json'),future_data=True,not_for_controller=True))
        print('extracted',arm,count,flush=True)


@contextlib.contextmanager
def oracle(spec,arm):
    from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
    from src.models import metanet as mn
    mode=spec['mode'];assert mode in ('mean_cap','distribution_cap')
    folder=Path(spec['observations']);observed=load(folder/(arm+'_observed.json'))
    assert observed['future_data'] and observed['not_for_controller']
    assert observed['geometry_sha256']==sha(B/'geometry_200_branch_guard.json')
    samples=observed['rows'];old=mn.effective_desired_speed_kmh
    # run_probe temporarily wraps advance with urban supply. Match the actual
    # core frame, not the wrapper currently installed on the class attribute.
    core_file=inspect.getsourcefile(PhysicalLaneGroups)
    audit=dict(mode=mode,future_native_desired_speed=True,not_for_controller=True,calls=0,
        supported_calls=0,empty_observed_group_calls=0,changed_calls=0,max_change=0.,no_vsl_calls=0)
    def desired(*args,**kwargs):
        frame=inspect.currentframe().f_back
        try:
            # The canonical audit calls twice (actual and nominal) from its
            # record_desired wrapper. Only physical group updates are targeted.
            while frame is not None and not (frame.f_code.co_name=='advance' and frame.f_code.co_filename==core_file):
                frame=frame.f_back
            if frame is None:return old(*args,**kwargs)
            loc=frame.f_locals;plant=loc['self']
            if plant.road!='FW_E':return old(*args,**kwargs)
            assert not kwargs and len(args)==10 and (not plant.hadi or plant.hadi['relaxation']=='fd_cap')
            i,g=loc['i'],loc['g'];t=int(loc['state'].time_sec)
            side=loc['side'] if i in plant.partitions else 'all'
            key=f'{t}:{i}:{g}:{side}';values=samples.get(key)
            baseline=old(*args);audit['calls']+=1
            if not args[5]:audit['no_vsl_calls']+=1
            if not values:
                audit['empty_observed_group_calls']+=1;return baseline
            # Preserve the same FD and current density; replace ONLY numeric
            # VSL capping with the actually exposed desired-speed distribution.
            uncapped=list(args);uncapped[5]=False;fd=old(*uncapped)
            value=min(fd,sum(values)/len(values)) if mode=='mean_cap' else capped_mean(values,fd)
            audit['supported_calls']+=1;audit['changed_calls']+=int(abs(value-baseline)>1e-10)
            audit['max_change']=max(audit['max_change'],abs(value-baseline))
            return value
        finally:del frame
    mn.effective_desired_speed_kmh=desired
    try:
        yield audit
        assert audit['calls']>0 and audit['supported_calls']>0
    finally:mn.effective_desired_speed_kmh=old


def main():
    # Import calibration only in this CLI, before the legacy harness adjusts
    # sys.path. The runtime context manager must not import its namesake there.
    global f,c
    import full_calibration as f
    c=f.c
    if sys.argv[1]=='extract':extract();return
    assert sys.argv[1] in ('run','resume')
    resume=sys.argv[1]=='resume';suffix='_v2' if resume else ''
    modes=('mean_cap','distribution_cap') if resume else ('disabled','mean_cap','distribution_cap')
    initial=c.load(B/'vsl_response_v1/hadi_fd_cap_r2_selected.json')['selected']['spec']
    protocol_path=O/('protocol'+suffix+'.json');assert not protocol_path.exists()
    save(protocol_path,dict(purpose='Falsify desired-speed exposure/dispersion bottleneck on recalibrated model before building transport',
        future_observations=True,not_for_controller=True,no_calibration=True,qualified=False,
        modes=list(modes),initial_s=2400,end_s=2850,arms=['none','vsl'],
        resumed_after='dd_mean_cap core-frame lookup failure; original output retained' if resume else None,
        same_fd_law_both_arms=True,empty_support='Original speed target; count every unsupported call; this is not an information-theoretic upper bound.',
        source_pins={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),B/'run.py',O/'none_observed.json',O/'vsl_observed.json']}))
    results=load(O/'results.json')['results'] if resume else []
    if resume:assert len(results)==1 and results[0]['mode']=='disabled'
    for mode in modes:
        spec={**initial,'name':'dd_'+mode+suffix,'output_group':O.name,'arms':['none','vsl']}
        spec.pop('control_response_fit',None)
        if mode!='disabled':spec['diagnostic_desired_distribution']=dict(mode=mode,observations=str(O),future_data=True)
        path=O/(spec['name']+'.json');save(path,spec)
        with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        result=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        rows={};checks={}
        for arm in ('none','vsl'):
            p=f.load_prediction(O/spec['name']/f'refined_guard1_{arm}.json');checks[arm]=c.screen(p)
            reference=f.load_prediction(B/'vsl_response_v1/vr_hadi_fd_cap_r2_validation'/f'refined_guard1_{arm}.json')
            if mode=='disabled':assert p==reference
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
            if arm=='none':
                rows=dict(train=c.score(p),late=c.score(p,10,15))
            else:rows['vsl_delta']=result['deltas']['vsl']
        record=dict(mode=mode,numerics=checks,**rows,future_data=mode!='disabled',qualified=False)
        results.append(record);save(O/('results'+suffix+'.json'),dict(results=results,production_adopted=False));print(record,flush=True)


if __name__=='__main__':main()
