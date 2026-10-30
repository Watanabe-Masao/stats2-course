"""見た目と手触りの値（元は math-lab の packages/ui/tokens.json。写しは docs/math-lab/tokens.json）。

- css()：ラボ（labkit）に差し込む CSS の変数（knowledge-net の scripts/tokens.mjs と同じ名前・同じ値）
- color(名前)・dark(名前)：静止図（svgkit・figures.py）が使う色
写しは build/sync_schema.py が元と同じか確かめる（違えば check_all が止まる）。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "docs" / "math-lab" / "tokens.json"


def _value(v, typ: str) -> str:
    if typ == "cubicBezier":
        return "cubic-bezier(" + ", ".join(str(x) for x in v) + ")"
    return str(v)


@lru_cache(maxsize=1)
def flatten() -> list[tuple[str, str, str | None, str]]:
    """[(名前, ライト, ダーク, 型)]"""
    data = json.loads(PATH.read_text(encoding="utf-8"))
    out = []
    for group, g in data.items():
        if group.startswith("$") or group.startswith("x-"):
            continue
        for name, t in g.items():
            if name.startswith("$"):
                continue
            typ = t.get("$type") or g.get("$type")
            d = (t.get("$extensions") or {}).get("dark")
            out.append((name, _value(t["$value"], typ), None if d is None else _value(d, typ), typ))
    return out


def color(name: str) -> str:
    for n, v, _, typ in flatten():
        if n == name and typ == "color":
            return v
    raise KeyError(f"tokens.json に色 {name} がない")


def dark(name: str) -> str:
    for n, _, d, typ in flatten():
        if n == name and typ == "color" and d:
            return d
    raise KeyError(f"tokens.json に色 {name} のダークがない")


def css() -> str:
    light = "".join(f"--{n}:{v};" for n, v, _, _ in flatten())
    drk = "".join(f"--{n}:{d};" for n, _, d, _ in flatten() if d is not None)
    return f":root{{{light}color-scheme:light}}\n@media (prefers-color-scheme:dark){{:root{{{drk}color-scheme:dark}}}}\n"
