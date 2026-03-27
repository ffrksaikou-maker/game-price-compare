"""スニダンから全ポケカBOXの価格推移データを取得して保存するスクリプト"""
import requests, json, re, time, os, sys

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'snkrdunk')
os.makedirs(OUT_DIR, exist_ok=True)

def get_chart(pid):
    """sales-chart APIからグラフデータ取得"""
    try:
        r = requests.get(
            f'https://snkrdunk.com/v1/apparels/{pid}/sales-chart?range=all&salesChartOptionId=0',
            headers=HEADERS, timeout=5
        )
        if r.status_code == 200:
            return r.json().get('points', [])
    except:
        pass
    return []

def get_title(pid):
    """商品ページからタイトル取得"""
    try:
        r = requests.get(f'https://snkrdunk.com/apparels/{pid}', headers=HEADERS, timeout=5)
        if r.status_code == 200:
            m = re.search(r'<title>(.+?)</title>', r.text)
            if m:
                return m.group(1).split('の新品')[0].strip()
    except:
        pass
    return ''

def is_pokeca_box(title):
    """ポケカBOX（シュリンク付）かどうか判定"""
    return ('ポケモン' in title and
            ('ボックス' in title or 'BOX' in title) and
            'シュリンクなし' not in title)

def main():
    # Phase 1: 広範囲スキャン（APIだけ叩いてデータあるIDを集める）
    print("Phase 1: Scanning for candidates...")
    candidates = []
    total = 0

    # ID範囲: 10000~780000をステップで
    ranges = [
        (10000, 20000, 5),      # S&S初期（14673あたり）
        (20000, 100000, 10),    # S&S
        (100000, 140000, 5),    # SV初期（116897, 118914あたり）
        (140000, 430000, 20),   # 中間帯
        (430000, 570000, 10),   # テラスタル〜ロケット団
        (570000, 780000, 5),    # MEGA系
    ]

    for start, end, step in ranges:
        for pid in range(start, end, step):
            total += 1
            pts = get_chart(pid)
            if len(pts) > 10:
                candidates.append((pid, pts))
            if total % 200 == 0:
                sys.stdout.write(f"\r  Scanned {total} IDs, candidates: {len(candidates)}")
                sys.stdout.flush()
            time.sleep(0.05)
        print(f"\n  Range {start}-{end} done. Candidates: {len(candidates)}")

    print(f"\nPhase 1 done: {len(candidates)} candidates from {total} IDs")

    # Phase 2: タイトル確認してポケカBOXだけ抽出
    print("\nPhase 2: Checking titles...")
    found = {}
    for i, (pid, pts) in enumerate(candidates):
        title = get_title(pid)
        if is_pokeca_box(title):
            found[str(pid)] = {'id': str(pid), 'name': title, 'points': pts}
            print(f"  BOX: {pid}: {title[:55]} ({len(pts)}pts)")
        if (i+1) % 10 == 0:
            sys.stdout.write(f"\r  Checked {i+1}/{len(candidates)}")
            sys.stdout.flush()
        time.sleep(0.1)

    print(f"\nPhase 2 done: {len(found)} BOX products")

    # Phase 3: 見つけたID周辺を±20で細かくスキャン
    print("\nPhase 3: Scanning nearby found IDs...")
    for base in list(found.keys()):
        base_id = int(base)
        for offset in range(-20, 21):
            pid = base_id + offset
            if str(pid) in found:
                continue
            pts = get_chart(pid)
            if len(pts) > 10:
                title = get_title(pid)
                if is_pokeca_box(title):
                    found[str(pid)] = {'id': str(pid), 'name': title, 'points': pts}
                    print(f"  NEW: {pid}: {title[:55]} ({len(pts)}pts)")
            time.sleep(0.05)

    # 保存
    for pid, data in found.items():
        path = os.path.join(OUT_DIR, f'{pid}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n=== DONE! {len(found)} Pokemon BOX products saved to {OUT_DIR} ===")
    for pid in sorted(found.keys(), key=int):
        print(f"  {pid}: {found[pid]['name'][:55]} ({len(found[pid]['points'])}pts)")

if __name__ == '__main__':
    main()
