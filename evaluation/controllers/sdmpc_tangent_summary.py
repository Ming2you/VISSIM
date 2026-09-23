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


def install_fused_operations():
    """Reverse-Dual arithmetic and ordering that call checked_operation's body directly.

    A taped rollout performs ~26M Dual operations. Each one used to go through the
    Dual method, primal() on the other operand, the trace.operation attribute lookup
    and checked_operation's two isinstance checks. For the operand types that occur on
    the hot path -- another reverse Dual, a float or an int -- these methods compute
    the same value with the same expression and then run checked_operation's body with
    `a` fixed to `self` (always a reverse Dual, so da is True). Every other operand
    type falls back to the original method, so no type gets new semantics.

    The emitted node is the same one ad.Dual's own methods emit through
    trace.operation: same parent order, same weights (the constant operand's weight is
    still written to w2, as checked_operation does), same support, guard and freeze
    checks, same result slots. Ordering calls trace.branch(self, other) and compares
    primal values exactly as sdmpc_dual.Dual._cmp. THIS IS A SECOND COPY OF
    checked_operation ABOVE: change both or neither. tools/verify_fused.py rolls one real
    prediction both ways and compares the tape arrays byte for byte.

    Installed only by install() below, i.e. only where checked_operation itself is
    the installed Trace.operation.
    """
    import math
    import operator
    Dual = ad.Dual
    originals = {name: getattr(Dual, name) for name in
                 ('__add__', '__sub__', '__rsub__', '__mul__', '__truediv__',
                  '__lt__', '__le__', '__gt__', '__ge__')}
    new = object.__new__
    isfinite = math.isfinite

    def emit(trace, value, a, wa, b, wb, db):
        if a.trace is not trace or (db and b.trace is not trace):
            raise ValueError('Reverse arithmetic mixed prediction tapes')
        if ad.PRIMAL_GUARD:
            node = support = 0
        else:
            na = a.node if wa != 0. else 0
            nb = b.node if db and wb != 0. else 0
            if not na and not nb:
                return float(value)
            if na and not nb and wa == 1.:
                node, support = na, a.support
            elif nb and not na and wb == 1.:
                node, support = nb, b.support
            else:
                if na == nb and wa == -wb and isfinite(wa):
                    return float(value)
                support = a.support if na else b.support
                if na and nb and support != b.support:
                    support |= b.support
                if trace.frozen:
                    raise ValueError('Reverse tape changed after derivative sweep')
                node = len(trace.p1)
                trace.p1.append(na); trace.p2.append(nb)
                trace.w1.append(wa); trace.w2.append(wb)
        result = new(Dual)
        result.value, result.node, result.support = float(value), node, support
        result.trace, result.risks, result.tangent = trace, (0, 0), None
        return result

    # ad.Dual.__add__: trace.operation(self.value+primal(other), self, 1., other, 1.)
    def add(self, other):
        t = type(other)
        if t is Dual:
            return emit(self.trace, self.value+other.value, self, 1., other, 1., True)
        if t is float or t is int:
            return emit(self.trace, self.value+float(other), self, 1., other, 1., False)
        return originals['__add__'](self, other)

    # ad.Dual.__sub__: trace.operation(self.value-primal(other), self, 1., other, -1.)
    def sub(self, other):
        t = type(other)
        if t is Dual:
            return emit(self.trace, self.value-other.value, self, 1., other, -1., True)
        if t is float or t is int:
            return emit(self.trace, self.value-float(other), self, 1., other, -1., False)
        return originals['__sub__'](self, other)

    # ad.Dual.__rsub__: trace.operation(primal(other)-self.value, self, -1., other, 1.)
    def rsub(self, other):
        t = type(other)
        if t is float or t is int:
            return emit(self.trace, float(other)-self.value, self, -1., other, 1., False)
        return originals['__rsub__'](self, other)

    # ad.Dual.__mul__: trace.operation(self.value*primal(other), self, primal(other), other, self.value)
    def mul(self, other):
        t = type(other)
        if t is Dual:
            ov = other.value
            return emit(self.trace, self.value*ov, self, ov, other, self.value, True)
        if t is float or t is int:
            ov = float(other)
            return emit(self.trace, self.value*ov, self, ov, other, self.value, False)
        return originals['__mul__'](self, other)

    # ad.Dual.__truediv__: d = primal(other);
    #   trace.operation(self.value/d, self, 1./d, other, -self.value/d**2)
    def truediv(self, other):
        t = type(other)
        if t is Dual or t is float or t is int:
            d = other.value if t is Dual else float(other)
            return emit(self.trace, self.value/d, self, 1./d, other, -self.value/d**2, t is Dual)
        return originals['__truediv__'](self, other)

    # sdmpc_dual.Dual._cmp: branch(self, other); op(self.value, primal(other))
    def ordering(name, op):
        fallback = originals[name]

        def method(self, other):
            t = type(other)
            if t is Dual:
                self.trace.branch(self, other)
                return op(self.value, other.value)
            if t is float or t is int:
                self.trace.branch(self, other)
                return op(self.value, float(other))
            return fallback(self, other)
        return method

    Dual.__add__ = add; Dual.__radd__ = add
    Dual.__sub__ = sub; Dual.__rsub__ = rsub
    Dual.__mul__ = mul; Dual.__rmul__ = mul
    Dual.__truediv__ = truediv
    Dual.__lt__ = ordering('__lt__', operator.lt)
    Dual.__le__ = ordering('__le__', operator.le)
    Dual.__gt__ = ordering('__gt__', operator.gt)
    Dual.__ge__ = ordering('__ge__', operator.ge)
    return originals


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
    install_fused_operations()
    path=Path(__file__).resolve()
    finder.source_hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
