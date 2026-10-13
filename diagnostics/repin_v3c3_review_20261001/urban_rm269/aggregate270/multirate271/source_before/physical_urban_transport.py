"""Conserved local lane transport shared by diagnostics and the SDMPC plant.

The equations and observation contracts are moved unchanged from the 2026-09-21
reference experiment. This module imports no experiment output or future data.
Local spatial/route coverage remains explicit; unsupported traffic fails closed.
"""
from __future__ import annotations
import copy
import math
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict, deque
from evaluation.controllers import sdmpc_prediction_cache as prediction_cache

EPS = 1e-9

class ReceivingEnvelope:
    def __init__(self,length,spacing,v_free,wave,positions):
        if any(not math.isfinite(x) or x<=0 for x in (length,spacing,v_free,wave)):
            raise ValueError('Positive finite link geometry and wave speeds required')
        p=sorted(positions);self.length=length;self.spacing=spacing;self.wave=wave
        self.initial=len(p);self.capacity=length/spacing;self.jam=1/spacing
        self.critical=self.jam*wave/(v_free+wave);self.qmax=v_free*self.critical
        self.lag=length/wave
        if len(p)>self.capacity+1e-8 or any(not 0<=x<=length for x in p):
            raise ValueError('Initial vehicles exceed physical storage/position range')
        # Isotonic least-squares projection: no lost vehicles, no extra storage.
        # Adjacent microscopic gaps may be smaller than the mean jam spacing.
        blocks=[]
        for i,x in enumerate(p):
            blocks.append([x-(i+1)*spacing,1])
            while len(blocks)>1 and blocks[-2][0]/blocks[-2][1]>blocks[-1][0]/blocks[-1][1]:
                b=blocks.pop();blocks[-1][0]+=b[0];blocks[-1][1]+=b[1]
        offsets=[];room=length-len(p)*spacing
        for total,n in blocks:offsets.extend([min(room,max(0.,total/n))]*n)
        self.positions=[u+(i+1)*spacing for i,u in enumerate(offsets)]
        self.projection_max_m=max((abs(a-b) for a,b in zip(p,self.positions)),default=0.)
        self.points=sorted({0.,length,*self.positions,*(x-spacing for x in self.positions)})

    def initial_prefix(self,x):
        return sum(min(1.,max(0.,(x-(p-self.spacing))/self.spacing)) for p in self.positions)

    def initial_bound(self,elapsed):
        limit=min(self.length,self.wave*elapsed)
        points=[p for p in self.points if p<=limit]+[limit]
        return self.qmax*elapsed+min(-self.initial_prefix(x)+self.critical*x for x in points)

    def offer(self,elapsed,dt,admitted,departures):
        if not elapsed>=dt>0 or admitted<0:raise ValueError('Invalid causal receiving interval')
        # departures is D(t), at every integer second since initialization;
        # only observations <= the CURRENT interval start may be provided.
        if len(departures)-1>elapsed-dt+1e-8:raise ValueError('Future departure observations supplied')
        bound=self.initial_bound(elapsed)
        lagged=elapsed-self.lag
        if lagged>=0:
            if lagged>len(departures)-1+1e-8:raise ValueError('Wave reaches beyond known departure history')
            lo=int(lagged);hi=min(lo+1,len(departures)-1);f=lagged-lo
            delayed=departures[lo]*(1-f)+departures[hi]*f
            bound=min(bound,delayed+self.capacity-self.initial)
        return max(0.,min(self.qmax*dt,bound-admitted))


class CumulativeLane:
    """One conserved link with matching initial-condition sending/receiving.

    The existing receiving envelope's triangular FD is used at both ends.
    Supplied outlet service limits cumulative discharge once, not once per
    fractional packet followed by another catch-up time. Initial microscopic
    positions undergo the envelope's declared finite-spacing projection.
    """
    def __init__(self,capacity,length,speed,vehicles,start,wave):
        self.envelope=ReceivingEnvelope(length,length/capacity,speed/3.6,wave,[p for p,v,size in vehicles])
        self.capacity=capacity;self.initial=len(vehicles);self.length=length;self.vfree=speed/3.6
        self.start=self.time=start;self.admitted=self.departed=self.residence_veh_h=0.
        self.internal_in=self.internal_out=0.;self.counters=0
        self.arrivals=[];self.departure_history=[0.];self.offer_dt=1.

    @property
    def stock(self):return self.initial+self.admitted-self.departed

    def sending_bound(self,elapsed):
        env=self.envelope;lo=max(0.,self.length-self.vfree*elapsed)
        points=[p for p in env.points if p>=lo]+[lo]
        initial=env.initial+env.qmax*elapsed-env.critical*self.length+min(-env.initial_prefix(x)+env.critical*x for x in points)
        upstream_time=elapsed-self.length/self.vfree
        if upstream_time>=0:
            upstream=math.fsum(n for t,n in self.arrivals if t<=upstream_time+1e-9)
            initial=min(initial,self.initial+upstream)
        return initial

    @property
    def ready(self):return max(0.,min(self.stock,self.sending_bound(self.time-self.start)-self.departed))

    def receiving(self,dt=10):
        elapsed=self.time-self.start;self.offer_dt=min(dt,elapsed)
        if not self.offer_dt:return 0.
        past=self.departure_history[:int(elapsed-self.offer_dt)+1]
        return max(0.,min(self.capacity-self.stock,self.envelope.offer(elapsed,self.offer_dt,self.admitted,past)))

    def check(self):
        if not -1e-7<=self.stock<=self.capacity+1e-7:raise ArithmeticError('Cumulative lane storage invalid')
        if self.departed>self.initial+self.admitted+1e-7:raise ArithmeticError('Cumulative lane loses vehicles')
        self.counters+=1

    def release(self,t,dt,service):
        if t!=self.time or dt!=1 or not math.isfinite(service) or service<0:raise ValueError('Contiguous1s service required')
        before=self.stock
        available=max(0.,min(before,self.envelope.qmax*dt,self.sending_bound(t+dt-self.start)-self.departed))
        served=min(available,service*dt/3600.)
        self.departed+=served;self.time=t+dt;self.departure_history.append(self.departed)
        # Uniform flow within each1s numerical interval; no unused service bank.
        self.residence_veh_h+=(before-served/2)*dt/3600.
        self.check();return served

    def accept(self,t,amount,**unused):
        if t!=self.time or not math.isfinite(amount) or amount<0 or amount>self.receiving(self.offer_dt)+1e-7:
            raise ArithmeticError('Cumulative admission exceeds causal receiving envelope')
        self.admitted+=amount
        self.arrivals.append((t-self.start,amount));self.check()


def geometry(network):
    root=ET.parse(network).getroot();routes={};exits={}
    for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
            routes[int(d.get('no')),int(r.get('no'))]=[int(d.get('link'))]+[int(v.get('key')) for v in r.findall('./linkSeq/intObjectRef')]+[int(r.get('destLink'))]
    for link in root.findall('./links/link'):
        p=link.find('./fromLinkEndPt')
        if p is not None and int(p.get('lane').split()[0])==71:
            first=int(p.get('lane').split()[1]);count=len(link.findall('./lanes/lane'))
            exits[int(link.get('no'))]=dict(lanes=list(range(first,first+count)),position_m=float(p.get('pos')))
    assert set(exits)=={10634,10635,10642}
    return routes,exits


def observe(frame,routes,exits):
    def intent(row):
        vid,link,lane,pos,speed,length,decision,number,kind,nextlink,*_=row
        # Current next-link is direct evidence on71, even without an active
        # static route. Else preserve only an explicitly assigned static path.
        path=routes.get((decision,number)) if kind and kind.lower()=='static' else None
        planned=None
        if path and 71 in path:
            i=path.index(71)
            if i+1<len(path) and path[i+1] in exits:planned=path[i+1]
        chosen=nextlink if link==71 and nextlink in exits else planned
        conflict=link==71 and nextlink in exits and planned is not None and nextlink!=planned
        if conflict:chosen=None
        return dict(connector=chosen,source='next_link' if link==71 and nextlink in exits and not conflict else 'assigned_static_route' if chosen else 'unknown',
            route_next_link_conflict=conflict,required_lanes=exits[chosen]['lanes'] if chosen else None)
    observations=[]
    for row in frame['vehicles']:
        if row[1] not in (10643,126,10641,10700,71):continue
        target=intent(row)
        observations.append(dict(vehicle=row[0],link=row[1],lane=row[2],position_m=row[3],speed_kmh=row[4],length_m=row[5],
            route_decision=row[6],route_number=row[7],route_type=row[8],next_link=row[9],
            current_lane_change_destination=row[10],lane_change=row[11],interaction_state=row[12],
            interaction_target_type=row[13],interaction_target_number=row[14],**target))
    lanes={}
    for lane in range(1,6):
        current=[r for r in observations if r['link']==71 and r['lane']==lane]
        head=max(current,key=lambda r:r['position_m']) if current else None
        head_state=None
        if head:
            head_state=dict(head);required=head['required_lanes']
            head_state['currently_in_required_lane']=lane in required if required else None
            head_state['adjacent_gaps']={}
            for other in (lane-1,lane+1):
                if not 1<=other<=5:continue
                neighbors=[r for r in observations if r['link']==71 and r['lane']==other]
                front=min((r for r in neighbors if r['position_m']>=head['position_m']),key=lambda r:r['position_m'],default=None)
                back=max((r for r in neighbors if r['position_m']<head['position_m']),key=lambda r:r['position_m'],default=None)
                head_state['adjacent_gaps'][str(other)]=dict(front_vehicle=front['vehicle'] if front else None,
                    front_net_gap_m=front['position_m']-front['length_m']-head['position_m'] if front else None,
                    front_speed_kmh=front['speed_kmh'] if front else None,back_vehicle=back['vehicle'] if back else None,
                    back_net_gap_m=head['position_m']-head['length_m']-back['position_m'] if back else None,
                    back_speed_kmh=back['speed_kmh'] if back else None)
        counts=Counter(str(r['connector']) if r['connector'] else 'unknown' for r in current)
        assert sum(counts.values())==len(current)
        lanes[str(lane)]=dict(n=len(current),intent_counts=dict(counts),head=head_state)
    off={}
    for lane in (1,2):
        current=[r for r in observations if r['link']==10643 and r['lane']==lane]
        counts=Counter(str(r['connector']) if r['connector'] else 'unknown' for r in current)
        assert sum(counts.values())==len(current)
        off[str(lane)]=dict(n=len(current),planned_71_exit_counts=dict(counts))
    return dict(time_s=frame['time_s'],urban_lanes=lanes,off_lanes=off,vehicles=observations)


class FIFO:
    """Fractional labelled vehicles; taking a prefix cannot bypass its head."""
    def _array(self, create=True):
        cache = prediction_cache.active()
        if cache is None or not cache.fifo_enabled:return None
        # The fused pipeline explicitly registers only the queues it consumes.
        # Other ramp/route queues keep their existing representation.
        if not cache.fifo_all_enabled and self not in cache.array_fifos:return None
        from evaluation.controllers.sdmpc_tangent_fifo import get
        return get(self,create=create)

    def __getattribute__(self,name):
        if name == 'q':
            buffer = object.__getattribute__(self,'_array')()
            if buffer is not None:return buffer.view
        return object.__getattribute__(self,name)

    def __deepcopy__(self,memo):
        result = object.__new__(type(self));memo[id(self)] = result
        fields = vars(self).copy()
        buffer = self._array(create=False)
        if buffer is not None:
            fields['q'] = buffer.materialize()
            from evaluation.controllers.sdmpc_tangent_fifo import STATS
            STATS['snapshots'] += 1
        result.__dict__.update(copy.deepcopy(fields,memo))
        return result

    def __init__(self, packets=()):
        self.q = deque()
        for label, amount in packets:
            self.append(label, amount)

    @property
    def stock(self):
        buffer = self._array()
        if buffer is not None:return buffer.stock()
        cache = prediction_cache.active()
        if cache is not None:
            if self not in cache.stocks:
                cache.stocks[self] = math.fsum(n for label, n in self.q)
            return cache.stocks[self]
        return math.fsum(n for label, n in self.q)

    def append(self, label, amount):
        if amount < -EPS or not math.isfinite(amount):
            raise ValueError('Invalid labelled mass')
        if amount <= EPS:
            return
        buffer = self._array()
        if buffer is not None:
            buffer.append(label,amount)
            return
        prediction_cache.invalidate(self)
        if self.q and self.q[-1][0] == label:
            self.q[-1][1] += amount
        else:
            self.q.append([label, amount])

    def take(self, amount):
        if amount < -EPS or amount > self.stock + 1e-7:
            raise ArithmeticError('FIFO overdraw')
        buffer = self._array()
        if buffer is not None:return buffer.take(amount)
        prediction_cache.invalidate(self)
        result = []
        while amount > EPS and self.q:
            label, n = self.q[0]
            d = min(amount, n)
            result.append((label, d))
            amount -= d
            self.q[0][1] -= d
            if self.q[0][1] <= EPS:
                self.q.popleft()
        return result

    def counts(self):
        buffer = self._array()
        if buffer is not None:return buffer.counts()
        result = Counter()
        for label, n in self.q:
            result[label] += n
        return result

    def take_label(self, label, amount):
        """Lateral departure may leave from behind a stopped longitudinal head."""
        buffer = self._array()
        if buffer is not None:
            phase=buffer.lateral()
            result=phase.take(label,amount);phase.commit()
            return result
        # Only this label can change. Building all label totals and subtracting
        # zero from every unrelated fragment costs O(labels * fragments) full
        # tangent operations during lateral allocation. Keep the same ordered
        # addition for the requested label and reuse the other immutable amounts.
        available = 0.
        for old_label, n in self.q:
            if old_label == label:
                # This total is used only for an overdraw assertion, never a
                # physical flow or output. Preserve Counter's ordered scalar
                # additions but do not build a Jacobian for the assertion.
                available += getattr(n, '_validation_primal', n)
        if amount < -EPS or amount > available+1e-7:
            raise ArithmeticError('Lateral label overdraw')
        remaining = amount
        result = deque()
        for old_label, n in self.q:
            if old_label != label:
                # append/take/take_label maintain strictly positive (>EPS)
                # fragments; compact_runs only adds such fragments together.
                result.append([old_label, n])
                continue
            moved = min(n, remaining)
            remaining -= moved
            if n-moved > EPS:
                result.append([old_label, n-moved])
        prediction_cache.invalidate(self)
        self.q = result
        return [(label, amount)]

    def compact_runs(self, behavior):
        """Coalesce identical-ID fragments inside one equivalent-flow run.

        Never cross a different destination/continuation behavior. Labels and
        mass remain separate, and first-occurrence order is retained. This
        changes only fragment order INSIDE a response-equivalent run, where
        sending, receiving, route and lateral-rate laws are identical.
        """
        buffer = self._array()
        if buffer is not None:
            buffer.compact(behavior)
            return
        result, run = deque(), {}
        previous = object()
        for label, n in self.q:
            key = behavior(label)
            if key != previous:
                result.extend([old, amount] for old, amount in run.items())
                run = {}
                previous = key
            run[label] = run.get(label, 0.)+n
        result.extend([old, amount] for old, amount in run.items())
        prediction_cache.invalidate(self)
        self.q = result


def tagged(v):
    # Retain both the current intended exit and initial vehicle identity.
    return (v['connector'], v['vehicle'])


def unassigned_continuation(v, routes):
    """No prescribed onward route on71; not an inferred turning destination.

    A1133 route ending on126 is different from an unknown vehicle BEFORE1126
    on10643. The latter must still encounter a route assignment and is excluded.
    """
    if v['connector'] is not None or v.get('route_next_link_conflict'):
        return False
    if v['link'] == 10643:
        return False
    if v['route_decision'] is None and v['route_number'] is None:
        return True
    path = routes.get((v['route_decision'], v['route_number']))
    return bool(path and path[-1] in (126, 10641))


class IndexedLateralDepartures:
    """Edit a FIFO's labelled fragments in place during one lateral phase.

    No arrival or longitudinal departure may interleave this phase. Each label
    has an ordered cursor; the physical FIFO is rebuilt once at commit. Keep
    the original fragment order, arithmetic and per-request overdraw guard.
    A zero primal with a nonzero tangent must still reach the next fragment.
    """
    def __init__(self, queue):
        self.queue = queue
        buffer = queue._array()
        if buffer is not None:
            self._array_phase = buffer.lateral(indexed=True)
            return
        self.rows = [[label, amount] for label, amount in queue.q]
        self.indices = defaultdict(deque)
        for index, (label, amount) in enumerate(self.rows):
            self.indices[label].append(index)

    def take_label(self, label, amount):
        phase = getattr(self,'_array_phase',None)
        if phase is not None:return phase.take(label,amount)
        indices = self.indices[label]
        available = 0.
        for index in indices:
            n = self.rows[index][1]
            available += getattr(n, '_validation_primal', n)
            # All surviving fragments are positive. The original ordered sum
            # can only increase; once its prefix passes the same guard, its
            # unseen suffix cannot change that verdict. Near an overdraw we
            # still compute the entire original sum, including its rounding.
            if amount <= available+1e-7:
                break
        if amount < -EPS or amount > available+1e-7:
            raise ArithmeticError('Lateral label overdraw')
        remaining = amount
        consumed = 0
        for index in indices:
            n = self.rows[index][1]
            moved = min(n, remaining)
            remaining -= moved
            left = n-moved
            if left > EPS:
                self.rows[index][1] = left
            else:
                self.rows[index] = None
                consumed += 1
            if (remaining == 0 and not getattr(remaining, 'tangent', None)
                    and not any(getattr(remaining, 'risks', ()))):
                break
        for _ in range(consumed):
            indices.popleft()
        return [(label, amount)]

    def commit(self):
        phase = getattr(self,'_array_phase',None)
        if phase is not None:
            phase.commit()
            return
        prediction_cache.invalidate(self.queue)
        self.queue.q = deque(row for row in self.rows if row is not None)


class UrbanTransport:
    def _array_owner(self):
        cache=prediction_cache.active()
        if cache is None or not cache.urban_pipeline_enabled:return None
        owner=cache.urban_pipelines.get(self)
        return owner if owner is not None and owner.native is not None else None

    def __deepcopy__(self,memo):
        owner=self._array_owner()
        if owner is not None:owner.publish_all()
        result=object.__new__(getattr(type(self),'_canonical_type',type(self)));memo[id(self)]=result
        result.__dict__.update(copy.deepcopy(vars(self),memo))
        return result

    """Local finite-volume approximation of126,10641 and five lanes of71.

    Longitudinal and lateral flows compete for the SAME old-state receiving
    space. No simultaneous swap creates an empty gap in two full lanes.
    A blocked prefix cannot be overtaken within a cell. Spatial order between
    vehicles inside one cell after a lateral insertion is an approximation.
    """
    def __init__(self, current, network, program, offset, speed, spacing, wave, lateral_access=False,
                 exchange_rates=(), continuation=False):
        root = ET.parse(network).getroot()
        links = {int(x.get('no')): x for x in root.findall('./links/link')}
        self.program, self.offset = program, offset
        self.time = current['time_s']
        self.speed, self.spacing, self.wave = speed, spacing, wave
        self.lateral_access = lateral_access
        self.continuation = continuation
        self.exchange_rates = {(r['road'], r['from_lane'], r['to_lane'], r['destination']): r['rate_per_s']
                               for r in exchange_rates}
        self.compact_equal_behavior = bool(exchange_rates)
        routes, _ = geometry(network)
        self.unrouted_labels = {tagged(v) for v in current['vehicles'] if unassigned_continuation(v, routes)}
        self.fallback_exits = {int(x.get('no')) for x in links.values() if x.get('direction') == 'ALL'
                               and x.find('./fromLinkEndPt') is not None
                               and x.find('./fromLinkEndPt').get('lane').split()[0] == '71'}
        if continuation:
            # The local model may apply fallback only if no later assignment
            # occurs on the represented continuation. Never ignore a decision.
            assert not any(int(d.get('link')) in (126,10641,71)
                           for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'))
            for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
                for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
                    if (int(d.get('no')), int(r.get('no'))) in {
                            (v['route_decision'], v['route_number']) for v in current['vehicles']
                            if unassigned_continuation(v, routes) and v['route_decision'] is not None}:
                        assert int(r.get('destLink')) in (126,10641)
        self.capacity_rate = speed * wave / (spacing * (speed + wave))
        self.exits = geometry(network)[1]
        self.heads = {int(x.get('lane').split()[1]): float(x.get('pos'))
                      for x in root.findall('./signalHeads/signalHead')
                      if x.get('lane', '').startswith('71 ')}
        self.edges = {}
        # The off-ramp joins the final126 cell; exact merge position is retained
        # as a reported spatial approximation, not a fictitious new connector.
        self.merge_position = float(links[10643].find('./toLinkEndPt').get('pos'))
        self.lengths = {}
        for road in (126, 10641, 71):
            points = list(links[road].find('./geometry/linkPolyPts'))
            self.lengths[road] = sum(math.sqrt(sum((float(a.get(k, '0')) - float(b.get(k, '0')))**2
                                                 for k in ('x', 'y', 'zOffset')))
                                     for a, b in zip(points, points[1:]))
        end126 = float(links[10641].find('./fromLinkEndPt').get('pos'))
        side = self.exits[10642]['position_m']
        end71 = max(x['position_m'] for x in self.exits.values())
        self.edges[126] = [end126 * i / 8 for i in range(9)]
        self.edges[10641] = [self.lengths[10641] * i / 2 for i in range(3)]
        self.edges[71] = [0., side/2, side, (side+end71)/2, end71]
        if min(b-a for edges in self.edges.values() for a, b in zip(edges, edges[1:])) < speed:
            raise ValueError('1s finite-volume CFL condition not satisfied')
        self.cells, self.cap, self.dx = {}, {}, {}
        self.projection = {}
        local = [v for v in current['vehicles'] if v['link'] != 10643]
        if any(v['link'] not in self.edges for v in local):
            raise ValueError('Unmodelled current local link: do not discard its vehicles')
        for road, edges in self.edges.items():
            for lane in range(1, 6 if road == 71 else 3):
                vehicles = sorted((v for v in local if v['link'] == road and v['lane'] == lane),
                                  key=lambda v: v['position_m'])
                env = ReceivingEnvelope(edges[-1], spacing, speed, wave,
                                        [min(edges[-1], v['position_m']) for v in vehicles])
                self.projection[f'{road}:{lane}'] = env.projection_max_m
                for i, (a, b) in enumerate(zip(edges, edges[1:])):
                    key = (road, lane, i)
                    self.dx[key], self.cap[key] = b-a, (b-a)/spacing
                    packets = []
                    for v, pos in reversed(list(zip(vehicles, env.positions))):
                        n = max(0., min(b, pos) - max(a, pos-spacing)) / spacing
                        if n > EPS:
                            packets.append((tagged(v), n))
                    self.cells[key] = FIFO(packets)
        self.initial = self.counts()
        self.admitted, self.departed = Counter(), Counter()
        self.movements, self.blocked_seconds = Counter(), Counter()
        self.vehicle_seconds = 0.
        self.checks = 0
        self.check()

    def counts(self):
        result = Counter()
        for q in self.cells.values():
            result.update(q.counts())
        return result

    def check(self):
        now = self.counts()
        for label in set(now) | set(self.initial) | set(self.admitted) | set(self.departed):
            if abs(now[label] - self.initial[label] - self.admitted[label] + self.departed[label]) > 1e-7:
                raise ArithmeticError(('Destination/vehicle conservation failed', label))
        for key, q in self.cells.items():
            if not -EPS <= q.stock <= self.cap[key]+1e-7:
                raise ArithmeticError(('Finite lane cell storage failed', key, q.stock, self.cap[key]))
        self.checks += 1

    def route(self, key, label, receiving):
        road, lane, cell = key
        destination = label[0]
        if road == 71:
            fallback = self.continuation and (label in self.unrouted_labels or label == (None, 'unrouted'))
            required = self.exits[destination]['lanes'] if destination is not None else None
            deadline = 1 if destination == 10642 else len(self.edges[71])-2
            if destination == 10642 and cell > deadline:
                # No reversing, deletion or teleport back to a missed exit.
                return None, 'past_turn'
            if required and lane not in required:
                other = lane + (1 if lane < min(required) else -1)
                target = (road, other, cell)
                if not self.lateral_access and receiving.get(target, 0.) > EPS:
                    return target, 'lateral'
                if cell >= deadline:
                    return None, 'lane_access'
            if destination == 10642 and lane == 1 and cell == deadline:
                return ('exit', 10642), 'exit'
            if fallback and cell == 1 and lane in self.exits[10642]['lanes'] and 10642 in self.fallback_exits:
                return ('exit', 10642), 'unrouted_exit'
            if cell == len(self.edges[road])-2:
                sg = 2 if lane <= 3 else 5
                if self.program.state_at(self.time+1, sg, controller_offset_sec=self.offset) != 'GREEN':
                    return None, 'signal'
                # Unknown labels remain unknown even when normal outflow occurs.
                if fallback:
                    possible = [d for d in self.fallback_exits if lane in self.exits[d]['lanes']
                                and self.exits[d]['position_m'] > self.edges[71][-2]]
                    if not possible: return None, 'unresolved_continuation'
                    return ('exit', min(possible, key=lambda d: self.exits[d]['position_m'])), 'unrouted_exit'
                return ('exit', destination), 'exit'
        if cell < len(self.edges[road])-2:
            return (road, lane, cell+1), 'forward'
        if road == 126:
            return (10641, lane, 0), 'forward'
        if road == 10641:
            return (71, lane+1, 0), 'forward'
        raise AssertionError(('Missing route', key, label))

    def step(self, external, *, exit_receiving=None, indexed_lateral=False):
        """external: name -> (entry cell, FIFO offered now).

        Unaccepted external packets stay in their upstream queue. External
        offers from10643 are bounded by its own causal sending envelope.
        """
        cache = prediction_cache.active()
        if cache is not None and cache.urban_pipeline_enabled:
            from evaluation.controllers.sdmpc_tangent_urban import step
            return step(self, external, exit_receiving, indexed_lateral)
        exit_room = None
        if exit_receiving is not None:
            if set(exit_receiving) != set(self.exits):
                raise ValueError('Every physical urban exit needs a receiving budget')
            exit_room = dict(exit_receiving)
            if any(not math.isfinite(n) or n < 0 for n in exit_room.values()):
                raise ValueError('Invalid physical urban exit receiving budget')
        self.last_transfers = []

        def routed(key, label, receiving):
            target, reason = self.route(key, label, receiving)
            if exit_room is not None and target == ('exit', None):
                # Preserve the unknown destination label. At this downstream
                # cross-section, the current physical lane has only one normal
                # forward connector; this identifies an event, not a new route.
                road, lane, cell = key
                possible = [d for d, e in self.exits.items()
                            if lane in e['lanes'] and e['position_m'] > self.edges[road][-2]]
                if len(possible) != 1:
                    raise ValueError('Unknown destination has no unique physical exit')
                target = ('exit', possible[0])
            return target, reason

        old_n = {k: q.stock for k, q in self.cells.items()}
        signal_room = None
        fraction_at = getattr(self.program, 'service_fraction_at', None)
        if fraction_at is not None:
            signal_room = {k: self.capacity_rate*fraction_at(self.time+1,
                2 if k[1] <= 3 else 5, controller_offset_sec=self.offset)
                for k in self.cells if k[0] == 71 and k[2] == len(self.edges[71])-2}
        receiving = {k: max(0., min(self.capacity_rate, self.wave/self.dx[k]*(self.cap[k]-n)))
                     for k, n in old_n.items()}
        sending = {k: min(self.capacity_rate, self.speed/self.dx[k]*n) for k, n in old_n.items()}
        sources = dict(self.cells)
        for name, (target, queue) in external.items():
            key = ('external', name)
            sources[key] = queue
            sending[key] = queue.stock
        # Start-of-step budgets cover lateral and forward allocations together;
        # their shared receiving space must never be certified twice.
        self.last_sending_limits = dict(sending)
        self.last_receiving_limits = dict(receiving)
        additions = defaultdict(list)
        accepted = defaultdict(list)
        if self.lateral_access:
            lateral_requests = defaultdict(list)
            for key, queue in self.cells.items():
                road, lane, cell = key
                budget = sending[key]
                for label, n in queue.q:
                    destination = label[0]
                    required = self.exits[destination]['lanes'] if destination is not None and road == 71 else None
                    mandatory = required and lane not in required and not (destination == 10642 and cell > 1)
                    if mandatory:
                        other = lane + (1 if lane < min(required) else -1)
                        # Diagnostic ablation: isolate which destination class
                        # causes the blanket-defer failure. This selector is
                        # not a calibrated, destination-specific driving law.
                        selected = getattr(self, 'defer_destinations', None)
                        defer = (getattr(self, 'defer_mandatory_while_forward_open', False)
                                 and (selected is None or destination in selected))
                        prefer_space = getattr(self, 'prefer_more_receiving_space', False)
                        if defer or prefer_space:
                            forward,reason=self.route(key,queue.q[0][0],receiving)
                            # Do not put a vehicle into a queued destination
                            # lane early while this lane's FIFO can progress.
                            # At the connector deadline route() blocks forward
                            # motion, so access remains mandatory there.
                            threshold = receiving.get((road,other,cell),0.) if prefer_space else 0.
                            if reason=='forward' and receiving.get(forward,0.)>threshold+EPS:
                                continue
                        requests = [(other, min(n, budget))]
                    else:
                        rates = [(other, self.exchange_rates.get((road,lane,other,destination), 0.))
                                 for other in (lane-1,lane+1)
                                 if (road,other,cell) in self.cells and (not required or other in required)]
                        total = sum(rate for other, rate in rates)
                        quantity = min(budget, n * -math.expm1(-total))
                        requests = [(other, quantity*rate/total) for other,rate in rates if rate > 0] if total else []
                    for other, offered in requests:
                        target = (road, other, cell)
                        # Diagnostic sensitivity only. Starting a fractional
                        # transfer into a cell with less than one body's space
                        # can mimic a microscopic gap that does not exist.
                        # This cell-local condition is NOT a validated gap law:
                        # real insertion can span cell edges and moving queues.
                        footprints = getattr(self, 'lateral_start_footprints', None)
                        if footprints and self.cells[target].counts().get(label, 0.) <= EPS:
                            needed = footprints.get(label[1], footprints[None])/self.spacing
                            if self.cap[target]-old_n[target] < needed-EPS:
                                continue
                        if offered > EPS and receiving.get(target, 0.) > EPS:
                            lateral_requests[target].append((key, label, offered))
                            budget -= offered
                    if budget <= EPS: break
            departures = {}
            for target, requests in lateral_requests.items():
                total = sum(n for key, label, n in requests)
                fraction = min(1., receiving[target]/total)
                for key, label, demand in requests:
                    n = demand*fraction
                    if n <= EPS: continue
                    queue = self.cells[key]
                    if indexed_lateral:
                        if key not in departures:
                            departures[key] = IndexedLateralDepartures(queue)
                        queue = departures[key]
                    packets = queue.take_label(label, n)
                    self.last_transfers.append((key, target, tuple(packets)))
                    additions[target].extend(packets)
                    sending[key] -= n
                    self.movements[(key, target, 'lateral')] += n
                receiving[target] = max(0., receiving[target]-total*fraction)
            for departure in departures.values():
                departure.commit()
        active = set(sources)
        # Iterative prefix allocation: simultaneous requests share receiving
        # proportionally; a partially served prefix cannot be bypassed.
        while active:
            requests = defaultdict(list)
            for key in sorted(active, key=str):
                q = sources[key]
                if not q.q or sending[key] <= EPS:
                    continue
                target, reason = ((external[key[1]][0], 'entry') if key[0] == 'external'
                                  else routed(key, q.q[0][0], receiving))
                if target is None:
                    self.blocked_seconds[(key, reason)] += 1
                    continue
                # Competing streams request their whole compatible FIFO prefix,
                # not the arbitrary size of its first numerical fragment.
                demand = 0.
                available = sending[key]
                if signal_room is not None and target[0] == 'exit' and key in signal_room:
                    available = min(available, signal_room[key])
                    if available <= EPS:
                        continue
                for label, n in q.q:
                    next_target = external[key[1]][0] if key[0] == 'external' else routed(key,label,receiving)[0]
                    if next_target != target: break
                    demand += min(n, available-demand)
                    if demand >= available-EPS: break
                requests[target].append((key, demand))
            active = set()
            for target in sorted(requests, key=str):
                values = requests[target]
                total = math.fsum(v[1] for v in values)
                fraction = ((1. if exit_room is None else min(1., exit_room[target[1]]/total))
                            if target[0] == 'exit' else min(1., receiving[target]/total))
                for key, demand in values:
                    amount = demand*fraction
                    if amount <= EPS:
                        continue
                    got = sources[key].take(amount)
                    self.last_transfers.append((key, target, tuple(got)))
                    sending[key] -= amount
                    if key[0] == 'external':
                        accepted[key[1]].extend(got)
                        for label, n in got: self.admitted[label] += n
                    if target[0] == 'exit':
                        if signal_room is not None and key in signal_room:
                            signal_room[key] = max(0., signal_room[key]-amount)
                        for label, n in got: self.departed[label] += n
                    else:
                        additions[target].extend(got)
                    for label, n in got:
                        reason = 'entry' if key[0] == 'external' else self.route(key,label,receiving)[1]
                        self.movements[(key, target, reason)] += n
                    if fraction >= 1.-EPS:
                        active.add(key)
                if target[0] != 'exit':
                    receiving[target] = max(0., receiving[target]-total*fraction)
                elif exit_room is not None:
                    exit_room[target[1]] = max(0., exit_room[target[1]]-total*fraction)
        for target, packets in additions.items():
            for label, n in packets:
                self.cells[target].append(label, n)
        if self.compact_equal_behavior:
            for queue in self.cells.values():
                queue.compact_runs(lambda label: (label[0], self.continuation and
                    (label in self.unrouted_labels or label == (None, 'unrouted'))))
        new_n = sum(q.stock for q in self.cells.values())
        self.vehicle_seconds += (sum(old_n.values())+new_n)/2
        self.time += 1
        self.check()
        return dict(accepted)


class ArrayUrbanTransport(UrbanTransport):
    """Transient access hooks only for the enabled, query-owned numeric store.

    Normal scalar prediction does not pay a custom attribute lookup. Copies
    and scope exit restore the original public class and all public fields.
    """
    _canonical_type=UrbanTransport

    def __getattribute__(self,name):
        if name in ('initial','admitted','departed','movements','vehicle_seconds'):
            owner=object.__getattribute__(self,'_array_owner')()
            if owner is not None:
                owner.publish(name);owner.exposed.add(name)
        return object.__getattribute__(self,name)

    def __setattr__(self,name,value):
        if name in ('initial','admitted','departed','movements','vehicle_seconds'):
            owner=object.__getattribute__(self,'_array_owner')()
            if owner is not None:
                owner.exposed.add(name);owner.pending_public.discard(name)
        object.__setattr__(self,name,value)


UrbanTransport._array_variant=ArrayUrbanTransport


class CoupledPort:
    def __init__(self, lanes, current, history, network, program, offset, speed, spacing, wave, lateral_access=False,
                 history_exchange=False, continuation=False):
        self.lanes = lanes
        self.urban = UrbanTransport(current, network, program, offset, speed, spacing, wave, lateral_access,
                                    history.get('exchange_rates', []) if history_exchange else (), continuation)
        self.start = self.urban.time
        self.fifo = [FIFO((tagged(v), 1.) for v in sorted(
            (v for v in current['vehicles'] if v['link'] == 10643 and v['lane'] == lane),
            key=lambda v: -v['position_m'])) for lane in (1, 2)]
        self.initial = [q.counts() for q in self.fifo]
        self.entered, self.left = [Counter(), Counter()], [Counter(), Counter()]
        self.history = history
        self.pending = defaultdict(FIFO)
        self.trace = []
        self.check()

    def check(self):
        for g, (lane, queue) in enumerate(zip(self.lanes, self.fifo)):
            if abs(lane.stock-queue.stock) > 1e-7:
                raise ArithmeticError('Hydraulic and destination inventory differ')
            n = queue.counts()
            for label in set(n) | set(self.initial[g]) | set(self.entered[g]) | set(self.left[g]):
                if abs(n[label]-self.initial[g][label]-self.entered[g][label]+self.left[g][label]) > 1e-7:
                    raise ArithmeticError('Off-ramp labelled mass imbalance')

    def admit(self, lane, amount):
        # Current composition is a forecast assumption, not a newly observed
        # vehicle route. Known configured routes are not changed in VISSIM.
        mixture = self.history['off_composition'][lane]
        for destination, fraction in mixture:
            label = (destination, None)
            n = amount*fraction
            self.fifo[lane].append(label, n)
            self.entered[lane][label] += n
        self.check()

    def step(self, time):
        if time != self.urban.time:
            raise ValueError('Noncontiguous coupled time')
        # Repeat only the PRE-cutoff150s boundary-arrival pattern. This retains
        # its platoon phase but is not a claim that future arrivals are known.
        phase = (time-self.start) % self.history.get('repeat_period_s', 150)
        for i, (road, lane, destination, amount) in enumerate(self.history['background'].get(phase, [])):
            flags = self.history.get('fallback_background', {}).get(phase, [])
            fallback = self.urban.continuation and i < len(flags) and flags[i]
            self.pending[(road, lane)].append((destination, 'unrouted' if fallback else None), amount)
        external = {f'background:{r}:{l}': ((r, l, 0), q) for (r, l), q in self.pending.items()}
        offered = []
        for g, p in enumerate(self.lanes):
            n = max(0., min(p.stock, p.envelope.qmax, p.sending_bound(time+1-p.start)-p.departed))
            offered.append(n)
            prefix = FIFO(copy.deepcopy(list(self.fifo[g].q)))
            prefix = FIFO(prefix.take(n))
            external[f'off:{g}'] = ((126, g+1, len(self.urban.edges[126])-2), prefix)
        accepted = self.urban.step(external)
        amounts = []
        for g, p in enumerate(self.lanes):
            packets = accepted.get(f'off:{g}', [])
            n = math.fsum(amount for label, amount in packets)
            served = p.release(time, 1, n*3600)
            if abs(n-served) > 1e-7:
                raise ArithmeticError('Urban receiving exceeds off sending')
            actual = self.fifo[g].take(served)
            a, b = Counter(), Counter()
            for label, amount in actual: a[label] += amount
            for label, amount in packets: b[label] += amount
            if any(abs(a[k]-b[k]) > 1e-7 for k in set(a)|set(b)):
                raise ArithmeticError('Coupling changed destination or vehicle identity')
            self.left[g].update(a)
            amounts.append(served)
        self.check()
        self.trace.append(dict(time_s=time+1, off_departures=amounts, off_sending=offered,
                               urban_n=sum(q.stock for q in self.urban.cells.values()),
                               upstream_unaccepted=sum(q.stock for q in self.pending.values())))
        return sum(amounts)


def history_inputs(frames, cutoff, routes, exits):
    """Only current/past observations accepted; future maps are rejected."""
    if any(t > cutoff for t in frames):
        raise ValueError('Future traffic supplied to boundary forecaster')
    states = {t: observe(frames[t], routes, exits) for t in range(cutoff-150, cutoff+1)}
    indices = {t: {v['vehicle']: v for v in s['vehicles']} for t, s in states.items()}
    background = defaultdict(list)
    fallback_background = defaultdict(list)
    composition = [Counter(), Counter()]
    exposure, changes = Counter(), Counter()
    for t in range(cutoff-149, cutoff+1):
        before, now = indices[t-1], indices[t]
        for vid, v in before.items():
            if v['link'] in (126,10641,71):
                exposure[v['link'],v['lane'],v['connector']] += 1
                next_v = now.get(vid)
                if next_v and next_v['link'] == v['link'] and next_v['lane'] != v['lane']:
                    changes[v['link'],v['lane'],next_v['lane'],v['connector']] += 1
        for vid, v in now.items():
            if vid not in before and v['link'] != 10643:
                if (v['link'], v['lane']) not in ((126,1), (126,2), (71,4), (71,5)):
                    raise ValueError(('Unexplained local entry', t, v))
                background[(t-cutoff-1) % 150].append((v['link'], v['lane'], v['connector'], 1.))
                fallback_background[(t-cutoff-1) % 150].append(unassigned_continuation(v, routes))
        for vid, v in before.items():
            if v['link'] == 10643 and vid in now and now[vid]['link'] != 10643:
                composition[v['lane']-1][v['connector']] += 1
    result = []
    for g, counts in enumerate(composition):
        if not sum(counts.values()):
            counts.update(v['connector'] for v in states[cutoff]['vehicles']
                          if v['link'] == 10643 and v['lane'] == g+1)
        if not sum(counts.values()):
            counts[None] = 1
        result.append([(key, n/sum(counts.values())) for key, n in counts.items()])
    return dict(background=dict(background), off_composition=result,
                background_arrivals=sum(len(x) for x in background.values()),
                fallback_background=dict(fallback_background),
                exchange_rates=[dict(road=road, from_lane=lane, to_lane=other, destination=destination,
                                     events=n, exposure_veh_s=exposure[road,lane,destination],
                                     rate_per_s=n/exposure[road,lane,destination])
                                for (road,lane,other,destination), n in changes.items()],
                information_cutoff_s=cutoff)
