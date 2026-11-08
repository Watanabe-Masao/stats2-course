"""build/ の単体テスト。使い方: python3 -m unittest discover -s tests

原本の検証・本文の構文・表示・生成物の検査・ラボの版が、誤りを見逃さないことを確かめる。
「正しいものが通る」だけでなく「間違いを入れたら止まる」ことを1つずつ確かめる。
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))

from labs import squeeze, validate_labs, variants  # noqa: E402
from lint import lint_page  # noqa: E402
from model import load_course, load_yaml, numbers, parse_blocks, run_check, run_checks, validate  # noqa: E402
from render_notion import COMP, NotionRenderer  # noqa: E402

COURSE = load_course()
TARGET = load_yaml(Path(__file__).resolve().parent.parent / "publish" / "notion.yaml")


def course():
    return copy.deepcopy(COURSE)


class TestCourseIsClean(unittest.TestCase):
    def test_validate_and_checks_pass(self):
        c = course()
        self.assertEqual(validate(c) + validate_labs(c), [])
        n, err = run_checks(c)
        self.assertEqual(err, [])
        self.assertGreater(n, 0)

    def test_every_container_has_a_look(self):
        from model import CONTAINERS
        self.assertEqual(CONTAINERS - {"toggle"}, set(COMP["callouts"]))


class TestParseBlocks(unittest.TestCase):
    def test_ok(self):
        b, err = parse_blocks("前\n::: key 題\n中\n:::\n{{problem:Q-U04-001}}\n^ 灰色")
        self.assertEqual(err, [])
        self.assertEqual([x.kind for x in b], ["line", "container", "problem", "gray"])
        self.assertEqual((b[1].name, b[1].title, b[1].inner[0].text), ("key", "題", "中"))

    def test_errors(self):
        cases = {
            "::: key\n中": "閉じていない",
            "::: toggle a\n::: key\nx\n:::\n:::": "枠の中に枠",
            "::: nope\nx\n:::": "未知の枠",
            "x\n:::": "開始のない",
        }
        for src, word in cases.items():
            _, err = parse_blocks(src, "t")
            self.assertTrue(any(word in e for e in err), (src, err))


class TestValidateCatchesMistakes(unittest.TestCase):
    def errs(self, mutate):
        c = course()
        mutate(c)
        return " / ".join(validate(c) + validate_labs(c))

    def q(self, c, qid):
        return c.units[qid.split("-")[1]]["problems"][qid]

    def test_unknown_reference(self):
        def m(c):
            c.units["U04"]["bodies"]["S1"] += "\n{{unit:U99}} {{term:TERM-xx}} {{lab:LAB-scale@nope}}"
        e = self.errs(m)
        for word in ("U99", "TERM-xx", "nope"):
            self.assertIn(word, e)

    def test_token_in_goal_is_checked(self):
        e = self.errs(lambda c: c.units["U04"].__setitem__("goal", "{{unit:U77}}"))
        self.assertIn("U77", e)

    def test_choice_rules(self):
        def m(c):
            q = self.q(c, "Q-U04-022")
            q["misconceptions"] = {2: "正解に誤解", 1: "x"}
        self.assertIn("正解や範囲外", self.errs(m))
        self.assertIn("全ての誤答", self.errs(lambda c: self.q(c, "Q-U04-022").__setitem__("misconceptions", {1: "x"})))
        self.assertIn("correct", self.errs(lambda c: self.q(c, "Q-U04-022").__setitem__("correct", 9)))

    def test_problem_use_count_and_retired(self):
        def twice(c):
            c.units["U04"]["bodies"]["S1"] += "\n{{problem:Q-U04-003}}"
        self.assertIn("2 回", self.errs(twice))
        self.assertIn("retired", self.errs(lambda c: self.q(c, "Q-U04-003").__setitem__("retired", True)))

    def test_difficulty_order(self):
        self.assertIn("易→難", self.errs(lambda c: self.q(c, "Q-U04-005").__setitem__("difficulty", 1)))

    def test_new_numbers_need_checks(self):
        def m(c):
            q = self.q(c, "Q-U04-011")
            q.pop("checks")
        self.assertIn("checks がない", self.errs(m))

    def test_lab_contract(self):
        def bad_key(c):
            self.q(c, "Q-U04-010")["lab"]["predict"]["key"] = "nope"
        self.assertIn("values にない", self.errs(bad_key))
        self.assertIn("使えない", self.errs(lambda c: self.q(c, "Q-U04-010")["lab"]["set"].__setitem__("zzz", 1)))
        self.assertIn("ラボにない", self.errs(lambda c: self.q(c, "Q-U04-010")["lab"].__setitem__("mode", "nope")))

    def test_lab_predict_needs_expect(self):
        self.assertIn("expect", self.errs(lambda c: self.q(c, "Q-U04-010")["lab"].pop("expect")))

    def test_numbers_ignore_tokens_and_commas(self):
        self.assertEqual(numbers("{{unit:U26}} 8,200円 と 1.5倍"), {"8200", "1.5"})


class TestChecks(unittest.TestCase):
    def test_sandbox(self):
        self.assertTrue(run_check("comb(5,2) == 10"))
        with self.assertRaises(Exception):
            run_check("__import__('os')")


class TestYaml(unittest.TestCase):
    def test_duplicate_key_stops(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            f.write("a: 1\na: 2\n")
        with self.assertRaises(Exception):
            load_yaml(Path(f.name))


class TestRender(unittest.TestCase):
    def setUp(self):
        self.r = NotionRenderer(course(), TARGET)
        self.probs = COURSE.units["U04"]["problems"]

    def test_long_choice_lists_one_per_line(self):
        out = self.r.problem(self.probs["Q-U04-022"], [0])
        self.assertIn("\n② 満足度", out)
        self.assertIn("<b>正解は②</b>", out)
        self.assertIn("- ①：", out)

    def test_lab_check_inside_answer(self):
        out = self.r.problem(self.probs["Q-U04-010"], [0])
        toggle = out[out.index("<toggle>"):]
        self.assertIn(f'<embed source="{self.r.lab_src("LAB-scale@Q-U04-010")}" />', toggle)

    def test_numbering_and_difficulty(self):
        counter = [0]
        self.r.problem(self.probs["Q-U04-003"], counter)
        out = self.r.problem(self.probs["Q-U04-004"], counter)
        self.assertTrue(out.startswith("<b>問2（中）</b>"))

    def test_all_pages_pass_lint(self):
        assets = set(COURSE.figures) | set(variants(COURSE)) | set(COURSE.labs)
        pages = {"guide": self.r.guide_page(), "root": self.r.root_page()}
        pages.update({u: self.r.unit_page(u) for u in COURSE.units})
        for name, md in pages.items():
            self.assertEqual(lint_page(name, md, assets), [], name)


class TestLint(unittest.TestCase):
    def test_catches(self):
        md = "{{unit:U01}}\n**太字**\n| a | b | c | d |\n<toggle>\nx\n@@ASSET:FIG-none@@\n<sup>2</sup>"
        e = " / ".join(lint_page("p", md, set()))
        for word in ("部品", "太字", "4 列", "<toggle>", "FIG-none", "sup"):
            self.assertIn(word, e)

    def test_math_and_code_are_exempt(self):
        md = "$$\n\\frac{a}{b}\n$$\n```txt\n**x** {{y}}\n```"
        self.assertEqual(lint_page("p", md, set()), [])


class TestLabs(unittest.TestCase):
    def test_variants_cover_presets_and_problems(self):
        v = variants(COURSE)
        self.assertIn("LAB-scale", v)
        self.assertIn("LAB-scale@s1-temp", v)
        self.assertIn("LAB-scale@Q-U04-010", v)

    def test_hosted_lab_urls(self):
        from labs import lab_url
        self.assertEqual(lab_url("https://x.github.io/labs/", COURSE, "LAB-scale@s1-temp"),
                         "https://x.github.io/labs/scale/?p=s1-temp")
        target = dict(TARGET, site_base_url="https://x.github.io/labs")
        r = NotionRenderer(course(), target)
        out = r.problem(COURSE.units["U04"]["problems"]["Q-U04-010"], [0])
        self.assertIn('<embed source="https://x.github.io/labs/scale/?p=Q-U04-010" />', out)
        page = r.unit_page("U04")
        self.assertNotIn("@@ASSET", page)   # 公開サイトがあれば、ラボも図もアップロード不要
        self.assertIn('<image source="https://x.github.io/labs/fig/FIG-U04-scale.svg">', page)

    def test_tour_states_and_expect(self):
        import tour
        p = COURSE.labs["LAB-pois"]["presets"]["rel-approx-tour"]
        st = tour.states(p["tour"])
        self.assertEqual(st[1]["start"]["n"], 10)          # 段2の始め＝段1の終わり
        self.assertEqual([f["n"] for f in st[2]["frames"]], [300, 1000])
        self.assertEqual(st[1]["start"], st[0]["end"])    # 段の始め＝前の段の終わり
        ex = tour.expect("LAB-pois", p)
        self.assertTrue(all(abs(x["lambda"] - 3) < 1e-12 for step in ex for x in step))   # 途中も np＝λ
        self.assertGreater(ex[0][0]["maxdiff"], ex[2][-1]["maxdiff"])   # n を大きくすると差が縮む
        self.assertAlmostEqual(ex[0][0]["bvar"], 2.1)                     # 平均は同じ3でも、分散は 2.1 と 3
        self.assertAlmostEqual(ex[2][-1]["bvar"], 2.991)                  # n＝1000 で分散も λ に近づく
        figs = tour.figure_specs(COURSE)
        self.assertEqual(sorted(f for f in figs if "approx-tour" in f), [f"FIG-LAB-pois-rel-approx-tour-{i}" for i in (1, 2, 3)])
        self.assertEqual(figs["FIG-LAB-pois-rel-contrast-tour-2"]["spec"]["lines"], ["分散　二項 1.2　／　ポアソン 3"])   # 対比：上限5回なら分散1.2
        self.assertTrue(figs["FIG-LAB-binom-def-tour-2"]["caption"].startswith("n 回くり返すと"))   # 題を重ねない

    def test_tour_definition_binom(self):
        import tour
        p = COURSE.labs["LAB-binom"]["presets"]["def-tour"]
        ex = tour.expect("LAB-binom", p)
        self.assertEqual([x["ncr"] for x in ex[1]], [1, 2, 3, 4])      # 成功1回の並びは n 通り
        self.assertAlmostEqual(ex[2][0]["pk"], 6 * 0.3 ** 2 * 0.7 ** 2)
        figs = tour.figure_specs(COURSE)
        self.assertEqual(figs["FIG-LAB-binom-def-tour-3"]["spec"], {"type": "paths", "n": 4, "k": 2, "p": 0.3, "decimals": 4})
        from render_notion import NotionRenderer
        page = NotionRenderer(course(), TARGET).unit_page("U14")
        self.assertIn("<b>▶ ラボで解説</b>\n\n<embed source=", page)   # 解説の版には見出しが付く

    def test_play_for_network(self):
        # 対象：ネットワークの画面が JS の部品で描くための play（#188 04b・#192）。
        # 想定する故障：予想の答え（expect・why）や予想の形（predict）が公開の JSON に出る・段の状態が静止図と違う重ね方になる・つまりの段が抜ける。
        # 見つけ方：公開先のある設定で書き出し、全部の play に答えの項目がないこと、解説の段の状態が tour.states の start と frames と同じこと、
        # 関係から開く解説の最後が gist の「つまり」であること。既存の test_tour_gist_step（ラボの版）とは別に、ネットワークへの書き出しを見る。
        import network
        from tour import states
        d = network.export_network(COURSE, {**TARGET, "site_base_url": "https://example.com/labs"})
        refs = [(x["id"], lab) for kind in ("concepts", "relations") for x in d[kind] for lab in x.get("labs", [])]
        self.assertGreater(len(refs), 30)
        for xid, lab in refs:
            play = lab["play"]
            self.assertFalse({"expect", "why", "predict", "unlock"} & set(play), f"{xid} {lab['preset']}")
            pre0 = COURSE.labs[lab["id"]]["presets"][lab["preset"]]
            if pre0.get("predict"):   # 予想させる版は問いの文を出さない（触るは答えをすぐ出す。#188 07d）
                self.assertNotIn("task", play, f"{xid} {lab['preset']}")
            pre = COURSE.labs[lab["id"]]["presets"][lab["preset"]]
            if pre.get("tour"):
                sx = states(pre["tour"])
                self.assertEqual([st["states"] for st in play["steps"][:len(sx)]], [[s0["start"], *s0["frames"]] for s0 in sx])
        rel = next(lab for xid, lab in refs if xid.endswith("REL-binom-hyper-contrast") and lab.get("kind") == "tour")
        self.assertTrue(rel["play"]["steps"][-1].get("gist"))
        self.assertIn("戻さずに取り出すと", rel["play"]["steps"][-1]["text"])

    def test_tour_gist_step(self):
        from labs import variants
        v = variants(COURSE)
        last = v["LAB-pois@rel-contrast-tour"]["tour"]["steps"][-1]
        self.assertEqual(last["title"], "つまり")   # 関係の gist から build が足す（原本の tour には書かない）
        self.assertIn("ばらつきが小さく", last["text"])
        self.assertEqual(len(v["LAB-pois@rel-contrast-tour"]["tour"]["steps"]),
                         len(COURSE.labs["LAB-pois"]["presets"]["rel-contrast-tour"]["tour"]["steps"]) + 1)
        self.assertNotIn("つまり", [s.get("title") for s in v["LAB-binom@def-tour"]["tour"]["steps"]])   # 概念の解説には足さない

    def test_tour_relation_visuals_batch1(self):
        import tour
        figs = tour.figure_specs(COURSE)
        # 二項→正規：n＝100 は平均±4標準偏差の範囲だけ（ラボと同じ決まり）、p＝0.02 は曲線とずれる
        sp2, sp3 = figs["FIG-LAB-binom-rel-norm-tour-2"]["spec"], figs["FIG-LAB-binom-rel-norm-tour-3"]["spec"]
        self.assertEqual((sp2["kmin"], sp2["kmax"]), tour.binom_window(100, 30, (100 * 0.3 * 0.7) ** 0.5))
        self.assertGreater(sp3["maxdiff"], sp2["maxdiff"])
        # 二項↔幾何：段でモードを変える。幾何の段は値を持ち越さない
        st = tour.states(COURSE.labs["LAB-pois"]["presets"]["rel-geom-contrast-tour"]["tour"])
        self.assertEqual(st[1]["start"], {"mode": "geom", "p": 0.3, "r": 1, "k": 3})
        self.assertEqual(figs["FIG-LAB-pois-rel-geom-contrast-tour-2"]["spec"]["family"], "geom")
        # 二項↔超幾何：全部取ると分散0
        ex = tour.expect("LAB-pois", COURSE.labs["LAB-pois"]["presets"]["rel-hyper-contrast-tour"])
        self.assertAlmostEqual(ex[0][0]["mean"], 1.5)
        self.assertAlmostEqual(ex[2][-1]["var"], 0)

    def test_tour_relation_visuals_batch2(self):
        import tour
        from network import relations_without_figures
        # 変換・対比・導出・一般化のうち、完成見本の単元（U13〜U16）の関係には全部図がある（#95）。
        # 骨格（P1）で足した関係の図は、その単元の肉付け（P7 以降）で付ける（build が警告で数える）
        import yaml
        rels = {r["id"]: r for r in yaml.safe_load((Path(__file__).resolve().parent.parent / "content" / "relations.yaml").read_text(encoding="utf-8"))["relations"]}
        done = {"U13", "U14", "U15", "U16"}
        self.assertEqual([i for i in relations_without_figures() if set(rels[i].get("basis", {}).get("units", [])) <= done], [])
        figs = tour.figure_specs(COURSE)
        ex = tour.expect("LAB-expect", COURSE.labs["LAB-expect"]["presets"]["rel-indep-tour"])
        self.assertEqual([round(e[0]["cov"], 9) for e in ex], [0, 0.1, -0.1])   # 独立→正→負（周辺は同じ）
        ex = tour.expect("LAB-expect", COURSE.labs["LAB-expect"]["presets"]["rel-varcov-tour"])
        self.assertAlmostEqual(ex[1][0]["cov"], ex[1][0]["vx"])                 # Cov(X, X)＝V(X)
        ex = tour.expect("LAB-pois", COURSE.labs["LAB-pois"]["presets"]["rel-hyper-tour"])
        self.assertAlmostEqual(ex[1][-1]["fpc"], 195 / 199)                     # 箱を大きくすると補正は1に近い（N＝200 で 0.98）
        self.assertTrue(figs["FIG-LAB-pois-rel-negbinom-tour-2"]["spec"]["label"].startswith("負の二項"))
        self.assertEqual(figs["FIG-LAB-expect-rel-indep-tour-1"]["spec"]["type"], "joint")

    def test_tour_validation(self):
        from labs import _check_spec
        tool = COURSE.labs["LAB-pois"]
        bad = {"mode": "approx", "task": "x", "tour": {"kmax": 10, "steps": [
            {"text": "**閉じない", "set": {"n": 10, "lam": 3, "zz": 1}},
            {"text": "ok", "frames": [{"n": 12.5}], "color": "red"}]}}
        err = _check_spec("T", bad, tool)
        for want in ("predict・steps・task を書かない", "** が閉じていない", "['zz'] はモード approx の set にない",
                     "n は整数で書く", "使えない項目 ['color']"):
            self.assertTrue(any(want in e for e in err), want)
        self.assertTrue(any("2段以上" in e for e in _check_spec("T", {"mode": "approx", "tour": {"steps": [{"text": "a"}]}}, tool)))

    def test_squeeze_keeps_urls_and_code(self):
        src = "  <a href='https://x'>\n  // コメント\n  const a=1; // 行末\n\n"
        self.assertEqual(squeeze(src), "<a href='https://x'>\nconst a=1; // 行末\n")


if __name__ == "__main__":
    unittest.main()


class TestVisuals(unittest.TestCase):
    """例題・問題にはラボか図。教材にチェック欄を残さない。"""

    def test_problem_needs_visual(self):
        from model import _validate_problem
        q = {"stage": "S1", "format": "written", "prompt": "問", "answer": "答"}
        c = course()
        err = _validate_problem(c, "U03", "Q-U03-901", q, 1)
        self.assertTrue(any("ラボか図がない" in e for e in err))
        q["no_visual"] = "理由"
        self.assertFalse(any("ラボか図がない" in e for e in _validate_problem(c, "U03", "Q-U03-901", q, 1)))

    def test_example_needs_visual(self):
        from model import _check_examples
        self.assertTrue(_check_examples("x", "**例題A** 文\n\n説明\n\n### 次"))
        self.assertFalse(_check_examples("x", "**例題A** 文\n\n{{fig:FIG-U03-exA}}\n\n### 次"))

    def test_figure_numbers_must_come_from_problem(self):
        import figures
        c = course()
        q = c.units["U03"]["problems"]["Q-U03-030"]
        q["figure"] = dict(q["figure"], stat=["標本の不良率 1/20＝7.3%"])
        self.assertTrue(any("ない数" in e for e in figures.validate_figures(c)))

    def test_dist_figure(self):
        import figures
        svg = figures.dist({"type": "dist", "family": "poisson", "lam": 2, "kmax": 6, "unit": "件"})
        self.assertIn("期待値 2件", svg)          # 棒を6件で切っても、平均は λ のまま
        svg = figures.dist({"type": "dist", "family": "table", "values": [0, 1, 2], "probs": [0.2, 0.5, 0.3], "band": 1})
        self.assertIn("期待値 1.1", svg)
        self.assertIn("0.4〜1.8", svg)
        self.assertIn("<path", figures.dist({"type": "dist", "family": "normal", "mu": 100, "sigma": 10, "ticks": [70, 130, 10]}))
        c = course()
        f = next(f for f in c.units["U16"]["figures"] if f["id"] == "FIG-U16-concept")
        f["spec"]["mu"] = 105                     # 本文にない数
        self.assertTrue(any("FIG-U16-concept" in e and "ない数" in e for e in figures.validate_figures(c)))

    def test_term_links_to_network(self):
        r = NotionRenderer(course(), TARGET)
        self.assertEqual(r.term_ref("TERM-expect"), f"[期待値 🕸]({TARGET['network_url']}?c=stats2:TERM-expect)")
        stub = next(t for t, v in r.c.terms.items() if not v.get("definition") and t in (TARGET.get("terms") or {}))
        self.assertIn("mention", r.term_ref(stub))       # まだ説明のない用語は旧版の用語ページ
        t2 = dict(TARGET, network_url="")
        self.assertNotIn("🕸", NotionRenderer(course(), t2).term_ref("TERM-expect"))   # 配布先（画面がない）

    def test_no_checkbox_in_pages(self):
        r = NotionRenderer(course(), TARGET)
        md = r.unit_page("U03")
        self.assertNotIn("- [ ]", md)
        self.assertIn("- □ ", md)
        self.assertEqual(lint_page("x", "- [ ] 自分で", set()) != [], True)

    def test_problem_figure_inside_answer(self):
        r = NotionRenderer(course(), TARGET)
        out = r.problem(COURSE.units["U04"]["problems"]["Q-U04-011"], [0])
        self.assertIn("図で確かめる", out[out.index("<toggle>"):])


class TestCheckChanged(unittest.TestCase):
    """変えたファイルから確かめる範囲を選ぶ。範囲が狭すぎる間違いを見逃さない。"""

    def test_classify(self):
        from check_changed import classify
        docs, units, labs, common = classify([
            "CLAUDE.md", "docs/a.md", "content/units/U10/S5.md", "content/problems/U05T.yaml",
            "migration/waivers/U24.yaml", "tools/prob_lab/prob_lab.src.html"])
        self.assertEqual((len(docs), units, labs, common), (2, {"U10", "U05T", "U24"}, {"prob_lab"}, []))

    def test_shared_parts_are_common(self):
        from check_changed import classify
        for f in ["build/model.py", "tests/test_build.py", "tools/labkit/labkit.js", "tools/test_labs.js",
                  "templates/notion/components.yaml", "content/stages.yaml", "content/shared.yaml",
                  "content/units/index.yaml", "publish/notion.yaml", "content/relations.yaml",
                  "docs/knowledge-net/schema/kn-schema-v1.json"]:
            self.assertEqual(classify([f])[3], [f], f)

    def test_unit_assets_exist(self):
        import json
        from check_changed import unit_assets
        man = Path(__file__).resolve().parent.parent / "out" / "site_manifest.json"
        if not man.exists():
            self.skipTest("build の前")
        have = {v["asset"] for v in json.loads(man.read_text(encoding="utf-8"))}
        for u in ["U05", "U10", "U24", "U31"]:
            a = unit_assets(u)
            self.assertTrue(a, u)
            self.assertEqual([x for x in a if x not in have], [], u)


class TestUnitLinks(unittest.TestCase):
    def test_prereq_needs_used_by(self):
        c = course()
        c.units["U01"]["used_by"] = [x for x in c.units["U01"]["used_by"] if x != "U03"]
        self.assertTrue(any("U03: 前提の U01 の used_by に U03 がない" in e for e in validate(c)))


class TestLegacy(unittest.TestCase):
    """旧版の削除の管理表：消し忘れと、削除済みの参照の戻りを見逃さない。"""

    def _run(self, items, pages):
        from legacy import legacy_status
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
            import yaml
            yaml.safe_dump({"items": items}, fh, allow_unicode=True)
        return legacy_status(pages, Path(fh.name))

    def test_deleted_but_still_referenced_stops(self):
        err, _ = self._run([{"id": "LEG-x", "name": "x", "notion": ["aaaa-bbbb"], "deleted": "2026-10-29"}],
                           {"U01": "リンク aaaabbbb"})
        self.assertTrue(err and "LEG-x" in err[0])

    def test_status_lines(self):
        err, lines = self._run([
            {"id": "LEG-a", "name": "まだのもの", "absent": ["REF-PQ-DB"]},
            {"id": "LEG-b", "name": "消せるもの", "absent": ["ZZZ-NOT-USED"]},
        ], {})
        self.assertEqual(err, [])
        self.assertIn("まだ", lines[0])
        self.assertIn("削除してよい", lines[1])

    def test_real_table_is_clean(self):
        from legacy import legacy_status
        err, lines = legacy_status({})
        self.assertEqual(err, [])
        self.assertTrue(lines)


class TestHomeAndLegacyPages(unittest.TestCase):
    def test_home_keeps_children_as_page_blocks(self):
        r = NotionRenderer(course(), TARGET)
        md = r.home_page()
        self.assertIn(f'<page url="https://app.notion.com/p/{TARGET["root_page"]}">', md)
        self.assertNotIn("<mention", md)

    def test_legacy_page_skips_deleted(self):
        r = NotionRenderer(course(), TARGET)
        rep = [{"item": {"id": "LEG-a", "name": "残すもの", "notion": [{"id": "aaaa", "type": "database", "title": "A"}]}, "state": "still", "reasons": ["x"]},
               {"item": {"id": "LEG-b", "name": "消したもの", "deleted": "2026-10-29"}, "state": "deleted", "reasons": []}]
        md = r.legacy_page(rep)
        self.assertIn('<database url="https://app.notion.com/p/aaaa">', md)
        self.assertNotIn("消したもの", md)


class TestNetwork(unittest.TestCase):
    """概念・関係・導出：参照の誤り・種類・成立条件・孤立・型を見逃さない。"""

    def setUp(self):
        import network
        self.n = network
        self.rels, self.ders = network.load_network()

    def _validate(self, c=None, rels=None, ders=None):
        orig = self.n.load_network
        self.n.load_network = lambda: (rels if rels is not None else self.rels, ders if ders is not None else self.ders)
        try:
            return self.n.validate_network(c or course())
        finally:
            self.n.load_network = orig

    def test_clean(self):
        self.assertEqual(self._validate(), [])

    def test_gist_required_for_visual_types(self):
        bad = copy.deepcopy(self.rels)
        r = next(x for x in bad if x["type"] == "対比")
        r.pop("gist")
        p = next(x for x in bad if x["type"] == "前提")
        self.assertNotIn("gist", p)   # 前提には要らない
        err = self._validate(rels=bad)
        self.assertTrue(any(f"{r['id']}: 対比の関係には gist" in e for e in err))
        self.assertEqual(len([e for e in err if "gist" in e]), 1)

    def test_unknown_term_and_type(self):
        bad = copy.deepcopy(self.rels)
        bad[0]["to"] = "TERM-nothing"
        bad[1]["type"] = "似ている"
        err = self._validate(rels=bad)
        self.assertTrue(any("TERM-nothing" in e for e in err))
        self.assertTrue(any("似ている" in e for e in err))

    def test_problem_concepts(self):
        c = course()
        qid = next(iter(c.units["U13"]["problems"]))
        q = c.units["U13"]["problems"][qid]
        q["concepts"] = ["TERM-nothing", "TERM-perm", "REL-rv-expect", "TERM-expect"]
        err = self._validate(c)
        self.assertTrue(any(f"{qid}: concepts の TERM-nothing が用語・関係にない" in e for e in err))
        self.assertTrue(any(f"{qid}: concepts の TERM-perm はまだ説明のない用語" in e for e in err))
        self.assertFalse(any("REL-rv-expect" in e or "TERM-expect" in e for e in err))
        q.pop("concepts")
        c.units["U13"]["concepts_linked"] = True
        self.assertTrue(any(f"{qid}: U13 は concepts_linked" in e for e in self._validate(c)))

    def test_formula_tree(self):
        c = course()
        f = c.terms["TERM-std"]["formulas"][0]
        self.assertEqual(f["tree"]["op"], "eq")
        f["tree"]["args"][1]["args"][1] = {"sym": "s"}                    # symbols にない記号
        f["tree"]["args"][0] = {"op": "fn", "name": "Q", "args": [{"num": 1}]}   # 知らない関数
        f["symbols"][2]["concept"] = "TERM-nothing"
        err = self._validate(c)
        self.assertTrue(any("記号 s が symbols の key にない" in e for e in err))
        self.assertTrue(any("関数 Q が symbols の key にない" in e for e in err))
        self.assertTrue(any("concept TERM-nothing が用語にない" in e for e in err))
        self.assertEqual(self.n.tree_errors({"op": "fn", "name": "exp", "args": [{"num": 1}]}, set()), [])

    def test_symbol_of_and_domain(self):
        # 記号と確率変数の対応（of）・定義域（domain）（#109）
        c = course()
        f = c.terms["TERM-std"]["formulas"][0]
        mu = next(s for s in f["symbols"] if s.get("key") == "mu")
        self.assertEqual(mu.get("of"), "X")
        self.assertFalse(self._validate(c))
        mu["of"] = "Y"                                   # 同じ式に確率変数 Y はない
        sig = next(s for s in f["symbols"] if s.get("key") == "sigma")
        sig["domain"] = {"min": 1, "max": 0}             # min > max
        X = next(s for s in f["symbols"] if s.get("key") == "X")
        X["domain"] = {"min": 0}                         # 確率変数に定義域は書かない
        err = self._validate(c)
        self.assertTrue(any("of Y が、同じ式の確率変数" in e for e in err))
        self.assertTrue(any("domain は min ≦ max" in e for e in err))
        self.assertTrue(any("domain を書けるのは value・param・const・index だけ" in e for e in err))
        sig["domain"] = {"max": "nothing"}               # 記号どうしの範囲は同じ式の記号
        self.assertTrue(any("domain の nothing は、同じ式のほかの値・母数の記号" in e for e in self._validate(c)))
        mu["domain"] = {"lo": 0}
        self.assertTrue(any("domain は min・max・minOpen・maxOpen・integer・nonzero だけ" in e for e in self._validate(c)))

    def test_formula_source_and_contracts(self):
        # 確かめる対象：式の原本の決まり（#118 単位 A：D1・D2・D6、M1 を起きない形に）。
        # 想定する故障：原本に tex が戻り木と食い違う（M1）・式 ID の重複や欠け・ref の元がない・契約のない（未分類の）式・語彙にない性質・
        # 組の条件が式にない記号を使う。見つけ方：原本を読み込んだ形にわざと誤りを入れて prepare の誤りを見る。
        # 既存のテストとの違い：test_formula_tree は木の形だけ、ここは式の ID・写し・TeX の出どころ・契約
        import copy as _copy
        from formulas import prepare
        from model import load_yaml as _ly
        from formulas import CONTRACTS
        c = course()
        self.assertFalse([e for e in c.errors if "式" in e or "契約" in e])
        rv = c.terms["TERM-rv"]["formulas"][1]                       # ref は元の式の写しになる（D2）
        self.assertEqual((rv["id"], rv["defined_in"], rv["tex"]), ("F-dist-sum", "TERM-dist", c.terms["TERM-dist"]["formulas"][0]["tex"]))
        self.assertEqual(c.terms["TERM-std"]["formulas"][0]["tex"], r"Z=\dfrac{X-\mu}{\sigma}")   # TeX は木から作る
        raw = {t["id"]: t for t in _ly(Path(__file__).resolve().parent.parent / "content" / "terms.yaml")}
        k = _ly(CONTRACTS)
        bad = _copy.deepcopy(raw)
        bad["TERM-std"]["formulas"][0]["tex"] = "Z=X"                 # M1：原本に tex を書く
        bad["TERM-binom"]["formulas"][1]["id"] = "F-binom-pmf"        # ID の重複
        bad["TERM-rv"]["formulas"][1] = {"ref": "F-nothing"}          # 元がない
        kk = _copy.deepcopy(k)
        kk["contracts"] = [x for x in kk["contracts"] if x["formula"] != "F-geom-var"]   # 未分類
        next(x for x in kk["contracts"] if x["formula"] == "F-std-def")["properties"].append("美しい")
        next(x for x in kk["contracts"] if x["formula"] == "F-hyper-pmf")["conditions"][0]["tree"]["args"][1] = {"sym": "Q"}
        err = prepare(bad, kk)
        for want in ("式 F-std-def に tex を書かない", "式 ID F-binom-pmf が2か所", "{ref: F-nothing} の元の式がない",
                     "契約がない式（未分類）：F-geom-var", "vocab にない語 美しい", "F-hyper-pmf：組の条件：記号 Q が symbols にない"):
            self.assertTrue(any(want in e for e in err), want)

    def test_formula_marks(self):
        # 確かめる対象：公開の JSON に出す式の印と条件（#118 単位 C・D4）。想定する故障：見本で確かめた式に「未検証」が付く／
        # レビューの記録があるのに「レビュー前」が残る／記号どうしの条件が書き出されない。見つけ方：見本にある式・ない式、記録の有無で marks を見る
        from formulas import CONTRACTS, marks
        from model import load_yaml as _ly
        k = _ly(CONTRACTS)
        m = marks(k, [])
        self.assertNotIn("unverified", m["F-binom-pmf"])                       # 独立な見本で確かめた
        self.assertTrue(m["F-geom-var"].get("unverified"))                       # 見本にない
        self.assertTrue(m["F-binom-pmf"].get("review_pending"))                  # 契約に review があり、記録がない
        self.assertEqual([c["text"][:5] for c in m["F-hyper-pmf"]["conditions"]], ["k ≦ M", "n−(N−"])
        rec = [{"formula": "F-binom-pmf", "points": next(x for x in k["contracts"] if x["formula"] == "F-binom-pmf")["review"], "judgement": "j", "date": "2026-11-01"}]
        self.assertNotIn("review_pending", marks(k, rec)["F-binom-pmf"])

    def test_walk_texts_match_engine(self):
        # 確かめる対象：解き方の公式の文（content/walk-texts.yaml）が engine の表（contracts.json の walk_rows）とちょうど合う（#211）。
        # 想定する故障：engine が行・穴・別の言い方を足したのに文を書き忘れる（画面に文が出ない・{x} のまま出る）・名前の書き違い・
        # 使われない文が残る・記号の意味の書き漏らし。見つけ方：原本は通り、1つずつ崩すとそれぞれの理由で止まる。
        # 既存との違い：walk_errors は課題ごとの walk（文の区切り・段・bind）で、公式の文は見ていなかった
        import copy
        from network import load_walk_texts, walk_texts_errors
        t = load_walk_texts()
        self.assertEqual(walk_texts_errors(t), [])
        for broke, want in [
            (lambda x: x["formulas"]["binom.pmf"]["rows"]["succ"].update(why="{zz}"), "穴 {zz}"),
            (lambda x: x["formulas"]["binom.mode"]["rows"]["floor"].pop("variants"), "別の言い方 tie がない"),
            (lambda x: x["formulas"]["ratio"]["rows"].update(extra={"title": "a", "why": "b"}), "engine が返さない"),
            (lambda x: x["formulas"]["binom.var"]["rows"].pop("q"), "行 q の文がない"),
            (lambda x: x["symbols"].pop("V"), "記号 V の意味がない"),
        ]:
            x = copy.deepcopy(t)
            broke(x)
            self.assertTrue(any(want in e for e in walk_texts_errors(x)), want)

    def test_apply_texts_match_engine(self):
        # 確かめる対象：応用の段の文（content/apply-texts.yaml）が engine の表（contracts.json の apply_steps・apply_words）とちょうど合う（#211）。
        # 想定する故障：engine が段・穴・別の言い方を足したのに文を書き忘れる・名前の書き違い・使われない文が残る・語の言葉の書き漏らし。
        # 見つけ方：原本は通り、1つずつ崩すとそれぞれの理由で止まる。既存との違い：test_walk_texts_match_engine は解き方の公式の文
        import copy
        from network import load_apply_texts, apply_texts_errors
        t = load_apply_texts()
        self.assertEqual(apply_texts_errors(t), [])
        for broke, want in [
            (lambda x: x["steps"]["mode.goal"].update(text="{zz}"), "穴 {zz}"),
            (lambda x: x["steps"]["mode.answer"]["variants"].pop("upper"), "別の言い方 upper がない"),
            (lambda x: x["steps"].update(extra={"title": "a"}), "engine が返さない"),
            (lambda x: x["steps"].pop("boundary.diff"), "段 boundary.diff の文がない"),
            (lambda x: x["words"]["op"].pop("gt"), "語 op の gt の言葉がない"),
        ]:
            x = copy.deepcopy(t)
            broke(x)
            self.assertTrue(any(want in e for e in apply_texts_errors(x)), want)

    def test_solve_value_matches_engine(self):
        # 確かめる対象：network.py の solve_value（情報の of を solve から求める小さな式）が、engine の solveValue と同じ値を出す（#212）。
        # 想定する故障：engine の式の読み方を変えたのに Python の写しを直し忘れる（教材の build は通るのに、画面では情報の値が違う・出ない）。
        # 見つけ方：engine が書き出した見本（contracts.json の solve_value_cases：たどる・足し引き・掛け算・数・空白・数でない値・ない所）と1件ずつ照らす。
        # 既存との違い：walk_errors は課題の文と solve を照らすだけで、engine と同じ読み方かは見ていなかった
        import json
        from network import solve_value, ROOT as NROOT
        c = json.loads((NROOT / "docs" / "math-lab" / "contracts.json").read_text(encoding="utf-8"))["solve_value_cases"]
        self.assertGreater(len(c["cases"]), 10)
        for x in c["cases"]:
            got = solve_value(c["solve"], x["path"])
            if x["value"] is None:
                self.assertIsNone(got, x["path"])
            else:
                self.assertIsNotNone(got, x["path"])
                self.assertAlmostEqual(got, x["value"], places=12, msg=x["path"])

    def test_term_icons_and_pillars(self):
        # 確かめる対象：語の印（build/term_icons.py）が全部の語にあり、動く物・外を指す物がないこと。柱にどの分類もちょうど1回入ること（#220）。
        # 想定する故障：語を足したのに印を描き忘れる（ライブラリに印が出ない）・印に <script>・on…=・href を入れる（教科書や Notion で開くと動く・外を読む）・
        # 分類を足したのに柱に入れ忘れる・2つの柱に入れる（ライブラリで消える・二重に出る）。
        # 見つけ方：原本は通り、印を1つ消す・危ない物を入れる・柱から分類を外す・重ねると止まる。既存との違い：印と柱の確かめはなかった
        import copy
        import term_icons as ti
        from model import load_course
        from network import validate_network
        c = load_course()
        self.assertEqual(ti.icon_errors(list(c.terms)), [])
        saved = dict(ti.I)
        try:
            del ti.I["TERM-binom"]
            self.assertTrue(any("TERM-binom" in e for e in ti.icon_errors(list(c.terms))))
            ti.I.update(saved)
            for bad in ['<script>x</script>', '<path onload="x"/>', '<use href="https://e.example/a.svg#x"/>', '<foreignObject/>']:
                ti.I["TERM-binom"] = {"svg": bad, "form": "形"}
                self.assertTrue(any("使えない物" in e for e in ti.icon_errors(list(c.terms))), bad)
        finally:
            ti.I.clear()
            ti.I.update(saved)
        self.assertFalse([e for e in validate_network(c) if "柱" in e])
        sh = copy.deepcopy(c.shared)
        c.shared["concept_pillars"][0]["categories"].remove("時系列")
        self.assertTrue(any("時系列" in e and "0 回" in e for e in validate_network(c)))
        c.shared["concept_pillars"][0]["categories"].append("確率")
        self.assertTrue(any("確率" in e and "2 回" in e for e in validate_network(c)))
        c.shared.clear()
        c.shared.update(sh)

    def test_screen_revision_gate(self):
        # 確かめる対象：公開の前に、公開中の画面の型の改訂がデータの改訂以上かを確かめる（#207）。
        # 想定する故障：画面の公開が遅れた日に、新しい改訂のデータだけを公開する（新しい項目が画面に出ないまま気づかない）・同じ改訂でも止めて公開できない。
        # 見つけ方：画面がデータより古いと止まる理由を返し、同じか新しければ止めない。既存との違い：公開の前の検査は式のレビューだけだった
        from screen_check import check
        self.assertIsNotNone(check({"schema_revision": 31}, {"schema_revision": 30, "experiment_revision": 1}))
        self.assertIsNone(check({"schema_revision": 30}, {"schema_revision": 30, "experiment_revision": 0}))
        self.assertIsNone(check({"schema_revision": 29}, {"schema_revision": 30}))
        # 型を芯と拡張に分けた（#211）：拡張だけ新しいデータも止める。拡張の型がまだない画面（0）は、拡張を使うデータを読めない
        self.assertIsNotNone(check({"schema_revision": 31, "experiment_revision": 2}, {"schema_revision": 31, "experiment_revision": 1}))
        self.assertIsNotNone(check({"schema_revision": 31, "experiment_revision": 1}, {"schema_revision": 30, "experiment_revision": 0}))
        self.assertIsNone(check({"schema_revision": 31, "experiment_revision": 1}, {"schema_revision": 31, "experiment_revision": 1}))
        # 芯の v2（#264）：v2 のデータの改訂（1から）を、画面の v1 の型の改訂と比べない（v1 の改訂は大きいので、v2 の型のない画面でも通ってしまう）。
        # 検出の確かめ：schemas_for が版を見ずに v1 の型を返すと落ちる
        from screen_check import schemas_for
        self.assertEqual(schemas_for(2)["schema_revision"][1], "schema/kn-schema-v2.json")
        self.assertEqual(schemas_for(1)["schema_revision"][1], "schema/kn-schema-v1.json")

    def test_review_version_and_publish_gate(self):
        # 確かめる対象：レビューを式の版（fingerprint）に結び付け、公開の前に止める（#118 M9）。
        # 想定する故障：レビューのあとに記号の of・domain や概念の条件を変えても、古い記録で「レビュー済み」のまま公開される／
        # 同じ内容の作り直しで要らないやり直しを求める／記録のない代表の式が公開される。
        # 見つけ方：今の版の記録は通り、記号の domain・概念の条件を変えると止まり、同じ原本から作り直した版は同じ値になる。
        # 既存との違い：test_formula_marks は記録の有無だけで、版を見ていなかった
        import copy
        from formulas import CONTRACTS, current_fingerprints, publish_errors
        from model import load_yaml as _ly
        k, c = _ly(CONTRACTS), course()
        prints = current_fingerprints(c.terms, k)
        self.assertEqual(prints, current_fingerprints(course().terms, k))   # 同じ原本からは同じ版
        reps = [x for x in k["contracts"] if x.get("representative") and x.get("review")]
        rec = [{"formula": x["formula"], "points": x["review"], "fingerprint": prints[x["formula"]], "by": "b", "judgement": "j", "date": "d"} for x in reps]
        self.assertEqual(publish_errors(k, rec, prints), [])
        self.assertTrue(publish_errors(k, [], prints))                       # 記録がなければ止まる
        terms = copy.deepcopy(c.terms)
        sym = next(s for s in next(f for f in terms["TERM-std"]["formulas"] if f.get("id") == "F-std-def")["symbols"] if s["key"] == "sigma")
        sym["domain"] = {"min": 0}                                            # σ＝0 を許す（M4 と同じ形の変更）
        terms["TERM-binom"]["conditions"]["math"] = terms["TERM-binom"]["conditions"]["math"][:-1]   # 条件を1つ落とす
        err = publish_errors(k, rec, current_fingerprints(terms, k))
        self.assertTrue(any("F-std-def" in e and "変わった" in e for e in err), err)
        self.assertTrue(any("F-binom-pmf" in e and "変わった" in e for e in err), err)
        # 観点の根拠（契約の review_refs：導出・実験室の反例）を変えても止まる（独立なレビューの指摘 2026-11-01）
        import formulas
        orig = formulas.evidence
        try:
            formulas.evidence = lambda: {**orig(), "DER-var-linear": {**orig()["DER-var-linear"], "steps": ["書き換えた"]}}
            err = publish_errors(k, rec, current_fingerprints(c.terms, k))
        finally:
            formulas.evidence = orig
        self.assertEqual([e.split("：")[0] for e in err], ["代表の式 F-var-linear"], err)   # 根拠を指す式だけがやり直し
        # 「なぜ」の段・部品の意味も版に入る（#204）。想定する故障：why の言い切りを直してもレビューが古くならない（2026-11-04 の独立なレビューで見つかった種類）・
        # 部品も段もない式の版まで変わり、要らないやり直しを求める・契約で外したのに止まる。見つけ方：F-binom-pmf の why の文と部品の意味を変えると止まり、
        # ほかの式は止まらない。契約で why を外すと、why を変えても止まらない
        terms = copy.deepcopy(c.terms)
        f = next(f for f in terms["TERM-binom"]["formulas"] if f.get("id") == "F-binom-pmf")
        f["why"]["steps"][2]["text"] += "（書き換えた）"
        err = publish_errors(k, rec, current_fingerprints(terms, k))
        self.assertEqual([e.split("：")[0] for e in err], ["代表の式 F-binom-pmf"], err)
        terms2 = copy.deepcopy(c.terms)
        next(f for f in terms2["TERM-binom"]["formulas"] if f.get("id") == "F-binom-pmf")["parts"][1]["meaning"] = "書き換えた"
        self.assertEqual([e.split("：")[0] for e in publish_errors(k, rec, current_fingerprints(terms2, k))], ["代表の式 F-binom-pmf"])
        k2 = copy.deepcopy(k)
        next(x for x in k2["contracts"] if x["formula"] == "F-binom-pmf")["review_excludes"] = ["why"]
        prints2 = current_fingerprints(c.terms, k2)
        rec2 = [{**r, "fingerprint": prints2[r["formula"]]} for r in rec]
        self.assertEqual(publish_errors(k2, rec2, current_fingerprints(terms, k2)), [])   # why を外した契約では、why を変えても止まらない
        # 成立条件の区分と基準の定義の式も版に入る（#249）。想定する故障：行の文は同じまま、仮定を要件に変える・保証すること・外れたときを
        # 書き換える・basis_formula を変えても、古いレビューで公開される（2026-11-08 の独立なレビューで見つかった）。区分を持たない概念の式の版まで変わる。
        # 見つけ方：二項分布の仮定の行の kind と outside、basis_formula をそれぞれ変えると F-binom-pmf だけが止まる。
        # 検出の確かめ（2026-11-08）：fingerprint に区分を入れる行を外すと、この3つの assert が落ちることを見た
        for change in ("kind", "outside", "basis"):
            terms3 = copy.deepcopy(c.terms)
            row = next(d for d in terms3["TERM-binom"]["_conditions_detail"] if d.get("text") == "各回が独立")
            if change == "kind":
                row["kind"] = "要件"
            elif change == "outside":
                row["outside"] += "（書き換えた）"
            else:
                terms3["TERM-binom"]["basis_formula"] = "F-binom-mean"
            self.assertEqual([e.split("：")[0] for e in publish_errors(k, rec, current_fingerprints(terms3, k))], ["代表の式 F-binom-pmf"], change)

    def test_lab_random_rule(self):
        # 確かめる対象：ラボの中に乱数を書かない決まり（issue 144 P6）。想定する故障：Math.random（種なし）や自前の rng が新しく入る・
        # 移したラボに自前の rng が戻る。見つけ方：移したラボ（count）の原本に Math.random と function rng を足すと validate_labs が止める
        import tempfile, shutil
        c = course()
        t = c.labs["LAB-count"]
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / t["src"]
            shutil.copy(t["dir"] / t["src"], src)
            src.write_text(src.read_text(encoding="utf-8") + "\n<script>const x=Math.random();let sd=1;const rnd=()=>{sd=(sd*16807)%2147483647;return sd;};</script>", encoding="utf-8")
            t["dir"] = Path(d)
            err = " / ".join(validate_labs(c))
        self.assertIn("LAB-count: Math.random は使わない", err)
        self.assertIn("LAB-count: 自前の乱数（function rng）は使わない", err)

    def test_mu_definition(self):
        # μ＝E(X)：μ を押して期待値の定義で開けるように（#109）
        c = course()
        f = next(f for f in c.terms["TERM-expect"]["formulas"] if f["tree"]["args"][0] == {"sym": "mu"})
        self.assertEqual(f["tree"]["args"][1], {"op": "fn", "name": "E", "args": [{"sym": "X"}]})
        self.assertEqual(next(s for s in f["symbols"] if s["key"] == "mu")["of"], "X")

    def test_table_workspace(self):
        # 対象：作業台の表と実験室のテーマのつながり（#119：同じ表を2か所に書かない）。
        # 故障：作業台と実験室で同じテーマの値・重み・期待値がずれる／ないテーマ・ない式番号・値を直書きした表で公開する。
        # 見つけ方：公開の JSON の表を、実験室のテーマの値・重み（start・compare）と、分数で求めた期待値で照らす。壊した参照で止まる。
        # 既存との違い：前は作業台が表を直書きしていて、実験室のテーマとの一致を確かめていなかった
        from fractions import Fraction as F
        import network
        c = course()
        self.assertFalse(self._validate(c))
        d = network.export_network(c, {"site_base_url": ""})
        tw = next(x for x in d["concepts"] if x["id"] == "stats2:TERM-expect")["table_workspace"]
        exp = next(x for x in network.load_experiments() if x["id"] == "EXP-expect-table")
        themes = {t["id"]: t for t in exp["themes"]}
        mean = lambda vs, ws: sum(F(v) * w for v, w in zip(vs, ws)) / sum(ws)
        for tb in tw["tables"]:
            tid, use = (tb["id"][:-8], "compare") if tb["id"].endswith("-compare") else (tb["id"], "start")
            th = themes[tid]
            self.assertEqual((tb["values"], tb["weights"], tb.get("labels")), (th["values"], th[use], th.get("labels")), tb["id"])
            self.assertEqual(mean(tb["values"], tb["weights"]), mean(th["values"], th[use]))
        self.assertIn("dice-compare", [tb["id"] for tb in tw["tables"]])
        w = c.terms["TERM-expect"]["table_workspace"]
        w["formula"] = -1
        w["linear"] = 999
        w["tables"] = [{"experiment": "EXP-expect-table", "theme": "nothing"}, {"experiment": "EXP-expect-table", "theme": "dice", "use": "later"},
                       {"experiment": "EXP-expect-table", "theme": "dice", "values": [1]}]
        err = "\n".join(self._validate(c))
        for part in ["table_workspace の formula", "table_workspace の linear", "値の表の実験室のテーマにない", "use は start か compare", "experiment・theme・use だけで書く"]:
            self.assertIn(part, err)

    def test_workspace_and_parts(self):
        # 式の作業台と意味のかたまり（#110）
        c = course()
        t = c.terms["TERM-binom"]
        self.assertEqual(t["workspace"]["over"], "k")
        self.assertEqual([p["path"] for p in t["formulas"][0]["parts"]], [[1, 0], [1, 1], [1, 2]])
        self.assertFalse(self._validate(c))
        t["formulas"][0]["parts"][0]["path"] = [1, 9]           # 木にない節
        t["workspace"]["vary"] = ["n", "X"]                      # 定義域のない記号
        t["workspace"]["over"] = "p"                             # 整数でない
        t["workspace"]["mean"] = 9
        t["workspace"]["linear"] = 9                             # 変換の欄の式がない（#156）
        err = self._validate(c)
        self.assertTrue(any("workspace の linear 9" in e for e in err))
        self.assertTrue(any("parts の path [1, 9] が木の中の節を指していない" in e for e in err))
        self.assertTrue(any("vary X は主役の式の、定義域（domain）のある記号" in e for e in err))
        self.assertTrue(any("over p は主役の式の、上限のある整数の記号" in e for e in err))
        self.assertTrue(any("mean 9 が木のある式を指していない" in e for e in err))

    def test_experiments(self):
        # 実験室の定義（#102）：つなぐ概念と線・条件の範囲・反例（崩す条件）・予想の答えを書かない
        import network
        c = course()
        self.assertFalse([e for e in self._validate(c) if "EXP-" in e])
        rel_ids = {r["id"] for r in network.load_network()[0]}
        der_ids = {d["id"] for d in network.load_network()[1]}
        orig = network.load_experiments
        x = dict(orig()[0])
        x.update({"links": {"concepts": ["TERM-binom", "TERM-nothing"], "relations": ["REL-nothing"]}, "compare": {"p": 2},
                  "counterexamples": [{"id": "urn", "name": "箱", "breaks": "空が青い", "mechanism": {"kind": "urn", "total": 5}, "text": "t"}], "answer": "右"})
        try:
            network.load_experiments = lambda: [x]
            err = network.experiment_errors(c, rel_ids, der_ids)
        finally:
            network.load_experiments = orig
        self.assertTrue(any("links.concepts の TERM-nothing" in e for e in err))
        self.assertTrue(any("links.relations の REL-nothing" in e for e in err))
        self.assertTrue(any("compare.p＝2 が vary の範囲にない" in e for e in err))
        self.assertTrue(any("箱（total）は取る数（n の最大）以上" in e for e in err))
        self.assertTrue(any("予想の答え（answer）は書かない" in e for e in err))
        self.assertTrue(any("breaks「空が青い」が、つなぐ概念の成り立つ条件にない" in e for e in err))
        d = network.export_network(c, {"site_base_url": ""})
        e = d["experiments"][0]
        self.assertEqual(e["id"], "stats2:EXP-binom-p")
        self.assertIn("stats2:REL-indep-binom", e["links"]["relations"])
        self.assertEqual(e["reason"]["concept"], "stats2:TERM-binom")
        self.assertFalse(network.schema_errors(d))

    def test_counterexample_effect(self):
        # 確かめる対象：反例の言い分（effect）が、起き方の定義から求めた分布と合うか（#118 層3、M7）。
        # 想定する故障：文と effect の向きの取り違え・端で言い分が外れる起き方（混ざるの切り詰め・戻さずに取るの割合の丸め）・effect の書き忘れ。
        # 見つけ方：本物の定義は通り、向きを逆にした effect・比べる条件をそろえない比較（戻さずに取るを p の二項分布と比べる）・
        # effect のない反例で、それぞれ止まるか。effect は公開の JSON に出ない。
        # 既存との違い：今までは文の言い分を確かめる仕組みがなかった
        import effects
        import network
        x = network.load_experiments()[0]
        self.assertEqual(effects.effect_errors("E", x), [])
        flip = {**x, "counterexamples": [{**b, "effect": {**b["effect"], "spread": "smaller" if b["effect"]["spread"] == "larger" else "larger"}} for b in x["counterexamples"]]}
        err = effects.effect_errors("E", flip)
        self.assertEqual(len(err), len(x["counterexamples"]), err)   # 3つとも止まる
        # 比べる条件をそろえない（戻さずに取るを p の二項分布と比べる）と、丸めた割合で外れる所が見つかる
        orig = effects.base_ratio
        try:
            effects.base_ratio = lambda m, n, p: p
            self.assertTrue(any("反例 urn の effect が計算と合わない" in e for e in effects.effect_errors("E", x)))
        finally:
            effects.base_ratio = orig
        none = {**x, "counterexamples": [{k: v for k, v in b.items() if k != "effect"} for b in x["counterexamples"]]}
        self.assertTrue(any("effect（平均・散らばりの向き）がない" in e for e in effects.effect_errors("E", none)))
        d = network.export_network(course(), {"site_base_url": ""})
        self.assertFalse(any("effect" in b for e in d["experiments"] for b in e.get("counterexamples") or []))

    def test_question_prob_scale(self):
        # 確かめる対象：入口の確率の値の問い（#161）。想定する故障：答えが目盛りの境目のすぐそば（10 回中 9 回以上・p＝0.5 は 1.07%、境目 1%）で、
        # ほぼ当たった予想が「違った」になる（#158 A4 と同じ種類）・k が n の外・目盛りの順が逆。見つけ方：本物の定義は通り、
        # それぞれを崩した定義が止まる。期待値は手で求めた値（10 回中 9 回以上・p＝0.5：(10＋1)÷1024）。既存との違い：問いの答えの位置を確かめるのは初めて
        import effects
        import network
        from fractions import Fraction as F
        x = network.load_experiments()[0]
        self.assertEqual(effects.question_errors("E", x), [])
        self.assertEqual(effects.event_prob(10, F(1, 2), "ge", 9), F(11, 1024))
        pq = next(q for q in x["questions"] if q["form"] == "prob" and not q.get("free"))
        near = {**x, "questions": [{**pq, "set": {"n": 10, "p": 0.5}, "events": [{"op": "ge", "k": 9}]}]}
        self.assertTrue(any("境目 0.01 に近い" in e for e in effects.question_errors("E", near)))
        out = {**x, "questions": [{**pq, "events": [{"op": "ge", "k": 11}]}]}
        # 広がりの問い：変えたあとの n が前より大きくない
        sq = next(q for q in x["questions"] if q["form"] == "spread")
        self.assertTrue(any("to.n" in e for e in effects.question_errors("E", {**x, "questions": [{**sq, "to": {"n": 10}}]})))
        self.assertTrue(any("0〜n＝10 の外" in e for e in effects.question_errors("E", out)))
        self.assertTrue(any("大きい順" in e for e in effects.question_errors("E", {**x, "prob_scale": [0.01, 0.5]})))
        # 並び・ばらつき（#171）：予想の答えが割れる定義。想定する故障：ばらつきの ps が 0.3 と 0.7 だけ（理論の分散が同じで最大が2つ）だと、
        # どちらを選んでも「予想と違った」になりうる。並びの2つの回数が同じ・n の外だと比べられない。見つけ方：崩した定義が止まる
        vq = next(q for q in x["questions"] if q["form"] == "var")
        self.assertTrue(any("1つに決まらない" in e for e in effects.question_errors("E", {**x, "questions": [{**vq, "ps": [0.3, 0.7]}]})))
        pa = next(q for q in x["questions"] if q["form"] == "paths")
        for ks in ([3, 3], [3, 7]):
            self.assertTrue(any("別々の2つ" in e for e in effects.question_errors("E", {**x, "questions": [{**pa, "ks": ks}]})))

    def test_experiment_table(self):
        # 値の表の実験（#119）：値と重み・呼び名の数がそろい、重みが正。前と変えた重みが同じなら問いにならない。書き出しは型（改訂10）に合う
        import network
        c = course()
        rel_ids = {r["id"] for r in network.load_network()[0]}
        der_ids = {d["id"] for d in network.load_network()[1]}
        orig = network.load_experiments
        x = dict(next(e for e in orig() if e.get("model") == "table"))
        x["themes"] = [{"id": "a", "name": "a", "icon": "a", "values": [3, 1], "labels": ["x"], "start": [1, 1], "compare": [1, 1], "change": "c"},
                       {"id": "b", "name": "b", "icon": "b", "values": [1, 2], "start": [0, 0], "compare": [1], "change": "c"}]
        x["counterexamples"] = [{"id": "w", "name": "w", "breaks": "和（連続なら積分）が有限の値になる", "values": [1, 2], "weights": [1, -1], "text": "t"}]
        try:
            network.load_experiments = lambda: [x]
            err = network.experiment_errors(c, rel_ids, der_ids)
        finally:
            network.load_experiments = orig
        for want in ("テーマ a の values は小さい順", "テーマ a の labels は values と同じ数", "テーマ a の start と compare が同じ",
                     "テーマ b の start は0以上で、合計が0より大きい", "テーマ b の compare は values と同じ数", "反例 w の weights は0以上"):
            self.assertTrue(any(want in e for e in err), want)
        d = network.export_network(c, {"site_base_url": ""})
        e = next(e for e in d["experiments"] if e["model"] == "table")
        self.assertEqual(e["id"], "stats2:EXP-expect-table")
        self.assertEqual(e["reason"]["concept"], "stats2:TERM-expect")
        self.assertNotIn("expect", json.dumps(e["themes"]))   # 予想の答えは書かない
        self.assertFalse(network.schema_errors(d))

    def test_catalog(self):
        # 確かめる対象：テーマ体系（#163）。想定する故障：開く問い（open）が問い・反例にない（入口で押すと何も開かない）、
        # 主概念の書き誤り（概念のページ・実験室のタブで問いが出ない）、まだ説明のない概念を主にした問いを開ける、同じ id が2つ、id の形（概念-まとまり-番号）の崩れ、同じ画面を開くだけの2つの問い、予測・操作・理解判定のない開ける問い。
        # 見つけ方：本物の定義は通り、1つずつ崩した定義がそれぞれの理由で止まる。書き出しは id に教材名が付き、型に合う。既存との違い：テーマ体系は初めて
        import network
        c = course()
        rel_ids = {r["id"] for r in network.load_network()[0]}
        der_ids = {d["id"] for d in network.load_network()[1]}
        orig = network.load_experiments
        x = dict(next(e for e in orig() if e.get("catalog")))
        self.assertEqual(sum(len(g["items"]) for g in x["catalog"]), 24)
        def errs(cat):
            try:
                network.load_experiments = lambda: [{**x, "catalog": cat}]
                return network.experiment_errors(c, rel_ids, der_ids)
            finally:
                network.load_experiments = orig
        self.assertFalse([e for e in errs(x["catalog"]) if "テーマ体系" in e or " の open " in e or " の概念 " in e])
        one = lambda **kw: [{"id": "A", "title": "t", "items": [{"id": "binom-A-01", "title": "t", "concept": "TERM-binom", **kw}]}]
        ok = dict(predict="p", operate="o", judge="j")
        self.assertTrue(any("open break:nothing が問い・反例にない" in e for e in errs(one(open="break:nothing", **ok))))
        self.assertTrue(any("open nothing が問い・反例にない" in e for e in errs(one(open="nothing", **ok))))
        self.assertTrue(any("主 TERM-binon が用語にも関係にもない" in e for e in errs(one(concept="TERM-binon"))))
        self.assertFalse(any("binom-A-01" in e for e in errs(one(concept="REL-binom-hyper-contrast"))))   # 関係を主にできる（#169）
        self.assertTrue(any("関連 REL-binom-hyper-contrast が用語にない" in e for e in errs(one(related=["REL-binom-hyper-contrast"]))))
        self.assertTrue(any("retired）なので open を書かない" in e for e in errs(one(retired=True, open="shift", **ok))))
        self.assertTrue(any("主概念 TERM-perm を先に説明のある概念に" in e for e in errs(one(concept="TERM-perm", open="shift", **ok))))
        self.assertFalse(errs(one(concept="TERM-perm")) and any("TERM-perm" in e for e in errs(one(concept="TERM-perm"))))   # 作成中なら骨格の概念でよい
        # id の形：概念-まとまり-番号（企画書の番号 B01 のままや、まとまりの取り違えを止める）
        bad = lambda iid: [{"id": "A", "title": "t", "items": [{"id": iid, "title": "t", "concept": "TERM-binom"}]}]
        for iid in ("B01", "binom-B-01", "binom-A-1"):
            self.assertTrue(any(f"テーマ体系の {iid} は 概念-まとまり-番号" in e for e in errs(bad(iid))), iid)
        self.assertFalse(any("テーマ体系の" in e for e in errs(bad("binom-A-01"))))
        # 同じ画面を開くだけの2つの問い・予測や理解判定のない開ける問い（渡辺さん 2026-11-02）
        two = [{"id": "A", "title": "t", "items": [{"id": f"binom-A-0{i}", "title": "t", "concept": "TERM-binom", "open": "shift", **ok} for i in (1, 2)]}]
        self.assertTrue(any("binom-A-02 の open shift は binom-A-01 と同じ" in e for e in errs(two)))
        self.assertTrue(any("binom-A-01 は開ける問いなので judge" in e for e in errs(one(open="shift", predict="p", operate="o"))))
        dup = [{"id": "A", "title": "t", "items": one()[0]["items"] * 2}]
        self.assertTrue(any("binom-A-01 が重なっている" in e for e in errs(dup)))
        d = network.export_network(c, {"site_base_url": ""})
        e = next(e for e in d["experiments"] if e.get("catalog"))
        it = {i["id"]: i for g in e["catalog"] for i in g["items"]}
        self.assertEqual((it["stats2:binom-D-01"]["concept"], it["stats2:binom-D-01"]["related"]), ("stats2:TERM-binom", ["stats2:TERM-expect"]))
        self.assertEqual(it["stats2:binom-E-01"]["open"], "break:fatigue")
        self.assertEqual(it["stats2:binom-E-03"]["concept"], "stats2:REL-binom-hyper-contrast")   # 関係が主
        self.assertTrue(it["stats2:binom-C-03"]["retired"])
        self.assertEqual((it["stats2:binom-D-03"]["concept"], it["stats2:binom-D-03"]["related"]), ("stats2:TERM-expect", ["stats2:TERM-var", "stats2:TERM-dist", "stats2:TERM-binom"]))   # 主概念は実験室の所属でなく、発見させたい性質で決める
        self.assertNotIn("open", it["stats2:binom-A-04"])   # 作成中の問いは open を出さない
        self.assertFalse(network.schema_errors(d))

    def test_apply(self):
        # 確かめる対象：応用の課題（apply。#171）。想定する故障：engine の知らない method（画面で課題が出ない）、条件の項目の書き漏れ・書き誤り（画面で理由を言って止まる）、
        # 選ぶ形の選び肢の数の違い（答えの番号が選び肢を指さない）、数の答えに幅（tol）がない（照らせない）、開けない問いに課題、公開中の14問のどれかから課題が落ちる。
        # 見つけ方：本物の定義は通り、1つずつ崩した課題がそれぞれの理由で止まる。答えの正しさは math-lab の apply.test.ts（手計算の値）と knowledge-net（公開の JSON の全部を解く）で見る。既存との違い：応用の課題は初めて
        import network
        c = course()
        rel_ids = {r["id"] for r in network.load_network()[0]}
        der_ids = {d["id"] for d in network.load_network()[1]}
        orig = network.load_experiments
        x = dict(next(e for e in orig() if e.get("catalog")))
        opened = [it for g in x["catalog"] for it in g["items"] if it.get("open")]
        self.assertTrue(opened and all(it.get("apply") for it in opened), "公開中の問いのどれかに応用の課題がない")
        def errs(**ap):
            item = {"id": "binom-A-01", "title": "t", "concept": "TERM-binom", "open": "shift", "predict": "p", "operate": "o", "judge": "j",
                    "apply": {"kind": "逆算", "task": "t", "why": "w", "solve": {"method": "mean-to-p", "n": 20, "mean": 6}, "answer": {"type": "number", "tol": {"abs": 1}}, **ap}}
            try:
                network.load_experiments = lambda: [{**x, "catalog": [{"id": "A", "title": "t", "items": [item]}]}]
                return [e for e in network.experiment_errors(c, rel_ids, der_ids) if "apply" in e or "応用" in e]
            finally:
                network.load_experiments = orig
        self.assertFalse(errs())
        self.assertTrue(any("method mean-to-q を engine が知らない" in e for e in errs(solve={"method": "mean-to-q", "n": 20, "mean": 6})))
        self.assertTrue(any("足りない ['mean']" in e for e in errs(solve={"method": "mean-to-p", "n": 20})))
        self.assertTrue(any("余分 ['p']" in e for e in errs(solve={"method": "mean-to-p", "n": 20, "mean": 6, "p": 0.3})))
        self.assertTrue(any("選び肢は 3 つ" in e for e in errs(solve={"method": "compare-eq", "a": {}, "b": {}}, answer={"type": "choice", "options": ["a", "b"]})))
        self.assertTrue(any("幅 tol を書く" in e for e in errs(answer={"type": "number"})))
        network.load_experiments = lambda: [{**x, "catalog": [{"id": "A", "title": "t", "items": [{"id": "binom-A-01", "title": "t", "concept": "TERM-binom", "apply": {"kind": "逆算", "task": "t", "why": "w", "solve": {"method": "mean-to-p", "n": 20, "mean": 6}, "answer": {"type": "number", "tol": {"abs": 1}}}}]}]}]
        try:
            self.assertTrue(any("開ける問い（open のある問い）にだけ" in e for e in network.experiment_errors(c, rel_ids, der_ids)))
        finally:
            network.load_experiments = orig
        d = network.export_network(c, {"site_base_url": ""})
        it = {i["id"]: i for g in next(e for e in d["experiments"] if e.get("catalog"))["catalog"] for i in g["items"]}
        self.assertEqual(it["stats2:binom-E-04"]["apply"]["solve"], {"method": "solve-spread", "n": 10, "p": 0.5, "variance": 3.4})
        self.assertFalse(network.schema_errors(d))

    def test_walk(self):
        # 確かめる対象：解き方を組み立てる（walk。#181・骨格設計）。想定する故障：課題の文の数と solve の値がずれる（式の枠に入る数が答えと合わない）・
        # 文の区切りをつなぐと課題と違う・正解の番号が選び肢の外・段の順の崩れ・公式の記号に当てはめる情報がない。見つけ方：本物の4問は通り、それぞれを崩すと止まる。
        # 既存との違い：apply の検査は solve の項目の有無だけ。公式の値と応用の答えの一致は knowledge-net のテスト（engine で解く）
        import copy
        import network
        x = network.load_experiments()[0]
        aps = {it["id"]: it["apply"] for g in x["catalog"] for it in g["items"] if (it.get("apply") or {}).get("walk")}
        self.assertEqual(sorted(aps), [f"binom-{x}" for x in ("A-01", "A-02", "A-03", "B-01", "B-02", "B-04", "C-01", "C-02", "D-01", "D-02", "E-01", "E-02", "E-03", "E-04")])
        for iid, ap in aps.items():
            self.assertEqual(network.walk_errors(iid, ap), [], iid)
        bad = copy.deepcopy(aps["binom-D-02"]); bad["solve"]["b"]["p"] = 0.4   # 文は 30% のまま
        self.assertTrue(any("情報 bp" in e and "違う" in e for e in network.walk_errors("D", bad)))
        bad = copy.deepcopy(aps["binom-A-01"]); bad["walk"]["segments"][1]["text"] = "の挑戦で、"
        self.assertTrue(any("task と違う" in e for e in network.walk_errors("A", bad)))
        bad = copy.deepcopy(aps["binom-B-02"]); bad["walk"]["steps"][4]["rowQuiz"]["one.comb"]["ok"] = 3
        self.assertTrue(any("正解の番号が選び肢の外" in e for e in network.walk_errors("B", bad)))
        bad = copy.deepcopy(aps["binom-B-04"]); bad["walk"]["steps"][1], bad["walk"]["steps"][2] = bad["walk"]["steps"][2], bad["walk"]["steps"][1]
        self.assertTrue(any("段の順" in e for e in network.walk_errors("B4", bad)))
        bad = copy.deepcopy(aps["binom-B-04"]); bad["walk"]["formulas"][1]["bind"]["p"] = "two"
        self.assertTrue(any("記号 p に当てはめる" in e for e in network.walk_errors("B4", bad)))
        # of を solve の式で書いた情報（E-01 の最初 80%＝p＋drop）。故障：式を読まず、文の数と solve がずれても通る
        bad = copy.deepcopy(aps["binom-E-01"]); bad["solve"]["mechanism"]["drop"] = 0.2   # 文は 80%・20% のまま
        self.assertTrue(any("情報 f" in e for e in network.walk_errors("E1", bad)) and any("情報 l" in e for e in network.walk_errors("E1", bad)))
    def test_skeleton(self):
        # 骨格（#105・P1）：定義1文と分類だけの語は skeleton として書き出し、型に合う。書き方の誤りを止め、skeleton_required で完了の条件も止める
        import network
        c = course()
        c.terms["TERM-perm"]["short"] = "区別できるものを並べる並べ方の数"
        c.terms["TERM-clt"]["short"] = "独立に同じ分布から取った平均は、n が大きいと正規分布に近づく"
        self.assertFalse([e for e in network.skeleton_errors(c)])
        d = network.export_network(c, {"site_base_url": ""})
        e = next(x for x in d["concepts"] if x["id"] == "stats2:TERM-perm")
        self.assertEqual((e["status"], e["category"]), ("skeleton", "数学の道具"))
        self.assertFalse(network.schema_errors(d))
        c.terms["TERM-perm"]["short"] = "並べ方の数。順番を区別する"
        c.terms["TERM-clt"]["category"] = "その他"
        c.terms["TERM-cc"].update({"short": "連続で近似するときに 0.5 ずらす", "category": None})
        err = network.skeleton_errors(c)
        for want in ("TERM-perm: short は1文で書く", "TERM-clt: category「その他」", "TERM-cc: 骨格（short）には category"):
            self.assertTrue(any(want in x for x in err), want)
        c2 = course()
        c2.shared["skeleton_required"] = True
        c2.terms["TERM-perm"].pop("short", None)   # 1語だけ定義1文を外す
        err2 = network.skeleton_errors(c2)
        self.assertTrue(any("定義1文（short）か説明（definition）がない" in x for x in err2))
        g = network.skeleton_gaps(course())
        self.assertEqual(len(g["no_short"]), sum(1 for t in course().terms.values() if not (t.get("definition") or t.get("short"))))

    def test_condition_kinds(self):
        # 確かめる対象：成立条件の区分（#249 ①）と基準にする定義の式（③）の build の止め、公開の JSON への書き出し。
        # 想定する故障：移した分類で区分のない数学の行・関係の行を見逃す（区分の付け忘れが公開に出る）。
        #   仮定に claim、区分に outside、目安に target・出典がなくても通る。出典・用語の id の誤りを見逃す。
        #   移していない分類まで止める。区分が公開の JSON に出ない・用語の id に教材名が付かない・型に合わない。
        #   区分を書いた行が文字の一覧に戻らず、実験室の反例の照合や式のレビューの指紋が形の違いで壊れる。
        # 見つけ方：今の教材の二項分布と REL-binom-normal に、区分の正しい行と誤った行を書いて止めの文を見る。
        #   正しい形に直すと止めが0になり、書き出した概念・関係に conditions_detail が出て型に合い、conditions は文字のまま。
        # 既存との違い：test_relation_map_ready はまとまり・前提・軸・種類の親。ここは成立条件の区分。
        # 検出の確かめ（2026-11-08）：detail_errors の「区分のない数学の行」の止めと、目安の出典の止めを外すと、それぞれ落ちることを見た
        import conditions as cd
        n = self.n
        c = course()
        c.shared["relation_map_ready"] = ["確率分布"]
        binom = c.terms["TERM-binom"]
        binom["conditions"] = {"math": [
            {"text": "n は1以上の整数・0≦p≦1", "kind": "要件", "outside": "この定義の二項分布として扱えない"},
            {"text": "各回が独立", "kind": "仮定", "outside": "保証できない", "terms": ["TERM-indep", "TERM-nowhere"]},   # claim がない・用語の id の誤り
            "各回の成功確率 p が同じ",                                                                                 # 区分がない
        ], "data": ["客ごとに確かめる"]}
        binom["basis_formula"] = "F-nowhere"
        cd.normalize_term(binom)
        self.assertEqual(binom["conditions"]["math"][1], "各回が独立")   # 区分を書いた行も文字に戻る
        rels = copy.deepcopy(self.rels)
        bn = next(r for r in rels if r["id"] == "REL-binom-normal")
        bn["conditions"] = [{"text": "np≧5 かつ n(1−p)≧5", "kind": "目安", "outside": "精度を別に確かめる",
                             "target": "二項分布の正規近似", "source": {"source": "どこかの本"}}]
        cd.normalize_relation(bn)
        err = n.condition_errors(c, rels)
        for w in ["TERM-binom: 成立条件の式の3行目「各回の成功確率 p が同じ」：関係図に移した分類なので",
                  "TERM-binom: 成立条件の式の2行目「各回が独立」：仮定には、何を保証する仮定か（claim）",
                  "terms の TERM-nowhere が用語にない",
                  "TERM-binom: basis_formula の F-nowhere",
                  "REL-binom-normal: 成立条件の1行目「np≧5 かつ n(1−p)≧5」：出典 どこかの本 が shared.yaml の sources にない"]:
            self.assertTrue(any(w in e for e in err), w)
        self.assertFalse(any("データの1行目" in e for e in err))   # データで確かめる手掛かりは区分なしでよい
        self.assertFalse(any(e.startswith("TERM-mean") for e in err))   # 移していない分類は止めない
        # 直すと、二項分布と REL-binom-normal の止めが消え、書き出しに区分が出て型に合う
        binom["conditions"] = {"math": [
            {"text": "n は1以上の整数・0≦p≦1", "kind": "要件", "outside": "この定義の二項分布として扱えない"},
            {"text": "各回が独立", "kind": "仮定", "claim": "成功回数が B(n, p) に従う", "outside": "保証できない", "terms": ["TERM-indep"]},
        ], "data": ["客ごとに確かめる"]}
        binom["basis_formula"] = "F-binom-pmf"
        binom.pop(cd.DETAIL, None)
        cd.normalize_term(binom)
        bn["conditions"] = [{"text": "np≧5 かつ n(1−p)≧5", "kind": "目安", "outside": "精度を別に確かめる",
                             "target": "二項分布の正規近似", "source": {"source": "NIST統計ハンドブック", "locator": "7.2.4"}}]
        bn.pop(cd.DETAIL, None)
        cd.normalize_relation(bn)
        err = n.condition_errors(c, rels)
        self.assertFalse([e for e in err if e.startswith(("TERM-binom", "REL-binom-normal"))])
        orig = n.load_network
        n.load_network = lambda: (rels, self.ders)
        try:
            d = n.export_network(c, {"site_base_url": ""})
        finally:
            n.load_network = orig
        b = next(x for x in d["concepts"] if x["id"] == "stats2:TERM-binom")
        self.assertEqual(b["conditions"]["math"], ["n は1以上の整数・0≦p≦1", "各回が独立"])
        self.assertEqual([x.get("kind") for x in b["conditions_detail"]], ["要件", "仮定", None])
        self.assertEqual(b["conditions_detail"][1]["terms"], ["stats2:TERM-indep"])
        self.assertEqual(b["basis_formula"], "F-binom-pmf")
        r = next(x for x in d["relations"] if x["id"] == "stats2:REL-binom-normal")
        self.assertEqual(r["conditions_detail"][0]["source"]["title"], "NIST統計ハンドブック")
        self.assertFalse(n.schema_errors(d))

    def test_dependency_one_step(self):
        # 確かめる対象：定義の依存と前提知識は直接の1段だけ（#249 ③）の build の止め。
        # 想定する故障：定義の依存の輪（A の定義に B、B の定義に A）を見逃す。前提知識を重ねて書いても通る
        #   （A → B → C と A → C の両方。画面の「前提をさかのぼる」で A が2回出て、学ぶ順が崩れる）。直接の1段だけの今の教材まで止める。
        # 見つけ方：今の教材では0。材料を1本逆向きに足して輪を、たどれる所に前提知識を1本足して重ねを起こし、止めの文を見る。
        # 既存との違い：材料の輪は今まで警告だけで、テストがなかった。前提知識の重ねは今回の止め。
        # 検出の確かめ（2026-11-08）：dependency_errors の重ねの判定で「a in seen」を外すと落ち、輪の止めを外すと落ちることを見た
        n = self.n
        self.assertEqual(n.dependency_errors(self.rels), [])
        rels = copy.deepcopy(self.rels)
        rels.append({"id": "REL-x-loop", "from": "TERM-dist", "to": "TERM-rv", "type": "材料", "description": "x", "version": 1})   # 確率変数 → 確率分布 の逆
        # 共分散 ← 確率変数 ← 確率（どちらも材料）とたどれるのに、確率 → 共分散 を前提知識でも書く（直接の関係はなく、2段の重ね）
        rels.append({"id": "REL-x-twice", "from": "TERM-prob", "to": "TERM-cov", "type": "前提", "premise": "learning", "description": "x", "version": 1})
        err = n.dependency_errors(rels)
        self.assertTrue(any(e.startswith("定義の依存の輪") and "TERM-rv" in e and "TERM-dist" in e for e in err), err)
        self.assertTrue(any(e.startswith("REL-x-twice:") for e in err), err)

    def test_relation_map_ready(self):
        # 確かめる対象：関係図の決まり（docs/relation-map.md・#233）の build の止め。
        # 想定する故障：移した分類（relation_map_ready）で、まとまりのない語・分け終えていない前提（mathematical）・
        #   軸のない対比・親が2つの種類を見逃す。移していない分類まで止めて、今の教材の build を落とす。
        #   まとまりと分類の食い違い・宣言にないまとまりを見逃す。書き出しにまとまり・軸・移した分類が出ない。
        # 見つけ方：確率分布を移した印にして、4つの止めをそれぞれ1つずつ起こし、どれも出ることを見る。
        #   印のない教材（今のまま）では関係図の誤りが0。直した教材を書き出して型に合うことを見る。
        # 既存との違い：test_clean は印のない教材だけ。ここは印を付けたときの止めと書き出し。
        # 検出の確かめ（2026-11-06）：4つの止めのそれぞれを関数から外すと、このテストが落ちることを見た
        n = self.n
        c = course()
        self.assertEqual(n.relation_map_errors(c, self.rels), [])   # 今の教材（印があれば、書き終えた形）は止めない
        for t in c.terms.values():   # 今の教材のまとまりを外して、テストの中で書く
            t.pop("group", None)
        c.shared["relation_map_ready"] = []
        c.shared["concept_groups"] = []
        c.shared["group_relations"] = []   # まとまりの間の関係は test_group_relations で確かめる
        self.assertEqual(n.relation_map_errors(c, self.rels), [])   # 印のない教材は止めない
        c.shared["concept_groups"] = [{"id": "GRP-dist-base", "category": "確率分布", "name": "分布のしくみ"},
                                      {"id": "GRP-dist-count", "category": "確率分布", "name": "くり返して数える"}]
        c.shared["relation_map_ready"] = ["確率分布"]
        c.terms["TERM-rv"]["group"] = "GRP-dist-base"
        c.terms["TERM-binom"]["group"] = "GRP-dist-count"
        c.terms["TERM-comb"]["group"] = "GRP-dist-count"   # 分類が違う（数学の道具）
        rels = copy.deepcopy(self.rels)
        rv = next(r for r in rels if r["id"] == "REL-rv-dist")
        rv.update({"type": "前提", "premise": "mathematical"})   # 分け終えていない前提
        next(r for r in rels if r["id"] == "REL-binom-geom-contrast").pop("axis", None)   # 軸のない対比
        rels.append({"id": "REL-x1", "from": "TERM-binom", "to": "TERM-dist", "type": "種類", "description": "x", "version": 1})
        rels.append({"id": "REL-x2", "from": "TERM-binom", "to": "TERM-rv", "type": "種類", "description": "x", "version": 1})
        err = n.relation_map_errors(c, rels)
        want = ["TERM-dist: 分類「確率分布」は関係図に移したので、group",          # まとまりのない語
                "REL-rv-dist: 分類「確率分布」は関係図に移したので、前提（mathematical）",   # 分け終えていない前提
                "REL-binom-geom-contrast: 関係図に移した分類の対比には axis",             # 軸のない対比
                "TERM-binom: 種類の親が 2 つある",                                       # 親が2つ
                "TERM-comb: group GRP-dist-count の分類（確率分布）"]                    # まとまりと分類の食い違い
        for w in want:
            self.assertTrue(any(w in e for e in err), w)
        self.assertFalse(any("TERM-mean" in e for e in err))   # 移していない分類の語は止めない
        # 直すと止めが消え、書き出しにまとまり・軸・移した分類が出て、型に合う
        for tid, t in c.terms.items():
            if t.get("category") == "確率分布":
                t["group"] = "GRP-dist-base"
        c.terms["TERM-binom"]["group"] = "GRP-dist-count"
        c.terms["TERM-comb"].pop("group")
        rels = [r for r in copy.deepcopy(self.rels)]
        next(r for r in rels if r["id"] == "REL-rv-dist").update({"type": "前提", "premise": "mathematical"})
        for r in rels:
            if r["type"] == "前提" and r.get("premise") == "mathematical" and c.terms.get(r["to"], {}).get("category") == "確率分布":
                r["type"] = "材料"; r.pop("premise")
            if r["type"] == "対比" and "確率分布" in (c.terms.get(r["from"], {}).get("category"), c.terms.get(r["to"], {}).get("category")):
                r["axis"] = "比べる軸"
        self.assertEqual(n.relation_map_errors(c, rels), [])
        orig = n.load_network
        n.load_network = lambda: (rels, self.ders)
        try:
            d = n.export_network(c, {"site_base_url": ""})
        finally:
            n.load_network = orig
        self.assertEqual(d["course"]["relation_map_ready"], ["確率分布"])
        self.assertEqual([x["id"] for x in d["course"]["groups"]], ["stats2:GRP-dist-base", "stats2:GRP-dist-count"])
        self.assertEqual(next(x for x in d["concepts"] if x["id"] == "stats2:TERM-binom")["group"], "stats2:GRP-dist-count")
        self.assertTrue(any(x.get("axis") for x in d["relations"]))
        self.assertFalse(n.schema_errors(d))

    def test_group_relations(self):
        # 確かめる対象：まとまりの間の関係（group_relations。関係図の全体の見え方の矢印。#240）の止めと書き出し。
        # 想定する故障：矢印が指す関係の両端が from・to のまとまりにない（向きが逆・別のまとまり）のに通す。教材にない関係・まとまりを
        #   指しても通す。同じ組に矢印が2本ある。言葉がない。書き出しに出ない・型に合わない。
        # 見つけ方：今の教材（確率分布の3本）は止めが0で、書き出しが型に合う。そこから1つずつ壊し、それぞれの止めが出ることを見る。
        # 既存との違い：test_relation_map_ready は概念と関係の段。ここはまとまりの間の段
        # 検出の確かめ（2026-11-07）：両端の確かめ（まとまりにあるか）を関数から外すと、このテストが落ちることを見た
        n = self.n
        c = course()
        self.assertEqual(n.relation_map_errors(c, self.rels), [])
        d = n.export_network(c, {"site_base_url": ""})
        self.assertEqual([(x["from"], x["to"]) for x in d["course"]["group_relations"]][0], ("stats2:GRP-dist-count", "stats2:GRP-dist-cont"))
        self.assertEqual(d["course"]["group_relations"][1]["relations"], ["stats2:REL-binom-poisson"])
        self.assertFalse(n.schema_errors(d))
        cases = [
            (lambda gr: gr[0].update(relations=["REL-binom-poisson"]), "REL-binom-poisson の両端"),     # 別のまとまりへの関係
            (lambda gr: gr[2].update({"from": "GRP-dist-cont", "to": "GRP-dist-wait"}), "REL-poisson-expo の両端"),   # 向きが逆
            (lambda gr: gr[0].update(relations=["REL-nothing"]), "REL-nothing が relations.yaml にない"),
            (lambda gr: gr[0].update({"to": "GRP-nothing"}), "concept_groups のまとまりにする"),
            (lambda gr: gr.append(dict(gr[0])), "同じ組の矢印が2本"),
            (lambda gr: gr[0].update(label=""), "label（矢印の言葉）がない"),
        ]
        for broke, want in cases:
            c2 = course()
            c2.shared = copy.deepcopy(c2.shared)
            broke(c2.shared["group_relations"])
            err = n.relation_map_errors(c2, self.rels)
            self.assertTrue(any(want in e for e in err), (want, err))

    def test_material_cycles(self):
        # 確かめる対象：材料の輪の警告。想定する故障：輪を見逃す・輪でない枝分かれを輪と数える。
        # 見つけ方：A→B→C→A の輪と、輪でない合流（D→B）を入れ、輪が1つだけ出ることを見る
        n = self.n
        rels = [{"id": f"REL-m{i}", "from": a, "to": b, "type": "材料"} for i, (a, b) in
                enumerate([("TERM-a", "TERM-b"), ("TERM-b", "TERM-c"), ("TERM-c", "TERM-a"), ("TERM-d", "TERM-b")])]
        orig = n.load_network
        n.load_network = lambda: (rels, [])
        try:
            cyc = n.material_cycles()
        finally:
            n.load_network = orig
        self.assertEqual(len(cyc), 1)
        self.assertEqual(set(cyc[0]), {"TERM-a", "TERM-b", "TERM-c"})

    def test_lab_refs(self):
        c = course()
        c.terms["TERM-expect"]["labs"] = [{"id": "LAB-nothing"}, {"id": "LAB-expect", "preset": "s9-none"},
                                         {"id": "LAB-expect", "url": "https://x"}]
        err = self._validate(c)
        self.assertTrue(any("TERM-expect: labs の LAB-nothing がない" in e for e in err))
        self.assertTrue(any("場面の版 s9-none がない" in e for e in err))
        self.assertTrue(any("URL は build が作る" in e for e in err))

    def test_figure_refs(self):
        c = course()
        c.terms["TERM-expect"]["figures"] = ["FIG-nothing", {"id": "FIG-U13-concept"}]
        err = self._validate(c)
        self.assertTrue(any("TERM-expect: figures の FIG-nothing がない" in e for e in err))
        self.assertTrue(any("図の id だけ" in e for e in err))

    def test_figure_refs_export(self):
        from network import export_network
        c = course()
        d = export_network(c, {"site_base_url": "https://example.com/labs"})
        binom = next(x for x in d["concepts"] if x["id"] == "stats2:TERM-binom")
        self.assertEqual(binom["figures"][0]["url"], "https://example.com/labs/fig/FIG-U14-concept.svg")
        self.assertIn("B(4, 0.25)", binom["figures"][0]["caption"])
        rel = next(x for x in d["relations"] if x["id"] == "stats2:REL-binom-poisson")
        self.assertEqual([lab["kind"] for lab in rel["labs"]], ["tour", "check"])   # ラボで解説／ラボで確かめる
        d = export_network(course(), {"site_base_url": ""})   # 公開先のない配布先では出さない
        self.assertFalse(any(x.get("figures") for x in d["concepts"]))

    def test_transform_needs_conditions(self):
        bad = copy.deepcopy(self.rels)
        r = next(x for x in bad if x["type"] == "変換")
        r.pop("conditions")
        r.pop("mode")
        err = self._validate(rels=bad)
        self.assertTrue(any("conditions を必ず書く" in e for e in err))
        self.assertTrue(any("mode を必ず書く" in e for e in err))

    def test_premise_kind_and_mode_place(self):
        bad = copy.deepcopy(self.rels)
        p = next(x for x in bad if x["type"] == "前提")
        p.pop("premise")
        q = next(x for x in bad if x["type"] == "対比")
        q["mode"] = "exact"
        err = self._validate(rels=bad)
        self.assertTrue(any("premise を必ず書く" in e for e in err))
        self.assertTrue(any("mode は変換だけ" in e for e in err))

    def test_generalization_one_direction(self):
        rels = copy.deepcopy(self.rels) + [
            {"id": "REL-x1", "from": "TERM-binom", "to": "TERM-normal", "type": "一般化", "description": "x", "basis": {"units": ["U14"]}},
            {"id": "REL-x2", "from": "TERM-normal", "to": "TERM-binom", "type": "特殊化", "description": "x", "basis": {"units": ["U14"]}}]
        self.assertTrue(any("両方向" in e for e in self._validate(rels=rels)))

    def test_conditions_split_and_sources(self):
        c = course()
        c.terms["TERM-binom"]["conditions"] = ["回数が決まっている"]
        c.terms["TERM-std"]["sources"] = [{"source": "どこにもない本"}]
        err = self._validate(c=c)
        self.assertTrue(any("TERM-binom: conditions は math" in e for e in err))
        self.assertTrue(any("TERM-std: 出典" in e for e in err))

    def test_other_course_allowed_own_prefix_not(self):
        rels = copy.deepcopy(self.rels)
        rels[0]["from"] = "math:CON-ratio"
        rels[1]["from"] = "stats2:TERM-expect"
        err = self._validate(rels=rels)
        self.assertFalse(any("math:CON-ratio" in e for e in err))
        self.assertTrue(any("教材名を付けずに" in e for e in err))

    def test_isolated_concept_and_missing_fields(self):
        c = course()
        c.terms["TERM-zz-test"] = {"id": "TERM-zz-test", "name": "試し", "en": "test", "definition": "どの関係にもつながっていない語"}
        err = self._validate(c=c)
        self.assertTrue(any("TERM-zz-test: 説明のある概念なのに" in e for e in err))
        self.assertTrue(any("TERM-zz-test: 概念の説明に" in e for e in err))

    def test_numbers_need_checks(self):
        c = course()
        c.terms["TERM-binom"].pop("checks")
        self.assertTrue(any("TERM-binom: 説明に数がある" in e for e in self._validate(c=c)))

    def test_export_matches_schema_and_is_namespaced(self):
        data = self.n.export_network(course(), TARGET)
        self.assertEqual(self.n.schema_errors(data), [])
        self.assertTrue(all(x["id"].startswith("stats2:") for x in data["concepts"]))
        bad = copy.deepcopy(data)
        bad["relations"][0]["type"] = "似ている"
        bad["relations"].append({**data["relations"][0], "id": "stats2:REL-y", "type": "変換"})   # mode がない
        bad["concepts"][0].pop("definition", None)
        bad["concepts"][0]["status"] = "filled"
        self.assertGreaterEqual(len(self.n.schema_errors(bad)), 3)

    def test_v2_export_is_same_as_v1(self):
        # 確かめる対象：build が型 v2 で書き出し、移していない分類の結果が今（v1）と同じであること（M4 の完了の条件。設計書 docs/schema-v2-design.md 8。#264）。
        # 想定する故障：v2 に写すときに関係の種類を落とす・v1 の種類の名前を v2 の type に入れる（画面が v2 の種類と取り違える）・項目を足し引きする。
        # 見つけ方：教材の原本から v1 で組み立てたものを v2 に写し、v2 の厳しい型に合うこと、type が残らないこと、
        #   legacy_type を type に戻すと v1 で組み立てたものとちょうど同じになること。
        # 既存との違い：test_export_matches_schema_and_is_namespaced は v1 の形と v1 の型だけを見る。
        # 検出の確かめ：to_v2 で type を legacy_type に替えないと、v2 の型（知らない種類）で落ちる。to_v2 で関係の項目を1つ落とすと、同じかの比べで落ちる
        import json as _json
        v1 = self.n.export_network(course(), TARGET)
        v2 = self.n.to_v2(v1, course().shared.get("v2_ready"))
        self.assertEqual(v2["version"], 2)
        self.assertEqual(self.n.schema_errors(v2), [])
        self.assertFalse(any("type" in r for r in v2["relations"]))
        rev = _json.loads(self.n.SCHEMA.read_text(encoding="utf-8"))["x-revision"]
        self.assertEqual(self.n.from_v2(v2, rev), v1)
        # 移した分類の書き出しは M5 で作る。それまで v2_ready に分類を書いたら止める（v1 の種類のまま「移した」と見せない）
        with self.assertRaises(ValueError):
            self.n.to_v2(v1, ["確率分布"])

    def test_basis_candidates_and_excludes(self):
        # 確かめる対象：基準の定義の式に出る記号の概念（定めるの候補。#86）を、材料・種類の親・basis_excludes で扱ったかの数え方と、basis_excludes の書き方の止め。
        # 想定する故障：記号の表にあるだけで木に出ない記号まで候補にする・種類の親や除外を候補に残す（警告が消えない）・
        #   ⑤ の一覧にない理由や、候補でない概念・材料と重なる概念の除外を通す（判断がどこにあるか分からなくなる）。
        # 見つけ方：教材の原本の写しで、二項分布の候補（組合せ・確率分布）を見て、除外・種類で候補が消え、書き方の誤り4通りがそれぞれ止まる。
        # 既存との違い：test_v2_checks は書き出した v2 で、移した分類の止めを見る。ここは原本の書き方と、全部の分類の警告の数え方。
        # 検出の確かめ：除外を候補から引く所を外すと「除外で消える」が、種類の親を外す所を外すと「種類で消える」が落ちる
        c = course()
        rels = self.n.load_network()[0]
        self.assertEqual(self.n.basis_candidates(c.terms["TERM-binom"], "TERM-binom"), {"TERM-comb", "TERM-dist"})
        gaps = lambda cc, rr=rels: {a for a, b in self.n.basis_gaps(cc, rr) if b == "TERM-binom"}  # noqa: E731
        self.assertEqual(gaps(c), {"TERM-dist"})   # 組合せは材料で扱っている
        c.terms["TERM-binom"]["basis_excludes"] = [{"concept": "TERM-dist", "kind": "使われる場", "text": "確率関数の値の割り当て方は使われる場"}]
        self.assertEqual(gaps(c), set())
        self.assertEqual(self.n.basis_exclude_errors(c, rels), [])
        c2 = course()
        self.assertEqual(gaps(c2, rels + [{"id": "REL-x", "type": "種類", "from": "TERM-binom", "to": "TERM-dist"}]), set())
        bad = [
            ({"concept": "TERM-dist", "kind": "一種の親", "text": "x"}, "kind は ⑤"),
            ({"concept": "TERM-dist", "kind": "使われる場"}, "理由の1文"),
            ({"concept": "TERM-normal", "kind": "使われる場", "text": "x"}, "木に出る記号の概念でない"),
            ({"concept": "TERM-comb", "kind": "使われる場", "text": "x"}, "材料と basis_excludes の両方"),
        ]
        for row, msg in bad:
            with self.subTest(msg):
                cc = course()
                cc.terms["TERM-binom"]["basis_excludes"] = [row]
                self.assertTrue(any(msg in e for e in self.n.basis_exclude_errors(cc, rels)), msg)

    def test_v2_carries_basis_excludes(self):
        # 確かめる対象：原本の basis_excludes を、v2 の書き出しの概念の basis.excludes（型 v2 の改訂2）に置き、v1 に戻すと今と同じ。
        # 想定する故障：除外を書き出さない（公開データで判断が追えない）・v1 の書き出しに混ぜて v1 の型を崩す。
        # 見つけ方：二項分布に除外を書いた原本で、v2 の型に合い、二項分布の basis に formula と excludes があり、v1 に戻すと v1 の書き出しと同じ。
        # 既存との違い：test_v2_export_is_same_as_v1 は除外のない今の原本だけを見る。
        # 検出の確かめ：to_v2 で excludes を置かないと basis の比べで落ちる
        import json as _json
        c = course()
        c.terms["TERM-binom"]["basis_excludes"] = [{"concept": "TERM-dist", "kind": "使われる場", "text": "確率関数の値の割り当て方は使われる場"}]
        v1 = self.n.export_network(c, TARGET)
        self.assertEqual(self.n.schema_errors(v1), [])
        v2 = self.n.to_v2(v1, None, self.n.v2_excludes(c))
        self.assertEqual(self.n.schema_errors(v2), [])
        b = next(x for x in v2["concepts"] if x["id"] == "stats2:TERM-binom")["basis"]
        self.assertEqual(b["formula"], c.terms["TERM-binom"]["basis_formula"])
        self.assertEqual(b["excludes"][0]["concept"], "stats2:TERM-dist")
        rev = _json.loads(self.n.SCHEMA.read_text(encoding="utf-8"))["x-revision"]
        self.assertEqual(self.n.from_v2(v2, rev), v1)

    def test_migration_counts(self):
        # 確かめる対象：製本への移行の残り（progress.py の行。#264）の数え方。
        # 想定する故障：前提を mathematical と learning に分けずに数える（行き先が M5 と M6 で違う）・名前だけ写せる行を移した（v2）と数える・どれかの行を落とす。
        # 見つけ方：教材の原本の関係で、名前だけ写せる＋未移行が全部の行数と同じ、v2 は 0、前提は区分ごとに分かれ、合計が前提の行数と同じ。
        # 既存との違い：進み具合の行は今まで単元と概念だけを数えていた。
        # 検出の確かめ：前提の区分の分け方を外す（区分なしにまとめる）と、区分ごとの行が見つからず落ちる
        rels = self.n.load_network()[0]
        m = self.n.migration_counts(rels)
        self.assertEqual(m["v2"], 0)
        self.assertEqual(sum(m["named"].values()) + sum(m["left"].values()), len(rels))
        premise = sum(1 for r in rels if r["type"] == "前提")
        self.assertEqual(m["left"].get("前提（mathematical）", 0) + m["left"].get("前提（learning）", 0), premise)
        self.assertNotIn("前提", m["named"])

    def test_concept_checks_pass(self):
        from model import run_check
        for tid, e in self.n.network_checks(course()):
            self.assertTrue(run_check(e), f"{tid}: {e}")


class TestProgress(unittest.TestCase):
    def test_counts_from_source(self):
        from progress import notion_page, unit_row
        c = course()
        r = unit_row(c, "U14", TARGET)
        terms = c.units["U14"]["terms"]   # 原本の用語のうち、説明のある語の数と合う（#105 でベルヌーイ分布を足したので全部ではない）
        self.assertEqual(list(r["concepts"][:2]), [sum(1 for t in terms if c.terms[t].get("definition")), len(terms)])
        c.terms["TERM-binom"].pop("definition")
        self.assertLess(unit_row(c, "U14", TARGET)["concepts"][0], r["concepts"][1])
        md = notion_page(course(), TARGET)
        self.assertNotIn("| ", md)   # スマホ前提：表を使わない
        self.assertIn("U32：", md)


class TestVersions(unittest.TestCase):
    def test_version_required(self):
        import network
        c = course()
        c.terms["TERM-binom"].pop("version")
        self.assertTrue(any("TERM-binom: 説明のある概念には version" in e for e in network.validate_network(c)))
