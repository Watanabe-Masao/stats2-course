"""Notion の読み戻しと生成物の照合（build/notion_compare.py。#483 の D）。

確かめる対象：Notion が自動で直す書き方（メンション・画像・<br>・span の区切り・エスケープ・表のセルの改行。#492）を同じとみて、
  中身の違い（概念 ID・ラボの版＝問題 ID・図・参照先・見出し・文）を見落とさないこと。
想定する故障：①許すべき書き直しを違いと数え、毎回「不一致」になって照合が使われなくなる
  ②正規化しすぎて、リンク先の概念・問題 ID の取り違えや文の書き換えを見落とす。
見つけ方：生成物の形と、Notion の返す形（W2 の9ページの読み戻しで実際に出た5種類）を並べて一致を見る。
  1つずつ中身を変えた写しで、それぞれ「不一致」と、どの事実が違うかが出ることを見る。
既存との違い：これまでは手で cmp.py を使い、数だけを比べていた（ID・参照・文は見ていなかった）。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))
import notion_compare as nc  # noqa: E402

PID = "407b7cd539a181f8bc27f67163370eb9"
GEN = f"""## 例題
<callout icon="💡" color="green_bg">
<b>答え</b>　<mention url="https://app.notion.com/p/{PID}" /> の式
</callout>
<image source="https://watanabe-masao.github.io/stats2-labs/fig/FIG-U28-concept.svg">
十字で4つに分けた図
</image>
① 正しい。
② 誤り。
<span color="gray">平均は <mention url="https://app.notion.com/p/{PID}" />、で見る</span>
SUM(B2:B5)^2 と {{1, 2}}
[相関係数 🕸](https://watanabe-masao.github.io/knowledge-net/?c=stats2:TERM-corr)
<embed source="https://watanabe-masao.github.io/stats2-labs/corr/?p=Q-U28-012" />
<table fit-page-width="true" header-row="true">
<tr>
<td>方法</td>
<td>選び方</td>
</tr>
</table>
"""
BACK = f"""## 例題

<callout icon="💡" color="green_bg">
<b>答え</b>　<mention url="https://app.notion.com/p/{PID}">13｜確率変数・期待値・分散</mention> の式
</callout>

![十字で4つに分けた図](https://watanabe-masao.github.io/stats2-labs/fig/FIG-U28-concept.svg)

① 正しい。<br>② 誤り。

<span color="gray">平均は </span><span color="gray"><mention url="https://app.notion.com/p/{PID}">13｜確率変数・期待値・分散</mention></span><span color="gray">、で見る</span>

SUM(B2:B5)\\^2 と \\{{1, 2\\}}

[相関係数 🕸](https://watanabe-masao.github.io/knowledge-net/?c=stats2:TERM-corr)

<embed source="https://watanabe-masao.github.io/stats2-labs/corr/?p=Q-U28-012" />

<table fit-page-width="true" header-row="true">
<tr>
<td>
方法
</td>
<td>
選び方
</td>
</tr>
</table>
"""


class TestNotionCompare(unittest.TestCase):
    def test_notion_rewrites_are_the_same(self):
        self.assertEqual(nc.compare(GEN, BACK), [])

    def test_content_changes_are_found(self):
        cases = [
            ("TERM-corr", "TERM-cov", "概念・分類"),
            ("Q-U28-012", "Q-U28-011", "ラボの版"),
            ("FIG-U28-concept", "FIG-U28-other", "図"),
            (PID, "407b7cd539a181d0a56dd2a7f54875b0", "ページへの参照"),
            ("## 例題", "## 問題", "見出し"),
            ("② 誤り。", "② 正しい。", "本文"),
            ("\n選び方\n", "\n選ぶ量\n", "本文"),   # 表のセルの中の文の違い（セルの改行をそろえても見落とさない）
        ]
        for old, new, want in cases:
            diffs = nc.compare(GEN, BACK.replace(old, new))
            self.assertTrue(any(d.startswith(want) for d in diffs), (old, diffs))
        self.assertTrue(any("埋め込み" in d for d in nc.compare(GEN, BACK.replace('<embed source="https://watanabe-masao.github.io/stats2-labs/corr/?p=Q-U28-012" />', ""))))


if __name__ == "__main__":
    unittest.main()


class TestPublishedRecord(unittest.TestCase):
    """確かめる対象：公開確認済みの記録（#58。notion_compare --record と published.confirmed）。
    想定する故障：①照らして食い違ったページまで公開確認済みと書く ②生成物が変わったあとも記録が古いまま「公開確認済み」と数える
      ③1つのページを記録すると、ほかのページの記録を消す。
    見つけ方：一時の場所に生成物と読み戻しを置き、一致する1ページと食い違う1ページを --record で照らして、記録に一致したほうだけが入り、
      生成物を1字変えると confirmed が偽になり、別のページを記録しても前の記録が残ることを見る。
    既存との違い：上のテストは照合の正規化だけを見て、記録は見ない。
    検出の確かめ（2026-11-19）：record を食い違ったページにも呼ぶ・confirmed で指紋を比べない、の2つの誤りを入れて落ちることを見た"""

    def test_record_only_matches_and_detect_change(self):
        import tempfile

        import published

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            out, back, rec = d / "out", d / "back", d / "published.yaml"
            out.mkdir(), back.mkdir()
            (out / "A.md").write_text(GEN, encoding="utf-8")
            (back / "A.md").write_text(GEN, encoding="utf-8")
            (out / "B.md").write_text(GEN, encoding="utf-8")
            (back / "B.md").write_text(GEN.replace("① 正しい。", "① 誤り。"), encoding="utf-8")
            old_out, old_rec = nc.OUT, published.RECORD
            try:
                nc.OUT, published.RECORD = out, rec
                self.assertEqual(nc.main(["x", str(back), "A", "B", "--record"]), 1)
                r = published.load()
                self.assertEqual(set(r), {"A"})
                self.assertTrue(published.confirmed("A", GEN))
                self.assertFalse(published.confirmed("A", GEN + "x"))
                self.assertFalse(published.confirmed("B", GEN))
                (back / "B.md").write_text(GEN, encoding="utf-8")
                nc.main(["x", str(back), "B", "--record"])
                self.assertEqual(set(published.load()), {"A", "B"})
            finally:
                nc.OUT, published.RECORD = old_out, old_rec
