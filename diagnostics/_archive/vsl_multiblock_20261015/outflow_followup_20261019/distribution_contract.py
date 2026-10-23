"""Read native desired-speed CDFs; deterministic, unfitted mean correction.

An experimental actuator-to-free-speed mapping, not a replacement Carlson law
or an assertion that mean speed captures native variance/lane-change effects.
"""
import hashlib
import json
import math
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
NETWORK = ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'


def moments(points):
    if len(points) < 2 or points[0][0] != 0 or points[-1][0] != 1:
        raise ValueError('CDF must cover zero through one')
    if any(not math.isfinite(x) for row in points for x in row):
        raise ValueError('Nonfinite CDF')
    if any(b <= a or y < x or x <= 0 for (a, x), (b, y) in zip(points, points[1:])):
        raise ValueError('CDF must be monotonic with positive speeds')
    mean = sum((b-a)*(x+y)/2 for (a,x),(b,y) in zip(points,points[1:]))
    second = sum((b-a)*(x*x+x*y+y*y)/3 for (a,x),(b,y) in zip(points,points[1:]))
    return mean, math.sqrt(max(0., second-mean*mean))


def quantile(points, fraction):
    if not 0 <= fraction <= 1:
        raise ValueError('Fraction outside CDF')
    for (a,x),(b,y) in zip(points,points[1:]):
        if fraction <= b:
            return x+(y-x)*(fraction-a)/(b-a)
    raise ValueError('CDF does not cover fraction')


def load_distributions():
    tree = ET.parse(NETWORK)
    rows = {}
    for number in (50,60,70,80,90,100,110):
        element = tree.find(f"./desSpeedDistributions/desSpeedDistribution[@no='{number}']")
        if element is None:
            continue
        points = [(float(p.get('fx')),float(p.get('x'))) for p in element.findall('./speedDistrDatPts/speedDistributionDataPoint')]
        mean, std = moments(points)
        rows[number] = dict(points=points, mean=mean, std=std)
    assert {90,110}.issubset(rows)
    for number in range(59,67):
        dsd = tree.find(f"./desSpeedDecisions/desSpeedDecision[@no='{number}']")
        assert dsd is not None
        assert {int(p.get('desSpeedDistr')) for p in dsd.findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')} == {110}
    return rows


def free_speed_multiplier(rows, command, maximum):
    # Only discrete 90/110 qualified for this isolated candidate. No optimizer
    # interpolation, tangent derivative, or other actuation value is implied.
    if command not in (90,110) or maximum != 110:
        raise ValueError('This diagnostic is qualified only for 90/110')
    if command == maximum:
        return 1.
    return rows[command]['mean']/rows[maximum]['mean']/(command/maximum)


class ContractTests(unittest.TestCase):
    def test_uniform(self):
        m,s=moments([(0,80),(1,120)])
        self.assertEqual(m,100)
        self.assertAlmostEqual(s,40/math.sqrt(12))
    def test_constant(self):
        self.assertEqual(moments([(0,90),(.5,90),(1,90)]),(90,0))
    def test_cdf_endpoints(self):
        with self.assertRaises(ValueError): moments([(.1,90),(1,110)])
    def test_cdf_order(self):
        with self.assertRaises(ValueError): moments([(0,90),(.7,110),(.5,120),(1,130)])
    def test_speed_order(self):
        with self.assertRaises(ValueError): moments([(0,110),(1,90)])
    def test_quantile(self):
        self.assertEqual(quantile([(0,80),(.5,100),(1,120)],.75),110)
    def test_no_control_identity(self):
        self.assertEqual(free_speed_multiplier(load_distributions(),110,110),1.)
    def test_only_qualified_commands(self):
        with self.assertRaises(ValueError): free_speed_multiplier(load_distributions(),100,110)


def main():
    target=OUT/'distribution_contract.json'
    assert not target.exists(), 'Reuse completed audit'
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
    assert result.wasSuccessful()
    rows=load_distributions()
    points=sorted(set(p for number in (90,110) for p,v in rows[number]['points']))
    coupled=[dict(fractile=p,desired110=quantile(rows[110]['points'],p),desired90=quantile(rows[90]['points'],p)) for p in points]
    record=dict(status='native_distribution_contract_verified_candidate_not_adopted',distributions=rows,
        same_fractile= coupled, nominal_ratio=90/110, native_population_mean_ratio=rows[90]['mean']/rows[110]['mean'],
        candidate_free_speed_multiplier=free_speed_multiplier(rows,90,110), tests=result.testsRun,
        source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (NETWORK,Path(__file__))},
        new_native=0,new_forecasts=0,production_edits=0,parameter_fits=0,
        references=['https://cgi.ptvgroup.com/vision-help/VISSIM_2025_ENG/Content/5_Netzbearbeiten/Strassennetz_Wunschg_vWunsch_aendern.htm',
                    'https://www.cgi.ptvgroup.com/vision-help/VISSIM_2022_ENG/Content/4_BasisdatenSim/BasisdatenWunschgeschw_verteil_verw.htm'],
        limitations=['Population means are not observed local vehicle means or achievable congested speeds.',
                     'The candidate addresses mean actuation amplitude only; variance, overtaking and lane imbalance remain unresolved.',
                     'Density/shape parameters retain nominal Carlson scaling. This hybrid is a diagnostic hypothesis, not a confirmed correction.'])
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    protocol=dict(hypothesis='Nominal 90/110 overstates mean desired-speed reduction encoded in native CDFs. Test population-mean free-speed scaling while preserving all nominal density/shape coefficients.',
        candidate='Only the speed component returned by literature_vsl_parameters is multiplied by mean(CDF90)/mean(CDF110)/(90/110). No other change.',
        budget=dict(initial_selected450=1,additional_forecasts=0,native=0,optimizer=0,fits=0),
        baseline='Reuse matched_off2250_v3; maximum110 branch is algebraically unchanged, so no baseline rerun.',
        gate='Compare approach18 throughflow and stock14:18 at150/300/450, whole Omega and regional costs, conservation, feasibility and runtime. Reject as a sufficient explanation if450 response remains wrong-sign; do not tune factor.',
        limits='Any improvement still requires separate existing independent-pair checks and scalar/AD, NP/NUF, actuator and walltime validation before adoption.')
    (OUT/'distribution_candidate_protocol.json').write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:record[k] for k in ('nominal_ratio','native_population_mean_ratio','candidate_free_speed_multiplier','tests')}))


if __name__=='__main__': main()
