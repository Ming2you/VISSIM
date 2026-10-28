# Markdown tables (Korean labels) from s22_profile_all.py output: per-decision stage seconds, this PC vs codex PC.
# usage: s26_tables.py prof.json > tables.md
import json, sys

rows = json.load(open(sys.argv[1], encoding='utf-8'))
by = {(r['label'], r['T']): r for r in rows if 'error' not in r}
ORDER = ['recorded', 'base_rep2', 'base', 'env_hsw', 'spd_hsw', 'spd_base', 'env_hsw_idle', 'spd_hsw_idle', 'py31214_base', 'py31214_hsw']
NAME = {'recorded': 'codex PC 기록', 'base_rep2': '이 PC base(반복)', 'base': '이 PC base', 'env_hsw': '이 PC env_hsw',
        'spd_hsw': '이 PC env_hsw+S1', 'spd_base': '이 PC base+S1', 'r900c_it01': '이 PC base(첫 완주, 차가운 numba·열기 추적)',
        'env_hsw_idle': '이 PC env_hsw (빈 PC)', 'spd_hsw_idle': '이 PC env_hsw+S1 (빈 PC)', 'py31214_base': '이 PC base, Py3.12.14', 'py31214_hsw': '이 PC env_hsw, Py3.12.14'}


def cap(r, i, k):
    c = r['caps']
    return c[i][k] if i < len(c) else None


METRICS = [
    ('결정 전체 벽시계 (decision_budget wall_sec)', lambda r: r['budget_wall_sec']),
    ('주 프로세스 CPU (cpu_sec)', lambda r: r['main_cpu_sec']),
    ('적재·모형 준비 (load_and_model_prepare)', lambda r: r['load_and_model_prepare_sec']),
    ('마무리 검증·출력 (final_action_validation_and_output)', lambda r: r['final_output_sec']),
    ('joint 밖 나머지 (전체 − joint 끝 − 적재 − 마무리)', lambda r: round(r['outside_joint_sec'] - r['load_and_model_prepare_sec'] - r['final_output_sec'], 3)),
    ('PFO 따뜻한 시작 (sdmpc_pfo_done.seconds)', lambda r: r['pfo_sec']),
    ('cap 1 전체', lambda r: cap(r, 0, 'wall_sec')),
    ('  cap 1 VSL secant 묶음 (derivatives_start→done)', lambda r: cap(r, 0, 'secant_sec')),
    ('  cap 1 걸음 예측 묶음', lambda r: cap(r, 0, 'step_batch_sec')),
    ('  cap 1 tangent (겹쳐 돎, 합)', lambda r: cap(r, 0, 'tangent_sec')),
    ('cap 2 전체 (미분 재사용)', lambda r: cap(r, 1, 'wall_sec')),
    ('  cap 2 진행 기록 없는 구간 (QP·중앙 복원, 주 프로세스)', lambda r: cap(r, 1, 'unlogged_sec')),
    ('cap 3 전체', lambda r: cap(r, 2, 'wall_sec')),
    ('미터 이웃 검사 전체', lambda r: (r['neighbor'] or {}).get('wall_sec')),
    ('plant 스칼라 롤아웃 중앙값 (1회)', lambda r: r['scalar_rollout_median_sec']),
    ('plant 스칼라 롤아웃 합 (워커 합)', lambda r: r['scalar_rollout_sum_sec']),
    ('plant tangent 롤아웃 중앙값 (1회)', lambda r: r['tangent_rollout_median_sec']),
    ('tangent 미분 1회 tangent_sec 평균', lambda r: round(sum(t['tangent_sec'] for t in r['tangent_derivatives']) / len(r['tangent_derivatives']), 3) if r['tangent_derivatives'] else None),
    ('진행 기록 두 줄 사이 최대 간격 (워치독 idle 상한 근거)', lambda r: r.get('max_progress_gap_sec')),
    ('tangent 미분 1회 spawn 포함 벽시계 평균', lambda r: round(sum(t['wall_incl_spawn_sec'] for t in r['tangent_derivatives']) / len(r['tangent_derivatives']), 3) if r['tangent_derivatives'] else None),
]
COUNTS = [
    ('cap 후보 수', lambda r: len(r['caps'])),
    ('PFO 예측 수', lambda r: r['pfo_predictions']),
    ('VSL secant 평가 수 (cap 합)', lambda r: sum(c['secant_evaluations'] for c in r['caps'])),
    ('이웃 검사 예측 수', lambda r: (r['neighbor'] or {}).get('predictions')),
    ('plant 스칼라 롤아웃 수', lambda r: r['scalar_rollouts']),
    ('plant tangent 롤아웃 수', lambda r: r['tangent_rollouts']),
    ('응답 요청 / 캐시 적중', lambda r: '%s / %s' % (r['requests'], r['cache_hits'])),
    ('기울기 행 (green·offset·meter: AD, vsl: secant)', lambda r: '/'.join(str(v) for v in r['gradient_rows_by_kind_method'].values())),
    ('이 PC CPU 전체 사용률 평균 % (typeperf 5 s)', lambda r: (r.get('cpu_load') or {}).get('cpu_total_pct_mean')),
]


def fmt(v):
    if v is None:
        return '—'
    if isinstance(v, float):
        return '%.1f' % v
    return str(v)


for T in (900, 2700, 4950):
    labels = [l for l in ORDER if (l, T) in by]
    rec = by[('recorded', T)]
    print('\n#### T = %d s\n' % T)
    print('| 항목 | ' + ' | '.join(NAME[l] for l in labels) + ' |')
    print('|---|' + '---|' * len(labels))
    for name, f in METRICS:
        cells = []
        base = f(rec)
        for l in labels:
            v = f(by[(l, T)])
            if l == 'recorded' or v is None or not base:
                cells.append(fmt(v))
            else:
                cells.append('%s (×%.2f)' % (fmt(v), v / base))
        print('| ' + name + ' | ' + ' | '.join(cells) + ' |')
    for name, f in COUNTS:
        print('| ' + name + ' | ' + ' | '.join(fmt(f(by[(l, T)])) for l in labels) + ' |')
