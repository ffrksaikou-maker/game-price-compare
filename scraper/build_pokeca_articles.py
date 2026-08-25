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
        "links": "\n".join(re.findall(r"<link[^>]*>", head)),
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
    return text


# ---------------------------------------------------------------- 記事データ

POKECA_ARTICLES: list[dict] = [
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
