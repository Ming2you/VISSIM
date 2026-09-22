"""Freeze matched VSL strength/location forecasts, then test native responses.

Reuse the conserved prediction runner, fixed-profile execution and native
postprocessor. New policy data is identification data, not an unused seed.
"""
from pathlib import Path
import copy,datetime,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
import vsl_response as v
from prepare import save,table
from diagnostics.fast_fixed_profile import prepare
from evaluation.controllers.desired_speed_transport import SpeedDistribution
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.segment_resolution_20260921 import vsl_spatial_native as native
c=v.c;f=v.f;B=v.B;ROOT=v.ROOT;K=v.K;O=B/'vsl_strength_v1'
POLICIES={'both100':(100,100),'up100':(100,120),'both80':(80,80),'up80':(80,120)}
SOURCE=K/'route_state_native_v1/none_s23/source/baseline.inpx'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def sampled_costs(p):
    main=[r for r in p['lane_groups']['FW_E'] if r['time_s']%5==0]
    on=[r for r in p['ramps'] if r['road']=='FW_E' and r['end_sec']%5==0]
    off=[r for r in p['ports'] if r['road']=='FW_E' and r['time_s']%5==0]
    expected=set(range(2405,2851,5))
    assert {r['time_s'] for r in main}=={r['end_sec'] for r in on}=={r['time_s'] for r in off}==expected
    assert len(main)==len(expected)*sum(map(len,c.WIDTHS)) and len(on)==len(off)==len(expected)*4
    return dict(mainline=sum(r['n_veh'] for r in main)*5/3600,
        on=sum(r['end']['connector_veh'] for r in on)*5/3600,off=sum(r['n_veh'] for r in off)*5/3600)


def setup():
    assert not (O/'protocol.json').exists()
    root=ET.parse(SOURCE).getroot();distributions={}
    for no in (80,100,120):
        x=next(x for x in root.findall('./desSpeedDistributions/desSpeedDistribution') if int(x.get('no'))==no)
        points=tuple((float(p.get('fx')),float(p.get('x'))) for p in x.findall('./speedDistrDatPts/speedDistributionDataPoint'))
        distributions[str(no)]={'points':points,**SpeedDistribution(points).moments()}
    save(O/'protocol.json',dict(purpose='Identify response to a stronger VSL with and without downstream restriction, after fixed100 response failed parameter/resolution/constraint checks.',
        policies=POLICIES,new_native=['both80','up80'],reused_native=['none','both100','up100'],
        stronger_policy='Native120 ->100 at2400 ->80 at2550, then hold; downstream nominal120 in upstream-only policies. Existing20/150s change constraint retained.',
        seed=23,start_s=2400,forecast_end_s=2850,native_end_s=3000,recording_s=5,
        network_sha256=sha(SOURCE),physical_sha256=native.old.physical_hash(root),distributions=distributions,
        fixed=['network','demand','routes','signals','RM OFF','seed','initial2400 state','DSD positions','plant coefficients','dt1 diagnostic integration','TTT waiting costs'],
        model_semantics='Existing cell-center DSD mapping and numeric FD cap retained. Native IDs are distributions, not deterministic speed caps. No cohort exposure correction silently added.',
        gates=['Freeze predictions before new native outcomes','Prefix original9 columns common5s exact','LDP/apply-time VSL readback/untargeted snapshot PASS','No unexplained disappearance counted as exit','Component costs use common5s samples in every arm','Conservation and spatial discharge inspection'],
        future_inputs=False,fit=False,independent_seed=False,production_adopted=False,qualified=False,
        source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),B/'run.py',B/'vsl_spatial_native.py',v.O/'vr_hadi_fd_cap_r2_validation.json',ROOT/'diagnostics/fast_fixed_profile.py',ROOT/'diagnostics/fast_nc_run.ps1',ROOT/'diagnostics/fast_nc_runner.vbs']}))
    template=c.load(K/'route_state_native_v1/vsl_s23/profile.json')
    for name in ('both80','up80'):
        folder=O/name
        if folder.exists():assert name=='both80' and (folder/'profile_rejected_step.json').exists() and not (folder/'prepared').exists()
        else:folder.mkdir()
        up,down=POLICIES[name]
        profile=copy.deepcopy(template);profile.update(network_sha256=sha(SOURCE),vehicle_record_interval_sec=5)
        assert profile['seed']==23 and profile['terminal_sec']==3000 and not profile['meter_commands']
        for row in profile['vsl_commands']:
            assert 51<=row['dsd_no']<=58 and 2400<=row['time_s']<=3000
            target=up if row['dsd_no']<=54 else down
            row['speed_id']=max(100,target) if row['time_s']==2400 else target
        save(folder/'profile.json',profile);prepare(SOURCE,folder/'profile.json',folder/'prepared')
        after=ET.parse(folder/'prepared/network/baseline.inpx').getroot()
        assert native.old.physical_hash(root)==native.old.physical_hash(after)
    print('Prepared two native profiles; predictions must be frozen before execution',flush=True)


def freeze():
    assert not (O/'frozen_predictions.json').exists()
    initial=c.load(v.O/'vr_hadi_fd_cap_r2_validation.json');predictions=[]
    for label,(up,down) in POLICIES.items():
        spec=copy.deepcopy(initial);spec.update(name='vs_'+label,output_group=O.name,arms=['none','vsl'],
            diagnostic_vsl_policy={str(i):[max(100,up if i<=54 else down),up if i<=54 else down,up if i<=54 else down] for i in range(51,59)})
        path=O/(spec['name']+'.json');save(path,spec)
        with (O/(spec['name']+'_process.log')).open('x',encoding='utf-8') as log:
            subprocess.run([sys.executable,'-B','-X','utf8',str(B/'run.py'),'refined_guard1',str(path)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        pins={};numerics={};values={}
        for arm in spec['arms']:
            p=f.load_prediction(O/spec['name']/f'refined_guard1_{arm}.json');numerics[arm]=c.screen(p)
            assert numerics[arm]['passed']
            actual_file=O/spec['name']/f'refined_guard1_{arm}.json.gz';pins[str(actual_file.relative_to(ROOT))]=sha(actual_file)
            old=f.load_prediction(v.O/'vr_hadi_fd_cap_r2_validation'/f'refined_guard1_{arm}.json')
            if arm=='none' or label=='both100':assert p==old,'Command hook changed the old forecast'
            for key in ('cells','flows'):
                assert [r for r in p[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
            # Re-score native-comparable output at5s. Retain original1s costs
            # separately; no mixing of quadrature conventions.
            values[arm]=sampled_costs(p)
            command_rows=c.load(O/spec['name']/f'vsl_policy_{arm}.json')['window_steps']
            snapshots={tuple(sorted(r['vsl_commands'].items())) for r in command_rows}
            assert len(snapshots)==(2 if arm=='vsl' and up==80 else 1)
            for row in command_rows:
                step=int((row['time_s']-2400)//150)
                actual_up,actual_down=spec['diagnostic_vsl_policy']['51'][step],spec['diagnostic_vsl_policy']['55'][step]
                expected={float(actual_up),float(actual_down),120.} if arm=='vsl' else {120.}
                assert set(row['vsl_commands'].values())==expected
        raw=c.load(K/('segment_resolution_20260921_cal_'+spec['name'])/'result.json')
        delta={key:values['vsl'][key]-values['none'][key] for key in values['none']}
        delta['total']=sum(delta.values())
        record=dict(policy=label,numerics=numerics,delta_1s=raw['deltas']['vsl'],values_common5s=values,delta_common5s=delta,prediction_pins=pins)
        predictions.append(record);save(O/'prediction_progress.json',predictions);print(json.dumps(record),flush=True)
    # No new native has begun: fail if a case run directory already exists.
    assert not any((O/name/'run').exists() for name in ('both80','up80'))
    save(O/'frozen_predictions.json',dict(frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        predictions=predictions,new_native_not_started=True,qualified=False,future_inputs=False,production_adopted=False,
        source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),B/'run.py',O/'protocol.json']}))


def analyze():
    frozen=c.load(O/'frozen_predictions.json')
    for p,h in frozen['source_pins'].items():assert sha(ROOT/p)==h
    for result in frozen['predictions']:
        for p,h in result['prediction_pins'].items():assert sha(ROOT/p)==h
    native.O=O
    results=[];reference=v.O/'upstream_native'
    for label,filename in [('none','none_summary.json'),('both100','both_zones_summary.json'),('up100','upstream_only_summary.json')]:
        result=c.load(reference/filename);assert sha(ROOT/result['path'])==result['sha256']
        result['arm']=label
        for row in result['rows']+result['flows']:row['arm']=label
        errors=c.load(reference/(dict(none='none',both100='both_zones',up100='upstream_only')[label]+'_errors.json'))
        save(O/(label+'_errors.json'),errors);results.append(result)
    for name in ('both80','up80'):
        run=O/name/'run';receipt=c.load(run/'run.json')
        start=datetime.datetime.fromisoformat(receipt['started']).astimezone(datetime.timezone.utc)
        assert start>datetime.datetime.fromisoformat(frozen['frozen_at_utc'])
        result=native.extract(name,run);save(O/(name+'_summary.json'),result);results.append(result);print('post-extracted',name,flush=True)
    assert len({r['prefix_sha256'] for r in results})==1
    assert all(r['initial']==results[0]['initial'] for r in results)
    rows=[x for r in results for x in r['rows']];flows=[x for r in results for x in r['flows']]
    table(O/'regions_common5s.csv',rows);table(O/'crossings_common5s.csv',flows)
    costs=[]
    for start,end in native.WINDOWS:
        parts={r['arm']:{k:next(x['ttt_veh_h'] for x in rows if x['arm']==r['arm'] and x['start']==start and x['end']==end and x['zone']==k) for k in ('mainline','on','off')} for r in results}
        for label,values in parts.items():
            total=sum(values.values());delta={k:value-parts['none'][k] for k,value in values.items()}
            costs.append(dict(arm=label,start=start,end=end,total=total,delta_total=sum(delta.values()),**{'delta_'+k:x for k,x in delta.items()}))
    table(O/'costs_common5s.csv',costs)
    compare=[]
    for pred in frozen['predictions']:
        actual=next(x for x in costs if x['arm']==pred['policy'] and x['start']==2400 and x['end']==2850)
        compare.append(dict(policy=pred['policy'],actual=actual,predicted=pred['delta_common5s']))
    save(O/'native_comparison.json',dict(compare=compare,costs=costs,prefix_common5s_original9_exact=True,
        future_inputs=False,new_native=2,independent_seed=False,qualified=False,production_adopted=False,
        scope='East mainline+4on+4off, not full Omega. Common5s right endpoint costs; abnormal-removal ledgers must be reviewed separately.',
        native_pins={r['path']:r['sha256'] for r in results}))
    print(json.dumps(compare,indent=2))


if __name__=='__main__':
    {'setup':setup,'freeze':freeze,'analyze':analyze}[sys.argv[1]]()
