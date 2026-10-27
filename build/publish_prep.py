"""生成物の @@ASSET:ID@@ を Notion のアップロード元に置き換え、公開用ファイルを作る。

使い方:
    python3 build/publish_prep.py U03                # 必要なアップロードの一覧を表示
    python3 build/publish_prep.py U03 uploads.json   # {"ASSET-ID": "file-upload://…"} で置き換え
出力: out/notion/<ID>.publish.md
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import ROOT, load_course  # noqa: E402

PH = re.compile(r"@@ASSET:([\w-]+)@@")


def asset_file(course, aid: str) -> Path:
    if aid in course.labs:
        t = course.labs[aid]
        return t["dir"] / t["file"]
    return ROOT / course.figures[aid]["file"]


def main(argv: list[str]) -> int:
    page = argv[0]
    src = ROOT / "out" / "notion" / f"{page}.md"
    text = src.read_text(encoding="utf-8")
    need = sorted(set(PH.findall(text)))
    course = load_course()
    if len(argv) == 1:
        for aid in need:
            f = asset_file(course, aid)
            print(f"{aid}\t{f.relative_to(ROOT)}\t{f.stat().st_size} bytes")
        return 0
    uploads = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    lacking = [a for a in need if a not in uploads]
    if lacking:
        print("アップロードが足りない:", ", ".join(lacking))
        return 1
    out = PH.sub(lambda m: uploads[m.group(1)], text)
    (ROOT / "out" / "notion" / f"{page}.publish.md").write_text(out, encoding="utf-8")
    print(f"out/notion/{page}.publish.md（{len(need)} 種類の素材を置き換え）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
