# 知識ネットワークの型（写し）

元はリポジトリ [knowledge-net](https://github.com/Watanabe-Masao/knowledge-net) の `schema/`（計画は同じリポジトリの `docs/plan.md`）。
ここは build が検査に使う写し。直すときは knowledge-net で直し、`python3 build/sync_schema.py --update` で取り込む。
写しが元と違うと `build/check_all.sh`（GitHub のチェック）が止まる。
