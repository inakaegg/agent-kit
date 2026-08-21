---
name: ui-verification
description: >-
  Use when changing or auditing visible UI in web・native apps: layout / components / style /
  interaction / navigation / loading・error・empty states. Japanese cues: 「UI確認」「実画面で検証」「画面崩れ」.
---

# UI Verification

本SkillはUI検証の正本である。設計・実装まで含む一貫したUI作業では `$ui-quality` を
使い、その検証段階として本Skillの規定（起動経路、検証matrix、証跡）を適用する。

## 使用条件

- layout、component、style、interaction、navigation、loading/error/empty stateを変更する
- screenshot、reference image、design token、visual consistencyが要求される
- responsive、keyboard、focus、accessibility、scroll、async updateが関係する

## 1. 実装前brief

短く固定する。

```markdown
## UI brief
- 対象surface: Web / macOS / iOS / CLI TUI / その他
- 主な利用者とtask:
- 主要action:
- 視覚階層:
- 対象size / theme / input method:
- 必須state: normal / long / loading / success / error / empty / disabled
- 既存token・component・reference:
- 実画面の起動・検証経路:
```

各screenまたはvisual regionの主要actionは原則1つにする。既存design systemを唯一の基準として再利用し、並行する体系を増やさない。

## 2. 実装

- 既存component、token、spacing、typography、interaction patternに合わせる。
- 1回限りのvalueで既存tokenを上書きしない。
- stateごとにlayoutへ影響してよい範囲を明確にする。
- async updateで本文、page、scroll、selection、focusが意図せず変わらないようにする。
- dynamic layoutは表示mode、page reset、layout calculation、state transitionをtestする。
- 並列作業ではUI sourceのimplementation ownerを1人に限定し、他agentはread-only reviewを基本とする。

## 3. 実画面を起動する

- Webでは、project付属のUI/E2E command、project dependency、local/global Playwright、installed browser、browser/DevTools系toolの順に、安全に使える実行経路を確認する。共有browserが利用できないことだけを理由に打ち切らない。
- Playwrightと対応browserが利用可能なら、必ず実行する。自動install、package追加、browser downloadが必要な場合は、network、容量、repository変更の権限境界に従う。
- 変更したinteractionは、開始状態から利用者操作と結果までを実際に通す。hoverなら対象からcontrolへのpointer移動、double clickならnative event列、keyboard/touchなら対象input methodを再現する。静止時のvisibility、bounding box、hit testだけで操作成功を代替しない。
- native UIはnative app、simulator、preview等を使い、browser表示で代用しない。
- userが特定browser・device・surfaceを指定した場合は優先する。
- server codeを変更した場合は、hot reload反映またはprocess再起動を確認する。既存portを使うならPID、start time、commandを確認する。
- route変更ではtrailing slash、deep link、reloadも必要に応じて確認する。

## 4. 検証matrix

最低限：

| 軸 | 例 |
|---|---|
| size | narrow / default / wide |
| content | empty / normal / long / overflow |
| state | loading / success / error / disabled |
| theme | projectがsupportするtheme |
| input | mouse / keyboard / touch / screen reader相当 |
| lifecycle | first load / update / retry / navigation back |

projectに該当しない軸は除外してよいが、除外理由を示す。

## 5. visual QA loop

```text
render
→ screenshotまたは画面を直接確認
→ blocking defectを列挙
→ 最小修正
→ 再render
→ interaction確認
→ targeted/full gate
```

source、DOM dimension、build成功だけでvisual合格としない。
Webのinteraction変更は、screenshot取得だけで終了せず、変更した操作列を自動操作して結果をassertする。

## 6. blocking defect

- clip、overlap、意図しないhorizontal scroll
- 同格controlの不整合
- primary actionが不明瞭
- 読めないcontrast、font、line length
- 操作を妨げる空白または過剰なnest
- keyboard、focus、label、accessible nameの欠落
- long text、localization、dynamic contentでcollapseする
- loading/error時に操作不能またはstateがstaleになる
- async updateでscroll・selection・pageが勝手に変わる

## 7. 証跡

- 起動commandとURL/surface
- 確認したsize・state・theme
- screenshot/recording path
- automated UI/E2E結果
- manual interaction結果
- 未確認surface

すべての安全な経路を試しても実画面を確認できなければ、試したproject command、Playwright、browserと各失敗結果を証跡へ残し、最終報告へ正確に `VISUAL_QA_UNVERIFIED` と記載する。「UI完成」「視覚監査合格」と表現しない。未確認でもcommit自体を禁止しないが、riskを明記する。
