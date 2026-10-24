"""Aggregate prediction core: lane/turn stocks and accepted flows.

The state size depends on declared lane/turn classes and the fixed horizon,
never the number of vehicles or prior cohort splits. Moving stock consumes
storage but cannot receive head service before its current-state ETA.

Strict FIFO is a lane-level approximation: a blocked *present* turn slows its
lane; other lanes retain their own service. This does not reproduce packet
order or spatial queue fronts. Bounded simultaneous lateral transfers retain
turn identity. No fitted control bonus or native hook is installed here.
All flow arguments are vehicles per configured update interval, not veh/h.
Arrival times remain absolute seconds. Rounding an ETA to the next update
boundary delays eligibility by less than one interval; it never advances it.
"""
import math
from collections import defaultdict
from evaluation.controllers.sdmpc_aggregate import TimeBins
from evaluation.controllers.sdmpc_dual import primal


def fraction(room, request):
    if room <= 0:
        return 0.
    if request <= room:
        return 1.
    return room/request


class IntervalBins(TimeBins):
    """Fixed arrays indexed by coarse intervals; public clock uses seconds."""
    def __init__(self, labels, start_sec, horizon_sec, step_sec):
        self.origin_sec = start_sec
        self.step_sec = step_sec
        super().__init__(labels, 0, horizon_sec//step_sec)

    def add(self, key, due, amount):
        # Future information is not pulled into an earlier interval.
        super().add(key, math.ceil((due-self.origin_sec)/self.step_sec), amount)

    def advance(self, second):
        index = (second-self.origin_sec)/self.step_sec
        if index != int(index):
            raise ValueError('Arrival clock must be on an aggregate update boundary')
        super().advance(int(index))


class LaneTurnReservoir:
    def __init__(self, capacities, labels, start, horizon, step_sec=1):
        labels = tuple(labels)
        if (isinstance(step_sec,bool) or int(step_sec)!=step_sec or step_sec<=0
                or horizon<=0 or horizon%step_sec!=0):
            raise ValueError('Positive integer update and divisible horizon required')
        if not capacities or any(not math.isfinite(v) or v <= 0 for v in capacities.values()):
            raise ValueError('Positive finite lane capacities required')
        if len(set(labels)) != len(labels) or any(lane not in capacities for lane, turn in labels):
            raise ValueError('Unique declared lane/turn labels required')
        self.capacity = dict(capacities)
        self.step_sec = int(step_sec)
        self.end_sec = start+horizon
        self.bins = IntervalBins(labels, start, int(horizon), self.step_sec)
        self.by_lane = {lane:[i for i,(l,t) in enumerate(labels) if l == lane] for lane in capacities}
        if any(not ix for ix in self.by_lane.values()):
            raise ValueError('Every physical lane needs a declared turn')
        self.time = start
        self.initial = self.entered = self.exited = self.residence_veh_h = 0.

    def stock(self, lane=None):
        ix = range(len(self.bins.labels)) if lane is None else self.by_lane[lane]
        return sum(self.bins.total(j) for j in ix)

    def seed(self, lane, turn, amount, due):
        if self.bins.last >= self.bins.start:
            raise ValueError('Seed only before the first prediction step')
        if amount > self.capacity[lane]-self.stock(lane)+1e-8:
            raise ValueError('Initial stock exceeds its own physical lane storage')
        self.bins.add((lane,turn), due, amount)
        self.initial += amount

    def receive(self, requested, shares, due):
        """Admit one unsplit inlet stream; rejected mass stays with its caller."""
        if requested < 0 or not math.isfinite(primal(requested)):
            raise ValueError('Invalid requested inflow')
        if (not shares or abs(sum(shares.values())-1.) > 1e-10
                or any(k not in self.bins.index or v <= 0 for k,v in shares.items())):
            raise ValueError('Conserved positive route/lane shares required')
        weights = defaultdict(float)
        for (lane, turn), share in shares.items():
            weights[lane] += share
        accepted = min(requested, min(max(0., self.capacity[l]-self.stock(l))/w
                                      for l,w in weights.items()))
        for label, share in shares.items():
            self.bins.add(label, due, accepted*share)
        self.entered += accepted
        return accepted

    def transfer_ready(self, requests):
        """Simultaneous lateral flows, using only pre-transfer lane space.

        No new arrival can immediately make a second lateral move. Transfers
        are internal, so neither entered nor exited counts change.
        """
        if any(a not in self.bins.index or b not in self.bins.index
               or a[0] == b[0] or a[1] != b[1]
               or not math.isfinite(primal(v)) or v < 0
               for (a,b),v in requests.items()):
            raise ValueError('Lateral flow must preserve turn and join distinct physical lanes')
        source = defaultdict(float)
        for (a,b),v in requests.items():
            source[a] += v
        source_scale = {a:fraction(self.bins.waiting[self.bins.index[a]],v) for a,v in source.items()}
        offers = {(a,b):v*source_scale[a] for (a,b),v in requests.items()}
        incoming = defaultdict(float)
        for (a,b),v in offers.items():
            incoming[b[0]] += v
        lane_scale = {l:fraction(max(0.,self.capacity[l]-self.stock(l)),v) for l,v in incoming.items()}
        accepted = {(a,b):v*lane_scale[b[0]] for (a,b),v in offers.items()}
        for (a,b),v in accepted.items():
            self.bins.waiting[self.bins.index[a]] -= v
            self.bins.waiting[self.bins.index[b]] += v
        self.check()
        return accepted

    def step(self, lane_service, receiving, allowed_exits=None):
        """One vector conservation update with shared downstream acceptance."""
        turns = {t for l,t in self.bins.labels}
        if set(lane_service) != set(self.capacity) or set(receiving) != turns:
            raise ValueError('All lane services and downstream supplies required')
        if any(not math.isfinite(primal(v)) or v < 0 for v in (*lane_service.values(), *receiving.values())):
            raise ValueError('Finite nonnegative flow limits required')
        if self.time >= self.end_sec:
            raise ValueError('Aggregate reservoir cannot extend its fixed horizon')
        allowed = set(self.bins.labels) if allowed_exits is None else set(allowed_exits)
        if not allowed <= set(self.bins.labels):
            raise ValueError('Exit must belong to a declared physical lane and turn')
        self.bins.advance(self.time)
        before = self.stock()
        demand = [0.]*len(self.bins.labels)
        for lane, ix in self.by_lane.items():
            ready = sum(self.bins.waiting[j] for j in ix)
            scale = fraction(lane_service[lane], ready)
            for j in ix:
                demand[j] = self.bins.waiting[j]*scale
        total = {t:sum(demand[j] for j,label in enumerate(self.bins.labels)
                       if label[1] == t and label in allowed) for t in turns}
        supply_fraction = {t:fraction(receiving[t], total[t]) for t in turns}
        out = [0.]*len(demand)
        for lane, ix in self.by_lane.items():
            present = [supply_fraction[self.bins.labels[j][1]] if self.bins.labels[j] in allowed else 0.
                       for j in ix if demand[j] > 0]
            scale = min(present) if present else 1.
            for j in ix:
                out[j] = demand[j]*scale
                self.bins.waiting[j] -= out[j]
        departed = sum(out)
        self.exited += departed
        # Trapezoidal inventory quadrature; not a reconstruction of individual
        # departures inside a red/green interval.
        self.residence_veh_h += (before-departed/2.)*self.step_sec/3600.
        self.time += self.step_sec
        self.check()
        return dict(zip(self.bins.labels, out))

    def check(self):
        if abs(self.initial+self.entered-self.exited-self.stock()) > 1e-7:
            raise ArithmeticError('Aggregate reservoir vehicle conservation failed')
        for lane, capacity in self.capacity.items():
            if not -1e-8 <= self.stock(lane) <= capacity+1e-8:
                raise ArithmeticError('Aggregate lane storage violated')
        if any(v < -1e-8 for v in self.bins.waiting):
            raise ArithmeticError('Negative ready inventory')
