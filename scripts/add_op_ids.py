"""ユーザー提供のスニダンapparel IDを検証して1商品1IDでグラフ保存＆マッピング追加。
旧弾はproductNumberが OPC-0XX 形式(弾番号と無関係)なので日本語名でも判定する。
usage: python scripts/add_op_ids.py 691521 548907 ...
"""
import requests, json, os, re, sys
h = {'User-Agent': 'Mozilla/5.0'}
ROOT = os.path.dirname(os.path.dirname(__file__))
OUT = os.path.join(ROOT, 'data', 'snkrdunk_op')
MP = os.path.join(OUT, 'product_mapping_op.json')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from fetch_snkrdunk_op import SET_MAP  # noqa

# コードキー正規化(SET_MAPは 'st-30' 等ハイフン有りキーも持つ)
def prod_by_code(code):
    return SET_MAP.get(code) or SET_MAP.get(
        {'st30': 'st-30', 'op01': 'op01'}.get(code, code))

# 日本語弾名/英語名 → コード(旧 OPC-0XX 形式の弾番号無し対策)
NAME_MAP = [
    ("決戦の刻", "op16"), ("神の島の冒険", "op15"), ("蒼海の七傑", "op14"),
    ("受け継がれる意志", "op13"), ("師弟の絆", "op12"), ("神速の拳", "op11"),
    ("王族の血統", "op10"), ("新たなる皇帝", "op09"), ("二つの伝説", "op08"),
    ("500年後の未来", "op07"), ("双璧の覇者", "op06"), ("新時代の主役", "op05"),
    ("謀略の王国", "op04"), ("強大な敵", "op03"), ("頂上決戦", "op02"),
    ("ロマンスドーン", "op01"), ("romance dawn", "op01"),
    ("メモリアルコレクション", "eb01"),
    ("25th", "eb02"), ("ヒロイン", "eb03"), ("heroines", "eb03"),
    ("egghead", "eb04"), ("エッグヘッド", "eb04"),
    ("best vol.2", "prb02"), ("ベスト vol.2", "prb02"), ("ベスト vol. 2", "prb02"),
    ("the best", "prb01"),
    ("ルフィ&エース", "st30"), ("ルフィ＆エース", "st30"),
]


def classify(pn, name):
    pnU = pn.upper()
    mm = re.search(r'-(OP|EB|PRB|ST)-?(\d+)', pnU) or re.search(r'\b(OP|EB|PRB|ST)-(\d+)', pnU)
    if mm:
        code = f"{mm.group(1).lower()}{int(mm.group(2)):02d}"
        p = prod_by_code(code)
        if p:
            return p
    nl = name.lower()
    for kw, code in NAME_MAP:
        if kw.lower() in nl:
            p = prod_by_code(code)
            if p:
                return p
    return None


m = json.load(open(MP, encoding='utf-8')) if os.path.exists(MP) else {}
for pid in sys.argv[1:]:
    try:
        d = requests.get(f"https://snkrdunk.com/v1/apparels/{pid}", headers=h, timeout=8).json()
    except Exception as e:
        print(f"  {pid}: 取得失敗 {e}"); continue
    pn = d.get('productNumber') or ''
    name = d.get('localizedName') or d.get('name') or ''
    color = d.get('colorLocalizedName') or ''
    # BOX以外(カートン/サプライ/プロモ)は除外
    if 'カートン' in color or any(k in name.lower() for k in ['carton', 'playmat', 'sleeve', 'storage', 'collection -', 'プレミアムカードコレクション', 'ストレージ', 'スリーブ']):
        print(f"  {pid}: BOX以外スキップ ({color}/{name[:24]})"); continue
    prod = classify(pn, name)
    if not prod:
        print(f"  {pid}: 弾判定不可 pn={pn!r} ({name[:30]})"); continue
    pts = requests.get(f"https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId=0",
                       headers=h, timeout=8).json().get('points', [])
    json.dump({"id": str(pid), "product": prod, "points": pts},
              open(os.path.join(OUT, f"{pid}.json"), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    m[prod] = str(pid)
    print(f"  +{pid} -> {prod[:34]} ({len(pts)}pts, {color})")

json.dump(m, open(MP, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
missing = set(SET_MAP.values()) - set(m.keys())
print(f"\nマッピング {len(m)}/23。未取得 {len(missing)}件:")
for x in sorted(missing):
    print("   ", x)
