"""Fit one cell22 anticipation branch, without using VSL outcomes."""
import copy
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent
assert h.read(HERE/'status.json')['status']=='complete_diagnostic_only'
assert not (HERE/'proposal.json').exists(), 'One proposal only'
h.save(HERE/'fit_protocol.json',dict(parameter='cell22 anticipation.downstream_ge_local multiplier',bounds=[.1,1.],
    training='67 late nominal110 only; cell22 all3 lanes,30s blocks with>=4 observed5s samples.',
    reason='Current native-state first30s mean rate observed+1.079, model-9.161 with anticipation-8.201kmh/s. Other-state29 also overdecelerates. Fit this negative-gradient-response magnitude only.',
    budget=dict(fit=1,autonomous450=8,independent450=0,new_native=0,new_FZP=0),
    fixed='All FD, merge, recovery, other anticipation branches, VSL law, physical flows/receiving/storage, objective, commands and input forecasts.',
    gate='Same >=.5vehh paired signs, >=10% response loss improvement, absolute<=110%, predicted-best actual regret<=.5. No widening bounds or further fit on failure.',
    limits='1s unclipped equation versus5s native finite-difference means;30s averaging reduces noise but does not make temporal operators identical. Training fit is not autonomous qualification.'))
rows=h.read(HERE/'rows.json.gz')
train=[r for r in rows if r['case']=='s67_late' and r['arm']=='release' and r['cell']==22 and 'model' in r]
blocks=[]
for lane in (1,2,3):
    for block in range(15):
        rr=[r for r in train if r['lane']==lane and int(round((r['time_s']-2670.1)/5))//6==block]
        if len(rr)<4:continue
        xx=[];yy=[]
        for r in rr:
            m=r['model'];active=m['downstream_rho']>=m['rho']
            xx.append(m['anticipation'] if active else 0.)
            yy.append(r['observed_rate']-m['relaxation']-m['convection']-(0. if active else m['anticipation']))
        blocks.append(dict(lane=lane,block=block,samples=len(rr),x=sum(xx)/len(xx),y=sum(yy)/len(yy)))
assert len(blocks)>=30
weight=.1*len(blocks);den=sum(r['x']**2 for r in blocks)+weight
unconstrained=(sum(r['x']*r['y'] for r in blocks)+weight)/den
z=max(.1,min(1.,unconstrained))
gradient=2*(sum(r['x']*(r['x']*z-r['y']) for r in blocks)+weight*(z-1))
assert gradient>=-1e-8 if z==.1 else gradient<=1e-8 if z==1. else abs(gradient)<1e-8
from diagnostics.repin_v3c3_review_20261001.jin_macro111 import run as common
from evaluation.controllers import lane_plant_runtime as lpr
from evaluation.controllers.freeway_fd import cell_state_response
context,_,_=common.setup();parent=h.R/'lane_state132/eval_01'
cfg=lpr.load_sources(parent/'manifest.json')['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
config=h.read(parent/'reference_config.json');original=copy.deepcopy(config)
branch=config['freeway']['state_response']['FW_E']['cell_overrides']['22']['anticipation']
before=branch['downstream_ge_local'];branch['downstream_ge_local']*=z
dest=HERE/'candidate';dest.mkdir();h.save(dest/'reference_config.json',config)
manifest=h.read(parent/'manifest.json');manifest['sources']['reference_config']=dict(path=(dest/'reference_config.json').relative_to(h.ROOT).as_posix(),sha256=h.sha(dest/'reference_config.json'))
manifest['qualification']='Unqualified137 cell22 native-state anticipation proposal. Requires shared124 runtime; not a production manifest.'
h.save(dest/'manifest.json',manifest)
ccfg=lpr.load_sources(dest/'manifest.json')['component']._config('FW_E',context['parameters']['by_direction']['FW_E'])
assert ccfg.network.freeway_segment_params==cfg.network.freeway_segment_params
for i in range(31):
    old=copy.deepcopy(cell_state_response(cfg.network,'FW_E',i));new=cell_state_response(ccfg.network,'FW_E',i)
    if i==22:old['anticipation']['downstream_ge_local']*=z
    assert old==new,(i,old,new)
restored=copy.deepcopy(config);restored['freeway']['state_response']['FW_E']['cell_overrides']['22']=original['freeway']['state_response']['FW_E']['cell_overrides']['22'];assert restored==original
pins=h.read(HERE/'verification.json')['input_sha256'];pins[str(Path(__file__))]=h.sha(__file__)
for p in [HERE/'rows.json.gz',HERE/'fit_protocol.json',parent/'manifest.json',parent/'reference_config.json']:pins[str(p)]=h.sha(p)
for p,v in pins.items():assert h.sha(p)==v,p
h.save(HERE/'fit_blocks.json',blocks)
h.save(HERE/'proposal.json',dict(z=[z],before=before,after=branch['downstream_ge_local'],unconstrained=unconstrained,gradient=gradient,
    conditional_mse_before=sum((r['x']-r['y'])**2 for r in blocks)/len(blocks),conditional_mse_after=sum((r['x']*z-r['y'])**2 for r in blocks)/len(blocks),
    block_count=len(blocks),rows_used=sum(r['samples'] for r in blocks),input_sha256=pins,core_binding_verified=True))
print('cell22 nu_ge',before,'->',branch['downstream_ge_local'],'multiplier',z)
