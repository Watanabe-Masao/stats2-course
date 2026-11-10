# 原本の書き方（参考）

CLAUDE.md の決まりを、原本に書くときの形（記法・YAML の例・項目の一覧・build が止めるもの）と公開の手順。決まりそのもの（何をどこに置くか・なぜか）は CLAUDE.md が元で、ここはその書き方。食い違ったら CLAUDE.md に合わせて直す。

## 本文の記法（content/units/*/S*.md）

| 書き方 | 意味 |
| --- | --- |
| `::: task` 〜 `:::` | 問題文の枠（他に ask・key・summary・pattern・warn・info） |
| `::: toggle 題名` 〜 `:::` | 開閉する欄（答えなど） |
| `{{problem:Q-U09-001}}` | 問題を差し込む（番号・難度・答えの開閉は自動） |
| `{{lab:LAB-count}}` | ラボを埋め込む（自由に動かす版） |
| `{{lab:LAB-scale@s1-temp}}` | 場面ごとの版（最初のモード・数値・課題・予測を tool.yaml の presets に書く） |
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
    predict: {type: number, key: "ratio:1", label: "K で B÷A", unit: "倍"}   # 予測するまで結果を隠す
    expect: 1.018                   # 予測の答え。テストでラボの計算値と照合する（HTML には入れない）
    why: 結果のあとに出す一言
```

場面の版はタブを1つ（mode）に絞る。複数見せるときは presets に `modes: [judge, bin]`。予測のある版では `set` で決めた選択欄（`data-key` の select）は文字になり、選べない。
Notion の埋め込み（高さ約320pxで固定）では小さい表示になる：予測の前は課題カードだけ、結果のあとは要点と操作だけ、表・式は「くわしく」、広く使うときは「大きく開く ↗」。`build/check_all.sh` が 360×320 で予測の前が枠に収まるかを調べる。

答えに問題文にない数が出るのに `checks` がないと build が止まる。計算した数でなければ `no_checks: 理由` を書く。

## 法則を見つける・解説付き再生（tool.yaml の presets）

法則を見つける（tool.yaml の presets、または問題の lab。応用・転用で使う）：

```yaml
  s3-rule:
    mode: power
    steps:                       # 2段以上。各段で予測する
      - label: n＝25             # 記録の表に出る条件の名前
        set: {n: 25}             # その段で変える値（前の段からの差分でよい）
        task: 課題の文
        predict: {type: number, key: power, label: "検出力"}
        expect: 0.516            # テストで照合（HTML には入れない）
        why: 結果のあとの一言
    law: {title: 式で説明する, lines: [式…], text: 説明, limit: この式で言えないこと}
```

解説付き再生（tour。#90、試作は LAB-pois@rel-approx-tour）：同じ段階データから「図で解説」（段ごとの静止図）・「アニメで解説」（ラボの再生）・「自分で触る」を作る。関係（変換・対比・導出）の説明に使う。予測は置かない。

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

ここは書き方（記法・項目・build が止めるもの）だけ。何を1つの概念にするか・どの関係で結ぶか・どの条件かの判断は製本（docs/rules/。① 概念・② 式と記号・③ 成立条件・④ 主張・⑤ 関係・⑥ 学ぶ順）。

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
- 公開サイトのネットワークでは、版を旧版のラボの iframe で開かず、JS の部品（math-lab の場面：Scene・Tour・Explore）で描く（#188 04b・#192）。build が版の mode・modes・set・task と、解説の段の状態（tour.states と同じ重ね方）を `play` として書き出す。予測の答え（expect・why・predict）は出さない。部品にないモードの版をネットワークから指すと、knowledge-net のテスト（tests/unit/scene.test.ts）が止まるので、先に math-lab の場面にモードを足す。本文（Notion）の `{{lab:…}}` は今までどおり旧版のラボ。

### 概念・関係に図を出す（`figures:`）

```yaml
  figures: [FIG-U14-concept]
```

- 概念と関係に書ける。書けるのは図の id だけ（unit.yaml の figures か content/assets.yaml にある図）。説明と URL は build が図の定義と `site_base_url` から作る（配布先で空なら出さない）。
- ネットワークの概念の詳細・関係の説明に出る（#88）。図の要らない線（前提など）には書かない。
- build が止めるもの：ない図、id 以外の書き方。

### 関係を開いたときの段と図（`stages:`・`chart:`。#188 04）

```yaml
  - id: REL-binom-hyper-contrast
    type: 対比
    stages:          # 対比は same・differ・so。変換は origin・operation・result。ほかの種類には書かない
      same: 当たりの数を数える。…
      differ: 戻して取る…か、戻さずに取る…か。
      so: 戻さない方が散らばりが小さい。…
    chart:           # pair＝2つの分布を並べた棒（binom・hyper・poisson）。normal＝二項分布に正規分布の曲線を重ねる（n・p）
      kind: pair
      a: {model: binom, n: 10, p: 0.3, label: 戻す（二項分布 n＝10・p＝0.3）}
      b: {model: hyper, n: 10, total: 20, success: 6, label: 戻さない（20個のうち当たり6個から10個）}
      note: どちらも平均は3個。…
    checks:          # 段・図の一言に数があれば書く（build が止める）
      - abs(10*0.3-3) < 1e-12 and abs(10*6/20-3) < 1e-12
```

- `focus`（任意）：このつながりが効く式の部品 `{formula: F-…, parts: [番号]}`。両端の概念のどちらかの式の parts の番号（ない式・範囲の外の番号は build が止める）。つながりの地図で選ぶと、その部品を光らせる（前提のつながりに使う。#188 07c）。
- `question`（任意）：このつながりで考える問い。概念のページのつながりの地図で点を選ぶと、最初に出る（その下に解説の段。#188 07c）。答えを書かない（問いの形にする）。
- 面の並びは つまり → 段 → 図 → 成立条件 → 解説・触る。段の名前（同じ所・違う所・だから／元の形・変える操作・行き着く形）は画面が付ける。前提・応用は段を書かず、説明が「なぜ前に要るか」「どう使うか」の1段になる。
- 図は画面がその場で engine の確率から描く（画像にしない）。`chart` のある関係では、画像の `figures` を面に重ねて出さない（`figures` は Notion の側で使う）。
- 図の中で学習者に予測させる数（実験室で確かめる数）を先に見せない。図は設定を1つに固定し、条件を変えて確かめるのは実験室に任せる。

### 関係図に移す（`group:`・種類・材料・`axis:`。#233）

決まりは定義書 docs/relation-map.md、手順と見本（確率分布）は設計書 docs/relation-map-design.md の 2・4。1つの分類ずつ移す。

```yaml
# shared.yaml
concept_groups:
  - {id: GRP-dist-count, category: 確率分布, name: くり返して数える, summary: 同じ条件でくり返して、成功の数を数える}
relation_map_ready: [確率分布]   # 書き終えた分類だけ
# terms.yaml
- id: TERM-binom
  group: GRP-dist-count
# relations.yaml
- {id: REL-comb-binom, from: TERM-comb, to: TERM-binom, type: 材料, description: …, version: 2}
- {id: REL-binom-hyper-contrast, …, type: 対比, axis: 取り出し方}
```

- まとまりの id は `GRP-`。まとまりの分類と語の category は同じにする（build が止める）。
- 移した分類では、その分類の語を to にした前提（mathematical）を、材料（画面の呼び名は「定義に使う概念」）か前提知識（content/learning.yaml の足す。下の「学ぶ順」）に分ける（数学的な条件は成立条件へ）。種類の親は1つまで。対比には axis。どの種類で書くかの判断は製本 ⑤・⑥、v1 の種類への写し方と移すまでの暫定は docs/rules/migration.md 2。
- 関係の種類を変えたら version を1つ上げ、description を新しい意味に直す。ID は変えない。
- 定義の依存（材料）と前提知識は直接の1段だけ。定義の依存の輪と、たどれば着く前提知識の重ね（A → B → C があるのに A → C を前提知識で書く）は build が止める（#249 ③。前提知識の重ねは学ぶ順の候補でたどる。下の「学ぶ順」）。

### 学ぶ順（content/learning.yaml。M6・#266）

学ぶ順 ＝ 関係から求める候補 ＋ 足す − 外す（製本 ⑥ の 2）。候補は build（build/learning.py）が ⑥ の 3 の向きで関係から求めるので、原本には書かない。前提（learning）を関係（relations.yaml）に書くと build が止める。

```yaml
learning:
  - id: LRN-indep-binom      # 足す：関係にはないが先に知っておきたいもの
    op: add
    from: TERM-indep          # 先に学ぶ
    to: TERM-binom            # 後に学ぶ
    version: 1
    reason: 各回が独立なので、1通りの確率が掛け算で求まる。
    units: [U14]              # 任意：その前提知識を使う単元（⑥ の 5 の 4 の根拠）
    question: なぜ並び1つの確率を掛け算で出せるのか？   # 任意：画面の前提知識のつながりで最初に出る問い
    focus: {formula: F-binom-pmf, parts: [1, 2]}        # 任意：効く式の部品
  - id: LRN-remove-t-normal  # 外す：候補のうち、学ぶ順では先に要らないもの
    op: remove
    from: TERM-t
    to: TERM-std-normal
    version: 1
    reason: 標準正規分布は t 分布の定義に使うので先に学ぶ。
```

- id は `LRN-`。理由の1文は必須（足す・外すとも）。version は1から、組か理由の意味が変わる書き直しで上げる。
- build が止めるもの：外す組が候補にない・足す組が候補と同じ・たどれば着く足す（直接の1段だけ）・合わせた学ぶ順の輪（輪の組と、来た関係の id を出す）・用語にない概念。
- 書き出し（型 v2 の改訂4）：`learning`（この行）と `learning_order`（仕上がりの組と、どこから来たか〔candidate は関係・導出の id、add は LRN- の id〕）。画面は learning_order だけで並べ、足すを「前提知識」として描く。
- 関係を足す・種類を変えると候補が変わる。輪や重ねで止まったら、⑥ の 3 の向きは変えず、組ごとに外すか足すを見直す（⑥ の 5 の 7）。

### 製本の形（型 v2）で書く（`type` を ⑤ の種類に・`forms`・`claims`。#287）

製本への移行（M5）で分類ごとに移すときの書き方。意味の判断は製本（関係は ⑤、概念は ①③、主張は ④）、項目の意味は設計書 docs/schema-v2-design.md。

```yaml
# relations.yaml：移した行は、その場で type を ⑤ の種類にし、⑤ の項目を足す（id は変えない。意味が変わるので version を1つ上げる）
- {id: REL-bernoulli-binom, from: TERM-bernoulli, to: TERM-binom, type: 特別な場合, fix: param_value, fix_text: 二項分布の n を 1 にする, …}
- {id: REL-…, type: 導ける, claim: CLM-13, …}            # 主張は claims.yaml の id
# terms.yaml
- id: TERM-binom
  forms: [distribution]          # 姿（① の 3）。2つ以上なら関係の側に from_form・to_form
  claims: [CLM-6]                # この概念が主語の主張
- id: TERM-indep
  basis: {text: P(A∩B)＝P(A)P(B), terms: [TERM-prob]}   # 基準の定義が文のとき（式なら basis_formula）
# claims.yaml
claims:
  - id: CLM-6                    # ④ の番号（④-28b → CLM-28b、13 の反例 → CLM-13-counter）
    label: ④-6
    kind: 等しい
    statement: {text: X ～ B(n, p) なら E(X)＝np}
    premises: {subjects: [TERM-binom]}
    conclusion: {subjects: [TERM-expect]}
    conditions: [{text: …, kind: 仮定}]   # 主張の仮定（掛かる先は claim）
    version: 1
```

- v1 の種類（前提・材料など）と ⑤ の種類は名前が重ならないので、build は種類の名前で v1 の決まりと ⑤ の決まりを分ける。⑤ の項目（fix・claim・properties など）は ⑤ の種類の行にだけ書く（build が止める）。
- 書き出しでは、⑤ の種類の行は `type`、v1 の行は `legacy_type` になる。分類を移し終えたら shared.yaml の `v2_ready` に足す。その分類に v1 の行が残る・姿のない端・基準の定義に出る概念の扱いの漏れなどを build が止める（設計書 3.2）。
- 主張を claims.yaml に移したら、製本 ④ の §6 からその行を消し、「原本へ移した」と書く（記録の置き場は1つ。README の運用の決まり 5）。
- 線にしない主張（⑤ の 4 の帰結の例など）に解説付きのラボ・図・つまりを置くときは、主張に `labs`・`figures`・`gist` を書く（関係と同じ形。型 v2 の改訂3）。問題の `concepts:` とまとまりの矢印（shared.yaml の group_relations の `claims`）からも主張を指せる。
- 移した主張の確かめの記録は claims.yaml の `verification`（④ の §9 から行を外す）。新しく足した主張は、④ の §6 に番号だけを取り（「原本で足した」）、確かめが済むまで確認済みに数えない。

### 成立条件の区分（`conditions` の行。#249 ①）

成立条件の1行は、文字のままか、区分を書いた形のどちらか。移した分類（`relation_map_ready`）では、概念の `conditions.math` の全部の行と、行き先がその分類の関係の `conditions` の全部の行に区分を書く（build が止める）。`conditions.data` で区分のない行は「データで確かめる手掛かり」になる。

```yaml
# terms.yaml（概念）
- id: TERM-binom
  basis_formula: F-binom-pmf          # 基準にする定義の式（定義1文は学習者向けの導入のまま）
  conditions:
    math:
    - text: n は1以上の整数・0≦p≦1
      kind: 要件                       # 定義の母数の範囲
      outside: 母数が範囲の外なら、この定義の二項分布として扱えない
    - text: 各回が独立
      kind: 仮定                       # その分布になることを保証する仮定
      claim: 成功回数が B(n, p) に従う
      outside: 成功回数に二項分布を使えるとは保証できない（偶然に一致することはある）
      terms: [TERM-indep]              # 文に出る概念（画面は押せる札にする）
    data:
    - 客ごとの購入が互いに影響しないかを確かめる   # 区分なし＝手掛かり
# relations.yaml（関係）
  conditions:
  - text: np≧5 かつ n(1−p)≧5
    kind: 目安
    outside: この目安では近似を勧められない。精度を別に確かめる
    target: 二項分布の正規近似
    source: {source: …, locator: …}    # shared.yaml の sources の名前
```

区分の意味と掛かる先の判断の正本は製本 ③（docs/rules/conditions.md）。下は書くときの要約。

- **要件**：採用している定義を満たさない（母数が範囲の外など）。外れると、この定義のものとして扱えない。
- **仮定**：その定理・モデルによる保証が使えない。結論が偽とは限らない（独立でなくても、たまたまその分布になることはある）。`claim` に何を保証する仮定かを書く。
- **目安**：この目安では適用を勧められない。精度を別に確かめる。`target`（対象の近似）と `source`（出典）を書く。
- 定義そのもの（「確率密度が f(x) の式で表される」など）は成立条件に書かない。手順（連続修正で境目を 0.5 ずらす）も書かない（説明か段に書く）。
- 区分を書いても、行の文（`text`）は文字の一覧として読まれる（実験室の反例の `breaks`・式のレビューの指紋）。文を変えると、その式のレビューは古くなる。
- 分布は確率関数・確率密度の式を基準の定義にする（`basis_formula`。判断は製本 ①）。「独立な試行の成功回数」などの生まれ方は、その分布になることを保証する仮定。
- 基準の定義の式の木に出る記号に `concept` があると、その概念は定める（v1 では材料）の候補になる（#86）。名前が定義に出るのは必要条件で、十分条件ではない（製本 ⑤ の構成）。候補ごとに、材料を書くか、構成要素にしないなら `basis_excludes` に理由を書く（種類の親は書かない。関係から外れる）。build は扱っていない候補を警告し、移した分類（`v2_ready`）では止める。

```yaml
- id: TERM-binom
  basis_formula: F-binom-pmf
  basis_excludes:                      # 公開データでは basis.excludes（型 v2 の改訂2）
  - concept: TERM-dist
    kind: 使われる場                   # ⑤ の「構成要素にしないもの」のどれか。合わないときは書かず ⑤ の未決にする
    text: 外す理由の1文
```

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

ここは書き方だけ。何を問いにし、何ができれば理解したとするかの判断は製本 ⑦（docs/rules/inquiry.md）。

### 値の表の作業台

概念の `table_workspace`（型の改訂15、#119）は `formula`（期待値の定義の式の番号）、任意の `linear`（E(aX＋b)の式の番号）、`tables`（実験室の値の表のテーマを指す：`{experiment: EXP-…, theme: テーマ id, use: start か compare}`。値・重みを2か所に書かない）を持つ。build がテーマから値・重み・呼び名・単位を写して公開の JSON（型の valueTable）にし、式の参照・テーマの有無・値・重みを検査する。同じテーマなら作業台と実験室で値・重み・期待値が一致する。

### 項目

- `links`：つなぐ概念（説明のある用語）と線（関係・導出）。地図と実験室を行き来する
- `start`（前の条件）と `compare`（問いで変える条件）、`vary`（条件の範囲）。`reason`（考察の段＝理由を考える段：概念の式と1〜3行。段の名前は 2026-11-05 に「理由」から「考察」へ。#224）
- `themes`：場面（こういう時に使う）。計算は同じで、並びの絵・言葉・最初の p が変わる
- `counterexamples`：反例を実験する。成り立つ条件（`breaks`。概念の `conditions.math` の言葉で）を1つ崩した起き方（urn・streak・mix）で理論とのずれを見る。数は概念しだい
- 反例の `effect`（平均・散らばりの向き。mean: same・spread: larger／smaller）：build（build/effects.py）が起き方の定義から分布を分数で求め、vary の全部の n・p とテーマの p で確かめる。端（n＝1・割合 0・1）は「同じ」になることも確かめる。公開の JSON には出さない（画面は engine の mechanismMoments から答えを求める）
- `model`：`binom`（二項分布。vary・start・compare）か `table`（値の表。#119：テーマごとに values・labels・start と compare の重み・change、反例は values と weights の表）。値の表は、値が小さい順・重みと呼び名が値と同じ数・前と変えた重みが違うことを build が確かめる

## 図の型（build/figures.py）

図は設定から作る：`popsample`（母集団と標本・どちらの側の数か）、`ladder`（尺度の段にデータを置く）、`bars`、`pairs`、`product`、`capture`、`fpc`、`hist`、`boxplot`、`line`、`dev`（平均からの偏差）、`paths`（n 回中ちょうど k 回成功する並びを全部書き出す。解説付き再生の静止図）、`joint`（2つの 0/1 の同時確率の2×2の表。独立なら の値つき）、`dist`（確率分布の棒か曲線。期待値の▲・±標準偏差の帯・確率の面積。例：`{type: dist, family: binom, n: 4, p: 0.25, unit: 人, highlight: [1]}`、`{type: dist, family: normal, mu: 100, sigma: 10, ticks: [70, 130, 10], shade: [{from: 90, to: 110, label: 約68%}]}`。family は table・binom・poisson・geom・hyper・normal・uniform・expo。`overlay` で2つ目の分布を点線の棒か正規分布の曲線で重ね、`lines` で数の行、`maxdiff` で差の最大（丸めて0になるときは「0.001未満」）を出す）。新しい形が要るときは figures.py に型を足す（設定から作れない図を手で描かない）。

## 直したら一緒に直すもの（#336）

1つを直すと、別の所も直さないと build・CI・記録が食い違うもの。M5 で取りこぼした（件数の誤り・見本の作り直し忘れなど）ので、一覧にする。数は手で数えず、原本から数える。

| 直したもの | 一緒に直すもの |
| --- | --- |
| 式の契約（content/formula-contracts.yaml の kinds など） | `python3 build/formula_fixture.py` で式の見本（docs/formula-correctness/formulas.json）を作り直す。分類の表（docs/formula-correctness/classification.md）の種類 |
| 式の木・記号・概念の conditions・basis_formula | `python3 build/formulas.py --fingerprint F-…` で指紋を見る。代表の式なら独立なレビューの記録を新しくし、`--publish-check` を通す |
| 主張（content/claims.yaml）を足す・移す | docs/rules/claims.md の §6 の行と §9 の確かめの記録。verification の version は文字列で書く（`'4660318'`。数だけの短い SHA は数として読まれる） |
| 関係を足す・外す・種類を変える | 外した id を原本・テストから探す。記録（check-pairs.md）に書く件数は原本から数える |
| 分類を移す（v2_ready に足す） | docs/rules/migration.md の 2・4。テストが原本の中身（ある種類の行・まだ移していない分類）に頼っていないか（頼るテストは写しの中で例を作る） |
| 概念（語）を足す | build/term_icons.py の印。knowledge-net の見本を取り込むとき、概念の数のテスト（tests/e2e/viewer.spec.ts） |
| 製本の未決を足す・決める | 担当する製本の「未決」と履歴（check-pairs.md だけに書かない） |

作業の順の決まり：
- 確かめ（`check_changed.py`）を走らせている間は、同じ作業フォルダの原本を書き換えない。並べて作業するときは `git worktree add` で別の作業フォルダを使う。
- 公開は main の別の作業フォルダで build してから行う（#330）。

## 公開

### 公開サイト（ラボと図）

`publish/notion.yaml` に `site_base_url` があると、ラボと図はアップロードせず URL で埋め込む（`<slug>/?p=場面`、`fig/<図ID>.svg`）。
`python3 build/build.py` で `out/site/` ができる。`build/check_all.sh` を通してから `build/deploy_site.sh <公開用リポジトリの手元のパス>` で公開する。公開されるのは out/site/ だけ（原本・予測の答え・個人データは出ない）。
公開は main の別の作業フォルダ（`git worktree add <場所> origin/main`）で `python3 build/build.py` してから行い、作業中のフォルダでは公開しない。build は out/site がどのコミットから作られたかの印（out/site.stamp。公開しない）を書き、deploy_site.sh はまず `build/site_stamp.py --check` で、今の HEAD が origin/main と同じか・作業フォルダに書きかけの変更がないか・out/site が今の HEAD から作られたかを確かめ、違えば止める（#330。2026-11-10 にブランチの build を公開した）。

deploy_site.sh はそのあと push の前に2つを確かめて、合わなければ止める：公開する代表の式が今の版でレビュー済みか（`build/formulas.py --publish-check`）、公開中の画面（knowledge-net の GitHub Pages）の型の改訂がデータの改訂以上か（`build/screen_check.py`。#207）。画面が古いときは、knowledge-net を先に公開してからやり直す。
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
