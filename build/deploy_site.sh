#!/usr/bin/env bash
# 公開サイト（ラボ）を、公開用リポジトリの手元の複製へ写して push する。
# 使い方: build/deploy_site.sh <公開用リポジトリの手元のパス>
# 先に build/check_all.sh を通すこと。out/site/ の中身だけが公開される（原本・答えは出ない）。
set -euo pipefail
cd "$(dirname "$0")/.."
dest="${1:?公開用リポジトリの手元のパスを指定する}"
[ -d "$dest/.git" ] || { echo "❌ $dest は git の作業フォルダではない"; exit 1; }
[ -f out/site/index.html ] || { echo "❌ out/site がない（python3 build/build.py を先に）"; exit 1; }
rsync -a --delete --exclude .git out/site/ "$dest/"
cd "$dest"
git add -A
if git diff --cached --quiet; then echo "変更なし"; exit 0; fi
git commit -q -m "ラボを更新（stats2-course $(git -C "$OLDPWD" rev-parse --short HEAD)）"
git push -q
echo "✅ 公開サイトを更新した"
