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


def with_gist(lid: str, name: str, preset: dict) -> dict:
    """関係の labs からこの版を開くとき、最後に「つまり」の段を足す（文は関係の gist。2か所に書かない。#95）。"""
    if not preset.get("tour"):
        return preset
    from network import load_network
    rels, _ = load_network()
    gist = next((r["gist"] for r in rels if r.get("gist") and any(
        lab.get("id") == lid and lab.get("preset") == name for lab in r.get("labs") or [])), None)
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
            "highlight": [x["k"]], "label": f"幾何 p＝{_n(x['p'])}（{x['r']}回目の当たりまでの回数）",
            "lines": [f"平均 1/p＝{_n(round(x['mean'], dec))} 回　上限なし"]}


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


MODES = {
    ("LAB-pois", "approx"): {"calc": _approx, "check": ("lambda", "bin", "poi", "diff", "maxdiff", "bvar"), "figure": _approx_fig},
    ("LAB-binom", "path"): {"calc": _path, "check": ("path", "ncr", "pk"), "figure": _path_fig},
    ("LAB-binom", "pmf"): {"calc": _pmf_binom, "check": ("pk", "mean", "var", "sd", "ngap"), "figure": _pmf_binom_fig},
    ("LAB-pois", "geom"): {"calc": _geom, "check": ("pk", "mean", "var"), "figure": _geom_fig},
    ("LAB-pois", "hyper"): {"calc": _hyper, "check": ("pk", "mean", "var", "binom", "fpc"), "figure": _hyper_fig},
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
                ("LAB-pois", "geom"): {"p", "k"}, ("LAB-pois", "hyper"): {"N", "K", "n", "k"}}.get((lid, p.get("mode")), set())
        if not need <= set(first):
            err.append(f"{where}: 段1の set に {sorted(need)} を書く（静止図と照合の計算に要る）")
    return err
