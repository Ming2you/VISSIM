"""Prepare three identical calibrated plants with explicit VSL treatments."""
from pathlib import Path
import copy,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
read=lambda p:json.loads(p.read_bytes())
def main():
    base=read(HERE.parent/'flow279/config_10686_free.json')
    bundle=HERE/'calibration.json'
    for arm in ('window','optimized','off'):
        cfg=copy.deepcopy(base)
        cfg['name']='native348_FW5_U10_'+arm
        cfg['description']='Fixed reviewed aggregate urban calibration; same FW80/U90 seed29 Omega701, 8100s. In-sample native experiment; large urban gain-direction error remains unqualified.'
        cfg['urban']['calibrated_aggregate']=dict(path=bundle.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(bundle.read_bytes()).hexdigest())
        if arm=='optimized':cfg['adapter'].pop('sdmpc_fixed_vsl')
        if arm=='off':cfg['adapter']['sdmpc_fixed_vsl']=dict(start_sec=0,base_kmh=110,zone_kmh={})
        (HERE/(arm+'_config.json')).write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        print(arm,cfg['adapter'].get('sdmpc_fixed_vsl','optimized'),cfg['freeway']['multirate_exchange_sec'],cfg['urban']['multirate_exchange_sec'])
if __name__=='__main__':main()
