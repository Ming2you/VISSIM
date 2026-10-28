"""Field check of the code-copy verify record GT/code_va.tree.json (PRE_VP_R3, user decision D-K9-109 (3)).

Every `vp_tree.py verify` (H0) rewrites the record with a new `checked_kst`, so since r3 its sha is no longer in the
outside pin list.  Instead its ok / count fields are compared, together with the two identity fields that are not
time stamps (schema and the FREEZE.json sha the copy was checked against).  `checked_kst` is ignored.  Prints and
writes booleans only (no path strings).

    python -B vp_treefields.py [record.json] [out.json]

Exit 0 = every field as expected, 2 = a field differs or the record is unreadable (S-ERR at L0)."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vp_common as C  # noqa: E402

EXPECT = {'schema': 'vp-tree/1', 'ok': True, 'freeze_sha256': C.FRZ_VA_FREEZE_SHA, 'files_expected': 10569,
          'missing_n': 0, 'differs_n': 0}


def check(doc):
    """Booleans per field; a value must be equal and of the same type (so 1 is not True)."""
    d = doc if isinstance(doc, dict) else {}
    res = {k: (k in d and type(d[k]) is type(v) and d[k] == v) for k, v in EXPECT.items()}
    res['missing_empty'] = d.get('missing') == []
    res['differs_empty'] = d.get('differs') == []
    return res


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(str(C.CODE) + '.tree.json')
    doc = C.read_json(path)
    res = check(doc)
    ok = isinstance(doc, dict) and all(res.values())
    rec = {'schema': 'vp-treefields/1', 'kst': C.kst(), 'ok': ok, 'fields': res,
           'record_sha256': C.sha256_file(path) if path.is_file() else None,
           'ignored_time_field': (doc or {}).get('checked_kst') if isinstance(doc, dict) else None}
    if len(sys.argv) > 2:
        C.write_json(sys.argv[2], rec)
    print('TREEFIELDS ok=%s %s' % (ok, ' '.join('%s=%s' % (k, v) for k, v in res.items())))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
