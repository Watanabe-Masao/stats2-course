#!/usr/bin/env bash
# 公開サイト（ラボ）を、公開用リポジトリの手元の複製へ写して push する。
# 使い方: build/deploy_site.sh <公開用リポジトリの手元のパス>
# 先に build/check_all.sh を通すこと。out/site/ の中身だけが公開される（原本・答えは出ない）。
set -euo pipefail
cd "$(dirname "$0")/.."
dest="${1:?公開用リポジトリの手元のパスを指定する}"
[ -d "$dest/.git" ] || { echo "❌ $dest は git の作業フォルダではない"; exit 1; }
[ -f out/site/index.html ] || { echo "❌ out/site がない（python3 build/build.py を先に）"; exit 1; }
# 公開の前の検査（#118 M9）：公開する代表の式は、今の版でレビュー済みでなければ止める
python3 build/formulas.py --publish-check
# 公開中の画面（knowledge-net）の型の改訂が、データの改訂以上か（#207）。画面の公開が遅れた日に教材だけを進めない
python3 build/screen_check.py
find "$dest" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
cp -a out/site/. "$dest/"
cd "$dest"
git add -A
if git diff --cached --quiet; then echo "変更なし"; exit 0; fi
# 付記（誰が公開したか）は、走らせる側が環境の変数で渡す（固定のセッションの URL を書かない）。例：PUBLISH_TRAILER="Co-Authored-By: …"
msg="ラボを更新（stats2-course $(git -C "$OLDPWD" rev-parse --short HEAD)）"
if [ -n "${PUBLISH_TRAILER:-}" ]; then git commit -q -m "$msg" -m "$PUBLISH_TRAILER"; else git commit -q -m "$msg"; fi
git push -q -u origin HEAD
echo "✅ 公開サイトを更新した"
