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
    lines, cur, cw = [], "", 0.0
    for ch in str(text):
        if ch == "\n":
            lines.append(cur); cur, cw = "", 0.0; continue
        if cw + _w(ch) * size > width_px and cur:
            lines.append(cur); cur, cw = "", 0.0
        cur += ch; cw += _w(ch) * size
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


TYPES = {"popsample": popsample, "ladder": ladder, "bars": bars, "pairs": pairs, "product": product,
         "capture": capture, "fpc": fpc}


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
                src = " ".join([q.get("prompt", ""), q.get("answer", ""), " ".join(map(str, q.get("choices") or []))])
                out[f"FIG-{qid}"] = {"spec": f, "caption": f.get("caption", ""), "where": qid, "source": src,
                                     "used_by": [uid]}
    return out


def _strings(v):
    if isinstance(v, dict):
        for k, x in v.items():
            if k not in ("type", "caption", "scale"):
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
        extra = {x for s in _strings(sp) for x in numbers(s)} - numbers(f["source"]) - {"0", "1"}
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
