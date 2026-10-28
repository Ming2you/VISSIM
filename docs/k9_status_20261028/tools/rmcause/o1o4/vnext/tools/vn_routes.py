# VERIFY_NEXT: static routing decisions 1135 (link 68) and 1137 (link 31) relFlow (read-only)
import sys, hashlib
import xml.etree.ElementTree as ET
for p in sys.argv[1:]:
    raw = open(p, 'rb').read()
    print('==', p, hashlib.sha256(raw).hexdigest()[:16])
    r = ET.fromstring(raw)
    for dec in r.iter('vehicleRoutingDecisionStatic'):
        if dec.get('no') in ('1135', '1137'):
            print(' decision', dec.get('no'), 'link', dec.get('link'), 'pos', dec.get('pos'))
            for rt in dec.iter('vehicleRouteStatic'):
                seq = [x.get('link') if x.get('link') else x.get('lane') for x in rt.iter() if x.tag in ('linkSeqItem', 'link')]
                links = rt.find('linkSeq')
                ls = [x.get('key') or x.get('link') for x in links] if links is not None else []
                print('   route', rt.get('no'), 'dest', rt.get('destLink'), 'relFlow', repr(rt.get('relFlow')), 'seq', ls[:6])
