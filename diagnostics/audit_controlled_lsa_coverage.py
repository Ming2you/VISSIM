"""Read one completed controlled LSA and at most5MiB of existing readback.

No model imports, COM, simulation, FZP or broad run discovery.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
from collections import Counter,defaultdict
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'evaluation/runs/codex_area_sources_beta0_s13_20260910'


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    dec=RUN/('decisions_'+RUN.name)
    lsa=RUN/'vissim_eval/modi_eval_userfix Ver2_001.lsa'
    raw_lsa=lsa.read_bytes(); by=defaultdict(list); previous=-1
    for line in raw_lsa.splitlines():
        if b';' not in line: continue
        fields=[s.strip() for s in line.decode('ascii').split(';')]
        assert len(fields)==9 and fields[-1]==''
        sec=float(fields[0]); assert math.isfinite(sec) and previous<=sec<=5400; previous=sec
        by[(int(fields[2]),int(fields[3]))].append({'sec':sec,'state':fields[4].upper(),'mode':fields[6]})
    readback=dec/'signal_readback.csv'; initial_stat=readback.stat()
    prefix_hash=hashlib.sha256(); prefix_bytes=0; kept=[]; first_past=None
    with readback.open('rb') as f:
        header=f.readline(); prefix_hash.update(header); prefix_bytes+=len(header)
        names=next(csv.reader([header.decode('ascii')]))
        for line in f:
            prefix_hash.update(line); prefix_bytes+=len(line)
            assert prefix_bytes<=5*1024*1024, 'Bounded prefix exceeded'
            row=dict(zip(names,next(csv.reader([line.decode('ascii')]))));sec=float(row['sim_sec'])
            if sec>1050: first_past=sec;break
            if sec==1 or 900<=sec<=1050: kept.append(row)
    assert first_past is not None
    assert (readback.stat().st_size,readback.stat().st_mtime_ns)==(initial_stat.st_size,initial_stat.st_mtime_ns)
    groups=sorted({(int(r['sc_no']),int(r['sg_no'])) for r in kept if float(r['sim_sec'])>=900})
    initial=defaultdict(list); post=defaultdict(list)
    for row in kept:
        g=(int(row['sc_no']),int(row['sg_no']));t=float(row['sim_sec'])
        sample={'sec':t,'stage':row['stage'],'requested':row['requested_state'],'actual':row['readback_state'],'ok':row['ok']}
        if t==1 or (t==900 and row['stage']=='immediate'):initial[g].append(sample)
        if 901<=t<=1050 and row['stage']=='post_step':post[g].append(sample)
    summary=[]
    for g in groups:
        rows=post[g];events=by.get(g,[])
        changes=[{'sec':r['sec'],'before':rows[i-1]['actual'],'after':r['actual']}
                 for i,r in enumerate(rows) if i and r['actual']!=rows[i-1]['actual']]
        mismatches=[]
        for r in rows:
            seen=[e for e in events if e['sec']<=r['sec']];last=seen[-1] if seen else None
            if last is None or last['state']!=r['actual'].upper():
                mismatches.append({'sec':r['sec'],'actual':r['actual'],'last_lsa':last})
        summary.append({'sc':g[0],'sg':g[1],'kind':'meter' if 9101<=g[0]<=9108 else 'urban',
            'lsa_rows':len(events),'lsa_first':events[0] if events else None,'lsa_last':events[-1] if events else None,
            'lsa_events_after900':sum(e['sec']>900 for e in events),
            'post_step_rows901_1050':len(rows),'unique_post_seconds':len({r['sec'] for r in rows}),
            'actual_states':dict(Counter(r['actual'] for r in rows)),'actual_changes901_1050':changes,
            'readback_all_ok':all(r['ok']=='1' and r['requested']==r['actual'] for r in rows),
            'lsa_state_mismatch_count':len(mismatches),'first_mismatch':mismatches[0] if mismatches else None,
            'initial_samples':initial[g][:4]})
    manifest=RUN/('run_provenance_'+RUN.name+'.json');md=json.loads(manifest.read_text(encoding='utf-8-sig'))
    network=Path(md['files']['network']['path']);assert digest(network)==md['files']['network']['sha256']
    tree=ET.parse(network).getroot()
    log=RUN/('runlog_'+RUN.name+'.txt'); lines=log.read_bytes().splitlines();watch=RUN/'WATCHDOG_PROGRESS.txt'
    counters={k:[r.decode('ascii') for r in lines if r.startswith((k+'=').encode())] for k in
        ('DECISIONS_FAILED','OBSERVATION_FAILURES','SIGNAL_FAILURES','ACTION_FORMAT_FAILURES','COM_FAILURES')}
    assert all(v==[k+'=0'] for k,v in counters.items())
    assert lines.count(b'STAGE=SIM_DONE')==1 and lines.count(b'SIM_SEC=5400')==1
    assert ('OK '+RUN.name+' attempt=1') in watch.read_text(encoding='utf-8-sig')
    action=dec/'action_000900.csv'
    with action.open(encoding='utf-8-sig') as f: commands=list(csv.DictReader(f))
    csv_city={(int(r['sc_no']),int(r['dsd_no'])) for r in commands if r['kind']=='signal_sg'}
    city=[r for r in summary if r['kind']=='urban'];meters=[r for r in summary if r['kind']=='meter']
    sources=[lsa,action,manifest,watch,log,network,ROOT/'scripts/run_real_world_stackelberg_controller.vbs',Path(__file__)]
    report={'schema':'controlled-native-lsa-coverage/v1','run':str(RUN),'run_id':md['run_id'],
        'scope':'Completed controlled run; whole small LSA and bounded readback prefix. CSV is expected command only. No model/COM/FZP.',
        'completion':{'controller':md['controller'],'period_sec':md['sim_period_sec'],'sim_done':True,'sim_sec5400':True,'watchdog_ok':True,'failure_counters':counters},
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'readback_prefix':{'path':str(readback),'file_bytes':initial_stat.st_size,'read_bytes':prefix_bytes,'sha256':prefix_hash.hexdigest(),'stop_after_first_sample_sec':first_past,'full_file_not_scanned':True},
        'lsa':{'rows':sum(len(v) for v in by.values()),'groups':len(by),'first_sec':min(v[0]['sec'] for v in by.values()),'last_sec':max(v[-1]['sec'] for v in by.values()),'modes':dict(Counter(e['mode'] for v in by.values() for e in v))},
        'coverage':{'command_city_groups':len(csv_city),'actual_readback_city_groups':len(city),'actual_readback_meter_groups':len(meters),
            'readback_city_not_in_csv':[[r['sc'],r['sg']] for r in city if (r['sc'],r['sg']) not in csv_city],
            'readback_groups_absent_from_lsa':[[r['sc'],r['sg']] for r in summary if not r['lsa_rows']],
            'urban_lsa_events_after900':sum(r['lsa_events_after900'] for r in city),'meter_lsa_events_after900':sum(r['lsa_events_after900'] for r in meters),
            'urban_actual_changes901_1050':sum(len(r['actual_changes901_1050']) for r in city),'meter_actual_changes901_1050':sum(len(r['actual_changes901_1050']) for r in meters),
            'all_readbacks_match_requested':all(r['readback_all_ok'] for r in summary),'lsa_cannot_replace_COM_readback':True},
        'groups':summary,
        'native_configuration':{'xml_signal_evaluation':[{'tag':x.tag,'attributes':x.attrib} for x in tree.find('evaluation').iter() if 'sig' in x.tag.lower()],
            'runtime_native_eval_log':[r.decode('ascii') for r in lines if r.startswith(b'NATIVE_EVAL=')],
            'env':{k:v for k,v in md['env'].items() if k in ('RW_NATIVE_EVAL','RW_MAINLINE_SG_ONLY','RW_SIGNAL_READBACK_SEC','RW_SIGNAL_WRITE_ON_CHANGE')},
            'sample_SC_attributes':{no:tree.find("./signalControllers/signalController[@no='%s']"%no).attrib for no in ('1','1004','9103')}},
        'limits':['LSA through900 is native pre-takeover evidence, not initial COM state.',
                  'Readback901..1050 observes post-step states each second, not subsecond events.',
                  'No extra native option exporting COM transitions has been established from current sources.',
                  'Initial+transition+first-post-step readback does not certify every unsampled second.']}
    assert lsa.read_bytes()==raw_lsa
    (ROOT/'diagnostics/controlled_native_lsa_coverage.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'coverage':report['coverage'],'readback_prefix_bytes':prefix_bytes,'lsa':report['lsa']}))


if __name__=='__main__':main()
