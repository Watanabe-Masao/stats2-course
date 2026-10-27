# このリポジトリでの作業ルール

統計検定2級の教材の原本。利用者（渡辺さん）は iPhone の Notion で読む。文章はすべて日本語、です・ます調ではなく常体。

## 守ること

1. **原本だけを編集する**。Notion のページ本文を直接直さない。直したら `python3 build/build.py` で生成し、生成物で Notion を更新する。
2. **ID を変えない・消さない**。不要になった問題は `retired: true` を付けて残す（個人の解答記録が ID を参照している）。
3. **同じことを2か所に書かない**。段階名・アイコン・力・説明の型などは `content/*.yaml` から `{{...}}` で呼ぶ。
4. **個人データを入れない**。学習記録・得点・回答は Notion の個人用ルートに置く。
5. **数値は検算式を書く**。問題には `checks`、本文の数値は unit.yaml の `checks` に書き、build が通ってから公開する。
6. **スマホ前提**。表は2〜3列まで。冒頭は「ナビ＋ゴール＋タブ」だけ。説明はガイドへ。

## 本文の記法（content/units/*/S*.md）

| 書き方 | 意味 |
| --- | --- |
| `::: task` 〜 `:::` | 問題文の枠（他に ask・key・summary・pattern・warn・info） |
| `::: toggle 題名` 〜 `:::` | 開閉する欄（答えなど） |
| `{{problem:Q-U09-001}}` | 問題を差し込む（番号・難度・答えの開閉は自動） |
| `{{lab:LAB-count}}` | ラボを埋め込む |
| `{{fig:FIG-U03-population}}` | 図を入れる（説明文は content/assets.yaml） |
| `{{ref:REF-PQ-DB}}` | 旧版の問題集などへのリンク（shared.yaml の refs） |
| `{{unit:U14}}` `{{term:TERM-perm}}` | 単元・用語へのリンク（ID で書く。番号や名前を直接書かない） |
| `{{power:P3}}` `{{icon:lab}}` `{{stage:S2}}` | 力・補助・段階の印 |
| `{{shared:explain_pattern}}` | 共通文言 |
| `^ 文` | 灰色の補足行 |
| `**太字**` `$$数式$$` 表・リスト | そのまま |

## Notion への公開手順

1. `python3 build/build.py`
2. `python3 build/publish_prep.py <ID>` で必要な素材（図・ラボ）を一覧し、それぞれ Notion にアップロード（create-attachment、content にファイル全文）。同じアップロード ID は1ページ内で何度でも埋め込める。
3. `{"素材ID": "file-upload://…"}` の JSON を作り、`python3 build/publish_prep.py <ID> <json>` で `out/notion/<ID>.publish.md` を作って、`publish/notion.yaml` のページへ replace_content。
4. 移行した単元は `python3 build/audit.py <ID>` で旧版との欠落がないことを確かめる（落とす項目は migration/waivers に理由を書く）。
5. 新しいページを作ったら、そのページ ID を `publish/notion.yaml` に書いてコミットする。

入口ページ（root.md）の子ページは `<page url>` ブロックのまま置く（mention に変えると子ページが消えるため Notion が拒否する）。

個人用の学習記録（publish/notion.yaml の personal_root）：解答記録・到達記録・学習ログの3つのDB。問題は「問題ID」の文字列で指す。教材の生成物から個人データを読み書きしない。

Notion の記法の注意：`<sup>` は消える（ʳ や ² を使う）。メンションは `<mention url="https://app.notion.com/p/ID" />`。
