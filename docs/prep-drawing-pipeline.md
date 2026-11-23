# 描画の流れを1つの部品にそろえる（決めるための準備。#582）

データの取得から描画までの流れを整理する（渡辺さん 2026-11-23）。今の流れ・課題・案・移す順・影響する範囲・決めることを書く。数は 2026-11-23 の main の原本と生成物から数え、別のエージェントが自分のコマンドで数え直して確かめた（約 35 件。食い違い5件を直した）。

前の決定：#188 の 01b（渡辺さん 2026-11-04）「図の元は教材の設定のまま（図の ID も変えない）、描く部品は math-lab の1つ。公開サイトはその部品で描き、Notion の画像も build が node で同じ部品から SVG にする（式の TeX と同じやり方）」。この文書はその続きで、新しい方針を足すものではない。

## 1. 今の流れ

### 1.1 データの取得
- 原本（content/）を build（build/build.py）が検査し、通ったものだけを書き出す。書き出すのは4つ。
  - 静止図の SVG（out/fig）
  - 公開データ（out/site/net/stats2.json）
  - ラボの HTML（out/site・out/labs）
  - Notion の本文（out/notion/*.md）
- 公開サイト（stats2-labs）は out/site を置くだけ（build/deploy_site.sh）。
- 画面（knowledge-net）は、教材の一覧（public/courses.json）から公開データを取りにいく。使うたびにサーバーへ新しいかを確かめる（`cache: "no-cache"`。src/data.ts）。原本は読まない（knowledge-net の守ること 4）。
- Notion は本文の中で、公開サイトの図（fig/…svg）とラボ（?p=…）の URL を指す。

### 1.2 描く仕組みは3つ

| 仕組み | 描くもの | 出る所 |
| --- | --- | --- |
| figures.py＋svgkit（Python） | 静止図 28 型・155 枚（問題 51・単元 40・解説の段 64）。ほかに設定から作っていない SVG 2枚（assets/figures/c03.svg は手描き、c04_scale.svg は tools/figure-src/make_u04.py で一度だけ作った物） | Notion（92 枚を参照。設定から作っていない2枚を含む）・画面（関係 44 本・概念 6 語の figures）・公開サイト |
| ラボ（tools/*_lab＋labkit。HTML と JS） | 33 本・826 版。解説付き再生（tour）もここで動く | Notion の埋め込み（URL 745 件）・公開サイト |
| math-lab（engine・ui。TypeScript） | 概念の図（chart。二項分布の1語）・関係の図（chart 4本：pair 3・normal 1）・解説と触る（play 65 件）・実験室・作業台 | 画面だけ |

数え方：
- 静止図：figures.specs の型を数えた。Notion：out/notion/*.md の fig/ の URL の重なりを除いた数。ラボの版：build の出力。play：公開データの labs のうち play があるもの。

### 1.3 そろえているもの・そろっていないもの
- 色：math-lab の tokens.json の写しから、ラボ（labkit の先頭）と静止図（svgkit）に入れている（#101・#107）。
- 乱数：math-lab の束の写し（docs/math-lab/random.js）をラボで使っている（#144）。
- 式：TeX は build が node で math-lab の束（docs/math-lab/formula.mjs）から作る（build/formula_tex.mjs。#118）。1つの部品から Python と画面の両方に出している、今ある唯一の例。
- 図の計算と形：3つの仕組みが別々に持つ。
  - 分布の確率：figures.py は Python の float（_pmf・_pdf）、ラボは各ラボの JS、画面は engine の modelPmf。
  - 棒の形・目盛り・強調：仕組みごとに別に作っている。

## 2. 課題

1. **同じ図を何通りにも作っている**。
   - 分布の棒は、静止図の dist（45 枚）・bars（15 枚）、ラボ（binom・pois・clt など）、画面の Bars で別々に描く。
   - 解説付き再生は、同じ段階データ（tour）から3つを作る。段ごとの静止図 64 枚（build/tour.py の figure_specs）・ラボの再生（labkit が tour を読む）・画面の play（build/network.py の play_of が tour.states で作る）。段ごとの静止図は、画面の関係から参照しているが、Notion の本文からは1枚も参照していない（tour.py の説明の「Notion で見える」と合っていない）。
   - 静止図とラボの数がずれないように、照合テスト（tools/test_labs.js）を持っている。これは、同じものを2回作っていることの費用。
2. **画面だけの図は Notion に出ない**。概念・関係の図（chart）は画面だけで描く。図を増やすほど、画面と Notion の見えるものがずれる（#577 の図の段）。
3. **01b の Notion の側に引き受け先がない**。2026-11-11 に R4 に回したが、R4（W1〜W5）は引き受けずに閉じた。roadmap・rollout にも書いていない。#577（問い・つまり）と同じ取りこぼしの型。
4. **設定から作っていない SVG が2枚残っている**（c03.svg は手描き、c04_scale.svg は一度だけスクリプトで作った物）。CLAUDE.md の「設定から作れない図を手で描かない」に合っていない。

## 3. 案：01b のとおり、描く部品を math-lab の1つにする

- math-lab に**描く関数**を置く。図の設定と数から、SVG の文字列を返す純粋な関数で、DOM と React を使わない。engine と同じ決まり（種つき乱数だけ・純粋関数）。
  - 画面の部品（React）は、この関数の結果を包むだけにする。
  - 触る・動く部分（つまみ・再生）は部品の側に残す。静止の1枚は関数だけで描ける形にする。
- 教材は、式と同じ形で使う。
  - math-lab の束の写し（docs/math-lab/draw.mjs）を `python3 build/sync_schema.py --update` で取り込み、版を docs/sync-lock.json に固定する。
  - build が node で呼んで SVG を作る（build/draw_svg.mjs。build/formula_tex.mjs と同じ形）。
- 図の元は変えない。設定（unit.yaml の figures・問題の figure・概念と関係の chart）も図の ID も同じ。公開サイトの URL（fig/<ID>.svg）も変わらないので、Notion の本文は変わらない。変わるのは画像の中身だけ。
- 数は engine が出す。figures.py の確率の計算（_pmf・_pdf）は外し、照合テストで engine の値と比べる。検査の決まりは「確かめる」の独立性に合わせ、期待値は別の計算で作る。

## 4. 移す順（案）

| 段 | 中身 | 閉じる確かめ |
| --- | --- | --- |
| D0 | 描く関数の形を決め、dist（二項分布の棒）を1型だけ移す。build が node で SVG を作る道を通す | 同じ設定で画面と Notion の SVG が同じ。棒の高さが engine の値の比。iPhone で見本を見る |
| D1 | 離散の分布の棒：静止図の dist・bars と、概念の chart を超幾何・ポアソン・幾何・負の二項に広げる（#577 の段1） | 静止図の照合テストが engine の値で通る。概念のページに図が出る |
| D2 | 連続の曲線：正規・一様・指数・t・カイ二乗・F（#577 の段2） | 同上 |
| D3 | データの図：hist・scatter・boxplot・line など | 同上 |
| D4 | 残りの型と解説の段（段ごとの静止図 64 枚は Notion が参照していないので、画面の参照を play の段に替えれば外せる） | test_labs.js の静止図の照合を外せる |
| D5 | figures.py・svgkit の図の部分を外し、設定から作っていない2枚を設定から作る | build が Python で図を描かない |

- どの段も、画面（knowledge-net）を先に公開してから、教材の設定を変える（教材の CLAUDE.md「データの意味が変わる公開は、画面を先に公開する」）。
- ラボ（33 本・826 版）は範囲に入れない。各ラボが自分の描き方を持ち、移す量が大きい。D5 のあとに、ラボの役目（Notion の埋め込み）を残すかと一緒に、別の issue で決める。

## 5. 影響する範囲

| 所 | 変わるもの |
| --- | --- |
| math-lab（knowledge-net の中） | 描く関数を足す・Bars などを関数の上に作り直す・単体テスト |
| knowledge-net の画面 | 概念・関係の図を描く所（src/Detail.tsx・src/Relation.tsx）・型の chart の種類（kn-schema の改訂） |
| stats2-course の build | build/draw_svg.mjs を足す・figures.py の型を段ごとに外す・sync_schema の写しを1つ足す・照合テスト |
| 公開サイト・Notion | 画像の中身が変わる（URL は同じ）。Notion の本文は変わらない。画像の見え方を iPhone で確かめる |
| CI | build に node の実行が増える（式の TeX と同じく1回の呼び出しにまとめる） |

## 6. 決めること

**決定（渡辺さん 2026-11-23。#582）**：下の4つとも推奨のとおり。実装は 11/30 の判断のあとに D0 から始める。

1. **01b の方針を続けるか**：推奨は続ける（2026-11-04 の決定のまま）。この issue（#582）を、Notion の側の引き受け先にする。
2. **時期**：推奨は、この文書と issue は今、実装（D0 から）は 11/30 の判断のあと。D0 は build と math-lab の土台を変える構造の変更で、11/30 までの「品質を優先し、大きな構造の変更をしない」方針に当たる。#577 の図の段（D1・D2）も同じ時期にする。
3. **ラボを範囲に入れるか**：推奨は入れない（4 の終わり）。
4. **見た目が変わる図の確かめ方**：推奨は、段ごとに代表の図を数枚、画面と Notion で iPhone で見る。D0 の見本で、Notion の画像の大きさ・文字の大きさを決める。

## 7. まだ確かめていないこと
- 描く関数の形（静止の1枚を関数だけで描けるか）。今の Bars は React の部品で、関数の形に分けられるかはコードを読んで確かめていない。D0 で確かめる。
- node で SVG を作る時間。式の TeX（55 式。公開データでは写し2件を含めて 57 件）は1回の呼び出しで済んでいるが、図 155 枚での時間は測っていない。
- Notion が、同じ URL で中身の変わった画像を読み直すか（Notion の側で画像を覚えていると、古い図が出続ける）。出続けるなら、図の URL に版を付けるなどの手が要る。
- Notion が SVG の中の字体をどう表示するか。今の静止図と同じ字体の指定にすれば変わらない見込みだが、確かめていない。
