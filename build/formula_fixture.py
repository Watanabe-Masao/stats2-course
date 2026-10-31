"""式の見本（math-lab のテストが読む写しの元。#118 単位 B・C5）。

教材の式（terms.yaml の木。ref は写した形）と、式ごとの契約（formula-contracts.yaml の種類・性質・組の条件）を1つの JSON にする。
docs/formula-correctness/formulas.json に書いてコミットし、math-lab が版を固定して写す（scripts/sync-stats2.mjs）。
原本を直したのにこのファイルが古いままだと、math-lab のテストが古い式で通ってしまう（C5）。check_all が --check で止める。

  python3 build/formula_fixture.py          # 書き直す
  python3 build/formula_fixture.py --check  # 原本から作ったものと同じか（違えば終了コード 1）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from formulas import CONTRACTS  # noqa: E402
from model import load_course, load_yaml  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "formula-correctness" / "formulas.json"
KEEP = ("id", "defined_in", "label", "tex", "symbols", "tree", "parts")


def build() -> str:
    c = load_course()
    bad = [e for e in c.errors if "式" in e or "契約" in e]
    if bad:
        raise SystemExit("❌ 式の原本に誤りがある：" + "／".join(bad[:5]))
    contracts = {k["formula"]: k for k in (load_yaml(CONTRACTS).get("contracts") or [])}
    out = []
    for tid, t in c.terms.items():
        for i, f in enumerate(t.get("formulas") or []):
            e = {"concept": tid, "index": i, **{k: f[k] for k in KEEP if k in f}}
            k = contracts.get(f.get("id"), {})
            e["contract"] = {x: k[x] for x in ("kinds", "properties", "representative", "conditions") if x in k}
            out.append(e)
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


def main(argv: list[str]) -> int:
    text = build()
    if "--check" in argv:
        now = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if now != text:
            print("❌ docs/formula-correctness/formulas.json が式の原本と違う（python3 build/formula_fixture.py で書き直し、math-lab で写しを取り込む）")
            return 1
        print(f"✅ 式の見本は原本と同じ（{text.count(chr(10) + ' {')} 式）")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"書いた：{OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
