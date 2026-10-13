"""Two declared continuous RM responses, reusing334 frozen model and anchor."""
from pathlib import Path
import copy,hashlib,json,pickle
HERE=Path(__file__).resolve().parent;W=HERE.parent/'worker334'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())
def main():
    proof=read(W/'assessment.json');assert proof['status']=='same_latest_model_continuous_scalar_ad_passed'
    for p,h in proof['source_pins'].items():assert sha(Path(p))==h,p
    req=pickle.loads((W/'capture_v2/request.pickle').read_bytes())
    cfg=req['owned'][0].cfg
    from evaluation.controllers import sdmpc_sequence as seq,signal_actuation_contract as signals,vissim_stackelberg_adapter as adapter
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.response332.commands import pair
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    runtime=copy.deepcopy(req['runtime'])
    runtime['_PHASE_VECTOR_FOLLOWER']['ref']=req['owned'][0]
    for k,v in runtime.items():setattr(adapter,k,v)
    anchor=req['action'];eps=copy.deepcopy(seq.actions(anchor,3))
    eps[0].diagnostics['rw_meter_green_RM_C10681']+=0.0001
    candidates={'epsilon':seq.pack(eps),'release':seq.pack(pair(req['owned'][2],cfg,anchor)['release'])}
    rows={}
    for name,action in candidates.items():
        for i,(b,a) in enumerate(zip(seq.actions(action,3),seq.actions(anchor,3))):
            for k in ('green_times','offsets','vsl','N_P_star','N_UF_star','inflow_outflow_allocation'):
                assert equal(getattr(b,k),getattr(a,k)),k
            for r in a.ramp_metering:
                if r!='RM_C10681':assert b.diagnostics['rw_meter_green_'+r]==a.diagnostics['rw_meter_green_'+r]
            if name=='release':signals.validate_writer(b,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
        out=HERE/name
        child=copy.deepcopy(req);child['action']=action
        if out.exists():
            #A previous preparation stopped before launching anything when the
            #writer loaded its default clock rather than this request's runtime.
            data=(out/'request.pickle').read_bytes();existing=pickle.loads(data)
            assert equal(existing['action'],action) and equal(existing['owned'],child['owned'])
            assert not (HERE/(name+'_run')).exists()
        else:
            out.mkdir();data=pickle.dumps(child,protocol=5);(out/'request.pickle').write_bytes(data)
        summary=read(W/'capture_v2/summary.json');summary.update(request_sha256=hashlib.sha256(data).hexdigest(),
            derived_from_sha=sha(W/'capture_v2/request.pickle'),variant=name,model_unchanged=True)
        (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
        rows[name]=dict(greens=[a.diagnostics['rw_meter_green_RM_C10681'] for a in seq.actions(action,3)],
                       finite_writer_qualified=name=='release',request_sha256=summary['request_sha256'])
    #Reuse the exact qualified hook and worker code; alter only request/output paths.
    source=(W/'worker.py').read_text(encoding='utf8')
    source=source.replace("out=HERE/(sys.argv[2] if len(sys.argv)>2 else mode);out.mkdir(exist_ok=False)",
                          "job=sys.argv[2];assert job in ('epsilon','release');out=HERE/(job+'_run');out.mkdir(exist_ok=False)")
    source=source.replace("HERE/'capture_v2/summary.json'","HERE/job/'summary.json'")
    source=source.replace("HERE/'capture_v2/request.pickle'","HERE/job/'request.pickle'")
    (HERE/'worker.py').write_text(source,encoding='utf8')
    plan=dict(stage='prepared',budget=dict(scalar=2,ad=0,optimization=0,native=0,fits=0),
        preparation_correction='Writer runtime cache now restored from canonical request; first preparation had no predictions and preserved identical epsilon request.',
        jobs=rows,initial_model_source=str(W/'capture_v2/request.pickle'),
        worker_source_sha=sha(W/'worker.py'),worker_sha=sha(HERE/'worker.py'),
        scope='One first-block +0.0001s directional check and one executable g4/6/8 isolated10681 contrast; no coefficient search',
        goal_complete=False)
    (HERE/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8')
    print(json.dumps(rows))
if __name__=='__main__':main()
