# stats2-course

統計検定2級の教材の**原本**。Notionのページやアプリの画面は、ここから生成する表示物。

## 設計の約束

| 約束 | 中身 |
| --- | --- |
| 1変更理由＝1か所 | 段階・力・共通文言・部品の見た目は、それぞれ1つのファイルにだけ書く |
| IDは変えない | 単元 `U09`、問題 `Q-U09-012`、ラボ `LAB-count`、用語 `TERM-perm`。参照はすべてIDで書く |
| 生成物を手で直さない | Notionのページを直したいときは原本を直して作り直す |
| 教材と個人データを分ける | このリポジトリには学習記録・得点・個人名を入れない |
| 数値は検算してから出す | 問題と本文の数値は `checks` に検算式を書き、build で自動確認する |

## 構成

```
content/
  stages.yaml        6段階（初学・復習・応用・転用・発展・創造）の定義
  powers.yaml        3つの力（式を読む・計算する・言葉にする）
  shared.yaml        共通の文言・領域・出典
  terms.yaml         用語
  guide.md           学び方ガイド（生成元）
  units/index.yaml   全単元の一覧と移行状況
  units/U09/         unit.yaml（属性・ゴール・検算）＋ S1.md〜S6.md（段階ごとの本文）
  problems/U09.yaml  問題（ID・段階・力・形式・答え・誤答の理由・検算）
tools/count_lab/     数え方ラボ（HTML）と tool.yaml
templates/notion/    Notion表示の見た目（部品の色・アイコン・ラベル）
build/               検証・検算・生成のプログラム
publish/notion.yaml  原本ID → NotionページID の対応表（公開先ごとに用意）
out/                 生成物（git管理外）
```

## 使い方

```bash
python3 build/build.py --check   # 検証と検算だけ
python3 build/build.py           # 生成（out/notion/*.md）
```

本文の書き方は `CLAUDE.md` の「本文の記法」を参照。
