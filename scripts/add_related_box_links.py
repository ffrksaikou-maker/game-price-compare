"""Add a '関連BOXをチェック' section to the end of each article.

Each article gets 5 thematically-relevant BOX links inserted right before
the next-article/back link. This is purely additive (no body text changes)
and uses existing article h2/ul styling (no CSS modification needed).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (slug, display_name) — all confirmed to exist in box/
BOXES = {
    "151": "ポケモンカード151",
    "inferno": "MEGA 拡張パック「インフェルノX」",
    "mega-brave": "MEGA 拡張パック「メガブレイブ」",
    "eevee-heroes": "強化拡張パック「イーブイヒーローズ」",
    "ruler-of-black-flame": "拡張パック「黒炎の支配者」",
    "vmax-climax": "ハイクラスパック「VMAXクライマックス」",
    "25th-anniversary-collection": "25th ANNIVERSARY COLLECTION",
    "shiny-treasure-ex": "ハイクラスパック「シャイニートレジャーex」",
    "crimson-haze": "拡張パック「クリムゾンヘイズ」",
    "terastal-fes-ex": "ハイクラスパック「テラスタルフェスex」",
    "black-bolt": "拡張パック「ブラックボルト」",
    "rocket-dan-no-eiko": "拡張パック「ロケット団の栄光」",
    "shiny-star": "ハイクラスパック「シャイニースター」",
}

# Per-article related BOX selection (5 each, no duplicates)
ARTICLE_RELATED = {
    "kaitori-tips.html": ["151", "inferno", "eevee-heroes", "ruler-of-black-flame", "mega-brave"],
    "shop-hikaku.html": ["eevee-heroes", "151", "vmax-climax", "shiny-star", "crimson-haze"],
    "single-card-tips.html": ["151", "ruler-of-black-flame", "shiny-treasure-ex", "terastal-fes-ex", "rocket-dan-no-eiko"],
    "psa-guide.html": ["eevee-heroes", "151", "25th-anniversary-collection", "vmax-climax", "shiny-star"],
    "mercari-hikaku.html": ["151", "inferno", "ruler-of-black-flame", "mega-brave", "black-bolt"],
    "shrink-nashi.html": ["eevee-heroes", "vmax-climax", "25th-anniversary-collection", "crimson-haze", "151"],
    "monthly-ranking-2026-03.html": ["151", "ruler-of-black-flame", "eevee-heroes", "crimson-haze", "mega-brave"],
    "box-toushi.html": ["inferno", "151", "ruler-of-black-flame", "mega-brave", "terastal-fes-ex"],
    "restock-guide.html": ["151", "ruler-of-black-flame", "crimson-haze", "inferno", "mega-brave"],
}

MARKER_COMMENT = "<!-- related-box-links -->"


def build_section(slugs: list[str]) -> str:
    items = []
    for s in slugs:
        name = BOXES.get(s)
        if not name:
            continue
        items.append(f'<li><a href="box/{s}.html">{name}</a> の買取価格をチェック</li>')
    items_html = "\n".join(items)
    return (
        f'\n{MARKER_COMMENT}\n'
        f'<h2>関連BOXの買取価格をチェック</h2>\n'
        f'<p>この記事で紹介したポイントを踏まえて、実際の買取価格を10店舗で比較できます。'
        f'以下は特に比較需要が高いBOXです。</p>\n'
        f'<ul>\n{items_html}\n</ul>\n'
    )


def main():
    for fname, slugs in ARTICLE_RELATED.items():
        path = ROOT / fname
        if not path.exists():
            print(f"SKIP: {fname} (not found)")
            continue

        content = path.read_text(encoding="utf-8")

        if MARKER_COMMENT in content:
            print(f"SKIP: {fname} (already has related-box section)")
            continue

        section = build_section(slugs)

        # Insert before the first occurrence of:
        # <a href="index.html" class="back"> (this is the "back to top" link)
        # or <a ... class="next-article"> whichever comes first
        patterns_try = [
            r'(\n\s*<a [^>]*class="next-article")',
            r'(\n\s*<a href="index\.html" class="back")',
            r'(\n\s*</article>)',
        ]
        inserted = False
        for pat in patterns_try:
            m = re.search(pat, content)
            if m:
                new_content = content[: m.start()] + "\n" + section + content[m.start():]
                path.write_text(new_content, encoding="utf-8")
                print(f"OK: {fname} (inserted before {pat})")
                inserted = True
                break
        if not inserted:
            print(f"WARN: {fname} (no insertion point found)")


if __name__ == "__main__":
    main()
