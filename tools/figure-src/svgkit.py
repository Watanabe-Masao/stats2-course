"""Tiny SVG chart kit: compact, mobile-friendly, text stays as text."""
import math

import json
from pathlib import Path

# 色は math-lab の tokens.json（写しは docs/math-lab/tokens.json）から。ラボと同じ系列の色（#42）
_T = json.loads((Path(__file__).resolve().parents[2] / "docs" / "math-lab" / "tokens.json").read_text(encoding="utf-8"))["color"]
C = {k: v["$value"] for k, v in _T.items() if not k.startswith("$")}
BG = C["figure-bg"]; INK = C["ink"]; INK2 = C["ink-2"]; INK3 = C["ink-3"]; GRID = C["line"]; SURFACE = C["surface"]
BLUE = C["data-1"]; ORANGE = C["data-hi"]; VIOLET = C["data-2"]; AQUA = C["data-3"]; RED = C["bad"]
MUTED = C["data-1-soft"]; SOFT = C["data-1-soft"]; LIGHT = C["data-bg"]; WARM_BG = C["data-hi-bg"]

# ダークの画面で読む図（#582。2026-11-27 の iPhone の確認：暗い画面の中に白い板が出た）。
# 図の色は上の名前の付いた色だけなので、明るい値を暗い値（tokens.json の $extensions.dark）に置き換える規則を、SVG の中に書く。
# CSS は SVG の fill／stroke の属性より強いので、絵を描く側は変えなくてよい。地（figure-bg・surface。どちらも白）は、画面の面の暗い値にする
_DARK_OF = {"figure-bg": "surface"}   # 地は画面の面の色に合わせる（figure-bg の暗い値は、図がダークに対応するまでの白のまま）
_USED = ("figure-bg", "surface", "ink", "ink-2", "ink-3", "line", "data-1", "data-hi", "data-2", "data-3", "bad",
         "data-1-soft", "data-bg", "data-hi-bg")


def dark_map():
    """明るい値 → 暗い値（図で使う色だけ。小文字の #rrggbb）"""
    out = {}
    for k in _USED:
        light = C[k].lower()
        dark = _T[_DARK_OF.get(k, k)]["$extensions"]["dark"].lower()
        if out.get(light, dark) != dark:
            raise ValueError(f"図の色 {light} の暗い値が2つある（{out[light]} と {dark}）")
        out[light] = dark
    return out


def themed(svg: str) -> str:
    """SVG に、ダークの画面で色を置き換える規則を足す（すでにあれば何もしない）"""
    if "prefers-color-scheme" in svg:
        return svg
    import re
    m = dark_map()
    if (odd := sorted({v.lower() for v in re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{6})"', svg)} - set(m))):
        # 名前の付いた色の外の色は、暗い画面でそのまま残る（白い文字が暗い地で消えるなど）。tokens.json の色を使う
        raise ValueError(f"図に、ダークの置き換えのない色がある：{', '.join(odd)}")
    rules = "".join(f'[fill="{a}" i]{{fill:{b}}}[stroke="{a}" i]{{stroke:{b}}}' for a, b in m.items() if a != b)
    head = svg.index(">", svg.index("<svg")) + 1
    return f"{svg[:head]}<style>@media (prefers-color-scheme: dark){{{rules}}}</style>{svg[head:]}"


def f(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w=480, h=300):
        self.w, self.h = w, h
        self.parts = [f'<rect width="{w}" height="{h}" fill="{BG}"/>']

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, t, size=12, color=INK, anchor="start", weight=None):
        wt = f' font-weight="{weight}"' if weight else ""
        self.add(f'<text x="{f(x)}" y="{f(y)}" font-size="{size}" fill="{color}" text-anchor="{anchor}"{wt}>{esc(t)}</text>')

    def line(self, x1, y1, x2, y2, color=INK2, width=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{color}" stroke-width="{width}"{d}/>')

    def rect(self, x, y, w, h, fill, rx=0, stroke=None, opacity=None):
        st = f' stroke="{stroke}" stroke-width="1.5"' if stroke else ""
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" fill="{fill}"{st}{op}/>')

    def circle(self, cx, cy, r, fill="none", stroke=None, width=1.5, opacity=None):
        st = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        self.add(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{fill}"{st}{op}/>')

    def poly(self, pts, color=BLUE, width=2, fill="none", opacity=None, dash=None, close=False):
        p = " ".join(f"{f(x)},{f(y)}" for x, y in pts)
        tag = "polygon" if close else "polyline"
        op = f' fill-opacity="{opacity}"' if opacity is not None else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        sc = f' stroke="{color}" stroke-width="{width}"' if color else ' stroke="none"'
        self.add(f'<{tag} points="{p}" fill="{fill}"{sc}{op}{d} stroke-linejoin="round"/>')

    def arrow(self, x1, y1, x2, y2, color=INK2, width=1.5):
        self.line(x1, y1, x2, y2, color, width)
        a = math.atan2(y2 - y1, x2 - x1)
        for s in (-1, 1):
            self.line(x2, y2, x2 - 7 * math.cos(a + s * 0.45), y2 - 7 * math.sin(a + s * 0.45), color, width)

    def svg(self):
        body = "".join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" font-family="sans-serif">{body}</svg>')


class Plot:
    """Data-coordinate plotting area inside an Svg."""

    def __init__(self, svg, x0, y0, x1, y1, xmin, xmax, ymin, ymax):
        self.s = svg; self.box = (x0, y0, x1, y1)
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

    def sx(self, x):
        x0, _, x1, _ = self.box
        return x0 + (x - self.xmin) / (self.xmax - self.xmin) * (x1 - x0)

    def sy(self, y):
        _, y0, _, y1 = self.box
        return y1 - (y - self.ymin) / (self.ymax - self.ymin) * (y1 - y0)

    def ygrid(self, ticks, fmt="{}", labels=True):
        x0, _, x1, _ = self.box
        for t in ticks:
            self.s.line(x0, self.sy(t), x1, self.sy(t), GRID, 1)
            if labels:
                self.s.text(x0 - 5, self.sy(t) + 4, fmt.format(t), 11, INK2, "end")

    def baseline(self, y=None):
        x0, _, x1, _ = self.box
        yy = self.sy(self.ymin if y is None else y)
        self.s.line(x0, yy, x1, yy, INK2, 1)

    def xlabels(self, items, size=12, dy=16):
        _, _, _, y1 = self.box
        for x, lab in items:
            self.s.text(self.sx(x), y1 + dy, lab, size, INK2, "middle")

    def bar(self, x, width, y, color=BLUE, base=0):
        top, bot = self.sy(max(y, base)), self.sy(min(y, base))
        w = abs(self.sx(x + width / 2) - self.sx(x - width / 2))
        self.s.rect(self.sx(x) - w / 2, top, w, max(bot - top, 0.8), color, rx=2)

    def curve(self, fn, a, b, n=48, color=BLUE, width=2, dash=None):
        pts = [(self.sx(a + (b - a) * i / n), self.sy(fn(a + (b - a) * i / n))) for i in range(n + 1)]
        self.s.poly(pts, color, width, dash=dash)

    def fill_under(self, fn, a, b, n=40, color=BLUE, opacity=0.25):
        pts = [(self.sx(a), self.sy(0))]
        pts += [(self.sx(a + (b - a) * i / n), self.sy(fn(a + (b - a) * i / n))) for i in range(n + 1)]
        pts += [(self.sx(b), self.sy(0))]
        self.s.poly(pts, None, 0, fill=color, opacity=opacity, close=True)


def npdf(x, mu=0, sd=1):
    return math.exp(-0.5 * ((x - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi))
