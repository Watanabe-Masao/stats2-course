# 型（kn-schema）の変更履歴

型の中の `x-revision` が改訂番号。教材は書き出す JSON に `schema_revision` を入れ、画面は自分の型より新しい改訂のデータに警告を出す。
任意の項目の追加は v1 のまま改訂番号だけ上げる。必須の項目・意味の変更は v2 にする。

| 改訂 | 日付 | 変更 |
| --- | --- | --- |
| 1 | 2026-10-29 | v1 を決定（#41）：概念・関係・導出・教材。成立条件の math／data、記号・誤解・出典、版。関係の種類8つ（relation-types.yaml） |
| 1 | 2026-10-29 | relation-types.yaml：trace を足す。変換はたどらない（型の中身は変わらないので改訂はそのまま） |
| 2 | 2026-10-29 | 概念・関係に任意の `labs`（数理ラボへの参照：id・preset・purpose・title・url）を追加。書き出しに任意の `schema_revision`（stats2-course #61・#62） |
| 3 | 2026-10-29 | 式の分解の木：`$defs.formulaNode`（記号・数・演算 eq／add／sub／mul／div／pow／neg／sqrt／abs／sum／prod／int／fn）と `formulas[].tree`。記号に `key`・`concept`・`kind`。誤解に `labs`、概念に `counterexample_labs`（stats2-course #70・#71）。どれも任意 |
| 4 | 2026-10-29 | 概念・関係に任意の `figures`（図への参照：id・url・caption。url は教材の build が作る）（stats2-course #88）。任意 |
| 5 | 2026-10-30 | ラボへの参照（labs）に任意の `kind`（tour：ラボで解説／check：ラボで確かめる）（stats2-course #90）。任意 |
| 6 | 2026-10-30 | 関係に任意の `gist`（つまり：日常の言葉で1〜2文）（stats2-course #95）。任意 |
| 7 | 2026-10-30 | 式の記号に任意の `of`（どの確率変数の記号か）と `domain`（定義域：min・max は数か同じ式の記号の key〔k ≦ n〕・minOpen・maxOpen・integer・nonzero）（stats2-course #109）。任意 |
| 8 | 2026-10-30 | 式に任意の `parts`（意味のかたまり：path・name・meaning）、概念に任意の `workspace`（式の作業台：formula・vary・over・mean）（stats2-course #110）。任意 |
| 9 | 2026-10-31 | 任意の `experiments`（実験室：問い・つなぐ概念と線・モデル・条件の範囲・前の条件と変える条件・理由・テーマ・反例の実験〔counterexamples：崩す条件と起き方。urn・streak・mix〕・次の問い・ポイント。予想の答えは書かない）（stats2-course #102）。任意 |
| 10 | 2026-10-31 | 実験室に値の表の形（`model: table`。stats2-course #119）：テーマは値・呼び名・前の重み・変えた重み・変えたことの文、反例は崩す条件と値・重みの表。`model` で二項分布（binom）と分かれる（if／then）。二項分布の形は変わらない。任意 |
| 11 | 2026-10-31 | 概念の状態に `skeleton`（骨格：定義1文と分類だけ）、概念に任意の `short`（定義1文）と `category`（分類）。骨格なら short と category が要る（stats2-course #105・P1）。任意 |
| 12 | 2026-10-31 | 単元に任意の `group`（まとまり）と `problems`（問題の id・段階の名前・問題文の始め）。学習・問題集のタブの一覧に使う。解いた記録は持たない（stats2-course #42・P5 の PR 4）。任意 |
| 13 | 2026-11-01 | 式に任意の `id`（式の ID。`F-…`。変えない・消さない）と `defined_in`（同じ式を2つの概念に出すとき、元の概念の id）。木から作る TeX と合わせ、式の検証の結果を式 ID で指す（stats2-course #118 D1・D2）。任意 |
| 14 | 2026-11-01 | 式に任意の `conditions`（記号どうしの条件：text と比べる式の木）、`unverified`（独立な見本で未検証）、`review_pending`（個別レビュー前）。画面は条件を満たさない値で計算せず、2つの印を出す（stats2-course #118 単位 C・D4）。任意 |
| 15 | 2026-11-01 | 値の表 `$defs.valueTable`。概念に任意の `table_workspace`（値の表の作業台：formula・linear・tables）。値の表の実験室に任意の `contrasts`（誤解を正す例 misconception・指標の限界を示す比較 limit：確かめる主張 claim と1〜2個の表）（stats2-course #119・#118 の反例の方針）。任意 |
| 16 | 2026-11-01 | 式の作業台（workspace）に任意の `linear`（E(aX＋b) の式の番号）。作業台の型（stats2-course #156）で、どの作業台にも変換の欄を出すため。任意 |
| 17 | 2026-11-01 | 二項分布の実験室に任意の `questions`（入口「何を確かめたい？」に並べる問い：id・form〔問いの形。今は prob＝確率の値〕・title・question・set〔n・p〕・events〔eq／ge／le と k。1〜2個〕）と `prob_scale`（確率の値の予想の目盛り）（stats2-course #161）。任意 |
| 18 | 2026-11-02 | 二項分布の実験室の `questions` の form に spread（広がり：to.n）・conv（理論と実測）を足し、prob に任意の free（学習者が結果を選ぶ）。反例の起き方に fatigue（回を追って確率が変わる：drop）（stats2-course #161）。任意 |
| 19 | 2026-11-02 | 二項分布の実験室に任意の `catalog`（テーマ体系：まとまり id・title と、その下の問い id〔教材名:概念-まとまり-番号。stats2:binom-A-01〕・title・finds〔主な発見〕・predict〔何を予想するか〕・operate〔何を操作するか〕・judge〔理解判定〕・open〔開く入口。ないものは作成中〕・concept〔主概念〕・related〔関連概念〕）。サイトの実験室のタブで概念から問いを絞る（stats2-course #163）。任意 |
| 20 | 2026-11-02 | テーマ体系の問いに任意の `retired`（使わない印。重複などで外した問い。id は残し、並べない）。主（concept）に関係（REL-…）も書ける（2つの概念のつながりが主の問い。両端の概念から引く）（stats2-course #169）。任意 |
| 21 | 2026-11-03 | テーマ体系の問いに任意の `apply`（応用の課題：考え方 kind・課題の文 task・答えの求め方 solve〔engine の solveApply の method と条件〕・答えの形 answer〔number は tol、choice は options〕・why）。答えは書かない（画面が求める）（stats2-course #171・#169 の3）。任意 |
| 22 | 2026-11-03 | 二項分布の問いの形に paths（並び・ks）・repeat（くり返し・events・sets）・mean（平均）・var（ばらつき・ps）。応用の求め方に mode・within-band・linear-sum・compare-var（stats2-course #171：作成中の A-03・C-01・D-01・D-02）。任意 |
| 23 | 2026-11-03 | 応用の課題に任意の `walk`（解き方を自分で組み立てる：課題の文の区切り segs〔key：q＝求めるもの・数〕・数の意味の選び肢 tags〔記号 sym・solve のどの値か of・正解の番号 ans・間違えたときの言葉 ng〕・意味の確かめ meaning・2段目から最後の1つ前の段 steps〔quiz か slots〕・確かめる段の言葉 check）。段の題名とまとめ・数の値・合わせる先は書かない（engine が作る）（stats2-course #181）。任意 |
| 24 | 2026-11-03 | 応用の課題の `walk` を、思考の段と操作の部品の形に置き換える（segments〔role〕・info〔word・sym・of〕・formulas〔engine の公式 ref と bind。前の公式の id で導いた値を運ぶ〕・steps〔kind：ask・unit・event・info・relate・formula・build・probe、mark・collect・choose・rowQuiz〕）。rev23 の形は教材の3問だけが使っていて、同じ PR で置き換える（stats2-course #181）。任意 |
| 25 | 2026-11-04 | 概念に任意の `gist`（つまり：日常の言葉で1〜2文）・`question`（この概念で考える問い）・`chart`（概要の図：分布の棒をその場で描く設定 kind・n・p・note。数は engine から）（stats2-course #188 R1c：概念のページを実験室と同じ質に）。任意 |
