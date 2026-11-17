"""旧版の削除の管理表（publish/legacy.yaml）を調べる。

各項目の条件を、原本と生成物に照らして「まだ参照あり／削除の候補／アーカイブ済み／削除済み」に分ける。
build が見るのは原本・生成物からの参照（6条件の ② の一部）と require（① の一部）だけ。削除してよいかは6条件（checks）と承認（approved）で決まる（渡辺さん 2026-11-17）。
削除済み（deleted）なのに文字列・ID が残っていたら誤りとして返す。
"""
from __future__ import annotations

from pathlib import Path

from model import ROOT, load_yaml, term_written

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
        missing = [t["id"] for t in terms if not term_written(t)]   # 文脈の見出しは定義を持たないが書き終えた形（model.term_state）
        return f"定義のない用語 {len(missing)}" if missing else None
    if name == "term_pages_unlinked":   # 説明のある概念はネットワークを指すので、旧版を指す残りだけ数える
        terms = {t["id"]: t for t in load_yaml(ROOT / "content" / "terms.yaml") or []}
        n = sum(1 for tid in (target.get("terms") or {}) if not term_written(terms.get(tid, {})))
        return f"旧版の用語ページを指す用語 {n}" if n else None
    return f"知らない検査 {name}"


SIX = {"content": "① 内容の移行", "refs": "② 参照の移行", "readback": "③ 公開内容の一致", "function": "④ 機能の代替",
       "backup": "⑤ 復元できる", "deps": "⑥ 依存がない"}
SIX_RULE_FROM = "2026-11-17"   # この日より前に削除した項目（LEG-confirm-q）は、6条件の決まりの前の記録として除く


def six_status(it: dict) -> tuple[int, list[str]]:
    """(確認済みの数, 誤り)。確認済みには evidence が要る。知らない条件・知らない状態は誤り"""
    checks, err, ok = it.get("checks") or {}, [], 0
    for k, v in checks.items():
        if k not in SIX:
            err.append(f"{it['id']}：checks に知らない条件 {k}")
            continue
        st = (v or {}).get("state")
        if st not in ("未確認", "確認済み", "問題あり"):
            err.append(f"{it['id']}：{SIX[k]} の state は 未確認・確認済み・問題あり のどれか（{st}）")
        elif st == "確認済み":
            if not (v or {}).get("evidence"):
                err.append(f"{it['id']}：{SIX[k]} を確認済みにするなら、何で確かめたか（evidence）を書く")
            else:
                ok += 1
    return ok, err


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
        state = "deleted" if it.get("deleted") else "archived" if it.get("archived") else ("still" if reasons else "ready")
        out.append({"item": it, "state": state, "reasons": reasons})
    return out


def legacy_status(pages: dict[str, str], path: Path | None = None) -> tuple[list[str], list[str]]:
    """(誤り, 状態の行) を返す。"""
    errors, lines = [], []
    for r in legacy_report(pages, path):
        it, reasons = r["item"], r["reasons"]
        ok, err6 = six_status(it)
        errors += err6
        before_rule = bool(it.get("deleted")) and str(it["deleted"]) < SIX_RULE_FROM
        if (it.get("archived") or it.get("deleted")) and not before_rule:
            if ok < len(SIX) or not it.get("approved"):
                errors.append(f"{it['id']}（{it['name']}）：アーカイブ・削除は、6条件がすべて確認済み（今 {ok}/{len(SIX)}）で、削除の承認（approved）を書いてから")
            if it.get("deleted") and not it.get("archived"):
                errors.append(f"{it['id']}（{it['name']}）：削除の前にアーカイブ（archived）する（二段階）")
        if r["state"] == "deleted":
            if reasons:
                errors.append(f"{it['id']}（{it['name']}）は削除済みなのに残っている：" + "、".join(reasons))
            else:
                lines.append(f"  削除済み　{it['name']}（{it['deleted']}）")
        elif r["state"] == "still":
            lines.append(f"  まだ　　　{it['name']}：" + "、".join(reasons[:2]) + f"（予定：{it.get('when', '未定')}）")
        elif r["state"] == "archived":
            lines.append(f"  アーカイブ済み　{it['name']}（{it['archived']}。参照や同期に問題がないことを確かめてから削除）")
        else:
            lines.append(f"  削除の候補　{it['name']}（build の確認は通った。6条件 {ok}/{len(SIX)} 確認済み・承認{'あり' if it.get('approved') else 'なし'}）")
    return errors, lines
