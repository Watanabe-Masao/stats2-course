"""ラボの場面ごとの版を作る。

tools/<lab>/tool.yaml に src があるラボは、共通部品（tools/labkit）を差し込み、
場面ごとの設定（window.__LABCFG__）を書き込んだ HTML を out/labs/ に作る。

  素材ID              中身
  LAB-scale           設定なし（自由に動かす）
  LAB-scale@s1-temp   tool.yaml の presets.s1-temp（本文では {{lab:LAB-scale@s1-temp}}）
  LAB-scale@Q-U04-010 問題 Q-U04-010 の lab（答えの中に「ラボで確かめる」として入る）

out/labs/manifest.json に、各版の設定と expect（予想の答え。テストでラボの値と照合する）を書く。
expect は HTML には入れない（答えはラボ自身が計算する）。
"""
from __future__ import annotations

import json
from pathlib import Path

from model import ROOT, TOOLS, Course

OUT = ROOT / "out" / "labs"
CFG_KEYS = ("mode", "set", "task", "predict", "why")


def safe(aid: str) -> str:
    return aid.replace("@", "__")


def lab_file(course: Course, aid: str) -> Path:
    """素材IDから、アップロードするファイルを返す。"""
    lab = aid.split("@")[0]
    t = course.labs[lab]
    if t.get("src"):
        return OUT / f"{safe(aid)}.html"
    return t["dir"] / t["file"]


def variants(course: Course) -> dict[str, dict]:
    """素材ID → 設定（expect を含む）。"""
    out = {}
    for lid, t in course.labs.items():
        if not t.get("src"):
            continue
        out[lid] = {}
        for name, p in (t.get("presets") or {}).items():
            out[f"{lid}@{name}"] = p
    for u in course.units.values():
        for qid, q in u["problems"].items():
            if q.get("lab"):
                out[f"{q['lab']['id']}@{qid}"] = q["lab"]
    return out


def squeeze(html: str) -> str:
    lines = []
    for line in html.splitlines():
        s = line.strip()
        if not s or (s.startswith("//") and not s.startswith("//@")):
            continue
        lines.append(s)
    return "\n".join(lines) + "\n"


def build_labs(course: Course) -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    kit_css = (TOOLS / "labkit" / "labkit.css").read_text(encoding="utf-8")
    kit_js = (TOOLS / "labkit" / "labkit.js").read_text(encoding="utf-8")
    manifest = []
    for lid, t in course.labs.items():   # 共通部品を使わない古い形のラボ（そのまま使う）
        if not t.get("src"):
            manifest.append({"asset": lid, "file": str((t["dir"] / t["file"]).relative_to(ROOT)), "cfg": {}, "expect": None})
    for aid, spec in variants(course).items():
        lid = aid.split("@")[0]
        t = course.labs[lid]
        src = (t["dir"] / t["src"]).read_text(encoding="utf-8")
        cfg = {k: spec[k] for k in CFG_KEYS if k in spec}
        html = (src.replace("/*@LABKIT_CSS@*/", kit_css)
                   .replace("/*@LABKIT_JS@*/", kit_js)
                   .replace("/*@LABCFG@*/", "window.__LABCFG__=" + json.dumps(cfg, ensure_ascii=False) + ";"))
        if "@LAB" in html:
            raise ValueError(f"{lid}: 差し込み口が残っている")
        f = OUT / f"{safe(aid)}.html"
        f.write_text(squeeze(html), encoding="utf-8")
        manifest.append({"asset": aid, "file": str(f.relative_to(ROOT)), "cfg": cfg, "expect": spec.get("expect")})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def validate_labs(course: Course) -> list[str]:
    err = []
    for lid, t in course.labs.items():
        if t.get("src") and not (t["dir"] / t["src"]).exists():
            err.append(f"{lid}: {t['src']} がない")
        for name, p in (t.get("presets") or {}).items():
            err += _check_spec(f"{lid}@{name}", p)
    for u in course.units.values():
        for qid, q in u["problems"].items():
            if not q.get("lab"):
                continue
            lab = q["lab"]
            if lab.get("id") not in course.labs:
                err.append(f"{qid}: lab.id {lab.get('id')} がない")
            elif not course.labs[lab["id"]].get("src"):
                err.append(f"{qid}: {lab['id']} は場面ごとの版を作れない（tool.yaml に src がない）")
            if not lab.get("task"):
                err.append(f"{qid}: lab.task（課題の文）がない")
            err += _check_spec(qid, lab)
    return err


def _check_spec(where: str, p: dict) -> list[str]:
    err = []
    pr = p.get("predict")
    if pr:
        if pr.get("type") not in ("number", "choice"):
            err.append(f"{where}: predict.type は number か choice")
        if not pr.get("key"):
            err.append(f"{where}: predict.key がない")
        if pr.get("type") == "choice" and not pr.get("options"):
            err.append(f"{where}: predict.options がない")
        if p.get("expect") is None:
            err.append(f"{where}: predict があるのに expect（ラボの値と照合する答え）がない")
        if not p.get("task"):
            err.append(f"{where}: predict があるのに task がない")
    return err
