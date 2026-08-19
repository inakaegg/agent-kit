# Native UI

## 調査

- 対象OS、デバイス、UI framework、scene／windowモデルを確認する。
- 既存のデザイントークン、共通View、OS標準パターン、最小対応サイズを優先する。
- 対象プラットフォームの標準コントロール、ナビゲーション、設定、メニュー、キーボード操作を確認する。

## 実装

- 対象OSの標準構造とコントロールを優先する。
- macOSではtoolbar、sidebar、inspector、Settings、menu、keyboard shortcutなどデスクトップの慣習を尊重し、モバイル画面を拡大した構成にしない。
- iOS等ではsafe area、Dynamic Type、orientation、touch target、navigationの慣習を尊重する。
- 同じ役割のコントロールはcontrol size、style、alignment、minimum-width policyを統一する。
- 既存トークンがある場合、局所的なframe、padding、corner radius、font値を増やさない。
- 過剰なカード、装飾コンテナ、独自コントロールでOS標準の階層を覆わない。
- 非同期更新、sidebar切替、sheet、popover、window resizeで本文、選択、focus位置を不用意に動かさない。

## 実アプリ確認

Browserをネイティブアプリの代替にしない。実アプリをbuild・launchし、GUI操作またはスクリーンショットが可能なツールを使う。利用できなければ、ユーザー提供の実画面画像を直接確認する。

デスクトップでは関連する次を確認する。

- 最小対応ウインドウ
- 通常作業サイズ
- 幅広サイズ
- resize途中とfullscreen（関連する場合）

モバイルでは関連する次を確認する。

- 対応する最小・標準デバイス
- portrait、landscape
- safe areaとkeyboard表示
- Dynamic Typeの拡大

共通して次を確認する。

- Light、Dark、高コントラスト（対応する場合）
- 長い日本語ラベル、empty、loading、error、disabled、populated
- clipping、overlap、優先度、整列、密度
- keyboard、focus、VoiceOver等に必要なラベル
- toolbar、sidebar、menu、sheet、popover、window復元
- 権限ダイアログ後や非同期更新後の状態

実画面またはスクリーンショットを直接確認できなければ `VISUAL_QA_UNVERIFIED` とする。
