# Codex相手のtransport — ファイルinbox/outbox + rollout監査

相手がCodex CLIの対話チャットの場合に、SKILL.md手順3〜6の**通信・発見・監視の手段だけ**を
置き換える手順。gate運用・reviewer選定・commit条件・briefの運用規則はSKILL.md手順5に従う。
本書のpath表記はskill root基準(例: `assets/impl-brief-codex.md`)。

Codex側はSendMessage/ListAgents/Monitorに参加できないため、通信は合意ファイル、
生存確認と監査はCodexセッションのrollout
(`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`。年/月/日の3階層)で行う。

## 前提と制約

- この体制の監視役はClaude(深い思考用モデル)、実装役がCodexチャット。逆は組めない。
- Codexはターン駆動で、ターンが終わるとユーザー入力なしに次ターンが始まらない。ただし
  **ターン継続中はshellのblocking watchでinboxを自分で監視できる**。実装役briefは
  「監視役の応答待ちではターンを終えず、inbox-watch(下記)を回す」ことを義務付けるため、
  通常は監視役がinboxへ書くだけで実装役が自動で動き出す。ユーザーへ「Codexチャットで
  『inbox確認して』と一言打ってください」と促すのは、**watchが切れているときの
  フォールバック**(初回起動、30分上限でturnが終わった後、承認拒否)に限る。
- Codexチャットのsandbox・承認設定によっては `.git` への書き込み(branch・worktree作成)が
  拒否される。その場合は実装役に回避させず、worktree・branch作成だけ監視役が代行する
  (Git基盤操作でありコード変更には当たらない)。
- 1チャット内でのサブエージェント委任(codexプラグインのtask委任等)はpairの対象外。
  それは監督付き委任であり、共通AGENTS §7のgate運用だけで足りる。

## 通信ファイル

**常にmain checkout側**の `_ai/tasks/<タスクslug>/` に置き、worktree内へ複製しない。
git commitの対象にもしない(`_ai/` がgit管理下のrepositoryでは対象外に保つ)。

| ファイル | 書き手 | 規約 |
|---|---|---|
| `pair-inbox.md` | 監視役のみ | 実装役への指示。冒頭を最新指示にし、過去分は日付見出しで下へ残す |
| `pair-outbox.md` | 実装役のみ | 監視役への報告。追記式。各entryに時刻+種別(開始宣言/方針提案/検証結果/レビュー依頼/完了報告)+要点のみ。長文・diff全文を書かず、実物はworktreeとrolloutを正とする |

## 手順(監視役側)

3C. **場所の確定と通信路の設営** — 対象repositoryのrootをユーザー指定または自分のcwdで確定する
  (確定できなければユーザーへ確認して停止)。`_ai/tasks/` の既存directoryを確認して重複しない
  タスクslugを選び、契約(`TASK.md`)が未作成なら共通AGENTS §4に従い先に作る。
  inbox/outboxの2ファイルを作成し、inboxへ `assets/impl-brief-codex.md` のbrief
  (`{TASK}` `{INBOX}` `{OUTBOX}` `{MY_JSONL}` を絶対pathで置換)を書く。
  完了判定: 契約と2ファイルが存在し、inboxにbriefがある。
4C. **ユーザーへ1回だけ依頼** — 「Codexチャットへ『<inboxの絶対path> を読んで従ってください』と
  貼ってください」と自チャットで依頼する。以後は実装役がinbox-watchで自動的に動き出すため、
  ユーザーへの促し依頼はwatchが切れているときのフォールバックに限る。
  完了判定: ユーザーへの依頼を出した。
5C. **開始宣言の確認とrollout特定** — turnを終える前に、outboxへの追記を検知するMonitor
  (またはuntilループのbackground実行)を必ず張る(張らずにturnを終えると相手の応答で
  起こされる契機がない)。outboxの開始宣言を確認したら、宣言に含まれるrollout絶対pathを
  監査対象として記録する。pathが書かれていない場合は
  `grep -l <inboxの絶対path> ~/.codex/sessions/<YYYY/MM/DD>/rollout-*.jsonl`
  (日跨ぎ時は前日のdirectoryも見る)で特定する。
  完了判定: outboxの開始宣言と対応rolloutファイルを1つ確定した。
6C. **作業ループと終了** — 指示・レビュー結果・`VERDICT` はinboxへ書く。書いた後およそ5分以内に
  rolloutまたはoutboxの更新(=実装役が動き出した形跡)が確認できなければ、そのとき初めて
  4Cの促しをユーザーへ依頼する(フォールバック)。報告はoutboxで受け、裏取りはworktreeのread-only確認とrolloutの
  絞り読みで行う。停滞監視はoutboxとrolloutのmtimeを対象に15分(検知したらinbox+ユーザー報告)。
  gate・commit条件・reviewer選定はSKILL.md手順5に従う。
  終了時は、inboxへ終了指示を書いてユーザーに促してもらい、outboxの完了報告を検証してから
  SKILL.md手順6の解散へ進む。pairファイル(inbox/outbox)は記録として残し、削除しない。

## inbox-watch(実装役の待機規約)

実装役briefが義務付ける待機動作。監視役はこの前提で運用する。

- 実装役は、監視役の応答待ち(レビュー依頼・質問・提案の後)でターンを終えず、inboxのmtimeを
  監視するblocking shellコマンドを実行する。1回あたり約5分以内に収め(sandboxのcommand timeout
  対策)、更新なしなら繰り返す。合計約30分更新がなければ、outboxへ「watch終了・次回はユーザー
  促しが必要」と1行書いてターンを終える。
- watchコマンドがsandboxで都度承認を要求される等で実用にならない場合は、回避せずその旨を
  outboxへ書いてターンを終える(以後は従来どおりユーザー促しで運用)。
- inbox更新を検知したら、inbox全体ではなく冒頭の最新指示を読み、最優先で従う。

## 省トークン規約

- 通常のやり取りはinbox/outboxの要点だけを読む。
- rolloutの全読は監査時に限定する: 開始宣言の裏取り、gate 3前の判断過程確認、報告と実物の
  食い違い・疑義の発生時。読むときもgrep等で該当範囲へ絞る。

## 停止条件(SKILL.md共通分に加えて)

- ユーザーがCodexチャットへの初回貼り付けを15分以内に行えない: 状況を報告して指示を待つ。
- outboxとrolloutの両方が30分更新なし: 観測事実をユーザーへ報告して停止する。
- 実装役がsandbox制約を回避する動き(main checkoutへの書き込み、承認の迂回)を見せた:
  即座にユーザーへ報告し、inboxへ停止指示を書く。
