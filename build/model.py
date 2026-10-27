"""原本（content/・tools/）を読み込み、型と参照を検証し、数値を検算する。

表示先（Notion・アプリ）に依存しない。表示は render_*.py が担当する。
"""
from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TOOLS = ROOT / "tools"

FORMATS = {"written", "fill", "choice", "task"}
TOKEN = re.compile(r"\{\{(\w+)(?::([^}]+))?\}\}")


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---- 検算で使える関数 -------------------------------------------------
def fact(n: int) -> int:
    return math.factorial(n)


def perm(n: int, r: int) -> int:
    return math.perm(n, r)


def comb(n: int, r: int) -> int:
    return math.comb(n, r)


def derange(n: int) -> int:
    d = [1, 0]
    for k in range(2, n + 1):
        d.append((k - 1) * (d[k - 1] + d[k - 2]))
    return d[n]


CHECK_ENV = {
    "fact": fact, "perm": perm, "comb": comb, "derange": derange,
    "Fraction": Fraction, "math": math, "itertools": itertools,
    "abs": abs, "round": round, "len": len, "sum": sum, "range": range,
    "all": all, "any": any, "zip": zip,
}


def run_check(expr: str) -> bool:
    env = {"__builtins__": {}, **CHECK_ENV}
    return bool(eval(expr, env))  # noqa: S307 (原本は自分たちで管理)


# ---- データ ------------------------------------------------------------
@dataclass
class Course:
    stages: list
    powers: dict
    shared: dict
    terms: dict
    index: dict          # unit id -> {number, migrated}
    labs: dict           # lab id -> tool.yaml + path
    figures: dict        # fig id -> content/assets.yaml の項目
    units: dict = field(default_factory=dict)      # id -> unit dict (+ bodies, problems)
    errors: list = field(default_factory=list)

    @property
    def stage_ids(self):
        return [s["id"] for s in self.stages]


def load_course() -> Course:
    stages = sorted(load_yaml(CONTENT / "stages.yaml"), key=lambda s: s["order"])
    powers = {p["id"]: p for p in load_yaml(CONTENT / "powers.yaml")}
    shared = load_yaml(CONTENT / "shared.yaml")
    terms = {t["id"]: t for t in load_yaml(CONTENT / "terms.yaml")}
    index = {u["id"]: u for u in load_yaml(CONTENT / "units" / "index.yaml")}
    labs = {}
    for ty in sorted(TOOLS.glob("*/tool.yaml")):
        t = load_yaml(ty)
        t["dir"] = ty.parent
        labs[t["id"]] = t
    figures = {f["id"]: f for f in (load_yaml(CONTENT / "assets.yaml") or {}).get("figures", [])}
    for fid, f in figures.items():
        if not (ROOT / f["file"]).exists():
            raise FileNotFoundError(f"{fid}: 図のファイル {f['file']} がない")
    c = Course(stages, powers, shared, terms, index, labs, figures)
    for uid, meta in index.items():
        if not meta.get("migrated"):
            continue
        udir = CONTENT / "units" / uid
        unit = load_yaml(udir / "unit.yaml")
        unit["bodies"] = {}
        for s in stages:
            p = udir / f"{s['id']}.md"
            unit["bodies"][s["id"]] = p.read_text(encoding="utf-8") if p.exists() else None
        pf = CONTENT / "problems" / f"{uid}.yaml"
        unit["problems"] = {q["id"]: q for q in (load_yaml(pf) or [])} if pf.exists() else {}
        c.units[uid] = unit
    return c


# ---- 検証 ------------------------------------------------------------
def validate(c: Course) -> list[str]:
    err = []
    seen_q = set()
    for uid, u in c.units.items():
        if u.get("id") != uid:
            err.append(f"{uid}: unit.yaml の id が {u.get('id')}")
        for key in ("prev", "next"):
            if u.get(key) and u[key] not in c.index:
                err.append(f"{uid}: {key}={u[key]} が一覧にない")
        for key in ("prereq", "used_by"):
            for ref in u.get(key, []):
                if ref not in c.index:
                    err.append(f"{uid}: {key} の {ref} が一覧にない")
        for t in u.get("terms", []):
            if t not in c.terms:
                err.append(f"{uid}: 用語 {t} が terms.yaml にない")
        if u.get("domain") not in c.shared["domains"]:
            err.append(f"{uid}: domain {u.get('domain')} が未定義")
        for sid in c.stage_ids:
            if u["bodies"].get(sid) is None:
                err.append(f"{uid}: 本文 {sid}.md がない")
            if sid not in u.get("stage_goals", {}):
                err.append(f"{uid}: stage_goals に {sid} がない")
        # 問題
        used = {}
        for sid, body in u["bodies"].items():
            for m in TOKEN.finditer(body or ""):
                kind, arg = m.group(1), m.group(2)
                if kind == "problem":
                    q = u["problems"].get(arg)
                    if not q:
                        err.append(f"{uid}/{sid}: 問題 {arg} が見つからない")
                        continue
                    if q["stage"] != sid:
                        err.append(f"{uid}/{sid}: 問題 {arg} の stage は {q['stage']}")
                    used[arg] = used.get(arg, 0) + 1
                else:
                    err += _check_token(c, f"{uid}/{sid}", kind, arg)
        for qid, q in u["problems"].items():
            if qid in seen_q:
                err.append(f"問題 id が重複：{qid}")
            seen_q.add(qid)
            if not qid.startswith(f"Q-{uid}-"):
                err.append(f"{qid}: id は Q-{uid}-NNN の形にする")
            if q.get("format") not in FORMATS:
                err.append(f"{qid}: format が不正 {q.get('format')}")
            for p in q.get("powers", []):
                if p not in c.powers:
                    err.append(f"{qid}: power {p} が未定義")
            if q.get("format") == "choice" and not (q.get("choices") and q.get("correct")):
                err.append(f"{qid}: 5択には choices と correct が必要")
            if used.get(qid, 0) != 1:
                err.append(f"{qid}: 本文で {used.get(qid, 0)} 回使われている（1回にする）")
            for text in (q.get("prompt", ""), q.get("answer", "")):
                for m in TOKEN.finditer(text or ""):
                    err += _check_token(c, qid, m.group(1), m.group(2))
    return err


def _check_token(c: Course, where: str, kind: str, arg):
    if kind == "unit" and arg not in c.index:
        return [f"{where}: 単元 {arg} が一覧にない"]
    if kind == "term" and arg not in c.terms:
        return [f"{where}: 用語 {arg} がない"]
    if kind == "lab" and arg not in c.labs:
        return [f"{where}: ラボ {arg} がない"]
    if kind == "fig" and arg.split("|")[0] not in c.figures:
        return [f"{where}: 図 {arg} が assets.yaml にない"]
    if kind == "ref" and arg not in c.shared.get("refs", {}):
        return [f"{where}: 参照 {arg} が shared.yaml の refs にない"]
    if kind == "power" and arg not in c.powers:
        return [f"{where}: 力 {arg} がない"]
    if kind == "stage" and arg not in c.stage_ids:
        return [f"{where}: 段階 {arg} がない"]
    if kind == "shared" and arg not in c.shared:
        return [f"{where}: 共通文言 {arg} がない"]
    if kind not in {"unit", "term", "lab", "power", "stage", "shared", "icon", "problem", "fig", "ref",
                    "stages_table", "powers_list"}:
        return [f"{where}: 未知の部品 {{{{{kind}}}}}"]
    return []


def run_checks(c: Course) -> tuple[int, list[str]]:
    n, err = 0, []
    for uid, u in c.units.items():
        exprs = [(f"{uid}", e) for e in u.get("checks", [])]
        for qid, q in u["problems"].items():
            exprs += [(qid, e) for e in q.get("checks", [])]
        for where, e in exprs:
            n += 1
            try:
                if not run_check(e):
                    err.append(f"{where}: 検算が合わない → {e}")
            except Exception as ex:  # noqa: BLE001
                err.append(f"{where}: 検算式のエラー {ex} → {e}")
    return n, err
