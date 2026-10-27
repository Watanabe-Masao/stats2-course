"""旧版との突き合わせ：旧版の数値・太字・誤解が新しい原本に残っているかを調べる。

使い方: python3 build/audit.py U03
落とす項目は migration/waivers/<ID>.yaml に理由付きで書く（書いていない欠落があると失敗）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import CONTENT, ROOT, load_yaml  # noqa: E402

NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w])")
BOLD = re.compile(r"<b>(.+?)</b>|\*\*(.+?)\*\*")
MISC = re.compile(r"^- (.+?)\s*→\s*✕")


def norm(s: str) -> str:
    s = re.sub(r"</?[a-zA-Z][^<>]*>|\*\*|\{\{[^}]*\}\}", "", s)   # タグだけ消す（検算の「a < b」を巻き込まない）
    return re.sub(r"\s+", "", s)


def new_text(uid: str) -> str:
    parts = [p.read_text(encoding="utf-8") for p in sorted((CONTENT / "units" / uid).glob("*"))]
    pf = CONTENT / "problems" / f"{uid}.yaml"
    if pf.exists():
        parts.append(pf.read_text(encoding="utf-8"))
    return "\n".join(parts)


def main(uid: str) -> int:
    old = (ROOT / "migration" / "old" / f"{uid}.md").read_text(encoding="utf-8")
    old = "\n".join(l for l in old.splitlines() if not l.startswith("<!--"))
    new = new_text(uid)
    new_n = norm(new)
    wf = ROOT / "migration" / "waivers" / f"{uid}.yaml"
    waived = (load_yaml(wf) or {}) if wf.exists() else {}
    w_num = {str(k) for k in (waived.get("numbers") or {})}
    w_phr = {str(k) for k in (waived.get("phrases") or {})}

    missing = []
    new_nums = set(NUM.findall(new))
    for n in sorted(set(NUM.findall(old)), key=lambda x: float(x.rstrip("%"))):
        if len(n.replace(".", "").rstrip("%")) > 6:
            continue  # ページIDなど
        if n not in new_nums and n not in w_num:
            ctx = re.search(rf".{{0,14}}(?<![\w.]){re.escape(n)}.{{0,14}}", old)
            missing.append(f"数値 {n}：…{ctx.group(0) if ctx else ''}…")
    phrases = {m.group(1) or m.group(2) for m in BOLD.finditer(old)}
    phrases |= {m.group(1) for line in old.splitlines() if (m := MISC.match(line))}
    for p in sorted(phrases):
        if norm(p) and norm(p) not in new_n and p not in w_phr:
            missing.append(f"語句 「{p}」")
    print(f"{uid}: 旧版の数値 {len(set(NUM.findall(old)))}・語句 {len(phrases)} を確認")
    if missing:
        print("❌ 新しい原本に見当たらない（残すか、waivers に理由を書く）")
        for m in missing:
            print("  -", m)
        return 1
    print(f"✅ 欠落なし（理由付きで落とした項目 {len(w_num) + len(w_phr)} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
