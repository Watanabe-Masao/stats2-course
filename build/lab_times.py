#!/usr/bin/env python3
"""ラボの版ごとの時間の記録（tools/lab_times.json）を GitHub の実行のログから作り直す（#129）。

使い方: python3 build/lab_times.py <実行の ID> [<実行の ID> …]
  - 各実行の labs のジョブのログから、tools/test_labs.js が出す「⏱ 秒 版の名前」の行を集める
  - 同じ版が複数の実行にあれば平均する（機械の速さの差をならすため、2回以上の実行を渡すとよい）
  - 今の記録にあって、渡した実行に出なかった版は消す（なくなった版を残さない）
  - tools/lab_shard.js がこの記録で SHARD=k/n の組を時間でそろえる。記録のない版は中央値で見積もるので、
    版が増えただけなら作り直さなくても組は壊れない（ずれが大きくなったら作り直す）
  - 実行の ID は `gh api "repos/{owner}/{repo}/actions/runs?status=success&per_page=5"` で調べる
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "lab_times.json")
REPO = "Watanabe-Masao/stats2-course"
LINE = re.compile(r"⏱ (\d+(?:\.\d+)?) (\S+)\s*$")


def gh(path: str) -> str:
    return subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout


def parse(log: str) -> dict[str, float]:
    """ログから 版の名前 → 秒。"""
    times: dict[str, float] = {}
    for line in log.splitlines():
        if m := LINE.search(line):
            times[m.group(2)] = float(m.group(1))
    return times


def collect(run_ids: list[str]) -> dict[str, list[float]]:
    seen: dict[str, list[float]] = {}
    for run in run_ids:
        jobs = json.loads(gh(f"repos/{REPO}/actions/runs/{run}/jobs?per_page=100"))["jobs"]
        labs = [j for j in jobs if j["name"].startswith("labs")]
        if not labs:
            raise SystemExit(f"実行 {run} に labs のジョブがない")
        for job in labs:
            if job["conclusion"] != "success":
                raise SystemExit(f"実行 {run} の {job['name']} が {job['conclusion']}（成功した実行だけを使う）")
            found = parse(gh(f"repos/{REPO}/actions/jobs/{job['id']}/logs"))
            if not found:
                raise SystemExit(f"実行 {run} の {job['name']} のログに ⏱ の行がない（時間を出す前の版の実行？）")
            for key, sec in found.items():
                seen.setdefault(key, []).append(sec)
    return seen


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(__doc__)
    seen = collect(argv)
    times = {k: round(sum(v) / len(v), 1) for k, v in sorted(seen.items())}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(times, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    print(f"✅ {len(times)} 版の時間（合計 {sum(times.values()):.0f}秒・実行 {len(argv)} 回の平均）→ tools/lab_times.json")


if __name__ == "__main__":
    main(sys.argv[1:])
