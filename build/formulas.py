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
CONTRACT_KEYS = {"formula", "kinds", "properties", "representative", "conditions", "review", "note"}


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
