"""既存マッピングの各ワンピBOXについて「1個販売」のグラフだけを取り直す。

salesChartOptionId=0 は複数個販売が混ざり価格が崩れる。各商品の sizes から
localizedName=='1個' のIDを探し、それを salesChartOptionId に使って取得する。
"""
import requests, json, os, time
h = {'User-Agent': 'Mozilla/5.0'}
ROOT = os.path.dirname(os.path.dirname(__file__))
OUT = os.path.join(ROOT, 'data', 'snkrdunk_op')
MP = os.path.join(OUT, 'product_mapping_op.json')

m = json.load(open(MP, encoding='utf-8'))


def one_unit_option(pid):
    """sizes から「1個」のIDを返す。無ければ salesChartOption 先頭。"""
    d = requests.get(f"https://snkrdunk.com/v1/apparels/{pid}", headers=h, timeout=8).json()
    for s in d.get('sizes', []):
        if s.get('localizedName') == '1個':
            return s['id']
    sc = requests.get(f"https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId=0",
                      headers=h, timeout=8).json()
    opts = sc.get('salesChartOption', [])
    for o in opts:
        if o.get('localizedName') == '1個':
            return o['id']
    return opts[0]['id'] if opts else 0


for prod, pid in sorted(m.items(), key=lambda x: x[0]):
    try:
        oid = one_unit_option(pid)
        pts = requests.get(
            f"https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId={oid}",
            headers=h, timeout=8).json().get('points', [])
        json.dump({"id": str(pid), "product": prod, "salesChartOptionId": oid, "points": pts},
                  open(os.path.join(OUT, f"{pid}.json"), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=2)
        v = [p[1] for p in pts]
        rng = f"{min(v):,}〜{max(v):,}" if v else "空"
        print(f"  {pid} 1個(oid={oid}): {len(pts)}点 {rng}  {prod[:26]}", flush=True)
        time.sleep(0.15)
    except Exception as e:
        print(f"  {pid}: 失敗 {e}", flush=True)

print("完了: 全弾を1個販売グラフで取り直し")
