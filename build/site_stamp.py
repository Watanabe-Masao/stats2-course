"""公開する out/site/ が、どのコミットから作られたかの印（#330）。

build.py が out/site/ を作ったあとに out/site.stamp を書き、deploy_site.sh が公開の前に照らす。
印は out/site/ の外に置く（公開しない）。
2026-11-10 に、作業中のブランチで build した out/site/ を公開してしまった（main から公開する決まりを、手順でしか守っていなかった）。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMP = ROOT / "out" / "site.stamp"


def _git(*args):
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def current():
    """今の作業フォルダの HEAD と、原本に書きかけの変更がないか（out/ は git の外）。"""
    status = _git("status", "--porcelain")
    return {"commit": _git("rev-parse", "HEAD"), "clean": status == ""}


def write_stamp():
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(json.dumps(current(), ensure_ascii=False), encoding="utf-8")


def stamp_errors(stamp, head, main, now_clean):
    """公開してよいかの理由のある止め。stamp は build の時の印、head は今の HEAD、main は origin/main、now_clean は今の作業フォルダ。"""
    errors = []
    if head != main:
        errors.append(f"今の HEAD（{(head or '?')[:7]}）が origin/main（{(main or '?')[:7]}）と違う。公開は main から")
    if not now_clean:
        errors.append("作業フォルダに書きかけの変更がある")
    if stamp is None:
        errors.append("out/site.stamp がない（python3 build/build.py を先に）")
    else:
        if stamp.get("commit") != head:
            errors.append(f"out/site は {(stamp.get('commit') or '?')[:7]} から作られた。今の HEAD（{(head or '?')[:7]}）で build し直す")
        if not stamp.get("clean"):
            errors.append("out/site は書きかけの変更がある作業フォルダで作られた")
    return errors


def main(argv):
    if "--check" not in argv:
        print("使い方: python3 build/site_stamp.py --check", file=sys.stderr)
        return 2
    _git("fetch", "-q", "origin", "main")
    stamp = json.loads(STAMP.read_text(encoding="utf-8")) if STAMP.exists() else None
    now = current()
    errors = stamp_errors(stamp, now["commit"], _git("rev-parse", "origin/main"), now["clean"])
    if errors:
        print("❌ 公開を止めた（#330）：\n" + "\n".join(f"  - {e}" for e in errors))
        return 1
    print(f"✅ out/site は main（{now['commit'][:7]}）から作られている")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
