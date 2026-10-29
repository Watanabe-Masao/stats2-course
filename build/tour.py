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
TSTEP_KEYS = ("title", "text", "set", "frames", "focus", "ms")


def states(tour: dict) -> list[dict]:
    """段ごとに {start, frames: [状態…], end}。状態は set と frames を重ねた dict。"""
    out, cur = [], {}
    for s in tour.get("steps") or []:
        start = {**cur, **(s.get("set") or {})}
        frames, st = [], start
        for f in s.get("frames") or []:
            st = {**st, **f}
            frames.append(st)
        end = frames[-1] if frames else start
        out.append({"start": start, "frames": frames, "end": end})
        cur = end
    return out


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
    return {"type": "dist", "family": "binom", "n": x["n"], "p": x["p"], "kmax": tour["kmax"], "decimals": dec,
            "highlight": [x["k"]], "mark_mean": True,
            "overlay": {"family": "poisson", "lam": state["lam"], "label": f"ポアソン λ＝{_n(state['lam'])}"},
            "label": f"二項 n＝{x['n']}、p＝{_n(x['p'])}", "maxdiff": round(x["maxdiff"], dec),
            "vars": [round(x["bvar"], dec), state["lam"]]}   # 分散 二項 np(1−p) ／ ポアソン λ


def _path(state: dict, tour: dict) -> dict:
    n, p = state["n"], state["p"]
    k = min(state.get("k", 0), n)
    path = p ** k * (1 - p) ** (n - k)
    ncr = math.comb(n, k)
    return {"n": n, "p": p, "k": k, "path": path, "ncr": ncr, "pk": ncr * path}


def _path_fig(x: dict, state: dict, tour: dict) -> dict:
    return {"type": "paths", "n": x["n"], "k": x["k"], "p": x["p"], "decimals": tour.get("decimals", 4)}


MODES = {
    ("LAB-pois", "approx"): {"calc": _approx, "check": ("lambda", "bin", "poi", "diff", "maxdiff", "bvar"), "figure": _approx_fig},
    ("LAB-binom", "path"): {"calc": _path, "check": ("path", "ncr", "pk"), "figure": _path_fig},
}


def numbers(lid: str, mode: str, state: dict, tour: dict) -> dict:
    return MODES[(lid, mode)]["calc"](state, tour)


def expect(lid: str, preset: dict) -> list[list[dict]]:
    """照合する数：段ごとに [始め, frame…] の各状態の数（HTML には入れない）。"""
    keys = MODES[(lid, preset["mode"])]["check"]
    out = []
    for st in states(preset["tour"]):
        seq = [st["start"], *st["frames"]]
        out.append([{k: numbers(lid, preset["mode"], s, preset["tour"])[k] for k in keys} for s in seq])
    return out


def figure_specs(course) -> dict[str, dict]:
    """段ごとの静止図（set か frames で状態が変わる段だけ）。図ID は FIG-<ラボ>-<版>-<段>。"""
    out = {}
    for lid, t in course.labs.items():
        for name, p in (t.get("presets") or {}).items():
            tour = p.get("tour")
            m = MODES.get((lid, p.get("mode")))
            if not tour or not m:
                continue
            steps = tour["steps"]
            for i, (s, st) in enumerate(zip(steps, states(tour)), 1):
                if not (s.get("set") or s.get("frames")):
                    continue
                spec = m["figure"](numbers(lid, p["mode"], st["end"], tour), st["end"], tour)
                cap = f"{s.get('title', '')}：{plain(s['text'])}"   # 数は図の中にある（説明文に重ねて書かない）
                out[f"FIG-{lid}-{name}-{i}"] = {"spec": spec, "caption": cap, "where": f"{lid}@{name} の段{i}",
                                                 "source": None, "used_by": [f"{lid}@{name}"]}
    return out


def _n(v) -> str:
    r = round(v, 6)
    return str(int(r)) if r == int(r) else str(r)


def validate(where: str, p: dict, mode: dict | None, lid: str) -> list[str]:
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
    allowed = set((mode or {}).get("set", []))
    for i, s in enumerate(steps, 1):
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
                err.append(f"{w}: {sorted(bad)} はモード {p.get('mode')} の set にない（{sorted(allowed)}）")
        for f in s.get("frames") or []:
            for k, v in f.items():
                if isinstance(v, float) and k == "n":
                    err.append(f"{w}: n は整数で書く（値を補間しない）")
    if not err:
        first = states(tour)[0]["start"]
        need = {("LAB-pois", "approx"): {"n", "lam"}, ("LAB-binom", "path"): {"n", "p", "k"}}.get((lid, p.get("mode")), set())
        if not need <= set(first):
            err.append(f"{where}: 段1の set に {sorted(need)} を書く（静止図と照合の計算に要る）")
    return err
