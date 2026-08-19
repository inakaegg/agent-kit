---
name: ci-fix
description: Use when a GitHub Actions run or PR check is failing — the user pastes a failing Actions run / PR URL, or says "CI失敗", "CIがこけてる", "CI直して", "デプロイ失敗", "why did CI fail".
---

# CI Fix

赤いGitHub Actions runの原因を特定し、修正してgreenへ戻す。

## 入力

Actions run URL、PR URL/番号、または引数なし。引数なしなら現在のブランチから推定する：
`gh pr checks` で失敗チェックを探し、なければ `gh run list --branch <branch> --limit 5`。

## 手順

1. **失敗箇所の特定**
   - run URL → `gh run view <id> --log-failed`
   - PR → `gh pr checks <n>` で失敗チェックを特定し、そのrun idのログへ
2. **最初の本物のエラーを探す。** CIログのエラーは連鎖する。最後に出たエラーは大抵症状であり、失敗ステップ内で最も早い失敗をroot cause候補とする。
3. **分類してから直す**
   - lint / format / typecheck / build / test → まずローカルでリポジトリのscriptsを使って再現する。再現しない場合はCIとの環境差分（Node version、lockfile、OS）を比較する
   - 依存関係のドリフト（lockfile不整合、engines違い）→ コードではなく環境側を直す
   - 権限・デプロイ系（403、IAM、workload identity、secrets欠落）→ コードを触る前に設定・ロールを確認する。コード修正で押し切らない
   - flaky・インフラ（network timeout、runner障害）→ 修正より先に `gh run rerun <id> --failed` で再実行し、再現性を確認する
4. **修正**はPRブランチ上で行い、テスト追加→実装修正の順（共通AGENTS §4）に従う。commitは共通AGENTS §8に従う。
5. **pushはユーザーの明示依頼がある場合のみ**（共通AGENTS §3）。依頼がなければ、修正内容・ローカル検証結果・push後の確認手順を報告して止める。push済みの場合は `gh pr checks <n> --watch` でgreenを確認してから完了報告する。

## よくある誤り

| 誤り | 正しい対応 |
|---|---|
| 最後のエラーメッセージを直す | 失敗ステップ内の最初のエラーを探す |
| flakyをコード修正で潰そうとする | まず再実行して再現性を確認する |
| IAM・権限エラーをコードで回避する | 設定・ロール側を確認して報告する |
| ローカル再現なしで修正pushを繰り返す | 先にローカルで再現させてから直す |
