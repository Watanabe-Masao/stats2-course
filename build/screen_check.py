"""公開の前に、公開中の画面（knowledge-net の GitHub Pages）の型の改訂が、公開するデータの改訂以上かを確かめる（stats2-course #207）。

画面は知らない項目を無視して読む（教材ごと外さない）ので、データが新しくても表示は壊れない。ただ、新しい項目は画面が読むまで出ない。
教材の公開（deploy_site.sh）と画面の公開（Pages）は別々に走るので、画面の公開が遅れた・落ちた日に、それと気づかずに教材だけを進めないため止める。
画面を先に公開してから、もう一度 deploy_site.sh を走らせる。

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


def screen_revision() -> tuple[int, str]:
    """公開中の画面の型の改訂と、その公開のコミット"""
    for d in gh(f"repos/{REPO}/deployments?environment=github-pages&per_page=10"):
        st = gh(f"repos/{REPO}/deployments/{d['id']}/statuses")
        if st and st[0].get("state") == "success":
            f = gh(f"repos/{REPO}/contents/schema/kn-schema-v1.json?ref={d['sha']}")
            return json.loads(base64.b64decode(f["content"]))["x-revision"], d["sha"][:7]
    raise RuntimeError("成功した画面の公開が見つからない")


def check(data_rev: int, screen_rev: int) -> str | None:
    """止める理由（なければ None）"""
    if screen_rev < data_rev:
        return f"公開中の画面の型の改訂（{screen_rev}）が、公開するデータの改訂（{data_rev}）より古い。knowledge-net の画面を先に公開する"
    return None


def main() -> int:
    if os.environ.get("SKIP_SCREEN_CHECK") == "1":
        print("⚠ 画面の改訂の確認を飛ばした（SKIP_SCREEN_CHECK=1）")
        return 0
    data_rev = json.loads(DATA.read_text(encoding="utf-8")).get("schema_revision", 1)
    try:
        screen_rev, sha = screen_revision()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 公開中の画面の型の改訂を確かめられない（{e}）。GitHub に届くか確かめる")
        return 1
    why = check(data_rev, screen_rev)
    if why:
        print(f"❌ {why}（画面は knowledge-net@{sha}）")
        return 1
    print(f"✅ 公開中の画面（knowledge-net@{sha}・型の改訂 {screen_rev}）は、データの改訂 {data_rev} を読める")
    return 0


if __name__ == "__main__":
    sys.exit(main())
