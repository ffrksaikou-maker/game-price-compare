"""Generate index.html from template.html + price data."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .matcher import MasterProduct

logger = logging.getLogger(__name__)

# JST timezone
JST = timezone(timedelta(hours=9))

# Shop IDs in display order
SHOP_IDS = ["morimori", "homura", "icchome", "runto", "collect_tendo", "shinsoku", "kaikyo", "oku", "rudeya"]

# BOX individual images (gamepedia.jp + 楽天から取得、ユーザー目視確認済み)
BOX_IMAGE_FILES: dict[str, str] = {
    "151": "151.jpg",
    "25th-anniversary-collection": "25th-anniversary-collection.jpg",
    "ancient-roar": "ancient-roar.jpg",
    "astonishing-voltecker": "astonishing-voltecker.jpg",
    "battle-collection": "battle-collection.jpg",
    "battle-partners": "battle-partners.jpg",
    "battle-region": "battle-region.jpg",
    "black-bolt-dx": "black-bolt-dx.jpg",
    "black-bolt": "black-bolt.jpg",
    "blue-sky-stream": "blue-sky-stream.jpg",
    "chouden-breaker": "chouden-breaker.jpg",
    "clay-burst": "clay-burst.jpg",
    "crimson-haze": "crimson-haze.jpg",
    "cyber-judge": "cyber-judge.jpg",
    "dark-phantasma": "dark-phantasma.jpg",
    "eevee-heroes": "eevee-heroes.jpg",
    "eruption-walker": "eruption-walker.jpg",
    "fukuoka": "fukuoka.jpg",
    "fusion-arts": "fusion-arts.jpg",
    "future-flash": "future-flash.jpg",
    "hengen-no-kamen": "hengen-no-kamen.jpg",
    "hiroshima": "hiroshima.jpg",
    "incandescent-arcana": "incandescent-arcana.jpg",
    "inferno": "inferno.jpg",
    "infinity-zone": "infinity-zone.jpg",
    "jet-black-geist": "jet-black-geist.jpg",
    "legendary-heartbeat": "legendary-heartbeat.jpg",
    "lost-abyss": "lost-abyss.jpg",
    "matchless-fighters": "matchless-fighters.jpg",
    "mega-brave": "mega-brave.jpg",
    "mega-ex": "mega-ex.jpg",
    "mega-sinfonia": "mega-sinfonia.jpg",
    "munikis-zero": "munikis-zero.jpg",
    "neppuu-arena": "neppuu-arena.jpg",
    "night-wanderer": "night-wanderer.jpg",
    "ninja-spinner": "ninja-spinner.jpg",
    "paradigm-trigger": "paradigm-trigger.jpg",
    "pokemon-go": "pokemon-go.jpg",
    "raging-surf": "raging-surf.jpg",
    "rakuen-dragona": "rakuen-dragona.jpg",
    "rapid-strike-master": "rapid-strike-master.jpg",
    "rebellion-crash": "rebellion-crash.jpg",
    "rocket-dan-no-eiko": "rocket-dan-no-eiko.jpg",
    "ruler-of-black-flame": "ruler-of-black-flame.jpg",
    "scarlet-ex": "scarlet-ex.jpg",
    "shield": "shield.jpg",
    "shiny-star": "shiny-star.jpg",
    "shiny-treasure-ex": "shiny-treasure-ex.jpg",
    "silver-lance": "silver-lance.jpg",
    "single-strike-master": "single-strike-master.jpg",
    "skyscraping-perfect": "skyscraping-perfect.jpg",
    "snow-hazard": "snow-hazard.jpg",
    "space-juggler": "space-juggler.jpg",
    "star-birth": "star-birth.jpg",
    "stellar-miracle": "stellar-miracle.jpg",
    "sword": "sword.jpg",
    "terastal-fes-ex": "terastal-fes-ex.jpg",
    "time-gazer": "time-gazer.jpg",
    "tohoku": "tohoku.jpg",
    "triplet-beat": "triplet-beat.jpg",
    "wild-force": "wild-force.jpg",
    "violet-ex": "violet-ex.jpg",
    "vmax-climax": "vmax-climax.jpg",
    "vmax-rising": "vmax-rising.jpg",
    "vstar-universe": "vstar-universe.jpg",
    "white-flare-dx": "white-flare-dx.jpg",
    "white-flare": "white-flare.jpg",
}

BASE_URL = "https://pokeca-box-hikaku.com"
DEFAULT_OG_IMAGE = f"{BASE_URL}/ogp.jpg"

# 薄ページnoindex判定の免除ライン。絶版高額BOXは買取対応店が2店程度まで減るが
# 検索需要は大きいため、この金額以上は店舗数によらずインデックス対象にする
HIGH_VALUE_BOX_PRICE = 30000


def get_box_image_url(slug: str) -> str:
    """Return the full URL for a BOX's primary image.
    Returns the individual image if available, else the default OGP image.
    """
    filename = BOX_IMAGE_FILES.get(slug)
    if filename:
        return f"{BASE_URL}/images/boxes/{filename}"
    return DEFAULT_OG_IMAGE

# Blog articles (newest first) - 記事追加時はここに1行足すだけ
BLOG_ARTICLES = [
    {"url": "weekly/", "title": "【今週】ポケカBOX 週間値動きランキング", "desc": "SV・MEGA TOP10 + S&S TOP3を毎日自動更新。9店舗実データから直近7日間で値上がり・値下がりしたBOXをグラフ付きで掲載。現在の下落トレンドもひと目で分かる。", "date": "2026-04-12"},
    {"url": "souba-mynumber-2026.html", "title": "ポケカ相場は下落から膠着へ｜30周年マイナンバー導入の影響", "desc": "直近30日で67BOX中49が下落(平均-9.5%)、直近7日は53BOXが横ばい=膠着へ。ポケモンセンター30周年記念商品の抽選にマイナンバーカード本人確認が導入決定。転売対策が相場に与える影響を当サイト実データと公式発表・専門家見解で解説。", "date": "2026-06-09"},
    {"url": "sv-box-list.html", "title": "SV(スカーレット&バイオレット) 全BOX一覧", "desc": "SVシリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗実データで一覧化。151/黒炎の支配者/超電ブレイカー/ロケット団の栄光などの最新相場を毎日自動更新。", "date": "2026-04-22"},
    {"url": "mega-box-list.html", "title": "MEGA(メガシンカ) 全BOX一覧", "desc": "MEGAシリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗実データで一覧化。メガブレイブ/メガシンフォニア/インフェルノX/ニンジャスピナー/ムニキスゼロの相場を毎日自動更新。", "date": "2026-04-22"},
    {"url": "ss-box-list.html", "title": "S&S(ソード&シールド) 全BOX一覧", "desc": "S&Sシリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗実データで一覧化。イーブイヒーローズ/VMAXクライマックス/25thアニバーサリーなど絶版BOX中心。", "date": "2026-04-22"},
    {"url": "battle-collection-spotlight.html", "title": "スタートデッキ100が大暴落？ピーク¥4,300→¥2,800", "desc": "MEGA スタートデッキ100「バトルコレクション」のBOX買取が4月ピーク¥4,300→¥2,800へ約35%下落。看板メガリザードンYex MUR(No.001)が5月12日の100万円→6月初旬の94.4万円へ反落したのと連動。下落4つの理由・店舗別買取・今後3シナリオ・売り時を実データで解説。", "date": "2026-06-06"},
    {"url": "release-schedule-2026.html", "title": "2026年ポケカ新弾発売カレンダー", "desc": "ムニキスゼロ・ニンジャスピナー発売済み、アビスアイ(5/22発売決定・メガダークライex)、5月値上げ(180→200円)、商標予想(ストームエメラルダ等)、30周年記念商品(世界同時発売)まで完全整理。", "date": "2026-04-21"},
    {"url": "storm-emeralda-spotlight.html", "title": "【徹底解剖】ストームエメラルダはなぜ高騰したのか・5年後¥70,000も狙える理由", "desc": "発売日に定価×4.17倍という、当サイト観測でMEGA弾史上最強の初動を記録したストームエメラルダ。高騰要因をメガレックウザex MUR(買取約15.8万・約51BOXに1枚)の射幸性・環境Tier1の対戦実需・ポケポケ同時展開・供給制約の4軸で分解し、68BOXの経過年数別倍率(1年×4.02/3年×2.67/5年×8.08)が描くU字カーブから1年後¥21,000・3年後¥30,000・5年後¥70,000(中立)を予想。", "date": "2026-08-10"},
    {"url": "storm-emeralda-review.html", "title": "【答え合わせ】ストームエメラルダ初動BOXは¥25,000・強気シナリオがほぼ的中", "desc": "2026-07-31発売のストームエメラルダBOX初動が¥25,000(定価×4.17倍)で着地。6月公開の3シナリオ予想を9店舗実データで答え合わせ。確率35%の強気シナリオがほぼ的中し、最有力の中立¥15,000は+67%の大外し。メガレックウザex MURが予想の2倍で始まった影響と、発売3日で-12.8%の調整局面を解説。", "date": "2026-08-02"},
    {"url": "storm-emeralda-forecast.html", "title": "【発売前予想】ストームエメラルダ BOX相場3シナリオ", "desc": "2026-07-31発売のストームエメラルダBOX相場を、過去MEGA弾M1〜M5の最新実データ+レックウザ三巨頭人気+蒼空ストリームの系譜から3シナリオ(弱気¥10,000/中立¥15,000/強気¥30,000)で徹底予想。メガレックウザex封入率・投資判断3基準も解説。", "date": "2026-06-22"},
    {"url": "abyss-eye-forecast.html", "title": "【発売前予想】アビスアイ BOX相場3シナリオ", "desc": "2026-05-22発売のアビスアイBOX相場を、過去MEGA弾M1〜M4の実データ+ダークライ人気+値上げ後初パックの歴史から3シナリオ(弱気¥9,600/中立¥15,000/強気¥30,000)で徹底予想。投資判断3基準とリスク要因も解説。", "date": "2026-04-21"},
    {"url": "abyss-eye-review.html", "title": "【発売日答え合わせ】アビスアイ初動BOXは¥13,500・中立シナリオほぼ的中", "desc": "2026-05-22発売のアビスアイBOX初動が¥13,500(定価×2.25倍)で着地。4月公開の3シナリオ予想を9店舗実データで答え合わせ。中立予想ほぼ的中の3つの理由、過去MEGA弾との発売日比較、これからの注目ポイントを解説。", "date": "2026-05-22"},
    {"url": "inferno-x-spotlight.html", "title": "インフェルノXが定価の5倍に高騰", "desc": "発売半年で定価¥5,400→¥27,000(約5倍)に急騰したインフェルノXの相場推移、収録カード、3つの高騰理由を実データで徹底解説。", "date": "2026-04-12"},
    {"url": "chouden-breaker-spotlight.html", "title": "超電ブレイカーが定価7.5倍に高騰", "desc": "BOX買取¥40,700、定価の7.5倍に達した超電ブレイカー(SV8)。ピカチュウex SAR¥55,000・ぎどら氏イラストの高騰5つの理由、Jレギュ前のスタン現役期の今後を解説。", "date": "2026-04-15"},
    {"url": "clay-burst-spotlight.html", "title": "クレイバーストとナンジャモSAR相場解説", "desc": "BOX買取¥12,200、Gレギュ絶版観測で再評価中のクレイバースト(SV2D)。ナンジャモSAR¥50,000・PSA10で¥108,000・kirisAki氏イラストを含む5つの注目理由を解説。", "date": "2026-04-15"},
    {"url": "ninja-spinner-spotlight.html", "title": "ニンジャスピナー(M4)が定価2.5倍に高騰", "desc": "BOX買取¥13,400、メガゲッコウガex MUR¥95,000(封入率約0.9〜2%)・SAR¥40,000(前屋進氏イラスト進化ライン一枚絵)・HP350の対戦実需・180円定価最後のMEGA弾の5つの高騰理由を解説。", "date": "2026-04-16"},
    {"url": "rocket-dan-no-eiko-spotlight.html", "title": "ロケット団の栄光(SV10)が定価5.8倍に高騰", "desc": "BOX買取¥31,500、ロケット団のミュウツーex SAR¥60,000(PSA10¥120,000)・20年ぶりロケット団メインパック・2026年30周年イヤー連動・悪路線構築需要の5つの高騰理由を解説。週間急上昇1位(+21.2%)。", "date": "2026-04-25"},
    {"url": "monthly-ranking-2026-07.html", "title": "【2026年7月】ポケカBOX買取 月間値上がりランキング", "desc": "2026年7月に最も値上がりしたポケカ未開封BOXを10店舗の実データで集計。超電ブレイカー(+¥4,000)・ブラックボルトDX(+¥3,700)・ホワイトフレアDX(+¥3,000)がTOP3。SV・MEGA(現役)を本体TOP10、S&S(旧)を参考TOP5として別枠掲載。", "date": "2026-08-01"},
    {"url": "monthly-ranking-2026-06.html", "title": "【2026年6月】ポケカBOX買取 月間値上がりランキング", "desc": "2026年6月のポケカ未開封BOX買取 値上がりランキング。現役シリーズで上昇したのはクレイバースト(+¥400)とムニキスゼロ(+¥200)の2銘柄のみという静かな月でした。9店舗の実データで集計し、S&S(旧)は参考TOP5として別枠掲載。", "date": "2026-07-01"},
    {"url": "monthly-ranking-2026-05.html", "title": "【2026年5月】ポケカBOX買取 月間値上がりランキング", "desc": "2026年5月のポケカ未開封BOX買取 値上がりランキング。上昇はスペシャルBOX トウホク(+¥500)・ナイトワンダラー(+¥400)・古代の咆哮(+¥300)と小幅で、相場が凪いだ月でした。9店舗の実データで集計し、S&S(旧)は参考TOP5として別枠掲載。", "date": "2026-06-01"},
    {"url": "monthly-ranking-2026-04.html", "title": "【2026年4月】ポケカBOX買取 月間値上がりランキング", "desc": "2026年4月に最も値上がりしたポケカ未開封BOXを9店舗の実データで集計。SV・MEGA(現役)を本体TOP10、S&S(旧)を参考TOP5として別枠掲載。151(+¥17,600)・超電ブレイカー(+¥16,400)・ロケット団の栄光(+¥13,000)がSV+MEGA TOP3。", "date": "2026-05-01"},
    {"url": "mega-ex-spotlight.html", "title": "MEGAドリームex(M2a)が定価3.2倍にW字回復", "desc": "BOX買取¥17,500、発売初動¥17,300→1月底値¥9,000台→5月¥17,500の見事なW字回復。メガゲンガーex SAR¥66,200・ピカチュウex SAR¥60,000・メガカイリューex MUR¥40,000-57,300・新レアリティMA(全10種)・お祭りパック性の5つの高騰理由を解説。", "date": "2026-05-03"},
    {"url": "mega-brave-spotlight.html", "title": "メガブレイブ(M1)が定価2.6倍で推移", "desc": "BOX買取¥13,800、MEGAシリーズ第1弾の記念パック。リーリエの決心SAR¥30,000台(PSA10¥95,000)・メガルカリオex MUR¥42,000台(封入率約1.64%)・世界人気2位ルカリオ・対戦環境での優勝レシピ実績・MEGA記念弾の節目性の5つの高騰理由を実データで解説。", "date": "2026-05-19"},
    {"url": "price-pattern-guide.html", "title": "BOX買取価格の5段階パターン", "desc": "発売前プレ値→初動高値→調整期→底打ち→絶版急騰の5段階を当サイト40日観測データと5スポットライトBOXの具体値で実証解説。買い時売り時の3判断基準、2024年バブル崩壊の教訓も紹介。", "date": "2026-04-16"},
    {"url": "151-spotlight.html", "title": "ポケモンカード151がなぜ高い？定価12倍超え", "desc": "BOX買取¥68,200、定価の12.6倍に達した151の絶版観測、5つの高騰理由、今後どこまで上がるかの3シナリオを実データで解説。", "date": "2026-04-14"},
    {"url": "kokuen-spotlight.html", "title": "黒炎の支配者が定価の約4倍に高騰", "desc": "BOX買取¥21,200、Gレギュ絶版観測で上昇継続中。リザードンex SAR(悪テラスタル)を筆頭に5つの高騰理由と今後の予想を解説。", "date": "2026-04-14"},
    {"url": "zeppan-ranking-2026-03.html", "title": "S&S以降 絶版BOXランキング", "desc": "Gレギュスタン落ち済みBOXを中心に、絶版観測・事実上絶版のBOXを相場順ランキング。中長期投資の判断材料に。", "date": "2026-04-14"},
    {"url": "lizardon-box-guide.html", "title": "リザードン高騰BOX完全ガイド", "desc": "151・黒炎の支配者・インフェルノXなどリザードン封入BOXを横断比較。なぜリザードン系は例外なく高額化するのかを解説。", "date": "2026-04-14"},
    {"url": "mega-pack-compare.html", "title": "MEGA拡張パック完全比較", "desc": "メガブレイブ・メガシンフォニア・インフェルノX・MEGAドリームex・ニンジャスピナーのMEGAシリーズ全体を相場・封入率で徹底比較。", "date": "2026-04-14"},
    {"url": "kokuen-vs-rocket.html", "title": "黒炎 vs ロケット団の栄光 徹底比較", "desc": "人気対決BOX2つを相場・目玉SAR・絶版観測・開封期待値で多角比較。どちらに投資すべきかを6観点で評価。", "date": "2026-04-14"},
    {"url": "mega-lizardon-x-guide.html", "title": "メガリザードンXex MUR/SAR 相場解説", "desc": "MUR¥200,000/SAR¥95,000に急騰したインフェルノX目玉カード。1ヶ月で1.8倍急騰の理由と今後の予想を徹底解説。", "date": "2026-04-14"},
    {"url": "lizardon-sar-kokuen-guide.html", "title": "リザードンex SAR(黒炎)相場解説", "desc": "買取¥37,000・PSA10で¥65,900の黒炎SAR。江川あきら氏イラストと悪テラスタル形態で高騰継続中のカードを詳解。", "date": "2026-04-14"},
    {"url": "erika-sar-guide.html", "title": "エリカの招待SAR 相場解説", "desc": "買取¥8,000・PSA10で¥33,400の151人気SAR。初動¥128,200からの調整と151絶版観測での再上昇を予想。", "date": "2026-04-14"},
    {"url": "pigeot-sar-guide.html", "title": "ピジョットex SAR 相場解説", "desc": "「ピジョリザ」デッキ必須の対戦用SAR。マッハサーチ特性とプレイヤー需要で安定相場の実用SARを徹底解説。", "date": "2026-04-14"},
    {"url": "masterball-mirror-guide.html", "title": "151マスターボールミラー 相場解説", "desc": "全153種のマスターボールミラーをピカチュウ¥55,000・ゲンガー¥60,000などの相場と封入率・コンプ難易度で解説。", "date": "2026-04-14"},
    {"url": "30th-celebration-atari-yosou.html", "title": "【発売前予想】30th CELEBRATION 当たりカード｜FURミュウツーexはいくらになる？", "desc": "2026年9月16日発売のポケカ30周年記念パック「30th CELEBRATION」の当たりカードを発売前予想。史上初の新レアリティFURのミュウツーex(発売直後 約¥90,000と予想)・ミュウex・ピカチュウexの価格を、25周年パックの実績(当サイト実データで定価×13.09)と新レアリティ「アメイジングレア」初登場時の実データから推定。各パック1枚確定のピカチュウ30種が1枚あたり薄まる構造も、26弾の追跡データから解説します。", "date": "2026-08-11"},
    {"url": "30th-celebration-forecast.html", "title": "【抽選締切8/14】30th CELEBRATION BOX3種の相場予想｜1年後・3年後・5年後", "desc": "ポケカ30周年「30th CELEBRATION」の抽選対象BOX3種(拡張パックBOX 定価¥7,200/FUTURISTIC BOX ¥27,500/プレミアムデッキセット エーフィ・ブラッキー ¥6,200)の相場を発売前予想。25周年商品の実績(25thコレクションが当サイト実データで定価×13.09、GOLDEN BOXが最大×15)を土台に、発売直後・1年後・3年後・5年後を3シナリオで算出。ポケモンセンターオンラインの抽選締切は2026年8月14日16:59、発売は9月16日世界同時。", "date": "2026-08-11"},
    {"url": "eruption-walker-atari-guide.html", "title": "爆炎ウォーカー 当たりカードランキング｜BOX¥42,000に対し最高額カードは約3,500円", "desc": "強化拡張パック「爆炎ウォーカー」の当たりカードランキングと封入率。最高額はサーナイトVMAX HRで買取約3,500円と当サイト追跡26弾で2番目に中身が安い弾。一方で未開封BOXは¥42,000(定価×8.48)、カード/BOX比0.083倍。同じサーナイトでもスカーレットexのex SAR(約22,000円)とは約6.3倍差があり、SAR/SAという受け皿の有無が価格を左右することを示します。2020年発売6弾の総括も収録。", "date": "2026-08-11"},
    {"url": "legendary-heartbeat-atari-guide.html", "title": "伝説の鼓動 当たりカードランキング｜上位6枚すべてがアメイジングレア", "desc": "強化拡張パック「伝説の鼓動」の当たりカードランキングと封入率。上位6枚すべてをアメイジングレア(A)が占める唯一の構成で、1位レックウザAは買取約15,000円。アメイジングレアが初登場した弾です。BOX買取¥40,000(定価×8.08)に対し最高額カードは約0.375倍で、2020年発売弾に共通する希少性牽引型。同じレックウザでも収録弾とレアリティで約53倍差がつく構造も解説。", "date": "2026-08-11"},
    {"url": "vmax-climax-atari-guide.html", "title": "VMAXクライマックス 当たりカードランキング｜上位8枚すべてが7,000円超の層厚型", "desc": "ハイクラスパック「VMAXクライマックス」の当たりカードランキングと封入率。1位レックウザVMAX UR(約29,000円)から8位ニンフィアVMAX CSR(約7,000円)まで上位8枚すべてが7,000円を超え、1位と8位の差はわずか約4.1倍。当サイト追跡24弾でもっとも層の厚い弾です。BOX買取¥37,500(定価¥5,500・×6.82)。CSRを擁するハイクラスパック特有の設計と、同じレックウザVMAXでも弾とレアリティで約27倍差がつく構造を解説。", "date": "2026-08-11"},
    {"url": "astonishing-voltecker-atari-guide.html", "title": "仰天のボルテッカー 当たりカードランキング｜ピカチュウVMAX HRは買取約6.5万円", "desc": "拡張パック「仰天のボルテッカー」の当たりカードランキングと封入率。ピカチュウVMAX HRは買取約65,000円でBOX買取¥45,000(定価×9.09)の約1.44倍。SA(スペシャルアート)が存在しない2020年発売の弾でありながらカード/BOX比が1を超えた唯一の例で、当サイトの「2020年＝希少性牽引型」という仮説を修正することになった弾です。看板カードの到達点こそが型を決めることを示します。", "date": "2026-08-11"},
    {"url": "matchless-fighters-atari-guide.html", "title": "双璧のファイター 当たりカードランキング｜バシャーモVMAX SAは買取約9万円", "desc": "強化拡張パック「双璧のファイター」の当たりカードランキングと封入率。バシャーモVMAX SAは買取約90,000円でBOX買取¥40,000(定価×8.08)の約2.25倍。上位8枚のうち5枚をSAが占める層の厚い弾です。ガラル三鳥のSAが3枚そろいながらファイヤー(約45,000円)とサンダー(約6,500円)で約6.9倍の差が生じる構造と、基本闘エネルギーURが収録弾によって約1.68倍変わる事実も解説。", "date": "2026-08-11"},
    {"url": "lost-abyss-atari-guide.html", "title": "ロストアビス 当たりカードランキング｜ギラティナV SAは買取約22万円で過去最高倍率", "desc": "拡張パック「ロストアビス」の当たりカードランキングと封入率。ギラティナV SAは買取約220,000円で、BOX買取¥49,000(定価×9.90)の約4.5倍。当サイト追跡23弾でカード/BOX比の最高記録で、蒼空ストリーム(2.81倍)を上回ります。2位プテラV SA(約12,000円)との差は約18倍と断層も過去最大。1枚引けばBOX4.5箱分という極端な構造を実データで解説。", "date": "2026-08-11"},
    {"url": "single-strike-master-atari-guide.html", "title": "一撃マスター 当たりカードランキング｜バンギラスV SAが看板に迫る二強型", "desc": "拡張パック「一撃マスター」の当たりカードランキングと封入率。1位いちげきウーラオスVMAX SA(約47,000円)と2位バンギラスV SA(約40,000円)の差はわずか約1.2倍で、当サイト追跡21弾中もっとも拮抗した二強型です。V の SAは通常VMAX SAの5〜19%にとどまるなか、バンギラスV SAは看板の約85%に到達。同日・同定価発売の連撃マスターとの比較でBOX価格の決まり方も解説します。", "date": "2026-08-11"},
    {"url": "rapid-strike-master-atari-guide.html", "title": "連撃マスター 当たりカードランキング｜れんげきウーラオスVMAX SAは買取約7万円", "desc": "拡張パック「連撃マスター」の当たりカードランキングと封入率。れんげきウーラオスVMAX SAは買取約70,000円でBOX買取¥50,000(定価×10.10)の約1.4倍。同日・同定価で発売された一撃マスター(BOX¥40,000)と比較すると、上位3枚の合計額では一撃マスターが上回るのにBOX価格は連撃マスターが高く、BOX価格を決めるのは2番手の厚みではなく最高額カード1枚だと分かります。", "date": "2026-08-11"},
    {"url": "infinity-zone-atari-guide.html", "title": "ムゲンゾーン 当たりカードランキング｜BOX1箱=最高額カード約28枚分という極端な弾", "desc": "拡張パック「ムゲンゾーン」の当たりカードランキングと封入率。最高額はキャプチャーエネルギーURで買取約1,700円、上位8枚すべてが2,000円未満と当サイト追跡68BOX中もっとも中身が安い弾。一方で未開封BOXは¥48,000(定価×9.70)で、カード/BOX比0.035倍は当サイト調査で最低記録。看板ムゲンダイナVMAX HRが4位にとどまる理由とSA登場前という時代背景を、2つの独立ソースで裏取りして解説。", "date": "2026-08-11"},
    {"url": "rebellion-crash-atari-guide.html", "title": "反逆クラッシュ 当たりカードランキング｜1位はポケモンではなくボスの指令SR", "desc": "拡張パック「反逆クラッシュ」の当たりカードランキングと封入率。1位はトレーナーズの「ボスの指令(サカキ)」SRで買取約19,000円、2位も同カードのHRで約14,000円と上位2枚で市場が完結。対戦での実用需要が相場を作った弾です。BOX買取¥52,000(定価×10.51)に対しカードは約0.37倍で、VMAXライジングと並ぶ希少性牽引型。SA登場前の2020年前半という共通点も解説。", "date": "2026-08-11"},
    {"url": "fusion-arts-atari-guide.html", "title": "フュージョンアーツ 当たりカードランキング｜ミュウVMAX SAは買取約14万円", "desc": "拡張パック「フュージョンアーツ」の当たりカードランキングと封入率。ミュウVMAX SAは買取約140,000円でBOX買取¥55,000(定価×11.11)の約2.5倍。上位4枚をミュウ関連が独占する一方、同じSAのゲノセクトVは約2,000円と70倍差で、レアリティより人気が価格を決める構造を実証。基本エネルギーURは炎・草の2種を収録し7タイプ目のデータが揃いました。", "date": "2026-08-11"},
    {"url": "vmax-rising-atari-guide.html", "title": "VMAXライジング 当たりカードランキング｜カードよりBOXが7.5倍高い異例の弾", "desc": "拡張パック「VMAXライジング」の当たりカードランキングと封入率。最高額はソニアSRで買取約16,000円ですが、未開封BOXは¥120,000(定価×24.24)。カード/BOX比0.13倍は蒼空ストリーム(2.81倍)の約21分の1で、当サイト追跡68BOX中もっとも「開けるほど損」が明確な弾です。S&S第1弾という位置・ブーム前の生産量・SA登場前という時代差から、希少性牽引型のBOX価格を実データで解説。", "date": "2026-08-10"},
    {"url": "blue-sky-stream-atari-guide.html", "title": "蒼空ストリーム 当たりカードランキング｜レックウザVMAX SAは買取約80万円", "desc": "拡張パック「蒼空ストリーム」の当たりカードランキングと封入率。レックウザVMAX SAは買取約80万円と当サイト調査で断トツの最高額で、BOX買取¥285,000(定価×57.58)も追跡68BOX中トップ。上位5枚のうち4枚をレックウザ関連が占める集中構造、SA封入率約4BOXに1枚(全4種)、同日同定価発売の摩天パーフェクト(¥18,000)との約16倍差、メガレックウザ(ストームエメラルダ)との系譜を実データで解説。", "date": "2026-08-10"},
    {"url": "battle-partners-atari-guide.html", "title": "バトルパートナーズ 当たりカードランキング｜リーリエのピッピex SARと4キャラ分散の構造", "desc": "拡張パック「バトルパートナーズ」の当たりカードランキング。リーリエのピッピex SAR(買取約17,000円)が最高額。リーリエ・ナンジャモ・N・ホップという人気キャラ4組にSAR枠が分散した結果、2ヶ月後発売で2キャラ集中の熱風のアリーナ(BOX¥20,000)に対し本弾は¥10,800と約85%の差。変幻の仮面のオーガポン4姿分散と同じ「豪華な収録が1枚あたりの価値を下げる」構造を解説。", "date": "2026-08-10"},
    {"url": "neppuu-arena-atari-guide.html", "title": "熱風のアリーナ 当たりカードランキング｜シロナのガブリアスexとヒビキのホウオウexの二強", "desc": "強化拡張パック「熱風のアリーナ」の当たりカードランキング。シロナのガブリアスex SAR(買取約33,000円)とヒビキのホウオウex SAR(約29,000円)の二強で、上位8枚のうち5枚をこの2キャラの別レアリティ版が占める多層構造。最高額がほぼ同じクレイバースト(BOX¥11,500)に対し本弾は¥20,000(×3.70)と約74%高く、受け皿の層の厚さがBOX相場を決めることを実証。UR約10BOXに1枚・AR1BOX3枚確定。", "date": "2026-08-10"},
    {"url": "snow-hazard-atari-guide.html", "title": "スノーハザード 当たりカードランキング｜最高額9倍のクレイバーストにBOX相場で勝つ理由", "desc": "強化拡張パック「スノーハザード」(SV2P)の当たりカードランキング。パオジアンex SAR(約3,500円)が最高額。同日発売クレイバーストの最高額ナンジャモSARは約32,000円と9倍だが、BOX買取はスノーハザード¥12,800が¥11,500を上回る逆転が発生。BOX相場を決めるのは最高額ではなく「最高額×引ける確率」であることを実データで解説。基本水エネルギーURで4タイプ目の比較表も掲載。", "date": "2026-08-10"},
    {"url": "cyber-judge-atari-guide.html", "title": "サイバージャッジ 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「サイバージャッジ」(SV5M)の当たりカードランキング。ベルのまごころ SAR(買取約5,000円)が最高額で、上位8枚のうち3枚をAR枠(シキジカ・メブキジカ・ニャビー)が占める構成。シキジカ ARはSAR2枚を上回る。「未来」テーマのテツノ系が3,000円以下に伸び悩んだ理由と、同日発売ワイルドフォース(¥14,400)との12%差を解説。BOX買取¥12,800。", "date": "2026-08-10"},
    {"url": "triplet-beat-atari-guide.html", "title": "トリプレットビート 当たりカードランキング｜コイキングARがBOX買取を超える唯一の弾", "desc": "強化拡張パック「トリプレットビート」(SV1a)の当たりカードランキング。AR(アートレア)のコイキングが買取約19,000円で1位、2位マスカーニャex SAR(約7,500円)の2.5倍という異例の構成。カンダシンジ氏のイラスト人気・コイキングの知名度・AR30種の希少性が重なりレアリティの序列が崩壊。1枚でBOX買取¥18,600を上回る当サイト調査で唯一「開封に勝ち筋がある」弾。", "date": "2026-08-10"},
    {"url": "ancient-roar-atari-guide.html", "title": "古代の咆哮 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「古代の咆哮」(SV4K)の当たりカードランキングを解説。トドロクツキex SARと基本悪エネルギー URがともに買取約5,500円で1位タイという珍しい構成。基本エネルギーURが他弾(基本闘・基本鋼は各約2,200円)の2.5倍をつける理由をタイプ別需要から分析。同日発売の未来の一閃との比較も掲載。BOX買取¥13,000。", "date": "2026-08-10"},
    {"url": "wild-force-atari-guide.html", "title": "ワイルドフォース 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「ワイルドフォース」(SV5K)の当たりカードランキングを解説。マツバの確信 SAR(買取約6,000円)が最高額、2位にSR枠のゲンガーex(約5,500円)が入りSARを上回る珍しい構成。上位8枚のうち3枚がゲンガー系統で、テーマの古代パラドックスを人気が凌駕。同日発売サイバージャッジとの比較も。BOX買取¥14,400。", "date": "2026-08-10"},
    {"url": "stellar-miracle-atari-guide.html", "title": "ステラミラクル 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「ステラミラクル」(SV7a)の当たりカードランキング・封入率を解説。タロ SAR(買取約4,000円)を筆頭に上位4枚が3,000〜4,000円に密集する天井の低い構成。SARが全6種と多く単独看板が不在なのが理由。『ゼロの秘宝』主役のテラパゴスex SARが3位という「テーマの主役≠相場の主役」の実例も整理。BOX買取¥13,100。", "date": "2026-08-10"},
    {"url": "scarlet-ex-atari-guide.html", "title": "スカーレットex 当たりカードランキング・封入率完全ガイド", "desc": "SVシリーズ第1弾「スカーレットex」(SV1S)の当たりカードランキングを解説。看板サーナイトex SAR(買取約2.2万円)が2位コライドンex SAR(約5,000円)に4.4倍差の一強。基本闘エネルギー UR(約2,200円)とネストボール UR(約1,500円)が3位・5位に入るSV初期特有の構造、同日発売バイオレットexとの28%の相場差も実データで整理。", "date": "2026-08-10"},
    {"url": "future-flash-atari-guide.html", "title": "未来の一閃 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「未来の一閃」(SV4M)の当たりカードランキング・封入率を解説。看板チルタリスex SAR(買取約8,000円)、テツノブジンex SAR、基本鋼エネルギー UR(約2,200円)とカウンターキャッチャー URの2つのUR枠。SAR封入率約5〜6BOXに1枚(全5種)。BOX買取¥11,800と同日発売の古代の咆哮との比較も掲載。", "date": "2026-08-10"},
    {"url": "raging-surf-atari-guide.html", "title": "レイジングサーフ 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「レイジングサーフ」の当たりカードランキング・封入率を解説。モブキャラながらイラスト人気で看板を超えたパラソルおねえさん SAR(買取約6,000円)を筆頭に、ガブリアスex SAR・サーフゴーex SAR・グラードン ARまで上位8枚が2,200〜6,000円に分散。SAR封入率は約10BOXに1枚と他のSV弾(約6BOX)より厳しい。BOX買取¥14,600との比較も掲載。", "date": "2026-08-10"},
    {"url": "night-wanderer-atari-guide.html", "title": "ナイトワンダラー 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「ナイトワンダラー」(SV6a)の当たりカードランキング・封入率を解説。最高額キチキギスex SAR(買取約2,500円)と控えめで上位8枚が900〜2,500円に密集する一方、BOX買取は¥12,800(定価×2.37)を維持。高額SARではなくキチキギスexや汎用グッズURの対戦実需が相場を支える構造を実データで解説。", "date": "2026-08-10"},
    {"url": "rakuen-dragona-atari-guide.html", "title": "楽園ドラゴーナ 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「楽園ドラゴーナ」(SV7)の当たりカードランキング・封入率を解説。ラティアスex SAR(買取約2.2万円)とルチアのアピール SAR(約1.9万円)が差14%で拮抗する珍しい二強構造。3位アローラナッシーex SARとは8倍の落差。SAR約6BOXに1枚(全5種)・SR以上1BOX確定の封入率とBOX期待値を実データで整理。", "date": "2026-08-10"},
    {"url": "hengen-no-kamen-atari-guide.html", "title": "変幻の仮面 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「変幻の仮面」(SV6)の当たりカードランキング・封入率を解説。看板ゼイユ SAR(買取約1.4万円)は2位スグリ SAR(約3,000円)に4倍以上の差。オーガポン4姿のex SARは分散収録で1枚あたり1,100〜2,200円、実用枠のなかよしポフィンUR、AR最高額ラッキー。SAR約6BOXに1枚・SR約1.2BOXに1枚の封入率とBOX期待値を実データで整理。", "date": "2026-08-10"},
    {"url": "crimson-haze-atari-guide.html", "title": "クリムゾンヘイズ 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「クリムゾンヘイズ」(SV5a)の当たりカードランキング・封入率を解説。看板ゲッコウガex SAR(買取約4.4万円)は2位サザレ SAR(約9,500円)に4倍以上の差をつける一強構成。AR枠ながら約4,000円のイーブイAR、SAR封入率約6BOXに1枚(全5種)、ACE SPEC1BOX確定、BOX開封の期待値まで実データで整理。", "date": "2026-08-10"},
    {"url": "kokuen-atari-guide.html", "title": "黒炎の支配者 当たりカード完全ガイド", "desc": "SAR/UR/SR/AR/RR 全41種の当たりカードを買取相場・封入率・期待値で徹底整理。リザードンex SAR一強の実態も解説。", "date": "2026-04-14"},
    {"url": "startdeck100-miwakekata.html", "title": "スタートデッキ100 当たりの見分け方【完全手順】", "desc": "スタートデッキ100の当たりの見分け方を手順で解説。デッキ番号は青い外箱と透明シュリンクの2段階内側にあり開封前は判別不可。開封後3ステップの判定フロー、全ミラーデッキ(12/101・約11.9%)を1枚目で見抜く方法、ミラーと当たり番号が別軸である点、「重さで分かる」説の真相と推奨しない3つの理由、未開封購入時の注意まで。", "date": "2026-08-10"},
    {"url": "startdeck100-atari-guide.html", "title": "スタートデッキ100 当たり番号一覧・見分け方完全ガイド", "desc": "スタートデッキ100「バトルコレクション」の当たり番号一覧・見分け方・封入率を解説。最高当たりNo.001(金)メガリザードンYex MUR約94万円、No.025ピカチュウex SAR・No.032リーリエのピッピex SAR・隠しNo.101 ZA御三家SARまで。開封前は見分け不可の理由と開封後のチェック法、全ミラー確率(約12%)も整理。", "date": "2026-06-19"},
    {"url": "abyss-eye-atari-guide.html", "title": "アビスアイ 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「アビスアイ」(M5)の当たりカードランキング・封入率・見分け方を解説。看板メガダークライex MUR(約100BOXに1枚)、SAR6種(ムク・モルペコex・メガゼラオラex・メガシャンデラex・グラジオの決戦)の買取相場、AR最高額ヤドラン、BOX開封の期待値まで実データで整理。", "date": "2026-07-12"},
    {"url": "mega-ex-atari-guide.html", "title": "MEGAドリームex 当たりカードランキング・封入率完全ガイド", "desc": "MEGAハイクラスパック「MEGAドリームex」(M2a)の当たりカードランキング・封入率を解説。看板メガゲンガーex SAR、唯一のMURメガカイリューex(約50BOXに1枚)、ピカチュウex SAR、新レアリティMA(メガリザードンXex MA等)、SAR17種の買取相場とBOX期待値を実データで整理。", "date": "2026-07-12"},
    {"url": "inferno-x-atari-guide.html", "title": "インフェルノX 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「インフェルノX」(M2)の当たりカードランキング・封入率を解説。看板メガリザードンXex MUR(約50BOXに1枚・約15万円)、SARも約8.5万円のリザードン一強構成。SAR6種・SR・AR枠の買取相場、BOX開封の期待値まで実データで整理。", "date": "2026-07-12"},
    {"url": "mega-brave-atari-guide.html", "title": "メガブレイブ 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「メガブレイブ」(M1)の当たりカードランキング・封入率を解説。看板メガルカリオex MUR(約50BOXに1枚)、歴代No.1人気トレーナーのリーリエの決心SAR、メガフシギバナex SARまで。レア別封入率・見分け方・BOX期待値を実データで整理。", "date": "2026-07-12"},
    {"url": "chouden-breaker-atari-guide.html", "title": "超電ブレイカー 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「超電ブレイカー」(SV8)の当たりカードランキング・封入率を解説。看板ピカチュウex SAR(約7.8万円・PSA10約13.5万円)、ピカチュウex UR、ミロカロスex SAR、エーススペック枠まで。SAR封入率約18%・見分け方・BOX期待値を実データで整理。", "date": "2026-07-12"},
    {"url": "clay-burst-atari-guide.html", "title": "クレイバースト 当たりカードランキング・封入率完全ガイド", "desc": "拡張パック「クレイバースト」(SV2D)の当たりカードランキング・封入率を解説。看板ナンジャモ SAR(約3.5万円・PSA10約7.8万円・きりさき氏イラスト)、ナンジャモSR、デカヌチャンex SAR、イーユイex SARまで。SAR封入率約20%・見分け方・BOX期待値を実データで整理。", "date": "2026-07-12"},
    {"url": "ninja-spinner-atari-guide.html", "title": "ニンジャスピナー 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「ニンジャスピナー」(M4)の当たりカードランキング・封入率を解説。看板メガゲッコウガex MUR(約50BOXに1枚・約6万円)、SAR(約2万円・前屋進氏イラスト)、チラチーノex SARまで。レア別封入率・見分け方・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "munikis-zero-atari-guide.html", "title": "ムニキスゼロ 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「ムニキスゼロ」(M3)の当たりカードランキング・封入率を解説。看板メガジガルデex MUR(約50〜70BOXに1枚・発売時5万円超から約2.7万円へ下落)、メイのはげまし SAR、ニャースex SARまで。レア別封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "mega-sinfonia-atari-guide.html", "title": "メガシンフォニア 当たりカードランキング・封入率完全ガイド", "desc": "MEGA拡張パック「メガシンフォニア」の当たりカードランキング・封入率を解説。看板メガサーナイトex MUR(約50BOXに1枚・約4万円)、SAR(約9,000円)、アセロラのいたずら SARまで。メガブレイブと同時発売の姉妹弾。レア別封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "black-bolt-atari-guide.html", "title": "ブラックボルト 当たりカードランキング・封入率完全ガイド", "desc": "SV拡張パック「ブラックボルト」の当たりカードランキング・封入率を解説。看板ゼクロムex BWR(約20〜24BOXに1枚・約5万円)、ゼクロムex SAR(約2.5万円)、Nの筋書き SARまで。新レアリティBWR・レア別封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "rocket-dan-no-eiko-atari-guide.html", "title": "ロケット団の栄光 当たりカードランキング・封入率完全ガイド", "desc": "SV拡張パック「ロケット団の栄光」(SV10)の当たりカードランキング・封入率を解説。看板ロケット団のミュウツーex SAR(約5万円・PSA10約11.7万円)、ファイヤーex SAR、ニドキングex SARまで。BOX買取¥27,500(定価5.1倍・上昇局面)。レア別封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "eevee-heroes-atari-guide.html", "title": "イーブイヒーローズ 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「イーブイヒーローズ」(S6a)の当たりカードランキング・封入率を解説。絶版・高騰弾。看板ブラッキーVMAX SA(約58万円・PSA10約85万円)、ニンフィアVMAX SA、グレイシアVMAX SAまで。BOX買取¥140,000(定価約28倍)。SA封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "151-atari-guide.html", "title": "ポケモンカード151 当たりカードランキング・封入率完全ガイド", "desc": "強化拡張パック「ポケモンカード151」(SV2a)の当たりカードランキング・封入率を解説。看板リザードンex SAR(約7万円・PSA10約13.7万円)、マスターボールミラー153種(ゲンガー/ピカチュウ)、ミュウex SARまで。BOX買取¥60,000(定価約11.1倍)。封入率・BOX期待値を実データで整理。", "date": "2026-07-19"},
    {"url": "white-flare-atari-guide.html", "title": "ホワイトフレア 当たりカードランキング・封入率完全ガイド", "desc": "SV拡張パック「ホワイトフレア」の当たりカードランキング・封入率を解説。看板レシラムex BWR(約5万円・PSA10約10.7万円)、レシラムex SAR(約2万円)、トウコ SAR(さいとうなおき氏・約6千円)まで。BOX買取¥23,200(定価約4.3倍)。ブラックボルトとの比較も実データで整理。", "date": "2026-07-26"},
    {"url": "terastal-fes-ex-atari-guide.html", "title": "テラスタルフェスex 当たりカードランキング・封入率完全ガイド", "desc": "SVハイクラスパック「テラスタルフェスex」の当たりカードランキング・封入率を解説。看板ブラッキーex SAR(約5.2万円・PSA10約10.1万円)、ブラッキー マスターボールミラー、ニンフィアex SARまで。ブイズ9種ex収録。SAR33種・約0.8BOXに1枚。BOX買取¥21,100(定価約3.8倍)。", "date": "2026-07-26"},
    {"url": "shiny-treasure-ex-atari-guide.html", "title": "シャイニートレジャーex 当たりカードランキング・封入率完全ガイド", "desc": "SVハイクラスパック「シャイニートレジャーex」の当たりカードランキング・封入率を解説。看板ミュウex SAR(約7.4万円・PSA10約13.5万円)、リザードンex SAR(約3万円)、色違い(S)枠まで。SAR8種は約8.3BOXに1枚。Gレギュでスタン落ち済みも高値維持。BOX買取¥20,000。", "date": "2026-07-26"},
    {"url": "restock-guide.html", "title": "再販情報の見つけ方", "desc": "ポケカBOXの再販入荷パターン、通知設定、抽選vs先着の攻略法まで。最速で再販情報をキャッチする方法を解説。", "date": "2026-04-10"},
    {"url": "box-toushi.html", "title": "ポケカBOX投資の始め方", "desc": "値上がりしやすいBOXの特徴、予算別の始め方、保管方法、リスクまで初心者向けに解説。", "date": "2026-04-02"},
    {"url": "shrink-nashi.html", "title": "シュリンクなしBOXの買取事情", "desc": "シュリンクなしポケカBOXの買取対応を買取店・メルカリ・スニダンで比較。高く売るコツも解説。", "date": "2026-03-27"},
    {"url": "mercari-hikaku.html", "title": "メルカリ・スニダン・買取店どれが得？", "desc": "手数料・送料込みで3つの売却方法を徹底比較。具体的な計算例で最適な売り方がわかります。", "date": "2026-03-26"},
    {"url": "psa-guide.html", "title": "PSA鑑定とは？ポケカの価値を最大化する方法", "desc": "鑑定の流れ、グレードの意味、費用対効果まで。PSA 10で価値が3〜10倍に跳ね上がる具体例も紹介。", "date": "2026-03-24"},
    {"url": "single-card-tips.html", "title": "ポケカBOX開封→シングル売りで利益を出す方法", "desc": "高額カードの当たり例、レアリティの封入率、トレンド変化まで。開封vs未開封売りの判断基準も解説。", "date": "2026-03-24"},
    {"url": "shop-hikaku.html", "title": "ポケカ買取9店舗の特徴を徹底比較", "desc": "当サイトで掲載している9店舗それぞれの強み・特徴をまとめました。自分に合った買取店選びの参考に。", "date": "2026-03-23"},
    {"url": "kaitori-tips.html", "title": "ポケカBOX買取で損しない5つのコツ", "desc": "シュリンク付きの重要性、複数店舗比較のメリット、売り時の見極め方など、高価買取のポイントを解説。", "date": "2026-03-23"},
]


def generate_product_js(products: list[MasterProduct], project_root: Path | None = None) -> str:
    """Generate the JavaScript `const P = [...]` array from product data."""
    # 前日の最高買取価格を読み込んで前日比計算用に渡す
    prev_max: dict[str, int] = {}
    if project_root:
        history_dir = project_root / "data" / "history"
        if history_dir.exists():
            files = sorted(history_dir.glob("*.json"))
            # 当日 = files[-1] (今regen中なのでその直前 = files[-2] が"前日")
            if len(files) >= 2:
                try:
                    prev_data = json.loads(files[-2].read_text(encoding="utf-8"))
                    prev_max = {x["name"]: x.get("max_price", 0) for x in prev_data}
                except (json.JSONDecodeError, OSError):
                    pass

    lines = []
    lines.append("const P=[")

    # Group by category
    current_cat = None
    for p in products:
        if p.category != current_cat:
            current_cat = p.category
            lines.append(f"// ===== {current_cat.upper()} =====")

        # Build price dict
        prices = {}
        for sid in SHOP_IDS:
            prices[sid] = p.prices.get(sid, 0)

        # Escape product name for JS string
        name_escaped = p.name.replace("\\", "\\\\").replace('"', '\\"')

        slug = _generate_slug(p.name)
        price_parts = ",".join(f"{sid}:{prices[sid]}" for sid in SHOP_IDS)
        # 前日比: 前日のmax_price (なければ0)
        y = prev_max.get(p.name, 0)
        line = (
            f'{{c:"{p.category}",n:"{name_escaped}",s:"{slug}",'
            f'r:{p.retail_price},d:"{p.release_date}",y:{y},p:{{{price_parts}}}}}'
        )
        lines.append(line + ",")

    lines.append("];")
    return "\n".join(lines)


def generate_history_js(history_dir: Path) -> str:
    """Generate JS object with price history data from daily snapshots."""
    if not history_dir.exists():
        return "const H={};"

    # Load all history files, sorted by date
    history = {}
    for f in sorted(history_dir.glob("*.json")):
        date = f.stem  # "2026-03-22"
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for item in data:
                name = item["name"]
                if name not in history:
                    history[name] = {}
                history[name][date] = item["max_price"]
        except (json.JSONDecodeError, KeyError):
            continue

    # Build JS: H = { "product name": { "2026-03-22": 18000, ... }, ... }
    return "const H=" + json.dumps(history, ensure_ascii=False) + ";"


def generate_jsonld(products: list[MasterProduct]) -> str:
    """Generate JSON-LD structured data for Google rich results."""
    items = []
    for p in products:
        active_prices = [v for v in p.prices.values() if v > 0]
        if not active_prices:
            continue
        items.append({
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "image": "https://pokeca-box-hikaku.com/ogp.jpg",
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "category": "トレーディングカードゲーム / ポケモンカード / 未開封BOX",
            "offers": {
                "@type": "AggregateOffer",
                "lowPrice": min(active_prices),
                "highPrice": max(active_prices),
                "priceCurrency": "JPY",
                "offerCount": len(active_prices),
            },
        })
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ポケカ買取チェッカー - 未開封BOX買取価格比較",
        "description": "ポケモンカード未開封BOXの買取価格をラントゥ・ホムラ・一丁目・森森買取等9店舗横断で比較",
        "numberOfItems": len(items),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": item}
            for i, item in enumerate(items)
        ],
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
        ],
    }
    return (
        '<script type="application/ld+json">\n' + json.dumps(ld, ensure_ascii=False, indent=2) + "\n</script>\n"
        '<script type="application/ld+json">\n' + json.dumps(breadcrumb, ensure_ascii=False, indent=2) + "\n</script>"
    )


def generate_ai_summary(products: list[MasterProduct]) -> str:
    """Generate a natural language summary for AI crawlers."""
    now = datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日")

    # Collect top products by max buyback price
    ranked = []
    for p in products:
        active = {k: v for k, v in p.prices.items() if v > 0}
        if not active:
            continue
        max_shop = max(active, key=active.get)
        ranked.append((p, active, max_shop))

    ranked.sort(key=lambda x: max(x[1].values()), reverse=True)

    shop_names = {
        "morimori": "森森買取", "homura": "買取ホムラ", "icchome": "買取一丁目",
        "runto": "ラントゥ買取", "kaikyo": "海峡通信",
        "oku": "買取オク", "rudeya": "買取ルデヤ",
    }

    lines = []
    lines.append(f"ポケカ買取チェッカー - {date_str}更新。ポケモンカード未開封BOXの買取価格を9店舗で横断比較。")

    # Top 5 products
    lines.append(f"【{date_str}時点の買取価格ランキング TOP5】")
    for i, (p, active, max_shop) in enumerate(ranked[:5]):
        max_price = max(active.values())
        min_price = min(active.values())
        shop = shop_names.get(max_shop, max_shop)
        lines.append(f"{i+1}位: {p.name} - 最高¥{max_price:,}({shop}) / 最安¥{min_price:,} / {len(active)}店舗掲載")

    lines.append(f"対応店舗: {', '.join(shop_names.values())}。毎日3回（11:00/15:00/18:00）自動更新。")

    summary_text = "\n".join(lines)
    return f'<div style="position:absolute;left:-9999px;font-size:1px;color:transparent" aria-hidden="true">{summary_text}</div>'


def generate_blog_links() -> str:
    """Generate blog cards: 1 random (left) + 3 latest pinned (right)."""
    # 最新3記事を date 降順で抽出(同日は元の並び順を維持)
    sorted_articles = sorted(
        BLOG_ARTICLES,
        key=lambda a: a.get("date", ""),
        reverse=True,
    )
    pinned = sorted_articles[:3]
    pinned_urls = {a["url"] for a in pinned}
    # 残りはJSでランダム選択
    candidates = [a for a in BLOG_ARTICLES if a["url"] not in pinned_urls]

    html = '<div class="blog-links" id="blogLinks">\n'
    # ランダム候補（非表示、JSで1つ選んで表示）
    for article in candidates:
        html += (
            f'  <a href="{article["url"]}" class="blog-card blog-random" style="display:none"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    # Pinned 2枚を常時表示
    for article in pinned:
        html += (
            f'  <a href="{article["url"]}" class="blog-card"'
            f' onclick="gtag(\'event\',\'blog_click\',{{article:\'{article["url"]}\'}})">\n'
            f'    <h3>{article["title"]}</h3>\n'
            f'    <p>{article["desc"]}</p>\n'
            f'  </a>\n'
        )
    html += '</div>'
    return html


def generate_chart_data(products: list[MasterProduct], project_root: Path) -> str:
    """Generate JS variable with snkrdunk price history for chart display."""
    mapping_path = project_root / "data" / "snkrdunk" / "product_mapping.json"
    if not mapping_path.exists():
        return "const SC={};"

    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "const SC={};"

    snkrdunk_dir = project_root / "data" / "snkrdunk"
    chart_data: dict[str, dict] = {}
    product_map = {p.name: p for p in products}

    for product_name, snkrdunk_id in mapping.items():
        if product_name not in product_map:
            continue
        data_path = snkrdunk_dir / f"{snkrdunk_id}.json"
        if not data_path.exists():
            continue
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            points = data.get("points", [])
            if points:
                entry: dict = {"p": points}
                rd = product_map[product_name].release_date
                if rd:
                    entry["d"] = rd
                chart_data[product_name] = entry
        except (json.JSONDecodeError, OSError):
            continue

    return "const SC=" + json.dumps(chart_data, ensure_ascii=False) + ";"


def generate_html(
    products: list[MasterProduct],
    template_path: Path | None = None,
    output_path: Path | None = None,
) -> str:
    """Generate index.html from template and product data.

    Args:
        products: List of master products with prices filled in.
        template_path: Path to template.html (default: project root/template.html)
        output_path: Path to write index.html (default: project root/index.html)

    Returns:
        The generated HTML content.
    """
    project_root = Path(__file__).resolve().parent.parent
    if template_path is None:
        template_path = project_root / "template.html"
    if output_path is None:
        output_path = project_root / "index.html"

    template = template_path.read_text(encoding="utf-8")

    # Generate product data JS
    product_js = generate_product_js(products, project_root)

    # Generate update date in JST
    now = datetime.now(JST)
    update_date = now.strftime("%Y/%m/%d %H:%M")

    # Generate JSON-LD structured data
    jsonld = generate_jsonld(products)

    # Generate AI-friendly summary
    ai_summary = generate_ai_summary(products)

    # Replace placeholders
    html = template.replace("// {{PRODUCT_DATA}}", product_js)
    html = html.replace("<!-- {{JSONLD}} -->", jsonld)
    html = html.replace("<!-- {{AI_SUMMARY}} -->", ai_summary)
    html = html.replace("{{UPDATE_DATE}}", update_date)
    html = html.replace("<!-- {{BLOG_LINKS}} -->", generate_blog_links())

    # Generate ranking page (before summary, so we can use the data)
    ranking_summary = _generate_ranking_summary(products, project_root)
    html = html.replace("<!-- {{RANKING_SUMMARY}} -->", ranking_summary)

    # Write output
    output_path.write_text(html, encoding="utf-8")
    logger.info("Generated %s (updated: %s)", output_path, update_date)

    # Generate per-shop buyback price pages (店舗名クエリの受け皿)
    # sitemap は generate_product_pages の末尾で書き出されるため、先に生成しておく
    generate_shop_pages(products, project_root, update_date)

    # Generate individual product pages
    generate_product_pages(products, project_root, update_date)

    # Generate ranking page
    generate_ranking_page(products, project_root, update_date)

    # Generate weekly hot-boxes article (task 10)
    generate_weekly_article(products, project_root, update_date)

    # Generate monthly ranking article for any completed months not yet archived
    generate_monthly_article(products, project_root, update_date)

    # Generate category summary pages (SV / MEGA / S&S)
    generate_category_pages(products, project_root, update_date)

    # Update time-sensitive article banners (発売日超過で自動切替)
    update_timed_articles(project_root)

    # Update spotlight article live-data summary blocks
    update_spotlight_summaries(products, project_root)

    return html


# ===== Slug generation =====

# Manual slug overrides for products with tricky names
SLUG_OVERRIDES = {
    "MEGA スタートデッキ100「バトルコレクション」": "battle-collection",
    "S&S 拡張パック「25th ANNIVERSARY COLLECTION」": "25th-anniversary-collection",
    "S&S 拡張パック「ソード」": "sword",
    "S&S 拡張パック「シールド」": "shield",
    "S&S 強化拡張パック「ポケモンGO」": "pokemon-go",
    "SV 拡張パックDX「ブラックボルト」": "black-bolt-dx",
    "SV 拡張パックDX「ホワイトフレア」": "white-flare-dx",
}

# Romanization map for common Pokemon TCG terms
ROMAJI_MAP = {
    "ストームエメラルダ": "storm-emeralda",
    "アビスアイ": "abyss-eye",
    "ニンジャスピナー": "ninja-spinner",
    "ムニキスゼロ": "munikis-zero",
    "メガドリーム": "mega-dream",
    "インフェルノ": "inferno",
    "メガブレイブ": "mega-brave",
    "メガシンフォニア": "mega-sinfonia",
    "ブラックボルト": "black-bolt",
    "ホワイトフレア": "white-flare",
    "ロケット団の栄光": "rocket-dan-no-eiko",
    "熱風のアリーナ": "neppuu-arena",
    "バトルパートナーズ": "battle-partners",
    "テラスタルフェス": "terastal-fes",
    "超電ブレイカー": "chouden-breaker",
    "楽園ドラゴーナ": "rakuen-dragona",
    "ステラミラクル": "stellar-miracle",
    "ナイトワンダラー": "night-wanderer",
    "変幻の仮面": "hengen-no-kamen",
    "ワイルドフォース": "wild-force",
    "サイバージャッジ": "cyber-judge",
    "クリムゾンヘイズ": "crimson-haze",
    "シャイニートレジャー": "shiny-treasure",
    "黒炎の支配者": "ruler-of-black-flame",
    "古代の咆哮": "ancient-roar",
    "未来の一閃": "future-flash",
    "レイジングサーフ": "raging-surf",
    "スカーレット": "scarlet",
    "バイオレット": "violet",
    "スノーハザード": "snow-hazard",
    "クレイバースト": "clay-burst",
    "トリプレットビート": "triplet-beat",
    "白熱のアルカナ": "incandescent-arcana",
    "ロストアビス": "lost-abyss",
    "パラダイムトリガー": "paradigm-trigger",
    "トウホク": "tohoku",
    "ヒロシマ": "hiroshima",
    "フクオカ": "fukuoka",
    "イーブイヒーローズ": "eevee-heroes",
    "バトルリージョン": "battle-region",
    "スターバース": "star-birth",
    "フュージョンアーツ": "fusion-arts",
    "蒼空ストリーム": "blue-sky-stream",
    "摩天パーフェクト": "skyscraping-perfect",
    "白銀のランス": "silver-lance",
    "漆黒のガイスト": "jet-black-geist",
    "双璧のファイター": "matchless-fighters",
    "連撃マスター": "rapid-strike-master",
    "一撃マスター": "single-strike-master",
    "シャイニースター": "shiny-star",
    "仰天のボルテッカー": "astonishing-voltecker",
    "伝説の鼓動": "legendary-heartbeat",
    "ムゲンゾーン": "infinity-zone",
    "爆炎ウォーカー": "eruption-walker",
    "反逆クラッシュ": "rebellion-crash",
    "ダークファンタズマ": "dark-phantasma",
    "タイムゲイザー": "time-gazer",
    "スペースジャグラー": "space-juggler",
    "VMAXクライマックス": "vmax-climax",
    "VSTARユニバース": "vstar-universe",
    "VMAXライジング": "vmax-rising",
}


def _generate_slug(product_name: str) -> str:
    """Generate a URL-friendly slug from a product name."""
    if product_name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[product_name]

    # Extract the part in quotes (e.g., 「xxx」)
    m = re.search(r"[「『](.+?)[」』]", product_name)
    if m:
        core = m.group(1)
    else:
        # For special BOX, use the last part
        core = product_name.split()[-1] if " " in product_name else product_name

    # Try romaji map first
    for jp, en in ROMAJI_MAP.items():
        if jp in core:
            # Handle suffixes like "ex"
            slug = en
            if "ex" in core.lower() and "ex" not in en:
                slug += "-ex"
            return slug

    # Fallback: normalize and transliterate
    slug = core.lower()
    slug = unicodedata.normalize("NFKC", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "unknown"


SHOP_NAMES = {
    "morimori": "森森買取",
    "homura": "買取ホムラ",
    "icchome": "買取一丁目",
    "runto": "ラントゥ買取",
    "kaikyo": "海峡通信",
    "oku": "買取オク",
    "rudeya": "買取ルデヤ",
    "collect_tendo": "買取コレクト",
    "shinsoku": "買取シンソク",
}

SHOP_URLS = {
    "morimori": "https://www.morimori-kaitori.jp/",
    "homura": "https://kaitori-homura.com/",
    "icchome": "https://www.1-chome.com/",
    "runto": "https://runto666.com/",
    "kaikyo": "https://www.mobile-ichiban.com/",
    "oku": "https://kaitori-oku.jp/",
    "rudeya": "https://kaitori-rudeya.com/",
    "collect_tendo": "https://x.com/collect_tendo",
    "shinsoku": "https://shinsoku-tcg.com/yuso-kaitori",
}

# 店舗別ページ用プロフィール (shop-hikaku.html の記述を単一ソース化)
SHOP_PROFILES = {
    "morimori": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電・iPhone等を扱う買取専門店。買取価格は業界でもトップクラスで、最高値を出すことが多い店舗の一つです。Xでのリポストキャンペーンは要注目。",
    },
    "homura": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電・iPhone・トレンド商品も取り扱う総合買取店。シュリンク無BOX対応。買取対象商品の品揃えが豊富で、古い弾のBOXも査定対象になることが多いです。",
    },
    "icchome": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電・iPhone・ウイスキーなど幅広いジャンルを取り扱う総合買取店。最近福岡にも店舗をオープンした勢いのある大手。",
    },
    "runto": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカに特化した買取店。ポケカBOXの買取に力を入れており、シュリンク無にも対応。安定して高い買取価格を提示しています。サイトの更新頻度も高く、最新の相場が反映されやすいです。",
    },
    "kaikyo": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電・iPhone等も取り扱う総合買取店。スマホ・タブレットの買取も行っており、ポケカBOXの買取にも対応しています。",
    },
    "oku": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電・iPhone等も取り扱う総合買取店。ポケカBOXの買取にも対応しており、使いやすいHPがユーザーから高評価。",
    },
    "rudeya": {
        "methods": ["店頭", "郵送"],
        "desc": "トレカ・家電等も取り扱う総合買取店。ポケカ・遊戯王・ワンピースなど主要カードゲームのBOX買取に幅広く対応しています。安定した買取実績があり、初めての方でも安心して利用できます。",
    },
    "collect_tendo": {
        "methods": ["店頭", "郵送"],
        "desc": "地方出店で地元にも愛される高額買取が売りの買取店。ホームページを持たずX(@collect_tendo)で買取価格表を不定期に公開しているスタイルが特徴。地域密着型の運営で常連ファン多数。当サイトではX投稿の画像から自動で価格を取得して掲載しています。",
    },
    "shinsoku": {
        "methods": ["店頭", "郵送"],
        "desc": "買取商品数業界トップが売りの買取店。現行のSV/MEGA系BOXからS&S絶版BOX、さらにポケモンカード初代/neo/eシリーズ等のヴィンテージBOXまで圧倒的な品揃えで買取対応しています。レトロカードや希少品の売却を考えている方にも有力な選択肢です。",
    },
}

CATEGORY_LABELS = {
    "mega": "MEGA シリーズ",
    "sv": "SV シリーズ",
    "special": "スペシャルBOX",
    "ss": "S&S ソード&シールド",
}


def _find_product_url(
    product_urls: dict[str, dict[str, str]],
    shop_id: str,
    product: MasterProduct,
) -> str | None:
    """Find product-specific URL from the URL mapping.

    Matches by checking if any of the product's keywords appear in the
    scraped product name from the URL mapping.
    """
    shop_map = product_urls.get(shop_id, {})
    if not shop_map:
        return None

    # Try exact keyword match against scraped names
    for kw in product.keywords:
        if not kw:
            continue
        kw_lower = kw.lower()
        for scraped_name, url in shop_map.items():
            if kw_lower in scraped_name.lower():
                # Avoid matching DX vs non-DX
                is_dx_product = "DX" in product.name
                is_dx_scraped = "dx" in scraped_name.lower() or "デラックス" in scraped_name
                if is_dx_product != is_dx_scraped:
                    continue
                # Avoid matching shrink-nashi / carton
                name_lower = scraped_name.lower()
                if "シュリンクなし" in scraped_name or "シュリンク無" in scraped_name:
                    continue
                if "カートン" in scraped_name or "carton" in name_lower:
                    continue
                return url

    return None


def _format_price(price: int) -> str:
    if price <= 0:
        return "-"
    return f"\u00a5{price:,}"


def _generate_trend_comment(
    product_name: str,
    history_dir: Path,
    current_price: int,
) -> str:
    """Generate a 1-line price trend comment from history data.

    Returns HTML string with trend indicator. Empty if insufficient data.
    """
    if current_price <= 0 or not history_dir.exists():
        return ""

    # Load last 30 days of own history
    files = sorted(history_dir.glob("*.json"))
    if len(files) < 7:
        return ""

    # Build time series: [(date_str, max_price), ...] for this product
    series: list[tuple[str, int]] = []
    for f in files[-60:]:  # up to 60 days
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for item in items:
            if item.get("name") == product_name:
                price = item.get("max_price", 0)
                if price > 0:
                    series.append((f.stem, price))
                break

    if len(series) < 7:
        return ""

    # 7 days ago point
    idx_7 = max(0, len(series) - 8)
    d_7d, p_7d = series[idx_7]
    # 30 days ago point
    idx_30 = max(0, len(series) - 31)
    d_30d, p_30d = series[idx_30]
    today_str = series[-1][0]

    diff_7 = current_price - p_7d
    pct_7 = (diff_7 / p_7d * 100) if p_7d > 0 else 0

    # Check for high/low updates (within last 30 days excluding today)
    recent30 = [p for _, p in series[-31:-1]] if len(series) > 30 else [p for _, p in series[:-1]]
    high_30 = max(recent30) if recent30 else 0
    low_30 = min(recent30) if recent30 else 0

    icon = ""
    color = ""
    text = ""

    if current_price > high_30 and high_30 > 0:
        icon = "📈"
        color = "#dc2626"
        text = (
            f"{today_str}時点で過去30日の最高値を更新中 "
            f"({d_7d}比 {'+' if diff_7 >= 0 else ''}¥{abs(diff_7):,} / "
            f"{'+' if pct_7 >= 0 else ''}{pct_7:.1f}%)"
        )
    elif current_price < low_30 and low_30 > 0:
        icon = "📉"
        color = "#2563eb"
        text = (
            f"{today_str}時点で過去30日の底値を更新中 "
            f"({d_7d}比 {'+' if diff_7 >= 0 else ''}¥{abs(diff_7):,} / "
            f"{'+' if pct_7 >= 0 else ''}{pct_7:.1f}%)"
        )
    elif abs(pct_7) >= 5:
        if pct_7 > 0:
            icon = "📈"
            color = "#dc2626"
            text = f"{d_7d}→{today_str}の7日間で+¥{diff_7:,} (+{pct_7:.1f}%) 上昇中"
        else:
            icon = "📉"
            color = "#2563eb"
            text = f"{d_7d}→{today_str}の7日間で-¥{abs(diff_7):,} ({pct_7:.1f}%) 下落中"
    elif p_30d > 0:
        diff_30 = current_price - p_30d
        pct_30 = (diff_30 / p_30d * 100) if p_30d > 0 else 0
        if abs(pct_30) < 3:
            icon = "➡️"
            color = "#6b7280"
            text = f"{d_30d}→{today_str}の30日間で±3%以内の横ばい推移"
        elif pct_30 >= 25:
            icon = "🚀"
            color = "#dc2626"
            text = f"{d_30d}→{today_str}の30日間で+¥{diff_30:,} (+{pct_30:.1f}%) 急騰中"
        elif pct_30 >= 10:
            icon = "📈"
            color = "#dc2626"
            text = f"{d_30d}→{today_str}の30日間で+¥{diff_30:,} (+{pct_30:.1f}%) 上昇トレンド"
        elif pct_30 > 0:
            icon = "📈"
            color = "#dc2626"
            text = f"{d_30d}→{today_str}の30日間で+¥{diff_30:,} (+{pct_30:.1f}%) 緩やか上昇"
        elif pct_30 <= -25:
            icon = "⚠️"
            color = "#2563eb"
            text = f"{d_30d}→{today_str}の30日間で-¥{abs(diff_30):,} ({pct_30:.1f}%) 急落"
        elif pct_30 <= -10:
            icon = "📉"
            color = "#2563eb"
            text = f"{d_30d}→{today_str}の30日間で-¥{abs(diff_30):,} ({pct_30:.1f}%) 下落トレンド"
        else:
            icon = "📉"
            color = "#2563eb"
            text = f"{d_30d}→{today_str}の30日間で-¥{abs(diff_30):,} ({pct_30:.1f}%) 緩やか下落"

    if not text:
        return ""

    return (
        f'<div class="trend-comment" style="color:{color}">'
        f'<span class="trend-icon">{icon}</span>'
        f'<span class="trend-text">{text}</span>'
        f'</div>'
    )


def _build_box_narrative(
    product: MasterProduct,
    max_price: int,
    shop_count: int,
    slug: str,
) -> str:
    """Generate per-BOX original narrative text (150-300 chars).

    Uses product fields (release_date, retail_price, hit_cards, category)
    + computed values to build a unique commentary per product.
    """
    parts: list[str] = []

    # シリーズ位置付け
    cat_text = {
        "sv": "スカーレット&バイオレット(SV)シリーズ",
        "mega": "メガシンカ(MEGA)シリーズ",
        "ss": "ソード&シールド(S&S)シリーズ",
        "special": "地域限定スペシャルBOX",
    }.get(product.category, "拡張パック")

    # リリース時期から経過月数を計算
    elapsed_text = ""
    if product.release_date:
        try:
            rd = datetime.strptime(product.release_date, "%Y-%m-%d").date()
            today = datetime.now(JST).date()
            months = (today - rd).days // 30
            if months < 1:
                elapsed_text = "発売直後の新弾"
            elif months < 6:
                elapsed_text = f"発売から約{months}ヶ月の比較的新しい弾"
            elif months < 18:
                elapsed_text = f"発売から約{months}ヶ月、スタンダード現役の弾"
            elif months < 36:
                elapsed_text = f"発売から約{months}ヶ月、スタン落ち観測の対象になりやすい弾"
            else:
                elapsed_text = f"発売から{months // 12}年以上経過した旧弾"
        except ValueError:
            pass

    intro = f"<p>{product.name}は、{cat_text}の{elapsed_text}です。"
    if product.release_date:
        try:
            rd = datetime.strptime(product.release_date, "%Y-%m-%d").date()
            intro += f"発売日は{rd.year}年{rd.month}月{rd.day}日。"
        except ValueError:
            pass
    if product.retail_price > 0:
        intro += f"定価は1BOXあたり¥{product.retail_price:,}(税込)で、30パック入りが基本構成です。"
    intro += "</p>"
    parts.append(intro)

    # 当たりカードの解説 (hit_cardsを活用)
    if product.hit_cards:
        top_cards = product.hit_cards[:3]
        card_text = "<p>注目の収録カードは"
        card_descriptions = []
        for card in top_cards:
            if isinstance(card, (list, tuple)) and len(card) >= 2:
                name, comment = card[0], card[1]
                card_descriptions.append(f"<strong>{name}</strong>({comment})")
            elif isinstance(card, (list, tuple)):
                card_descriptions.append(f"<strong>{card[0]}</strong>")
            else:
                card_descriptions.append(f"<strong>{card}</strong>")
        card_text += "、".join(card_descriptions)
        card_text += "など。これらの高額レアを引き当てられるかが本BOXの開封価値を大きく左右します。</p>"
        parts.append(card_text)

    # 相場ポジショニング
    if product.retail_price > 0 and max_price > 0:
        ratio = max_price / product.retail_price
        if ratio >= 8:
            tier_text = (
                f"<p>現在のBOX買取最高額は¥{max_price:,}で、定価の約{ratio:.1f}倍に達しています。"
                f"超高額帯BOXの典型例で、看板SAR/MURの相場と連動した投資対象として扱われる水準です。"
                f"短期の急騰局面では調整が入りやすいため、追随する場合は押し目を意識した方が無難です。</p>"
            )
        elif ratio >= 4:
            tier_text = (
                f"<p>現在のBOX買取最高額は¥{max_price:,}で、定価の約{ratio:.1f}倍。"
                f"中高額帯のBOXとして、コレクター需要+スタン落ち観測の先取り投資需要が共存している価格帯です。"
                f"再販頻度や同シリーズ内の動向を観察しながら、判断材料を積み上げるのが定石です。</p>"
            )
        elif ratio >= 2:
            tier_text = (
                f"<p>現在のBOX買取最高額は¥{max_price:,}で、定価の約{ratio:.1f}倍。"
                f"中堅BOX帯で、まだ過熱感が薄く取引もしやすい水準です。"
                f"看板SARの相場が動き出すタイミングを捉えれば、追加上昇の余地が残るゾーンです。</p>"
            )
        elif ratio >= 1.2:
            tier_text = (
                f"<p>現在のBOX買取最高額は¥{max_price:,}で、定価の約{ratio:.1f}倍。"
                f"定価+αの位置取りで、再販供給が安定しているか需要が控えめなBOXに多い価格帯です。"
                f"プレイ・コレクション目的なら定価購入で十分カバーできるレンジと言えます。</p>"
            )
        else:
            tier_text = (
                f"<p>現在のBOX買取最高額は¥{max_price:,}で、定価¥{product.retail_price:,}を下回っています。"
                f"再販供給が需要を上回っているか、シリーズ内で他BOXに需要が分散している状態です。"
                f"ただし買取相場と販売相場には乖離があるため、購入価格は別途確認してください。</p>"
            )
        parts.append(tier_text)

    # 店舗数情報
    if shop_count >= 6:
        shop_text = f"<p>当サイトでは{shop_count}店舗で買取掲載が確認できており、流動性の高いBOXとして扱われています。複数店舗の最高値を比較するのが、最も損のない売却方法です。</p>"
    elif shop_count >= 3:
        shop_text = f"<p>当サイトでは{shop_count}店舗で買取掲載が確認できています。掲載店舗が限定的なため、最高値店舗での売却が特に重要になります。</p>"
    else:
        shop_text = f"<p>当サイトで掲載中の取扱店舗は現状{shop_count}店舗のみです。需給バランスや在庫状況により、表示価格が大きく変動する可能性があります。</p>"
    parts.append(shop_text)

    # スポットライト記事への内部リンク (該当BOXのみ)
    spot_links = {
        "151": ("151-spotlight.html", "ポケモンカード151が定価12.6倍に高騰した5つの理由"),
        "ruler-of-black-flame": ("kokuen-spotlight.html", "黒炎の支配者が定価4倍に高騰した解説"),
        "inferno": ("inferno-x-spotlight.html", "インフェルノXが定価5倍に高騰した解説"),
        "chouden-breaker": ("chouden-breaker-spotlight.html", "超電ブレイカーが定価7.5倍に高騰した解説"),
        "clay-burst": ("clay-burst-spotlight.html", "クレイバーストとナンジャモSAR相場の解説"),
        "ninja-spinner": ("ninja-spinner-spotlight.html", "ニンジャスピナーが定価2.5倍に高騰した解説"),
        "rocket-dan-no-eiko": ("rocket-dan-no-eiko-spotlight.html", "ロケット団の栄光が定価5.8倍に高騰した解説"),
    }
    if slug in spot_links:
        link_url, link_text = spot_links[slug]
        parts.append(
            f'<p>📖 さらに詳しい解説は'
            f'<a href="../{link_url}">【特集】{link_text}</a>'
            f'をご覧ください。発売後の相場推移、高騰理由、3シナリオ予想、当たりカード相場を実データで掘り下げています。</p>'
        )

    # 当たりカードガイドへの内部リンク (該当BOXのみ)
    atari_links = {
        "abyss-eye": ("abyss-eye-atari-guide.html", "アビスアイ 当たりカードランキング・封入率完全ガイド"),
        "mega-ex": ("mega-ex-atari-guide.html", "MEGAドリームex 当たりカードランキング・封入率完全ガイド"),
        "inferno": ("inferno-x-atari-guide.html", "インフェルノX 当たりカードランキング・封入率完全ガイド"),
        "mega-brave": ("mega-brave-atari-guide.html", "メガブレイブ 当たりカードランキング・封入率完全ガイド"),
        "chouden-breaker": ("chouden-breaker-atari-guide.html", "超電ブレイカー 当たりカードランキング・封入率完全ガイド"),
        "clay-burst": ("clay-burst-atari-guide.html", "クレイバースト 当たりカードランキング・封入率完全ガイド"),
        "ninja-spinner": ("ninja-spinner-atari-guide.html", "ニンジャスピナー 当たりカードランキング・封入率完全ガイド"),
        "munikis-zero": ("munikis-zero-atari-guide.html", "ムニキスゼロ 当たりカードランキング・封入率完全ガイド"),
        "mega-sinfonia": ("mega-sinfonia-atari-guide.html", "メガシンフォニア 当たりカードランキング・封入率完全ガイド"),
        "black-bolt": ("black-bolt-atari-guide.html", "ブラックボルト 当たりカードランキング・封入率完全ガイド"),
        "white-flare": ("white-flare-atari-guide.html", "ホワイトフレア 当たりカードランキング・封入率完全ガイド"),
        "terastal-fes-ex": ("terastal-fes-ex-atari-guide.html", "テラスタルフェスex 当たりカードランキング・封入率完全ガイド"),
        "shiny-treasure-ex": ("shiny-treasure-ex-atari-guide.html", "シャイニートレジャーex 当たりカードランキング・封入率完全ガイド"),
        "rocket-dan-no-eiko": ("rocket-dan-no-eiko-atari-guide.html", "ロケット団の栄光 当たりカードランキング・封入率完全ガイド"),
        "eevee-heroes": ("eevee-heroes-atari-guide.html", "イーブイヒーローズ 当たりカードランキング・封入率完全ガイド"),
        "151": ("151-atari-guide.html", "ポケモンカード151 当たりカードランキング・封入率完全ガイド"),
        "ruler-of-black-flame": ("kokuen-atari-guide.html", "黒炎の支配者 当たりカード完全ガイド"),
        "battle-collection": ("startdeck100-atari-guide.html", "スタートデッキ100 当たり番号一覧・見分け方完全ガイド"),
        "crimson-haze": ("crimson-haze-atari-guide.html", "クリムゾンヘイズ 当たりカードランキング・封入率完全ガイド"),
        "hengen-no-kamen": ("hengen-no-kamen-atari-guide.html", "変幻の仮面 当たりカードランキング・封入率完全ガイド"),
        "rakuen-dragona": ("rakuen-dragona-atari-guide.html", "楽園ドラゴーナ 当たりカードランキング・封入率完全ガイド"),
        "night-wanderer": ("night-wanderer-atari-guide.html", "ナイトワンダラー 当たりカードランキング・封入率完全ガイド"),
        "raging-surf": ("raging-surf-atari-guide.html", "レイジングサーフ 当たりカードランキング・封入率完全ガイド"),
        "scarlet-ex": ("scarlet-ex-atari-guide.html", "スカーレットex 当たりカードランキング・封入率完全ガイド"),
        "future-flash": ("future-flash-atari-guide.html", "未来の一閃 当たりカードランキング・封入率完全ガイド"),
        "stellar-miracle": ("stellar-miracle-atari-guide.html", "ステラミラクル 当たりカードランキング・封入率完全ガイド"),
        "ancient-roar": ("ancient-roar-atari-guide.html", "古代の咆哮 当たりカードランキング・封入率完全ガイド"),
        "wild-force": ("wild-force-atari-guide.html", "ワイルドフォース 当たりカードランキング・封入率完全ガイド"),
        "triplet-beat": ("triplet-beat-atari-guide.html", "トリプレットビート 当たりカードランキング｜コイキングAR"),
        "cyber-judge": ("cyber-judge-atari-guide.html", "サイバージャッジ 当たりカードランキング・封入率完全ガイド"),
        "snow-hazard": ("snow-hazard-atari-guide.html", "スノーハザード 当たりカードランキング・封入率完全ガイド"),
        "neppuu-arena": ("neppuu-arena-atari-guide.html", "熱風のアリーナ 当たりカードランキング・封入率完全ガイド"),
        "eruption-walker": ("eruption-walker-atari-guide.html", "爆炎ウォーカー 当たりカードランキング・封入率完全ガイド"),
        "legendary-heartbeat": ("legendary-heartbeat-atari-guide.html", "伝説の鼓動 当たりカードランキング・封入率完全ガイド"),
        "vmax-climax": ("vmax-climax-atari-guide.html", "VMAXクライマックス 当たりカードランキング・封入率完全ガイド"),
        "astonishing-voltecker": ("astonishing-voltecker-atari-guide.html", "仰天のボルテッカー 当たりカードランキング・封入率完全ガイド"),
        "matchless-fighters": ("matchless-fighters-atari-guide.html", "双璧のファイター 当たりカードランキング・封入率完全ガイド"),
        "lost-abyss": ("lost-abyss-atari-guide.html", "ロストアビス 当たりカードランキング・封入率完全ガイド"),
        "single-strike-master": ("single-strike-master-atari-guide.html", "一撃マスター 当たりカードランキング・封入率完全ガイド"),
        "rapid-strike-master": ("rapid-strike-master-atari-guide.html", "連撃マスター 当たりカードランキング・封入率完全ガイド"),
        "infinity-zone": ("infinity-zone-atari-guide.html", "ムゲンゾーン 当たりカードランキング・封入率完全ガイド"),
        "rebellion-crash": ("rebellion-crash-atari-guide.html", "反逆クラッシュ 当たりカードランキング・封入率完全ガイド"),
        "fusion-arts": ("fusion-arts-atari-guide.html", "フュージョンアーツ 当たりカードランキング・封入率完全ガイド"),
        "vmax-rising": ("vmax-rising-atari-guide.html", "VMAXライジング 当たりカードランキング・封入率完全ガイド"),
        "blue-sky-stream": ("blue-sky-stream-atari-guide.html", "蒼空ストリーム 当たりカードランキング・封入率完全ガイド"),
        "battle-partners": ("battle-partners-atari-guide.html", "バトルパートナーズ 当たりカードランキング・封入率完全ガイド"),
    }
    if slug in atari_links:
        atari_url, atari_text = atari_links[slug]
        parts.append(
            f'<p>🎯 当たりカードを狙うなら'
            f'<a href="../{atari_url}">{atari_text}</a>'
            f'もご覧ください。当たりカードのランキング・レア別封入率・開封前後の見分け方・BOX開封の期待値を実データで整理しています。</p>'
        )

    return f'<div class="box-narrative">' + "".join(parts) + '</div>'


def _generate_box_chart_section(product: MasterProduct, project_root: Path) -> str:
    """Generate inline chart HTML+JS for an individual product page.

    Uses snkrdunk data for historical prices, then switches to our own
    history data (data/history/) from the date our collection started.
    """
    # --- Load snkrdunk data ---
    snkrdunk_points: list[list] = []
    mapping_path = project_root / "data" / "snkrdunk" / "product_mapping.json"
    if mapping_path.exists():
        try:
            mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            snkrdunk_id = mapping.get(product.name)
            if snkrdunk_id:
                data_path = project_root / "data" / "snkrdunk" / f"{snkrdunk_id}.json"
                if data_path.exists():
                    data = json.loads(data_path.read_text(encoding="utf-8"))
                    snkrdunk_points = data.get("points", [])
        except (json.JSONDecodeError, OSError):
            pass

    # --- Load our own history data ---
    history_dir = project_root / "data" / "history"
    own_points: list[list] = []  # [timestamp_ms, max_price]
    if history_dir.exists():
        for hist_file in sorted(history_dir.glob("*.json")):
            try:
                date_str = hist_file.stem  # "2026-03-08"
                ts = int(datetime.strptime(date_str, "%Y-%m-%d")
                         .replace(tzinfo=JST).timestamp() * 1000)
                items = json.loads(hist_file.read_text(encoding="utf-8"))
                for item in items:
                    if item.get("name") == product.name:
                        max_price = item.get("max_price", 0)
                        if max_price > 0:
                            own_points.append([ts, max_price])
                        break
            except (json.JSONDecodeError, OSError, ValueError):
                continue

    # --- Merge: snkrdunk before own data starts, then own data ---
    if own_points:
        own_start = own_points[0][0]
        # Keep snkrdunk points before our data starts
        merged = [p for p in snkrdunk_points if p[0] < own_start]
        merged.extend(own_points)
        points = merged
    else:
        points = snkrdunk_points

    if not points:
        return ""

    release_date = product.release_date or ""
    points_json = json.dumps(points, ensure_ascii=False)
    # Number of snkrdunk points at the beginning of merged list
    # スタートデッキ等（定価2000円未満）は単品取引なので0.9倍補正しない
    no_correction = product.retail_price < 2000
    if no_correction:
        snkr_count = 0
    elif own_points:
        own_start = own_points[0][0]
        snkr_count = len([p for p in points if p[0] < own_start])
    else:
        snkr_count = len(points)
    box_name = product.name

    return f"""<h3 class="section-title">{box_name} 価格推移</h3>
<div class="chart-wrap">
<div class="chart-periods">
  <button class="cp-btn active" data-period="all">全期間</button>
  <button class="cp-btn" data-period="3m">3ヶ月</button>
  <button class="cp-btn" data-period="1m">1ヶ月</button>
</div>
<canvas id="boxChart"></canvas>
<div class="chart-note">※ 9店舗の最高買取価格の推移（過去分は参考データ）</div>
</div>
<script>
(function(){{
var pts={points_json};
var rd="{release_date}";
var snkrCount={snkr_count};
var ci=null;
function draw(period){{
  var now=Date.now(),cutoff=0;
  if(period==="3m")cutoff=now-90*86400000;
  else if(period==="1m")cutoff=now-30*86400000;
  var f=cutoff?pts.filter(function(p){{return p[0]>=cutoff}}):pts;
  if(!f.length)f=pts;
  var labels=f.map(function(p){{var d=new Date(p[0]);return d.getFullYear()+"/"+(d.getMonth()+1)+"/"+d.getDate()}});
  var sc=cutoff?pts.slice(0,snkrCount).filter(function(p){{return p[0]>=cutoff}}).length:snkrCount;
  var data=f.map(function(p,i){{return i<sc?Math.round(p[1]*0.9):p[1]}});
  var ridx=-1;
  if(rd){{var rt=new Date(rd+"T00:00:00+09:00").getTime();if(!cutoff||rt>=cutoff){{for(var i=0;i<f.length;i++){{if(f[i][0]>=rt){{ridx=i;break}}}}}}}}
  var ann=undefined;
  if(ridx>=0){{ann={{annotations:{{rl:{{type:"line",drawTime:"beforeDatasetsDraw",xMin:ridx,xMax:ridx,borderColor:"#ef4444",borderWidth:2,borderDash:[6,4],label:{{display:true,content:"発売日",position:"end",backgroundColor:"#ef4444",color:"#fff",font:{{size:11,weight:"bold"}},padding:{{top:3,bottom:3,left:6,right:6}},borderRadius:4}}}}}}}};}}
  if(ci)ci.destroy();
  ci=new Chart(document.getElementById("boxChart").getContext("2d"),{{
    type:"line",
    data:{{labels:labels,datasets:[{{label:"参考価格",data:data,borderColor:"#6366f1",backgroundColor:"rgba(99,102,241,.1)",fill:true,tension:0.3,pointRadius:f.length>60?0:2,pointHoverRadius:5,borderWidth:2}}]}},
    options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:"index",intersect:false}},
      plugins:{{legend:{{display:false}},annotation:ann,tooltip:{{callbacks:{{label:function(c){{return"\\u00a5"+c.parsed.y.toLocaleString()}}}}}}}},
      scales:{{x:{{ticks:{{maxTicksLimit:8,font:{{size:11}},color:"#6b7280"}},grid:{{display:false}}}},y:{{ticks:{{callback:function(v){{return"\\u00a5"+v.toLocaleString()}},font:{{size:11}},color:"#6b7280"}},grid:{{color:"#f3f4f6"}}}}}}
    }}
  }});
}}
draw("all");
document.querySelectorAll(".cp-btn").forEach(function(b){{
  b.addEventListener("click",function(){{
    document.querySelectorAll(".cp-btn").forEach(function(x){{x.classList.remove("active")}});
    b.classList.add("active");draw(b.dataset.period);
  }});
}});
}})();
</script>"""


def generate_product_pages(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate individual product pages for all BOX products."""
    box_dir = project_root / "box"
    box_dir.mkdir(exist_ok=True)

    template_path = project_root / "box-template.html"
    if not template_path.exists():
        logger.warning("box-template.html not found, skipping product pages")
        return

    template = template_path.read_text(encoding="utf-8")

    # Load product URL mapping (shop_id -> {scraped_name -> url})
    product_urls: dict[str, dict[str, str]] = {}
    urls_path = project_root / "data" / "product_urls.json"
    if urls_path.exists():
        try:
            product_urls = json.loads(urls_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Group products by category for related links
    by_cat: dict[str, list[MasterProduct]] = {}
    slug_map: dict[str, str] = {}  # product name -> slug
    for p in products:
        by_cat.setdefault(p.category, []).append(p)
        slug_map[p.name] = _generate_slug(p.name)

    total_products = len(products)
    generated = 0

    for p in products:
        slug = slug_map[p.name]
        active_prices = {sid: p.prices.get(sid, 0) for sid in SHOP_IDS if p.prices.get(sid, 0) > 0}

        if not active_prices:
            continue

        max_price = max(active_prices.values())
        max_shop_id = max(active_prices, key=active_prices.get)
        max_shop_name = SHOP_NAMES.get(max_shop_id, max_shop_id)
        shop_count = len(active_prices)
        diff = max_price - p.retail_price if p.retail_price > 0 and max_price > 0 else 0

        # Build price table rows (sorted by price desc)
        sorted_shops = sorted(
            [(sid, p.prices.get(sid, 0)) for sid in SHOP_IDS],
            key=lambda x: x[1],
            reverse=True,
        )
        table_rows = []
        for sid, price in sorted_shops:
            shop_name = SHOP_NAMES.get(sid, sid)
            # Try to find product-specific URL from mapping
            shop_url = _find_product_url(product_urls, sid, p) or SHOP_URLS.get(sid, "#")
            # 店舗名は自サイトの店舗別ページへ内部リンク、公式サイトは「公式↗」で併記
            shop_cell = (
                f'<a href="../shop/{sid}.html">{shop_name}</a>'
                f'<a class="shop-official" href="{shop_url}" target="_blank" rel="noopener noreferrer">公式↗</a>'
            )
            if price > 0:
                is_best = price == max_price
                tr_class = ' class="best"' if is_best else ""
                table_rows.append(
                    f'<tr{tr_class}>'
                    f'<td class="shop-name">{shop_cell}</td>'
                    f'<td>{_format_price(price)}</td>'
                    f'</tr>'
                )
            else:
                table_rows.append(
                    f'<tr><td class="shop-name">{shop_cell}</td><td class="no-price">取扱なし</td></tr>'
                )

        price_table = (
            '<table class="price-table">\n'
            '<tr><th>買取店</th><th>買取価格</th></tr>\n'
            + "\n".join(table_rows)
            + "\n</table>"
        )

        # Related links (same category, exclude self, 同時発売BOXを先頭に)
        related = [
            r for r in by_cat.get(p.category, [])
            if r.name != p.name and any(r.prices.get(s, 0) > 0 for s in SHOP_IDS)
        ]
        related.sort(key=lambda r: (0 if r.release_date == p.release_date and p.release_date else 1))
        related_html = "\n".join(
            f'    <a href="{slug_map[r.name]}.html" class="related-link">{r.name}</a>'
            for r in related
        )

        # Diff text
        if diff > 0:
            diff_text = f"+\u00a5{diff:,}"
        elif diff < 0:
            diff_text = f"-\u00a5{abs(diff):,}"
        else:
            diff_text = "-"

        # Individual BOX image (falls back to ogp.jpg for slugs not yet mapped)
        box_image_url = get_box_image_url(slug)

        # JSON-LD for individual product
        # 個別店舗 Offer リスト (AggregateOffer.offers として埋め込み)
        shop_offers = []
        for sid, price in sorted_shops:
            if price <= 0:
                continue
            shop_offers.append({
                "@type": "Offer",
                "seller": {
                    "@type": "Organization",
                    "name": SHOP_NAMES.get(sid, sid),
                },
                "price": price,
                "priceCurrency": "JPY",
                "availability": "https://schema.org/InStock",
                "url": _find_product_url(product_urls, sid, p) or SHOP_URLS.get(sid, "#"),
            })
        product_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": p.name,
            "description": f"ポケモンカード {p.name} 未開封BOX 買取価格比較",
            "image": box_image_url,
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "category": "トレーディングカードゲーム / ポケモンカード / 未開封BOX",
            "sku": f"pokeca-box-{slug}",
            "url": f"https://pokeca-box-hikaku.com/box/{slug}.html",
            "offers": {
                "@type": "AggregateOffer",
                "lowPrice": min(active_prices.values()),
                "highPrice": max_price,
                "priceCurrency": "JPY",
                "offerCount": shop_count,
                "availability": "https://schema.org/InStock",
                "offers": shop_offers,
            },
        }, ensure_ascii=False, indent=2)
        breadcrumb_jsonld = json.dumps({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 2, "name": "買取価格比較", "item": "https://pokeca-box-hikaku.com/"},
                {"@type": "ListItem", "position": 3, "name": p.name},
            ],
        }, ensure_ascii=False, indent=2)

        # FAQ: 事実ベースのQ&A (絶版・再販など推測要素は入れない)
        faq_items: list[dict] = []
        if p.release_date:
            try:
                rd = datetime.strptime(p.release_date, "%Y-%m-%d").date()
                faq_items.append({
                    "q": f"{p.name}はいつ発売されましたか？",
                    "a": f"{p.name}は{rd.year}年{rd.month}月{rd.day}日に発売されたBOXです。",
                })
            except ValueError:
                pass
        if p.retail_price > 0:
            faq_items.append({
                "q": f"{p.name}の定価はいくらですか？",
                "a": f"{p.name}の定価(メーカー希望小売価格)は1BOXあたり¥{p.retail_price:,}(税込)です。",
            })
        if max_price > 0:
            faq_items.append({
                "q": f"{p.name}の最高買取価格はいくらですか？",
                "a": (
                    f"{update_date}時点の最高買取価格は¥{max_price:,}({max_shop_name})です。"
                    f"当サイトでは{shop_count}店舗の買取価格を毎日自動比較しています。"
                ),
            })
        if p.retail_price > 0 and max_price > 0:
            ratio = max_price / p.retail_price
            if ratio >= 1.3:
                faq_items.append({
                    "q": f"{p.name}は定価より高く売れますか？",
                    "a": (
                        f"現在の最高買取価格¥{max_price:,}は定価¥{p.retail_price:,}の約{ratio:.1f}倍です。"
                        f"ただしシュリンク有無・外箱の状態により実際の買取額は変動します。"
                    ),
                })
        if p.hit_cards:
            card_names = [
                c[0] if isinstance(c, (list, tuple)) else c
                for c in p.hit_cards[:3]
            ]
            faq_items.append({
                "q": f"{p.name}の当たりカードは何ですか？",
                "a": (
                    f"主な当たりカードは「{'」「'.join(card_names)}」です。"
                    f"これらの高額レアカードを引けるかどうかがBOX相場に影響しています。"
                ),
            })

        if faq_items:
            faq_jsonld = json.dumps({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": it["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": it["a"]},
                    }
                    for it in faq_items
                ],
            }, ensure_ascii=False, indent=2)
            faq_html = (
                '<h3 class="section-title">よくある質問</h3>\n'
                '<div class="faq-list">\n'
                + "\n".join(
                    f'<details class="faq-item"><summary>{it["q"]}</summary>'
                    f'<div class="faq-answer">{it["a"]}</div></details>'
                    for it in faq_items
                )
                + '\n</div>'
            )
        else:
            faq_jsonld = ""
            faq_html = ""

        jsonld_parts = [
            f'<script type="application/ld+json">\n{product_jsonld}\n</script>',
            f'<script type="application/ld+json">\n{breadcrumb_jsonld}\n</script>',
        ]
        if faq_jsonld:
            jsonld_parts.append(
                f'<script type="application/ld+json">\n{faq_jsonld}\n</script>'
            )
        jsonld_tag = "\n".join(jsonld_parts)

        # Generate chart section for this product
        chart_section = _generate_box_chart_section(p, project_root)

        # Generate trend comment (1-liner above product description)
        trend_comment_html = _generate_trend_comment(
            p.name,
            project_root / "data" / "history",
            max_price,
        )

        # Replace all placeholders
        html = template
        html = html.replace("{{PRODUCT_NAME}}", p.name)
        html = html.replace("{{PRODUCT_DESC}}", p.desc or "")
        # 当たりカードセクション
        if p.hit_cards:
            top_cards = p.hit_cards[:3]
            cards_html = '<div class="hit-cards"><h3>当たりカード</h3><dl class="hit-list">'
            for card in top_cards:
                if isinstance(card, (list, tuple)) and len(card) >= 2:
                    name, comment = card[0], card[1]
                else:
                    name, comment = card, ""
                cards_html += f"<dt>{name}</dt>"
                if comment:
                    cards_html += f"<dd>{comment}</dd>"
            cards_html += '</dl></div>'
        else:
            cards_html = ""
        html = html.replace("{{HIT_CARDS}}", cards_html)
        # description用の当たりカード名テキスト
        if p.hit_cards:
            card_names = [c[0] if isinstance(c, (list, tuple)) else c for c in p.hit_cards[:3]]
            hit_text = "当たりカード: " + "、".join(card_names) + "。"
        else:
            hit_text = ""
        html = html.replace("{{HIT_CARDS_TEXT}}", hit_text)
        html = html.replace("{{SLUG}}", slug)
        html = html.replace("{{MAX_PRICE_TEXT}}", _format_price(max_price))
        html = html.replace("{{MAX_SHOP_NAME}}", max_shop_name)
        html = html.replace("{{SHOP_COUNT}}", str(shop_count))
        html = html.replace("{{RETAIL_PRICE_TEXT}}", _format_price(p.retail_price))
        html = html.replace("{{DIFF_TEXT}}", diff_text)
        html = html.replace("{{CATEGORY_LABEL}}", CATEGORY_LABELS.get(p.category, p.category))
        html = html.replace("{{PRICE_TABLE}}", price_table)
        html = html.replace("{{RELATED_LINKS}}", related_html)
        html = html.replace("{{TOTAL_PRODUCTS}}", str(total_products))
        html = html.replace("{{UPDATE_DATE}}", update_date)
        html = html.replace("{{BOX_IMAGE_URL}}", box_image_url)
        # ヒーロー画像 (マップされたBOXのみ表示、それ以外は空)
        if slug in BOX_IMAGE_FILES:
            # SEO alt: 商品名 + 未開封BOX + 買取価格 + 定価倍率(retailがあれば)
            if p.retail_price and p.retail_price > 0 and max_price > 0:
                ratio = max_price / p.retail_price
                alt_text = f"{p.name} 未開封BOX 買取価格¥{max_price:,} 定価{ratio:.1f}倍"
            elif max_price > 0:
                alt_text = f"{p.name} 未開封BOX 買取価格¥{max_price:,}"
            else:
                alt_text = f"{p.name} 未開封BOX"
            jpg_name = BOX_IMAGE_FILES[slug]
            webp_name = jpg_name.rsplit(".", 1)[0] + ".webp"
            box_hero_html = (
                f'<div class="box-hero">'
                f'<picture>'
                f'<source srcset="../images/boxes/{webp_name}" type="image/webp">'
                f'<img src="../images/boxes/{jpg_name}" '
                f'alt="{alt_text}" '
                f'loading="eager" fetchpriority="high" decoding="async" '
                f'width="280" height="280">'
                f'</picture>'
                f'</div>'
            )
            hero_preload = (
                f'<link rel="preload" as="image" '
                f'href="../images/boxes/{webp_name}" '
                f'type="image/webp" fetchpriority="high">'
            )
        else:
            box_hero_html = ""
            hero_preload = ""
        # 独自narrative(150-300字程度): 商品ごとに異なる動的解説テキスト
        narrative_html = _build_box_narrative(p, max_price, shop_count, slug)

        # noindex判定: 取扱店舗が3未満 or 定価の半分未満は薄ページ扱い
        # ただし高額BOXは検索需要が大きいため店舗数によらずインデックス対象
        thin_page = shop_count < 3 or (p.retail_price > 0 and max_price < p.retail_price * 0.5)
        if thin_page and max_price < HIGH_VALUE_BOX_PRICE:
            robots_meta = "noindex, follow"
        else:
            robots_meta = "index, follow"

        html = html.replace("{{BOX_HERO}}", box_hero_html)
        html = html.replace("{{HERO_PRELOAD}}", hero_preload)
        html = html.replace("{{JSONLD}}", jsonld_tag)
        html = html.replace("{{FAQ_SECTION}}", faq_html)
        html = html.replace("{{TREND_COMMENT}}", trend_comment_html)
        html = html.replace("{{BOX_NARRATIVE}}", narrative_html)
        html = html.replace("{{ROBOTS}}", robots_meta)
        html = html.replace("<!-- {{CHART_SECTION}} -->", chart_section)

        # Write file
        out_path = box_dir / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        generated += 1

    logger.info("Generated %d product pages in %s", generated, box_dir)

    # Update sitemap
    _update_sitemap(products, slug_map, project_root)


# ===== 店舗別ページ (/shop/{shop_id}.html) =====

AFFILIATE_BLOCK = """<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>"""


def _load_onepiece_prices(project_root: Path) -> list[dict]:
    """data/history_op の最新JSONから [{slug, name, prices}] を返す。"""
    hist_dir = project_root / "data" / "history_op"
    if not hist_dir.exists():
        return []
    files = sorted(hist_dir.glob("*.json"))
    if not files:
        return []
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out = []
    for r in data:
        m = re.search(r"(OP|EB|PRB|ST)-?(\d+)", r.get("name", ""))
        if not m:
            continue
        prices = {k: v for k, v in r.get("prices", {}).items() if v > 0}
        if not prices:
            continue
        out.append({
            "slug": f"{m.group(1).lower()}-{int(m.group(2)):02d}",
            "name": r["name"],
            "prices": prices,
        })
    return out


def _shop_rows(items: list[dict], shop_id: str, link_prefix: str) -> tuple[list[str], int, list[tuple]]:
    """店舗の取扱行HTML・最高値件数・最高値商品リストを返す。

    items: [{slug, name, prices}] 形式(価格>0のみ)
    """
    rows, best_count, best_items = [], 0, []
    ranked = []
    for it in items:
        price = it["prices"].get(shop_id, 0)
        if price <= 0:
            continue
        others = [v for k, v in it["prices"].items() if k != shop_id]
        top = max(it["prices"].values())
        is_best = price == top
        gap = price - max(others) if others else 0
        ranked.append((price, it, is_best, gap))
    ranked.sort(key=lambda x: -x[0])
    for price, it, is_best, gap in ranked:
        if is_best:
            best_count += 1
            best_items.append((it["name"], it["slug"], price, gap))
        cls = ' class="best"' if is_best else ""
        badge = ' <span class="best-badge">最高値</span>' if is_best else ""
        rows.append(
            f'<tr{cls}><td><a href="{link_prefix}{it["slug"]}.html">{it["name"]}</a>{badge}</td>'
            f'<td class="price">{_format_price(price)}</td></tr>'
        )
    return rows, best_count, best_items


def _avg_gap_pct(items: list[dict], shop_id: str) -> float | None:
    """他店平均に対する平均乖離率(%)。比較可能な商品が無ければ None。"""
    diffs = []
    for it in items:
        price = it["prices"].get(shop_id, 0)
        others = [v for k, v in it["prices"].items() if k != shop_id]
        if price > 0 and others:
            avg = sum(others) / len(others)
            if avg > 0:
                diffs.append((price - avg) / avg * 100)
    if not diffs:
        return None
    return sum(diffs) / len(diffs)


def generate_shop_pages(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """店舗別の買取価格一覧ページを生成する (店舗名クエリの受け皿)。"""
    shop_dir = project_root / "shop"
    shop_dir.mkdir(exist_ok=True)

    base = "https://pokeca-box-hikaku.com"

    poke_items = []
    for p in products:
        prices = {sid: p.prices.get(sid, 0) for sid in SHOP_IDS if p.prices.get(sid, 0) > 0}
        if prices:
            poke_items.append({"slug": _generate_slug(p.name), "name": p.name, "prices": prices})
    op_items = _load_onepiece_prices(project_root)

    generated = 0
    for shop_id in SHOP_IDS:
        name = SHOP_NAMES.get(shop_id, shop_id)
        profile = SHOP_PROFILES.get(shop_id, {})
        official = SHOP_URLS.get(shop_id, "#")

        p_rows, p_best, p_best_items = _shop_rows(poke_items, shop_id, "../box/")
        o_rows, o_best, o_best_items = _shop_rows(op_items, shop_id, "../onepiece/box/")
        if not p_rows and not o_rows:
            continue

        total = len(p_rows) + len(o_rows)
        best_total = p_best + o_best
        gap = _avg_gap_pct(poke_items + op_items, shop_id)

        html = _build_shop_page_html(
            shop_id=shop_id, name=name, profile=profile, official=official,
            p_rows=p_rows, o_rows=o_rows, p_best_items=p_best_items,
            o_best_items=o_best_items, total=total, best_total=best_total,
            gap=gap, update_date=update_date, base=base,
        )
        (shop_dir / f"{shop_id}.html").write_text(html, encoding="utf-8")
        generated += 1

    logger.info("Generated %d shop pages in %s", generated, shop_dir)


SHOP_PAGE_STYLE = """<style>
:root{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#d97706}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}
.header{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}
.header a{text-decoration:none}
.header .logo{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.wrap{max-width:900px;margin:0 auto;padding:28px 16px 48px}
.breadcrumb{font-size:12px;color:var(--text-sub);margin-bottom:18px}
.breadcrumb a{color:var(--accent);text-decoration:none}
article{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:30px 26px;margin-bottom:24px}
article h1{font-size:23px;font-weight:800;margin-bottom:8px;line-height:1.4;background:linear-gradient(135deg,#d97706,#b45309);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.meta{font-size:12px;color:var(--text-sub);margin-bottom:22px}
article h2{font-size:18px;font-weight:700;margin:30px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
article p{font-size:14px;margin-bottom:14px}
article ul{font-size:14px;padding-left:22px;margin-bottom:14px}
article li{margin-bottom:8px}
.hero{margin-bottom:22px;padding:18px 20px;background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:12px;border:1px solid #fbbf24}
.hero .stat-label{font-size:11px;color:#92400e;font-weight:700;letter-spacing:.5px}
.hero .stat-big{font-size:26px;font-weight:800;color:#b45309;line-height:1.25;margin:4px 0 10px}
.hero .stat-sub{font-size:12px;color:#78350f}
.price-table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
.price-table th,.price-table td{padding:9px 11px;border-bottom:1px solid var(--border)}
.price-table th{background:#f9fafb;text-align:left;font-size:11px;color:var(--text-sub);letter-spacing:.5px}
.price-table tr.best td{background:#fef3c7}
.price-table td.price{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
.price-table a{color:var(--text);text-decoration:none}
.price-table a:hover{color:var(--accent);text-decoration:underline}
.best-badge{display:inline-block;font-size:10px;font-weight:700;color:#b45309;background:#fff7ed;border:1px solid #fbbf24;border-radius:4px;padding:1px 5px;margin-left:6px;vertical-align:middle}
.callout{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:14px 18px;margin:14px 0;font-size:13px}
.callout strong{color:#1d4ed8}
.tags span{display:inline-block;font-size:11px;font-weight:700;color:#b45309;background:#fff7ed;border:1px solid #fbbf24;border-radius:999px;padding:2px 10px;margin-right:6px}
.disclaimer{background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:14px 18px;margin:22px 0;font-size:12px;color:#9a3412}
.disclaimer strong{color:#c2410c}
.cta{display:block;text-align:center;padding:15px;background:linear-gradient(135deg,#d97706,#b45309);color:#fff;border-radius:12px;text-decoration:none;font-weight:700;margin:22px 0}
.shop-links{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.shop-links a{font-size:13px;padding:7px 12px;border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--text);text-decoration:none}
.shop-links a:hover{border-color:var(--accent);color:var(--accent)}
.back{display:inline-block;margin-top:14px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600;margin-right:16px}
.ad{text-align:center;padding:12px 0}
.ft{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}
.ft a{color:var(--accent)}
@media(max-width:640px){article{padding:20px 16px}article h1{font-size:19px}.hero .stat-big{font-size:21px}}
</style>"""


def _build_shop_page_html(
    *, shop_id: str, name: str, profile: dict, official: str,
    p_rows: list[str], o_rows: list[str], p_best_items: list[tuple],
    o_best_items: list[tuple], total: int, best_total: int,
    gap: float | None, update_date: str, base: str,
) -> str:
    url = f"{base}/shop/{shop_id}.html"
    has_op = bool(o_rows)
    scope = "ポケカ・ワンピ" if has_op else "ポケカ"

    # title は SERP 表示上限(全角約32字)に収める。サイト名は og:site_name 側に持たせる
    title = f"{name}の{scope}BOX買取価格一覧【全{total}商品】"
    desc = (
        f"{name}のポケモンカード{'・ワンピースカード' if has_op else ''}未開封BOX買取価格を"
        f"全{total}商品まとめて掲載。うち{best_total}商品が当サイト掲載9店舗中の最高値です。"
        f"毎日3回自動更新で、他店との価格差も商品ごとに比較できます。"
    )

    # 最高値ランキング (差額の大きい順・上位10件)
    best_all = sorted(
        [(n, s, pr, g, "../box/") for n, s, pr, g in p_best_items]
        + [(n, s, pr, g, "../onepiece/box/") for n, s, pr, g in o_best_items],
        key=lambda x: -x[3],
    )[:10]
    if best_all:
        brows = "".join(
            f'<tr><td><a href="{pre}{s}.html">{n}</a></td>'
            f'<td class="price">{_format_price(pr)}</td>'
            f'<td class="price">{("+" + _format_price(g)) if g > 0 else "同率1位"}</td></tr>'
            for n, s, pr, g, pre in best_all
        )
        best_section = (
            f'<h2>{name}が最高値をつけているBOX</h2>'
            f'<p>当サイト掲載9店舗の買取価格を突き合わせた結果、<strong>{name}が最も高い金額を提示している商品が{best_total}件</strong>'
            f'あります。差額が大きい順に上位を掲載します（2位の店舗との差）。</p>'
            f'<table class="price-table"><thead><tr><th>商品</th>'
            f'<th style="text-align:right">{name}の買取価格</th>'
            f'<th style="text-align:right">2位との差</th></tr></thead><tbody>{brows}</tbody></table>'
        )
    else:
        best_section = (
            f'<h2>{name}の価格ポジション</h2>'
            f'<p>2026年{update_date}時点では、{name}が9店舗中の最高値をつけている商品はありません。'
            f'ただし買取価格は毎日動くため、売却前には最新の比較をご確認ください。</p>'
        )

    if gap is None:
        gap_html = ""
    elif gap >= 0:
        gap_html = (
            f'<div class="callout"><strong>他店との比較:</strong> 同じ商品を扱う他店の平均と比べて、'
            f'{name}の買取価格は平均で<strong>約{gap:.1f}%高い</strong>水準です（当サイト掲載商品の実測平均）。</div>'
        )
    else:
        gap_html = (
            f'<div class="callout"><strong>他店との比較:</strong> 同じ商品を扱う他店の平均と比べて、'
            f'{name}の買取価格は平均で<strong>約{abs(gap):.1f}%低い</strong>水準です（当サイト掲載商品の実測平均）。'
            f'商品によっては最高値になる場合もあるため、個別の価格をご確認ください。</div>'
        )

    poke_section = (
        f'<h2>{name}のポケカBOX買取価格一覧（{len(p_rows)}商品）</h2>'
        f'<p>買取価格の高い順に並べています。商品名から各BOXの9店舗比較ページへ移動できます。</p>'
        f'<table class="price-table"><thead><tr><th>商品</th>'
        f'<th style="text-align:right">買取価格</th></tr></thead><tbody>{"".join(p_rows)}</tbody></table>'
    ) if p_rows else ""

    op_section = (
        f'<h2>{name}のワンピカードBOX買取価格一覧（{len(o_rows)}商品）</h2>'
        f'<p>ONE PIECEカードゲームの未開封BOXも取り扱っています。商品名から各BOXの比較ページへ移動できます。</p>'
        f'<table class="price-table"><thead><tr><th>商品</th>'
        f'<th style="text-align:right">買取価格</th></tr></thead><tbody>{"".join(o_rows)}</tbody></table>'
    ) if o_rows else ""

    others = "".join(
        f'<a href="{sid}.html">{SHOP_NAMES.get(sid, sid)}</a>'
        for sid in SHOP_IDS if sid != shop_id
    )

    methods = "".join(f"<span>{m}</span>" for m in profile.get("methods", []))
    itemlist = {
        "@context": "https://schema.org", "@type": "ItemList",
        "name": f"{name}のBOX買取価格一覧",
        "numberOfItems": total,
        "itemListElement": [
            {"@type": "ListItem", "position": i,
             "name": n, "url": f"{base}/{pre.replace('../', '')}{s}.html"}
            for i, (n, s, _pr, _g, pre) in enumerate(best_all, 1)
        ],
    }
    crumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "買取店比較", "item": f"{base}/shop-hikaku.html"},
            {"@type": "ListItem", "position": 3, "name": f"{name}の買取価格一覧"},
        ],
    }

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{base}/ogp.png">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<title>{title}</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<script type="application/ld+json">
{json.dumps(crumb, ensure_ascii=False, indent=0)}
</script>
<script type="application/ld+json">
{json.dumps(itemlist, ensure_ascii=False, indent=0)}
</script>
{SHOP_PAGE_STYLE}
</head>
<body>
<div class="header"><a href="../index.html"><span class="logo">ポケカ買取チェッカー</span></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="../index.html">トップ</a> &gt; <a href="../shop-hikaku.html">買取店比較</a> &gt; {name}の買取価格一覧</div>

<article>
<h1>{name}の{scope}BOX買取価格一覧｜全{total}商品を毎日自動更新</h1>
<div class="meta">更新: {update_date} / 当サイト掲載9店舗の実測データ / ポケカ買取チェッカー</div>

<div class="hero">
<div class="stat-label">{name} 掲載商品数と最高値件数（{update_date}時点）</div>
<div class="stat-big">全{total}商品 / 最高値 {best_total}件</div>
<div class="stat-sub">当サイトが毎日3回自動収集した9店舗の買取価格をもとに、{name}の取扱商品と価格を一覧化しています。価格はすべて実測値です。</div>
</div>

<p>このページでは、<strong>{name}</strong>が買取対象としているポケモンカード{'・ONE PIECEカード' if has_op else ''}の未開封BOXについて、<strong>現在の買取価格を全{total}商品ぶん掲載</strong>しています。当サイトは9店舗の買取ページを毎日3回自動で収集しているため、<strong>{name}が他店と比べて高いのか安いのか</strong>を商品単位で確認できます。</p>

{best_section}

{gap_html}

{poke_section}

{op_section}

<h2>{name}の基本情報</h2>
<div class="tags">{methods}</div>
<p>{profile.get('desc', '')}</p>
<ul>
<li><strong>公式サイト</strong>: <a href="{official}" target="_blank" rel="noopener noreferrer">{official}</a></li>
<li><strong>当サイト掲載商品数</strong>: {total}商品（ポケカ{len(p_rows)}{f' / ワンピ{len(o_rows)}' if has_op else ''}）</li>
<li><strong>9店舗中で最高値の商品</strong>: {best_total}件</li>
</ul>

<a href="{official}" class="cta" target="_blank" rel="noopener noreferrer">{name}の公式サイトで買取条件を確認する &rarr;</a>

<h2>他の買取店の価格も見る</h2>
<p>売却前には複数店舗の比較をおすすめします。同じBOXでも店舗により買取価格は異なり、高額BOXほど差が大きくなります。</p>
<div class="shop-links">{others}</div>
<p><a href="../shop-hikaku.html">9店舗の特徴を比較する</a> / <a href="../index.html">全BOXの買取価格を比較する</a> / <a href="../ranking.html">週間価格変化ランキング</a></p>

<div class="disclaimer">
<strong>ご注意:</strong> 掲載価格は当サイトが{name}の公開買取情報から自動取得した{update_date}時点の実測値です。買取価格は需給や在庫状況により日々変動し、シュリンクの有無・外箱の状態等により実際の査定額は変わります。最終的な価格・条件は必ず{name}の公式サイトでご確認ください。当サイトは{name}とは独立した第三者の比較サイトであり、掲載内容について同店が保証するものではありません。
</div>

<a href="../shop-hikaku.html" class="back">&larr; 買取店比較へ</a>
<a href="../index.html" class="back">&larr; 買取価格比較トップ</a>
</article>
</div>

{AFFILIATE_BLOCK}

<div class="ft">
  <a href="../index.html">ポケカ買取チェッカー</a> / <a href="../privacy.html">プライバシーポリシー</a>
</div>
</body>
</html>
"""


def _last_price_change_dates(project_root: Path) -> dict[str, str]:
    """商品ごとに最高買取価格が最後に変わった日を日次履歴から求める。

    sitemap の lastmod に使う。全ページを毎日 today で更新したことにすると
    lastmod 自体が検索エンジンに信用されなくなり、クロール優先度が下がるため。
    """
    hist_dir = project_root / "data" / "history"
    if not hist_dir.exists():
        return {}

    last_price: dict[str, int] = {}
    changed_on: dict[str, str] = {}
    for path in sorted(hist_dir.glob("*.json")):
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(items, dict):
            items = list(items.values())
        for item in items:
            name = item.get("name")
            price = item.get("max_price") or 0
            if not name or not price:
                continue
            if last_price.get(name) != price:
                last_price[name] = price
                changed_on[name] = path.stem
    return changed_on


def _update_sitemap(
    products: list[MasterProduct],
    slug_map: dict[str, str],
    project_root: Path,
) -> None:
    """Regenerate sitemap.xml including all product pages."""
    base = "https://pokeca-box-hikaku.com"
    today = datetime.now(JST).strftime("%Y-%m-%d")

    # Static pages: (path, changefreq, priority, lastmod)
    # 記事ページは lastmod を個別管理 (手動更新日)
    static_pages = [
        ("/", "daily", "1.0", today),
        ("/ranking.html", "daily", "0.9", today),
        ("/weekly/", "weekly", "0.9", today),
        ("/souba-mynumber-2026.html", "monthly", "0.9", "2026-06-09"),
        ("/inferno-x-spotlight.html", "monthly", "0.8", "2026-04-12"),
        ("/151-spotlight.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-spotlight.html", "monthly", "0.8", "2026-04-14"),
        ("/chouden-breaker-spotlight.html", "monthly", "0.8", "2026-04-15"),
        ("/clay-burst-spotlight.html", "monthly", "0.8", "2026-04-15"),
        ("/ninja-spinner-spotlight.html", "monthly", "0.8", "2026-04-16"),
        ("/rocket-dan-no-eiko-spotlight.html", "monthly", "0.8", "2026-04-25"),
        ("/mega-ex-spotlight.html", "monthly", "0.8", "2026-05-03"),
        ("/mega-brave-spotlight.html", "monthly", "0.8", "2026-05-19"),
        ("/battle-collection-spotlight.html", "monthly", "0.8", "2026-06-06"),
        ("/abyss-eye-forecast.html", "monthly", "0.8", "2026-04-21"),
        ("/abyss-eye-review.html", "monthly", "0.8", "2026-05-22"),
        ("/storm-emeralda-forecast.html", "monthly", "0.8", "2026-07-19"),
        ("/storm-emeralda-review.html", "monthly", "0.9", "2026-08-02"),
        ("/storm-emeralda-spotlight.html", "monthly", "0.9", "2026-08-10"),
        ("/zeppan-ranking-2026-03.html", "monthly", "0.8", "2026-04-14"),
        ("/lizardon-box-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/mega-pack-compare.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-vs-rocket.html", "monthly", "0.8", "2026-04-14"),
        ("/mega-lizardon-x-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/lizardon-sar-kokuen-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/erika-sar-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/pigeot-sar-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/masterball-mirror-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/kokuen-atari-guide.html", "monthly", "0.8", "2026-04-14"),
        ("/startdeck100-atari-guide.html", "monthly", "0.8", "2026-06-19"),
        ("/startdeck100-miwakekata.html", "monthly", "0.9", "2026-08-10"),
        ("/abyss-eye-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/mega-ex-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/inferno-x-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/mega-brave-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/chouden-breaker-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/clay-burst-atari-guide.html", "monthly", "0.8", "2026-07-12"),
        ("/ninja-spinner-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/munikis-zero-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/mega-sinfonia-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/black-bolt-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/rocket-dan-no-eiko-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/eevee-heroes-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/151-atari-guide.html", "monthly", "0.8", "2026-07-19"),
        ("/crimson-haze-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/hengen-no-kamen-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/rakuen-dragona-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/night-wanderer-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/raging-surf-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/scarlet-ex-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/future-flash-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/stellar-miracle-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/ancient-roar-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/triplet-beat-atari-guide.html", "monthly", "0.9", "2026-08-10"),
        ("/cyber-judge-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/snow-hazard-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/neppuu-arena-atari-guide.html", "monthly", "0.9", "2026-08-10"),
        ("/30th-celebration-atari-yosou.html", "weekly", "0.9", "2026-08-11"),
        ("/30th-celebration-forecast.html", "weekly", "0.9", "2026-08-11"),
        ("/eruption-walker-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/legendary-heartbeat-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/vmax-climax-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/astonishing-voltecker-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/matchless-fighters-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/lost-abyss-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/single-strike-master-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/rapid-strike-master-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/infinity-zone-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/rebellion-crash-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/fusion-arts-atari-guide.html", "monthly", "0.8", "2026-08-11"),
        ("/vmax-rising-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/blue-sky-stream-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/battle-partners-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/wild-force-atari-guide.html", "monthly", "0.8", "2026-08-10"),
        ("/white-flare-atari-guide.html", "monthly", "0.8", "2026-07-26"),
        ("/terastal-fes-ex-atari-guide.html", "monthly", "0.8", "2026-07-26"),
        ("/shiny-treasure-ex-atari-guide.html", "monthly", "0.8", "2026-07-26"),
        ("/restock-guide.html", "monthly", "0.8", "2026-04-10"),
        ("/sv-box-list.html", "daily", "0.8", today),
        ("/mega-box-list.html", "daily", "0.8", today),
        ("/ss-box-list.html", "daily", "0.8", today),
        ("/release-schedule-2026.html", "monthly", "0.8", "2026-04-15"),
        ("/price-pattern-guide.html", "monthly", "0.8", "2026-04-16"),
        ("/box-toushi.html", "monthly", "0.8", "2026-04-02"),
        ("/shrink-nashi.html", "monthly", "0.8", "2026-03-27"),
        ("/mercari-hikaku.html", "monthly", "0.8", "2026-03-26"),
        ("/psa-guide.html", "monthly", "0.8", "2026-03-24"),
        ("/single-card-tips.html", "monthly", "0.8", "2026-03-24"),
        ("/shop-hikaku.html", "monthly", "0.8", "2026-03-23"),
        ("/kaitori-tips.html", "monthly", "0.8", "2026-03-23"),
        ("/monthly-ranking-2026-03.html", "monthly", "0.7", "2026-04-01"),
        ("/privacy.html", "monthly", "0.5", "2026-04-26"),
        ("/about.html", "monthly", "0.7", "2026-04-26"),
        ("/contact.html", "monthly", "0.6", "2026-04-26"),
    ]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for path, freq, priority, lastmod in static_pages:
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}{path}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append(f"  </url>")

    # Product pages (重複URL防止のため slug を set で管理)
    price_changed_on = _last_price_change_dates(project_root)
    seen_slugs: set[str] = set()
    for p in products:
        slug = slug_map.get(p.name)
        if not slug or slug in seen_slugs:
            continue
        if not any(p.prices.get(s, 0) > 0 for s in SHOP_IDS):
            continue
        seen_slugs.add(slug)
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}/box/{slug}.html</loc>")
        lines.append(f"    <lastmod>{price_changed_on.get(p.name, today)}</lastmod>")
        lines.append(f"    <changefreq>daily</changefreq>")
        lines.append(f"    <priority>0.7</priority>")
        lines.append(f"  </url>")

    # 店舗別買取価格ページ
    shop_dir = project_root / "shop"
    if shop_dir.exists():
        for sid in SHOP_IDS:
            if not (shop_dir / f"{sid}.html").exists():
                continue
            lines.append(f"  <url>")
            lines.append(f"    <loc>{base}/shop/{sid}.html</loc>")
            lines.append(f"    <lastmod>{today}</lastmod>")
            lines.append(f"    <changefreq>daily</changefreq>")
            lines.append(f"    <priority>0.7</priority>")
            lines.append(f"  </url>")

    # Weekly hot-boxes articles (archived)
    weekly_dir = project_root / "weekly"
    if weekly_dir.exists():
        for wf in sorted(weekly_dir.glob("*.html")):
            if wf.name == "index.html":
                continue
            lines.append(f"  <url>")
            lines.append(f"    <loc>{base}/weekly/{wf.name}</loc>")
            lines.append(f"    <lastmod>{today}</lastmod>")
            lines.append(f"    <changefreq>weekly</changefreq>")
            lines.append(f"    <priority>0.8</priority>")
            lines.append(f"  </url>")

    # Monthly ranking articles (archived — auto-generated per completed month)
    for mf in sorted(project_root.glob("monthly-ranking-*.html")):
        # Skip the manually-listed 2026-03 entry to avoid duplicates
        if any(f"/{mf.name}" == p[0] for p in static_pages):
            continue
        lines.append(f"  <url>")
        lines.append(f"    <loc>{base}/{mf.name}</loc>")
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>monthly</changefreq>")
        lines.append(f"    <priority>0.7</priority>")
        lines.append(f"  </url>")

    lines.append("</urlset>")
    lines.append("")

    sitemap_path = project_root / "sitemap.xml"
    sitemap_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Updated sitemap.xml (%d URLs)", len([l for l in lines if "<loc>" in l]))


def _generate_ranking_summary(
    products: list[MasterProduct],
    project_root: Path,
) -> str:
    """トップページ用の週間上昇ランキングサマリーを生成する。"""
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        return ""

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 2:
        return ""

    today_file = files[-1]
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    slug_map = {p.name: _generate_slug(p.name) for p in products}
    changes = []
    for p in products:
        if p.category not in ("sv", "mega"):
            continue
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        if diff > 0:
            pct = (diff / wp) * 100
            changes.append({"name": p.name, "slug": slug_map.get(p.name, ""), "diff": diff, "pct": pct})

    top5 = sorted(changes, key=lambda x: x["diff"], reverse=True)[:5]
    if not top5:
        return ""

    items_html = ""
    for c in top5:
        items_html += (
            f'<li>'
            f'<span class="rs-name"><a href="box/{c["slug"]}.html">{c["name"]}</a></span>'
            f'<span class="rs-change" style="color:#dc2626">+¥{c["diff"]:,} (+{c["pct"]:.1f}%)</span>'
            f'</li>'
        )

    return (
        '<div class="ranking-summary">'
        '<div class="rs-card">'
        '<h3><a href="ranking.html">週間 価格変化ランキング</a></h3>'
        f'<ul class="rs-list">{items_html}</ul>'
        '<a href="ranking.html" class="rs-more">もっと見る &rarr;</a>'
        '</div>'
        '</div>'
    )


def generate_ranking_page(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """週間の上昇ランキングページをグラフ付きで生成する。"""
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        return

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 2:
        logger.info("Not enough history data for ranking page")
        return

    today_file = files[-1]
    # 7日前のデータ（なければ最も古いデータ）
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    # 差分計算（カテゴリ付き）
    changes = []
    slug_map = {p.name: _generate_slug(p.name) for p in products}
    cat_map = {p.name: p.category for p in products}
    for p in products:
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        pct = (diff / wp) * 100 if wp > 0 else 0
        changes.append({
            "name": p.name,
            "slug": slug_map.get(p.name, ""),
            "category": cat_map.get(p.name, ""),
            "today": tp,
            "week_ago": wp,
            "diff": diff,
            "pct": pct,
        })

    # MEGA+SV: 上昇TOP5
    sv_mega = [c for c in changes if c["category"] in ("sv", "mega")]
    sv_gainers = sorted([c for c in sv_mega if c["diff"] > 0], key=lambda x: x["diff"], reverse=True)[:10]

    # S&S: 高騰TOP3のみ
    ss = [c for c in changes if c["category"] == "ss"]
    ss_gainers = sorted([c for c in ss if c["diff"] > 0], key=lambda x: x["diff"], reverse=True)[:3]

    # 値下がり（下落）ランキング: SV+MEGA TOP10 / S&S TOP3（下落幅の大きい順）
    sv_losers = sorted([c for c in sv_mega if c["diff"] < 0], key=lambda x: x["diff"])[:10]
    ss_losers = sorted([c for c in ss if c["diff"] < 0], key=lambda x: x["diff"])[:3]

    # SV+MEGA全BOXの平均変化額・変化率＋値上がり/横ばい/値下がり件数
    sv_mega_all = [c for c in changes if c["category"] in ("sv", "mega") and c["week_ago"] > 0]
    if sv_mega_all:
        avg_diff = sum(c["diff"] for c in sv_mega_all) / len(sv_mega_all)
        avg_pct = sum(c["pct"] for c in sv_mega_all) / len(sv_mega_all)
    else:
        avg_diff = 0
        avg_pct = 0
    n_up = len([c for c in sv_mega_all if c["pct"] > 0])
    n_down = len([c for c in sv_mega_all if c["pct"] < 0])
    n_flat = len(sv_mega_all) - n_up - n_down

    # 今週の地合いを1文で言語化する。数字の羅列だけのページにしないための解説用
    if n_up >= n_down * 2 and avg_pct > 0.5:
        market_comment = (
            "値上がりした銘柄が値下がりの2倍以上あり、平均でもプラス圏です。"
            "相場全体に買いが戻っている局面で、売却を考えている方には追い風になります。"
        )
    elif n_down >= n_up * 2 and avg_pct < -0.5:
        market_comment = (
            "値下がりした銘柄が値上がりの2倍以上を占め、平均でもマイナス圏です。"
            "全体が調整局面にあるため、売り急ぐより下げ止まりを確認したい場面です。"
        )
    elif abs(avg_pct) <= 0.5:
        market_comment = (
            "平均変化率が±0.5%以内に収まっており、相場全体としては横ばいです。"
            "こうした膠着局面では、個別BOXごとの材料(再販・新弾・環境変化)が値動きを左右します。"
        )
    elif avg_pct > 0:
        market_comment = (
            "値上がりと値下がりが混在しつつ、平均ではプラス圏です。"
            "銘柄によって方向が分かれているため、保有BOXごとに個別ページで推移を確認するのが確実です。"
        )
    else:
        market_comment = (
            "値上がりと値下がりが混在しつつ、平均ではマイナス圏です。"
            "全面安ではないため、下げているBOXに固有の理由(再販・新弾の影響)がないか確認する価値があります。"
        )

    today_str = today_file.stem
    week_ago_str = week_ago_file.stem

    # 直近7日分の価格推移データ（グラフ用）
    recent_files = files[-8:] if len(files) >= 8 else files
    chart_dates = [f.stem for f in recent_files]

    # 日次データキャッシュ（何度も読まないように）
    daily_cache = []
    for f in recent_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        daily_cache.append({d["name"]: d.get("max_price", 0) for d in data})

    def _short_name(name: str) -> str:
        short = re.sub(r"^(MEGA|SV|S&S)\s*(拡張パック|強化拡張パック|ハイクラスパック|拡張パックDX)\s*", "", name)
        return re.sub(r"[「」]", "", short)

    chart_labels_js = json.dumps(chart_dates, ensure_ascii=False)

    # SV+MEGA全BOXの日次平均価格
    sv_mega_names = [p.name for p in products if p.category in ("sv", "mega")]
    daily_avgs = []
    for dc in daily_cache:
        prices = [dc.get(n, 0) for n in sv_mega_names if dc.get(n, 0) > 0]
        daily_avgs.append(round(sum(prices) / len(prices)) if prices else 0)
    avg_chart_data_js = json.dumps(daily_avgs)

    def _build_mini_charts(items: list, prefix: str, color: str) -> str:
        """各BOXごとの個別ミニグラフHTMLとJSを生成"""
        html_parts = []
        js_parts = []
        for i, item in enumerate(items):
            daily_prices = [dc.get(item["name"], 0) for dc in daily_cache]
            canvas_id = f"{prefix}Chart{i}"
            short = _short_name(item["name"])
            sign = "+" if item["diff"] > 0 else ""
            diff_color = "#dc2626" if item["diff"] > 0 else "#2563eb"
            arrow = "↑" if item["diff"] > 0 else "↓"
            html_parts.append(
                f'<div class="mini-chart-card">'
                f'<div class="mc-header">'
                f'<a href="box/{item["slug"]}.html" class="mc-name">{short}</a>'
                f'<span class="mc-price">¥{item["today"]:,}</span>'
                f'<span class="mc-diff" style="color:{diff_color}">{arrow}{sign}¥{item["diff"]:,} ({sign}{item["pct"]:.1f}%)</span>'
                f'</div>'
                f'<canvas id="{canvas_id}" height="120"></canvas>'
                f'</div>'
            )
            data_js = json.dumps(daily_prices)
            js_parts.append(f"""
new Chart(document.getElementById('{canvas_id}'), {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{ data: {data_js}, borderColor: '{color}', borderWidth: 2, fill: true,
      backgroundColor: '{color}22', tension: 0.3, pointRadius: 2 }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ font: {{ size: 10 }}, maxRotation: 0 }} }},
      y: {{ ticks: {{ callback: v => '¥' + v.toLocaleString(), font: {{ size: 10 }} }} }}
    }}
  }}
}});""")
        return "\n".join(html_parts), "\n".join(js_parts)

    sv_gain_html, sv_gain_js = _build_mini_charts(sv_gainers, "svUp", "#dc2626")
    ss_gain_html, ss_gain_js = _build_mini_charts(ss_gainers, "ssUp", "#f59e0b")
    sv_loss_html, sv_loss_js = _build_mini_charts(sv_losers, "svDown", "#2563eb")
    ss_loss_html, ss_loss_js = _build_mini_charts(ss_losers, "ssDown", "#2563eb")

    def _make_table(items: list) -> str:
        if not items:
            return '<p class="no-data">変動なし</p>'
        rows = []
        for i, c in enumerate(items, 1):
            sign = "+" if c["diff"] > 0 else ""
            color = "#dc2626" if c["diff"] > 0 else "#2563eb"
            arrow = "↑" if c["diff"] > 0 else "↓"
            rows.append(
                f'<tr>'
                f'<td class="rank">{i}</td>'
                f'<td class="pname"><a href="box/{c["slug"]}.html">{c["name"]}</a></td>'
                f'<td class="price">¥{c["today"]:,}</td>'
                f'<td style="color:{color};font-weight:700">{arrow} {sign}¥{c["diff"]:,} ({sign}{c["pct"]:.1f}%)</td>'
                f'</tr>'
            )
        return (
            '<table class="ranking-table">'
            '<tr><th>順位</th><th>商品名</th><th>現在価格</th><th>週間変動</th></tr>'
            + "\n".join(rows)
            + '</table>'
        )

    sv_gainers_table = _make_table(sv_gainers)
    ss_gainers_table = _make_table(ss_gainers)
    sv_losers_table = _make_table(sv_losers)
    ss_losers_table = _make_table(ss_losers)

    # JSON-LD 構造化データ (ItemList + BreadcrumbList + Article)
    ranking_products = []
    for c in sv_gainers + ss_gainers + sv_losers + ss_losers:
        ranking_products.append({
            "@type": "Product",
            "name": c["name"],
            "url": f"https://pokeca-box-hikaku.com/box/{c['slug']}.html",
            "image": "https://pokeca-box-hikaku.com/ogp.jpg",
            "brand": {"@type": "Brand", "name": "ポケモンカードゲーム"},
            "offers": {
                "@type": "Offer",
                "price": c["today"],
                "priceCurrency": "JPY",
                "availability": "https://schema.org/InStock",
            },
        })

    ranking_itemlist_obj = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "ポケカBOX 週間価格変化ランキング",
        "description": f"ポケモンカード未開封BOX 週間価格変化ランキング（値上がり・値下がり） ({week_ago_str} → {today_str})",
        "numberOfItems": len(ranking_products),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": item}
            for i, item in enumerate(ranking_products)
        ],
    }
    ranking_breadcrumb_obj = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": "週間価格変化ランキング", "item": "https://pokeca-box-hikaku.com/ranking.html"},
        ],
    }
    ranking_article_obj = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "ポケカBOX 週間価格変化ランキング",
        "description": "ポケモンカード未開封BOXの買取価格 週間価格変化ランキング。直近7日間で最も値上がり・値下がりしたBOXをグラフ付きで紹介。毎日自動更新。",
        "datePublished": today_str,
        "dateModified": today_str,
        "image": "https://pokeca-box-hikaku.com/ogp.jpg",
        "author": {"@type": "Organization", "name": "ポケカ買取チェッカー編集部"},
        "publisher": {
            "@type": "Organization",
            "name": "ポケカ買取チェッカー",
            "logo": {"@type": "ImageObject", "url": "https://pokeca-box-hikaku.com/ogp.png"},
        },
        "mainEntityOfPage": "https://pokeca-box-hikaku.com/ranking.html",
    }
    ranking_jsonld = (
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_itemlist_obj, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_breadcrumb_obj, ensure_ascii=False, indent=2)
        + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(ranking_article_obj, ensure_ascii=False, indent=2)
        + '\n</script>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<!-- Preconnect hints for Core Web Vitals -->
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="ポケカ未開封BOXの買取価格 週間価格変化ランキング。直近7日間で値上がり・値下がりしたBOXをグラフ付きで紹介(値上がりTOP・値下がりTOP)。毎日自動更新で現在の下落トレンドもひと目で分かる。">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/ranking.html">
<meta property="og:title" content="ポケカBOX 週間価格変化ランキング(値上がり・値下がり)｜ポケカ買取チェッカー">
<meta property="og:description" content="ポケカ未開封BOXの買取価格 週間価格変化ランキング。直近7日間の値上がり・値下がりTOPをグラフ付きで紹介。">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/ranking.html">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ポケカBOX 週間価格変化ランキング(値上がり・値下がり)">
<meta name="twitter:description" content="ポケカ未開封BOXの買取価格 週間価格変化ランキング。値上がり・値下がりTOPを毎日自動更新。">
<title>ポケカBOX 週間価格変化ランキング(値上がり・値下がり)｜ポケカ買取チェッカー</title>
{ranking_jsonld}
<!-- Google AdSense -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root{{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#6366f1}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}}
.header{{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}}
.header a{{text-decoration:none}}
.header h1{{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.wrap{{max-width:1240px;margin:0 auto;padding:32px 16px 48px}}
.content-layout{{display:flex;gap:24px;align-items:flex-start}}
.content-layout .main-card{{flex:1;min-width:0}}
.article-nav{{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}}
.article-nav-title{{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.article-nav a{{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4;transition:all .2s}}
.article-nav a:hover{{color:var(--accent);border-left-color:var(--accent)}}
.article-nav a.current{{color:var(--accent);border-left-color:var(--accent);font-weight:600}}
.article-nav-sub{{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}}
@media(max-width:1023px){{.content-layout{{display:block}}.article-nav{{display:none}}}}
.breadcrumb{{font-size:12px;color:var(--text-sub);margin-bottom:20px}}
.breadcrumb a{{color:var(--accent);text-decoration:none}}
.main-card{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}}

.main-card h2{{font-size:22px;font-weight:700;margin-bottom:8px}}
.meta{{font-size:12px;color:var(--text-sub);margin-bottom:24px}}
.section-title{{font-size:17px;font-weight:700;margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid var(--accent)}}
.section-title.up{{color:#dc2626}}
.section-title.down{{color:#2563eb}}
.chart-wrap{{margin:24px 0;background:#fff;border-radius:8px;padding:16px}}
.chart-wrap canvas{{max-height:320px}}
.ranking-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ranking-table th{{background:#f9fafb;padding:10px 12px;text-align:left;font-size:12px;color:var(--text-sub);border-bottom:2px solid var(--border)}}
.ranking-table td{{padding:10px 12px;border-bottom:1px solid var(--border)}}
.ranking-table .rank{{width:40px;text-align:center;font-weight:700;color:var(--accent)}}
.ranking-table .pname a{{color:var(--text);text-decoration:none}}
.ranking-table .pname a:hover{{color:var(--accent);text-decoration:underline}}
.ranking-table .price{{white-space:nowrap}}
.no-data{{color:var(--text-sub);font-size:14px}}
.mini-charts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:8px}}
.mini-chart-card{{background:#fff;border-radius:10px;border:1px solid var(--border);padding:14px 16px}}
.mc-header{{margin-bottom:8px}}
.mc-name{{font-size:14px;font-weight:700;color:var(--text);text-decoration:none;display:block}}
.mc-name:hover{{color:var(--accent)}}
.mc-price{{font-size:18px;font-weight:700;margin-right:8px}}
.mc-diff{{font-size:13px;font-weight:700}}
.avg-stats{{display:flex;gap:24px;flex-wrap:wrap}}
.avg-item{{background:#f9fafb;border-radius:8px;padding:12px 20px;flex:1;min-width:140px;text-align:center}}
.avg-label{{display:block;font-size:12px;color:var(--text-sub);margin-bottom:4px}}
.avg-value{{font-size:22px;font-weight:700}}
.cta{{display:block;text-align:center;padding:14px;background:linear-gradient(135deg,#6366f1,#818cf8);color:#fff;border-radius:10px;text-decoration:none;font-weight:600;margin-top:32px}}
.footer{{text-align:center;color:var(--text-sub);font-size:12px;margin-top:32px}}
@media(max-width:640px){{.ranking-table{{font-size:12px}}.ranking-table td,.ranking-table th{{padding:8px 6px}}.main-card{{padding:20px 16px}}}}
</style>
</head>
<body>
<div class="header"><a href="index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="index.html">トップ</a> &gt; 週間価格変化ランキング</div>

<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="index.html">買取価格比較</a>
<a href="weekly/">🔥 今週の値動き記事</a>
<a href="ranking.html" class="current">📊 週間価格変化ランキング</a>
<a href="souba-mynumber-2026.html">📰 相場下落・膠着とマイナンバー</a>
<a href="kaitori-tips.html">BOX買取のコツ</a>
<a href="shop-hikaku.html">9店舗比較</a>
<a href="single-card-tips.html">シングル売り</a>
<a href="psa-guide.html">PSA鑑定ガイド</a>
<a href="mercari-hikaku.html">メルカリ・スニダン比較</a>
<a href="shrink-nashi.html">シュリンクなしBOX</a>
<a href="box-toushi.html">BOX投資の始め方</a>
<a href="restock-guide.html">再販情報の見つけ方</a>
<a href="release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
<a href="price-pattern-guide.html">📈 相場5段階パターン</a>
<div class="article-nav-sub">🔥 BOX深掘り特集</div>
<a href="30th-celebration-atari-yosou.html">【予想】30th 当たりカード</a>
<a href="30th-celebration-forecast.html">【予想】30th CELEBRATION 3種</a>
<a href="151-spotlight.html">【特集】ポケモンカード151高騰</a>
<a href="inferno-x-spotlight.html">【特集】インフェルノX高騰</a>
<a href="kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>
<a href="chouden-breaker-spotlight.html">【特集】超電ブレイカー高騰</a>
<a href="clay-burst-spotlight.html">【特集】クレイバースト高騰</a>
<a href="ninja-spinner-spotlight.html">【特集】ニンジャスピナー高騰</a>
<a href="storm-emeralda-spotlight.html">【特集】ストームエメラルダ高騰と長期予想</a>
<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>
<a href="zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
<a href="lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
<a href="mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
<a href="kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
<a href="mega-lizardon-x-guide.html">メガリザードンXex MUR/SAR</a>
<a href="lizardon-sar-kokuen-guide.html">リザードンex SAR(黒炎)</a>
<a href="erika-sar-guide.html">エリカの招待 SAR</a>
<a href="pigeot-sar-guide.html">ピジョットex SAR</a>
<a href="masterball-mirror-guide.html">151マスターボールミラー</a>
<a href="kokuen-atari-guide.html">黒炎 当たりカード完全ガイド</a>
<a href="startdeck100-atari-guide.html">スタートデッキ100 当たり番号一覧</a>
<a href="startdeck100-miwakekata.html">スタートデッキ100 見分け方</a>
<a href="abyss-eye-atari-guide.html">アビスアイ 当たりカードランキング</a>
<a href="mega-ex-atari-guide.html">MEGAドリームex 当たりカード</a>
<a href="inferno-x-atari-guide.html">インフェルノX 当たりカード</a>
<a href="mega-brave-atari-guide.html">メガブレイブ 当たりカード</a>
<a href="chouden-breaker-atari-guide.html">超電ブレイカー 当たりカード</a>
<a href="clay-burst-atari-guide.html">クレイバースト 当たりカード</a>
<a href="ninja-spinner-atari-guide.html">ニンジャスピナー 当たりカード</a>
<a href="munikis-zero-atari-guide.html">ムニキスゼロ 当たりカード</a>
<a href="mega-sinfonia-atari-guide.html">メガシンフォニア 当たりカード</a>
<a href="black-bolt-atari-guide.html">ブラックボルト 当たりカード</a>
<a href="white-flare-atari-guide.html">ホワイトフレア 当たりカード</a>
<a href="rocket-dan-no-eiko-atari-guide.html">ロケット団の栄光 当たりカード</a>
<a href="eruption-walker-atari-guide.html">爆炎ウォーカー 当たりカード</a>
<a href="legendary-heartbeat-atari-guide.html">伝説の鼓動 当たりカード</a>
<a href="vmax-climax-atari-guide.html">VMAXクライマックス 当たりカード</a>
<a href="astonishing-voltecker-atari-guide.html">仰天のボルテッカー 当たりカード</a>
<a href="matchless-fighters-atari-guide.html">双璧のファイター 当たりカード</a>
<a href="lost-abyss-atari-guide.html">ロストアビス 当たりカード</a>
<a href="single-strike-master-atari-guide.html">一撃マスター 当たりカード</a>
<a href="rapid-strike-master-atari-guide.html">連撃マスター 当たりカード</a>
<a href="infinity-zone-atari-guide.html">ムゲンゾーン 当たりカード</a>
<a href="rebellion-crash-atari-guide.html">反逆クラッシュ 当たりカード</a>
<a href="fusion-arts-atari-guide.html">フュージョンアーツ 当たりカード</a>
<a href="vmax-rising-atari-guide.html">VMAXライジング 当たりカード</a>
<a href="blue-sky-stream-atari-guide.html">蒼空ストリーム 当たりカード</a>
<a href="eevee-heroes-atari-guide.html">イーブイヒーローズ 当たりカード</a>
<a href="terastal-fes-ex-atari-guide.html">テラスタルフェスex 当たりカード</a>
<a href="shiny-treasure-ex-atari-guide.html">シャイニートレジャーex 当たりカード</a>
<a href="151-atari-guide.html">ポケモンカード151 当たりカード</a>
<a href="crimson-haze-atari-guide.html">クリムゾンヘイズ 当たりカード</a>
<a href="hengen-no-kamen-atari-guide.html">変幻の仮面 当たりカード</a>
<a href="rakuen-dragona-atari-guide.html">楽園ドラゴーナ 当たりカード</a>
<a href="night-wanderer-atari-guide.html">ナイトワンダラー 当たりカード</a>
<a href="raging-surf-atari-guide.html">レイジングサーフ 当たりカード</a>
<a href="scarlet-ex-atari-guide.html">スカーレットex 当たりカード</a>
<a href="future-flash-atari-guide.html">未来の一閃 当たりカード</a>
<a href="stellar-miracle-atari-guide.html">ステラミラクル 当たりカード</a>
<a href="ancient-roar-atari-guide.html">古代の咆哮 当たりカード</a>
<a href="wild-force-atari-guide.html">ワイルドフォース 当たりカード</a>
<a href="triplet-beat-atari-guide.html">トリプレットビート 当たりカード</a>
<a href="cyber-judge-atari-guide.html">サイバージャッジ 当たりカード</a>
<a href="snow-hazard-atari-guide.html">スノーハザード 当たりカード</a>
<a href="neppuu-arena-atari-guide.html">熱風のアリーナ 当たりカード</a>
<a href="battle-partners-atari-guide.html">バトルパートナーズ 当たりカード</a>
</nav>

<div class="main-card">
<h2>ポケカBOX 週間価格変化ランキング</h2>
<div class="meta">更新: {update_date}　比較期間: {week_ago_str} → {today_str}（直近7日間）</div>

<p style="font-size:14px;margin-bottom:8px">直近7日間でSV・MEGA全{len(sv_mega_all)}BOX中、<strong style="color:#dc2626">値上がり {n_up}件</strong> / <strong style="color:var(--text-sub)">横ばい {n_flat}件</strong> / <strong style="color:#2563eb">値下がり {n_down}件</strong>。値上がり・値下がりの両方をランキング形式で掲載し、現在の相場トレンドをひと目で確認できます。</p>

<h3 class="section-title up">📈 SV・MEGA 値上がり TOP10</h3>
<div class="mini-charts">{sv_gain_html or '<p class="no-data">今週は値上がりしたSV・MEGA BOXはありません</p>'}</div>

<h3 class="section-title up" style="margin-top:48px">📈 S&amp;S 値上がり TOP3</h3>
<div class="mini-charts">{ss_gain_html or '<p class="no-data">今週は値上がりしたS&amp;S BOXはありません</p>'}</div>

<h3 class="section-title down" style="margin-top:48px">📉 SV・MEGA 値下がり TOP10</h3>
<div class="mini-charts">{sv_loss_html or '<p class="no-data">今週は値下がりしたSV・MEGA BOXはありません</p>'}</div>

<h3 class="section-title down" style="margin-top:48px">📉 S&amp;S 値下がり TOP3</h3>
<div class="mini-charts">{ss_loss_html or '<p class="no-data">今週は値下がりしたS&amp;S BOXはありません</p>'}</div>

<h3 class="section-title" style="margin-top:48px">SV・MEGA 全BOX平均</h3>
<div class="avg-stats">
<div class="avg-item"><span class="avg-label">平均上昇額</span><span class="avg-value" style="color:{'#dc2626' if avg_diff >= 0 else '#2563eb'}">{"+" if avg_diff >= 0 else ""}¥{avg_diff:,.0f}</span></div>
<div class="avg-item"><span class="avg-label">平均上昇率</span><span class="avg-value" style="color:{'#dc2626' if avg_pct >= 0 else '#2563eb'}">{"+" if avg_pct >= 0 else ""}{avg_pct:.1f}%</span></div>
</div>
<div class="chart-wrap" style="margin-top:16px">
<canvas id="avgChart" height="200"></canvas>
</div>

<h3 class="section-title" style="margin-top:48px">今週の相場をどう読むか</h3>
<p>直近7日間({week_ago_str} → {today_str})の集計では、SV・MEGAの{len(sv_mega_all)}BOX中<strong>値上がり{n_up}件・横ばい{n_flat}件・値下がり{n_down}件</strong>、平均変化率は<strong>{avg_pct:+.1f}%</strong>({'+' if avg_diff >= 0 else ''}¥{avg_diff:,.0f})でした。{market_comment}</p>
<p>ただし<strong>1週間の変動だけで判断するのは危険</strong>です。ポケカのBOX相場は数ヶ月単位の大きな波の中で日々上下しており、週次の増減はその一部を切り取ったものにすぎません。長期の位置づけは<a href="price-pattern-guide.html">BOX買取価格の5段階パターン</a>(発売前プレ値→初動高値→調整期→底打ち→絶版急騰)と併せて確認してください。</p>

<h3 class="section-title" style="margin-top:32px">BOX買取価格が動く5つの要因</h3>
<p>ランキングの順位そのものより、<strong>なぜ動いたのか</strong>を押さえておくと次の値動きが読めるようになります。買取価格が変動する主な要因は次の5つです。</p>
<ol style="font-size:14px;line-height:1.9;padding-left:22px">
<li><strong>新弾の発売</strong> — 新しいパックが出ると資金と注目がそちらへ移り、既存弾は一時的に下がりやすくなります。発売日前後は特に顕著です。</li>
<li><strong>再販・増産</strong> — 供給が増えると買取店は仕入れ値を下げます。人気弾ほど再販が組まれやすく、品薄が解消した瞬間に相場が緩みます。<a href="restock-guide.html">再販情報の見つけ方</a>で入荷状況を追えます。</li>
<li><strong>対戦環境の変化</strong> — レギュレーション変更や新デッキの流行で、収録カードの実需が増減します。環境トップに立ったカードを含む弾は上がりやすくなります。</li>
<li><strong>絶版化</strong> — 生産が終了すると供給は一方通行で細っていきます。当サイトが追跡する発売5年以上のBOX21商品のうち、定価割れしているものは1つもありません。</li>
<li><strong>目玉カードの単品相場</strong> — BOX相場は看板カードの価格に従属します。高額SARが下げればBOXも連動します。弾ごとの看板は<a href="sv-box-list.html">SV全BOX一覧</a>や各当たりカードガイドで確認できます。</li>
</ol>

<h3 class="section-title" style="margin-top:32px">このランキングの使い方</h3>
<ul style="font-size:14px;line-height:1.9;padding-left:22px">
<li><strong>売りたい人</strong> — 値上がりランキング上位に自分の保有BOXがあれば、勢いが続いているうちに複数店を比較して売る判断材料になります。手順は<a href="kaitori-tips.html">BOX買取のコツ</a>にまとめています。</li>
<li><strong>買いたい人</strong> — 値下がりランキングは仕込みの候補リストです。ただし下落の理由が「再販」なのか「人気の低下」なのかで、その後の戻り方がまったく違います。</li>
<li><strong>持ち続ける人</strong> — 週次の上下に一喜一憂せず、個別ページの全期間グラフで大きな流れを見てください。各BOXページには9店舗の最新価格と価格推移グラフを掲載しています。</li>
</ul>

<p style="font-size:13px;color:#6b7280;margin-top:20px">※ 本ランキングは当サイトが毎日3回自動収集している9店舗の買取価格をもとに、7日前との差分を機械的に算出したものです。掲載価格はシュリンクの有無や外箱の状態によって実際の買取額と異なる場合があります。投資助言を目的とするものではありません。</p>

<a href="index.html" class="cta">全66商品の買取価格を比較する &rarr;</a>

<div class="ad" style="margin-top:32px;text-align:center">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad" style="margin-top:16px;text-align:center">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
</div>
</div>

<div class="footer">&copy; ポケカ買取チェッカー</div>
</div>
<script>
{sv_gain_js}
{ss_gain_js}
{sv_loss_js}
{ss_loss_js}
new Chart(document.getElementById('avgChart'), {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{
      label: 'SV・MEGA 平均買取価格',
      data: {avg_chart_data_js},
      borderColor: '#6366f1',
      backgroundColor: '#6366f122',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
      pointRadius: 3
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: true, position: 'bottom' }} }},
    scales: {{
      y: {{ ticks: {{ callback: v => '¥' + v.toLocaleString() }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    out_path = project_root / "ranking.html"
    out_path.write_text(html, encoding="utf-8")
    logger.info("Generated ranking page: %s", out_path)


def generate_weekly_article(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate /weekly/YYYY-wWW.html and /weekly/index.html archive.

    The file for the current ISO week is overwritten on each cron run
    with the latest data. Past weeks' files are left untouched and serve
    as permanent archives.
    """
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        logger.info("No history dir; skipping weekly article")
        return

    files = sorted(history_dir.glob("*.json"))
    if len(files) < 8:
        logger.info("Insufficient history for weekly article (need >= 8 days)")
        return

    # Import the template module lazily to keep top-level lean
    import sys
    sys.path.insert(0, str(project_root))
    from scripts.weekly_article_template import build_weekly_html, build_weekly_index_html

    # Today = latest snapshot, week ago = 7 days before
    today_file = files[-1]
    week_ago_idx = max(0, len(files) - 8)
    week_ago_file = files[week_ago_idx]

    today_data = json.loads(today_file.read_text(encoding="utf-8"))
    week_ago_data = json.loads(week_ago_file.read_text(encoding="utf-8"))

    today_prices = {item["name"]: item.get("max_price", 0) for item in today_data}
    week_ago_prices = {item["name"]: item.get("max_price", 0) for item in week_ago_data}

    # Build changes list
    slug_map = {p.name: _generate_slug(p.name) for p in products}
    cat_map = {p.name: p.category for p in products}

    all_changes = []
    for p in products:
        tp = today_prices.get(p.name, 0)
        wp = week_ago_prices.get(p.name, 0)
        if tp <= 0 or wp <= 0:
            continue
        diff = tp - wp
        pct = (diff / wp) * 100 if wp > 0 else 0
        all_changes.append({
            "name": p.name,
            "slug": slug_map.get(p.name, ""),
            "category": cat_map.get(p.name, ""),
            "today": tp,
            "week_ago": wp,
            "diff": diff,
            "pct": pct,
        })

    # Split by category: SV+MEGA main ranking (TOP10), S&S secondary (TOP3)
    sv_mega_changes = [c for c in all_changes if c["category"] in ("sv", "mega")]
    ss_changes = [c for c in all_changes if c["category"] == "ss"]

    sv_mega_gainers = sorted([c for c in sv_mega_changes if c["diff"] > 0],
                             key=lambda x: x["diff"], reverse=True)
    ss_gainers = sorted([c for c in ss_changes if c["diff"] > 0],
                        key=lambda x: x["diff"], reverse=True)
    # 値下がり（下落幅の大きい順）
    sv_mega_losers = sorted([c for c in sv_mega_changes if c["diff"] < 0],
                            key=lambda x: x["diff"])
    ss_losers = sorted([c for c in ss_changes if c["diff"] < 0],
                       key=lambda x: x["diff"])

    top_gainers = sv_mega_gainers[:10]       # main TOP10 (SV+MEGA)
    minor_gainers = sv_mega_gainers[10:15]   # next 5 (SV+MEGA)
    ss_top_gainers = ss_gainers[:3]          # S&S TOP3 secondary section
    top_losers = sv_mega_losers[:10]         # 値下がり TOP10 (SV+MEGA)
    ss_top_losers = ss_losers[:3]            # S&S 値下がり TOP3

    if not top_gainers and not top_losers:
        logger.info("No SV+MEGA price changes this week; skipping weekly article")
        return

    # Build per-BOX 7-day price history for mini charts
    recent_files = files[-8:]  # last 8 days (including today)
    chart_dates = [f.stem for f in recent_files]
    daily_cache: list[dict[str, int]] = []
    for f in recent_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        daily_cache.append({d["name"]: d.get("max_price", 0) for d in data})

    chart_history: dict[str, list[int]] = {}
    for c in top_gainers + ss_top_gainers + top_losers + ss_top_losers:
        series = [dc.get(c["name"], 0) for dc in daily_cache]
        chart_history[c["slug"]] = series

    # Determine ISO week from today_file filename (YYYY-MM-DD.json)
    today_str = today_file.stem
    week_ago_str = week_ago_file.stem
    today_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
    iso_year, iso_week, _ = today_dt.isocalendar()

    weekly_dir = project_root / "weekly"
    weekly_dir.mkdir(exist_ok=True)

    # Only publish weekly article on Sunday (Python weekday=6).
    # On other days, keep the existing file untouched and only regenerate the
    # archive index below.
    if today_dt.weekday() == 6:
        out_path = weekly_dir / f"{iso_year}-w{iso_week:02d}.html"
        html = build_weekly_html(
            year=iso_year,
            week_no=iso_week,
            today_str=today_str,
            week_ago_str=week_ago_str,
            update_date=update_date,
            top_gainers=top_gainers,
            minor_gainers=minor_gainers,
            ss_top_gainers=ss_top_gainers,
            all_changes=sv_mega_changes,  # stats use SV+MEGA only (main set)
            chart_dates=chart_dates,
            chart_history=chart_history,
            top_losers=top_losers,
            ss_top_losers=ss_top_losers,
        )
        out_path.write_text(html, encoding="utf-8")
        logger.info("Generated weekly article: %s (%d gainers, %d losers)",
                    out_path, len(top_gainers), len(top_losers))
    else:
        logger.info(
            "Weekly article publish is Sunday-only; today=%s (weekday=%d), skipping write",
            today_dt, today_dt.weekday()
        )

    # Build archive index from all existing weekly files
    all_weekly_files = sorted(weekly_dir.glob("*.html"), reverse=True)
    week_entries = []
    for wf in all_weekly_files:
        if wf.name == "index.html":
            continue
        # Parse filename: 2026-w15.html
        m = re.match(r"(\d{4})-w(\d{2})\.html", wf.name)
        if not m:
            continue
        y, w = int(m.group(1)), int(m.group(2))

        # Extract published date and top gainer from the file if possible
        try:
            content = wf.read_text(encoding="utf-8")
            date_m = re.search(r"公開日:\s*(\d{4}-\d{2}-\d{2})", content)
            published_date = date_m.group(1) if date_m else f"{y}年第{w}週"
            # First BOX name in the ranking table (th after "順位")
            top_m = re.search(
                r'<td class="rank">1</td>\s*<td class="pname"><a[^>]*>([^<]+)</a>',
                content,
            )
            top_gainer_name = top_m.group(1) if top_m else "データなし"
        except Exception:
            published_date = f"{y}年第{w}週"
            top_gainer_name = "データなし"

        week_entries.append({
            "year": y,
            "week": w,
            "filename": wf.name,
            "title": f"{y}年 第{w}週 価格変化ランキング",
            "published_date": published_date,
            "top_gainer_name": top_gainer_name,
        })

    # Write archive index
    index_path = weekly_dir / "index.html"
    index_path.write_text(build_weekly_index_html(week_entries), encoding="utf-8")
    logger.info("Generated weekly index: %s (%d entries)", index_path, len(week_entries))


CATEGORY_PAGE_CONFIG = [
    {
        "cat_id": "sv",
        "filename": "sv-box-list.html",
        "title": "SV(スカーレット&バイオレット) 全BOX 買取価格一覧",
        "short": "SVシリーズ",
        "desc_meta": "SV(スカーレット&バイオレット)シリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗の実データで一覧化。151/黒炎の支配者/超電ブレイカー/ロケット団の栄光など全商品の相場を毎日自動更新。",
        "lead": (
            "SV(スカーレット&バイオレット)シリーズは2023年1月の「スカーレットex/バイオレットex」を起点に、"
            "レギュレーションマークG/H/I/Jで展開された現行ポケカのメインシリーズです。"
            "151・黒炎の支配者・超電ブレイカー・ロケット団の栄光など高騰BOXが多数含まれ、"
            "スタン落ち観測のタイミングで相場が動きやすいのが特徴。"
            "本ページではSVシリーズ全BOXの買取価格・発売日・定価倍率を一覧化し、相場動向を毎日自動更新しています。"
        ),
        "narrative": [
            ("レギュレーションと相場連動", (
                "SVシリーズはレギュレーションマークG/H/I/Jで展開され、最古のGレギュは2026年1月にスタンダード落ちしました。"
                "Gレギュ落ちのタイミングで「151」「黒炎の支配者」「クレイバースト」など主力BOXが軒並み再上昇しており、"
                "今後はH→I→Jの順に段階的なスタン落ちが続くため、レギュ別の在庫動向と相場が連動しやすい構造です。"
            )),
            ("看板SARの相場が直接BOX相場を動かす構造", (
                "SVシリーズはSAR(スペシャルアートレア)の高騰がBOX相場を牽引する典型例です。"
                "リザードンex SAR(黒炎)/エリカの招待SAR(151)/ピカチュウex SAR(超電ブレイカー)/ナンジャモSAR(クレイバースト)/ミュウツーex SAR(ロケット団の栄光)など、"
                "高額SARを擁するBOXが順番に高騰しており、SAR単体相場のチェックがBOX投資判断に直結します。"
            )),
            ("180円→200円の値上げが分水嶺", (
                "2026年5月発売のアビスアイから1パック200円に値上げされる予定で、180円定価の最後のSV弾(ロケット団の栄光・熱風のアリーナ周辺)は"
                "「最後の旧定価BOX」としてのコレクション価値が意識されています。"
                "値上げ後初期は相場形成が読みづらいため、180円定価BOXの希少性が再評価される流れも見込まれます。"
            )),
        ],
    },
    {
        "cat_id": "mega",
        "filename": "mega-box-list.html",
        "title": "MEGA(メガシンカ) 全BOX 買取価格一覧",
        "short": "MEGAシリーズ",
        "desc_meta": "MEGAシリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗の実データで一覧化。メガブレイブ/メガシンフォニア/インフェルノX/ニンジャスピナー/ムニキスゼロ/メガドリームexの相場を毎日自動更新。",
        "lead": (
            "MEGA(メガシンカ)シリーズは2025年春の「メガブレイブ/メガシンフォニア」から始まった新シリーズで、"
            "メガ進化ポケモンを主軸にしたBOX群です。"
            "メガリザードンXexが収録されたインフェルノXが定価の5倍超に高騰するなど、"
            "各弾の看板メガ進化ポケモンex の相場牽引力が極めて強いシリーズです。"
            "本ページではMEGAシリーズ全BOXの買取価格・発売日・定価倍率を一覧化しています。"
        ),
        "narrative": [
            ("メガ進化人気とSAR/MUR封入率", (
                "MEGAシリーズは1弾につき主役メガ進化ポケモンexのMUR(ミュウツー級)とSAR(美麗版)が同時収録される構成です。"
                "MUR封入率は約45BOXに1枚と稀少で、引き当てれば10万円超もある単発高額カードのため、BOX期待値が他シリーズより跳ね上がりやすい特徴があります。"
            )),
            ("発売直後の高値→数ヶ月底値→絶版観測で再上昇", (
                "MEGAシリーズBOXの典型的な相場パターンは「発売初動2〜3倍 → 再販で底値¥7,000〜¥9,000台 → 在庫薄観測で再上昇」です。"
                "メガブレイブ/メガシンフォニア/メガドリームexは底値圏から¥10,000台に戻し、インフェルノXは¥27,000超まで上昇しています。"
                "底値で仕込めば数倍リターンの可能性があり、メガ進化人気の継続性を見極めるシリーズです。"
            )),
            ("値上げ後初パック「アビスアイ」が転換点", (
                "2026年5月22日発売のアビスアイ(M5)が値上げ後初のメガ弾。1BOX定価は¥6,000(税込)に上がります。"
                "メガダークライexを軸にした新基準BOXとして、相場が¥9,600(弱気)〜¥30,000(強気)で形成されると予想されます。"
                "詳細は別記事「アビスアイ発売前予想」で解説しています。"
            )),
        ],
    },
    {
        "cat_id": "ss",
        "filename": "ss-box-list.html",
        "title": "S&S(ソード&シールド) 全BOX 買取価格一覧",
        "short": "S&Sシリーズ",
        "desc_meta": "S&S(ソード&シールド)シリーズ全BOXの買取価格・定価・発売日・相場トレンドを9店舗の実データで一覧化。イーブイヒーローズ/VMAXクライマックス/25thアニバーサリー/蒼空ストリームなど絶版BOX中心。毎日自動更新。",
        "lead": (
            "S&S(ソード&シールド)シリーズは2019年12月の「ソード/シールド」から2022年12月の「VSTARユニバース」まで約3年間展開された旧世代シリーズで、"
            "Gレギュ以降はスタン落ち済み。そのためほぼ全BOXが生産終了(絶版)状態にあり、中長期投資対象として根強い需要があります。"
            "特にイーブイヒーローズ(¥150,000超)・VMAXクライマックス・蒼空ストリームなどは5桁〜6桁の高値相場。"
            "本ページではS&Sシリーズ全BOXの買取価格・発売日・定価倍率を一覧化しています。"
        ),
        "narrative": [
            ("Gレギュ落ち以降は実質全BOX絶版", (
                "S&SシリーズはレギュレーションマークA/B/C/D/E/Fで構成され、2023年〜2026年1月にかけて段階的にスタンダード落ちが完了しました。"
                "公式の生産は既に終了しており、市場流通は中古/未開封の在庫のみ。"
                "在庫が枯れるほど相場が上昇する『絶版プレミア相場』の典型シリーズで、BOX買取は需給バランスのみで決まります。"
            )),
            ("VMAX/VSTAR 看板カードが相場を支える", (
                "S&Sシリーズの目玉はVMAX(全身イラストの大型レア)とVSTAR(技付き全身イラスト)です。"
                "イーブイヒーローズのイーブイズセットVMAX HRやVMAXクライマックスのリザードンVMAX HR、"
                "蒼空ストリームのレックウザVMAX HRなど、5万円超のVMAX HR収録BOXは10万円台で安定します。"
            )),
            ("過去の暴落と再上昇のサイクル", (
                "S&Sシリーズも2024年バブル崩壊で一時的に大幅下落しましたが、その後の絶版進行で再び上昇基調に転じています。"
                "2026年に入り、イーブイヒーローズは¥150,000超、VMAXライジング・パラダイムトリガーも上昇トレンド入り。"
                "新弾発売(SV/MEGA)のたびに相場の物差しがずれるため、タイミングを見ての分散売却が無難な投資戦略です。"
            )),
        ],
    },
]


def _build_category_crosslinks(current_cat_id: str) -> str:
    """Build cross-reference links to the other 2 category pages."""
    parts = []
    for c in CATEGORY_PAGE_CONFIG:
        if c["cat_id"] == current_cat_id:
            continue
        parts.append(f'<a href="{c["filename"]}">📋 {c["short"]} 全BOX一覧</a>')
    # Also link to weekly ranking and home
    parts.append('<a href="weekly/">🔥 今週の値動きランキング</a>')
    parts.append('<a href="ranking.html">📊 週間価格変化ランキング</a>')
    return "\n".join(parts)


def _category_summary_stats(
    items: list[dict],
) -> dict:
    """Compute aggregate stats for a category page."""
    with_price = [x for x in items if x["max_price"] > 0]
    if not with_price:
        return {}
    total = len(with_price)
    avg_price = sum(x["max_price"] for x in with_price) // total
    top = max(with_price, key=lambda x: x["max_price"])
    low = min(with_price, key=lambda x: x["max_price"])
    premium_count = len([x for x in with_price if x["retail_price"] > 0 and x["max_price"] > x["retail_price"]])
    return {
        "total": total,
        "avg_price": avg_price,
        "top_name": top["name"],
        "top_price": top["max_price"],
        "top_slug": top["slug"],
        "low_name": low["name"],
        "low_price": low["max_price"],
        "premium_count": premium_count,
    }


def _build_category_page_html(
    config: dict,
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> str:
    """Build a category summary page (SV/MEGA/S&S)."""
    cat_id = config["cat_id"]
    category_products = [p for p in products if p.category == cat_id]

    # Pre-load history snapshots for 7d/30d comparison
    history_dir = project_root / "data" / "history"
    hist_files = sorted(history_dir.glob("*.json")) if history_dir.exists() else []
    price_7d_ago: dict[str, int] = {}
    price_30d_ago: dict[str, int] = {}
    if len(hist_files) >= 8:
        try:
            data = json.loads(hist_files[-8].read_text(encoding="utf-8"))
            price_7d_ago = {x["name"]: x.get("max_price", 0) for x in data}
        except (json.JSONDecodeError, OSError):
            pass
    if len(hist_files) >= 31:
        try:
            data = json.loads(hist_files[-31].read_text(encoding="utf-8"))
            price_30d_ago = {x["name"]: x.get("max_price", 0) for x in data}
        except (json.JSONDecodeError, OSError):
            pass

    # Build item rows with pricing + trend
    items: list[dict] = []
    for p in category_products:
        active = {sid: p.prices.get(sid, 0) for sid in SHOP_IDS if p.prices.get(sid, 0) > 0}
        if not active:
            continue
        max_price = max(active.values())
        max_shop_id = max(active, key=active.get)
        slug = _generate_slug(p.name)
        ratio = (max_price / p.retail_price) if p.retail_price > 0 else 0
        p7 = price_7d_ago.get(p.name, 0)
        p30 = price_30d_ago.get(p.name, 0)
        diff_7d = max_price - p7 if p7 > 0 else 0
        pct_7d = (diff_7d / p7 * 100) if p7 > 0 else 0
        diff_30d = max_price - p30 if p30 > 0 else 0
        pct_30d = (diff_30d / p30 * 100) if p30 > 0 else 0
        items.append({
            "name": p.name,
            "slug": slug,
            "release_date": p.release_date or "",
            "retail_price": p.retail_price,
            "max_price": max_price,
            "max_shop": SHOP_NAMES.get(max_shop_id, max_shop_id),
            "ratio": ratio,
            "shop_count": len(active),
            "p7": p7,
            "p30": p30,
            "diff_7d": diff_7d,
            "pct_7d": pct_7d,
            "diff_30d": diff_30d,
            "pct_30d": pct_30d,
        })
    # Sort by release_date desc (newest first); empty dates last
    items.sort(key=lambda x: x["release_date"], reverse=True)

    stats = _category_summary_stats(items)

    # Build ranking table rows
    rows_html = []
    for x in items:
        ratio_text = f"{x['ratio']:.1f}倍" if x["ratio"] > 0 else "-"
        retail_text = f"¥{x['retail_price']:,}" if x["retail_price"] > 0 else "-"
        rows_html.append(
            f'<tr>'
            f'<td class="bx-name"><a href="box/{x["slug"]}.html">{x["name"]}</a></td>'
            f'<td class="bx-date">{x["release_date"] or "-"}</td>'
            f'<td class="bx-retail">{retail_text}</td>'
            f'<td class="bx-max">¥{x["max_price"]:,}</td>'
            f'<td class="bx-ratio">{ratio_text}</td>'
            f'<td class="bx-shop">{x["shop_count"]}店</td>'
            f'</tr>'
        )
    table_html = (
        '<table class="cat-table"><thead><tr>'
        '<th>商品名</th><th>発売日</th><th>定価</th><th>最高買取</th><th>倍率</th><th>掲載</th>'
        '</tr></thead><tbody>\n' + "\n".join(rows_html) + '\n</tbody></table>'
    )

    # Ranking 3 types: 定価倍率TOP5 / 7日上昇率TOP5 / 30日上昇率TOP5
    def _mini_rank_table(title: str, sub: str, rows: list[dict], value_key: str, value_fmt) -> str:
        if not rows:
            return ""
        lines = [
            f'<div class="rank-card"><div class="rk-title">{title}</div>'
            f'<div class="rk-sub">{sub}</div>'
            '<ol class="rk-list">'
        ]
        for i, r in enumerate(rows, 1):
            value = value_fmt(r[value_key], r)
            lines.append(
                f'<li><span class="rk-num">#{i}</span>'
                f'<a href="box/{r["slug"]}.html" class="rk-name">{r["name"]}</a>'
                f'<span class="rk-val">{value}</span></li>'
            )
        lines.append('</ol></div>')
        return "".join(lines)

    ratio_top = sorted([x for x in items if x["ratio"] > 0], key=lambda x: x["ratio"], reverse=True)[:5]
    pct7_top = sorted([x for x in items if x["pct_7d"] > 0], key=lambda x: x["pct_7d"], reverse=True)[:5]
    pct30_top = sorted([x for x in items if x["pct_30d"] > 0], key=lambda x: x["pct_30d"], reverse=True)[:5]

    rank_html = (
        '<div class="rank-grid">'
        + _mini_rank_table(
            "💰 定価倍率TOP5", "現在の最高買取÷定価で算出",
            ratio_top, "ratio", lambda v, r: f"{v:.1f}倍 (¥{r['max_price']:,})",
        )
        + _mini_rank_table(
            "📈 7日上昇率TOP5", "直近1週間の最高買取上昇率",
            pct7_top, "pct_7d", lambda v, r: f"+{v:.1f}% (+¥{r['diff_7d']:,})",
        )
        + _mini_rank_table(
            "🚀 30日上昇率TOP5", "直近1ヶ月の最高買取上昇率",
            pct30_top, "pct_30d", lambda v, r: f"+{v:.1f}% (+¥{r['diff_30d']:,})",
        )
        + '</div>'
    )

    # Timeline: 年次別グルーピング(発売日昇順)
    timeline_groups: dict[str, list[dict]] = {}
    for x in items:
        if not x["release_date"]:
            continue
        year = x["release_date"][:4]
        timeline_groups.setdefault(year, []).append(x)
    timeline_html = ""
    if timeline_groups:
        parts = ['<div class="timeline">']
        for year in sorted(timeline_groups.keys()):
            entries = sorted(timeline_groups[year], key=lambda x: x["release_date"])
            parts.append(f'<div class="tl-year"><div class="tl-year-label">{year}年</div><ul class="tl-list">')
            for x in entries:
                ratio_t = f"{x['ratio']:.1f}倍" if x["ratio"] > 0 else "-"
                parts.append(
                    f'<li><span class="tl-date">{x["release_date"][5:]}</span>'
                    f'<a href="box/{x["slug"]}.html" class="tl-name">{x["name"]}</a>'
                    f'<span class="tl-price">¥{x["max_price"]:,} ({ratio_t})</span></li>'
                )
            parts.append('</ul></div>')
        parts.append('</div>')
        timeline_html = "".join(parts)

    # Series narrative blocks
    narrative_html = ""
    if config.get("narrative"):
        nb = ['<div class="series-narrative">']
        for h, p in config["narrative"]:
            nb.append(f'<h3>{h}</h3><p>{p}</p>')
        nb.append('</div>')
        narrative_html = "".join(nb)

    # Summary box
    summary_html = ""
    if stats:
        summary_html = (
            '<div class="cat-summary"><div class="cs-row">'
            f'<div class="cs-cell"><div class="cs-label">掲載BOX</div><div class="cs-value">{stats["total"]}商品</div></div>'
            f'<div class="cs-cell"><div class="cs-label">平均最高買取</div><div class="cs-value">¥{stats["avg_price"]:,}</div></div>'
            f'<div class="cs-cell"><div class="cs-label">定価超え</div><div class="cs-value">{stats["premium_count"]}商品</div></div>'
            '</div>'
            f'<div class="cs-top">🏆 TOP: <a href="box/{stats["top_slug"]}.html">{stats["top_name"]}</a> ¥{stats["top_price"]:,}</div>'
            '</div>'
        )

    # FAQ (拡充: シリーズ別の特徴・データ・投資視点を含む7-8問)
    faq_items_base = [
        {
            "q": f"{config['short']}には何種類のBOXがありますか？",
            "a": f"当サイトで追跡中の{config['short']}は全{stats.get('total', len(items))}商品です(買取価格掲載ベース)。未開封BOX・拡張パック・ハイクラスパック・強化拡張パックなどを含みます。",
        },
        {
            "q": f"{config['short']}で現在最も高価なBOXは？",
            "a": f"{update_date}時点で最も高い買取価格が付いているのは「{stats.get('top_name', '-')}」で¥{stats.get('top_price', 0):,}です。" if stats else "",
        },
        {
            "q": f"{config['short']}の定価より高く売れるBOXは何商品ありますか？",
            "a": f"{stats.get('premium_count', 0)}商品が定価を上回る買取価格を付けています(全{stats.get('total', 0)}商品中)。" if stats else "",
        },
    ]
    if ratio_top:
        top_ratio = ratio_top[0]
        faq_items_base.append({
            "q": f"{config['short']}で定価倍率が最も高いBOXは？",
            "a": f"定価倍率TOP1は「{top_ratio['name']}」で約{top_ratio['ratio']:.1f}倍(現在最高買取¥{top_ratio['max_price']:,}/定価¥{top_ratio['retail_price']:,})です。",
        })
    if pct7_top:
        top_p7 = pct7_top[0]
        faq_items_base.append({
            "q": f"{config['short']}で直近1週間に最も上昇したBOXは？",
            "a": f"7日上昇率TOP1は「{top_p7['name']}」で+{top_p7['pct_7d']:.1f}% (+¥{top_p7['diff_7d']:,})です。短期の急騰は調整を伴いやすいので、追随購入は押し目を待つのが無難です。",
        })
    # シリーズ固有のFAQ
    if cat_id == "sv":
        faq_items_base.extend([
            {
                "q": "SVシリーズのスタン落ちはいつですか？",
                "a": "SVシリーズはレギュレーションマークG/H/I/Jで構成され、Gレギュは2026年1月にスタンダード落ちが完了しました。今後はH→I→Jの順に毎年スタン落ちが進むため、Gレギュ落ち後のBOX相場推移は他レギュの参考データになります。",
            },
            {
                "q": "SVシリーズで投資対象として注目すべきBOXは？",
                "a": "高騰実績がある151・黒炎の支配者・クレイバースト・超電ブレイカーは既に高値圏。投資視点では(1)定価倍率がまだ低めで看板SARが強いBOX、(2)スタン落ち1年前後のBOX、(3)180円定価最後の弾(ロケット団の栄光・熱風のアリーナ周辺)が注目候補です。",
            },
        ])
    elif cat_id == "mega":
        faq_items_base.extend([
            {
                "q": "MEGAシリーズのMUR封入率はどれくらいですか？",
                "a": "MEGAシリーズの主役メガ進化ポケモンexのMUR(ミュウツー級)封入率は、メディア予想で約45BOXに1枚(約2.19%)とされています。MUR単体相場は10万円超もあり、引き当てれば1BOXで定価の20倍以上の回収が可能な「夢のある」シリーズです。",
            },
            {
                "q": "MEGAシリーズの定価値上げはいつから？",
                "a": "2026年5月22日発売のアビスアイ(M5)から、1パックの希望小売価格が180円→200円に値上げされ、1BOX定価は¥6,000(税込)になります。値上げ後の初動相場形成は不確実性が高く、値上げ前の180円定価最後のメガ弾(ニンジャスピナー周辺)はコレクション価値が意識されています。",
            },
        ])
    elif cat_id == "ss":
        faq_items_base.extend([
            {
                "q": "S&SシリーズのBOXは絶版ですか？",
                "a": "S&Sシリーズの公式の生産は終了しており、市場流通は中古/未開封の在庫のみです。レギュレーションマークA〜Fで構成され、2023年〜2026年1月にかけて段階的にスタンダード落ちが完了しました。需要が在庫を上回るほど相場が上昇する『絶版プレミア相場』のシリーズです。",
            },
            {
                "q": "S&Sシリーズで最も高額なBOXは？",
                "a": f"{update_date}時点で当サイト掲載の最高額BOXは「{stats.get('top_name', 'イーブイヒーローズ')}」で¥{stats.get('top_price', 0):,}です。S&Sシリーズはイーブイヒーローズ・VMAXクライマックス・蒼空ストリーム・パラダイムトリガーなどが5桁〜6桁の高値圏で安定しています。" if stats else "",
            },
        ])
    faq_items_base.append({
        "q": f"{config['short']}の買取価格はどのくらいの頻度で更新されますか？",
        "a": "毎日3回(11時・15時・18時 JST)、9店舗の公式サイトから自動取得して反映しています。本ページの順位・上昇率も毎回再計算されます。",
    })
    faq_items = [f for f in faq_items_base if f.get("a")]
    faq_html = (
        '<h2>よくある質問</h2>\n<div class="faq-list">\n'
        + "\n".join(
            f'<details class="faq-item"><summary>{it["q"]}</summary>'
            f'<div class="faq-answer">{it["a"]}</div></details>'
            for it in faq_items
        )
        + '\n</div>'
    )

    # JSON-LD
    breadcrumb_jsonld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ポケカ買取チェッカー", "item": "https://pokeca-box-hikaku.com/"},
            {"@type": "ListItem", "position": 2, "name": config["title"]},
        ],
    }
    faq_jsonld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": it["q"],
             "acceptedAnswer": {"@type": "Answer", "text": it["a"]}}
            for it in faq_items
        ],
    }
    article_jsonld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": config["title"],
        "description": config["desc_meta"],
        "url": f"https://pokeca-box-hikaku.com/{config['filename']}",
        "inLanguage": "ja",
        "isPartOf": {
            "@type": "WebSite",
            "name": "ポケカ買取チェッカー",
            "url": "https://pokeca-box-hikaku.com/",
        },
    }
    jsonld_block = (
        '<script type="application/ld+json">\n'
        + json.dumps(article_jsonld, ensure_ascii=False, indent=2) + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(breadcrumb_jsonld, ensure_ascii=False, indent=2) + '\n</script>\n'
        '<script type="application/ld+json">\n'
        + json.dumps(faq_jsonld, ensure_ascii=False, indent=2) + '\n</script>'
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://pagead2.googlesyndication.com" crossorigin>
<link rel="preconnect" href="https://www.googletagmanager.com">
<link rel="preconnect" href="https://h.accesstrade.net">
<meta name="description" content="{config['desc_meta']}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://pokeca-box-hikaku.com/{config['filename']}">
<meta property="og:title" content="{config['title']}｜ポケカ買取チェッカー">
<meta property="og:description" content="{config['desc_meta']}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pokeca-box-hikaku.com/{config['filename']}">
<meta property="og:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<meta property="og:site_name" content="ポケカ買取チェッカー">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{config['title']}｜ポケカ買取チェッカー">
<meta name="twitter:description" content="{config['desc_meta']}">
<meta name="twitter:image" content="https://pokeca-box-hikaku.com/ogp.jpg">
<title>{config['title']}｜ポケカ買取チェッカー</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5831186943118320" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-RPTS6CRTCS"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', 'G-RPTS6CRTCS');
</script>
{jsonld_block}
<style>
:root{{--bg:#f6f7fb;--card:#fff;--border:#e5e7eb;--text:#111827;--text-sub:#6b7280;--accent:#6366f1}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"メイリオ","Hiragino Sans","Yu Gothic",sans-serif;background:var(--bg);color:var(--text);line-height:1.8}}
.header{{position:sticky;top:0;z-index:100;height:56px;background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:center;padding:0 20px}}
.header a{{text-decoration:none}}
.header h1{{font-size:18px;font-weight:700;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.wrap{{max-width:1240px;margin:0 auto;padding:32px 16px 48px}}
.content-layout{{display:flex;gap:24px;align-items:flex-start}}
.content-layout article{{flex:1;min-width:0}}
.article-nav{{width:180px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 88px);overflow-y:auto}}
.article-nav-title{{font-size:13px;font-weight:700;margin-bottom:8px;color:var(--text)}}
.article-nav a{{display:block;font-size:12px;color:var(--text-sub);text-decoration:none;padding:5px 0 5px 12px;border-left:2px solid var(--border);line-height:1.4}}
.article-nav a:hover{{color:var(--accent);border-left-color:var(--accent)}}
.article-nav a.current{{color:var(--accent);border-left-color:var(--accent);font-weight:600}}
.article-nav-sub{{font-size:12px;font-weight:700;margin:14px 0 6px;color:#b91c1c;padding-top:10px;border-top:1px solid var(--border)}}
.mobile-footer-nav{{display:none;margin:24px 0;padding:18px 16px;background:#f9fafb;border:1px solid var(--border);border-radius:12px}}
.mfn-title{{font-size:14px;font-weight:700;margin-bottom:10px;color:var(--text)}}
.mfn-section{{margin-top:14px}}
.mfn-section-title{{font-size:12px;font-weight:700;color:#b91c1c;margin-bottom:8px;letter-spacing:.5px}}
.mobile-footer-nav a{{display:block;font-size:13px;padding:10px 12px;border-radius:8px;color:var(--text);text-decoration:none;background:#fff;margin-bottom:6px;border:1px solid var(--border)}}
.mobile-footer-nav a.spot{{border-left:3px solid #b91c1c;font-weight:600}}
@media(max-width:1023px){{.content-layout{{display:block}}.article-nav{{display:none}}.mobile-footer-nav{{display:block}}}}
.breadcrumb{{font-size:12px;color:var(--text-sub);margin-bottom:20px}}
.breadcrumb a{{color:var(--accent);text-decoration:none}}
article{{background:var(--card);border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:32px 28px;margin-bottom:24px}}
article h1{{font-size:22px;font-weight:800;margin-bottom:8px;line-height:1.4}}
.meta{{font-size:12px;color:var(--text-sub);margin-bottom:24px}}
article h2{{font-size:17px;font-weight:700;margin:32px 0 14px;padding-bottom:6px;border-bottom:2px solid var(--accent)}}
article p{{font-size:14px;margin-bottom:14px}}
.lead{{background:#f5f3ff;border:1px solid #c4b5fd;border-radius:8px;padding:16px 20px;margin-bottom:24px;font-size:14px}}
.cat-summary{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:18px 20px;margin:16px 0 24px}}
.cs-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:10px}}
.cs-cell{{text-align:center}}
.cs-label{{font-size:11px;color:var(--text-sub);font-weight:600}}
.cs-value{{font-size:18px;font-weight:800;color:var(--text);margin-top:2px}}
.cs-top{{font-size:14px;color:var(--text);padding-top:10px;border-top:1px dashed #fde68a;text-align:center}}
.cs-top a{{color:var(--accent);text-decoration:none;font-weight:700}}
.cat-table{{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0}}
.cat-table th{{background:#f9fafb;padding:10px 8px;text-align:left;font-size:11px;color:var(--text-sub);border-bottom:2px solid var(--border)}}
.cat-table td{{padding:10px 8px;border-bottom:1px solid var(--border)}}
.cat-table td.bx-name a{{color:var(--text);text-decoration:none;font-weight:600}}
.cat-table td.bx-name a:hover{{color:var(--accent);text-decoration:underline}}
.cat-table td.bx-date,.cat-table td.bx-retail,.cat-table td.bx-shop{{color:var(--text-sub);white-space:nowrap;font-size:12px}}
.cat-table td.bx-max,.cat-table td.bx-ratio{{white-space:nowrap;font-weight:700;font-variant-numeric:tabular-nums;color:#dc2626}}
.rank-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:14px 0 28px}}
.rank-card{{background:#fff;border:1px solid var(--border);border-radius:10px;padding:14px 16px}}
.rk-title{{font-size:13px;font-weight:800;color:var(--text);margin-bottom:2px}}
.rk-sub{{font-size:11px;color:var(--text-sub);margin-bottom:10px}}
.rk-list{{list-style:none;padding:0;margin:0}}
.rk-list li{{display:flex;align-items:center;gap:8px;padding:7px 0;border-top:1px solid #f3f4f6;font-size:12px}}
.rk-list li:first-child{{border-top:none}}
.rk-num{{font-weight:800;color:var(--accent);width:22px;flex-shrink:0;font-size:11px}}
.rk-name{{flex:1;color:var(--text);text-decoration:none;line-height:1.4}}
.rk-name:hover{{color:var(--accent);text-decoration:underline}}
.rk-val{{font-weight:700;color:#dc2626;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:11px}}
.series-narrative{{background:#f5f3ff;border-radius:10px;padding:18px 22px;margin:14px 0 28px;border-left:3px solid var(--accent)}}
.series-narrative h3{{font-size:14px;font-weight:800;color:#4338ca;margin:14px 0 6px}}
.series-narrative h3:first-child{{margin-top:0}}
.series-narrative p{{font-size:13px;color:var(--text);line-height:1.8;margin-bottom:0}}
.timeline{{margin:14px 0 28px}}
.tl-year{{margin-bottom:14px;padding:14px 18px;background:#f9fafb;border-radius:10px;border:1px solid var(--border)}}
.tl-year-label{{font-size:13px;font-weight:800;color:var(--accent);margin-bottom:8px;padding-bottom:6px;border-bottom:1px dashed var(--border)}}
.tl-list{{list-style:none;padding:0;margin:0}}
.tl-list li{{display:flex;gap:10px;align-items:baseline;padding:5px 0;font-size:12px}}
.tl-date{{color:var(--text-sub);font-variant-numeric:tabular-nums;width:42px;flex-shrink:0;font-size:11px}}
.tl-name{{flex:1;color:var(--text);text-decoration:none;line-height:1.4}}
.tl-name:hover{{color:var(--accent);text-decoration:underline}}
.tl-price{{color:#dc2626;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:11px}}
.faq-list{{margin:8px 0 20px}}
.faq-item{{background:#f9fafb;border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-bottom:8px}}
.faq-item summary{{font-size:14px;font-weight:700;color:var(--text);cursor:pointer;list-style:none;position:relative;padding-right:24px}}
.faq-item summary::-webkit-details-marker{{display:none}}
.faq-item summary::after{{content:"+";position:absolute;right:0;top:0;color:var(--accent);font-size:18px;font-weight:700}}
.faq-item[open] summary::after{{content:"−"}}
.faq-item .faq-answer{{font-size:13px;color:var(--text-sub);margin-top:10px;line-height:1.7}}
.series-links{{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0 24px}}
.series-links a{{display:inline-block;padding:10px 18px;background:#f5f3ff;border:1px solid #c4b5fd;border-radius:8px;text-decoration:none;color:var(--text);font-size:14px;font-weight:600;transition:all .15s}}
.series-links a:hover{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.cta{{display:block;margin-top:24px;padding:16px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:12px;text-align:center;text-decoration:none;color:#fff;font-size:15px;font-weight:700}}
.back{{display:inline-block;margin-top:24px;color:var(--accent);text-decoration:none;font-size:14px;font-weight:600}}
.ad{{text-align:center;padding:12px 16px}}
.ft{{text-align:center;padding:24px 16px;font-size:11px;color:var(--text-sub)}}
.ft a{{color:var(--accent)}}
@media(max-width:640px){{
  .cat-table{{font-size:12px}}
  .cat-table th,.cat-table td{{padding:8px 6px}}
  .cat-table td.bx-date,.cat-table td.bx-retail,.cat-table td.bx-shop{{display:none}}
  .cat-table th:nth-child(2),.cat-table th:nth-child(3),.cat-table th:nth-child(6){{display:none}}
  .cs-row{{grid-template-columns:repeat(3,1fr)}}
  article{{padding:20px 16px}}
}}
</style>
</head>
<body>
<div class="header"><a href="index.html"><h1>ポケカ買取チェッカー</h1></a></div>
<div class="wrap">
<div class="breadcrumb"><a href="index.html">トップ</a> &gt; {config['short']} 一覧</div>

<div class="content-layout">
<nav class="article-nav">
<div class="article-nav-title">一般記事</div>
<a href="index.html">買取価格比較</a>
<a href="sv-box-list.html"{(' class="current"' if config['cat_id']=='sv' else '')}>📋 SV全BOX一覧</a>
<a href="mega-box-list.html"{(' class="current"' if config['cat_id']=='mega' else '')}>📋 MEGA全BOX一覧</a>
<a href="ss-box-list.html"{(' class="current"' if config['cat_id']=='ss' else '')}>📋 S&S全BOX一覧</a>
<a href="weekly/">🔥 今週の値動き記事</a>
<a href="ranking.html">📊 週間価格変化ランキング</a>
<a href="souba-mynumber-2026.html">📰 相場下落・膠着とマイナンバー</a>
<a href="kaitori-tips.html">BOX買取のコツ</a>
<a href="about.html">運営者情報</a>
<a href="shop-hikaku.html">9店舗比較</a>
<a href="single-card-tips.html">シングル売り</a>
<a href="psa-guide.html">PSA鑑定ガイド</a>
<a href="mercari-hikaku.html">メルカリ・スニダン比較</a>
<a href="shrink-nashi.html">シュリンクなしBOX</a>
<a href="box-toushi.html">BOX投資の始め方</a>
<a href="restock-guide.html">再販情報の見つけ方</a>
<a href="release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
<a href="price-pattern-guide.html">📈 相場5段階パターン</a>
<div class="article-nav-sub">🔥 BOX深掘り特集</div>
<a href="30th-celebration-atari-yosou.html">【予想】30th 当たりカード</a>
<a href="30th-celebration-forecast.html">【予想】30th CELEBRATION 3種</a>
<a href="151-spotlight.html">【特集】ポケモンカード151高騰</a>
<a href="inferno-x-spotlight.html">【特集】インフェルノX高騰</a>
<a href="kokuen-spotlight.html">【特集】黒炎の支配者高騰</a>
<a href="chouden-breaker-spotlight.html">【特集】超電ブレイカー高騰</a>
<a href="clay-burst-spotlight.html">【特集】クレイバースト高騰</a>
<a href="ninja-spinner-spotlight.html">【特集】ニンジャスピナー高騰</a>
<a href="rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光高騰</a>
<a href="mega-ex-spotlight.html">【特集】MEGAドリームex高騰</a>
<a href="mega-brave-spotlight.html">【特集】メガブレイブ高騰</a>
<a href="battle-collection-spotlight.html">【特集】スタートデッキ100 下落</a>
<a href="storm-emeralda-spotlight.html">【特集】ストームエメラルダ高騰と長期予想</a>
<div class="article-nav-sub" style="color:#6d28d9">📘 掘り下げガイド</div>
<a href="zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
<a href="lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
<a href="mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
<a href="kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
</nav>

<article>
<h1>{config['title']}</h1>
<div class="meta">更新: {update_date} / データ源: 9店舗買取価格の自動収集</div>

<div class="lead"><p>{config['lead']}</p></div>

<h2>{config['short']} 相場サマリー</h2>
{summary_html}

<h2>{config['short']} 注目ランキング</h2>
<p>定価倍率と直近の上昇率で見る、シリーズ内の注目BOXトップ5を3軸で抽出しました。投資・コレクション判断の入口として活用できます。</p>
{rank_html}

<h2>{config['short']} の特徴と相場の見方</h2>
{narrative_html}

<h2>{config['short']} 発売タイムライン</h2>
<p>{config['short']}の主要BOXを発売年別に並べました。新シリーズほど相場の伸びしろが大きく、旧シリーズほど絶版プレミア相場の比重が高い傾向があります。</p>
{timeline_html}

<h2>{config['short']} 全BOX一覧 (発売日順)</h2>
<p>発売日の新しい順。商品名クリックで個別BOXの9店舗比較ページへ。</p>
{table_html}

{faq_html}

<h2>他のシリーズを見る</h2>
<div class="series-links">
{_build_category_crosslinks(config['cat_id'])}
</div>

<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100p4pe00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100p4pe00opz3" alt="トレトク" border="0" width="640" height="100" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>
<div class="ad">
  <a href="https://h.accesstrade.net/sp/cc?rk=0100pumf00opz3" rel="nofollow" referrerpolicy="no-referrer-when-downgrade"><img src="https://h.accesstrade.net/sp/rr?rk=0100pumf00opz3" alt="オリくじ" border="0" width="728" height="90" loading="lazy" decoding="async" style="max-width:100%;height:auto"></a>
</div>

<a href="index.html" class="cta">全商品の買取価格比較を見る &rarr;</a>
<a href="index.html" class="back">&larr; トップに戻る</a>
</article>
</div><!-- /content-layout -->
<nav class="mobile-footer-nav">
  <div class="mfn-title">📚 他の記事を読む</div>
  <div class="mfn-section">
    <div class="mfn-section-title">🔥 BOX深掘り特集</div>
    <a class="spot" href="151-spotlight.html">【特集】ポケモンカード151が定価12.6倍に高騰</a>
    <a class="spot" href="inferno-x-spotlight.html">【特集】インフェルノXが定価の5倍に高騰</a>
    <a class="spot" href="kokuen-spotlight.html">【特集】黒炎の支配者がなぜ高い？定価の約4倍</a>
    <a class="spot" href="chouden-breaker-spotlight.html">【特集】超電ブレイカーが定価7.5倍に高騰</a>
    <a class="spot" href="clay-burst-spotlight.html">【特集】クレイバーストとナンジャモSAR相場</a>
    <a class="spot" href="ninja-spinner-spotlight.html">【特集】ニンジャスピナーが定価2.5倍に高騰</a>
    <a class="spot" href="rocket-dan-no-eiko-spotlight.html">【特集】ロケット団の栄光が定価5.8倍に高騰</a>
    <a class="spot" href="mega-ex-spotlight.html">【特集】MEGAドリームexが定価3.2倍にW字回復</a>
    <a class="spot" href="mega-brave-spotlight.html">【特集】メガブレイブが定価2.6倍で推移</a>
    <a class="spot" href="battle-collection-spotlight.html">【特集】スタートデッキ100が大暴落？ピーク比-35%</a>
  </div>
  <div class="mfn-section">
    <div class="mfn-section-title" style="color:#6d28d9">📘 掘り下げガイド</div>
    <a href="zeppan-ranking-2026-03.html">📊 S&amp;S以降 絶版BOXランキング</a>
    <a href="lizardon-box-guide.html">🔥 リザードン高騰BOX完全ガイド</a>
    <a href="mega-pack-compare.html">⚡ MEGA拡張パック完全比較</a>
    <a href="kokuen-vs-rocket.html">⚔️ 黒炎 vs ロケット団の栄光</a>
  </div>
  <div class="mfn-section">
    <div class="mfn-section-title">📰 一般記事</div>
    <a href="index.html">買取価格比較トップ</a>
    <a href="sv-box-list.html">📋 SV全BOX一覧</a>
    <a href="mega-box-list.html">📋 MEGA全BOX一覧</a>
    <a href="ss-box-list.html">📋 S&S全BOX一覧</a>
    <a href="weekly/">🔥 今週の値動き記事</a>
    <a href="ranking.html">📊 週間価格変化ランキング</a>
    <a href="souba-mynumber-2026.html">📰 相場下落・膠着とマイナンバー</a>
    <a href="kaitori-tips.html">BOX買取のコツ</a>
    <a href="shop-hikaku.html">9店舗比較</a>
    <a href="about.html">運営者情報</a>
    <a href="release-schedule-2026.html">📅 2026年 新弾カレンダー</a>
  </div>
</nav>

<div class="ft"><a href="index.html">ポケカ買取チェッカー</a> / <a href="about.html">運営者情報</a> / <a href="contact.html">お問い合わせ</a> / <a href="privacy.html">プライバシーポリシー</a></div>
</div>
</body>
</html>"""


def generate_monthly_article(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate monthly-ranking-YYYY-MM.html for completed months.

    Idempotent: skips months whose article file already exists. The current
    (in-progress) month is also skipped so the article only ever publishes
    after the month has ended. The first and last day snapshots are sourced
    from data/history/*.json.
    """
    history_dir = project_root / "data" / "history"
    if not history_dir.exists():
        return

    import sys
    sys.path.insert(0, str(project_root))
    from scripts.monthly_article_template import build_monthly_html, build_change_list

    # Group history files by YYYY-MM
    files = sorted(history_dir.glob("*.json"))
    by_month: dict[str, list[Path]] = {}
    for f in files:
        ym = f.stem[:7]  # "2026-04"
        by_month.setdefault(ym, []).append(f)

    today = datetime.now(JST).date()
    current_ym = today.strftime("%Y-%m")

    slug_map = {p.name: _generate_slug(p.name) for p in products}

    for ym, month_files in sorted(by_month.items()):
        if ym == current_ym:
            continue  # do not publish mid-month
        if len(month_files) < 2:
            continue  # need at least two snapshots to compute change

        output_path = project_root / f"monthly-ranking-{ym}.html"
        if output_path.exists():
            continue  # already archived; do not overwrite

        first_file = month_files[0]
        last_file = month_files[-1]
        try:
            first_data = json.loads(first_file.read_text(encoding="utf-8"))
            last_data = json.loads(last_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("monthly: could not read snapshots for %s: %s", ym, e)
            continue

        changes = build_change_list(products, first_data, last_data, slug_map)
        # SV+MEGA は現役シリーズ、S&S は旧シリーズで相場特性が異なるため分けて集計
        sv_mega_gainers = sorted(
            [c for c in changes if c["diff"] > 0 and c["category"] in ("sv", "mega", "special")],
            key=lambda x: x["diff"],
            reverse=True,
        )
        ss_gainers = sorted(
            [c for c in changes if c["diff"] > 0 and c["category"] == "ss"],
            key=lambda x: x["diff"],
            reverse=True,
        )
        losers = sorted(
            [c for c in changes if c["diff"] < 0],
            key=lambda x: x["diff"],
        )

        if not sv_mega_gainers and not ss_gainers and not losers:
            logger.info("monthly: no movement detected for %s; skipping", ym)
            continue

        year, month = int(ym[:4]), int(ym[5:7])

        # Compute previous/next month YYYY-MM, only if a file exists for it
        if month == 1:
            prev_y, prev_m = year - 1, 12
        else:
            prev_y, prev_m = year, month - 1
        if month == 12:
            next_y, next_m = year + 1, 1
        else:
            next_y, next_m = year, month + 1
        prev_ym = f"{prev_y}-{prev_m:02d}"
        next_ym = f"{next_y}-{next_m:02d}"
        prev_path = project_root / f"monthly-ranking-{prev_ym}.html"
        next_path = project_root / f"monthly-ranking-{next_ym}.html"

        html = build_monthly_html(
            year=year,
            month=month,
            first_date=first_file.stem,
            last_date=last_file.stem,
            sv_mega_gainers=sv_mega_gainers,
            ss_gainers=ss_gainers,
            losers=losers,
            published_date=update_date[:10] if len(update_date) >= 10 else update_date,
            prev_ym=prev_ym if prev_path.exists() else None,
            next_ym=next_ym if next_path.exists() else None,
        )
        output_path.write_text(html, encoding="utf-8")
        logger.info(
            "monthly: wrote %s (SV+MEGA %d gainers, S&S %d gainers, %d losers)",
            output_path.name, len(sv_mega_gainers), len(ss_gainers), len(losers),
        )


def generate_category_pages(
    products: list[MasterProduct],
    project_root: Path,
    update_date: str,
) -> None:
    """Generate category summary pages (SV / MEGA / S&S)."""
    for config in CATEGORY_PAGE_CONFIG:
        html = _build_category_page_html(config, products, project_root, update_date)
        out_path = project_root / config["filename"]
        out_path.write_text(html, encoding="utf-8")
        logger.info("Generated category page: %s", out_path)


# 時限記事: 発売日到達で自動バナー切替
# file: 記事ファイル名
# release_date: 発売日 (YYYY-MM-DD)
# post_release_link: 発売後の誘導先
# post_release_label: 誘導先のラベル
TIMED_ARTICLES = [
    {
        "file": "storm-emeralda-forecast.html",
        "release_date": "2026-07-31",
        "post_release_link": "box/storm-emeralda.html",
        "post_release_label": "ストームエメラルダBOXの現在の買取価格を9店舗比較で見る",
        "pre_text_prefix": "🔮 発売前予想記事 — 発売まで",
    },
    {
        "file": "abyss-eye-forecast.html",
        "release_date": "2026-05-22",
        "post_release_link": "box/abyss-eye.html",
        "post_release_label": "アビスアイBOXの現在の買取価格を9店舗比較で見る",
        "pre_text_prefix": "🔮 発売前予想記事 — 発売まで",
    },
]


# スポットライト記事(slug → 対応BOX名) マッピング。
# generator がBOXの最新データを使って記事冒頭の「最新データ」ボックスを上書きする。
SPOTLIGHT_ARTICLES = [
    {"file": "151-spotlight.html", "box_name": "SV 強化拡張パック「151」", "box_slug": "151"},
    {"file": "kokuen-spotlight.html", "box_name": "SV 強化拡張パック「黒炎の支配者」", "box_slug": "ruler-of-black-flame"},
    {"file": "inferno-x-spotlight.html", "box_name": "MEGA 拡張パック「インフェルノX」", "box_slug": "inferno"},
    {"file": "chouden-breaker-spotlight.html", "box_name": "SV 拡張パック「超電ブレイカー」", "box_slug": "chouden-breaker"},
    {"file": "clay-burst-spotlight.html", "box_name": "SV 拡張パック「クレイバースト」", "box_slug": "clay-burst"},
    {"file": "ninja-spinner-spotlight.html", "box_name": "MEGA 拡張パック「ニンジャスピナー」", "box_slug": "ninja-spinner"},
    {"file": "rocket-dan-no-eiko-spotlight.html", "box_name": "SV 拡張パック「ロケット団の栄光」", "box_slug": "rocket-dan-no-eiko"},
]


def update_spotlight_summaries(
    products: list[MasterProduct],
    project_root: Path,
) -> None:
    """Populate <!-- AUTO:SPOT_SUMMARY --> blocks in spotlight articles.

    Shows: current max-price, retail multiplier, 7-day trend, last update.
    Runs daily via cron so figures stay fresh even when article prose is frozen.
    """
    pattern = re.compile(
        r"<!-- AUTO:SPOT_SUMMARY -->.*?<!-- /AUTO:SPOT_SUMMARY -->",
        re.DOTALL,
    )
    today = datetime.now(JST).date().isoformat()
    history_dir = project_root / "data" / "history"

    by_name = {p.name: p for p in products}

    for spot in SPOTLIGHT_ARTICLES:
        fpath = project_root / spot["file"]
        if not fpath.exists():
            continue
        product = by_name.get(spot["box_name"])
        if not product:
            continue
        active = {sid: product.prices.get(sid, 0) for sid in SHOP_IDS if product.prices.get(sid, 0) > 0}
        if not active:
            continue
        max_price = max(active.values())
        max_shop = SHOP_NAMES.get(max(active, key=active.get), "-")
        ratio = (max_price / product.retail_price) if product.retail_price > 0 else 0
        trend_html = _generate_trend_comment(product.name, history_dir, max_price)
        # Strip outer wrapper (it has its own styling for box pages) and use inner text only
        trend_text = ""
        trend_color = "#6b7280"
        m = re.search(r'color:(#[0-9a-fA-F]+)".*?<span class="trend-icon">([^<]+)</span><span class="trend-text">([^<]+)</span>', trend_html)
        if m:
            trend_color = m.group(1)
            trend_text = f'{m.group(2)} {m.group(3)}'

        block = (
            '<!-- AUTO:SPOT_SUMMARY -->'
            '<div class="spot-live-summary" '
            'style="background:linear-gradient(135deg,#eef2ff,#f5f3ff);'
            'border:1px solid #c4b5fd;border-radius:10px;padding:14px 18px;'
            'margin:14px 0 22px;display:grid;'
            'grid-template-columns:repeat(3,1fr);gap:12px;align-items:center">'
            f'<div><div style="font-size:11px;color:#6b7280;font-weight:600">最新BOX買取最高額</div>'
            f'<div style="font-size:20px;font-weight:800;color:#7c3aed">¥{max_price:,}</div>'
            f'<div style="font-size:11px;color:#6b7280">{max_shop}</div></div>'
            f'<div><div style="font-size:11px;color:#6b7280;font-weight:600">定価倍率</div>'
            f'<div style="font-size:20px;font-weight:800;color:#111827">{f"{ratio:.1f}倍" if ratio > 0 else "-"}</div>'
            f'<div style="font-size:11px;color:#6b7280">定価¥{product.retail_price:,}</div></div>'
            f'<div><div style="font-size:11px;color:#6b7280;font-weight:600">相場トレンド</div>'
            f'<div style="font-size:13px;font-weight:700;color:{trend_color};line-height:1.4">'
            f'{trend_text or "データ蓄積中"}</div>'
            f'<div style="font-size:10px;color:#6b7280;margin-top:2px">更新日: {today} (毎日自動)</div></div>'
            '</div>'
            '<!-- /AUTO:SPOT_SUMMARY -->'
        )

        content = fpath.read_text(encoding="utf-8")
        if not pattern.search(content):
            continue
        new_content = pattern.sub(block, content)
        if new_content != content:
            fpath.write_text(new_content, encoding="utf-8")
            logger.info("Updated spotlight summary: %s (¥%d)", fpath.name, max_price)


def update_timed_articles(project_root: Path) -> None:
    """Insert/update a time-sensitive banner inside <!-- AUTO:TIMED_BANNER --> blocks.

    - Before release_date: show countdown banner
    - After release_date: show 'released, see current price' banner
    """
    today = datetime.now(JST).date()
    pattern = re.compile(
        r"<!-- AUTO:TIMED_BANNER -->.*?<!-- /AUTO:TIMED_BANNER -->",
        re.DOTALL,
    )
    banner_style = (
        "background:linear-gradient(135deg,#fef3c7,#fde68a);"
        "border:2px solid #f59e0b;border-radius:10px;"
        "padding:14px 18px;margin:12px 0 20px;"
        "font-size:14px;font-weight:600;color:#78350f;"
        "display:flex;gap:10px;align-items:center;flex-wrap:wrap"
    )
    released_style = (
        "background:linear-gradient(135deg,#dcfce7,#bbf7d0);"
        "border:2px solid #16a34a;border-radius:10px;"
        "padding:14px 18px;margin:12px 0 20px;"
        "font-size:14px;font-weight:600;color:#14532d;"
        "display:flex;gap:10px;align-items:center;flex-wrap:wrap"
    )

    for t in TIMED_ARTICLES:
        fpath = project_root / t["file"]
        if not fpath.exists():
            continue
        try:
            rd = datetime.strptime(t["release_date"], "%Y-%m-%d").date()
        except ValueError:
            continue

        if today < rd:
            days = (rd - today).days
            banner = (
                f'<!-- AUTO:TIMED_BANNER -->'
                f'<div class="timed-banner" style="{banner_style}">'
                f'<span>{t["pre_text_prefix"]}あと{days}日 '
                f'({rd.year}年{rd.month}月{rd.day}日発売予定)</span>'
                f'</div>'
                f'<!-- /AUTO:TIMED_BANNER -->'
            )
        else:
            banner = (
                f'<!-- AUTO:TIMED_BANNER -->'
                f'<div class="timed-banner" style="{released_style}">'
                f'<span>✅ {rd.year}年{rd.month}月{rd.day}日 発売済み</span>'
                f'<a href="{t["post_release_link"]}" '
                f'style="color:#14532d;text-decoration:underline;font-weight:700">'
                f'{t["post_release_label"]} →</a>'
                f'</div>'
                f'<!-- /AUTO:TIMED_BANNER -->'
            )

        content = fpath.read_text(encoding="utf-8")
        if not pattern.search(content):
            continue
        new_content = pattern.sub(banner, content)
        if new_content != content:
            fpath.write_text(new_content, encoding="utf-8")
            logger.info("Updated timed banner: %s", fpath.name)
