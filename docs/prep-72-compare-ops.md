# #72 案 A の設計の下書き（比べる式を formulaNode の op にする）

2026-11-22 に、11/30 のあとの実装に向けて、knowledge-net の main と教材の原本を読んで作った。原本・型・engine は変えていない。

**結論（渡辺さん 2026-11-26）**：3 の B1〜B3 は推奨どおりに決まった（2式に分ける・今は等式だけ開く・値は真偽の 1／0。docs/decisions-1130.md）。


- 決定（渡辺さん 2026-11-21）：比べる式の型は案 A。比べる演算を formulaNode の op に足す。範囲は le・lt を3つ以上の引数で連ねる。「1式＝1つの等式の連なり」を「1つの関係（＝・≦・＜）の連なり」に広げる。lim は大数の法則・一致性を式の木にする段で足す。
- 実装の時期：11/30 のあと、#532 B・C と同じ段（渡辺さん 2026-11-21）。
- 読む製本：② 式と記号（比べる式の書き方は ② に足す。正本は ②）

## 1. 今の形と、変える所

| 場所 | 今 | 変える所 |
| --- | --- | --- |
| 型 kn-schema-v2.json の formulaNode | op の enum は eq・add・…・fn。比べる式は fn の名前（gt・ge・lt・le・between） | op に lt・le・gt・ge を足す（2つ以上の引数。左から読む順）。説明に連ね方を書く。x-revision 8 → 9。任意の値を足すだけなので v2 のまま（knowledge-net 守ること 2） |
| engine types.ts | `Op` の型。COMMON_FNS に gt・ge・lt・le・between | `Op` に4つを足す。COMMON_FNS から5つを外す（読み替えの期間のあと） |
| engine tex.ts | fn の case で `a>b`・`a\le b`・`a\le b\le c` を作る。eq の case で `a=b=…` | op の case にする。eq と同じ連ね方（引数の間に記号を置く）。括弧は関係の強さ（いちばん弱い）で決める |
| engine evaluate.ts | BUILTIN に比べる関数。**between は (x, a, b) と読む**（tex は (a, x, b)。#72 の 2026-11-21 のコメントの食い違い） | op の比べるは「隣どうしが全部成り立てば 1、どれか崩れれば 0」。引数の順は左から（a≦X≦b なら a≦X かつ X≦b）。食い違いは型の上でなくなる |
| engine validate.ts | eq・sub は引数2つ以上。fn の名前は記号か COMMON_FNS | 比べる op も引数2つ以上 |
| engine open.ts・parts.ts・domain.ts | 一番上が eq の式だけ、左辺と右辺に分けて開く・部品にする | 一番上が「関係の連なり」の式も同じに扱うか、eq だけにするかを決める（下の 3 の 2） |
| ui Formula.tsx | 一番上が eq なら左辺・右辺に分けて出す | 3 の 2 に合わせる |
| 教材 terms.yaml | F-expo-surv：P(gt(X, x))。F-pdf-interval：P(between(a, X, b)) | P(gt(X, x)) → P({op: gt, args: [X, x]})。between → {op: le, args: [a, X, b]} |
| 教材 formula-contracts.yaml | conditions の木 3つ（le・lt などの fn） | op に書き直す |
| 教材 build | formula_tex.mjs は写しを読むだけ。formulas.py の fingerprint は木を含む | 2式と、契約の条件を変えた式の fingerprint が変わる → 式のレビューのやり直し（独立なレビュー） |
| 決まりの文 | 教材の CLAUDE.md・docs/authoring.md「1式＝1つの等式の連なり」 | 「1つの関係（＝・≦・＜）の連なり」に直す。② に比べる式の書き方を足す |

ProbQ.tsx の `op: "eq" | "ge" | "le"` は事象の選び方の型（実験室の問い）で、式の木とは別。変えない。

## 2. 公開の順（画面を先に）

1. knowledge-net：型（x-revision 9）・engine・画面を1つの PR で直す。
   - 読む側は、古い fn の比べる（gt・between）も読めるまま残す（読み替えの期間）。
   - 画面を公開する。
2. stats2-course：sync_schema で型と engine の写しを取り込む。2式と契約の木を op に書き直す。
   - 式のレビューをやり直す。
   - 公開する（build/screen_check.py が、画面の型の改訂を見て止める）。
3. knowledge-net：古い fn の比べるを COMMON_FNS から外す。
   - 教材の式の見本（math-lab の test/fixtures）に古い形が残っていないことを、テストで止める。

## 3. 決めること

1. **関係が混ざる連なり**：チェビシェフ「P(｜X−μ｜≧kσ) ≦ σ²/(kσ)² ＝ 1/k²」は ≦ と ＝ が混ざる。
   - 案 a：op を1つの関係にし、混ざる式は2式に分ける（「≦ σ²/(kσ)²」と「σ²/(kσ)²＝1/k²」）。「1式＝1つの関係の連なり」の決まりに合う。
   - 案 b：`{op: "rel", rels: ["le", "eq"], args: [A, B, C]}` のように、隣どうしの関係を並べて持つ。1式で書けるが、型が1つ増える。
   - おすすめは案 a。決まり（1式＝1つの関係の連なり）をそのまま守れ、型も増えない。
2. **開く・部品にするのを、等式だけにするか**：今は一番上が eq の式だけを左辺・右辺に分ける（作業台の主役の式、Formula.tsx の左辺）。
   - 不等式の式（チェビシェフの上限・r の範囲）で、右辺を開く・部品にする必要は、今の教材にはない。
   - 案：まず eq だけのままにし、不等式の式は一番上を分けずに出す。要る式が出てから広げる。
3. **比べるの値**：evaluate で「成り立てば 1・成り立たなければ 0」を返すのは今の fn と同じ。
   - 一番上が不等式の式の「値」は何か（今の eq は最後の引数の値）。
   - 案：一番上が比べるなら、成り立つかの 0・1 を返す。読み戻しのテスト（TeX を読み戻した値が木の値と同じ）は、比べるの式では「真偽が同じ」で確かめる。

## 4. テスト（何を確かめるか・想定する故障）

knowledge-net と教材の「テストの有効性と最小十分性」に合わせ、重ねない。

| テスト | 確かめる対象 | 想定する故障 | 見つけ方 | わざと誤りを入れて落ちるか |
| --- | --- | --- | --- | --- |
| 範囲の引数の順 | le(a, X, b) の値と TeX | 今の between の食い違い（TeX は a≦X≦b、値は X≦a≦b） | a＜X＜b・X＜a・b＜X の3点で、値が 1・0・0 かつ TeX が `a\le X\le b` | evaluate の引数の順を (x, a, b) に戻すと落ちる |
| 読み戻し（性質） | 比べる op の TeX を読み戻した真偽が、木の真偽と同じ | 記号の向き（≦ と ≧）の取り違え、`\le` と `<` の取り違え | fast-check で数を入れて、両方の真偽を比べる（今の eq の読み戻しのテストに足す） | tex の ge を `\le` にすると落ちる |
| 括弧 | P(X＞x) の中の比べると、外の演算の括弧 | 関係の強さの決め違いで `P(X>x)` が `P((X>x))` や `X>x+1` の取り違えになる | 代表の木（gt の中に add、add の中に gt）で TeX を固定の文字列と比べる | 関係の強さを ATOM にすると落ちる |
| validate | 比べる op の引数が1つ | 引数1つの比べるが通る | validate が理由つきで止める | 引数の数の検査を外すと落ちる |
| 型 | 教材の公開データが新しい型で通る | 型の enum に足し忘れ | 教材の check_all（Ajv で型を通す）。新しいテストは足さない | — |

教材の側は、新しいテストを足さない。既存の止めで足りる。

- formula_tex の写しの一致（sync-lock）
- 式のレビューの fingerprint
- 式の見本が KaTeX で読めること（math-lab の stats2-formulas.json）

## 5. 見積もり（大きさ）

- knowledge-net：
  - 型 1行（enum）と説明
  - engine 5ファイル（types・tex・evaluate・validate・open/parts は 3 の 2 しだい）
  - テスト 4つ
  - 画面は Formula.tsx の左辺の扱いだけ
- 教材：
  - terms.yaml 2式・formula-contracts.yaml 3か所の木の書き直し
  - 式のレビュー2〜5式（独立なレビュー）
  - CLAUDE.md・authoring.md・② の文
- 中くらい（#532 B・C より小さい）。#532 C と同じ PR にはしない（式の型と概念の条件は別の変更。数学の意味の変更と書き方の変更を混ぜない）。
