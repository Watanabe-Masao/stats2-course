# 旧版（Notion）の削除前の控え

旧版を削除する前に、復元に要るデータと関係を保存する所（publish/legacy.yaml の削除の判定 ⑤「復元できる」）。

- 中身は Notion の fetch・query の返り値そのまま（トランスクリプトから機械で切り出し、手で写していない）。
- 個人の記録は入れない（入っていないことを確かめてから置く）。
- Notion のゴミ箱（削除から一定期間は戻せる）とは別の、長く残る控え。

| フォルダ | 旧版 | 中身 |
| --- | --- | --- |
| LEG-pq-db/ | 本番形式問題（DB・15行） | database.json（DB の型・ビュー）・rows.json（15行の属性。状態は全部「未着手」、解いた回数0）・406…page.json（各行のページ本文） |
| LEG-confusion/ | 混同しやすい概念｜図で比べる（ページ） | page.json（本文。図の13枚は notion-file-block の参照）。図の SVG そのものはリポジトリの assets/figures/confusion/ にある（01_sd_se.svg〜13_simple_multi.svg） |
| LEG-reference/ | 公式・用語リファレンス（ページ） | page.json（本文・数式・タブ・表）。埋め込みの HTML 9件（sim_stage1・sim_stage2・s3〜s8・sim_all30）は Notion のファイルで、この環境から取り出せず、残さないと決めた（渡辺さん 2026-11-18。今は各単元のラボで代わる） |
| LEG-term-db/ | 統計用語辞典（DB・114行） | database.json（DB の型・ビュー）・rows.json（114行の属性。各行のページ本文は空）。「導入状態」は114行すべて「未導入」で、個人の記録はない |

