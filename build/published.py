"""公開確認済みの記録（#58。2026-11-19）。

Notion に公開したページを読み戻して生成物と照らし（notion_compare.py）、一致したら、その生成物の指紋と日付を
publish/published.yaml に残す。今の生成物の指紋が記録と同じなら「公開確認済み」（公開したページが今の生成物と同じ）。
原本や build を直して生成物が変わると、入れ直して照らし直すまで「公開確認済み」でなくなる。
"""
from __future__ import annotations

import hashlib

from model import ROOT, load_yaml

RECORD = ROOT / "publish" / "published.yaml"


def digest(md: str) -> str:
    """生成物の指紋（本文の sha256 の先頭 16 字）"""
    return hashlib.sha256(md.encode("utf-8")).hexdigest()[:16]


def load() -> dict:
    return (load_yaml(RECORD) if RECORD.exists() else None) or {}


def confirmed(name: str, md: str, rec: dict | None = None) -> bool:
    """公開したページが今の生成物と同じか（記録の指紋と今の指紋が同じ）"""
    r = (rec if rec is not None else load()).get(name) or {}
    return r.get("digest") == digest(md)


def record(entries: dict[str, str], date: str) -> None:
    """照らして一致したページ（名前 → 生成物の本文）の指紋と日付を書く。ほかのページの記録は残す"""
    rec = load()
    for name, md in entries.items():
        rec[name] = {"digest": digest(md), "date": date}
    lines = ["# 公開確認済みの記録（#58）。build/notion_compare.py --record が、読み戻しが生成物と一致したページだけを書く。手で書かない。",
             "# 名前: {digest: 一致した生成物の指紋, date: 照らした日}。今の生成物の指紋と同じなら、進み具合で「公開確認済み」"]
    lines += [f"{k}: {{digest: '{v['digest']}', date: '{v['date']}'}}" for k, v in sorted(rec.items())]
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8")
