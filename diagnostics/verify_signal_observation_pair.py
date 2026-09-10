"""Read-only configuration/launcher comparison; never generate or launch a run."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LEAF = ('urban','capacity','head_observation','enabled')


def differences(a,b,path=()):
    if isinstance(a,dict) and isinstance(b,dict):
        result=[]
        for key in sorted(a.keys()|b.keys()):
            if key not in a or key not in b:
                result.append({'path':list(path+(key,)),'presence_changed':True})
            else:result.extend(differences(a[key],b[key],path+(key,)))
        return result
    if type(a) is not type(b) or a != b:
        return [{'path':list(path),'on':a,'off':b}]
    return []


def check(on, overlay, off=None):
    expected={'urban':{'capacity':{'head_observation':{'enabled':False}}}}
    if overlay != expected or type(overlay['urban']['capacity']['head_observation']['enabled']) is not bool:
        raise ValueError('OFF overlay must contain only the boolean head-observation flag')
    if on['urban']['capacity']['head_observation']['enabled'] is not True:
        raise ValueError('The designated ON configuration is not enabled')
    wanted=deepcopy(on);wanted['urban']['capacity']['head_observation']['enabled']=False
    actual=wanted if off is None else off
    if actual['urban']['capacity']['head_observation']['enabled'] is not False:
        raise ValueError('The designated OFF configuration must use boolean false')
    changes=differences(on,actual)
    if changes != [{'path':list(LEAF),'on':True,'off':False}]:
        raise ValueError('ON/OFF configurations differ beyond the head flag: '+repr(changes))
    return changes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--on-config',type=Path,required=True)
    p.add_argument('--off-config',type=Path)
    p.add_argument('--overlay',type=Path,default=ROOT/'diagnostics/signal_observation_off_overlay.json')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    sources={}
    def load(path):
        blob=path.read_bytes();sources[str(path.resolve())]=hashlib.sha256(blob).hexdigest()
        value=json.loads(blob.decode('utf-8-sig'))
        if 'extends' in value:raise ValueError('Use reviewed flattened config for exact comparison')
        return value
    on=load(a.on_config);overlay=load(a.overlay);off=load(a.off_config) if a.off_config else None
    changes=check(on,overlay,off)
    launcher=ROOT/'diagnostics/run_area_beta_trial.ps1'
    watchdog=ROOT/'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
    texts=[]
    for path in (launcher,watchdog):
        blob=path.read_bytes();sources[str(path)]=hashlib.sha256(blob).hexdigest()
        texts.append(blob.decode('utf-8-sig'))
    if not all(re.search(r'\[switch\]\s*\$ForceStepwise',s,re.I) for s in texts):
        raise ValueError('Launcher/watchdog ForceStepwise parameter missing')
    if '-ForceStepwise:$ForceStepwise' not in texts[0]:
        raise ValueError('Launcher does not pass its switch to the watchdog')
    output=a.output.resolve()
    if not output.is_relative_to(ROOT/'diagnostics') or output.exists():
        raise ValueError('New diagnostic output required')
    result={'schema':'signal-observation-pair/v1','status':'PASS','differences':changes,
            'off_materialized_in_memory_only':off is None,'source_sha256':sources,
            'launcher_force_stepwise_passthrough_present':True,
            'fixed_run_arguments':{'BetaSeconds':0,'Seed':13,'SimPeriod':1050,
                'Controller':'no-control','ForceStepwise':True,'ControlIntervalSec':150,
                'ControlStartSec':900,'WarmupController':'no-control','StateLogIntervalSec':30,
                'DemandScale':1,'RW_VEHREC_RESOLUTION':'1','RW_VEHICLE_ROUTES':'1'},
            'scope':'Config proof and source-text argument binding only. No candidate generation, simulator, controller, COM, or launcher execution.',
            'limits':['Disabling the head feature also disables its measured-capacity consumer. Under NoControl those model values must not change physical commands; verify all actual command/readback vectors after the run.',
                'The older ON smoke and a later OFF run may use different model source hashes after the independent phase-price repair. Preserve that limitation and verify physical command equality; do not label the entire software build a one-feature comparison.']}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(output),'status':'PASS','differences':changes}))


if __name__=='__main__':main()
