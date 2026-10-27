"""原本 → Notion用のページ本文（Notion-flavored Markdown）を作る。

見た目の決まりは templates/notion/components.yaml とこのファイルにだけある。
Notion のページIDは publish/notion.yaml から読み、本文には ID で参照を書く。
"""
from __future__ import annotations

import re
from pathlib import Path

from model import ROOT, TOKEN, Block, Course, load_yaml, parse_blocks

COMP = load_yaml(ROOT / "templates" / "notion" / "components.yaml")
CIRC = "①②③④⑤⑥⑦⑧⑨"
LIST_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s")
ASSET_PLACEHOLDER = "@@ASSET:{}@@"
LONG_CHOICE = 12   # これより長い選択肢があれば、選択肢を1行ずつ並べる


def mention(page_id: str) -> str:
    return f'<mention url="https://app.notion.com/p/{page_id.replace("-", "")}" />'


class NotionRenderer:
    def __init__(self, course: Course, target: dict):
        self.c = course
        self.t = target
        self.tones = COMP["tones"]

    # ---- 参照 -------------------------------------------------------
    def unit_ref(self, uid: str) -> str:
        pid = (self.t.get("units") or {}).get(uid) or (self.t.get("legacy_units") or {}).get(uid)
        if pid:
            return mention(pid)
        return f"教科書{self.c.index[uid]['number']}"

    def term_ref(self, tid: str) -> str:
        pid = (self.t.get("terms") or {}).get(tid)
        return mention(pid) if pid else self.c.terms[tid]["name"]

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
            if kind == "lab":
                return f'<embed source="{ASSET_PLACEHOLDER.format(arg)}" />'
            if kind == "fig":
                fid, _, cap = arg.partition("|")
                cap = cap or self.c.figures[fid].get("caption", "")
                return f'<image source="{ASSET_PLACEHOLDER.format(fid)}">\n{self.inline(cap)}\n</image>'
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
        if q.get("lab"):
            aid = f"{q['lab']['id']}@{q['id']}"
            ans += (f"\n\n{COMP['icons']['lab']} <b>{COMP['labels']['lab_check']}</b>"
                    f"<span color=\"gray\">{COMP['labels']['lab_check_note']}</span>\n\n"
                    f'<embed source="{ASSET_PLACEHOLDER.format(aid)}" />')
        return "\n".join(parts) + f"\n\n<toggle>\n{title}\n\n{ans}\n</toggle>"

    # ---- ページ ------------------------------------------------------
    def unit_page(self, uid: str) -> str:
        u = self.c.units[uid]
        dom = self.c.shared["domains"][u["domain"]]
        nav_tone = self.tones[dom["tone"]]
        lab = COMP["labels"]
        home = mention(self.t["root_page"])
        ref = ""
        if self.t.get("legacy_reference") and u.get("reference_section"):
            ref = (f'\n\n<span color="gray">忘れたら：</span>{mention(self.t["legacy_reference"])}'
                   f'<span color="gray"> の「{u["reference_section"]}」</span>')
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
        return "\n\n".join(out) + "\n"

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
        lines += ["## まだ旧版の単元", "", "| 番号 | 単元 |", "| --- | --- |", *rows,
                  "", '<span color="gray">新しい形に移すと、上の一覧に移る。</span>']
        return "\n".join(lines) + "\n"

    def guide_page(self) -> str:
        src = (ROOT / "content" / "guide.md").read_text(encoding="utf-8")
        rows = "\n".join(f"| {s['icon']} {s['name']} | {s['aim']} | {s['state']} |" for s in self.c.stages)
        table = "| タブ | 目指すこと | できる状態 |\n| --- | --- | --- |\n" + rows
        powers = "\n".join(f"- {p['icon']} <b>{p['name']}</b>：{p['desc']}" for p in self.c.powers.values())
        src = src.replace("{{stages_table}}", table).replace("{{powers_list}}", powers)
        return self.body(src) + "\n"
