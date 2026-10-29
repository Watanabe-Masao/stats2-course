#!/usr/bin/env bash
# 公開・コミットの前に全部を確かめる。どれか1つでも失敗したら止まる。
#   1. build/ の単体テスト（間違いを入れたら止まることの確認）
#   2. 原本の検証・検算 → 生成 → 生成物の検査
#   3. 旧版との突き合わせ（migration/old にある単元）
#   4. ラボ：全部の版（エラー・380px・予想の前は結果が隠れる・予想の答え＝ラボの値）と、ラボごとの数値の検算
# GitHub では分けて並行に走らせる（.github/workflows/check.yml）：
#   PART=base … 1〜3 とラボの検算（check.js）
#   PART=labs … 生成とラボの版（SHARD=k/n でその組だけ）
#   何も付けなければ全部（手元で原因を調べるとき）
set -euo pipefail
cd "$(dirname "$0")/.."
PART="${PART:-all}"
case "$PART" in all|base|labs) ;; *) echo "❌ PART は all・base・labs"; exit 1;; esac
if [ "$PART" != labs ]; then
  echo "== 1. 単体テスト"; python3 -m unittest discover -s tests -q
  echo "== 1b. 知識ネットワークの型の写し"; python3 build/sync_schema.py
fi
echo "== 2. 生成"; python3 build/build.py
if [ "$PART" != labs ]; then
  echo "== 3. 旧版との突き合わせ"
  for f in migration/old/*.md; do python3 build/audit.py "$(basename "$f" .md)"; done
fi
if [ "$PART" != base ]; then
  echo "== 4. ラボの版${SHARD:+（組 $SHARD）}"; node tools/test_labs.js
fi
if [ "$PART" != labs ]; then
  echo "== 4b. ラボの検算"
  for c in tools/*/check.js; do node "$c" | tail -1; done
fi
case "$PART" in all) echo "✅ 全部 OK";; *) echo "✅ ${PART}${SHARD:+ $SHARD} OK";; esac
