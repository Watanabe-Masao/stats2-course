"""概念・関係・導出（知識ネットワークのデータ）の検証と書き出し。

原本：content/terms.yaml（説明のある用語＝概念）・content/relations.yaml・content/derivations.yaml
型：docs/knowledge-net/schema/kn-schema-v2.json で書き出す（元は knowledge-net。製本への移行 M4、#264）。
  組み立ては今の形（v1）で行い、to_v2 で v2 に写す。移していない分類の関係は legacy_type（v1 の種類の名前）のまま書く（設計書 docs/schema-v2-design.md 8）。
書き出し：out/site/net/<教材名>.json（公開サイトに載る。ネットワークの画面はこれだけを読む）
"""
from __future__ import annotations

import json
import re
import math

from model import CONTENT, ROOT, Course, load_yaml, run_check
import term_icons  # 語の印（#220）
from effects import effect_errors, question_errors

SCHEMA = ROOT / "docs" / "knowledge-net" / "schema" / "kn-schema-v1.json"
SCHEMA_V2 = ROOT / "docs" / "knowledge-net" / "schema" / "kn-schema-v2.json"   # 書き出す型（M4。#264）
EXPERIMENT_SCHEMA = ROOT / "docs" / "knowledge-net" / "schema" / "kn-experiment-v1.json"   # 実験室の拡張（芯の experiments が指す。#211）
RELATION_TYPES = ROOT / "docs" / "knowledge-net" / "schema" / "relation-types.yaml"   # 種類の定義（どの教材も共通）
KIND = load_yaml(RELATION_TYPES)
TYPES = tuple(KIND["types"])
TYPES_V2 = tuple(KIND["types_v2"])   # 製本 ⑤ の種類。原本の relations.yaml に v1 の行と並べて書く（v1 と名前は重ならない。#287）
V2_FIELDS = ("fix", "fix_text", "claim", "properties", "operation", "theorem", "reversible", "use_form", "from_form", "to_form", "same", "differ")
# 同じ働きの v1 と v2 の種類（build の決まりを両方に当てる所で使う）。意味が ⑤ に合うかは移すときに決める（設計書 3.3）
DEFINES = ("材料", "定める")
KIND_OF = ("種類", "一種")
FILLED_FIELDS = ("definition", "principle", "conditions", "example", "counterexample")
TEXT_FIELDS = ("definition", "principle", "example", "counterexample")
OPTIONAL_FIELDS = ("formulas", "misconceptions", "sources")
NS = re.compile(r"^[a-z0-9-]+:")


# 式の分解の木（kn-schema の formulaNode）。葉の記号・関数の名前・動かす記号は、その式の symbols の key を指す。
# 次の関数だけは記号に書かなくてよい（どの式でも同じ意味）。計算・展開・表示は math-lab（#72）。
BUILTIN_FN = {"exp", "log", "gt", "ge", "lt", "le", "between"}
TREE_OPS = {"eq", "add", "sub", "mul", "div", "pow", "neg", "sqrt", "abs", "sum", "prod", "int", "fn"}


def tree_errors(node, keys: set) -> list[str]:
    err: list[str] = []

    def walk(n) -> None:
        if not isinstance(n, dict):
            err.append(f"節が辞書でない（{n!r}）")
            return
        if "sym" in n:
            if n["sym"] not in keys:
                err.append(f"記号 {n['sym']} が symbols の key にない")
            return
        if "num" in n:
            return
        o = n.get("op")
        if o not in TREE_OPS:
            err.append(f"知らない演算 {o}")
        if o == "fn" and n.get("name") not in keys and n.get("name") not in BUILTIN_FN:
            err.append(f"関数 {n.get('name')} が symbols の key にない（{'・'.join(sorted(BUILTIN_FN))} は書かなくてよい）")
        if o in ("sum", "prod", "int") and n.get("var") and n["var"] not in keys:
            err.append(f"動かす記号 {n['var']} が symbols の key にない")
        if not n.get("args"):
            err.append(f"{o} に args がない")
        for a in n.get("args", []) + [n[k] for k in ("lower", "upper") if k in n]:
            walk(a)

    walk(node)
    return err


def course_id(c: Course) -> str:
    return c.shared.get("course", {}).get("id", "stats2")


def _first(prompt: str, limit: int = 120) -> str:
    """問題文の始め（一覧に出す1行）。記法の印と改行を落とし、長ければ … で切る"""
    t = re.sub(r"\$\$?|\*\*|\{\{[^}]*\}\}|^\s*[-^>]\s*", "", prompt.strip().split("\n\n")[0], flags=re.M)
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    return t if len(t) <= limit else t[: limit - 1] + "…"


def load_network() -> tuple[list[dict], list[dict]]:
    rel = (load_yaml(CONTENT / "relations.yaml") or {}).get("relations", []) if (CONTENT / "relations.yaml").exists() else []
    der = (load_yaml(CONTENT / "derivations.yaml") or {}).get("derivations", []) if (CONTENT / "derivations.yaml").exists() else []
    from conditions import normalize_relation   # 成立条件の区分（#249）
    for r in rel:
        normalize_relation(r)
    return rel, der


def load_experiments() -> list[dict]:
    """実験室の定義（#102・計画の 6 の骨格 1）：content/experiments.yaml"""
    path = CONTENT / "experiments.yaml"
    return (load_yaml(path) or {}).get("experiments", []) if path.exists() else []


def table_errors(eid: str, x: dict) -> list[str]:
    """値の表の実験（#119）：値は小さい順で重なりなし、呼び名・重みは値と同じ数、重みは0以上で合計が正。前と変えた重みは違うこと"""
    err: list[str] = []
    def one(where: str, values: list, weights: dict, labels) -> None:
        if not values or any(b <= a for a, b in zip(values, values[1:])):
            err.append(f"{eid}: {where} の values は小さい順で重ならない（1つ以上）")
        if labels is not None and len(labels) != len(values):
            err.append(f"{eid}: {where} の labels は values と同じ数")
        for k, w in weights.items():
            if len(w) != len(values):
                err.append(f"{eid}: {where} の {k} は values と同じ数")
            elif any(v < 0 for v in w) or not sum(w) > 0:
                err.append(f"{eid}: {where} の {k} は0以上で、合計が0より大きい")
    for t in x.get("themes") or []:
        one(f"テーマ {t.get('id')}", t.get("values") or [], {"start": t.get("start") or [], "compare": t.get("compare") or []}, t.get("labels"))
        if t.get("start") == t.get("compare"):
            err.append(f"{eid}: テーマ {t.get('id')} の start と compare が同じ（問いで何も変わらない）")
    for b in x.get("counterexamples") or []:
        one(f"反例 {b.get('id')}", b.get("values") or [], {"weights": b.get("weights") or []}, b.get("labels"))
    return err



# 応用の課題の求め方（math-lab engine の ApplySolve。#171）と解き方の公式の記号（engine の WALK_FORMULAS）は、
# engine が書き出した JSON の写し（docs/math-lab/contracts.json。build/sync_schema.py で取り込む）から読む。ここに書き写さない（#208）
_CONTRACTS = json.loads((ROOT / "docs" / "math-lab" / "contracts.json").read_text(encoding="utf-8"))
APPLY_METHODS = {m: f["required"] for m, f in _CONTRACTS["apply_methods"].items()}   # method ごとの条件の項目
APPLY_OPTIONAL = {m: f["optional"] for m, f in _CONTRACTS["apply_methods"].items() if f["optional"]}   # 実験室の道具の刻みに合わせる（省くと1）
APPLY_CHOICES = {m: f["choices"] for m, f in _CONTRACTS["apply_methods"].items() if "choices" in f}   # 選ぶ形の答えの選び肢の数（engine の answer が番号）


WALK_ORDER = ["ask", "unit", "event", "info", "relate", "formula", "build", "probe"]
WALK_FORMULAS = _CONTRACTS["walk_formulas"]   # 公式ごとの記号（枠の順）


def solve_value(sv: dict, path: str) -> float | None:
    """情報の of を solve から求める（math-lab の solveValue と同じ）。a.n のように . でたどり、足し引き・掛け算で書ける（掛け算が先）"""
    def one(t: str):
        if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", t):
            return float(t)
        v: object = sv
        for part in t.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    total = 0.0
    for term in re.split(r"(?=[+-])", re.sub(r"\s+", "", path)):
        if not term:
            continue
        sign = -1 if term.startswith("-") else 1
        prod = 1.0
        for f in term.lstrip("+-").split("*"):
            x = one(f)
            if x is None:
                return None
            prod *= x
        total += sign * prod
    return total


def walk_errors(iid: str, ap: dict) -> list[str]:
    """解き方を組み立てる（walk。#181・骨格設計）を確かめる。数の値は原本に書かず、文の中の数と solve の値が同じかを見る
    （想定する故障：課題の文の数を直して solve を直し忘れる・その逆。文をつなぐと課題と違う。押させる区切りがない〔進めない〕。
    段の順の崩れ。公式の記号に当てはめる情報がない。正解の番号が選び肢の外）。
    公式の値と応用の答えが同じかは、公開の JSON を engine で解く knowledge-net のテストが見る"""
    err: list[str] = []
    w, sv = ap.get("walk") or {}, ap.get("solve") or {}
    segs, info = w.get("segments") or [], w.get("info") or {}
    if "".join(g.get("text", "") for g in segs) != ap.get("task"):
        err.append(f"{iid} の walk：segments をつなぐと task と違う")
    asks = [g for g in segs if g.get("role") == "ask"]
    if len(asks) != 1 or not asks[0].get("key"):
        err.append(f"{iid} の walk：聞かれている所（role: ask・key あり）がちょうど1つでない")
    keys = {g.get("key") for g in segs if g.get("key")}
    for g in segs:
        if g.get("role") in ("info", "event", "condition") and g.get("key") not in info:
            err.append(f"{iid} の walk：区切り「{g.get('text')}」の key が info にない")
    for k, v in info.items():
        hit = [g for g in segs if g.get("key") == k]
        if len(hit) != 1:
            err.append(f"{iid} の walk：情報 {k} が文の中にちょうど1つでない"); continue
        if not v.get("of"):
            continue
        val = solve_value(sv, str(v["of"]))
        m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(%|ポイント)?", hit[0]["text"])   # 割合の差の「ポイント」も % と同じく 1/100（#199）
        num = (float(m.group(1)) / (100 if m.group(2) else 1)) if m else None
        # 文の数に符号は書かない（「50 円払う」は solve の -50）。向きは言葉が担うので、大きさを比べる
        if val is None or num is None or abs(num - abs(val)) > 1e-9:
            err.append(f"{iid} の walk：情報 {k}（文「{hit[0]['text']}」）と solve の {v.get('of')}（{val}）が違う")
    got = {k for k, v in info.items() if v.get("of")}
    for f in w.get("formulas") or []:
        syms = WALK_FORMULAS.get(f.get("ref"))
        if syms is None:
            err.append(f"{iid} の walk：公式 {f.get('ref')} を engine が知らない（{'・'.join(WALK_FORMULAS)}）"); continue
        for sym in syms:
            if (f.get("bind") or {}).get(sym) not in got:
                err.append(f"{iid} の walk：公式 {f.get('id')} の記号 {sym} に当てはめる情報か前の公式がない")
        got.add(f.get("id"))
    kinds = [st.get("kind") for st in w.get("steps") or []]
    idx = [WALK_ORDER.index(k) if k in WALK_ORDER else -1 for k in kinds]
    if any(b <= a for a, b in zip(idx, idx[1:])) or -1 in idx:
        err.append(f"{iid} の walk：段の順が {'→'.join(WALK_ORDER)} でない（同じ段も2つ置かない）")
    for k in ("ask", "info", "formula", "build"):
        if k not in kinds:
            err.append(f"{iid} の walk：段 {k} がない（問い・情報・公式・当てはめは省かない）")
    def quiz(q: dict, where: str) -> None:
        if not 0 <= int(q.get("ok", -1)) < len(q.get("opts") or []):
            err.append(f"{iid} の walk：{where}の正解の番号が選び肢の外")
        if len(q.get("fb") or []) != len(q.get("opts") or []):
            err.append(f"{iid} の walk：{where}の fb の数が選び肢と違う")
    for i, st in enumerate(w.get("steps") or [], start=1):
        if st.get("mark") and st["mark"] not in keys:
            err.append(f"{iid} の walk：段 {i} の mark {st['mark']} が文にない")
        for k in ((st.get("collect") or {}).get("need") or []) + ((st.get("collect") or {}).get("later") or []):
            if k not in keys:
                err.append(f"{iid} の walk：段 {i} の collect の {k} が文にない")
        for j, q in enumerate(st.get("choose") or [], start=1):
            quiz(q, f"段 {i} の問い {j} ")
        for k, q in (st.get("rowQuiz") or {}).items():
            quiz(q, f"段 {i} の計算の問い {k} ")
    return err


WALK_TEXTS = CONTENT / "walk-texts.yaml"   # 解き方の公式の文（engine は文の型の id・穴の値・別の言い方だけを返す。#211）


def load_walk_texts() -> dict:
    return (load_yaml(WALK_TEXTS) or {}) if WALK_TEXTS.exists() else {}


def walk_texts_errors(t: dict) -> list[str]:
    """解き方の公式の文が engine の表（contracts.json の walk_formulas・walk_rows）とちょうど合うか
    （想定する故障：engine が行や穴を足したのに文がない〔画面に文が出ない・{x} のまま出る〕・別の言い方の名前の書き違い・
    使われない文が残る・記号の意味の書き漏らし）"""
    err: list[str] = []
    spec = _CONTRACTS.get("walk_rows") or {}
    fs = t.get("formulas") or {}
    for ref in sorted(set(WALK_FORMULAS) - set(fs)):
        err.append(f"walk-texts：公式 {ref} の文がない")
    for ref in sorted(set(fs) - set(WALK_FORMULAS)):
        err.append(f"walk-texts：公式 {ref} は engine にない")
    syms = t.get("symbols") or {}
    for ref, f in fs.items():
        if ref not in WALK_FORMULAS:
            continue
        for k in ("word", "pick"):
            if not str(f.get(k) or "").strip():
                err.append(f"walk-texts：{ref} の {k} がない")
        for s in WALK_FORMULAS[ref]:
            if s not in syms and s not in (f.get("mean") or {}):
                err.append(f"walk-texts：{ref} の記号 {s} の意味がない（symbols か mean に書く）")
        rows, want = f.get("rows") or {}, spec.get(ref) or {}
        for rid in sorted(set(want) - set(rows)):
            err.append(f"walk-texts：{ref} の行 {rid} の文がない")
        for rid in sorted(set(rows) - set(want)):
            err.append(f"walk-texts：{ref} の行 {rid} は engine が返さない")
        for rid, r in rows.items():
            if rid not in want:
                continue
            vs, alts = set(want[rid]["vars"]), r.get("variants") or {}
            for name in sorted(set(want[rid]["variants"]) - set(alts)):
                err.append(f"walk-texts：{ref} の行 {rid} の別の言い方 {name} がない")
            for name in sorted(set(alts) - set(want[rid]["variants"])):
                err.append(f"walk-texts：{ref} の行 {rid} の別の言い方 {name} は engine が返さない")
            for where, s in [("title", r.get("title")), ("why", r.get("why"))] + [(f"{a}.{k}", v) for a, o in alts.items() for k, v in (o or {}).items()]:
                for h in re.findall(r"\{(\w+)\}", str(s or "")):
                    if h not in vs:
                        err.append(f"walk-texts：{ref} の行 {rid} の {where} の穴 {{{h}}} は engine が返さない（{'・'.join(sorted(vs)) or 'なし'}）")
    return err


APPLY_TEXTS = CONTENT / "apply-texts.yaml"   # 応用の解き方の段の文（engine は文の型の id・穴の値・別の言い方だけを返す。#211）


def load_apply_texts() -> dict:
    return (load_yaml(APPLY_TEXTS) or {}) if APPLY_TEXTS.exists() else {}


def apply_texts_errors(t: dict) -> list[str]:
    """応用の段の文が engine の表（contracts.json の apply_steps・apply_words）とちょうど合うか
    （想定する故障：engine が段・穴・別の言い方を足したのに文を書き忘れる・名前の書き違い・使われない文が残る・語の穴の言葉の書き漏らし）"""
    err: list[str] = []
    spec, words = _CONTRACTS.get("apply_steps") or {}, _CONTRACTS.get("apply_words") or {}
    steps, tw = t.get("steps") or {}, t.get("words") or {}
    for w, keys in words.items():
        for k in sorted(set(keys) - set(tw.get(w) or {})):
            err.append(f"apply-texts：語 {w} の {k} の言葉がない")
    for sid in sorted(set(spec) - set(steps)):
        err.append(f"apply-texts：段 {sid} の文がない")
    for sid in sorted(set(steps) - set(spec)):
        err.append(f"apply-texts：段 {sid} は engine が返さない")
    for sid, s in steps.items():
        if sid not in spec:
            continue
        vs, alts = set(spec[sid]["vars"]), s.get("variants") or {}
        if not str(s.get("title") or "").strip():
            err.append(f"apply-texts：段 {sid} の題がない")
        for name in sorted(set(spec[sid]["variants"]) - set(alts)):
            err.append(f"apply-texts：段 {sid} の別の言い方 {name} がない")
        for name in sorted(set(alts) - set(spec[sid]["variants"])):
            err.append(f"apply-texts：段 {sid} の別の言い方 {name} は engine が返さない")
        for where, v in [("title", s.get("title")), ("text", s.get("text"))] + [(f"{a}.{k}", x) for a, o in alts.items() for k, x in (o or {}).items()]:
            for h in re.findall(r"\{(\w+)\}", str(v or "")):
                if h not in vs:
                    err.append(f"apply-texts：段 {sid} の {where} の穴 {{{h}}} は engine が返さない（{'・'.join(sorted(vs)) or 'なし'}）")
    return err


def resolve_table_workspace(tw: dict) -> tuple[dict, list[str]]:
    """値の表の作業台の表を、実験室のテーマから作る（#119：同じ表を2か所に書かない）。
    原本は {experiment: EXP-…, theme: テーマ id, use: start か compare} だけを書き、値・重み・呼び名・単位はテーマから写す。
    公開の JSON は型の valueTable（id・name・values・weights …）。compare の表の id は「テーマ id-compare」"""
    err: list[str] = []
    exps = {x.get("id"): x for x in load_experiments()}
    out = []
    for ref in tw.get("tables") or []:
        x = exps.get(ref.get("experiment"))
        th = next((t for t in (x or {}).get("themes") or [] if t.get("id") == ref.get("theme")), None)
        use = ref.get("use", "start")
        if set(ref) - {"experiment", "theme", "use"}:
            err.append(f"table_workspace の表は experiment・theme・use だけで書く（値・重みは実験室のテーマから写す）：{ref}")
            continue
        if not x or x.get("model") != "table" or not th:
            err.append(f"table_workspace の表 {ref.get('experiment')}・{ref.get('theme')} が値の表の実験室のテーマにない")
            continue
        if use not in ("start", "compare"):
            err.append(f"table_workspace の表 {ref.get('theme')} の use は start か compare")
            continue
        tb = {"id": th["id"] if use == "start" else f"{th['id']}-compare",
              "name": th["name"] if use == "start" else f"{th['name']}（{th.get('change', '変えたあと')}）",
              "values": list(th["values"]), "weights": list(th[use])}
        for k in ("icon", "unit", "labels"):
            if th.get(k) is not None:
                tb[k] = th[k]
        out.append(tb)
    return {**{k: v for k, v in tw.items() if k != "tables"}, "tables": out}, err

def experiment_errors(c: Course, rel_ids: set, der_ids: set) -> list[str]:
    """実験の定義を確かめる：id・つなぐ概念と線・条件の範囲・テーマ・反例（崩す条件は概念の成り立つ条件の言葉で）。予想の答えは書かない（画面がモデルから求める）"""
    err: list[str] = []
    seen = set()
    for x in load_experiments():
        eid = x.get("id", "?")
        if not str(eid).startswith("EXP-"):
            err.append(f"{eid}: 実験の id は EXP- で始める")
        if eid in seen:
            err.append(f"{eid}: id が重なっている")
        seen.add(eid)
        links = x.get("links") or {}
        if not (links.get("concepts") or links.get("relations")):
            err.append(f"{eid}: つなぐ概念（concepts）か線（relations）を1つ以上書く")
        for ref in links.get("concepts") or []:
            if ref not in c.terms or not filled(c.terms[ref]):
                err.append(f"{eid}: links.concepts の {ref} が説明のある概念にない")
        for ref in links.get("relations") or []:
            if ref not in rel_ids and ref not in der_ids:
                err.append(f"{eid}: links.relations の {ref} が関係・導出にない")
        # テーマ体系（#163）：まとまりの下の問い。主概念・関連概念は用語にあること、開く問い（open）は説明のある主概念を持ち、
        # 開く先（shift・questions の id・break:反例の id）があること。open のない問いは作成中
        qids = {q.get("id") for q in x.get("questions") or []}
        cxids = {b.get("id") for b in x.get("counterexamples") or []}
        seen_items: set = set()
        opened: dict = {}
        for grp in x.get("catalog") or []:
            for it in grp.get("items") or []:
                iid = it.get("id")
                m = re.fullmatch(r"([a-z][a-z0-9]*)-([A-Z])-(\d{2})", str(iid))
                if not m or m.group(2) != grp.get("id"):
                    err.append(f"{eid}: テーマ体系の {iid} は 概念-まとまり-番号（例 binom-{grp.get('id')}-01）で、まとまりは {grp.get('id')}")
                elif m.group(1) != str((x.get("catalog") or [{}])[0].get("items", [{}])[0].get("id", "")).split("-")[0]:
                    err.append(f"{eid}: テーマ体系の {iid} の概念の部分が、ほかの問いとそろっていない")
                if iid in seen_items:
                    err.append(f"{eid}: テーマ体系の {iid} が重なっている")
                seen_items.add(iid)
                # 主（concept）は概念か関係（REL-…。2つの概念のつながりが主の問い。#169）。関連（related）は概念
                if it.get("concept") not in c.terms and it.get("concept") not in rel_ids:
                    err.append(f"{eid}: {iid} の主 {it.get('concept')} が用語にも関係にもない")
                for ref in list(it.get("related") or []):
                    if ref not in c.terms:
                        err.append(f"{eid}: {iid} の関連 {ref} が用語にない")
                op = it.get("open")
                if it.get("retired") and op:
                    err.append(f"{eid}: {iid} は使わない印（retired）なので open を書かない")
                # 応用の課題（#171）：開ける問いにだけ。答えは書かず、method ごとに条件の項目がそろうかだけを見る
                # （値が条件の外なら画面の engine が理由を言って止まり、knowledge-net のテストが公開の JSON の全部の課題を解いて止める）
                ap = it.get("apply")
                if ap:
                    if not op:
                        err.append(f"{eid}: {iid} の応用の課題（apply）は開ける問い（open のある問い）にだけ書く")
                    sv = ap.get("solve") or {}
                    need = APPLY_METHODS.get(sv.get("method"))
                    if need is None:
                        err.append(f"{eid}: {iid} の apply の method {sv.get('method')} を engine が知らない（{'・'.join(APPLY_METHODS)}）")
                    else:
                        miss = [k for k in need if k not in sv]
                        extra = [k for k in sv if k != "method" and k not in need and k not in APPLY_OPTIONAL.get(sv["method"], [])]
                        if miss or extra:
                            err.append(f"{eid}: {iid} の apply（{sv['method']}）の条件：足りない {miss}・余分 {extra}")
                    an = ap.get("answer") or {}
                    nopt = APPLY_CHOICES.get(sv.get("method"))
                    if nopt and (an.get("type") != "choice" or len(an.get("options") or []) != nopt):
                        err.append(f"{eid}: {iid} の apply（{sv.get('method')}）の答えは選ぶ形で、選び肢は {nopt} つ")
                    if not nopt and need is not None and (an.get("type") != "number" or not an.get("tol")):
                        err.append(f"{eid}: {iid} の apply（{sv.get('method')}）の答えは数（type: number）で、合っているとする幅 tol を書く")
                    if ap.get("walk"):
                        err += [f"{eid}: {e}" for e in walk_errors(iid, ap)]
                if op:
                    # 実験の仕組みは共有してよいが、同じ画面を開くだけで別の問いを実現した扱いにしない（渡辺さん 2026-11-02）
                    if op in opened:
                        err.append(f"{eid}: {iid} の open {op} は {opened[op]} と同じ。問いごとに予測・初期表示の違う入口を作るか、作成中にする")
                    opened.setdefault(op, iid)
                    for need in ("predict", "operate", "judge"):
                        if not it.get(need):
                            err.append(f"{eid}: {iid} は開ける問いなので {need}（予測・操作・理解判定）を書く")
                    if it.get("concept") in c.terms and not filled(c.terms[it["concept"]]):
                        err.append(f"{eid}: {iid} は開ける問いなので、主概念 {it['concept']} を先に説明のある概念にする")
                    ok = op == "shift" or op in qids or (op.startswith("break:") and op[6:] in cxids)
                    if not ok:
                        err.append(f"{eid}: {iid} の open {op} が問い・反例にない")
        vary = x.get("vary") or {}
        for where in ("start", "compare"):
            for k, v in (x.get(where) or {}).items():
                r = vary.get(k)
                if not r or not (r["min"] <= v <= r["max"]):
                    err.append(f"{eid}: {where}.{k}＝{v} が vary の範囲にない")
        for nx in x.get("next") or []:
            for k, v in (nx.get("set") or {}).items():
                r = vary.get(k)
                if not r or not (r["min"] <= v <= r["max"]):
                    err.append(f"{eid}: next の {k}＝{v} が vary の範囲にない")
        ids = [t.get("id") for t in x.get("themes") or []]
        if len(ids) != len(set(ids)):
            err.append(f"{eid}: テーマの id が重なっている")
        for t in x.get("themes") or []:
            if "p" in t and not (vary.get("p", {}).get("min", 0) <= t["p"] <= vary.get("p", {}).get("max", 1)):
                err.append(f"{eid}: テーマ {t.get('id')} の p が vary の範囲にない")
        for b in x.get("counterexamples") or []:
            m = b.get("mechanism") or {}
            if m.get("kind") == "urn" and not (m.get("total") and vary["n"]["max"] <= m["total"] and (m.get("success") is None or m["success"] <= m["total"])):
                err.append(f"{eid}: 反例 {b.get('id')}：箱（total）は取る数（n の最大）以上、当たり（success。省くと p×total）は total 以下")
            if m.get("kind") == "streak" and m.get("carry") is None:
                err.append(f"{eid}: 反例 {b.get('id')}：streak には carry を書く")
            if m.get("kind") == "mix" and m.get("spread") is None:
                err.append(f"{eid}: 反例 {b.get('id')}：mix には spread を書く")
            if b.get("concept") and (b["concept"] not in c.terms or not filled(c.terms[b["concept"]])):
                err.append(f"{eid}: 反例 {b.get('id')} の concept {b['concept']} が説明のある概念にない")
            # 崩す条件は、つなぐ概念の「成り立つ条件」の言葉で書く（どの条件の反例かを地図とそろえる）
            def math_conds(ref: str) -> list:
                cd = (c.terms.get(ref) or {}).get("conditions") or {}
                return cd.get("math", []) if isinstance(cd, dict) else []   # 形の違う条件は、その概念の検査が別に止める
            conds = [q for ref in links.get("concepts") or [] for q in math_conds(ref)]
            for part in str(b.get("breaks", "")).split("・"):
                if conds and not any(part.strip() and part.strip() in q for q in conds):
                    err.append(f"{eid}: 反例 {b.get('id')} の breaks「{part}」が、つなぐ概念の成り立つ条件にない")
        if x.get("model") == "table":
            err += table_errors(eid, x)
        err += effect_errors(eid, x)   # 反例の言い分（effect）を厳密な計算で確かめる（#118 層3）
        err += question_errors(eid, x)   # 入口の問い：確率の値の答えが目盛りの境目から離れているか（#161）
        rs = x.get("reason") or {}
        if rs.get("concept"):
            t = c.terms.get(rs["concept"])
            if not t or not filled(t):
                err.append(f"{eid}: reason.concept {rs['concept']} が説明のある概念にない")
            elif "formula" in rs and not (0 <= rs["formula"] < len(t.get("formulas") or [])):
                err.append(f"{eid}: reason.formula {rs['formula']} が {rs['concept']} の式にない")
        for bad in ("answer", "expect"):
            if bad in x or bad in (x.get("predict") or {}):
                err.append(f"{eid}: 予想の答え（{bad}）は書かない（公開の JSON に出てしまう。画面がモデルから求める）")
    return err


def filled(t: dict) -> bool:
    return bool(t.get("definition"))


def skeleton(t: dict) -> bool:
    """骨格：定義1文（short）だけあり、説明（definition）はまだ（#105・P1）"""
    return bool(t.get("short")) and not filled(t)


def linked_terms() -> set:
    rels, ders = load_network()
    linked = {r.get(k) for r in rels for k in ("from", "to")}
    return linked | {p for d in ders for p in d.get("premises", [])} | {d.get("conclusion") for d in ders}


def skeleton_gaps(c: Course) -> dict:
    """骨格の完了の条件（#105）で数えるもの：定義1文がない語・分類がない語・どの関係にもつながっていない語"""
    linked = linked_terms()
    return {
        "no_short": [tid for tid, t in c.terms.items() if not (t.get("short") or filled(t))],
        "no_category": [tid for tid, t in c.terms.items() if not t.get("category")],
        "isolated": [tid for tid, t in c.terms.items() if (t.get("short") or filled(t)) and tid not in linked],
    }


def skeleton_errors(c: Course) -> list[str]:
    """定義1文と分類の書き方。skeleton_required のときは、完了の条件（全語に定義1文と分類・孤立0）も止める"""
    err: list[str] = []
    cats = c.shared.get("concept_categories") or []
    for tid, t in c.terms.items():
        s = t.get("short")
        if s is not None:
            s = str(s).strip()
            if not s:
                err.append(f"{tid}: short（定義1文）が空")
            elif "。" in s.rstrip("。"):
                err.append(f"{tid}: short は1文で書く（途中に「。」がある）：{s}")
            elif len(s) > 80:
                err.append(f"{tid}: short は80字まで（{len(s)}字）")
        if t.get("category") is not None and t["category"] not in cats:
            err.append(f"{tid}: category「{t['category']}」が shared.yaml の concept_categories にない")
        if s and not t.get("category"):
            err.append(f"{tid}: 骨格（short）には category（分類）も書く")
    if c.shared.get("skeleton_required"):
        g = skeleton_gaps(c)
        err += [f"{tid}: 定義1文（short）か説明（definition）がない（骨格の完了の条件）" for tid in g["no_short"]]
        err += [f"{tid}: category（分類）がない（骨格の完了の条件）" for tid in g["no_category"]]
        err += [f"{tid}: どの関係・導出にもつながっていない（骨格の完了の条件：孤立0）" for tid in g["isolated"]]
    return err


GROUP_ID = re.compile(r"^GRP-[a-z0-9-]+$")


def relation_map_errors(c: Course, rels: list[dict]) -> list[str]:
    """関係図の決まり（docs/relation-map.md・設計書 2。#233）。
    まとまりの宣言と語の所属・種類の親の数・axis の置き場所はどの分類でも確かめ、
    移し終えた分類（shared.yaml の relation_map_ready）にだけ、書き終えたことの条件を止める。"""
    err: list[str] = []
    cats = c.shared.get("concept_categories") or []
    groups = c.shared.get("concept_groups") or []
    gcat: dict[str, str] = {}
    for gr in groups:
        gid = str(gr.get("id", "?"))
        if not GROUP_ID.match(gid):
            err.append(f"shared.yaml：まとまりの id {gid} は GRP- と小文字・数字・ハイフンで書く")
        if gid in gcat:
            err.append(f"shared.yaml：まとまりの id {gid} が重複")
        if gr.get("category") not in cats:
            err.append(f"shared.yaml：まとまり {gid} の category「{gr.get('category')}」が concept_categories にない")
        if not gr.get("name"):
            err.append(f"shared.yaml：まとまり {gid} に name がない")
        gcat[gid] = gr.get("category")
    for tid, t in c.terms.items():
        g = t.get("group")
        if g is None:
            continue
        if g not in gcat:
            err.append(f"{tid}: group の {g} が shared.yaml の concept_groups にない")
        elif gcat[g] != t.get("category"):
            err.append(f"{tid}: group {g} の分類（{gcat[g]}）と、語の category（{t.get('category')}）が違う")
    used = {t.get("group") for t in c.terms.values()}
    for gid in gcat:
        if gid not in used:
            err.append(f"shared.yaml：まとまり {gid} に属する語がない")
    ready = c.shared.get("relation_map_ready") or []
    for cat in ready:
        if cat not in cats:
            err.append(f"shared.yaml：relation_map_ready の {cat} が concept_categories にない")
    cat_of = {tid: t.get("category") for tid, t in c.terms.items()}
    parents: dict[str, list[str]] = {}
    for r in rels:
        rid = r.get("id", "?")
        if r.get("axis") and r.get("type") not in ("対比", "比べる"):
            err.append(f"{rid}: axis（比べる軸）は対比・比べるだけに書く")
        if r.get("type") in KIND_OF:
            parents.setdefault(r.get("from"), []).append(r.get("to"))
    for tid, ps in parents.items():
        if len(ps) > 1:
            err.append(f"{tid}: 種類の親が {len(ps)} つある（{'・'.join(ps)}）。1つにする（docs/relation-map.md 3）")
    # 移し終えた分類だけ：書き終えたことの条件
    for tid, t in c.terms.items():
        if t.get("category") in ready and not t.get("group"):
            err.append(f"{tid}: 分類「{t['category']}」は関係図に移したので、group（まとまり）を書く")
    for r in rels:
        rid = r.get("id", "?")
        if r.get("type") == "前提" and r.get("premise") == "mathematical" and cat_of.get(r.get("to")) in ready:
            err.append(f"{rid}: 分類「{cat_of[r['to']]}」は関係図に移したので、前提（mathematical）を材料か学ぶ順（前提 learning）に分ける")
        if r.get("type") == "対比" and not r.get("axis") and (cat_of.get(r.get("from")) in ready or cat_of.get(r.get("to")) in ready):
            err.append(f"{rid}: 関係図に移した分類の対比には axis（比べる軸）を書く")
    err += group_relation_errors(c, rels, gcat)
    return err


def group_relation_errors(c: Course, rels: list[dict], gcat: dict[str, str]) -> list[str]:
    """まとまりの間の関係（shared.yaml の group_relations。関係図の全体の見え方の矢印。#240）。
    矢印は裏付けの関係を少なくとも1本指し、指した関係の両端がそれぞれ from と to のまとまりにある（概念の段と食い違わない）。
    まとまりの組ごとに矢印は1本。種類は書かない（指した関係から画面が決める）"""
    err: list[str] = []
    by_id = {r.get("id"): r for r in rels}
    grp = {tid: t.get("group") for tid, t in c.terms.items()}
    seen: set[tuple[str, str]] = set()
    for i, gr in enumerate(c.shared.get("group_relations") or []):
        f, t = gr.get("from"), gr.get("to")
        at = f"shared.yaml：group_relations の {i + 1} 本目（{f} → {t}）"
        if f not in gcat or t not in gcat:
            err.append(f"{at}：from・to は concept_groups のまとまりにする")
            continue
        if f == t:
            err.append(f"{at}：同じまとまりどうしは結ばない")
        if gcat[f] != gcat[t]:
            err.append(f"{at}：分類の違うまとまりは結ばない（{gcat[f]}・{gcat[t]}）")
        if (f, t) in seen:
            err.append(f"{at}：同じ組の矢印が2本ある（組ごとに1本）")
        seen.add((f, t))
        if not gr.get("label"):
            err.append(f"{at}：label（矢印の言葉）がない")
        rs = gr.get("relations") or []
        cs = gr.get("claims") or []
        if not rs and not cs:
            err.append(f"{at}：relations（裏付けの関係）か claims（線にしない主張。型 v2 の改訂3）を1つ以上書く")
        claims = {cl.get("id"): cl for cl in load_claims()}
        for cid in cs:   # 主張の主語・述語の概念が、from と to のまとまりに1つずつある（概念の段と食い違わない）
            cl = claims.get(cid)
            if not cl:
                err.append(f"{at}：裏付けの主張 {cid} が claims.yaml にない")
                continue
            groups = {grp.get(x) for side in ("premises", "conclusion") for v in (cl.get(side) or {}).values() for x in v}
            if not {f, t} <= groups:
                err.append(f"{at}：裏付けの主張 {cid} の主語・述語の概念が {f} と {t} のまとまりにない")
        for rid in rs:
            r = by_id.get(rid)
            if not r:
                err.append(f"{at}：裏付けの {rid} が relations.yaml にない")
            elif (grp.get(r.get("from")), grp.get(r.get("to"))) != (f, t):
                err.append(f"{at}：裏付けの {rid} の両端（{r.get('from')} → {r.get('to')}）が {f} → {t} のまとまりにない")
    return err


from conditions import export_detail  # noqa: E402


def condition_errors(c: Course, rels: list[dict]) -> list[str]:
    """成立条件の区分（#249 ①）と基準にする定義の式（③）。区分を書いた行はどの分類でも確かめ、
    関係図に移した分類（relation_map_ready）では、概念の数学の行と、行き先がその分類の関係の行に区分を要る"""
    from conditions import DETAIL, _split, detail_errors
    ready = set(c.shared.get("relation_map_ready") or [])
    sources = {s["name"] for s in c.shared.get("sources", [])}
    terms = set(c.terms)
    cat_of = {tid: t.get("category") for tid, t in c.terms.items()}
    err: list[str] = []
    for tid, t in c.terms.items():
        cond = t.get("conditions")
        if isinstance(cond, dict):
            details = t.get(DETAIL) or [d for sc in ("math", "data") for d in _split(cond.get(sc), sc)[1]]
            err += detail_errors(tid, details, terms, sources, t.get("category") in ready and filled(t), False)
        bf = t.get("basis_formula")
        if bf is not None and bf not in {f.get("id") for f in t.get("formulas") or []}:
            err.append(f"{tid}: basis_formula の {bf} がこの概念の式（formulas）にない")
    for r in rels:
        if r.get("conditions"):
            details = r.get(DETAIL) or _split(r["conditions"], None)[1]
            err += detail_errors(r.get("id", "?"), details, terms, sources, cat_of.get(r.get("to")) in ready, True)
    return err


EXCLUDE_KINDS = ("言い換え", "使われる場", "計算の近道の式", "求める結果", "成り立つための条件",
                 "学ぶのに要るだけの知識", "操作の対象", "1つの概念の中の式・性質")   # ⑤ の構成の「構成要素にしないもの」（型 v2 の改訂2）


def tree_names(node) -> set[str]:
    """式の木に出る記号の key と関数の名前"""
    out: set[str] = set()
    if isinstance(node, dict):
        if "sym" in node:
            out.add(node["sym"])
        if node.get("op") == "fn" and node.get("name"):
            out.add(node["name"])
        for v in node.values():
            out |= tree_names(v)
    elif isinstance(node, list):
        for v in node:
            out |= tree_names(v)
    return out


def basis_candidates(t: dict, tid: str) -> set[str]:
    """基準の定義の式（basis_formula）の木に出る記号が指す概念（自分を除く）。定めるの候補（#86。⑤ では必要条件で、十分条件ではない）"""
    f = next((x for x in t.get("formulas") or [] if x.get("id") == t.get("basis_formula")), None)
    if f is None:
        return set()
    used = tree_names(f.get("tree"))
    return {s["concept"] for s in f.get("symbols") or [] if s.get("concept") and s.get("key") in used} - {tid}


INCLUSION = ("種類", "一般化", "一種", "特別な場合")   # 包含（v1 の一般化は ⑤ の特別な場合。from が to に含まれる）


def inclusion_ancestors(k: str, rels: list[dict]) -> set[str]:
    """包含の連なり（一種・特別な場合。混ざってよい）をたどった親の全部（⑤ の包含：親への一種を重ねて書かない。#290）"""
    up: dict[str, list[str]] = {}
    for r in rels:
        if r.get("type") in INCLUSION or r.get("legacy_type") in INCLUSION:
            up.setdefault(r["from"], []).append(r["to"])
    seen: set[str] = set()
    stack = list(up.get(k, []))
    while stack:
        x = stack.pop()
        if x not in seen:
            seen.add(x)
            stack += up.get(x, [])
    return seen


def basis_gaps(c: Course, rels: list[dict]) -> list[tuple[str, str]]:
    """定めるの候補のうち、材料（⑤ の定める）も、種類の親（⑤ の一種）も、除外（basis_excludes）もないもの：(候補の概念, 定義される概念)"""
    linked = {(r["from"], r["to"]) for r in rels if r.get("type") in DEFINES}
    linked |= {(a, k) for k in {x for r in rels for x in (r["from"], r["to"])} for a in inclusion_ancestors(k, rels)}   # 包含の親（⑤ の包含。#290）
    out = []
    for tid, t in c.terms.items():
        ex = {x.get("concept") for x in t.get("basis_excludes") or []}
        out += [(k, tid) for k in sorted(basis_candidates(t, tid)) if (k, tid) not in linked and k not in ex]
    return out


def basis_exclude_errors(c: Course, rels: list[dict]) -> list[str]:
    """基準の定義から外す概念（basis_excludes。型 v2 の basis.excludes。#86）の書き方。
    外すのは候補（基準の定義の式の木に出る記号の概念）だけで、材料と両方には書かない（どちらが判断か分からなくなる）"""
    err: list[str] = []
    mat = {(r["from"], r["to"]) for r in rels if r.get("type") in DEFINES}
    for tid, t in c.terms.items():
        xs = t.get("basis_excludes")
        if xs is None:
            continue
        if not t.get("basis_formula"):
            err.append(f"{tid}: basis_excludes は基準の定義の式（basis_formula）がある概念にだけ書く")
            continue
        cand = basis_candidates(t, tid)
        seen = set()
        for x in xs if isinstance(xs, list) else [xs]:
            if not isinstance(x, dict):
                err.append(f"{tid}: basis_excludes の行は concept・kind・text を持つ表で書く")
                continue
            k = x.get("concept")
            if set(x) - {"concept", "kind", "text"}:
                err.append(f"{tid}: basis_excludes の行は concept・kind・text だけ")
            if x.get("kind") not in EXCLUDE_KINDS:
                err.append(f"{tid}: basis_excludes の kind は ⑤ の「構成要素にしないもの」（{'・'.join(EXCLUDE_KINDS)}）のどれか。合わないときは ⑤ の未決にする")
            if not str(x.get("text") or "").strip():
                err.append(f"{tid}: basis_excludes の行に、外す理由の1文（text）を書く")
            if k in seen:
                err.append(f"{tid}: basis_excludes の {k} が重複")
            seen.add(k)
            if k not in cand:
                err.append(f"{tid}: basis_excludes の {k} は、基準の定義の式の木に出る記号の概念でない（外すものがない）")
            if (k, tid) in mat:
                err.append(f"{tid}: {k} を材料と basis_excludes の両方に書いている。どちらか1つにする")
    return err


def v2_source_errors(c: Course) -> list[str]:
    """原本の v2 だけの項目（#287）の書き方：概念の姿・基準の定義の文・主張の参照と、claims.yaml の id。
    中身の形（主張の種類・条件の行など）は書き出しのあと型 v2 が、関係とのつながりは v2_checks が止める"""
    forms = set(json.loads(SCHEMA_V2.read_text(encoding="utf-8"))["$defs"]["form"]["enum"])
    claims = load_claims()
    ids = [cl.get("id") for cl in claims]
    err: list[str] = []
    for i in ids:
        if not re.match(r"^CLM-[0-9]+[a-z]?(-[a-z]+)?$", str(i)):
            err.append(f"claims.yaml：主張の id {i} は CLM-番号（④ の番号。例：CLM-13・CLM-28b・CLM-13-converse）")
    for i in {x for x in ids if ids.count(x) > 1}:
        err.append(f"claims.yaml：主張の id {i} が重複")
    for cl in claims:
        for side in ("premises", "conclusion"):
            for k, v in (cl.get(side) or {}).items():
                for tid in v:
                    if not NS.match(tid) and tid not in c.terms:
                        err.append(f"claims.yaml：{cl.get('id')} の {side}.{k} の {tid} が terms.yaml にない")
    for tid, t in c.terms.items():
        bad = set(t.get("forms") or []) - forms
        if bad:
            err.append(f"{tid}: forms の {'・'.join(sorted(bad))} は姿（① の 3：{'・'.join(sorted(forms))}）にない")
        if t.get("basis"):
            if t.get("basis_formula"):
                err.append(f"{tid}: 基準の定義は basis_formula（式）か basis（文）のどちらか1つ（① の 2）")
            if not str(t["basis"].get("text") or "").strip():
                err.append(f"{tid}: basis に定義の文（text）を書く")
            for x in t["basis"].get("terms") or []:
                if not NS.match(x) and x not in c.terms:
                    err.append(f"{tid}: basis.terms の {x} が terms.yaml にない")
        for x in t.get("claims") or []:
            if x not in ids:
                err.append(f"{tid}: claims の {x} が claims.yaml にない")
    return err


def dependency_errors(rels: list[dict]) -> list[str]:
    """定義の依存と前提知識は直接の1段だけ（#249 ③）。
    - 定義の依存の輪（材料の輪）は止める：A の定義に B、B の定義に A … は、どちらかが定義の構成要素でない
    - 重ねた前提知識は止める：A → D の前提知識があるのに、D から「前提をさかのぼる」種類をたどって A に着くなら、A → D は書かない
      （A → B → C → D なら D は C だけを持ち、A・B は C をたどって出す）"""
    err = [f"定義の依存の輪：{' → '.join(x)}（どちらかの材料が定義の構成要素でない。#249 ③）" for x in material_cycles(rels)]
    trace = {k for key in ("types", "types_v2") for k, v in (KIND.get(key) or {}).items() if v.get("trace")}
    back: dict[str, list[tuple[str, str]]] = {}
    for r in rels:
        if r.get("type") in trace:
            back.setdefault(r["to"], []).append((r["from"], r.get("id", "?")))
    for r in rels:
        if not (r.get("type") == "前提" and r.get("premise") == "learning"):
            continue
        a, d = r["from"], r["to"]
        stack = [x for x, rid in back.get(d, []) if rid != r.get("id")]
        seen = set(stack)
        while stack:
            x = stack.pop()
            for y, _ in back.get(x, []):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        if a in seen:
            err.append(f"{r.get('id')}: {a} → {d} の前提知識は、{d} の前提をたどると {a} に着くので重ねて書かない（直接の1段だけ。#249 ③）")
    return err


def material_cycles(rels: list[dict] | None = None) -> list[list[str]]:
    """材料の輪（A の材料に B、B の材料に A …）。dependency_errors が止める（#249 ③）"""
    if rels is None:
        rels, _ = load_network()
    nxt: dict[str, list[str]] = {}
    for r in rels:
        if r.get("type") in DEFINES:
            nxt.setdefault(r["from"], []).append(r["to"])
    cycles: list[list[str]] = []
    seen: set = set()
    state: dict[str, int] = {}
    stack: list[str] = []

    def walk(v: str) -> None:
        state[v] = 1
        stack.append(v)
        for w in nxt.get(v, []):
            if state.get(w) == 1:
                cyc = stack[stack.index(w):]
                key = frozenset(cyc)
                if key not in seen:
                    seen.add(key)
                    cycles.append(cyc + [w])
            elif not state.get(w):
                walk(w)
        stack.pop()
        state[v] = 2

    for v in list(nxt):
        if not state.get(v):
            walk(v)
    return cycles


# 図とラボで補う関係の種類（#95）。gist は必須、図がなければ build が警告する
VISUAL_TYPES = ("変換", "対比", "導出", "一般化")
VISUAL_TYPES_V2 = ("移る", "比べる", "導ける", "特別な場合")   # gist・図の決まり（#95）を v2 の行にも当てる


def relations_without_figures() -> list[str]:
    rels, _ = load_network()
    return [r["id"] for r in rels if r.get("type") in VISUAL_TYPES + VISUAL_TYPES_V2 and not r.get("figures")]


def play_of(lid: str, name: str | None, pre: dict) -> dict | None:
    """ラボの版を、ネットワークの画面が JS の部品で描く形にする（#188 04b・#192）。
    段の状態は tour.states（静止図と同じ重ね方）で作り、関係から開く解説には最後に「つまり」の段を足す。
    予想の答え（expect・why）と予想の形（predict）は出さない（公開の JSON に答えを出さない）。"""
    from tour import states, with_gist
    if not pre.get("mode"):
        return None
    pre = with_gist(lid, name or "", pre)
    out: dict = {"mode": pre["mode"]}
    for k in ("modes", "set", "task"):
        if pre.get(k):
            out[k] = pre[k]
    if pre.get("predict"):
        # 予想させる版の課題の文は問い（「…の確率は？」）。触るは答えの数をすぐ出すので、問いと答えが同時に出ないよう文を出さない（#188 07d）
        out.pop("task", None)
    if pre.get("tour"):
        t = pre["tour"]
        for k in ("kmax", "decimals"):
            if t.get(k) is not None:
                out[k] = t[k]
        out["steps"] = []
        for st, sx in zip(t["steps"], states(t)):
            step = {"title": st["title"], "text": st["text"], "states": [] if st.get("gist") else [sx["start"], *sx["frames"]]}
            for k in ("focus", "gist", "ms"):
                if st.get(k):
                    step[k] = st[k]
            out["steps"].append(step)
    return out


def validate_network(c: Course) -> list[str]:
    rels, ders = load_network()
    err: list[str] = []
    own = course_id(c) + ":"

    def known(ref: str, what: str, where: str, allow_rel: bool = False) -> None:
        if NS.match(ref):
            if ref.startswith(own):
                err.append(f"{where}: {what} の {ref} は自分の教材なので、教材名を付けずに書く")
            return  # 別の教材の概念。つながる先がまだ無くてもよい（画面で「未接続」と出す）
        if ref in c.terms or (allow_rel and ref in rel_ids):
            return
        err.append(f"{where}: {what} の {ref} が用語{'・関係' if allow_rel else ''}にない")

    # 語の印（全部の語にあり、動く物・外を指す物がない）と柱（どの分類もちょうど1つの柱に入る）。#220
    err += term_icons.icon_errors(list(c.terms))
    cats = c.shared.get("concept_categories") or []
    pillars = c.shared.get("concept_pillars") or []
    placed = [cat for p in pillars for cat in p.get("categories", [])]
    for cat in cats:
        if placed.count(cat) != 1:
            err.append(f"shared.yaml：分類 {cat} が柱（concept_pillars）に {placed.count(cat)} 回ある（ちょうど1回にする）")
    for cat in sorted(set(placed) - set(cats)):
        err.append(f"shared.yaml：柱の分類 {cat} が concept_categories にない")

    # 概念
    for tid, t in c.terms.items():
        if not filled(t):
            continue
        miss = [f for f in FILLED_FIELDS if not t.get(f)]
        if not (isinstance(t.get("version"), int) and t["version"] >= 1):
            err.append(f"{tid}: 説明のある概念には version（1以上の整数）を書く")
        if miss:
            err.append(f"{tid}: 概念の説明に {'・'.join(miss)} がない")
        cond = t.get("conditions")
        if cond is not None and not (isinstance(cond, dict) and cond.get("math")):
            err.append(f"{tid}: conditions は math（数学的な条件）と data（データに当てはめるときの条件）に分けて書く")
        for f in t.get("formulas", []):
            for s in f.get("symbols", []):
                if not (s.get("symbol") and s.get("meaning")):
                    err.append(f"{tid}: 記号には symbol と meaning を書く")
                if s.get("concept") and not NS.match(str(s["concept"])) and s["concept"] not in c.terms:
                    err.append(f"{tid}: 記号 {s.get('symbol')} の concept {s['concept']} が用語にない")
                # 記号と確率変数の対応（#109）：of は同じ式の確率変数（kind: rv）の key
                rvs = {x.get("key") for x in f.get("symbols", []) if x.get("kind") == "rv"}
                if s.get("of") and s["of"] not in rvs:
                    err.append(f"{tid}: 記号 {s.get('symbol')} の of {s['of']} が、同じ式の確率変数（kind: rv）の key にない")
                # 定義域（#109）：min ≦ max、値を入れられる記号（value・param・const・index）だけ
                d = s.get("domain")
                if d is not None:
                    if s.get("kind") not in ("value", "param", "const", "index"):
                        err.append(f"{tid}: 記号 {s.get('symbol')} に domain を書けるのは value・param・const・index だけ")
                    if not isinstance(d, dict) or set(d) - {"min", "max", "minOpen", "maxOpen", "integer", "nonzero"}:
                        err.append(f"{tid}: 記号 {s.get('symbol')} の domain は min・max・minOpen・maxOpen・integer・nonzero だけ")
                    else:
                        lo, hi = d.get("min"), d.get("max")
                        nums = {x.get("key") for x in f.get("symbols", []) if x.get("kind") in ("value", "param", "const", "index")}
                        for b in (lo, hi):   # 記号どうしの範囲（k ≦ n なら max: n）は、同じ式の値を入れられる記号
                            if isinstance(b, str) and (b not in nums or b == s.get("key")):
                                err.append(f"{tid}: 記号 {s.get('symbol')} の domain の {b} は、同じ式のほかの値・母数の記号の key で書く")
                        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and not lo <= hi:
                            err.append(f"{tid}: 記号 {s.get('symbol')} の domain は min ≦ max")
            if f.get("tree"):
                err += [f"{tid}: 式 {f.get('id')} の木：{e}" for e in tree_errors(f["tree"], {s.get("key") for s in f.get("symbols", []) if s.get("key")})]
            # 意味のかたまり（#110）：path は木の中の節を指す
            for part in f.get("parts", []):
                node = f.get("tree")
                for i in part.get("path", []):
                    node = (node or {}).get("args", [None] * (i + 1))[i] if isinstance(node, dict) and i < len(node.get("args", [])) else None
                if not (part.get("name") and part.get("meaning")):
                    err.append(f"{tid}: 式 {f.get('id')} の parts には path・name・meaning を書く")
                if not isinstance(node, dict) or not part.get("path"):
                    err.append(f"{tid}: 式 {f.get('id')} の parts の path {part.get('path')} が木の中の節を指していない")
            # なぜこの式で求まるかの段（型 rev30。#188）：段ごとに title・text、効く部品の番号は parts の中。2段以上
            wy = f.get("why")
            if wy is not None:
                steps = wy.get("steps") if isinstance(wy, dict) else None
                if not isinstance(steps, list) or len(steps) < 2:
                    err.append(f"{tid}: 式 {f.get('id')} の why には2段以上の steps を書く")
                else:
                    for j, st in enumerate(steps):
                        if not (isinstance(st, dict) and st.get("title") and st.get("text")):
                            err.append(f"{tid}: 式 {f.get('id')} の why の段 {j + 1} には title・text を書く")
                        elif any(not (isinstance(i, int) and 0 <= i < len(f.get("parts") or [])) for i in st.get("parts") or []):
                            err.append(f"{tid}: 式 {f.get('id')} の why の段 {j + 1} の部品の番号が parts の外")
                        # 文の中の [[番号]]（部品を式と同じ色の札で出す印。#188）も parts の中
                        elif any(not (0 <= int(m) < len(f.get("parts") or [])) for m in re.findall(r"\[\[(\d+)\]\]", str(st.get("text")))):
                            err.append(f"{tid}: 式 {f.get('id')} の why の段 {j + 1} の文の [[番号]] が parts の外")
                        # 文の札は、その段で式の上で濃く見せる部品と同じ（文と式の強調をそろえる。独立なレビューの指摘 2026-11-04）
                        elif st.get("parts") and {int(m) for m in re.findall(r"\[\[(\d+)\]\]", str(st.get("text")))} - set(st["parts"]):
                            err.append(f"{tid}: 式 {f.get('id')} の why の段 {j + 1} の文の [[番号]] が、その段の parts（式の上で濃く見せる部品）に入っていない")
        # 式の作業台（#110）：主役の式・動かす記号（定義域つき）・横軸の記号（上限つき）・期待値の式
        ws = t.get("workspace")
        if ws:
            fs = t.get("formulas", [])
            main = fs[ws["formula"]] if isinstance(ws.get("formula"), int) and ws["formula"] < len(fs) else None
            if not main or not main.get("tree"):
                err.append(f"{tid}: workspace の formula {ws.get('formula')} が木のある式を指していない")
            else:
                syms = {x.get("key"): x for x in main.get("symbols", [])}
                for k in ws.get("vary", []):
                    if k not in syms or not syms[k].get("domain"):
                        err.append(f"{tid}: workspace の vary {k} は主役の式の、定義域（domain）のある記号")
                o = syms.get(ws.get("over"))
                if not o or not (o.get("domain") or {}).get("integer") or (o.get("domain") or {}).get("max") is None:
                    err.append(f"{tid}: workspace の over {ws.get('over')} は主役の式の、上限のある整数の記号（棒を並べるため）")
            if "mean" in ws and not (isinstance(ws["mean"], int) and ws["mean"] < len(fs) and fs[ws["mean"]].get("tree")):
                err.append(f"{tid}: workspace の mean {ws.get('mean')} が木のある式を指していない")
            if "linear" in ws and not (isinstance(ws["linear"], int) and ws["linear"] < len(fs) and (fs[ws["linear"]].get("tree") or fs[ws["linear"]].get("ref"))):
                err.append(f"{tid}: workspace の linear {ws.get('linear')} が木のある式を指していない（変換の欄の E(aX＋b)。#156）")
        tw = t.get("table_workspace")
        if tw is not None:
            tw, terr = resolve_table_workspace(tw)
            err += [f"{tid}: {e}" for e in terr]
            fs = t.get("formulas") or []
            for field in ("formula", "linear"):
                if field == "linear" and field not in tw:
                    continue
                i = tw.get(field)
                if type(i) is not int or not 0 <= i < len(fs) or not fs[i].get("tree"):
                    err.append(f"{tid}: table_workspace の {field} は木のある式の番号")
            tables = tw.get("tables") or []
            if not tables:
                err.append(f"{tid}: table_workspace の tables は1つ以上")
            ids = set()
            for tb in tables:
                bid = tb.get("id")
                if bid in ids:
                    err.append(f"{tid}: table_workspace の表の id {bid} が重複")
                ids.add(bid)
                vals, ws = tb.get("values") or [], tb.get("weights") or []
                finite = lambda vs: all(type(v) in (int, float) and math.isfinite(v) for v in vs)
                if not vals or not finite(vals) or any(b <= a for a, b in zip(vals, vals[1:])):
                    err.append(f"{tid}: table_workspace の values は有限の数を小さい順で重ならずに書く")
                if len(ws) != len(vals) or not finite(ws) or any(w < 0 for w in ws) or not 0 < sum(ws) < float('inf'):
                    err.append(f"{tid}: table_workspace の weights は values と同じ数で0以上、合計は正の有限値")
                if "labels" in tb and len(tb["labels"]) != len(vals):
                    err.append(f"{tid}: table_workspace の labels は values と同じ数")
        for m in t.get("misconceptions", []):
            if not (m.get("misconception") and m.get("correction")):
                err.append(f"{tid}: よくある誤解には misconception と correction を書く")
        known_src = {s["name"] for s in c.shared.get("sources", [])}
        for s in t.get("sources", []):
            if s.get("source") not in known_src:
                err.append(f"{tid}: 出典 {s.get('source')} が shared.yaml の sources にない")
        has_num = any(re.search(r"[0-9０-９]", str(t.get(f, ""))) for f in TEXT_FIELDS + ("misconceptions",))
        if has_num and not t.get("checks") and not t.get("no_checks"):
            err.append(f"{tid}: 説明に数があるのに checks がない（計算した数でなければ no_checks: 理由）")
    # 関係
    rel_ids: set[str] = set()
    for r in rels:
        rid = r.get("id", "?")
        # このつながりが効く式の部品：両端の概念のどちらかの式で、その式の parts の番号の中（#188 07c）
        if r.get("focus"):
            fo = r["focus"]
            fs = [f for t in (r.get("from"), r.get("to")) for f in (c.terms.get(t) or {}).get("formulas", []) if isinstance(f, dict) and f.get("id") == fo.get("formula")]
            if not fs:
                err.append(f"{rid}: focus の式 {fo.get('formula')} が両端の概念の式にない")
            elif any(not (0 <= i < len(fs[0].get("parts") or [])) for i in fo.get("parts") or []):
                err.append(f"{rid}: focus の部品の番号が式 {fo.get('formula')} の parts の外")
        # 開いたときの段・図の一言に数があれば検算を書く（概念の説明と同じ決まり。#188 04）
        if re.search(r"[0-9０-９]", str(r.get("stages", "")) + str((r.get("chart") or {}).get("note", ""))) and not r.get("checks"):
            err.append(f"{rid}: 段・図の一言に数があるのに checks がない")
        if not str(rid).startswith("REL-"):
            err.append(f"{rid}: 関係の id は REL- で始める")
        if rid in rel_ids:
            err.append(f"{rid}: 関係の id が重複")
        rel_ids.add(rid)
    for r in rels:
        rid = r.get("id", "?")
        for k in ("from", "to"):
            known(str(r.get(k, "")), k, rid)
        if r.get("from") == r.get("to"):
            err.append(f"{rid}: from と to が同じ")
        if r.get("type") not in TYPES + TYPES_V2:
            err.append(f"{rid}: type「{r.get('type')}」は {'・'.join(TYPES)}（v1）か {'・'.join(TYPES_V2)}（製本 ⑤）のどれか")
        v2 = r.get("type") in TYPES_V2
        extra = [k for k in V2_FIELDS if k in r]
        if extra and not v2:
            err.append(f"{rid}: {'・'.join(extra)} は製本 ⑤ の種類（v2）の行にだけ書く")
        if not (isinstance(r.get("version"), int) and r["version"] >= 1):
            err.append(f"{rid}: version（1以上の整数）を書く")
        if not r.get("description"):
            err.append(f"{rid}: description がない")
        if r.get("type") in VISUAL_TYPES + VISUAL_TYPES_V2 and not r.get("gist"):   # つまりどういうことか（#95）
            err.append(f"{rid}: {r.get('type')}の関係には gist（つまり：日常の言葉で1〜2文）を書く")
        for need in ((KIND["types_v2"] if v2 else KIND["types"]).get(r.get("type")) or {}).get("required", []):
            if not r.get(need):
                err.append(f"{rid}: {r.get('type')} には {need} を必ず書く（relation-types.yaml）")
        if r.get("mode") and (r.get("type") not in ("変換", "移る") or r["mode"] not in KIND["modes"]):
            err.append(f"{rid}: mode は変換・移るだけに、{'・'.join(KIND['modes'])} のどれかで書く")
        if r.get("premise") and (r.get("type") != "前提" or r["premise"] not in KIND["premises"]):
            err.append(f"{rid}: premise は前提だけに、{'・'.join(KIND['premises'])} のどれかで書く")
    pairs = {(r.get("from"), r.get("to")) for r in rels if r.get("type") in ("一般化", "特殊化")}
    for a, b in pairs:
        if (b, a) in pairs:
            err.append(f"{a} と {b}：一般化・特殊化を両方向に書いている（片方だけにする）")
    for r in rels:
        rid = r.get("id", "?")
        for u in (r.get("basis") or {}).get("units", []):
            if u not in c.index:
                err.append(f"{rid}: basis の単元 {u} がない")
    # 導出
    der_ids: set[str] = set()
    for d in ders:
        did = d.get("id", "?")
        if not str(did).startswith("DER-"):
            err.append(f"{did}: 導出の id は DER- で始める")
        if did in der_ids:
            err.append(f"{did}: 導出の id が重複")
        der_ids.add(did)
        for p in d.get("premises", []):
            known(str(p), "premises", did, allow_rel=True)
        known(str(d.get("conclusion", "")), "conclusion", did, allow_rel=True)
        if not (isinstance(d.get("version"), int) and d["version"] >= 1):
            err.append(f"{did}: version（1以上の整数）を書く")
        for k in ("statement", "steps", "conditions"):
            if not d.get(k):
                err.append(f"{did}: {k} がない（導出には成立条件を必ず書く）")
        for u in (d.get("basis") or {}).get("units", []):
            if u not in c.index:
                err.append(f"{did}: basis の単元 {u} がない")
    # 図への参照（概念・関係の figures:）。図の id だけを書く。説明と URL は build が図の定義から作る
    def check_figs(owner: str, figs) -> None:
        for fid in figs or []:
            if not isinstance(fid, str):
                err.append(f"{owner}: figures に書けるのは図の id だけ（説明・URL は build が作る）")
            elif fid not in c.figures:
                err.append(f"{owner}: figures の {fid} がない（unit.yaml の figures か content/assets.yaml）")

    # ラボへの参照（概念・関係の labs:）。ラボと場面の版がある。値・学習目標はラボの側（tool.yaml）
    def check_labs(owner: str, labs) -> None:
        for lab in labs or []:
            lid, pre = lab.get("id"), lab.get("preset")
            if lid not in c.labs:
                err.append(f"{owner}: labs の {lid} がない")
            elif pre and pre not in (c.labs[lid].get("presets") or {}):
                err.append(f"{owner}: labs の {lid} に場面の版 {pre} がない（tool.yaml の presets）")
            if set(lab) - {"id", "preset", "purpose"}:
                err.append(f"{owner}: labs に書けるのは id・preset・purpose だけ（URL は build が作る）")
    for tid, t in c.terms.items():
        check_labs(tid, t.get("labs"))
        check_figs(tid, t.get("figures"))
    for r in rels:
        check_labs(r.get("id", "?"), r.get("labs"))
        check_figs(r.get("id", "?"), r.get("figures"))
    claim_ids = set()
    for cl in load_claims():   # 主張のラボ・図（型 v2 の改訂3。線にしない主張の解説の置き場。#289）
        claim_ids.add(cl.get("id"))
        check_labs(cl.get("id", "?"), cl.get("labs"))
        check_figs(cl.get("id", "?"), cl.get("figures"))
    # 問題 → 確かめる概念・関係・主張（concepts:）。説明のある概念か、ある関係・主張だけを指せる。
    # unit.yaml に concepts_linked: true がある単元は、retired 以外の全問に concepts: を書く。
    for uid, u in c.units.items():
        for qid, q in u["problems"].items():
            refs = q.get("concepts") or []
            if not isinstance(refs, list):
                err.append(f"{qid}: concepts は概念・関係の id の一覧で書く")
                continue
            for ref in refs:
                if NS.match(str(ref)):
                    continue
                if ref in rel_ids or ref in claim_ids:
                    continue
                if ref not in c.terms:
                    err.append(f"{qid}: concepts の {ref} が用語・関係・主張にない")
                elif not filled(c.terms[ref]):
                    err.append(f"{qid}: concepts の {ref} はまだ説明のない用語（概念にしてから指す）")
            if u.get("concepts_linked") and not q.get("retired") and not refs:
                err.append(f"{qid}: {uid} は concepts_linked なので、確かめる概念（concepts:）を書く")
    # 説明のある概念は、どこかの関係か導出につながっている（孤立させない）
    linked = {r.get(k) for r in rels for k in ("from", "to")}
    linked |= {p for d in ders for p in d.get("premises", [])} | {d.get("conclusion") for d in ders}
    for tid, t in c.terms.items():
        if filled(t) and tid not in linked:
            err.append(f"{tid}: 説明のある概念なのに、関係・導出のどれにもつながっていない")
    err += experiment_errors(c, rel_ids, {d["id"] for d in ders})
    if load_experiments():
        err += walk_texts_errors(load_walk_texts())
        err += apply_texts_errors(load_apply_texts())
    err += skeleton_errors(c)
    err += relation_map_errors(c, rels)
    err += condition_errors(c, rels)
    err += basis_exclude_errors(c, rels)
    err += v2_source_errors(c)
    err += dependency_errors(rels)
    return err


def network_checks(c: Course) -> list[tuple[str, str]]:
    rels, _ = load_network()
    return [(tid, e) for tid, t in c.terms.items() for e in t.get("checks", [])] + \
        [(r["id"], e) for r in rels for e in r.get("checks", [])]   # 関係を開いたときの段・図の一言の数（#188 04）


def lab_refs(c: Course, base: str, items) -> list[dict]:
    """概念・関係・主張のラボへの参照（公開の形）"""
    from labs import lab_url
    out = []
    for lab in items or []:
        if not base:
            continue   # 公開先がない配布先では、ラボへの参照を出さない
        aid = lab["id"] + (f"@{lab['preset']}" if lab.get("preset") else "")
        pre = (c.labs[lab["id"]].get("presets") or {}).get(lab.get("preset") or "", {})
        e = {"id": lab["id"], "url": lab_url(base, c, aid), "title": c.labs[lab["id"]].get("name", lab["id"]),
             "kind": "tour" if pre.get("tour") else "check"}   # ラボで解説／ラボで確かめる（版から判定。#90）
        for k in ("preset", "purpose"):
            if lab.get(k):
                e[k] = lab[k]
        if play_of(lab["id"], lab.get("preset"), pre):
            e["play"] = play_of(lab["id"], lab.get("preset"), pre)
        out.append(e)
    return out


def fig_refs(c: Course, base: str, ids) -> list[dict]:
    from labs import fig_url
    if not base:
        return []   # 公開先がない配布先では、図への参照を出さない
    return [{"id": f, "url": fig_url(base, f), **({"caption": c.figures[f]["caption"]} if c.figures[f].get("caption") else {})}
            for f in ids or []]


def export_network(c: Course, target: dict) -> dict:
    rels, ders = load_network()
    cid = course_id(c)

    def g(x: str) -> str:
        return x if NS.match(x) else f"{cid}:{x}"

    base = target.get("site_base_url") or ""

    def labs(items) -> list[dict]:
        return lab_refs(c, base, items)

    def figs(ids) -> list[dict]:
        return fig_refs(c, base, ids)

    units_of: dict[str, list[str]] = {}
    for uid, u in c.units.items():
        for tid in u.get("terms", []):
            units_of.setdefault(tid, []).append(g(uid))
    problems_of: dict[str, list[str]] = {}
    for u in c.units.values():
        for qid, q in u["problems"].items():
            for tid in q.get("concepts", []):
                problems_of.setdefault(tid, []).append(g(qid))
    referenced = {r[k] for r in rels for k in ("from", "to")} | {p for d in ders for p in d["premises"]} | {d["conclusion"] for d in ders}
    concepts = []
    for tid, t in c.terms.items():
        if not (filled(t) or skeleton(t) or tid in referenced):
            continue
        e = {"id": g(tid), "name": t["name"], "status": "filled" if filled(t) else "skeleton" if skeleton(t) else "stub", "version": t.get("version", 1),
             "units": units_of.get(tid, []), "problems": problems_of.get(tid, [])}
        for k in ("en", "short", "category"):
            if t.get(k):
                e[k] = t[k]
        if t.get("group"):   # 意味のまとまり（型の改訂35。docs/relation-map.md）
            e["group"] = g(t["group"])
        if base and term_icons.svg(tid):   # 語の印（build/term_icons.py が原本。公開サイトの icons/ に書く。#220）
            e["icon"] = f"{base.rstrip('/')}/icons/{tid}.svg"
        if filled(t):
            for k in ("definition", "principle", "formulas", "conditions", "example", "counterexample", "misconceptions", "workspace", "table_workspace", "gist", "question", "chart"):
                if t.get(k):
                    e[k] = t[k]
            if t.get("table_workspace"):
                e["table_workspace"] = resolve_table_workspace(t["table_workspace"])[0]   # 表は実験室のテーマから写す
            if t.get("_conditions_detail"):   # 成立条件の区分（型の改訂38。#249）
                e["conditions_detail"] = export_detail(t["_conditions_detail"], g, {x["name"]: x.get("url") for x in c.shared.get("sources", [])})
            if t.get("basis_formula"):
                e["basis_formula"] = t["basis_formula"]
            if t.get("formulas"):   # 記号が指す概念は、ネットワークの id（教材名:ID）にする
                e["formulas"] = [{**f, **({"symbols": [{**s, **({"concept": g(s["concept"])} if s.get("concept") else {})}
                                                       for s in f["symbols"]]} if f.get("symbols") else {}),
                                  **({"defined_in": g(f["defined_in"])} if f.get("defined_in") else {}),
                                  **c.formula_marks.get(f.get("id"), {})} for f in t["formulas"]]
            if labs(t.get("labs")):
                e["labs"] = labs(t.get("labs"))
            if figs(t.get("figures")):
                e["figures"] = figs(t.get("figures"))
            if t.get("sources"):
                url = {s["name"]: s.get("url") for s in c.shared.get("sources", [])}
                e["sources"] = [{"title": s["source"], **({"locator": s["locator"]} if s.get("locator") else {}),
                                 **({"url": url[s["source"]]} if url.get(s["source"]) else {})} for s in t["sources"]]
        concepts.append(e)
    pages = target.get("units") or {}
    stage_name = {st["id"]: st["name"] for st in c.stages}
    units = []
    for uid, meta in c.index.items():
        e = {"id": g(uid), "number": str(meta["number"]), "title": c.units[uid]["title"]}
        if pages.get(uid):
            e["url"] = f"https://app.notion.com/p/{pages[uid]}"
        # 学習・問題集のタブ（knowledge-net 型の改訂12。#42）：まとまり（領域の名前）と問題の一覧（id・段階・問題文の始め）
        dom = (c.shared.get("domains") or {}).get(c.units[uid].get("domain"), {}).get("name")
        if dom:
            e["group"] = re.sub(r"^[①-⑳]\s*", "", dom)
        probs = [{"id": g(qid), "stage": stage_name.get(q.get("stage"), q.get("stage") or ""), "prompt": _first(q.get("prompt") or "")}
                 for qid, q in c.units[uid]["problems"].items() if not q.get("retired")]
        if probs:
            e["problems"] = probs
        units.append(e)
    relations = []
    for r in rels:
        e = {"id": g(r["id"]), "version": r["version"], "from": g(r["from"]), "to": g(r["to"]), "type": r["type"],
             "description": r["description"], "units": [g(u) for u in (r.get("basis") or {}).get("units", [])]}
        for k in ("conditions", "mode", "premise", "axis", "gist", "question", "focus", "stages", "chart") + V2_FIELDS:   # axis は対比の比べる軸（改訂36）   # stages・chart は開いたときの段と図（#188 04）
            if r.get(k):
                e[k] = r[k]
        if (r.get("basis") or {}).get("derivation"):
            e["derivation"] = g(r["basis"]["derivation"])
        if r.get("_conditions_detail"):   # 成立条件の区分（型の改訂38。#249）
            e["conditions_detail"] = export_detail(r["_conditions_detail"], g, {x["name"]: x.get("url") for x in c.shared.get("sources", [])})
        if labs(r.get("labs")):
            e["labs"] = labs(r.get("labs"))
        if figs(r.get("figures")):
            e["figures"] = figs(r.get("figures"))
        relations.append(v2_ids(e, g) if r["type"] in TYPES_V2 else e)
    derivations = [{"id": g(d["id"]), "version": d["version"], "premises": [g(p) for p in d["premises"]], "conclusion": g(d["conclusion"]),
                    "statement": d["statement"], "steps": d["steps"], "conditions": d["conditions"],
                    "units": [g(u) for u in (d.get("basis") or {}).get("units", [])]} for d in ders]
    experiments = []
    for x in load_experiments():
        e = {k: v for k, v in x.items() if k not in ("links", "reason", "counterexamples")}
        e["id"] = g(x["id"])
        e["links"] = {k: [g(r) for r in v] for k, v in (x.get("links") or {}).items() if v}
        if x.get("reason"):
            e["reason"] = {**x["reason"], **({"concept": g(x["reason"]["concept"])} if x["reason"].get("concept") else {})}
        if x.get("catalog"):
            e["catalog"] = [{**grp, "items": [{**it, "id": g(it["id"]), "concept": g(it["concept"]), **({"related": [g(r) for r in it["related"]]} if it.get("related") else {})} for it in grp["items"]]} for grp in x["catalog"]]
        if x.get("counterexamples"):
            # effect（言い分の向き）は予想の答えになるので公開の JSON に出さない（画面は engine の mechanismMoments から求める）
            e["counterexamples"] = [{**{k: v for k, v in b.items() if k != "effect"}, **({"concept": g(b["concept"])} if b.get("concept") else {})} for b in x["counterexamples"]]
        experiments.append(e)
    revision = json.loads(SCHEMA.read_text(encoding="utf-8")).get("x-revision", 1)
    exp_revision = json.loads(EXPERIMENT_SCHEMA.read_text(encoding="utf-8")).get("x-revision", 1)
    return {"schema": "kn-schema", "version": 1, "schema_revision": revision, **({"experiment_revision": exp_revision} if experiments else {}),
            "course": {"id": cid, "title": c.shared.get("course", {}).get("title", cid), "units": units,
                       **({"pillars": c.shared["concept_pillars"]} if c.shared.get("concept_pillars") else {}),
                       # まとまり（改訂35）と、関係図に移した分類（改訂36）。docs/relation-map.md
                       **({"groups": [{"id": g(gr["id"]), "category": gr["category"], "name": gr["name"], **({"summary": gr["summary"]} if gr.get("summary") else {})}
                                      for gr in c.shared["concept_groups"]]} if c.shared.get("concept_groups") else {}),
                       **({"relation_map_ready": list(c.shared["relation_map_ready"])} if c.shared.get("relation_map_ready") else {}),
                       **({"group_relations": [{"from": g(x["from"]), "to": g(x["to"]), "label": x["label"],
                                                **({"relations": [g(rid) for rid in x["relations"]]} if x.get("relations") else {}),
                                                **({"claims": [g(cid) for cid in x["claims"]]} if x.get("claims") else {}),
                                                **({"note": x["note"]} if x.get("note") else {})}
                                               for x in c.shared["group_relations"]]} if c.shared.get("group_relations") else {})},
            "concepts": concepts, "relations": relations, "derivations": derivations, **({"experiments": experiments, "walk_texts": load_walk_texts(), "apply_texts": load_apply_texts()} if experiments else {})}


# 機械で写せる v1 の種類 → ⑤ の種類（設計書 3.3）。M4 では名前を書き出さず（legacy_type のまま）、未移行の数え方にだけ使う。
# 意味が ⑤ に合うかは、M5 の分類ごとの作業で振り分け直す
NAME_MAP_V2 = {"材料": "定める", "種類": "一種", "一般化": "特別な場合", "変換": "移る", "対比": "比べる"}


CLAIMS = CONTENT / "claims.yaml"   # 主張（製本 ④ の単位。原本へ移したもの。#287）
LOCAL_ID = re.compile(r"^(TERM|REL|DER|CLM|U[0-9])")


def load_claims() -> list[dict]:
    return (load_yaml(CLAIMS) or {}).get("claims", []) if CLAIMS.exists() else []


def _ns(cid: str):
    """教材の中の id に教材名を付ける（文はそのまま）"""
    return lambda x: f"{cid}:{x}" if isinstance(x, str) and LOCAL_ID.match(x) and not NS.match(x) else x


def export_claim(cl: dict, g, refs=None) -> dict:
    """主張（claims.yaml の1件）を型 v2 の claims の形に。id は教材名つき。refs はラボ・図の参照を公開の形にする (labs, figs)"""
    side = lambda x: {k: [g(i) for i in v] for k, v in (x or {}).items()}  # noqa: E731
    e = {k: v for k, v in cl.items() if k not in ("premises", "conclusion", "conditions", "grounds", "converse", "counterexamples", "units", "labs", "figures")}
    if refs:
        if refs[0](cl.get("labs")):
            e["labs"] = refs[0](cl.get("labs"))
        if refs[1](cl.get("figures")):
            e["figures"] = refs[1](cl.get("figures"))
    e["id"] = g(cl["id"])
    for k in ("premises", "conclusion"):
        if cl.get(k):
            e[k] = side(cl[k])
    if cl.get("conditions"):
        e["conditions"] = [{**x, **({"terms": [g(t) for t in x["terms"]]} if x.get("terms") else {}),
                            **({"subject": g(x["subject"])} if x.get("subject") else {}), "target": x.get("target", "claim")} for x in cl["conditions"]]
    if cl.get("grounds"):
        e["grounds"] = [{k: (g(v) if k in ("claim", "derivation") else v) for k, v in x.items()} for x in cl["grounds"]]
    if cl.get("converse"):
        e["converse"] = g(cl["converse"])
    for k in ("counterexamples", "units"):
        if cl.get(k):
            e[k] = [g(x) for x in cl[k]]
    return e


def v2_extras(c: Course, target: dict | None = None) -> dict:
    """原本の v2 だけの項目（v1 の型には置き場がない）を、書き出しの id で。to_v2 が置く。
    概念：姿（forms）・基準の定義の文（basis の text と terms）・除外（basis_excludes。#86）・主張（claims）。教材：主張（claims.yaml）"""
    g = _ns(course_id(c))
    concepts = {}
    for tid, t in c.terms.items():
        e = {}
        if t.get("forms"):
            e["forms"] = list(t["forms"])
        if t.get("basis"):
            e["basis"] = {"text": t["basis"]["text"], "terms": [g(x) for x in t["basis"].get("terms") or []]}
        if t.get("basis_excludes"):
            e["excludes"] = [{**x, "concept": g(x["concept"])} for x in t["basis_excludes"]]
        if t.get("claims"):
            e["claims"] = [g(x) for x in t["claims"]]
        if e:
            concepts[g(tid)] = e
    base = (target or {}).get("site_base_url") or ""
    refs = (lambda x: lab_refs(c, base, x), lambda x: fig_refs(c, base, x))
    return {"concepts": concepts, "claims": [export_claim(cl, g, refs) for cl in load_claims()]}


def v2_ids(r: dict, g) -> dict:
    """v2 の関係の項目のうち、id を指すもの（主張・性質・通す定理・通す操作が概念のとき）に教材名を付ける"""
    out = dict(r)
    for k in ("claim", "theorem", "operation"):
        if out.get(k):
            out[k] = g(out[k])
    if out.get("properties"):
        out["properties"] = [g(x) for x in out["properties"]]
    return out


def to_v2(data: dict, ready: list[str] | None = None, extras: dict | None = None) -> dict:
    """v1 の形で組み立てたデータを v2 に写す。v1 の種類の行は legacy_type（移していない行）、⑤ の種類の行は type のまま。
    移した分類（v2_ready）に legacy_type が残っていないかなどは v2_checks が止める"""
    extras = extras or {}
    out = {**data, "version": 2, "schema_revision": json.loads(SCHEMA_V2.read_text(encoding="utf-8")).get("x-revision", 1)}
    out["relations"] = [r if r.get("type") in TYPES_V2 else {("legacy_type" if k == "type" else k): v for k, v in r.items()}
                        for r in data["relations"]]
    # 基準の定義（v2 の basis）：basis_formula のある概念は、その式を基準にする（① の 2）。文の基準・除外（#86）・姿・主張もここに置く
    ex = extras.get("concepts") or {}
    out["concepts"] = []
    for c in data["concepts"]:
        e, x = dict(c), ex.get(c["id"], {})
        if c.get("basis_formula"):
            e["basis"] = {"formula": c["basis_formula"], **({"excludes": x["excludes"]} if x.get("excludes") else {})}
        elif x.get("basis"):
            e["basis"] = {**x["basis"], **({"excludes": x["excludes"]} if x.get("excludes") else {})}
        for k in ("forms", "claims"):
            if x.get(k):
                e[k] = x[k]
        out["concepts"].append(e)
    if extras.get("claims"):
        out["claims"] = extras["claims"]
    if ready:
        out["course"] = {**out["course"], "v2_ready": list(ready)}
    return out


def from_v2(data: dict, v1_revision: int) -> dict:
    """to_v2 の逆（M4 の完了の条件「今と同じ」を比べるため。設計書 8）：legacy_type を type に戻し、版を v1 にする"""
    out = {**data, "version": 1, "schema_revision": v1_revision}
    out["relations"] = [{("type" if k == "legacy_type" else k): v for k, v in r.items()} for r in data["relations"]]
    out["concepts"] = [{k: v for k, v in c.items() if k not in ("basis", "forms", "claims")} for c in data["concepts"]]   # v2 で足した項目
    out.pop("claims", None)
    out["course"] = {k: v for k, v in data["course"].items() if k != "v2_ready"}
    return out


def migration_counts(rels: list[dict]) -> dict:
    """製本への移行の残り（#264）：v1 の関係を、名前だけ機械で写せるもの（M5 で意味を振り分け直す）と、写せないもの（未移行）に分けて数える。
    前提は premise（mathematical・learning）ごとに分ける（mathematical は M5 で定める・条件・主張へ、learning は M6 で学ぶ順へ）"""
    named, left, v2 = {}, {}, 0
    for r in rels:
        t = r["type"]
        if t in TYPES_V2:
            v2 += 1
        elif t in NAME_MAP_V2:
            named[t] = named.get(t, 0) + 1
        else:
            key = f"{t}（{r.get('premise') or '区分なし'}）" if t == "前提" else t
            left[key] = left.get(key, 0) + 1
    return {"total": len(rels), "v2": v2, "named": named, "left": left}


def schema_errors(data: dict) -> list[str]:
    import jsonschema  # requirements.txt
    from referencing import Registry, Resource
    v1 = json.loads(SCHEMA.read_text(encoding="utf-8"))
    ext = json.loads(EXPERIMENT_SCHEMA.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_V2.read_text(encoding="utf-8")) if data.get("version") == 2 else v1
    # 芯と実験室の拡張は互いを $id（URL）で指す（v2 は v1 の部品も指す）。ネットには取りに行かず、写しを登録して解く
    reg = Registry().with_resources([(s["$id"], Resource.from_contents(s)) for s in (v1, schema, ext)])
    v = jsonschema.Draft202012Validator(schema, registry=reg)
    return [f"{'/'.join(map(str, e.absolute_path)) or '(全体)'}: {e.message}" for e in v.iter_errors(data)]


def write_network(data: dict) -> str:
    out = ROOT / "out" / "site" / "net"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{data['course']['id']}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


__all__ = ["relation_map_errors", "condition_errors", "dependency_errors", "material_cycles", "validate_network", "network_checks", "export_network", "to_v2", "from_v2", "migration_counts", "basis_gaps", "basis_candidates", "inclusion_ancestors", "v2_extras", "load_claims", "schema_errors", "write_network", "run_check"]
