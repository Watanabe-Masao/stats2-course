"""反例の言い分（effect）を厳密な計算で確かめる（#118 層3、M7）。

実験室の反例の文（「山が広がる」「散らばりが小さくなる」「平均は np のまま」）は、原本の `effect` に向きとして書く。
build は、起き方ごとの成功の回数の分布を **定義から** 分数で求め（閉じた式を使わない：引きずられるは前の結果を状態にした
数え上げ、混ざるは2つの二項分布の半々、戻さずに取るは超幾何）、二項分布の理論（同じ n・p）と比べる。
vary の範囲の全部の n と、p の 0.01 刻み・テーマの p で確かめる（点ではなく範囲。#118 の決まり 1）。

effect の書き方（どちらも任意。書いた向きだけを確かめる）
- mean: same（どこでも np）
- spread: larger / smaller（n≧2 かつ 0＜q＜1 のどこでも、比べる二項分布 B(n, q) の分散より大きい／小さい）。
  n＝1・q＝0・1 は差が出ない所として、別に「同じ」になることを確かめる（端で言い分が外れる起き方を見つける）
- 比べる二項分布の q は p。戻さずに取るだけは箱の当たりの割合（当たり÷全部）にそろえる（#118 の反例の方針 2。画面と同じ）

effect は公開の JSON に出さない（予想の答えになるため。画面は engine の mechanismMoments から求める）。
起き方の決まりは math-lab の engine（lab.ts の drawSet）と同じ：
- urn：箱 total 個（n より小さければ n 個）、当たり success 個（省くと round(p×total)。JS の Math.round と同じ丸め）
- streak：最初は p、成功のあとは p＋carry(1−p)、失敗のあとは p−carry·p
- mix：ずれ幅 d＝min(spread, p, 1−p)。各セットの開始時に p−d か p＋d を等確率で選び、セットの中は同じ確率
"""
from __future__ import annotations

from fractions import Fraction as F
from math import comb, floor


def _frac(x) -> F:
    return F(str(x))


def _binom_all(N: int, q: F) -> list[list[F]]:
    """n＝1〜N の二項分布の確率（1回ずつ足して作る。n ごとにやり直さない）"""
    out, cur = [], [F(1)]
    for _ in range(N):
        cur = [(cur[k] if k < len(cur) else 0) * (1 - q) + (cur[k - 1] * q if k else 0) for k in range(len(cur) + 1)]
        out.append(cur)
    return out


def _streak_all(N: int, p: F, c: F) -> list[list[F]]:
    # 状態（成功の回数 k, 直前の結果）の確率を1回ずつ進め、n 回目ごとに k の分布を書き出す
    state = {(1, 1): p, (0, 0): 1 - p}
    out = []
    for n in range(1, N + 1):
        if n > 1:
            nxt: dict = {}
            for (k, last), pr in state.items():
                q = p + c * (last - p)
                for x, w in ((1, q), (0, 1 - q)):
                    if w:
                        key = (k + x, x)
                        nxt[key] = nxt.get(key, 0) + pr * w
            state = nxt
        pmf = [F(0)] * (n + 1)
        for (k, _), pr in state.items():
            pmf[k] += pr
        out.append(pmf)
    return out


def _urn_pmf(n: int, total: int, success: int) -> list[F]:
    den = comb(total, n)
    return [F(comb(success, k) * comb(total - success, n - k), den) for k in range(n + 1)]


def js_round(x: F) -> int:
    return floor(x + F(1, 2))


def base_ratio(m: dict, n: int, p: F) -> F:
    """比べる二項分布の成功確率。戻さずに取るは箱の当たりの割合 q＝当たり÷全部（丸めで p とずれる。比べる条件をそろえる：#118 の反例の方針 2）"""
    if m["kind"] != "urn":
        return p
    total = max(n, int(m.get("total") or 40))
    return F(int(m["success"]) if m.get("success") is not None else js_round(p * total), total)


def mechanism_all(m: dict, N: int, p: F) -> list[list[F]]:
    """n＝1〜N の、起き方ごとの成功の回数の分布（定義から）"""
    kind = m["kind"]
    if kind == "mix":
        d = max(F(0), min(_frac(m["spread"]), p, 1 - p))
        return [[(x + y) / 2 for x, y in zip(a, b)] for a, b in zip(_binom_all(N, p - d), _binom_all(N, p + d))]
    if kind == "streak":
        return _streak_all(N, p, _frac(m["carry"]))
    if kind == "urn":
        out = []
        for n in range(1, N + 1):
            total = max(n, int(m.get("total") or 40))
            success = int(m["success"]) if m.get("success") is not None else js_round(p * total)
            out.append(_urn_pmf(n, total, success))
        return out
    raise ValueError(f"知らない起き方 {kind}")


def moments(pmf: list[F]) -> tuple[F, F]:
    mean = sum(k * x for k, x in enumerate(pmf))
    return mean, sum((k - mean) ** 2 * x for k, x in enumerate(pmf))


def effect_errors(eid: str, x: dict) -> list[str]:
    """二項分布の実験の反例の effect を、vary の全部の n と p の格子・テーマの p で確かめる。最初に外れた所を1つ返す"""
    err: list[str] = []
    vary = x.get("vary") or {}
    if x.get("model") != "binom" or "n" not in vary:
        return err
    ns = range(int(vary["n"]["min"]), int(vary["n"]["max"]) + 1)
    ps = sorted({F(k, 100) for k in range(0, 101)} | {_frac(t["p"]) for t in x.get("themes") or [] if "p" in t})
    for b in x.get("counterexamples") or []:
        eff, m = b.get("effect"), b.get("mechanism") or {}
        if eff is None:
            err.append(f"{eid}: 反例 {b.get('id')} に effect（平均・散らばりの向き）がない（文の言い分を build が確かめる。#118 層3）")
            continue
        if set(eff) - {"mean", "spread"} or eff.get("mean", "same") != "same" or eff.get("spread", "larger") not in ("larger", "smaller"):
            err.append(f"{eid}: 反例 {b.get('id')} の effect は mean: same・spread: larger か smaller で書く")
            continue
        bad = None
        for p in ps:
            for n, pmf in enumerate(mechanism_all(m, ns.stop - 1, p), start=1):
                if n < ns.start:
                    continue
                mean, var = moments(pmf)
                q = base_ratio(m, n, p)   # 比べる二項分布 B(n, q)
                bv = n * q * (1 - q)
                if eff.get("mean") == "same" and mean != n * q:
                    bad = f"n＝{n}・p＝{float(p):g} で平均 {float(mean):.4g}（二項分布 {float(n * q):.4g}）"
                elif "spread" in eff:
                    want = "same" if (n == 1 or q in (0, 1)) else eff["spread"]   # 差が出ない端（方針 3）
                    got = "same" if var == bv else "larger" if var > bv else "smaller"
                    if got != want:
                        bad = f"n＝{n}・p＝{float(p):g} で分散 {float(var):.4g}（二項分布 {float(bv):.4g}）＝{got}。言い分は {want}"
                if bad:
                    break
            if bad:
                break
        if bad:
            err.append(f"{eid}: 反例 {b.get('id')} の effect が計算と合わない：{bad}")
    return err
