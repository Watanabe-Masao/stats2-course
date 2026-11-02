# 原本の書き方（参考）

CLAUDE.md の決まりを、原本に書くときの形（記法・YAML の例・項目の一覧・build が止めるもの）と公開の手順。決まりそのもの（何をどこに置くか・なぜか）は CLAUDE.md が元で、ここはその書き方。食い違ったら CLAUDE.md に合わせて直す。

## 本文の記法（content/units/*/S*.md）

| 書き方 | 意味 |
| --- | --- |
| `::: task` 〜 `:::` | 問題文の枠（他に ask・key・summary・pattern・warn・info） |
| `::: toggle 題名` 〜 `:::` | 開閉する欄（答えなど） |
| `{{problem:Q-U09-001}}` | 問題を差し込む（番号・難度・答えの開閉は自動） |
| `{{lab:LAB-count}}` | ラボを埋め込む（自由に動かす版） |
| `{{lab:LAB-scale@s1-temp}}` | 場面ごとの版（最初のモード・数値・課題・予想を tool.yaml の presets に書く） |
| `{{fig:FIG-U03-population}}` | 図を入れる（説明文は content/assets.yaml） |
| `{{ref:REF-PQ-DB}}` | 旧版の問題集などへのリンク（shared.yaml の refs） |
| `{{unit:U14}}` `{{term:TERM-perm}}` | 単元・用語へのリンク（ID で書く。番号や名前を直接書かない） |
| `{{power:P3}}` `{{icon:lab}}` `{{stage:S2}}` | 力・補助・段階の印 |
| `{{shared:explain_pattern}}` | 共通文言 |
| `^ 文` | 灰色の補足行 |
| `**太字**` `$$数式$$` 表・リスト | そのまま |

## 問題の答えに「ラボで確かめる」を付ける

問題に `lab:` を書くと、答えの中にその問題の数値が入ったラボが入る。

```yaml
  lab:
    id: LAB-scale
    mode: unit                      # 最初に開くモード
    set: {kind: temp, a: 10, b: 15} # 問題の数値
    task: 課題の文（ラボの上に出る）
    predict: {type: number, key: "ratio:1", label: "K で B÷A", unit: "倍"}   # 予想するまで結果を隠す
    expect: 1.018                   # 予想の答え。テストでラボの計算値と照合する（HTML には入れない）
    why: 結果のあとに出す一言
```

場面の版はタブを1つ（mode）に絞る。複数見せるときは presets に `modes: [judge, bin]`。予想のある版では `set` で決めた選択欄（`data-key` の select）は文字になり、選べない。
Notion の埋め込み（高さ約320pxで固定）では小さい表示になる：予想の前は課題カードだけ、結果のあとは要点と操作だけ、表・式は「くわしく」、広く使うときは「大きく開く ↗」。`build/check_all.sh` が 360×320 で予想の前が枠に収まるかを調べる。

答えに問題文にない数が出るのに `checks` がないと build が止まる。計算した数でなければ `no_checks: 理由` を書く。

## 法則を見つける・解説付き再生（tool.yaml の presets）

法則を見つける（tool.yaml の presets、または問題の lab。応用・転用で使う）：

```yaml
  s3-rule:
    mode: power
    steps:                       # 2段以上。各段で予想する
      - label: n＝25             # 記録の表に出る条件の名前
        set: {n: 25}             # その段で変える値（前の段からの差分でよい）
        task: 課題の文
        predict: {type: number, key: power, label: "検出力"}
        expect: 0.516            # テストで照合（HTML には入れない）
        why: 結果のあとの一言
    law: {title: 式で説明する, lines: [式…], text: 説明, limit: この式で言えないこと}
```

解説付き再生（tour。#90、試作は LAB-pois@rel-approx-tour）：同じ段階データから「図で解説」（段ごとの静止図）・「アニメで解説」（ラボの再生）・「自分で触る」を作る。関係（変換・対比・導出）の説明に使う。予想は置かない。

```yaml
  rel-approx-tour:
    mode: approx
    tour:
      kmax: 10          # 棒を出す範囲。ラボと静止図で共有する
      decimals: 3       # 丸め。ラボと静止図で共有する
      steps:            # 2段以上
        - title: λ を決める
          text: 二項分布で **n×p＝λ** を一定に保つ。   # **…** を強調。埋め込み（360×320）に収まる長さ（2行まで）
          set: {n: 10, lam: 3, k: 3}                     # 段の始め＝前の段の終わり＋set
          focus: np                                      # 囲む場所（ラボの data-focus）
        - title: n を大きく
          text: '**n を大きく**すると p＝λ÷n は小さくなる。'
          frames: [{n: 15}, {n: 20}, {n: 30}]            # 再生で順に渡す値。補間しない（整数は整数で書く）
          ms: 900                                        # 1つの frame の時間（省略 900）
```

- 再生は今の段だけ動かして止まる（自動で次へ進めない）。操作は「前へ／再生／次へ」。「自分で動かす」で解説を止め、「解説に戻る」で値・説明・強調を止めた frame に戻す。
- 静止図は build が set か frames のある段ごとに作る（図ID `FIG-<ラボ>-<版>-<段>`）。関係の `figures:` に書くとネットワークに出る。
- 状態から静止図と照合する数を作る計算は build/tour.py の MODES に、ラボのモードごとに書く（今は LAB-pois の approx・geom・hyper・pois、LAB-binom の path・pmf、LAB-expect の joint）。段に `mode:` を書くと別のモードへ移る（値は持ち越さない。対比で2つの分布を段ごとに並べるときに使う）。テスト（test_labs.js）が段と frame ごとにラボの値と照合し、再生・戻る・埋め込みの収まりを確かめる。
- build が止めるもの：tour と predict・steps・task の同居、2段未満、text がない・`**` が閉じない、モードの set にない値、整数の値を小数で書く、MODES にないモード。

## 概念データの書き方（content/terms.yaml・relations.yaml）

### 問題 → 確かめる概念（`concepts:`）


```yaml
- id: Q-U13-021
  stage: S3
  concepts: [TERM-expect, TERM-var, TERM-sd, TERM-indep]   # 用語（説明のある概念）か REL-… の id
```

- build が止めるもの：用語・関係にない id、まだ説明のない用語（先に概念にする）、`concepts_linked` の単元で `concepts:` のない問題。
- 書いた概念は、ネットワークの概念の「確かめる問題」に出る。

### 概念・関係からラボを開く（`labs:`）

```yaml
  labs:
  - {id: LAB-expect, preset: s1-var, purpose: ずれの2乗の期待値として分散を組み立てる}
```

- 概念（terms.yaml）と関係（relations.yaml）に書ける。書けるのは id・preset・purpose だけ。URL は build が `site_base_url` から作る（配布先で空なら出さない）。
- build が止めるもの：ないラボ、そのラボにない場面の版（tool.yaml の presets）、id・preset・purpose 以外の項目。

### 概念・関係に図を出す（`figures:`）

```yaml
  figures: [FIG-U14-concept]
```

- 概念と関係に書ける。書けるのは図の id だけ（unit.yaml の figures か content/assets.yaml にある図）。説明と URL は build が図の定義と `site_base_url` から作る（配布先で空なら出さない）。
- ネットワークの概念の詳細・関係の説明に出る（#88）。図の要らない線（前提など）には書かない。
- build が止めるもの：ない図、id 以外の書き方。

### 式の分解の木（`formulas[].tree`）


```yaml
  formulas:
  - id: F-std-def                 # 式 ID（F-…。変えない・消さない。#118 D1）。tex は書かない（build が木から作る）
    symbols:
    - {symbol: Z, meaning: 標準化した値, key: Z, kind: rv}
    - {symbol: X, meaning: 確率変数, key: X, kind: rv}
    - {symbol: μ, meaning: X の期待値, key: mu, concept: TERM-expect, kind: param}
    - {symbol: σ, meaning: X の標準偏差, key: sigma, concept: TERM-sd, kind: param}
    tree: {"op": "eq", "args": [{"sym": "Z"}, {"op": "div", "args": [{"op": "sub", "args": [{"sym": "X"}, {"sym": "mu"}]}, {"sym": "sigma"}]}]}
```

- 葉は `{"sym": key}` か `{"num": 数}`。演算は eq・add・sub・mul・div・pow・neg・sqrt・abs・sum・prod・int・fn（kn-schema の formulaNode）。sum・prod・int は `var`（動かす記号）と `lower`・`upper`。
- `fn` の `name` は、その式の symbols の key（E・V・P・Cov・comb・fact など。記号に `concept` を書けば、その概念の式へ開く）か、記号に書かなくてよい共通の関数（exp・log・gt・ge・lt・le・between）。比べる式（X＞x・a≦X≦b）を gt・between で書くのは仮の形で、#72 で型として決め直す。
- 記号の `kind`：value（1つの値）・data（データの一覧）・rv（確率変数）・param（母数）・index（添え字）・const（定数）。
- build が止めるもの：symbols の key にない葉・関数・動かす記号、記号の `concept` が用語にない、知らない演算。
- build が型で検査し、out/site/net/stats2.json を書き出す。画面はこの JSON だけを読む。個人の理解度・得点・復習日は概念の原本に入れない（個人用の学習記録へ）。

## 実験室の定義の書き方（content/experiments.yaml）

### 値の表の作業台

概念の `table_workspace`（型の改訂15、#119）は `formula`（期待値の定義の式の番号）、任意の `linear`（E(aX＋b)の式の番号）、`tables`（実験室の値の表のテーマを指す：`{experiment: EXP-…, theme: テーマ id, use: start か compare}`。値・重みを2か所に書かない）を持つ。build がテーマから値・重み・呼び名・単位を写して公開の JSON（型の valueTable）にし、式の参照・テーマの有無・値・重みを検査する。同じテーマなら作業台と実験室で値・重み・期待値が一致する。

### 項目

- `links`：つなぐ概念（説明のある用語）と線（関係・導出）。地図と実験室を行き来する
- `start`（前の条件）と `compare`（問いで変える条件）、`vary`（条件の範囲）。`reason`（理由の段：概念の式と1〜3行）
- `themes`：場面（こういう時に使う）。計算は同じで、並びの絵・言葉・最初の p が変わる
- `counterexamples`：反例を実験する。成り立つ条件（`breaks`。概念の `conditions.math` の言葉で）を1つ崩した起き方（urn・streak・mix）で理論とのずれを見る。数は概念しだい
- 反例の `effect`（平均・散らばりの向き。mean: same・spread: larger／smaller）：build（build/effects.py）が起き方の定義から分布を分数で求め、vary の全部の n・p とテーマの p で確かめる。端（n＝1・割合 0・1）は「同じ」になることも確かめる。公開の JSON には出さない（画面は engine の mechanismMoments から答えを求める）
- `model`：`binom`（二項分布。vary・start・compare）か `table`（値の表。#119：テーマごとに values・labels・start と compare の重み・change、反例は values と weights の表）。値の表は、値が小さい順・重みと呼び名が値と同じ数・前と変えた重みが違うことを build が確かめる

## 図の型（build/figures.py）

図は設定から作る：`popsample`（母集団と標本・どちらの側の数か）、`ladder`（尺度の段にデータを置く）、`bars`、`pairs`、`product`、`capture`、`fpc`、`hist`、`boxplot`、`line`、`dev`（平均からの偏差）、`paths`（n 回中ちょうど k 回成功する並びを全部書き出す。解説付き再生の静止図）、`joint`（2つの 0/1 の同時確率の2×2の表。独立なら の値つき）、`dist`（確率分布の棒か曲線。期待値の▲・±標準偏差の帯・確率の面積。例：`{type: dist, family: binom, n: 4, p: 0.25, unit: 人, highlight: [1]}`、`{type: dist, family: normal, mu: 100, sigma: 10, ticks: [70, 130, 10], shade: [{from: 90, to: 110, label: 約68%}]}`。family は table・binom・poisson・geom・hyper・normal・uniform・expo。`overlay` で2つ目の分布を点線の棒か正規分布の曲線で重ね、`lines` で数の行、`maxdiff` で差の最大（丸めて0になるときは「0.001未満」）を出す）。新しい形が要るときは figures.py に型を足す（設定から作れない図を手で描かない）。

## 公開

### 公開サイト（ラボと図）

`publish/notion.yaml` に `site_base_url` があると、ラボと図はアップロードせず URL で埋め込む（`<slug>/?p=場面`、`fig/<図ID>.svg`）。
`python3 build/build.py` で `out/site/` ができる。`build/check_all.sh` を通してから `build/deploy_site.sh <公開用リポジトリの手元のパス>` で公開する。公開されるのは out/site/ だけ（原本・予想の答え・個人データは出ない）。
ラボの `slug` と図の ID は URL の一部なので変えない。

### Notion への公開手順

`site_base_url` があるので、ラボと図はアップロードせず公開サイトの URL で埋め込む（out/notion/<ID>.md をそのまま使う）。

1. `build/check_all.sh` を通し、`build/deploy_site.sh <公開用リポジトリの手元のパス>` で公開サイトを更新する（ページより先に。埋め込み先が無いと空の枠になる）。
2. 既にあるページは、`out/notion/<ID>.md` の全文で `publish/notion.yaml` のページへ replace_content。長いので、別のエージェントにファイルを読ませて一字も変えずに送らせてよい。
3. 新しい単元ページは、入口ページを親に create-pages（アイコン 📘、題名 `NN｜単元名`、本文は out/notion/<ID>.md）。返ったページ ID を `publish/notion.yaml` の `units:` に番号順で書く。
4. もう一度 build し、`out/notion/*.md` で新しい ID を参照しているページを探して、それぞれ旧版の ID へのメンションを新しい ID に置き換える（update_content、replace_all）。
5. 入口ページ：旧版一覧の行を消し、末尾に自動で付いた子ページを、前の単元の子ページの後ろへ移す。
6. 表示される数（タブ・開閉・ラボ・図・メンションなど）を、公開後に取得したページと照らし合わせる。
7. 移行した単元は `python3 build/audit.py <ID>` で旧版との欠落がないことを確かめる（落とす項目は migration/waivers に理由を書く）。

`site_base_url` が空の配布先では、`python3 build/publish_prep.py <ID>` で素材を一覧してアップロードし（返った content_length が一覧のバイト数と一致することを確かめる）、`python3 build/publish_prep.py <ID> <json>` で作る `out/notion/<ID>.publish.md` を使う。

旧版（Notion）の残りは `publish/legacy.yaml` で管理する。build が各項目を「まだ参照あり／削除してよい／削除済み」で出す。「削除してよい」になったら、その生成物を Notion に公開してから旧版を削除し、`deleted:` に日付を書く。削除済みの ID が原本や生成物に戻ると build が止まる。旧版を新しく参照しない（refs に足さない）。

入口ページ（root.md）の子ページは `<page url>` ブロックのまま置く（mention に変えると子ページが消えるため Notion が拒否する）。新しい単元ページを作ると入口の末尾に子ページが付くので、root.md の並びに合わせて動かす。

個人用の学習記録（publish/notion.yaml の personal_root）：解答記録・到達記録・学習ログの3つのDB。問題は「問題ID」の文字列で指す。教材の生成物から個人データを読み書きしない。

Notion の記法の注意：`<sup>` は消える（ʳ や ² を使う）。メンションは `<mention url="https://app.notion.com/p/ID" />`。
