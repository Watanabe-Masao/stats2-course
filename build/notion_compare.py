"""Notion を読み戻した本文と生成物（out/notion/NAME.md）を照らす（#483 の D。渡辺さん 2026-11-17）。

確かめる対象：公開した Notion のページが、生成物と同じ中身か。本文の文だけでなく、概念 ID（ネットワークへのリンク）・問題 ID（ラボの版）・
  図の ID・ページへの参照（メンション）・見出しの並び・数（タブ・開く段・囲み・表の行・埋め込み・画像）も照らす。
許す違い：Notion が書き方を自動で直したもの（メンションの書き方、`\\_` などのエスケープ、空白・改行の数、メンションに Notion が付ける題）。
  指す先が同じなら同じとみる。
使い方：python3 build/notion_compare.py <読み戻した本文のフォルダ> NAME ...（NAME は out/notion の名前。U01・progress など）
  どれかが食い違えば終了コード 1（警告として使う。止めるか知らせるかの基準（CLAUDE.md）で、Notion の照合は公開の手順の中で知らせる）。
読み戻しは Notion の fetch の <content> の中身をそのまま NAME.md に保存したもの（CI からは Notion の鍵を使えないので、公開の手順の中で行う）。
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "notion"

HEX = r"[0-9a-f]{32}"


def _pid(s: str) -> str:
    return s.replace("-", "").lower()


def normalize(t: str) -> str:
    """Notion の自動の書き直しをそろえる"""
    t = t.replace("\r\n", "\n")
    # メンション：<mention-page url="…"/>・<mention url="…" />・<mention url="…">題</mention> → [[ページID]]
    t = re.sub(r'<mention(?:-page)?\s+url="[^"]*?(' + HEX + r')[^"]*"\s*/>', lambda m: f"[[{m.group(1)}]]", t)
    t = re.sub(r'<mention(?:-page)?\s+url="[^"]*?(' + HEX + r')[^"]*"\s*>.*?</mention(?:-page)?>', lambda m: f"[[{m.group(1)}]]", t)
    t = re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", t)   # Markdown のエスケープ（\_・\^・\{ など。記号の前の \ を外す）
    # 画像：生成物の <image source="…">説明</image> と、Notion が返す ![説明](…) は同じ
    t = re.sub(r'<image\s+source="([^"]+)"\s*>\s*(.*?)\s*</image>', lambda m: f"![{m.group(2)}]({m.group(1)})", t, flags=re.S)
    # 同じ色の span が続くのは、Notion がメンションの前後で区切っただけ（同じ色なら1つにつなぐ）
    t = re.sub(r'</span><span color="([^"]+)">', "", t)
    # データベースの子：Notion は data-source-url と inline を足して返す
    t = re.sub(r'(<database url="[^"]+")[^>]*>', r"\1>", t)
    # 表のセル：生成物は <td>文</td> の1行、Notion は <td> と文と </td> を別の行で返す（#492）
    t = re.sub(r"<(td|th)>\s*(.*?)\s*</\1>", r"<\1>\2</\1>", t, flags=re.S)
    t = re.sub(r"<br\s*/?>", "\n", t)   # 段落の中の改行：生成物は改行、Notion は <br> でつなぐ
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r" *\| *", "|", t)   # 表の区切りの前後の空白
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def facts(t: str) -> dict:
    """照らす事実：ID・参照・構造の数"""
    u = unquote(t)
    return {
        "概念・分類（ネットワーク）": sorted(set(re.findall(r"knowledge-net/\?[cg]=([^)\s\"&]+)", u))),
        "ラボの版（問題 ID を含む）": sorted(set(re.findall(r"stats2-labs/([a-z0-9_]+)/\?p=([^&\"\s)]+)", u))),
        "図": sorted(set(re.findall(r"fig/(FIG-[A-Za-z0-9-]+)\.svg", u))),
        "ページへの参照": sorted(set(re.findall(r"\[\[(" + HEX + r")\]\]", t))),
        "見出し": re.findall(r"^#{1,4} (.+)$", t, re.M),
        "数": {
            "タブ": len(re.findall(r"<tab\b", t)),
            "開く段": len(re.findall(r"<toggle\b|<details\b", t)),
            "囲み": len(re.findall(r"<callout\b", t)),
            "埋め込み": len(re.findall(r"<embed\b", t)),
            "画像": len(re.findall(r"<image\b|!\[[^\]]*\]\(", t)),
            "表の行": len(re.findall(r"^\|.*\|$|<tr\b", t, re.M)),
        },
    }


def compare(gen: str, back: str) -> list[str]:
    """食い違いの行（空なら一致）"""
    a, b = normalize(gen), normalize(back)
    fa, fb = facts(a), facts(b)
    out = []
    for k in fa:
        if fa[k] != fb[k]:
            if isinstance(fa[k], list):
                miss = [x for x in fa[k] if x not in fb[k]]
                extra = [x for x in fb[k] if x not in fa[k]]
                out.append(f"{k}：生成物にだけある {miss[:5]}・Notion にだけある {extra[:5]}" if (miss or extra) else f"{k}：並びが違う")
            else:
                out.append(f"{k}：{ {x: (fa[k][x], fb[k][x]) for x in fa[k] if fa[k][x] != fb[k][x]} }（生成物, Notion）")
    if a != b:
        al, bl = a.splitlines(), b.splitlines()
        diff = [d for d in difflib.unified_diff(al, bl, lineterm="", n=0) if d[:1] in "+-" and d[:3] not in ("+++", "---")]
        if diff:
            out.append(f"本文：{len(diff)} 行が違う（最初：{diff[0][:120]}）")
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    folder, names, bad = Path(argv[1]), argv[2:], 0
    for n in names:
        g, f = OUT / f"{n}.md", folder / f"{n}.md"
        if not f.exists():
            print(f"⚠️ {n}：読み戻しがない（{f}）")
            bad += 1
            continue
        diffs = compare(g.read_text(encoding="utf-8"), f.read_text(encoding="utf-8"))
        if diffs:
            bad += 1
            print(f"❌ {n}：")
            for d in diffs:
                print(f"   {d}")
        else:
            print(f"✅ {n}：一致（本文・ID・参照・構造）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
