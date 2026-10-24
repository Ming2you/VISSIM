"""Redraw the supplied stopped-density figure without text, using its original cache."""
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize, LinearSegmentedColormap
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / 'to8550'
summary = json.loads((OUT / 'summary.json').read_bytes())
network = next(Path(p) for p,h in summary['source_sha256'].items()
               if p.lower().endswith('.inpx') and h == summary['network_sha256'])
raw = network.read_bytes()
assert hashlib.sha256(raw).hexdigest() == summary['network_sha256']
net = ET.fromstring(raw)
with (OUT / 'link_window_metrics.csv').open(encoding='utf-8-sig', newline='') as f:
    rows = [r for r in csv.DictReader(f) if int(r['from_sec']) == 7950 and int(r['to_sec']) == 8550]
data = {a: {int(r['link']): r for r in rows if r['arm'] == a} for a in ('nc','sdmpc')}
ids = sorted(data['nc'])
assert ids == sorted(data['sdmpc'])
bg = next(x for x in net.findall('./backgroundImages/backgroundImage') if x.get('no') == '4')
origin = np.array([float(bg.find('coordBL').get(k)) for k in ('x','y')])
polylines = {int(link.get('no')): np.array([[float(p.get('x')),float(p.get('y'))]
             for p in link.findall('./geometry/linkPolyPts/linkPolyPoint')])
             for link in net.findall('./links/link')}
geom = [(polylines[lid] - origin)/1000 for lid in ids]
cats = [data['nc'][lid]['category'] for lid in ids]
urban = np.array([c == 'urban_and_other_inside' for c in cats])
outside = np.array([c == 'outside' for c in cats])
ramps = np.array([c in ('on_ramp_connector','off_ramp_connector') for c in cats])
freeway = np.array([c.startswith('FW_') for c in cats])
major = np.array([float(data['nc'][lid]['length_m']) >= 60 for lid in ids])
points = np.vstack([geom[j] for j in np.where(urban)[0]])
bounds = [points[:,0].min()-.18,points[:,0].max()+.18,
          points[:,1].min()-.18,points[:,1].max()+.18]
cmap = LinearSegmentedColormap.from_list('urban_density', ['#719db4','#ecddae','#efa45b','#d6543b','#851b34'])
norm = Normalize(0,100)
fig, axes = plt.subplots(1,2,figsize=(17,7.4))
fig.subplots_adjust(left=.006,right=.946,bottom=.015,top=.985,wspace=.035)
for ax, arm in zip(axes, ('nc','sdmpc')):
    avg = sum(float(data[arm][ids[j]]['mean_stopped']) for j in np.where(urban)[0])
    assert abs(avg-summary['arms'][arm]['urban_inside']['window_means'][-1]['stopped']) < 1e-9
    ax.add_collection(LineCollection(geom,colors='#d7dce1',linewidths=.55,zorder=1))
    ax.add_collection(LineCollection([geom[j] for j in np.where(freeway)[0]],colors='#6d4ca0',linewidths=1.25,zorder=2))
    ax.add_collection(LineCollection([geom[j] for j in np.where(ramps)[0]],colors='#495f76',linewidths=1,zorder=2))
    values = np.array([float(data[arm][lid]['stopped_density_veh_per_lane_km']) for lid in ids])
    for mask,style,width in ((outside,'dashed',1.45),(urban,'solid',1.9)):
        js=np.where(mask & major)[0]
        ax.add_collection(LineCollection([geom[j] for j in js],array=values[js],cmap=cmap,norm=norm,
                                        linewidths=width,linestyles=style,zorder=3))
    ax.set(xlim=bounds[:2],ylim=bounds[2:],aspect='equal')
    ax.set_xticks([]);ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_edgecolor('#d0d6dd')
cax=fig.add_axes([.964,.16,.014,.68])
bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),cax=cax,extend='max')
bar.set_ticks([])
cax.set_ylabel('')
fig.canvas.draw()
assert all(not t.get_text() for t in fig.findobj(matplotlib.text.Text)), 'Unexpected visible text'
for extension in ('png','svg'):
    fig.savefig(OUT/f'urban_stopped_density_no_text.{extension}',dpi=200,facecolor='white')
plt.close(fig)
print('Saved urban_stopped_density_no_text.png / .svg; identical 7950-8550 data and 0-100 color normalization; no text.')
