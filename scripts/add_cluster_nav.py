"""Add 📘 掘り下げガイド subsection to left article-nav and mobile footer nav.

Adds 10 cluster/detail articles below the 🔥 BOX深掘り特集 section.

Idempotent.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Cluster articles to add (ordered by importance/scope)
CLUSTER_ARTICLES = [
    ("zeppan-ranking-2026-03.html", "📊 S&S以降 絶版BOXランキング"),
    ("lizardon-box-guide.html", "🔥 リザードン高騰BOX完全ガイド"),
    ("mega-pack-compare.html", "⚡ MEGA拡張パック完全比較"),
    ("kokuen-vs-rocket.html", "⚔️ 黒炎 vs ロケット団の栄光"),
    ("mega-lizardon-x-guide.html", "メガリザードンXex MUR/SAR"),
    ("lizardon-sar-kokuen-guide.html", "リザードンex SAR(黒炎)"),
    ("erika-sar-guide.html", "エリカの招待 SAR"),
    ("pigeot-sar-guide.html", "ピジョットex SAR"),
    ("masterball-mirror-guide.html", "151マスターボールミラー"),
    ("kokuen-atari-guide.html", "黒炎 当たりカード完全ガイド"),
]

ROOT_ARTICLES = [
    "kaitori-tips.html", "shop-hikaku.html", "single-card-tips.html",
    "psa-guide.html", "mercari-hikaku.html", "shrink-nashi.html",
    "monthly-ranking-2026-03.html", "box-toushi.html", "restock-guide.html",
    "ranking.html", "151-spotlight.html", "inferno-x-spotlight.html",
    "kokuen-spotlight.html", "zeppan-ranking-2026-03.html",
    "lizardon-box-guide.html", "mega-pack-compare.html", "kokuen-vs-rocket.html",
    "mega-lizardon-x-guide.html", "lizardon-sar-kokuen-guide.html",
    "erika-sar-guide.html", "pigeot-sar-guide.html",
    "masterball-mirror-guide.html", "kokuen-atari-guide.html",
]

# Left sidebar — add after the kokuen-spotlight entry (last item in 🔥 BOX深掘り特集)
LEFT_MARKER_ROOT = '<a href="kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>'
LEFT_MARKER_BOX = '<a href="../kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>'


def build_left_block(prefix: str, current_file: str = "") -> str:
    lines = ['<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>']
    for fname, label in CLUSTER_ARTICLES:
        cls = ' class="current"' if fname == current_file else ''
        lines.append(f'<a href="{prefix}{fname}"{cls}>{label}</a>')
    return "\n".join(lines)


MOBILE_MARKER_ROOT = '<a class="spot" href="kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>'
MOBILE_MARKER_BOX = '<a class="spot" href="../kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>'


def build_mobile_block(prefix: str) -> str:
    """Add cluster articles as a new section in mobile footer nav."""
    lines = [
        '  </div>',
        '  <div class="mfn-section">',
        '    <div class="mfn-section-title" style="color:#6d28d9">📘 掘り下げガイド</div>',
    ]
    for fname, label in CLUSTER_ARTICLES:
        lines.append(f'    <a href="{prefix}{fname}">{label}</a>')
    return "\n".join(lines)


MARKER_SENTINEL = 'article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド'
MOBILE_SENTINEL = 'mfn-section-title" style="color:#6d28d9">📘 掘り下げガイド'


def process(path: Path, prefix: str, current_file: str = "") -> bool:
    content = path.read_text(encoding="utf-8")
    orig = content

    # Skip if already added
    if MARKER_SENTINEL in content:
        pass  # already processed
    else:
        left_marker = LEFT_MARKER_BOX if prefix == '../' else LEFT_MARKER_ROOT
        if left_marker in content:
            block = build_left_block(prefix, current_file)
            content = content.replace(left_marker, left_marker + '\n' + block, 1)

    # Mobile footer nav
    if MOBILE_SENTINEL not in content:
        mobile_marker = MOBILE_MARKER_BOX if prefix == '../' else MOBILE_MARKER_ROOT
        # Find the mobile marker's closing </div> (end of BOX深掘り特集 section)
        # and insert new section before the 📰 一般記事 section
        # Strategy: insert right after the mobile_marker line (it's the last in spot section)
        if mobile_marker in content:
            # The marker is: <a class="spot" href="...">...</a>
            # After this line, the section closes with </div> and a new section starts
            # We need to find the closing </div> after mobile_marker and insert a new section
            # Simpler: insert AFTER mobile_marker + newline, but before the </div>
            # Actually it's easier to insert new section replacing </div> with </div>+newSection
            # But that would affect all </div>.
            # Let's find marker's position, then insert after it with a closing+opening div
            idx = content.find(mobile_marker)
            if idx != -1:
                # Find the end of this <a> line
                line_end = content.find('\n', idx)
                if line_end != -1:
                    insertion = '\n' + build_mobile_block(prefix)
                    # Insert 新 section の </div> opening </div> と </div>  一般記事 の前に新規 section
                    # Pattern: after mobile_marker line, we insert:
                    #   </div>   <- closes 🔥 section
                    #   <div class="mfn-section"> ... (new 📘 section)
                    # But the existing </div> is already there.
                    # Actually easier: insert a new "</div>\n<div class=mfn-section>..." right before existing closing of 🔥 section
                    # Simpler: insert RIGHT AFTER mobile_marker line, as a sibling
                    # Instead of complex </div> manipulation, let's just close 🔥 early and open 📘 then close (the existing </div> will close 📘)
                    # So: after mobile_marker line, insert "</div><div class=mfn-section>📘section" and let existing </div> close it
                    content = content[:line_end] + insertion + content[line_end:]

    if content != orig:
        path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    ok = 0
    # Root articles
    for fname in ROOT_ARTICLES:
        p = ROOT / fname
        if not p.exists(): continue
        if process(p, prefix='', current_file=fname):
            ok += 1; print(f"OK: {fname}")

    # box-template + box/*
    for p in [ROOT / "box-template.html", *sorted((ROOT / "box").glob("*.html"))]:
        if p.exists() and process(p, prefix='../'):
            ok += 1; print(f"OK: {p.relative_to(ROOT)}")

    # weekly/*
    for p in sorted((ROOT / "weekly").glob("*.html")):
        if process(p, prefix='../'):
            ok += 1; print(f"OK: {p.relative_to(ROOT)}")

    print(f"\n=== {ok} files patched ===")


if __name__ == "__main__":
    main()
