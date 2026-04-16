"""Add Article + FAQPage JSON-LD schema to existing article HTML files.

This is a one-time script to bulk-add structured data to the 8 remaining articles
(kaitori-tips.html was done manually as the template).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Article metadata (title/desc from <title>/meta, dates from BLOG_ARTICLES in generator.py)
ARTICLES = [
    {
        "file": "shop-hikaku.html",
        "headline": "ポケカ買取8店舗の特徴を徹底比較",
        "description": "ポケカBOX買取に対応した8店舗の特徴を比較。森森買取・買取ホムラ・買取一丁目など、各店舗の強みや対応方法を解説。",
        "datePublished": "2026-03-23",
        "dateModified": "2026-03-23",
        "section": "ポケカBOX買取ガイド",
        "faq": [
            {
                "q": "ポケカ買取チェッカーが掲載している店舗は?",
                "a": "2026年4月時点で、森森買取・買取ホムラ・買取一丁目・ラントゥ買取・買取ソムリエ・海峡通信・買取オク・買取ルデヤの8店舗を掲載しています。すべての店舗から毎日3回(11:00/15:00/18:00)自動で価格を取得しています。"
            },
            {
                "q": "どの店舗が一番高く買い取ってくれますか?",
                "a": "BOX商品によって最高値の店舗は変動します。最新の価格は各BOX個別ページの「店舗別 買取価格」表と、週間上昇ランキングページで確認できます。全体傾向としては、ラントゥ買取・買取ルデヤ・森森買取が高値を付けることが多い傾向があります。"
            },
            {
                "q": "店頭買取と郵送買取どちらが使いやすい?",
                "a": "店頭買取は即日現金化できますが、店舗が近くにないと使えません。郵送買取は全国対応で送料無料キャンペーンを行う店舗も多いです。8店舗すべてが郵送買取に対応しています。"
            },
            {
                "q": "買取金額に差が出る理由は?",
                "a": "各店舗の在庫状況、販売先の違い(コレクター層/プレイヤー層/海外)、キャンペーンの有無などで差が出ます。同じBOXでも数千円単位で差が出るため、必ず複数店舗を比較してから売却するのが鉄則です。"
            }
        ]
    },
    {
        "file": "single-card-tips.html",
        "headline": "ポケカBOX開封→シングル売りで利益を出す方法",
        "description": "ポケカBOX開封からシングルカード売却で利益を出す方法を解説。高額カードの当たり例、レアリティの種類、トレンド変化まで。",
        "datePublished": "2026-03-24",
        "dateModified": "2026-03-24",
        "section": "ポケカBOX買取ガイド",
        "faq": [
            {
                "q": "BOXのまま売るのとシングル売りはどちらが儲かる?",
                "a": "高額SAR/SRが封入されているBOXを引き当てれば、シングル売りの方が儲かるケースが多いです。ただし当たりを引けないとBOX売りのほうが確実です。目安として、定価+2,000円以内で買えるBOXで、SAR相場が15,000円以上なら期待値的にシングル売りが有利です。"
            },
            {
                "q": "シングル売りに向いているBOXは?",
                "a": "SAR・UR・SRの封入率が高く、主力カードの相場が安定しているBOX(例: 151、黒炎の支配者、メガブレイブなど)が向いています。逆に主力カードの相場が変動しやすい新弾は売り時を逃すリスクがあります。"
            },
            {
                "q": "シングルカードはどこで売れば良い?",
                "a": "高額カードはスニーカーダンク(スニダン)やメルカリ、大手のカードショップ(カードラッシュ、カードラボ、遊々亭等)で売れます。低額カードはまとめてオリパ業者やカードラッシュの一括買取を使うのが手間対効果的に有利です。"
            }
        ]
    },
    {
        "file": "psa-guide.html",
        "headline": "PSA鑑定とは?ポケカの価値を最大化する方法",
        "description": "ポケモンカードのPSA鑑定を徹底解説。鑑定の流れ、グレードの意味、費用、PSA10で価値が何倍になるかの具体例まで。",
        "datePublished": "2026-03-24",
        "dateModified": "2026-03-24",
        "section": "ポケカ鑑定・コレクション",
        "faq": [
            {
                "q": "PSA鑑定とは何ですか?",
                "a": "PSA(Professional Sports Authenticator)は世界最大級のトレーディングカード鑑定サービスです。カードの状態を1〜10のグレードで評価し、専用ケースに封入して鑑定書を発行します。特にPSA10(GEM MINT)は市場価値が跳ね上がります。"
            },
            {
                "q": "PSA10だと価値はどれくらい上がる?",
                "a": "カードや状態によりますが、PSA10は生カードの3〜10倍の価格になることが多いです。ポケモンカードの場合、人気のSAR・URでPSA10が付くと、生カード相場の5倍以上になる例も珍しくありません。"
            },
            {
                "q": "PSA鑑定の費用と期間は?",
                "a": "2026年4月時点で、通常コースで1枚あたり約3,000〜5,000円、返却まで2〜3ヶ月かかります。エクスプレスコースは1枚1万円以上ですが2週間程度で返却されます。日本からの発送は代行業者を使うのが一般的です。"
            },
            {
                "q": "鑑定に出すべきカードの見極め方は?",
                "a": "生カードで10,000円以上の相場があり、白欠け・曲がり・センタリング・印刷ズレのないカードが対象です。PSA10想定で鑑定費用の3倍以上の相場があるカードなら黒字になる可能性が高いです。"
            }
        ]
    },
    {
        "file": "mercari-hikaku.html",
        "headline": "ポケカBOX売却はメルカリ・スニダン・買取店どれが得?",
        "description": "ポケカBOXを売るならメルカリ・スニダン・買取店どれが得?手数料・送料・手間を徹底比較。具体的な計算例で最適な売却方法がわかります。",
        "datePublished": "2026-03-26",
        "dateModified": "2026-03-26",
        "section": "ポケカBOX買取ガイド",
        "faq": [
            {
                "q": "メルカリで売る場合の手取りは?",
                "a": "販売価格の10%が販売手数料、送料が500〜1,000円程度、振込手数料200円を差し引いた金額が手取りです。例えば10,000円で売れた場合、手取りは約8,000〜8,500円程度になります。"
            },
            {
                "q": "スニダン(スニーカーダンク)のメリットは?",
                "a": "スニダンは本物鑑定込みでメルカリより安心感があり、売れやすいです。販売手数料は5.5%(2026年4月時点)と低めですが、配送がやや複雑です。10,000円で売れた場合の手取りは約9,000円程度。"
            },
            {
                "q": "買取店に売るメリットは?",
                "a": "即日現金化できる点と、面倒な梱包・発送・購入者対応が不要な点がメリットです。手取り額は市場価格の80〜90%程度になるため、急ぎでなければメルカリ/スニダンのほうが手取りは高くなります。"
            },
            {
                "q": "結局どれが一番お得?",
                "a": "手取り最大化を優先するならスニダン > メルカリ > 買取店 の順です。ただし、急ぎで現金化したい・手間を掛けたくない場合は買取店が最適です。ポケカ買取チェッカーで8店舗を比較すれば、買取店の中で最高値を即座に見つけられます。"
            }
        ]
    },
    {
        "file": "shrink-nashi.html",
        "headline": "シュリンクなしポケカBOXの買取事情",
        "description": "シュリンクなしポケカBOXの買取事情を徹底解説。買取店・メルカリ・スニダンでの価格差、対応店舗、高く売るコツまで。",
        "datePublished": "2026-03-27",
        "dateModified": "2026-03-27",
        "section": "ポケカBOX買取ガイド",
        "faq": [
            {
                "q": "シュリンクなしBOXは買取してもらえる?",
                "a": "店舗によります。森森買取・買取ホムラ・ラントゥ買取など一部店舗は対応していますが、価格はシュリンク付きの60〜80%程度に下がります。完全未開封(シュリンクのみ剥がれ)なら対応率が高く、開封済みだと買取不可の店舗が多いです。"
            },
            {
                "q": "シュリンクなしはなぜ価格が下がる?",
                "a": "シュリンクがないと「中身が入れ替えられていないか」「抜き取りがないか」の証明ができないため、店舗のリスクが上がります。そのリスクを吸収するために買取価格が下がります。"
            },
            {
                "q": "シュリンクなしBOXを高く売る方法は?",
                "a": "メルカリやスニダンなど個人間取引の方が買取店より高く売れる傾向があります。メルカリでは「完全未開封・シュリンクなし」と明記し、商品写真で全面を撮影すると購入者の安心感が増して高値で売れやすいです。"
            }
        ]
    },
    {
        "file": "monthly-ranking-2026-03.html",
        "headline": "【2026年3月】ポケカBOX買取 月間値上がりランキング",
        "description": "2026年3月のポケカ未開封BOX買取価格の値上がりランキング。151が約+1万円で1位、MEGAドリームexが+33.3%の上昇率トップ。8店舗の実データに基づく月間レポート。",
        "datePublished": "2026-04-01",
        "dateModified": "2026-04-01",
        "section": "月間レポート",
        "faq": []  # no FAQ for monthly report
    },
    {
        "file": "box-toushi.html",
        "headline": "ポケカBOX投資の始め方｜値上がりしやすいBOXの特徴とは",
        "description": "ポケカ未開封BOX投資の始め方を初心者向けに解説。値上がりしやすいBOXの特徴、予算別の始め方、保管方法、リスクまで。",
        "datePublished": "2026-04-02",
        "dateModified": "2026-04-02",
        "section": "ポケカ投資ガイド",
        "faq": [
            {
                "q": "ポケカBOX投資はいくらから始められる?",
                "a": "定価5,000円のBOX1箱から始められます。初心者はまず5〜10万円の予算で人気BOXを2〜3種類買って相場に慣れるのがおすすめです。余剰資金で行うのが鉄則で、生活資金を投入するのは避けてください。"
            },
            {
                "q": "値上がりしやすいBOXの特徴は?",
                "a": "①主力SAR/URの単価が高い ②再販が少ない/絶版になりやすい ③コレクター需要とプレイヤー需要の両方がある ④ポケモン25周年や記念弾 などが値上がりしやすい特徴です。過去の実例ではイーブイヒーローズ、VMAXクライマックス、151、クリムゾンヘイズなどが該当します。"
            },
            {
                "q": "保管方法で注意すべきことは?",
                "a": "①直射日光を避ける(シュリンクと印刷が劣化) ②湿度40〜60%を保つ(カビと反り防止) ③平積みで押しつぶさない ④温度変化の激しい場所を避ける、の4点が重要です。クローゼット奥や専用ケースに保管するのが一般的です。"
            },
            {
                "q": "BOX投資のリスクは?",
                "a": "①再販による相場下落 ②人気低下 ③保管事故(シュリンク剥がれ・カビ) ④詐欺(偽物・抜き取り品) などがリスクです。特に再販は価格を半減させることもあるため、1商品に集中投資するのではなく分散が重要です。"
            }
        ]
    },
    {
        "file": "restock-guide.html",
        "headline": "ポケカBOX再販情報の見つけ方｜入荷パターンと通知設定まとめ",
        "description": "ポケカBOXの再販情報を最速でキャッチする方法を解説。店舗別の入荷パターン、X通知設定、抽選・先着の攻略法、再販されやすいBOXの特徴まで。",
        "datePublished": "2026-04-10",
        "dateModified": "2026-04-10",
        "section": "ポケカBOX購入ガイド",
        "faq": [
            {
                "q": "ポケカBOXの再販情報はどこで確認する?",
                "a": "公式なら「ポケモンカードゲーム公式」のXアカウントとポケモンセンターオンライン、店舗ならAmazon・楽天ブックス・家電量販店(ヨドバシ/ビック)・カードショップ(カードラッシュ/カードラボ/駿河屋)のX公式アカウントが最速情報源です。"
            },
            {
                "q": "抽選販売と先着販売どちらが当たりやすい?",
                "a": "再販初期は抽選販売が多く、倍率10〜100倍のことも珍しくありません。先着販売は平日昼間の不定期時間(特に12〜14時/16〜18時)に多く、在庫通知botを使うと当選率が上がります。"
            },
            {
                "q": "再販されやすいBOXは?",
                "a": "①直近3ヶ月の新弾 ②人気SV系拡張パック(151、黒炎の支配者など) ③ハイクラスパック ④SAR封入BOX が再販されやすいです。逆に絶版指定された旧弾(イーブイヒーローズ等)は再販されないため中古相場が高止まりします。"
            },
            {
                "q": "再販情報を見逃さない通知設定は?",
                "a": "①X(Twitter)の各店舗公式アカウントの通知ONと検索ワード「再販」「入荷」をリスト化 ②Amazon在庫通知アプリ(Keepa等) ③Discord在庫通知サーバー ④楽天ブックスの在庫通知メール、を組み合わせると見逃しが減ります。"
            }
        ]
    },
]


def build_article_schema(art: dict) -> str:
    obj = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": art["headline"],
        "description": art["description"],
        "datePublished": art["datePublished"],
        "dateModified": art["dateModified"],
        "image": "https://pokeca-box-hikaku.com/ogp.jpg",
        "author": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー編集部",
            "url": "https://pokeca-box-hikaku.com/",
        },
        "publisher": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー",
            "logo": {
                "@type": "ImageObject",
                "url": "https://pokeca-box-hikaku.com/ogp.png",
            },
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://pokeca-box-hikaku.com/{art['file']}",
        },
        "articleSection": art["section"],
        "inLanguage": "ja",
    }
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n</script>"
    )


def build_faq_schema(faqs: list[dict]) -> str:
    if not faqs:
        return ""
    obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["q"],
                "acceptedAnswer": {"@type": "Answer", "text": f["a"]},
            }
            for f in faqs
        ],
    }
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n</script>"
    )


def main():
    for art in ARTICLES:
        path = ROOT / art["file"]
        if not path.exists():
            print(f"SKIP: {art['file']} (not found)")
            continue

        content = path.read_text(encoding="utf-8")

        # Idempotency: skip if already has BlogPosting schema
        if '"@type": "BlogPosting"' in content:
            print(f"SKIP: {art['file']} (already has BlogPosting)")
            continue

        article_schema = build_article_schema(art)
        faq_schema = build_faq_schema(art["faq"])

        new_schemas = article_schema
        if faq_schema:
            new_schemas += "\n" + faq_schema

        # Insert right before </head> (after existing BreadcrumbList script)
        if "</head>" not in content:
            print(f"ERROR: {art['file']} (no </head> found)")
            continue

        new_content = content.replace(
            "</head>",
            new_schemas + "\n</head>",
            1,
        )
        path.write_text(new_content, encoding="utf-8")
        print(f"OK: {art['file']} (+Article{'+FAQ' if faq_schema else ''})")


if __name__ == "__main__":
    main()
