"""生成物（out/notion/*.md）の検査。原本の検証をすり抜けた表示の崩れを、公開前に止める。

  - 部品 {{...}}・太字 ** が変換されずに残っていない
  - Notion で消える <sup> を使っていない
  - 表は3列まで（スマホで読むため）
  - 開いた枠・開閉・タブが閉じている、$$ が対になっている
  - 素材 @@ASSET:ID@@ が図の一覧かラボの版にある
  - メンションの URL が NotionページIDの形
"""
from __future__ import annotations

import re

MAX_COLS = 3
TAGS = ("callout", "toggle", "tabs", "tab", "image", "page")
ASSET = re.compile(r"@@ASSET:([\w@-]+)@@")
MENTION = re.compile(r'<mention url="([^"]*)"')
PAGE_URL = re.compile(r"https://app\.notion\.com/p/[0-9a-f]{32}")


def lint_page(name: str, md: str, assets: set[str]) -> list[str]:
    err = []
    body = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), md, flags=re.S)  # コードの欄は対象外
    text = re.sub(r"\$\$.*?\$\$", lambda m: "\n" * m.group(0).count("\n"), body, flags=re.S)  # 数式も対象外（行番号は保つ）
    for i, line in enumerate(text.splitlines(), 1):
        where = f"{name}:{i}"
        if "{{" in line or "}}" in line:
            err.append(f"{where}: 部品が変換されずに残っている → {line.strip()[:60]}")
        if "**" in line:
            err.append(f"{where}: 太字 ** が残っている → {line.strip()[:60]}")
        if re.match(r"^\s*- \[[ xX]\] ", line):
            err.append(f"{where}: 教材にチェック欄（- [ ]）がある。個人の状態が教材に残る（□ の箇条書きにする）")
        if "<sup>" in line:
            err.append(f"{where}: <sup> は Notion で消える（ʳ や ² を使う）")
        if line.startswith("|") and line.rstrip().endswith("|"):
            cols = line.strip().strip("|").count("|") + 1
            if cols > MAX_COLS:
                err.append(f"{where}: 表が {cols} 列（{MAX_COLS} 列まで）")
    for tag in TAGS:
        opened = len(re.findall(rf"<{tag}[\s>]", body))
        closed = body.count(f"</{tag}>") + len(re.findall(rf"<{tag}[^>]*/>", body))
        if opened != closed:
            err.append(f"{name}: <{tag}> の開き {opened}・閉じ {closed} が合わない")
    if body.count("$$") % 2:
        err.append(f"{name}: $$ が対になっていない")
    for aid in ASSET.findall(md):
        if aid not in assets:
            err.append(f"{name}: 素材 {aid} が図の一覧にもラボの版にもない")
    for url in MENTION.findall(md):
        if not PAGE_URL.fullmatch(url):
            err.append(f"{name}: メンションの URL が不正 {url}")
    return err
