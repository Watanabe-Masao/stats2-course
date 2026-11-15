"""解説付き再生（#90）：場面の版の tour（段階データ）から、ラボの再生・段ごとの静止図・照合する数を作る。

同じ段階データから3つを作る：
  図で解説      段ごとの静止図（build が SVG を作る。ネットワーク・Notion で見える）
  アニメで解説  ラボの再生（labkit の tour。前へ／再生／次へ・文の強調・注目する場所）
  自分で触る    同じラボを自由に動かし、「解説に戻る」で段の状態に戻す

段の状態は、前の段の終わりの状態に set を重ね、frames を順に重ねたもの。値は補間しない（frames に書いた値だけを出す）。
静止図とラボは、棒の範囲（kmax）と丸め（decimals）を tour から共有する。照合テスト（tools/test_labs.js）が、
段と frame ごとに、ラボの計算値と静止図の数を比べる。
"""
from __future__ import annotations

import math

TOUR_KEYS = ("kmax", "decimals", "steps")
TSTEP_KEYS = ("title", "text", "set", "frames", "focus", "ms", "gist", "mode")


def states(tour: dict) -> list[dict]:
    """段ごとに {start, frames: [状態…], end}。状態は set と frames を重ねた dict。"""
    out, cur = [], {}
    for s in tour.get("steps") or []:
        if s.get("mode") and s["mode"] != cur.get("mode"):   # 別のモードへ移る段は、値を持ち越さない
            cur = {"mode": s["mode"]}
        start = {**cur, **(s.get("set") or {})}
        frames, st = [], start
        for f in s.get("frames") or []:
            st = {**st, **f}
            frames.append(st)
        end = frames[-1] if frames else start
        out.append({"start": start, "frames": frames, "end": end})
        cur = end
    return out


_GISTS: dict | None = None


def _gists() -> dict:
    """(ラボ, 版) → 関係の gist。relations.yaml は1回だけ読む（版ごとに読み直すと build が数分遅くなっていた。#129）"""
    global _GISTS
    if _GISTS is None:
        from network import load_claims, load_network
        rels, _ = load_network()
        _GISTS = {}
        for r in rels + load_claims():   # 主張のラボの解説も、主張の gist で「つまり」の段を足す（#289）
            for lab in r.get("labs") or []:
                if r.get("gist"):
                    _GISTS.setdefault((lab.get("id"), lab.get("preset")), r["gist"])
    return _GISTS


def with_gist(lid: str, name: str, preset: dict) -> dict:
    """関係の labs からこの版を開くとき、最後に「つまり」の段を足す（文は関係の gist。2か所に書かない。#95）。"""
    if not preset.get("tour"):
        return preset
    gist = _gists().get((lid, name))
    if not gist:
        return preset
    steps = [*preset["tour"]["steps"], {"title": "つまり", "text": f"💡 {gist}", "gist": True}]
    return {**preset, "tour": {**preset["tour"], "steps": steps}}


def plain(text: str) -> str:
    return text.replace("**", "")


# ---- モードごとの「状態 → 照合する数・静止図」。1本広げるごとにここへ足す
# calc(状態, tour) → 数（照合する数は check の key）、figure(数, 状態, tour) → 図の設定（build/figures.py の型）

def _approx(state: dict, tour: dict) -> dict:
    n, lam = state["n"], state["lam"]
    p = lam / n
    kmax, k = tour["kmax"], state.get("k", 0)
    b = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) if i <= n else 0.0 for i in range(kmax + 1)]
    q = [math.exp(-lam) * lam ** i / math.factorial(i) for i in range(kmax + 1)]
    return {"n": n, "p": p, "k": k, "lambda": n * p, "bin": b[k], "poi": q[k], "diff": q[k] - b[k], "bvar": n * p * (1 - p),
            "maxdiff": max(abs(x - y) for x, y in zip(b, q)), "pmf": b, "pmf2": q}


def _approx_fig(x: dict, state: dict, tour: dict) -> dict:
    dec = tour.get("decimals", 3)
    if state.get("only") == "binom":   # 二項だけ（対比で別の分布と並べるとき）
        return {"type": "dist", "family": "binom", "n": x["n"], "p": x["p"], "kmax": tour["kmax"], "decimals": dec,
                "highlight": [x["k"]], "label": f"二項 n＝{x['n']}、p＝{_n(x['p'])}",
                "lines": [f"平均 np＝{_n(round(x['lambda'], dec))}　分散 {_n(round(x['bvar'], dec))}"]}
    return {"type": "dist", "family": "binom", "n": x["n"], "p": x["p"], "kmax": tour["kmax"], "decimals": dec,
            "highlight": [x["k"]], "mark_mean": True,
            "overlay": {"family": "poisson", "lam": state["lam"], "label": f"ポアソン λ＝{_n(state['lam'])}"},
            "label": f"二項 n＝{x['n']}、p＝{_n(x['p'])}", "maxdiff": round(x["maxdiff"], dec),
            "lines": [f"分散　二項 {_n(round(x['bvar'], dec))}　／　ポアソン {_n(state['lam'])}"]}


def _path(state: dict, tour: dict) -> dict:
    n, p = state["n"], state["p"]
    k = min(state.get("k", 0), n)
    path = p ** k * (1 - p) ** (n - k)
    ncr = math.comb(n, k)
    return {"n": n, "p": p, "k": k, "path": path, "ncr": ncr, "pk": ncr * path}


def _path_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "paths", "n": x["n"], "k": x["k"], "p": x["p"], "decimals": tour.get("decimals", 4)}


def _pmf_binom(state: dict, tour: dict) -> dict:
    n, p = state["n"], state["p"]
    k = min(state.get("k", 0), n)
    ps = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    mean, var = n * p, n * p * (1 - p)
    sd = math.sqrt(var)
    phi = lambda i: math.exp(-((i - mean) / sd) ** 2 / 2) / (sd * math.sqrt(2 * math.pi)) if sd > 0 else 0.0  # noqa: E731
    return {"n": n, "p": p, "k": k, "pk": ps[k], "mean": mean, "var": var, "sd": sd,
            "ngap": max(abs(q - phi(i)) for i, q in enumerate(ps))}   # 棒と正規分布の曲線の高さの差の最大


def binom_window(n: int, mean: float, sd: float) -> tuple[int, int]:
    """棒を出す範囲。n が30より大きいときは平均±4標準偏差（ラボの pmf モードと同じ決まり）。"""
    if n <= 30:
        return 0, n
    return max(0, math.floor(mean - 4 * sd)), min(n, math.ceil(mean + 4 * sd))


def _pmf_binom_fig(x: dict, state: dict, tour: dict) -> dict:
    dec = tour.get("decimals", 3)
    lo, hi = binom_window(x["n"], x["mean"], x["sd"])
    return {"type": "dist", "family": "binom", "n": x["n"], "p": x["p"], "kmin": lo, "kmax": hi, "decimals": dec,
            "highlight": [x["k"]] if lo <= x["k"] <= hi else [],
            "overlay": {"family": "normal", "mu": x["mean"], "sigma": x["sd"], "label": "正規分布の曲線"},
            "label": f"二項 n＝{x['n']}、p＝{_n(x['p'])}",
            "lines": [f"np＝{_n(round(x['mean'], dec))}　n(1−p)＝{_n(round(x['n'] * (1 - x['p']), dec))}"],
            "maxdiff": round(x["ngap"], dec), "maxdiff_label": "棒と曲線の差の最大"}


def _geom(state: dict, tour: dict) -> dict:
    p, r = state["p"], state.get("r", 1)
    k = state.get("k", r)
    pk = math.comb(k - 1, r - 1) * p ** r * (1 - p) ** (k - r)
    return {"p": p, "r": r, "k": k, "pk": pk, "mean": r / p, "var": r * (1 - p) / p ** 2}


def _geom_fig(x: dict, state: dict, tour: dict) -> dict:
    dec = tour.get("decimals", 3)
    return {"type": "dist", "family": "geom", "p": x["p"], "r": x["r"], "kmax": tour["kmax"], "decimals": dec,
            "highlight": [x["k"]],
            "label": f"{'幾何' if x['r'] == 1 else '負の二項'} p＝{_n(x['p'])}（{x['r']}回目の当たりまでの回数）",
            "lines": [f"平均 {mean_label(x)}＝{_n(round(x['mean'], dec))} 回　上限なし"]}


def mean_label(x: dict) -> str:
    return "1/p" if x["r"] == 1 else f"r/p＝{x['r']}/{_n(x['p'])}"


def _hyper(state: dict, tour: dict) -> dict:
    N, K, n = state["N"], state["K"], state["n"]
    k = state.get("k", 0)
    pk = (math.comb(K, k) * math.comb(N - K, n - k) / math.comb(N, n)) if 0 <= n - k <= N - K and k <= K else 0.0
    q = K / N
    fpc = (N - n) / (N - 1)
    bvar = n * q * (1 - q)
    return {"N": N, "K": K, "n": n, "k": k, "pk": pk, "mean": n * q, "var": bvar * fpc, "fpc": fpc,
            "binom": math.comb(n, k) * q ** k * (1 - q) ** (n - k), "bvar": bvar}


def _hyper_fig(x: dict, state: dict, tour: dict) -> dict:
    dec = tour.get("decimals", 3)
    return {"type": "dist", "family": "hyper", "N": x["N"], "K": x["K"], "n": x["n"], "kmax": min(x["n"], x["K"]), "decimals": dec,
            "highlight": [x["k"]],
            "overlay": {"family": "binom", "n": x["n"], "p": x["K"] / x["N"], "label": f"二項 p＝{_n(x['K'] / x['N'])}（戻す）"},
            "label": f"超幾何 N＝{x['N']}・K＝{x['K']}・n＝{x['n']}",
            "lines": [f"分散　超幾何 {_n(round(x['var'], dec))}　／　二項 {_n(round(x['bvar'], dec))}（×{_n(round(x['fpc'], dec))}）"]}


def _pois(state: dict, tour: dict) -> dict:
    rate, t, k = state["rate"], state.get("t", 1), state.get("k", 0)
    lam = rate * t
    pk = math.exp(-lam) * lam ** k / math.factorial(k)
    return {"rate": rate, "t": t, "k": k, "lambda": lam, "pk": pk, "p0": math.exp(-lam), "mean": lam, "var": lam}


def _pois_fig(x: dict, state: dict, tour: dict) -> dict:
    dec = tour.get("decimals", 3)
    return {"type": "dist", "family": "poisson", "lam": x["lambda"], "kmax": tour["kmax"], "decimals": dec,
            "highlight": [x["k"]], "label": f"ポアソン λ＝{_n(x['rate'])}×{_n(x['t'])}＝{_n(round(x['lambda'], 6))}",
            "lines": [f"0件の確率 e^(−λ)＝{x['p0']:.{dec}f}"]}


def _joint(state: dict, tour: dict) -> dict:
    q11, q10, q01 = state["p11"] / 100, state["p10"] / 100, state["p01"] / 100
    px, py = q11 + q10, q11 + q01
    return {"p11": q11, "p10": q10, "p01": q01, "p00": 1 - q11 - q10 - q01, "px": px, "py": py, "exy": q11,
            "cov": q11 - px * py, "vx": px * (1 - px)}


def _joint_fig(x: dict, state: dict, tour: dict) -> dict:
    """両方の確率と、それぞれの確率の積（等しければ独立）。共分散の行は、共分散を見せる解説（段の focus に cov がある）だけ
    （事象の排反・独立の解説〔#45 の U10〕で、まだ学んでいない共分散を出さない）"""
    dec = tour.get("decimals", 3)
    pc = lambda v: f"{_n(round(v * 100, 2))}%"  # noqa: E731
    lines = [f"両方 {pc(x['p11'])}　積 {pc(x['px'])}×{pc(x['py'])}＝{pc(x['px'] * x['py'])}"]
    if any(s.get("focus") == "cov" for s in tour.get("steps") or []):
        lines += [f"Cov＝E(XY)−E(X)E(Y)＝{_n(round(x['exy'], dec))}−{_n(round(x['px'], dec))}×{_n(round(x['py'], dec))}＝{_n(round(x['cov'], dec))}",
                  f"V(X)＝{_n(round(x['vx'], dec))}"]
    return {"type": "joint", "p11": x["p11"], "p10": x["p10"], "p01": x["p01"], "lines": lines,
            "names": [state.get("nameX") or "X", state.get("nameY") or "Y"], "events": bool(state.get("events"))}


def _list(state: dict, tour: dict) -> dict:
    """並べて数える（数え方ラボの list。#45 の U09）：順列・組合せ・数える数（ラボの lVals と同じ。r は 4 と n まで）"""
    n = state["n"]
    r = min(state.get("r", 1), n, 4)
    perm = math.perm(n, r)
    comb = math.comb(n, r)
    return {"n": n, "r": r, "role": state.get("role", "なし"), "perm": perm, "comb": comb,
            "count": perm if state.get("role") == "あり" else comb}


def _list_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "arrange", "n": x["n"], "r": x["r"], "role": x["role"]}


def _bayes(state: dict, tour: dict) -> dict:
    """ベイズ（確率ラボの bayes。#45 の U12）：1000 個で数える。旧版のラボの bVals と同じ（total は1回の検査の全確率）"""
    p, se, fp = state["prior"] / 100, state["sens"] / 100, state["fpr"] / 100
    t = 2 if state.get("times") == 2 else 1
    tp, fpn = 1000 * p * se ** t, 1000 * (1 - p) * fp ** t
    return {"prior": p, "sens": se, "fpr": fp, "times": t, "tpn": tp, "fpn": fpn,
            "total": (p * se + (1 - p) * fp) * 100, "post": tp / (tp + fpn) * 100 if tp + fpn else float("nan")}


def _bayes_fig(x: dict, state: dict, tour: dict) -> dict:
    t = x["times"]
    ev = state.get("event") or "検出"
    return {"type": "count_tree", "n": 1000, "prior": x["prior"], "sens": x["sens"] ** t, "fpr": x["fpr"] ** t,
            "name": state.get("name") or "不良", "other": state.get("other") or "良品", "event": ev,
            "hit": f"2回とも{ev}あり" if t == 2 else f"{ev}あり", "miss": "それ以外" if t == 2 else f"{ev}なし",
            "lines": False}


def _clt(state: dict, tour: dict) -> dict:
    """中心極限定理（中心極限定理ラボの clt。#47 の U19）：待ち時間（指数分布・平均5分・標準偏差5分・歪度2）の n 人分の平均。
    ラボの cVals と同じ理論の値（se＝σ÷√n、skew＝|歪度|÷√n）。取り直しの乱数の値（simsd など）は使わない"""
    assert (state.get("shape") or "expo") == "expo", "解説で使える母集団の形は expo だけ（場面 clt が正確な密度を描けるのは指数分布だけ）"
    n = state["n"]
    return {"n": n, "mu": 5.0, "se": 5 / math.sqrt(n), "skew": 2 / math.sqrt(n)}


def _clt_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "dist", "family": "xbar_expo", "mu": 5, "n": x["n"], "unit": "分", "ticks": [0, 25, 5],
            "label": "1人分の値" if x["n"] == 1 else f"{x['n']}人分の平均", "overlay": {"family": "normal", "mu": 5, "sigma": round(x["se"], 4), "label": "同じ平均・幅の正規分布"},
            "lines": [f"X̄ の標準偏差 {_n(round(x['se'], 2))}分　歪度 {_n(round(x['skew'], 2))}"]}


def _t_pdf(t: float, df: int) -> float:
    return math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi) - (df + 1) / 2 * math.log(1 + t * t / df))


def _f_pdf(x: float, a: int, b: int) -> float:
    if x <= 0:
        return 0.0
    return math.exp(0.5 * (a * math.log(a * x) + b * math.log(b) - (a + b) * math.log(a * x + b)) - math.log(x)
                    - (math.lgamma(a / 2) + math.lgamma(b / 2) - math.lgamma((a + b) / 2)))


def _area(f, a: float, b: float, m: int = 4000) -> float:
    h = (b - a) / m
    return sum((1 if i in (0, m) else 4 if i % 2 else 2) * f(a + i * h) for i in range(m + 1)) * h / 3


def _t_cdf(t: float, df: int) -> float:
    return 0.5 + math.copysign(_area(lambda x: _t_pdf(x, df), 0, abs(t)), t)


def _f_cdf(x: float, a: int, b: int) -> float:
    """x＝u² と置いて u の中点則で積分する（a＝1 では 0 の近くで密度が限りなく大きいが、2u·f(u²) は有限）"""
    if x <= 0:
        return 0.0
    m, r = 20000, math.sqrt(x)
    h = r / m
    return sum(2 * u * _f_pdf(u * u, a, b) for u in ((i + 0.5) * h for i in range(m))) * h


def _bisect(cdf, p: float, lo: float, hi: float) -> float:
    for _ in range(80):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if cdf(m) < p else (lo, m)
    return (lo + hi) / 2


def _tdist(state: dict, tour: dict) -> dict:
    """t 分布の点（t・χ²・F ラボの t。#47 の U20）。ラボの値 tcrit・zcrit・diff と同じ（ラボは不完全ベータ関数、ここは数値積分。別の道）"""
    df = int(state["df"])
    two = state.get("side", "two") != "one"
    q = 1 - state.get("alpha", 0.05) / (2 if two else 1)
    tc = _bisect(lambda t: _t_cdf(t, df), q, 0, 50)
    zc = _bisect(lambda z: 0.5 * (1 + math.erf(z / math.sqrt(2))), q, 0, 10)
    return {"df": df, "two": two, "tcrit": tc, "zcrit": zc, "diff": tc - zc}


def _tdist_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "dist", "family": "t", "df": x["df"], "ticks": [-4, 4, 2], "mark_mean": False,
            "shade": [{"outside": [-x["tcrit"], x["tcrit"]] if x["two"] else [-99, x["tcrit"]]}],
            "label": f"t({x['df']})", "overlay": {"family": "normal", "mu": 0, "sigma": 1, "label": "標準正規分布"},
            "lines": [f"両側5%の点　t({x['df']}) {_n(round(x['tcrit'], 3))}　／　正規 {_n(round(x['zcrit'], 3))}"]}


def _fdist(state: dict, tour: dict) -> dict:
    """F 分布（t・χ²・F ラボの f）。ラボの値 F・fcrit・pUp と同じ（別の道：数値積分と二分法）"""
    d1, d2 = int(state["n1"]) - 1, int(state["n2"]) - 1
    F = state["s1"] / state["s2"]
    fc = _bisect(lambda v: _f_cdf(v, d1, d2), 0.95, 0, 500)
    return {"d1": d1, "d2": d2, "F": F, "fcrit": fc, "pUp": 1 - _f_cdf(F, d1, d2)}


def _fdist_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "dist", "family": "f", "d1": x["d1"], "d2": x["d2"], "ticks": [0, 10, 2], "mark_mean": False,
            "shade": [{"outside": [-99, x["fcrit"]]}],
            "label": f"F({x['d1']}, {x['d2']})",
            "lines": [f"上側5%の点 {_n(round(x['fcrit'], 3))}　F＝{_n(round(x['F'], 3))}"]}


def _comp(state: dict, tour: dict) -> dict:
    """推定量を比べる（推定ラボの comp。#47 の U21）：理論の値（ラボの kVals の seMean・seFirst・biasShift と同じ式）"""
    sig, n, b = state["sigma"], int(state["n"]), state.get("b", 0)
    se = sig / math.sqrt(n)
    return {"n": n, "seMean": se, "seFirst": sig, "biasShift": b, "mseShift": se * se + b * b}


def _comp_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "bars", "title": f"n＝{x['n']}：標準誤差（ばらつき）", "decimals": 2,
            "bars": [["標本平均", round(x["seMean"], 2)], ["最初の1個", round(x["seFirst"], 2)]]}


def _vest(state: dict, tour: dict) -> dict:
    """分散の推定量（推定ラボの var）：v の偏り −σ²/n、s² と v の MSE（ラボの vVals と同じ式）"""
    s2, n = state["sigma2"], int(state["n"])
    bias = -s2 / n
    var_s2, var_v = 2 * s2 * s2 / (n - 1), 2 * (n - 1) * s2 * s2 / (n * n)
    return {"n": n, "biasV": bias, "mseS2": var_s2, "mseV": var_v + bias * bias}


def _vest_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "bars", "title": f"n＝{x['n']}：偏りの大きさ", "decimals": 2,
            "bars": [["s²（n−1 で割る）", 0], ["v（n で割る）", round(-x["biasV"], 2)]]}


_ZTABLE = {0.9: 1.645, 0.95: 1.96, 0.99: 2.576}   # 2級の数表の値（信頼区間ラボの ZQ と同じ）


def _cimean(state: dict, tour: dict) -> dict:
    """平均の区間（信頼区間ラボの mean。#47 の U22）：x̄ ± 確率点 × s÷√n（ラボの mVals の se・crit・margin・lo・hi と同じ式。t は数値積分の点で、ラボの不完全ベータ関数とは別の道）"""
    lv, n = float(state.get("level", 0.95)), int(state["n"])
    xb, s = state["xbar"], state["s"]
    se = s / math.sqrt(n)
    crit = _ZTABLE[lv] if state.get("kind", "z") == "z" else _bisect(lambda t: _t_cdf(t, n - 1), 1 - (1 - lv) / 2, 0, 50)
    m = crit * se
    return {"n": n, "level": lv, "xbar": xb, "se": se, "crit": crit, "margin": m, "lo": xb - m, "hi": xb + m}


def _cimean_fig(x: dict, state: dict, tour: dict) -> dict:
    """区間の横の棒と点推定 x̄ の点（ラボの平均の区間と同じ見せ方。x̄ を中心にした曲線は「μ の分布」と読まれるので描かない）"""
    xb, span = x["xbar"], max(x["margin"] * 1.6, x["se"])
    step = 5 if 2 * span > 12 else 2
    lo = math.floor((xb - span) / step) * step
    hi = math.ceil((xb + span) / step) * step
    pct = round(x["level"] * 100)
    return {"type": "ci_bar", "lo": x["lo"], "hi": x["hi"], "center": xb, "ticks": [lo, hi, step],
            "center_label": f"x̄ {_n(xb)}", "label": f"{pct}%信頼区間・n＝{x['n']}",
            "lines": [f"{_n(round(x['lo'], 3))}〜{_n(round(x['hi'], 3))}（誤差幅 {_n(round(x['margin'], 3))}）"]}


def _tq975(df: float) -> float:
    return _bisect(lambda t: _t_cdf(t, df), 0.975, 0, 50)


def _twodiff(state: dict, tour: dict) -> dict:
    """平均の差（2群のラボの diff。#47 の U23）：ラボの dVals と同じ式（ウェルチ：SE＝√(s₁²/n₁＋s₂²/n₂)・近似の自由度、等分散：合わせた分散・n₁＋n₂−2）"""
    x1, s1, n1, x2, s2, n2 = (state[k] for k in ("x1", "s1", "n1", "x2", "s2", "n2"))
    a, b = s1 * s1 / n1, s2 * s2 / n2
    if state.get("method", "welch") == "welch":
        se, df = math.sqrt(a + b), (a + b) ** 2 / (a * a / (n1 - 1) + b * b / (n2 - 1))
    else:
        sp2 = ((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2)
        se, df = math.sqrt(sp2 * (1 / n1 + 1 / n2)), n1 + n2 - 2
    tc = _tq975(df)
    d = x1 - x2
    return {"label": "ウェルチ" if state.get("method", "welch") == "welch" else "等分散", "diff": d, "se": se, "df": df,
            "tcrit": tc, "margin": tc * se, "lo": d - tc * se, "hi": d + tc * se}


def _twopaired(state: dict, tour: dict) -> dict:
    """対応あり（2群のラボの paired）：差の平均の区間 D̄ ± t(n−1)×s_D÷√n（ラボの pVals と同じ式）"""
    d, sd, n = state["dbar"], state["sd"], int(state["n"])
    se, tc = sd / math.sqrt(n), _tq975(n - 1)
    return {"label": "対応あり", "diff": d, "se": se, "df": n - 1, "tcrit": tc, "margin": tc * se, "lo": d - tc * se, "hi": d + tc * se}


def _twoci_fig(x: dict, state: dict, tour: dict) -> dict:
    """差の区間の横の棒（0 の位置に印を付けて、区間が 0 を含むかを読む）"""
    return {"type": "ci_bar", "lo": x["lo"], "hi": x["hi"], "center": x["diff"], "ticks": [-10, 15, 5], "zero": True, "decimals": 2,
            "center_label": f"差 {_n(x['diff'])}", "label": f"{x['label']}の95%信頼区間（自由度 {_n(round(x['df'], 1))}）",
            "lines": [f"{x['lo']:.2f}〜{x['hi']:.2f}（誤差幅 {x['margin']:.2f}）".replace("-", "−")]}


MODES = {
    ("LAB-pois", "approx"): {"calc": _approx, "check": ("lambda", "bin", "poi", "diff", "maxdiff", "bvar"), "figure": _approx_fig},
    ("LAB-binom", "path"): {"calc": _path, "check": ("path", "ncr", "pk"), "figure": _path_fig},
    ("LAB-binom", "pmf"): {"calc": _pmf_binom, "check": ("pk", "mean", "var", "sd", "ngap"), "figure": _pmf_binom_fig},
    ("LAB-pois", "geom"): {"calc": _geom, "check": ("pk", "mean", "var"), "figure": _geom_fig},
    ("LAB-pois", "hyper"): {"calc": _hyper, "check": ("pk", "mean", "var", "binom", "fpc"), "figure": _hyper_fig},
    ("LAB-pois", "pois"): {"calc": _pois, "check": ("pk", "p0", "lambda"), "figure": _pois_fig},
    ("LAB-expect", "joint"): {"calc": _joint, "check": ("px", "py", "exy", "cov", "vx"), "figure": _joint_fig},
    ("LAB-count", "list"): {"calc": _list, "check": ("perm", "comb", "count"), "figure": _list_fig},
    ("LAB-prob", "bayes"): {"calc": _bayes, "check": ("tpn", "fpn", "total", "post"), "figure": _bayes_fig},
    ("LAB-clt", "clt"): {"calc": _clt, "check": ("mu", "se", "skew"), "figure": _clt_fig},
    ("LAB-tcf", "t"): {"calc": _tdist, "check": ("tcrit", "zcrit", "diff"), "figure": _tdist_fig},
    ("LAB-tcf", "f"): {"calc": _fdist, "check": ("F", "fcrit", "pUp"), "figure": _fdist_fig},
    ("LAB-est", "comp"): {"calc": _comp, "check": ("seMean", "seFirst", "biasShift"), "figure": _comp_fig},
    ("LAB-est", "var"): {"calc": _vest, "check": ("biasV", "mseS2", "mseV"), "figure": _vest_fig},
    ("LAB-two", "diff"): {"calc": _twodiff, "check": ("diff", "se", "df", "tcrit", "margin", "lo", "hi"), "figure": _twoci_fig},
    ("LAB-two", "paired"): {"calc": _twopaired, "check": ("se", "df", "tcrit", "margin", "lo", "hi"), "figure": _twoci_fig},
    ("LAB-ci", "mean"): {"calc": _cimean, "check": ("se", "crit", "margin", "lo", "hi"), "figure": _cimean_fig},
}


def numbers(lid: str, mode: str, state: dict, tour: dict) -> dict:
    return MODES[(lid, state.get("mode") or mode)]["calc"](state, tour)


def mode_of(preset: dict, state: dict) -> str:
    return state.get("mode") or preset["mode"]


def expect(lid: str, preset: dict) -> list[list[dict]]:
    """照合する数：段ごとに [始め, frame…] の各状態の数（HTML には入れない）。"""
    out = []
    for st in states(preset["tour"]):
        seq = [st["start"], *st["frames"]]
        out.append([{k: numbers(lid, preset["mode"], s, preset["tour"])[k]
                     for k in MODES[(lid, mode_of(preset, s))]["check"]} for s in seq])
    return out


def figure_specs(course) -> dict[str, dict]:
    """段ごとの静止図（set か frames で状態が変わる段だけ）。図ID は FIG-<ラボ>-<版>-<段>。"""
    out = {}
    for lid, t in course.labs.items():
        for name, p in (t.get("presets") or {}).items():
            tour = p.get("tour")
            if not tour or (lid, p.get("mode")) not in MODES:
                continue
            steps = tour["steps"]
            for i, (s, st) in enumerate(zip(steps, states(tour)), 1):
                if not (s.get("set") or s.get("frames")):
                    continue
                m = MODES[(lid, mode_of(p, st["end"]))]
                spec = m["figure"](numbers(lid, p["mode"], st["end"], tour), st["end"], tour)
                cap = plain(s["text"])   # 説明文だけ（題は本文と重なりやすい。数は図の中にある）
                out[f"FIG-{lid}-{name}-{i}"] = {"spec": spec, "caption": cap, "where": f"{lid}@{name} の段{i}",
                                                 "source": None, "used_by": [f"{lid}@{name}"]}
    return out


def _n(v) -> str:
    r = round(v, 6)
    return str(int(r)) if r == int(r) else str(r)


def validate(where: str, p: dict, mode: dict | None, lid: str, modes: dict | None = None) -> list[str]:
    err = []
    tour = p["tour"]
    if not isinstance(tour, dict):
        return [f"{where}: tour は {{kmax, decimals, steps}}"]
    extra = set(tour) - set(TOUR_KEYS)
    if extra:
        err.append(f"{where}: tour に使えない項目 {sorted(extra)}")
    if not mode:
        err.append(f"{where}: tour を使うときは mode を書く")
    if p.get("predict") or p.get("steps") or p.get("task"):
        err.append(f"{where}: tour（解説付き再生）には predict・steps・task を書かない（説明は各段の text）")
    if (lid, p.get("mode")) not in MODES:
        err.append(f"{where}: tour の静止図と照合の計算がまだない（build/tour.py の MODES に {lid} の {p.get('mode')} を足す）")
    steps = tour.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        return err + [f"{where}: tour.steps は2段以上のリスト"]
    modes = modes or {}
    cur = p.get("mode")
    for i, s in enumerate(steps, 1):
        if s.get("mode"):
            if s["mode"] not in modes:
                err.append(f"{where} の段{i}: mode {s['mode']} はラボにない")
            elif (lid, s["mode"]) not in MODES:
                err.append(f"{where} の段{i}: モード {s['mode']} の静止図と照合の計算がまだない（build/tour.py の MODES）")
            cur = s["mode"]
        allowed = set((modes.get(cur) or mode or {}).get("set", []))
        w = f"{where} の段{i}"
        extra = set(s) - set(TSTEP_KEYS)
        if extra:
            err.append(f"{w}: 使えない項目 {sorted(extra)}")
        if not s.get("text"):
            err.append(f"{w}: text（その段の説明。強調は **…**）がない")
        elif s["text"].count("**") % 2:
            err.append(f"{w}: text の ** が閉じていない")
        for f in [s.get("set") or {}, *(s.get("frames") or [])]:
            bad = set(f) - allowed
            if bad:
                err.append(f"{w}: {sorted(bad)} はモード {cur} の set にない（{sorted(allowed)}）")
        for f in s.get("frames") or []:
            for k, v in f.items():
                if isinstance(v, float) and k in ("n", "N", "K", "k", "r"):
                    err.append(f"{w}: n は整数で書く（値を補間しない）")
    if not err:
        first = states(tour)[0]["start"]
        need = {("LAB-pois", "approx"): {"n", "lam"}, ("LAB-binom", "path"): {"n", "p", "k"}, ("LAB-binom", "pmf"): {"n", "p", "k"},
                ("LAB-pois", "geom"): {"p", "k"}, ("LAB-pois", "hyper"): {"N", "K", "n", "k"},
                ("LAB-pois", "pois"): {"rate", "t", "k"}, ("LAB-expect", "joint"): {"p11", "p10", "p01"},
                ("LAB-count", "list"): {"n", "r", "role"}, ("LAB-prob", "bayes"): {"prior", "sens", "fpr"}}.get((lid, p.get("mode")), set())
        if not need <= set(first):
            err.append(f"{where}: 段1の set に {sorted(need)} を書く（静止図と照合の計算に要る）")
    return err
