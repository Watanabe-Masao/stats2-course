"""原本 → Notion用のページ本文（Notion-flavored Markdown）を作る。

見た目の決まりは templates/notion/components.yaml とこのファイルにだけある。
Notion のページIDは publish/notion.yaml から読み、本文には ID で参照を書く。
"""
from __future__ import annotations

import re
from urllib.parse import quote
from pathlib import Path

from labs import fig_url, lab_url
from model import ROOT, TOKEN, Block, Course, load_yaml, parse_blocks, term_written

COMP = load_yaml(ROOT / "templates" / "notion" / "components.yaml")
CIRC = "①②③④⑤⑥⑦⑧⑨"
LIST_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
ASSET_PLACEHOLDER = "@@ASSET:{}@@"
LONG_CHOICE = 12   # これより長い選択肢があれば、選択肢を1行ずつ並べる
CHECK = re.compile(r"^- \[[ xX]\] ")   # 教材のチェック欄（□ の箇条書きにする）


# ---- スマホで読める形にする（#489）------------------------------------
# 原本の書き方（```txt の式のまとめ・x̄_st のような下付き）はそのままにし、Notion に書き出すときだけ変える。
# ① コードの欄は iPhone の Notion で折り返さず、長い行が切れる → 1行ずつの段落にした灰色の枠にする
# ② 「_」の下付きは Notion で文字のまま出る → Unicode の下付き文字にする。下付き文字のない字（b・y・大文字・漢字など）を
#    含む行は、その行の下付きを全部 Notion の数式（$s_{xy}$）にする（1つの行で2つの書き方を混ぜない）
SUB = dict(zip("aehijklmnoprstuvx0123456789", "ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ₀₁₂₃₄₅₆₇₈₉"))
TEX_BASE = {"σ": r"\sigma", "π": r"\pi", "μ": r"\mu"}
TEX_MARK = {"\u0304": r"\bar", "\u0302": r"\hat"}
TEX_SUP = {"²": "2", "³": "3"}
# 前が英字でない1〜2字の記号（結合文字の上線・ハットを含む）＋「_」＋下付き（英数字の並び。偏相関の「r_xy・z」の「・z」。z_a・z_b のような並びは含めない。漢字1字も）
SUBSCRIPT = re.compile(r"(?<![A-Za-z])((?:[A-Za-z][\u0302\u0304]?){1,2}|[σπμ])_([A-Za-z0-9]+(?:・[A-Za-z](?![A-Za-z_]))?|[\u4e00-\u9fff])([²³]?)")
PROTECT = re.compile(r"(<[^>]*>|\]\([^)]*\)|https?://\S+|\$[^$\n]+\$)")
FENCE = re.compile(r"^```[a-z]*\n(.*?)\n```$", re.M | re.S)
CODE_ESCAPE = re.compile(r"([\\`*~\[\]<>|])")   # 「_」は下付きにするので除く


def _tex(base: str, sub: str, sup: str) -> str:
    mark = TEX_MARK.get(base[-1]) if len(base) == 2 else None
    b = f"{mark}{{{base[0]}}}" if mark else TEX_BASE.get(base, base)
    sub = sub.replace("・", r"\cdot ")
    sub = rf"\text{{{sub}}}" if re.fullmatch(r"[\u4e00-\u9fff]", sub) else f"{{{sub}}}"   # 漢字は \text（「{{」を作らない。lint が部品の残りと見る）
    return f"${b}_{sub}" + (f"^{{{TEX_SUP[sup]}}}" if sup else "") + "$"


def subscripts(line: str) -> str:
    """1行の「_」の下付きを、Unicode の下付き文字か Notion の数式にする。タグ・リンク・数式の中は変えない。"""
    parts = PROTECT.split(line)
    plain = [re.sub(r"_([A-Za-z0-9])([A-Za-z])_", "_\\1\x00\\2_", seg) for seg in parts[0::2]]   # b_kx_k は b_k と x_k
    unicode_ok = all(all(ch in SUB for ch in m.group(2)) for seg in plain for m in SUBSCRIPT.finditer(seg))
    def one(m):
        base, sub, sup = m.groups()
        return base + "".join(SUB[ch] for ch in sub) + sup if unicode_ok else _tex(base, sub, sup)
    parts[0::2] = [SUBSCRIPT.sub(one, seg) for seg in plain]
    return "".join(parts).replace("\x00", "")


def code_to_callout(m: re.Match) -> str:
    """コードの欄 → 1行ずつの段落にした灰色の枠。中の記号は文字のまま出す（下付きは for_phone がこのあと変える）。"""
    spec = COMP["code_block"]
    lines = [CODE_ESCAPE.sub(r"\\\1", line) for line in m.group(1).split("\n")]
    return f'<callout icon="{spec["icon"]}" color="{spec["color"]}">\n' + "\n".join(lines) + "\n</callout>"


# ③ 3列以上の表は iPhone の Notion で右が切れる（列の幅が決まっていて、fit-page-width でも縮まない。2026-11-17 の実画面）
#    → 2列にまとめる：1列目はそのまま、2列目に2列目以降を改行で重ね、3列目からは灰色の列の見出しを付ける（#492）
TABLE = re.compile(r"^(\|.*\|)\n\|(?: *-+ *\|)+\n((?:\|.*\|\n?)*)", re.M)
CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _cells(row: str) -> list[str]:
    return [c.strip().replace("\\|", "|") for c in CELL_SPLIT.split(row.strip())[1:-1]]


def wide_table(m: re.Match) -> str:
    """3列以上のパイプの表 → 2列のパイプの表。2列の表はそのまま。"""
    head = _cells(m.group(1))
    if len(head) < 3:
        return m.group(0)
    esc = lambda c: c.replace("|", "\\|")
    rows = [[head[0], "／".join(head[1:])]]
    for r in (_cells(r) for r in m.group(2).rstrip("\n").split("\n")):
        rest = [r[1]] + [f'<span color="gray">{h}：</span>{c}' for h, c in zip(head[2:], r[2:])]
        rows.append([r[0], "<br />".join(rest)])
    lines = [f"| {esc(a)} | {esc(b)} |" for a, b in rows]
    lines.insert(1, "| --- | --- |")
    tail = "\n" if m.group(2).endswith("\n") else ""
    return "\n".join(lines) + tail


def for_phone(md: str) -> str:
    """ページ全体をスマホで読める形にする（#489・#492）。表示の数式（$$ の行）の中は変えない。"""
    md = FENCE.sub(code_to_callout, md)
    md = TABLE.sub(wide_table, md)
    out, in_math = [], False
    for line in md.split("\n"):
        if line.strip() == "$$":
            in_math = not in_math
        out.append(line if in_math or line.strip() == "$$" else subscripts(line))
    return "\n".join(out)


def mention(page_id: str) -> str:
    return f'<mention url="https://app.notion.com/p/{page_id.replace("-", "")}" />'


class NotionRenderer:
    def __init__(self, course: Course, target: dict):
        self.c = course
        self.t = target
        self.tones = COMP["tones"]

    # ---- 参照 -------------------------------------------------------
    def unit_ref(self, uid: str) -> str:
        pid = (self.t.get("units") or {}).get(uid)
        if pid:
            return mention(pid)
        return f"教科書{self.c.index[uid]['number']}"

    def term_ref(self, tid: str) -> str:
        """用語のリンク。説明のある概念は知識ネットワークの画面へ。説明がまだの語と、画面のない配布先では名前だけ（旧版の用語ページは指さない。#53）。"""
        t = self.c.terms[tid]
        if term_written(t) and self.t.get("network_url"):   # 説明ありと文脈の見出しは画面にページがある（model.term_state）
            from network import course_id
            return f"[{t['name']} 🕸]({self.t['network_url']}?c={course_id(self.c)}:{tid})"
        return t["name"]

    def lab_src(self, aid: str) -> str:
        """公開サイトがあれば URL、なければアップロードの差し込み口（publish_prep が置き換える）。"""
        lid = aid.split("@")[0]
        if self.t.get("site_base_url") and self.c.labs[lid].get("src"):
            return lab_url(self.t["site_base_url"], self.c, aid)
        return ASSET_PLACEHOLDER.format(aid)

    def stage_label(self, sid: str) -> str:
        s = next(s for s in self.c.stages if s["id"] == sid)
        return f"{s['icon']} {s['name']}"

    # ---- インライン ---------------------------------------------------
    def inline(self, text: str) -> str:
        def tok(m):
            kind, arg = m.group(1), m.group(2)
            if kind == "unit":
                return self.unit_ref(arg)
            if kind == "term":
                return self.term_ref(arg)
            if kind == "power":
                return self.c.powers[arg]["icon"]
            if kind == "icon":
                return COMP["icons"][arg]
            if kind == "stage":
                return self.stage_label(arg)
            if kind == "shared":
                return self.inline(self.c.shared[arg])
            if kind == "lab":   # 解説付き再生の版には「▶ ラボで解説」を付ける（確かめる版と見分ける。#90）
                lid, _, pre = arg.partition("@")
                head = (f'<b>{COMP["labels"]["lab_tour"]}</b>\n\n'
                        if pre and ((self.c.labs[lid].get("presets") or {}).get(pre) or {}).get("tour") else "")
                return f'{head}<embed source="{self.lab_src(arg)}" />'
            if kind == "fig":
                fid, _, cap = arg.partition("|")
                cap = cap or self.c.figures[fid].get("caption", "")
                src = fig_url(self.t["site_base_url"], fid, self.c) if self.t.get("site_base_url") else ASSET_PLACEHOLDER.format(fid)
                return f'<image source="{src}">\n{self.inline(cap)}\n</image>'
            if kind == "ref":
                pid = (self.t.get("refs") or {}).get(arg)
                label = self.c.shared["refs"][arg]
                return mention(pid) if pid else label
            return m.group(0)
        text = TOKEN.sub(tok, text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        return text

    # ---- ブロック ------------------------------------------------------
    def body(self, src: str, problems: dict | None = None, counter: list | None = None) -> str:
        blocks, err = parse_blocks(src)
        if err:  # validate() で先に止まるはず。ここに来たら生成をやめる
            raise ValueError("本文の書き方の誤り: " + " / ".join(err))
        return self.blocks(blocks, problems, counter)

    def blocks(self, blocks: list[Block], problems: dict | None, counter: list | None) -> str:
        out = []
        for b in blocks:
            if b.kind == "container":
                out.append(self.container(b, problems, counter))
            elif b.kind == "problem":
                out.append(self.problem(problems[b.text], counter))
            elif b.kind == "gray":
                out.append(f'<span color="gray">{self.inline(b.text)}</span>')
            else:
                out.append(self.inline(b.text))
        return "\n".join(out)

    def container(self, b: Block, problems, counter) -> str:
        inner = self.blocks(b.inner, problems, counter)
        if b.name == "toggle":
            return f"<toggle>\n{self.inline(b.title)}\n\n{inner}\n</toggle>"
        spec = COMP["callouts"][b.name]
        content = self.join_soft_breaks(inner)
        head = f"<b>{self.inline(b.title or spec.get('title', ''))}</b>\n\n" if (b.title or spec.get("title")) else ""
        return f'<callout icon="{spec["icon"]}" color="{spec["color"]}">\n{head}{content}\n</callout>'

    @staticmethod
    def join_soft_breaks(text: str) -> str:
        """枠の中で、リストでない連続行を <br /> でつなぐ（Notionで1つの段落にする）。"""
        out = []
        for line in text.split("\n"):
            if out and out[-1] and line and not LIST_RE.match(line) and not LIST_RE.match(out[-1]) \
                    and not line.startswith("<") and not out[-1].endswith(">"):
                out[-1] += "<br />" + line
            else:
                out.append(line)
        return "\n".join(out)

    def problem(self, q: dict, counter: list) -> str:
        icons = "".join(self.c.powers[p]["icon"] for p in q.get("powers", []))
        if q.get("label"):
            label = q["label"]
        else:
            counter[0] += 1
            tag = q.get("tag") or COMP["labels"]["difficulty"].get(q.get("difficulty"))
            label = f"問{counter[0]}" + (f"（{tag}）" if tag else "")
        first, *rest = self.inline(q["prompt"]).split("\n")
        parts = [f"<b>{label}</b> {icons}　{first}".replace(" 　", "　")]
        if rest:
            parts.append("\n".join(rest))
        if q["format"] == "choice":
            ch, k = q["choices"], q["correct"]
            long = max(len(str(v)) for v in ch) > LONG_CHOICE   # 長い選択肢は1行ずつ
            sep = "\n" if long else "　"
            parts.append("\n" + sep.join(f"{CIRC[i]} {self.inline(str(v))}" for i, v in enumerate(ch)))
            head = f"<b>正解は{CIRC[k - 1]}</b>" if long else f"<b>{CIRC[k - 1]} {self.inline(str(ch[k - 1]))}</b>"
            ans = f"{head}。{self.inline(q['answer'])}"
            mis = sorted((int(n), t) for n, t in (q.get("misconceptions") or {}).items())
            if mis:
                ans += "\n\n" + "\n".join(
                    f"- {CIRC[n - 1]}：{self.inline(t)}" if long else f"- {CIRC[n - 1]} {self.inline(str(ch[n - 1]))}＝{self.inline(t)}"
                    for n, t in mis)
            title = q.get("answer_title") or COMP["labels"]["answer_choice"]
        else:
            ans = self.inline(q["answer"])
            title = q.get("answer_title") or COMP["labels"]["answer_default"]
        if q.get("figure"):
            fid = f"FIG-{q['id']}"
            ans += (f"\n\n{COMP['icons']['fig']} <b>{COMP['labels']['fig_check']}</b>\n\n"
                    + self.inline(f"{{{{fig:{fid}}}}}"))
        if q.get("lab"):
            aid = f"{q['lab']['id']}@{q['id']}"
            ans += (f"\n\n{COMP['icons']['lab']} <b>{COMP['labels']['lab_check']}</b>"
                    f"<span color=\"gray\">{COMP['labels']['lab_check_note']}</span>\n\n"
                    f'<embed source="{self.lab_src(aid)}" />')
        return "\n".join(parts) + f"\n\n<toggle>\n{title}\n\n{ans}\n</toggle>"

    def checklists(self, md: str) -> str:
        """教材の中に、押して状態が残るチェック欄を作らない（個人の状態は個人用の記録に置く）。
        「- [ ] 文」は「□ 文」の箇条書きにし、続けて記録先を灰色で添える（配布先の設定では記録先なし）。"""
        lines, out, i = md.split("\n"), [], 0
        note = COMP["labels"]["checklist_note"]
        dest = f" → {mention(self.t['personal_root'])}" if self.t.get("personal_root") else ""
        while i < len(lines):
            if CHECK.match(lines[i]):
                while i < len(lines) and CHECK.match(lines[i]):
                    out.append("- □ " + CHECK.sub("", lines[i]))
                    i += 1
                out.append(f'\n<span color="gray">{note}</span>{dest}')
                continue
            out.append(lines[i])
            i += 1
        return "\n".join(out)

    # ---- ページ ------------------------------------------------------
    def unit_page(self, uid: str) -> str:
        u = self.c.units[uid]
        dom = self.c.shared["domains"][u["domain"]]
        nav_tone = self.tones[dom["tone"]]
        lab = COMP["labels"]
        home = mention(self.t["root_page"])
        ref = ""
        if self.t.get("network_url") and u.get("recall_group"):   # 忘れたら、その分類の概念を知識ネットワークで開く（#53）
            g = u["recall_group"]
            ref = (f'\n\n<span color="gray">忘れたら：</span>[{g} 🕸]({self.t["network_url"]}?g={quote(g)})')
        prev = f"◀ {self.unit_ref(u['prev'])}" if u.get("prev") else "（最初）"
        nxt = f"{self.unit_ref(u['next'])} ▶" if u.get("next") else "（最後）"
        out = [
            f'<callout icon="🧭" color="{nav_tone}">\n<b>{dom["icon"]} {dom["name"]}</b>　｜　'
            f'{self.c.index[uid]["number"]} / {self.c.shared["total_units"]}\n\n'
            f"{prev}　｜　{home}　｜　{nxt}{ref}\n</callout>",
            f'<callout icon="🎯" color="blue_bg">\n{self.inline(u["goal"])}\n\n'
            f'<span color="gray">{lab["guide_link"]} </span>{mention(self.t["guide_page"])}\n</callout>',
            "<tabs>",
        ]
        for s in self.c.stages:
            counter = [0]
            tone = self.tones[s["tone"]]
            goal = (f'<callout icon="{s["icon"]}" color="{tone}">\n<b>{lab["goal_title"]}：{s["state"]}</b>　'
                    f'{self.inline(u["stage_goals"][s["id"]])}\n</callout>')
            body = self.body(u["bodies"][s["id"]].strip(), u["problems"], counter)
            out.append(f'<tab icon="{s["icon"]}">\n{s["name"]}\n\n{goal}\n\n{body}\n</tab>')
        out.append("</tabs>")
        # 戻り先
        back = [f"### {lab['back_title']}", ""]
        if u.get("terms"):
            back.append("- 用語を確かめる → " + "・".join(self.term_ref(t) for t in u["terms"]))
        if u.get("prereq"):
            back.append("- 前提の単元 → " + "・".join(self.unit_ref(x) for x in u["prereq"]))
        if u.get("used_by"):
            back.append("- この単元が使われる先 → " + "・".join(self.unit_ref(x) for x in u["used_by"]))
        out += ["---", "\n".join(back)]
        ev = "\n".join(f"| {self.stage_label(s['id'])} | {u['evidence'][s['id']]} |" for s in self.c.stages)
        personal = f" → {mention(self.t['personal_root'])}" if self.t.get("personal_root") else ""
        out.append(f"<toggle>\n{lab['evidence_title']}\n\n| 段階 | できた証拠 |\n| --- | --- |\n{ev}\n\n"
                   f'<span color="gray">{self.c.shared["personal_note"]}</span>{personal}\n</toggle>')
        src = "・".join(f"[{s['name']}]({s['url']})" for s in self.c.shared["sources"])
        out.append(f"<toggle>\n{lab['meta_title']}\n\n単元ID：{uid}　版：{u['version']}　原本：stats2-course/content/units/{uid}/"
                   f"（このページは生成物。直すときは原本を直して作り直す）\n\n{self.c.shared['content_note']}\n\n"
                   f"出典：{src} を内容照合の基準とし、説明・例題・問題は独自に構成。\n</toggle>")
        return for_phone(self.checklists("\n\n".join(out))) + "\n"

    def root_page(self) -> str:
        lines = [
            '<callout icon="📌" color="blue_bg">\nこのページと配下の単元は、GitHub の原本（stats2-course）から生成している。'
            "直すときはページではなく原本を直して作り直す。\n</callout>",
        ]
        # このページの子ページは <page> ブロックで並べる（mention にすると子ページが消える）
        def child(pid, title):
            return f'<page url="https://app.notion.com/p/{pid}">\n{title}\n</page>'
        lines += ["", "## 最初に読む", "", child(self.t["guide_page"], "学び方ガイド")]
        if self.t.get("personal_root"):
            lines.append(f"\n自分の記録 → {mention(self.t['personal_root'])}")
        new = self.t.get("units") or {}
        lines += ["", "## 単元（新しい形）", ""]
        for uid, meta in self.c.index.items():
            if uid in new:
                lines += [child(new[uid], f"{meta['number']}｜{self.c.units[uid]['title']}"), ""]
        rows = [f"| {m['number']} | {self.unit_ref(uid)} |" for uid, m in self.c.index.items() if uid not in new]
        if rows:   # 全部移したら、旧版の一覧は出さない
            lines += ["## まだ旧版の単元", "", "| 番号 | 単元 |", "| --- | --- |", *rows,
                      "", '<span color="gray">新しい形に移すと、上の一覧に移る。</span>']
        return "\n".join(lines).rstrip("\n") + "\n"

    def home_page(self) -> str:
        """一番上のページ（ホーム）。入口だけを置く。子ページは <page> ブロックで並べる。"""
        def child(pid, title):
            return f'<page url="https://app.notion.com/p/{pid.replace("-", "")}">\n{title}\n</page>'
        lines = [
            '<callout icon="📐" color="gray_bg">\n統計検定2級の教材と、自分の学習記録の入口。'
            "教材は GitHub の原本（stats2-course）から生成している。\n</callout>",
            "", "## 入口", "", child(self.t["root_page"], "教材 v2｜統計検定2級"),
        ]
        net = "🕸 知識ネットワーク：概念と関係の地図（前提をさかのぼる・比べる）"
        if self.t.get("network_url"):   # 公開した画面（knowledge-net）
            lines += ["", f"- 🕸 [知識ネットワーク]({self.t['network_url']})：概念と関係の地図（前提をさかのぼる・比べる）"]
        if self.t.get("personal_root"):
            lines += ["", child(self.t["personal_root"], "学習記録（個人用）")]
        lines += ["", "## 準備中", ""]
        if not self.t.get("network_url"):
            lines.append(f"- {net}")
        lines.append("- 🤖 AI と学ぶ：学習記録を読んで、問いかけ→ヒント→確認問題で進める")
        status = [child(self.t[k], name) for k, name in (("progress_page", "進み具合"), ("legacy_page", "旧版（削除予定）")) if self.t.get(k)]
        if status:
            lines += ["", "## 作業の状況", "", "\n\n".join(status)]
        return "\n".join(lines).rstrip("\n") + "\n"

    def legacy_page(self, report: list[dict]) -> str:
        """旧版（削除予定）。publish/legacy.yaml の項目ごとに、置き換え先・削除の条件・今の状態と、旧版そのもの（子）を並べる。"""
        from legacy import SIX
        state = {"still": "まだ参照あり", "ready": "削除の候補（build の確認は通った。削除は6条件と承認のあと）", "archived": "アーカイブ済み", "deleted": "削除済み"}
        lines = ['<callout icon="🗄" color="gray_bg">\n新しい構造に取り込むまで残している旧版。'
                 "条件を満たしたものから削除する（管理表は GitHub の publish/legacy.yaml）。新しく参照しない。\n</callout>"]
        for r in report:
            it = r["item"]
            if r["state"] == "deleted":
                continue
            lines += ["", f"## {it['name']}", "",
                      f"- 置き換え先：{it.get('replaced_by', '')}",
                      f"- 削除する時期：{it.get('when', '未定')}",
                      f"- 今の状態：<b>{state[r['state']]}</b>"]
            checks = it.get("checks") or {}
            if checks:   # 削除の6条件（渡辺さん 2026-11-17）
                lines += ["- 削除の6条件：" + "・".join(f"{SIX[k]} {(checks.get(k) or {}).get('state', '未確認')}" for k in SIX),
                          f"- 削除の承認：{it.get('approved') or 'まだ'}"]
            lines.append("")
            for n in it.get("notion", []):
                pid = str(n["id"]).replace("-", "")
                tag = "database" if n.get("type") == "database" else "page"
                lines += [f'<{tag} url="https://app.notion.com/p/{pid}">\n{n.get("title", "")}\n</{tag}>', ""]
        return "\n".join(lines).rstrip("\n") + "\n"

    def guide_page(self) -> str:
        src = (ROOT / "content" / "guide.md").read_text(encoding="utf-8")
        rows = "\n".join(f"| {s['icon']} {s['name']} | {s['aim']} | {s['state']} |" for s in self.c.stages)
        table = "| タブ | 目指すこと | できる状態 |\n| --- | --- | --- |\n" + rows
        powers = "\n".join(f"- {p['icon']} <b>{p['name']}</b>：{p['desc']}" for p in self.c.powers.values())
        src = src.replace("{{stages_table}}", table).replace("{{powers_list}}", powers)
        return for_phone(self.body(src)) + "\n"
