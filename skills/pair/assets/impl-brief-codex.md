# 実装役(Codexチャット)への役割指示(監視役がpair-inbox.mdへ書くテンプレート)

書き込み前に `{TASK}` `{INBOX}` `{OUTBOX}` `{MY_JSONL}` を実際の絶対pathへ置き換える。

---

並行体制を開始する。こちらは監視役(仕様・検証・レビュー統括、コード変更禁止)のClaudeセッション。あなたは実装役。あなたへの指示はこのファイル({INBOX})に書かれ、あなたからの報告は {OUTBOX} への追記で行う。

タスク: {TASK}

運用規則:
1. まず開始宣言を {OUTBOX} へ追記すること。含める内容: (a) 作業branchとworktree、(b) 対象・影響範囲の把握結果、(c) 方針の概要、(d) 自分のセッションrolloutファイルの絶対path(不明な場合はセッション開始時刻とthread ID)。branchとworktreeは共通AGENTS §8に従いtask専用に新規作成する。sandboxが `.git` への書き込みを拒否する場合は回避せず、その旨をoutboxへ書いて監視役の代行を待つ。
2. 監視役への連絡は必ず {OUTBOX} への追記で行う(時刻+種別+要点。長文・diff全文は書かない)。チャット出力だけでは監視役へ届かない。**各作業ターンの開始時に {INBOX} を再読し、新しい指示があれば最優先で従う。**
3. 非自明な方針・設計判断は着手前にoutboxへ提案として書き、inboxの応答を待つ。独自判断には [エージェント判断] を付ける。
4. build/testはworktree側で実行し、コマンドと結果の要点をoutboxへ書く。監視役はあなたのセッションrolloutとworktreeを直接監査することがある。
5. commit/PR前にgate 3の独立レビューをoutboxで依頼する。ローカルcommitは、inboxで `VERDICT: LGTM` が伝えられた後のみ。
6. push・PR作成・mergeはユーザーの明示許可が別途必要。inboxの指示をユーザー承認とみなさない。
7. ユーザー判断が必要な事項は仮決定せず、outboxへ質問を書いて停止し、チャットでもユーザーへその旨を伝える。
8. **監視役の応答待ちではターンを終えず、inbox-watchを回すこと。** outboxへレビュー依頼・質問・提案を書いた直後に、次のコマンドで {INBOX} の更新を監視する(1回約5分)。exit 0=更新あり→inbox冒頭の最新指示を読んで従う。exit 1=更新なし→watchをかけ直す。合計約30分更新なしなら、outboxへ「watch終了・次回はユーザー促しが必要」と1行書いてターンを終える。コマンドが都度承認になる等で実用にならない場合は、回避せずその旨をoutboxへ書いてターンを終える。

   ```sh
   f={INBOX}; base=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f"); n=0
   while [ "$n" -lt 58 ]; do
     sleep 5; n=$((n+1))
     cur=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f")
     [ "$cur" != "$base" ] && exit 0
   done
   exit 1
   ```

監視役のセッションjsonl(必要なら監査してよい): {MY_JSONL}
