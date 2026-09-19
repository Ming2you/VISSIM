"""Rejected standalone lane-buffer hypothesis; never installed by the controller."""
from math import fsum
from evaluation.controllers.physical_ramp_boundary import PhysicalRampBoundary, _number, _MASS_TOLERANCE

class LaneResolvedRampBoundary(PhysicalRampBoundary):
    """Opt-in independent lane buffers for a physical ramp connector.

    A vacant lane cannot lend head service or storage to a queued lane. This
    assumes no in-connector lane exchange during the forecast; the caller must
    supply causal arrival shares. Merge supply is divided equally by physical
    lane count, not fitted from observed departures. This is not a gap-acceptance
    model and does not identify a congested receiving-mainline lane's supply.
    Only the existing local one-second interface is supported.
    """

    def __init__(self, *, lane_arrival_shares, **kwargs):
        kwargs = dict(kwargs)
        kwargs['initial_cohorts'] = tuple(kwargs.get('initial_cohorts', ()))
        super().__init__(**kwargs)
        if (not isinstance(lane_arrival_shares, (list, tuple))
                or len(lane_arrival_shares) != self.lanes):
            raise ValueError('One explicit arrival share per physical ramp lane is required')
        shares = tuple(_number(x, 'lane arrival share') for x in lane_arrival_shares)
        if abs(fsum(shares)-1.) > _MASS_TOLERANCE:
            raise ValueError('Physical ramp lane arrival shares must sum to one')
        if kwargs.get('initial_backlog_veh', 0.) != 0:
            raise ValueError('Unclassified initial lane backlog is unsupported')
        self.lane_arrival_shares = shares
        self._lane_buffers = []
        for lane in range(1, self.lanes+1):
            spec = dict(kwargs, lanes=1)
            spec['initial_cohorts'] = [(pos, speed, 1) for pos, speed, index
                                       in self.initial_cohorts if index == lane]
            self._lane_buffers.append(PhysicalRampBoundary(**spec))

    @staticmethod
    def _aggregate_snapshots(snapshots, connector_id):
        # All nonidentifying snapshot fields are additive inventories/counters.
        first = snapshots[0]
        if any((s['time_sec'], s['phase']) != (first['time_sec'], first['phase'])
               for s in snapshots):
            raise ValueError('Lane buffer clocks/phases differ')
        identity = {'connector_id', 'time_sec', 'phase'}
        return {**{k: first[k] for k in identity}, 'connector_id': connector_id,
                **{k: fsum(s[k] for s in snapshots) for k in first if k not in identity}}

    def snapshot(self):
        if not hasattr(self, '_lane_buffers'):
            return super().snapshot()
        return self._aggregate_snapshots([b.snapshot() for b in self._lane_buffers], self.connector_id)

    def metadata(self):
        return {**super().metadata(), 'lane_resolution': True,
                'lane_arrival_shares': self.lane_arrival_shares,
                'lane_exchange': 'None; independent lane FIFO inventories',
                'lane_supply': 'Equal shares of canonical aggregate receiving budget'}

    def begin_interval(self, *args, **kwargs):
        raise ValueError('Lane-resolved ramps require advance_local_interval')

    commit_merge = begin_interval
    apply_head_service = begin_interval
    finish_interval = begin_interval

    def advance_local_interval(self, **kwargs):
        receipts = []
        for share, buffer in zip(self.lane_arrival_shares, self._lane_buffers):
            lane_args = dict(kwargs)
            for key in ('receiving_budget_veh', 'service_veh'):
                lane_args[key] = _number(kwargs[key], key)/self.lanes
            lane_args['request_arrivals_veh'] = _number(kwargs['request_arrivals_veh'], 'request_arrivals_veh')*share
            receipts.append(buffer.advance_local_interval(**lane_args))
        def combine(rs):
            first = rs[0]
            same = {'start_sec', 'end_sec', 'duration_sec', 'meter_mode', 'green_sec',
                    'local_step_sec', 'eligible_merge_scope'}
            result = {k:v for k,v in first.items() if k in same}
            for k,v in first.items():
                if k in same or k in ('start','end','local_receipts'):
                    continue
                if not isinstance(v, (int,float)):
                    raise ValueError('Unexpected lane receipt field: '+k)
                result[k] = fsum(r[k] for r in rs)
            for key in ('start','end'):
                result[key] = self._aggregate_snapshots([r[key] for r in rs], self.connector_id)
            return result
        result = combine(receipts)
        result['local_receipts'] = [combine([r['local_receipts'][i] for r in receipts])
                                    for i in range(len(receipts[0]['local_receipts']))]
        result['lane_receipts'] = [{k:v for k,v in r.items() if k!='local_receipts'} for r in receipts]
        result['lane_arrival_shares'] = self.lane_arrival_shares
        self.time_sec = result['end_sec']
        return result
