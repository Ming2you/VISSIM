"""Build an unapplied fixed-freeway-query v2 patch using stdlib text/AST only.

The v1 producer and artifacts are immutable historical evidence. This file never
imports a model or writes production source. Tests may extract individual method
ASTs with explicit pure stubs; that is not actual physical-model validation.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'evaluation/controllers/link_predictor.py'
EXPECTED = '1053a4769f85c7c444281c0b53dc4eb941c57a30df7c20e4a6eb5dd336ac2c14'
SETUP_NAMES = ('ControlAction', 'segment_vsl', 'freeway_substep_local', 'net',
               'sim', 'ff', 'model', 'horizon', 'dt_h', 'vsl_max', 'smooth_w', 'n_seg', 'prev_vec')


def one(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Extraction anchor multiplicity: {old[:100]!r}')
    return text.replace(old, new, 1)


def build():
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('The reviewed canonical local predictor changed')
    original = raw.decode('utf-8').replace('\r\n', '\n')
    prefix, separator, body = original.partition('    # 후보 무관 초기 스냅샷(이 link 권역만).\n')
    if not separator or separator in body:
        raise ValueError('Initial state extraction anchor is not unique')
    imports_start = prefix.index('    from src.controllers import wu_faithful_follower as vendor\n',
                                 prefix.index('def solve_freeway_agent_local('))
    setup_end = prefix.index('\n    candidates = (', imports_start)
    setup = prefix[imports_start:setup_end]
    unpack = '    (' + ', '.join(SETUP_NAMES) + ') = setup\n'
    # Preserve all thirteen captured values and their original read order before
    # candidate generation. Captured cfg objects remain references, as before;
    # later loop reads of other self/cfg fields deliberately remain unchanged.
    prefix = (prefix[:imports_start] +
              '    setup = _freeway_query_setup(self, link, previous)\n' + unpack +
              prefix[setup_end:])
    delegation = '''    result = _evaluate_freeway_sequences(
        self, link, state, coupling, demand, previous, vsl_sequences,
        setup=setup,
    )
    return result['vsl'], result['cost'], result['candidate_count']


def _freeway_query_setup(self, link, previous):
    """Read the original pre-enumeration setup once, in its original order."""
'''
    delegation += setup + '\n    return (' + ', '.join(SETUP_NAMES) + ')\n\n\n'
    delegation += '''def evaluate_fixed_freeway_candidate(
    self, link, state, coupling, demand, candidate, reference, *,
    include_price_terms=False,
):
    """Score exactly one held VSL+meter action, or reject an invalid result.

    `reference` supplies smoothness references; `candidate` supplies applied
    controls. This retains the existing local frozen-boundary approximation,
    regularizers and price-dependent smoothness policy. Omitting additive VSL
    and cross prices does not silently alter that independent policy.

    No candidate search or direct standing-flow/selected-result commit occurs.
    This is not a joint-network feasibility or GNE certificate. The caller must
    isolate/restore all installed runtime hooks, including adapter lane-profile
    context and operational follower state, on both success and exception.
    """
    if type(include_price_terms) is not bool:
        raise ValueError('include_price_terms must be a boolean')
    if not getattr(self.cfg.network, 'local_landing_state', False):
        raise ValueError('Fixed freeway query requires canonical local landing')
    setup = _freeway_query_setup(self, link, reference)
'''
    delegation += unpack
    delegation += '''    vector = [float(segment_vsl(candidate, link, i, self.cfg)) for i in range(n_seg)]
    if not vector or any(not math.isfinite(v) or v <= 0 for v in vector):
        raise ValueError('Fixed freeway VSL must be finite and positive')
    expected = {f"{link}__seg{i}": value for i, value in enumerate(vector)}
    expected[link] = min(vector)
    result = _evaluate_freeway_sequences(
        self, link, state, coupling, demand, reference,
        [[list(vector) for _ in range(horizon)]], setup=setup,
        candidate_base=candidate, commit=False,
        include_price_terms=include_price_terms,
    )
    if (type(result['cost']) not in (int, float) or not math.isfinite(result['cost'])
            or type(result['candidate_count']) is not int or result['candidate_count'] != 1):
        raise ValueError('Fixed freeway query did not return exactly one finite score')
    if (not isinstance(result['vsl'], Mapping) or set(result['vsl']) != set(expected)
            or any(type(result['vsl'][key]) not in (int, float)
                   or not math.isfinite(result['vsl'][key])
                   or result['vsl'][key] != value for key, value in expected.items())):
        raise ValueError('Fixed freeway query returned a different expanded VSL action')
    return result


def _evaluate_freeway_sequences(
    self, link, state, coupling, demand, previous, vsl_sequences, *, setup,
    candidate_base=None, commit=True, include_price_terms=True,
):
'''
    delegation += unpack + '    applied_base = previous if candidate_base is None else candidate_base\n\n'
    body = separator + body
    for field in ('ramp_metering', 'vsl', 'green_times', 'offsets'):
        body = one(body, f'{field}=dict(previous.{field}),', f'{field}=dict(applied_base.{field}),')
    body = one(body, 'm_now = float(previous.ramp_metering.get(ramp, float(m_ref)))',
               'm_now = float(applied_base.ramp_metering.get(ramp, float(m_ref)))')
    body = one(body, '        if self.vsl_marginal_price:\n',
               '        if include_price_terms and self.vsl_marginal_price:\n')
    body = one(body, '        if self.vsl_meter_cross_price:\n',
               '        if include_price_terms and self.vsl_meter_cross_price:\n')
    commit_start = body.index('    # 선택 후보 VSL의 off-ramp 유출 캐시')
    commit_end = body.index('    vsl_dict: Dict[str, float]', commit_start)
    commit_block = body[commit_start:commit_end]
    diag_start = commit_block.index('    diagnostics = getattr(')
    flow_commit, diag_block = commit_block[:diag_start], commit_block[diag_start:]
    diag_block = one(diag_block,
                    "    diagnostics = getattr(self, '_last_local_landing_diagnostics', {})\n    diagnostics[link] = ",
                    '    query_diagnostics = ')
    diag_block = one(diag_block, '    self._last_local_landing_diagnostics = diagnostics\n', '')
    indented_flow = ''.join('    ' + line if line.strip() else line for line in flow_commit.splitlines(keepends=True))
    replacement = diag_block + '    if commit:\n' + indented_flow + '''        diagnostics = getattr(self, '_last_local_landing_diagnostics', {})
        diagnostics[link] = query_diagnostics
        self._last_local_landing_diagnostics = diagnostics
'''
    body = body[:commit_start] + replacement + body[commit_end:]
    body = one(body, '    return vsl_dict, best_obj, evals\n', '''    return {
        'vsl': vsl_dict, 'cost': best_obj, 'candidate_count': evals,
        'first_offramp_flow_veh_h': dict(best_offramp_flow),
        'landing_diagnostics': query_diagnostics,
        'includes_price_terms': include_price_terms,
        'standing_result_committed': commit,
    }
''')
    revised = prefix + delegation + body
    ast.parse(revised, filename=str(SOURCE))
    delta = ''.join(difflib.unified_diff(original.splitlines(keepends=True), revised.splitlines(keepends=True),
                    fromfile='a/evaluation/controllers/link_predictor.py', tofile='b/evaluation/controllers/link_predictor.py'))
    if SOURCE.read_bytes() != raw:
        raise RuntimeError('Canonical source changed while preparing patch')
    return original, revised, delta


def prepare():
    original, revised, delta = build()
    out = ROOT / 'diagnostics/fixed_freeway_query_preparation_v2'
    out.mkdir(exist_ok=False)
    (out / 'link_predictor.patch').write_text(delta, encoding='utf-8', newline='\n')
    preserved = [ROOT / 'diagnostics/prepare_fixed_freeway_query_patch.py',
                 ROOT / 'diagnostics/fixed_freeway_query_preparation_v1/link_predictor.patch',
                 ROOT / 'diagnostics/fixed_freeway_query_preparation_v1/manifest.json',
                 ROOT / 'diagnostics/fixed_freeway_query_preparation_v1/review.md']
    manifest = {
        'schema': 'fixed-freeway-query-preparation/v2', 'source_sha256': EXPECTED,
        'prepared_lf_source_sha256': hashlib.sha256(revised.encode()).hexdigest(),
        'patch_sha256': hashlib.sha256(delta.encode()).hexdigest(),
        'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'preserved_v1_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in preserved},
        'setup_capture_fields_in_order': list(SETUP_NAMES),
        'ast_parse_pass': True, 'installed': False, 'model_imported': False, 'model_executed': False,
        'behavioral_equivalence_verified_on_actual_model': False,
        'pending': ['Actual legacy model/worker candidate trace and commit equivalence',
                    'Runtime lane-profile and all operational state isolation on success/exception',
                    'Fixed-action query actual realized vectors and price/reference parity',
                    'Joint shared-node reconciliation and GNE residual are separate work'],
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    prepare()
