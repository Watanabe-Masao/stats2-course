"""build/ の単体テスト。使い方: python3 -m unittest discover -s tests

原本の検証・本文の構文・表示・生成物の検査・ラボの版が、誤りを見逃さないことを確かめる。
「正しいものが通る」だけでなく「間違いを入れたら止まる」ことを1つずつ確かめる。
"""
from __future__ import annotations

import copy
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

    def test_squeeze_keeps_urls_and_code(self):
        src = "  <a href='https://x'>\n  // コメント\n  const a=1; // 行末\n\n"
        self.assertEqual(squeeze(src), "<a href='https://x'>\nconst a=1; // 行末\n")


if __name__ == "__main__":
    unittest.main()
