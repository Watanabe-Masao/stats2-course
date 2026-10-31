"""原本（content/・tools/）を読み込み、型と参照を検証し、数値を検算する。

表示先（Notion・アプリ）に依存しない。表示は render_*.py が担当する。
"""
from __future__ import annotations

import itertools
import math
import statistics
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


class _StrictLoader(yaml.SafeLoader):
    """同じキーが2回出たら止める（後の値で黙って上書きされるのを防ぐ）。"""


def _mapping(loader, node, deep=False):
    keys = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise yaml.constructor.ConstructorError(None, None, f"キー {key!r} が重複している", k.start_mark)
        keys.add(key)
    return loader.construct_mapping(node, deep)


_StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_StrictLoader)  # noqa: S506 (SafeLoader を継承)


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
    "Fraction": Fraction, "math": math, "itertools": itertools, "statistics": statistics,
    "abs": abs, "round": round, "len": len, "sum": sum, "range": range,
    "all": all, "any": any, "zip": zip, "sorted": sorted, "min": min, "max": max,
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
    # 式の原本を整える（#118）：ref を元の式に、木から TeX を作る、契約を確かめる
    from formulas import CONTRACTS, prepare
    c.errors += prepare(terms, load_yaml(CONTRACTS) if CONTRACTS.exists() else None)
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
        unit["problems"] = {}
        for q in (load_yaml(pf) or []) if pf.exists() else []:
            if q["id"] in unit["problems"]:
                c.errors.append(f"{uid}: 問題 id が重複：{q['id']}")
            unit["problems"][q["id"]] = q
        c.units[uid] = unit
    from figures import register   # 問題・例題ごとの図（原本の figure: から作る）
    register(c)
    return c


# ---- 本文の構造 --------------------------------------------------------
CONTAINERS = {"toggle", "task", "ask", "key", "summary", "pattern", "warn", "info"}
_OPEN = re.compile(r"^:::\s*(\w+)\s*(.*)$")
_PROBLEM = re.compile(r"\{\{problem:([^}]+)\}\}")


@dataclass
class Block:
    kind: str                # container / problem / gray / line
    text: str = ""           # problem id・行の文
    name: str = ""           # 枠の種類
    title: str = ""          # 枠の題名
    inner: list = field(default_factory=list)
    line: int = 0


def parse_blocks(src: str, where: str = "", offset: int = 0) -> tuple[list[Block], list[str]]:
    """本文を枠・問題・灰色行・ふつうの行に分ける。書き間違い（閉じ忘れ・入れ子・未知の枠）は err に返す。"""
    blocks, err = [], []
    lines = src.splitlines()
    i = 0
    while i < len(lines):
        line, no = lines[i], offset + i + 1
        if line.strip() == ":::":
            err.append(f"{where}:{no}: 開始のない :::")
            i += 1
            continue
        m = _OPEN.match(line)
        if m:
            name, title = m.group(1), m.group(2).strip()
            if name not in CONTAINERS:
                err.append(f"{where}:{no}: 未知の枠 ::: {name}")
            j = i + 1
            while j < len(lines) and lines[j].strip() != ":::":
                if _OPEN.match(lines[j]):
                    err.append(f"{where}:{offset + j + 1}: 枠の中に枠は入れられない（::: {name} の中）")
                j += 1
            if j >= len(lines):
                err.append(f"{where}:{no}: ::: {name} が閉じていない")
            inner, e = parse_blocks("\n".join(lines[i + 1:j]), where, offset + i + 1)
            err += e
            blocks.append(Block("container", name=name, title=title, inner=inner, line=no))
            i = j + 1
            continue
        pm = _PROBLEM.fullmatch(line.strip())
        if pm:
            blocks.append(Block("problem", text=pm.group(1), line=no))
        elif line.startswith("^ "):
            blocks.append(Block("gray", text=line[2:], line=no))
        else:
            blocks.append(Block("line", text=line, line=no))
        i += 1
    return blocks, err


def walk(blocks: list[Block]):
    for b in blocks:
        yield b
        if b.kind == "container":
            yield from walk(b.inner)


# ---- 検証 ------------------------------------------------------------
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> set[str]:
    """文中の数（3桁区切りのカンマは外す）。"""
    text = TOKEN.sub("", text or "")
    return {n.replace(",", "").rstrip(".") for n in _NUM.findall(text)}


def validate(c: Course) -> list[str]:
    err = list(c.errors)
    texts: list[tuple[str, str]] = []          # (場所, 部品を含みうる文)
    for key, val in c.shared.items():
        if isinstance(val, str):
            texts.append((f"shared.{key}", val))
    for fid, f in c.figures.items():
        texts.append((fid, f.get("caption", "")))
    for uid, u in c.units.items():
        err += _validate_unit(c, uid, u, texts)
    for where, text in texts:
        for m in TOKEN.finditer(text or ""):
            err += _check_token(c, where, m.group(1), m.group(2))
    return err


def _validate_unit(c: Course, uid: str, u: dict, texts: list) -> list[str]:
    err = []
    if u.get("id") != uid:
        err.append(f"{uid}: unit.yaml の id が {u.get('id')}")
    for key in ("prev", "next"):
        if u.get(key) and u[key] not in c.index:
            err.append(f"{uid}: {key}={u[key]} が一覧にない")
    for key in ("prereq", "used_by"):
        for ref in u.get(key, []):
            if ref not in c.index:
                err.append(f"{uid}: {key} の {ref} が一覧にない")
    # 前提に書いた単元からは、使われる先としてこちらへ戻れるようにする（used_by は直接の前提より広くてよい）
    for ref in u.get("prereq", []):
        if ref in c.units and uid not in c.units[ref].get("used_by", []):
            err.append(f"{uid}: 前提の {ref} の used_by に {uid} がない")
    for t in u.get("terms", []):
        if t not in c.terms:
            err.append(f"{uid}: 用語 {t} が terms.yaml にない")
    for lid in u.get("labs", []):
        if lid not in c.labs:
            err.append(f"{uid}: labs の {lid} がない")
    if u.get("domain") not in c.shared["domains"]:
        err.append(f"{uid}: domain {u.get('domain')} が未定義")
    texts.append((f"{uid}.goal", u.get("goal", "")))
    for sid in c.stage_ids:
        if u["bodies"].get(sid) is None:
            err.append(f"{uid}: 本文 {sid}.md がない")
        for key in ("stage_goals", "evidence"):
            if sid not in (u.get(key) or {}):
                err.append(f"{uid}: {key} に {sid} がない")
            else:
                texts.append((f"{uid}.{key}.{sid}", u[key][sid]))

    probs = u["problems"]
    used: dict[str, int] = {}
    for sid, body in u["bodies"].items():
        where = f"{uid}/{sid}"
        blocks, e = parse_blocks(body or "", where)
        err += e
        last_diff = 0
        for b in walk(blocks):
            if b.kind == "problem":
                q = probs.get(b.text)
                if not q:
                    err.append(f"{where}:{b.line}: 問題 {b.text} が見つからない")
                    continue
                if q["stage"] != sid:
                    err.append(f"{where}:{b.line}: 問題 {b.text} の stage は {q['stage']}")
                used[b.text] = used.get(b.text, 0) + 1
                d = q.get("difficulty")
                if d:
                    if d < last_diff:
                        err.append(f"{where}:{b.line}: {b.text} の難度 {d} が前の問題より易しい（易→難の順にする）")
                    last_diff = d
            else:
                texts.append((f"{where}:{b.line}", b.text + " " + b.title))
                for m in _PROBLEM.finditer(b.text):
                    err.append(f"{where}:{b.line}: {{{{problem:...}}}} は1行に単独で書く")

    pending = u.get("visuals_pending")   # まだ図解を付け終えていない単元（付け終えたら消す）
    for sid, body in u["bodies"].items():
        if not pending:
            err += _check_examples(f"{uid}/{sid}", body or "")

    for qid, q in probs.items():
        err += _validate_problem(c, uid, qid, q, used.get(qid, 0), pending)
        texts += [(qid, q.get("prompt", "")), (qid, q.get("answer", ""))]
        texts += [(qid, t) for t in (q.get("choices") or [])]
        texts += [(qid, t) for t in (q.get("misconceptions") or {}).values()]
    return err


_EX_START = re.compile(r"^\*\*例題")
_EX_END = re.compile(r"^(\*\*例題|#{2,4} |\{\{problem:)")


def _check_examples(where: str, body: str) -> list[str]:
    """本文に書いた例題（**例題…）には、次の例題・見出し・問題までの間にラボか図を置く。"""
    err, start, has = [], None, False
    lines = body.splitlines() + ["### (終わり)"]
    for i, line in enumerate(lines, 1):
        if start is not None and _EX_END.match(line):
            if not has:
                err.append(f"{where}:{start}: 例題にラボか図がない（{{{{lab:…}}}} か {{{{fig:…}}}} を置く）")
            start = None
        if _EX_START.match(line):
            start, has = i, False
        if start is not None and ("{{lab:" in line or "{{fig:" in line):
            has = True
    return err


def _validate_problem(c: Course, uid: str, qid: str, q: dict, used: int, pending=False) -> list[str]:
    err = []
    if not pending and not q.get("retired") and not (q.get("lab") or q.get("figure") or q.get("no_visual")):
        err.append(f"{qid}: ラボか図がない（lab: か figure: を書く。どうしても要らないなら no_visual: 理由）")
    if not re.fullmatch(rf"Q-{uid}-\d{{3}}", qid):
        err.append(f"{qid}: id は Q-{uid}-NNN の形にする")
    if q.get("stage") not in c.stage_ids:
        err.append(f"{qid}: stage {q.get('stage')} が未定義")
    fmt = q.get("format")
    if fmt not in FORMATS:
        err.append(f"{qid}: format が不正 {fmt}")
    for p in q.get("powers", []):
        if p not in c.powers:
            err.append(f"{qid}: power {p} が未定義")
    if q.get("difficulty") not in (None, 1, 2, 3):
        err.append(f"{qid}: difficulty は 1・2・3")
    if not q.get("prompt") or not q.get("answer"):
        err.append(f"{qid}: prompt と answer が必要")
    want = 0 if q.get("retired") else 1
    if used != want:
        err.append(f"{qid}: 本文で {used} 回使われている（{'retired なので0回' if want == 0 else '1回'}にする）")
    if fmt == "choice":
        ch, k = q.get("choices") or [], q.get("correct")
        if not ch or not isinstance(k, int) or not 1 <= k <= len(ch):
            err.append(f"{qid}: choices と、その範囲の correct（1始まり）が必要")
        else:
            mis = {int(n) for n in (q.get("misconceptions") or {})}
            wrong = set(range(1, len(ch) + 1)) - {k}
            if mis - wrong:
                err.append(f"{qid}: misconceptions に正解や範囲外の番号 {sorted(mis - wrong)}")
            if q.get("tag") == "本番形式" and wrong - mis:
                err.append(f"{qid}: 本番形式は全ての誤答に誤解の説明が要る（不足 {sorted(wrong - mis)}）")
    # 答えで新しく出てくる数（問題文にない数）があるのに、検算がない
    new_nums = numbers(q.get("answer", "")) - numbers(q.get("prompt", "")) - numbers(" ".join(map(str, q.get("choices") or [])))
    new_nums = {n for n in new_nums if n not in {"0", "1"}}
    if new_nums and not q.get("checks") and not q.get("no_checks"):
        err.append(f"{qid}: 答えに新しい数 {sorted(new_nums, key=float)} があるのに checks がない"
                   f"（計算しない数なら no_checks に理由を書く）")
    return err


def _check_token(c: Course, where: str, kind: str, arg):
    if kind == "unit" and arg not in c.index:
        return [f"{where}: 単元 {arg} が一覧にない"]
    if kind == "term" and arg not in c.terms:
        return [f"{where}: 用語 {arg} がない"]
    if kind == "lab":
        lid, _, name = arg.partition("@")
        if lid not in c.labs:
            return [f"{where}: ラボ {lid} がない"]
        if name and name not in (c.labs[lid].get("presets") or {}):
            return [f"{where}: ラボ {lid} に場面 {name} がない（tool.yaml の presets）"]
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
