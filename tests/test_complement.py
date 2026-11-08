"""Offline coverage for the optional style and manually checked source provenance."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import complement


class ComplementTests(unittest.TestCase):
    def setUp(self):
        self.palettes = {variant: json.loads((ROOT / f'palette/{variant}.json').read_text())
                         for variant in ('light', 'dark')}
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source'
        shutil.copytree(complement.SOURCE, self.source)

    def test_render_is_deterministic_offline_and_valid(self):
        with patch.object(complement, 'download', side_effect=AssertionError('Network forbidden')):
            first = complement.render(self.palettes, '0.2.0', self.source)
            self.assertEqual(first, complement.render(self.palettes, '0.2.0', self.source))
        source = first.decode()
        complement.validate(source, self.palettes, '0.2.0')
        self.assertIn('@version      0.2.0', source)
        self.assertNotIn('@updateURL', source)
        self.assertNotIn('@import', source)
        self.assertNotIn('{{', source)
        self.assertIn('prefers-color-scheme: dark', source)
        self.assertIn('MIT', source)

    def test_custom_palettes_change_both_modes_without_hardcoded_fallback(self):
        before = complement.render(self.palettes, '0.2.0', self.source)
        self.palettes['dark']['base'] = '#123456'
        self.palettes['light']['base'] = '#abcdef'
        after = complement.render(self.palettes, '0.2.0', self.source)
        self.assertNotEqual(before, after)
        self.assertIn(b'--achroma-complement-base: #123456;', after)
        self.assertIn(b'--achroma-complement-base: #abcdef;', after)
        complement.validate(after.decode(), self.palettes, '0.2.0')

    def test_missing_corrupt_and_mismatched_source_lock_fail(self):
        path = self.source / 'upstream.user.css'
        original = path.read_bytes()
        path.write_bytes(original + b'\n')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            complement.render(self.palettes, '0.2.0', self.source)
        path.write_bytes(original)
        lockpath = self.source / 'upstream.lock.json'
        lock = json.loads(lockpath.read_text())
        lock['version'] = '999'
        lockpath.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, 'version mismatch'):
            complement.render(self.palettes, '0.2.0', self.source)
        lockpath.unlink()
        with self.assertRaises(FileNotFoundError):
            complement.render(self.palettes, '0.2.0', self.source)

    def test_unreviewed_template_roles_markers_and_imports_fail(self):
        path = self.source / 'style.css.tmpl'
        original = path.read_text()
        for source in (original.replace('var(--achroma-complement-base)', 'var(--achroma-complement-typo)'),
                       original + '\n{{UNKNOWN}}', original + '\n@import "https://bad.test/css";',
                       original + '\n@updateURL https://bad.test/css',
                       original.replace('{{LIGHT_PALETTE}}', '')):
            path.write_text(source)
            with self.subTest(source=source[-60:]), self.assertRaises(ValueError):
                complement.render(self.palettes, '0.2.0', self.source)

    def test_check_compares_bytes_even_if_version_unchanged_and_never_writes(self):
        previous = (self.source / 'upstream.user.css').read_bytes()
        lock = (self.source / 'upstream.lock.json').read_bytes()
        for data, changed in ((previous, False), (previous + b'\n', True)):
            with patch.object(complement, 'download', return_value=data):
                self.assertEqual(complement.check_upstream(self.source), changed)
            self.assertEqual((self.source / 'upstream.user.css').read_bytes(), previous)
            self.assertEqual((self.source / 'upstream.lock.json').read_bytes(), lock)

    def test_snapshot_uses_fixed_url_and_refuses_overwrite(self):
        previous = (self.source / 'upstream.user.css').read_bytes()
        destination = Path(self.temp.name) / 'new snapshot'
        with patch.object(complement, 'download', return_value=previous):
            complement.snapshot(destination)
            lock, data = complement.upstream_inputs(destination)
            self.assertEqual(lock['url'], 'https://userstyles.world/api/style/25419.user.css')
            self.assertEqual(data, previous)
            with self.assertRaises(FileExistsError):
                complement.snapshot(destination)

    def test_snapshot_identity_license_and_network_errors_leave_no_output(self):
        previous = (self.source / 'upstream.user.css').read_bytes()
        destination = Path(self.temp.name) / 'rejected'
        for data in (b'<html>Not a style</html>', previous.replace(b'@license      MIT', b'@license      GPL'),
                     previous.replace(b'achroma complement', b'other style')):
            with patch.object(complement, 'download', return_value=data), self.assertRaises(ValueError):
                complement.snapshot(destination)
            self.assertFalse(destination.exists())
        with patch.object(complement, 'download', side_effect=OSError('download failed')):
            with self.assertRaises(OSError):
                complement.snapshot(destination)
        self.assertFalse(destination.exists())

    def test_standalone_validation_rejects_rehashed_palette_metadata_and_network_changes(self):
        original = complement.render(self.palettes, '0.2.0', self.source).decode()
        for source in (original.replace('@version      0.2.0', '@version      9.9.9'),
                       original.replace('@license      MIT', '@license      GPL'),
                       original.replace('--achroma-complement-base: #1e1e1e;',
                                        '--achroma-complement-base: #000000;'),
                       original.replace('prefers-color-scheme: dark', 'prefers-color-scheme: light'),
                       original + '\n@import "https://bad.test/css";'):
            with self.subTest(source=source[-60:]), self.assertRaises(ValueError):
                complement.validate(source, self.palettes, '0.2.0')


if __name__ == '__main__':
    unittest.main()
