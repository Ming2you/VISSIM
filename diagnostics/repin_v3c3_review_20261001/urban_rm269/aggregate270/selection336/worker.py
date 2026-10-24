"""Isolated latest-model hooks around the unchanged canonical tangent worker."""
from pathlib import Path
from contextlib import ExitStack
import ast, hashlib, inspect, json, pickle, sys, textwrap, time, traceback

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]

def main():
    request_path,result_path,expected=sys.argv[1:4]
    out=Path(result_path).parent
    result={};started=time.perf_counter()
    try:
        from evaluation.controllers.sdmpc_tangent_runtime import install,Transform
        finder=install(ROOT,'reverse-v1')
        from evaluation.controllers import sdmpc_tangent_worker as canonical
        summary=json.loads((HERE.parent/'worker334/capture_v2/summary.json').read_bytes())
        data=Path(request_path).read_bytes()
        assert hashlib.sha256(data).hexdigest()==expected
        request=pickle.loads(data)
        mode=request['surrogate_evaluation'];assert mode in ('scalar','ad')
        from src.models.urban_queue_model import movement_specs
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_initial306.state_check import equal
        assert equal(request['owned'][0]._specs,movement_specs(request['owned'][0].cfg)), 'Stale follower movement cache'
        #The optional per-stock report calls float(Dual). Omit that redundant
        #diagnostic; complete owner costs, physical constraints and exported
        #ledger stocks remain. No model, gradient or constraint is removed.
        request['diagnostic_stock_costs']=False
        result['request_sha256']=expected
        for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        from src.controllers import rollout_endpoint as endpoint
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.branch_service315 import candidate as branch
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import enabled as transport
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc10_north325.candidate import enabled as north
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.native_routes329.candidate import enabled as routes
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook,verify_pending
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gate296.candidate import installed,geometry
        from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc108_geometry311.candidate import clock
        from evaluation.controllers.control_area_objective import get_ledger
        from evaluation.controllers.area_runtime import model_inventory
        #315 compiles source text dynamically, outside the import finder. Preserve
        #the exact same numeric AST transform there rather than lose AD primitives.
        original_compile=branch.compile_method
        def compile_instrumented(original,rates):
            source=textwrap.dedent(inspect.getsource(original));tree=ast.parse(source)
            match=ast.dump(ast.parse(branch.EXPRESSION,mode='eval').body)
            class Replace(ast.NodeTransformer):
                count=0
                def visit_BinOp(self,node):
                    if ast.dump(node)==match:
                        self.count+=1
                        return ast.copy_location(ast.parse('_branch_service315(spec, branch)',mode='eval').body,node)
                    return self.generic_visit(node)
            change=Replace();tree=change.visit(tree);assert change.count==1
            tree=Transform().visit(tree);ast.fix_missing_locations(tree)
            namespace=dict(original.__globals__)
            namespace['_branch_service315']=lambda spec,b:branch.service(spec,b,rates)
            exec(compile(tree,str(HERE/'worker.py')+':branch315','exec'),namespace)
            return namespace[original.__name__],hashlib.sha256(source.encode()).hexdigest()
        branch.compile_method=compile_instrumented
        evaluate=endpoint.evaluate_price_point;receipts=[];cfg=request['owned'][0].cfg
        def scoped(state,action,forecast,*args,**kw):
            assert len(receipts)==0,'Exactly one prediction per worker'
            began=time.perf_counter()
            with ExitStack() as stack:
                br=stack.enter_context(branch.enabled())
                tr=stack.enter_context(transport());ng=stack.enter_context(north());rt=stack.enter_context(routes())
                side=stack.enter_context(hook('source_path_current_physical_speed'))
                gate=stack.enter_context(installed(cfg,'aggregate_sc10_native_calendar',geometry(ROOT,cfg)))
                prehead=stack.enter_context(clock(cfg))
                point=evaluate(state,action,forecast,*args,**kw)
                for s in (state,*point.states):
                    get_ledger(s).assert_stocks(model_inventory(s,cfg));verify_pending(s)
            #Use the worker's numeric primal converter for receipts only.
            p=finder.ad.primal
            rows=[]
            for s in (state,*point.states):
                rows.append(dict(time_sec=p(s.time_sec),stocks={k:{a:p(v) for a,v in row.items()} for k,row in get_ledger(s).stocks.items()}))
            (out/'stocks.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n',encoding='utf8')
            receipts.append(dict(branch=br,transport_count=len(tr),north_count=len(ng),routes_count=len(rt),
                side_count=len(side['receipts']),gate_count=len(gate),prehead_count=len(prehead),
                conservation_states=4,endpoint_wall_sec=time.perf_counter()-began))
            return point
        endpoint.evaluate_price_point=scoped
        try:result.update(canonical.run(request,finder,result))
        finally:
            endpoint.evaluate_price_point=evaluate;branch.compile_method=original_compile
        assert len(receipts)==1
        result['latest_model_hooks']=receipts
        result['branch315_dynamic_ast_instrumented']=True
        result['optional_per_stock_cost_report_omitted']=True
    except Exception:result['error']=traceback.format_exc()
    result['wall_sec_including_imports']=time.perf_counter()-started
    Path(result_path).write_bytes(pickle.dumps(result,protocol=5))
    small={k:v for k,v in result.items() if k in ('request_sha256','error','scalar_sec','tangent_sec','reverse_sec','wall_sec_including_imports','latest_model_hooks','branch315_dynamic_ast_instrumented')}
    small['status']='failed_preserved' if 'error' in result else 'complete'
    (out/'completion.json').write_text(json.dumps(small,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(small,ensure_ascii=False),flush=True)
    return int('error' in result)

if __name__=='__main__':raise SystemExit(main())
