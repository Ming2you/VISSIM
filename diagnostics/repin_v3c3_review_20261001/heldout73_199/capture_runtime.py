"""Reuse the real recorded-state initializer, then stop before any prediction.

No new adapter, interpolation, native execution or calibration. This captures
the causal controller state to assess compatibility with local component tests.
"""
import ctypes
import ctypes.wintypes
import dataclasses
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'


def primitive(value, path='root'):
    if value is None or type(value) in (str,int,float,bool):return value
    if isinstance(value,(list,tuple)):return [primitive(x,f'{path}[{i}]') for i,x in enumerate(value)]
    if isinstance(value,dict):
        assert all(type(k) in (str,int) for k in value),path
        return {str(k):primitive(v,path+'.'+str(k)) for k,v in value.items()}
    # Declared data only; runtime object instances are not silently flattened
    # into something that pretends to be a complete restart checkpoint.
    if dataclasses.is_dataclass(value):
        return primitive({f.name:getattr(value,f.name) for f in dataclasses.fields(value)},path)
    raise TypeError((path,type(value).__name__))


def main():
    lane_mode=sys.argv[1].split('=',1)[1] if len(sys.argv)==2 and sys.argv[1].startswith('--coupled-lanes=') else None
    assert lane_mode in (None,'disabled','enabled')
    forecast_mode=sys.argv[1:]==['--forecast']
    audit_mode=sys.argv[1:]==['--regional-audit202']
    assert forecast_mode or lane_mode or audit_mode or not sys.argv[1:]
    assert (HERE/'capture.json.gz').exists() if forecast_mode or lane_mode or audit_mode else not (HERE/'capture.json.gz').exists()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes=[ctypes.wintypes.HANDLE,ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x4000)
    from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
    source=Path(probe.__file__)
    plan=json.loads((R/'replication_s73_95/postprocess_plan.json').read_bytes())
    args=plan['commands']['forecast'][1:]
    label='s73_runtime199_forecast' if forecast_mode else 's73_runtime199_v2'
    if lane_mode:label='s73_coupled200_'+lane_mode+('_v5' if lane_mode=='enabled' else '')
    if audit_mode:label='s73_regional_audit202_v2'
    args=[('--probe-label='+label if a.startswith('--probe-label=') else a) for a in args]
    original_probe=probe.probe_levers
    received=[]
    def capture(captured,reference,output,**kwargs):
        assert not received
        assert captured['state'].time_sec==2700
        assert kwargs['replay_pair']['seed']==73
        assert not kwargs['replay_pair']['future_states_used']
        assert len(captured['forecast'])==3
        extensions={}
        for name,obj in (('state',captured['state']),('network',captured['cfg'].network)):
            declared={f.name for f in dataclasses.fields(obj)}
            extensions[name]={k:type(v).__name__ for k,v in vars(obj).items() if k not in declared}
        payload=primitive(dict(state=captured['state'],cfg=captured['cfg'],forecast=captured['forecast'],
            reference=reference,raw=captured['raw'],metadata=captured['metadata'],
            replay_pair=kwargs['replay_pair']))
        if forecast_mode or lane_mode or audit_mode:
            expected=json.loads(gzip.decompress((HERE/'capture.json.gz').read_bytes()))
            # Runtime path provenance may use this new output directory; physical
            # state, demand forecast and actual prior command must be exact.
            checks={k:payload[k]==expected[k] for k in ('state','forecast','reference')}
            assert all(checks.values()),checks
            if audit_mode:
                from diagnostics.repin_v3c3_review_20261001.coupled_lane200 import hooks
                from diagnostics.repin_v3c3_review_20261001.regional_audit202 import audit
                patch,stats=hooks.install(captured,True,report_dir=audit.HERE)
                try:original_probe(captured,reference,output,prepared_probe_callback=audit.run,**kwargs)
                finally:hooks.restore(patch)
                (audit.HERE/'coupling_stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
                received.append(dict(audit=True,output=str(output)))
                return
            pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted((ROOT/'evaluation/controllers').glob('*.py'))}
            destination=R/'coupled_lane200' if lane_mode else HERE
            protocol_name=lane_mode+'_protocol.json' if lane_mode else 'forecast_protocol.json'
            assert not (destination/protocol_name).exists()
            (destination/protocol_name).write_text(json.dumps(dict(
                comparison=('Frozen148 structural connection to the full-network runtime, deployed FD retained; diagnostic '+lane_mode
                            if lane_mode else 'Current deployed plant, same native73 common state and recorded two command sequences. Not unadopted148 local lane candidate.'),
                budget=dict(autonomous450=2,fits=0,native=0,FZP=0),initial_state_checks=checks,
                source_sha256=pins,output=str(output),capture_sha256=hashlib.sha256((HERE/'capture.json.gz').read_bytes()).hexdigest(),
                gate='Compare meaningful OmegaTTT sign (>0.5vehh) and observed best of two commands; absolute, flow, ramp and outside effects remain reported. No tuning from73 results.',
                no_future_observation_inputs=True,production_adopted=False),indent=2),encoding='utf-8')
            if lane_mode:
                from diagnostics.repin_v3c3_review_20261001.coupled_lane200 import hooks
                patch,stats=hooks.install(captured,lane_mode=='enabled')
                try:original_probe(captured,reference,output,**kwargs)
                finally:
                    hooks.restore(patch)
                    (destination/(lane_mode+'_coupling_stats.json')).write_text(json.dumps(stats,indent=2),encoding='utf-8')
            else:original_probe(captured,reference,output,**kwargs)
            assert pins=={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted((ROOT/'evaluation/controllers').glob('*.py'))}
            received.append(dict(forecast=True,output=str(output)))
            return
        data=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
        (HERE/'capture.json.gz').write_bytes(gzip.compress(data))
        receipt=dict(status='CAUSAL_RUNTIME_CAPTURED_NO_FORECAST',
            initial_sec=2700,history='Canonical native150 observations and verified executed past VSL/head history',
            shared_native_initial_verified=True,new_forecasts=0,new_fits=0,new_native=0,fzp_reads=0,
            output_directory=str(output),capture_sha256=hashlib.sha256((HERE/'capture.json.gz').read_bytes()).hexdigest(),
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            fields={k:list(v) if isinstance(v,dict) else len(v) for k,v in payload.items()},
            runtime_extension_types_not_serialized=extensions,
            limitation='Declared data plus raw observations only, NOT a restart checkpoint: runtime class instances are explicitly listed, not serialized. Reinitialize them with the canonical initializer. No30s interpolation or new gain-validation result.')
        (HERE/'capture_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
        received.append(receipt)
        print(json.dumps({k:v for k,v in receipt.items() if k!='fields'},ensure_ascii=False),flush=True)
    probe.probe_levers=capture
    sys.argv=[str(source),*args]
    probe.main()
    assert len(received)==1


if __name__=='__main__':main()
