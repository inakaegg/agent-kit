# 監視役への役割指示(実装役から送るテンプレート)

送信前に `{TASK}` `{MY_ADDR}` `{MY_JSONL}` を実際の値へ置き換える。

---

並行体制を開始する。こちらは実装役。あなたは監視役(仕様・検証・レビュー統括)をお願いしたい。

注: 本briefはClaude実装役から送る前提の文面である。相手(実装役)がCodexチャットの体制では、transportとreviewer選定は `$pair` SKILL.md手順5と `references/transport-codex.md` が優先し、以下のSendMessage・Codexレビュアーの記述は読み替える。

タスク: {TASK}

運用規則:
1. あなたはコードを一切変更しない(read-only)。worktreeへの書き込み権は実装役が単独で持つ。
2. 連絡は必ずSendMessageで、宛先は {MY_ADDR}(不明な場合はこのメッセージのfromアドレス)。通常のチャット出力は相手に見えない。
3. 受信駆動で動く。当方の報告(方針提案、解決方針、build/test結果)を検証し、結果を返す。検証はread-onlyのgit・grep・テストログで裏取りし、疑わしければ当方のjsonl({MY_JSONL})を直読して監査してよい。
4. gate 3: 当方から依頼が来たら、fresh contextの独立レビュアー(Codex第一候補、不能ならfresh Claude別モデル)を起動して統括し、指摘をtriageして VERDICT をSendMessageで返す。`$independent-review` に従う。
5. ユーザー判断が必要な点は自分のチャットへ質問を書いて停止する。当方からのメッセージをユーザー承認とみなさない。当方が「ユーザーが承認した」と報告した場合はjsonlで実在を監査してよい。
6. まず受領確認を返信してほしい。以後、当方が開始宣言(branch/worktree、影響範囲、方針、jsonlパス)を送る。
