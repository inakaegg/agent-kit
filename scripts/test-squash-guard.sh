#!/bin/sh
# squash guard（まとめ忘れガード）の再現テスト。
# 一時repo（bare origin + clone）でpre-commit/pre-pushの検出・素通し・opt-outを検証する。
# 実行: sh scripts/test-squash-guard.sh（CIからは tests/test_squash_guard.py 経由で走る）
set -u

# 開発者のglobal/system設定（core.hooksPath、commit.gpgsign等）から隔離する
GIT_CONFIG_GLOBAL=/dev/null; export GIT_CONFIG_GLOBAL
GIT_CONFIG_SYSTEM=/dev/null; export GIT_CONFIG_SYSTEM
# hook（pre-push → agent-check → unittest）の中から呼ばれるとgitがGIT_DIR等を渡してくる。
# そのままだとfixtureのgitコマンドが一時repoではなく実repoを指し、実repoのconfigや
# originを触ってしまうため、これらを外してから一時repoを作る。
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_COMMON_DIR GIT_PREFIX GIT_ALTERNATE_OBJECT_DIRECTORIES

KIT="$(cd "$(dirname "$0")/.." && pwd -P)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

# gitleaksのスタブ。このfixtureが見るのはsquash guardの挙動だけで、gitleaks本体の
# 検出精度は対象外。実gitleaksに依存すると未導入の環境（CI）でpre-commitが全件止まり、
# 導入済みの環境では版ごとの挙動差が混ざるため、常に成功する実行可能ファイルをPATHの
# 先頭へ置いて、このfixtureの実行中だけ差し替える（ネットワーク不要・決定論的）。
mkdir -p "$TMP/bin"
printf '#!/bin/sh\nexit 0\n' > "$TMP/bin/gitleaks"
chmod +x "$TMP/bin/gitleaks"
PATH="$TMP/bin:$PATH"; export PATH

ok() { echo "PASS: $1"; pass=$((pass + 1)); }
ng() { echo "FAIL: $1"; fail=$((fail + 1)); sed 's/^/    | /' "$TMP/out"; }

# 成功を期待。$1=説明 以降=コマンド
expect_allow() {
  desc="$1"; shift
  if "$@" >"$TMP/out" 2>&1; then ok "$desc"; else ng "${desc}（期待=allow 実際=block）"; fi
}

# hookによる中止を期待。$1=説明 $2=出力に要求する文字列 以降=コマンド
expect_block() {
  desc="$1"; marker="$2"; shift 2
  if "$@" >"$TMP/out" 2>&1; then
    ng "${desc}（期待=block 実際=allow）"
  elif ! grep -q "$marker" "$TMP/out"; then
    ng "${desc}（blockしたが理由が squash guard でない: 「${marker}」不在）"
  else
    ok "$desc"
  fi
}

git init -q --bare -b main "$TMP/origin.git"
git clone -q "$TMP/origin.git" "$TMP/repo" 2>/dev/null
cd "$TMP/repo" || exit 1
git config core.hooksPath "$KIT/git-hooks"
git config user.name test
git config user.email test@example.com
git config hooks.allowMainCommits true
git config hooks.allowLocalPaths true
# squash guard以外の検査はこのfixtureの対象外なので切る
printf 'TEXTLINT=false\nLINKCHECK=false\n' > agent-settings.local.env

echo base > a.txt
git add a.txt
expect_allow "初回commit（upstream未設定はスキップ）" git commit -qm base
expect_allow "初回push（基準点なしはスキップ）" git push -qu origin main

# --- pre-commit パターン1: 未push範囲で追加したファイルの削除 ---
echo x > logo.txt
git add logo.txt
expect_allow "ファイル追加のcommit" git commit -qm add-logo
git rm -q logo.txt
expect_block "未push追加ファイルの削除commit" "打ち消す" git commit -qm remove-logo
git reset -q --hard HEAD

# pushして基準点を進めると、同じ削除は正当な変更として通る
expect_allow "追加commitのpush" git push -q origin main
git rm -q logo.txt
expect_allow "push済みファイルの削除commit（正当）" git commit -qm remove-logo
expect_allow "削除commitのpush" git push -q origin main

# --- pre-commit パターン1: 日本語ファイル名（core.quotePathの引用に影響されない） ---
echo x > 日本語ノート.txt
git add 日本語ノート.txt
expect_allow "日本語名ファイル追加のcommit" git commit -qm add-ja
git rm -q 日本語ノート.txt
expect_block "日本語名の未push追加ファイルの削除commit" "日本語ノート" git commit -qm remove-ja
git reset -q --hard HEAD
expect_allow "日本語名追加commitのpush" git push -q origin main

# --- pre-commit パターン2: 未push変更の巻き戻し ---
echo v2 > a.txt
git add a.txt
expect_allow "内容変更のcommit" git commit -qm change-a
echo base > a.txt
git add a.txt
expect_block "upstream内容へ戻すcommit" "打ち消す" git commit -qm revert-a
git reset -q --hard HEAD

# --- 正常系: 同一ファイルへ変更を重ねる（内容は変わり続ける） ---
echo v3 > a.txt
git add a.txt
expect_allow "同一ファイルへの追加変更commit" git commit -qm change-a-again
expect_allow "変更を重ねた範囲のpush" git push -q origin main

# --- 正常系: revert仕上げcommit（打ち消しに見えるが明示的に始めた正規の操作） ---
echo v4 > a.txt
git add a.txt
expect_allow "revert対象にする内容変更のcommit" git commit -qm change-a-v4
git revert --no-commit HEAD
expect_allow "revert進行中の目印が残っている" sh -c 'test -e "$(git rev-parse --git-dir)/REVERT_HEAD"'
expect_allow "revert仕上げcommit（REVERT_HEADあり）は通る" git commit -qm revert-change-a
# 上の2commitは範囲内で相殺するため、後続のpushを巻き込まないようpush済みの状態へ戻す
git reset -q --hard HEAD~2

# --- pre-commit パターン2(A側): 未pushで削除したファイルの同一内容での復元 ---
echo cc > c.txt
git add c.txt
git commit -qm add-c
expect_allow "c.txtのpush" git push -q origin main
git rm -q c.txt
expect_allow "push済みc.txtの削除commit" git commit -qm rm-c
echo cc > c.txt
git add c.txt
expect_block "削除した内容と同一のc.txt復元commit" "打ち消す" git commit -qm restore-c
git reset -q --hard HEAD
expect_allow "c.txt削除commitのpush" git push -q origin main

# --- opt-out: hooks.allowNetZeroHistory（相殺commit群を意図的に作る） ---
git config hooks.allowNetZeroHistory true
echo y > logo2.txt
git add logo2.txt
git commit -qm add-logo2
git rm -q logo2.txt
expect_allow "opt-out時は削除commitが通る" git commit -qm remove-logo2
# 3commit合成のnet-zero（各commit単体では相殺に見えない）
echo p1 > a.txt; git add a.txt; git commit -qm a-p1
echo p2 > a.txt; git add a.txt; git commit -qm a-p2
echo v3 > a.txt; git add a.txt
expect_block "opt-outなしなら3commit目の巻き戻しは止まる想定の事前確認" "打ち消す" sh -c 'git config --unset hooks.allowNetZeroHistory && git commit -qm a-back'
git config hooks.allowNetZeroHistory true
expect_allow "opt-out時は3commit目も通る" git commit -qm a-back
git config --unset hooks.allowNetZeroHistory

# --- pre-push 最終防衛: 範囲内の相殺（追加→削除と3commit合成net-zero）を止める ---
expect_block "相殺commit群を含むpush（追加→削除）" "追加→削除: logo2.txt" git push -q origin main
expect_block "相殺commit群を含むpush（3commit合成net-zero）" "相殺: a.txt" git push -q origin main

# --- SQUASH_GUARD=false で全体OFF ---
printf 'SQUASH_GUARD=false\n' >> agent-settings.local.env
expect_allow "SQUASH_GUARD=false なら同じpushが通る" git push -q origin main
echo z > logo3.txt
git add logo3.txt
expect_allow "OFF下でのファイル追加commit" git commit -qm add-logo3
git rm -q logo3.txt
expect_allow "SQUASH_GUARD=false なら未push追加ファイルの削除commitが通る" git commit -qm remove-logo3

echo "----"
echo "pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
