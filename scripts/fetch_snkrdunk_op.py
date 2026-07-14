"""スニダンから全ワンピBOXの価格推移データを取得(スレッド並列版)。

ポケカ版 fetch_snkrdunk.py と同方式でID範囲を全スキャンし、タイトルに
ONE PIECE を含むBOX/Boosterを拾う。スニダンのタイトルは英語なので、
英語セット名→日本語製品名の対応表(SET_MAP)でマッピングして
data/snkrdunk_op/{id}.json と product_mapping_op.json を出力する。
"""
import requests, json, os, sys, time, re
from concurrent.futures import ThreadPoolExecutor

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
ROOT = os.path.dirname(os.path.dirname(__file__))
OUT_DIR = os.path.join(ROOT, 'data', 'snkrdunk_op')
MAP_PATH = os.path.join(ROOT, 'data', 'snkrdunk_op', 'product_mapping_op.json')
os.makedirs(OUT_DIR, exist_ok=True)

_session = requests.Session()
_session.headers.update(HEADERS)


def get_chart(pid):
    for _ in range(3):
        try:
            r = _session.get(
                f'https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId=0',
                timeout=8)
            if r.status_code == 200:
                return r.json().get('points', [])
            if r.status_code == 429:
                time.sleep(1.5)
                continue
            return []
        except Exception:
            time.sleep(0.4)
    return []


def get_meta(pid):
    """(name, productNumber) を返す。429は長めバックオフでリトライ。"""
    for attempt in range(6):
        try:
            r = _session.get(f'https://snkrdunk.com/v1/apparels/{pid}', timeout=8)
            if r.status_code == 200:
                d = r.json()
                return d.get('name', '') or '', d.get('productNumber', '') or ''
            if r.status_code == 429:
                time.sleep(2.5 + attempt)
                continue
            return '', ''
        except Exception:
            time.sleep(0.5)
    return '', ''


def map_product_number(pn: str) -> str | None:
    """OPC-TCG-OP-16 等の商品番号を日本語製品名に対応付け(最も確実)。"""
    if not pn:
        return None
    m = re.search(r'(OP|EB|PRB|ST)-?(\d+)', pn.upper())
    if not m:
        return None
    key = f"{m.group(1).lower()}{int(m.group(2)):02d}"
    return SET_MAP.get(key)


def is_onepiece_box(title: str) -> bool:
    t = title.lower()
    if 'one piece' not in t:
        return False
    # BOX/デッキ物のみ。単品・プロモ・サプライ・カートンは除外
    if not any(k in t for k in ['box', 'start deck', 'ultimate deck']):
        return False
    if any(k in t for k in ['carton', 'playmat', 'sleeve', 'storage', 'deck case',
                            'promotional card', 'single', 'binder', 'don!!']):
        return False
    return True


# 英語セット識別子 → 日本語製品名(products_onepiece.py の name と一致させる)
SET_MAP = {
    'romance dawn': 'ブースターパック「ROMANCE DAWN」【OP-01】',
    'op01': 'ブースターパック「ROMANCE DAWN」【OP-01】',
    'paramount war': 'ブースターパック「頂上決戦」【OP-02】',
    'op02': 'ブースターパック「頂上決戦」【OP-02】',
    'pillars of strength': 'ブースターパック「強大な敵」【OP-03】',
    'mighty enemies': 'ブースターパック「強大な敵」【OP-03】',
    'op03': 'ブースターパック「強大な敵」【OP-03】',
    'kingdoms of intrigue': 'ブースターパック「謀略の王国」【OP-04】',
    'op04': 'ブースターパック「謀略の王国」【OP-04】',
    'awakening of the new era': 'ブースターパック「新時代の主役」【OP-05】',
    'op05': 'ブースターパック「新時代の主役」【OP-05】',
    'wings of the captain': 'ブースターパック「双璧の覇者」【OP-06】',
    'twin champions': 'ブースターパック「双璧の覇者」【OP-06】',
    'op06': 'ブースターパック「双璧の覇者」【OP-06】',
    '500 years in the future': 'ブースターパック「500年後の未来」【OP-07】',
    'op07': 'ブースターパック「500年後の未来」【OP-07】',
    'two legends': 'ブースターパック「二つの伝説」【OP-08】',
    'op08': 'ブースターパック「二つの伝説」【OP-08】',
    'emperors in the new world': 'ブースターパック「新たなる皇帝」【OP-09】',
    'new emperor': 'ブースターパック「新たなる皇帝」【OP-09】',
    'op09': 'ブースターパック「新たなる皇帝」【OP-09】',
    'royal bloodlines': 'ブースターパック「王族の血統」【OP-10】',
    'op10': 'ブースターパック「王族の血統」【OP-10】',
    'a fist of divine speed': 'ブースターパック「神速の拳」【OP-11】',
    'divine speed': 'ブースターパック「神速の拳」【OP-11】',
    'op11': 'ブースターパック「神速の拳」【OP-11】',
    'legacy of the master': 'ブースターパック「師弟の絆」【OP-12】',
    'op12': 'ブースターパック「師弟の絆」【OP-12】',
    'the will that carries on': 'ブースターパック「受け継がれる意志」【OP-13】',
    'inherited will': 'ブースターパック「受け継がれる意志」【OP-13】',
    'op13': 'ブースターパック「受け継がれる意志」【OP-13】',
    'seven warlords of the sea': 'ブースターパック「蒼海の七傑」【OP-14】',
    'op14': 'ブースターパック「蒼海の七傑」【OP-14】',
    'adventure on the island of god': 'ブースターパック「神の島の冒険」【OP-15】',
    "the island of god": 'ブースターパック「神の島の冒険」【OP-15】',
    'op15': 'ブースターパック「神の島の冒険」【OP-15】',
    'the time of battle': 'ブースターパック「決戦の刻」【OP-16】',
    'op16': 'ブースターパック「決戦の刻」【OP-16】',
    'memorial collection': 'エクストラブースター「メモリアルコレクション」【EB-01】',
    'eb01': 'エクストラブースター「メモリアルコレクション」【EB-01】',
    'anime 25th': 'エクストラブースター「Anime 25th collection」【EB-02】',
    'eb02': 'エクストラブースター「Anime 25th collection」【EB-02】',
    'heroines': 'エクストラブースター「ONE PIECE Heroines Edition」【EB-03】',
    'eb03': 'エクストラブースター「ONE PIECE Heroines Edition」【EB-03】',
    'egghead': 'エクストラブースター「EGGHEAD CRISIS」【EB-04】',
    'eb04': 'エクストラブースター「EGGHEAD CRISIS」【EB-04】',
    'the best vol.2': 'プレミアムブースター「ONE PIECE CARD THE BEST vol.2」【PRB-02】',
    'the best vol. 2': 'プレミアムブースター「ONE PIECE CARD THE BEST vol.2」【PRB-02】',
    'prb02': 'プレミアムブースター「ONE PIECE CARD THE BEST vol.2」【PRB-02】',
    'the best': 'プレミアムブースター「ONE PIECE CARD THE BEST」【PRB-01】',
    'prb01': 'プレミアムブースター「ONE PIECE CARD THE BEST」【PRB-01】',
    'luffy & ace': 'スタートデッキEX ルフィ＆エース【ST-30】',
    'st-30': 'スタートデッキEX ルフィ＆エース【ST-30】',
}


def map_title(title: str) -> str | None:
    """英語タイトルを日本語製品名に対応付け。vol.2やEBを先に判定。"""
    t = title.lower()
    # 優先順(より限定的なキーを先に)
    priority = ['the best vol.2', 'the best vol. 2', 'anime 25th', 'egghead',
                'heroines', 'memorial collection']
    for k in priority:
        if k in t:
            return SET_MAP[k]
    for k, v in SET_MAP.items():
        if k in t:
            return v
    return None


WORKERS = 8


def scan_range(start, end, step):
    ids = list(range(start, end, step))
    results = []
    def probe(pid):
        pts = get_chart(pid)
        time.sleep(0.02)
        if len(pts) > 8:
            return (pid, pts)
        return None
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for r in ex.map(probe, ids):
            if r:
                results.append(r)
    return results


def classify(pid, pts):
    """productNumber優先→英語タイトルで日本語製品名に対応付け。BOX/デッキのみ。"""
    name, pn = get_meta(pid)
    prod = map_product_number(pn)
    if prod and ('box' in name.lower() or 'ultimate deck' in name.lower()
                 or 'start deck' in name.lower()):
        return (name, prod)
    if is_onepiece_box(name):
        m = map_title(name)
        if m:
            return (name, m)
    return None


CAND_CACHE = os.path.join(OUT_DIR, '_candidates.json')


def main():
    # OP-01は2022-07(≈60k以降)。それ以前はワンピ未発売なので60kから。
    if os.path.exists(CAND_CACHE):
        candidates = [tuple(x) for x in json.load(open(CAND_CACHE, encoding='utf-8'))]
        print(f"Loaded {len(candidates)} cached candidates (skip Phase1)", flush=True)
    else:
        ranges = [
            (60000, 120000, 5),
            (120000, 620000, 7),
            (620000, 860000, 5),
        ]
        candidates = []
        for start, end, step in ranges:
            c = scan_range(start, end, step)
            candidates += c
            print(f"  Range {start}-{end}: +{len(c)} candidates (total {len(candidates)})", flush=True)
        json.dump(candidates, open(CAND_CACHE, 'w', encoding='utf-8'))
        print(f"Phase1 done: {len(candidates)} candidates (cached)", flush=True)

    # Phase2: productNumber/タイトルでワンピBOX確認
    found = {}
    def check(item):
        pid, pts = item
        r = classify(pid, pts)
        time.sleep(0.02)
        if r:
            name, prod = r
            return (pid, name, prod, pts)
        return None
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(check, candidates):
            if r:
                pid, name, prod, pts = r
                found[str(pid)] = {'id': str(pid), 'name': name, 'product': prod, 'points': pts}
                print(f"  BOX {pid}: {name[:52]} -> {prod[:24]} ({len(pts)}pts)", flush=True)

    # Phase3: 近傍±25を密スキャン(兄弟/未ヒット弾拾い)
    neigh = []
    for base in list(found.keys()):
        for off in range(-25, 26):
            pid = int(base) + off
            if str(pid) not in found:
                neigh.append(pid)
    def probe2(pid):
        pts = get_chart(pid)
        time.sleep(0.02)
        if len(pts) > 8:
            r = classify(pid, pts)
            if r:
                return (pid, r[0], r[1], pts)
        return None
    with ThreadPoolExecutor(max_workers=4) as ex:
        for r in ex.map(probe2, neigh):
            if r:
                pid, name, prod, pts = r
                if str(pid) not in found:
                    found[str(pid)] = {'id': str(pid), 'name': name, 'product': prod, 'points': pts}
                    print(f"  NEW {pid}: {name[:52]} -> {prod[:24]} ({len(pts)}pts)", flush=True)

    # 保存 + マッピング構築。
    # ★グラフは1商品につき1ID厳守(shrink/no-shrink等の重複を混ぜない)。
    #   同一製品に複数ID該当時は「シュリンクなし(No shrink)のBox」を優先、
    #   なければpoints数最多を採用。
    mapping = {}
    best = {}  # product -> (score, pid)
    for pid, data in found.items():
        path = os.path.join(OUT_DIR, f'{pid}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        prod = data.get('product')
        if not prod:
            continue
        nm = data['name'].lower()
        # スコア: no shrink box を最優先, 次にbox, 次にpoints数
        score = len(data['points'])
        if 'no shrink' in nm and 'box' in nm:
            score += 1_000_000
        elif 'box' in nm:
            score += 500_000
        if prod not in best or score > best[prod][0]:
            best[prod] = (score, pid)
    for prod, (score, pid) in best.items():
        mapping[prod] = pid

    with open(MAP_PATH, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n=== DONE! {len(found)} OP ids / {len(mapping)} products mapped (1 id each) ===", flush=True)
    for prod, pid in sorted(mapping.items()):
        print(f"  {pid} -> {prod}", flush=True)
    print("mapped products:", len(mapping), flush=True)


if __name__ == '__main__':
    main()
