# ワンピース買取 店舗調査結果（2026-07-14）

各店のワンピBOX買取カテゴリ。ポケカ現行URLと対比。

## A. 専用カテゴリURL追加型（確定）
| 店 | ポケカ現行 | ワンピBOX対応 | 検証 |
|---|---|---|---|
| ホムラ homura | sub128/parent14 | **sub132/parent14**（ワンピース未開封BOX） | ✓ 40件取得 |
| ルデヤ rudeya | detail/114 | **detail/224**（ONE PIECEカードゲーム） | ✓ 商品多数 |
| オク oku | cat1=340&cat2=363 | **cat1=340&cat2=364**（ONE PIECE） | ✓ 55件相当 |
| ラントゥ runto | product-category/card/ | **product-category/onepiece/** | ✓ OP-14〜16,EB-04等 |
| 森森 morimori | 検索sk=ポケカ | **検索sk=ワンピース** | ✓ OP-01〜,EB-01〜04 |

- homura ワンピURL: `/products?q[product_sub_category_id_eq]=132&q[product_sub_category_product_category_id_eq]=14`
- homura ワンピカートン=sub133、その他=sub160（BOXはsub132のみ使う）
- oku ワンピURL: `/category.html?cat1=340&cat2=364`
- rudeya ワンピURL: `/category/detail/224`
- runto ワンピURL: `/product-category/onepiece/`

## B. 全カテゴリ取得型（URL変更不要・matcherでop振り分けのみ）
| 店 | 取得範囲 | ワンピ含有 |
|---|---|---|
| ソムリエ sommelier | /products 全件 | ✓ OP-14等を確認。現状NON_POKEMONで捨ててる |
| 海峡 kaikyo | /Prod/3/（おもちゃ全般） | ✓ Prod3内にポケモン22+ONE PIECE検出。専用tag要調査 |

→ この2店は「ワンピを既に取得済み→matcherが除外」してるだけ。matcherでopカテゴリに振れば拾える。

## A2. 専用カテゴリURL追加型（確定・追加分）
| 店 | ポケカ現行 | ワンピBOX対応 | 検証 |
|---|---|---|---|
| 一丁目 icchome | cateCode=IIzyMdayU5wp7T4G | **cateCode=SEbO7gSBevo6KsPE**（ONE PIECE） | ✓ 22件(OP-16〜,EB-04〜) |

- 一丁目ワンピ: listPage APIに `cateCode=SEbO7gSBevo6KsPE`。ログイン不要で叩ける（cate/list列挙だけが要ログイン）。
- フロント確認用URL: `https://www.1-chome.com/tradeCards?category=SEbO7gSBevo6KsPE`

## B2. Claude Vision解析型（プロンプト分岐で対応）
| 店 | 状況 |
|---|---|
| コレクト collect_tendo | Xの買取価格表画像にワンピ(OP-XX)も掲載。現行プロンプトが214行目で明示的に除外中。**ワンピ用の抽出プロンプト（OP-XX/EB-XX未開封BOXのみ）を分岐追加すれば対応可** |

## B(追記) シンソク shinsoku 確定
- /yuso-kaitori で「BOX」種別フィルタ→全BOXスクロール取得→matcher絞りの方式。
- ワンピBOXも既に取得済み（NON_POKEMONで除外中）。URL変更不要でmatcher振り分けのみ。
- 任意で絞るなら `?title=ワンピース`（`https://shinsoku-tcg.com/yuso-kaitori?title=ワンピース`）。

## 結論（最終）
**全11店がワンピ対応、確定。**
- A(専用URL追加): homura(sub132)/rudeya(224)/oku(cat364)/runto(onepiece)/morimori(検索)/icchome(SEbO7gSBevo6KsPE) = 6店
- B(全件取得→matcher op振り分け・URL変更不要): sommelier/kaikyo/shinsoku = 3店
- B2(Vision抽出プロンプト分岐): collect_tendo = 1店
- 対象外: なし
→ ポケカ(8〜11店)と完全同等のフル比較が可能。
