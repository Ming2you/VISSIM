from pathlib import Path
root=Path(r"C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926/diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270")
source=(root/'worker334/worker.py').read_text(encoding='utf8')
def replace(old,new):
    global source
    assert source.count(old)==1,old
    source=source.replace(old,new)
replace('"""Isolated latest-model hooks around the unchanged canonical tangent worker."""',
        '"""Matched current-source legacy/static branch service in the canonical worker."""')
replace("mode=sys.argv[1];assert mode in ('scalar','ad')\n    out=HERE/(sys.argv[2] if len(sys.argv)>2 else mode);out.mkdir(exist_ok=False)",
        "mode=sys.argv[1];assert mode in ('scalar','ad')\n    service_mode=sys.argv[2];assert service_mode in ('legacy','static')\n    base=Path(sys.argv[3]);out=base/(service_mode+'_'+mode);out.mkdir(exist_ok=False)")
replace("from evaluation.controllers.sdmpc_tangent_runtime import install,Transform\n        finder=install(ROOT,'reverse-v1')",
        "from evaluation.controllers import sdmpc_tangent_runtime as runtime\n        runtime._CACHE_DIR=base/'tangent_cache';runtime._CACHE_DIR.mkdir(exist_ok=True)\n        from evaluation.controllers.sdmpc_tangent_runtime import install,Transform\n        finder=install(ROOT,'reverse-v1')")
replace("summary=json.loads((HERE/'capture_v2/summary.json').read_bytes())\n        data=(HERE/'capture_v2/request.pickle').read_bytes()",
        "summary=json.loads((HERE.parent/'worker334/capture_v2/summary.json').read_bytes())\n        data=(HERE.parent/'worker334/capture_v2/request.pickle').read_bytes()")
replace("for p,h in summary['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p",
        """# This is a new matched current-tree experiment, not replay of old334 pins.
        pins=json.loads((base/'source_pins.json').read_bytes())
        for p,h in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        for p,h in summary['source_pins'].items():
            if Path(p).suffix!='.py':assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
        changes=[]
        for p,h in request['bootstrap']['runtime_sources'].items():
            now=hashlib.sha256(Path(p).read_bytes()).hexdigest()
            assert pins[p]==now,p
            if now!=h:changes.append(dict(path=p,old=h,current=now))
        request['bootstrap']['runtime_sources']={p:pins[p] for p in request['bootstrap']['runtime_sources']}
        result['current_runtime_rebinding']=changes
        result['current_source_pins']=pins
        result['service_mode']=service_mode""")
replace("evaluate=endpoint.evaluate_price_point;receipts=[];cfg=request['owned'][0].cfg",
        """evaluate=endpoint.evaluate_price_point;receipts=[];cfg=request['owned'][0].cfg
        from evaluation.controllers.aggregate_route_corridors import configure_branch_service
        declared=None
        if service_mode=='static':
            rates,evidence=branch.settings()
            declared=configure_branch_service(cfg,rates)
            declared.update(evidence=str(evidence),rates=rates,static_config=True)
        # Values (including branch service) survive the same process boundary.
        request=pickle.loads(pickle.dumps(request,protocol=5));cfg=request['owned'][0].cfg""")
replace("br=stack.enter_context(branch.enabled())","br=stack.enter_context(branch.enabled()) if service_mode=='legacy' else declared")
replace("result['branch315_dynamic_ast_instrumented']=True",
        "result['branch315_dynamic_ast_instrumented']=service_mode=='legacy'")
replace("small['status']='failed_preserved' if 'error' in result else 'complete'",
        "small['service_mode']=service_mode\n    small['status']='failed_preserved' if 'error' in result else 'complete'")
(root/'canonical347/worker.py').write_text(source,encoding='utf8')
print('wrote matched worker',len(source))

