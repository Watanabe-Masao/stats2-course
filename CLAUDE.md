# このリポジトリでの作業ルール

統計検定2級の教材の原本。利用者（渡辺さん）は iPhone の Notion で読む。文章はすべて日本語、です・ます調ではなく常体。

## 守ること

1. **原本だけを編集する**。Notion のページ本文を直接直さない。直したら `python3 build/build.py` で生成し、生成物で Notion を更新する。
2. **ID を変えない・消さない**。不要になった問題は `retired: true` を付けて残す（個人の解答記録が ID を参照している）。
3. **同じことを2か所に書かない**。段階名・アイコン・力・説明の型などは `content/*.yaml` から `{{...}}` で呼ぶ。
4. **個人データを入れない**。学習記録・得点・回答は Notion の個人用ルートに置く。
5. **数値は検算式を書く**。問題には `checks`、本文の数値は unit.yaml の `checks` に書き、build が通ってから公開する。
6. **スマホ前提**。表は2〜3列まで。冒頭は「ナビ＋ゴール＋タブ」だけ。説明はガイドへ。

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

## 段階の定義（問い・問題・ラボの形はここから決める）

| 段階 | 身に付ける力と形 |
| --- | --- |
| 初学・復習 | 意味と手順。1つの場面で予想→確かめる（課題1つ・予想1回）。分かりやすさを優先 |
| 応用・転用 | 統計検定2級の範囲の全部。ばらつき・外れ値・混ざりのあるデータを要約・検定・区間でシンプルにする。「法則を見つける」（下の steps）もここ |
| 発展 | 統計を理解する力。なぜその形か・1つの数で何が消えるか・前提が崩れると何が揺れるか・他の単元とのつながり |
| 創造 | 統計で考え、統計の外と切り分ける力。要因の混ざったデータで自分で問いを立て、統計で言えることと解釈を分ける |

- 発展・創造は統計検定の枠を意図的に外した段階。手前の延長（難しい計算・1級の知識）ではなく、考え方を変える。統計が中心であることは変えない。
- 発展・創造には答えの決まった問い（予想→照合・`predict`）を置かない。問題は「説明する」「切り分ける」形にし、答えには「1つの考え方の例」を置く。
- 2級の範囲で解ける問題は、難しくても応用に置く（040番台の問題も同じ。ID は変えず `stage` だけ直す）。
- 発展・創造の本文は `{{shared:complex_pattern}}`（何が複雑にしているか→なぜ1つの数では言えないか→どう分けて考えるか→数字とどう向き合うか）で説明させる。単元によって形は変えてよい。
- 創造の振り返りの観点（任意。到達の基準・点数にしない）に「切り分け」（統計で言えること／言えないこと）と「解釈」（筋の通った読み方を2つ以上）を置く。

## 考え方の枠組み（単元ごとに選ぶ・組み合わせる）

発展・創造とラボの設計には、次の3つの考え方を単元の内容に合わせて選んで使う（江崎貴裕の3冊をエッセンスとして）。向かない単元に無理に当てない。

| 考え方 | 何を問うか |
| --- | --- |
| データ解釈学 | データはどう生まれたか（取り方・偏り・欠け）。事実と解釈を分ける |
| データ可視化学 | 何を指標にするか・どう見せるか。指標と図で何が見え、何が消えるか |
| 数理モデル思考 | 仮定を置いて式にする。仮定を変えると結論がどう動くか |

目安：U04〜08 は可視化学、U09〜16 は数理モデル、U17〜23 は解釈学（取り方）＋数理モデル、U24〜27 は解釈学、U28〜30 は解釈学＋可視化学、U31〜32 は解釈学（取り方）。

## 段階ごとのラボの形

- 初学・復習：1つの場面で予想→確かめる。入口は単純にする。
- 応用・転用：複雑なデータを統計でシンプルにする。条件を変えて決まりを見つけ、式で説明する（steps と law）。
- 発展・創造：複雑なものを複雑なものとして扱う。予想→照合ではなく、自由に動かして「なぜ複雑か」を説明させる（LAB-explore など。presets に task だけを書き、predict は書かない）。
- 統計図は、数字と図のつながりを触って覚える（LAB-graph：点を動かすと図と数がいっしょに動く）。
- 統計とデータの解釈は別の力として書く。統計は前提のもとで言えること（要約・推定・検定と誤差の幅）。解釈は文脈・現場の知識・因果の見立て・価値判断と合わせて読む力で、学習者に委ねる。
  - 「成り立たない場合」は統計の弱点ではなく境目。そのとき何で判断するか（データの取り方を変える・現場の知識・費用や価値判断）まで考えさせる。創造の振り返りの観点は「切り分け」。
  - 解釈には正解を書かない。「1つの考え方の例」は統計の結果と解釈を分け、筋の通った読み方を2つ以上並べてもよい。
  - きれいに説明できない複雑なデータも載せ、統計でどこまで整理でき、どこからが解釈かを見せる。

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

## 概念・関係・導出（知識ネットワークのデータ）

型 v1（2026-10-29 決定）の元はリポジトリ knowledge-net の schema/。ここの docs/knowledge-net/schema/ は build が使う写しで、直すときは knowledge-net で直して `python3 build/sync_schema.py --update` で取り込む（違うと check_all が止まる）。関係の種類の定義は relation-types.yaml。

- 概念＝用語（content/terms.yaml）。`definition` を書いた用語が概念になる。
  - 必須：`principle`・`conditions`・`example`・`counterexample`・`version`（1から。意味が変わる書き直しで1つ上げる）。
  - `conditions` は `math`（数学的な定義・成立の条件）と `data`（現実のデータに当てはめるときの条件・確かめ方の手掛かり）に分ける。形の手掛かりを定義の条件に書かない。
  - 任意：`formulas`（式ごとに `tex` と `symbols`：記号・意味・値の範囲）、`misconceptions`（よくある誤解と訂正。反例とは別）、`sources`（`source` は shared.yaml の sources の名前、`locator` は該当箇所）。
  - 説明に数があれば `checks`。
- 関係は content/relations.yaml（REL-…、`version` 必須）。8種類（前提・導出・一般化・特殊化・変換・対比・統合・応用）。登録の前に relation-types.yaml の定義・矢印の読み方・該当例・該当しない例を確かめる。
  - 前提には `premise`（learning：理解に必要な知識／mathematical：数学的な成立条件・定義に使う）。
  - 変換には `mode`（exact：厳密／approximation：近似／limit：極限）と成立条件。「近い」と「等しい」を混ぜない。
  - 導出には成立条件。前提が2つ以上なら関係ではなく導出の点にする。
  - 一般化と特殊化は同じ組を両方向に書かない（原則は一般化）。
  - 「前提をさかのぼる」でたどるのは前提・導出・一般化・特殊化・統合だけ（変換・対比・応用はたどらない）。学ぶ順に要るものは、変換とは別に「前提」（learning）で書く。
- 導出は content/derivations.yaml（DER-…、`version` 必須）。前提（概念・関係）→ 結論。手順と、どの前提がどこで要るか（conditions）を書く。
- 自分の教材の id は教材名を付けずに書く。別の教材の概念は `math:CON-…` のように教材名を付ける（ネットワークでは自分の id も `stats2:TERM-…` になる）。
- 説明のある概念は、どれかの関係か導出につながっていること（孤立させない）。build が止める。

### 問題 → 確かめる概念（`concepts:`）

問題に、その問題を**解く・解説を理解するのに必要な**概念か関係を書く。選択肢や文中に名前が出るだけの概念は書かない。

```yaml
- id: Q-U13-021
  stage: S3
  concepts: [TERM-expect, TERM-var, TERM-sd, TERM-indep]   # 用語（説明のある概念）か REL-… の id
```

- unit.yaml に `concepts_linked: true` を書いた単元は、retired 以外の全問に `concepts:` を書く。
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

式は、記号が別の式に開く木で持つ（#71）。1式＝1つの等式の連なり（「E(X)＝np、V(X)＝np(1−p)」は2式に分ける）。

```yaml
  formulas:
  - tex: 'Z=\dfrac{X-\mu}{\sigma}'
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
- **#72 で木から TeX を作るまでは、tex と tree を両方持つ。式を直すときは両方を直し、同じ式になっているかを自分で読み合わせる**（今は build が一致を確かめない）。単元の「式の構造」の表も手書きのままなので、記号を概念に合わせる。
- build が型で検査し、out/site/net/stats2.json を書き出す。画面はこの JSON だけを読む。個人の理解度・得点・復習日は概念の原本に入れない（個人用の学習記録へ）。

## 例題・問題にはラボか図を付ける（build が止める）

- 問題には `lab:`（上）か `figure:` を書く。`figure:` は答えの中に「🖼️ 図で確かめる」として入る（図ID は `FIG-<問題ID>`）。
- 本文の例題（`**例題…`）には、次の例題・見出し・問題までに `{{lab:…}}` か `{{fig:…}}` を置く。例題の図は unit.yaml の `figures:` に書く。
- 図は設定から作る（build/figures.py）：`popsample`（母集団と標本・どちらの側の数か）、`ladder`（尺度の段にデータを置く）、`bars`、`pairs`、`product`、`capture`、`fpc`、`hist`、`boxplot`、`line`、`dev`（平均からの偏差）、`dist`（確率分布の棒か曲線。期待値の▲・±標準偏差の帯・確率の面積。例：`{type: dist, family: binom, n: 4, p: 0.25, unit: 人, highlight: [1]}`、`{type: dist, family: normal, mu: 100, sigma: 10, ticks: [70, 130, 10], shade: [{from: 90, to: 110, label: 約68%}]}`。family は table・binom・poisson・normal・uniform・expo）。新しい形が要るときは figures.py に型を足す（設定から作れない図を手で描かない）。
- 各単元の初学「意味」か「式の構造」に、単元の中心を1枚で見せる概念図を置く。初学「図を再現する」は、その概念図を手本として示し、自分で描いて照らし合わせる形にする（手本のない「図を再現する」を作らない）。
- 図の中の数は問題文・答え（例題なら本文）にある数だけ。計算で出す数（合計・比・係数）は図を作るときに計算する。
- まだ付け終えていない単元は unit.yaml に `visuals_pending: true`（build が警告する）。

## チェック欄を教材に置かない

教材のページに、押して状態が残るチェック欄（`- [ ]`）を作らない。本文の `- [ ]` は「□」の箇条書きで出し、記録先（個人用の学習記録の到達記録）を添える。配布先の設定（personal_root が空）では記録先は出ない。lint が `- [ ]` の残りを止める。

## issue で管理する

計画の変更や置き換えで、やることと影響範囲がこぼれないよう、作業は GitHub の issue で管理する。

- 最終ゴールは #55。各段階（W0〜W5）・旧版の削除・図の型・knowledge-net・個人記録は、それぞれの issue（マイルストーン付き）にある。
- 作業は issue から始める。新しい作業は issue を作り（テンプレート「作業」の影響範囲を確かめる）、マイルストーンとラベルを付ける。
- PR の説明に、閉じる issue は `Closes #番号`、進めるだけなら `Refs #番号` と書く。終わった項目は issue のチェックを付ける。
- 計画が変わったら、計画書（docs/）・#55・関係する issue を同じ PR（または同じ作業の中）で直す。片方だけ直さない。
- 渡辺さんの判断が要るものはラベル「決めること」を付け、決まったら issue に結論を書く。
- 途中で出たアイデア・方針の変更は、すぐ直さず issue（テンプレート「アイデア・方針の変更」）にする。Claude が原本を調べて修正の大きさ（小・中・大）と影響する範囲を数で書き、取り込む時期の案を出す。渡辺さんが時期を決めたら、作業の issue に移す（済んだ段階のやり直しも作業として書く）。
- 進み具合は `python3 build/progress.py` で原本から数える（人の記憶で判断しない）。Notion の「進み具合」ページも同じものから生成する。段階を閉じる前に、その単元が全部 ✓ かを確かめる。
- issue のチェックリストは GitHub の上のもの。教材の Notion ページにはチェック欄を置かない（下の決まりのまま）。

## 確かめる

作業は必ずブランチを切って行い、全部の確認はマージの前に1回だけかける。

- **ブランチの途中のコミット**：`python3 build/check_changed.py` で、変えたものに合わせた範囲だけ確かめる（origin/main からの差分を見て、下の表のとおりに選ぶ）。
- **マージの前（PR を「マージしてよい」と伝える前）**：PR を作ると GitHub が全部（`build/check_all.sh` を base と labs の6組に分けて並行）を走らせる（.github/workflows/check.yml。PR と main への取り込みでだけ走る）。その結果が成功であることを `gh api repos/{owner}/{repo}/actions/runs` で確かめてから伝える。手元で全部を走らせるのは、GitHub で落ちた原因を調べるときだけ。
- **公開**：公開サイトの更新（deploy_site.sh）と Notion への公開は、全部が通った main から行う。

| 変えたもの | ブランチの途中で確かめること |
| --- | --- |
| CLAUDE.md・README・docs/ だけ | なし |
| 単元（content/units/UXX・problems/UXX・migration の UXX） | 単体テスト・build・その単元の旧版との突き合わせ・その単元のラボの版（1単元で数分） |
| 1つのラボ（tools/xx_lab/） | 上に加えて、そのラボの全部の版と check.js |
| 共通部分（build/・tests/・labkit・test_labs.js・templates/・content/*.yaml など） | 単体テスト・build・全単元の旧版との突き合わせ（ラボの版はマージ前の全部で） |

- 終了コードをログに残して判定する：`… > ログ 2>&1; echo "EXIT=$?" >> ログ`。「✅ 範囲内 OK」または「✅ 全部 OK」と `EXIT=0` の両方を見てから次へ進む（`tail` などの終了コードで判定しない）。
- ラボのテストを同時に2つ走らせない（ブラウザが落ちて誤った結果になる）。
- 個別には `ONLY=LAB-x,LAB-y node tools/test_labs.js`（そのラボの全部の版）、`ASSETS=LAB-prob@s6-free,… node tools/test_labs.js`（その版だけ）。

## 公開サイト（ラボと図）

`publish/notion.yaml` に `site_base_url` があると、ラボと図はアップロードせず URL で埋め込む（`<slug>/?p=場面`、`fig/<図ID>.svg`）。
`python3 build/build.py` で `out/site/` ができる。`build/check_all.sh` を通してから `build/deploy_site.sh <公開用リポジトリの手元のパス>` で公開する。公開されるのは out/site/ だけ（原本・予想の答え・個人データは出ない）。
ラボの `slug` と図の ID は URL の一部なので変えない。

## Notion への公開手順

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
