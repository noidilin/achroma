"""Offline mocked regressions for scheduled proposals and their privileged boundary."""

import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('achroma_upstream', ROOT / 'tools/upstream.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
sys.path.insert(0, str(ROOT / 'tools'))
import ci
BASE = 'a' * 40
TREE = 'b' * 40
HEAD = 'c' * 40
REPO = 'noidilin/achroma'
RUN = f'https://github.com/{REPO}/actions/runs/123'


class Remote:
    def __init__(self):
        self.head = None
        self.tree = None
        self.pulls = []
        self.calls = []
        self.moved = False
        self.human = False
        self.fail_pr = False

    def __call__(self, method, endpoint, data=None, **kwargs):
        self.calls.append((method, endpoint, data))
        path = endpoint.removeprefix(f'repos/{REPO}/')
        if method == 'GET':
            if path == 'git/ref/heads/main':
                return {'object': {'sha': 'd' * 40 if self.moved else BASE}}
            if path.startswith('pulls?'):
                return self.pulls
            if path == f'git/ref/heads/{u.BRANCH}':
                return {'object': {'sha': self.head}} if self.head else None
            if path.startswith('commits/'):
                return {'commit': {'message': u.MESSAGE, 'tree': {'sha': self.tree}},
                        'author': {'login': 'maintainer' if self.human else 'github-actions[bot]'}}
            if path.startswith('compare/'):
                return {'files': [{'filename': str(u.VENDOR / 'prism.css'), 'status': 'modified'}]}
        if method == 'POST' and path == 'git/trees':
            return {'sha': TREE}
        if method == 'POST' and path == 'git/commits':
            self.tree = data['tree']
            return {'sha': HEAD}
        if path.startswith('git/refs') and method in ('POST', 'PATCH'):
            self.head = data['sha']
            return {}
        if path == 'pulls' and method == 'POST':
            if self.fail_pr:
                raise RuntimeError('PR creation forbidden')
            self.pulls = [{'number': 1, 'state': 'open', 'base': {'ref': 'main'}}]
            return self.pulls[0]
        if path == 'pulls/1' and method == 'PATCH':
            return {}
        raise AssertionError((method, path, data))


class UpstreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / u.VENDOR, self.root / u.VENDOR)
        self.directory = self.root / '.work/proposal'
        self.root_patch = patch.object(u, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.commit = json.loads((self.root / u.VENDOR / 'upstream.lock.json').read_text())['standard_commit']

    def candidate(self, changed=True, name='prism.css'):
        shutil.copytree(self.root / u.VENDOR, self.directory)
        if changed:
            path = self.directory / name
            path.write_bytes(path.read_bytes() + b'\n')
            lock = json.loads((self.directory / 'upstream.lock.json').read_text())
            lock['files'][name]['sha256'] = u.stylus.digest(path.read_bytes())
            (self.directory / 'upstream.lock.json').write_bytes(u.stylus.json_bytes(lock))
        report = {'base': BASE, 'standard_commit': self.commit,
                  'checks': {'build': 0, 'verify': 0, 'compile': 0, 'full_ci': 1}}
        (self.directory / 'proposal.json').write_bytes(u.stylus.json_bytes(report))
        return report

    def publish(self, remote):
        with patch.object(u, 'git', side_effect=lambda *args: BASE), patch.object(u, 'api', remote):
            u.publish(self.directory, REPO, RUN)

    def test_prepare_noop_and_same_sha_independent_update(self):
        for changed, name in ((False, 'prism.css'), (True, 'prism.css'), (True, 'export.json')):
            with self.subTest(changed=changed, name=name):
                if self.directory.exists():
                    shutil.rmtree(self.directory)
                def update(directory, commit, url):
                    self.assertEqual(commit, self.commit)
                    self.assertEqual(url, u.EXPORT_URL)
                    # Use the fixture helper to emulate the existing downloader's transaction.
                    directory.rmdir()
                    self.candidate(changed, name)
                    (directory / 'proposal.json').unlink()
                with patch.object(u.stylus, 'download', return_value=json.dumps({'sha': self.commit}).encode()), \
                        patch.object(u.stylus, 'update', side_effect=update), \
                        patch.object(u, 'git', return_value=BASE) as git:
                    self.assertEqual(u.prepare(self.directory), changed)
                    self.assertEqual(any(call.args[0] == 'commit' or 'commit' in call.args
                                         for call in git.call_args_list), changed)
                self.assertEqual(self.directory.exists(), changed)

    def test_prepare_bad_revision_or_download_failure_never_stages(self):
        for sha in ('$(bad)', 'A' * 40, '../main'):
            with patch.object(u, 'git', return_value=BASE) as git, \
                    patch.object(u.stylus, 'download', return_value=json.dumps({'sha': sha}).encode()):
                with self.assertRaises(ValueError):
                    u.prepare(self.directory)
                self.assertEqual(git.call_count, 1)
        with patch.object(u, 'git', return_value=BASE) as git, \
                patch.object(u.stylus, 'download', return_value=json.dumps({'sha': self.commit}).encode()), \
                patch.object(u.stylus, 'update', side_effect=ValueError('unsupported dependency')):
            with self.assertRaisesRegex(ValueError, 'unsupported dependency'):
                u.prepare(self.directory)
            self.assertEqual(git.call_count, 1)

    def test_data_handoff_rejects_extra_files_checksums_urls_and_license_changes(self):
        self.candidate()
        path = self.directory / 'run.py'
        path.write_text('bad')
        with self.assertRaisesRegex(ValueError, 'file set'):
            u.read_candidate(self.directory)
        path.unlink()
        path = self.directory / 'prism.css'
        original = path.read_bytes()
        path.write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            u.read_candidate(self.directory)
        path.unlink()
        path.symlink_to(self.root / u.VENDOR / 'prism.css')
        with self.assertRaisesRegex(ValueError, 'regular files'):
            u.read_candidate(self.directory)
        path.unlink()
        path.write_bytes(original)
        lockpath = self.directory / 'upstream.lock.json'
        lock = json.loads(lockpath.read_text())
        lock['files']['prism.css']['url'] = 'https://attacker.test/css'
        lockpath.write_bytes(u.stylus.json_bytes(lock))
        with self.assertRaisesRegex(ValueError, 'provenance URL'):
            u.read_candidate(self.directory)
        lock['files']['prism.css']['url'] = u.stylus.CSS_URLS['prism.css']
        (self.directory / 'LICENSE').write_bytes(b'new terms')
        lock['files']['LICENSE']['sha256'] = u.stylus.digest(b'new terms')
        lockpath.write_bytes(u.stylus.json_bytes(lock))
        with self.assertRaisesRegex(ValueError, 'manual license'):
            u.read_candidate(self.directory)

    def test_publish_noop_makes_no_api_calls(self):
        self.candidate(False)
        remote = Remote()
        self.publish(remote)
        self.assertEqual(remote.calls, [])

    def test_publish_creates_draft_and_rerun_does_not_duplicate_commits_or_prs(self):
        self.candidate()
        remote = Remote()
        self.publish(remote)
        self.publish(remote)
        commits = [c for c in remote.calls if c[0] == 'POST' and c[1].endswith('/git/commits')]
        pulls = [c for c in remote.calls if c[0] == 'POST' and c[1].endswith('/pulls')]
        self.assertEqual(len(commits), 1)
        self.assertEqual(len(pulls), 1)
        self.assertTrue(pulls[0][2]['draft'])
        self.assertIn('full_ci: exit 1', pulls[0][2]['body'])
        self.assertIn('not PR CI', pulls[0][2]['body'])
        tree = next(c[2] for c in remote.calls if c[1].endswith('/git/trees'))
        self.assertEqual({item['path'] for item in tree['tree']},
                         {str(u.VENDOR / name) for name in u.NAMES})

    def test_existing_automation_branch_is_updated(self):
        self.candidate()
        remote = Remote()
        remote.head, remote.tree = HEAD, 'd' * 40
        remote.pulls = [{'number': 1, 'state': 'open', 'base': {'ref': 'main'}}]
        self.publish(remote)
        self.assertTrue(any(c[0] == 'PATCH' and '/git/refs/heads/' in c[1] for c in remote.calls))
        self.assertFalse(any(c[0] == 'POST' and c[1].endswith('/pulls') for c in remote.calls))

    def test_refuses_main_movement_human_edits_and_closed_declined_pr(self):
        self.candidate()
        for state, message in (('moved', 'Main moved'), ('human', 'human/unrecognized'),
                               ('closed', 'closed without merge')):
            remote = Remote()
            if state == 'closed':
                remote.pulls = [{'number': 1, 'state': 'closed', 'merged_at': None}]
            else:
                setattr(remote, state, True)
                if state == 'human':
                    remote.head = HEAD
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, message):
                self.publish(remote)
            self.assertFalse(any(c[0] in ('POST', 'PATCH') for c in remote.calls))

    def test_refuses_out_of_scope_existing_branch_diff(self):
        self.candidate()
        remote = Remote()
        remote.head, remote.tree = HEAD, 'd' * 40
        def api(method, endpoint, data=None, **kwargs):
            if '/compare/' in endpoint:
                return {'files': [{'filename': 'tools/build.py', 'status': 'modified'}]}
            return remote(method, endpoint, data, **kwargs)
        with self.assertRaisesRegex(ValueError, 'outside the snapshot allowlist'):
            self.publish(api)
        self.assertFalse(any(c[0] in ('POST', 'PATCH') for c in remote.calls))

    def test_refuses_observed_branch_race_before_ref_update(self):
        self.candidate()
        remote = Remote()
        remote.head, remote.tree = HEAD, 'd' * 40
        reads = 0
        def api(method, endpoint, data=None, **kwargs):
            nonlocal reads
            if endpoint.endswith(f'/git/ref/heads/{u.BRANCH}'):
                reads += 1
                if reads == 2:
                    return {'object': {'sha': 'e' * 40}}
            return remote(method, endpoint, data, **kwargs)
        with self.assertRaisesRegex(ValueError, 'moved during publication'):
            self.publish(api)
        self.assertFalse(any(c[0] == 'PATCH' for c in remote.calls))

    def test_pr_permission_failure_is_explicit_and_retry_reuses_branch(self):
        self.candidate()
        remote = Remote()
        remote.fail_pr = True
        with self.assertRaisesRegex(RuntimeError, 'forbidden'):
            self.publish(remote)
        remote.fail_pr = False
        self.publish(remote)
        self.assertEqual(sum(c[0] == 'POST' and c[1].endswith('/git/commits') for c in remote.calls), 1)
        self.assertEqual(len(remote.pulls), 1)

    def test_validate_records_all_failures_without_skipping_later_checks(self):
        self.candidate()
        with patch.object(u, 'git', return_value=BASE), \
                patch.object(ci, 'require_network_namespace'), \
                patch.object(u.subprocess, 'run') as run:
            run.return_value.returncode = 1
            u.validate(self.directory)
            self.assertEqual(run.call_count, 4)
        report = json.loads((self.directory / 'proposal.json').read_text())
        self.assertEqual(set(report['checks'].values()), {1})

    def test_workflow_privilege_and_trigger_seams(self):
        text = (ROOT / '.github/workflows/upstream-refresh.yml').read_text()
        for action in re.findall(r'uses: (\S+)', text):
            self.assertRegex(action, r'^actions/[a-z-]+@[0-9a-f]{40}$')
        for forbidden in ('pull_request_target', 'workflow_run', 'secrets.', 'environment:',
                          'continue-on-error', 'release create', 'deploy-pages', 'checks: write'):
            self.assertNotIn(forbidden, text)
        self.assertIn("cron: '23 6 * * 1'", text)
        self.assertIn('workflow_dispatch:', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertEqual(text.count('contents: write'), 1)
        self.assertEqual(text.count('pull-requests: write'), 1)
        refresh, propose = text.split('  propose:')
        self.assertNotIn('GH_TOKEN:', refresh)
        self.assertNotIn('contents: write', refresh)
        self.assertNotIn('npm ci', propose)
        self.assertNotIn(' validate ', propose)
        self.assertIn('artifact-ids: ${{ needs.refresh.outputs.artifact-id }}', propose)
        self.assertIn('sudo unshare --net -- setpriv', refresh)
        self.assertIn('ref: ${{ github.sha }}', propose)
        in_run = False
        for line in text.splitlines():
            if re.match(r'      - ', line):
                in_run = False
            if re.match(r'        run:', line):
                in_run = True
            if in_run:
                self.assertNotIn('${{', line)


if __name__ == '__main__':
    unittest.main()
