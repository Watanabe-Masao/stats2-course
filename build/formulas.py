"""式の原本を整える（#118 単位 A：D1・D2・D6、M1 を起きない形に）。

- 式の元は木（tree）だけ。原本に tex は書かない。TeX は math-lab の toTex で木から作る（build/formula_tex.mjs が docs/math-lab/formula.mjs の写しを読む）
- 式には ID（`F-…`）。変えない・消さない
- 同じ式を2つの概念に出すときは、元でない側に `{ref: F-…}` と書く。build が元の式を写し、`defined_in`（元の概念）を付ける
- 式ごとの検証の契約は content/formula-contracts.yaml（種類・性質・代表・記号どうしの条件・レビューの観点）。全部の式に1つずつ

load_course の中で呼ぶので、build のどこから見ても式には id・tex（作ったもの）がそろっている。
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "content" / "formula-contracts.yaml"
FID = re.compile(r"^F-[a-z0-9]+(-[a-z0-9]+)*$")
CONTRACT_KEYS = {"formula", "kinds", "properties", "representative", "conditions", "review", "review_refs", "note"}


def originals(terms: dict) -> dict:
    """式 ID → (概念 ID, 式)。元の式だけ（ref は数えない）"""
    out = {}
    for tid, t in terms.items():
        for f in t.get("formulas") or []:
            if isinstance(f, dict) and "ref" not in f and f.get("id"):
                out.setdefault(f["id"], []).append((tid, f))
    return out


def prepare(terms: dict, contracts: dict | None) -> list[str]:
    """ref を元の式に置き換え、木から TeX を作り、検査する。見つけた誤りを返す（terms はその場で書き換える）"""
    err: list[str] = []
    orig = originals(terms)
    for fid, places in orig.items():
        if len(places) > 1:
            err.append(f"式 ID {fid} が2か所にある（{'・'.join(t for t, _ in places)}）。同じ式なら片方を {{ref: {fid}}} にする")
        if not FID.match(fid):
            err.append(f"式 ID {fid} は F-小文字と数字（- でつなぐ）で書く")
    for tid, t in terms.items():
        fs = t.get("formulas") or []
        for i, f in enumerate(fs):
            if not isinstance(f, dict):
                continue
            if "ref" in f:
                src = orig.get(f["ref"])
                if set(f) - {"ref"}:
                    err.append(f"{tid}: 式 {{ref: {f['ref']}}} には ref だけを書く（中身は元の式で直す）")
                if not src:
                    err.append(f"{tid}: 式 {{ref: {f['ref']}}} の元の式がない")
                    continue
                fs[i] = {**copy.deepcopy(src[0][1]), "defined_in": src[0][0]}
                continue
            if not f.get("id"):
                err.append(f"{tid}: {i} 番目の式に id（F-…）がない")
            if f.get("tree") and f.get("tex"):
                err.append(f"{tid}: 式 {f.get('id')} に tex を書かない（TeX は木から作る。#118）")
            if not f.get("tree") and not f.get("tex"):
                err.append(f"{tid}: 式 {f.get('id')} に木（tree）がない")
    # 契約（D6）
    by_id = {fid: places[0] for fid, places in orig.items()}
    checks: dict[str, list] = {}
    if contracts is not None:
        vocab = contracts.get("vocab") or {}
        kinds, props = set(vocab.get("kinds") or []), set(vocab.get("properties") or [])
        seen = set()
        for k in contracts.get("contracts") or []:
            fid = k.get("formula")
            if fid in seen:
                err.append(f"契約：式 {fid} が2回ある")
            seen.add(fid)
            if fid not in by_id:
                err.append(f"契約：式 {fid} が terms.yaml にない（元の式の ID を書く）")
                continue
            if set(k) - CONTRACT_KEYS:
                err.append(f"契約 {fid}：知らない項目 {'・'.join(sorted(set(k) - CONTRACT_KEYS))}")
            if not k.get("kinds") or set(k["kinds"]) - kinds:
                err.append(f"契約 {fid}：kinds は vocab.kinds から1つ以上（{'・'.join(sorted(set(k.get('kinds') or []) - kinds)) or '空'}）")
            if set(k.get("properties") or []) - props:
                err.append(f"契約 {fid}：properties に vocab にない語 {'・'.join(sorted(set(k['properties']) - props))}")
            for c in k.get("conditions") or []:
                if not (isinstance(c, dict) and c.get("text") and isinstance(c.get("tree"), dict)):
                    err.append(f"契約 {fid}：conditions は text と tree（比べる式の木）で書く")
            for r in k.get("review_refs") or []:
                if r not in evidence():
                    err.append(f"契約 {fid}：review_refs の {r} が導出・実験室にない")
            checks[fid] = [c["tree"] for c in k.get("conditions") or [] if isinstance(c, dict) and isinstance(c.get("tree"), dict)]
        missing = sorted(set(by_id) - seen)
        if missing:
            err.append(f"契約がない式（未分類）：{'・'.join(missing)}（content/formula-contracts.yaml に書く。#118 C6）")
    # 木から TeX を作り、木と組の条件を検査する（1回の node でまとめて）
    jobs = [{"id": fid, "tree": f["tree"], "symbols": f.get("symbols") or [], "checks": checks.get(fid, [])}
            for fid, (_, f) in by_id.items() if f.get("tree")]
    if jobs:
        try:
            r = subprocess.run(["node", str(ROOT / "build" / "formula_tex.mjs")], input=json.dumps(jobs), capture_output=True, text=True, check=True, timeout=60)
            res = {x["id"]: x for x in json.loads(r.stdout)}
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
            return err + [f"式の TeX を作れない（node と docs/math-lab/formula.mjs を確かめる）：{e}"]
        for fid, (tid, f) in by_id.items():
            x = res.get(fid)
            if not x:
                continue
            err += [f"{tid}: 式 {fid}：{e}" for e in x["errors"]]
            f["tex"] = x["tex"]
        for t in terms.values():   # 写した式にも TeX を入れる
            for f in t.get("formulas") or []:
                if isinstance(f, dict) and f.get("defined_in") and f.get("id") in res:
                    f["tex"] = res[f["id"]]["tex"]
    return err


def contract_summary(contracts: dict | None) -> dict:
    """契約の数：代表の式・レビューの観点のある式（進み具合・C6 の知らせ用）"""
    ks = (contracts or {}).get("contracts") or []
    return {"contracts": len(ks), "representative": sum(1 for k in ks if k.get("representative")), "review": sum(1 for k in ks if k.get("review"))}


REVIEWS = ROOT / "content" / "formula-reviews.yaml"
REFERENCE = ROOT / "docs" / "formula-correctness" / "reference.json"


def evidence() -> dict:
    """レビューの観点の根拠になる原本（契約の review_refs で指す）：導出 DER-… と、実験室 EXP-… の反例（counterexamples・contrasts）"""
    out = {}
    der = ROOT / "content" / "derivations.yaml"
    exp = ROOT / "content" / "experiments.yaml"
    from model import load_yaml   # build の中から呼ぶ（循環を避けて関数の中で読む）
    for d in ((load_yaml(der) or {}).get("derivations") or []) if der.exists() else []:
        out[d["id"]] = d
    for x in ((load_yaml(exp) or {}).get("experiments") or []) if exp.exists() else []:
        out[x["id"]] = {"counterexamples": x.get("counterexamples") or [], "contrasts": x.get("contrasts") or []}
    return out


def fingerprint(term: dict, formula: dict, contract: dict | None, refs: dict | None = None) -> str:
    """レビューの対象の版（#118 M9）：式の木・記号の表（of・domain・concept・意味）・契約の組の条件・概念の成り立つ条件と反例・誤解、
    契約の review_refs が指す根拠（導出・実験室の反例）。この中の何かが変われば値が変わり、古いレビューの記録では通らない。
    TeX は木から作るので入れない。同じ内容の作り直しでは変わらない"""
    import hashlib
    refs = refs or {}
    body = {"tree": formula.get("tree"), "symbols": formula.get("symbols") or [],
            "contract_conditions": (contract or {}).get("conditions") or [], "term_conditions": term.get("conditions") or {},
            "term_counterexample": term.get("counterexample"), "term_misconceptions": term.get("misconceptions") or [],
            "evidence": {r: refs.get(r) for r in (contract or {}).get("review_refs") or []}}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def current_fingerprints(terms: dict, contracts: dict | None) -> dict:
    """式 ID → 今の fingerprint（元の式だけ）"""
    ks = {k["formula"]: k for k in (contracts or {}).get("contracts") or []}
    refs = evidence()
    out = {}
    for tid, t in terms.items():
        for f in t.get("formulas") or []:
            if isinstance(f, dict) and f.get("id") and "ref" not in f and not f.get("defined_in"):   # 写した式（defined_in）は元の概念で数える
                out.setdefault(f["id"], fingerprint(t, f, ks.get(f["id"]), refs))
    return out


def pending(contracts: dict | None, reviews: list | None, prints: dict | None = None) -> dict:
    """式 ID → レビュー前の理由（契約に review があり、その全部の観点が今の版の記録にそろっていない式）"""
    out = {}
    for k in (contracts or {}).get("contracts") or []:
        fid, need = k["formula"], set(k.get("review") or [])
        if not need:
            continue
        done: set = set()
        stale = False
        for r in reviews or []:
            if r.get("formula") != fid:
                continue
            if prints is not None and r.get("fingerprint") != prints.get(fid):
                stale = True   # 記録のあとに式・記号・条件が変わった
                continue
            done |= set(r.get("points") or [])
        if need - done:
            out[fid] = "レビューのあとに式・記号・条件が変わった（やり直す）" if stale and not done else f"観点 {'・'.join(sorted(need - done))} のレビューの記録がない"
    return out


def marks(contracts: dict | None, reviews: list | None, prints: dict | None = None) -> dict:
    """公開の JSON に出す式ごとのもの（#118 単位 C・D4）：記号どうしの条件、未検証・レビュー前の印。
    - 未検証：独立な見本（reference.json の formula_ids）に出てこない式
    - レビュー前：契約に review（数で保証できない観点）があり、今の版（fingerprint）の記録にその全部がない式
    """
    covered = set()
    if REFERENCE.exists():
        ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
        for c in ref.get("cases", []):
            covered.update(c.get("formula_ids") or [])
    pend = pending(contracts, reviews, prints)
    out = {}
    for k in (contracts or {}).get("contracts") or []:
        fid = k["formula"]
        m = {}
        if k.get("conditions"):
            m["conditions"] = [{"text": c["text"], "tree": c["tree"]} for c in k["conditions"]]
        if fid not in covered:
            m["unverified"] = True
        if fid in pend:
            m["review_pending"] = True
        out[fid] = m
    return out


def publish_errors(contracts: dict | None, reviews: list | None, prints: dict) -> list[str]:
    """公開の前の検査（#118 M9）：公開する代表の式（representative）に、今の版のレビューがそろっていなければ止める。
    ふだんの build は止めず「レビュー前」の印を出すだけ"""
    pend = pending(contracts, reviews, prints)
    return [f"代表の式 {k['formula']}：{pend[k['formula']]}" for k in (contracts or {}).get("contracts") or [] if k.get("representative") and k["formula"] in pend]


def review_errors(contracts: dict | None, reviews: list | None) -> list[str]:
    """レビューの記録：契約にある式・観点だけ、日付と判断を書く"""
    err = []
    ks = {k["formula"]: k for k in (contracts or {}).get("contracts") or []}
    for r in reviews or []:
        k = ks.get(r.get("formula"))
        if not k:
            err.append(f"レビュー：式 {r.get('formula')} に契約がない")
            continue
        extra = set(r.get("points") or []) - set(k.get("review") or [])
        if extra:
            err.append(f"レビュー {r['formula']}：契約の review にない観点 {'・'.join(sorted(extra))}")
        if not (r.get("date") and r.get("judgement") and r.get("by")):
            err.append(f"レビュー {r['formula']}：date（日付）・by（だれが）・judgement（判断と根拠）を書く")
        if not r.get("fingerprint"):
            err.append(f"レビュー {r['formula']}：fingerprint（レビューした版。python3 build/formulas.py --fingerprint {r['formula']} で出す）を書く")
    return err


if __name__ == "__main__":
    # python3 build/formulas.py --fingerprint F-…   今の版を出す（レビューの記録に書く）
    # python3 build/formulas.py --publish-check     公開の前の検査（build/deploy_site.sh が呼ぶ）
    import sys
    sys.path.insert(0, str(ROOT / "build"))
    from model import load_course, load_yaml
    c = load_course()
    contracts = load_yaml(CONTRACTS)
    reviews = (load_yaml(REVIEWS) or {}).get("reviews") or []
    prints = current_fingerprints(c.terms, contracts)
    if sys.argv[1:2] == ["--fingerprint"]:
        for fid in sys.argv[2:]:
            print(fid, prints.get(fid, "（その式はない）"))
    elif sys.argv[1:2] == ["--publish-check"]:
        err = publish_errors(contracts, reviews, prints)
        for e in err:
            print("❌", e)
        print("✅ 公開する代表の式は、今の版でレビュー済み" if not err else f"❌ {len(err)} 件：レビューしてから公開する（#118 M9）")
        sys.exit(1 if err else 0)
    else:
        print(__doc__)
