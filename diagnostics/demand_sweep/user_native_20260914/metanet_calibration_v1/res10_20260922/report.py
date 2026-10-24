"""Summarize frozen offline fits without selecting or modifying parameters."""
import gzip
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

B=Path(__file__).resolve().parent;ROOT=B.parent.parents[3]
sys.path[:0]=[str(ROOT/'.review-deps'),str(B.parent),str(ROOT)]
from boundary_factory import ObservationData
from calibrate import long_path


def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=B/sys.argv[1]
    result=load(out/'validation.json');protocol=load(out/'protocol.json')
    groups=defaultdict(list)
    for row in result['scores']:groups[row['case'],row['mode'],row['road'],row['model']].append(row)
    summary=[]
    for (case,mode,road,model),rows in groups.items():
        item=dict(case=case,mode=mode,road=road,model=model,windows=len(rows),invalid=sum(r['invalid'] for r in rows))
        for metric in ('speed','density','flow_vph'):
            valid=[r[metric] for r in rows if metric in r]
            count=sum(r['count'] for r in valid)
            item[metric+'_rmse']=math.sqrt(sum(r['count']*r['rmse']**2 for r in valid)/count) if count else None
        item['mean_objective']=sum(r['objective'] for r in rows)/len(rows)
        item['continuity_max_veh']=max((r.get('diagnostics',{}).get('continuity_residual_max_veh',0) for r in rows))
        item['speed_projections']=sum(r.get('diagnostics',{}).get('speed_projection_count',0) for r in rows)
        item['requested_source_veh']=sum(r.get('diagnostics',{}).get('requested_source_veh',0) for r in rows)
        item['accepted_source_veh']=sum(r.get('diagnostics',{}).get('accepted_source_veh',0) for r in rows)
        item['unaccepted_source_fraction']=(1-item['accepted_source_veh']/item['requested_source_veh']) if item['requested_source_veh'] else 0
        item['missed_sustained_congestion_cells']=sum(e['status']=='miss' for r in rows for e in r.get('onset_events',[]))
        item['false_sustained_congestion_cells']=sum(e['status']=='false_alarm' for r in rows for e in r.get('onset_events',[]))
        item['freeway_component_ttt_error_veh_h']=sum(r.get('freeway_ttt_predicted_veh_h',0)-r.get('freeway_ttt_observed_veh_h',0) for r in rows)
        summary.append(item)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# SimRes10 METANET 재보정','',
        '100% 무제어 자료로 보정하고 계수를 고정한 뒤 다른 수요 조건에서 450초 예측을 비교했다. 모든 자료는 seed23이다. 다른 seed 검증이나 RM·VSL 이득 검증이 아니다.',
        '', '31개 세그먼트/방향, native FZP5초, 실제 기록 위상0.1초 유지. 내부 적분1초. 미래 본선 상태를 중간에 다시 넣지 않는다.',
        '', '## 과거150초 경계 관측만 사용하는 예측', '',
        '|수요 조건|방향|속도 RMSE 전→후 [km/h]|밀도 RMSE 전→후 [veh/km/lane]|유량 RMSE 전→후 [veh/h]|실패 전/후|',
        '|---|---|---:|---:|---:|---:|']
    lookup={(r['case'],r['mode'],r['road'],r['model']):r for r in summary}
    for case in [protocol['training']]+protocol['validation']:
        for road in ('FW_E','FW_W'):
            pair=[lookup[case['id'],'history_forecast',road,m] for m in ('baseline','calibrated')]
            cells=[' → '.join('없음' if r[k] is None else f'{r[k]:.2f}' for r in pair) for k in ('speed_rmse','density_rmse','flow_vph_rmse')]
            lines.append(f'|{case["id"]}|{road}|'+ '|'.join(cells)+f'|{pair[0]["invalid"]}/{pair[1]["invalid"]}|')
    lines += ['', '## 해석 범위', '',
        '- conditioned_diagnostic은 미래 실제 경계 유량을 사용하는 물리식 진단이다. 실시간 예측 성능과 분리한다.',
        '- baseline은 기존 정본 계수, calibrated는 훈련 초기 자유류 속도 갱신과 방향별6개 계수 보정이다. 형상·수요·제어 정책은 같다.',
        '- off-ramp 수용량은 외부 방출률 대리값, forecast에서는 과거값이다. 도시 신호·출구 배수의 완전한 폐루프 예측이 아니다.',
        '- TTT 수치는 고속도로 구성요소만 포함한다. Ω 전체 TTT나 제어 개선율로 해석하지 않는다.',
        '- 5초 궤적 사이 경계 통과는 구간 단위 추정이며, 단일 연결이 확인되는 connector 생략만 인정한다. 삭제와 미확인 이동은 정상 방출에 넣지 않는다.',
        '- 생산 기본값은 변경하지 않았다. 개별 혼잡 위치·발생/해소 오류와 실패를 summary.json, validation.json에 함께 남겼다.']
    if (out/'ASSESSMENT.md').exists(): lines += ['',(out/'ASSESSMENT.md').read_text(encoding='utf-8')]
    (out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plt.rcParams['font.family']='Malgun Gothic'
    plt.rcParams['axes.unicode_minus']=False
    for name in ('p90','fw080_urban100'):
        case=next(c for c in protocol['validation'] if c['id']==name)
        data=ObservationData(ROOT/case['observations'])
        times=sorted(t for t in data.cells if t>0)
        for road in ('FW_E','FW_W'):
            geometry=sorted((r for r in data.geometry['cells'] if r['road']==road),key=lambda r:r['cell'])
            arrays=[np.full((len(geometry),len(times)),np.nan) for _ in range(3)]
            time_idx={round(t,6):i for i,t in enumerate(times)}
            for t in times:
                for r in data.cells[t]:
                    if r['road']==road and r['n_veh']>=5 and r['v_kmh'] is not None:arrays[0][r['cell'],time_idx[t]]=r['v_kmh']
            for ai,model in enumerate(('baseline','calibrated'),1):
                for cutoff in case['cutoffs_s']:
                    path=out/f'{name}_history_forecast_{road}_{cutoff}_{model}.json.gz'
                    if not path.exists():continue
                    with gzip.open(long_path(path),'rt',encoding='utf-8') as f:pred=json.load(f)
                    for r in pred['cells']:
                        ti=time_idx[round(r['time_s'],6)]
                        if r['road']==road and np.isfinite(arrays[0][r['cell'],ti]):arrays[ai][r['cell'],ti]=r['v_kmh']
            fig,axes=plt.subplots(3,1,figsize=(13,10),sharex=True,sharey=True,layout='constrained')
            xs=np.array([times[0]-15]+[t+15 for t in times])/60
            ys=np.array([geometry[0]['start_m']]+[r['end_m'] for r in geometry])/1000
            cmap=plt.get_cmap('RdYlBu').copy();cmap.set_bad('#dddddd')
            for ax,a,title in zip(axes,arrays,('VISSIM 실측','기존 계수: 450초 예측','재보정 계수: 450초 예측')):
                im=ax.pcolormesh(xs,ys,a,cmap=cmap,vmin=0,vmax=120,shading='flat')
                ax.set_title(title);ax.set_ylabel('상류 → 하류 거리 [km]')
            axes[-1].set_xlabel('simulation 시간 [분]')
            fig.colorbar(im,ax=axes,label='평균속도 [km/h]',shrink=.8)
            fig.suptitle(f'{name} · {road} · seed23 · 과거 관측만 사용\n15분 간격 초기화 후 각450초 예측; 회색은 예측하지 않은 시간 또는 실측 차량5대 미만')
            fig.savefig(out/f'{name}_{road}_forecast.png',dpi=140)
            plt.close(fig)
    print(json.dumps({'report':str(out/'README.md'),'summary':summary}))


def literature_report():
    """Compare frozen families; evaluation only, never feeds parameter choice."""
    from canonical_harness import load_base_model, sha256
    from boundary_factory import build_window
    from scoring import score_rollout
    o=B/'boundary_literature_v1'
    all_rows=[];baseline=None;parameters={};proof={}
    for family in ('boundary','hadi','wang'):
        out=o/(family+'_fit')
        complete=load(out/'completion.json')
        if not complete['complete']: raise ValueError('Incomplete family')
        frozen=load(out/'freeze.json')
        if sha256(out/'parameters.json')!=frozen['parameters_sha256']:raise ValueError('Changed frozen fit')
        rows=load(out/'validation.json')['scores']
        old=[r for r in rows if r['model']=='baseline']
        if baseline is None:
            baseline=old;all_rows.extend([{**r,'model':'previous_fit'} for r in old])
        elif baseline!=old: raise ValueError('Shared reference predictions changed between families')
        all_rows.extend([{**r,'model':family} for r in rows if r['model']=='calibrated'])
        parameters[family]=load(out/'parameters.json')['parameters']
        proof[family]=complete
    fresh=load(o/'fresh_holdout_protocol.json')
    fresh_path=o/'fresh_holdout_validation.json'
    if fresh_path.exists():
        checked=load(fresh_path)
        if checked['parameters']!=parameters:raise ValueError('Fresh holdout parameters changed')
        all_rows.extend(checked['scores'])
    else:
        data=ObservationData(ROOT/fresh['observations'])
        manifest=load(data.folder/'manifest.json')
        if manifest['seed']!=fresh['seed'] or manifest['requested_terminal_sec']!=9000:
            raise ValueError('Fresh holdout source differs')
        models={family:load_base_model(data.geometry,o/(family+'_config.json')) for family in parameters}
        models['previous_fit']=load_base_model(data.geometry,B/'fit_config.json')
        old_parameters=load(B/'fit_v1/parameters.json')['parameters']
        fresh_rows=[]
        for mode in ('conditioned_diagnostic','history_forecast'):
            for t in fresh['cutoffs_s']:
                w=build_window(data,t,mode,model_step_sec=1)
                for family,model in models.items():
                    for road in model.roads:
                        row=dict(case=fresh['case'],mode=mode,road=road,model=family,cutoff_s=t)
                        try:
                            p=old_parameters if family=='previous_fit' else parameters[family]
                            pred=model.rollout(w['initial_cells'],w['boundary_steps'],p,w['initial_origin_queue'],roads=(road,))
                            row.update(score_rollout(data,t,pred,road,include_source_boundary=True))
                            with gzip.open(long_path(o/f'fresh_{family}_{mode}_{road}_{t}.json.gz'),'wt',encoding='utf-8',compresslevel=1) as f:
                                json.dump(pred,f,allow_nan=False)
                        except (ArithmeticError,ValueError,OverflowError) as exc:
                            row.update(invalid=True,objective=1e12,failure=repr(exc))
                        fresh_rows.append(row)
                print(json.dumps({'fresh_holdout':mode,'cutoff':t}),flush=True)
        fresh_path.write_text(json.dumps(dict(parameters=parameters,manifest_sha256=sha256(data.folder/'manifest.json'),scores=fresh_rows),indent=2,allow_nan=False),encoding='utf-8')
        all_rows.extend(fresh_rows)
    groups=defaultdict(list)
    for row in all_rows:groups[row['case'],row['mode'],row['road'],row['model']].append(row)
    summary=[]
    for (case,mode,road,model),rows in groups.items():
        item=dict(case=case,mode=mode,road=road,model=model,windows=len(rows),invalid=sum(r['invalid'] for r in rows))
        for metric in ('speed','density','flow_vph','source_flow_vph'):
            values=[r[metric] for r in rows if metric in r];count=sum(r['count'] for r in values)
            item[metric+'_rmse']=math.sqrt(sum(r['count']*r['rmse']**2 for r in values)/count) if count else None
        item['mean_objective']=sum(r['objective'] for r in rows)/len(rows)
        item['requested_source_veh']=sum(r.get('diagnostics',{}).get('requested_source_veh',0) for r in rows)
        item['accepted_source_veh']=sum(r.get('diagnostics',{}).get('accepted_source_veh',0) for r in rows)
        item['unaccepted_source_fraction']=1-item['accepted_source_veh']/item['requested_source_veh'] if item['requested_source_veh'] else 0.
        item['continuity_max_veh']=max(r.get('diagnostics',{}).get('continuity_residual_max_veh',0.) for r in rows)
        item['speed_projection_count']=sum(r.get('diagnostics',{}).get('speed_projection_count',0) for r in rows)
        item['speed_projection_events_per_cell_step']=item['speed_projection_count']/max(1,sum(not r['invalid'] for r in rows)*450*31)
        for status in ('miss','false_alarm'):
            item[status]=sum(e['status']==status for r in rows for e in r.get('onset_events',[]))
        item['literature_counts']={k:sum(r.get('diagnostics',{}).get('literature_counts',{}).get(k,0.) for r in rows)
            for k in ('literature_receiving_limited_cells','literature_command_cells','literature_drop_changes_receiving_cells','literature_actual_limited_boundaries')}
        summary.append(item)
    # Isolate source and terminal changes, holding the previous fit fixed.
    ablation=[];train=load(o/'boundary_protocol.json')['training']
    data=ObservationData(ROOT/train['observations'])
    old_parameters=load(B/'fit_v1/parameters.json')['parameters']
    for family in ('source_only','terminal_only','boundary'):
        model=load_base_model(data.geometry,o/(family+'_config.json'))
        for t in train['cutoffs_s']:
            w=build_window(data,t,'conditioned_diagnostic',model_step_sec=1)
            for road in model.roads:
                pred=model.rollout(w['initial_cells'],w['boundary_steps'],old_parameters,w['initial_origin_queue'],roads=(road,))
                ablation.append(dict(family=family,road=road,cutoff_s=t,**{k:v for k,v in score_rollout(data,t,pred,road,include_source_boundary=True).items() if k not in ('road','cutoff_s')}))
    for name,value in [('summary.json',summary),('boundary_ablation.json',ablation),('family_parameters.json',parameters),('verification.json',proof)]:
        (o/name).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    # Event timing is reported separately from the fitting loss.
    def recovered(sequence):
        low_seen=False;clear=[]
        for r in sequence:
            if r['n_veh']>=5 and r['v_kmh'] is not None and r['v_kmh']<30:
                low_seen=True;clear=[]
            elif low_seen and r['v_kmh'] is not None and r['v_kmh']>=60:
                clear.append(r['time_s'])
                if clear[-1]-clear[0]>=120-1e-8:return clear[0]
            else:clear=[]
        return None
    events=[];cache={};boundary_samples=defaultdict(list)
    protocol=load(o/'boundary_protocol.json')
    observations={c['id']:ROOT/c['observations'] for c in [protocol['training']]+protocol['validation']}
    observations[fresh['case']]=ROOT/fresh['observations']
    for row in all_rows:
        if row['invalid']:continue
        case,mode,road,family,t=(row[k] for k in ('case','mode','road','model','cutoff_s'))
        if case not in cache:cache[case]=ObservationData(observations[case])
        d=cache[case]
        if case==fresh['case']:path=o/f'fresh_{family}_{mode}_{road}_{t}.json.gz'
        else:
            folder=o/(('boundary' if family=='previous_fit' else family)+'_fit')
            path=folder/f'{case}_{mode}_{road}_{t}_{"baseline" if family=="previous_fit" else "calibrated"}.json.gz'
        with gzip.open(long_path(path),'rt',encoding='utf-8') as f:pred=json.load(f)
        times=[round(t+j,6) for j in range(0,451,30)]
        road_cells=[int(c['cell']) for c in d.geometry['cells'] if c['road']==road]
        pred_flows={(round(r['window_end_s'],6),r['cell']):r for r in pred['flows'] if r['road']==road}
        for name,truth_key,pred_key in (
                ('source','source_admissions','source_admissions'),
                ('ramp_merge','ramp_merges','ramp_merges'),
                ('off_exit','off_departures','off_departures'),
                ('terminal_exit','terminal_exits_inferred','terminal_exits')):
            for s in times[1:]:
                truth=sum(float(d.flows[s,road,c][truth_key]) for c in road_cells)
                estimate=sum(float(pred_flows[s,c][pred_key]) for c in road_cells)
                boundary_samples[case,mode,road,family,name].append((truth,estimate))
        predicted={(round(r['time_s'],6),r['cell']):r for r in pred['cells'] if r['road']==road}
        observed={(s,r['cell']):r for s in times for r in d.cells[s] if r['road']==road}
        for cell in sorted(r['cell'] for r in d.cells[t] if r['road']==road):
            a=recovered([observed[s,cell] for s in times])
            b=recovered([observed[t,cell]]+[predicted[s,cell] for s in times[1:]])
            events.append(dict(case=case,mode=mode,road=road,model=family,cutoff_s=t,cell=cell,
                observed_recovery_s=a,predicted_recovery_s=b,
                status='both' if a is not None and b is not None else 'miss' if a is not None else 'false_alarm' if b is not None else 'neither',
                timing_error_s=b-a if a is not None and b is not None else None))
    (o/'recovery_events.json').write_text(json.dumps({'definition':'After an in-window observed/predicted low-speed state N>=5 and v<30, first >=60km/h span lasting120s at30s states. Window events, not independent network episodes. Not used in fitting.','events':events},indent=2),encoding='utf-8')
    boundary_flow=[]
    for (case,mode,road,family,name),values in boundary_samples.items():
        errors=[(estimate-truth)*120 for truth,estimate in values]
        boundary_flow.append(dict(case=case,mode=mode,road=road,model=family,boundary=name,count=len(values),
            rmse_vph=math.sqrt(sum(e*e for e in errors)/len(errors)),bias_vph=sum(errors)/len(errors),
            observed_veh=sum(a for a,b in values),predicted_veh=sum(b for a,b in values)))
    (o/'boundary_flow_validation.json').write_text(json.dumps({'definition':'30s aggregate component boundary flows; terminal events are native FZP-inferred normal physical-end departures, not all disappearance or Omega TTD. Counts cover only evaluated windows. Conditioned mode prescribes observed future external supply; forecast uses history.','rows':boundary_flow},indent=2),encoding='utf-8')
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family']='Malgun Gothic'
    plt.rcParams['axes.unicode_minus']=False
    d=cache[fresh['case']];t=2700.1;times=[round(t+j,6) for j in range(30,451,30)]
    geo=sorted((c for c in d.geometry['cells'] if c['road']=='FW_E'),key=lambda c:c['cell'])
    y=np.array([geo[0]['start_m']]+[c['end_m'] for c in geo])/1000
    observed={(s,r['cell']):r for s in times for r in d.cells[s] if r['road']=='FW_E'}
    panels=[('VISSIM 실측',observed)]
    for family,title in [('boundary','경계 정합 + 기존 METANET'),('hadi','Hadi 재보정'),('wang','Wang 재보정')]:
        path=o/f'fresh_{family}_history_forecast_FW_E_{t}.json.gz'
        if long_path(path).exists():
            with gzip.open(long_path(path),'rt',encoding='utf-8') as f:pred=json.load(f)
            panels.append((title,{(round(r['time_s'],6),r['cell']):r for r in pred['cells']}))
        else:panels.append((title+' — 예측 실패, 로그 참조',{}))
    fig,axes=plt.subplots(4,1,figsize=(13,13),sharex=True,sharey=True,layout='constrained')
    for ax,(title,values) in zip(axes,panels):
        z=np.array([[values[s,c['cell']]['v_kmh'] if (s,c['cell']) in values and observed[s,c['cell']]['n_veh']>=5 else np.nan for s in times] for c in geo])
        im=ax.pcolormesh(np.array([t]+times),y,z,cmap='RdYlBu',vmin=0,vmax=120,shading='flat')
        ax.set_title(title);ax.set_ylabel('동측 본선 거리 [km]')
    axes[-1].set_xlabel('시뮬레이션 시간 [초]')
    fig.suptitle('고속도로 80% · 도시 90% — 고정 계수의 450초 예측\n2700.1초 관측으로 초기화, 이후 본선 상태 재입력 없음')
    fig.colorbar(im,ax=axes,label='차량 평균속도 [km/h]',shrink=.8)
    fig.supxlabel('각 칸은 끝 시각의 30초 간격 상태값이며 시간평균이 아님 · 실측 N<5 공통 제외 · 실제 셀 길이 반영',fontsize=10)
    fig.savefig(o/'fresh_holdout_FW_E_2700.png',dpi=150);plt.close(fig)
    lines=['# 경계 정합 및 Hadi / Wang 재보정','',
        '현재 resolution10, native FZP5초, 방향별31셀·내부1초·450초 예측. 훈련100%, 검증90/80/70 및 FW80urban100; 모두seed23. 새 native 런·제어 이득 검증·운영 기본값 승격은 없음.',
        '', '## 과거 관측만 이용한 검증','',
        '|조건|방향|모델|속도 RMSE km/h|밀도 RMSE veh/km/lane|유량 RMSE veh/h|실패|미수용 유입 %|',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for row in summary:
        if row['mode']!='history_forecast':continue
        values=['없음' if row[k] is None else f'{row[k]:.2f}' for k in ('speed_rmse','density_rmse','flow_vph_rmse')]
        lines.append(f"|{row['case']}|{row['road']}|{row['model']}|"+'|'.join(values)+f"|{row['invalid']}/{row['windows']}|{100*row['unaccepted_source_fraction']:.2f}|")
    lines+=['','## 적용 범위와 제한','',
        '[동측 450초 공간 예측 비교](fresh_holdout_FW_E_2700.png). 속도·유량 오차와 발생/회복 사건을 함께 확인한다.',
        '',
        '- source는 관측/예측된 실제 진입 경계 공급이다. 같은 요청에 기존6937 상한을 다시 적용하지 않는다. 첫 셀의 물리 저장·수용 제한과 미수용량의 외부 재고 장부는 유지한다.',
        '- terminal은 실제 망 끝이다. 별도 하류 링크가 없는지 XML로 확인했고 진입 상한을 재사용하지 않는다. 본선 sending과 기존 마지막 셀 ghost density 조건은 유지한다.',
        '- Hadi: R=min(Qprime,w*(jam-rho)), Qprime=Q*(1-theta) when rho>critical. Wang: 혼잡 wprime=Qprime/(jam-critical), critical=Q/nominal120. 물리 jam 저장밀도는 기존값이다.',
        '- 두 논문의 명령속도 relaxation을 기존 모델 VSL 영역 전체에 고정 적용했다. 무제어120과 제한 명령 모두 같은 식을 사용한다. 논문 밖 기존 merge/lane-drop 감속은 이 두 family에서 겹쳐 넣지 않았다.',
        '- Wang 인쇄식의 ramp-minus-off 항을 mainline 전이량에 또 더하지 않는다. 이미 별도 차량 보존 항으로 집계하고 공유 수용 예산에서 합류량을 뺀다. 이 변수 변환을 포함하므로 논문 코드 전체의 문자 그대로 복제라는 주장은 하지 않는다.',
        '- Q,w,critical,theta는 방향별 유효 보정값이다. 양의 theta가 선택되어도 실제 capacity drop의 독립 식별이나 VSL 이득 증명이 아니다. 실행 중 유량·재고·목적함수는 보상으로 조작하지 않았다.',
        '- summary의 speed_projection_count는 최저속도 도달과 수용 유량에 맞춘 속도 상한 적용을 합친 기존 진단값이다. 이를 모두 수치 불안정이나 독립적인 속도식 오차로 해석하지 않는다.',
        '- 재보정 손실은 기존 속도/20·밀도/10·유량/1000의 제곱합에 실제 진입유량/1000 오차의 제곱을 추가했다. 세 family와 비교 기준에 동일하며 controller 목적함수는 변경하지 않았다.',
        '- 원문: [Hadiuzzaman et al.](https://doi.org/10.1061/(ASCE)TE.1943-5436.0000507), [Wang–Niu](https://doi.org/10.1177/1687814019831913). 원 논문의 MPC 전체·액추에이터 배치·목적 가중치를 복제한 실험은 아니다.',
        '- on/off-ramp 경계는 외생 관측/과거 예측이다. 전체 도시 신호·대기와 폐루프 actuator 효과는 이번 검증 범위 밖이다. 미수용 source는 보존하지만 본선 구성요소 TTT를 전체Omega 개선율로 사용하지 않는다.',
        '- 80–90 런은 세 모델의 계수를 모두 고정한 뒤 추가 검증했다. 훈련·후보 선택에 사용하지 않았다. 다른seed 및 현 망 실제 제어 쌍 검증은 별도 필요하다.',
        '- boundary_ablation.json은 직전 계수를 고정한 source-only/terminal-only/both의 54개 예측이다. source와 terminal 변화의 효과를 재보정 효과와 구분한다.']
    lines+=['','진입·합류·진출·최종 출구별30초 유량 오차와 평가창별 합계는 [boundary_flow_validation.json](boundary_flow_validation.json)에 따로 기록했다.']
    if (o/'ASSESSMENT.md').exists():lines+=['','[결과 판단 및 다음 단계](ASSESSMENT.md)']
    (o/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (o/'completion.json').write_text(json.dumps({'complete':True,'families':proof,'comparison_rows':len(all_rows),'boundary_ablation_rollouts':len(ablation),'production_adopted':False,'control_gain_validated':False},indent=2),encoding='utf-8')
    print(json.dumps({'report':str(o/'README.md'),'family_invalid':{k:v['invalid_windows'] for k,v in proof.items()}}))


def rolling150_report():
    """Stitch causal150s forecasts; use completed cached NC observations only."""
    from canonical_harness import load_base_model, sha256
    from boundary_factory import build_window
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    o=B/'boundary_literature_v1'
    out=ROOT/'diagnostics/prediction_heatmaps_20260922/fw080_urban090_150s'
    data=ObservationData(B/'fw080_urban090_observations')
    manifest=load(data.folder/'manifest.json')
    assert manifest['seed']==23 and manifest['requested_terminal_sec']==9000
    params={};models={};pins={};proof={'default450_exact':0,'prefix150_exact':0,'prefix120_exact':0}
    sources=load(out/'before_sources.json')
    # Preserve the exact fitted sources; only the explicit horizon interface changed.
    for family in ('boundary','hadi','wang'):
        f=o/(family+'_fit');frozen=load(f/'freeze.json')
        assert load(f/'completion.json')['complete'] and sha256(f/'parameters.json')==frozen['parameters_sha256']
        oldpins=load(f/('validation_resume_pins.json' if family=='boundary' else 'input_pins.json'))
        for name,digest in {**oldpins['code'],**oldpins['configs']}.items():
            if name in sources:
                assert sources[name]==digest
                assert sha256(out/(Path(name).name+'.before150.txt'))==digest
            else:assert sha256(ROOT/name)==digest,name
        params[family]=load(f/'parameters.json')['parameters']
        pins[family]=dict(parameters_sha256=frozen['parameters_sha256'],config_sha256=sha256(o/(family+'_config.json')))
        models[family]=load_base_model(data.geometry,o/(family+'_config.json'))
    before=load(out/'before_default_window.json')
    w=build_window(data,2700.1,'history_forecast',model_step_sec=1)
    assert w==before
    # The short forecast must be exactly the causal prefix of the saved450s one.
    for family,model in models.items():
        for road in model.roads:
            with gzip.open(long_path(o/f'fresh_{family}_history_forecast_{road}_2700.1.json.gz'),'rt',encoding='utf-8') as stream:old=json.load(stream)
            pred=model.rollout(w['initial_cells'],w['boundary_steps'],params[family],w['initial_origin_queue'],roads=(road,))
            assert pred==old,(family,road,'default450 changed')
            proof['default450_exact']+=1
            for horizon in (150,120):
                short=build_window(data,2700.1,'history_forecast',model_step_sec=1,horizon_sec=horizon)
                assert short['boundary_steps']==w['boundary_steps'][:horizon]
                result=model.rollout(short['initial_cells'],short['boundary_steps'],params[family],short['initial_origin_queue'],roads=(road,),horizon_sec=horizon)
                for key,timekey in (('cells','time_s'),('flows','window_end_s')):
                    assert result[key]==[r for r in old[key] if r[timekey]<=2700.1+horizon+1e-8]
                proof[f'prefix{horizon}_exact']+=1
    queue=load(Path('D:/VISSIM_runs/20260922_fw080_urban090_controls/queue.json'))
    assert all(sha256(Path(p))==h for p,h in queue['code_sha256'].items())
    pins['sources']={str(B.parent/name):sha256(B.parent/name) for name in ('canonical_harness.py','boundary_factory.py')}
    pins['observations']={p.name:sha256(p) for p in data.folder.iterdir() if p.suffix in ('.json','.csv')}
    proof['active_native_queue_pins_unchanged']=True
    (out/'preflight.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    last=manifest['last_complete_30s_window_s'];cutoffs=[round(s+data.phase_sec,6) for s in range(150,8851,150)]
    predictions=[];failures=[];checks=[]
    for cutoff in cutoffs:
        horizon=min(150,int(round(last-cutoff)))
        w=build_window(data,cutoff,'history_forecast',model_step_sec=1,horizon_sec=horizon)
        assert w['meta']['features_latest_realized_time_s']==cutoff
        for family,model in models.items():
            for road in model.roads:
                try:
                    pred=model.rollout(w['initial_cells'],w['boundary_steps'],params[family],w['initial_origin_queue'],roads=(road,),horizon_sec=horizon)
                    diag=pred['diagnostics']['roads'][0]
                    assert diag['density_projection_count']==0 and diag['jam_density_exceedance_count']==0
                    assert diag['continuity_residual_max_veh']<1e-8
                    assert pred['diagnostics']['future_state_resets']==0
                    predictions.extend(dict(model=family,cutoff_s=cutoff,horizon_s=horizon,**r) for r in pred['cells'])
                    checks.append(dict(model=family,cutoff_s=cutoff,horizon_s=horizon,**diag))
                except (ValueError,ArithmeticError,OverflowError,AssertionError) as exc:
                    failures.append(dict(model=family,road=road,cutoff_s=cutoff,error=repr(exc)))
        if int(cutoff)%900==0:print(json.dumps({'rolling150_cutoff':cutoff,'failures':len(failures)}),flush=True)
    with gzip.open(out/'predictions.json.gz','wt',encoding='utf-8') as stream:json.dump(predictions,stream,allow_nan=False)
    (out/'diagnostics.json').write_text(json.dumps(dict(checks=checks,failures=failures),indent=2),encoding='utf-8')
    times=sorted(t for t in data.cells if 0<t<=last)
    tindex={round(t,6):i for i,t in enumerate(times)}
    labels={'boundary':'경계 정합 + METANET','hadi':'Hadi 재보정','wang':'Wang 재보정'}
    summary=[]
    plt.rcParams.update({'font.family':'Malgun Gothic','axes.unicode_minus':False,'font.size':10})
    for road,korean in (('FW_E','동측'),('FW_W','서측')):
        geo=sorted((c for c in data.geometry['cells'] if c['road']==road),key=lambda c:c['cell'])
        observed=np.full((len(geo),len(times)),np.nan)
        for t in times:
            for r in data.cells[t]:
                if r['road']==road and r['n_veh']>=5 and r['v_kmh'] is not None:observed[r['cell'],tindex[t]]=r['v_kmh']
        panels=[('VISSIM 실측',observed)]
        for family in models:
            z=np.full_like(observed,np.nan)
            for r in predictions:
                if r['road']==road and r['model']==family:z[r['cell'],tindex[round(r['time_s'],6)]]=r['v_kmh']
            z[~np.isfinite(observed)]=np.nan
            mask=np.isfinite(z)&np.isfinite(observed);errors=z[mask]-observed[mask]
            metric=dict(model=family,road=road,count=int(mask.sum()),speed_rmse=float(np.sqrt(np.mean(errors**2))),speed_mae=float(np.mean(abs(errors))),speed_bias=float(np.mean(errors)),failed_windows=sum(f['model']==family and f['road']==road for f in failures))
            summary.append(metric)
            panels.append((f"{labels[family]} · 속도 RMSE {metric['speed_rmse']:.2f} km/h",z))
        fig,axes=plt.subplots(4,1,figsize=(16,12),sharex=True,sharey=True,layout='constrained')
        cmap=plt.get_cmap('RdYlBu').copy();cmap.set_bad('#e8e8e8')
        x=np.array([data.phase_sec]+times);y=np.array([geo[0]['start_m']]+[c['end_m'] for c in geo])/1000
        for ax,(title,z) in zip(axes,panels):
            ax.set_facecolor('#e8e8e8');im=ax.pcolormesh(x,y,z,cmap=cmap,vmin=0,vmax=120,shading='flat',rasterized=True)
            ax.set(title=title,xlim=(0,9000),ylim=(0,y[-1]),ylabel='상류 → 하류 [km]')
            ax.set_xticks(range(0,9001,900));ax.grid(axis='x',alpha=.2,color='white')
            if road=='FW_E':
                for km in (5.042,6.827):ax.axhline(km,color='#6f226f',ls=':',lw=.8,alpha=.7)
        axes[-1].set_xlabel('시뮬레이션 시간 [초]')
        fig.colorbar(im,ax=axes,label='속도 [km/h]',shrink=.83,pad=.01)
        fig.suptitle(f'고속도로 80% · 도시 90% — {korean} 본선 150초 예측 비교\n무제어 · seed23 · 150초마다 실측 초기화, 다음 150초만 예측 · 계수 재보정 없음',fontsize=16)
        fig.supxlabel('30초 간격의 끝 시각 상태값 · 실제 31개 셀 길이 · 실측 N<5 공통 제외\n회색: 첫 150초 이력 확보 / 기록 끝 이후 / 저표본 또는 실패 · 마지막 창은 120초(8850.1–8970.1초)',fontsize=10)
        fig.savefig(out/f'{road}_rolling150.png',dpi=150,facecolor='white');plt.close(fig)
    assert all(sha256(Path(p))==h for p,h in queue['code_sha256'].items())
    for family,p in pins.items():
        if family in models:assert sha256(o/(family+'_fit')/'parameters.json')==p['parameters_sha256']
    result=dict(complete=not failures,scenario='FW80 urban90 NC9000 seed23',initializations=cutoffs,rollouts=len(checks),failures=failures,
        forecast_horizon_sec=150,final_partial_horizon_sec=120,prediction_sample_sec=30,integration_step_sec=1,
        first_forecast_cutoff=150.1,last_observed_sample=last,mode='history_forecast',within_window_observation_resets=0,
        meaning='Rolling150s forecasts stitched; not a single open-loop9000s prediction or temporal-average heatmap.',
        maximum_continuity_residual_veh=max(c['continuity_residual_max_veh'] for c in checks),summary=summary,pins=pins,preflight=proof)
    (out/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    lines=['# 80–90 정본: 세 plant의150초 예측 히트맵','',
        '150.1초부터150초마다 관측으로 초기화하고 다음150초를 예측했다. 한 번 초기화한9000초 예측이 아니다. 계수 재보정·새 VISSIM 실행·진행 중 제어 런 변경은 없다.',
        '입력은 완료된 무제어9000초 런의 추출 자료다. 초기 상태와 직전150초 경계 관측, 저장된 수요 시간표만 사용한다. 예측 구간의 실제 미래 유량·본선 상태를 입력하지 않는다. on/off-ramp 경계는 과거 이력 대리이며 완전한 도시부 연계 예측은 아니다.',
        '첫150초는 예측용 이력 확보로 남겼다. native5초 기록의 .1초 위상을 유지하며 마지막 완전30초 관측은8970.1초다. 마지막 초기값8850.1초에서는120초만 예측했다.9000초까지 실측을 외삽하지 않는다.',
        '그림의 칸은30초 간격 끝 시각의 평균차량속도 상태값이며,30초 시간평균 또는150초 평균이 아니다. 실제31셀 길이로 표시한다. 실측N<5 마스크를 세 예측에도 동일하게 적용한다. 내부 적분은 짧은 셀의 보존검사를 통과한1초다.',
        '', '[동측](FW_E_rolling150.png) · [서측](FW_W_rolling150.png)','',
        '|방향|모델|속도 RMSE km/h|MAE km/h|편향 km/h|실패 창|','|---|---|---:|---:|---:|---:|']
    for r in summary:lines.append(f"|{r['road']}|{r['model']}|{r['speed_rmse']:.2f}|{r['speed_mae']:.2f}|{r['speed_bias']:.2f}|{r['failed_windows']}|")
    lines+=['','기존450초 예측6개 전체 JSON 일치,150초·120초 예측은 각각6개 기존 예측의 정확한 앞부분과 일치한다. 당시 source는 *.before150.txt에 보존했다. 새 horizon 인자 기본값은450초이며 모델 계수와 물리식은 바꾸지 않았다. 이전 calibration input pins의 두 파일은 이 보존본으로 재현하고 현재 실행 코드는 summary.json의 pins를 사용한다.',
        f"진행 중 native 큐의 모든 코드 pin은 전후 동일. 완료 예측{len(checks)}개, 실패{len(failures)}개. 대량 FZP 재스캔 없이 기존 CSV만 사용했다."]
    (out/'README.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'complete':result['complete'],'report':str(out/'README.md'),'summary':summary}),flush=True)


if __name__=='__main__':
    if '--rolling150' in sys.argv:rolling150_report()
    elif '--literature' in sys.argv:literature_report()
    else:main()
