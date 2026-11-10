"""型 v2 の止め（build/v2_checks.py。製本への移行 M4、#264）のテスト。

確かめる対象：設計書 docs/schema-v2-design.md 3.2 の「機械で止める」のうち、型（kn-schema-v2.json）で書けないもの：
  端の姿（⑤ の 4 の表・姿が2つ以上のときの from_form/to_form）、定めるの from が基準の定義に出ること、導けるの主張の述語の役、
  参照する主張と通す定理、基準の定義に出る概念の扱い（#86）、一種の親の数、1つの組に重ねられる関係、定理の点で2つを結ぶこと（⑤ の 6）、定義の依存の輪、移した分類に残る legacy_type。
想定する故障：v2 の種類で書いた行が、⑤ と反対の端（確率変数 → 確率変数 の従う など）・構成要素でない定める・前提が2つの導けるを通してしまう。
  あるいは、正しく書いた行や移していない行（legacy_type）を止めて、今の教材の build を落とす。
見つけ方：手で書いた小さな v2 のデータ（下の base。⑤ の例から取った組）が止まらないことを先に確かめ、1つずつ誤りを入れた写しが、
  それぞれ決まった止めの文で止まることを見る。教材の今の書き出し（v2 の種類の行が0）が止まらないことも見る。
既存との違い：test_build.py の test_v2_export_is_same_as_v1 は型と書き出しの形だけを見る。ここは型で書けない、行と概念のつながりを見る。
独立性：base は教材の原本からではなく、製本 ⑤ の例から手で書いた（止めの実装と同じ読み違いを共有しないため）。
検出の確かめ：各行は、誤りのない base では止まらないことを同じテストの中で確かめてから、誤りを入れて止まることを見る。
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from v2_checks import v2_errors  # noqa: E402


def C(cid: str, forms: list[str], **kw) -> dict:
    return {"id": f"t:{cid}", "name": cid, "status": "filled", "category": kw.pop("category", "確率分布"), "forms": forms, **kw}


def base() -> dict:
    binom_f = {"id": "F-binom", "tree": {"op": "eq", "args": [{"op": "fn", "name": "P", "args": [{"sym": "k"}]},
                                                       {"op": "mul", "args": [{"op": "fn", "name": "comb", "args": [{"sym": "n"}, {"sym": "k"}]},
                                                                              {"sym": "p"}]}]},
               "symbols": [{"key": "P", "symbol": "P", "concept": "t:prob"}, {"key": "comb", "symbol": "C", "concept": "t:comb"},
                           {"key": "n", "symbol": "n"}, {"key": "k", "symbol": "k"}, {"key": "p", "symbol": "p"}]}
    concepts = [
        C("prob", ["number"], basis={"text": "事象に割り当てる数", "terms": []}),
        C("comb", ["number"], basis={"text": "選び方の数", "terms": []}),
        C("binom", ["distribution"], formulas=[binom_f],
          basis={"formula": "F-binom", "excludes": [{"concept": "t:prob", "kind": "使われる場", "text": "確率関数の値が確率であることは使われる場（テストの見本）"}]}),
        C("bern", ["distribution"], basis={"text": "1回の試行の分布", "terms": ["t:prob"]}),
        C("normal", ["distribution"], basis={"text": "正規分布", "terms": []}),
        C("stdnormal", ["distribution"], basis={"text": "標準正規分布", "terms": []}),
        C("poisson", ["distribution"], basis={"text": "ポアソン分布", "terms": []}),
        C("xbar", ["rv"], basis={"text": "標本平均", "terms": []}),
        C("mu", ["number"], basis={"text": "母平均", "terms": []}),
        C("indep", ["property"], basis={"text": "独立", "terms": []}),
        C("uncorr", ["property"], basis={"text": "無相関", "terms": []}),
        C("expect", ["operation", "number"], basis={"text": "期待値", "terms": []}),
        C("estimator", ["rv"], basis={"text": "推定量", "terms": []}),
        C("statistic", ["rv"], basis={"text": "統計量", "terms": []}),
        C("clt", ["proposition"], basis={"text": "中心極限定理", "terms": []}, claims=["t:CLM-9"]),
        C("other", ["number"], category="要約", basis={"text": "移していない分類の語", "terms": []}),
    ]
    relations = [
        {"id": "t:REL-1", "type": "定める", "from": "t:comb", "to": "t:binom"},
        {"id": "t:REL-2", "type": "特別な場合", "from": "t:bern", "to": "t:binom", "fix": "param_value", "fix_text": "n＝1"},
        {"id": "t:REL-3", "type": "移る", "from": "t:bern", "to": "t:binom", "mode": "exact", "operation": "独立な n 個の和"},
        {"id": "t:REL-4", "type": "推定する", "from": "t:xbar", "to": "t:mu", "properties": ["t:CLM-1"]},
        {"id": "t:REL-5", "type": "導ける", "from": "t:indep", "to": "t:uncorr", "claim": "t:CLM-13"},
        {"id": "t:REL-6", "type": "比べる", "from": "t:binom", "to": "t:poisson", "axis": "回数の上限", "same": "回数を数える", "differ": "上限"},
        {"id": "t:REL-7", "type": "移る", "from": "t:binom", "to": "t:poisson", "mode": "limit", "claim": "t:CLM-5a"},
        {"id": "t:REL-8", "type": "一種", "from": "t:estimator", "to": "t:statistic"},
        {"id": "t:REL-9", "type": "従う", "from": "t:xbar", "to": "t:stdnormal", "claim": "t:CLM-9", "theorem": "t:clt"},
        {"id": "t:REL-10", "type": "定める", "from": "t:expect", "to": "t:mu", "from_form": "operation"},
        {"id": "t:REL-12", "type": "定める", "from": "t:prob", "to": "t:bern"},
        {"id": "t:REL-11", "legacy_type": "前提", "premise": "learning", "from": "t:prob", "to": "t:other"},
    ]
    claims = [
        {"id": "t:CLM-13", "premises": {"subjects": ["t:xbar"], "predicates": ["t:indep"]}, "conclusion": {"subjects": ["t:xbar"], "predicates": ["t:uncorr"]}},
        {"id": "t:CLM-9", "premises": {"subjects": ["t:xbar"]}, "conclusion": {"subjects": ["t:xbar"], "predicates": ["t:stdnormal"]}},
        {"id": "t:CLM-5a"}, {"id": "t:CLM-1"},
    ]
    # mu の基準の定義に expect を出す（REL-10 の定めるが通るように）
    concepts[8]["basis"]["terms"] = ["t:expect"]
    return {"version": 2, "course": {"id": "t", "v2_ready": ["確率分布"]}, "concepts": concepts, "relations": relations, "claims": claims}


def rel(d: dict, rid: str) -> dict:
    return next(r for r in d["relations"] if r["id"] == f"t:{rid}")


def con(d: dict, cid: str) -> dict:
    return next(c for c in d["concepts"] if c["id"] == f"t:{cid}")


BREAKS = [
    ("端に姿がない", lambda d: con(d, "comb").pop("forms"), "姿（forms）がない"),
    ("姿が2つ以上なのに使う姿がない", lambda d: rel(d, "REL-10").pop("from_form"), "使う姿 from_form を書く"),
    ("使う姿がその概念にない", lambda d: rel(d, "REL-10").update(from_form="rv"), "from_form rv は"),
    ("従うの from が確率変数でない", lambda d: rel(d, "REL-9").update(**{"from": "t:mu", "claim": "t:CLM-9"}), "(from, to) の姿が"),
    ("推定するの to が数でない", lambda d: rel(d, "REL-4").update(to="t:normal"), "(from, to) の姿が"),
    ("移るの両端の姿が違う", lambda d: rel(d, "REL-3").update(to="t:mu"), "from と to が同じ姿"),
    ("比べるの両端の姿が違う", lambda d: rel(d, "REL-6").update(to="t:xbar"), "from と to が同じ姿"),
    ("導けるの端が命題・性質でない", lambda d: rel(d, "REL-5").update(to="t:mu"), "to の姿が"),
    ("定めるの from が基準の定義に出ない", lambda d: rel(d, "REL-1").update(**{"from": "t:normal"}), "to の基準の定義に出ない"),
    ("定めるの to に基準の定義がない", lambda d: con(d, "binom").pop("basis"), "基準の定義（basis）がない"),
    ("式の記号表にあっても木に出ない記号の概念は構成要素にしない",
     lambda d: con(d, "binom")["formulas"][0]["tree"]["args"].__setitem__(1, {"sym": "p"}), "to の基準の定義に出ない"),
    ("導けるの from が前提の述語にない", lambda d: next(c for c in d["claims"] if c["id"] == "t:CLM-13")["premises"].update(predicates=[]), "前提の述語にない"),
    ("導けるの to が結論の述語にない", lambda d: next(c for c in d["claims"] if c["id"] == "t:CLM-13")["conclusion"].update(predicates=[]), "結論の述語にない"),
    ("導けるの前提の述語に from 以外がある", lambda d: next(c for c in d["claims"] if c["id"] == "t:CLM-13")["premises"]["predicates"].append("t:prob"), "from 以外"),
    ("主張がない", lambda d: d["claims"].pop(), "主張 t:CLM-1 がない"),
    ("通す定理の姿が命題でない", lambda d: rel(d, "REL-9").update(theorem="t:mu"), "姿が命題でない"),
    ("一種の親が2つ", lambda d: d["relations"].append({"id": "t:REL-x", "type": "一種", "from": "t:estimator", "to": "t:xbar"}), "一種の親が2つ以上"),
    ("同じ組に重ねられない関係", lambda d: d["relations"].append({"id": "t:REL-x", "type": "定める", "from": "t:binom", "to": "t:poisson"}), "重ねられない"),
    # 比べるを同じ組に2本（#333。比べるを数えずに通していた。#332 の確かめ V が見つけた）
    ("同じ組に比べる2本", lambda d: d["relations"].append({"id": "t:REL-x", "type": "比べる", "from": "t:poisson", "to": "t:binom",
                                                       "axis": "別の軸", "same": "同じ", "differ": "違う"}), "重ねられない"),
    ("移していない行と重なる", lambda d: d["relations"].append({"id": "t:REL-x", "legacy_type": "材料", "from": "t:comb", "to": "t:binom"}), "重ねられない"),
    ("定理で結べる組に theorem を添えない", lambda d: rel(d, "REL-9").pop("theorem"), "theorem として添える"),
    ("定めるの輪", lambda d: (con(d, "comb")["basis"].update(terms=["t:binom"]),
                         d["relations"].append({"id": "t:REL-x", "type": "定める", "from": "t:binom", "to": "t:comb"})), "定めるの輪"),
    # #86：基準の定義に出る概念は、定める・一種の親・除外のどれかで扱う（移した分類だけ）
    ("基準の定義に出る概念を扱っていない", lambda d: con(d, "binom")["basis"].pop("excludes"), "どれでも扱っていない"),
    ("除外した概念から定めるも書く", lambda d: d["relations"].append({"id": "t:REL-x", "type": "定める", "from": "t:prob", "to": "t:binom"}),
     "定めると basis.excludes の両方"),
    ("移した分類に legacy_type が残る", lambda d: d["relations"].append({"id": "t:REL-x", "legacy_type": "前提", "premise": "mathematical", "from": "t:prob", "to": "t:poisson"}),
     "legacy_type（前提）が残っている"),
]


class TestV2Checks(unittest.TestCase):
    def test_base_passes(self):
        self.assertEqual(v2_errors(base()), [])

    def test_each_break_is_stopped(self):
        for name, mutate, msg in BREAKS:
            with self.subTest(name):
                d = base()
                self.assertEqual(v2_errors(d), [])
                mutate(d)
                errs = v2_errors(d)
                self.assertTrue(any(msg in e for e in errs), f"{name}: {errs}")

    def test_allowed_overlaps_pass(self):
        # 重ねてよい組（⑤ の 7）：包含＋移る（REL-2・REL-3）と、比べる＋移る（REL-6・REL-7）は base に入っていて止まらない。
        # 移していない分類の行（REL-11 の行き先は「要約」）の legacy_type も止めない。
        # 検出の確かめ：重ねてよい組の決まりを「1つの組に1つ」だけにすると、REL-2・REL-3 で止まって落ちる
        d = base()
        self.assertTrue({r["id"] for r in d["relations"]} >= {"t:REL-2", "t:REL-3", "t:REL-6", "t:REL-7", "t:REL-11"})
        self.assertEqual(v2_errors(d), [])

    def test_kind_parent_and_unmigrated_are_not_stopped(self):
        # #86 の止めは、一種の親を候補から外し、移していない分類の概念には掛けない。
        # 検出の確かめ：一種の親を外す行（kind_parent）を消すと1つ目が、分類の条件（ready）を消すと2つ目が落ちる
        d = base()
        con(d, "binom")["basis"].pop("excludes")
        d["relations"].append({"id": "t:REL-x", "type": "一種", "from": "t:binom", "to": "t:prob"})
        self.assertFalse([e for e in v2_errors(d) if "扱っていない" in e])
        # 混ざった包含の連なり（⑤ の包含。#290）：二項分布 →（特別な場合）normal（見本の都合の名前）→（一種）確率 でも親として外す。
        # 検出の確かめ：連なりをたどらず直接の親だけを見ると落ちる
        d = base()
        con(d, "binom")["basis"].pop("excludes")
        con(d, "normal")["forms"] = ["distribution"]
        d["relations"] += [{"id": "t:REL-y", "type": "特別な場合", "from": "t:binom", "to": "t:normal", "fix": "count", "fix_text": "見本"},
                           {"id": "t:REL-z", "type": "一種", "from": "t:normal", "to": "t:prob"}]
        self.assertFalse([e for e in v2_errors(d) if "扱っていない" in e])
        d = base()
        con(d, "binom")["basis"].pop("excludes")
        d["course"]["v2_ready"] = []
        self.assertFalse([e for e in v2_errors(d) if "扱っていない" in e])

    def test_reached_and_theorem_terms_are_handled(self):
        # ⑤ の構成（#290）：ほかの直接の構成要素をたどって着く概念は線を書かないので、扱ったと数える。
        # 定理の点（姿が命題）の基準の定義に出る概念は、その主張の前提・結論・条件に出してつなぐ（⑤ の 5 の表。#295 の確率で、事象・条件付き確率などが当たった）。
        # 想定する故障：たどって着く概念や定理の主張に出る概念まで「扱っていない」と止め、⑤ に合う原本の build を落とす。逆に、主張にも出ない概念を通す。
        # 検出の確かめ：たどる所（reach）を直接の親だけにすると1つ目が、定理の主張を見る所を消すと2つ目が落ち、主張に出ない概念は3つ目で止まる（2026-11-09 に手元で確かめた）
        d = base()
        d["concepts"].append(C("mix", ["distribution"], basis={"text": "ベルヌーイ分布を混ぜたもの", "terms": ["t:bern", "t:prob"]}))
        d["relations"].append({"id": "t:REL-x", "type": "定める", "from": "t:bern", "to": "t:mix"})   # 確率は ベルヌーイ分布 ← 確率 でたどって着く
        self.assertEqual([e for e in v2_errors(d) if "扱っていない" in e], [])
        d = base()
        con(d, "clt")["basis"]["terms"] = ["t:xbar", "t:stdnormal"]   # 主張 CLM-9 の前提・結論に出る
        self.assertEqual([e for e in v2_errors(d) if "扱っていない" in e], [])
        con(d, "clt")["basis"]["terms"].append("t:mu")   # 主張に出ず、たどっても着かない
        self.assertTrue([e for e in v2_errors(d) if "t:mu を、定める" in e])

    def test_learning_rows_after_m6(self):
        # 前提（learning）は M6（#266）で学ぶ順（learning.yaml）へ移した。移した分類に残る前提（learning）も、ほかの legacy_type と同じく止める。
        # 検出の確かめ：M6 の前の例外（前提 learning を飛ばす行）を戻すと落ちる
        d = base()
        d["relations"].append({"id": "t:REL-x", "legacy_type": "前提", "premise": "learning", "from": "t:prob", "to": "t:poisson"})
        self.assertTrue([e for e in v2_errors(d) if e.startswith("t:REL-x:") and "legacy_type（前提）" in e])

    def test_current_export_passes(self):
        # 教材の今の書き出し（移した分類を含む。#289 から確率分布）は止まらない
        import network
        from model import load_course
        c = load_course()
        d = network.export_v2(c, {"site_base_url": ""})
        self.assertEqual(v2_errors(d), [])


if __name__ == "__main__":
    unittest.main()
