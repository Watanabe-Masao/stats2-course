"""写しを確かめる・取り込む：知識ネットワークの型（元は knowledge-net の schema/）と、見た目と手触りの値（元は math-lab の packages/ui/tokens.json。#107）、式の計算の束（math-lab の packages/engine/dist/formula.mjs。#118）。

写しは「取り込んだときの元の版（コミット）」を docs/sync-lock.json に固定して照らす（#129）。
元のリポジトリの main が先に進んでも、教材の CI は落ちない（取り込むまでは固定した版のまま）。

使い方:
    python3 build/sync_schema.py           # 写しが固定した版の元と同じか確かめる（違えば止まる）。main が先に進んでいれば知らせる（止めない）
    python3 build/sync_schema.py --update  # 元の main を写しに取り込み、版を固定し直す（取り込んだら build とテストを通す）
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "docs" / "sync-lock.json"
OWNER = "Watanabe-Masao"
# （元のリポジトリ, 元の中の場所, 写しの場所）
FILES = (
    ("knowledge-net", "schema/kn-schema-v1.json", ROOT / "docs" / "knowledge-net" / "schema" / "kn-schema-v1.json"),
    ("knowledge-net", "schema/relation-types.yaml", ROOT / "docs" / "knowledge-net" / "schema" / "relation-types.yaml"),
    ("math-lab", "packages/ui/tokens.json", ROOT / "docs" / "math-lab" / "tokens.json"),
    # 式の計算の束（木から TeX を作る・木を検査する。build/formula_tex.mjs が読む。#118）
    ("math-lab", "packages/engine/dist/formula.mjs", ROOT / "docs" / "math-lab" / "formula.mjs"),
)


def fetch(url: str) -> str:
    headers = {"User-Agent": "stats2-course-sync"}
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):   # CI では回数の制限を避ける
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def raw(repo: str, ref: str, path: str) -> str:
    return fetch(f"https://raw.githubusercontent.com/{OWNER}/{repo}/{ref}/{path}")


def head(repo: str) -> str:
    """元のリポジトリの main の今のコミット"""
    return json.loads(fetch(f"https://api.github.com/repos/{OWNER}/{repo}/commits/main"))["sha"]


def main(argv: list[str]) -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.exists() else {}
    repos = sorted({r for r, _, _ in FILES})
    if "--update" in argv:
        try:
            pins = {r: head(r) for r in repos}
        except Exception as e:  # noqa: BLE001
            print(f"❌ 元の版を読めない（{e}）")
            return 1
        for repo, path, copy in FILES:
            src = raw(repo, pins[repo], path)
            mine = copy.read_text(encoding="utf-8") if copy.exists() else None
            if src != mine:
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_text(src, encoding="utf-8")
                print(f"取り込んだ：{copy.relative_to(ROOT)}（{repo}@{pins[repo][:7]}）")
        LOCK.write_text(json.dumps(pins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"版を固定した：" + "・".join(f"{r}@{s[:7]}" for r, s in pins.items()))
        return 0
    missing = [r for r in repos if r not in lock]
    if missing:
        print(f"❌ 版が固定されていない：{'・'.join(missing)}（python3 build/sync_schema.py --update で取り込む）")
        return 1
    bad = []
    for repo, path, copy in FILES:
        try:
            src = raw(repo, lock[repo], path)
        except Exception as e:  # noqa: BLE001
            print(f"❌ 元を読めない：{repo}@{lock[repo][:7]} {path}（{e}）")
            return 1
        mine = copy.read_text(encoding="utf-8") if copy.exists() else None
        if src != mine:
            bad.append(f"{copy.relative_to(ROOT)}（{repo}@{lock[repo][:7]}）")
    if bad:
        print("❌ 写しが固定した版の元と違う：" + "・".join(bad) + "（写しを手で直さない。python3 build/sync_schema.py --update で取り込む）")
        return 1
    # main が先に進んでいても止めない。取り込みは作業として行う
    for repo in repos:
        try:
            now = head(repo)
            ahead = [p for r, p, c in FILES if r == repo and now != lock[repo] and raw(repo, now, p) != c.read_text(encoding="utf-8")]
        except Exception:  # noqa: BLE001  知らせるだけなので、読めなければ黙る
            continue
        if ahead:
            print(f"ℹ️ {repo} の main は固定した版より先に進み、写しの元が変わっている：{'・'.join(ahead)}（取り込むときは --update）")
    print("✅ 型（knowledge-net）と見た目の値（math-lab）の写しは固定した版の元と同じ（" + "・".join(f"{r}@{lock[r][:7]}" for r in repos) + "）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
