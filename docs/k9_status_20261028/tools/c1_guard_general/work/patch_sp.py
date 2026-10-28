p = 'tools/inv_spacing.py'
s = open(p, encoding='utf-8').read()
s = s.replace("from collections import defaultdict\n", "from array import array\nfrom collections import defaultdict\n", 1)
s = s.replace("""        self.lead_len_s = 0.0

    def add(self, d, gap, lead_len):
        self.n += 1""", """        self.lead_len_s = 0.0
        self.vals = array('d')
        self.gaps = array('d')

    def add(self, d, gap, lead_len):
        self.vals.append(d)
        self.gaps.append(gap)
        self.n += 1""")
s = s.replace("""    def summary(self):
        if not self.n:
            return {'pairs': 0}
        m = self.s / self.n""", """    @staticmethod
    def exact(vals, q):
        v = sorted(vals)
        if not v:
            return None
        k = q * (len(v) - 1)
        i = int(math.floor(k))
        j = min(i + 1, len(v) - 1)
        return v[i] + (v[j] - v[i]) * (k - i)

    def summary(self):
        if not self.n:
            return {'pairs': 0}
        m = self.s / self.n""")
s = s.replace("""                'd_pct': {str(q): self.pct(self.hist, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},
                'gap_pct': {str(q): self.pct(self.gap_hist, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},""",
"""                'd_pct': {str(q): self.exact(self.vals, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},
                'gap_pct': {str(q): self.exact(self.gaps, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},
                'mean_gap_m': sum(self.gaps) / self.n, 'share_gap_negative': sum(1 for x in self.gaps if x < 0) / self.n,""")
s = s.replace("'recommended_rule': 'median d over all stopped pairs (bin 0.1 m, centre)'", "'recommended_rule': 'median d over all stopped pairs (exact, linear interpolation)'")
open(p, 'w', encoding='utf-8').write(s)
print('ok')
