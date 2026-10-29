#!/usr/bin/env python3
"""変えたファイルに合わせて、確かめる範囲を選んで実行する。

使い方: python3 build/check_changed.py [比べる元（既定: origin/main）]
  - 比べる元からの差分＋まだコミットしていない変更＋新しいファイルを見る
  - 範囲の決め方（CLAUDE.md「確かめる」の表と同じ）
      説明文だけ（CLAUDE.md・README・docs/）       → 何もしない
      単元（content/units/UXX・problems/UXX・migration の UXX）
                                                  → 単体テスト・build・その単元の旧版との突き合わせ・その単元のラボの版
      1つのラボ（tools/xx_lab/）                    → 単体テスト・build・そのラボの全部の版・check.js
      共通部分（build/・tests/・labkit・test_labs.js・templates/・content/*.yaml など）
                                                  → 単体テスト・build・全単元の旧版との突き合わせ（ラボの版はマージ前の全部で）
  - ブランチの途中のコミットはこれで確かめる。マージの前（PR を出す前）に build/check_all.sh で全部を確かめる
  - 最後に「✅ 範囲内 OK」と出す。どれか1つでも失敗したら止まる（終了コード≠0）
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = re.compile(r"^(CLAUDE\.md|README\.md|docs/)")
UNIT = re.compile(r"^(?:content/units/(U\d+T?)/|content/problems/(U\d+T?)\.yaml$|migration/(?:old|waivers)/(U\d+T?)\.)")
LAB = re.compile(r"^tools/([a-z0-9_]+_lab)/")


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def changed(base: str) -> list[str]:
    files = set(git("diff", "--name-only", f"{base}...HEAD"))
    files |= set(git("diff", "--name-only", "HEAD"))
    files |= set(git("ls-files", "--others", "--exclude-standard"))
    return sorted(f for f in files if not f.startswith("out/"))


def classify(files: list[str]) -> tuple[list[str], set[str], set[str], list[str]]:
    """(説明文, 単元, ラボのフォルダ, 共通部分) に分ける。"""
    docs, units, labs, common = [], set(), set(), []
    for f in files:
        if DOCS.match(f):
            docs.append(f)
        elif m := UNIT.match(f):
            units.add(next(g for g in m.groups() if g))
        elif m := LAB.match(f):
            labs.add(m.group(1))
        else:
            common.append(f)
    return docs, units, labs, common


def lab_id(folder: str) -> str:
    with open(os.path.join(ROOT, "tools", folder, "tool.yaml"), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("id:"):
                return line.split(":", 1)[1].split("#")[0].strip()
    raise SystemExit(f"tools/{folder}/tool.yaml に id がない")


def unit_assets(unit: str) -> list[str]:
    """単元が使うラボの版（本文の {{lab:…}} と、問題の答えのラボ LAB-x@Q-UXX-…）。"""
    names: set[str] = set()
    folder = os.path.join(ROOT, "content", "units", unit)
    texts = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".md")]
    for path in texts:
        with open(path, encoding="utf-8") as fh:
            names |= set(re.findall(r"\{\{lab:(LAB-[\w-]+(?:@[\w-]+)?)\}\}", fh.read()))
    prob = os.path.join(ROOT, "content", "problems", f"{unit}.yaml")
    if os.path.exists(prob):
        with open(prob, encoding="utf-8") as fh:
            text = fh.read()
        for qid, lab in re.findall(r"- id: (Q-[\w-]+)\n(?:(?!- id:).*\n)*?  lab:\n    id: (LAB-[\w-]+)", text):
            names.add(f"{lab}@{qid}")
    return sorted(names)


def run(title: str, cmd: list[str], env: dict | None = None) -> None:
    print(f"== {title}", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env={**os.environ, **(env or {})})
    if r.returncode != 0:
        print(f"❌ {title} で止まった（終了コード {r.returncode}）")
        sys.exit(r.returncode)


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    files = changed(base)
    docs, units, labs, common = classify(files)
    print(f"比べる元: {base}　変えたファイル: {len(files)}")
    print(f"  説明文 {len(docs)}・単元 {' '.join(sorted(units)) or 'なし'}・ラボ {' '.join(sorted(labs)) or 'なし'}・共通 {len(common)}")
    if common:
        print("  共通部分が変わった：" + "、".join(common[:5]) + ("…" if len(common) > 5 else ""))
        units = {os.path.basename(f)[:-3] for f in os.listdir(os.path.join(ROOT, "migration", "old")) if f.endswith(".md")}
        labs_note = True
    else:
        labs_note = False
    if not units and not labs:
        print("説明文だけなので、確かめるものはない")
        print("✅ 範囲内 OK")
        return
    run("単体テスト", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"])
    run("生成（検証・検算・生成物の検査）", [sys.executable, "build/build.py"])
    for u in sorted(units):
        if os.path.exists(os.path.join(ROOT, "migration", "old", f"{u}.md")):
            run(f"旧版との突き合わせ {u}", [sys.executable, "build/audit.py", u])
    lab_ids = sorted(lab_id(f) for f in labs)
    if lab_ids:
        run("ラボの全部の版 " + " ".join(lab_ids), ["node", "tools/test_labs.js"], {"ONLY": ",".join(lab_ids)})
        for f in sorted(labs):
            check = os.path.join("tools", f, "check.js")
            if os.path.exists(os.path.join(ROOT, check)):
                run(f"ラボの検算 {f}", ["node", check])
    # ラボごと全部確かめたラボの版は除く
    assets = [] if labs_note else [a for u in sorted(units) for a in unit_assets(u) if a.split("@")[0] not in lab_ids]
    if assets:
        run(f"単元のラボの版（{len(assets)}）", ["node", "tools/test_labs.js"], {"ASSETS": ",".join(assets)})
    if labs_note:
        print("⚠️ 共通部分が変わったので、マージの前に build/check_all.sh（全部）を通す")
    print("✅ 範囲内 OK")


if __name__ == "__main__":
    main()
