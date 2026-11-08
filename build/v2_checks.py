"""型 v2 の止め（製本への移行 M4。#264）：書き出した v2 のデータのうち、v2 の種類で書いた関係（type を持つ行）にかける。

型（kn-schema-v2.json）が止めるもの（種類ごとの必須・fix の値・掛かる先ごとの区分・主張の id の形）は schema_errors に任せ、
ここは型で書けない、行どうし・概念とのつながりで決まるもの（設計書 docs/schema-v2-design.md 3.2 の「機械で止める」）を止める。
人の確かめに残すもの（3.2 の右の列）は止めない。意味の判断の正本は製本 ⑤（docs/rules/relations.md）。

学ぶ順の止め（前提知識の重ねと輪。⑥ の 2）は、候補を build が求める M6（#266）で足す（候補がないと重ねを判定できない）。
移していない行（legacy_type）は、v2_ready の分類に残っていないかだけを見る（ほかは今の build の止めのまま）。
"""
from __future__ import annotations

# ⑤ の 4 の表：種類ごとに、端に置ける姿（① の 3。型の form の値）。
#   same：from と to が同じ姿。pairs：置ける (from, to) の組。from/to：それぞれに置ける姿（None は問わない）
FORM_RULES = {
    "定める": {},   # from はどれでも。to は「定義を持つ概念」で、姿では決まらない（basis で止める）
    "一種": {"same": True},
    "特別な場合": {"same": True},
    "比べる": {"same": True},
    "移る": {"same": True, "from": {"distribution", "rv", "number", "procedure"}},
    "従う": {"pairs": {("rv", "distribution")}},
    "推定する": {"pairs": {("rv", "number"), ("random_set", "function")}},
    "導ける": {"from": {"proposition", "property"}, "to": {"proposition", "property"}},
    "同値": {"from": {"proposition", "property"}, "to": {"proposition", "property"}},
    "根拠": {"pairs": {("proposition", "procedure")}},
}
INCLUSION = {"一種", "特別な場合"}
THEOREM_KINDS = {"移る", "従う", "推定する"}   # theorem（通す定理）を添えられる種類（⑤ の 6）


def _forms(c: dict) -> list[str]:
    return list(c.get("forms") or [])


def _side(rel: dict, end: str, c: dict, err: list[str]) -> str | None:
    """その関係で使う端の姿。姿がない・2つ以上なのに from_form/to_form がない・その姿を持たないときは止めて None"""
    fs = _forms(c)
    rid = rel["id"]
    if not fs:
        err.append(f"{rid}: {end} の {c['id']} に姿（forms）がない（移していない分類の相手も書く。設計書 D2）")
        return None
    key = f"{end}_form"
    if len(fs) == 1:
        if rel.get(key) and rel[key] != fs[0]:
            err.append(f"{rid}: {key} {rel[key]} は {c['id']} の姿 {fs} にない")
            return None
        return fs[0]
    if not rel.get(key):
        err.append(f"{rid}: {c['id']} は姿が2つ以上（{fs}）なので、この関係で使う姿 {key} を書く（D2）")
        return None
    if rel[key] not in fs:
        err.append(f"{rid}: {key} {rel[key]} は {c['id']} の姿 {fs} にない")
        return None
    return rel[key]


def _form_errors(rel: dict, a: str, b: str) -> list[str]:
    rule = FORM_RULES.get(rel["type"], {})
    bad = []
    if rule.get("same") and a != b:
        bad.append("from と to が同じ姿")
    if rule.get("from") and a not in rule["from"]:
        bad.append(f"from の姿が {sorted(rule['from'])} のどれか")
    if rule.get("to") and b not in rule["to"]:
        bad.append(f"to の姿が {sorted(rule['to'])} のどれか")
    if rule.get("pairs") and (a, b) not in rule["pairs"]:
        bad.append(f"(from, to) の姿が {sorted(rule['pairs'])} のどれか")
    return [f"{rel['id']}: {rel['type']} は {'・'.join(bad)}であること（⑤ の 4。今は {a} → {b}）"] if bad else []


def basis_concepts(c: dict) -> set[str] | None:
    """概念の基準の定義に出る概念（定めるの from になれるもの）。式なら木に出る記号・関数の concept、文なら terms。基準の定義がなければ None"""
    basis = c.get("basis") or {}
    if basis.get("formula"):
        f = next((x for x in c.get("formulas") or [] if x.get("id") == basis["formula"]), None)
        if f is None:
            return set()
        used: set[str] = set()

        def walk(n):
            if isinstance(n, dict):
                if "sym" in n:
                    used.add(n["sym"])
                if n.get("op") == "fn" and n.get("name"):
                    used.add(n["name"])
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)
        walk(f.get("tree"))
        return {s["concept"] for s in f.get("symbols") or [] if s.get("concept") and s.get("key") in used} - {c["id"]}   # build/network.py の basis_candidates と同じ読み方
    if basis.get("terms"):
        return set(basis["terms"]) - {c["id"]}
    return None


def _preds(side: dict | None) -> list[str]:
    return list((side or {}).get("predicates") or [])


def _ends(side: dict | None) -> set[str]:
    return set((side or {}).get("subjects") or []) | set(_preds(side))


def _cycles(edges: list[tuple[str, str]]) -> list[list[str]]:
    """向きのある辺の輪（1つの輪を1回）"""
    nxt: dict[str, list[str]] = {}
    for a, b in edges:
        nxt.setdefault(a, []).append(b)
    seen, out, done = set(), [], set()

    def dfs(n, path):
        if n in path:
            cyc = path[path.index(n):]
            key = frozenset(cyc)
            if key not in done:
                done.add(key)
                out.append(cyc + [n])
            return
        if n in seen:
            return
        path.append(n)
        for m in nxt.get(n, []):
            dfs(m, path)
        path.pop()
        seen.add(n)
    for n in list(nxt):
        dfs(n, [])
    return out


def v2_errors(data: dict) -> list[str]:
    """v2 のデータ（書き出したもの）の止め。v2 の種類の行がなく、v2_ready も空なら何も止めない"""
    err: list[str] = []
    concepts = {c["id"]: c for c in data.get("concepts", [])}
    claims = {c["id"]: c for c in data.get("claims", [])}
    ready = set((data.get("course") or {}).get("v2_ready") or [])
    rels = data.get("relations", [])
    v2 = [r for r in rels if "type" in r]

    # 移した分類に、移していない行を残さない（設計書 8。行き先の概念の分類で見る）
    for r in rels:
        if "legacy_type" in r and (concepts.get(r["to"]) or {}).get("category") in ready:
            err.append(f"{r['id']}: 移した分類（{concepts[r['to']]['category']}）の行に legacy_type（{r['legacy_type']}）が残っている")

    for r in v2:
        a, b = concepts.get(r["from"]), concepts.get(r["to"])
        if a is None or b is None:
            continue   # ほかの教材の概念（未接続）は姿を照らせない
        fa, fb = _side(r, "from", a, err), _side(r, "to", b, err)
        if fa and fb:
            err += _form_errors(r, fa, fb)
        if r["type"] == "定める":
            used = basis_concepts(b)
            if used is None:
                err.append(f"{r['id']}: 定めるの to（{b['id']}）に基準の定義（basis）がない（⑤ の構成）")
            elif r["from"] not in used:
                err.append(f"{r['id']}: 定めるの from（{a['id']}）が、to の基準の定義に出ない（⑤ の構成。言い換え・使われる場などは構成要素にしない）")
        if r["type"] == "導ける" and r.get("claim") in claims:
            cl = claims[r["claim"]]
            pre, con = _preds(cl.get("premises")), _preds(cl.get("conclusion"))
            if r["from"] not in pre:
                err.append(f"{r['id']}: from（{r['from']}）が主張 {cl['id']} の前提の述語にない（設計書 4）")
            if r["to"] not in con:
                err.append(f"{r['id']}: to（{r['to']}）が主張 {cl['id']} の結論の述語にない")
            others = [p for p in pre if p != r["from"]]
            if others:
                err.append(f"{r['id']}: 主張 {cl['id']} の前提の述語に from 以外（{others}）がある。前提が2つなら定理の点にする（⑤ の 4 の帰結・6）")
        for cid in ([r["claim"]] if r.get("claim") else []) + list(r.get("properties") or []):
            if cid not in claims:
                err.append(f"{r['id']}: 主張 {cid} がない")
        if r.get("theorem"):
            t = concepts.get(r["theorem"])
            if t is not None and "proposition" not in _forms(t):
                err.append(f"{r['id']}: 通す定理 {t['id']} の姿が命題でない（⑤ の 6：定理の点は姿が命題の概念）")

    # 一種の親は1つまで（⑤ の 包含）
    parents: dict[str, list[str]] = {}
    for r in v2:
        if r["type"] == "一種":
            parents.setdefault(r["from"], []).append(r["to"])
    for k, ps in parents.items():
        if len(ps) > 1:
            err.append(f"{k}: 一種の親が2つ以上（{ps}）。親は多くて1つ（⑤ の 包含）")

    # 1つの組に関係は1つ。重ねてよいのは 包含＋移る と 比べる＋ほか（⑤ の 7。向きを問わない。移していない行も数える）
    pairs: dict[frozenset, list[dict]] = {}
    for r in rels:
        pairs.setdefault(frozenset((r["from"], r["to"])), []).append(r)
    for rs in pairs.values():
        if not any("type" in r for r in rs) or len(rs) < 2:
            continue
        kinds = [r.get("type") or r.get("legacy_type") for r in rs]
        rest = [k for k in kinds if k != "比べる"]
        ok = len(rest) <= 1 or (len(rest) == 2 and "移る" in rest and set(rest) - {"移る"} <= INCLUSION)
        if not ok:
            err.append(f"{'・'.join(r['id'] for r in rs)}: 同じ組に重ねられない関係（{kinds}。⑤ の 7）")

    # 定理の結論が2つの概念の関係そのものなら、その関係に通す定理として添える（⑤ の 6）
    theorems = [c for c in concepts.values() if "proposition" in _forms(c)]
    for r in v2:
        if r["type"] not in THEOREM_KINDS or r.get("theorem"):
            continue
        for t in theorems:
            for cid in t.get("claims") or []:
                cl = claims.get(cid) or {}
                if {r["from"], r["to"]} <= (_ends(cl.get("premises")) | _ends(cl.get("conclusion"))):
                    err.append(f"{r['id']}: 定理 {t['id']} の主張 {cid} が同じ2つを結んでいる。関係に theorem として添える（⑤ の 6）")

    # 基準の定義に出る概念は、定める・一種の親・除外（basis.excludes）のどれかで扱う（#86。⑤ の構成：名前が出るのは必要条件なので、外すなら理由を書く）。
    # 移した分類の概念だけ。除外した概念から定めるを書いたら、どちらが判断か分からないので止める
    defines = {(r["from"], r["to"]) for r in rels if r.get("type") == "定める" or r.get("legacy_type") == "材料"}
    kind_parent = {(r["to"], r["from"]) for r in rels if r.get("type") == "一種" or r.get("legacy_type") == "種類"}
    for c in concepts.values():
        used = basis_concepts(c)
        if not used:
            continue
        ex = {x["concept"] for x in (c.get("basis") or {}).get("excludes") or []}
        for k in sorted(ex & {a for a, b in defines if b == c["id"]}):
            err.append(f"{c['id']}: {k} を定めると basis.excludes の両方に書いている（#86）")
        if c.get("category") in ready:
            for k in sorted(used - ex):
                if (k, c["id"]) not in defines and (k, c["id"]) not in kind_parent:
                    err.append(f"{c['id']}: 基準の定義に出る {k} を、定める・一種の親・basis.excludes のどれでも扱っていない（#86。⑤ の構成）")

    # 定義の依存は輪にならない（⑤ の 構成）
    for cyc in _cycles([(r["from"], r["to"]) for r in v2 if r["type"] == "定める"]):
        err.append(f"定めるの輪：{' → '.join(cyc)}（⑤ の 構成）")
    return err
