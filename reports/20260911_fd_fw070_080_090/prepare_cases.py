"""Prepare the two user-requested highway demand variants using the existing NC path."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'diagnostics/demand_sweep/baseline_prepared/demand.csv'
OLD = ROOT / 'diagnostics/demand_sweep/fw070_urban050/prepared/demand.csv'

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)

def main():
    base, old = read(BASE), read(OLD)
    key=lambda r:(int(r['input_no']),int(r['start_sec']))
    reference={key(r):float(r['volume_vph']) for r in old}
    assert len(base)==len(reference)==204
    assert {int(r['start_sec']) for r in base}=={0,900,1800,2700,3600,4500}
    cases=[]
    for pct in (80,90):
        case=f'fw{pct:03d}_urban050'
        directory=ROOT/'diagnostics/demand_sweep'/case
        directory.mkdir(exist_ok=False)
        overrides, desired=[],[]
        for r in base:
            no,start=key(r)
            factor=pct/100 if no in (1098,1099) else .5
            before=float(r['volume_vph']);after=before*factor
            if no not in (1098,1099):
                assert abs(after-reference[no,start])<1e-9
            else:
                assert abs(reference[no,start]-before*.7)<1e-9
            overrides.append(dict(input_no=no,start_sec=start,volume_vph=after))
            desired.append(dict(input_no=no,start_sec=start,role='freeway_input' if no in (1098,1099) else 'urban_input',
                                factor=factor,before_vph=before,after_vph=after,fw070_reference_vph=reference[no,start]))
        write(directory/'input_override.csv',overrides)
        write(directory/'desired_inputs.csv',desired)
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'diagnostics/fast_nc_prepare.py'),
                 '--demand-overrides',str(directory/'input_override.csv'),'--output',str(directory/'prepared')]
        subprocess.run(command,cwd=ROOT,check=True)
        assert (directory/'prepared/controls.csv').read_bytes()==(OLD.parent/'controls.csv').read_bytes()
        assert (directory/'prepared/route_checks.csv').read_bytes()==(OLD.parent/'route_checks.csv').read_bytes()
        preparation=json.loads((directory/'prepared/prepared.json').read_text())
        oldprep=json.loads((OLD.parent/'prepared.json').read_text())
        assert preparation['network']==oldprep['network']
        receipt=dict(FW_input_factor=pct/100,urban_input_factor=.5,rows=204,highway_ids=[1098,1099],
                     unchanged_urban_interval_rows=192,route_weights='unchanged baseline',network_geometry_signals='unchanged baseline',
                     source='baseline_prepared/demand.csv final profiled volumes',seed=13,terminal_sec=5400,
                     preparation_command=command,controls_exact_to_fw070=True,
                     source_sha256=hashlib.sha256(BASE.read_bytes()).hexdigest())
        (directory/'case.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        for start in (0,900,1800,2700,3600,4500):
            rows=[r for r in desired if r['start_sec']==start]
            cases.append(dict(case=case,start_sec=start,end_sec=start+900,
                              freeway_vph=sum(r['after_vph'] for r in rows if r['role']=='freeway_input'),
                              urban_vph=sum(r['after_vph'] for r in rows if r['role']=='urban_input'),
                              urban_unchanged=True))
    write(OUT/'desired_demand_comparison.csv',cases)
    print(json.dumps(cases,indent=2))

if __name__=='__main__':
    main()
