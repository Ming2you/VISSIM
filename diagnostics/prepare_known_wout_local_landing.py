"""Unapplied, sequential after known_wout_routes.patch; FW-local/coupling only."""
import ast
from contextlib import contextmanager,ExitStack
import difflib
import hashlib
import json
import linecache
from unittest.mock import patch
from diagnostics.prepare_known_wout_routes import ROOT,replace_once,installed as global_installed,sources as global_sources,ROUTE

HELPER=ROOT/'diagnostics/known_wout_local_landing_proposal.py'
LOCAL=ROOT/'evaluation/controllers/link_predictor.py'
ADAPTER=ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py'


def sources():
    base=global_sources()[ROUTE]
    route=base+'\n\n'+HELPER.read_text(encoding='utf-8')
    local=LOCAL.read_text(encoding='utf-8')
    local=replace_once(local,'        self.replaced_coupling = Counter()\n',
        '        from evaluation.controllers import route_choice_corridor as known\n        known.initialize_known_local_landing(self,state)\n        self.replaced_coupling = Counter()\n')
    local=replace_once(local,'                for ramp, share in self.split[k].get("ramps", {}).items():\n',
        '                tagged=known.known_local_requests(self,k,reach_rate*self.cfg.simulation.T_c_h,\n                    self.arrived(k),self.step,snapshot=True)\n                for ramp, share in self.split[k].get("ramps", {}).items():\n')
    local=replace_once(local,'                        self.replaced_coupling[ramp] += reach_rate * float(share)\n',
        '                        self.replaced_coupling[ramp] += (reach_rate*float(share) if tagged is None\n                            else tagged.get(ramp,0.)/self.cfg.simulation.T_c_h)\n')
    local=replace_once(local,"        self.ledger['arrivals_veh'] += sum(additions.values())\n",
        "        from evaluation.controllers.route_choice_corridor import known_local_direct_receipts\n        known_local_direct_receipts(self,flows,dt_h)\n        self.ledger['arrivals_veh'] += sum(additions.values())\n")
    local=replace_once(local,'        from src.models.urban_queue_model import _link_delay_steps\n',
        '        from src.models.urban_queue_model import _link_delay_steps\n        from evaluation.controllers import route_choice_corridor as known\n')
    local=replace_once(local,'                if split:\n', '                receipts=[]\n                if split:\n')
    local=replace_once(local,"                    free = reach * float(split.get('free', 0))\n",
        "                    tagged=known.known_local_requests(self,target,reach,arrived,self.step)\n                    free = reach*float(split.get('free',0)) if tagged is None else tagged.get('free',0.)\n")
    local=replace_once(local,'                    for ramp, share in split.get(\'ramps\', {}).items():\n',
        "                    receipts.append((target,None,departed))\n                    for ramp, share in split.get('ramps', {}).items():\n")
    local=replace_once(local,'                        transfer = min(reach * float(share), room, cap)\n',
        '                        request=reach*float(share) if tagged is None else tagged.get(ramp,0.)\n                        transfer = min(request, room, cap)\n                        receipts.append((target,ramp,transfer))\n')
    local=replace_once(local,'                self.stock[target] -= departed\n',
        '                self.stock[target] -= departed\n                known.known_local_commit(self,target,receipts,self.step)\n')
    adapter=ADAPTER.read_text(encoding='utf-8')
    adapter=replace_once(adapter,'            total = stock\n            _LEGSPLIT_LAST',
        "            total = stock\n            from evaluation.controllers.route_choice_corridor import known_legsplit_request_snapshot\n            tagged=known_legsplit_request_snapshot(state,cfg_arg,str(link),total,arrived,idx)\n            _LEGSPLIT_LAST")
    adapter=replace_once(adapter,'                veh = total * max(0.0, float(share))\n',
        '                veh = (total*max(0.,float(share)) if tagged is None else tagged.get(str(ramp),0.))\n')
    return {ROUTE:(base,route),LOCAL:(LOCAL.read_text(encoding='utf-8'),local),ADAPTER:(ADAPTER.read_text(encoding='utf-8'),adapter)}


@contextmanager
def installed():
    from evaluation.controllers import route_choice_corridor as route,link_predictor, vissim_stackelberg_adapter as adapter
    with global_installed(),ExitStack() as stack:
        texts=sources();namespace=dict(route.__dict__)
        text=HELPER.read_text(encoding='utf-8');exec(compile(text,str(HELPER),'exec'),namespace)
        for node in ast.parse(text).body:
            if isinstance(node,ast.FunctionDef):stack.enter_context(patch.object(route,node.name,namespace[node.name],create=True))
        tree=ast.parse(texts[LOCAL][1]);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalLandingState')
        methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('__init__','land','advance')]
        ns=dict(link_predictor.__dict__)
        virtual=str(LOCAL)+'<known-local>'
        stack.enter_context(patch.dict(linecache.cache,{virtual:(len(texts[LOCAL][1]),None,texts[LOCAL][1].splitlines(True),virtual)}))
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),virtual,'exec'),ns)
        for method in methods:stack.enter_context(patch.object(link_predictor.LocalLandingState,method.name,ns[method.name]))
        tree=ast.parse(texts[ADAPTER][1]);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='install_leg_ramp_split_runtime')
        ns=dict(adapter.__dict__)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(ADAPTER)+'<known-local>','exec'),ns)
        stack.enter_context(patch.object(adapter,'install_leg_ramp_split_runtime',ns[node.name]))
        yield route


def main():
    changed=sources()
    for path,(_,text) in changed.items():compile(text,str(path),'exec')
    out=ROOT/'diagnostics/known_wout_local_landing.patch'
    out.write_text(''.join(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='a/'+path.relative_to(ROOT).as_posix(),tofile='b/'+path.relative_to(ROOT).as_posix()))
        for path,(before,after) in changed.items()),encoding='utf-8',newline='\n')
    metadata={'patch_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'requires':'known_wout_routes.patch first',
        'production_applied':False,'scope':'FW-local landing and frozen onramp coupling. Urban green/offset/refinement W_out dynamic state remains unsupported.',
        'base_normalized_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(a.encode()).hexdigest() for p,(a,b) in changed.items()}}
    out.with_suffix('.manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
