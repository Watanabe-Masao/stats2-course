# 独立な見本（オラクル）の試作（#118）

**試作で、隔離している**。build・`build/check_all.sh`・CI（.github/workflows）・math-lab のテストはこのフォルダを読まない。設計は docs/formula-correctness/（README・test-plan.md の 5）。

## 何をするか

代表の5つ（二項分布・期待値・分散・標準化・回帰）の値を、math-lab の engine とも教材の式（content/terms.yaml の tex・tree）とも別に、Python の標準ライブラリ（math・fractions・itertools）だけで求め、`reference.json` に書く。

| 代表 | 求め方（式を使わない） | case id |
| --- | --- | --- |
| 二項分布 | n 回の成功・失敗の並び 2ⁿ 通りを数え上げ、成功の数ごとに足す。平均・分散は定義の和 | binom-* |
| 期待値・分散 | 値の表から Σ x p(x)、Σ (x−μ)² p(x) と E(X²)−μ²。aX+b は表の値を置き換えた別の表で | table-* |
| 標準化 | 上の表で z＝(x−μ)/σ、E(Z) の分子、V(Z)＝E[(X−μ)²]/σ² | table-*.standardize |
| 回帰 | 正規方程式を Fraction で解く。決定係数は 1−SSE/SST と相関係数の2乗の2通り | ols-* |
| 前提の崩れ | σ＝0・p＝1.5・k＞n・k が小数・Sxx＝0 は「計算しない」 | preconditions |

`mutants` は、わざと入れた誤りの値（分散の2乗落ち・σ で割る・x と y の取り違え）。見本と食い違うことを確かめ、test-plan.md の M6 などの検出の実証に使う。

## 使い方

```sh
python3 research/oracle/oracle.py          # reference.json を書き直す
python3 research/oracle/oracle.py --check  # 書き直さず一致だけ確かめる（不一致なら終了コード 1）
```

乱数は使わない。同じ版の script なら出力は1バイトも変わらない（時刻・Python の版は書かない。script の sha256 を書く）。

## 誤差の決まり

| 種類 | 何の値か | 許す幅 | 理由 |
| --- | --- | --- | --- |
| exact | Fraction で正確に求めた値（`exact` は "分子/分母"、`float` はそれを丸めた値） | 相対 1e−12・絶対 1e−15 | 比べる側（engine の浮動小数）の丸めだけを許す |
| derived | √ を1回通した値（σ・z） | 相対 1e−12・絶対 1e−12 | math.sqrt の丸め（0.5 ulp）と比べる側の丸め |
| sum | 和が1・平均0など、正確に決まる値を浮動小数で足した結果 | 絶対 1e−12 | 項は 41 個まで。項が多い（ポアソンの打ち切りなど）ときは別に幅と出所を書く |

- 見本の側は正確な値（`exact`）を正とし、比べる側が `float` と比べる。正確な値どうしで比べられるときは `exact` で比べる。
- 許す幅を広げるときは、理由（どの計算の丸めか）を書く。テストを通すために広げない。
- 乱数の実験（層2）の許す幅（標準誤差の5倍）とは別の決まり。見本は乱数を使わない。

## 独立にするための決まり

- 教材の式を読まない・評価しない。engine のコードを使わない（同じ誤りを共有しない。README の原則 3）。
- 自分の中でも2通りで照らす（二項分布は数え上げと math.comb、分散は2つの形、決定係数は2つの形、最小二乗は少し動かすと残差が増えること）。食い違えば書き出さずに止まる（assert）。

## あとで math-lab のテストへ渡す流れ（統合の 3。今はしない）

1. この試作を build の一部（例 build/oracle.py）に移し、out/ に書き出す。式 ID はフェーズ0で決めた形にする（今は仮の `TERM-binom#0`）。
2. math-lab の packages/engine/test/fixtures/ に写す。写しには元の hash を入れ、教材の check_all がずれで止める（型・tokens の写しと同じ形。test-plan.md の C5）。
3. math-lab のテストは見本を読むだけで、値は engine で計算し、上の誤差の決まりで照らす。

2026-10-31 に、この見本 85 個（二項の確率・平均・分散、値の表の平均、z）を engine の今の値と使い捨ての調べで照らし、最大の差 4.4×10⁻¹⁶ で一致した。
