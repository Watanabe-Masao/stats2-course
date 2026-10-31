# 棚卸し：式の正しさについて今あるもの（2026-10-31）

調べた版：math-lab main `fbfe9fc`、knowledge-net main `5ad07a3`（型 `x-revision` 11）、stats2-course main `be68994`。
math-lab の engine のテストは手元で全部通ることを確かめた（8ファイル・81件）。下の「確かめた」は、そのときに足して消した使い捨ての調べ（コミットしていない）で見た事実。

## 1. math-lab packages/engine（式の木）

| 物 | 場所 | 中身 |
| --- | --- | --- |
| 式の木の型 | src/formula/types.ts | `FormulaNode`（`SymNode`・`NumNode`・`OpNode`）、`Op`（eq〜fn の13）、`SymbolKind`、`Domain`、`FormulaSymbol`（`of`・`domain`・`concept`・`range`）、`FormulaPart`、`COMMON_FNS` |
| 値 | src/formula/evaluate.ts | `evaluate`（eq・∫ は値にしない。Σ・Π は端か `env.domains` で決まれば求める。項は1万まで）、`substitute`、`expand`（1段ずつ。最大100段）、`factorial`・`comb`、`symbolsIn`・`fnsIn` |
| TeX | src/formula/tex.ts | `toTex`（括弧は演算の強さから）、`symbolTex`、`formatNum`。`wrap`・`mark`・`data` で画面の印 |
| 検査 | src/formula/validate.ts | `validateFormula`：葉・関数・動かす記号が symbols にあるか、引数の数、数が有限か |
| 開く・閉じる | src/formula/open.ts | `definitionsFor`、`openSymbol`（関数の引数の結び付け・`of` で属する記号を移す・α 変換）、`applyOpens`、`substituteFree` |
| スコープ | src/formula/scope.ts | `freeSymbols`、`boundSymbols`、`renameBound`、`freshName` |
| 定義域・前提 | src/formula/domain.ts | `inDomain`、`describeDomain`、`checkDomain`、`sliderRange`、`stopReason` |
| かたまり・分布 | src/formula/parts.ts | `nodeAt`、`rhsOf`・`lhsOf`、`distribution` |
| 作業台 | packages/ui/src/Workspace.tsx（ui の側） | engine の `applyOpens`・`distribution`・`sliderRange`・`expand` などを呼ぶ。作業台の計算は engine にはない |

テスト（packages/engine/test/）

| ファイル | 件数 | 式に関わる主なもの |
| --- | --- | --- |
| formula.test.ts | 10 | 「教材の式（stats2-course の35式）」：検査を通る・KaTeX で読める・代表の式の形（7式の TeX を手書きの文字列と比べる）。「性質」：TeX を読み戻した値＝木の値（400回）、展開の最後＝値で段ごとに小さくなる（300回） |
| open.test.ts | 8 | σ・V を開く、印、V(Z) で μ→μ_Z、V(aX+b) で μ→E(aX+b)、定義がなければ開かず理由、閉じる、開けるものは全部 TeX にできる（20か所より多い）。「性質」：開いても値は変わらない（300回） |
| correctness.test.ts | 25 | 1 スコープ（例2・性質1）、2 対応（教材の式を全部開く・μ＝E(X) で開く）、3 定義域（例4）、4 前提（σ＝0・負の分散）、5 式の中身（二項・ポアソン・幾何・超幾何・一様・指数の和1と平均・分散）、Σ・Π の値、値の表の Σ |
| parts.test.ts | 4 | 二項分布のかたまり、かたまりの値の積＝式の値（性質）、分布の和1 |
| test/fixtures/stats2-formulas.json | — | 教材の terms.yaml の式の写し（38式。`concept`・`index` で式を指す）。今は原本と一致（38式とも tree・symbols・tex が同じ）。**写しを作る手順と、ずれを止める検査はない**（手で写している） |

注：issue やテスト名には「35式」とあるが、今の原本と写しは **38式**（U13〜U16 の式に TERM-expect#1 μ＝E(X) などが足された）。

## 2. knowledge-net の型（schema/kn-schema-v1.json、改訂11）

| 物 | 場所 | 中身 |
| --- | --- | --- |
| 式の木 | `$defs.formulaNode` | 葉（sym・num）と演算（op・args・name・var・lower・upper）。演算は13 |
| 式 | `properties.concepts.items.properties.formulas` | `tex`（必須）・`label`・`symbols`・`tree`・`parts`。**式に id はない** |
| 記号 | 同 `symbols.items` | `symbol`・`meaning`（必須）・`range`・`key`・`concept`・`kind`・`of`（改訂7）・`domain`（改訂7：min・max〔数か同じ式の記号の key〕・minOpen・maxOpen・integer・nonzero） |
| 作業台 | 概念の `workspace`（改訂8） | formula・vary・over・mean（式は番号で指す） |
| 画面のテスト | tests/e2e/viewer.spec.ts | 「式の記号を押すと意味が出て…1段ずつ計算できる」「式の記号を定義の式で開き、閉じると戻る」「定義域の外の値は計算せず、理由を知らせる」「V(aX+b) を開くと中の μ は E(aX+b) になり…」「式の作業台…」。数は文字の有無で見ている（engine で計算し直して照らしてはいない） |
| 型のテスト | tests/unit/data.test.ts | 「式の分解の木（改訂3）：見本は合い、知らない演算・葉のない節・記号の種類の誤りを止める」 |

`parts`（式の部品）は型にあるが、記号の `of`・`domain` を検証の契約に使う欄（種類・性質・状態）はまだない。

## 3. stats2-course の build と原本

### 3.1 build が式について止めるもの（build/network.py）

| 検査 | 関数・行 | 止めるもの |
| --- | --- | --- |
| 木の形 | `tree_errors`（`TREE_OPS`・`BUILTIN_FN`） | 知らない演算、symbols にない葉・関数・動かす記号、args のない演算 |
| 記号 | `validate_network` の式の部分 | symbol・meaning がない、`concept` が用語にない |
| of | 同 | `of` が同じ式の確率変数（kind: rv）の key でない |
| domain | 同 | domain を書けない kind（rv・data）に書いた、知らない項目、端の記号が同じ式の値・母数の key でない、min ≦ max でない（数どうしだけ） |
| parts | 同 | path が木の節を指さない |
| workspace | 同 | 主役の式に木がない、vary に domain がない、over に上限のある整数の domain がない |
| 説明の数 | `network_checks`・`run_checks` | 概念の説明に数があるのに `checks`（検算式）がない |

**build が確かめないもの**：tex と tree が同じ式か（CLAUDE.md「#72 で木から TeX を作るまでは…自分で読み合わせる」）、式の値・性質、記号どうしの domain の意味（k ≦ n は書けるが、k ≦ M のように2つ目の上限は書けない）。

### 3.2 教材の式（content/terms.yaml）

- 式のある概念 19（説明のある概念 19 と同じ）、式 **38**。38式とも `tree` がある。`parts` は2式（TERM-comb#0・TERM-binom#0）。
- 記号 151。`kind` 102、`concept` 52、`domain` 34、`range` 33、`of` 7。
- `of` のある記号（7）：TERM-var#0 μ（X）、TERM-sd#0 σ（X）、TERM-std#0 μ・σ（X）、TERM-expect#1 μ（X）、TERM-cov#0 μ_X（X）・μ_Y（Y）。
- `domain` のある式（20）：TERM-comb#0、TERM-fact#0、TERM-sd#0、TERM-std#0、TERM-normal#0、TERM-binom#0〜2、TERM-poisson#0〜1、TERM-geom#0〜2、TERM-negbinom#0、TERM-hyper#0〜1、TERM-expo#0〜3。一様分布（TERM-uniform#0〜2）・分散・共分散・期待値の式には domain がない。
- 代表の5つの式 ID（仮の呼び方 `<概念ID>#<番号>`）：二項分布 TERM-binom#0〜2、期待値 TERM-expect#0〜2、分散 TERM-var#0〜1、標準化 TERM-std#0〜2。**回帰の式は原本にない**（TERM-ols・TERM-regcoef・TERM-slr・TERM-resid・TERM-r2 は骨格＝short だけ）。
- 近似・極限は式ではなく関係（content/relations.yaml の変換）にある：REL-binom-poisson（limit）、REL-binom-normal（approximation）、REL-hyper-binom（limit）、REL-t-normal（limit）、REL-prior-posterior（exact）。

## 4. #109 の項目ごとの状態

| 項目 | 状態 | 実装（証拠） | 今のテストが保証すること | 確かめていないこと |
| --- | --- | --- | --- | --- |
| 記号と確率変数の対応（of） | **一部** | 型（改訂7）、build の検査（of は同じ式の rv）、`openSymbol` の手順1（引数が記号なら μ→μ_Z、式なら定義で開いてから移す）。原本の7記号 | V(Z)→E((Z−μ_Z)²) と μ_Z の意味（open.test.ts）。V(aX+b)→E((aX+b−E(aX+b))²)（open.test.ts・e2e）。定義がなければ開かず理由（open.test.ts）。教材の式を全部開いたとき、新しくできた属する記号の確率変数は式の中にある（correctness.test.ts「対応」） | ・of の**中身が正しいか**（μ に of: Y と書いても build は通る）・of のない μ・σ を開いたとき（正規分布の σ を √V(X) で開くと、式にない確率変数 X が自由な記号として入る：確かめた）・「どの確率変数にも属さない μ が残らない」は正規表現 `aX\+b-\mu` の1つの形だけで見ている・2つの確率変数の関数（Cov(aX, Y)）を開く場合 |
| 変数のスコープ（α 変換） | **実装済み**（範囲は Σ の1種類で確かめた） | scope.ts の4関数、`substituteFree`（縛られた所は置き換えない）、`openSymbol` の手順2（ぶつかる名前を付け替える） | 外の x と Σ の x がぶつからない・引数に同じ名前があっても取り込まれない（例）。開いても元の自由な記号は自由なまま・縛る記号は元の自由な記号と重ならない（性質200回。ただし定義は E(X)＝Σ_x x p(x) の1つだけ）。Σ・Π の値で外の値が中に漏れない（例）・内側で同じ記号を縛る Σ（例） | ・∫（int）を含む定義を開く場合（教材の TERM-pdf#0 は ∫ だが、開く対象の定義にならない）・入れ子の Σ と下端・上端に縛る記号の名前が出る場合・`renameBound` 単体の性質（付け替えても値が同じ）・付け替えた名前（x′）の表示が画面で衝突しないか |
| 定義域（domain） | **一部** | 型（改訂7）、build の検査、domain.ts の `inDomain`・`checkDomain`・`describeDomain`・`sliderRange`。原本の34記号 | p＝1.5・k＝2.5・n＝0、k ≦ n の知らせ、端を含まない・0でない（例）。sliderRange が n に合わせて動く（例）。domain の端の値が range の文に出てくる（原本の全記号）。二項分布の性質テストの入力が domain の中（correctness.test.ts） | ・**記号どうしの条件が1つの端で書けない**：超幾何の k ≦ M・n ≦ N・n−(N−M) ≦ k、一様分布の a＜b（確かめた：N＝2・n＝5 で checkDomain は空、値は NaN。a＝b で空、値は ∞）・幾何分布の p の domain が 0 を含む（p＝0 で checkDomain は空、E＝1/p は ∞：確かめた）・`evaluate` は domain を見ない（守るのは呼ぶ側。今は ui の Formula だけ）・「定義域の中の値だけで同値性を確かめる」は二項分布だけ・確率変数（rv）には domain を書けない（とる値は env.domains で別に渡す） |
| 前提条件 | **一部** | `stopReason`（0 で割る・負の数の平方根・0の負の累乗・対数・組合せ）。原本の `conditions.math`（文） | σ＝0 の標準化で「0 で割ることになる」・負の分散の平方根（correctness.test.ts） | ・前提は**値が有限でなくなってから**気づく形で、宣言した前提（σ≠0・V≥0）と結び付いていない・`conditions.math` は文で、どの記号のどの条件かを機械が読めない・**開いた式の前提＝元の式と定義の式の前提を合わせたもの**は未実装（`openSymbol` は定義の記号の domain を、まだない key のときだけ足す）・p＝1.5 は stopReason ではなく checkDomain が止める（issue の「展開が止まり理由が出る」は domain 側で満たしている） |
| 意味を保つ展開 | **一部** | `openSymbol`・`applyOpens`・`definitionsFor`（＝が続く式のどの辺で開くかを選べる）。数の展開は `expand` | 記号の葉を定義で開いても値が同じ（性質300回。ただし関数・of・Σ のない定義だけ）。展開の最後は値と同じ・段ごとに小さくなる（性質300回）。開いた形の TeX（例） | ・**関数を開いたときの値の同値**（V(aX+b) を開いた式と a²V(X) が同じ値になるか。E・V は分布を決めないと値にならないので、今は形だけを見ている）・＝が続く式の**各辺が同じ値か**（V(X)＝E[(X−μ)²]＝E(X²)−{E(X)}² の2つの右辺。二項分布などの「式の中身」は分布ごとに確かめているが、定義の式そのものの辺どうしは確かめていない）・開いて閉じたら元の木に戻る、の性質（例だけ） |
| μ＝E(X) の定義式 | **実装済み** | 原本 TERM-expect#1（μ の of: X）。`openSymbol` が引数が式のときにこれで μ を開く | 標準化の式の μ を開くと X−E(X)（correctness.test.ts・e2e）。V(aX+b) の中の μ が E(aX+b) になる（open.test.ts・e2e） | ・σ に同じ形の定義（σ＝√V(X) は TERM-sd#0 にある）が of を持つ μ と同じ扱いで選ばれるか（`resolve` は左辺が記号の最初の定義を使う。候補が2つ以上になったときの選び方の決まりがない） |

### 4.1 新しい検証の契約は既存の of・domain をそのまま参照できるか

**できる。作り直さない。** 理由と、足りない所：

- **of**：記号の key → 同じ式の確率変数の key、という形で、契約からは「この式のこの記号はこの確率変数に属する」として参照できる。意味（μ が「期待値」か）は記号の `concept`（TERM-expect）が持つので、契約は of と concept の組を読むだけでよい。足りないのは**データではなく検査**：of の中身の正しさは build も engine も確かめない（個別レビューの観点に入れる。test-plan.md の M2）。正規分布の μ・σ に of がないのは、データの決め（D7）。
- **domain**：1つの記号の範囲（端・整数・0でない・記号を端にする k ≦ n）は、そのまま契約の「成り立つ条件」として参照できる。足りないのは**記号どうしの条件のうち1つの端で書けないもの**（k ≦ M と k ≦ n の両方、a＜b、n ≦ N）。これは domain を作り直さず、契約か型に任意の「組の条件」を足して書く（式の木の比べる式 gt・le・between で書けば、#72 の比べる式の型の決定と一緒に決まる）。
- **前提**：`conditions.math` は文なので、契約からは「概念のこの条件」として番号で参照するまでにとどまる。機械が確かめる前提は domain と組の条件で持ち、文の条件はレビューの対象にする。
- **スコープ**：データの項目はない（木の var の形で決まる）。契約からは engine の関数（`freeSymbols` など）を使う共通テストとして参照する。
