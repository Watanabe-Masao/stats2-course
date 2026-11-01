"""ラボの場面ごとの版を作る。

tools/<lab>/tool.yaml に src があるラボは、共通部品（tools/labkit）を差し込み、
場面ごとの設定（window.__LABCFG__）を書き込んだ HTML を out/labs/ に作る。

  素材ID              中身
  LAB-scale           設定なし（自由に動かす）
  LAB-scale@s1-temp   tool.yaml の presets.s1-temp（本文では {{lab:LAB-scale@s1-temp}}）
  LAB-scale@Q-U04-010 問題 Q-U04-010 の lab（答えの中に「ラボで確かめる」として入る）

公開サイト（publish/notion.yaml に site_base_url があるとき）は out/site/<slug>/index.html を1つ作り、
全部の場面を中に持つ。Notion には <slug>/?p=名前 の URL で埋め込む（アップロードは要らない）。

out/labs/manifest.json に、各版の設定と expect（予想の答え。テストでラボの値と照合する）を書く。
expect は HTML には入れない（答えはラボ自身が計算する）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from model import ROOT, TOOLS, Course
from tour import with_gist
import tokens

OUT = ROOT / "out" / "labs"
CFG_KEYS = ("mode", "modes", "set", "unlock", "task", "predict", "why", "steps", "law", "tour")
STEP_KEYS = ("label", "task", "set", "predict", "why")


def page_cfg(spec: dict) -> dict:
    """HTML に入れる設定。expect（予想の答え）は入れない。steps（法則を見つける）も各段の expect を除く。"""
    cfg = {k: spec[k] for k in CFG_KEYS if k in spec}
    if "steps" in cfg:
        cfg["steps"] = [{k: s[k] for k in STEP_KEYS if k in s} for s in cfg["steps"]]
    return cfg


def expect_of(spec: dict):
    """テストで照合する答え。steps なら各段の expect の並び。"""
    if spec.get("steps"):
        return [s.get("expect") for s in spec["steps"]]
    return spec.get("expect")


def tour_expect(aid: str, spec: dict):
    """解説付き再生の照合する数（段・frame ごと）。tour がなければ None。"""
    if not spec.get("tour"):
        return None
    import tour
    try:
        return tour.expect(aid.split("@")[0], spec)
    except KeyError:
        return None


def safe(aid: str) -> str:
    return aid.replace("@", "__")


def lab_file(course: Course, aid: str) -> Path:
    """素材IDから、アップロードするファイルを返す。"""
    lab = aid.split("@")[0]
    t = course.labs[lab]
    if t.get("src"):
        return OUT / f"{safe(aid)}.html"
    return t["dir"] / t["file"]


def variants(course: Course) -> dict[str, dict]:
    """素材ID → 設定（expect を含む）。"""
    out = {}
    for lid, t in course.labs.items():
        if not t.get("src"):
            continue
        out[lid] = {}
        for name, p in (t.get("presets") or {}).items():
            out[f"{lid}@{name}"] = with_gist(lid, name, p)   # 関係から開く解説には最後に「つまり」の段（#95）
    for u in course.units.values():
        for qid, q in u["problems"].items():
            if q.get("lab"):
                out[f"{q['lab']['id']}@{qid}"] = q["lab"]
    return out


RANDOM = TOOLS.parent / "docs" / "math-lab" / "random.js"


def _drop_head_comment(src: str) -> str:
    """先頭の説明コメント（/* … */）は版に入れない（説明は原本で読む）。"""
    src = src.lstrip()
    return src[src.index("*/") + 2:] if src.startswith("/*") else src


def squeeze(html: str) -> str:
    lines = []
    for line in html.splitlines():
        s = line.strip()
        if not s or (s.startswith("//") and not s.startswith("//@")):
            continue
        lines.append(s)
    return "\n".join(lines) + "\n"


SITE = ROOT / "out" / "site"
_PICK = ("window.__LABCFG__=(function(){try{var p=new URLSearchParams(location.search).get(\"p\");"
         "return (p&&window.__LABPRESETS__[p])||{};}catch(e){return {};}})();")


def fig_url(base: str, fid: str) -> str:
    return f"{base.rstrip('/')}/fig/{fid}.svg"


def lab_url(base: str, course: Course, aid: str) -> str:
    """公開先のラボの URL（場面は ?p=名前 で渡す）。"""
    lid, _, name = aid.partition("@")
    url = f"{base.rstrip('/')}/{course.labs[lid]['slug']}/"
    return url + (f"?p={name}" if name else "")


def _assemble(t: dict, cfg_js: str) -> str:
    kit_css = tokens.css() + _drop_head_comment((TOOLS / "labkit" / "labkit.css").read_text(encoding="utf-8"))   # 値（knowledge-net と共通）→ ラボの見た目
    # ラボの乱数は math-lab の束（docs/math-lab/random.js。写し）を labkit の前に置き、LK.rng(seed) で使う（#144 P6）
    rand_js = "\n".join(l for l in RANDOM.read_text(encoding="utf-8").splitlines() if not l.startswith("//"))
    kit_js = rand_js + "\n" + _drop_head_comment((TOOLS / "labkit" / "labkit.js").read_text(encoding="utf-8"))
    src = (t["dir"] / t["src"]).read_text(encoding="utf-8")
    html = (src.replace("/*@LABKIT_CSS@*/", kit_css)
               .replace("/*@LABKIT_JS@*/", kit_js)
               .replace("/*@LABCFG@*/", cfg_js))
    if "@LAB" in html:
        raise ValueError(f"{t['id']}: 差し込み口が残っている")
    return squeeze(html)


def build_site(course: Course) -> list[dict]:
    """公開サイト用：ラボごとに1ファイル。全部の場面を中に持ち、URL の ?p= で選ぶ。"""
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    entries, links = [], []
    by_lab: dict[str, dict] = {}
    for aid, spec in variants(course).items():
        lid, _, name = aid.partition("@")
        if name:
            by_lab.setdefault(lid, {})[name] = page_cfg(spec)
    for lid, t in course.labs.items():
        if not t.get("src"):   # 共通部品を使わない古い形のラボはそのまま置く（場面の版はない）
            d = SITE / t["slug"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_bytes((t["dir"] / t["file"]).read_bytes())
            entries.append({"asset": lid, "file": str((d / "index.html").relative_to(ROOT)), "query": "", "cfg": {}, "expect": None})
            links.append(f'<li><a href="{t["slug"]}/">{t["name"]}</a></li>')
            continue
        presets = by_lab.get(lid, {})
        js = "window.__LABPRESETS__=" + json.dumps(presets, ensure_ascii=False) + ";" + _PICK
        d = SITE / t["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(_assemble(t, js), encoding="utf-8")
        modes = [m["key"] for m in t.get("modes", []) if isinstance(m, dict)]
        rel = str((d / "index.html").relative_to(ROOT))
        entries.append({"asset": lid, "file": rel, "query": "", "cfg": {}, "expect": None, "modes": modes})
        for name, cfg in presets.items():
            spec = variants(course)[f"{lid}@{name}"]
            entries.append({"asset": f"{lid}@{name}", "file": rel, "query": f"?p={name}", "cfg": cfg,
                            "expect": expect_of(spec), "modes": modes, "tour_expect": tour_expect(f"{lid}@{name}", spec)})
        links.append(f'<li><a href="{t["slug"]}/">{t["name"]}</a>（場面 {len(presets)}）</li>')
    figdir = SITE / "fig"   # 図も公開サイトから出す（アップロード不要）
    figdir.mkdir(exist_ok=True)
    for fid, f in course.figures.items():
        (figdir / f"{fid}.svg").write_bytes((ROOT / f["file"]).read_bytes())
    (SITE / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>統計検定2級 ラボ</title><h1>統計検定2級 ラボ</h1><p>教材の原本（stats2-course）から自動で作るページ。"
        "教材のページから場面を指定して埋め込む。</p><ul>" + "".join(links) + "</ul>\n", encoding="utf-8")
    # 試験用の一覧（予想の答えを含むので公開サイトの外に置く）
    (ROOT / "out" / "site_manifest.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    return entries


def build_labs(course: Course) -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for lid, t in course.labs.items():   # 共通部品を使わない古い形のラボ（そのまま使う）
        if not t.get("src"):
            manifest.append({"asset": lid, "file": str((t["dir"] / t["file"]).relative_to(ROOT)), "cfg": {}, "expect": None})
    for aid, spec in variants(course).items():
        lid = aid.split("@")[0]
        t = course.labs[lid]
        cfg = page_cfg(spec)
        f = OUT / f"{safe(aid)}.html"
        f.write_text(_assemble(t, "window.__LABCFG__=" + json.dumps(cfg, ensure_ascii=False) + ";"), encoding="utf-8")
        manifest.append({"asset": aid, "file": str(f.relative_to(ROOT)), "cfg": cfg, "expect": expect_of(spec),
                         "modes": [m["key"] for m in t.get("modes", []) if isinstance(m, dict)], "tour_expect": tour_expect(aid, spec)})
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


# 自前の乱数がまだ残っているラボ（#144 P6 の組 B・C で移し、ここから外す。空になったらこの一覧を消す）
RNG_PENDING = {"LAB-sample", "LAB-ts"}


def validate_labs(course: Course) -> list[str]:
    err = []
    for lid, t in course.labs.items():
        if t.get("src") and not (t["dir"] / t["src"]).exists():
            err.append(f"{lid}: {t['src']} がない")
        if not t.get("src") and not (t["dir"] / str(t.get("file", ""))).is_file():
            err.append(f"{lid}: file（古い形のラボ）がない")
        slugs = [x.get("slug") for x in course.labs.values()]
        if slugs.count(t.get("slug")) > 1:
            err.append(f"{lid}: slug {t.get('slug')} がほかのラボと重なる")
        if t.get("src") and (t["dir"] / t["src"]).exists():
            # 色は design/tokens.json の変数で（#42。ラボ・静止図・知識ネットワークで同じ色）。色付きの面の上の白い文字だけ例外
            for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", (t["dir"] / t["src"]).read_text(encoding="utf-8")):
                if m.group(0).lower() not in ("#fff", "#ffffff"):
                    err.append(f"{lid}: 色の値 {m.group(0)} は書かない（var(--data-1) などの変数で。値は docs/math-lab/tokens.json）")
                    break
        if t.get("src") and (t["dir"] / t["src"]).exists():
            # 乱数はラボの中に書かない（math-lab の種つき乱数を LK.rng で。#144 P6）。自前の rng は移すまでの間だけ RNG_PENDING に
            body = (t["dir"] / t["src"]).read_text(encoding="utf-8")
            if "Math.random" in body:
                err.append(f"{lid}: Math.random は使わない（LK.rng(種) で。同じ種なら同じ結果）")
            # 自前の乱数：中身（Park–Miller の 16807・mulberry32 の 0x6D2B79F5）で見る（function rng でない書き方も捕まえる）
            if re.search(r"16807|0x6D2B79F5", body, re.I) and lid not in RNG_PENDING:
                err.append(f"{lid}: 自前の乱数（function rng）は使わない（LK.rng(種) で。#144）")
        if not re.fullmatch(r"[a-z0-9-]+", str(t.get("slug", ""))):
            err.append(f"{lid}: 公開先のフォルダ名 slug（英小文字・数字・-）がない")
        for name, p in (t.get("presets") or {}).items():
            err += _check_spec(f"{lid}@{name}", p, t)
    for u in course.units.values():
        for qid, q in u["problems"].items():
            if not q.get("lab"):
                continue
            lab = q["lab"]
            if lab.get("id") not in course.labs:
                err.append(f"{qid}: lab.id {lab.get('id')} がない")
            elif not course.labs[lab["id"]].get("src"):
                err.append(f"{qid}: {lab['id']} は場面ごとの版を作れない（tool.yaml に src がない）")
            if not lab.get("task"):
                err.append(f"{qid}: lab.task（課題の文）がない")
            err += _check_spec(qid, lab, course.labs.get(lab.get("id")))
    return err


def _check_spec(where: str, p: dict, tool: dict | None) -> list[str]:
    """場面の設定が、ラボの約束（tool.yaml の modes の set・values）に合っているか。"""
    err = []
    modes = {m["key"]: m for m in (tool or {}).get("modes", []) if isinstance(m, dict)}
    mode = modes.get(p.get("mode")) if p.get("mode") else None
    if p.get("mode") and not mode:
        err.append(f"{where}: mode {p.get('mode')} はラボにない（{', '.join(modes)}）")
    if mode:
        extra = set(p.get("set") or {}) - set(mode.get("set", []))
        if extra:
            err.append(f"{where}: set の {sorted(extra)} はモード {mode['key']} で使えない（{mode.get('set')}）")
        key = (p.get("predict") or {}).get("key")
        if key and key not in mode.get("values", []):
            err.append(f"{where}: predict.key {key} はモード {mode['key']} の values にない（{mode.get('values')}）")
    for k in p.get("modes") or []:
        if k not in modes:
            err.append(f"{where}: modes の {k} はラボにない（{', '.join(modes)}）")
    for k in p.get("unlock") or []:
        if k not in (p.get("set") or {}):
            err.append(f"{where}: unlock の {k} は set にない（予想のあとも選べるようにする選択欄は set で値を決める）")
    if p.get("modes") and p.get("mode") not in p["modes"]:
        err.append(f"{where}: mode は modes に含める")
    if not mode and (p.get("set") or p.get("predict")):
        err.append(f"{where}: set や predict を使うときは mode を書く")
    if p.get("tour") is not None:
        import tour
        err += tour.validate(where, p, mode, (tool or {}).get("id", ""), modes)
    steps = p.get("steps")
    if steps is not None:
        if not isinstance(steps, list) or len(steps) < 2:
            err.append(f"{where}: steps（法則を見つける）は2段以上のリスト")
            steps = []
        if not mode:
            err.append(f"{where}: steps を使うときは mode を書く")
        if p.get("predict") or p.get("task"):
            err.append(f"{where}: steps を使うときは、task・predict は各段に書く")
        for i, s in enumerate(steps, 1):
            w = f"{where} の段{i}"
            if not s.get("label"):
                err.append(f"{w}: label（条件の短い名前。記録の表に出る）がない")
            extra = set(s) - set(STEP_KEYS) - {"expect"}
            if extra:
                err.append(f"{w}: 使えない項目 {sorted(extra)}")
            err += _check_spec(w, {"mode": p.get("mode"), **{k: s[k] for k in ("set", "predict", "expect", "task") if k in s}}, tool)
            if not s.get("predict"):
                err.append(f"{w}: predict がない（探究は毎段で予想する）")
        law = p.get("law")
        if not law or not law.get("lines"):
            err.append(f"{where}: steps の最後に見せる law.lines（式）がない")
    pr = p.get("predict")
    if pr:
        if pr.get("type") not in ("number", "choice"):
            err.append(f"{where}: predict.type は number か choice")
        if not pr.get("key"):
            err.append(f"{where}: predict.key がない")
        if pr.get("type") == "choice" and not pr.get("options"):
            err.append(f"{where}: predict.options がない")
        if p.get("expect") is None:
            err.append(f"{where}: predict があるのに expect（ラボの値と照合する答え）がない")
        if not p.get("task"):
            err.append(f"{where}: predict があるのに task がない")
    return err
