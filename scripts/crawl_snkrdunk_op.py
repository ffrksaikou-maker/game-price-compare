"""スニダンのワンピBOXを関連商品リンクからBFSクロールして全弾のグラフを取得。

スニダン検索窓はトレンド枠でBOXを1件しか返さず、全ID範囲scanはBOXの正確なIDを外す。
一方、BOX商品ページのHTMLには関連商品の /apparels/{id} が載っており、
ワンピBOX同士がリンクし合っている。既知BOX(190553/755998/816932)を種に
関連リンクをBFSで辿り、productNumberで弾を確定して1商品1IDでグラフ保存する。
"""
import requests, json, os, re, time
from collections import deque

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
ROOT = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(ROOT, 'data', 'snkrdunk_op')
MAP_PATH = os.path.join(OUT_DIR, 'product_mapping_op.json')
os.makedirs(OUT_DIR, exist_ok=True)
_s = requests.Session(); _s.headers.update(HEADERS)

from fetch_snkrdunk_op import SET_MAP  # noqa

SEEDS = [190553, 755998, 816932]  # OP-08, OP-15, OP-16


def get_json(pid):
    for a in range(4):
        try:
            r = _s.get(f'https://snkrdunk.com/v1/apparels/{pid}', timeout=8)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + a); continue
            return None
        except Exception:
            time.sleep(0.4)
    return None


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


def related_ids(pid):
    """商品ページHTMLから関連 apparel ID を抽出。"""
    for a in range(3):
        try:
            r = _s.get(f'https://snkrdunk.com/apparels/{pid}', timeout=12)
            if r.status_code == 200:
                ids = re.findall(r'/apparels/(\d+)', r.text)
                return [int(x) for x in dict.fromkeys(ids)]
            if r.status_code == 429:
                time.sleep(2 + a); continue
            return []
        except Exception:
            time.sleep(0.4)
    return []


def product_of(meta):
    """productNumber(OP-08 / OPC-TCG-OP-16 等)→日本語製品名。BOX/シュリンクなし優先。"""
    pn = (meta.get('productNumber') or '').upper()
    m = re.search(r'(OP|EB|PRB|ST)-?(\d+)', pn)
    if not m:
        return None
    key = f"{m.group(1).lower()}{int(m.group(2)):02d}"
    return SET_MAP.get(key)


def is_box(meta):
    name = (meta.get('name') or '').lower()
    color = meta.get('colorLocalizedName') or ''
    if any(k in name for k in ['carton', 'playmat', 'sleeve', 'storage', 'promotional', 'single']):
        return False
    if 'カートン' in color:
        return False
    return 'box' in name or 'ボックス' in color


def main():
    mapping = {}
    if os.path.exists(MAP_PATH):
        try:
            mapping = json.load(open(MAP_PATH, encoding='utf-8'))
        except Exception:
            mapping = {}
    # product -> (score, pid) : シュリンクなしBox優先で1商品1ID
    best = {}
    for prod, pid in mapping.items():
        best[prod] = (10, int(pid))

    seen = set()
    q = deque(SEEDS)
    processed = 0
    while q:
        pid = q.popleft()
        if pid in seen:
            continue
        seen.add(pid)
        meta = get_json(pid)
        processed += 1
        if not meta:
            continue
        prod = product_of(meta)
        is_b = is_box(meta)
        if prod and is_b:
            color = meta.get('colorLocalizedName') or ''
            score = 100 + (50 if 'シュリンクなし' in color else 0)
            if prod not in best or score > best[prod][0]:
                best[prod] = (score, pid)
            # このBOXの関連を辿る(ワンピBOX同士が繋がる)
            for rid in related_ids(pid):
                if rid not in seen:
                    q.append(rid)
            time.sleep(0.1)
        elif prod or ('one piece' in (meta.get('name') or '').lower()):
            # ワンピ関連(単品/プロモ等)も一段だけ関連展開(BOXに繋がることがある)
            for rid in related_ids(pid):
                if rid not in seen:
                    q.append(rid)
            time.sleep(0.1)
        if processed % 15 == 0:
            print(f"  processed {processed}, boxes found {len(best)}", flush=True)

    # 保存
    mapping = {}
    for prod, (score, pid) in best.items():
        pts = get_chart(pid)
        json.dump({"id": str(pid), "product": prod, "points": pts},
                  open(os.path.join(OUT_DIR, f"{pid}.json"), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        mapping[prod] = str(pid)
    json.dump(mapping, open(MAP_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"\n=== {len(mapping)}/{len(SET_MAP_PRODUCTS())} products found ===", flush=True)
    for prod, pid in sorted(mapping.items()):
        print(f"  {pid} -> {prod}", flush=True)
    missing = SET_MAP_PRODUCTS() - set(mapping.keys())
    if missing:
        print("MISSING:", flush=True)
        for m in sorted(missing):
            print("  ", m, flush=True)


def SET_MAP_PRODUCTS():
    return set(SET_MAP.values())


if __name__ == '__main__':
    main()
