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

from figures import build_figures, validate_figures  # noqa: E402
from legacy import legacy_report, legacy_status  # noqa: E402
from progress import notion_page as progress_page  # noqa: E402
from network import export_network, network_checks, schema_errors, validate_network, write_network  # noqa: E402
from labs import build_labs, build_site, validate_labs  # noqa: E402
from lint import lint_page  # noqa: E402
from model import ROOT, load_course, load_yaml, run_check, run_checks, validate  # noqa: E402
from render_notion import NotionRenderer  # noqa: E402


def fail(title: str, errors: list[str]) -> int:
    print(f"❌ {title}")
    for e in errors:
        print("  -", e)
    return 1


def main(argv: list[str]) -> int:
    course = load_course()
    errors = validate(course) + validate_labs(course) + validate_figures(course) + validate_network(course)
    n, check_errors = run_checks(course)
    errors += check_errors
    for tid, e in network_checks(course):   # 概念の説明に出てくる数の検算
        n += 1
        try:
            if not run_check(e):
                errors.append(f"{tid}: 検算が合わない → {e}")
        except Exception as ex:  # noqa: BLE001
            errors.append(f"{tid}: 検算式のエラー {ex} → {e}")
    print(f"単元 {len(course.units)}・問題 {sum(len(u['problems']) for u in course.units.values())}・検算 {n} 件")
    if errors:
        return fail("エラー", errors)
    print("✅ 検証・検算 OK")
    pending = [uid for uid, u in course.units.items() if u.get("visuals_pending")]
    if pending:
        print(f"⚠ 例題・問題のラボか図がまだの単元：{', '.join(pending)}（unit.yaml の visuals_pending）")
    from network import relations_without_figures
    nofig = relations_without_figures()
    if nofig:
        print(f"⚠ 図のない関係（変換・対比・導出・一般化）{len(nofig)}本：{', '.join(nofig)}（relations.yaml の figures。#95）")
    if "--check" in argv:
        return 0

    figs = build_figures(course)
    labs = build_labs(course)
    site = build_site(course)
    assets = set(course.figures) | {v["asset"] for v in labs} | set(course.labs)
    r = NotionRenderer(course, load_yaml(ROOT / "publish" / "notion.yaml"))
    pages = {"guide": r.guide_page(), "root": r.root_page()}
    pages.update({uid: r.unit_page(uid) for uid in course.units})
    if r.t.get("home_page"):
        pages["home"] = r.home_page()
    if r.t.get("progress_page"):
        pages["progress"] = progress_page(course, r.t)
    if r.t.get("legacy_page"):
        pages["legacy"] = r.legacy_page(legacy_report(pages))
    lint = [e for name, md in pages.items() for e in lint_page(name, md, assets)]
    if lint:
        return fail("生成物の検査", lint)
    net = export_network(course, r.t)
    net_errors = schema_errors(net)
    if net_errors:
        return fail("知識ネットワークのデータ（docs/knowledge-net/schema/kn-schema-v1.json）", net_errors)
    legacy_errors, legacy_lines = legacy_status(pages)
    if legacy_errors:
        return fail("旧版の削除の管理表（publish/legacy.yaml）", legacy_errors)
    outdir = ROOT / "out" / "notion"
    outdir.mkdir(parents=True, exist_ok=True)
    for name, md in pages.items():
        (outdir / f"{name}.md").write_text(md, encoding="utf-8")
    print(f"生成：out/notion/ に {len(pages)} ページ、out/labs/ に {len(labs)} 版、out/site/ にラボ {sum(1 for e in site if not e['query'])} 本・図 {len(course.figures)}（問題・例題の図 {len(figs)}）（生成物の検査 OK）")
    filled = sum(1 for x in net["concepts"] if x["status"] == "filled")
    print(f"知識ネットワーク：{write_network(net)}（概念 {filled}・まだ説明のない概念 {len(net['concepts']) - filled}・関係 {len(net['relations'])}・導出 {len(net['derivations'])}）")
    if legacy_lines:
        print("旧版（publish/legacy.yaml）")
        print("\n".join(legacy_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
