"""Capture the failed debit operands once; no completed or optimized forecast."""
import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.argv=[str(HERE/'forecast.py'),'--at','2400']
loader=importlib.util.spec_from_file_location('debit_forecast',HERE/'forecast.py')
m=importlib.util.module_from_spec(loader);loader.loader.exec_module(m)
m.OUT=HERE/'debit_repro'
try:
    m.main()
except ValueError as exc:
    if not str(exc).startswith('Regular head evidence differs'):raise
    tb=exc.__traceback__
    while tb:
        f=tb.tb_frame
        if f.f_code.co_name=='urban_substep_accounted':
            v=f.f_locals;group=v['group'];sources=v['accepted_sources'];used=v['used'][group]
            result=dict(error=str(exc),python=sys.version,step=v['step_idx'],group=group,
                        accepted_sources=sources,builtin_sum=sum(sources.values()),used=used,
                        difference=sum(sources.values())-used,complete_forecasts=0)
            (HERE/'debit_failure_evidence.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
            print(json.dumps(result),flush=True)
            break
        tb=tb.tb_next
    else:raise
