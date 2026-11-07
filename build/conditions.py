"""成立条件の区分（#249 ①。型の改訂38 の conditions_detail）。

原本（terms.yaml の conditions.math／data、relations.yaml の conditions）の1行は、文字か、区分を書いた形のどちらか：
    - 各回が独立                                   # 区分なし（まだ移していない分類・データで確かめる手掛かり）
    - text: 各回が独立
      kind: 仮定                                   # 要件／仮定／目安
      claim: 成功回数が B(n, p) に従う             # 仮定のとき：何を保証する仮定か
      outside: 成功回数に二項分布を使えるとは保証できない（偶然に一致することはある）
      terms: [TERM-indep]                          # 文に出る概念（画面は押せる札にする）
      target: …  source: {source: …, locator: …}   # 目安のとき：対象の近似と出典（shared.yaml の sources の名前）

読み込むとき（normalize_*）に、行を文字の一覧に戻し、区分は _conditions_detail に分けて持つ。
今の使い手（実験室の反例の照合・式のレビューの指紋・Notion）は文字の一覧のまま読む。区分は公開の JSON にだけ出す。
"""
from __future__ import annotations

KINDS = ("要件", "仮定", "目安")
KEYS = {"text", "kind", "claim", "outside", "terms", "target", "source"}
DETAIL = "_conditions_detail"


def _split(items, scope: str | None) -> tuple[list, list]:
    texts, details = [], []
    for x in items or []:
        if isinstance(x, dict):
            texts.append(x.get("text", ""))
            details.append({**x, **({"scope": scope} if scope else {})})
        else:
            texts.append(x)
            details.append({"text": x, **({"scope": scope} if scope else {}), "_plain": True})
    return texts, details


def normalize_term(t: dict) -> None:
    cond = t.get("conditions")
    if not isinstance(cond, dict):
        return
    out, details = {}, []
    for scope in ("math", "data"):
        if scope in cond:
            out[scope], d = _split(cond[scope], scope)
            details += d
    t["conditions"] = {**cond, **out}
    if any(not d.get("_plain") for d in details):
        t[DETAIL] = details


def normalize_relation(r: dict) -> None:
    if not isinstance(r.get("conditions"), list):
        return
    r["conditions"], details = _split(r["conditions"], None)
    if any(not d.get("_plain") for d in details):
        r[DETAIL] = details


def detail_errors(owner: str, details: list, terms: set, sources: set, ready: bool, is_relation: bool) -> list[str]:
    """区分の検査。ready（関係図に移した分類）なら、数学の行（関係はすべての行）に区分が要る"""
    err = []
    for i, d in enumerate(details, 1):
        at = f"{owner}: 成立条件の{'' if is_relation else ('式の' if d.get('scope') == 'math' else 'データの')}{i}行目「{d.get('text', '')[:20]}」"
        if d.get("_plain"):
            if ready and (is_relation or d.get("scope") == "math"):
                err.append(f"{at}：関係図に移した分類なので、要件・仮定・目安のどれかを書く（#249 ①）")
            continue
        extra = set(d) - KEYS - {"scope"}
        if extra:
            err.append(f"{at}：知らない項目 {'・'.join(sorted(extra))}")
        if not d.get("text"):
            err.append(f"{at}：text がない")
        k = d.get("kind")
        if k is None:
            if is_relation or d.get("scope") == "math":
                err.append(f"{at}：区分の形で書いたなら kind（要件・仮定・目安）を書く（区分のないのはデータで確かめる手掛かりだけ）")
        elif k not in KINDS:
            err.append(f"{at}：kind は要件・仮定・目安のどれか（{k}）")
        if k and not d.get("outside"):
            err.append(f"{at}：外れたときの説明（outside）がない")
        if k == "仮定" and not d.get("claim"):
            err.append(f"{at}：仮定には、何を保証する仮定か（claim）を書く")
        if k == "目安":
            if not d.get("target"):
                err.append(f"{at}：目安には対象の近似（target）を書く")
            src = d.get("source") or {}
            if not src.get("source"):
                err.append(f"{at}：目安には出典（source.source）を書く")
            elif src["source"] not in sources:
                err.append(f"{at}：出典 {src['source']} が shared.yaml の sources にない")
        if k != "仮定" and d.get("claim"):
            err.append(f"{at}：claim は仮定にだけ書く")
        if k != "目安" and (d.get("target") or d.get("source")):
            err.append(f"{at}：target・source は目安にだけ書く")
        for tid in d.get("terms") or []:
            if tid not in terms:
                err.append(f"{at}：terms の {tid} が用語にない")
    return err


def export_detail(details: list, g, source_url: dict) -> list[dict]:
    """公開の JSON の conditions_detail（型の改訂38）。id は教材名を付け、出典は title・locator・url の形に"""
    out = []
    for d in details:
        e = {"text": d["text"], **({"scope": d["scope"]} if d.get("scope") else {})}
        for k in ("kind", "claim", "outside", "target"):
            if d.get(k):
                e[k] = d[k]
        if d.get("terms"):
            e["terms"] = [g(t) for t in d["terms"]]
        if d.get("source"):
            s = d["source"]
            e["source"] = {"title": s["source"], **({"locator": s["locator"]} if s.get("locator") else {}),
                           **({"url": source_url[s["source"]]} if source_url.get(s["source"]) else {})}
        out.append(e)
    return out
