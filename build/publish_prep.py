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
from labs import lab_file  # noqa: E402
from model import ROOT, load_course  # noqa: E402

PH = re.compile(r"@@ASSET:([\w@-]+)@@")


def asset_file(course, aid: str) -> Path:
    if aid.split("@")[0] in course.labs:
        return lab_file(course, aid)
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
    bad = [a for a in need if not re.fullmatch(r"file-upload://[0-9a-f-]{36}", uploads[a])]
    if bad:
        print("アップロード元の形が不正:", ", ".join(bad))
        return 1
    out = PH.sub(lambda m: uploads[m.group(1)], text)
    (ROOT / "out" / "notion" / f"{page}.publish.md").write_text(out, encoding="utf-8")
    print(f"out/notion/{page}.publish.md（{len(need)} 種類の素材を置き換え）")
    print("公開後に Notion から取得したページと照らし合わせる数：")
    for k, v in fingerprint(out).items():
        print(f"  {k}: {v}")
    return 0


def fingerprint(md: str) -> dict:
    """公開したページが生成物どおりかを、取得したページと数で照合するための要約。"""
    return {
        "タブ": md.count("<tab "),
        "開閉": md.count("<toggle>"),
        "枠": md.count("<callout"),
        "ラボ": md.count("<embed "),
        "図": md.count("<image "),
        "メンション": md.count("<mention "),
        "表の行": sum(1 for line in md.splitlines() if line.startswith("|")),
        "問題（問N・例題）": len(re.findall(r"^<b>(?:問\d+|例題|約1|計算練習|確かめ)", md, flags=re.M)),
    }


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
