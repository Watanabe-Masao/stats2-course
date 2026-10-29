"""進み具合を原本から測る（最終ゴール #55 のうち、原本で確かめられるもの）。

使い方: python3 build/progress.py [--md 出力先]
人の記憶ではなく原本を数えるので、やり残し・やりこぼしがそのまま見える。
  概念      単元の用語のうち、説明（definition）のある数
  問題→概念 問題のうち、concepts: のある数
  概念図    初学（S1）に図があるか
  手本      復習「図を再現する」の近くに図かラボがあるか
  発展      新しい定義の形か（complex_pattern を使い、発展の問題に予想→照合がない）
  創造      探究の形か（「解釈」を扱い、評価の観点に「解釈」がある）
  用語      単元の用語のうち、まだ旧版の用語ページを指している数（0 が完了）
"""
from __future__ import annotations

import re
import sys

from legacy import legacy_status
from model import CONTENT, ROOT, load_course, load_yaml


def _text(uid: str, s: int) -> str:
    p = CONTENT / "units" / uid / f"S{s}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def unit_row(c, uid: str, target: dict) -> dict:
    u = c.units[uid]
    terms = u.get("terms", [])
    probs = u["problems"]
    s1, s2, s5, s6 = (_text(uid, s) for s in (1, 2, 5, 6))
    rep = re.search(r"図を再現", s2)
    if rep:
        seg = s2[rep.start():]
        m = re.search(r"\n#{2,3} ", seg[3:])
        seg = seg[: m.start() + 3] if m else seg
        model = bool(re.search(r"\{\{(fig|lab):", seg))
    else:
        model = None
    pred56 = [q for q, p in probs.items() if p.get("stage") in ("S5", "S6") and ((p.get("lab") or {}).get("predict") or (p.get("lab") or {}).get("steps"))]
    legacy_terms = target.get("terms") or {}
    return {
        "unit": uid,
        "concepts": (sum(1 for t in terms if c.terms.get(t, {}).get("definition")), len(terms)),
        "problems": (sum(1 for p in probs.values() if p.get("concepts")), len(probs)),
        "figure": "{{fig:" in s1,
        "model": model,
        "hatten": "complex_pattern" in s5 and not pred56,
        "sozo": "解釈" in s6 and bool(re.search(r"\|\s*解釈\s*\|", s6)),
        "legacy_terms": sum(1 for t in terms if t in legacy_terms and not c.terms.get(t, {}).get("definition")),
    }


def mark(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, tuple):
        done, total = v
        return "✓" if total and done == total else f"{done}/{total}"
    if isinstance(v, bool):
        return "✓" if v else "・"
    return "✓" if v == 0 else str(v)


WAVES = [("W0", ["U13", "U14", "U15", "U16"]), ("W1", ["U09", "U10", "U11", "U12"]),
         ("W2", ["U01", "U02", "U03", "U04", "U05", "U05T", "U06", "U07", "U08"]),
         ("W3", ["U17", "U18", "U19", "U20", "U21", "U22", "U23"]), ("W4", ["U24", "U25", "U26", "U27"]),
         ("W5", ["U28", "U29", "U30", "U31", "U32"])]


def _legacy_short(line: str) -> str:
    s = line.strip()
    state, rest = s.split("　", 1)
    return f"{rest.strip().split('：')[0].split('（')[0]}：{state}"


def notion_page(c=None, target: dict | None = None) -> str:
    """Notion 用（スマホ前提：表を使わず、単元ごとに1行）。"""
    c = c or load_course()
    target = target if target is not None else (load_yaml(ROOT / "publish" / "notion.yaml") or {})
    rows = {uid: unit_row(c, uid, target) for uid in c.index}
    probs = [p for u in c.units.values() for p in u["problems"].values()]
    lines = ['<callout icon="📊" color="gray_bg">\n原本から自動で数えた進み具合（公開のたびに入れ直す）。'
             "作業の一覧は GitHub の issue（最終ゴール #55）。\n</callout>", "",
             "## 最終ゴールごと", "",
             f"- 概念の説明：{sum(1 for t in c.terms.values() if t.get('definition'))}/{len(c.terms)} 語",
             f"- 問題→概念：{sum(1 for p in probs if p.get('concepts'))}/{len(probs)} 問",
             f"- 旧版を指す用語リンク：{len(target.get('terms') or {})}（0 で完了）",
             f"- 概念図 {sum(r['figure'] for r in rows.values())}/{len(rows)}・発展 {sum(r['hatten'] for r in rows.values())}/{len(rows)}"
             f"・創造 {sum(r['sozo'] for r in rows.values())}/{len(rows)} 単元",
             "- 旧版：", *[f"  - {_legacy_short(x)}" for x in legacy_status({})[1]], ""]
    for w, units in WAVES:
        lines += [f"## {w}", ""]
        for uid in units:
            r = rows[uid]
            m = lambda v: mark(v).replace("・", "未")  # noqa: E731（区切りの「・」と見分けるため）
            lines.append(f"- {uid}：概念 {m(r['concepts'])}／問題 {m(r['problems'])}／概念図 {m(r['figure'])}"
                         f"／手本 {m(r['model'])}／発展 {m(r['hatten'])}／創造 {m(r['sozo'])}／用語 {m(r['legacy_terms'])}")
        lines.append("")
    lines.append('<span color="gray">✓＝済み　未＝まだ　数字＝済み/全体（用語は旧版を指している残りの数）</span>')
    return "\n".join(lines) + "\n"


def report() -> str:
    c = load_course()
    target = load_yaml(ROOT / "publish" / "notion.yaml") or {}
    rows = [unit_row(c, uid, target) for uid in c.index]
    lines = ["# 進み具合（原本から自動で数えた値）", "",
             "✓＝済み　・＝まだ　数字＝済み/全体（用語は旧版を指している残りの数）", "",
             "| 単元 | 概念 | 問題→概念 | 概念図 | 手本 | 発展 | 創造 | 用語 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['unit']} | {mark(r['concepts'])} | {mark(r['problems'])} | {mark(r['figure'])} | "
                     f"{mark(r['model'])} | {mark(r['hatten'])} | {mark(r['sozo'])} | {mark(r['legacy_terms'])} |")
    n = len(rows)
    filled = sum(1 for t in c.terms.values() if t.get("definition"))
    probs = [p for u in c.units.values() for p in u["problems"].values()]
    lines += ["", "## 最終ゴールごと（#55）", "",
              f"- 1 概念の説明：{filled}/{len(c.terms)} 語",
              f"- 3 問題→概念：{sum(1 for p in probs if p.get('concepts'))}/{len(probs)} 問",
              f"- 4 用語リンクの切り替え：旧版を指す用語 {len(target.get('terms') or {})}（0 で完了）",
              f"- 5 概念図 {sum(r['figure'] for r in rows)}/{n}・手本 {sum(1 for r in rows if r['model'])}/{sum(1 for r in rows if r['model'] is not None)}"
              f"・発展 {sum(r['hatten'] for r in rows)}/{n}・創造 {sum(r['sozo'] for r in rows)}/{n} 単元",
              "- 6 旧版：", *[f"  {x.strip()}" for x in legacy_status({})[1]],
              "- 2 孤立した概念がないこと・7 個人の記録は、build と #54 で確かめる"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    md = report()
    if "--md" in sys.argv:
        out = sys.argv[sys.argv.index("--md") + 1]
        (ROOT / out).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / out).write_text(md, encoding="utf-8")
    print(md)
