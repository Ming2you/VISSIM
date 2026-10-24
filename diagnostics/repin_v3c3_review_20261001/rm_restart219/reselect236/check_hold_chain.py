"""Read the completed219 error-hold chain without replaying traffic."""
import csv
import hashlib
import json
from pathlib import Path
import sys

D=Path(__file__).resolve().parent
ROOT=D.parents[3]
sys.path.insert(0,str(ROOT))
from evaluation.controllers.sdmpc import load_prices

F=Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
FIELDS=('N_P_star','N_UF_star','ramp_metering','vsl','green_times','offsets','inflow_outflow_allocation')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_bytes())


def rows(path):
    def normalize(value):
        try:return float(value)
        except ValueError:return value
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return [{k:normalize(v) for k,v in row.items() if k!='metadata'}
                for row in csv.DictReader(stream)]


def main():
    assert not (D/'hold_chain.json').exists()
    records=[]
    for sec in range(4500,9001,150):
        previous=F/f'action_{sec-150:06d}.json'
        path=F/f'action_{sec:06d}.json'
        error=F/f'action_{sec:06d}.error.txt'
        raw,old=read(path),read(previous)
        hold=raw['metadata']['hold_previous']
        assert raw['metadata']['controller_status']=='hold_previous_error'
        assert hold['json_sha256']==sha(previous)
        assert hold['csv_sha256']==sha(previous.with_suffix('.csv'))
        assert Path(hold['source']).resolve()==previous.resolve()
        assert hold['source_sim_sec']==sec-150
        assert all(raw[k]==old[k] for k in FIELDS)
        assert rows(path.with_suffix('.csv'))==rows(previous.with_suffix('.csv'))
        assert 'Current lane/full-network projection differs on physical link 10483' in error.read_text(encoding='utf-8-sig')
        prices,receipt=load_prices(path,None,{})
        assert list(prices)==[0.,0.] and not receipt['committed']
        records.append(dict(sim_sec=sec,source_sec=sec-150,physical_command_unchanged=True,
            error='initial_projection_link10483',price_loader_accepts_hold=True,
            price_receipt=receipt,action_sha256=sha(path)))
    result=dict(status='recorded_hold_chain_verified_read_only',records=records,
        operating_intervals=30,terminal_record_count=1,native_replays=0,forecasts=0,
        meaning='Repeated errors were the same10483 projection defect, not missing price receipts. '
                'A held command has no sdmpc_state; production load_prices starts at zero uncommitted prices. '
                'This does not prove a full future decision succeeds or validate new native control.')
    (D/'hold_chain.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(result['status'],len(records),'records')


if __name__=='__main__':main()
