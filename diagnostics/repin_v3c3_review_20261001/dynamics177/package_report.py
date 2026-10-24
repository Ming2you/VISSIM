"""Package the reviewed numeric evidence without recomputing or fitting."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
read=lambda name:json.loads((H/name).read_text(encoding='utf-8-sig'))
r=read('results.json');v=read('verification.json');ledger=read('five_second_ledger.json')
items=[]
def card(id,title,files,period,columns,rows,definition,caveats,method):
    return dict(id=id,title=title,queries=[dict(id=id+'-query',source=dict(label='검증된 VISSIM seed67 기존 캐시',
       files=[dict(label=f) for f in files],metricDefinitions=[dict(label='정의',definition=definition)],caveats=caveats),
       reportingPeriod=period,columns=columns,rows=rows,methods=[dict(language='calculation',code=method)])])
rows=[dict(condition=x['arm'],onsets=x['onset'],recoveries=x['recovery'],entries=x['slow_entry'],leaves=x['slow_leave'])
      for x in ledger['rows'] if x['cell']==20 and x['threshold']=='<5']
items.append(card('stock-transitions','RM·VSL와 저속 대열 생성·해소',['five_second_ledger.json','verification.json'],
    '2700.1–3120.1초,5초 간격',['condition','onsets','recoveries','entries','leaves'],rows,
    '셀20·1차로에서 속도5km/h 문턱을 통과한 사건과 저속 차량의 구간 진입·이탈.',
    ['고유 차량 수가 아닌 반복 사건 수. 5초 사이 사건은 관측하지 못함.','같은 초기 상태의 RM 유지·완화 × VSL110·90이며 무제어 비교가 아님.','진입·이탈에는 종방향 이동과 차로 변경이 포함됨.'],
    'delta_slow_stock = onsets - recoveries + slow_entries - slow_leaves; 2688 independent balances passed.'))
rows=[dict(target=x['target'],model=x['model'],MAE=x['mae'],n=x['n']) for x in r['scores'] if x['fold']=='forward']
items.append(card('one-step-screen','후반 미학습 구간의30초 조건부 예측',['results.json','predictions.json','protocol.json'],
    '학습 입력2700.1–2880.1초 / 검증 입력2940.1–3090.1초',['target','model','MAE','n'],rows,
    'MAE: 다음30초 진출량 또는 저속 재고의 평균 절대오차[대]. 모든 저속 재고 식은 현재 재고에 예측 증감을 더함.',
    ['동일 seed의56개 구간. 독립 seed 검증이 아님.','현재 관측 상태를 넣은 작은 회귀 진단이며 자율 plant/TTT/제어이득 검증이 아님.','현재 저속 재고 유지의 후반 MAE2.500대.','한30초 구간의 시간 간격을 두고 검증; 총60고정적합, 가중치 탐색 없음.'],
    'MAE = mean(abs(predicted - actual)); current/past features only; no policy/seed/time features.'))
(H/'sources.json').write_text(json.dumps(dict(schemaVersion=1,items=items),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(H/'completion.json').write_text(json.dumps(dict(completed=True,review='177',adopted=False,overall_goal='ACTIVE_NOT_QUALIFIED',
    verification=v,new_native_runs=0,raw_FZP_reads=0,plant_rollouts=0,production_edits=0,push=False,
    report='README.md',decision='Prefer conservative local lane-group queue formation/release and shared receiving; queue-only flow correction not supported.'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('report and source receipt prepared')
