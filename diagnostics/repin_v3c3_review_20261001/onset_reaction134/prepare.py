"""One bounded two-coefficient proposal from current-state reaction evidence."""
import copy
import itertools
import math
from pathlib import Path
import numpy as np
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
from diagnostics.repin_v3c3_review_20261001.onset_reaction134.check import load_frames

HERE=Path(__file__).resolve().parent
assert h.read(HERE/'status.json')['status']=='complete_diagnostic_only'
assert not (HERE/'proposal.json').exists(),'Keep the first proposal; no repeated fit'
rows=h.read(HERE/'rows.json.gz')
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.freeway_fd import cell_state_response
context,_,_=common.setup()
parent=h.R/'lane_state132/eval_01'
model=lpr.load_sources(parent/'manifest.json')['component']
cfg=model._config('FW_E',context['parameters']['by_direction']['FW_E'])
pins=h.read(HERE/'verification.json')['input_sha256']
pins[str(Path(__file__))]=h.sha(__file__)

# The trial region uses aggregate cell18 speed at its inlet. Keep the first
# physically mapped-lane calculation as an explicitly different diagnostic.
# The correction affects only cell19, never the cell21 fit below.
corrected=copy.deepcopy(rows)
for case,arm,path in [('s67_late','release',h.F/'flow67/release_frames.json.gz'),('s29_late','hold',h.F/'vsl_native_exposure/s29_late_hold_frames.json.gz')]:
    frames=load_frames(path)
    for r in corrected:
        if (r['case'],r['arm'],r['cell'])!=(case,arm,19) or 'model' not in r:continue
        values=[z['speed_kmh'] for z in frames[r['time_s']].values() if z['cell']==18]
        assert values
        r['physically_mapped_inlet_model']=copy.deepcopy(r['model'])
        m=r['model'];m['upstream_speed']=sum(values)/len(values)
        m['convection']=r['v0']*(m['upstream_speed']-r['v0'])/(cfg.network.freeway_segment_params['FW_E'][19]['segment_length_km']*3600)
        m['premerge_rate']=max(cfg.network.v_min,r['v0']+m['relaxation']+m['convection']+m['anticipation'])-r['v0']
        m['pre_exit_rate']=m['premerge_rate']
        m['inlet_basis']='Current aggregate cell18 speed, matching shared124/132 runtime.'
h.save(HERE/'inlet_correction.json',dict(reason='Initial134 used physically mapped lane speed at cell19; shared124/132 actually uses aggregate upstream18. Original lane ledger unaffected. Preserve both and use canonical-inlet value in interpretation.',
    rows=[r for r in corrected if 'physically_mapped_inlet_model' in r],fit_cell21_unchanged=True))

train=[r for r in corrected if r['case']=='s67_late' and r['arm']=='release' and r['cell']==21 and 'model' in r and r['model']['merge_known']]
blocks=[]
for lane in (1,2,3):
    for j in range(15):
        rr=[r for r in train if r['lane']==lane and int(round((r['time_s']-2670.1)/5))//6==j]
        if len(rr)<4:continue
        a=[];b=[]
        for r in rr:
            m=r['model'];lower=m['downstream_rho']<m['rho']
            a.append([m['anticipation'] if lower else 0.,-m['merge_loss']])
            b.append(r['observed_rate']-m['relaxation']-m['convection']-(0. if lower else m['anticipation']))
        blocks.append(dict(lane=lane,block=j,samples=len(rr),x=np.mean(a,axis=0).tolist(),y=float(np.mean(b))))
x=np.array([r['x'] for r in blocks]);y=np.array([r['y'] for r in blocks]);assert len(blocks)>=30
rank=int(np.linalg.matrix_rank(x));assert rank==2
lower=np.array([.5,0.]);upper=np.array([2.,1.5]);weight=math.sqrt(.1*len(blocks))
xx=np.vstack([x,weight*np.eye(2)]);yy=np.r_[y,weight*np.ones(2)]
candidates=[]
for state in itertools.product((-1,0,1),repeat=2):
    z=np.zeros(2);fixed=[i for i,s in enumerate(state) if s];free=[i for i,s in enumerate(state) if not s]
    for i in fixed:z[i]=lower[i] if state[i]<0 else upper[i]
    if free:z[free]=np.linalg.lstsq(xx[:,free],yy-xx[:,fixed]@z[fixed],rcond=None)[0]
    if np.all(z>=lower-1e-10) and np.all(z<=upper+1e-10):candidates.append(z)
z=min(candidates,key=lambda v:float(np.sum((xx@v-yy)**2)))
gradient=2*xx.T@(xx@z-yy)
for i in range(2):
    assert (gradient[i]>=-1e-7 if abs(z[i]-lower[i])<1e-8 else gradient[i]<=1e-7 if abs(z[i]-upper[i])<1e-8 else abs(gradient[i])<1e-7)
config=h.read(parent/'reference_config.json');original=copy.deepcopy(config)
local=config['freeway']['state_response']['FW_E']['cell_overrides']['21']
old_nu=local['anticipation']['downstream_lt_local'];old_delta=local['delta_merge']
local['anticipation']['downstream_lt_local']*=float(z[0]);local['delta_merge']*=float(z[1])
dest=HERE/'candidate';dest.mkdir()
h.save(dest/'reference_config.json',config)
manifest=h.read(parent/'manifest.json');manifest['sources']['reference_config']=dict(path=(dest/'reference_config.json').relative_to(h.ROOT).as_posix(),sha256=h.sha(dest/'reference_config.json'))
manifest['qualification']='Unqualified134 native-state cell21 two-coefficient proposal; shared124 source needed. Not autonomous or fullOmega qualification.'
h.save(dest/'manifest.json',manifest)
candidate=lpr.load_sources(dest/'manifest.json')['component']
ccfg=candidate._config('FW_E',context['parameters']['by_direction']['FW_E'])
assert ccfg.network.freeway_segment_params==cfg.network.freeway_segment_params
for i in range(31):
    before=copy.deepcopy(cell_state_response(cfg.network,'FW_E',i));after=cell_state_response(ccfg.network,'FW_E',i)
    if i==21:
        before['anticipation']['downstream_lt_local']*=float(z[0]);before['delta_merge']*=float(z[1])
    assert before==after,(i,before,after)
restored=copy.deepcopy(config)
restored['freeway']['state_response']['FW_E']['cell_overrides']['21']=original['freeway']['state_response']['FW_E']['cell_overrides']['21']
assert restored==original
for p,digest in pins.items():assert h.sha(p)==digest,p
h.save(HERE/'fit_blocks.json',blocks)
h.save(HERE/'proposal.json',dict(z=z.tolist(),parameters=['cell21 anticipation.downstream_lt_local multiplier','cell21 delta_merge multiplier'],
    before=dict(nu=old_nu,delta=old_delta),after=dict(nu=local['anticipation']['downstream_lt_local'],delta=local['delta_merge']),
    bounds=[lower.tolist(),upper.tolist()],block_count=len(blocks),rows_used=sum(r['samples'] for r in blocks),rank=rank,condition_number=float(np.linalg.cond(x)),
    gradient=gradient.tolist(),active_bounds=[bool(abs(z[i]-lower[i])<1e-8 or abs(z[i]-upper[i])<1e-8) for i in range(2)],
    conditional_linear_mse_before=float(np.mean((x@np.ones(2)-y)**2)),conditional_linear_mse_after=float(np.mean((x@z-y)**2)),
    interpretation='One regularized bounded2D linear least-squares proposal on unclipped1s reaction versus5s observed derivative, averaged30s. This is not fitting an autonomous trajectory or proving a causal merge loss. Runtime clamps and all state/flow dynamics are tested next.',
    training='67 late nominal110 only; all3 cell21 lanes, >=4 native5s samples per30s block. No VSL outcomes in fit. All four67 arms remain training-state validation,29late is other-state validation previously inspected.',
    autonomous_budget=8,additional_fits=0,scope='FW_E31+4on/4off, not wholeOmega. Original source forecast, current-only states, all coefficients except these2 untouched.',
    gate='Compared to frozen132: >=.5vehh pair signs, all-pair response>=10% improvement, absolute<=110%, predicted-best actual regret<=.5. No passing conditional-fit claim.',
    input_sha256=pins,core_binding_verified=True))
print((HERE/'proposal.json').read_text(encoding='utf-8'))
