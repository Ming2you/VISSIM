from pathlib import Path
import sys
import json
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from evaluation.controllers.physical_movement_routes import load_evidence
_, routes, _ = load_evidence('diagnostics/physical_movement_routes_ver2.json')
need = set(sys.argv[1:])
for key, row in routes.items():
    if need.intersection(row['path']):
        print(json.dumps({'id': key, 'path': row['path'], 'weight': row['weight'], 'decision_link': row['decision']['link']}))
