"""問題・例題ごとの図解を、原本に書いた設定（figure:）から SVG で作る。

問題（problems/*.yaml）:   figure: {type: ladder, caption: …, …}   → 図ID FIG-<問題ID>（答えの中に「図で確かめる」）
単元（units/*/unit.yaml）: figures: [{id: FIG-U03-exA, caption: …, spec: {type: …}}] → 本文で {{fig:FIG-U03-exA}}

図の中の数は、問題文・答え（単元の図は本文）にある数だけを使う（validate_figures が調べる）。
計算で出す数（合計・比・係数）は、図を作るときにこの中で計算する。
幅360の図にする（iPhone の Notion で、文字が12px前後に見える）。
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from model import ROOT, Course, numbers

sys.path.insert(0, str(ROOT / "tools" / "figure-src"))
from svgkit import BLUE, GRID, INK, INK2, LIGHT, ORANGE, RED, Svg, esc  # noqa: E402

OUT = ROOT / "out" / "fig"
W = 360
SCALES = ["名義", "順序", "間隔", "比例"]
OPS = ["＝ ≠", "＜ ＞", "＋ −", "× ÷"]
WARM, WARM_BG = ORANGE, "#fdf0e9"
NO_HEAD = "、。，．）」』】〕・ー々…）)"
NO_TAIL = "（「『【〔("


# ---- 文字の折り返し（全角1字＝1em、半角＝0.55em で幅を見積もる） ----
def _w(ch: str) -> float:
    return 0.55 if ord(ch) < 0x2000 else 1.0


def wrap(text: str, width_px: float, size: float) -> list[str]:
    import re as _re
    lines, cur, cw = [], "", 0.0
    # 半角の英数字の並び（47.75、Q₁ など）は途中で折らない
    for tok in _re.findall(r"[0-9A-Za-z.,%₀-₉]+|\n|.", str(text)):
        if tok == "\n":
            lines.append(cur); cur, cw = "", 0.0; continue
        tw = sum(_w(ch) for ch in tok) * size
        if cw + tw > width_px and cur:
            lines.append(cur); cur, cw = "", 0.0
        cur += tok; cw += tw
    if cur:
        lines.append(cur)
    # 行頭に来てはいけない字（句読点・閉じ括弧）は前の行へ、行末の開き括弧は次の行へ
    for i in range(1, len(lines)):
        while lines[i] and lines[i][0] in NO_HEAD and lines[i - 1]:
            lines[i - 1] += lines[i][0]; lines[i] = lines[i][1:]
        while lines[i - 1] and lines[i - 1][-1] in NO_TAIL:
            lines[i] = lines[i - 1][-1] + lines[i]; lines[i - 1] = lines[i - 1][:-1]
    return [ln for ln in lines if ln] or [""]


class Canvas(Svg):
    """高さを後で決める Svg。"""

    def __init__(self):
        super().__init__(W, 10)
        self.parts = []

    def para(self, x, y, text, width, size=13, color=INK, weight=None, anchor="start", lh=1.45):
        for i, line in enumerate(wrap(text, width, size)):
            self.text(x, y + i * size * lh, line, size, color, anchor, weight)
        return y + len(wrap(text, width, size)) * size * lh

    def done(self, h):
        self.h = int(h)
        self.parts.insert(0, f'<rect width="{W}" height="{self.h}" rx="10" fill="#fcfcfb"/>')
        return self.svg()


# ---- 母集団と標本（どの数がどちらの側か） ----
def popsample(sp: dict) -> str:
    c = Canvas()
    pop, smp = sp["pop"], sp.get("sample") or {}
    # 母集団の枠（標本はその中の一部）
    y = 30
    head = [f"母集団：{pop['label']}"] + ([pop["size"]] if pop.get("size") else [])
    top = 8
    c_parts_before = len(c.parts)
    y = c.para(22, y, head[0], 316, 14, BLUE, "bold")
    if len(head) > 1:
        y = c.para(22, y, head[1], 316, 13, INK2)
    sy0 = y + 4
    sy = sy0 + 22
    if sp.get("whole"):
        sy = c.para(38, sy, "全数調査：知りたい全体を全部調べた", 284, 13, BLUE, "bold")
        dash = True
    else:
        sy = c.para(38, sy, f"標本：{smp['label']}", 284, 14, WARM, "bold")
        if smp.get("size"):
            sy = c.para(38, sy, smp["size"], 284, 13, INK2)
        if smp.get("bias"):
            sy = c.para(38, sy + 2, "⚠ " + smp["bias"], 284, 12.5, RED)
        dash = False
    sbox = (26, sy0, 308, sy - sy0 + 6)
    pbox = (8, top, 344, sbox[1] + sbox[3] + 12 - top)
    box = [f'<rect x="{pbox[0]}" y="{pbox[1]}" width="{pbox[2]}" height="{pbox[3]:.0f}" rx="12" fill="{LIGHT}" stroke="{BLUE}" stroke-width="1.5"/>']
    if dash:
        box.append(f'<rect x="{sbox[0]}" y="{sbox[1]}" width="{sbox[2]}" height="{sbox[3]:.0f}" rx="10" fill="#ffffff" stroke="{BLUE}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    else:
        box.append(f'<rect x="{sbox[0]}" y="{sbox[1]}" width="{sbox[2]}" height="{sbox[3]:.0f}" rx="10" fill="{WARM_BG}" stroke="{WARM}" stroke-width="1.5"/>')
    c.parts[c_parts_before:c_parts_before] = box
    y = pbox[1] + pbox[3] + 24
    # どちらの側の数か
    groups = [("param", "母数（母集団の値）", BLUE, sp.get("param_note") or "決まっているが、ふつうは分からない"),
              ("stat", "統計量（標本から計算した値）", WARM, "標本を取り直すと変わる")]
    for key, title, color, sub in groups:
        vals = sp.get(key) or []
        if not vals:
            continue
        c.rect(8, y - 15, 5, 18, color, rx=2)
        y = c.para(20, y, title, 330, 13.5, color, "bold")
        y = c.para(20, y, sub, 330, 12, INK2)
        for v in vals:
            y = c.para(28, y + 2, "・" + v, 322, 13, INK)
        y += 14
    if sp.get("note"):
        y = c.para(8, y, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


# ---- 尺度の階段にデータを置く（段ごとに1行。スマホで読める幅にする） ----
STEP_OPS = ["＝ ≠ だけ", "＜ ＞ まで", "＋ − まで", "× ÷ まで"]


def ladder(sp: dict) -> str:
    c = Canvas()
    rows = [[] for _ in SCALES]
    for it in sp["items"]:
        rows[it["scale"]].append(it)
    y = 8
    lx, lw, cx0, cx1 = 8, 70, 84, 352
    for i, name in enumerate(SCALES):
        color = WARM if i < 2 else BLUE
        bg = WARM_BG if i < 2 else LIGHT
        # 中のカードを並べる（左から詰めて、はみ出したら次の行）
        cards, x, yy, rowh = [], cx0 + 6, y + 6, 0
        for it in rows[i]:
            name_l = wrap(it["name"], cx1 - cx0 - 24, 13)
            note_l = wrap(it.get("note", ""), cx1 - cx0 - 24, 12) if it.get("note") else []
            wpx = max([sum(_w(ch) * 13 for ch in ln) for ln in name_l] + [sum(_w(ch) * 12 for ch in ln) for ln in note_l]) + 16
            hpx = 10 + len(name_l) * 17 + len(note_l) * 16 + 2
            if x + wpx > cx1 - 4 and x > cx0 + 6:
                x, yy = cx0 + 6, yy + rowh + 6
                rowh = 0
            cards.append((x, yy, wpx, hpx, name_l, note_l, it.get("ng")))
            x += wpx + 6
            rowh = max(rowh, hpx)
        band = (yy + rowh + 6 - y) if cards else 36
        band = max(band, 44)
        c.rect(lx, y, cx1 - lx, band, bg, rx=8, stroke=color)
        c.text(lx + 8, y + 20, name, 14, color, weight="bold")
        c.text(lx + 8, y + 37, STEP_OPS[i], 11, INK2)
        for (x, yy, wpx, hpx, name_l, note_l, ng) in cards:
            c.rect(x, yy, wpx, hpx, "#ffffff", rx=6, stroke=color)
            ty = yy + 18
            for ln in name_l:
                c.text(x + 8, ty, ln, 13, INK, weight="bold"); ty += 17
            for ln in note_l:
                c.text(x + 8, ty - 1, ln, 12, RED if ng else INK2); ty += 16
        if not cards:
            c.text(cx0 + 10, y + 27, "（この段のデータはない）", 11.5, "#9a9894")
        y += band + 6
    c.rect(lx, y + 4, 10, 10, WARM, rx=2); c.text(lx + 16, y + 13, "質的変数（名義・順序）", 12, INK2)
    c.rect(lx + 176, y + 4, 10, 10, BLUE, rx=2); c.text(lx + 192, y + 13, "量的変数（間隔・比例）", 12, INK2)
    y += 34
    if sp.get("note"):
        y = c.para(8, y, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


# ---- 棒グラフ（値・平均の線） ----
def bars(sp: dict) -> str:
    c = Canvas()
    data = sp["bars"]
    unit = sp.get("unit", "")
    vmax = max(v for _, v in data)
    top, base, left, right = 46, 196, 16, 344
    y = 20
    dec = sp.get("decimals")
    fmt = (lambda v: f"{v:.{dec}f}") if dec is not None else _num
    if sp.get("title"):
        c.para(8, y, sp["title"], 230 if "mean" in sp else 344, 13.5, INK, "bold")
    scale = (base - top - 16) / vmax
    n = len(data)
    slot = (right - left) / n
    bw = min(44, slot * 0.6)
    c.line(left, base, right, base, INK2, 1)
    vals = [v for _, v in data]
    hi, lo = max(vals), min(vals)
    for i, (lab, v) in enumerate(data):
        cx = left + slot * (i + 0.5)
        color = BLUE if v in (hi, lo) and sp.get("mark_extremes") else "#8fb3e3"
        c.rect(cx - bw / 2, base - v * scale, bw, v * scale, color, rx=3)
        c.add(f'<text x="{cx:.1f}" y="{base - v * scale - 6:.1f}" font-size="12.5" fill="{INK}" text-anchor="middle" font-weight="bold" '
              f'stroke="#fcfcfb" stroke-width="4" paint-order="stroke">{esc(fmt(v) + unit)}</text>')
        for k, ln in enumerate(wrap(lab, slot - 4, 11.5)):
            c.text(cx, base + 16 + k * 14, ln, 11.5, INK2, "middle")
    if "mean" in sp:
        m = Fraction(str(sum(Fraction(str(v)) for v in vals))) / n
        my = base - float(m) * scale
        c.line(left, my, right, my, ORANGE, 2, "6 4")
        c.line(right - 112, 15, right - 88, 15, ORANGE, 2, "6 4")
        c.text(right, 20, f"平均 {fmt(float(m))}{unit}", 12.5, ORANGE, "end", "bold")
    y = base + 16 + 14 * max(len(wrap(lab, slot - 4, 11.5)) for lab, _ in data) + 8
    if sp.get("mark_extremes"):
        r = Fraction(str(hi)) / Fraction(str(lo))
        y = c.para(8, y, f"最大 {fmt(hi)}{unit} ÷ 最小 {fmt(lo)}{unit} ≒ {float(r):.1f}倍", 344, 13, INK, "bold")
    if sp.get("note"):
        y = c.para(8, y + 2, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


def _num(v) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s


# ---- 組合せを並べる（何通りか・その中の何通りか） ----
def pairs(sp: dict) -> str:
    from itertools import combinations
    c = Canvas()
    items, k, mark = sp["items"], sp["k"], sp.get("mark")
    combos = list(combinations(items, k))
    hit = [cb for cb in combos if mark in cb]
    y = c.para(8, 22, sp.get("title", f"{len(items)}つから{k}つを選ぶ：全部で{len(combos)}通り"), 344, 13.5, INK, "bold")
    per = 5
    bw, bh, gx = 62, 34, 8
    x0 = (W - (per * bw + (per - 1) * gx)) / 2
    y += 4
    for i, cb in enumerate(combos):
        x = x0 + (i % per) * (bw + gx)
        yy = y + (i // per) * (bh + 8)
        on = mark in cb
        c.rect(x, yy, bw, bh, BLUE if on else "#ffffff", rx=8, stroke=BLUE)
        c.text(x + bw / 2, yy + 22, "・".join(cb), 13.5, "#ffffff" if on else INK, "middle", "bold")
    y += ((len(combos) - 1) // per + 1) * (bh + 8) + 16
    if mark:
        p = Fraction(len(hit), len(combos))
        y = c.para(8, y, f"{mark} を含む選び方（色付き）：{len(hit)}通り → 確率 {len(hit)}/{len(combos)}＝{p.numerator}/{p.denominator}", 344, 13, INK)
    if sp.get("note"):
        y = c.para(8, y + 2, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


# ---- かけ算で数える（各段の通り数を掛ける） ----
def product(sp: dict) -> str:
    c = Canvas()
    fs = sp["factors"]
    total = 1
    for _, n in fs:
        total *= n
    y = c.para(8, 22, sp.get("title", "それぞれの選び方を掛ける"), 344, 13.5, INK, "bold")
    bw, gap = 64, 26
    x0 = 10
    for i, (lab, n) in enumerate(fs):
        x = x0 + i * (bw + gap)
        c.rect(x, y + 4, bw, 56, LIGHT, rx=8, stroke=BLUE)
        c.text(x + bw / 2, y + 26, lab, 12.5, INK2, "middle")
        c.text(x + bw / 2, y + 48, f"{n}通り", 14, BLUE, "middle", "bold")
        c.text(x + bw + gap / 2, y + 40, "×" if i < len(fs) - 1 else "＝", 16, INK, "middle", "bold")
    x = x0 + len(fs) * (bw + gap)
    c.text(min(x, W - 8), y + 40, f"{total}通り", 15, ORANGE, "end" if x > W - 70 else "start", "bold")
    y += 80
    if sp.get("note"):
        y = c.para(8, y, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


# ---- 捕獲再捕獲（印の割合で全体を推し量る） ----
def capture(sp: dict) -> str:
    c = Canvas()
    M, n, m = sp["marked"], sp["second"], sp["recaught"]
    r = Fraction(m, n)
    N = Fraction(M) / r
    panels = [(f"1回目：{M}匹に印", M, M), (f"2回目：{n}匹を捕まえる", n, m)]
    for p, (title, cnt, mk) in enumerate(panels):
        x0 = 8 + p * 178
        c.para(x0, 22, title, 168, 12.5, INK, "bold")
        cols = 10
        for i in range(cnt):
            cx = x0 + 9 + (i % cols) * 16
            cy = 56 + (i // cols) * 16
            c.circle(cx, cy, 6, ORANGE if i < mk else "#ffffff", stroke=ORANGE if i < mk else INK2, width=1.2)
    y = 56 + ((max(M, n) - 1) // 10 + 1) * 16 + 10
    c.circle(16, y - 4, 6, ORANGE, stroke=ORANGE); c.text(28, y, "印あり", 12, INK2)
    y += 22
    y = c.para(8, y, f"2回目の中の印の割合：{m}/{n}＝{r.numerator}/{r.denominator}", 344, 13, INK)
    y = c.para(8, y, f"池全体でも印の{M}匹が{r.numerator}/{r.denominator}なら：{M}÷({r.numerator}/{r.denominator})＝約{int(N)}匹", 344, 13, INK, "bold")
    if sp.get("note"):
        y = c.para(8, y + 2, sp["note"], 344, 12.5, INK2)
    return c.done(y + 4)


# ---- 有限母集団修正の係数 ----
def fpc(sp: dict) -> str:
    c = Canvas()
    N, n = sp["N"], sp["n"]
    k = (N - n) / (N - 1)
    y = c.para(8, 22, f"係数 (N−n)/(N−1)：N＝{N:,} のとき", 344, 13.5, INK, "bold")
    left, right, top, base = 44, 344, y + 6, y + 150
    X = lambda v: left + v / N * (right - left)  # noqa: E731
    Y = lambda v: base - v * (base - top)        # noqa: E731
    for t in (0, 0.5, 1):
        c.line(left, Y(t), right, Y(t), GRID, 1)
        c.text(left - 6, Y(t) + 4, _num(t), 11.5, INK2, "end")
    for t, a in ((0, "middle"), (N // 2, "middle"), (N, "end")):
        c.text(X(t), base + 16, f"{t:,}", 11.5, INK2, a)
    c.text(right, base + 32, "選ぶ数 n", 11.5, INK2, "end")
    c.poly([(X(0), Y(1)), (X(N), Y(0))], BLUE, 2)
    c.line(left, Y(1), right, Y(1), INK2, 1, "4 3")
    c.text(right, Y(1) - 6, "戻して選ぶ＝1（修正なし）", 11.5, INK2, "end")
    c.circle(X(n), Y(k), 5, ORANGE, stroke="#ffffff", width=2)
    c.text(X(n) + 9, Y(k) + 18, f"n＝{n}：{k:.3f}", 13, ORANGE, weight="bold")
    y = base + 48
    y = c.para(8, y, f"分散は約{k:.2f}倍、標準偏差は √{k:.3f}≒{k ** 0.5:.2f}倍。n が N に近づくほど係数は0に近づく。", 344, 12.5, INK2)
    return c.done(y + 4)


# ---- 四分位数（ラボ・本文と同じ定義：中央値を除いた下半分・上半分の中央値） ----
def _median(s):
    n = len(s)
    return s[(n - 1) // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def five(values):
    s = sorted(values)
    n, h = len(s), len(s) // 2
    q1, q2, q3 = _median(s[:h]), _median(s), _median(s[n - h:])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = [x for x in s if lo <= x <= hi]
    return {"min": s[0], "max": s[-1], "q1": q1, "q2": q2, "q3": q3, "iqr": iqr, "lo": lo, "hi": hi,
            "wlo": inside[0], "whi": inside[-1], "out": [x for x in s if x < lo or x > hi], "mean": sum(s) / n}


def _box(c, F, y, X, color=BLUE, fence=False, label=None, mean=None):
    if label:
        c.text(8, y - 22, label, 12.5, INK, weight="bold")   # 柵の点線（y−16から）と箱に重ならない高さ
    if fence:
        for v in (F["lo"], F["hi"]):
            c.line(X(v), y - 16, X(v), y + 16, RED, 1.2, "3 3")
    c.line(X(F["wlo"]), y, X(F["q1"]), y, color, 2); c.line(X(F["q3"]), y, X(F["whi"]), y, color, 2)
    for v in (F["wlo"], F["whi"]):
        c.line(X(v), y - 7, X(v), y + 7, color, 2)
    c.rect(X(F["q1"]), y - 11, max(1, X(F["q3"]) - X(F["q1"])), 22, color, rx=3, opacity=0.15)
    c.add(f'<rect x="{X(F["q1"]):.1f}" y="{y - 11}" width="{max(1, X(F["q3"]) - X(F["q1"])):.1f}" height="22" rx="3" fill="none" stroke="{color}" stroke-width="2"/>')
    c.line(X(F["q2"]), y - 11, X(F["q2"]), y + 11, color, 3)
    for v in F["out"]:
        c.circle(X(v), y, 4.5, "#ffffff", stroke=RED, width=2)
    if mean is not None:                                       # 平均の位置（▲）。中央値（箱の中の線）との違いを見せる
        m = X(mean)
        c.add(f'<path d="M{m:.1f} {y + 13} l-5 8 h10 z" fill="{INK}"/>')
        c.text(m, y + 32, f"平均 {_num(round(mean, 2))}", 11, INK, "middle")


def _axis(c, lo, hi, y, step, X):
    c.line(16, y, W - 16, y, INK2, 1)
    t = lo
    while t <= hi + 1e-9:
        c.text(X(t), y + 15, _num(t), 11, INK2, "middle")
        t += step


# ---- ヒストグラム（階級・度数。幅が違えば度数密度。箱ひげ図を下に付けられる） ----
def hist(sp: dict) -> str:
    c = Canvas()
    if "data" in sp:                        # データと階級の幅から数える
        a0, w, top = sp["start"], sp["width"], max(sp["data"])
        cls, a = [], a0
        while a <= top:
            cls.append([a, a + w, sum(1 for x in sp["data"] if a <= x < a + w)])
            a += w
    else:
        cls = sp["classes"]                 # [[下限, 上限, 度数], …]
    dens = sp.get("density", False)
    lo, hi = cls[0][0], cls[-1][1]
    X = lambda v: 16 + (v - lo) / (hi - lo) * (W - 32)  # noqa: E731
    y = 8
    if sp.get("title"):
        y = c.para(8, 22, sp["title"], 344, 13.5, INK, "bold") - 8
    top, base = y + 26, y + 170
    hts = [(n / (b - a) if dens else n) for a, b, n in cls]
    mx = max(hts) or 1
    total = sum(n for _, _, n in cls)
    mark = sp.get("mark")
    for i, ((a, b, n), h) in enumerate(zip(cls, hts)):
        hh = h / mx * (base - top - 18)
        col = ORANGE if mark is not None and i == mark else BLUE
        c.rect(X(a), base - hh, X(b) - X(a) - 1.5, hh, col, opacity=0.8)
        lab = (f"{_num(round(h, 3))}" if dens else f"{n}")
        c.add(f'<text x="{(X(a) + X(b)) / 2:.1f}" y="{base - hh - 5:.1f}" font-size="12" fill="{INK}" text-anchor="middle" font-weight="bold" '
              f'stroke="#fcfcfb" stroke-width="4" paint-order="stroke">{esc(lab)}</text>')
    ticks = sorted({v for a, b, _ in cls for v in (a, b)})
    c.line(16, base, W - 16, base, INK2, 1)
    for t in ticks:
        c.text(X(t), base + 15, _num(t), 11, INK2, "middle")
    y = base + 24
    if sp.get("axis_label"):
        c.text(W - 16, base + 31, sp["axis_label"], 11, INK2, "end"); y = base + 46
    if dens:
        y += 8
        for a, b, n in cls:
            y = c.para(8, y + 4, f"{_num(a)}〜{_num(b)}：度数{n}÷幅{_num(b - a)}＝高さ{_num(round(n / (b - a), 3))}（面積＝{n}）", 344, 12.5, INK)
    elif sp.get("cumulative"):
        y += 8
        cum = 0
        row = []
        for a, b, n in cls:
            cum += n
            row.append(f"{_num(b)}未満 {cum / total:.2f}")
        y = c.para(8, y + 4, "累積相対度数：" + "、".join(row), 344, 12.5, INK)
    if sp.get("box"):
        F = five(sp["box"])
        y += 40
        _box(c, F, y, X, ORANGE, fence=True)
        y += 26
        y = c.para(8, y + 10, f"箱ひげ図：Q₁ {_num(F['q1'])}・中央値 {_num(F['q2'])}・Q₃ {_num(F['q3'])}。柵 {_num(F['lo'])}〜{_num(F['hi'])} の外（○）が外れ値候補", 344, 12, INK2)
    if sp.get("note"):
        y = c.para(8, y + 10, sp["note"], 344, 12.5, INK2)
    return c.done(y + 6)


# ---- 箱ひげ図（データから5つの数を計算して描く。複数並べられる） ----
def boxplot(sp: dict) -> str:
    c = Canvas()
    rows = sp["rows"]                       # [{label, data}]
    Fs = [five(r["data"]) for r in rows]
    lo = sp.get("lo", min(min(r["data"]) for r in rows))
    hi = sp.get("hi", max(max(max(r["data"]) for r in rows), max(F["hi"] for F in Fs) if sp.get("fence") else 0))
    step = sp.get("step", 10)
    lo, hi = step * (lo // step), step * -(-hi // step)
    X = lambda v: 16 + (v - lo) / (hi - lo) * (W - 32)  # noqa: E731
    y = 8
    if sp.get("title"):
        y = c.para(8, 22, sp["title"], 344, 13.5, INK, "bold") - 8
    y += 38
    for r, F in zip(rows, Fs):
        mean = sum(r["data"]) / len(r["data"]) if sp.get("mean") else None
        _box(c, F, y, X, BLUE, fence=sp.get("fence"), label=r.get("label"), mean=mean)
        y += 64 if mean is not None else 52
    _axis(c, lo, hi, y - 22, step, X)
    y += 6
    for r, F in zip(rows, Fs):
        head = f"{r['label']}：" if r.get("label") else ""
        out = "・".join(_num(v) for v in F["out"]) or "なし"
        y = c.para(8, y + 4, f"{head}Q₁ {_num(F['q1'])}・中央値 {_num(F['q2'])}・Q₃ {_num(F['q3'])}・IQR {_num(F['iqr'])}", 344, 12.5, INK)
        if sp.get("fence"):
            y = c.para(8, y, f"柵 {_num(F['lo'])} と {_num(F['hi'])} → 外れ値候補：{out}", 344, 12.5, RED if F["out"] else INK2)
    if sp.get("note"):
        y = c.para(8, y + 4, sp["note"], 344, 12.5, INK2)
    return c.done(y + 6)


# ---- 折れ線（時系列。幾何平均の率で結んだ線・指数平滑の線を計算して重ねられる） ----
def line(sp: dict) -> str:
    c = Canvas()
    series = [dict(s) for s in sp["series"]]           # [{label, values}]
    labels = sp.get("labels") or [str(i + 1) for i in range(len(series[0]["values"]))]
    first = series[0]["values"]
    extra = []
    if sp.get("geom"):                                    # 最初と最後を同じ倍率で結ぶ（平均成長率の線）
        m = len(first) - 1
        g = (first[-1] / first[0]) ** (1 / m)
        extra.append({"label": f"毎期 {_num(round((g - 1) * 100, 2))}%（幾何平均）", "values": [first[0] * g ** i for i in range(m + 1)], "dash": "6 4"})
    if sp.get("smooth") is not None:                      # 指数平滑 S_t＝αx_t＋(1−α)S_{t−1}
        a, sm = sp["smooth"], [first[0]]
        for x in first[1:]:
            sm.append(a * x + (1 - a) * sm[-1])
        extra.append({"label": f"指数平滑（α＝{_num(a)}）", "values": sm, "dash": "6 4"})
    allv = [v for s in series + extra for v in s["values"]]
    lo, hi = min(allv), max(allv)
    if sp.get("zero"):
        lo = 0
    pad = (hi - lo) * 0.15 or 1
    lo, hi = lo - (0 if sp.get("zero") else pad), hi + pad
    y = 8
    if sp.get("title"):
        y = c.para(8, 22, sp["title"], 344, 13.5, INK, "bold") - 8
    top, base = y + 22, y + 170
    n = len(labels)
    X = lambda i: 30 + i * (W - 60) / max(1, n - 1)            # noqa: E731
    Y = lambda v: base - (v - lo) / (hi - lo) * (base - top)  # noqa: E731
    c.line(16, base, W - 16, base, INK2, 1)
    colors = [BLUE, ORANGE, "#6250d6"]
    for k, s in enumerate(series + extra):
        col = colors[k % len(colors)]
        pts = [(X(i), Y(v)) for i, v in enumerate(s["values"])]
        c.poly(pts, col, 2.5, dash=s.get("dash"))
        for i, (px, py) in enumerate(pts):
            c.circle(px, py, 4, col)
            if k == 0 or s.get("show_values", True):
                c.add(f'<text x="{px:.1f}" y="{py - 9:.1f}" font-size="12" fill="{INK}" text-anchor="middle" font-weight="bold" '
                      f'stroke="#fcfcfb" stroke-width="4" paint-order="stroke">{esc(_num(round(s["values"][i], 2)))}</text>')
    for i, t in enumerate(labels):
        c.text(X(i), base + 16, t, 11.5, INK2, "middle")
    y = base + 32
    for k, s in enumerate(series + extra):
        col = colors[k % len(colors)]
        c.line(10, y - 4, 30, y - 4, col, 2.5, s.get("dash"))
        y = c.para(36, y, s.get("label", ""), 316, 12, INK2)
    if sp.get("note"):
        y = c.para(8, y + 4, sp["note"], 344, 12.5, INK2)
    return c.done(y + 6)


# ---- 偏差（平均からのずれ）を行ごとに線で見せる。偏差平方和・分散は図を作るときに計算する ----
def dev(sp: dict) -> str:
    c = Canvas()
    rows = sp["rows"]                       # [{label, data}]
    allv = [v for r in rows for v in r["data"]]
    step = sp.get("step", 2)
    lo, hi = step * (min(allv) // step), step * -(-max(allv) // step)
    X = lambda v: 16 + (v - lo) / (hi - lo) * (W - 32)  # noqa: E731
    y = 8
    if sp.get("title"):
        y = c.para(8, 22, sp["title"], 344, 13.5, INK, "bold") - 8
    y += 14
    colors = [BLUE, ORANGE, RED]
    for k, r in enumerate(rows):
        d = r["data"]; n = len(d); m = Fraction(sum(Fraction(str(v)) for v in d), n)
        ss = sum((Fraction(str(v)) - m) ** 2 for v in d)
        col = colors[k % len(colors)]
        c.text(8, y + 4, r["label"], 12.5, INK, weight="bold")
        y0 = y + 14
        c.line(X(float(m)), y0 - 4, X(float(m)), y0 + 12 * n, INK2, 1.5)
        for i, v in enumerate(d):
            yy = y0 + 4 + i * 12
            c.add(f'<line x1="{X(float(m)):.1f}" y1="{yy}" x2="{X(v):.1f}" y2="{yy}" stroke="{col}" stroke-width="2" stroke-dasharray="4 3"/>')
            c.circle(X(v), yy, 4, col)
        y = y0 + 12 * n + 6
        y = c.para(8, y + 8, f"平均 {_num(float(m))}・偏差平方和 {_num(float(ss))}・分散（n）{_num(float(ss / n))}・不偏分散 {_num(float(ss / (n - 1)))}", 344, 12.5, INK) + 4
    _axis(c, lo, hi, y + 2, step, X)
    y += 26
    if sp.get("note"):
        y = c.para(8, y + 4, sp["note"], 344, 12.5, INK2)
    return c.done(y + 6)


# ---- 確率分布の概念図（棒か曲線。期待値の▲・±標準偏差・確率の面積） ----
def _pmf(sp: dict):
    import math
    f = sp["family"]
    if f == "table":
        return list(zip(sp["values"], sp["probs"]))
    if f == "binom":
        n, p = sp["n"], sp["p"]
        top = sp["kmax"] if sp.get("kmax") is not None else n   # kmax：棒を出す範囲（解説付き再生でラボと共有）。n より先は0（上限が見える）
        return [(k, math.comb(n, k) * p ** k * (1 - p) ** (n - k) if k <= n else 0.0) for k in range(sp.get("kmin", 0), top + 1)]
    if f == "poisson":
        lam = sp["lam"]
        return [(k, math.exp(-lam) * lam ** k / math.factorial(k)) for k in range(sp["kmax"] + 1)]
    if f == "geom":   # r 回目の成功が k 回目（r＝1 で幾何分布）。k は r から kmax まで
        p, r = sp["p"], sp.get("r", 1)
        return [(k, math.comb(k - 1, r - 1) * p ** r * (1 - p) ** (k - r)) for k in range(r, sp["kmax"] + 1)]
    if f == "hyper":  # N 個中 K 個が当たり、戻さず n 個
        N, K, n = sp["N"], sp["K"], sp["n"]
        top = sp["kmax"] if sp.get("kmax") is not None else n
        return [(k, math.comb(K, k) * math.comb(N - K, n - k) / math.comb(N, n) if 0 <= n - k <= N - K and k <= K else 0.0)
                for k in range(top + 1)]
    raise ValueError(f"family {f}")


def _pdf(sp: dict):
    import math
    f = sp["family"]
    if f == "normal":
        mu, s = sp["mu"], sp["sigma"]
        return (lambda x: math.exp(-((x - mu) / s) ** 2 / 2) / (s * math.sqrt(2 * math.pi))), mu, s
    if f == "uniform":
        a, b = sp["a"], sp["b"]
        return (lambda x: 1 / (b - a) if a <= x <= b else 0.0), (a + b) / 2, (b - a) / math.sqrt(12)
    if f == "expo":
        lam = sp["lam"]
        return (lambda x: lam * math.exp(-lam * x) if x >= 0 else 0.0), 1 / lam, 1 / lam
    raise ValueError(f"family {f}")


def dist(sp: dict) -> str:
    import math
    c = Canvas()
    unit = sp.get("unit", "")
    y = 8
    if sp.get("title"):
        y = c.para(8, 22, sp["title"], 344, 13.5, INK, "bold") - 8
    top, base, left, right = y + (44 if sp.get("band") else 26), y + 190, 20, 340
    discrete = sp["family"] in ("table", "binom", "poisson", "geom", "hyper")
    curve = None
    if discrete:
        pmf = _pmf(sp)
        if sp["family"] == "binom":      # 棒を途中で切っても、平均・標準偏差は分布の値を使う
            mean, sd = sp["n"] * sp["p"], math.sqrt(sp["n"] * sp["p"] * (1 - sp["p"]))
        elif sp["family"] == "poisson":
            mean, sd = sp["lam"], math.sqrt(sp["lam"])
        elif sp["family"] == "geom":
            r = sp.get("r", 1)
            mean, sd = r / sp["p"], math.sqrt(r * (1 - sp["p"])) / sp["p"]
        elif sp["family"] == "hyper":
            q = sp["K"] / sp["N"]
            mean = sp["n"] * q
            sd = math.sqrt(sp["n"] * q * (1 - q) * (sp["N"] - sp["n"]) / (sp["N"] - 1))
        else:
            mean = sum(x * p for x, p in pmf)
            sd = math.sqrt(sum(x * x * p for x, p in pmf) - mean ** 2)
        lo, hi = pmf[0][0] - 0.5, pmf[-1][0] + 0.5
        X = lambda v: left + (v - lo) / (hi - lo) * (right - left)  # noqa: E731
        curve = sp.get("overlay") if (sp.get("overlay") or {}).get("family") == "normal" else None   # 正規分布の曲線を重ねる
        ov = dict(_pmf({**sp["overlay"], "kmax": pmf[-1][0]})) if sp.get("overlay") and not curve else None   # 重ねる分布の棒（同じ範囲）
        pmax = max([p for _, p in pmf] + (list(ov.values()) if ov else [])
                   + ([1 / (curve["sigma"] * math.sqrt(2 * math.pi))] if curve else []))
        scale = (base - top - 18) / pmax
        slot = (right - left) / len(pmf)
        bw = min(40, slot * (0.36 if ov else 0.62))
        dec = sp.get("decimals", 2)
        hl = set(sp.get("highlight") or [])
    else:
        f, mean, sd = _pdf(sp)
        lo, hi, step = sp["ticks"]
        X = lambda v: left + (v - lo) / (hi - lo) * (right - left)  # noqa: E731
        xs = [lo + (hi - lo) * i / 240 for i in range(241)]
        pmax = max(f(x) for x in xs)
        scale = (base - top - 18) / pmax
    k = sp.get("band")
    if k:   # 期待値±k標準偏差の帯（後ろに薄く）
        a, b = max(lo, mean - k * sd), min(hi, mean + k * sd)
        c.rect(X(a), top - 4, X(b) - X(a), base - top + 4, "#eef3fb")
        c.line(X(a), top - 14, X(b), top - 14, BLUE, 1.5)
        c.text(X(mean), top - 20, ("±標準偏差" if k == 1 else f"±{_num(k)}標準偏差") + f"（{_num(round(mean - k * sd, 2))}〜{_num(round(mean + k * sd, 2))}）", 11.5, BLUE, "middle", "bold")
    c.line(left, base, right, base, INK2, 1)
    if discrete:
        for x, p in pmf:
            cx = X(x) - (bw / 2 + 1 if ov else 0)
            col = ORANGE if x in hl else "#8fb3e3"
            c.rect(cx - bw / 2, base - p * scale, bw, p * scale, col, rx=3)
            if ov:   # 重ねる分布は点線の枠（ラボと同じ見せ方）
                q = ov.get(x, 0.0)
                c.add(f'<rect x="{cx + bw / 2 + 2:.1f}" y="{base - q * scale:.1f}" width="{bw:.1f}" height="{q * scale:.1f}" rx="2" '
                      f'fill="none" stroke="{INK}" stroke-width="1.2" stroke-dasharray="3 2"/>')
                cx = X(x)
            if (p * scale > 1.5 and not ov and len(pmf) <= 12) or x in hl:
                c.add(f'<text x="{cx:.1f}" y="{base - p * scale - 5:.1f}" font-size="11.5" fill="{INK}" text-anchor="middle" '
                      f'stroke="#fcfcfb" stroke-width="4" paint-order="stroke">{esc(f"{p:.{dec}f}")}</text>')
            every = max(1, math.ceil(len(pmf) / 12))   # 棒が多いときは目盛りを間引く
            if (x - pmf[0][0]) % every == 0 or x in hl:
                c.text(cx, base + 15, f"{_num(x)}{unit}", 11.5, INK2, "middle")
        if curve:
            mu, sg = curve["mu"], curve["sigma"]
            xs2 = [lo + (hi - lo) * i / 160 for i in range(161)]
            d = "M" + " L".join(f"{X(x):.1f},{base - math.exp(-((x - mu) / sg) ** 2 / 2) / (sg * math.sqrt(2 * math.pi)) * scale:.1f}" for x in xs2)
            c.add(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="4 3"/>')
    else:
        for sh in sp.get("shade") or []:
            if "outside" in sh:
                parts = [(lo, sh["outside"][0]), (sh["outside"][1], hi)]
                col, op = ORANGE, 0.55
            else:
                parts = [(sh["from"], sh["to"])]
                col, op = BLUE, 0.35
            for a, b in parts:
                pts = [a + (b - a) * i / 80 for i in range(81)]
                d = f"M{X(a):.1f},{base} " + " ".join(f"L{X(x):.1f},{base - f(x) * scale:.1f}" for x in pts) + f" L{X(b):.1f},{base} Z"
                c.add(f'<path d="{d}" fill="{col}" fill-opacity="{op}"/>')
            if sh.get("label"):
                if "outside" in sh:
                    c.text(right, base - 62, sh["label"], 11.5, ORANGE, "end", "bold")
                else:
                    mid = (sh["from"] + sh["to"]) / 2
                    c.add(f'<text x="{X(mid):.1f}" y="{base - f(mid) * scale * 0.45:.1f}" font-size="12.5" fill="{INK}" text-anchor="middle" font-weight="bold" '
                          f'stroke="#fcfcfb" stroke-width="4" paint-order="stroke">{esc(sh["label"])}</text>')
        d = "M" + " L".join(f"{X(x):.1f},{base - f(x) * scale:.1f}" for x in xs)
        c.add(f'<path d="{d}" fill="none" stroke="{BLUE}" stroke-width="2.2"/>')
        t = lo
        while t <= hi + 1e-9:
            c.text(X(t), base + 15, _num(t), 11, INK2, "middle")
            t += step
    if discrete and sp.get("overlay") and sp["family"] == "binom" and not curve and sp["n"] < pmf[-1][0]:   # 二項の上限 n（そこから先は0）
        xl = (X(sp["n"]) + X(sp["n"] + 1)) / 2
        c.line(xl, top - 4, xl, base, INK2, 1.2, dash="4 3")
        c.text(xl + 4, top + 8, f"二項の上限 n＝{sp['n']}", 11.5, INK2)
    if sp.get("mark_mean", True):   # 期待値＝重心の▲
        mx = X(mean)
        c.add(f'<path d="M{mx:.1f},{base + 20} l-7,12 h14 z" fill="{ORANGE}"/>')
        c.text(mx, base + 46, f"{'期待値' if discrete else '平均'} {_num(round(mean, 2))}{unit}", 12, ORANGE, "middle", "bold")
    y = base + 58
    if sp.get("overlay") or sp.get("label"):   # 凡例・分散・差の最大（解説付き再生の静止図）
        c.rect(8, y + 2, 12, 12, "#8fb3e3", rx=2)
        c.text(24, y + 12, sp.get("label", "棒"), 12, INK2)
        if sp.get("overlay"):
            if curve:
                c.line(190, y + 8, 202, y + 8, INK, 1.6, dash="4 3")
            else:
                c.add(f'<rect x="190" y="{y + 2}" width="12" height="12" rx="2" fill="none" stroke="{INK}" stroke-dasharray="3 2"/>')
            c.text(206, y + 12, sp["overlay"].get("label", "重ねる分布"), 12, INK2)
        y += 20
        for line in sp.get("lines") or []:   # 数の行（例：分散 二項 2.1 ／ ポアソン 3）
            c.text(8, y + 12, line, 12.5, INK)
            y += 20
        if sp.get("maxdiff") is not None:
            dec = sp.get("decimals", 3)
            md = f"{10 ** -dec:.{dec}f}未満" if sp["maxdiff"] < 10 ** -dec else f"{sp['maxdiff']:.{dec}f}"   # 丸めて0に見せない
            c.text(8, y + 12, f"{sp.get('maxdiff_label', '棒どうしの差の最大')} {md}", 12.5, INK, weight="bold")
            y += 20
    if sp.get("note"):
        y = c.para(8, y + 10, sp["note"], 344, 12.5, INK2)
    return c.done(y + 6)


def paths(sp: dict) -> str:
    """n 回中ちょうど k 回成功する並びを全部書き出す（🛒 成功・❌ 失敗）。並び1つの確率×並びの数＝ちょうど k 回の確率。"""
    import itertools
    import math
    n, k, p = sp["n"], sp["k"], sp["p"]
    dec = sp.get("decimals", 4)
    rows = [c for c in itertools.product([1, 0], repeat=n) if sum(c) == k]
    c = Canvas()
    y, r, gap = 42, 9, 24
    c.text(16, 18, f"n＝{n} 回のうち ちょうど {k} 回成功する並び（{len(rows)} 通り）", 12.5, INK2)
    for row in rows:
        y += gap
        for j, x in enumerate(row):   # ラボと同じ印（🛒 成功・❌ 失敗）
            c.text(16 + j * 26, y + 1, "🛒" if x else "❌", 17)
        pr = "×".join(_num(round(p if x else 1 - p, 6)) for x in row)
        c.text(36 + n * 26, y, pr, 12, INK2)
    path = p ** k * (1 - p) ** (n - k)
    ncr = math.comb(n, k)
    y += 30
    sup = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")   # ラボと同じ書き方（0.3²×0.7²・₄C₂）
    sub = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    c.text(16, y, f"並び1つの確率 {_num(round(p, 6))}{str(k).translate(sup)}×{_num(round(1 - p, 6))}{str(n - k).translate(sup)}＝{path:.{dec}f}", 12.5, INK)
    y += 20
    c.text(16, y, f"並びの数 {str(n).translate(sub)}C{str(k).translate(sub)}＝{ncr} 通り", 12.5, INK)
    y += 22
    c.text(16, y, f"ちょうど {k} 回＝{ncr}×{path:.{dec}f}＝{ncr * path:.{dec}f}", 13.5, INK, weight="bold")
    c.text(16, 38, f"🛒 成功（確率 {_num(round(p, 6))}）　❌ 失敗（確率 {_num(round(1 - p, 6))}）", 11.5, INK2)
    return c.done(y + 14)


TYPES = {"popsample": popsample, "ladder": ladder, "bars": bars, "pairs": pairs, "product": product,
         "capture": capture, "fpc": fpc, "hist": hist, "boxplot": boxplot, "line": line, "dev": dev, "dist": dist, "paths": paths}


def specs(course: Course) -> dict[str, dict]:
    """図ID → {spec, caption, where, source}（source は数の照合に使う文）。"""
    out = {}
    for uid, u in course.units.items():
        body = "\n".join(t or "" for t in u["bodies"].values())
        for f in u.get("figures") or []:
            out[f["id"]] = {"spec": f.get("spec") or {}, "caption": f.get("caption", ""), "where": f"{uid}:{f['id']}",
                            "source": body, "used_by": [uid]}
        for qid, q in u["problems"].items():
            if q.get("figure"):
                f = q["figure"]
                # 問題文・答え・選択肢と、同じ単元の本文（「例題Aの表で」のように本文を指す問題があるため）
                src = " ".join([q.get("prompt", ""), q.get("answer", ""), " ".join(map(str, q.get("choices") or [])), body])
                out[f"FIG-{qid}"] = {"spec": f, "caption": f.get("caption", ""), "where": qid, "source": src,
                                     "used_by": [uid]}
    from tour import figure_specs   # 解説付き再生の段ごとの静止図（数は段階データから計算する）
    out.update(figure_specs(course))
    return out


LAYOUT_KEYS = ("type", "family", "band", "mark_mean", "highlight_label", "caption", "scale", "mark", "density", "cumulative", "fence", "step", "decimals", "k", "whole", "mean", "mark_extremes", "geom", "zero", "dash", "show_values")


def _strings(v):
    if isinstance(v, dict):
        for k, x in v.items():
            if k not in LAYOUT_KEYS:
                yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        yield str(v)
    elif isinstance(v, str):
        yield v


def validate_figures(course: Course) -> list[str]:
    err = []
    for fid, f in specs(course).items():
        sp = f["spec"]
        if sp.get("type") not in TYPES:
            err.append(f"{f['where']}: 図の type {sp.get('type')} がない（{', '.join(TYPES)}）")
            continue
        if not f["caption"]:
            err.append(f"{f['where']}: 図の caption（説明文）がない")
        if fid in course.figures and not course.figures[fid].get("generated"):
            err.append(f"{f['where']}: 図ID {fid} が assets.yaml の図と重なる")
        extra = set() if f["source"] is None else {x for s in _strings(sp) for x in numbers(s)} - numbers(f["source"]) - {"0", "1"}
        if extra:
            err.append(f"{f['where']}: 図に、問題文・答えにない数 {sorted(extra, key=float)} がある")
        try:
            TYPES[sp["type"]](sp)
        except Exception as e:  # noqa: BLE001
            err.append(f"{f['where']}: 図を作れない（{type(e).__name__}: {e}）")
    return err


def register(course: Course) -> None:
    """作る図を course.figures に加える（本文の {{fig:…}} と公開で同じ扱いにする）。"""
    for fid, f in specs(course).items():
        course.figures.setdefault(fid, {"id": fid, "file": str((OUT / f"{fid}.svg").relative_to(ROOT)),
                                        "caption": f["caption"], "used_by": f["used_by"], "generated": True})


def build_figures(course: Course) -> list[str]:
    OUT.mkdir(parents=True, exist_ok=True)
    made = []
    for fid, f in specs(course).items():
        (OUT / f"{fid}.svg").write_text(TYPES[f["spec"]["type"]](f["spec"]), encoding="utf-8")
        made.append(fid)
    return made


if __name__ == "__main__":   # 試しに全部作る：python3 build/figures.py
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model import load_course
    c = load_course()
    print("\n".join(validate_figures(c)) or "OK")
    print(build_figures(c))
