"""検証 → 検算 → 生成 → 生成物の検査。

使い方:
    python3 build/build.py            # 全部
    python3 build/build.py --check    # 検証と検算だけ（生成しない）
出力: out/notion/<ID>.md・guide.md・root.md と out/labs/（ラボの場面ごとの版）
どこかで誤りが見つかったら、何も公開せずに止まる（終了コード 1）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from labs import build_labs, validate_labs  # noqa: E402
from lint import lint_page  # noqa: E402
from model import ROOT, load_course, load_yaml, run_checks, validate  # noqa: E402
from render_notion import NotionRenderer  # noqa: E402


def fail(title: str, errors: list[str]) -> int:
    print(f"❌ {title}")
    for e in errors:
        print("  -", e)
    return 1


def main(argv: list[str]) -> int:
    course = load_course()
    errors = validate(course) + validate_labs(course)
    n, check_errors = run_checks(course)
    errors += check_errors
    print(f"単元 {len(course.units)}・問題 {sum(len(u['problems']) for u in course.units.values())}・検算 {n} 件")
    if errors:
        return fail("エラー", errors)
    print("✅ 検証・検算 OK")
    if "--check" in argv:
        return 0

    labs = build_labs(course)
    assets = set(course.figures) | {v["asset"] for v in labs} | set(course.labs)
    r = NotionRenderer(course, load_yaml(ROOT / "publish" / "notion.yaml"))
    pages = {"guide": r.guide_page(), "root": r.root_page()}
    pages.update({uid: r.unit_page(uid) for uid in course.units})
    lint = [e for name, md in pages.items() for e in lint_page(name, md, assets)]
    if lint:
        return fail("生成物の検査", lint)
    outdir = ROOT / "out" / "notion"
    outdir.mkdir(parents=True, exist_ok=True)
    for name, md in pages.items():
        (outdir / f"{name}.md").write_text(md, encoding="utf-8")
    print(f"生成：out/notion/ に {len(pages)} ページ、out/labs/ に {len(labs)} 版（生成物の検査 OK）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
