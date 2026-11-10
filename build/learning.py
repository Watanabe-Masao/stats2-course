"""学ぶ順（製本 ⑥。M6・#266）。

学ぶ順 ＝ 関係から求める候補 ＋ 足す − 外す（⑥ の 2）。
- 候補：関係の種類ごとの向き（⑥ の 3 の表）で、build がここで求める。原本には書かない。
- 足す・外す：content/learning.yaml（LRN-…。op・from・to・reason・version）。
止めること（⑥ の 2）：外す相手の候補がない・足すが候補と同じ・たどれば着く前提知識の重ね・合わせた学ぶ順の輪。
書き出し：`learning`（足す・外すの行）と `learning_order`（仕上がりの組と、どこから来たか。型 v2 の改訂4）。
画面は ⑥ の 3 の表を持たず、learning_order だけを読む（渡辺さん 2026-11-10。knowledge-net の docs/decisions.md「学ぶ順」）。
"""
from __future__ import annotations

import re

from model import CONTENT, load_yaml

LEARNING = CONTENT / "learning.yaml"
LRN_ID = re.compile(r"^LRN-[A-Za-z0-9-]+$")

# ⑥ の 3：関係（from → to）から、どちらを先に学ぶ候補にするか。"from"＝from が先、"to"＝to が先
CANDIDATE_SIDE = {
    "定める": "from",    # 構成要素を知らないと定義が読めない
    "一種": "to",        # 親の定義を満たすものとして区別する
    "移る": "from",      # 元の形（と通す操作の概念）を知ってから行き先を読む
    "従う": "to",        # 分布を知ってから、何が従うかを読む
    "推定する": "to",    # 何を知りたいかが先
    "導ける": "from",    # 前の主張から読む
    "根拠": "from",      # 定理を知ってから手続きの根拠として読む
}
NO_CANDIDATE = {"特別な場合", "同値", "比べる"}   # 特別な場合は教え方で向きが変わる。同値・比べるは向きがない


def load_learning() -> list[dict]:
    return (load_yaml(LEARNING) or {}).get("learning", []) if LEARNING.exists() else []


def candidates(rels: list[dict], ders: list[dict]) -> list[tuple[str, str, str]]:
    """⑥ の 3 の候補（先に学ぶ, 後に学ぶ, 来た関係・導出の id）。
    定理の点（導出）は、前提の概念 → その点（DER-…）。点の先へはつながないので、概念どうしの順・輪・重ねには効かない"""
    out: list[tuple[str, str, str]] = []
    for r in rels:
        side = CANDIDATE_SIDE.get(r.get("type"))
        if side is None:
            continue
        a, b = (r["from"], r["to"]) if side == "from" else (r["to"], r["from"])
        out.append((a, b, r["id"]))
        op = r.get("operation")
        if r["type"] == "移る" and isinstance(op, str) and op.startswith("TERM-"):   # 通す操作が概念のとき、その概念も先
            out.append((op, r["to"], r["id"]))
    for d in ders:
        for p in d.get("premises") or []:
            if p.startswith("TERM-"):
                out.append((p, d["id"], d["id"]))
    return out


def _reach(edges: list[tuple[str, str, str]], start: str, skip: str | None = None) -> set[str]:
    nxt: dict[str, list[str]] = {}
    for a, b, via in edges:
        if via != skip:
            nxt.setdefault(a, []).append(b)
    seen: set[str] = set()
    stack = [start]
    while stack:
        for y in nxt.get(stack.pop(), []):
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen


def _cycle(edges: list[tuple[str, str, str]]) -> list[tuple[str, str]] | None:
    """輪を1つ（(点, 次へ行く組の id) の並び）。なければ None"""
    nxt: dict[str, list[tuple[str, str]]] = {}
    for a, b, via in edges:
        nxt.setdefault(a, []).append((b, via))
    state: dict[str, int] = {}
    path: list[tuple[str, str]] = []

    def walk(v: str) -> list[tuple[str, str]] | None:
        state[v] = 1
        for w, via in nxt.get(v, []):
            path.append((v, via))
            if state.get(w) == 1:
                i = next(k for k, (x, _) in enumerate(path) if x == w)
                return path[i:]
            if not state.get(w):
                got = walk(w)
                if got:
                    return got
            path.pop()
        state[v] = 2
        return None

    for v in sorted(nxt):
        if not state.get(v):
            got = walk(v)
            if got:
                return got
    return None


def learning_order(rels: list[dict], ders: list[dict], rows: list[dict], terms: set[str]) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """仕上がりの学ぶ順（先, 後, source, via）と止め。source は candidate（候補）か add（足す）"""
    err: list[str] = []
    cand = candidates(rels, ders)
    pairs = {(a, b) for a, b, _ in cand}
    ids: set[str] = set()
    for x in rows:
        lid = x.get("id", "?")
        for k in ("id", "op", "from", "to", "reason", "version"):
            if x.get(k) in (None, ""):
                err.append(f"{lid}: 学ぶ順の行に {k} がない（⑥ の 2：組と理由の1文）")
        if not LRN_ID.match(str(x.get("id", ""))):
            err.append(f"{lid}: 学ぶ順の id は LRN-…")
        if lid in ids:
            err.append(f"{lid}: 学ぶ順の id が重なっている")
        ids.add(lid)
        if x.get("op") not in ("add", "remove"):
            err.append(f"{lid}: op は add（足す）か remove（外す）")
        for k in ("from", "to"):
            if x.get(k) and x[k] not in terms:
                err.append(f"{lid}: {k} の {x[k]} が用語にない（学ぶ順は概念どうし。⑥ の 5 の 5：別の教材の概念は前提知識にしない）")
        if x.get("from") and x.get("from") == x.get("to"):
            err.append(f"{lid}: from と to が同じ")
    removes = {(x["from"], x["to"]): x for x in rows if x.get("op") == "remove"}
    adds = [x for x in rows if x.get("op") == "add"]
    for (a, b), x in removes.items():
        if (a, b) not in pairs:
            err.append(f"{x['id']}: 外す組 {a} → {b} は候補にない（外すのは関係から求めた候補だけ。⑥ の 2）")
    for x in adds:
        if (x["from"], x["to"]) in pairs and (x["from"], x["to"]) not in removes:
            err.append(f"{x['id']}: 足す組 {x['from']} → {x['to']} は関係から候補になる（同じ組を重ねて書かない。⑥ の 2）")
        if (x["from"], x["to"]) in removes:
            err.append(f"{x['id']}: 足す組 {x['from']} → {x['to']} を、外すにも書いている")
    edges = [(a, b, "candidate", via) for a, b, via in cand if (a, b) not in removes]
    edges += [(x["from"], x["to"], "add", x["id"]) for x in adds]
    flat = [(a, b, via) for a, b, _, via in edges]
    # 直接の1段だけ（⑥ の 2）：足した A → D のほかの組で D から戻ると…ではなく、A から D へ別の道で着くなら A → D は重ね
    for x in adds:
        if x["to"] in _reach(flat, x["from"], skip=x["id"]):
            err.append(f"{x['id']}: {x['from']} → {x['to']} は、ほかの組をたどれば着くので重ねて書かない（直接の1段だけ。⑥ の 2）")
    cyc = _cycle(flat)
    if cyc:
        err.append("学ぶ順の輪：" + " → ".join(f"{v}（{via}）" for v, via in cyc) + "。組ごとに外す（op: remove と理由）か、足すを見直す（⑥ の 2・3）")
    return edges, err


def export_learning(rows: list[dict], edges: list[tuple[str, str, str, str]], g) -> dict:
    """書き出し（型 v2 の改訂4）：learning（足す・外すの行）と learning_order（仕上がりの組）"""
    out_rows = []
    for x in rows:
        e = {"id": g(x["id"]), "op": x["op"], "from": g(x["from"]), "to": g(x["to"]), "reason": x["reason"], "version": x["version"]}
        if x.get("units"):
            e["units"] = [g(u) for u in x["units"]]
        if x.get("question"):
            e["question"] = x["question"]
        if x.get("focus"):
            e["focus"] = dict(x["focus"])
        out_rows.append(e)
    return {
        "learning": out_rows,
        "learning_order": [{"from": g(a), "to": g(b), "source": s, "via": g(via)} for a, b, s, via in edges],
    }


__all__ = ["LEARNING", "CANDIDATE_SIDE", "load_learning", "candidates", "learning_order", "export_learning"]
