"""Prepare one bounded corrected benchmark, preserving the failed attempt."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = HERE/'runtime_pair2400'
NEW = HERE/'runtime_pair2400_numericfix'


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    prior = read(OLD/'plan.json')
    assert prior['status'] == 'failed_or_stopped_no_retry' and prior['launches_consumed'] == 1
    assert read(OLD/'cache_off.execution.json')['exit_code'] == 1
    assert not (OLD/'cache_on.execution.json').exists()
    changed = [str(p) for p, sha in prior['source_pins'].items() if digest(p) != sha]
    assert len(changed) == 1 and Path(changed[0]).name == 'route_choice_corridor.py', changed
    NEW.mkdir(exist_ok=False)
    for name in ('run_pair.ps1', 'compare.py', 'cache_off_config.json', 'cache_on_config.json'):
        shutil.copyfile(OLD/name, NEW/name)
    plan = deepcopy(prior)
    plan.pop('failure', None)
    plan.update(status='prepared_not_launched', launches_consumed=0,
        previous_failed_attempt=str(OLD), correction='Clipped receiving avoids inactive huge ratios; AD quotient derivatives avoid squared-denominator underflow. No coefficient, demand, horizon or objective change.',
        regression_checks={'passed': 46, 'failing_reproduction_before_fix': 9,
            'commands': ['test_tiny_receiving.py + test_canonical_helper.py + lateral_order/test_candidate.py: 31 passed',
                         'tests/test_known_wout_lane_receiving.py + runtime_pair2400/test_compare.py: 15 passed']},
        prior_AD_gate_scope='Reference scalar/AD validated before the numerical correction. Current candidate AD is checked by the corrected full selections; no new trajectory-fitting gate.')
    for mode, argv in plan['commands'].items():
        plan['commands'][mode] = [x.replace(str(OLD), str(NEW)) for x in argv]
    pins = {}
    for path in prior['source_pins']:
        target = Path(path.replace(str(OLD), str(NEW)))
        pins[str(target)] = digest(target)
    for name in ('sdmpc_dual.py', 'sdmpc_tangent_reverse.py', 'sdmpc_tangent_summary.py'):
        path = ROOT/'evaluation/controllers'/name
        pins[str(path)] = digest(path)
    for path in (NEW/'compare.py', HERE/'isolated10681/test_tiny_receiving.py'):
        pins[str(path)] = digest(path)
    plan['source_pins'] = pins
    plan['launcher'] = str(NEW/'run_pair.ps1')
    write(NEW/'plan.json', plan)
    stamp = datetime.now(timezone.utc).isoformat()
    note = dict(checked_utc=stamp, calibration_frozen=True, further_coefficient_search=False,
        failed_full_selection=str(OLD), numerical_fix_tests_passed=46,
        corrected_benchmark=str(NEW), status='prepared_not_launched', new_native_runs=0,
        criterion='Material cost directions and meaningful candidate ranking; do not fit the near-zero native net sign.')
    write(NEW/'preparation.json', note)
    for path, field, value in ((HERE/'plan.json', 'current_stage',
            'Macro calibration accepted and frozen. Corrected numerical underflow; 46 tests pass. Bounded complete SDMPC cacheOFF/ON comparison prepared, not yet launched.'),
            (HERE/'isolated10681/plan.json', 'status', 'practical_calibration_frozen_numericfix_pair_prepared')):
        doc = read(path)
        doc[field] = value
        doc['numericfix_followup'] = note
        write(path, doc)
    text = '''# 수치 오류 수정 후 계산시간 비교

큰 RM 반응 방향은 실용 기준으로 채택하고 계수 보정을 멈췄다. 실측 전체 Ω 차이 +0.042%의 작은 부호는 추가로 맞추지 않는다.

기존 cacheOFF 전체 선택은 494.50초 뒤 극소 재고 분모의 제곱 언더플로로 실패했다. cacheON은 실행되지 않았다. 실패 자료는 원래 runtime_pair2400에 보존했다.

현재 수정은 수용량 비율의 이미 포화된 분기 계산을 생략하고, 분모 제곱이 0으로 언더플로될 때만 동등한 나눗셈 순서를 쓴다. 정상 크기에서 기존 미분 산술을 유지하며 차량 삭제·계수 재보정은 없다. 세 미분 경로와 실제 connector→road 보존/수용 제약을 포함해 46시험 통과했다.

다음은 같은 저장 상태의 전체 SDMPC 선택을 cacheOFF/ON 각 한 번 비교하는 작업이다. 3블록 명령·목적값·제약이 같은 경우에만 계산시간 단축을 채택한다. 현재 돌고 있는 VISSIM 동결본은 변경하지 않는다. 새 native 런은 없다.
'''
    (NEW/'README.md').write_text(text, encoding='utf8')
    with (HERE/'isolated10681/README.md').open('a', encoding='utf8') as stream:
        stream.write('\n\n## 2026-10-09 실용 보정 종료와 계산시간 단계\n\n'+text.split('\n\n', 1)[1])
    print(json.dumps(dict(status=plan['status'], output=str(NEW), tests=46), ensure_ascii=False))


if __name__ == '__main__':
    main()
