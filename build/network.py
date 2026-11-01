"""概念・関係・導出（知識ネットワークのデータ）の検証と書き出し。

原本：content/terms.yaml（説明のある用語＝概念）・content/relations.yaml・content/derivations.yaml
型：docs/knowledge-net/schema/kn-schema-v1.json（リポジトリ knowledge-net を作るまでは、これが元）
書き出し：out/site/net/<教材名>.json（公開サイトに載る。ネットワークの画面はこれだけを読む）
"""
from __future__ import annotations

import json
import re
import math

from model import CONTENT, ROOT, Course, load_yaml, run_check
from effects import effect_errors

SCHEMA = ROOT / "docs" / "knowledge-net" / "schema" / "kn-schema-v1.json"
RELATION_TYPES = ROOT / "docs" / "knowledge-net" / "schema" / "relation-types.yaml"   # 種類の定義（どの教材も共通）
KIND = load_yaml(RELATION_TYPES)
TYPES = tuple(KIND["types"])
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


# 図とラボで補う関係の種類（#95）。gist は必須、図がなければ build が警告する
VISUAL_TYPES = ("変換", "対比", "導出", "一般化")


def relations_without_figures() -> list[str]:
    rels, _ = load_network()
    return [r["id"] for r in rels if r.get("type") in VISUAL_TYPES and not r.get("figures")]


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
        if r.get("type") not in TYPES:
            err.append(f"{rid}: type「{r.get('type')}」は {'・'.join(TYPES)} のどれか")
        if not (isinstance(r.get("version"), int) and r["version"] >= 1):
            err.append(f"{rid}: version（1以上の整数）を書く")
        if not r.get("description"):
            err.append(f"{rid}: description がない")
        if r.get("type") in VISUAL_TYPES and not r.get("gist"):   # つまりどういうことか（#95）
            err.append(f"{rid}: {r.get('type')}の関係には gist（つまり：日常の言葉で1〜2文）を書く")
        for need in (KIND["types"].get(r.get("type")) or {}).get("required", []):
            if not r.get(need):
                err.append(f"{rid}: {r.get('type')} には {need} を必ず書く（relation-types.yaml）")
        if r.get("mode") and (r.get("type") != "変換" or r["mode"] not in KIND["modes"]):
            err.append(f"{rid}: mode は変換だけに、{'・'.join(KIND['modes'])} のどれかで書く")
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
    # 問題 → 確かめる概念・関係（concepts:）。説明のある概念か、ある関係だけを指せる。
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
                if ref in rel_ids:
                    continue
                if ref not in c.terms:
                    err.append(f"{qid}: concepts の {ref} が用語・関係にない")
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
    err += skeleton_errors(c)
    return err


def network_checks(c: Course) -> list[tuple[str, str]]:
    return [(tid, e) for tid, t in c.terms.items() for e in t.get("checks", [])]


def export_network(c: Course, target: dict) -> dict:
    rels, ders = load_network()
    cid = course_id(c)

    def g(x: str) -> str:
        return x if NS.match(x) else f"{cid}:{x}"

    base = target.get("site_base_url") or ""

    def labs(items) -> list[dict]:
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
            out.append(e)
        return out

    def figs(ids) -> list[dict]:
        from labs import fig_url
        if not base:
            return []   # 公開先がない配布先では、図への参照を出さない
        return [{"id": f, "url": fig_url(base, f), **({"caption": c.figures[f]["caption"]} if c.figures[f].get("caption") else {})}
                for f in ids or []]

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
        if filled(t):
            for k in ("definition", "principle", "formulas", "conditions", "example", "counterexample", "misconceptions", "workspace", "table_workspace"):
                if t.get(k):
                    e[k] = t[k]
            if t.get("table_workspace"):
                e["table_workspace"] = resolve_table_workspace(t["table_workspace"])[0]   # 表は実験室のテーマから写す
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
        for k in ("conditions", "mode", "premise", "gist"):
            if r.get(k):
                e[k] = r[k]
        if (r.get("basis") or {}).get("derivation"):
            e["derivation"] = g(r["basis"]["derivation"])
        if labs(r.get("labs")):
            e["labs"] = labs(r.get("labs"))
        if figs(r.get("figures")):
            e["figures"] = figs(r.get("figures"))
        relations.append(e)
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
        if x.get("counterexamples"):
            # effect（言い分の向き）は予想の答えになるので公開の JSON に出さない（画面は engine の mechanismMoments から求める）
            e["counterexamples"] = [{**{k: v for k, v in b.items() if k != "effect"}, **({"concept": g(b["concept"])} if b.get("concept") else {})} for b in x["counterexamples"]]
        experiments.append(e)
    revision = json.loads(SCHEMA.read_text(encoding="utf-8")).get("x-revision", 1)
    return {"schema": "kn-schema", "version": 1, "schema_revision": revision,
            "course": {"id": cid, "title": c.shared.get("course", {}).get("title", cid), "units": units},
            "concepts": concepts, "relations": relations, "derivations": derivations, **({"experiments": experiments} if experiments else {})}


def schema_errors(data: dict) -> list[str]:
    import jsonschema  # requirements.txt
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '(全体)'}: {e.message}" for e in v.iter_errors(data)]


def write_network(data: dict) -> str:
    out = ROOT / "out" / "site" / "net"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{data['course']['id']}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


__all__ = ["validate_network", "network_checks", "export_network", "schema_errors", "write_network", "run_check"]
