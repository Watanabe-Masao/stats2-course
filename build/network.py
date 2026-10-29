"""概念・関係・導出（知識ネットワークのデータ）の検証と書き出し。

原本：content/terms.yaml（説明のある用語＝概念）・content/relations.yaml・content/derivations.yaml
型：docs/knowledge-net/schema/kn-schema-v1.json（リポジトリ knowledge-net を作るまでは、これが元）
書き出し：out/site/net/<教材名>.json（公開サイトに載る。ネットワークの画面はこれだけを読む）
"""
from __future__ import annotations

import json
import re

from model import CONTENT, ROOT, Course, load_yaml, run_check

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


def load_network() -> tuple[list[dict], list[dict]]:
    rel = (load_yaml(CONTENT / "relations.yaml") or {}).get("relations", []) if (CONTENT / "relations.yaml").exists() else []
    der = (load_yaml(CONTENT / "derivations.yaml") or {}).get("derivations", []) if (CONTENT / "derivations.yaml").exists() else []
    return rel, der


def filled(t: dict) -> bool:
    return bool(t.get("definition"))


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
            if not f.get("tex"):
                err.append(f"{tid}: formulas に tex（式）がない")
            for s in f.get("symbols", []):
                if not (s.get("symbol") and s.get("meaning")):
                    err.append(f"{tid}: 記号には symbol と meaning を書く")
                if s.get("concept") and not NS.match(str(s["concept"])) and s["concept"] not in c.terms:
                    err.append(f"{tid}: 記号 {s.get('symbol')} の concept {s['concept']} が用語にない")
            if f.get("tree"):
                err += [f"{tid}: 式 {f['tex']} の木：{e}" for e in tree_errors(f["tree"], {s.get("key") for s in f.get("symbols", []) if s.get("key")})]
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
        if not (filled(t) or tid in referenced):
            continue
        e = {"id": g(tid), "name": t["name"], "status": "filled" if filled(t) else "stub", "version": t.get("version", 1),
             "units": units_of.get(tid, []), "problems": problems_of.get(tid, [])}
        if t.get("en"):
            e["en"] = t["en"]
        if filled(t):
            for k in ("definition", "principle", "formulas", "conditions", "example", "counterexample", "misconceptions"):
                if t.get(k):
                    e[k] = t[k]
            if t.get("formulas"):   # 記号が指す概念は、ネットワークの id（教材名:ID）にする
                e["formulas"] = [{**f, **({"symbols": [{**s, **({"concept": g(s["concept"])} if s.get("concept") else {})}
                                                       for s in f["symbols"]]} if f.get("symbols") else {})} for f in t["formulas"]]
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
    units = []
    for uid, meta in c.index.items():
        e = {"id": g(uid), "number": str(meta["number"]), "title": c.units[uid]["title"]}
        if pages.get(uid):
            e["url"] = f"https://app.notion.com/p/{pages[uid]}"
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
    revision = json.loads(SCHEMA.read_text(encoding="utf-8")).get("x-revision", 1)
    return {"schema": "kn-schema", "version": 1, "schema_revision": revision,
            "course": {"id": cid, "title": c.shared.get("course", {}).get("title", cid), "units": units},
            "concepts": concepts, "relations": relations, "derivations": derivations}


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
