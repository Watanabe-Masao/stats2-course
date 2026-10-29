"""知識ネットワークの型（元は knowledge-net の schema/）の写しを確かめる・取り込む。

使い方:
    python3 build/sync_schema.py           # 写しが元と同じか確かめる（違えば止まる）
    python3 build/sync_schema.py --update  # 元を写しに取り込む（取り込んだら build とテストを通す）
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://raw.githubusercontent.com/Watanabe-Masao/knowledge-net/main/schema/"
FILES = ("kn-schema-v1.json", "relation-types.yaml")
COPY = ROOT / "docs" / "knowledge-net" / "schema"


def main(argv: list[str]) -> int:
    bad = []
    for name in FILES:
        try:
            with urllib.request.urlopen(BASE + name, timeout=30) as r:
                src = r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            print(f"❌ 元の型を読めない：{BASE + name}（{e}）")
            return 1
        mine = (COPY / name).read_text(encoding="utf-8")
        if src != mine:
            if "--update" in argv:
                (COPY / name).write_text(src, encoding="utf-8")
                print(f"取り込んだ：{name}")
            else:
                bad.append(name)
    if bad:
        print("❌ 型の写しが knowledge-net の元と違う：" + "・".join(bad) + "（python3 build/sync_schema.py --update で取り込む）")
        return 1
    print("✅ 型の写しは knowledge-net の元と同じ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
