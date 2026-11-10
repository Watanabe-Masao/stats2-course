"""学ぶ順（build/learning.py。製本 ⑥。M6・#266）のテスト。

確かめる対象：関係から求める候補（⑥ の 3 の向き）と、候補＋足す−外すの止め（⑥ の 2）、書き出し。
想定する故障：
  - 候補の向きを取り違える（一種で子を先にする〔#298 で関係図のたどり方に起きた〕・従う／推定するで from を先にする・
    特別な場合や比べるから候補を作る）。画面は learning_order だけで並べるので、向きの誤りはそのまま学ぶ順の誤りになる。
  - 外すの相手の候補がない・足すが候補と同じ・たどれば着く足す（重ね）・合わせた学ぶ順の輪を通す。
  - 外した候補を書き出しに残す。
見つけ方：⑥ の 3 の表から手で書いた期待の組（下の EXPECT。CANDIDATE_SIDE を読まない）と比べる。止めは、誤りのない小さなデータが
  通ることを先に見てから、1つずつ誤りを入れて決まった文で止まることを見る。今の原本が通り、外した4組が書き出しにないことも見る。
既存との違い：test_build の test_dependency_one_step は定義の依存（材料）の輪だけ。M6 の前の前提知識の重ねの止め
  （前提をさかのぼる種類でたどる形）は、ここへ移した（候補で判定する）。
検出の確かめ（2026-11-10）：CANDIDATE_SIDE の一種を "from" にすると test_candidate_sides が、_cycle の呼び出しを外すと
  test_stops の輪が、重ねの判定（_reach）を外すと test_stops の重ねが落ちることを見た。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from learning import candidates, learning_order  # noqa: E402

# ⑥ の 3 の表（関係 from → to、先に学ぶ側）から手で書いた期待：(種類, 先, 後)
EXPECT = [
    ("定める", "A", "B"),       # 構成要素（from）が先
    ("一種", "B", "A"),         # 親（to）が先
    ("移る", "A", "B"),         # from が先
    ("従う", "B", "A"),         # 分布（to）が先
    ("推定する", "B", "A"),     # 推定の相手（to）が先
    ("導ける", "A", "B"),       # from が先
    ("根拠", "A", "B"),         # 定理（from）が先
]
NONE = ["特別な場合", "同値", "比べる"]


def rel(rid: str, t: str, a: str, b: str, **kw) -> dict:
    return {"id": rid, "type": t, "from": a, "to": b, **kw}


def row(lid: str, op: str, a: str, b: str) -> dict:
    return {"id": lid, "op": op, "from": a, "to": b, "reason": "テストの理由", "version": 1}


class TestLearning(unittest.TestCase):
    def test_candidate_sides(self):
        for t, first, then in EXPECT:
            with self.subTest(t):
                self.assertEqual(candidates([rel("REL-x", t, "A", "B")], []), [(first, then, "REL-x")])
        for t in NONE:
            with self.subTest(t):
                self.assertEqual(candidates([rel("REL-x", t, "A", "B")], []), [])
        # 移るの通す操作が概念なら、その概念も先。文なら候補にしない
        got = candidates([rel("REL-x", "移る", "A", "B", operation="TERM-op"), rel("REL-y", "移る", "C", "D", operation="n→∞ とする")], [])
        self.assertEqual(sorted(got), [("A", "B", "REL-x"), ("C", "D", "REL-y"), ("TERM-op", "B", "REL-x")])
        # 定理の点は、前提の概念 → その点（結論の概念へはつながない）
        got = candidates([], [{"id": "DER-x", "premises": ["TERM-a", "REL-z"], "conclusion": "TERM-c"}])
        self.assertEqual(got, [("TERM-a", "DER-x", "DER-x")])

    def test_stops(self):
        terms = {"TERM-a", "TERM-b", "TERM-c", "TERM-d"}
        rels = [rel("REL-ab", "定める", "TERM-a", "TERM-b"), rel("REL-bc", "定める", "TERM-b", "TERM-c")]
        ok = [row("LRN-dc", "add", "TERM-d", "TERM-c")]
        edges, err = learning_order(rels, [], ok, terms)
        self.assertEqual(err, [])
        self.assertEqual(sorted((a, b, s) for a, b, s, _ in edges),
                         [("TERM-a", "TERM-b", "candidate"), ("TERM-b", "TERM-c", "candidate"), ("TERM-d", "TERM-c", "add")])

        def stop(rows, piece, rs=rels):
            _, e = learning_order(rs, [], rows, terms)
            self.assertTrue([x for x in e if piece in x], e)

        stop([row("LRN-x", "remove", "TERM-b", "TERM-a")], "候補にない")                 # 外す相手の候補がない（向きが逆）
        stop([row("LRN-x", "add", "TERM-a", "TERM-b")], "関係から候補になる")            # 足すが候補と同じ
        stop([row("LRN-x", "add", "TERM-a", "TERM-c")], "たどれば着く")                  # a → b → c があるので重ね
        stop([row("LRN-x", "add", "TERM-c", "TERM-a")], "学ぶ順の輪")                    # c → a で輪
        stop([row("LRN-x", "add", "TERM-a", "TERM-z")], "用語にない")
        stop([row("LRN-x", "add", "TERM-d", "TERM-c"), row("LRN-x", "add", "TERM-d", "TERM-b")], "重なっている")
        stop([{**row("LRN-x", "add", "TERM-d", "TERM-c"), "reason": ""}], "reason がない")
        # 輪は、輪を作る候補を外せば消え、外した候補は書き出さない
        loop = [row("LRN-x", "add", "TERM-c", "TERM-a"), row("LRN-y", "remove", "TERM-a", "TERM-b")]
        edges, err = learning_order(rels, [], loop, terms)
        self.assertEqual(err, [])
        self.assertNotIn(("TERM-a", "TERM-b"), [(a, b) for a, b, _, _ in edges])

    def test_current_source(self):
        # 今の原本は止まらず、M6 で外した4組（輪になる候補。#266・#327）は仕上がりの学ぶ順にない
        import network
        from learning import load_learning
        from model import load_course
        c = load_course()
        rels, ders = network.load_network()
        edges, err = learning_order(rels, ders, load_learning(), set(c.terms))
        self.assertEqual(err, [])
        pairs = {(a, b) for a, b, _, _ in edges}
        for gone in [("TERM-t", "TERM-std-normal"), ("TERM-chi2", "TERM-unbvar"), ("TERM-pdf", "TERM-hist"), ("TERM-perm", "TERM-fact")]:
            self.assertNotIn(gone, pairs)
        self.assertIn(("TERM-hist", "TERM-pdf"), pairs)
        self.assertIn(("TERM-fact", "TERM-perm"), pairs)
        self.assertFalse([r for r in rels if r.get("type") == "前提" and r.get("premise") == "learning"])


if __name__ == "__main__":
    unittest.main()
