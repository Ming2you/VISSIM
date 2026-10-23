"""Retarget the previously tested analysis only; no simulation/forecast/FZP read."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

old = HERE/'analyze_multizone.py'
assert sha(old) == '3c4f9dd051185893ac191e372e7ea7c73d55595061dc1f980ca6610122c48996'
target = HERE/'analyze_multizone_repaired_20261016.py'
horizon = HERE/'summarize_multizone_repaired_20261016.py'
assert not target.exists() and not horizon.exists()
text = old.read_text(encoding='utf-8')
for a, b in [
    ("'native_vsl_multizone2250/protocol.json'", "'native_vsl_multizone2250_repaired_20261016/protocol.json'"),
    ('20261015_vsl_multizone2250_s29', '20261016_vsl_multizone2250_repaired_s29'),
    ("OUT = HERE / 'native_analysis'", "OUT = HERE / 'native_analysis_repaired_20261016'"),
    ("'native_preparation.json'", "'native_preparation_repaired_20261016.json'")
]:
    assert text.count(a) == 1, a
    text = text.replace(a, b)
ast.parse(text)
target.write_text(text, encoding='utf-8')
old_h = HERE/'summarize_multizone_horizons.py'
assert sha(old_h) == '6bcd024672a404b57611b86b74e821b16d5e46d3dae33a76329eb9a698e17b0c'
text = old_h.read_text(encoding='utf-8')
for a, b in [('import analyze_multizone as task','import analyze_multizone_repaired_20261016 as task'),("'analysis_preparation.json'", "'analysis_preparation_repaired_20261016.json'")]:
    assert text.count(a) == 1, a
    text = text.replace(a, b)
ast.parse(text)
horizon.write_text(text, encoding='utf-8')
replacement = read(HERE/'replacement_preparation_20261016.json')
protocol = read(replacement['protocol'])
save(HERE/'native_preparation_repaired_20261016.json', dict(protocol=replacement['protocol'],protocol_sha256=replacement['protocol_sha256'],physical_command_check=protocol['physical_command_check'],replacement_authorization=replacement['authorization'],forecasts_reused=True))
preparation = read(HERE/'analysis_preparation.json')
for p, digest in preparation['source_pins'].items():
    assert sha(p) == digest, p
preparation['source_pins'].update({str(target):sha(target), str(horizon):sha(horizon)})
preparation['status'] = 'retargeted_analysis_not_started'
preparation['prior_tests_reused'] = 5
preparation['changes'] = 'Protocol/run/output/preparation paths only; qualification, prefix, execution and cached baseline gates unchanged.'
save(HERE/'analysis_preparation_repaired_20261016.json', preparation)
plan = read(HERE/'plan.json')
stage = plan['next_stage']
stage['postprocess'] = dict(program='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe', script=str(target), output=str(HERE/'native_analysis_repaired_20261016'), source_pins=preparation['source_pins'], closure_receipt_required=str(HERE/'native_analysis_repaired_20261016/runtime_closure.json'), status='requires_normal2700_and_all_owner_closure', baseline_cache_reused=True)
stage['cached_horizon_postprocess'] = dict(script=str(horizon), sha256=sha(horizon), prerequisite='Qualified native analysis and exact runtime closure', new_forecasts=0, new_fzp_scans=0, status='not_started')
plan['updated_utc'] = datetime.now(timezone.utc).isoformat()
save(HERE/'plan.json', plan)
summary = read(HERE/'summary.json')
summary['authorized_replacement_20261016'] = dict(preparation=str(HERE/'replacement_preparation_20261016.json'), runtime=replacement['runtime'], results=replacement['results'], additional_budget=1, retries=0, status='waiting_canonical_freeze', prior_failure_preserved=True, no_new_forecasts=True)
save(HERE/'summary.json', summary)
with (HERE/'README.md').open('a',encoding='utf-8') as f:
    f.write('\n## 2026-10-16 승인된 수정본 추가1회\n\n사용자가 "수정본으로 1회 추가 실행"을 명시적으로 승인했다. 이전2250초 실패와 동결본을 보존하고, 새 runtime/result/command packet에서 추가1회·재시도0으로 진행한다. 정본 사전검사는 통과했고, 동결PID45764와 대기wrapper PID19488이 각1회 시작됐다. 최신 소유·진행 기록은 D:/VISSIM_runtime/20261016_vsl_multizone2250_repaired 아래 영수증과 pair_state.json을 따른다.\n\n이미 검증된639개 수정 명령을 복사했고 도시/RM/다른VSL 값은 이전 준비와 같다. 초기 설치 검사의 메타데이터 문자열 일치 가정은 램프 부가태그 때문에 쓰기/실행 전에 멈췄으며, 검증된 기준선의 전체 메타데이터와 행별 비교하도록 바로잡았다. native 추가실행을 소비한 실패가 아니다. 완료된 예측·writer·테스트를 재실행하지 않았다. 분석 경로만 새 실행으로 바꿨으며 SIM_DONE2700/runner exit0/모든 소유와wrapper 종료 전 분석하지 않는다. 앱 목표 도구가 마지막으로 반환한 상태는BLOCKED·미완료이며, 새 승인을 받아 실제 작업은 재개했다.\n')
print('Replacement analysis paths staged; no FZP, forecast, optimization, or native call.')
