"""Prove a selection-only source change and reconstruct saved decision inputs."""
from pathlib import Path
import ast, copy, hashlib, json, pickle

HERE=Path(__file__).resolve().parent; A=HERE.parent; S=A/'selection336'; ROOT=HERE.parents[4]
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(HERE/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')

def compatible_sources():
    proof=read(S/'seed_patch.json'); source=ROOT/'evaluation/controllers/sdmpc.py'
    assert sha(source)==proof['after_sha256']
    assert sha(S/'sdmpc_before_seed_fix.py')==proof['before_sha256']
    class Strip(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name=='solve': return None
            if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):
                node.body=node.body[1:]
            return self.generic_visit(node)
    trees=[ast.dump(Strip().visit(ast.parse(p.read_text(encoding='utf8'))),include_attributes=False)
           for p in (source,S/'sdmpc_before_seed_fix.py')]
    assert trees[0]==trees[1], 'Prediction or other executable functions changed'
    pins=read(S/'execution.json')['source_pins']; changes=[]
    for p,h in pins.items():
        actual=sha(p)
        if actual!=h:
            assert Path(p).resolve()==source.resolve() and h==proof['before_sha256']
            changes.append(p);pins[p]=actual
    assert len(changes)==1
    save('source_compatibility.json',dict(status='selection_only_change_verified',changed=changes,
        all_other_execution_pins_match=True,prediction_AST_identical=True,source_pins=pins,
        scope='Only solve changed executable code; helper docstring excluded from AST comparison'))
    workerpins=read(A/'worker334/capture_v2/summary.json')['source_pins']
    for p,h in workerpins.items():
        if sha(p)!=h:
            assert Path(p).resolve()==source.resolve() and h==proof['before_sha256']
            workerpins[p]=sha(p)
    save('worker_pins.json',dict(source_pins=workerpins))
    return pins

def inputs():
    from evaluation.controllers import vissim_stackelberg_adapter as adapter,sdmpc_sequence as seq
    from evaluation.controllers.runtime_setup import install_worker_runtime
    from evaluation.controllers.joint_owner_game import build_ownership
    from evaluation.controllers.joint_owner_neighbors import build_fixed_move_box
    from evaluation.controllers.area_follower_objective import joint_decision_move_limits
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
    old=pickle.loads((S/'workers/0001/request.pickle').read_bytes()); request=copy.deepcopy(old)
    source=ROOT/'evaluation/controllers/sdmpc.py'
    for p,h in request['bootstrap']['runtime_sources'].items():
        if sha(p)!=h:
            assert Path(p).resolve()==source.resolve() and h==read(S/'seed_patch.json')['before_sha256']
            request['bootstrap']['runtime_sources'][p]=sha(p)
    follower,state,reference,forecast=request['owned']; cfg=follower.cfg
    frozen=pickle.dumps(request['owned'],protocol=5)
    install_worker_runtime(adapter,cfg,request['bootstrap']['state_json'],request['bootstrap']['detector_mapping'])
    assert pickle.dumps(request['owned'],protocol=5)==frozen
    runtime=copy.deepcopy(request['runtime']); runtime['_PHASE_VECTOR_FOLLOWER']['ref']=follower
    for name in tuple(vars(adapter)):
        if name.startswith('_') and name.isupper() and isinstance(getattr(adapter,name),(dict,list,set)) and name not in runtime:delattr(adapter,name)
    for name,value in runtime.items():setattr(adapter,name,value)
    plan={'controllers':{signal[2:]:node for signal,node in cfg.network.signal_actuation_contract['nodes'].items()}}
    mapping_path=ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
    owner=build_ownership(cfg,read(mapping_path),plan,segment_dsd_controls=adapter._segment_dsd_controls)
    box=build_fixed_move_box(owner,seq.first_action(reference),cfg,joint_decision_move_limits(follower))
    coord=seq.SequenceCoordinates(cfg,reference,box,cfg.network.sdmpc_options)
    assert equal(coord.axes,request['axes']) and equal(coord.green_vectors,request['green_vectors'])
    original=read(S/'full3300/coordinates.json')
    assert equal(coord.axes,original['axes'])
    assert equal([coord.lower.tolist(),coord.upper.tolist()],original['bounds'])
    save('coordinate_check.json',dict(status='canonical_reconstructed',axes=len(coord.axes),
        green_vectors_exact=True,lower=coord.lower.tolist(),upper=coord.upper.tolist(),
        saved_bounds=original['bounds'],seed_valid=bool(coord.valid(coord.encode(request['action']))),
        seed_three_blocks=coord.validate(request['action']),move_box_entries=len(box.entries)))
    return request,coord,plan

if __name__=='__main__':
    compatible_sources(); r,c,p=inputs()
    (HERE/'prepared.pickle').write_bytes(pickle.dumps((r,c,p),protocol=5))
    print('PREPARE337_OK',len(c.axes),flush=True)
