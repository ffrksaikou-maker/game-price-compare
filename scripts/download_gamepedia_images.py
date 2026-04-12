"""Download BOX images from gamepedia.jp CDN.

Uses the decoded product names to match against our slug system,
then downloads 600px JPEG versions via the CDN image proxy.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "images" / "boxes"

# Load decoded entries
DECODED_PATH = Path("C:/Users/fifty/gamepedia_decoded.json")

# Manual mapping: decoded Japanese name substring -> our slug
# Only need to cover BOXes we track (66 slugs)
NAME_TO_SLUG: dict[str, str] = {
    # MEGA
    "ニンジャスピナー": "ninja-spinner",
    "ムニキスゼロ": "munikis-zero",
    "MEGAドリームex": "mega-ex",
    "インフェルノX": "inferno",
    "メガブレイブ": "mega-brave",
    "メガシンフォニア": "mega-sinfonia",
    "バトルコレクション": "battle-collection",
    # SV
    "スカーレットex": "scarlet-ex",
    "バイオレットex": "violet-ex",
    "トリプレットビート": "triplet-beat",
    "スノーハザード": "snow-hazard",
    "クレイバースト": "clay-burst",
    "ポケモンカード151": "151",
    "黒炎の支配者": "ruler-of-black-flame",
    "レイジングサーフ": "raging-surf",
    "古代の咆哮": "ancient-roar",
    "未来の一閃": "future-flash",
    "シャイニートレジャーex": "shiny-treasure-ex",
    "変幻の仮面": "hengen-no-kamen",
    "ナイトワンダラー": "night-wanderer",
    "ステラミラクル": "stellar-miracle",
    "クリムゾンヘイズ": "crimson-haze",
    "楽園ドラゴーナ": "rakuen-dragona",
    "超電ブレイカー": "chouden-breaker",
    "テラスタルフェスex": "terastal-fes-ex",
    "バトルパートナーズ": "battle-partners",
    "ロケット団の栄光": "rocket-dan-no-eiko",
    "ブラックボルト": "black-bolt",
    "ホワイトフレア": "white-flare",
    "熱風のアリーナ": "neppuu-arena",
    # S&S
    "ソード": "sword",
    "シールド": "shield",
    "VMAXライジング": "vmax-rising",
    "反逆クラッシュ": "rebellion-crash",
    "ムゲンゾーン": "infinity-zone",
    "仰天のボルテッカー": "astonishing-voltecker",
    "爆炎ウォーカー": "eruption-walker",
    "伝説の鼓動": "legendary-heartbeat",
    "シャイニースターV": "shiny-star",
    "一撃マスター": "single-strike-master",
    "連撃マスター": "rapid-strike-master",
    "白銀のランス": "silver-lance",
    "漆黒のガイスト": "jet-black-geist",
    "イーブイヒーローズ": "eevee-heroes",
    "フュージョンアーツ": "fusion-arts",
    "蒼空ストリーム": "blue-sky-stream",
    "摩天パーフェクト": "skyscraping-perfect",
    "VMAXクライマックス": "vmax-climax",
    "25thANNIVERSARYCOLLECTION": "25th-anniversary-collection",
    "スターバース": "star-birth",
    "バトルリージョン": "battle-region",
    "タイムゲイザー": "time-gazer",
    "スペースジャグラー": "space-juggler",
    "ダークファンタズマ": "dark-phantasma",
    "ポケモンGO": "pokemon-go",
    "ロストアビス": "lost-abyss",
    "白熱のアルカナ": "incandescent-arcana",
    "パラダイムトリガー": "paradigm-trigger",
    "VSTARユニバース": "vstar-universe",
    "無敵のファイター": "matchless-fighters",
    # DX
    "拡張パックDXブラックボルト": "black-bolt-dx",
    "拡張パックDXホワイトフレア": "white-flare-dx",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def download(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main():
    entries = json.loads(DECODED_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matched = 0
    downloaded = 0
    skipped = 0

    for entry in entries:
        name = entry["name"]
        url_path = entry["url"]  # relative: assets.gamepedia.jp/...

        # Match against our slug map
        slug = None
        for keyword, s in NAME_TO_SLUG.items():
            if keyword in name:
                slug = s
                break

        if not slug:
            continue

        matched += 1
        dest = OUT_DIR / f"{slug}.jpg"

        # Always replace: gamepedia has actual product shots (better than
        # our current mix of hero illustrations from pokemon-card.com)

        # Direct source URL (no CDN transformation to avoid 415 errors)
        cdn_url = f"https://{url_path}"

        try:
            size = download(cdn_url, dest)
            print(f"OK:   {slug:40s} <- {name[:40]}  ({size:,} bytes)")
            downloaded += 1
        except Exception as e:
            print(f"FAIL: {slug:40s} <- {name[:40]}  ({e})")

    print(f"\n--- Matched: {matched}, Downloaded: {downloaded}, Skipped: {skipped} ---")


if __name__ == "__main__":
    main()
