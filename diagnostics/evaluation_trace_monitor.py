"""CPython 3.12 monitoring transport for the unchanged v1 record semantics.

No CALL/C_RETURN events and no sys.settrace hook. PY_START discovery is disabled
at each unselected code location; PY_RETURN and LINE are local to selected code.
Callbacks own no model state and their main-thread frame must match the event.
"""
from __future__ import annotations

import atexit
import os
import sys
import threading

from diagnostics import evaluation_trace as base
from diagnostics.evaluation_trace_local import LocalRecorder


class Monitor:
    def __init__(self, recorder, local=None, tool_id=3):
        self.recorder, self.local, self.tool_id = recorder, local, tool_id
        self.thread_id = threading.get_ident()
        self.specs, self.armed = {}, set()
        self.finished = False
        self.counts = {'discovery_callbacks':0, 'selected_start':0, 'selected_return':0,
                       'line_callbacks':0, 'candidate_lines':0, 'unwind_callbacks':0,
                       'foreign_thread_events':0, 'frame_mismatch':0}
        self.mon=sys.monitoring; self.ev=self.mon.events
        self.callbacks={self.ev.PY_START:self.start, self.ev.PY_RETURN:self.returned,
                        self.ev.LINE:self.line, self.ev.PY_UNWIND:self.unwind}

    def spec(self, code):
        if code not in self.specs:
            self.specs[code]=(self.recorder.selector(code), self.local.targets.get(code) if self.local else None)
        return self.specs[code]

    def main(self):
        if threading.get_ident()!=self.thread_id:
            self.counts['foreign_thread_events']+=1
            return False
        return True

    def valid_frame(self, frame, code):
        if frame.f_code is not code:
            self.counts['frame_mismatch']+=1
            self.recorder.errors.append({'event':'monitor_frame_mismatch','function':code.co_qualname})
            return False
        return True

    def dispatch(self, frame, event, result):
        if self.local:
            self.local.profile(frame,event,result)
        else:
            self.recorder.profile(frame,event,result)

    def start(self, code, instruction_offset):
        self.counts['discovery_callbacks']+=1
        kind,spec=self.spec(code)
        if kind is None and spec is None:
            return self.mon.DISABLE
        # Code events are per interpreter, not per thread. Arm before filtering
        # a foreign first caller; never DISABLE a selected code on that account.
        if code not in self.armed:
            events=self.ev.PY_RETURN
            if spec is not None and spec['mode']=='counter':events |= self.ev.LINE
            self.mon.set_local_events(self.tool_id,code,events)
            self.armed.add(code)
        if not self.main():return
        frame=sys._getframe(1)
        if not self.valid_frame(frame,code):return
        self.counts['selected_start']+=1
        self.dispatch(frame,'call',None)

    def returned(self, code, instruction_offset, retval):
        if not self.main():return
        frame=sys._getframe(1)
        if not self.valid_frame(frame,code):return
        self.counts['selected_return']+=1
        self.dispatch(frame,'return',retval)

    def line(self, code, line_number):
        self.counts['line_callbacks']+=1
        spec=self.spec(code)[1]
        if spec is None or line_number not in spec['lines']:
            return self.mon.DISABLE
        if not self.main():return
        frame=sys._getframe(1)
        if not self.valid_frame(frame,code):return
        self.counts['candidate_lines']+=1
        try:self.local.candidate(frame,spec)
        except Exception as exc:
            self.local.errors.append({'event':'monitor_line','function':code.co_qualname,
                                      'type':type(exc).__name__,'message':str(exc)})

    def unwind(self, code, instruction_offset, exception):
        # PY_UNWIND is not a local event and cannot return DISABLE.
        self.counts['unwind_callbacks']+=1
        if not self.main():return
        kind,spec=self.spec(code)
        if kind is None and spec is None:return
        frame=sys._getframe(1)
        if not self.valid_frame(frame,code):return
        self.dispatch(frame,'return',None)

    def enable(self):
        self.mon.use_tool_id(self.tool_id,'decision-evaluation-monitor')
        try:
            for event,callback in self.callbacks.items():
                old=self.mon.register_callback(self.tool_id,event,callback)
                if old is not None:raise RuntimeError('Monitoring callback already occupied')
            self.mon.set_events(self.tool_id,self.ev.PY_START|self.ev.PY_UNWIND)
        except BaseException:
            self.stop();raise

    def stop(self):
        self.mon.set_events(self.tool_id,0)
        for code in self.armed:self.mon.set_local_events(self.tool_id,code,0)
        for event,expected in self.callbacks.items():
            old=self.mon.register_callback(self.tool_id,event,None)
            if old!=expected:self.recorder.errors.append({'event':'monitor_callback_replaced','event_id':event})
        self.mon.free_tool_id(self.tool_id)

    def close_for_writer(self):
        if (self.mon.get_tool(self.tool_id)!='decision-evaluation-monitor'
                or self.mon.get_events(self.tool_id)!=(self.ev.PY_START|self.ev.PY_UNWIND)
                or sys.getprofile() is not None or sys.gettrace() is not None):
            self.recorder.errors.append({'event':'monitor_ownership_changed'})
        self.stop()
        self.recorder.provenance['monitoring']={
            'backend':'CPython 3.12 sys.monitoring', 'counts':self.counts,
            'selected_code_count':len(self.armed), 'main_thread_filter':True,
            'no_builtin_call_callbacks':True,
            'timing_scope':'Monitoring/serialization overhead included; compare normal timing separately.'}
        if self.local:self.local.finish(monitoring_stopped=True)

    def finish(self):
        if self.finished:return
        self.finished=True
        from diagnostics.evaluation_trace_finalize import finish
        return finish(self.recorder,backend=self)


def install(directory, *, selector=base.classify, local_targets=None, include_local=True, disk_backed=True):
    mon=getattr(sys,'monitoring',None)
    if (mon is None or sys.version_info[:2]!=(3,12) or sys.implementation.name!='cpython'):
        raise RuntimeError('This validated transport requires CPython 3.12')
    if (sys.getprofile() is not None or sys.gettrace() is not None
            or threading.getprofile() is not None or threading.gettrace() is not None
            or any(mon.get_tool(i) is not None for i in range(6))
            or any(os.environ.get(k) for k in ('RW_DECISION_PROFILE_DIR','RW_PHASE_TRACE_DIR','RW_PHASE_COMMIT_TRACE_DIR'))):
        raise RuntimeError('Monitoring trace cannot coexist with another profiling/tracing tool')
    recorder=base.Recorder(directory,selector,disk_backed=disk_backed)
    local=LocalRecorder(recorder,local_targets) if include_local else None
    monitor=Monitor(recorder,local)
    recorder.provenance['transport']='monitoring; v1 event comparison semantics unchanged'
    monitor.enable()
    atexit.register(monitor.finish)
    return monitor
