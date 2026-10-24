"""Walk-forward source-only validation on saved observations. No FZP/model run."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,pickle,statistics
from evaluation.controllers import obs150_contract as oc,obs150_lane as ol
from evaluation.controllers.source_boundary import forecast,road_schedules
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.source_history328.candidate import predict

HERE=Path(__file__).resolve().parent;A=HERE.parent
HOLD=Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/hold/decisions_sdmpc31_g_2400_hold_s29')
PINS={}
def pin(p):
    p=Path(p);PINS[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(pin(p).read_bytes())

def main():
    assert not (HERE/'assessment.json').exists()
    plan=read(HERE/'plan.json');tests=(HERE/'tests.log').read_text(encoding='utf8')
    assert 'Ran 5 tests' in tests and 'OK' in tests
    cfg,_,_=pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle').read_bytes())
    schedules=road_schedules(cfg.network.native_input_schedule)
    context=SimpleNamespace(source_refs={r:'source:'+r for r in oc.ROADS},source_schedule=schedules)
    past=[];run_id=None
    for end in range(300,2851,150):
        s=read(HOLD/f'state_{end:06}.json');obs=s['obs150']
        rid=s['run_provenance']['run_id']
        if run_id is None:run_id=rid
        assert rid==run_id and s['sim_sec']==end
        allrows,_=oc.read_detector_csv(pin(obs['detector_config']['path']),obs['detector_config']['sha256'])
        rows=[r for r in allrows if r.role=='source'];frames={}
        for name,at in (('current',end),('previous',end-150)):
            meta=obs['frames'][name]
            frames[name]=oc.load_frame(pin(oc.resolve(obs,meta['path'])),meta['sha256'],at)
        err=oc.load_err_chunk(pin(oc.resolve(obs,obs['err']['chunk'])),obs['err']['chunk_sha256'])
        terms=oc.evaluate_boundaries(obs,rows,frames['current'],frames['previous'],err)
        source=ol.source_boundary(obs,context,terms)
        for road in oc.ROADS:
            assert source[road]['interval_s']==150
            if past:assert source[road]['admitted_cum']-past[-1]['source'][road]['admitted_cum']==source[road]['admitted_window']
        past.append(dict(end_sec=end,run_id=rid,source=source))
    bytime={r['end_sec']:r for r in past};results=[]
    for cutoff in plan['forecast_origins_hold']:
        row=dict(cutoff=cutoff,roads={})
        for road in oc.ROADS:
            history=[dict(end_sec=r['end_sec'],run_id=r['run_id'],**r['source'][road]) for r in past]
            current=bytime[cutoff]['source'][road]
            baseline=forecast(current['recent_vph'],current['backlog_veh'],schedules[road],cutoff,150,3,10)
            smoothed,receipt=predict(history,cutoff,current['backlog_veh'],schedules[road])
            # Truncating all later observations must produce identical output.
            assert (smoothed,receipt)==predict([r for r in history if r['end_sec']<=cutoff],cutoff,current['backlog_veh'],schedules[road])
            actual=[bytime[cutoff+150*k]['source'][road]['admitted_window'] for k in (1,2,3)]
            row['roads'][road]=dict(actual150=actual,baseline150=[v/24 for v in baseline],smoothed150=[v/24 for v in smoothed],
                                  receipt=receipt,backlog_proxy=current['backlog_veh'])
        results.append(row)
    metrics={}
    for road in oc.ROADS:
        metrics[road]={}
        for mode in ('baseline150','smoothed150'):
            windows=[r['roads'][road] for r in results]
            err=[sum(r[mode])-sum(r['actual150']) for r in windows]
            metrics[road][mode]=dict(MAE450=statistics.mean(abs(x) for x in err),bias450=statistics.mean(err),
                max_abs450=max(abs(x) for x in err),MAE150=statistics.mean(abs(p-y) for r in windows for p,y in zip(r[mode],r['actual150'])),errors450=err)
    future=read(A/'source_boundary318/audit.json')
    for road in oc.ROADS:
        assert results[-1]['roads'][road]['actual150']==future['comparison'][road]['hold']['corrected_admissions_150s']
        results[-1]['roads'][road]['city_actual150']=future['comparison'][road]['city']['corrected_admissions_150s']
    for module in (oc,ol):pin(module.__file__)
    pin(Path(__file__));pin(HERE/'candidate.py');pin(HERE/'tests.log')
    report=dict(status='complete_causal_source_rate_history_walk_forward328',metrics=metrics,windows=results,
        observations=past,source_pins=PINS,production_adopted=False,goal_complete=False,budget=plan['budget'],
        limitation=['One completed seed29 history; overlapping forecast windows are not independent samples.',
                    'History600s is a predeclared single candidate, not a fitted saturation rate.',
                    'No endogenous source receiving or stochastic paired realization prediction is added.',
                    'Backlog remains schedule integral minus admissions, not a count of actual stochastic uninserted vehicles.',
                    'No city-minus-hold gain claim follows from a better source prediction MAE.'])
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('METRICS',json.dumps(metrics));print('AT2400',json.dumps(results[-1]))

if __name__=='__main__':main()
