---
name: architecture-diagram
description: >-
  Use when a README / SPEC / design doc needs an architecture or flow diagram: system /
  service / cloud architecture with official icons (AWS / GCP / Azure / k8s / on-prem / SaaS /
  languages / generic), deploy paths, request flows,
  or when an existing diagram is unreadable (icons too big, text too small, labels overlapping,
  too small on GitHub). Japanese cues: 「構成図」「アーキテクチャ図」「図を入れて」「図が読みづらい」
  「アイコンが大きい」「文字が小さい」「図がかぶる」「Mermaidで」「diagramsで」.
---

# Architecture Diagram

README と設計文書に入れる図を、コードから生成して保守できる形で作る。構成図（システム・サービス間・
クラウド・オンプレ）は公式アイコン付きの Diagram as Code（mingrammer/diagrams）、流れ・状態・
シーケンス・ER は Mermaid を使う。diagrams は AWS / GCP / Azure / k8s / オンプレ / SaaS /
プログラミング言語 / 汎用のアイコンを同梱しており、クラウド以外の構成図にも使う。

## 使用条件

- システム構成図、サービス間の構成、デプロイ経路、リクエストの流れを README / SPEC / docs へ入れる
- 既存の図が読みにくい（アイコンと文字の比率、ラベルの重なり、GitHub 上で小さい）
- 図の置き場と形式（PNG / SVG / Mermaid）を決める

## 1. 形式を決める

| 図の種類 | 道具 | 理由 |
|---|---|---|
| 構成図（システム・サービス間・クラウド・オンプレ）、デプロイ経路 | diagrams → SVG | 公式アイコン、クラスタの入れ子、配置の自由度 |
| シーケンス、状態遷移、ER、簡単な流れ | Mermaid | GitHub が描画し、ズーム操作も付く。アイコンは出ない |

完了判定: 図ごとに道具を決め、どの文書に置くかを決めた。正本は生成スクリプト（または Mermaid 本文）で、
画像を手で編集しない。

## 2. 環境を確かめる

```
which dot || brew install graphviz      # macOS。他 OS は各パッケージ管理
uv run --with diagrams python -c "import diagrams"
```

完了判定: 両方が成功した。`brew install` は system 変更なので、実行前に一言断る。

## 3. テンプレートから書く

`assets/diagram_template.py` を `docs/diagrams/<name>.py` へコピーして書き換える。テンプレートの
`svc()` は、アイコン・タイトル・補足行を Graphviz の HTML ラベルに入れる。diagrams 既定の
固定サイズノードを使わないのは、文字を大きくすると隣と重なるため（`references/pitfalls.md`）。

- 構成図は `direction="TB"`、経路図は `"LR"` から始める
- 「後回し」「将来」の群は破線クラスタにし、invisible edge で最下段に固定する
- 課金・危険など強調したい経路は 1 色だけ使う
- ラベルは 1 行 12 文字程度。長いものは `\n` で折る

完了判定: `uv run --with diagrams python docs/diagrams/<name>.py` が SVG を出し、
`grep -c 'xlink:href="/' <svg>` が 0（アイコンが埋め込まれている）。

## 4. 目視で確かめる

SVG は画像ツールで直接読めないことがあるので、PNG に変換して見る（macOS: `qlmanage -t -s 1800 -o <dir> <svg>`）。
見る点: ラベルの重なり、矢印ラベルが別の矢印の近くに置かれていないか、後回し群の位置、文字とアイコンの比率。

完了判定: 重なりがない。矢印のラベルがその矢印の横にある。

## 5. 文書へ入れる

```html
<img src="docs/diagrams/<name>.svg" alt="<図の主張を一文で>" width="100%">
```

README のコマンド表へ再生成コマンドを載せる。GitHub の本文幅は約 830px で、それより広い図は縮小される。
遷移なしの拡大（ライトボックス）は README では作れないので、SVG にしてブラウザのズームに任せる。
図が 1,700px 幅程度なら、ズームで十分読める。

完了判定: README に図と再生成コマンドがあり、PNG の残骸がない。

## 誤った近道 → 正しい行動

- 文字が小さいので `fontsize` だけ上げる → 固定サイズノードでははみ出して重なる。`svc()`（HTML ラベル）を使う
- アイコンが大きいので `width` / `height` を縮める → 文字まで縮む。アイコンは `ICON_PX`、文字は `TITLE_PT` / `SUB_PT` で別に決める
- 図が大きいのでノードを減らす → 13 ノード程度は普通。一瞥で全体が見えるほうがよい。分割は読者が求めたときだけ
- PNG をコミットしてクリックで原寸表示 → ページ遷移する。SVG + ブラウザズームにする
- Mermaid で AWS 構成図 → GitHub ではアイコンが出ない。diagrams を使う
- 画像を手で直す → スクリプトを直して再生成する

## 停止条件

- レイアウト調整は 3 回まで。収まらなければ `direction` を変えるか、クラスタの分け方を変える
- Graphviz を入れられない環境では Mermaid へ切り替え、アイコン無しであることを報告する
