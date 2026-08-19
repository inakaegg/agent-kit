---
name: dep-upgrade-safe
description: Use when upgrading specific npm packages — the user names a package to bump, pastes upgrade-interactive / npm outdated rows, or asks "breaking changeある？", "安全にupdateできる？", "changelog確認して". Especially for major-version bumps.
---

# Safe Dependency Upgrade

特定パッケージの更新を、破壊的変更の調査を先に済ませてから適用する。

## 手順

1. **要求の解釈**: パッケージ名と現在→目標versionを特定し、major / minor / patchに分類する。package managerはlockfileから判定する（package-lock.json → npm、yarn.lock → yarn、pnpm-lock.yaml → pnpm）。
2. **利用実態の確認**: import / require箇所をgrepする。未使用なら更新ではなく削除を提案し、そのパッケージは終了。
3. **破壊的変更の調査**（majorは必須。挙動変更で知られるminorも）:
   - 目標versionのchangelog / GitHub Releases / migration guideを取得する
   - 各breaking changeについて、このコードベースが該当するかを使用箇所と突き合わせて判定する
   - 旧APIが残っている前提で書かない。目標versionのAPIシグネチャを正とする
   - changelogを取得できない場合は「未確認の推測」と明記し、安全とは判断しない
4. **適用**: package manager CLIで更新する（`npm install <pkg>@<ver>` など）。package.jsonを手編集しない。型エラーを `as` キャストや `eslint-disable` で黙らせず、目標versionのAPIに合わせて実装を直す。
5. **検証**: リポジトリに存在するscripts（lint / typecheck / build / test）を実行する。実行時にしか壊れない変更（設定形式、defaultの変更）は最小の実行経路でsmoke確認する。
6. **報告**: 更新したversion、対応したbreaking change、検証結果、未確認範囲を報告する。

## 判断基準

- 複数パッケージをまとめて更新しない。1つずつ適用・検証し、原因の切り分けを保つ。
- 一括のminor / patch更新やauditが目的なら、このskillの対象外として通常の依存更新作業で扱う。

## よくある誤り

| 誤り | 正しい対応 |
|---|---|
| 更新してからエラーで学ぶ | 先にchangelogで破壊的変更を列挙する |
| package.jsonの数字だけ書き換える | package manager CLIで更新しlockfileを整合させる |
| 型エラーをキャストで黙らせる | 目標versionのAPIに合わせて実装を直す |
| 未使用パッケージを律儀に更新する | 削除を提案する |
