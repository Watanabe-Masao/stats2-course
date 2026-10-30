"""写しを確かめる・取り込む：知識ネットワークの型（元は knowledge-net の schema/）と、見た目と手触りの値（元は math-lab の packages/ui/tokens.json。#107）。

使い方:
    python3 build/sync_schema.py           # 写しが元と同じか確かめる（違えば止まる）
    python3 build/sync_schema.py --update  # 元を写しに取り込む（取り込んだら build とテストを通す）
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/Watanabe-Masao/"
# （元の URL, 写しの場所）
FILES = (
    (RAW + "knowledge-net/main/schema/kn-schema-v1.json", ROOT / "docs" / "knowledge-net" / "schema" / "kn-schema-v1.json"),
    (RAW + "knowledge-net/main/schema/relation-types.yaml", ROOT / "docs" / "knowledge-net" / "schema" / "relation-types.yaml"),
    (RAW + "math-lab/main/packages/ui/tokens.json", ROOT / "docs" / "math-lab" / "tokens.json"),
)


def main(argv: list[str]) -> int:
    bad = []
    for url, copy in FILES:
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                src = r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"❌ 元を読めない：{url}（{e}）")
            return 1
        mine = copy.read_text(encoding="utf-8") if copy.exists() else None
        if src != mine:
            if "--update" in argv:
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_text(src, encoding="utf-8")
                print(f"取り込んだ：{copy.relative_to(ROOT)}")
            else:
                bad.append(str(copy.relative_to(ROOT)))
    if bad:
        print("❌ 写しが元と違う：" + "・".join(bad) + "（python3 build/sync_schema.py --update で取り込む）")
        return 1
    print("✅ 型（knowledge-net）と見た目の値（math-lab）の写しは元と同じ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
