#!/usr/bin/env python3
"""独立な見本（オラクル）の試作（stats2-course #118。隔離した試作で、build・CI は使わない）。

代表の5つ（二項分布・期待値・分散・標準化・回帰）の見本の値を、math-lab の engine とも教材の式の木とも別に、
Python の標準ライブラリ（math・fractions・itertools）だけで求め、生成の条件と誤差の決まりを添えて JSON に書く。

独立にするための決まり
- 教材の式（content/terms.yaml の tex・tree）を読まない。式を評価しない。定義（数え上げ・期待値の和）から求める
  例：二項分布の確率は ₙCₖpᵏ(1−p)ⁿ⁻ᵏ の式ではなく、n 回の成功・失敗の並び 2ⁿ 通りを数え上げて足す
- 有理数で閉じる値は Fraction で正確に求め、"分子/分母" の文字列と浮動小数の両方を書く
- 乱数を使わない（入力は下の表で固定）。同じ版の script なら出力は1バイトも変わらない（--check で確かめる）

使い方
  python3 research/oracle/oracle.py          # research/oracle/reference.json を書き直す
  python3 research/oracle/oracle.py --check  # 書き直さず、今のファイルと一致するかだけ確かめる（不一致なら終了コード 1）
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from fractions import Fraction as F
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "reference.json"
FORMAT = "oracle-prototype/0"

# 誤差の決まり（README の「誤差の決まり」と同じ）。exact は有理数で正確な値、derived は √ などで無理数になる値
TOLERANCE = {
    "exact": {"rel": 1e-12, "abs": 1e-15, "note": "Fraction の正確な値。比べる側の浮動小数の丸めだけを許す"},
    "derived": {"rel": 1e-12, "abs": 1e-12, "note": "√ を1回通した値（σ・z）。math.sqrt の丸め（0.5 ulp）と比べる側の丸めを許す"},
    "sum": {"rel": 0.0, "abs": 1e-12, "note": "和が1・平均0など、正確に決まる値を浮動小数で足した結果（項は n+1 ≦ 41 個）"},
}


def frac(x: F) -> dict:
    return {"exact": f"{x.numerator}/{x.denominator}", "float": float(x)}


def flt(x: float) -> dict:
    return {"float": x}


# ---------- 1. 二項分布：n 回の並びを数え上げる ----------
BINOM_INPUTS = [
    (1, F(0)), (1, F(1)), (1, F(1, 2)),
    (4, F(1, 4)), (5, F(1, 2)), (6, F(1, 3)),
    (10, F(3, 10)), (10, F(0)), (10, F(1)),
    (12, F(2, 3)),
]


def binom_by_enumeration(n: int, p: F) -> list[F]:
    """n 回の成功(1)・失敗(0)の並びを全部つくり、成功の数ごとに並びの確率を足す（ₙCₖ の式を使わない）。"""
    pmf = [F(0)] * (n + 1)
    for seq in itertools.product((0, 1), repeat=n):
        k = sum(seq)
        pr = F(1)
        for s in seq:
            pr *= p if s else (1 - p)
        pmf[k] += pr
    return pmf


def binom_cases() -> list[dict]:
    out = []
    for n, p in BINOM_INPUTS:
        pmf = binom_by_enumeration(n, p)
        total = sum(pmf)
        mean = sum(k * q for k, q in enumerate(pmf))
        var = sum((k - mean) ** 2 * q for k, q in enumerate(pmf))
        assert total == 1, (n, p)
        # 見本どうしの照らし合わせ（独立な2つ目の求め方：math.comb。ここは試作の自己点検で、見本の値は数え上げのほう）
        assert all(pmf[k] == math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(n + 1)), (n, p)
        out.append({
            "id": f"binom-n{n}-p{p.numerator}_{p.denominator}",
            "formula_ids": ["TERM-binom#0", "TERM-binom#1", "TERM-binom#2"],
            "representative": "二項分布",
            "method": "n 回の並び 2^n 通りを数え上げ、成功の数ごとに並びの確率を足す（式を使わない）",
            "inputs": {"n": n, "p": frac(p)},
            "values": {
                "pmf": [frac(q) for q in pmf],
                "sum": frac(total),
                "mean_by_definition": frac(mean),
                "var_by_definition": frac(var),
            },
            "properties": {"正規化": "sum = 1", "非負": "pmf[k] ≥ 0", "同値": "mean = np・var = np(1−p)（式の右辺と照らす）"},
            "tolerance": {"pmf": "exact", "sum": "sum", "mean_by_definition": "exact", "var_by_definition": "exact"},
        })
    return out


# ---------- 2〜4. 値の表：期待値・分散・標準化 ----------
TABLES = [
    {"id": "die", "note": "さいころ（1〜6 が同じ重み）", "rows": [(x, 1) for x in range(1, 7)]},
    {"id": "skew", "note": "偏った表（負の値と重みの違いを含む）", "rows": [(-2, 1), (0, 3), (1, 4), (5, 2)]},
    {"id": "two-point", "note": "2点（0 と 10 が 3:1）", "rows": [(0, 3), (10, 1)]},
]
LINEAR = [(F(2), F(3)), (F(-1), F(0)), (F(1, 2), F(-4)), (F(0), F(7))]   # aX+b の (a, b)。a=0 は分散が0になる端


def dist(rows: list[tuple[int, int]]) -> list[tuple[F, F]]:
    w = sum(r[1] for r in rows)
    return [(F(x), F(c, w)) for x, c in rows]


def E(d: list[tuple[F, F]], g=lambda x: x) -> F:
    return sum((g(x) * p for x, p in d), F(0))


def table_cases() -> list[dict]:
    out = []
    for t in TABLES:
        d = dist(t["rows"])
        assert sum(p for _, p in d) == 1
        mu = E(d)
        var_def = E(d, lambda x: (x - mu) ** 2)            # V(X)＝E[(X−μ)²]
        var_moment = E(d, lambda x: x * x) - mu**2         # ＝E(X²)−{E(X)}²
        assert var_def == var_moment
        lin = []
        for a, b in LINEAR:
            dy = [(a * x + b, p) for x, p in d]                # 表の値を aX+b に置き換えた別の表（式 E(aX+b)＝aE(X)+b を使わない）
            ey = E(dy)
            vy = E(dy, lambda y: (y - ey) ** 2)
            lin.append({
                "a": frac(a), "b": frac(b),
                "E_by_table": frac(ey), "V_by_table": frac(vy),
                "mutants": {   # わざと入れた誤り：見本と食い違うことを確かめる（test-plan.md の M6）
                    "V_missing_square": frac(a * var_def),          # a²V(X) を aV(X) と書いた
                    "V_keeps_b": frac(a * a * var_def + b),        # b を分散に残した
                },
            })
        # 標準化：σ は √ なので浮動小数。E(Z)・V(Z) は σ² を使って正確に出せる
        std = None
        if var_def > 0:
            sigma = math.sqrt(var_def)
            ez_num = E(d, lambda x: x - mu)                      # E(Z)＝E(X−μ)/σ。分子が正確に0
            vz = E(d, lambda x: (x - mu) ** 2) / var_def          # V(Z)＝E[(X−μ)²]/σ²
            std = {
                "sigma": flt(sigma),
                "z": [{"x": frac(x), "z": flt(float(x - mu) / sigma)} for x, _ in d],
                "E_Z_numerator": frac(ez_num),
                "V_Z": frac(vz),
                "mutants": {"V_Z_divided_by_sigma_not_squared": flt(float(var_def) / sigma)},   # σ² ではなく σ で割った
            }
        out.append({
            "id": f"table-{t['id']}",
            "formula_ids": ["TERM-expect#0", "TERM-expect#1", "TERM-expect#2", "TERM-var#0", "TERM-var#1", "TERM-std#0", "TERM-std#1", "TERM-std#2"],
            "representative": "期待値・分散・標準化",
            "method": "値の表から定義の和（Σ x p(x)・Σ (x−μ)² p(x)）で求める。aX+b は表の値を置き換えた別の表で求める（線形の式を使わない）",
            "note": t["note"],
            "inputs": {"rows": [{"x": x, "weight": c} for x, c in t["rows"]]},
            "values": {
                "mu": frac(mu),
                "var_by_definition": frac(var_def),
                "var_by_moments": frac(var_moment),
                "linear": lin,
                "standardize": std,
            },
            "properties": {
                "同値": "var_by_definition = var_by_moments（V(X) の2つの形）",
                "線形": "E_by_table = aμ+b",
                "不変": "V_by_table = a²V(X)（b によらない）",
                "非負": "V ≥ 0",
                "正規化": "E(Z)=0・V(Z)=1",
            },
            "tolerance": {"mu": "exact", "var_by_definition": "exact", "var_by_moments": "exact", "linear": "exact", "sigma": "derived", "z": "derived", "V_Z": "exact"},
        })
    return out


# ---------- 5. 回帰（単回帰の最小二乗） ----------
REG_DATA = [
    {"id": "tiny", "x": [1, 2, 3, 4, 5], "y": [2, 4, 5, 4, 5]},
    {"id": "exact-line", "x": [0, 1, 2, 3], "y": [1, 3, 5, 7]},
    {"id": "negative", "x": [-2, -1, 0, 1, 2, 3], "y": [7, 4, 4, 1, 0, -2]},
]


def ols(xs: list[F], ys: list[F]) -> dict | None:
    """残差の2乗の和を最小にする直線 y＝b0＋b1 x を、正規方程式を解いて求める（Sxx＝0 なら決まらない）。"""
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx, sxy = sum(x * x for x in xs), sum(x * y for x, y in zip(xs, ys))
    det = n * sxx - sx * sx                       # 正規方程式 [[n, Σx],[Σx, Σx²]] の行列式＝n·Sxx
    if det == 0:
        return None
    b0 = (sy * sxx - sx * sxy) / det
    b1 = (n * sxy - sx * sy) / det
    return {"b0": b0, "b1": b1}


def reg_cases() -> list[dict]:
    out = []
    for r in REG_DATA:
        xs, ys = [F(v) for v in r["x"]], [F(v) for v in r["y"]]
        n = len(xs)
        fit = ols(xs, ys)
        assert fit is not None
        b0, b1 = fit["b0"], fit["b1"]
        xbar, ybar = sum(xs) / n, sum(ys) / n
        res = [y - (b0 + b1 * x) for x, y in zip(xs, ys)]
        sst = sum((y - ybar) ** 2 for y in ys)
        sse = sum(e * e for e in res)
        sxx = sum((x - xbar) ** 2 for x in xs)
        sxy = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys))
        r2 = 1 - sse / sst if sst else None
        r_sq = sxy * sxy / (sxx * sst) if sst else None   # 相関係数の2乗（別の求め方）
        assert r2 == r_sq
        # 最小であることの確かめ：b0・b1 を少し動かすと残差の2乗の和は増える（試作の自己点検）
        for d0, d1 in ((F(1, 100), 0), (0, F(1, 100)), (F(-1, 100), F(1, 100))):
            assert sum((y - (b0 + d0 + (b1 + d1) * x)) ** 2 for x, y in zip(xs, ys)) > sse
        out.append({
            "id": f"ols-{r['id']}",
            "formula_ids": [],
            "formula_ids_note": "教材に回帰の式の原本がまだない（TERM-ols・TERM-regcoef・TERM-slr・TERM-resid・TERM-r2 は骨格）。式を足したら ID を書く",
            "representative": "回帰",
            "method": "正規方程式を Fraction で解く（偏差の積和 Sxy/Sxx の式は使わない）。決定係数は 1−SSE/SST と相関係数の2乗の2通りで照らす",
            "inputs": {"x": r["x"], "y": r["y"]},
            "values": {
                "b0": frac(b0), "b1": frac(b1),
                "residual_sum": frac(sum(res)),
                "residual_dot_x": frac(sum(e * x for e, x in zip(res, xs))),
                "sse": frac(sse), "sst": frac(sst),
                "r2": frac(r2) if r2 is not None else None,
                "line_through_means": frac(b0 + b1 * xbar - ybar),
                "mutants": {"b1_swapped_xy": frac(sxy / sst) if sst else None},   # x と y を取り違えた傾き Sxy/Syy
            },
            "properties": {"同値": "r2 = 1−SSE/SST = r²", "正規化": "残差の和 0・残差と x の積和 0", "有界": "0 ≦ r2 ≦ 1", "再現": "直線は (x̄, ȳ) を通る"},
            "tolerance": {"*": "exact"},
        })
    return out


# ---------- 前提が崩れる入力（計算せず、理由を言うべきもの） ----------
def precondition_cases() -> list[dict]:
    degenerate = dist([(4, 1)])          # 1点だけの表：σ＝0
    assert E(degenerate, lambda x: (x - E(degenerate)) ** 2) == 0
    assert ols([F(2), F(2), F(2)], [F(1), F(2), F(3)]) is None
    return [
        {"id": "std-sigma-zero", "formula_ids": ["TERM-std#0"], "inputs": {"rows": [{"x": 4, "weight": 1}]},
         "expect": "計算しない", "reason": "σ＝0（標準偏差が0でない、が崩れる）", "domain_ref": "TERM-std#0 の sigma の domain（min 0・minOpen）"},
        {"id": "binom-p-out", "formula_ids": ["TERM-binom#0"], "inputs": {"n": 5, "k": 2, "p": 1.5},
         "expect": "計算しない", "reason": "p は 0以上1以下", "domain_ref": "TERM-binom#0 の p の domain"},
        {"id": "binom-k-over-n", "formula_ids": ["TERM-binom#0"], "inputs": {"n": 5, "k": 10, "p": 0.5},
         "expect": "計算しない", "reason": "k は 0以上 n 以下の整数", "domain_ref": "TERM-binom#0 の k の domain（max: n）"},
        {"id": "binom-k-noninteger", "formula_ids": ["TERM-binom#0"], "inputs": {"n": 5, "k": 2.5, "p": 0.5},
         "expect": "計算しない", "reason": "k は整数", "domain_ref": "TERM-binom#0 の k の domain（integer）"},
        {"id": "ols-sxx-zero", "formula_ids": [], "inputs": {"x": [2, 2, 2], "y": [1, 2, 3]},
         "expect": "計算しない", "reason": "x のばらつきが0（傾きが決まらない）", "domain_ref": "まだない（回帰の式と条件が原本にない）"},
    ]


def build() -> dict:
    src = Path(__file__).read_bytes()
    return {
        "format": FORMAT,
        "status": "試作（隔離）。build・CI・math-lab のテストはまだ読まない",
        "generated_by": {
            "script": "research/oracle/oracle.py",
            "script_sha256": hashlib.sha256(src).hexdigest(),
            "libraries": ["math", "fractions", "itertools"],
            "python_min": "3.10",
            "random": "使わない（入力は固定の表）",
            "independence": "教材の式（tex・tree）と math-lab の engine を読まない。定義（数え上げ・期待値の和・正規方程式）から求める",
        },
        "formula_id_scheme": "仮の式 ID：<概念ID>#<式の番号>（terms.yaml の formulas の並び。README 参照。正式な形はフェーズ0で決める）",
        "tolerance": TOLERANCE,
        "cases": binom_cases() + table_cases() + reg_cases(),
        "preconditions": precondition_cases(),
    }


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    text = dump(build())
    if "--check" in argv:
        now = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if now != text:
            print("❌ reference.json が script と食い違う（python3 research/oracle/oracle.py で書き直す）")
            return 1
        print("✅ reference.json は script と一致")
        return 0
    OUT.write_text(text, encoding="utf-8")
    d = json.loads(text)
    print(f"書いた：{OUT.relative_to(HERE.parent.parent)}（見本 {len(d['cases'])} 件・前提の崩れ {len(d['preconditions'])} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
