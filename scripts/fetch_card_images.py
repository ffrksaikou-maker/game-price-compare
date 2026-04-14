"""公式ポケモンカードDBから当たりカードの画像をダウンロードするスクリプト"""
import requests
import json
import time
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scraper.matcher import MASTER_PRODUCTS

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
BASE_URL = 'https://www.pokemon-card.com'
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'images', 'cards')
os.makedirs(OUT_DIR, exist_ok=True)

# パック名 → pgコードのマッピング
PG_CODES = {
    "ニンジャスピナー": "953",
    "ムニキスゼロ": "952",
    "バトルコレクション": "951",
    "MEGAドリームex": "950",
    "インフェルノX": "949",
    "メガシンフォニア": "945",
    "メガブレイブ": "944",
    "ホワイトフレア": "943",
    "ブラックボルト": "942",
    "ロケット団の栄光": "941",
    "熱風のアリーナ": "940",
    "バトルパートナーズ": "939",
    "テラスタルフェスex": "933",
    "超電ブレイカー": "932",
    "楽園ドラゴーナ": "931",
    "ステラミラクル": "930",
    "ナイトワンダラー": "929",
    "変幻の仮面": "928",
    "クリムゾンヘイズ": "927",
    "ワイルドフォース": "926",
    "サイバージャッジ": "925",
    "シャイニートレジャーex": "905",
    "古代の咆哮": "901",
    "未来の一閃": "902",
    "レイジングサーフ": "899",
    "黒炎の支配者": "894",
    "151": "882",
    "クレイバースト": "880",
    "スノーハザード": "879",
    "トリプレットビート": "878",
    "スカーレットex": "870",
    "バイオレットex": "871",
    # S&S
    "VSTARユニバース": "832",
    "パラダイムトリガー": "826",
    "白熱のアルカナ": "824",
    "ロストアビス": "822",
    "ポケモンGO": "820",
    "ダークファンタズマ": "818",
    "タイムゲイザー": "816",
    "スペースジャグラー": "815",
    "バトルリージョン": "812",
    "スターバース": "811",
    "VMAXクライマックス": "808",
    "25th ANNIVERSARY COLLECTION": "805",
    "フュージョンアーツ": "803",
    "蒼空ストリーム": "801",
    "摩天パーフェクト": "800",
    "イーブイヒーローズ": "797",
    "白銀のランス": "795",
    "漆黒のガイスト": "794",
    "双璧のファイター": "792",
    "連撃マスター": "789",
    "一撃マスター": "788",
    "シャイニースターV": "783",
    "仰天のボルテッカー": "779",
    "伝説の鼓動": "776",
    "ムゲンゾーン": "774",
    "爆炎ウォーカー": "771",
    "反逆クラッシュ": "768",
    "VMAXライジング": "766",
    "ソード": "763",
    "シールド": "764",
}


def get_all_cards(pg_code):
    """指定パックの全カードリストを取得"""
    all_cards = []
    for page in range(1, 10):
        try:
            r = requests.get(f'{BASE_URL}/card-search/resultAPI.php',
                           params={'pg': pg_code, 'p': str(page)},
                           headers=HEADERS, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            cards = data.get('cardList', [])
            if not cards:
                break
            all_cards.extend(cards)
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching page {page}: {e}")
            break
    return all_cards


def find_card_image(cards, card_name):
    """カード名からSAR/MUR等の画像URLを特定する。
    同名カードが複数ある場合、最後のもの（レアリティが高い方）を選ぶ。
    """
    # カード名からポケモン名/サポート名を抽出
    clean_name = card_name.split(" ")[0]  # "メガゲッコウガex MUR" → "メガゲッコウガex"
    clean_name = clean_name.replace("ex", "").replace("V", "").replace("VMAX", "").replace("VSTAR", "")
    clean_name = clean_name.replace("の", "").replace("　", "")

    matches = []
    for card in cards:
        name = card.get('cardNameViewText', '') or card.get('cardNameAltText', '')
        img = card.get('cardThumbFile', '')
        card_id = card.get('cardID', '')

        # ファイル名からもマッチ（ローマ字名）
        if clean_name in name or name in clean_name:
            matches.append((card_id, name, img))

    if matches:
        # 同名カードの最後（IDが大きい = レアリティが高い傾向）を返す
        matches.sort(key=lambda x: x[0])
        return matches[-1]

    return None


def download_image(img_path, filename):
    """画像をダウンロードして保存"""
    url = f'{BASE_URL}{img_path}'
    filepath = os.path.join(OUT_DIR, filename)
    if os.path.exists(filepath):
        return True
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return True
    except Exception as e:
        print(f"  Download error: {e}")
    return False


def main():
    results = {}  # product_name -> [(card_name, image_filename), ...]

    for product in MASTER_PRODUCTS:
        if not product.hit_cards:
            continue

        # パック名からpgコードを特定
        pg_code = None
        for key, code in PG_CODES.items():
            if key in product.name:
                pg_code = code
                break

        if not pg_code:
            print(f"SKIP (no pg code): {product.name}")
            continue

        print(f"\n=== {product.name} (pg={pg_code}) ===")
        cards = get_all_cards(pg_code)
        print(f"  Total cards in pack: {len(cards)}")

        product_results = []
        for hit_card in product.hit_cards[:3]:
            if isinstance(hit_card, (list, tuple)):
                card_name = hit_card[0]
            else:
                card_name = hit_card

            match = find_card_image(cards, card_name)
            if match:
                card_id, name, img_path = match
                # ファイル名: パックslug_カードID.jpg
                ext = os.path.splitext(img_path)[1] or '.jpg'
                filename = f"{card_id}{ext}"

                if download_image(img_path, filename):
                    print(f"  OK: {card_name} -> {filename}")
                    product_results.append((card_name, filename))
                else:
                    print(f"  FAIL download: {card_name}")
                    product_results.append((card_name, ""))
            else:
                print(f"  NOT FOUND: {card_name}")
                product_results.append((card_name, ""))

            time.sleep(0.2)

        results[product.name] = product_results

    # 結果をJSONで保存
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'card_images.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 統計
    total = sum(len(v) for v in results.values())
    found = sum(1 for v in results.values() for _, fn in v if fn)
    print(f"\n=== DONE: {found}/{total} images downloaded ===")


if __name__ == '__main__':
    main()
