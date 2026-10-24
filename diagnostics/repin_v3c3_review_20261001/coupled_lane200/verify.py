"""Read-only result checks for the bounded full-network connection experiment."""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    protocol=read(HERE/'enabled_protocol.json')
    original=read(HERE/'disabled_protocol.json')
    assert protocol['source_sha256']==original['source_sha256']
    for name,value in protocol['source_sha256'].items():
        assert digest(ROOT/name)==value,name
    assert read(HERE/'disabled_parity.json')['status']=='PASS'
    on,off=read(HERE/'enabled_binding.json'),read(HERE/'disabled_binding.json')
    assert on['unchanged_cell_parameters_sha256']==off['unchanged_cell_parameters_sha256']
    assert on['initial_partition_verified'] and on['max_initial_route_residual']==0
    stats=read(HERE/'enabled_coupling_stats.json')
    assert stats['commits']==900 and stats['ramp_supply_queries']==3600,stats
    assert max(stats['max_route_residual'],stats['max_split19_residual'])<1e-7
    output=Path(protocol['output']);counts={}
    for arm in ('release','release_vsl90'):
        rows=json.loads(gzip.decompress((output/(arm+'.terms.gz')).read_bytes()))
        assert len(rows)==4500
        assert {(r['time_sec'],r['cell']) for r in rows}=={(t,c) for t in range(2700,3150) for c in range(16,26)}
        regional=[r for r in rows if r.get('kind')=='regional_lane_update']
        assert len(regional)==450*7
        for row in regional:
            assert row['cell'] in range(19,26)
            assert 'after_speed_equation' not in row
            assert len(row['lane_speeds_final'])==3
            assert all(math.isfinite(v) and v>=0 for v in row['lane_speeds_final'])
        counts[arm]={'scalar_cell_rows':len(rows)-len(regional),'regional_cell_rows':len(regional)}
    # Keep the historical95 assessor behavior unchanged while adding200 output.
    assessor=HERE.parent/'s67_full_observation/assess76.py'
    archived=HERE.parent/'replication_s73_95/assess76.executed95.py.txt'
    def main_ast(p):
        return ast.dump(next(n for n in ast.parse(p.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='main'))
    assert main_ast(assessor)==main_ast(archived)
    stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert digest(stop)=='91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    assessment=read(HERE/'assessment.json')
    receipt=dict(status='CONNECTION_VERIFIED',gain_gate=assessment['gate'],
        computed450=6,scored450=4,failed_export450=2,initialization_failures=2,
        forecasts_seconds_valid=sum(read(Path(p['output'])/'summary.json')['results'][arm]['wall_sec']
            for p in (protocol,original) for arm in ('release_actual','release_vsl90_actual')),
        optimizer_iterations=0,fits=0,new_native=0,FZP_reads=0,
        production_files_unchanged=len(protocol['source_sha256']),
        historical_assessor_main_unchanged=True,old_STOP_preserved=True,
        coupling_stats=stats,speed_witness_counts=counts,goal='ACTIVE_NOT_QUALIFIED',
        production_adopted=False,AD_verified=False,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in (
            HERE/'hooks.py',HERE.parent/'heldout73_199/capture_runtime.py',assessor,Path(__file__))})
    (HERE/'completion.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
