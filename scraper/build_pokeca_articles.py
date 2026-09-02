"""ポケカ側の記事をデータ差し込みで生成するビルダー。

既存のポケカ記事(手書きHTML)はそのまま残し、ここで作るのは「実データを
差し込む新規記事」だけ。ワンピ側の build_onepiece_articles.py と同じ考え方で、
BOX買取価格・値動きテーブルをプレースホルダで埋めるため、CI で毎回再生成
すれば数値が古くならない。

外枠(CSS/nav/footer)は既存記事 SHELL_SOURCE から実行時に抽出する。
デザインを既存記事側で変更すれば、ここで生成する記事にも自動で追従する。

カード相場は扱わない(ポケカ側は既存記事が担当)。本ビルダーが差し込むのは
当サイトが最大9店舗から自動取得している BOX 買取の実データのみ。
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = ROOT / "data" / "history"
HISTORY_OP_DIR = ROOT / "data" / "history_op"
ART_DIR = ROOT
SHELL_SOURCE = ROOT / "price-pattern-guide.html"
BASE = "https://pokeca-box-hikaku.com"

# 値動き集計の既定期間(日)。履歴がこれより短ければ全期間を使う。
CHANGE_WINDOW_DAYS = 60
# ランキングに載せる上位件数(ポケカは商品数が多いため絞る)
RANKING_LIMIT = 20

# 既存のポケカ記事CSSに無いクラスだけ補う。テーブルは既存の .data-table を
# 使うのでここでは定義しない(デザインは既存記事側の変更に追従させる)。
EXTRA_CSS = """
.hero{margin-bottom:24px;padding:22px;background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-radius:12px;border:1px solid #c7d2fe}
.stat-label{font-size:11px;color:#4338ca;font-weight:700;letter-spacing:.5px}
.stat-big{font-size:30px;font-weight:800;color:#4338ca;line-height:1.2;margin:4px 0 12px}
.stat-sub{font-size:12px;color:#4f46e5;line-height:1.7}
.callout{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin:14px 0;font-size:13px}
"""


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _shell() -> dict:
    """既存記事から外枠(CSS/nav/footer/head内のlink・script)を抜き出す。"""
    h = SHELL_SOURCE.read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", h, re.S)
    nav = re.search(r'(<nav class="article-nav">.*?</nav>)', h, re.S)
    ft = re.search(r'(<div class="ft">.*?</div>)', h, re.S)
    head = h[: h.find("</head>")]
    return {
        "css": css.group(1) if css else "",
        "nav": nav.group(1) if nav else "",
        "ft": ft.group(1) if ft else "",
        "links": "\n".join(l for l in re.findall(r"<link[^>]*>", head)
                           if "canonical" not in l),
        "scripts": "\n".join(re.findall(r"<script[^>]*src=[^>]*></script>", h)),
    }


# ---------------------------------------------------------------- データ取得

def _load_history(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["name"]: r.get("max_price", 0) for r in data}


def _history_at(directory: Path, days_ago: int):
    """days_ago 日前に最も近い履歴を (Path, {name: max_price}) で返す。"""
    files = sorted(directory.glob("*.json"))
    if not files:
        return None, {}
    latest = date.fromisoformat(files[-1].stem)
    target = latest - timedelta(days=days_ago)
    pick = files[0]
    for f in files:
        try:
            if date.fromisoformat(f.stem) <= target:
                pick = f
        except ValueError:
            continue
    return pick, _load_history(pick)


def _change_summary(directory: Path, days: int, base: list | None = None) -> dict:
    """指定期間の値動きを集計する。base を渡すと対象商品を固定できる。"""
    files = sorted(directory.glob("*.json"))
    if len(files) < 2:
        return {}
    old_f, old = _history_at(directory, days)
    now_f, now = _history_at(directory, 0)
    if base is None:
        keys = [n for n in old if old[n] > 0 and now.get(n, 0) > 0]
    else:
        keys = [n for n in base if old.get(n, 0) > 0 and now.get(n, 0) > 0]
    if not keys:
        return {}
    rows = [{"name": n, "old": old[n], "new": now[n],
             "pct": (now[n] - old[n]) / old[n] * 100} for n in keys]
    rows.sort(key=lambda r: -r["pct"])
    up = sum(1 for r in rows if r["pct"] > 1)
    down = sum(1 for r in rows if r["pct"] < -1)
    d0 = date.fromisoformat(old_f.stem)
    d1 = date.fromisoformat(now_f.stem)
    return {
        "rows": rows, "n": len(rows), "up": up, "down": down,
        "flat": len(rows) - up - down,
        "avg": sum(r["pct"] for r in rows) / len(rows),
        "days": (d1 - d0).days,
        "period": (f"{d0.year}年{d0.month}月{d0.day}日〜{d1.month}月{d1.day}日"
                   f"({(d1 - d0).days}日間)"),
        "keys": keys,
    }


def _full_span_days(directory: Path) -> int:
    files = sorted(directory.glob("*.json"))
    if len(files) < 2:
        return 0
    return (date.fromisoformat(files[-1].stem) - date.fromisoformat(files[0].stem)).days


def _change_table(rows: list, limit: int = 0) -> str:
    shown = rows[:limit] if limit else rows
    body = ""
    for r in shown:
        cls = ""
        if r["pct"] > 1:
            cls = ' style="color:#15803d;font-weight:700"'
        elif r["pct"] < -1:
            cls = ' style="color:#b91c1c;font-weight:700"'
        body += (f'<tr><td>{_esc(r["name"])}</td>'
                 f'<td class="num">¥{r["old"]:,}</td>'
                 f'<td class="num">¥{r["new"]:,}</td>'
                 f'<td class="num"{cls}>{r["pct"]:+.1f}%</td></tr>')
    return ('<table class="data-table"><thead><tr><th>BOX</th>'
            '<th style="text-align:right">期間はじめ</th>'
            '<th style="text-align:right">最新</th>'
            '<th style="text-align:right">変化率</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


# 経過月数を区切る幅(月)
AGE_BUCKET_MONTHS = 6


def _age_multiple_rows() -> list:
    """発売からの経過月数ごとに「現在の最高買取 ÷ 定価」の分布を返す。

    対象は現在買取価格が付いている商品のみ。買取掲載が終わった商品は
    含まれないため、生存バイアスがある点は記事側で明示する。
    """
    import sys
    sys.path.insert(0, str(ROOT))
    from scraper.matcher import MASTER_PRODUCTS

    files = sorted(HISTORY_DIR.glob("*.json"))
    if not files:
        return []
    now = _load_history(files[-1])
    latest = date.fromisoformat(files[-1].stem)

    buckets: dict[int, list] = {}
    for p in MASTER_PRODUCTS:
        price = now.get(p.name, 0)
        retail = getattr(p, "retail_price", 0) or 0
        rel = getattr(p, "release_date", None)
        if price <= 0 or retail <= 0 or not rel:
            continue
        try:
            months = (latest - date.fromisoformat(str(rel)[:10])).days / 30.44
        except ValueError:
            continue
        if months < 0:
            continue
        key = int(months // AGE_BUCKET_MONTHS) * AGE_BUCKET_MONTHS
        buckets.setdefault(key, []).append(price / retail)

    rows = []
    for key in sorted(buckets):
        vals = sorted(buckets[key])
        if len(vals) < 2:  # 1件だけの区間は個別商品の値そのものになるため除く
            continue
        rows.append({
            "from": key, "to": key + AGE_BUCKET_MONTHS, "n": len(vals),
            "avg": sum(vals) / len(vals),
            "med": vals[len(vals) // 2],
        })
    return rows


def _age_multiple_table(rows: list) -> str:
    if not rows:
        return ""
    peak = max(rows, key=lambda r: r["med"])
    body = ""
    for r in rows:
        cls = ' class="up"' if r is peak else ""
        body += (f'<tr{cls}><td>{r["from"]}〜{r["to"]}ヶ月</td>'
                 f'<td class="num">{r["n"]}</td>'
                 f'<td class="num">{r["avg"]:.2f}倍</td>'
                 f'<td class="num">{r["med"]:.2f}倍</td></tr>')
    return ('<table class="data-table"><thead><tr><th>発売からの経過</th>'
            '<th style="text-align:right">対象数</th>'
            '<th style="text-align:right">平均</th>'
            '<th style="text-align:right">中央値</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


# 店舗間の価格差を集計する対象条件(この店数以上が掲載している商品のみ)
GAP_MIN_SHOPS = 4


def _shop_gap_rows() -> dict:
    """同一商品の店舗間価格差を集計する。

    最新の履歴から、GAP_MIN_SHOPS 店以上が価格を出している商品について
    最高値・最安値・差額・差率を出す。あわせて「最高値を出した店」の
    偏りも数える(特定の1店に集中しているかを見るため)。
    """
    import statistics
    from collections import Counter
    files = sorted(HISTORY_DIR.glob("*.json"))
    if not files:
        return {}
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    rows, best, appear = [], Counter(), Counter()
    for r in data:
        prices = {k: v for k, v in (r.get("prices") or {}).items() if v > 0}
        if len(prices) < GAP_MIN_SHOPS:
            continue
        mx, mn = max(prices.values()), min(prices.values())
        for k, v in prices.items():
            appear[k] += 1
            if v == mx:
                best[k] += 1
        rows.append({"name": r["name"], "shops": len(prices), "max": mx, "min": mn,
                     "gap": mx - mn, "pct": (mx - mn) / mn * 100 if mn else 0})
    if not rows:
        return {}
    rows.sort(key=lambda r: -r["pct"])
    return {
        "rows": rows, "n": len(rows),
        "shops": len(appear),
        "med_pct": statistics.median([r["pct"] for r in rows]),
        "med_gap": statistics.median([r["gap"] for r in rows]),
        "max_share": max(best.values()) / len(rows) * 100 if best else 0,
        "date": files[-1].stem,
    }


def _shop_gap_table(rows: list, limit: int = 10) -> str:
    body = ""
    for r in rows[:limit]:
        body += (f'<tr><td>{_esc(r["name"])}</td>'
                 f'<td class="num">{r["shops"]}店</td>'
                 f'<td class="num">¥{r["max"]:,}</td>'
                 f'<td class="num">¥{r["min"]:,}</td>'
                 f'<td class="num" style="color:#b91c1c;font-weight:700">'
                 f'¥{r["gap"]:,}</td></tr>')
    return ('<table class="data-table"><thead><tr><th>BOX</th>'
            '<th style="text-align:right">掲載店</th>'
            '<th style="text-align:right">最高値</th>'
            '<th style="text-align:right">最安値</th>'
            '<th style="text-align:right">差額</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _kougaku_rows() -> list:
    """商品ごとの最高買取・定価比・掲載店舗数を、買取の高い順に返す。"""
    from scraper.matcher import MASTER_PRODUCTS
    retail = {p.name: p.retail_price for p in MASTER_PRODUCTS}
    files = sorted(HISTORY_DIR.glob("*.json"))
    if not files:
        return []
    data = json.loads(files[-1].read_text(encoding="utf-8"))
    rows = []
    for r in data:
        vals = [v for v in r.get("prices", {}).values() if v > 0]
        if not vals:
            continue
        mx = max(vals)
        rt = retail.get(r["name"], 0)
        rows.append({"name": r["name"], "retail": rt, "max": mx,
                     "mult": mx / rt if rt else 0, "shops": len(vals)})
    rows.sort(key=lambda r: -r["max"])
    return rows


def _kougaku_table(rows: list, limit: int = 0) -> str:
    body = ""
    for i, r in enumerate(rows if not limit else rows[:limit], 1):
        cls = ' class="up"' if i == 1 else ""
        mult = f'{r["mult"]:.1f}倍' if r["mult"] else "—"
        retail = f'¥{r["retail"]:,}' if r["retail"] else "—"
        body += (f'<tr{cls}><td>{i}位</td><td>{_esc(r["name"])}</td>'
                 f'<td class="num">{retail}</td>'
                 f'<td class="num">¥{r["max"]:,}</td>'
                 f'<td class="num">{mult}</td>'
                 f'<td class="num">{r["shops"]}店</td></tr>')
    return ('<table class="data-table"><thead><tr><th>順位</th><th>商品</th>'
            '<th class="num">定価</th><th class="num">最高買取</th>'
            '<th class="num">定価比</th><th class="num">掲載店舗</th></tr></thead>'
            f'<tbody>{body}</tbody></table>')


def _placeholders(text: str) -> str:
    """記事テキストの {{...}} を実データで置換する。"""
    if "{{" not in text:
        return text

    span = _full_span_days(HISTORY_DIR)
    long_agg = _change_summary(HISTORY_DIR, span) if span else {}
    # 短期は長期と同じ商品セットに固定する(対象数が変わると比較が成立しない)
    short_agg = _change_summary(
        HISTORY_DIR, CHANGE_WINDOW_DAYS, long_agg.get("keys")) if long_agg else {}

    for key, agg in (("LONG", long_agg), ("SHORT", short_agg)):
        if not agg:
            continue
        text = text.replace(f"{{{{PK_{key}_PERIOD}}}}", agg["period"])
        text = text.replace(f"{{{{PK_{key}_DAYS}}}}", str(agg["days"]))
        text = text.replace(f"{{{{PK_{key}_UP}}}}", str(agg["up"]))
        text = text.replace(f"{{{{PK_{key}_DOWN}}}}", str(agg["down"]))
        text = text.replace(f"{{{{PK_{key}_FLAT}}}}", str(agg["flat"]))
        text = text.replace(f"{{{{PK_{key}_N}}}}", str(agg["n"]))
        text = text.replace(f"{{{{PK_{key}_AVG}}}}", f"{agg['avg']:+.1f}%")
        if agg["rows"]:
            text = text.replace(f"{{{{PK_{key}_TOP_NAME}}}}", agg["rows"][0]["name"])
            text = text.replace(f"{{{{PK_{key}_TOP_PCT}}}}",
                                f"{agg['rows'][0]['pct']:+.1f}%")
            text = text.replace(f"{{{{PK_{key}_BOTTOM_NAME}}}}", agg["rows"][-1]["name"])
            text = text.replace(f"{{{{PK_{key}_BOTTOM_PCT}}}}",
                                f"{agg['rows'][-1]['pct']:+.1f}%")

    if "{{PK_CHANGE_TABLE_UP}}" in text and short_agg:
        text = text.replace("{{PK_CHANGE_TABLE_UP}}",
                            _change_table(short_agg["rows"], RANKING_LIMIT // 2))
    if "{{PK_CHANGE_TABLE_DOWN}}" in text and short_agg:
        text = text.replace("{{PK_CHANGE_TABLE_DOWN}}",
                            _change_table(short_agg["rows"][::-1], RANKING_LIMIT // 2))
    if "{{PK_LONG_TABLE}}" in text and long_agg:
        text = text.replace("{{PK_LONG_TABLE}}", _change_table(long_agg["rows"]))

    # ワンピ側との比較。ワンピの履歴は短いため、ワンピの全期間に両者を揃える。
    # {{OP_*}} がワンピ、{{PKM_*}} が同じ期間で再集計したポケカ。
    if "{{OP_" in text or "{{PKM_" in text:
        op = _change_summary(HISTORY_OP_DIR, _full_span_days(HISTORY_OP_DIR))
        if op:
            pkm = _change_summary(HISTORY_DIR, op["days"], long_agg.get("keys"))
            if pkm:
                text = text.replace("{{PKM_DAYS}}", str(pkm["days"]))
                text = text.replace("{{PKM_UP}}", str(pkm["up"]))
                text = text.replace("{{PKM_DOWN}}", str(pkm["down"]))
                text = text.replace("{{PKM_FLAT}}", str(pkm["flat"]))
                text = text.replace("{{PKM_N}}", str(pkm["n"]))
                text = text.replace("{{PKM_AVG}}", f"{pkm['avg']:+.1f}%")
                text = text.replace("{{PKM_PERIOD}}", pkm["period"])
            text = text.replace("{{OP_DAYS}}", str(op["days"]))
            text = text.replace("{{OP_UP}}", str(op["up"]))
            text = text.replace("{{OP_DOWN}}", str(op["down"]))
            text = text.replace("{{OP_FLAT}}", str(op["flat"]))
            text = text.replace("{{OP_N}}", str(op["n"]))
            text = text.replace("{{OP_AVG}}", f"{op['avg']:+.1f}%")
            text = text.replace("{{OP_PERIOD}}", op["period"])

    if "{{PK_AGE" in text:
        age = _age_multiple_rows()
        text = text.replace("{{PK_AGE_TABLE}}", _age_multiple_table(age))
        if age:
            # 初期ピーク=3年以内での最大、ボトム=初期ピーク後〜3年以内での最小。
            # 単に全体の最大を取ると「最も古い区間」を拾ってしまうため区切る。
            early = [r for r in age if r["to"] <= 36]
            peak = max(early, key=lambda r: r["med"]) if early else age[0]
            after = [r for r in early if r["from"] > peak["from"]]
            bottom = min(after, key=lambda r: r["med"]) if after else peak
            first, last = age[0], age[-1]
            for tag, r in (("FIRST", first), ("PEAK", peak),
                           ("BOTTOM", bottom), ("LAST", last)):
                text = text.replace(f"{{{{PK_AGE_{tag}_RANGE}}}}",
                                    f'{r["from"]}〜{r["to"]}ヶ月')
                text = text.replace(f"{{{{PK_AGE_{tag}_MED}}}}", f'{r["med"]:.2f}倍')
                text = text.replace(f"{{{{PK_AGE_{tag}_AVG}}}}", f'{r["avg"]:.2f}倍')
            text = text.replace("{{PK_AGE_N}}", str(sum(r["n"] for r in age)))
            text = text.replace("{{PK_AGE_PEAK_YEARS}}", f'{peak["from"] / 12:.1f}')
            text = text.replace("{{PK_AGE_LAST_YEARS}}", f'{last["from"] / 12:.0f}')

    if "{{PK_GAP" in text:
        gap = _shop_gap_rows()
        if gap:
            text = text.replace("{{PK_GAP_TABLE}}", _shop_gap_table(gap["rows"]))
            text = text.replace("{{PK_GAP_N}}", str(gap["n"]))
            text = text.replace("{{PK_GAP_SHOPS}}", str(gap["shops"]))
            text = text.replace("{{PK_GAP_MIN_SHOPS}}", str(GAP_MIN_SHOPS))
            text = text.replace("{{PK_GAP_MED_PCT}}", f'{gap["med_pct"]:.0f}%')
            text = text.replace("{{PK_GAP_MED_YEN}}", f'¥{int(gap["med_gap"]):,}')
            text = text.replace("{{PK_GAP_MAX_SHARE}}", f'{gap["max_share"]:.0f}%')
            top = gap["rows"][0]
            text = text.replace("{{PK_GAP_MAX_NAME}}", top["name"])
            text = text.replace("{{PK_GAP_MAX_PCT}}", f'{top["pct"]:.0f}%')
            text = text.replace("{{PK_GAP_MAX_YEN}}", f'¥{top["gap"]:,}')
            byyen = sorted(gap["rows"], key=lambda r: -r["gap"])[0]
            text = text.replace("{{PK_GAP_MAXYEN_NAME}}", byyen["name"])
            text = text.replace("{{PK_GAP_MAXYEN_YEN}}", f'¥{byyen["gap"]:,}')

    rows = _kougaku_rows()
    if rows and "{{PK_KG_" in text:
        text = text.replace("{{PK_KG_TABLE}}", _kougaku_table(rows))
        text = text.replace("{{PK_KG_TOP20}}", _kougaku_table(rows, 20))
        text = text.replace("{{PK_KG_N}}", str(len(rows)))
        for i in range(1, 6):
            if i > len(rows):
                break
            r = rows[i - 1]
            text = text.replace("{{PK_KG_TOP%d_NAME}}" % i, r["name"])
            text = text.replace("{{PK_KG_TOP%d_PRICE}}" % i, f'¥{r["max"]:,}')
            text = text.replace("{{PK_KG_TOP%d_MULT}}" % i, f'{r["mult"]:.1f}倍')
            text = text.replace("{{PK_KG_TOP%d_SHOPS}}" % i, f'{r["shops"]}店')
        ss = [r for r in rows[:10] if r["name"].startswith("S&S")]
        text = text.replace("{{PK_KG_SS_IN_TOP10}}", str(len(ss)))
        bymult = sorted(rows, key=lambda r: -r["mult"])[0]
        text = text.replace("{{PK_KG_MULT_NAME}}", bymult["name"])
        text = text.replace("{{PK_KG_MULT_VAL}}", f'{bymult["mult"]:.1f}倍')
        top10_shops = sum(r["shops"] for r in rows[:10]) / 10
        bottom = rows[-10:]
        low_shops = sum(r["shops"] for r in bottom) / len(bottom)
        text = text.replace("{{PK_KG_TOP10_SHOPS_AVG}}", f'{top10_shops:.1f}店')
        text = text.replace("{{PK_KG_LOW10_SHOPS_AVG}}", f'{low_shops:.1f}店')
        under = [r for r in rows if 0 < r["mult"] < 1]
        text = text.replace("{{PK_KG_UNDER_N}}", str(len(under)))
    return text


# ---------------------------------------------------------------- 記事データ

POKECA_ARTICLES: list[dict] = [
    {'slug': 'kougaku-box-ranking',
     'crumb': 'ポケカ高額BOX買取ランキング',
     'date': '2026-09-02',
     'date_jp': '2026年9月2日',
     'title': 'ポケカ 高額BOX買取ランキング｜全{{PK_KG_N}}商品の最高買取と定価比',
     'h1': 'ポケカ 高額BOX買取ランキング｜全{{PK_KG_N}}商品を最高買取の順に並べた',
     'meta_desc': 'ポケモンカードの未開封BOX買取価格を、当サイトが最大10店舗から毎日自動収集した実データで高い順にランキング。1位は{{PK_KG_TOP1_NAME}}の{{PK_KG_TOP1_PRICE}}({{PK_KG_TOP1_MULT}})です。TOP10のうち{{PK_KG_SS_IN_TOP10}}件をS&S世代が占め、高額BOXほど買取を掲載する店舗が減るという構造まで、全{{PK_KG_N}}商品の実測値で解説します。',
     'og_title': 'ポケカ 高額BOX買取ランキング｜全{{PK_KG_N}}商品',
     'og_desc': '1位は{{PK_KG_TOP1_NAME}} {{PK_KG_TOP1_PRICE}}({{PK_KG_TOP1_MULT}})。最大10店舗の実データで全{{PK_KG_N}}商品を毎日更新。',
     'meta_line': 'ポケカ未開封BOXの最高買取ランキング(当サイト実データ・毎日更新)',
     'hero_label': 'BOX最高買取ランキング 1位',
     'hero_big': '{{PK_KG_TOP1_NAME}} {{PK_KG_TOP1_PRICE}}',
     'hero_sub': '定価比{{PK_KG_TOP1_MULT}}。2位 {{PK_KG_TOP2_NAME}} {{PK_KG_TOP2_PRICE}}({{PK_KG_TOP2_MULT}})、3位 {{PK_KG_TOP3_NAME}} '
                 '{{PK_KG_TOP3_PRICE}}({{PK_KG_TOP3_MULT}})。全{{PK_KG_N}}商品の最高買取・定価比・掲載店舗数を毎日更新しています。',
     'disclaimer': '本記事の買取価格は、当サイトが最大10店舗から自動取得した実データです。表示は取得時点のスナップショットで、相場は需給・再販・各店の在庫状況により日々変動します。金額は目安であり、特定の買取価格を保証するものではありません。定価はメーカー希望小売価格(税込)で、実売価格とは異なります。掲載店舗数は当サイトが価格を取得できた店舗の数で、その商品を扱う店の総数ではありません。売買の判断はご自身の責任で行ってください。',
     'related': '<li><a href="index.html">ポケカBOX買取価格比較トップ</a> — 全商品の店舗別価格を毎日更新</li>\n'
                '<li><a href="ranking.html">週間価格変化ランキング</a> — 直近で値上がり・値下がりしたBOX</li>\n'
                '<li><a href="box-age-multiple.html">発売から何年で何倍になるか</a> — 経過月数と定価比の関係</li>\n'
                '<li><a href="shop-price-gap.html">同じBOXでも店で買取価格はどれだけ違うか</a> — 店舗差の実測</li>\n'
                '<li><a href="ss-box-list.html">S&amp;S全BOX一覧</a> — 上位を独占する絶版世代の一覧</li>',
     'body': '<p>ポケモンカードの未開封BOXは、商品によって買取価格が<strong>数十倍</strong>開きます。同じ定価5,000円前後の拡張パックでも、1万円に届かないものから<strong>{{PK_KG_TOP1_PRICE}}</strong>になるものまであるのが実情です。本記事では、当サイトが最大10店舗から毎日自動収集している買取データをもとに、<strong>全{{PK_KG_N}}商品を最高買取価格の高い順にランキング</strong>します。</p>\n'
             '\n'
             '<h2>高額BOX TOP20</h2>\n'
             '<p>各商品の<strong>最高買取価格</strong>(当サイト掲載店舗のうち最も高い店の価格)、<strong>定価に対する倍率</strong>、そして<strong>買取価格を掲載している店舗数</strong>を並べたものです。</p>\n'
             '{{PK_KG_TOP20}}\n'
             '<div class="callout"><strong>掲載店舗の列に注目してください。</strong> '
             '高額BOXほど買取を出している店が少なくなります。TOP10の平均が{{PK_KG_TOP10_SHOPS_AVG}}なのに対し、下位10商品は{{PK_KG_LOW10_SHOPS_AVG}}です。<strong>高く売れる商品ほど、売り先が限られる</strong>という構造があります。</div>\n'
             '\n'
             '<h2>TOP10はS&amp;S世代がほぼ独占している</h2>\n'
             '<p>TOP10のうち<strong>{{PK_KG_SS_IN_TOP10}}件</strong>がS&amp;S(ソード&amp;シールド)シリーズです。2019年から2022年に発売された、すでに再販が止まっている世代にあたります。</p>\n'
             '<p>1位の<strong>{{PK_KG_TOP1_NAME}}</strong>は{{PK_KG_TOP1_PRICE}}、定価比{{PK_KG_TOP1_MULT}}という水準です。定価比で見ても全商品中トップで、{{PK_KG_MULT_NAME}}の{{PK_KG_MULT_VAL}}が最高倍率になっています。</p>\n'
             '<div class="callout"><strong>読み違えやすい点:</strong> 「新しい弾ほど高い」わけでも「古いほど高い」わけでもありません。同じS&amp;S世代でも上位と下位で10倍以上の差があります。決めているのは<strong>その弾の看板カードがどこまで高くなれるか</strong>で、これは当サイトが<a '
             'href="box-price-trend.html">値動きレポート</a>や各弾の当たりカードガイドで繰り返し確認している構造です。</p></div>\n'
             '\n'
             '<h2>定価割れしている商品はあるか</h2>\n'
             '<p>現時点で定価を下回っている商品は<strong>{{PK_KG_UNDER_N}}件</strong>です。ポケカの未開封BOXは、買取価格が付いている限り定価を割りにくい商品群だと言えます。</p>\n'
             '<p>ただしこれは<strong>買取掲載が続いている商品だけを見た結果</strong>である点に注意が必要です。買い取ってもらえなくなった商品はこの表から消えるため、生き残りだけを見て「ポケカBOXは値下がりしない」と結論づけることはできません。経過年数との関係は <a href="box-age-multiple.html">発売から何年で何倍になるか</a> '
             'で詳しく扱っています。</p>\n'
             '\n'
             '<h2>全{{PK_KG_N}}商品の完全ランキング</h2>\n'
             '<p>掲載しているすべての商品を、最高買取の高い順に並べたものです。</p>\n'
             '{{PK_KG_TABLE}}\n'
             '\n'
             '<h2>売るときに見るべきポイント</h2>\n'
             '<ul>\n'
             '<li><strong>店舗差を必ず確認する</strong>: 同じBOXでも店によって価格が違い、最高値の店は商品ごとに入れ替わります。詳しくは <a href="shop-price-gap.html">店舗差の実測記事</a> をご覧ください</li>\n'
             '<li><strong>掲載店舗が少ない商品は急がない</strong>: 上の表で掲載店舗が1〜2店の商品は、その店の在庫状況ひとつで価格が動きます。1店だけの価格を相場と見なさないでください</li>\n'
             '<li><strong>最新値はトップページで</strong>: 本記事の数値は毎日自動更新されますが、店頭に持ち込む前に <a href="index.html">買取価格比較トップ</a> で最終確認をおすすめします</li>\n'
             '</ul>\n',
     'faq': [{'q': 'ポケカで一番高く買い取られているBOXはどれですか？',
              'a': '当サイトが最大10店舗から毎日取得している実データでは、{{PK_KG_TOP1_NAME}}が{{PK_KG_TOP1_PRICE}}で1位です。定価に対して{{PK_KG_TOP1_MULT}}にあたります。2位は{{PK_KG_TOP2_NAME}}の{{PK_KG_TOP2_PRICE}}、3位は{{PK_KG_TOP3_NAME}}の{{PK_KG_TOP3_PRICE}}です。'},
             {'q': '高額BOXはどこの店でも買い取ってもらえますか？',
              'a': 'いいえ。当サイトのデータでは、TOP10の平均掲載店舗数が{{PK_KG_TOP10_SHOPS_AVG}}なのに対し、下位10商品は{{PK_KG_LOW10_SHOPS_AVG}}です。高額BOXほど買取を出している店が少なく、売り先が限られます。1店だけの価格を相場と見なさないよう注意してください。'},
             {'q': '新しい弾のほうが高く売れますか？', 'a': 'そうとは限りません。上位は再販が止まったS&Sシリーズ(2019〜2022年発売)が中心で、TOP10のうち{{PK_KG_SS_IN_TOP10}}件を占めています。ただし同じS&S世代でも上位と下位で10倍以上の差があり、世代だけでは決まりません。'},
             {'q': '定価より安くなっているBOXはありますか？', 'a': '現時点で定価を下回っているのは{{PK_KG_UNDER_N}}件です。ただしこれは買取掲載が続いている商品だけを見た数字で、買い取ってもらえなくなった商品は集計から外れています。生存バイアスがある点に注意してください。'}]},
    {
        "slug": "box-price-trend",
        "crumb": "ポケカBOX相場の値動きレポート",
        "date": "2026-08-26",
        "date_jp": "2026年8月26日",
        "title": "ポケカBOX相場の値動きレポート｜実データで見る上がる弾・下がる弾と、期間で結論が変わる理由",
        "h1": "ポケカBOX相場の値動きレポート｜実データで見る上がる弾・下がる弾と、期間で結論が変わる理由",
        "meta_desc": "当サイトが最大9店舗から毎日自動取得しているポケモンカードのBOX買取実データで、全弾の値動きを横断集計。長期({{PK_LONG_DAYS}}日)では上昇{{PK_LONG_UP}}弾・平均{{PK_LONG_AVG}}である一方、同じ{{PK_LONG_N}}商品を直近{{PKM_DAYS}}日で切り取ると平均{{PKM_AVG}}と結論が逆になります。上がる弾・下がる弾の傾向、ワンピースカードとの同期間比較、買い時・売り時の考え方までを実測値で整理します。",
        "og_title": "ポケカBOX相場の値動きレポート｜上がる弾・下がる弾を実データで",
        "og_desc": "最大9店舗のBOX買取実データで全弾の値動きを横断集計。長期は平均{{PK_LONG_AVG}}、直近は{{PKM_AVG}}。期間で結論が変わる理由と買い時・売り時の考え方。",
        "meta_line": "全弾のBOX買取値動き実測・期間別の比較",
        "hero_label": "ポケカBOX相場 値動きレポート({{PK_LONG_PERIOD}})",
        "hero_big": "長期 平均{{PK_LONG_AVG}}",
        "hero_sub": "当サイトが最大9店舗から毎日自動取得しているBOX買取実データで、全{{PK_LONG_N}}商品の値動きを横断集計しました。長期では上昇{{PK_LONG_UP}}・下落{{PK_LONG_DOWN}}ですが、同じ商品を直近{{PKM_DAYS}}日で切り取ると平均{{PKM_AVG}}と様相が変わります。",
        "disclaimer": "本記事のBOX買取価格は、当サイトが最大9店舗から自動取得した実データです。各商品の「最高買取価格」(掲載店舗のうち最も高い店の価格)を用いており、店舗ごとの価格差や掲載店舗の増減による変動を含みます。集計対象は<strong>起点の日に価格が存在した商品</strong>に固定しています(期間ごとに対象商品が変わると上昇・下落の比較が成立しないため)。値動きの<strong>理由</strong>については、再販の実施状況などを網羅的に確認できないため断定していません。相場は今後も変動し、本記事の傾向が継続することを保証するものではありません。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="index.html">ポケカBOX買取価格比較トップ</a> — 全BOXの買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="ranking.html">週間価格変化ランキング</a> — 直近の値上がり・値下がりを毎日自動更新</li>\n'
                   '<li><a href="price-pattern-guide.html">BOX買取価格の5段階パターン</a> — 発売から絶版までの相場推移フェーズ解説</li>\n'
                   '<li><a href="sv-box-list.html">SV全BOX一覧</a> / <a href="mega-box-list.html">MEGA全BOX一覧</a> — シリーズ別の買取価格一覧</li>\n'
                   '<li><a href="/onepiece/box-price-pattern.html">ワンピBOX相場の値動きパターン</a> — 同じ手法でワンピースカードを分析した記事</li>\n'
                   '<li><a href="kaitori-tips.html">BOX買取のコツ</a> — 高く売るための実践ポイント</li>',
        "body": """<p>「ポケカのBOXは今、上がっているのか下がっているのか」——この問いに、<strong>当サイトが最大9店舗から毎日自動取得しているBOX買取の実データ</strong>で答えます。</p>

<p>結論から言うと、<strong>答えは「どの期間で見るか」で変わります</strong>。同じ商品を対象にしても、長期と直近では逆の結論が出ます。本記事ではその両方を示したうえで、上がる弾・下がる弾の傾向まで整理します。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・長期({{PK_LONG_DAYS}}日)では上昇{{PK_LONG_UP}}・下落{{PK_LONG_DOWN}}、平均<strong>{{PK_LONG_AVG}}</strong><br>
・<strong>同じ{{PK_LONG_N}}商品</strong>を直近{{PKM_DAYS}}日で切り取ると上昇{{PKM_UP}}・下落{{PKM_DOWN}}、平均<strong>{{PKM_AVG}}</strong>と逆転<br>
・上がっているのは発売から時間が経ったシリーズ、下げているのは特殊BOXと新シリーズという傾向</div>

<h2>長期の値動き一覧({{PK_LONG_PERIOD}})</h2>
<p>当サイトに価格履歴が蓄積されている全期間での変化率です。対象は起点の日に価格が存在した{{PK_LONG_N}}商品に固定しています。</p>

{{PK_LONG_TABLE}}

<p>最大の上昇は<strong>{{PK_LONG_TOP_NAME}}({{PK_LONG_TOP_PCT}})</strong>、最大の下落は<strong>{{PK_LONG_BOTTOM_NAME}}({{PK_LONG_BOTTOM_PCT}})</strong>でした。全体では上昇{{PK_LONG_UP}}・下落{{PK_LONG_DOWN}}・横ばい{{PK_LONG_FLAT}}、平均{{PK_LONG_AVG}}です。</p>

<h2>発見①｜期間を変えると結論が逆になる</h2>
<p>ここが本記事でもっとも重要な点です。<strong>まったく同じ{{PK_LONG_N}}商品</strong>を、期間だけ変えて集計し直すと次のようになります。</p>

<table class="data-table">
<thead><tr><th>集計期間</th><th style="text-align:right">上昇</th><th style="text-align:right">下落</th><th style="text-align:right">横ばい</th><th style="text-align:right">平均変化率</th></tr></thead>
<tbody>
<tr class="up"><td><strong>長期 {{PK_LONG_DAYS}}日間</strong></td><td class="num">{{PK_LONG_UP}}</td><td class="num">{{PK_LONG_DOWN}}</td><td class="num">{{PK_LONG_FLAT}}</td><td class="num"><strong>{{PK_LONG_AVG}}</strong></td></tr>
<tr><td>中期 {{PK_SHORT_DAYS}}日間</td><td class="num">{{PK_SHORT_UP}}</td><td class="num">{{PK_SHORT_DOWN}}</td><td class="num">{{PK_SHORT_FLAT}}</td><td class="num"><strong>{{PK_SHORT_AVG}}</strong></td></tr>
<tr><td>直近 {{PKM_DAYS}}日間</td><td class="num">{{PKM_UP}}</td><td class="num">{{PKM_DOWN}}</td><td class="num">{{PKM_FLAT}}</td><td class="num"><strong>{{PKM_AVG}}</strong></td></tr>
</tbody>
</table>

<p>長期では大きくプラスですが、直近を切り取るとマイナスに転じています。<strong>商品も集計方法も同じで、違うのは期間だけ</strong>です。</p>

<div class="callout"><strong>これをどう読むか:</strong> 直近の下げは<strong>長期の上昇トレンドの中の調整</strong>とも読めますし、<strong>トレンドの転換点</strong>とも読めます。どちらかを断定できるだけの材料は現時点のデータにはありません。<br><br>
確実に言えるのは、<strong>「ポケカBOXは上がっている/下がっている」という主張は、期間を明示しないと意味をなさない</strong>ということです。相場情報を見るときは、それが何日間の話なのかを必ず確認してください。</div>

<h2>発見②｜上がる弾・下がる弾の傾向</h2>
<h3>直近で上昇している商品</h3>
{{PK_CHANGE_TABLE_UP}}

<h3>直近で下落している商品</h3>
{{PK_CHANGE_TABLE_DOWN}}

<p>並べてみると傾向が見えます。<strong>上昇側は発売から時間が経った拡張パックが中心</strong>で、<strong>下落側には特殊BOXや比較的新しいシリーズが並びます</strong>。</p>

<p>BOX相場は市場に残る<strong>未開封在庫の量</strong>に強く影響されます。発売から時間が経つほど開封が進んで未開封BOXが減り、再販も新しい商品に集中するため、古い弾は価格が下支えされやすくなります。逆に新しい商品は供給が続いている段階なので、相場が緩みやすい局面にあります。</p>

<div class="callout"><strong>注意 — 因果は断定できません:</strong> 個別商品の再販・追加出荷の実施状況を網羅的に確認する手段がないため、「この商品が下がったのは再販のせい」と特定することはできません。上記はあくまで<strong>値動きの傾向と、BOX相場の一般的な構造を突き合わせた整理</strong>です。相場が動くフェーズの考え方は<a href="price-pattern-guide.html">BOX買取価格の5段階パターン</a>で詳しく解説しています。</div>

<h2>発見③｜ワンピースカードでも同じことが起きている</h2>
<p>当サイトは<a href="/onepiece">ワンピースカードのBOX買取価格</a>も同じ方法で毎日取得しています。同じ期間で比較すると、傾向の答え合わせができます。</p>

<table class="data-table">
<thead><tr><th>タイトル</th><th>期間</th><th style="text-align:right">上昇</th><th style="text-align:right">下落</th><th style="text-align:right">平均変化率</th></tr></thead>
<tbody>
<tr class="up"><td><strong>ポケモンカード</strong></td><td>{{PKM_DAYS}}日間</td><td class="num">{{PKM_UP}}</td><td class="num">{{PKM_DOWN}}</td><td class="num"><strong>{{PKM_AVG}}</strong></td></tr>
<tr><td>ワンピースカード</td><td>{{OP_DAYS}}日間(同期間)</td><td class="num">{{OP_UP}}</td><td class="num">{{OP_DOWN}}</td><td class="num"><strong>{{OP_AVG}}</strong></td></tr>
</tbody>
</table>

<p><strong>両タイトルとも同じ方向に動いています。</strong>タイトルをまたいで同時に起きている以上、ポケカ固有の事情というより<strong>トレカ市場全体の地合い</strong>が効いている可能性があります。ワンピース側の詳しい分析は<a href="/onepiece/box-price-pattern.html">ワンピBOX相場の値動きパターン</a>にまとめています。</p>

<h2>実務的な示唆</h2>
<h3>買う場合</h3>
<ul>
<li><strong>新しい商品は焦らない</strong> — 供給が続いている段階では相場が緩みやすく、押し目を待つ判断がしやすくなります。</li>
<li><strong>古い弾は下がりにくいが、その分すでに高い</strong> — 値動きが安定している商品は参入コストも高くなっています。</li>
</ul>

<h3>売る場合</h3>
<ul>
<li><strong>直近の動きは<a href="ranking.html">週間価格変化ランキング</a>で</strong> — 本記事は長めの期間の傾向を見るものです。売る直前の判断は直近の動きも合わせて確認してください。</li>
<li><strong>必ず複数店を比較する</strong> — 本記事の数値は「最高買取価格」です。同じ商品でも店舗差があるため、<a href="index.html">比較トップ</a>で最高値の店を確認してから売却してください。</li>
</ul>

<h2>この分析の限界</h2>
<ul>
<li><strong>最高買取価格ベース</strong> — 掲載店舗の増減や、特定店の値付け変更が数値に影響します。</li>
<li><strong>理由は断定していない</strong> — 再販の実施状況を網羅的に確認できないため、個別商品の値動きの原因は特定できません。本記事は「何が起きたか」の記録です。</li>
<li><strong>対象は起点日に価格があった商品のみ</strong> — 期間中に追加された新商品は集計に含まれません。</li>
<li><strong>傾向は変わり得る</strong> — 本記事の数値は集計時点のものです。最新の順位は<a href="index.html">比較トップ</a>でご確認ください。</li>
</ul>""",
        "faq": [
            {"q": "ポケカのBOX相場は今、上がっていますか？下がっていますか？",
             "a": "期間によって答えが変わります。長期({{PK_LONG_DAYS}}日間)では上昇{{PK_LONG_UP}}・下落{{PK_LONG_DOWN}}で平均{{PK_LONG_AVG}}ですが、まったく同じ{{PK_LONG_N}}商品を直近{{PKM_DAYS}}日間で切り取ると上昇{{PKM_UP}}・下落{{PKM_DOWN}}で平均{{PKM_AVG}}と逆になります。相場情報を見るときは、それが何日間の話なのかを必ず確認してください。"},
            {"q": "どんなBOXが上がりやすいですか？",
             "a": "本記事の集計では、上昇側は発売から時間が経った拡張パックが中心でした。BOX相場は市場に残る未開封在庫の量に強く影響されるため、開封が進んで未開封BOXが減り、再販も新商品に集中する古い弾ほど価格が下支えされやすくなります。ただし個別商品の値動きの原因を断定することはできません。"},
            {"q": "どんなBOXが下がりやすいですか？",
             "a": "集計では特殊BOXや比較的新しいシリーズが下落側に並びました。新しい商品は供給が続いている段階のため相場が緩みやすい局面にあります。相場が動くフェーズの考え方はBOX買取価格の5段階パターンの記事で詳しく解説しています。"},
            {"q": "ワンピースカードの相場とは連動していますか？",
             "a": "同じ期間で集計すると、ポケカが平均{{PKM_AVG}}、ワンピースカードが平均{{OP_AVG}}と同じ方向に動いています。タイトルをまたいで同時に起きている以上、どちらか固有の事情というよりトレカ市場全体の地合いが効いている可能性があります。"},
            {"q": "この記事の数値はいつ時点のものですか？",
             "a": "当サイトが最大9店舗から毎日自動取得しているBOX買取実データをもとに、記事の再生成時点で集計しています。集計期間は本文の各表に明記しています。直近の値動きは週間価格変化ランキング、最新の店舗別価格は比較トップでご確認ください。"},
        ],
    },
    {
        "slug": "box-age-multiple",
        "crumb": "発売から何年で何倍になるか",
        "date": "2026-08-26",
        "date_jp": "2026年8月26日",
        "title": "ポケカBOXは発売から何年で何倍になるか｜経過年数別の定価比を実データで検証",
        "h1": "ポケカBOXは発売から何年で何倍になるか｜経過年数別の定価比を実データで検証",
        "meta_desc": "当サイトが最大9店舗から毎日自動取得しているBOX買取実データで、発売からの経過月数と「現在の買取価格÷定価」の関係を{{PK_AGE_N}}商品ぶん集計。発売直後は約{{PK_AGE_FIRST_MED}}、{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}まで上がった後、{{PK_AGE_BOTTOM_RANGE}}で{{PK_AGE_BOTTOM_MED}}まで下げ、そこから年を追って上昇していくという推移が見えました。買い時の考え方と、この集計に生存バイアスがある点まで正直に整理します。",
        "og_title": "ポケカBOXは発売から何年で何倍になるか｜経過年数別の定価比",
        "og_desc": "BOX買取実データで経過月数と定価比の関係を{{PK_AGE_N}}商品ぶん集計。発売直後{{PK_AGE_FIRST_MED}}→{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}→{{PK_AGE_BOTTOM_RANGE}}で{{PK_AGE_BOTTOM_MED}}という推移。",
        "meta_line": "経過年数別の定価比・買い時の考え方",
        "hero_label": "発売からの経過年数と定価比({{PK_AGE_N}}商品)",
        "hero_big": "{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}",
        "hero_sub": "発売直後は約{{PK_AGE_FIRST_MED}}、{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}に達したあと、{{PK_AGE_BOTTOM_RANGE}}で{{PK_AGE_BOTTOM_MED}}まで下げ、そこから年を追って切り上がっていきます。最も古い{{PK_AGE_LAST_RANGE}}の区間は{{PK_AGE_LAST_MED}}です。",
        "disclaimer": "本記事のBOX買取価格は、当サイトが最大9店舗から自動取得した実データ(各商品の最高買取価格)です。定価比は「現在の最高買取価格 ÷ 定価」で算出しています。<strong>集計対象は現在も買取価格が付いている商品に限られる</strong>ため、買取掲載が終わった商品は含まれません(生存バイアス)。この点は本文でも詳しく触れています。各区間の対象数は少ないものでは数件しかなく、統計的に十分な標本数ではありません。過去の傾向であり、将来同じ推移をたどることを保証するものではありません。売買の判断はご自身の責任で行ってください。",
        "related": '<li><a href="index.html">ポケカBOX買取価格比較トップ</a> — 全BOXの買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="box-price-trend.html">BOX相場の値動きレポート</a> — 期間別の値動きと上がる弾・下がる弾</li>\n'
                   '<li><a href="price-pattern-guide.html">BOX買取価格の5段階パターン</a> — 発売から絶版までの相場推移フェーズ解説</li>\n'
                   '<li><a href="sv-box-list.html">SV全BOX一覧</a> / <a href="ss-box-list.html">S&amp;S全BOX一覧</a> — シリーズ別の買取価格一覧</li>\n'
                   '<li><a href="kaitori-tips.html">BOX買取のコツ</a> — 高く売るための実践ポイント</li>\n'
                   '<li><a href="ranking.html">週間価格変化ランキング</a> — 直近の値上がり・値下がりを毎日自動更新</li>',
        "body": """<p>「ポケカのBOXは寝かせておけば上がる」とよく言われますが、<strong>実際にはどのくらいの期間で、どのくらい上がるのか</strong>。当サイトが最大9店舗から毎日自動取得しているBOX買取の実データで検証しました。</p>

<p>指標は<strong>定価比(現在の最高買取価格 ÷ 定価)</strong>です。発売からの経過月数ごとに{{PK_AGE_N}}商品を集計すると、単純な右肩上がりではない推移が見えてきます。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・発売直後は約{{PK_AGE_FIRST_MED}}。そこから<strong>{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}</strong>まで一度上がる<br>
・ところが<strong>{{PK_AGE_BOTTOM_RANGE}}で{{PK_AGE_BOTTOM_MED}}まで下げる</strong>。ここが調整の谷<br>
・4年目以降は年を追って切り上がり、最も古い{{PK_AGE_LAST_RANGE}}の区間は<strong>{{PK_AGE_LAST_MED}}</strong></div>

<h2>経過月数別の定価比</h2>
<p>発売からの経過月数を6ヶ月刻みで区切り、それぞれの区間に属する商品の定価比を集計しました。<strong>中央値</strong>を併記しているのは、一部の超高額BOXが平均を大きく引き上げるためです(後述)。</p>

{{PK_AGE_TABLE}}

<p>色を付けた行が、発売から3年以内でもっとも定価比が高い区間です。</p>

<h2>発見①｜単純な右肩上がりではない</h2>
<p>「古いBOXほど高い」は大枠では正しいのですが、<strong>発売から3年以内に限ると一度上がって下がる</strong>という動きをしています。</p>

<table class="data-table">
<thead><tr><th>局面</th><th>経過</th><th style="text-align:right">定価比(中央値)</th></tr></thead>
<tbody>
<tr><td>発売直後</td><td>{{PK_AGE_FIRST_RANGE}}</td><td class="num">{{PK_AGE_FIRST_MED}}</td></tr>
<tr class="up"><td><strong>初期ピーク</strong></td><td>{{PK_AGE_PEAK_RANGE}}</td><td class="num"><strong>{{PK_AGE_PEAK_MED}}</strong></td></tr>
<tr><td><strong>調整の谷</strong></td><td>{{PK_AGE_BOTTOM_RANGE}}</td><td class="num"><strong>{{PK_AGE_BOTTOM_MED}}</strong></td></tr>
<tr><td>長期</td><td>{{PK_AGE_LAST_RANGE}}</td><td class="num">{{PK_AGE_LAST_MED}}</td></tr>
</tbody>
</table>

<p>発売直後に{{PK_AGE_FIRST_MED}}、そこから1年ほどで{{PK_AGE_PEAK_MED}}まで上がります。ところが2年目に入ると{{PK_AGE_BOTTOM_MED}}まで下げ、<strong>初期ピークの水準を割り込みます</strong>。</p>

<div class="callout"><strong>考えられる構造:</strong> 発売から1年前後は「新弾としての注目」と「まだ在庫が枯れていない」がせめぎ合う時期で、供給が絞られはじめると価格が伸びます。その後2年目に入ると、次の新弾に話題が移り、再販も行き渡って需要が一巡します。ここが谷です。さらに時間が経つと、開封が進んで未開封BOXが本格的に減りはじめ、今度はコレクション需要が価格を押し上げていく——という流れとして整理できます。<br><br>
ただし<strong>これは値動きの傾向から読み取れる構造の説明であって、個別商品の値動きの原因を特定したものではありません</strong>。相場が動くフェーズの考え方は<a href="price-pattern-guide.html">BOX買取価格の5段階パターン</a>で詳しく扱っています。</div>

<h2>発見②｜4年目以降は年を追って上昇</h2>
<p>谷を抜けたあとは、経過年数とともに定価比が切り上がっていきます。最も古い{{PK_AGE_LAST_RANGE}}の区間では中央値{{PK_AGE_LAST_MED}}、平均では{{PK_AGE_LAST_AVG}}に達しています。</p>

<p>この帯域の商品は、すでに定価では手に入らず、再販もかからない状態です。<strong>供給が完全に止まった商品の価格は、残った未開封BOXをどれだけの人が欲しがるかだけで決まります。</strong></p>

<h2>平均と中央値が離れる理由</h2>
<p>表を見ると、区間によっては<strong>平均と中央値が大きく離れています</strong>。これは一部の突出した高額BOXが平均を引き上げているためです。</p>

<p>ポケカには定価の10倍を超えるBOXがいくつか存在し、それらが含まれる区間では平均が跳ね上がります。<strong>「その年代のBOXが一般的にどのくらいか」を知りたい場合は、平均ではなく中央値を見てください。</strong>平均だけを見ると、実際より高く見積もることになります。</p>

<h2>重要な限界｜生存バイアス</h2>
<div class="callout"><strong>この集計には構造的な偏りがあります。</strong> 対象は<strong>現在も買取価格が付いている商品</strong>だけです。買取掲載が終わった商品——つまり<strong>価値が下がって店が扱わなくなった商品</strong>——は集計に入っていません。<br><br>
つまり「古い商品ほど定価比が高い」という結果には、<strong>生き残った商品だけを見ているという偏り</strong>が含まれます。もし過去に値下がりして買取対象から外れた商品が相当数あるなら、実際の期待値は本記事の数字より低くなります。</div>

<p>加えて、各区間の対象数は少ないものでは数件しかありません。<strong>統計的に十分な標本数ではない</strong>ため、区間ごとの数値は「そういう傾向がある」程度に受け取ってください。</p>

<h2>買い時の考え方</h2>
<ul>
<li><strong>発売直後は定価比が低い</strong> — 数字のうえでは、発売直後は{{PK_AGE_FIRST_MED}}と低い水準です。定価で買えるなら参入コストは最も低くなります。</li>
<li><strong>2年目の谷は仕込みどころになり得る</strong> — {{PK_AGE_BOTTOM_RANGE}}の区間は{{PK_AGE_BOTTOM_MED}}と、初期ピークより低い水準です。ここで拾えれば、その後の上昇局面を取れる可能性があります。ただし谷がさらに深くなるリスクもあります。</li>
<li><strong>古い商品は高いが、すでに織り込まれている</strong> — {{PK_AGE_LAST_RANGE}}の商品は{{PK_AGE_LAST_MED}}ですが、その分の購入コストも高くなっています。今から買って同じ倍率が乗るわけではありません。</li>
<li><strong>短期の動きは別に確認する</strong> — 本記事は経過年数という長期の軸で見たものです。今この瞬間に上がっているか下がっているかは<a href="box-price-trend.html">BOX相場の値動きレポート</a>と<a href="ranking.html">週間価格変化ランキング</a>で確認してください。</li>
</ul>""",
        "faq": [
            {"q": "ポケカのBOXは発売から何年で何倍になりますか？",
             "a": "当サイトの実データ({{PK_AGE_N}}商品)では、定価比の中央値が発売直後{{PK_AGE_FIRST_RANGE}}で{{PK_AGE_FIRST_MED}}、{{PK_AGE_PEAK_RANGE}}で{{PK_AGE_PEAK_MED}}、{{PK_AGE_BOTTOM_RANGE}}で{{PK_AGE_BOTTOM_MED}}、最も古い{{PK_AGE_LAST_RANGE}}の区間で{{PK_AGE_LAST_MED}}となっています。単純な右肩上がりではなく、一度上がって2年目に下げ、そこから年を追って上昇するという推移です。"},
            {"q": "なぜ2年目に下がるのですか？",
             "a": "本記事は値動きの記録であり、原因を特定したものではありません。構造としては、発売1年前後は新弾としての注目と在庫の減少で価格が伸び、2年目に入ると話題が次の新弾へ移り再販も行き渡って需要が一巡する、という流れが考えられます。その後は開封が進んで未開封BOXが本格的に減り、コレクション需要が価格を押し上げていくと整理できます。"},
            {"q": "平均と中央値のどちらを見ればいいですか？",
             "a": "その年代のBOXが一般的にどのくらいかを知りたい場合は中央値です。ポケカには定価の10倍を超えるBOXがいくつかあり、それらが含まれる区間では平均が大きく引き上げられます。平均だけを見ると実際より高く見積もることになります。"},
            {"q": "この数字を信じて買っても大丈夫ですか？",
             "a": "そのまま将来の期待値として使うのは避けてください。集計対象は現在も買取価格が付いている商品だけで、価値が下がって買取対象から外れた商品は含まれていません(生存バイアス)。また各区間の対象数は少ないものでは数件しかなく、統計的に十分な標本数ではありません。過去の傾向として参考にする程度が適切です。"},
            {"q": "買い時はいつですか？",
             "a": "数字のうえでは、定価で買える発売直後({{PK_AGE_FIRST_MED}})と、初期ピークより低い水準まで下げる{{PK_AGE_BOTTOM_RANGE}}の区間({{PK_AGE_BOTTOM_MED}})が候補になります。ただし谷がさらに深くなるリスクもあり、BOXは値上がりを保証する商品ではありません。短期の方向感はBOX相場の値動きレポートや週間価格変化ランキングもあわせて確認してください。"},
        ],
    },
    {
        "slug": "shop-price-gap",
        "crumb": "店舗間の買取価格差",
        "date": "2026-08-26",
        "date_jp": "2026年8月26日",
        "title": "同じBOXでも店で{{PK_GAP_MED_YEN}}違う｜9店舗の買取価格差を実データで検証",
        "h1": "同じBOXでも買取価格は店でどれだけ違うか｜9店舗の実データで検証",
        "meta_desc": "まったく同じポケカBOXでも、買取価格は店舗によって大きく違います。当サイトが最大9店舗から毎日自動取得している実データで、{{PK_GAP_MIN_SHOPS}}店以上が掲載する{{PK_GAP_N}}商品の最高値と最安値を比較したところ、差額の中央値は{{PK_GAP_MED_YEN}}({{PK_GAP_MED_PCT}})、最大では{{PK_GAP_MAXYEN_YEN}}に達しました。さらに最高値を出す店は1店に集中しておらず、商品ごとに入れ替わります。損をしないための確認手順まで実データで解説します。",
        "og_title": "同じBOXでも店で{{PK_GAP_MED_YEN}}違う｜9店舗の買取価格差",
        "og_desc": "9店舗の実データで{{PK_GAP_N}}商品の最高値と最安値を比較。差額の中央値{{PK_GAP_MED_YEN}}、最大{{PK_GAP_MAXYEN_YEN}}。最高値の店は商品ごとに入れ替わります。",
        "meta_line": "店舗間の買取価格差・比較の実践手順",
        "hero_label": "店舗間の買取価格差({{PK_GAP_N}}商品・最大{{PK_GAP_SHOPS}}店)",
        "hero_big": "差額の中央値 {{PK_GAP_MED_YEN}}",
        "hero_sub": "まったく同じBOXでも、最高値の店と最安値の店では中央値で{{PK_GAP_MED_YEN}}({{PK_GAP_MED_PCT}})の開きがあります。最大では{{PK_GAP_MAXYEN_YEN}}。しかも最高値を出す店は1店に固定されておらず、商品ごとに入れ替わります。",
        "disclaimer": "本記事の買取価格は、当サイトが最大9店舗から自動取得した実データ({{PK_GAP_MIN_SHOPS}}店以上が価格を掲載している{{PK_GAP_N}}商品が対象)です。各店の掲載状況は日々変わるため、対象商品数や価格差も変動します。掲載価格はあくまで各店が公表している買取価格であり、実際の査定額はシュリンクの有無・外箱の状態・点数などにより上下します。特定の店舗を推奨・非推奨する意図はなく、本記事で示すのは「店舗間に差がある」という事実と、その確認手順です。売却の判断はご自身の責任で行ってください。",
        "related": '<li><a href="index.html">ポケカBOX買取価格比較トップ</a> — 全BOXの買取価格を最大9店舗で横断比較(毎日更新)</li>\n'
                   '<li><a href="shop-hikaku.html">9店舗比較</a> — 各店の特徴・買取方法の違い</li>\n'
                   '<li><a href="kaitori-tips.html">BOX買取のコツ</a> — 高く売るための実践ポイント</li>\n'
                   '<li><a href="box-price-trend.html">BOX相場の値動きレポート</a> — いつ売るかの判断材料</li>\n'
                   '<li><a href="ranking.html">週間価格変化ランキング</a> — 直近の値上がり・値下がりを毎日自動更新</li>\n'
                   '<li><a href="mercari-hikaku.html">メルカリ・スニダン比較</a> — 買取店以外の売却先との比較</li>',
        "body": """<p>「BOXを売るなら、どこの店でも大して変わらないだろう」——そう思って1店だけで決めていませんか。</p>

<p>当サイトは最大9店舗の買取価格を毎日自動で取得しています。そのデータで<strong>まったく同じBOXの最高値と最安値を突き合わせた</strong>結果、想像以上の差がありました。</p>

<div class="callout"><strong>3行まとめ:</strong><br>
・{{PK_GAP_MIN_SHOPS}}店以上が掲載する{{PK_GAP_N}}商品で、<strong>差額の中央値は{{PK_GAP_MED_YEN}}({{PK_GAP_MED_PCT}})</strong><br>
・最大では<strong>{{PK_GAP_MAXYEN_YEN}}</strong>。1BOX売るだけで、店選びだけこれだけ変わる<br>
・しかも<strong>最高値を出す店は1店に固定されていない</strong>。商品ごとに入れ替わるので「いつもこの店」は損になり得る</div>

<h2>店舗間の価格差はどのくらいか</h2>
<p>集計対象は、{{PK_GAP_MIN_SHOPS}}店以上が買取価格を掲載している<strong>{{PK_GAP_N}}商品</strong>です(掲載店が少ない商品は比較にならないため除外しています)。</p>

<table class="data-table">
<thead><tr><th>指標</th><th style="text-align:right">値</th></tr></thead>
<tbody>
<tr class="up"><td><strong>差額の中央値</strong></td><td class="num"><strong>{{PK_GAP_MED_YEN}}</strong></td></tr>
<tr><td>差率の中央値</td><td class="num">{{PK_GAP_MED_PCT}}</td></tr>
<tr><td>最大の差額</td><td class="num">{{PK_GAP_MAXYEN_YEN}}</td></tr>
<tr><td>最大の差率</td><td class="num">{{PK_GAP_MAX_PCT}}</td></tr>
</tbody>
</table>

<p>中央値で{{PK_GAP_MED_YEN}}ということは、<strong>半分の商品はこれ以上の差がある</strong>ということです。「たかが数百円」ではありません。</p>

<h2>差が大きいBOX TOP10</h2>
<p>最高値と最安値の開きが大きい順に並べたものです。同じ商品を、同じ日に、違う店が査定した結果がこれだけ違います。</p>

{{PK_GAP_TABLE}}

<p>最大は<strong>{{PK_GAP_MAX_NAME}}</strong>で、差率にして{{PK_GAP_MAX_PCT}}、金額では{{PK_GAP_MAX_YEN}}の開きがありました。金額ベースで最も大きかったのは<strong>{{PK_GAP_MAXYEN_NAME}}</strong>の{{PK_GAP_MAXYEN_YEN}}です。</p>

<h2>最高値の店は1店に固定されていない</h2>
<p>ここが本記事でもっとも実用的な発見です。「どこか1店が常に高い」なら話は簡単ですが、<strong>実際はそうなっていません</strong>。</p>

<p>{{PK_GAP_N}}商品それぞれで最高値を出した店を数えると、<strong>最も多く最高値を取った店でもシェアは{{PK_GAP_MAX_SHARE}}</strong>にとどまります。裏を返せば、<strong>半分以上の商品では別の店のほうが高い</strong>ということです。</p>

<div class="callout"><strong>これが意味すること:</strong> 「前回この店が高かったから今回もここ」という決め方は、<strong>半分以上の確率で最高値を逃します</strong>。店ごとに得意なシリーズや在庫状況が違うため、<strong>売りたい商品ごとに比較し直す</strong>のが正解です。当サイトの<a href="index.html">比較トップ</a>は商品ごとに全店の価格を並べているので、この確認が一度で済みます。</div>

<h2>なぜこれだけ差が出るのか</h2>
<p>買取価格は「その店がいくらで仕入れたいか」で決まります。同じ商品でも店によって事情が違うため、価格に差が出ます。</p>
<ul>
<li><strong>在庫状況</strong> — すでに十分な在庫を持つ店は積極的に買う理由がなく、価格を下げます。逆に品切れなら強気に出ます。</li>
<li><strong>得意なシリーズ</strong> — 店ごとに客層や販売力が違い、売りやすい商品には高値を付けられます。</li>
<li><strong>価格改定のタイミング</strong> — 相場が動いたとき、すぐ追随する店と数日遅れる店があります。この時差がそのまま差額になります。</li>
<li><strong>買取キャンペーン</strong> — 特定期間・特定商品を強化している店があります。</li>
</ul>

<p>相場が大きく動いている時期ほど、3つ目の「追随の時差」で差が開きやすくなります。直近の相場の動きは<a href="box-price-trend.html">BOX相場の値動きレポート</a>で確認できます。</p>

<h2>損しないための3ステップ</h2>
<h3>1. 売りたい商品ごとに全店を並べる</h3>
<p>「店を選ぶ」のではなく「商品ごとに店を選ぶ」のが正解です。<a href="index.html">比較トップ</a>で商品を探せば、全店の価格が横並びで表示されます。</p>

<h3>2. 差額と手間を天秤にかける</h3>
<p>差額が{{PK_GAP_MED_YEN}}程度なら、送料や手数料で相殺される可能性もあります。一方で万円単位の差がある商品なら、多少手間をかけても高い店に送る価値があります。<strong>差額を先に把握してから動く</strong>のが効率的です。</p>

<h3>3. 売る直前に見る</h3>
<p>価格は日々動きます。数日前に調べた順位が、売る日には入れ替わっていることもあります。<strong>当サイトは毎日自動更新している</strong>ので、発送・来店の直前にもう一度確認してください。</p>

<h2>この集計の限界</h2>
<ul>
<li><strong>掲載価格であって査定額ではない</strong> — 実際の買取額はシュリンクの有無・外箱の状態・まとめ売りの点数などで上下します。本記事の数値は各店が公表している価格の比較です。</li>
<li><strong>対象は{{PK_GAP_MIN_SHOPS}}店以上が掲載する商品のみ</strong> — 掲載店が少ない商品は比較対象から外れています。</li>
<li><strong>掲載状況は日々変わる</strong> — 店が取り扱いをやめたり再開したりするため、対象商品数も価格差も変動します。</li>
<li><strong>特定店の推奨ではない</strong> — 本記事は「差がある」という事実と確認手順を示すもので、どの店が良い・悪いという評価ではありません。買取方法や入金スピードなど価格以外の条件は<a href="shop-hikaku.html">9店舗比較</a>をご覧ください。</li>
</ul>""",
        "faq": [
            {"q": "同じBOXでも店によって買取価格は違いますか？",
             "a": "違います。当サイトが最大9店舗から取得した実データでは、{{PK_GAP_MIN_SHOPS}}店以上が掲載する{{PK_GAP_N}}商品で、最高値と最安値の差額は中央値{{PK_GAP_MED_YEN}}({{PK_GAP_MED_PCT}})でした。最大では{{PK_GAP_MAXYEN_YEN}}の開きがあります。中央値ということは、半分の商品はこれ以上の差があるということです。"},
            {"q": "一番高く買い取ってくれる店はどこですか？",
             "a": "商品によって変わります。{{PK_GAP_N}}商品それぞれで最高値を出した店を数えると、最も多く最高値を取った店でもシェアは{{PK_GAP_MAX_SHARE}}にとどまり、半分以上の商品では別の店のほうが高いという結果でした。「いつもこの店」という決め方では最高値を逃しやすいため、売りたい商品ごとに比較し直すことをおすすめします。"},
            {"q": "なぜ店によって価格が違うのですか？",
             "a": "買取価格は「その店がいくらで仕入れたいか」で決まるためです。在庫を十分に持つ店は価格を下げ、品切れの店は強気に出ます。また店ごとに得意なシリーズや客層が違い、売りやすい商品には高値を付けられます。相場が動いたときにすぐ追随する店と数日遅れる店があり、この時差も差額になります。"},
            {"q": "何円くらい差があれば比較する価値がありますか？",
             "a": "差額が中央値の{{PK_GAP_MED_YEN}}程度だと送料や手数料で相殺される可能性もあります。一方、本記事の集計では万円単位の差がある商品も複数あり、そうした商品なら多少手間をかけても高い店を選ぶ価値があります。差額を先に把握してから動くのが効率的です。"},
            {"q": "この価格で必ず買い取ってもらえますか？",
             "a": "保証はできません。本記事の数値は各店が公表している買取価格の比較で、実際の査定額はシュリンクの有無・外箱の状態・まとめ売りの点数などにより上下します。また価格は日々変動するため、発送や来店の直前にもう一度ご確認ください。"},
        ],
    },
]


# ---------------------------------------------------------------- 描画

def _render(a: dict) -> str:
    sh = _shell()
    slug = a["slug"]
    url = f"{BASE}/{slug}.html"
    body = _placeholders(a["body"])
    faq = [{"q": _placeholders(f["q"]), "a": _placeholders(f["a"])} for f in a["faq"]]
    # タイトル・meta・heroラベルにも実データを差し込む
    a = {k: (_placeholders(v) if isinstance(v, str) else v) for k, v in a.items()}

    blog_ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": a["title"], "description": a["meta_desc"],
        "datePublished": a["date"], "dateModified": a["date"],
        "image": f"{BASE}/ogp.jpg",
        "author": {"@type": "Organization", "name": "ポケカ買取チェッカー編集部",
                   "url": f"{BASE}/"},
        "publisher": {"@type": "Organization", "name": "ポケカ買取チェッカー",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/ogp.png"}},
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "inLanguage": "ja",
    }
    crumb_ld = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE}/"},
            {"@type": "ListItem", "position": 2, "name": a["crumb"]},
        ],
    }
    faq_ld = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq
        ],
    }
    faq_html = "".join(f'<h3>{_esc(f["q"])}</h3>\n<p>{f["a"]}</p>\n' for f in faq)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{sh['links']}
<title>{_esc(a['title'])}</title>
<meta name="description" content="{_esc(a['meta_desc'])}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{_esc(a['og_title'])}">
<meta property="og:description" content="{_esc(a['og_desc'])}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_esc(a['og_title'])}">
<meta name="twitter:description" content="{_esc(a['og_desc'])}">
<meta name="twitter:image" content="{BASE}/ogp.jpg">
<script type="application/ld+json">{json.dumps(blog_ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(crumb_ld, ensure_ascii=False)}</script>
<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False)}</script>
<style>{sh['css']}{EXTRA_CSS}</style>
{sh['scripts']}
</head>
<body>
<div class="header"><a href="index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="index.html">トップ</a> &gt; {_esc(a['crumb'])}</div>

<div class="content-layout">
{sh['nav']}
<article>
<h1>{a['h1']}</h1>
<div class="meta">公開: {_esc(a['date_jp'])} / 相場更新: {_esc(a['date_jp'])} / {_esc(a['meta_line'])} / ポケカ買取チェッカー編集部</div>

<div class="hero">
<div class="stat-label">{_esc(a['hero_label'])}</div>
<div class="stat-big">{_placeholders(a['hero_big'])}</div>
<div class="stat-sub">{_placeholders(a['hero_sub'])}</div>
</div>

{body}

<h2>よくある質問(FAQ)</h2>
{faq_html}

<h2>関連ページ</h2>
<ul>
{a['related']}
</ul>

<div class="disclaimer"><strong>ご注意:</strong> {_placeholders(a['disclaimer'])}</div>

<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
</article>
</div>
</div>
{sh['ft']}
</body>
</html>
"""


def build() -> None:
    for a in POKECA_ARTICLES:
        html = _render(a)
        (ART_DIR / f"{a['slug']}.html").write_text(html, encoding="utf-8")
        print(f"wrote {a['slug']}.html")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
