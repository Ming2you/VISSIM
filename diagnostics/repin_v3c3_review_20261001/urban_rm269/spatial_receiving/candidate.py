"""Diagnostic-only causal receiving on10681; reuse the existing envelope.

This is a receiving-only hybrid, not a replacement LTM sending model. Meter
service, merge supply and each original vehicle/cohort owner are unchanged.
The existing urban wave speed and ramp travel speed are transferred assumptions,
not new fits or identified10681 fundamental-diagram parameters.
"""
from evaluation.controllers import physical_ramp_boundary as pr
from evaluation.controllers.physical_urban_transport import ReceivingEnvelope

def attach(buffer,wave):
    if buffer.lanes!=1 or buffer.head_position_m<=0:
        raise ValueError('Positive-length lane-resolved prehead required')
    if hasattr(buffer,'_spatial_entry'):raise ValueError('Duplicate spatial receiving installation')
    env=ReceivingEnvelope(buffer.head_position_m,buffer.spacing_m,buffer._speed_mps,wave,
        [pos for pos,speed,lane in buffer.initial_cohorts if pos<=buffer.head_position_m])
    buffer._spatial_entry={'envelope':env,'start':buffer.time_sec,'departures':[0.],
        'admitted_start':buffer.cumulative_admitted_veh,'interval_end':buffer.time_sec,'dt':0.}

def offer(buffer,original_room):
    x=buffer._spatial_entry;dt=x['dt']
    if not dt:return 0.
    elapsed=x['interval_end']-x['start']
    past=x['departures'][:int(elapsed-dt)+1]
    available=x['envelope'].offer(elapsed,dt,x['admitted_start'],past)
    # Multiple reads/commits cannot spend the same one-second flow budget twice.
    used=buffer.cumulative_admitted_veh-x['admitted_start']
    if used < -1e-8:raise ArithmeticError('Cumulative admissions went backwards')
    return min(original_room,max(0.,available-used))

def install(wave):
    original_init=pr.PhysicalRampBoundary.__init__
    original_begin=pr.PhysicalRampBoundary.begin_interval
    original_head=pr.PhysicalRampBoundary.apply_head_service
    original_space=pr.PhysicalRampBoundary._admission_space_veh
    receipts=[]
    def init(self,*a,**kw):
        original_init(self,*a,**kw)
        if self.connector_id=='10681' and self.lanes==1:
            attach(self,wave);e=self._spatial_entry['envelope']
            receipts.append(dict(start=self.time_sec,vehicles=e.initial,wave_m_s=wave,
                lag_sec=e.lag,qmax_veh_s=e.qmax,projection_max_m=e.projection_max_m,
                travel_speed_kmh=self.travel_speed_kmh))
    def begin(self,start_sec,duration_sec=10.,**kw):
        if hasattr(self,'_spatial_entry') and duration_sec!=1:
            raise ValueError('Diagnostic receiving requires the existing1s ramp step')
        result=original_begin(self,start_sec,duration_sec,**kw)
        if hasattr(self,'_spatial_entry'):
            x=self._spatial_entry
            if len(x['departures'])!=int(start_sec-x['start'])+1:
                raise ValueError('Noncontiguous causal head history')
            x.update(admitted_start=self.cumulative_admitted_veh,interval_end=start_sec+duration_sec,dt=duration_sec)
        return result
    def head(self,*a,**kw):
        result=original_head(self,*a,**kw)
        if hasattr(self,'_spatial_entry'):
            self._spatial_entry['departures'].append(self.cumulative_head_service_veh)
        return result
    def space(self):
        value=original_space(self)
        return offer(self,value) if hasattr(self,'_spatial_entry') else value
    pr.PhysicalRampBoundary.__init__=init
    pr.PhysicalRampBoundary.begin_interval=begin
    pr.PhysicalRampBoundary.apply_head_service=head
    pr.PhysicalRampBoundary._admission_space_veh=space
    from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
    runtime_init=LaneRampRuntime.__init__
    def runtime(self,component,*a,**kw):
        if component.ramp_lane_exchange.get('RM_C10681'):
            raise ValueError('Spatial receiving needs explicit lateral-history support before ramp lane exchange')
        runtime_init(self,component,*a,**kw)
    LaneRampRuntime.__init__=runtime
    return receipts
