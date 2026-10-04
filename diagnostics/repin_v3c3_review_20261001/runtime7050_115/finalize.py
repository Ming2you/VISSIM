"""Record partial-run closure without changing original failed execution artifacts."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
stop_sha = hashlib.sha256(stop.read_bytes()).hexdigest()
assert stop_sha == '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
validation = json.loads((HERE/'native_check_v3/verification.json').read_text())
assert validation['status'] == 'PASS'
assert 'OK (skipped=1)' in (HERE/'tests_v4.log').read_text(encoding='utf-8-sig')

history = HERE.parent/'queuezero_restart96'
plan_path = history/'postprocess_plan.json'
before = HERE/'postprocess_plan.before.json'
if not before.exists():
    before.write_bytes(plan_path.read_bytes())
plan = json.loads(plan_path.read_text(encoding='utf-8-sig'))
plan.update(stage='failed7050_closed_no_restart',
            normal9000_postprocess_performed=False,
            partial_user_authorized_comparison='../runtime7050_115/partial7050/summary.json',
            terminal_failure='7050 .err buffered mainline removals caused strict balance failure',
            next_run_authorized_by_this_report=False)
plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
readme = history/'README.md'
notice = ('> **2026-10-03 종료 상태 정정:** 이 런은 7050초 관측 오류로 종료됐다. '
          '0–7050초 무제어 대비 Ω TTT −1.29%, 동측 본선 +7.84%, 전체 삽입 차량 체류 +1.34%. '
          '삭제 증가로 개선 판정은 보류한다. 오류 수정·짧은 검증 완료, 9000초 재시작 없음. '
          '[115 보고서](../runtime7050_115/README.md) 참조. 아래는 시작 당시 기록이다.\n\n')
content=readme.read_text(encoding='utf-8-sig')
if not content.startswith(notice):
    readme.write_text(notice+content, encoding='utf-8')

header=('CURRENT REVIEW115 COMPLETE (2026-10-03): PROGRESS ACTIVE/NOT_QUALIFIED. '
        '96DATA9000 FAILED7050, all owned processes closed; DO NOT RESTART9000. '
        'User requested matched0..7050 TTT: Omega6082.64->6003.96(-1.29pct), East1911.75->2061.61(+7.84pct), '
        'allinserted8141.40->8250.53(+1.34pct); deletions224->333/inside70->135, no gain claim. '
        'R/runtime7050_115 README/partial7050/balance authoritative. ClosedERR proves6 missedremovals6900..7050, '
        '1mainline eachE/W explains terminal inferred214/140 vsmeasured213/139 exactly. '
        'Existing runner+capture CLI now current LogNOTE barrier+2x8KB pads, failclosed freshness; '
        'no physics/objective/guard relaxation.92tests91pass1skip; real151s loggingpair392veh/6028FZP allcolumnsEXACT, '
        'live1/150markerscomplete/noextraSimStep. Failedprobes preserved. Failedoriginal/frozen/STOP untouched, '
        'no9000/fullanalysis/push. Prior114 passive-stop model remainsDO_NOT_CONNECT.\n\n')
for name in ('AGENTS.md','CLAUDE.md'):
    path=ROOT/name
    content=path.read_text(encoding='utf-8-sig')
    if not content.startswith(header):
        path.write_text(header+content,encoding='utf-8')

changed = ['evaluation/controllers/obs150_capture.py','scripts/obs150_capture.py',
           'scripts/run_real_world_stackelberg_controller.vbs']
result=dict(status='complete_partial_comparison_and_runtime_fix',gain_qualified=False,
            native9000_restarted=False,goal='ACTIVE/NOT_QUALIFIED',stop_sha256=stop_sha,
            regression=dict(total=92,passed=91,skipped=1),native_parity=validation,
            source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in changed})
(HERE/'completion.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Report and terminal status recorded; no9000 restart, no gain qualification.')
