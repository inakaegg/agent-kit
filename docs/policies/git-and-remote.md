# Git・remote状態の運用ポリシー

この文書はGit、GitHub、registry、release、deploy等の作業のときだけ読む。project固有ルールとbranch protectionを優先する。

## 作業場所とrepositoryの区分

- 機能追加、バグ修正、refactorなど、コードまたは製品挙動を変更する作業は `main` のcheckoutで行わない。task専用の新規branchと別worktreeを作成してから編集する（`REQUIRE_WORKTREE=false` のときは別worktree不要、task branchのみでよい）。ただし編集・commit・branch切替を行い得る他のセッションが同じcheckoutを使っているときは、`REQUIRE_WORKTREE` の値や変更の種類によらず、git管理下のファイルの編集とcommitをtask branchの別worktreeで行う。いないと確認できないときも同様とし、read-onlyの調査・レビューだけのセッションは数えない。他のセッションのbranch切替でHEADが動き、commitが意図しないbranchへ乗るためである。git管理外の `_ai/` は`AGENTS.md` §2のとおりmain checkout側へ書く。既にそのtask専用のlinked worktreeにいて、編集し得る他のセッションがそれを使っていない場合は、新しいworktreeを重ねて作らない。merge済みのworktreeは `AUTO_PRUNE_WORKTREES=true` なら許可なく削除してよい（未commit差分・ignoredなローカルファイルが残るものは除く。確認手順は本書§6）。branchはgraphでつながりを見るために残し、削除は明示許可がある場合だけ行う。
- 公開repositoryでは、誤字修正などの軽微な文書更新も含め、`main`（master等のdefault branch）への取り込みを常にPR経由とし、mainへ直接commit・pushしない。軽微な文書更新もtask branchを作って編集・commitする（別worktreeは不要。ただし他のセッションと同じcheckoutを使う場合は前項のとおり別worktreeを作る）。push・PR作成は`AGENTS.md` §3のとおり明示許可を得てから行い、許可がない間はbranchへのcommitと報告に留める。公開か確認できないrepositoryは公開として扱い、非公開でも他者と共有するrepositoryは公開と同じ扱いとする。
- ユーザーが管理権限を持つ公開repositoryには、branch protectionを設定して上記を機械的にも強制する。設定・変更の実行は`AGENTS.md` §3のとおり明示許可を得て行い、protectionの内容と公開状態の確認手順は本書§7 に従う。
- 他者と共有しない非公開repositoryでは従来どおり、軽微な文書更新に限り、branchとstatusを確認し他作業の差分を巻き込まない場合だけ `main` のcheckoutで行ってよい。他のセッションと同じcheckoutを使う場合は、この場合もtask branchと別worktreeを作る。
- コード・製品挙動の変更か軽微な文書更新か、またはrepositoryの公開・共有の区分を判断できない場合は、編集を始める前にユーザーへ確認する。

## 1. 作業開始前

- `git status -sb`、現在branch、remote、base、既存差分を確認する。
- 期待と違うbranch、別taskの差分、意図不明のuntracked fileがある場合は、それを巻き込まず停止して報告する。
- regression調査では、必要に応じて `git log -S`、`git blame`、導入commitのdiffを確認する。履歴を見ていない推測を「原因」と断定しない。
- feature branch作成、PR準備、remote状態の判断前には、必要なremoteを `git fetch` してbaseの進みを確認する。fetch後もmerge・rebase・branch切替を自動実行せず、差分とproject方針を確認する。
- 大きい変更、実機・新SDK・migration・security・billing・releaseに関わる変更はfeature branchで行う。小変更でもproject方針がbranchを要求する場合は従う。

## 2. local commit

実装・変更を明示されたtaskでは、次をすべて満たす場合だけlocal commitしてよい。

1. 許可されたtaskの差分だけである
2. 変更種別に必要な検査が成功している
3. 1commit 1目的で説明できる
4. secret、大容量の生成物、debug残骸、個人絶対pathを含まない
5. final diffを確認した

追加規則：

- stageはfileを個別指定する。`git add .`、`git add -A`、directory丸ごとのaddは使わない。
- untracked fileを無断削除しない。
- pre-commit Hookをskipしない。
- 未pushの直前commitと同じ目的の修正は `git commit --amend` で統合してよい。
- commit messageはrepository規則（明文か、履歴の支配的な形式）を優先する。規則がなければ、件名は「**英語の要約 / 日本語の要約**」を斜線で並べた1行とする（`COMMIT_LANG_ORDER`。`en-ja` が既定、日本語先のrepositoryは `ja-en`、検査しないなら `off`）。英語側は簡潔に書く。本文を書く場合も英語と日本語を併記し、順序は件名と同じ `COMMIT_LANG_ORDER` に従う。末尾のtrailerブロックと区切り線は本文と数えない。
- 検査失敗、未解決の仕様判断、意図確認が必要な削除・大改変がある場合はcommitしない。

## 3. push・PR

- push、PR作成・更新は、そのターンの明示許可がある場合だけ行う。
- 公開repositoryでは、軽微な文書更新も含め、default branchへの取り込みを常にPR経由とする（AGENTS.md §8）。default branchへの直接pushをしない。
- 「PRを作成して」は、現在のfeature branchの必要なpushとPR作成までを許可する。merge、base branchへのpush、public化は含まない。
- PR作成前に、base/head、title、scope、test、未確認範囲、最新headの独立review結果を確認する。
- 自分のリポジトリでは `git config --local hooks.runAgentCheck true` を設定し、検証コマンドを `scripts/agent-check.sh` へ集約する。設定したリポジトリでは共有pre-push hookが `fast` モードで実行し、失敗したpushは止まる。opt-inなのは、cloneした他者のリポジトリのスクリプトをpushだけで実行させないためである。
- PR作成の直後に `$pr-review-loop` へ入り、最新headのbot review・CIを確認する。projectが要求するかユーザーが依頼したbotが利用上限等で止まっていれば、その事実と再開時刻を同Skillのstate記録へ残す。再依頼のcomment投稿はremote writeなので §3 の許可範囲に従い、許可がなければ再開時刻の記録と報告に留める。
- PRは、ユーザーがDraftを指定しない限りreview-readyを既定とする。既知blockerは本文へ明記するが、勝手にDraftへ切り替えない。
- 元のユーザープロンプト全文、個人情報、内部戦略、未公開情報をPRへ自動転載しない。必要な要件だけを安全なtask summaryへ整理する。
- GitHub上のbot reviewは、ユーザーが依頼した場合またはproject方針が要求する場合に使う。botの名前やworkflow名をcommon policyへ固定しない。

## 4. review対応

- 対応が必要なすべての指摘を確認し、`修正 / 記録のみ / 誤検知として反証`へ分類する。
- bot同士が矛盾しても、両方を機械的に満足させない。code、spec、test、実挙動から正しい判断を選ぶ。
- 修正した場合はlocalの検査を再実行し、必要なpush権限の範囲内で更新する。
- latest headへのreview結果、required CI、未解決threadを確認する。silence、rate limit、processing中reaction、経過時間をapproval扱いしない。
- `$pr-review-loop` のiteration上限とstate記録に従う。

## 5. merge・履歴改変

- mergeは、そのターンの明示依頼、required CI成功、最新headへのreview完了、未確認範囲の確認がある場合だけ行う。`AUTO_MERGE_PRIVATE=true` の非公開・非共有repositoryでは、明示依頼の代わりに「必要なレビューがすべてLGTMで、暫定通過のやり直しが済んでいる」を条件にローカルmergeしてよい（`AGENTS.md` §3）。自己検証・記録付きの例外通過は、この許可なしmergeの条件を満たさない。
- project規則がない通常のGitHub開発では、`feature branch → PR → CI → merge commit` を既定とする。squash mergeはbranchとbaseの繋がりをgraphから消し、取り込み済み判定を壊すため使わない。ユーザーが明示指示した場合だけ例外とする。
- localでfeature branchをbaseへ取り込む場合は `git merge --no-ff` を使い、fast-forwardでmerge commitを省略しない。
- shared historyのrebase、squash、force push、base branch直接pushは行わない。明示合意とteam方針がある場合だけ例外とする。
- `--force`は使わない。`--force-with-lease`も、共有済み履歴では原則使わず、明示許可と安全確認がある場合に限定する。
- PR運用を始めた変更を、PR作成前にlocal base branchへmergeしない。

## 6. worktree

project方針がない場合：

- 新しいworktreeはrepository直下の `.worktrees/` に置き、`.gitignore`へ追加する。
- merge済みのworktreeは `git worktree remove` で片づける（`AUTO_PRUNE_WORKTREES=true` なら許可不要。`AGENTS.md` §8）。branchは残す。
- 削除前に `git -C <worktree> status --porcelain --ignored` を実行する。出力が無ければ前項のとおり許可なく削除してよい。出力があれば削除せず、消してよいかをユーザーへ確認する。`git worktree remove` は `--force` なしでもignoredな未追跡ファイル（`.env`、生成物など）ごとdirectoryを消すため、`git status -sb` がcleanに見えても安全とは限らない。
- remote-tracking branchからfeature branchを作るときはupstreamを誤設定しない。作成後に `git status -sb` または `git branch -vv` で追跡先を確認する。
- 初回pushは同名remote branchを明示してupstreamを設定する。

## 7. repository・artifactのvisibility

- 既存repositoryの公開状態は `gh repo view <owner>/<repo> --json visibility` で確認する。確認できない場合は公開として扱う。
- ユーザーが管理権限を持つ公開repositoryのdefault branchには、branch protection（GitHubではRulesets。PR必須・force push禁止・削除禁止。CIがある場合は必須checkに緑）を設定する。設定はクラウド設定変更にあたるため、実行前に明示許可を得る。設定後は `gh api repos/<owner>/<repo>/rulesets` で実際の内容を再確認する（旧式の `branches/<branch>/protection` APIはRulesetsを返さないため確認に使わない）。

- 新規source repository、container repository、package、bucket、artifact storeはprivateを既定とする。
- 作成時はvisibilityをdefaultへ任せずprivateを明示する。確認方法が不明なら作成・初回pushを止める。
- 初回pushでresourceが自動作成されるregistryでは、存在、namespace、default privacyを事前確認する。
- source、container image、release artifact、package、deploy先は別々にvisibilityを確認する。
- 作成、visibility変更、初回push後は、実際の公開範囲をAPIまたは管理画面で再確認し、報告する。
- public化、初回のpublic push、または非公開のまま他者（collaborator・team）へ共有を始める前に、`DOCS_LEVEL=full` へ移行する。`minimal`（既定値）のrepoでは追跡対象の `agent-settings.env` に `DOCS_LEVEL=full` を置き、骨組みだけだった人間向け文書を完成文書へ整える。そのうえで次の2つを済ませて記録を残す（現在taskの `reviews/` 等）。人間向け文書（README等）の読みやすさレビュー（`$docs-maintenance`）で `VERDICT: LGTM` を得ること。READMEの手順のうち、ローカルで完結し副作用のない部分（インストール、起動、dry-run）を書いたとおりに実行して確かめること。
- デプロイ、課金、公開を伴う手順は実行して確かめない。dry-runやplanがあればそれで代え、無ければ「未実行」と完了報告に明記する。
