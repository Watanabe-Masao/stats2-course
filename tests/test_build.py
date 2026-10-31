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

    def test_tour_gist_step(self):
        from labs import variants
        v = variants(COURSE)
        last = v["LAB-pois@rel-contrast-tour"]["tour"]["steps"][-1]
        self.assertEqual(last["title"], "つまり")   # 関係の gist から build が足す（原本の tour には書かない）
        self.assertIn("散らばりが小さい", last["text"])
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

    def test_mu_definition(self):
        # μ＝E(X)：μ を押して期待値の定義で開けるように（#109）
        c = course()
        f = next(f for f in c.terms["TERM-expect"]["formulas"] if f["tree"]["args"][0] == {"sym": "mu"})
        self.assertEqual(f["tree"]["args"][1], {"op": "fn", "name": "E", "args": [{"sym": "X"}]})
        self.assertEqual(next(s for s in f["symbols"] if s["key"] == "mu")["of"], "X")

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
        err = self._validate(c)
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
