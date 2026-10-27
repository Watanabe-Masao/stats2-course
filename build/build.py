"""検証 → 検算 → 生成。

使い方:
    python3 build/build.py            # 全部
    python3 build/build.py --check    # 検証と検算だけ（生成しない）
出力: out/notion/<ID>.md と out/notion/guide.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from model import ROOT, load_course, load_yaml, run_checks, validate  # noqa: E402
from render_notion import NotionRenderer  # noqa: E402


def main(argv: list[str]) -> int:
    course = load_course()
    errors = validate(course)
    n, check_errors = run_checks(course)
    errors += check_errors
    print(f"単元 {len(course.units)}・問題 {sum(len(u['problems']) for u in course.units.values())}・検算 {n} 件")
    if errors:
        print("❌ エラー")
        for e in errors:
            print("  -", e)
        return 1
    print("✅ 検証・検算 OK")
    if "--check" in argv:
        return 0
    target = load_yaml(ROOT / "publish" / "notion.yaml")
    r = NotionRenderer(course, target)
    outdir = ROOT / "out" / "notion"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "guide.md").write_text(r.guide_page(), encoding="utf-8")
    (outdir / "root.md").write_text(r.root_page(), encoding="utf-8")
    for uid in course.units:
        (outdir / f"{uid}.md").write_text(r.unit_page(uid), encoding="utf-8")
    print(f"生成：{outdir.relative_to(ROOT)}/ に {len(course.units) + 1} ページ")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
