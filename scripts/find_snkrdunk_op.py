"""各ワンピBOXのスニダンIDを発売日→ID補間で推定し、狭い窓をget_metaで精査して発見する。

IDスキャン(全範囲step)ではワンピBOXの正確なIDを外すため、既知3アンカー
(OP-08=190553, OP-15=755998, OP-16=816932)+ポケカ時系列で補間し、
各弾の推定ID周辺をstep1で精査。productNumber(OPC-TCG-OP-16等)で確定し、
「ボックス(シュリンクなし)」を1商品1IDで採用する。
"""
import requests, json, os, time
from datetime import date
from concurrent.futures import ThreadPoolExecutor

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
ROOT = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(ROOT, 'data', 'snkrdunk_op')
MAP_PATH = os.path.join(OUT_DIR, 'product_mapping_op.json')
os.makedirs(OUT_DIR, exist_ok=True)
_s = requests.Session(); _s.headers.update(HEADERS)

# (発売日, ID) アンカー。ワンピBOX実測5点+ポケカ時系列。日付→IDは概ね単調。
ANCHORS = sorted([
    (date(2021, 9, 25), 14673),
    (date(2022, 10, 28), 101885),
    (date(2023, 3, 15), 116897),
    (date(2024, 5, 25), 190553),   # OP-08 box(実測)
    (date(2024, 8, 31), 299926),   # OP-09 box(実測)
    (date(2025, 1, 25), 407696),   # EB-02 box(実測)
    (date(2025, 6, 13), 618442),
    (date(2025, 8, 29), 687430),
    (date(2026, 2, 28), 755998),   # OP-15 box(実測)
    (date(2026, 5, 30), 816932),   # OP-16 box(実測)
])

# 製品コード -> (発売日, 日本語製品名)
from fetch_snkrdunk_op import SET_MAP  # noqa
PRODUCTS = [
    ("op01", date(2022, 7, 22)), ("op02", date(2022, 11, 4)),
    ("op03", date(2023, 2, 11)), ("op04", date(2023, 5, 27)),
    ("op05", date(2023, 8, 26)), ("op06", date(2023, 11, 25)),
    ("op07", date(2024, 2, 24)), ("op08", date(2024, 5, 25)),
    ("op09", date(2024, 8, 31)), ("op10", date(2024, 11, 30)),
    ("op11", date(2025, 3, 1)), ("op12", date(2025, 5, 31)),
    ("op13", date(2025, 8, 23)), ("op14", date(2025, 11, 22)),
    ("op15", date(2026, 2, 28)), ("op16", date(2026, 5, 30)),
    ("eb01", date(2024, 1, 27)), ("eb02", date(2025, 1, 25)),
    ("eb03", date(2025, 10, 25)), ("eb04", date(2026, 1, 31)),
    ("prb01", date(2024, 7, 27)), ("prb02", date(2025, 7, 26)),
    ("st30", date(2026, 4, 11)),
]


def estimate_id(d: date) -> int:
    for i in range(len(ANCHORS) - 1):
        d0, id0 = ANCHORS[i]
        d1, id1 = ANCHORS[i + 1]
        if d0 <= d <= d1:
            span = (d1 - d0).days or 1
            return int(id0 + (id1 - id0) * ((d - d0).days / span))
    if d < ANCHORS[0][0]:
        return ANCHORS[0][1]
    return ANCHORS[-1][1]


def get_meta(pid):
    for a in range(4):
        try:
            r = _s.get(f'https://snkrdunk.com/v1/apparels/{pid}', timeout=8)
            if r.status_code == 200:
                d = r.json()
                return (d.get('name', '') or '', d.get('productNumber', '') or '',
                        d.get('colorLocalizedName', '') or '')
            if r.status_code == 429:
                time.sleep(2 + a); continue
            return '', '', ''
        except Exception:
            time.sleep(0.4)
    return '', '', ''


def get_chart(pid):
    for a in range(3):
        try:
            r = _s.get(f'https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId=0', timeout=8)
            if r.status_code == 200:
                return r.json().get('points', [])
            if r.status_code == 429:
                time.sleep(2 + a); continue
            return []
        except Exception:
            time.sleep(0.4)
    return []


def find_box(code, est, window=4500):
    """推定ID±windowをstep1でget_meta。productNumber一致のBOXを収集し、
    シュリンクなしBox>Box>その他 で1つ選ぶ。"""
    target = code.upper().replace("OP", "OP-").replace("EB", "EB-").replace("PRB", "PRB-").replace("ST", "ST-")
    # 例: op16 -> OP-16 / eb04 -> EB-04 / prb02 -> PRB-02 / st30 -> ST-30
    cands = []
    ids = list(range(est - window, est + window))
    def probe(pid):
        name, pn, color = get_meta(pid)
        if pn and target in pn.upper():
            return (pid, name, color)
        return None
    with ThreadPoolExecutor(max_workers=12) as ex:
        for r in ex.map(probe, ids):
            if r:
                cands.append(r)
    if not cands:
        return None
    def score(c):
        pid, name, color = c
        s = 0
        nl, cl = name.lower(), color
        if 'box' in nl or 'ボックス' in color:
            s += 100
        if 'シュリンクなし' in cl or 'no shrink' in nl:
            s += 50
        if any(k in nl for k in ['carton', 'カートン', 'playmat', 'sleeve']):
            s -= 1000
        return s
    cands.sort(key=score, reverse=True)
    return cands[0][0] if score(cands[0]) > 0 else None


def main():
    mapping = {}
    if os.path.exists(MAP_PATH):
        try:
            mapping = json.load(open(MAP_PATH, encoding='utf-8'))
        except Exception:
            mapping = {}
    for code, d in PRODUCTS:
        prod = SET_MAP.get(code)
        if not prod:
            print("no SET_MAP for", code, flush=True); continue
        if prod in mapping and os.path.exists(os.path.join(OUT_DIR, f"{mapping[prod]}.json")):
            print(f"  skip {code} (already {mapping[prod]})", flush=True); continue
        est = estimate_id(d)
        pid = find_box(code, est)
        if pid:
            pts = get_chart(pid)
            json.dump({"id": str(pid), "product": prod, "points": pts},
                      open(os.path.join(OUT_DIR, f"{pid}.json"), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=2)
            mapping[prod] = str(pid)
            json.dump(mapping, open(MAP_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            print(f"  FOUND {code}: {pid} ({len(pts)}pts) est={est}", flush=True)
        else:
            print(f"  MISS {code}: est={est} (要窓拡大)", flush=True)
    print(f"\n=== {len(mapping)} products mapped ===", flush=True)
    for p, i in sorted(mapping.items()):
        print(f"  {i} -> {p}", flush=True)


if __name__ == '__main__':
    main()
