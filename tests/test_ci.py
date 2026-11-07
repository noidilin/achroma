"""Narrow regressions for CI identity, handoff integrity, and workflow policy."""

import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('achroma_ci', ROOT / 'tools/ci.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
REVISION = 'a' * 40


class CiTests(unittest.TestCase):
    def test_identity_uses_checked_out_commit_not_environment(self):
        with patch.object(ci, 'git', side_effect=['', REVISION]):
            self.assertEqual(ci.identity(), {'version': '0.1.0-dev', 'sourceRevision': REVISION})

    def test_identity_rejects_dirty_and_untracked_source(self):
        for status in (' M palette/dark.json', '?? surprise.py'):
            with self.subTest(status=status), patch.object(ci, 'git', return_value=status):
                with self.assertRaisesRegex(ValueError, 'committed, clean'):
                    ci.identity()

    def test_identity_rejects_unsafe_or_nonsemantic_tags(self):
        for tag in ('0.1.0', 'v01.0.0', 'v0.1.0-01', 'v0.1.0+build', 'v$(touch bad)', 'v../bad'):
            with self.subTest(tag=tag), patch.object(ci, 'git', side_effect=['', REVISION]):
                with self.assertRaises(ValueError):
                    ci.identity(tag)

    def test_identity_peels_tag_and_requires_matching_commit(self):
        with patch.object(ci, 'git', side_effect=['', REVISION, 'b' * 40]) as git:
            with self.assertRaisesRegex(ValueError, 'does not match'):
                ci.identity('v0.1.0')
            self.assertEqual(git.call_args.args, ('rev-parse', '--verify', 'refs/tags/v0.1.0^{commit}'))

    def test_identity_requires_nonempty_committed_version_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            notes = root / 'docs/releases/0.1.0-rc.1.md'
            notes.parent.mkdir(parents=True)
            notes.write_text('  \n')
            with patch.object(ci, 'git', side_effect=['', REVISION, REVISION, '']):
                with self.assertRaisesRegex(ValueError, 'must not be empty'):
                    ci.identity('v0.1.0-rc.1', root)
            notes.write_text('Reviewed release notes\n')
            with patch.object(ci, 'git', side_effect=['', REVISION, REVISION, '']) as git:
                self.assertEqual(ci.identity('v0.1.0-rc.1', root)['version'], '0.1.0-rc.1')
                self.assertEqual(git.call_args.args,
                                 ('ls-files', '--error-unmatch', '--', 'docs/releases/0.1.0-rc.1.md'))

    def test_network_boundary_rejects_normal_host_network(self):
        with patch.object(ci.sys, 'platform', 'linux'), \
                patch.object(ci.socket, 'if_nameindex', return_value=[(1, 'lo'), (2, 'eth0')]):
            with self.assertRaisesRegex(ValueError, 'network namespace'):
                ci.require_network_namespace()

    def test_network_boundary_requires_linux_and_only_loopback(self):
        with patch.object(ci.sys, 'platform', 'darwin'):
            with self.assertRaisesRegex(ValueError, 'Linux network namespace'):
                ci.require_network_namespace()
        with patch.object(ci.sys, 'platform', 'linux'), \
                patch.object(ci.socket, 'if_nameindex', return_value=[(1, 'lo')]):
            ci.require_network_namespace()

    def test_bundle_binds_exact_files_and_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'output'
            output.mkdir()
            archive = output / 'achroma-0.1.0.zip'
            archive.write_bytes(b'verified archive')
            (output / 'SHA256SUMS').write_text(f'{ci.digest(archive)}  {archive.name}\n')
            notes = root / 'docs/releases/0.1.0.md'
            notes.parent.mkdir(parents=True)
            notes.write_text('Reviewed notes\n')
            source = root / 'source.py'
            source.write_text('exact input\n')
            release = {'version': '0.1.0', 'sourceRevision': REVISION}
            manifest = {'release': release, 'buildInputs': {'source.py': ci.digest(source)}}
            destination = root / 'bundle'
            with patch.object(ci.verify, 'verify', return_value=manifest):
                transfer = ci.bundle(output, destination, release, 'v0.1.0', root)
                self.assertEqual(transfer, ci.digest(destination / 'TRANSFER.sha256'))
                for line in (destination / 'TRANSFER.sha256').read_text().splitlines():
                    checksum, name = line.split('  ')
                    self.assertEqual(checksum, ci.digest(destination / name))
                self.assertEqual(json.loads((destination / 'SOURCE.json').read_text()),
                                 {'release': release, 'tag': 'v0.1.0'})
                self.assertEqual((destination / archive.name).read_bytes(), archive.read_bytes())
                with self.assertRaises(FileExistsError):
                    ci.bundle(output, destination, release, 'v0.1.0', root)
                source.write_text('modified input\n')
                with self.assertRaisesRegex(ValueError, 'input differs'):
                    ci.bundle(output, root / 'bad-bundle', release, 'v0.1.0', root)
                manifest['release'] = {**release, 'sourceRevision': 'b' * 40}
                with self.assertRaisesRegex(ValueError, 'identity differs'):
                    ci.bundle(output, root / 'bad-bundle', release, 'v0.1.0', root)

    def test_workflow_security_and_handoff_seams(self):
        for name in ('ci', 'release'):
            text = (ROOT / f'.github/workflows/{name}.yml').read_text()
            for action in re.findall(r'uses: (\S+)', text):
                self.assertRegex(action, r'^actions/[a-z-]+@[0-9a-f]{40}$')
            for forbidden in ('pull_request_target', 'continue-on-error', 'secrets.', '--clobber', 'actions/deploy-pages'):
                self.assertNotIn(forbidden, text)
            self.assertIn('persist-credentials: false', text)
            self.assertIn('bash tools/ci.sh', text)
            self.assertIn('--cache "$GITHUB_WORKSPACE/.work/npm-cache" --ignore-scripts', text)
            # Expressions belong in structured YAML fields/env, never shell code.
            in_run = False
            for line in text.splitlines():
                if re.match(r'      - ', line):
                    in_run = False
                if re.match(r'        run:', line):
                    in_run = True
                if in_run:
                    self.assertNotIn('${{', line)
        release = (ROOT / '.github/workflows/release.yml').read_text()
        self.assertIn("tags: ['v*']", release)
        self.assertNotIn('workflow_dispatch', release)
        self.assertIn('environment: release', release)
        self.assertIn("if: ${{ vars.RELEASE_PUBLICATION_ENABLED == 'true' }}", release)
        self.assertEqual(release.count('contents: write'), 1)
        self.assertIn('artifact-ids: ${{ needs.build.outputs.artifact-id }}', release)
        self.assertIn('TRANSFER_SHA256: ${{ needs.build.outputs.transfer-sha256 }}', release)
        self.assertIn('--verify-tag --target "$REVISION"', release)
        shell = (ROOT / 'tools/ci.sh').read_text()
        self.assertIn('sudo unshare --net -- setpriv', shell)
        self.assertIn('--reuid="$(id -u)"', shell)


if __name__ == '__main__':
    unittest.main()
