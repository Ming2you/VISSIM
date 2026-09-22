"""Decision-only summaries of already-checked model allocation/bound records.

The canonical checks still construct and validate every record at the original
site. Successful rows are counted, not retained/packed/unpacked as full ledgers.
Transfers, residence, coverage, freeway operands and AD traffic remain intact.
Only install in an isolated continuous-surrogate worker, never the native model.
"""
from collections import Counter
import hashlib
from pathlib import Path
from evaluation.controllers import sdmpc_tangent_reverse as ad


def checked_operation(self,value,a,wa,b=None,wb=0.):
    """Same tape nodes/weights, with one type dispatch per operand.

    Inline the tiny node/result constructors on this hot path. Do not reorder
    arithmetic, coalesce nodes, remove guards, or change branch accounting.
    """
    da,db=isinstance(a,ad.Dual),isinstance(b,ad.Dual)
    if (da and a.trace is not self) or (db and b.trace is not self):
        raise ValueError('Reverse arithmetic mixed prediction tapes')
    if ad.PRIMAL_GUARD:
        node=support=0
    else:
        na=a.node if da and wa!=0. else 0
        nb=b.node if db and wb!=0. else 0
        if not na and not nb:return float(value)
        if na and not nb and wa==1.:
            node,support=na,a.support
        elif nb and not na and wb==1.:
            node,support=nb,b.support
        else:
            if na==nb and wa==-wb and ad.math.isfinite(wa):return float(value)
            support=a.support if na else b.support
            if na and nb and support!=b.support:support|=b.support
            if self.frozen:raise ValueError('Reverse tape changed after derivative sweep')
            node=len(self.p1)
            self.p1.append(na);self.p2.append(nb)
            self.w1.append(wa);self.w2.append(wb)
    result=object.__new__(ad.Dual)
    result.value,result.node,result.support=float(value),node,support
    result.trace,result.risks,result.tangent=self,(0,0),None
    return result


class CheckedRecords:
    """An append sink for checked rows, deliberately not an iterable ledger."""
    def __init__(self, family):
        if family not in ('resource_allocations','state_bounds'):
            raise ValueError('Unknown model check family')
        self.family=family
        self.count=0
        self.kinds=Counter()
        self.max_exceedance=0.

    def append(self, record):
        # The original method raises on violations before reaching this sink.
        self.count+=1
        self.kinds[record['kind']]+=1
        if self.family=='resource_allocations':
            self.max_exceedance=max(self.max_exceedance,record['exceedance_veh'])

    def __len__(self):
        return self.count

    def __iter__(self):
        raise TypeError('Full model check rows were not retained in summary mode')

    def __deepcopy__(self,memo):
        result=CheckedRecords(self.family)
        memo[id(self)]=result
        result.count=self.count
        result.kinds=self.kinds.copy()
        result.max_exceedance=self.max_exceedance
        return result


def install(finder,cfg,*,surrogate_mode):
    options=cfg.network.sdmpc_options
    if not options.get('prediction_hotpath'):
        return
    if (surrogate_mode not in ('ad','scalar') or not options.get('surrogate_reuse')
            or not options.get('fast_primitives') or not options.get('primal_audit')
            or finder.backend!='reverse-v1'):
        raise ValueError('Stream summary requires an isolated continuous-surrogate worker with primal checks')
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    if getattr(ModelAreaLedger,'_sdmpc_stream_summary_installed',False):
        raise ValueError('Stream summary already installed')
    original_init=ModelAreaLedger.__init__
    original_pack=ModelAreaLedger.pack_completed_response_records
    original_response=ModelAreaLedger.response
    families=('resource_allocations','state_bounds')

    def initialize(self,*args,**kwargs):
        original_init(self,*args,**kwargs)
        if self.captures_response:
            if not getattr(self,'_primal_audit',False):
                raise ValueError('Stream summary requires original primal record checks')
            for key in families:
                self._response[key]=CheckedRecords(key)

    def without_rows(self,function,*args,**kwargs):
        if not self.captures_response:
            return function(self,*args,**kwargs)
        saved={key:self._response[key] for key in families}
        if any(type(value) is not CheckedRecords for value in saved.values()):
            raise ValueError('Summary ledger contains unowned full check records')
        try:
            for key in families:self._response[key]=[]
            return function(self,*args,**kwargs)
        finally:
            self._response.update(saved)

    def pack(self,*,compact=False):
        return without_rows(self,original_pack,compact=compact)

    def response(self):
        result=without_rows(self,original_response)
        allocation,bounds=(self._response[key] for key in families)
        if result['resource_allocations'] or result['state_bounds']:
            raise ValueError('Summary response unexpectedly contains packed full check rows')
        result['model_constraint_coverage'].update(checked_allocation_count=len(allocation),
            checked_state_bound_count=len(bounds))
        result['streamed_model_checks']=dict(schema='sdmpc-streamed-model-checks/v1',
            successful_records_retained=False,original_checks_performed=True,
            allocation_summary=dict(count=len(allocation),kinds=dict(allocation.kinds),
                max_exceedance_veh=allocation.max_exceedance),state_bound_count=len(bounds),
            scope='All original checks run; full successful check rows omitted, traffic/coverage records retained')
        return result

    ModelAreaLedger.__init__=initialize
    ModelAreaLedger.pack_completed_response_records=pack
    ModelAreaLedger.response=response
    ModelAreaLedger._sdmpc_stream_summary_installed=True
    ad.Trace.operation=checked_operation
    path=Path(__file__).resolve()
    finder.source_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
