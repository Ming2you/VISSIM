"""Conservative static dependency graph for later diagnostic-artifact cleanup.

Imports are dependencies; string path mentions also include output producers.
Nothing is deleted and absence of a static edge does not prove dynamic non-use.
"""
import ast
from collections import defaultdict
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    diagnostic_files = {path.stem: path for path in (ROOT/'diagnostics').glob('*.py')}
    candidates = {path for path in (ROOT/'diagnostics').glob('*.patch')}
    candidates |= {path for path in diagnostic_files.values() if
                   re.search(r'(?:proposal|candidate|proposed|^prepare_|^build_.*patch|^build_urban_flow_accounting)', path.name)}
    incoming = defaultdict(list)
    sources = list((ROOT/'diagnostics').glob('*.py')) + list((ROOT/'evaluation/controllers').glob('*.py')) + list((ROOT/'scripts').glob('*.py'))
    for source in sources:
        if source.name == Path(__file__).name:
            continue
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        def scope(node):
            while node in parents:
                node = parents[node]
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    return node.name
            return '<module>'
        for node in ast.walk(tree):
            targets = []
            kind = 'python_import'
            if isinstance(node, ast.Import):
                targets = [alias.name.rsplit('.', 1)[-1] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'diagnostics':
                    targets = [alias.name for alias in node.names]
                elif node.module:
                    targets = [node.module.rsplit('.', 1)[-1]]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                kind = 'string_path_reference_or_output'
                for target in candidates:
                    if target.name in node.value and len(node.value) < 1200:
                        incoming[target].append({'source': source.relative_to(ROOT).as_posix(), 'line': node.lineno,
                                                 'scope': scope(node), 'kind': kind})
            for name in targets:
                target = diagnostic_files.get(name)
                if target in candidates:
                    incoming[target].append({'source': source.relative_to(ROOT).as_posix(), 'line': node.lineno,
                                             'scope': scope(node), 'kind': kind})
    rows = []
    for path in sorted(candidates):
        edges = sorted({(r['source'], r['line'], r['scope'], r['kind']) for r in incoming[path]})
        refs = [dict(zip(('source', 'line', 'scope', 'kind'), edge)) for edge in edges]
        imports = [r for r in refs if r['kind'] == 'python_import']
        test_imports = [r for r in imports if Path(r['source']).name.startswith('test_')]
        production = [r for r in refs if r['source'].startswith(('evaluation/controllers/', 'scripts/'))]
        state = ('active_test_import_migrate_first' if test_imports else
                 'production_or_script_reference_review_first' if production else
                 'historical_diagnostic_dependency_group' if imports else
                 'patch_evidence_or_unimported_candidate')
        rows.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                     'classification': state, 'incoming': refs})
    output = {'scope': 'Current diagnostic patch/candidate/proposal/patch-builder artifacts; no deletion performed.',
              'limits': 'Static AST imports plus path-string references. A path-string edge can be a producer, not a reader. CLI/manual historical use and dynamically assembled paths require review before deleting.',
              'candidate_count': len(rows), 'files': rows}
    (ROOT/'diagnostics/obsolete_diagnostic_artifacts.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'candidate_count': len(rows), 'direct_test_dependencies': [row for row in rows if row['classification']=='active_test_import_migrate_first'],
                      'production_or_script_references': [row for row in rows if row['classification']=='production_or_script_reference_review_first']}, indent=2))


if __name__ == '__main__':
    main()
