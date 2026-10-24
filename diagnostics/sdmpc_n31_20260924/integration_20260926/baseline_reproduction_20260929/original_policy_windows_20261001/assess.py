"""Summarize a completed frozen comparison; no forecast or native execution."""
import ast
import hashlib
import json
import statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=load(HERE/'summary.json');rows=s['rows']
assert load(HERE/'status.json')['stage']=='complete'
assert len(rows)==32 and s['rollouts']==33
assert all(not r['score']['invalid'] and r['conservation_max']<1e-7 for r in rows)
assert all(sha(Path(p))==h for p,h in s['source_pins'].items())
history=load(HERE/'history_audit.json')
assert max(z['max_mass_residual'] for z in history['rows'])<1e-7
assert load(HERE/'nc_history_parity.json')['max_cell_difference']==0
helper=HERE.parents[1]/'replay_congested_component.py'
before=ast.parse((HERE/'capture_source_executed.py.txt').read_text(encoding='utf-8-sig'))
after=ast.parse(helper.read_text(encoding='utf-8-sig'))
functions=lambda tree:{x.name:ast.dump(x,include_attributes=False) for x in tree.body if isinstance(x,ast.FunctionDef)}
a,b=functions(before),functions(after)
changed=[k for k in a if b.get(k)!=a[k]]
assert changed==['predict_baseline_policy_windows'],changed
assert set(b)-set(a)=={'baseline_policy_vsl_history'}
summary=[];contrasts=[]
for arm in ('none','bottleneck90','rm','both'):
    selected=[r for r in rows if r['mode']=='own_state150' and r['arm']==arm]
    summary.append(dict(arm=arm,
        speed_rmse_mean=statistics.mean(r['score']['speed']['rmse'] for r in selected),
        stock_rmse_mean=statistics.mean(r['score']['cell_n']['rmse'] for r in selected),
        flow_rmse_mean=statistics.mean(r['score']['flow_vph']['rmse'] for r in selected),
        ttt_mae=statistics.mean(abs(r['predicted']['ttt']-r['actual']['ttt']) for r in selected)))
    if arm=='none':continue
    for r in selected:
        n=next(z for z in rows if z['mode']==r['mode'] and z['cutoff']==r['cutoff'] and z['arm']=='none')
        av=r['actual']['ttt']-n['actual']['ttt'];pv=r['predicted']['ttt']-n['predicted']['ttt']
        contrasts.append(dict(arm=arm,cutoff=r['cutoff'],actual=av,predicted=pv,
            nonzero=abs(av)>1e-9,sign_matches=av*pv>0 if abs(av)>1e-9 else abs(pv)<1e-9))
common=[r for r in rows if r['mode']=='common870_450']
base=next(r for r in common if r['arm']=='none')
pairs=[dict(arm=r['arm'],actual=r['actual']['ttt']-base['actual']['ttt'],
            predicted=r['predicted']['ttt']-base['predicted']['ttt']) for r in common]
assessment=dict(
    frozen_model='expanded036',comparison_rollouts=32,nc_parity_rollouts=1,
    max_model_mass_residual=max(r['conservation_max'] for r in rows),
    own_state_scores=summary,own_state_contrasts=contrasts,common_initial_contrasts=pairs,
    own_state_nonzero_signs_matched=sum(z['nonzero'] and z['sign_matches'] for z in contrasts),
    own_state_nonzero_contrasts=sum(z['nonzero'] for z in contrasts),
    unchanged_old_functions=len(a)-len(changed),changed_functions=changed,
    latest_history_sinks={arm:next(z['past_unresolved_disappearance'] for z in history['rows'] if z['arm']==arm and z['cutoff']==7800.1) for arm in ('none','bottleneck90','rm','both')},
    prevention_gain_qualified=False,calibration=False,core_and_pinned_inputs_unchanged=True,
    new_native=0,live_poll=0,new_fzp_reads=0)
(HERE/'assessment.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2),encoding='utf-8')
table='\n'.join(f"|{z['arm']}|{z['speed_rmse_mean']:.2f}|{z['stock_rmse_mean']:.2f}|{z['ttt_mae']:.3f}|" for z in summary)
text=f"""# 원래 ALINEA·고정VSL90 네 정책: expanded036 동결 확인

완료: 28개 자체 초기 상태150초 + 공통870.1초450초 네 조건 =32회, 무제어 이력 처리 동등성1회. 새 VISSIM·FZP 재읽기·재보정·실행 중인 작업 조회는0회다. 코어와 설정, 목적함수는 변경하지 않았다.

## 결과

|정책|7시점 평균 속도RMSE[km/h]|셀 재고RMSE[veh]|150초 부분영역 TTT MAE[veh·h]|
|---|---:|---:|---:|
{table}

900.1/1800.1/2700.1/4500.1/5400.1/6300.1/7800.1초에서 시작했다. 동측31셀+4on+4off connector 범위로 도시 접근도로와 Ω 전체를 포함하지 않는다. TTT는 동일30초 표본 사다리꼴 적분이다.

자체 상태에서 무제어 대비 비용 차이는0이 아닌20건 모두 부호가 같았다. 예를 들어4500.1–4650.1초 RM−NC는 실측−15.108/예측−14.530veh·h, 결합−NC는−16.529/−16.247이다. **이미 정책에 따라 달라진 초기 재고·속도를 입력한 결과이므로 예방 효과의 사전 예측 통과가 아니다.** 속도RMSE16–17km/h와 합류량 오차도 남는다. 이 결과로 단순 총비용 맞춤을 완료라고 판정하지 않는다.

공통870.1초450초에서 VSL/결합−NC는 실측+0.833333/예측+1.312070veh·h, RM은 양쪽0이다. 이 시점에는 RM 제한의 실제 합류 차이가 없어 혼잡기RM 이득 검증을 대신하지 못한다. 실행된 명령을 조건으로 한 반응 시험이며 미래 ALINEA 명령을 예측한 결과가 아니다.

## 비교 전 수정한 진단 초기화

옛 component builder는 과거 VSL 노출을 넘기지 않아, 후기 상태의 기존 차량을 기본110으로 시작한다. 이번 비교에만 기존 pure cohort assimilation을 사용해 시점 이전30초 유량·재고와 기존 검증 명령표에서 과거90/110 노출을 추정했다. 기존 예측 훅에 첫 상태를 주입하고 종료 시 복원했다. **실제 SDMPC의 기존 과거이력 초기화가 빠졌다는 뜻은 아니다.**

무제어는 처리 전후 모든 셀 출력이 정확히 같다. 코호트 재고와 실측 초기 재고 일치, 모델 차량 보존, 초기 공통 상태·교통 입력 동일성 검사를 통과했다. 미래 실측 유량은 공급하지 않았다. 창 안 유량의 균일 분포와 셀 내 혼합 근사로, 개별 차량 DSD 통과 또는 셀 일부의 위치까지 재현한 추정치는 아니다.

원래 관측 캐시의7800.1초까지 미확인 소실은 NC4/VSL11/RM5/결합2대다. 과거 이력 추정의 별도 소실항으로 보존했으며 정상 종료나native 삭제로 바꾸지 않았다. 이 수치는 현 모델의 차량보존 잔차와 구분한다.

## 다음 보정 기준

기본 freeway 역학은 같은 고정 도시 신호의NC/RM/VSL/결합 자료를 우선한다. RM 단독만 맞추면 안 된다. 실제 합류→병목 방출·회복→램프·도시 대기 비용을 함께 검증한다. SDMPC 기록은 도시 신호/도착 분포가 함께 변한 결합 검증과 추가 실패 상태로 사용한다.

동일 혼잡 상태의 명령 분기 자료가 예방 이득·선택 순위의 주 검증이다. 자체 상태150초 정확도, 부분영역 이득, Ω 이득, 전체9000초 재현은 서로 다른 판정이다. 이번 결과는 보정 완료나 원래 네9000초 재현 완료가 아니다.

근거: protocol.json, capture.json, history_protocol.json, history_audit.json, nc_history_parity.json, summary.json, assessment.json, predictions/. 예측 계산 {s['rollout_sec']:.3f}초; summary wall {s['wall_sec']:.3f}초는 과거이력 준비 전 시간을 포함하지 않는다. 준비 포함 전체 경과시간은 별도 측정하지 않아 단축률을 주장하지 않는다.
"""
(HERE/'README.md').write_text(text,encoding='utf-8')
print(json.dumps(assessment,ensure_ascii=False))

