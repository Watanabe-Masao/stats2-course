#!/usr/bin/env bash
# 教材の生成物（out/site/net/stats2.json）を見本の代わりに入れて、知識ネットワークの画面のテストを走らせる（#483 の C。渡辺さん 2026-11-17）。
# 確かめる対象：教材の概念・関係・構造を変えた PR で、公開中の画面（knowledge-net の main）が新しいデータを読み、描け、画面のテストが通ること。
# 想定する故障：画面の型が新しいデータを拒む・画面のテストが語を数や名前で指していて落ちる（#302・#475 の公開のあと、knowledge-net #271 で起きた）。
# 見つけ方：knowledge-net の単体テスト（型・読み込み・ネットワークの計算）と、概念・関係のデータを読む画面のテストの一部を chromium で走らせる。
#   全部の画面のテストは時間がかかる（viewer だけで約6分）ので、まず概念・関係・見出し・分類・条件・主張のテストに絞る。足りなければ広げる。
# 既存との違い：knowledge-net の CI は、取り込んだ見本（公開済みの教材）で走る。ここは、まだ公開していない教材のブランチの生成物で走る。
set -euo pipefail
cd "$(dirname "$0")/.."
KN="${KN_DIR:-.kn}"
[ -f out/site/net/stats2.json ] || { echo "❌ out/site/net/stats2.json がない（python3 build/build.py を先に）"; exit 1; }
if [ ! -d "$KN/.git" ]; then
  git clone --quiet --depth 1 https://github.com/Watanabe-Masao/knowledge-net "$KN"
fi
echo "画面：knowledge-net@$(git -C "$KN" rev-parse --short HEAD)（公開中の main）"
cp out/site/net/stats2.json "$KN/public/sample/stats2.json"
cd "$KN"
[ -d node_modules ] || npm ci --silent
npx playwright install chromium >/dev/null
npm run gen --silent
npx vitest run tests/unit
npm run build --silent >/dev/null
SPECS="${SCREEN_SPECS:-heading category-list concept-page claims conditions relation-open relmap-pairs v2-read map-icons}"
npx playwright test --project=chromium $(for s in $SPECS; do printf 'tests/e2e/%s.spec.ts ' "$s"; done)
echo "✅ 画面のテスト OK"
