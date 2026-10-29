"""旧版の削除の管理表（publish/legacy.yaml）を調べる。

各項目の条件を、原本と生成物に照らして「まだ参照あり／削除してよい／削除済み」に分ける。
削除済み（deleted）なのに文字列・ID が残っていたら誤りとして返す。
"""
from __future__ import annotations

from pathlib import Path

from model import ROOT, load_yaml

SCAN_DIRS = ("content", "templates")


def _sources() -> dict[str, str]:
    texts = {}
    for d in SCAN_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.suffix in (".md", ".yaml", ".yml"):
                texts[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8")
    p = ROOT / "publish" / "notion.yaml"
    texts["publish/notion.yaml"] = p.read_text(encoding="utf-8")
    return texts


def _nid(n) -> str:
    return str(n["id"] if isinstance(n, dict) else n).replace("-", "")


def _require(name: str, target: dict) -> str | None:
    """満たしていなければ理由を返す。"""
    if name == "terms_defined":
        terms = load_yaml(ROOT / "content" / "terms.yaml") or []
        missing = [t["id"] for t in terms if not t.get("definition")]
        return f"定義のない用語 {len(missing)}" if missing else None
    if name == "term_pages_unlinked":   # 説明のある概念はネットワークを指すので、旧版を指す残りだけ数える
        terms = {t["id"]: t for t in load_yaml(ROOT / "content" / "terms.yaml") or []}
        n = sum(1 for tid in (target.get("terms") or {}) if not terms.get(tid, {}).get("definition"))
        return f"旧版の用語ページを指す用語 {n}" if n else None
    return f"知らない検査 {name}"


def legacy_report(pages: dict[str, str], path: Path | None = None) -> list[dict]:
    """項目ごとに {item, state（still／ready／deleted）, reasons} を返す。
    pages は生成した Notion ページ（名前→本文）。「旧版（削除予定）」ページ（legacy）は旧版を並べるページなので調べない。"""
    table = load_yaml(path or ROOT / "publish" / "legacy.yaml") or {}
    target = load_yaml(ROOT / "publish" / "notion.yaml") or {}
    texts = _sources() | {f"out/notion/{k}.md": v for k, v in pages.items() if k != "legacy"}
    out = []
    for it in table.get("items", []):
        needles = list(it.get("absent", [])) + [_nid(n) for n in it.get("notion", [])]
        found = [(s, f) for s in needles for f, t in texts.items() if s in t]
        reasons = [f"「{s}」が {f}" for s, f in found[:3]] + (["…"] if len(found) > 3 else [])
        reasons += [r for r in (_require(n, target) for n in it.get("require", [])) if r]
        state = "deleted" if it.get("deleted") else ("still" if reasons else "ready")
        out.append({"item": it, "state": state, "reasons": reasons})
    return out


def legacy_status(pages: dict[str, str], path: Path | None = None) -> tuple[list[str], list[str]]:
    """(誤り, 状態の行) を返す。"""
    errors, lines = [], []
    for r in legacy_report(pages, path):
        it, reasons = r["item"], r["reasons"]
        if r["state"] == "deleted":
            if reasons:
                errors.append(f"{it['id']}（{it['name']}）は削除済みなのに残っている：" + "、".join(reasons))
            else:
                lines.append(f"  削除済み　{it['name']}（{it['deleted']}）")
        elif r["state"] == "still":
            lines.append(f"  まだ　　　{it['name']}：" + "、".join(reasons[:2]) + f"（予定：{it.get('when', '未定')}）")
        else:
            lines.append(f"  削除してよい　{it['name']}（この生成物を Notion に公開してから削除し、deleted に日付を書く）")
    return errors, lines
