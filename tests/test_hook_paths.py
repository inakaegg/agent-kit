"""Exercise hook delegation and filename handling through executable hooks."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1]


class HookPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        HOOK_LOG=str(self.root / 'hook.json'), LINT_LOG=str(self.root / 'lint.jsonl'))
        # This fixture isolates delegation/lint; the existing suite tests real gitleaks.
        self.executable(self.bin / 'gitleaks', '#!/bin/sh\nexit 0\n')
        self.git('init', '-q', '-b', 'feature')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('commit', '--allow-empty', '-qm', 'Initial')
        self.git('config', 'core.hooksPath', str(KIT / 'git-hooks'))

    def executable(self, path, body):
        path.write_text(body, encoding='utf-8')
        path.chmod(0o755)

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, check=True).stdout

    def hook(self, name='pre-commit', cwd=None, args=(), stdin=''):
        return subprocess.run(['sh', str(KIT / 'git-hooks' / name), *args],
                              cwd=cwd or self.repo, env=self.env, input=stdin,
                              capture_output=True, text=True, timeout=5)

    def worktree(self):
        wt = self.root / 'linked worktree'
        self.git('worktree', 'add', '-qb', 'linked', str(wt))
        return wt

    def test_common_hooks_receive_arguments_stdin_and_exit_status(self):
        wt = self.worktree()
        for name in ('pre-commit', 'commit-msg', 'pre-push'):
            local = self.repo / '.git' / 'hooks' / name
            self.executable(local, f'#!{sys.executable}\n'
                            'import json, os, sys\n'
                            'with open(os.environ["HOOK_LOG"], "w") as f:\n'
                            '    json.dump([sys.argv[1:], sys.stdin.read()], f)\n'
                            'sys.exit(42)\n')
            try:
                for cwd in (self.repo, wt):
                    with self.subTest(hook=name, cwd=cwd.name):
                        msg = cwd / 'message.txt'
                        msg.write_text('Valid subject\n')
                        args = (str(msg),) if name == 'commit-msg' else ('origin', 'example.invalid')
                        zero = '0' * 40
                        stdin = f'(delete) {zero} refs/heads/old {"1" * 40}\n' if name == 'pre-push' else 'input\n'
                        result = self.hook(name, cwd, args, stdin)
                        self.assertEqual(result.returncode, 42, result.stderr)
                        self.assertEqual(json.loads(Path(self.env['HOOK_LOG']).read_text()), [list(args), stdin])
            finally:
                local.unlink()

    def test_symlink_to_shared_hook_does_not_recurse(self):
        wt = self.worktree()
        for name in ('pre-commit', 'commit-msg', 'pre-push'):
            local = self.repo / '.git' / 'hooks' / name
            local.symlink_to(KIT / 'git-hooks' / name)
            try:
                for cwd in (self.repo, wt):
                    with self.subTest(hook=name, cwd=cwd.name):
                        msg = cwd / 'message.txt'
                        msg.write_text('Valid subject\n')
                        args = (str(msg),) if name == 'commit-msg' else ()
                        result = self.hook(name, cwd, args)
                        self.assertEqual(result.returncode, 0, result.stderr)
            finally:
                local.unlink()

    def stage(self, name, body):
        (self.repo / name).write_text(body, encoding='utf-8')
        self.git('add', '--', name)

    def test_linkcheck_checks_unusual_filenames(self):
        self.git('config', 'hooks.skipTextlint', 'true')
        for name in ('english.md', '日本語.md', 'space name.md', 'line\nbreak.md', 'quote"name.md'):
            with self.subTest(name=name):
                self.stage(name, '[broken](missing.md)\n')
                result = self.hook()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('missing.md', result.stderr)
                self.git('reset', '-q', 'HEAD', '--', name)

    def fake_textlint(self):
        self.executable(self.bin / 'textlint', f'#!{sys.executable}\n' + '''import json, os, sys
from pathlib import Path
with open(os.environ['LINT_LOG'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
files = [Path(arg) for arg in sys.argv[1:] if arg.endswith('.md')]
if '--fix' in sys.argv:
    for path in files:
        path.write_text(path.read_text().replace('指摘', '修正'))
sys.exit(1 if any('指摘' in path.read_text() for path in files) else 0)
''')

    def test_textlint_receives_unusual_filenames(self):
        self.fake_textlint()
        names = ('日本語.md', 'space name.md', 'line\nbreak.md', 'quote"name.md')
        for name in names:
            self.stage(name, 'これは正常な日本語の文書です。\n')
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in Path(self.env['LINT_LOG']).read_text().splitlines()]
        seen = {str(Path(arg)) for call in calls for arg in call if arg.endswith('.md')}
        self.assertEqual(seen, set(names))

    def test_autofix_stops_commit_and_leaves_index_unchanged(self):
        self.fake_textlint()
        name = '日本語\n文書.md'
        self.stage(name, 'これは指摘です。\n')
        result = self.hook()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((self.repo / name).read_text(), 'これは修正です。\n')
        self.assertEqual(self.git('show', ':' + name), 'これは指摘です。\n')

    def test_partial_stage_is_not_autofixed(self):
        self.fake_textlint()
        name = '日本語.md'
        self.stage(name, 'これは指摘です。\n')
        body = 'これは指摘です。未stageの編集です。\n'
        (self.repo / name).write_text(body)
        result = self.hook()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual((self.repo / name).read_text(), body)
        calls = [json.loads(line) for line in Path(self.env['LINT_LOG']).read_text().splitlines()]
        self.assertFalse(any('--fix' in call for call in calls))

    def test_no_targets_and_english_text_do_not_invoke_textlint(self):
        self.fake_textlint()
        self.assertEqual(self.hook().returncode, 0)
        self.stage('english.md', 'This document is English.\n')
        self.assertEqual(self.hook().returncode, 0)
        self.assertFalse(Path(self.env['LINT_LOG']).exists())

    def test_dash_entrypoint_and_direct_execution(self):
        self.stage('日本語.md', '[broken](missing.md)\n')
        self.git('config', 'hooks.skipTextlint', 'true')
        commands = [[str(KIT / 'git-hooks/pre-commit')]]
        if shutil.which('dash'):
            commands.append(['dash', str(KIT / 'git-hooks/pre-commit')])
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(command, cwd=self.repo, env=self.env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('missing.md', result.stderr)

    def test_direct_execution_resolves_bash_from_path(self):
        bash = shutil.which('bash')
        self.assertIsNotNone(bash)
        marker = self.root / 'bash-used'
        self.executable(self.bin / 'bash', f'#!{sys.executable}\n'
                        'import os, sys\n'
                        f'open({str(marker)!r}, "w").close()\n'
                        f'os.execv({bash!r}, [{bash!r}, *sys.argv[1:]])\n')
        result = subprocess.run([str(KIT / 'git-hooks/pre-commit')],
                                cwd=self.repo, env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(marker.exists(), 'pre-commit must resolve Bash from PATH')
