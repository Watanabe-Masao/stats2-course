"""公開の前に、公開中の画面（knowledge-net の GitHub Pages）の型の改訂が、公開するデータの改訂以上かを確かめる（stats2-course #207）。

画面は知らない項目を無視して読む（教材ごと外さない）ので、データが新しくても表示は壊れない。ただ、新しい項目は画面が読むまで出ない。
教材の公開（deploy_site.sh）と画面の公開（Pages）は別々に走るので、画面の公開が遅れた・落ちた日に、それと気づかずに教材だけを進めないため止める。
画面を先に公開してから、もう一度 deploy_site.sh を走らせる。

意味の確かめ（#293）：型の改訂が同じでも、画面がデータの種類を描けるとは限らない（2026-11-09、⑤ の種類を描けない画面のまま確率分布を公開した）。
公開中の画面の src/screen-kinds.json（描ける ⑤ の種類と読み替え先）を読み、データの関係の type（⑤ の種類）が全部そこにあるかも見る。

確かめ方：GitHub の deployments（environment＝github-pages）で、いちばん新しい成功した公開のコミットを引き、その版の型の x-revision を読む。
GitHub に届かないときも止める（確かめられないまま公開しない）。どうしても進めるときだけ SKIP_SCREEN_CHECK=1 で飛ばす。
"""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "Watanabe-Masao/knowledge-net"
DATA = Path(__file__).resolve().parent.parent / "out/site/net/stats2.json"


def gh(path: str):
    return json.loads(subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout)


# 型は芯と実験室の拡張の2つ（#211）。データの項目の名前 → 型のファイル。芯の改訂は芯の版ごとに数える（v2 は改訂1から。#264）
SCHEMAS = {"schema_revision": ("芯", "schema/kn-schema-v2.json"), "experiment_revision": ("実験室の拡張", "schema/kn-experiment-v1.json")}
CORE = {2: "schema/kn-schema-v2.json"}   # v1 は M7 で外した（#267）


def schemas_for(version: int) -> dict:
    """データの芯の版（version）に合わせた型のファイル。v2 の改訂を v1 の型の改訂と比べない"""
    return {**SCHEMAS, "schema_revision": ("芯", CORE[version])}


def screen_revision(schemas: dict = SCHEMAS) -> tuple[dict[str, int], str]:
    """公開中の画面の型の改訂（芯・拡張）と、その公開のコミット。型がまだない版は 0（その版の芯を読めない）"""
    for d in gh(f"repos/{REPO}/deployments?environment=github-pages&per_page=10"):
        st = gh(f"repos/{REPO}/deployments/{d['id']}/statuses")
        if st and st[0].get("state") == "success":
            revs = {}
            for key, (_, path) in schemas.items():
                try:
                    f = gh(f"repos/{REPO}/contents/{path}?ref={d['sha']}")
                    revs[key] = json.loads(base64.b64decode(f["content"]))["x-revision"]
                except subprocess.CalledProcessError:
                    revs[key] = 0
            return revs, d["sha"]
    raise RuntimeError("成功した画面の公開が見つからない")


KINDS_FILE = "src/screen-kinds.json"


def screen_kinds(sha: str) -> set[str]:
    """公開中の画面が描ける ⑤ の種類。ファイルがない版は空（⑤ の種類を1つも描けない）"""
    try:
        f = gh(f"repos/{REPO}/contents/{KINDS_FILE}?ref={sha}")
        return set(json.loads(base64.b64decode(f["content"])).get("v2_to_screen", {}))
    except subprocess.CalledProcessError:
        return set()


def kinds_check(data: dict, drawable: set[str]) -> str | None:
    """データの関係の ⑤ の種類（type）のうち、画面が描けないもの（移していない行の legacy_type は画面が v1 の種類で描く）"""
    used = {r["type"] for r in data.get("relations", []) if r.get("type")}
    missing = sorted(used - drawable)
    if missing:
        return f"公開中の画面は ⑤ の種類 {'・'.join(missing)} を描けない。knowledge-net の画面（src/screen-kinds.json）を先に対応させて公開する"
    return None


def check(data_revs: dict[str, int], screen_revs: dict[str, int], schemas: dict = SCHEMAS) -> str | None:
    """止める理由（なければ None）。データに書いていない型（実験室のない教材の拡張）は見ない"""
    for key, (name, _) in schemas.items():
        if key in data_revs and screen_revs.get(key, 0) < data_revs[key]:
            return f"公開中の画面の{name}の型の改訂（{screen_revs.get(key, 0)}）が、公開するデータの改訂（{data_revs[key]}）より古い。knowledge-net の画面を先に公開する"
    return None


def main() -> int:
    if os.environ.get("SKIP_SCREEN_CHECK") == "1":
        print("⚠ 画面の改訂の確認を飛ばした（SKIP_SCREEN_CHECK=1）")
        return 0
    data = json.loads(DATA.read_text(encoding="utf-8"))
    schemas = schemas_for(data.get("version", 1))
    data_rev = {k: data.get(k, 1) for k in schemas if k in data or k == "schema_revision"}
    try:
        screen_rev, sha = screen_revision(schemas)
    except Exception as e:  # noqa: BLE001
        print(f"❌ 公開中の画面の型の改訂を確かめられない（{e}）。GitHub に届くか確かめる")
        return 1
    why = check(data_rev, screen_rev, schemas)
    if not why:
        try:
            why = kinds_check(data, screen_kinds(sha))
        except Exception as e:  # noqa: BLE001
            print(f"❌ 公開中の画面が描ける種類を確かめられない（{e}）")
            return 1
    if why:
        print(f"❌ {why}（画面は knowledge-net@{sha[:7]}）")
        return 1
    print(f"✅ 公開中の画面（knowledge-net@{sha[:7]}・型の改訂 {screen_rev}）は、データの改訂 {data_rev} を読み、⑤ の種類を描ける")
    return 0


if __name__ == "__main__":
    sys.exit(main())
